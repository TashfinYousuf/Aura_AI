# FILE: backend/app/integrations/telegram_adapter.py

import os
import httpx
import asyncio
import base64
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from fastapi import APIRouter, Request, BackgroundTasks

from app.core.unified_state import UniversalMessage
from app.database.session import SessionLocal
from app.database.models import UserProfile, SemanticMemory
from app.Aura.brain.cognitive_pipeline import cognitive_pipeline
from app.services.visual_engine import generate_aura_identity_image, validate_deliverable_asset
from app.services.voice_ssml import render_neural_voice
from app.Aura.memory.open_loops import scan_and_extract_open_loops

router = APIRouter(prefix="/integrations/telegram", tags=["Telegram Adapter"])

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ==============================================================================
# TELEGRAM DISPATCH & RENDERER PRIMITIVES (NO BRAIN LOGIC HERE)
# ==============================================================================

async def send_chat_action(client: httpx.AsyncClient, chat_id: int, action: str):
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        await client.post(
            f"{TELEGRAM_API_BASE}/sendChatAction",
            json={"chat_id": chat_id, "action": action},
            timeout=5.0
        )
    except Exception:
        pass

async def send_telegram_message(client: httpx.AsyncClient, chat_id: int, text: str):
    if not TELEGRAM_BOT_TOKEN or not text:
        return
    try:
        await client.post(
            f"{TELEGRAM_API_BASE}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10.0
        )
    except Exception as e:
        print(f"⚠️ [TG SEND MSG ERROR]: {e}")

async def send_telegram_photo(client: httpx.AsyncClient, chat_id: int, photo_data: str, caption: Optional[str] = None):
    """
    Delivers validated media deliverables to Telegram users.
    Enforces strict asset boundary guard before transmission.
    """
    if not photo_data:
        return
    
    # Enforce asset boundary invariant (MUST raise if non-deliverable)
    validate_deliverable_asset(photo_data)

    if not TELEGRAM_BOT_TOKEN:
        return

    try:

        if photo_data.startswith("/static/"):
            local_rel = photo_data.replace("/static/", "")
            local_path = Path(__file__).resolve().parent.parent / "static" / local_rel
            if local_path.exists():
                with open(local_path, "rb") as f:
                    raw_bytes = f.read()
                files = {"photo": ("selfie.jpg", raw_bytes, "image/jpeg")}
                data = {"chat_id": str(chat_id)}
                if caption:
                    data["caption"] = caption
                await client.post(f"{TELEGRAM_API_BASE}/sendPhoto", data=data, files=files, timeout=25.0)
                return

        if photo_data.startswith("data:image/"):
            base64_data = photo_data.split(",")[1]
            raw_bytes = base64.b64decode(base64_data)
            files = {"photo": ("selfie.jpg", raw_bytes, "image/jpeg")}
            data = {"chat_id": str(chat_id)}
            if caption:
                data["caption"] = caption
            await client.post(f"{TELEGRAM_API_BASE}/sendPhoto", data=data, files=files, timeout=25.0)
        else:
            # Regular HTTPS URL (e.g. Unsplash or S3/Supabase storage)
            payload = {"chat_id": chat_id, "photo": photo_data}
            if caption:
                payload["caption"] = caption
            await client.post(f"{TELEGRAM_API_BASE}/sendPhoto", json=payload, timeout=20.0)
    except Exception as e:
        print(f"⚠️ [TG SEND PHOTO ERROR]: {e}")

async def send_telegram_voice(client: httpx.AsyncClient, chat_id: int, audio_bytes: bytes):
    if not TELEGRAM_BOT_TOKEN or not audio_bytes:
        return
    try:
        files = {"voice": ("voice.mp3", audio_bytes, "audio/mpeg")}
        data = {"chat_id": str(chat_id)}
        await client.post(f"{TELEGRAM_API_BASE}/sendVoice", data=data, files=files, timeout=20.0)
    except Exception as e:
        print(f"⚠️ [TG SEND VOICE ERROR]: {e}")

# ==============================================================================
# CANONICAL TELEGRAM CONVERSATION TURN (ONE BRAIN INTEGRATION)
# ==============================================================================

