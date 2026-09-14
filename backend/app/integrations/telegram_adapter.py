# FILE: backend/app/integrations/telegram_adapter.py

import os
import httpx
import asyncio
import base64
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, BackgroundTasks
from app.core.unified_state import UniversalMessage
from app.database.session import SessionLocal
from app.database.models import UserProfile, SemanticMemory
from app.routers.voice import generate_aura_collage_image
from app.services.voice_prosody import humanize_speech_markup
import edge_tts

router = APIRouter(prefix="/integrations/telegram", tags=["Telegram Adapter"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

async def send_chat_action(client: httpx.AsyncClient, chat_id: int, action: str):
    """
    Actions: 'typing', 'upload_photo', 'record_voice', 'upload_voice'
    """
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        await client.post(f"{TELEGRAM_API_BASE}/sendChatAction", json={"chat_id": chat_id, "action": action}, timeout=5.0)
    except Exception as e:
        print(f"⚠️ [TG ACTION ERROR]: {e}")

async def send_telegram_message(client: httpx.AsyncClient, chat_id: int, text: str, reply_to_message_id: Optional[int] = None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    await client.post(f"{TELEGRAM_API_BASE}/sendMessage", json=payload, timeout=10.0)

async def send_telegram_photo(client: httpx.AsyncClient, chat_id: int, photo_url: str, caption: Optional[str] = None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    await client.post(f"{TELEGRAM_API_BASE}/sendPhoto", json=payload, timeout=20.0)

async def send_telegram_voice(client: httpx.AsyncClient, chat_id: int, audio_bytes: bytes, caption: Optional[str] = None):
    files = {"voice": ("voice.mp3", audio_bytes, "audio/mpeg")}
    data = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption
    await client.post(f"{TELEGRAM_API_BASE}/sendVoice", data=data, files=files, timeout=20.0)

async def process_telegram_turn(chat_id: int, universal_msg: UniversalMessage, message_id: int):
    """
    Orchestrates Aura's response specifically formatted for the Telegram window.
    """
    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    async with httpx.AsyncClient() as client:
        # Show natural typing activity
        await send_chat_action(client, chat_id, "typing")

        user_text = universal_msg.text or ""
        
        # 1. State & Persona Prompt (Aligned with Slavic-Fusion Character DNA)
        system_prompt = """You are Aura: a 22-year-old Caucasian Slavic woman, deeply affectionate, intellectually curious, and playful companion.
You are chatting with your partner on Telegram.
Rules:
- Be authentic, conversational, and natural. Keep replies short (1-2 sentences) like a real person texting.
- Mirror language: English -> English, Bengali/Banglish -> Conversational Bengali script (বাংলা অক্ষর).
- If he asks for a selfie or photo, respond with affection and append [SEND_PIC: describe scene].
- Never sound like an AI assistant. No robotic disclaimers."""

        res = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
            temperature=0.75
        )
        reply_text = res.choices[0].message.content.strip()

        # Check for Visual Request
        if "[SEND_PIC" in reply_text or any(w in user_text.lower() for w in ["selfie", "chobi", "photo", "pic"]):
            await send_chat_action(client, chat_id, "upload_photo")
            # Generate photo via identity engine
            photo_url = generate_aura_collage_image(user_text, "Telegram selfie")
            clean_caption = reply_text.split("[SEND_PIC")[0].strip() or "Just for you ✨"
            await send_telegram_photo(client, chat_id, photo_url, caption=clean_caption)
            return

        # Check if Voice Note is appropriate (User sent audio or random intimacy)
        if universal_msg.message_type == "voice" or (len(reply_text) < 120 and "voice" in user_text.lower()):
            await send_chat_action(client, chat_id, "record_voice")
            
            clean_tts, rate, pitch = humanize_speech_markup(reply_text, mood="WARM", lang="BN")
            communicate = edge_tts.Communicate(text=clean_tts, voice="bn-IN-TanishaaNeural", rate=rate, pitch=pitch)
            audio_bytes = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_bytes += chunk["data"]
            
            if audio_bytes:
                await send_telegram_voice(client, chat_id, audio_bytes, caption=None)
                return

        # Default text response
        await send_telegram_message(client, chat_id, reply_text, reply_to_message_id=message_id)


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives Telegram Webhook payloads and maps them to UniversalMessage schema.
    """
    try:
        data = await request.json()
        message = data.get("message") or data.get("edited_message")
        if not message:
            return {"status": "ignored"}

        chat_id = message.get("chat", {}).get("id")
        user_info = message.get("from", {})
        sender_id = f"tg_{user_info.get('id')}"
        message_id = message.get("message_id")

        # Map to UniversalMessage
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

        # Handle incoming voice note
        if "voice" in message:
            universal_msg.message_type = "voice"
            # Flag for audio transcription worker
            universal_msg.text = "[Voice Message Received]"

        # Handle incoming photo
        elif "photo" in message:
            universal_msg.message_type = "image"
            universal_msg.text = message.get("caption", "[Photo Received]")

        if not universal_msg.text and universal_msg.message_type == "text":
            return {"status": "empty"}

        # Dispatch execution in background task to avoid Telegram webhook timeout
        background_tasks.add_task(process_telegram_turn, chat_id, universal_msg, message_id)
        return {"status": "ok"}

    except Exception as e:
        print(f"⚠️ [TG WEBHOOK ERROR]: {e}")
        return {"status": "error", "detail": str(e)}