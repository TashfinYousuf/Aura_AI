from enum import Enum
from app.Aura.vision.visual_engine import (
    VisualEngine,
    visual_engine,
    generate_aura_identity_image,
    validate_deliverable_asset,
    AssetBoundaryViolationError
)
from app.Aura.vision.image_engine import GENERATED_DIR
from pathlib import Path

class AssetPurpose(str, Enum):
    REFERENCE_ANCHOR = "reference_anchor"
    DELIVERABLE = "deliverable"
    PROMOTIONAL = "promotional"

# Static directories for backward compatibility
STATIC_BASE = Path(__file__).resolve().parent.parent / "static"
STATIC_DIR = GENERATED_DIR
STATIC_REF_DIR = Path(__file__).resolve().parent.parent / "identity" / "aura" / "canon"

def build_decoupled_scene_prompt(scene_category: str = "desk", context_text: str = ""):
    prompt = (
        f"unedited raw phone selfie of Aura in a {scene_category} setting, {context_text}, "
        f"shot on iPhone 15 Pro, visible skin pores, authentic skin texture, natural lighting, "
        f"no beauty filter, no retouching, no plastic skin, smartphone camera photography."
    )
    return prompt, scene_category

def get_reference_vault_images():
    canon_refs = list(STATIC_REF_DIR.glob("*.*"))
    static_refs = list((STATIC_BASE / "references").glob("*.*"))
    seen = {c.name for c in canon_refs}
    combined = list(canon_refs)
    for r in static_refs:
        if r.name not in seen:
            combined.append(r)
            seen.add(r.name)
    return combined

__all__ = [
    "VisualEngine",
    "visual_engine",
    "generate_aura_identity_image",
    "validate_deliverable_asset",
    "AssetBoundaryViolationError",
    "AssetPurpose",
    "build_decoupled_scene_prompt",
    "get_reference_vault_images",
    "STATIC_BASE",
    "STATIC_DIR",
    "STATIC_REF_DIR",
    "GENERATED_DIR"
]