# FILE: backend/app/services/avatar_service.py

import os
import httpx
import base64
import uuid
from typing import Optional

STATIC_DIR = os.path.join(os.getcwd(), "app", "static", "avatars")
os.makedirs(STATIC_DIR, exist_ok=True)

DEFAULT_PORTRAIT_PATH = os.path.join(os.getcwd(), "app", "static", "references", "aura_master_identity.png")

async def upload_asset_to_fal(client: httpx.AsyncClient, fal_key: str, data_bytes: bytes, content_type: str) -> Optional[str]:
    """
    Uploads raw audio/image bytes to Fal.ai storage to avoid oversized Base64 payloads and SSL EOF drops.
    """
    try:
        headers = {
            "Authorization": f"Key {fal_key}",
            "User-Agent": "AuraOS/1.0",
        }
        
        # Request upload URL from Fal Storage
        init_res = await client.post(
            "https://rest.alpha.fal.ai/storage/upload/initiate",
            headers=headers,
            json={"file_name": f"asset_{uuid.uuid4().hex[:8]}", "content_type": content_type},
            timeout=10.0
        )
        if init_res.status_code == 200:
            upload_data = init_res.json()
            upload_url = upload_data.get("upload_url")
            file_url = upload_data.get("file_url")
            
            # Put actual binary data
            put_res = await client.put(upload_url, content=data_bytes, headers={"Content-Type": content_type}, timeout=15.0)
            if put_res.status_code in [200, 201]:
                return file_url
    except Exception as e:
        print(f"⚠️ [FAL STORAGE FALLBACK]: {e}")
    return None


async def generate_talking_avatar_video(audio_base64: str, image_url: Optional[str] = None) -> Optional[str]:
    """
    Combines Aura's facial portrait with TTS audio to generate a synchronized talking avatar video.
    Uses async httpx with connection pooling and Fal storage uploading.
    """
    if not audio_base64:
        return None

    fal_key = os.getenv("FAL_API_KEY")
    
    # 1. Resolve Face Image (Image URL or local portrait)
    resolved_image_bytes = None
    target_image_url = image_url

    if not target_image_url or target_image_url.startswith("/static/"):
        if os.path.exists(DEFAULT_PORTRAIT_PATH):
            with open(DEFAULT_PORTRAIT_PATH, "rb") as f:
                resolved_image_bytes = f.read()
    
    audio_bytes = base64.b64decode(audio_base64)

    # 2. Process via Cloud Fal.ai (LivePortrait)
    if fal_key:
        async with httpx.AsyncClient(headers={"User-Agent": "AuraOS/1.0"}) as client:
            try:
                print("🎬 [AVATAR ENGINE] Uploading media to Fal storage...")
                
                # Upload assets to Fal storage to get clean lightweight HTTPS URLs
                audio_fal_url = await upload_asset_to_fal(client, fal_key, audio_bytes, "audio/mpeg")
                
                if resolved_image_bytes and not (target_image_url and target_image_url.startswith("http")):
                    image_fal_url = await upload_asset_to_fal(client, fal_key, resolved_image_bytes, "image/png")
                else:
                    image_fal_url = target_image_url

                # If storage upload succeeded, run LivePortrait using clean URLs
                if audio_fal_url and image_fal_url:
                    print("🎬 [AVATAR ENGINE] Triggering Cloud LivePortrait with clean URLs...")
                    headers = {
                        "Authorization": f"Key {fal_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "face_image_url": image_fal_url,
                        "audio_url": audio_fal_url,
                        "driving_mode": "audio",
                        "expression_friendly": True
                    }

                    res = await client.post(
                        "https://fal.run/fal-ai/live-portrait",
                        headers=headers,
                        json=payload,
                        timeout=40.0
                    )
                    
                    if res.status_code == 200:
                        data = res.json()
                        video_url = data.get("video", {}).get("url")
                        if video_url:
                            print(f"✅ [AVATAR SUCCESS]: {video_url}")
                            return video_url
                    else:
                        print(f"⚠️ [FAL API REJECTED]: Status {res.status_code} - {res.text}")
            except Exception as e:
                print(f"⚠️ [AVATAR FAL FAILED]: {e}")

    # 3. Fallback: High-Quality Ambient Aesthetics (Zero server crash)
    import random
    subtle_motion_fallbacks = [
        "https://cdn.pixabay.com/video/2021/08/18/85433-590289053_tiny.mp4",
        "https://cdn.pixabay.com/video/2020/05/25/40143-424844342_tiny.mp4"
    ]
    return random.choice(subtle_motion_fallbacks)