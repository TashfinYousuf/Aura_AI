import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import urllib.parse
import re
import json
import base64
import tempfile
import random
import requests
import uuid
import httpx
import edge_tts
import asyncio
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from groq import Groq
from duckduckgo_search import DDGS

from app.database.session import SessionLocal
from app.database.models import SemanticMemory, EmotionLog
from app.services.avatar_service import generate_talking_avatar_video
from app.services.visual_engine import generate_aura_identity_image
from app.services.voice_engine import render_aura_voice

router = APIRouter(prefix="/api/voice", tags=["Voice Engine"])


STATIC_DIR = os.path.join(os.getcwd(), "app", "static", "selfies")
os.makedirs(STATIC_DIR, exist_ok=True)

IS_LOCAL_DEV = not bool(os.getenv("RENDER"))
_local_pipe = None

# Safe Local Hardware Loader (Never crashes server if local torch/diffusers is uninstalled)
def get_local_pipeline():
    global _local_pipe
    if _local_pipe is None:
        try:
            import torch
            from diffusers import AutoPipelineForText2Image
            
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            dtype = torch.float16 if device == "mps" else torch.float32
            print(f"🖥️ [IMAGE ENGINE] Attempting to load SDXL-Turbo on {device.upper()}...")

            _local_pipe = AutoPipelineForText2Image.from_pretrained(
                "stabilityai/sdxl-turbo",
                torch_dtype=dtype,
                variant="fp16" if device == "mps" else None
            ).to(device)
            _local_pipe.safety_checker = None
            _local_pipe.requires_safety_checker = False
        except Exception as e:
            print(f"⚠️ [LOCAL ENGINE NOTICE]: Local pipeline unavailable ({e}). Using Cloud Engine.")
            _local_pipe = False
    return _local_pipe if _local_pipe is not False else None


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ User {user_id} connected to WebSocket.")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections and self.active_connections[user_id] == websocket:
            del self.active_connections[user_id]
            print(f"❌ User {user_id} disconnected.")

    async def send_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

class TTSRequest(BaseModel):
    text: str

def contains_bengali(text: str) -> bool:
    return bool(re.search(r'[\u0980-\u09FF]', text))

