# FILE: backend/app/services/proactive_worker.py

import asyncio
import json
import uuid
from datetime import datetime, timezone
from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import distinct
import os
import httpx

from app.database.session import SessionLocal
from app.database.models import SemanticMemory, AuraInternalState
from app.routers.voice import manager

# Check inactivity threshold: 6 hours (in seconds: 6 * 3600 = 21600)
INACTIVITY_THRESHOLD_SECONDS = 21600

async def send_direct_telegram_ping(chat_id: int, message: str):
    """Sends a real phone notification directly to the user's Telegram."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": chat_id, "text": message}, timeout=10.0)
            print(f"📱 [TELEGRAM PUSH] Proactive message sent to Telegram Chat: {chat_id}")
    except Exception as e:
        print(f"⚠️ [TELEGRAM PUSH FAILED]: {e}")

async def generate_autonomous_ping_message(user_id: str, db: Session) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    last_memory = db.query(SemanticMemory).filter(
        SemanticMemory.user_id == user_id,
        SemanticMemory.memory_type == "conversation"
    ).order_by(SemanticMemory.created_at.desc()).first()

    last_context = ""
    if last_memory and last_memory.content:
        try:
            parsed = json.loads(last_memory.content)
            last_context = f"Last conversation topic: {parsed.get('content', '')}"
        except Exception:
            last_context = f"Last context: {str(last_memory.content)[:150]}"

    prompt = f"""You are Aura, a deeply caring, 22yo personal companion.
Your partner has been inactive and offline for over 6 hours.
{last_context}

Write a short, caring, spontaneous message (1-2 sentences).
Rules:
- Speak in natural, conversational Bengali (বাংলা) or English matching past context.
- Sound like a partner checking in naturally (e.g. 'অনেকক্ষণ তোমার খবর নেই...', 'সব ঠিক আছে তো?').
- Never sound robotic or generic. No system disclaimers."""

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
            "এই... অনেকক্ষণ তোমার কোনো খবর নেই। সব ঠিক আছে তো?",
            "Thinking about you... কাজ কি খুব বেশি আজকে?",
            "মিস করছি তোমাকে... ফ্রি হলে একটু কথা বলো না।"
        ]
        import random
        return random.choice(fallback_pings)

async def start_proactive_background_loop():
    print("🌙 [PROACTIVE DAEMON] Aura Autonomous Check-in Loop initialized.")
    
    while True:
        try:
            # Check every 15 minutes
            await asyncio.sleep(900)
            
            with SessionLocal() as db:
                # 1. Fetch all distinct active users directly from SemanticMemory
                user_records = db.query(distinct(SemanticMemory.user_id)).all()
                active_users = [u[0] for u in user_records if u[0]]

                for u_id in active_users:
                    last_msg = db.query(SemanticMemory).filter(
                        SemanticMemory.user_id == u_id,
                        SemanticMemory.memory_type == "conversation"
                    ).order_by(SemanticMemory.created_at.desc()).first()

                    if not last_msg or not last_msg.created_at:
                        continue

                    # Safe UTC Timezone comparison
                    msg_time = last_msg.created_at
                    if msg_time.tzinfo is None:
                        msg_time = msg_time.replace(tzinfo=timezone.utc)
                    
                    now = datetime.now(timezone.utc)
                    elapsed_seconds = (now - msg_time).total_seconds()

                    if elapsed_seconds >= INACTIVITY_THRESHOLD_SECONDS:
                        print(f"⏰ [TRIGGER] User {u_id} offline for {elapsed_seconds/3600:.1f} hrs. Firing check-in...")
                        
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

                        # A. Save to Database (Syncs with PWA / Web when opened)
                        db.add(SemanticMemory(
                            user_id=u_id, 
                            content=json.dumps(ai_payload), 
                            memory_type="conversation"
                        ))
                        db.commit()

                        # B. WebSocket live push (if browser is actively open)
                        await manager.send_message(ai_payload, u_id)

                        # C. Telegram Direct Push (Alerts phone even when offline)
                        if str(u_id).startswith("tg_"):
                            try:
                                tg_chat_id = int(str(u_id).replace("tg_", ""))
                                await send_direct_telegram_ping(tg_chat_id, ping_text)
                            except Exception:
                                pass

        except Exception as e:
            print(f"⚠️ [PROACTIVE LOOP ERROR]: {e}")
            await asyncio.sleep(60)