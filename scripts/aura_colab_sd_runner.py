# Install necessary dependencies first
# !pip install -q pyngrok nest-asyncio diffusers transformers accelerate fastapi uvicorn pydantic

# FILE: scripts/aura_colab_sd_runner.py
"""
Google Colab 1-Click Remote Stable Diffusion Server for Aura:
Run this on a free Google Colab (T4 GPU runtime) or remote Linux GPU machine.
Generates an ngrok or Cloudflare tunnel URL to paste into SD_REMOTE_URL.
"""

import os
import torch
import base64
from io import BytesIO
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# Fast lightweight Colab runner for Realistic Vision / CyberRealistic
def launch_server():
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    from pyngrok import ngrok
    import nest_asyncio

    model_id = "SG161222/Realistic_Vision_V5.1_noVAE"
    print(f"⌒ Loading {model_id} on CUDA GPU...")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        dtype=torch.float16,
        safety_checker=None  # Allows consensual intimate / sensual roleplay visuals
    )
    
    try:
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                pipe.scheduler.config,
                use_karras_sigmas=True,
                algorithm_type="dpmsolver++"
            )
    except Exception:
        from diffusers import EulerAncestralDiscreteScheduler
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.to("cuda")
    print("✅ Model loaded successfully on GPU!")

    app = FastAPI(title="Aura Remote SD API")

    class Txt2ImgRequest(BaseModel):
        prompt: str
        negative_prompt: str = ""
        steps: int = 25
        width: int = 768
        height: int = 1024
        cfg_scale: float = 7.0

    @app.get("/sdapi/v1/options")
    def health_check():
        return {
            "status": "online",
            "model": model_id,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        }

    @app.post("/sdapi/v1/txt2img")
    def generate_image(req: Txt2ImgRequest):
        image = pipe(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            num_inference_steps=req.steps,
            guidance_scale=req.cfg_scale,
            width=req.width,
            height=req.height
        ).images[0]

        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"images": [img_b64]}

    token = os.getenv("NGROK_AUTHTOKEN", "3G1yJe40UpaD17GLtlqvsQVRnpn_3aEmdUVKLh7NYHUjRe4ZK")
    if token:
        ngrok.set_auth_token(token)

    tunnel = ngrok.connect(8000)
    print("=" * 60)
    print(f"— Copy this URL into your Aura .env file:")
    print(f"SD_REMOTE_URL={tunnel.public_url}")
    print("=" * 60)

    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    launch_server()