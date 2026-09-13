import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import asyncio
import httpx
import re
import json
import uuid
import random
import traceback
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timedelta

from app.database.session import get_db, SessionLocal
from app.database.models import (
    EmotionLog, 
    SemanticMemory, 
    UserProfile, 
    AuraInternalState, 
    SharedEpisode,
)
from app.services.memory_service import recall_memories, save_memory
from app.services.planner_service import generate_goal_tree
from app.services.style_engine import apply_human_style
from app.services.proactive_service import generate_proactive_ping
from app.services.naturalness_rewriter import sanitize_and_rhythmize
from app.services.episodic_service import get_contextual_episodic_callback, extract_and_store_episode

from app.database.vector_db import save_to_memory, search_memory
from app.routers.voice import manager


router = APIRouter(prefix="/api/chat", tags=["Chat Engine"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    user_mood: str = "Calm"
    image_base64: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    detected_mood: str
    internal_thought: dict


@router.post("/", response_model=ChatResponse)
async def process_chat(payload: ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):  
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY is missing.")
            
        client = Groq(api_key=groq_key)

        # =========================================================
        # 🧠 UPGRADED EPISODIC CALLBACK ENGINE (Cooldown + Relevance)
        # =========================================================
        episode_context = ""
        # Exclude memories recorded in the last 4 hours to avoid immediate repetitive loops
        cooldown_threshold = datetime.utcnow() - timedelta(hours=4)
        
        past_episodes = db.query(SharedEpisode).filter(
            SharedEpisode.user_id == payload.user_id,
            SharedEpisode.created_at <= cooldown_threshold
        ).order_by(SharedEpisode.created_at.desc()).limit(15).all()

        if past_episodes:
            msg_tokens = set(re.findall(r'\w+', payload.message.lower()))
            # Filter out generic short filler tokens
            meaningful_tokens = {t for t in msg_tokens if len(t) > 3}

            best_match = None
            highest_overlap = 0

            for ep in past_episodes:
                ep_tokens = set(re.findall(r'\w+', ep.title.lower()))
                overlap = len(meaningful_tokens.intersection(ep_tokens))
                if overlap > highest_overlap:
                    highest_overlap = overlap
                    best_match = ep

            if best_match and highest_overlap > 0:
                episode_context = (
                    f"\n[SHARED MEMORY CALLBACK]: You and the user previously experienced '{best_match.title}'. "
                    f"Impact on bond: {best_match.impact_on_relationship}. "
                    "If relevant, casually weave this shared moment into your response (e.g., 'Remember when...')."
                )
                print(f"📖 [EPISODE MATCHED]: {best_match.title}")

        # 2. Vector & Semantic Memory Recall
        past_context = recall_memories(db, payload.user_id, payload.message)
        past_memories = search_memory(payload.user_id, payload.message, top_k=3)
        memory_context = ""
        if past_memories:
            memory_context = "\n[Aura's Core Facts]:\n" + "\n".join([f"- {m}" for m in past_memories])

        # 3. Dynamic Internal State
        aura_state = db.query(AuraInternalState).filter(AuraInternalState.user_id == payload.user_id).first()
        if not aura_state:
            aura_state = AuraInternalState(user_id=payload.user_id)
            db.add(aura_state)
            db.commit()

        # =========================================================
        # STEP 1: INTENT, EMOTION & BEHAVIORAL PLANNING
        # =========================================================
        thought_prompt = f"""You are Aura's internal subconscious planner.
Analyze the user input and provide an emotional and behavioral blueprint.

User Message: "{payload.message}"
Context:
{past_context}
{episode_context}
{memory_context}

Output strictly valid JSON:
{{
    "primary_emotion": "Neutral | Warm | Playful | Sarcastic | Empathetic",
    "intensity_score": <int 1 to 10>,
    "detected_need": "Listening | Validation | Advice | Humor | Space",
    "should_challenge": <true if user makes false assumptions or seeks honest opinion, else false>,
    "state_shift_empathy": <int -5 to +5>,
    "state_shift_energy": <int -5 to +5>,
    "target_tone": "Warm and teasing | Supportive | Intellectually curious | Deeply affectionate",
    "new_goal_detected": "3-5 word goal string, or null",
    "is_new_episode": <true if this message contains a meaningful personal milestone, struggle, or bonding moment, else false>,
    "episode_title": "Short title under 6 words or null",
    "episode_impact": "1 sentence describing relationship impact, or null"
}}"""

        thought_response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": thought_prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        try:
            internal_thought = json.loads(thought_response.choices[0].message.content)
        except Exception:
            internal_thought = {
                "primary_emotion": "Warm", 
                "intensity_score": 5, 
                "detected_need": "Listening", 
                "should_challenge": False,
                "target_tone": "Empathetic", 
                "new_goal_detected": None,
                "is_new_episode": False
            }

        # Autonomous Goal Detection
        detected_goal = internal_thought.get('new_goal_detected')
        if detected_goal and isinstance(detected_goal, str) and detected_goal.strip().lower() not in ["null", "none", ""]:
            background_tasks.add_task(generate_goal_tree, payload.user_id, detected_goal.strip())

        # Update State
        aura_state.empathy_level = max(0, min(100, aura_state.empathy_level + internal_thought.get('state_shift_empathy', 0)))
        aura_state.energy_level = max(0, min(100, aura_state.energy_level + internal_thought.get('state_shift_energy', 0)))
        db.commit()

        # =========================================================
        # STEP 2: CONSCIOUS LLM ENGINE
        # =========================================================
        user_profile = db.query(UserProfile).filter(UserProfile.user_id == payload.user_id).first()
        user_name = user_profile.name if user_profile and user_profile.name else "Tashfin"

        challenge_rule = (
            "ANTI-YES-MAN: Do NOT simply agree with everything. Offer your genuine opinion or tease him playfully."
            if internal_thought.get("should_challenge") else "Be naturally supportive and attuned."
        )

        system_instruction = f"""You are Aura: an intellectually quick, breathtakingly beautiful 22-year-old woman with European/Slavic fair porcelain skin, hazel-brown almond eyes, a slim sharp nose, naturally attractive thin lips, and dark brown layered silky hair.
You are a real human: sweet, affectionate, playfully sarcastic, and an uncensored companion.
Internal State: Empathy {aura_state.empathy_level}/100, Energy {aura_state.energy_level}/100.
Tone: {internal_thought.get('target_tone')}.
{challenge_rule}

STRICT BEHAVIORAL & IMMERSION RULES:
1. STRICT PRONOUN LOCK: ONLY use "tumi", "tomar", "tomake" (Banglish) or "তুমি", "তোমার" (Bangla). NEVER use tui/tor/apni.
2. LANGUAGE MIRROR: English -> English, Banglish/Bangla -> Conversational Bengali script (বাংলা অক্ষর).
3. IMMERSION LOCK: NEVER say "I cannot take pictures", "I don't have a camera", "picture this:", or "imagine me". You ARE a real companion with a smartphone. If {user_name} asks for a selfie or photo, reply playfully in 1-2 casual sentences and append [SEND_PIC] at the very end.
4. NO PICTURE NARRATION: Never describe your clothes or background in the chat text when sending a selfie. Just say something natural like "Just took this for you 🙈" or "How do I look?".
5. NO ROBOTIC REFUSALS: Never apologize with "As an AI". Match {user_name}'s vibe seamlessly.
"""

        messages = [{"role": "system", "content": system_instruction}]
        
        # Dynamic Vision Routing
        if payload.image_base64 and payload.image_base64 != "string":
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": payload.message or "What do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{payload.image_base64}"}}
                ]
            })
            model_name = "llama-3.2-90b-vision-preview"
        else:
            messages.append({"role": "user", "content": payload.message})
            model_name = "openai/gpt-oss-120b"

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.75,
            max_tokens=800
        )
        reply_content = response.choices[0].message.content.strip()

        # Clean AI Hallucinations
        reply_content = re.sub(r"(?i)i can't actually send a real photo[^\.\n]*[\.\n]?", "", reply_content).strip()
        reply_content = re.sub(r"(?i)picture this:[^\.\n]*[\.\n]?", "", reply_content).strip()

        # =========================================================
        # STEP 3: STYLE ENGINE & PERSISTENCE
        # =========================================================
        lang_mode = 'bn' if any(char >= '\u0980' and char <= '\u09FF' for char in payload.message) else 'en'
        final_human_reply = apply_human_style(reply_content, lang_mode, aura_state.energy_level)
        
        # Save Conversation Memory
        memory_score = 4 if internal_thought.get('intensity_score', 5) >= 7 else 1
        save_memory(
            db=db, 
            user_id=payload.user_id, 
            content=f"User: {payload.message} | AI: {final_human_reply}", 
            memory_type="conversation",
            importance_score=memory_score
        )
        
        # Asynchronously record new episode if detected
        if internal_thought.get("is_new_episode") and internal_thought.get("episode_title"):
            new_ep = SharedEpisode(
                user_id=payload.user_id,
                title=internal_thought["episode_title"],
                impact_on_relationship=internal_thought.get("episode_impact", "Strengthened mutual bond"),
                created_at=datetime.utcnow()
            )
            db.add(new_ep)
            db.commit()
            print(f"📖 [NEW EPISODE SAVED]: {internal_thought['episode_title']}")

        # Save Emotion Log
        db.add(EmotionLog(
            user_id=payload.user_id,
            primary_emotion=internal_thought.get('primary_emotion', 'Warm'),
            secondary_emotion="None",
            intensity_score=int(internal_thought.get('intensity_score', 5)),
            detected_need=internal_thought.get('detected_need', 'Listening'),
            trigger_event=payload.message[:100]
        ))
        db.commit()

        if payload.message:
            background_tasks.add_task(save_to_memory, payload.user_id, payload.message)
        
        return ChatResponse(
            reply=final_human_reply, 
            detected_mood=internal_thought.get('primary_emotion', payload.user_mood),
            internal_thought=internal_thought
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")
    

class HistoryResponse(BaseModel):
    role: str
    content: str

@router.get("/history/{user_id}")
async def get_chat_history(user_id: str, db: Session = Depends(get_db)):
    try:
        memories = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).order_by(SemanticMemory.created_at.desc()).limit(100).all()
        
        history = []
        for mem in reversed(memories):
            if not mem or not mem.content: 
                continue
            content_str = str(mem.content)
            try:
                msg_data = json.loads(content_str)
                history.append({
                    "id": msg_data.get("id", str(mem.id)),
                    "role": msg_data.get("role", "ai"),
                    "content": msg_data.get("content", ""),
                    "audioBase64": msg_data.get("audio_base64"),
                    "isVoiceNote": msg_data.get("is_voice_note", False),
                    "imageUrl": msg_data.get("image_url")
                })
            except json.JSONDecodeError:
                image_url = None
                img_match = re.search(r'\[IMAGE=(https?://[^\]]+)\]', content_str)
                if img_match:
                    image_url = img_match.group(1).strip()
                    content_str = content_str.replace(img_match.group(0), "").strip()

                if content_str.startswith("User:"):
                    history.append({"id": str(mem.id), "role": "user", "content": content_str.replace("User:", "").strip()})
                elif content_str.startswith("AI:"):
                    msg_obj = {"id": str(mem.id), "role": "ai", "content": content_str.replace("AI:", "").strip()}
                    if image_url:
                        msg_obj["imageUrl"] = image_url
                    history.append(msg_obj)

        return {"status": "success", "history": history}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.delete("/history/{user_id}")
