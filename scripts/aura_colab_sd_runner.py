# Install necessary dependencies in Google Colab (Run in a cell first):
# !pip install -q pyngrok nest-asyncio diffusers transformers accelerate fastapi uvicorn pydantic insightface onnxruntime-gpu opencv-python-headless pillow
# !wget -nc https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx -O inswapper_128.onnx

# FILE: scripts/aura_colab_sd_runner.py
"""
Google Colab 1-Click Remote Stable Diffusion Server for Aura:
- Runs on a free Google Colab (T4 GPU runtime) or any remote Linux GPU.
- Realistic Vision V5.1 SD Photorealistic pipeline.
- Dual-Mode: Pure SD prompt synthesis + 100% Master Face Consistency Lock via InsightFace.
- Uncensored consensual intimate, bedroom, and aesthetic portrait generation.
- Generates an ngrok or Cloudflare tunnel URL to paste into SD_REMOTE_URL.
"""

import os
import torch
import base64
from io import BytesIO
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

def launch_server():
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    from pyngrok import ngrok
    import nest_asyncio

    model_id = "SG161222/Realistic_Vision_V5.1_noVAE"
    print(f"🚀 Loading {model_id} on CUDA GPU...")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,
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

    # Attempt to initialize InsightFace for Master Facial Identity Lock
    face_swapper = None
    face_analyzer = None
    try:
        import insightface
        from insightface.app import FaceAnalysis
        print("🔍 Initializing InsightFace for master facial consistency...")
        face_analyzer = FaceAnalysis(name='buffalo_l')
        face_analyzer.prepare(ctx_id=0, det_size=(640, 640))

        swapper_path = "inswapper_128.onnx"
        if os.path.exists(swapper_path):
            face_swapper = insightface.model_zoo.get_model(swapper_path, download=False)
            print("✨ [FACIAL IDENTITY LOCK]: InsightFace Inswapper active! 100% Aura face lock enabled!")
        else:
            print(f"ℹ️ {swapper_path} not found. Running in high-fidelity prompt diffusion mode.")
            print("👉 Run: !wget -nc https://github.com/facefusion/facefusion-assets/releases/download/models/inswapper_128.onnx -O inswapper_128.onnx")
    except Exception as e:
        print(f"ℹ️ InsightFace optional module: {e}. Standard diffusion synthesis active.")

    app = FastAPI(title="Aura Remote SD API")

    class Txt2ImgRequest(BaseModel):
        prompt: str
        negative_prompt: str = ""
        face_image: str = ""  # Base64 string of Aura's master reference face
        steps: int = 25
        width: int = 768
        height: int = 1024
        cfg_scale: float = 7.0

    @app.get("/sdapi/v1/options")
    def health_check():
        return {
            "status": "online",
            "model": model_id,
            "face_lock_active": face_swapper is not None,
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

        # Apply facial identity conditioning if master face and swapper are available
        if face_swapper and face_analyzer and req.face_image:
            try:
                import numpy as np
                import cv2
                from PIL import Image

                # Convert generated PIL image to BGR numpy array
                target_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

                # Decode master source reference face
                src_raw = req.face_image.split(",")[-1]
                src_bytes = base64.b64decode(src_raw)
                src_np = cv2.imdecode(np.frombuffer(src_bytes, np.uint8), cv2.IMREAD_COLOR)

                # Extract faces
                src_faces = face_analyzer.get(src_np)
                if src_faces:
                    src_face = src_faces[0]
                    tgt_faces = face_analyzer.get(target_np)
                    if tgt_faces:
                        # Sort by face bounding box area to get the primary face
                        tgt_faces = sorted(tgt_faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]), reverse=True)
                        target_np = face_swapper.get(target_np, tgt_faces[0], src_face, paste_back=True)
                        image = Image.fromarray(cv2.cvtColor(target_np, cv2.COLOR_BGR2RGB))
                        print("✨ [FACIAL IDENTITY LOCK]: Aura's master face seamlessly applied to generated deliverable!")
            except Exception as fe:
                print(f"⚠️ [FACE SWAP NOTICE]: {fe}")

        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"images": [img_b64]}

    token = os.getenv("NGROK_AUTHTOKEN", "3G1yJe40UpaD17GLtlqvsQVRnpn_3aEmdUVKLh7NYHUjRe4ZK")
    if token:
        ngrok.set_auth_token(token)

    tunnel = ngrok.connect(8000)
    print("=" * 60)
    print(f"🔥 Copy this URL into your Aura .env and Render:")
    print(f"SD_REMOTE_URL={tunnel.public_url}")
    print("=" * 60)

    nest_asyncio.apply()
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    launch_server()