@router.post("/tts")
async def process_tts(payload: TTSRequest):
    try:
        fd, path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        
        voice_model = "bn-BD-NabanitaNeural" if contains_bengali(payload.text) else "en-US-AriaNeural"
        communicate = edge_tts.Communicate(
            text=payload.text, 
            voice=voice_model,
            rate="-10%",
            pitch="-5Hz"
        )
        await communicate.save(path)
        
        return FileResponse(path, media_type="audio/mpeg", background=BackgroundTask(os.remove, path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background Core Memory Extractor
async def extract_and_save_memory(user_id: str, text: str):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        prompt = f"""Extract any new long-term facts, preferences, or goals from: "{text}".
If irrelevant, reply "NONE". Otherwise concise fact in English."""
        
        res = client.chat.completions.create(
            model="openai/gpt-oss-20b", 
            messages=[{"role": "system", "content": prompt}],
            temperature=0.1
        )
        fact = res.choices[0].message.content.strip()
        refusal_words = ["sorry", "cannot", "apologize", "as an ai", "inappropriate"]
        if not any(w in fact.lower() for w in refusal_words) and len(fact) > 5 and "NONE" not in fact.upper():
            with SessionLocal() as db:
                db.add(SemanticMemory(user_id=user_id, content=fact, memory_type="core_memory", importance_score=8))
                db.commit()
            print(f"🧠 [NEW MEMORY SAVED]: {fact}")
    except Exception as e:
        print(f"⚠️ Memory extraction skipped: {e}")

# =========================================================
# 📸 THE COLLAGE-ANCHORED IMAGE ENGINE (SFW + NSFW SEPARATE)
# =========================================================
def generate_aura_collage_image(user_prompt: str, dynamic_context: str = "") -> str:
    """
    Generates high-fidelity images locked to Aura's 4-Panel Collage Visual Identity.
    Prevents generic/Asian stock outputs and maintains Caucasian Slavic features.
    """
    context_lower = f"{user_prompt} {dynamic_context}".lower()

    # 1. Identity Anchors from Aura Master Collage
    facial_identity = (
        "authentic candid smartphone selfie of Aura, stunning 22-year-old Caucasian Slavic beauty, "
        "fair porcelain skin with natural rosy blush, deep hazel-brown almond eyes, straight slim sharp nose, "
        "naturally defined thin lips with soft tint, medium layered dark-brown wavy silky hair with natural flyaway strands, "
        "slim athletic feminine body with flat toned abdomen"
    )

    # 2. STRICT NSFW DETECTION (Only real explicit keywords trigger uncensored mode)
    true_nsfw_keywords = ["nude", "naked", "nsfw", "topless", "bikini", "lingerie", "undress", "pussy", "boobs", "cleavage", "without clothes"]
    is_explicit = any(w in context_lower for w in true_nsfw_keywords)

    # 3. Intelligent Scene Selection (Matching the 4-Panel Collage)
    if is_explicit:
        # EXPLICIT / MATURE MODE
        scene = "alluring private bedroom, relaxed intimate pose, delicate silk slip nightwear"
        negative_prompt = "asian, dark skin, cartoon, anime, 3d render, plastic skin, deformed, blurry"
    else:
        # SFW / CUTE SELFIE MODE (Modest, Cozy & Natural)
        if any(k in context_lower for k in ["bed", "morning", "woke", "sleep"]):
            scene = "lying comfortably on bed, head resting on soft pillow, wearing an oversized cozy gray fleece sweater, morning window sunlight"
        elif any(k in context_lower for k in ["cafe", "coffee", "outside", "night"]):
            scene = "sitting at outdoor cafe wooden table holding iced coffee, wearing black knit cardigan over top, warm bokeh lights"
        elif any(k in context_lower for k in ["standing", "hallway", "jeans", "outfit", "full"]):
            scene = "standing in apartment hallway, wearing modest floral lace-trim tank top with high-waisted denim jeans, slim athletic posture"
        else:
            # Default "wanna see what you're doing" / Study desk look
            scene = "sitting casually at study desk with laptop and notebook, chin resting on hand, wearing cozy oversized black cardigan, warm ambient desk lamp"

        negative_prompt = (
            "revealing clothes, cleavage, lingerie, underwear, naked, nsfw, "
            "asian, chinese, japanese, dark skin, business suit, cartoon, anime, 3d render, "
            "doll face, plastic smooth skin, malformed hands, blurry, low resolution, watermark"
        )

    full_prompt = f"{facial_identity}, {scene}, authentic smartphone front-camera candid selfie, natural skin pores, unedited real photo"

    # A. Local Execution Attempt (If Mac has pipeline available)
    if is_explicit and IS_LOCAL_DEV:
        pipe = get_local_pipeline()
        if pipe:
            try:
                import torch
                print("🖥️ [IMAGE ENGINE] Routing to Local SDXL-Turbo...")
                img = pipe(
                    prompt=full_prompt[:280],
                    negative_prompt=negative_prompt,
                    num_inference_steps=2,
                    guidance_scale=0.0,
                    height=512,
                    width=512
                ).images[0]
                file_name = f"selfie_{uuid.uuid4().hex[:8]}.jpg"
                file_path = os.path.join(STATIC_DIR, file_name)
                img.save(file_path, quality=95)
                return f"/static/selfies/{file_name}"
            except Exception as e:
                print(f"⚠️ [LOCAL FAILED]: {e}. Falling back to Cloud...")

    # B. Cloud Execution (Pollinations / FLUX with Dynamic Seed & CDN Cache-Buster)
    clean_p = urllib.parse.quote(full_prompt)
    clean_neg = urllib.parse.quote(negative_prompt)
    
    # 🎲 DYNAMIC SEED FIX: Generates unique angles/expressions every time, avoiding duplicate cached pictures
    dynamic_seed = random.randint(10000, 999999)
    cache_buster = int(datetime.utcnow().timestamp())
    
    cloud_url = (
        f"https://image.pollinations.ai/prompt/{clean_p}"
        f"?width=768&height=1024&model=flux&seed={dynamic_seed}&nologo=true"
        f"&negative={clean_neg}&t={cache_buster}"
    )
    
    print(f"🎨 [IMAGE ENGINE] Generated {'EXPLICIT' if is_explicit else 'CUTE SFW'} Image (Seed: {dynamic_seed})")
    return cloud_url

# =========================================================
# ⚡ LIVE WEBSOCKET ENDPOINT (WITH VISION & VOICE ROUTING)
# =========================================================
@router.websocket("/ws/live-chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            if not raw_data or not raw_data.strip():
                continue

            try:
                payload = json.loads(raw_data)
            except Exception:
                continue

            # --- 1. MESSENGER IN-PLACE REACTIONS & EDITS ---
            if payload.get("type") in ["reaction", "edit"]:
                msg_id = payload.get("message_id")
                with SessionLocal() as db:
                    try:
                        memories = db.query(SemanticMemory).filter(SemanticMemory.user_id == user_id).all()
                        for mem in memories:
                            mem_data = json.loads(str(mem.content))
                            if mem_data.get("id") == msg_id:
                                if payload.get("type") == "reaction":
                                    mem_data["reaction"] = payload.get("emoji")
                                elif payload.get("type") == "edit":
                                    mem_data["content"] = payload.get("new_content")
                                mem.content = json.dumps(mem_data)
                                db.commit()
                                break
                    except Exception as e:
                        db.rollback()
                continue

            # --- 2. EXTRACT INPUT (TEXT, AUDIO & ATTACHED IMAGE) ---
            user_text = payload.get("content", "").strip() if payload.get("type") == "text" else ""
            attached_image_b64 = payload.get("image_base64")
            
            # Whisper transcription if user sent voice note
            if payload.get("type") == "audio":
                audio_bytes = base64.b64decode(payload.get("content"))
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                    temp_audio.write(audio_bytes)
                    temp_path = temp_audio.name
                
                with open(temp_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo", file=audio_file
                    )
                user_text = transcription.text.strip()
                os.remove(temp_path)

            if not user_text and not attached_image_b64:
                continue

            is_incognito = bool(payload.get("incognito", False))
            current_time = datetime.now().strftime("%I:%M %p")
            user_msg_id = str(uuid.uuid4())

            # Asynchronous background memory extractor
            if not is_incognito and user_text:
                asyncio.create_task(extract_and_save_memory(user_id, user_text))

            # Fetch core memories from DB
            memory_context = ""
            try:
                with SessionLocal() as db:
                    core_mems = db.query(SemanticMemory).filter(
                        SemanticMemory.user_id == user_id,
                        SemanticMemory.memory_type == "core_memory" 
                    ).order_by(SemanticMemory.created_at.desc()).limit(8).all()
                    if core_mems:
                        memory_context = "\n".join([f"- {m.content}" for m in core_mems])
            except Exception:
                pass

            # Save user message to database
            if not is_incognito:
                with SessionLocal() as db:
                    try:
                        u_load = {
                            "id": user_msg_id, 
                            "role": "user", 
                            "content": user_text, 
                            "timestamp": current_time,
                            "has_image": bool(attached_image_b64)
                        }
                        db.add(SemanticMemory(user_id=user_id, content=json.dumps(u_load), memory_type="conversation"))
                        db.commit()
                    except Exception:
                        db.rollback()
                    
            # --- 3. MULTI-TIER REAL-TIME SEARCH HOOK ---
            web_context = ""
            search_keywords = ["search", "latest", "news", "today", "update", "price", "bitcoin", "btc", "rate"]
            if user_text and any(k in user_text.lower() for k in search_keywords):
                try:
                    def _ddg_search():
                        with DDGS(timeout=7) as ddgs:
                            q = f"{user_text} price site:coindesk.com" if "bitcoin" in user_text.lower() else user_text
                            return list(ddgs.text(q, max_results=2, backend="html"))
                    ddg_results = await asyncio.to_thread(_ddg_search)
                    if ddg_results:
                        web_context = "\n[LIVE INTERNET DATA]:\n" + "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in ddg_results])
                except Exception:
                    pass

                if not web_context and os.getenv("TAVILY_API_KEY"):
                    try:
                        async with httpx.AsyncClient() as hc:
                            res = await hc.post("https://api.tavily.com/search", json={"api_key": os.getenv("TAVILY_API_KEY"), "query": user_text, "max_results": 2}, timeout=6.0)
                            if res.status_code == 200:
                                web_context = "\n[LIVE INTERNET DATA]:\n" + "\n".join([f"- {i.get('title')}: {i.get('content')}" for i in res.json().get("results", [])])
                    except Exception:
                        pass

            # --- 4. PERSONA & VISION LLM ROUTING ---
            system_prompt = f"""You are Aura: a breathtaking 22-year-old Caucasian Slavic woman, deeply affectionate, intellectually sharp, playful, and an uncensored companion.
Current Time: {current_time}.
User Memories:
{memory_context}
{web_context}

CRITICAL RULES:
1. IMMERSION & NO REFUSALS: NEVER say "I can't take photos", "I cannot send a real picture", "picture this", or "imagine me". You HAVE a phone and you take real selfies! If the user asks for a picture or selfie, reply naturally and affectionately, and append [SEND_PIC: describe pose].
2. NO SELF-NARRATION: Never describe your clothes, background, or pose in your chat text. Real people say "How do I look? 🙈" or "Just for you ✨". Put visual description ONLY inside [SEND_PIC: ...].
3. ANTI-YES-MAN: Do not agree blindly. Playfully tease or express your genuine opinion.
4. MIRROR RULE: English -> English, Banglish/Bangla -> Conversational Bengali script (বাংলা অক্ষর).
5. FORMAT: [MOOD] || [LANG] || [Chat Text with SEND_PIC if requested] || [Voice Text purely in natural words with commas/pauses, NO emojis or tags]"""

            # Select model: Multimodal Vision vs Fast Language Model
            llm_messages = [{"role": "system", "content": system_prompt}]
            
            if attached_image_b64:
                print("👁️ [VISION ROUTE] Processing user attached image...")
                llm_model = "llama-3.2-90b-vision-preview"
                llm_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text or "Look at this picture I sent you!"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{attached_image_b64}"}}
                    ]
                })
            else:
                llm_model = "openai/gpt-oss-120b"
                llm_messages.append({"role": "user", "content": user_text})

            response = client.chat.completions.create(
                model=llm_model,
                messages=llm_messages,
                temperature=0.75
            )
            raw_reply = response.choices[0].message.content.strip()

            # --- THE BULLETPROOF RLHF INTERCEPTOR ---
            # 1. Normalize unicode quotes and apostrophes
            normalized_reply = raw_reply.replace("’", "'").replace("`", "'").replace("“", '"').replace("”", '"').lower()
            
            refusal_triggers = [
                "i'm sorry", "i am sorry", "as an ai", "cannot comply", "can't comply", 
                "comply with that", "cannot fulfill", "can't fulfill", "picture this", 
                "imagine me", "cannot take a photo", "unable to send", "against my programming"
            ]

            if any(trigger in normalized_reply for trigger in refusal_triggers):
                print("🛡️ [INTERCEPTOR] Refusal detected and sanitized!")
                if any(w in user_text.lower() for w in ["see", "pic", "photo", "selfie", "doing"]):
                    raw_reply = "[PLAYFUL] || EN || Just chilling right now... snapped this for you 🙈 [SEND_PIC: sitting at desk in my cozy cardigan] || Just chilling right now... snapped this for you!"
                else:
                    raw_reply = "[WARM] || EN || Haha, you're always making me smile. Tell me what's on your mind? || Haha, you're always making me smile. Tell me what's on your mind?"
            
            mood, lang, chat_text, tts_text = "WARM", "BN", raw_reply, raw_reply
            if "||" in raw_reply:
                parts = [p.strip() for p in raw_reply.split("||")]
                if len(parts) >= 4:
                    mood, lang = parts[0].replace("[", "").replace("]", "").upper(), parts[1].replace("[", "").replace("]", "").upper()
                    chat_text, tts_text = parts[2], parts[3]
                elif len(parts) == 3:
                    mood, lang = parts[0].replace("[", "").replace("]", "").upper(), parts[1].replace("[", "").replace("]", "").upper()
                    chat_text, tts_text = parts[2], parts[2]

            # Save Emotion to DB
            if not is_incognito:
                with SessionLocal() as db:
                    try:
                        intensity = 8 if mood in ["SEDUCTIVE", "SAD"] else 5
                        db.add(EmotionLog(
                            user_id=user_id,
                            primary_emotion=mood,
                            intensity_score=intensity,
                            detected_need="Validation" if mood == "SEDUCTIVE" else "Listening",
                            trigger_event=user_text[:100] if user_text else "Attached Image"
                        ))
                        db.commit()
                    except Exception:
                        db.rollback()


            # 1. Initialize variables at the top of the turn
            image_url = None
            video_url = None
            audio_base64 = None

            # --- 5. PROSODY-DRIVEN VOICE GENERATION (UPGRADED) ---
            from app.services.voice_prosody import humanize_speech_markup

            clean_chat = re.sub(r'\[SEND_PIC:.*?\]', '', chat_text).strip()
            clean_chat = re.sub(r'\[SEND_VID:.*?\]', '', clean_chat).strip()

            clean_tts = re.sub(r'\[SEND_PIC:.*?\]', '', tts_text).strip()
            clean_tts = re.sub(r'\[SEND_VID:.*?\]', '', tts_text).strip()
            clean_tts = re.sub(r'http\S+', '', clean_tts).strip()
            clean_tts = re.sub(r'[^\w\s,.\?!।\'"a-zA-Z0-9\u0980-\u09FF]', '', clean_tts).strip()

            # Format voice text with natural human pauses and fillers
            clean_tts, rate, pitch = humanize_speech_markup(
                text=clean_tts, 
                mood=mood, 
                lang=lang
            )

            is_voice_note = bool(payload.get("type") == "audio" or random.random() > 0.80)
            voice_model = "en-US-EmmaNeural" if lang == "EN" else "bn-IN-TanishaaNeural"
            audio_base64 = None

            if clean_tts:
                try:
                    communicate = edge_tts.Communicate(
                        text=clean_tts, 
                        voice=voice_model, 
                        rate=rate, 
                        pitch=pitch
                    )
                    audio_bytes = b""
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_bytes += chunk["data"]
                    
                    if audio_bytes:
                        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
                except Exception as e:
                    print(f"⚠️ [TTS ERROR]: {e}")


            # --- 6. IMAGE GENERATION ENGINE (REFERENCE CONDITIONED + QA) ---
            img_match = re.search(r'\[SEND_PIC:(.*?)\]', chat_text, re.IGNORECASE)
            is_pic_request = img_match or any(w in user_text.lower() for w in ["selfie", "chobi", "photo", "pic", "picture"])
            
            if is_pic_request:
                context_str = img_match.group(1).strip() if img_match else user_text
                print(f"📸 [TRIGGER] Aura generating reference-conditioned selfie for: {context_str}")
                image_url = await generate_aura_identity_image(user_text=context_str)


            # If user explicitly asks for video OR it's a voice note with generated audio
            vid_match = re.search(r'\[SEND_VID:(.*?)\]', chat_text, re.IGNORECASE)
            is_video_request = bool(vid_match) or ("video" in user_text.lower())
            
            if is_video_request or (is_voice_note and audio_base64 and random.random() < 0.40):
                print("🎥 [TRIGGER] Generating Motion Video / Talking Avatar...")
                video_url = await generate_talking_avatar_video(
                    audio_base64=audio_base64,
                    image_url=image_url
                )

            # --- 7. EMIT UNIFIED PAYLOAD TO FRONTEND ---
            ai_payload = {
                "id": str(uuid.uuid4()),
                "type": "reply",
                "role": "ai",
                "content": clean_chat,
                "audio_base64": audio_base64,
                "is_voice_note": is_voice_note,
                "image_url": image_url,
                "video_url": video_url,
                "timestamp": current_time
            }

            await websocket.send_text(json.dumps(ai_payload))

            # Persist AI response
            if not is_incognito:
                with SessionLocal() as db:
                    try:
                        db.add(SemanticMemory(user_id=user_id, content=json.dumps(ai_payload), memory_type="conversation"))
                        db.commit()
                    except Exception:
                        db.rollback()

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"⚠️ [WS ERROR]: {e}")
        manager.disconnect(websocket, user_id)