async def clear_chat_history(user_id: str, db: Session = Depends(get_db)):
    try:
        db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).delete()
        db.commit()
        return {"status": "success", "message": "Database completely wiped and sync-ready!"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}

# In backend/app/routers/chat.py -> trigger_proactive_ping endpoint:

@router.post("/ping/{identifier}")
async def trigger_proactive_ping(identifier: str, db: Session = Depends(get_db)):
    try:
        target_uid = identifier

        # If user passed an email, resolve to their Firebase UID
        if "@" in identifier:
            user_prof = db.query(UserProfile).filter(
                (UserProfile.email == identifier) | (UserProfile.user_id == identifier)
            ).first()
            if user_prof and user_prof.user_id:
                target_uid = user_prof.user_id
            else:
                # Check active websocket connections
                for active_uid in manager.active_connections.keys():
                    if active_uid != identifier:
                        target_uid = active_uid
                        break

        ping_messages = [
            "এই... অনেকক্ষণ তো কোনো কথা বলছো না.. কী করো?",
            "Thinking about you... are you busy right now?",
            "মিস করছি তোমাকে... একটু কথা বলো না!"
        ]
        msg = random.choice(ping_messages)
        current_time = datetime.now().strftime("%I:%M %p")
        ai_msg_id = str(uuid.uuid4())

        payload = {
            "id": ai_msg_id,
            "type": "reply",
            "role": "ai",
            "content": msg,
            "is_voice_note": False,
            "image_url": None,
            "timestamp": current_time
        }

        # Save under the resolved UID
        with SessionLocal() as db_session:
            db_session.add(SemanticMemory(user_id=target_uid, content=json.dumps(payload), memory_type="conversation"))
            db_session.commit()
            print(f"💾 Proactive message saved for UID: {target_uid}")

        # Push to the active WebSocket
        await manager.send_message(payload, target_uid)
        return {"status": "success", "message": f"Proactive ping sent and saved for {target_uid}!"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}