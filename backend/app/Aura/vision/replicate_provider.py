# FILE: backend/app/Aura/vision/replicate_provider.py
"""
Replicate Serverless On-Demand Vision Provider:
- Zero-Pera serverless execution: runs only when an image is requested.
- Zero Colab tabs, zero Kaggle limits, zero GPU heating or battery drain.
- Uses cutting-edge FLUX.1 / SDXL for flawless human anatomy (no multi-heads, no extra limbs).
- Automatically downloads and saves the generated asset locally.
"""

import os
import uuid
import asyncio
import httpx
from pathlib import Path
from typing import List, Optional
from app.core.config import settings

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "generated" / "aura"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

class ReplicateImageProvider:
    def __init__(self):
        self.api_token = os.getenv("REPLICATE_API_TOKEN", "").strip()

    def is_configured(self) -> bool:
        token = self.api_token or os.getenv("REPLICATE_API_TOKEN", "").strip()
        return bool(token and token.startswith("r8_"))

    async def generate_image(
        self,
        prompt: str,
        scene: str,
        reference_paths: List[Path],
        aspect_ratio: str = "768:1024"
    ) -> Optional[str]:
        token = self.api_token or os.getenv("REPLICATE_API_TOKEN", "").strip()
        if not token:
            return None

        # Build master photorealistic prompt locking Aura's physical DNA
        master_prompt = (
            f"A hyper-realistic candid portrait of Aura, a 22-year-old Slavic-fusion beauty, "
            f"fair porcelain skin with natural visible pores, deep hazel-brown almond eyes, "
            f"dark brown layered silky hair, slim straight sharp nose, slight blush. "
            f"She is in {scene} setting, {prompt}. Shot on 35mm lens, f/1.8, authentic lighting, "
            f"natural smartphone camera grain, masterpiece, 8k uhd, photorealistic, no distortion"
        )

        aspect = "3:4" if "1024" in aspect_ratio else "1:1"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Model: black-forest-labs/flux-schnell (serverless, 1-3 seconds, pristine anatomy)
        payload = {
            "version": "black-forest-labs/flux-schnell",
            "input": {
                "prompt": master_prompt,
                "aspect_ratio": aspect,
                "output_format": "jpg",
                "output_quality": 95,
                "num_outputs": 1
            }
        }

        try:
            print("🚀 [REPLICATE SERVERLESS]: Dispatching on-demand generation to FLUX.1...")
            async with httpx.AsyncClient(timeout=45.0) as client:
                # 1. Create prediction
                init_res = await client.post(
                    "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
                    headers=headers,
                    json={"input": payload["input"]}
                )

                if init_res.status_code not in (200, 201):
                    # Fallback to general predictions endpoint
                    init_res = await client.post(
                        "https://api.replicate.com/v1/predictions",
                        headers=headers,
                        json=payload
                    )

                if init_res.status_code not in (200, 201):
                    print(f"⚠️ [REPLICATE INIT NOTICE]: HTTP {init_res.status_code}: {init_res.text[:150]}")
                    return None

                pred_data = init_res.json()
                get_url = pred_data.get("urls", {}).get("get")
                if not get_url:
                    return None

                # 2. Poll until completed (usually 2-5 seconds for flux-schnell)
                for _ in range(25):
                    await asyncio.sleep(1.0)
                    poll_res = await client.get(get_url, headers=headers)
                    if poll_res.status_code == 200:
                        status_data = poll_res.json()
                        status = status_data.get("status")
                        if status == "succeeded":
                            output = status_data.get("output")
                            if output:
                                img_url = output[0] if isinstance(output, list) else output
                                # Download generated image bytes
                                dl_res = await client.get(img_url)
                                if dl_res.status_code == 200:
                                    file_name = f"aura_{scene}_{uuid.uuid4().hex[:8]}.jpg"
                                    save_path = GENERATED_DIR / file_name
                                    with open(save_path, "wb") as f:
                                        f.write(dl_res.content)
                                    print(f"✨ [REPLICATE SERVERLESS SUCCESS]: Generated deliverable via FLUX: {file_name}")
                                    return f"/static/generated/aura/{file_name}"
                        elif status in ("failed", "canceled"):
                            print(f"⚠️ [REPLICATE PREDICTION FAILED]: {status_data.get('error')}")
                            break

        except Exception as e:
            print(f"⚠️ [REPLICATE PROVIDER ERROR]: {e}")

        return None

replicate_provider = ReplicateImageProvider()

