# FILE: backend/app/Aura/vision/sd_remote_provider.py
"""
Remote / Cloud Google Colab Stable Diffusion Provider:
- Optimized for users on resource-constrained hardware (e.g. MacBook Monterey 8GB RAM).
- Connects to Google Colab, Cloud GPU, or remote SD WebUI/Forge/ComfyUI tunnel.
- Standard API interface via /sdapi/v1/txt2img.
- Fully supports uncensored intimate, boudoir, and photorealistic portrait synthesis.
"""

import os
import uuid
import base64
import httpx
from pathlib import Path
from typing import List, Optional
from app.core.config import settings

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "generated" / "aura"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

class RemoteStableDiffusionProvider:
    def __init__(self):
        self.remote_url = settings.SD_REMOTE_URL or settings.COLAB_SD_API_URL or os.getenv("SD_REMOTE_URL", "")

    def get_effective_url(self) -> str:
        url = self.remote_url or os.getenv("SD_REMOTE_URL", "") or os.getenv("COLAB_SD_API_URL", "")
        return url.rstrip("/")

    async def is_available(self) -> bool:
        url = self.get_effective_url()
        if not url:
            return False
        try:
            headers = {"ngrok-skip-browser-warning": "any", "User-Agent": "AuraClient/1.0"}
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{url}/sdapi/v1/options", headers=headers)
                return res.status_code == 200
        except Exception:
            return False

    async def generate_image(
        self,
        prompt: str,
        scene: str,
        reference_paths: List[Path],
        aspect_ratio: str = "768:1024"
    ) -> Optional[str]:
        base_url = self.get_effective_url()
        if not base_url:
            return None

        # Determine target resolution
        w, h = (768, 1024) if "1024" in aspect_ratio else (768, 768)

        # Load master reference face for exact face conditioning / swapping
        master_face_b64 = ""
        ref_face_path = Path(__file__).resolve().parent.parent.parent / "static" / "references" / "aura_master_identity.jpg"
        if not ref_face_path.exists():
            ref_face_path = Path(__file__).resolve().parent.parent.parent / "static" / "references" / "aura_master_identity.png"
        if ref_face_path.exists():
            try:
                with open(ref_face_path, "rb") as rf:
                    master_face_b64 = base64.b64encode(rf.read()).decode("utf-8")
            except Exception as e:
                print(f"⚠️ [MASTER FACE READ]: {e}")

        # Build photorealistic prompt incorporating Aura's immutable facial DNA
        positive_prompt = (
            f"A hyper-realistic, candid selfie of a 22-year-old Slavic-fusion beauty, Aura, "
            f"fair porcelain skin, deep hazel-brown almond eyes, dark brown layered hair, {prompt}, "
            f"in {scene} atmosphere, natural skin texture, slight blush, realistic phone camera grain, "
            f"shallow depth of field, intimate and authentic vibe, soft warm indoor lighting, masterpiece, 8k uhd"
        )
        negative_prompt = (
            "cartoon, anime, 3d, painting, plastic skin, over-smooth skin, extra fingers, "
            "mutated hands, deformed, blurry, bad anatomy, wrong anatomy, doll, cgi, retouch"
        )

        payload = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "face_image": master_face_b64,
            "steps": 25,
            "width": w,
            "height": h,
            "cfg_scale": 7.0,
            "sampler_name": "DPM++ 2M Karras",
            "batch_size": 1
        }

        headers = {"ngrok-skip-browser-warning": "any", "User-Agent": "AuraClient/1.0"}

        try:
            print(f"🎨 [COLAB SD]: Dispatching txt2img generation to {base_url}...")
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{base_url}/sdapi/v1/txt2img",
                    json=payload,
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    images = data.get("images", [])
                    if images:
                        raw_b64 = images[0]
                        if "," in raw_b64:
                            raw_b64 = raw_b64.split(",")[1]

                        img_bytes = base64.b64decode(raw_b64)
                        file_name = f"aura_{scene}_{uuid.uuid4().hex[:8]}.jpg"
                        save_path = GENERATED_DIR / file_name

                        with open(save_path, "wb") as f:
                            f.write(img_bytes)

                        print(f"🔥 [REMOTE STABLE DIFFUSION SUCCESS]: Generated fresh deliverable via Colab SD: {file_name}")
                        return f"/static/generated/aura/{file_name}"
                else:
                    if "ERR_NGROK_3200" in response.text or response.status_code == 404:
                        print(f"⚠️ [COLAB SD OFFLINE]: Ngrok tunnel at {base_url} is currently offline (Colab session stopped or new URL generated).")
                        print("💡 Check your Google Colab tab, copy the active URL, and update SD_REMOTE_URL in .env and Render!")
                    else:
                        print(f"⚠️ [COLAB SD ERROR]: Remote server returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️ [REMOTE STABLE DIFFUSION PROVIDER]: Connection failed to {base_url}: {e}")

        return None

remote_sd_provider = RemoteStableDiffusionProvider()
