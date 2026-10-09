# FILE: backend/test_master_reference.py

import os
import sys
import asyncio
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.append(str(backend_dir))

from app.services.visual_engine import (
    generate_aura_identity_image,
    validate_deliverable_asset,
    AssetBoundaryViolationError,
    STATIC_DIR
)

async def test_identity_generation():
    print("🚀 [TEST] Testing canonical visual engine (IDENTITY LOCK)...")
    
    # Generate image for desk
    desk_url = await generate_aura_identity_image(scene_category="desk", user_text="can you send me a desk selfie?")
    print(f"✅ Generated desk deliverable: {desk_url}")
    
    # Assert it passes delivery validation
    validated = validate_deliverable_asset(desk_url)
    assert not ("references/" in validated), "FATAL: Reference asset delivered!"
    print(f"🔒 Security Invariant Verified: No reference leak!")

    # Test asset boundary violation rejection
    try:
        validate_deliverable_asset("/static/references/Aura Collage.png")
        assert False, "FAILED: Should have raised AssetBoundaryViolationError"
    except AssetBoundaryViolationError:
        print("🛡️ Security Invariant Guard successfully blocked reference leak!")

if __name__ == "__main__":
    asyncio.run(test_identity_generation())