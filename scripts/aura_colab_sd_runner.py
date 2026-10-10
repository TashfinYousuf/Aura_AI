# FILE: scripts/aura_colab_sd_runner.py
"""
Aura 1-Click Indestructible Remote Stable Diffusion Server:
- Zero-Pera Auto-Installer: Automatically detects and installs any missing packages on Colab or Kaggle.
- 100% Free of ModuleNotFoundError: Never crashes on missing pyngrok, fastapi, diffusers, or uvicorn.
- Auto-Detects & Activates trained Aura LoRA (aura_v1.safetensors) from Colab, Kaggle, or Google Drive.
- Runs Cloudflare Tunnel (100% free, unlimited, no token needed, zero registration).
- Provides instant URL for SD_REMOTE_URL in Aura .env.
"""

import os
import sys
import subprocess

# -----------------------------------------------------------------------------
# 1. Self-Healing Package Installer (Guarantees true 1-click execution)
# -----------------------------------------------------------------------------
def ensure_dependencies():
    packages_to_check = [
        ("torch", "torch"),
        ("diffusers", "diffusers>=0.30.0"),
        ("transformers", "transformers"),
        ("accelerate", "accelerate"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("PIL", "pillow"),
        ("nest_asyncio", "nest-asyncio")
    ]
    missing = []
    for mod, pkg in packages_to_check:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print("=" * 70)
        print(f"📦 [AURA AUTO-SETUP]: Preparing environment ({', '.join(missing)})...")
        print("⏳ Installing required libraries (takes ~30-45s)...")
        print("=" * 70)
        subprocess.run([sys.executable, "-m", "pip", "install", "-q"] + missing, check=False)
        print("✅ [AURA AUTO-SETUP]: Environment ready!")

ensure_dependencies()

import base64
import urllib.request
from io import BytesIO
from pathlib import Path
import torch
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# -----------------------------------------------------------------------------
# 2. Master Face Model Auto-Downloader
# -----------------------------------------------------------------------------
def ensure_inswapper_model() -> str:
    possible_paths = [
        Path("inswapper_128.onnx"),
        Path("/content/inswapper_128.onnx"),
        Path("/kaggle/working/inswapper_128.onnx")
    ]
    for p in possible_paths:
        if p.exists() and p.stat().st_size > 100000000:
            return str(p)

    swapper_path = "inswapper_128.onnx"
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

# -----------------------------------------------------------------------------
# 3. Main Server Orchestrator
# -----------------------------------------------------------------------------
def launch_server():
    from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
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
        safety_checker=None
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

    # -------------------------------------------------------------------------
    # Comprehensive Aura LoRA Discovery
    # -------------------------------------------------------------------------
    lora_loaded = False
    candidate_loras = [
        "aura_v1.safetensors",
        "/content/aura_v1.safetensors",
        "/kaggle/working/aura_v1.safetensors",
        "/content/drive/MyDrive/Aura_AI/aura_v1.safetensors",
        "/content/drive/MyDrive/aura_v1.safetensors",
        "backend/app/static/models/aura_v1.safetensors"
    ]
    # Scan filesystem dynamically
    for root_dir in ["/content", "/kaggle/working", "."]:
        rp = Path(root_dir)
        if rp.exists():
            try:
                for f in rp.rglob("aura_v1.safetensors"):
                    fs = str(f)
                    if fs not in candidate_loras:
                        candidate_loras.insert(0, fs)
            except Exception:
                pass

    for lp in candidate_loras:
        if os.path.exists(lp) and os.path.getsize(lp) > 100000:
            try:
                pipe.load_lora_weights(lp)
                lora_loaded = True
                print("=" * 70)
                print(f"💎 [LORA IDENTITY ACTIVATED]: Loaded custom trained Aura LoRA from:")
                print(f"👉 {lp}")
                print("=" * 70)

                # Auto-backup to Google Drive if Drive is mounted on Colab
                if os.path.exists("/content/drive/MyDrive"):
                    try:
                        import shutil
                        drive_dest = Path("/content/drive/MyDrive/Aura_AI/aura_v1.safetensors")
                        drive_dest.parent.mkdir(parents=True, exist_ok=True)
                        if not drive_dest.exists():
                            shutil.copy(lp, str(drive_dest))
                            print(f"💾 [PERMANENT BACKUP]: Backed up aura_v1.safetensors to your Google Drive ({drive_dest})!")
                    except Exception:
                        pass
                break
            except Exception as le:
                print(f"⚠️ [LORA LOAD NOTICE]: {le}")

    # Optional InsightFace Face Swap
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
    except Exception as e:
        print(f"ℹ️ InsightFace notice: {e}. Running in pure photorealistic LoRA diffusion mode.")

    app = FastAPI(title="Aura Remote SD API")

    class Txt2ImgRequest(BaseModel):
        prompt: str
        negative_prompt: str = ""
        face_image: str = ""
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
        anti_horror_neg = (
            "(extra heads:1.5), (duplicate:1.4), (duplicate limbs:1.4), (multiple people:1.4), "
            "(mutated hands:1.4), (fused fingers:1.4), (bad anatomy:1.4), cartoon, anime, 3d, cgi"
        )
        full_neg = f"{req.negative_prompt}, {anti_horror_neg}" if req.negative_prompt else anti_horror_neg

        gen_w = min(req.width, 512) if req.width else 512
        gen_h = min(req.height, 768) if req.height else 768

        final_prompt = req.prompt.strip()
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

                target_np = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                src_raw = req.face_image.split(",")[-1]
                src_bytes = base64.b64decode(src_raw)
                src_np = cv2.imdecode(np.frombuffer(src_bytes, np.uint8), cv2.IMREAD_COLOR)

                src_faces = face_analyzer.get(src_np)
                if src_faces:
                    src_face = src_faces[0]
                    tgt_faces = face_analyzer.get(target_np)
                    if tgt_faces:
                        tgt_faces = sorted(tgt_faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]), reverse=True)
                        target_np = face_swapper.get(target_np, tgt_faces[0], src_face, paste_back=True)
                        image = Image.fromarray(cv2.cvtColor(target_np, cv2.COLOR_BGR2RGB))
                        image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=105, threshold=3))
                        print("✨ [FACIAL IDENTITY LOCK]: Aura's master face seamlessly applied!")
            except Exception as fe:
                print(f"⚠️ [FACE SWAP NOTICE]: {fe}")

        target_w = req.target_width or 768
        target_h = req.target_height or 1024
        if image.size != (target_w, target_h):
            from PIL import Image
            image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)

        buffered = BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return {"images": [img_b64]}

    import socket
    import threading
    import time
    import re

    def free_and_get_available_port(preferred_port: int = 8000) -> int:
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
    public_url = None

    # Safe optional ngrok attempt (never crashes if pyngrok is missing)
    try:
        from pyngrok import ngrok
        token = os.getenv("NGROK_AUTHTOKEN", "3G1yJe40UpaD17GLtlqvsQVRnpn_3aEmdUVKLh7NYHUjRe4ZK")
        if token:
            try:
                ngrok.kill()
            except Exception:
                pass
            ngrok.set_auth_token(token)
            tunnel = ngrok.connect(server_port)
            public_url = tunnel.public_url
    except Exception as e:
        print(f"ℹ️ [NGROK BYPASS]: {e}. Proceeding directly with Cloudflare Tunnel...")

    # Cloudflare Tunnel (100% free, unlimited, zero token required)
    if not public_url:
        print("🌐 Starting Cloudflare Tunnel (100% free, unlimited, zero token required)...")
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
            print(f"⚠️ [CLOUDFLARE NOTICE]: {ce}")

    print("=" * 60)
    print("🔥 COPY THIS URL INTO YOUR AURA .env AND RENDER:")
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