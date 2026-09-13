import os
import uuid
import random
import urllib.parse
from app.services.prompt_composer import AuraPromptComposer

STATIC_DIR = os.path.join(os.getcwd(), "app", "static", "selfies")
os.makedirs(STATIC_DIR, exist_ok=True)

IS_LOCAL_DEV = not bool(os.getenv("RENDER"))
_local_pipe = None

composer = AuraPromptComposer()

import torch

def get_optimized_device() -> torch.device:
    """
    Forces Apple Silicon MPS (Metal Performance Shaders) execution.
    Prevents silent CPU fallback and manages GPU memory allocation.
    """
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        # Ensure memory allocation watermark is cleared for fresh inference
        torch.mps.empty_cache()
        print("🖥️ [HARDWARE] Active Backend: Apple Silicon Metal (MPS Accelerated)")
        return device
    else:
        print("⚠️ [HARDWARE WARNING] MPS unavailable. Falling back to CPU.")
        return torch.device("cpu")
    

def get_local_pipeline():
    global _local_pipe
    if _local_pipe is None:
        from diffusers import AutoPipelineForText2Image
        
        device = get_optimized_device()
        dtype = torch.float16 if device.type == "mps" else torch.float32
        
        print(f"🖥️ [IMAGE ENGINE] Loading model on {device.type.upper()}...")
        _local_pipe = AutoPipelineForText2Image.from_pretrained(
            "stabilityai/sdxl-turbo",
            torch_dtype=dtype,
            variant="fp16" if device.type == "mps" else None
        ).to(device)
        
        _local_pipe.safety_checker = None
        _local_pipe.requires_safety_checker = False
    return _local_pipe

def generate_aura_image(user_text: str, dynamic_context: str = "") -> str:
    """
    Main image routing engine: Compiles character DNA and sends to local or cloud tier.
    """
    intent = {
        "setting": "bedroom_bed" if "bed" in user_text.lower() else "bedroom_mirror",
        "outfit": "saree" if "saree" in user_text.lower() else "bedroom_casual",
        "expression": "teasing subtle smile, direct gaze"
    }
    
    composed_prompt = composer.build_prompt(intent)
    negative_prompt = composer.build_negative_prompt()

    # Local MPS Generation on Mac
    if IS_LOCAL_DEV:
        try:
            pipe = get_local_pipeline()
            import torch
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            
            image = pipe(
                prompt=composed_prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=2,
                guidance_scale=0.0,
                height=512,
                width=512
            ).images[0]
            
            file_name = f"selfie_{uuid.uuid4()}.jpg"
            file_path = os.path.join(STATIC_DIR, file_name)
            image.save(file_path, format="JPEG", quality=95)
            
            if device == "mps":
                torch.mps.empty_cache()
                
            return f"/static/selfies/{file_name}"
        except Exception as e:
            print(f"⚠️ [IMAGE ENGINE] Local pipeline error: {e}")

    # Cloud Fallback (Pollinations / HuggingFace)
    clean_text = urllib.parse.quote(composed_prompt[:250])
    seed = random.randint(1, 999999)
    return f"https://image.pollinations.ai/prompt/{clean_text}?width=512&height=512&nologo=true&seed={seed}&model=flux"