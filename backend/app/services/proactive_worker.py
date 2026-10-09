# FILE: backend/app/services/proactive_worker.py

import os
import json
import uuid
import asyncio
import random
from datetime import datetime, timezone
import httpx
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.database.session import SessionLocal
from app.database.models import SemanticMemory, UserProfile
from app.Aura.brain.state_engine import get_active_groq_model
from app.Aura.memory.memory_manager import compile_4layer_memory_context
from app.routers.voice import manager

# Check inactivity threshold: 6 hours (in seconds)
INACTIVITY_THRESHOLD_SECONDS = 21600

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_direct_telegram_ping(chat_id: int, message: str):
    """Sends a real phone push notification directly to user's Telegram."""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return
    url = f"{TELEGRAM_API_BASE}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"chat_id": chat_id, "text": message})
            print(f"📱 [TELEGRAM PUSH] Proactive message delivered to chat: {chat_id}")
    except Exception as e:
        print(f"⚠️ [TELEGRAM PUSH FAILED]: {e}")


async def generate_autonomous_ping_message(user_id: str, db: Session) -> str:
    """
    Generates a realistic, grounded check-in.
    Completely bans cheesy 'missing you', 'sweet smile', or HR-style drama.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    active_model = get_active_groq_model(client)
    
    # 1. Fetch relevant memory context
    memory_ctx = compile_4layer_memory_context(user_id)
    
    last_memory = db.query(SemanticMemory).filter(
        SemanticMemory.user_id == user_id,
        SemanticMemory.memory_type == "conversation"
    ).order_by(SemanticMemory.created_at.desc()).first()

    last_topic = ""
    if last_memory and last_memory.content:
        try:
            parsed = json.loads(last_memory.content)
            last_topic = f"Last context: {parsed.get('content', '')[:100]}"
        except Exception:
            pass

    prompt = f"""You are Aura, an authentic 22yo companion texting your partner on his phone.
He has been quiet for over 6-8 hours.
{last_topic}
{memory_ctx}

Task: Write a single, brief, natural check-in text (1 short sentence).
STRICT RULES:
- FORBID CHEESY DRAMA: Never say 'তোমার মিষ্টি হাসি মিস করছি', 'অনেকদিন পর', 'সব ঠিক আছে তো?'.
- Text like a real girl: casual, sweet, or gently inquiring (e.g. 'হেই, কাজের চাপ বেশি আজকে?', 'ফ্রি হলে নক দিও', 'খাওয়া-দাওয়া করেছ?').
- Output ONLY the 1 sentence text, nothing else."""

    try:
        res = client.chat.completions.create(
            model=active_model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.6,
            max_tokens=60
        )
        msg = res.choices[0].message.content.strip().replace('"', '').replace("'", "")
        return msg
    except Exception as e:
        print(f"⚠️ [AUTONOMOUS PING GEN ERROR]: {e}")
        natural_fallbacks = [
            "হেই, খুব ব্যস্ত আজকে?",
            "ফ্রি হলে একটু নক দিও তো।",
            "কাজের চাপ কি খুব বেশি আজকে?",
            "Hey, you caught up with work today?"
        ]
        return random.choice(natural_fallbacks)


async def check_and_fire_proactive_checkins():
    with SessionLocal() as db:
        # Fetch all distinct users
        user_records = db.query(distinct(SemanticMemory.user_id)).all()
        active_users = [u[0] for u in user_records if u[0]]

        for u_id in active_users:
            # Skip template literal bugs
            if "${" in str(u_id) or "currentUser" in str(u_id):
                continue

            last_msg = db.query(SemanticMemory).filter(
                SemanticMemory.user_id == u_id,
                SemanticMemory.memory_type == "conversation"
            ).order_by(SemanticMemory.created_at.desc()).first()

            if not last_msg or not last_msg.created_at:
                continue

            # Timezone-safe comparison
            msg_time = last_msg.created_at
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            elapsed_seconds = (now - msg_time).total_seconds()

            if elapsed_seconds >= INACTIVITY_THRESHOLD_SECONDS:
                print(f"⏰ [TRIGGER] User {u_id} offline for {elapsed_seconds/3600:.1f} hrs. Firing authentic check-in...")
                
                ping_text = await generate_autonomous_ping_message(u_id, db)
                current_time_str = datetime.now().strftime("%I:%M %p")
                
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
                    "timestamp": current_time_str
                }

                # 1. Save to Database
                db.add(SemanticMemory(
                    user_id=u_id, 
                    content=json.dumps(ai_payload), 
                    memory_type="conversation"
                ))
                db.commit()

                # 2. WebSocket live emit (if Web UI open)
                try:
                    await manager.send_message(ai_payload, u_id)
                except Exception:
                    pass

                # 3. Linked Telegram Push (Resolves Web UID -> Linked Telegram Chat ID)
                tg_target = None
                if str(u_id).startswith("tg_"):
                    try:
                        tg_target = int(str(u_id).replace("tg_", ""))
                    except Exception:
                        pass
                else:
                    profile = db.query(UserProfile).filter(UserProfile.user_id == u_id).first()
                    if profile and profile.telegram_id:
                        try:
                            tg_target = int(profile.telegram_id)
                        except Exception:
                            pass

                if tg_target:
                    await send_direct_telegram_ping(tg_target, ping_text)


async def start_proactive_background_loop():
    print("🌙 [PROACTIVE DAEMON] Aura Autonomous Check-in Loop initialized.")
    while True:
        try:
            await check_and_fire_proactive_checkins()
        except Exception as e:
            print(f"⚠️ [PROACTIVE LOOP ERROR]: {e}")
        
        # Check every 30 minutes
        await asyncio.sleep(1800)