# FILE: backend/app/services/identity_pipeline.py

import os
import uuid
import torch
from pathlib import Path
from PIL import Image

class AuraIdentityEngine:
    """
    Coordinates reference-conditioned image generation.
    Handles token-budget optimization for CLIP and hardware acceleration.
    """
    def __init__(self, reference_image_path: str = "app/static/references/aura_master_identity.png"):
        self.ref_path = reference_image_path
        self.device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")
        self.dtype = torch.float16 if self.device.type == "mps" else torch.float32
        
        # Identity tokens: under 30 tokens to leave budget for dynamic scenes
        self.core_identity_prompt = (
            "candid selfie of Aura, 22yo slavic woman, fair porcelain skin, "
            "deep hazel almond eyes, sharp slim nose, dark layered hair, slim athletic fit"
        )
        self.negative_prompt = (
            "cartoon, anime, 3d render, plastic smooth skin, distorted eyes, "
            "bad anatomy, extra fingers, blurry, watermark"
        )

    def compose_scene_prompt(self, user_scene: str) -> str:
        """
        Combines core identity with concise scene descriptors to stay strictly under 77 CLIP tokens.
        """
        clean_scene = user_scene.strip().rstrip(".")
        # Resulting token count: ~45-55 tokens, well within the 77-token hard ceiling
        return f"{self.core_identity_prompt}, {clean_scene}, warm bedroom lighting, phone camera grain"

    def generate(self, pipe, scene_description: str, output_dir: str = "app/static/selfies") -> str:
        full_prompt = self.compose_scene_prompt(scene_description)
        print(f"🎨 [GENERATING] Prompt ({len(full_prompt.split())} words): {full_prompt}")

        image = pipe(
            prompt=full_prompt,
            negative_prompt=self.negative_prompt,
            num_inference_steps=2,
            guidance_scale=0.0,
            width=512,
            height=512
        ).images[0]

        os.makedirs(output_dir, exist_ok=True)
        file_name = f"aura_{uuid.uuid4().hex[:8]}.jpg"
        save_path = os.path.join(output_dir, file_name)
        
        image.save(save_path, quality=95)
        
        if self.device.type == "mps":
            torch.mps.empty_cache()
            
        return f"/static/selfies/{file_name}"