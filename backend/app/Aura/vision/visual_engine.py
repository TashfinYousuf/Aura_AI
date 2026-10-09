# FILE: backend/app/Aura/vision/visual_engine.py

from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from app.Aura.vision.image_engine import image_engine, CANON_DIR, GENERATED_DIR
from app.Aura.vision.video_engine import video_engine
from app.Aura.vision.qa_engine import qa_engine

class AssetBoundaryViolationError(Exception):
    """Raised when an internal identity reference asset is routed to a delivery channel."""
    pass

def validate_deliverable_asset(asset_url_or_path: str) -> str:
    """
    Ensures that no internal identity reference (canon/reference files)
    can ever leak directly into user channels.
    """
    normalized = str(asset_url_or_path).replace("\\", "/").lower()
    if "canon/" in normalized or "references/" in normalized or "identity_vault/" in normalized or "collage" in normalized:
        raise AssetBoundaryViolationError(
            f"SECURITY VIOLATION: Reference file '{asset_url_or_path}' cannot be delivered directly! "
            f"Only generated assets (from generated/aura/ or selfies/) are permitted."
        )
    return asset_url_or_path

class VisualEngine:
    """
    Master Canonical Visual Engine for Aura:
    - Image Generation: Nano Banana / Imagen 3 + Generative Identity Synthesizer.
    - Video Generation: Google Veo for cinematic reels and advertisements.
    - Visual QA: Identity consistency, realism, and asset boundary security.
    """
    @staticmethod
    async def generate_image(
        scene_category: str = "desk",
        prompt_desc: str = "",
        user_text: str = "",
        aspect_ratio: str = "768:1024",
        **kwargs
    ) -> str:
        effective_prompt = prompt_desc or user_text or f"relaxing at {scene_category}"
        asset_url = await image_engine.generate(
            prompt=effective_prompt,
            scene=scene_category,
            aspect_ratio=aspect_ratio
        )
        if not asset_url:
            asset_url = f"/static/generated/aura/aura_{scene_category}_backup.jpg"

        validate_deliverable_asset(asset_url)
        return asset_url

    @staticmethod
    async def generate_video(
        prompt: str,
        scene: str = "lifestyle",
        duration_seconds: int = 5
    ) -> Optional[str]:
        video_url = await video_engine.generate_reel(
            concept=prompt,
            scene=scene,
            duration_seconds=duration_seconds
        )
        if video_url:
            validate_deliverable_asset(video_url)
        return video_url

visual_engine = VisualEngine()

# Compatibility bridge for existing imports
generate_aura_identity_image = VisualEngine.generate_image
__all__ = ["VisualEngine", "visual_engine", "generate_aura_identity_image", "validate_deliverable_asset", "AssetBoundaryViolationError"]