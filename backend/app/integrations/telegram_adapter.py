# FILE: backend/app/integrations/telegram_adapter.py

import os
import httpx
import asyncio
import base64
import json

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, BackgroundTasks

from app.core.unified_state import UniversalMessage
from app.database.session import SessionLocal
from app.database.models import UserProfile, SemanticMemory
from app.services.visual_engine import generate_aura_identity_image
from app.services.voice_engine import render_aura_voice
from app.services.text_realization import realize_conversational_response
from app.core.prompts import build_system_prompt

router = APIRouter(prefix="/integrations/telegram", tags=["Telegram Adapter"])


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_chat_action(client: httpx.AsyncClient, chat_id: int, action: str):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        await client.post(f"{TELEGRAM_API_BASE}/sendChatAction", json={"chat_id": chat_id, "action": action}, timeout=5.0)
    except Exception:
        pass

async def send_telegram_message(client: httpx.AsyncClient, chat_id: int, text: str):
    await client.post(f"{TELEGRAM_API_BASE}/sendMessage", json={"chat_id": chat_id, "text": text}, timeout=10.0)

async def send_telegram_photo(client: httpx.AsyncClient, chat_id: int, photo_url: str, caption: Optional[str] = None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    await client.post(f"{TELEGRAM_API_BASE}/sendPhoto", json=payload, timeout=20.0)

async def send_telegram_voice(client: httpx.AsyncClient, chat_id: int, audio_bytes: bytes):
    files = {"voice": ("voice.mp3", audio_bytes, "audio/mpeg")}
    data = {"chat_id": str(chat_id)}
    await client.post(f"{TELEGRAM_API_BASE}/sendVoice", data=data, files=files, timeout=20.0)

async def process_telegram_turn(chat_id: int, universal_msg: UniversalMessage):
    from groq import Groq
    from app.services.state_engine import evaluate_interaction_state, create_response_director_plan
    from app.services.text_realization import realize_conversational_response
    
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # 1. Ensure user exists & save message
    with SessionLocal() as db:
        user_id = universal_msg.user_id
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            new_profile = UserProfile(user_id=user_id)
            db.add(new_profile)
            db.commit()

        u_payload = {
            "id": f"tg_msg_{datetime.utcnow().timestamp()}",
            "role": "user",
            "content": universal_msg.text,
            "timestamp": datetime.now().strftime("%I:%M %p")
        }
        db.add(SemanticMemory(user_id=user_id, content=json.dumps(u_payload), memory_type="conversation"))
        db.commit()

    async with httpx.AsyncClient() as client:
        await send_chat_action(client, chat_id, "typing")
        user_text = universal_msg.text or ""

        # --- SPECIAL COMMAND: ACCOUNT LINKING ---
        if user_text.startswith("/link"):
            parts = user_text.split()
            if len(parts) > 1:
                target_uid = parts[1].strip()
                with SessionLocal() as db:
                    # 1. Look for existing web profile
                    master_profile = db.query(UserProfile).filter(UserProfile.user_id == target_uid).first()
                    if not master_profile:
                        # Create if not existing yet
                        master_profile = UserProfile(user_id=target_uid)
                        db.add(master_profile)

                    master_profile.telegram_id = str(chat_id)
                    db.commit()
                    await send_telegram_message(
                        client, 
                        chat_id, 
                        f"✅ Account successfully linked!\nAura now recognizes you across both Web and Telegram as a single person. 💜"
                    )
                    print(f"🔗 [LINK SUCCESS] Telegram {chat_id} linked to Web UID: {target_uid}")
            else:
                await send_telegram_message(client, chat_id, "⚠️ Please provide your Web UID. Usage: /link YOUR_FIREBASE_UID")
            return
        
        # 2. Evaluate Unified State (Detects if user is stressed/tired)
        current_aura_state = await evaluate_interaction_state(user_text)
        director_plan = create_response_director_plan(current_aura_state, user_text)

        state_context = f"State: Mode={current_aura_state.conversation_mode}, User Emotion={current_aura_state.user_emotion}, Goal={director_plan.text_goal}"
        
        system_prompt = build_system_prompt(state_context=state_context)

        res = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.6
        )

        reply_text = res.choices[0].message.content.strip()
        
        # 3. Apply Text Realization Filter (Prunes AI cliches & awkward phrasings)
        reply_text = await realize_conversational_response(reply_text, user_text)

        # Handle Photo Request
        if "[SEND_PIC" in reply_text or any(w in user_text.lower() for w in ["selfie", "chobi", "photo", "pic"]):
            await send_chat_action(client, chat_id, "upload_photo")
            photo_url = await generate_aura_identity_image(user_text)
            clean_caption = reply_text.split("[SEND_PIC")[0].strip() or "Just for you ✨"
            await send_telegram_photo(client, chat_id, photo_url, caption=clean_caption)
            ai_content = f"[Photo Sent] {clean_caption}"
        
        # Handle Voice Note Request
        elif universal_msg.message_type == "voice" or (len(reply_text) < 140 and "voice" in user_text.lower()):
            await send_chat_action(client, chat_id, "record_voice")
            audio_b64, _ = await render_aura_voice(reply_text, mood="WARM", energy=0.65)
            if audio_b64:
                raw_audio = base64.b64decode(audio_b64)
                await send_telegram_voice(client, chat_id, raw_audio)
            await send_telegram_message(client, chat_id, reply_text)
            ai_content = reply_text
        
        # Handle Photo / Voice / Text delivery...
        await send_telegram_message(client, chat_id, reply_text)

        with SessionLocal() as db:
            ai_payload = {
                "id": f"tg_ai_{datetime.utcnow().timestamp()}",
                "role": "ai",
                "content": reply_text,
                "timestamp": datetime.now().strftime("%I:%M %p")
            }
            db.add(SemanticMemory(user_id=user_id, content=json.dumps(ai_payload), memory_type="conversation"))
            db.commit()


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
        message = data.get("message") or data.get("edited_message")
        if not message:
            return {"status": "ignored"}

        chat_id = message.get("chat", {}).get("id")
        user_info = message.get("from", {})
        sender_id = f"tg_{user_info.get('id')}"
        message_id = message.get("message_id")

        universal_msg = UniversalMessage(
            platform="telegram",
            user_id=sender_id,
            message_type="text",
            text=message.get("text"),
            metadata={
                "first_name": user_info.get("first_name"),
                "username": user_info.get("username"),
                "chat_id": chat_id
            }
        )

        if "voice" in message:
            universal_msg.message_type = "voice"
            universal_msg.text = "[Voice Message]"
        elif "photo" in message:
            universal_msg.message_type = "image"
            universal_msg.text = message.get("caption", "[Photo]")

        if not universal_msg.text:
            return {"status": "empty"}

        background_tasks.add_task(process_telegram_turn, chat_id, universal_msg)
        return {"status": "ok"}
    except Exception as e:
        print(f"⚠️ [TG WEBHOOK ERROR]: {e}")
        return {"status": "error", "detail": str(e)}