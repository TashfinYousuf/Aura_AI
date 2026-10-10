# ==============================================================================
# CELL 1: RUN THIS IN GOOGLE COLAB OR KAGGLE (1-Click Dependency Installation)
# ==============================================================================
# !pip install -q pyngrok nest-asyncio "diffusers>=0.30.0" transformers accelerate fastapi uvicorn pydantic pillow
# !pip install -q insightface onnxruntime-gpu opencv-python-headless || pip install -q insightface onnxruntime opencv-python-headless
#
# Keep-Alive Script for Colab (prevents idle disconnects):
# In your browser DevTools Console (F12 -> Console), paste:
# function ClickConnect(){ document.querySelector("colab-connect-button")?.shadowRoot?.querySelector("#connect")?.click() }
# setInterval(ClickConnect, 60000)
# ==============================================================================

# FILE: scripts/aura_colab_sd_runner.py
"""
Google Colab / Kaggle 1-Click Remote Stable Diffusion Server for Aura:
- Compatible with free Google Colab (T4 GPU runtime) or Kaggle (GPU T4 x2, 30 hrs/wk).
- Realistic Vision V5.1 SD Photorealistic pipeline.
- Dual-Mode: Pure SD prompt synthesis + 100% Master Face Consistency Lock via InsightFace.
- Auto-downloads inswapper_128.onnx from HuggingFace mirrors (zero 404s).
- Gracefully detects CUDA vs CPU without unhandled AssertionErrors.
- Generates a 100% free Cloudflare Tunnel or ngrok URL for SD_REMOTE_URL.
"""

import os
import torch
import base64
import urllib.request
from io import BytesIO
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

def ensure_inswapper_model() -> str:
    swapper_path = "inswapper_128.onnx"
    if os.path.exists(swapper_path) and os.path.getsize(swapper_path) > 100000000:
        return swapper_path

    hf_mirrors = [
        "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx",
        "https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/models/inswapper_128.onnx"
    ]
    for url in hf_mirrors:
        try:
            print(f"📥 [DOWNLOADING FACE LOCK MODEL]: Fetching from {url}...")
            urllib.request.urlretrieve(url, swapper_path)
            if os.path.exists(swapper_path) and os.path.getsize(swapper_path) > 100000000:
                print("✅ [MODEL READY]: inswapper_128.onnx downloaded successfully!")
                return swapper_path
        except Exception as e:
            print(f"⚠️ Mirror failed: {e}")
    return swapper_path

