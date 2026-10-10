# FILE: backend/app/routers/voice.py

import os
import json
import uuid
import tempfile
import base64
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from groq import Groq

from pathlib import Path
from app.database.session import SessionLocal
from app.database.models import SemanticMemory, EmotionLog, UserProfile
from app.Aura.brain.cognitive_pipeline import cognitive_pipeline
from app.services.visual_engine import generate_aura_identity_image
from app.services.voice_ssml import render_neural_voice
from app.services.episodic_service import extract_and_store_episode
from app.Aura.memory.open_loops import scan_and_extract_open_loops

router = APIRouter(prefix="/api/voice", tags=["Voice Engine"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"✅ User {user_id} connected to WebSocket.")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f"❌ User {user_id} disconnected.")

    async def send_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                print(f"⚠️ [MANAGER SEND ERROR]: {e}")

from typing import Optional
from app.core.security import verify_ws_token

manager = ConnectionManager()

@router.websocket("/ws/live-chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: Optional[str] = None):
    if token:
        verified_uid = verify_ws_token(token)
        if verified_uid and verified_uid != user_id:
            await websocket.close(code=1008)
            return

    await manager.connect(websocket, user_id)
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    try:
        while True:
            raw_data = await websocket.receive_text()
            if not raw_data or not raw_data.strip():
                continue

            payload = json.loads(raw_data)
            msg_type = payload.get("type")

            # ---------------------------------------------------------
            # 0. Messenger Actions: Reaction, Unsend, Edit
            # ---------------------------------------------------------
            if msg_type == "reaction":
                msg_id = payload.get("message_id")
                emoji = payload.get("emoji")
                with SessionLocal() as db:
                    mems = db.query(SemanticMemory).filter(
                        SemanticMemory.user_id == user_id,
                        SemanticMemory.memory_type == "conversation"
                    ).order_by(SemanticMemory.created_at.desc()).limit(100).all()
                    for m in mems:
                        try:
                            d = json.loads(str(m.content))
                            if d.get("id") == msg_id or str(m.id) == msg_id:
                                if emoji:
                                    d["reaction"] = emoji
                                else:
                                    d.pop("reaction", None)
                                m.content = json.dumps(d)
                                db.commit()
                                break
                        except Exception:
                            pass

                # Emotional Feedback Loop based on reaction emoji
                if emoji == "😢":
                    with SessionLocal() as db:
                        db.add(EmotionLog(
                            user_id=user_id,
                            primary_emotion="Vulnerable",
                            secondary_emotion="NeedComfort",
                            intensity_score=7,
                            detected_need="Validation",
                            trigger_event="User reacted with 😢 (seeking comfort/vulnerability)"
                        ))
                        p = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                        if p:
                            p.current_mood = "comforting_soft"
                        db.commit()
                elif emoji == "❤️":
                    with SessionLocal() as db:
                        db.add(EmotionLog(
                            user_id=user_id,
                            primary_emotion="Loved",
                            secondary_emotion="Appreciation",
                            intensity_score=8,
                            detected_need="Listening",
                            trigger_event="User reacted with ❤️ (expressing affection)"
                        ))
                        p = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                        if p:
                            p.trust_score = min(100.0, (p.trust_score or 50.0) + 1.0)
                        db.commit()
                elif emoji in ["🔥", "😆"]:
                    with SessionLocal() as db:
                        db.add(EmotionLog(
                            user_id=user_id,
                            primary_emotion="Playful",
                            secondary_emotion="Amused",
                            intensity_score=8,
                            detected_need="Humor",
                            trigger_event=f"User reacted with {emoji} (playful banter)"
                        ))
                        p = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                        if p:
                            p.current_mood = "playful_tease"
                        db.commit()

                await websocket.send_text(json.dumps({
                    "type": "reaction_updated",
                    "message_id": msg_id,
                    "emoji": emoji
                }))
                continue

            if msg_type == "unsend":
                msg_id = payload.get("message_id")
                with SessionLocal() as db:
                    mems = db.query(SemanticMemory).filter(
                        SemanticMemory.user_id == user_id,
                        SemanticMemory.memory_type == "conversation"
                    ).all()
                    for m in mems:
                        try:
                            d = json.loads(str(m.content))
                            if d.get("id") == msg_id or str(m.id) == msg_id:
                                db.delete(m)
                                db.commit()
                                break
                        except Exception:
                            pass

                await websocket.send_text(json.dumps({
                    "type": "message_unsent",
                    "message_id": msg_id
                }))
                continue

            if msg_type == "edit":
                msg_id = payload.get("message_id")
                new_content = payload.get("new_content", "")
                with SessionLocal() as db:
                    mems = db.query(SemanticMemory).filter(
                        SemanticMemory.user_id == user_id,
                        SemanticMemory.memory_type == "conversation"
                    ).all()
                    for m in mems:
                        try:
                            d = json.loads(str(m.content))
                            if d.get("id") == msg_id or str(m.id) == msg_id:
                                d["content"] = new_content
                                d["isEdited"] = True
                                m.content = json.dumps(d)
                                db.commit()
                                break
                        except Exception:
                            pass

                await websocket.send_text(json.dumps({
                    "type": "message_edited",
                    "message_id": msg_id,
                    "new_content": new_content
                }))
                continue

            user_text = payload.get("content", "").strip() if payload.get("type") == "text" else ""

            # 1. Handle Voice Note (Whisper Large v3 Turbo)
            user_audio_b64 = None
            if payload.get("type") == "audio":
                user_audio_b64 = payload.get("content")
                audio_bytes = base64.b64decode(user_audio_b64)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
                    temp_audio.write(audio_bytes)
                    temp_path = temp_audio.name

                def _transcribe():
                    with open(temp_path, "rb") as f:
                        return groq_client.audio.transcriptions.create(
                            model="whisper-large-v3-turbo", file=f
                        ).text.strip()

                user_text = await asyncio.to_thread(_transcribe)
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            # 2. Handle User Uploaded Image (Direct Database Storage, Zero Disk Clutter)
            user_image_url = None
            if payload.get("image_base64"):
                try:
                    img_data = str(payload.get("image_base64")).strip()
                    if "," in img_data:
                        img_data = img_data.split(",")[1]
                    raw_bytes = base64.b64decode(img_data)
                    # Optimize in-memory if large to keep DB footprint small
                    if len(raw_bytes) > 300_000:
                        from io import BytesIO
                        from PIL import Image
                        with Image.open(BytesIO(raw_bytes)) as im:
                            rgb_im = im.convert("RGB")
                            rgb_im.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                            out_io = BytesIO()
                            rgb_im.save(out_io, format="JPEG", quality=75, optimize=True)
                            compressed_b64 = base64.b64encode(out_io.getvalue()).decode("utf-8")
                            user_image_url = f"data:image/jpeg;base64,{compressed_b64}"
                    else:
                        user_image_url = f"data:image/jpeg;base64,{img_data}"
                except Exception as img_err:
                    print(f"⚠️ [USER IMAGE DB ENCODING ERROR]: {img_err}")

            if not user_text:
                if user_image_url:
                    user_text = "Here's a photo for you!"
                else:
                    continue

            current_time = datetime.now().strftime("%I:%M %p")
            user_msg_id = str(uuid.uuid4())
            mode = payload.get("presentation_mode", "private")
            reply_to = payload.get("reply_to")
            reply_preview = payload.get("reply_preview")

            # 🟢 ইউজারের মেসেজ ও মিডিয়া সাথে সাথে ডেটাবেসে সেভ করুন
            user_payload = {
                "id": user_msg_id,
                "role": "user",
                "content": user_text,
                "timestamp": current_time,
                "imageUrl": user_image_url,
                "image_url": user_image_url,
                "audioBase64": user_audio_b64,
                "audio_base64": user_audio_b64,
                "isVoiceNote": bool(payload.get("type") == "audio"),
                "is_voice_note": bool(payload.get("type") == "audio"),
                "replyTo": reply_to,
                "replyPreview": reply_preview,
                "presentationMode": mode,
                "presentation_mode": mode
            }
            with SessionLocal() as db:
                try:
                    db.add(SemanticMemory(
                        user_id=user_id, 
                        content=json.dumps(user_payload), 
                        memory_type="conversation"
                    ))
                    db.commit()
                except Exception as db_err:
                    print(f"⚠️ [USER MSG DB SAVE ERROR]: {db_err}")
                    db.rollback()

            # 3. Fetch Recent Conversation History
            history = []
            with SessionLocal() as db:
                recent_history = db.query(SemanticMemory).filter(
                    SemanticMemory.user_id == user_id,
                    SemanticMemory.memory_type == "conversation"
                ).order_by(SemanticMemory.created_at.desc()).limit(6).all()
                for m in reversed(recent_history):
                    try:
                        d = json.loads(str(m.content))
                        history.append({"role": d.get("role", "user"), "content": d.get("content", "")})
                    except Exception:
                        pass

            # 4. Human Thinking & Reading Delay (No 0ms cold robot replies)
            from app.Aura.brain.presence_engine import presence_engine
            curr_presence = presence_engine.get_current_presence()
            natural_delay = curr_presence.get("natural_reply_delay", 1.0)
            await asyncio.sleep(natural_delay)

            # Notify Frontend Streaming Starts
            await websocket.send_text(json.dumps({"type": "message_start"}))

            # 5. Run Single Cognitive Pipeline Turn
            turn = await cognitive_pipeline.process_turn(user_id, user_text, history, presentation_mode=mode)

            # 6. Stream Text Word-by-Word (Organic human keystroke pacing)
            words = turn.reply_text.split(" ")
            for w in words:
                await websocket.send_text(json.dumps({"type": "token", "content": w + " "}))
                await asyncio.sleep(0.045)  # Natural human typing cadence (45ms per word)

            # 7. Visual Identity Vault Generation
            image_url = None
            if turn.is_media_requested:
                await websocket.send_text(json.dumps({
                    "type": "action_start",
                    "action": "generate_image",
                    "scene": turn.scene_category
                }))
                image_url = await generate_aura_identity_image(scene_category=turn.scene_category, user_text=user_text)
                await websocket.send_text(json.dumps({
                    "type": "action_complete",
                    "action": "generate_image",
                    "image_url": image_url
                }))

            # 8. Expressive Voice Prosody (Edge-TTS)
            audio_b64, _ = await render_neural_voice(turn.audio_text, mood=turn.state.conversation_mode)

            # 9. Final Payload Delivery
            msg_id = str(uuid.uuid4())
            ai_payload = {
                "id": msg_id,
                "type": "reply",
                "role": "ai",
                "content": turn.reply_text,
                "audioBase64": audio_b64,
                "audio_base64": audio_b64,
                "isVoiceNote": bool(payload.get("type") == "audio"),
                "is_voice_note": bool(payload.get("type") == "audio"),
                "imageUrl": image_url,
                "image_url": image_url,
                "timestamp": current_time,
                "presentationMode": turn.presentation_mode,
                "presentation_mode": turn.presentation_mode
            }
            await websocket.send_text(json.dumps(ai_payload))
            await websocket.send_text(json.dumps({"type": "message_complete", "id": msg_id}))

            # 10. Persist AI Response to DB
            with SessionLocal() as db:
                db.add(SemanticMemory(user_id=user_id, content=json.dumps(ai_payload), memory_type="conversation"))
                db.commit()

            # 11. Record Emotion Log for Live Analytics & Mood Graph
            intensity = max(1, min(10, int(round((turn.state.energy * 5) + (turn.state.affection * 5)))))
            need_map = {
                "advice": "Advice",
                "emotional_support": "Validation",
                "planning": "Motivation",
                "casual_chat": "Listening"
            }
            detected_need = need_map.get(turn.intent, "Listening")
            if turn.state.conversation_mode == "comfort":
                detected_need = "Validation"
            elif turn.state.conversation_mode == "playful_tease" or turn.state.humor > 0.6:
                detected_need = "Humor"
            elif turn.state.user_emotion == "tired":
                detected_need = "Space"

            try:
                with SessionLocal() as db:
                    emo_log = EmotionLog(
                        user_id=user_id,
                        primary_emotion=turn.state.user_emotion.capitalize() if turn.state.user_emotion else "Neutral",
                        secondary_emotion=turn.state.emotion,
                        intensity_score=intensity,
                        detected_need=detected_need,
                        trigger_event=user_text[:100]
                    )
                    db.add(emo_log)

                    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
                    if profile:
                        profile.current_mood = turn.state.emotion
                    db.commit()
            except Exception as emo_err:
                print(f"⚠️ [EMOTION LOG DB SAVE ERROR]: {emo_err}")

            # 12. Asynchronously extract episodic milestones and open loops
            def _async_memory_workers():
                try:
                    with SessionLocal() as db:
                        extract_and_store_episode(
                            db=db,
                            client=groq_client,
                            user_id=user_id,
                            message=user_text,
                            ai_reply=turn.reply_text,
                            intensity=intensity
                        )
                except Exception as ep_err:
                    print(f"⚠️ [EPISODE ASYNC ERROR]: {ep_err}")
                try:
                    scan_and_extract_open_loops(user_text, user_id)
                except Exception as loop_err:
                    print(f"⚠️ [OPEN LOOP ASYNC ERROR]: {loop_err}")

            asyncio.create_task(asyncio.to_thread(_async_memory_workers))

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f"⚠️ [WS ERROR]: {e}")
        manager.disconnect(websocket, user_id)