async def process_telegram_turn(chat_id: int, universal_msg: UniversalMessage):
    """
    Telegram Turn Processor:
    Acts purely as Transport Gateway and Channel Renderer.
    Delegates all cognitive processing, state analysis, memory synthesis,
    and action planning to the UnifiedCognitivePipeline.
    """
    user_id = universal_msg.user_id
    user_text = (universal_msg.text or "").strip()

    async with httpx.AsyncClient() as client:
        # --- Command: /start ---
        if user_text.startswith("/start"):
            welcome_msg = (
                "💜 হ্যালো! আমি Aura — তোমার সার্বক্ষণিক সঙ্গী।\n\n"
                "এখানে তুমি আমার সাথে সাধারণ আড্ডা, পড়ালেখা বা ক্যারিয়ার নিয়ে কথা, কিংবা একান্ত মনের গল্প করতে পারো।\n\n"
                "📌 দরকারী কমান্ডসমূহ:\n"
                "📸 /selfie — আমার একটা ছবি বা সেলফি দেখতে চাইলে\n"
                "🔄 /mode — মোড পরিবর্তন (Normal / Intimate)\n"
                "🔗 /link <UID> — তোমার ওয়েব অ্যাকাউন্টের সাথে সিঙ্ক করতে\n"
                "✨ /app — ওয়েব ড্যাশবোর্ড ওপেন করতে\n\n"
                "তুমি যেকোনো ভাষায় (বাংলা, বাংলিশ, ইংরেজি) মেসেজ বা ভয়েস পাঠাতে পারো! 😊"
            )
            await send_telegram_message(client, chat_id, welcome_msg)
            return

        # --- Command: /mode ---
        if user_text.startswith("/mode"):
            with SessionLocal() as db:
                p = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                if not p:
                    p = UserProfile(user_id=user_id, is_adult_mode=True)
                    db.add(p)

                args = user_text.split()
                if len(args) > 1:
                    target = args[1].lower()
                    if target in ["intimate", "adult", "hot"]:
                        p.is_adult_mode = True
                    elif target in ["normal", "private", "casual"]:
                        p.is_adult_mode = False
                else:
                    p.is_adult_mode = not p.is_adult_mode
                db.commit()
                status_text = "🔥 Intimate Mode সক্রিয়! আমাদের কথোপকথন এখন অনেক বেশি ঘনিষ্ঠ ও রোমান্টিক।" if p.is_adult_mode else "🌿 Normal Mode সক্রিয়! আমরা সাধারণ ফ্রেন্ডলি আড্ডার মোডে আছি।"
                await send_telegram_message(client, chat_id, status_text)
            return

        # --- Command: /app ---
        if user_text.startswith("/app"):
            frontend_url = os.getenv("FRONTEND_PRODUCTION_URL", "").strip()
            if not frontend_url or "aura-companion.vercel.app" in frontend_url:
                app_text = (
                    "✨ Aura Web Dashboard:\n\n"
                    "🖥️ তোমার ওয়েব অ্যাপ লোকাল কম্পিউটারে চলছে:\n"
                    "http://localhost:3000\n\n"
                    "💡 টেলিগ্রাম থেকে সরাসরি ব্রাউজ করতে চাইলে তোমার Vercel বা Ngrok লিংকটি .env ফাইলে FRONTEND_PRODUCTION_URL হিসেবে বসিয়ে দাও।"
                )
            else:
                app_text = f"✨ Aura Web Dashboard:\n{frontend_url}\n\nলাইভ ভয়েস কল, এইচডি ভিজ্যুয়াল ও মেমরি অ্যানালিটিক্স অ্যাক্সেস করতে লিংকটি ভিজিট করো।"
            await send_telegram_message(client, chat_id, app_text)
            return

        # --- 1. Account Linking Command (/link) ---
        if user_text.startswith("/link"):
            parts = user_text.split()
            if len(parts) > 1:
                target_uid = parts[1].strip()
                with SessionLocal() as db:
                    master_profile = db.query(UserProfile).filter(UserProfile.user_id == target_uid).first()
                    if not master_profile:
                        master_profile = UserProfile(user_id=target_uid)
                        db.add(master_profile)

                    master_profile.telegram_id = str(chat_id)
                    db.commit()
                    await send_telegram_message(
                        client, 
                        chat_id, 
                        "✅ Account successfully linked!\nAura now recognizes you across both Web and Telegram as a single person. 💜"
                    )
                    print(f"🔗 [LINK SUCCESS] Telegram {chat_id} linked to Web UID: {target_uid}")
            else:
                await send_telegram_message(client, chat_id, "⚠️ Usage: /link YOUR_FIREBASE_UID")
            return

        # --- 2. Persist Incoming User Message ---
        with SessionLocal() as db:
            profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.add(profile)
                db.commit()

            user_is_adult = bool(profile.is_adult_mode)

            u_payload = {
                "id": f"tg_msg_{datetime.utcnow().timestamp()}",
                "role": "user",
                "content": user_text,
                "timestamp": datetime.now().strftime("%I:%M %p")
            }
            db.add(SemanticMemory(user_id=user_id, content=json.dumps(u_payload), memory_type="conversation"))
            db.commit()

        # Scan for open loops asynchronously
        scan_and_extract_open_loops(user_text, user_id)

        # --- 3. Compile Recent Chat History ---
        history_turns: List[Dict[str, str]] = []
        with SessionLocal() as db:
            recent_mems = db.query(SemanticMemory).filter(
                SemanticMemory.user_id == user_id,
                SemanticMemory.memory_type == "conversation"
            ).order_by(SemanticMemory.created_at.desc()).limit(6).all()
            for m in reversed(recent_mems):
                try:
                    data = json.loads(m.content)
                    history_turns.append({"role": data.get("role", "user"), "content": data.get("content", "")})
                except Exception:
                    pass

        # --- 4. Single Canonical Cognitive Brain Turn ---
        await send_chat_action(client, chat_id, "typing")

        tg_presentation_mode = "adult" if user_is_adult else "private"
        turn = await cognitive_pipeline.process_turn(
            user_id=user_id,
            user_text=user_text,
            conversation_history=history_turns,
            presentation_mode=tg_presentation_mode
        )

        final_reply = turn.reply_text
        ai_content = final_reply

        # --- 5. Multimodal Dispatch (Image, Voice, or Text) ---
        if turn.is_media_requested or any(a.type == "generate_image" for a in turn.actions):
            await send_chat_action(client, chat_id, "upload_photo")
            photo_url = await generate_aura_identity_image(
                scene_category=turn.scene_category,
                user_text=user_text
            )
            # Enforce asset boundary before dispatch
            validate_deliverable_asset(photo_url)
            await send_telegram_photo(client, chat_id, photo_url, caption=final_reply)
            ai_content = f"[Photo Sent: {photo_url}] {final_reply}"

        elif universal_msg.message_type == "voice" or any(a.type == "voice_note" for a in turn.actions):
            await send_chat_action(client, chat_id, "record_voice")
            audio_b64, clean_spoken_text = await render_neural_voice(turn.audio_text, mood=turn.state.conversation_mode)
            if audio_b64:
                raw_audio = base64.b64decode(audio_b64)
                await send_telegram_voice(client, chat_id, raw_audio)
            await send_telegram_message(client, chat_id, clean_spoken_text or final_reply)
            ai_content = clean_spoken_text or final_reply

        else:
            await send_telegram_message(client, chat_id, final_reply)

        # --- 6. Persist Assistant Response ---
        with SessionLocal() as db:
            ai_payload = {
                "id": f"tg_ai_{datetime.utcnow().timestamp()}",
                "role": "ai",
                "content": ai_content,
                "timestamp": datetime.now().strftime("%I:%M %p")
            }
            db.add(SemanticMemory(user_id=user_id, content=json.dumps(ai_payload), memory_type="conversation"))
            db.commit()

            # --- 7. Record Emotion Log for Analytics ---
            try:
                from app.database.models import EmotionLog
                intensity = max(1, min(10, int(round((turn.state.energy * 5) + (turn.state.affection * 5)))))
                need_map = {
                    "advice": "Advice",
                    "emotional_support": "Validation",
                    "planning": "Motivation",
                    "casual_chat": "Listening"
                }
                det_need = need_map.get(turn.intent, "Listening")
                if turn.state.conversation_mode == "comfort":
                    det_need = "Validation"
                elif turn.state.conversation_mode == "playful_tease" or turn.state.humor > 0.6:
                    det_need = "Humor"

                emo_entry = EmotionLog(
                    user_id=user_id,
                    primary_emotion=turn.state.user_emotion.capitalize() if turn.state.user_emotion else "Neutral",
                    secondary_emotion=turn.state.emotion,
                    intensity_score=intensity,
                    detected_need=det_need,
                    trigger_event=user_text[:100]
                )
                db.add(emo_entry)
                db.commit()
            except Exception as tg_emo_err:
                print(f"⚠️ [TG EMOTION LOG ERROR]: {tg_emo_err}")

# ==============================================================================
# TELEGRAM WEBHOOK ENDPOINT
# ==============================================================================

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