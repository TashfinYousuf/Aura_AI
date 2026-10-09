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
    Main image routing engine: Delegates to the realistic unedited visual engine.
    """
    import asyncio
    from app.services.visual_engine import generate_aura_identity_image
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, generate_aura_identity_image(user_text=user_text, prompt_desc=dynamic_context)).result()
        return loop.run_until_complete(generate_aura_identity_image(user_text=user_text, prompt_desc=dynamic_context))
    except Exception:
        return asyncio.run(generate_aura_identity_image(user_text=user_text, prompt_desc=dynamic_context))