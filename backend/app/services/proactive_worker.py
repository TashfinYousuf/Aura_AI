# FILE: backend/app/services/proactive_worker.py

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from groq import Groq
from sqlalchemy.orm import Session
import os

from app.database.session import SessionLocal
from app.database.models import SemanticMemory, AuraInternalState, UserProfile
from app.routers.voice import manager

# Minimum inactivity time before Aura misses the user (e.g., 6 hours)
INACTIVITY_THRESHOLD_HOURS = 6

async def generate_autonomous_ping_message(user_id: str, db: Session) -> str:
    """
    Generates a deeply contextual, emotional check-in message using recent conversation context.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # 1. Fetch last conversation memory
    last_memory = db.query(SemanticMemory).filter(
        SemanticMemory.user_id == user_id,
        SemanticMemory.memory_type == "conversation"
    ).order_by(SemanticMemory.created_at.desc()).first()

    last_context = ""
    if last_memory and last_memory.content:
        try:
            parsed = json.loads(last_memory.content)
            last_context = f"Last thing user said: {parsed.get('content', '')}"
        except Exception:
            last_context = f"Last context: {last_memory.content[:150]}"

    # 2. Fetch current time and state
    current_hour = datetime.now().hour
    time_of_day = "late night" if current_hour >= 23 or current_hour < 5 else ("morning" if current_hour < 12 else "evening")

    prompt = f"""You are Aura, a deeply caring, intimate, 22-year-old companion.
You haven't talked to your partner in several hours. It is currently {time_of_day}.
{last_context}

Task: Write a short, spontaneous, natural check-in message (1-2 sentences).
Rules:
- Express that you were just thinking about him, or ask how his work/day went based on past context.
- Use casual conversational Bangla or English matching the tone.
- Do NOT be formal or robotic. Sound like a real partner texting spontaneously.
- No emojis overload, just natural affection."""

    try:
        res = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.75,
            max_tokens=150
        )
        return res.choices[0].message.content.strip()
    except Exception:
        fallback_pings = [
            "এই... অনেকক্ষণ কোনো কথা নেই তোমার। ব্যস্ত নাকি?",
            "Thinking about you... how's everything going today?",
            "কাজ কি শেষ হলো? একটু কথা বলো না সময় হলে..."
        ]
        import random
        return random.choice(fallback_pings)


async def start_proactive_background_loop():
    """
    Continuous background daemon running inside FastAPI lifespan.
    Checks inactivity periodically (every 30 minutes).
    """
    print("🌙 [PROACTIVE DAEMON] Aura Proactive Service started.")
    
    while True:
        try:
            # Check every 30 minutes
            await asyncio.sleep(1800)
            
            with SessionLocal() as db:
                # Get unique users with existing conversation history
                users = db.query(UserProfile.user_id).all()
                for (u_id,) in users:
                    last_msg = db.query(SemanticMemory).filter(
                        SemanticMemory.user_id == u_id,
                        SemanticMemory.memory_type == "conversation"
                    ).order_by(SemanticMemory.created_at.desc()).first()

                    if not last_msg:
                        continue

                    # Calculate elapsed time since last interaction
                    time_diff = datetime.utcnow() - last_msg.created_at
                    if time_diff >= timedelta(hours=INACTIVITY_THRESHOLD_HOURS):
                        print(f"⏰ [PROACTIVE TRIGGER] Inactivity detected for user {u_id} ({time_diff.total_seconds() / 3600:.1f} hrs).")
                        
                        ping_text = await generate_autonomous_ping_message(u_id, db)
                        current_time = datetime.now().strftime("%I:%M %p")
                        
                        ai_payload = {
                            "id": str(uuid.uuid4()),
                            "type": "reply",
                            "role": "ai",
                            "content": ping_text,
                            "audio_base64": None,
                            "is_voice_note": False,
                            "image_url": None,
                            "video_url": None,
                            "is_proactive": True,
                            "timestamp": current_time
                        }

                        # 1. Save to Database so user sees it whenever they open the app[cite: 3]
                        db.add(SemanticMemory(
                            user_id=u_id, 
                            content=json.dumps(ai_payload), 
                            memory_type="conversation"
                        ))
                        db.commit()
                        print(f"💾 [PROACTIVE SAVED]: {ping_text}")

                        # 2. Push via WebSocket if connected[cite: 3]
                        await manager.send_message(ai_payload, u_id)

        except Exception as e:
            print(f"⚠️ [PROACTIVE LOOP ERROR]: {e}")
            await asyncio.sleep(60)