# FILE: backend/run_telegram.py

import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

from app.integrations.telegram_adapter import process_telegram_turn
from app.core.unified_state import UniversalMessage

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"

async def run_bot_polling():
    if not TOKEN:
        print("❌ [ERROR] TELEGRAM_BOT_TOKEN is missing in .env!")
        return

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Verify Bot Token & Get Bot Info
        try:
            me_res = await client.get(f"{API_URL}/getMe")
            me_data = me_res.json()
            if not me_data.get("ok"):
                print(f"❌ [AUTH FAILED] Telegram rejected token: {me_data}")
                return
            bot_username = me_data["result"]["username"]
            print(f"✅ [CONNECTED] Bot verified: @{bot_username}")
        except Exception as e:
            print(f"❌ [NETWORK ERROR] Cannot reach Telegram API: {e}")
            return

        # 2. Flush Webhook
        await client.get(f"{API_URL}/deleteWebhook?drop_pending_updates=True")
        print(f"📡 [AURA LISTENING] Send a message to @{bot_username} in Telegram now...")

        offset = 0
        while True:
            try:
                res = await client.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 15})
                if res.status_code == 200:
                    data = res.json()
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        message = update.get("message")
                        if not message:
                            continue

                        chat_id = message["chat"]["id"]
                        sender_id = f"tg_{message['from']['id']}"
                        user_name = message['from'].get('first_name', 'User')
                        user_text = message.get("text", "")

                        print(f"\n📩 [INCOMING] From {user_name} ({sender_id}): '{user_text}'")

                        universal_msg = UniversalMessage(
                            platform="telegram",
                            user_id=sender_id,
                            message_type="text",
                            text=user_text,
                            metadata={"first_name": user_name, "chat_id": chat_id}
                        )

                        print("🧠 [AURA] Thinking & Generating response...")
                        asyncio.create_task(process_telegram_turn(chat_id, universal_msg))
            except Exception as e:
                print(f"⚠️ [POLLING RECONNECT]: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_bot_polling())