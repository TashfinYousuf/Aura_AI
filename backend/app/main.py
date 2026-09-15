from dotenv import load_dotenv

from app.routers import analytics, chat

# Load environment variables
load_dotenv()

import os
import certifi
import asyncio

from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime, timezone

from app.routers import voice
from app.database.session import engine, Base
from app.database import models
from app.services.proactive_worker import start_proactive_background_loop
from app.integrations.telegram_adapter import router as telegram_router
from run_telegram import run_bot_polling

# Create database tables (অন্যান্য লোকাল মেমোরি টেবিলগুলোর জন্য)
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
except Exception as e:
    print(f"[WARNING] Could not run create_all: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ১. প্রোঅ্যাক্টিভ চেকার ব্যাকগ্রাউন্ডে চালু হবে
    proactive_task = asyncio.create_task(start_proactive_background_loop())
    
    # ২. টেলিগ্রাম লং-পোলিং ব্যাকগ্রাউন্ডে চালু হবে (কোনো আলাদা সার্ভার ছাড়াই ২৪/৭ চলবে)
    telegram_task = asyncio.create_task(run_bot_polling())
    
    print("🚀 [SYSTEM] Both Proactive Daemon & Telegram Polling running in background.")
    yield
    
    # শাটডাউনে টাস্ক ক্লিনআপ
    proactive_task.cancel()
    telegram_task.cancel()
    

app = FastAPI(title="Companion OS", version="1.0", lifespan=lifespan)

# CORS Middleware (ফ্রন্টএন্ডকে ব্যাকএন্ডের সাথে কথা বলার পারমিশন দেয়)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # প্রোডাকশনে ফ্রন্টএন্ডের ডোমেইন
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the chat routing logic
app.include_router(chat.router)
app.include_router(voice.router)
app.include_router(analytics.router)

# Ensure static folder is accessible from backend
static_path = os.path.join(os.getcwd(), "app", "static")
os.makedirs(static_path, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def root():
    return {"message": "Aura is running perfectly. Safe space activated."}


# ==========================================
# ☁️ MONGODB CLOUD DATABASE CONNECTION
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["aura_os_db"] # ডাটাবেসের নাম
    chats_collection = db["permanent_chats"] # টেবিল বা কালেকশনের নাম
    
    # কানেকশন ঠিক আছে কি না টেস্ট করা
    client.admin.command('ping')
    print("✅ Successfully connected to MongoDB Cloud!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")

# 2. Schema for receiving chat data
class SaveMessage(BaseModel):
    user_id: str
    role: str
    content: str
    image_url: str | None = None

# 3. API to SAVE message from any device (Now saves to Cloud)
@app.post("/api/chat/save")
def save_chat_message(msg: SaveMessage):
    chat_data = {
        "user_id": msg.user_id,
        "role": msg.role,
        "content": msg.content,
        "image_url": msg.image_url,
        "timestamp": datetime.now(timezone.utc)
    }
    chats_collection.insert_one(chat_data)
    return {"status": "saved to cloud"}

# 4. API to FETCH history from any device (Now fetches from Cloud)
@app.get("/api/chat/history/{user_id}")
def get_permanent_history(user_id: str):
    # MongoDB থেকে ইউজারের মেসেজগুলো সময় অনুযায়ী (timestamp, 1) সাজিয়ে আনা হচ্ছে
    chats = chats_collection.find({"user_id": user_id}).sort("timestamp", 1)
    
    history = []
    for chat in chats:
        history.append({
            "role": chat["role"],
            "content": chat["content"],
            "imageUrl": chat.get("image_url")
        })
        
    return history