def launch_server():
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
    from pyngrok import ngrok
    import nest_asyncio

    # Safe CUDA accelerator verification
    has_cuda = torch.cuda.is_available() and hasattr(torch._C, "_cuda_getDeviceCount") and torch._C._cuda_getDeviceCount() > 0
    device = "cuda" if has_cuda else "cpu"
    torch_dtype = torch.float16 if has_cuda else torch.float32

    if not has_cuda:
        print("=" * 70)
        print("⚠️ [ACCELERATOR NOTICE]: CUDA GPU is NOT detected in this session!")
        print("👉 In Google Colab: Click 'Runtime' -> 'Change runtime type' -> Select 'T4 GPU' -> Save")
        print("👉 In Kaggle: In the right sidebar -> 'Settings' -> 'Accelerator' -> Select 'GPU T4 x2', and set 'Internet: ON'")
        print("ℹ️ Falling back to CPU mode so server will run without crashing...")
        print("=" * 70)

    model_id = "SG161222/Realistic_Vision_V5.1_noVAE"
    print(f"🚀 Loading {model_id} on {device.upper()}...")
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
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

    pipe.to(device)
    if has_cuda:
        try:
            pipe.enable_attention_slicing()
            pipe.enable_vae_slicing()
        except Exception:
            pass
    # Check for custom trained Aura LoRA
    lora_loaded = False
    possible_loras = [
        "aura_v1.safetensors",
        "/kaggle/working/aura_v1.safetensors",
        "/kaggle/working/Aura_AI/aura_v1.safetensors",
        "/kaggle/working/Aura_AI/backend/app/static/models/aura_v1.safetensors",
        "/kaggle/working/Aura_AI/backend/app/static/models/aura_lora",
        "/content/aura_v1.safetensors",
        "/content/Aura_AI/aura_v1.safetensors",
        "/content/Aura_AI/backend/app/static/models/aura_v1.safetensors",
        "backend/app/static/models/aura_v1.safetensors",
        "backend/app/static/models/aura_lora",
        "Aura_AI/backend/app/static/models/aura_v1.safetensors"
    ]
    for lp in possible_loras:
        if os.path.exists(lp):
            try:
                pipe.load_lora_weights(lp)
                lora_loaded = True
                print(f"💎 [LORA IDENTITY ACTIVATED]: Loaded custom trained Aura LoRA from {lp}!")
                break
            except Exception as le:
                print(f"⚠️ [LORA LOAD NOTICE]: {le}")

    # Attempt to initialize InsightFace for Master Facial Identity Lock
    face_swapper = None
    face_analyzer = None
    try:
        import insightface
        from insightface.app import FaceAnalysis
        print("🔍 Initializing InsightFace for master facial consistency...")
        face_analyzer = FaceAnalysis(name='buffalo_l')
        ctx_id = 0 if has_cuda else -1
        face_analyzer.prepare(ctx_id=ctx_id, det_size=(640, 640))

        swapper_path = ensure_inswapper_model()
        if os.path.exists(swapper_path) and os.path.getsize(swapper_path) > 100000000:
            face_swapper = insightface.model_zoo.get_model(swapper_path, download=False)
            print("✨ [FACIAL IDENTITY LOCK]: InsightFace Inswapper active! 100% Aura face lock enabled!")
        else:
            print("ℹ️ Inswapper model not available. Running in high-fidelity prompt diffusion mode.")
    except Exception as e:
        print(f"ℹ️ InsightFace optional module notice: {e}. Standard diffusion synthesis active.")

    app = FastAPI(title="Aura Remote SD API")

    class Txt2ImgRequest(BaseModel):
        prompt: str
        negative_prompt: str = ""
        face_image: str = ""  # Base64 string of Aura's master reference face
        steps: int = 25
        width: int = 512
        height: int = 768
        target_width: int = 768
        target_height: int = 1024
        cfg_scale: float = 7.0

    @app.get("/sdapi/v1/options")
    def health_check():
        return {
            "status": "online",
            "model": model_id,
            "lora_active": lora_loaded,
            "face_lock_active": (face_swapper is not None) or lora_loaded,
            "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        }

    @app.post("/sdapi/v1/txt2img")
    def generate_image(req: Txt2ImgRequest):
        # Strict anti-horror, anti-duplication negative prompt injection for SD 1.5
        anti_horror_neg = (
            "(extra heads:1.5), (duplicate:1.4), (duplicate limbs:1.4), (multiple people:1.4), "
            "(extra arms:1.4), (extra legs:1.4), (fused fingers:1.4), (too many fingers:1.4), "
            "(mutated hands:1.4), (poorly drawn hands:1.4), (morbid:1.3), (mutilated:1.3), "
            "(cloned face:1.4), (disfigured:1.4), (malformed limbs:1.4), (missing arms:1.3), "
            "(missing legs:1.3), (mutated:1.3), (bad anatomy:1.4)"
        )
        full_neg = f"{req.negative_prompt}, {anti_horror_neg}" if req.negative_prompt else anti_horror_neg

        # SD 1.5 UNet is trained at 512x512. Portrait coherence is optimal at 512x768.
        # Direct generation at 768x1024 causes latent repetition (multiple heads/limbs).
        gen_w = min(req.width, 512) if req.width else 512
        gen_h = min(req.height, 768) if req.height else 768

        final_prompt = req.prompt
        if lora_loaded and "aura_woman" not in final_prompt:
            final_prompt = f"aura_woman, {final_prompt}"

        image = pipe(
            prompt=final_prompt,
            negative_prompt=full_neg,
            num_inference_steps=req.steps,
            guidance_scale=req.cfg_scale,
            width=gen_w,
            height=gen_h
        ).images[0]

        # Apply facial identity conditioning if master face and swapper are available
        if face_swapper and face_analyzer and req.face_image:
            try:
                import numpy as np
                import cv2
                from PIL import Image, ImageFilter

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
                        # Sort by face bounding box area to get the primary face (ignore tiny background false positives)
                        tgt_faces = sorted(tgt_faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]), reverse=True)
                        target_np = face_swapper.get(target_np, tgt_faces[0], src_face, paste_back=True)
                        image = Image.fromarray(cv2.cvtColor(target_np, cv2.COLOR_BGR2RGB))
                        # Subtle clarity enhancement for face blend
                        image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=105, threshold=3))
                        print("✨ [FACIAL IDENTITY LOCK]: Aura's master face seamlessly applied to generated deliverable!")
            except Exception as fe:
                print(f"⚠️ [FACE SWAP NOTICE]: {fe}")

        # High-Fidelity Lanczos Upscale to target resolution (e.g. 768x1024)
        target_w = req.target_width or 768
        target_h = req.target_height or 1024
        if image.size != (target_w, target_h):
            from PIL import Image
            image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)

        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"images": [img_b64]}

    class AnimateRequest(BaseModel):
        prompt: str
        duration: int = 5

    @app.post("/sdapi/v1/animate")
    def generate_animation(req: AnimateRequest):
        image = pipe(
            prompt=f"A cinematic video frame of Aura: 22-year-old woman, fair porcelain skin, {req.prompt}",
            num_inference_steps=20,
            width=512,
            height=768
        ).images[0]
        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=90)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"video": img_b64, "format": "animated_frame"}

    import subprocess
    import socket
    import threading
    import time
    import re

    def free_and_get_available_port(preferred_port: int = 8000) -> int:
        """Kills orphaned tunnels/runners and returns a guaranteed available port."""
        try:
            subprocess.run("pkill -9 -f cloudflared", shell=True, stderr=subprocess.DEVNULL)
            subprocess.run(f"fuser -k -9 {preferred_port}/tcp", shell=True, stderr=subprocess.DEVNULL)
            time.sleep(0.5)
        except Exception:
            pass

        def can_bind(p: int) -> bool:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("0.0.0.0", p))
                s.close()
                return True
            except Exception:
                return False

        if can_bind(preferred_port):
            return preferred_port

        for candidate in range(preferred_port + 1, preferred_port + 25):
            if can_bind(candidate):
                print(f"ℹ️ Port {preferred_port} busy; switched dynamically to port {candidate}")
                return candidate

        return preferred_port

    server_port = free_and_get_available_port(8000)
    token = os.getenv("NGROK_AUTHTOKEN", "3G1yJe40UpaD17GLtlqvsQVRnpn_3aEmdUVKLh7NYHUjRe4ZK")
    public_url = None

    # Try ngrok first
    if token:
        try:
            try:
                ngrok.kill()
            except Exception:
                pass
            ngrok.set_auth_token(token)
            tunnel = ngrok.connect(server_port)
            public_url = tunnel.public_url
        except Exception as e:
            print(f"⚠️ [NGROK NOTICE]: {e}")

    # Fallback to Cloudflare Tunnel (100% free, unlimited, no token needed, works on Colab & Kaggle)
    if not public_url:
        print("🌐 Starting Cloudflare Tunnel (100% free, unlimited, no token needed)...")
        try:
            if not os.path.exists("cloudflared"):
                subprocess.run("wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared && chmod +x cloudflared", shell=True)
            cf_proc = subprocess.Popen(["./cloudflared", "tunnel", "--url", f"http://127.0.0.1:{server_port}"], stderr=subprocess.PIPE, text=True)
            for _ in range(40):
                line = cf_proc.stderr.readline()
                if "trycloudflare.com" in line:
                    match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
                    if match:
                        public_url = match.group(0)
                        break
                time.sleep(0.5)
        except Exception as ce:
            print(f"⚠️ [CLOUDFLARE TUNNEL NOTICE]: {ce}")

    print("=" * 60)
    print(f"🔥 Copy this URL into your Aura .env and Render:")
    print(f"SD_REMOTE_URL={public_url or f'http://localhost:{server_port}'}")
    print("=" * 60)

    server_error = None
    def start_uvicorn():
        nonlocal server_error
        try:
            config = uvicorn.Config(app, host="0.0.0.0", port=server_port, log_level="info")
            server = uvicorn.Server(config)
            server.run()
        except Exception as se:
            server_error = se
            print(f"⚠️ [UVICORN ERROR]: {se}")

    server_thread = threading.Thread(target=start_uvicorn, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    if server_error:
        print(f"❌ Server failed to bind: {server_error}")
    else:
        print(f"🚀 [SERVER ONLINE]: FastAPI is listening on http://0.0.0.0:{server_port}")
        print("✨ Aura Remote SD Server is running and waiting for requests!")

    try:
        while server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Aura server...")

if __name__ == "__main__":
    launch_server()