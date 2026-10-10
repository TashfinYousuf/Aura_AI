# FILE: backend/app/main.py

import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.database.session import SessionLocal, engine, Base
from app.database.models import SemanticMemory
from app.routers import analytics, chat, voice
from app.services.proactive_worker import start_proactive_background_loop
from run_telegram import run_bot_polling

def run_auto_migrations():
    from sqlalchemy import text
    with engine.begin() as conn:
        migrations = [
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS telegram_id VARCHAR;",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS is_adult_mode BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS email VARCHAR;",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS name VARCHAR;",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS companion_name VARCHAR DEFAULT 'Aura';",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS current_mood VARCHAR DEFAULT 'Calm';",
            "ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS relationship_level INTEGER DEFAULT 1;"
        ]
        for sql in migrations:
            try:
                conn.execute(text(sql))
            except Exception:
                pass

try:
    Base.metadata.create_all(bind=engine)
    run_auto_migrations()
    print("✅ Database tables and schema migrations verified!")
except Exception as e:
    print(f"[WARNING] Table initialization notice: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    proactive_task = asyncio.create_task(start_proactive_background_loop())
    telegram_task = asyncio.create_task(run_bot_polling())
    print("🚀 [SYSTEM] Proactive Daemon & Telegram Polling running.")
    yield
    proactive_task.cancel()
    telegram_task.cancel()

app = FastAPI(title="Aura Companion OS", version="3.0", lifespan=lifespan)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    os.getenv("FRONTEND_PRODUCTION_URL", "https://aura-companion.vercel.app")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Canonical Route Mounts
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(analytics.router)

from pathlib import Path
static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    db_status = "ok"
    try:
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"notice: {e}"

    return {
        "status": "online",
        "app": "Aura Companion OS",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/presence/status")
def get_presence_status():
    from app.Aura.brain.presence_engine import presence_engine
    return presence_engine.get_current_presence()

# Persistence Endpoints
class SaveMessage(BaseModel):
    user_id: str
    role: str
    content: str
    image_url: Optional[str] = None

@app.post("/api/chat/save")
def save_chat_message(msg: SaveMessage):
    with SessionLocal() as db:
        payload = {
            "id": f"msg_{datetime.now(timezone.utc).timestamp()}",
            "role": msg.role,
            "content": msg.content,
            "imageUrl": msg.image_url,
            "timestamp": datetime.now(timezone.utc).strftime("%I:%M %p")
        }
        db.add(SemanticMemory(user_id=msg.user_id, content=json.dumps(payload), memory_type="conversation"))
        db.commit()
    return {"status": "saved"}

@app.get("/api/chat/history/{user_id}")
def get_permanent_history(user_id: str):
    with SessionLocal() as db:
        memories = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).order_by(SemanticMemory.created_at.asc()).all()

        history = []
        for m in memories:
            try:
                data = json.loads(str(m.content))
                history.append({
                    "id": data.get("id", str(m.id)),
                    "role": data.get("role", "user"),
                    "content": data.get("content", ""),
                    "imageUrl": data.get("imageUrl") or data.get("image_url"),
                    "audioBase64": data.get("audioBase64") or data.get("audio_base64"),
                    "isVoiceNote": data.get("isVoiceNote") if "isVoiceNote" in data else data.get("is_voice_note", False),
                    "videoUrl": data.get("videoUrl") or data.get("video_url"),
                    "presentationMode": data.get("presentationMode") or data.get("presentation_mode", "private"),
                    "timestamp": data.get("timestamp")
                })
            except Exception:
                continue
        return history

@app.delete("/api/chat/history/{user_id}")
def clear_chat_history(user_id: str):
    with SessionLocal() as db:
        db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation"
        ).delete()
        db.commit()
    return {"status": "cleared"}