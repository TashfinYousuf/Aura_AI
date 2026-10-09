# FILE: tests/test_reference_leak.py

import os
import sys
import unittest
from pathlib import Path

# Resolve backend directory robustly
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.visual_engine import (
    validate_deliverable_asset,
    AssetBoundaryViolationError,
    AssetPurpose,
    build_decoupled_scene_prompt,
    generate_aura_identity_image
)

class TestAssetUniverseSeparation(unittest.TestCase):
    def test_reference_asset_delivery_blocked(self):
        """Invariant: Under NO circumstance can files from references/ be delivered."""
        leaky_paths = [
            "/static/references/Aura Collage.png",
            "/static/references/aura_master_identity.png",
            "backend/app/static/references/Aura Collage.png",
            "references/some_collage.jpg",
            "/static/references/test.png"
        ]
        for path in leaky_paths:
            with self.assertRaises(AssetBoundaryViolationError, msg=f"Failed to block reference leak: {path}"):
                validate_deliverable_asset(path)

    def test_deliverable_asset_allowed(self):
        """Invariant: Only genuine deliverable assets from selfies/ or external URLs are permitted."""
        valid_paths = [
            "/static/selfies/aura_desk_12345678.jpg",
            "/static/selfies/aura_bed_87654321.jpg",
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=768&h=1024"
        ]
        for path in valid_paths:
            validated = validate_deliverable_asset(path)
            self.assertEqual(validated, path)

    def test_anti_plastic_scene_prompt(self):
        """Invariant: Visual prompt must front-load anti-plastic and Canon-compliant tokens."""
        prompt, cat = build_decoupled_scene_prompt("bed", "I'm heading to sleep")
        self.assertEqual(cat, "bed")
        self.assertIn("visible skin pores", prompt)
        self.assertIn("authentic skin texture", prompt)
        self.assertIn("no beauty filter", prompt)
        self.assertIn("no retouching", prompt)
        self.assertIn("no plastic skin", prompt)

    def test_generate_image_never_returns_reference(self):
        """Invariant: Calling generate_aura_identity_image must never return a reference path."""
        import asyncio
        url = asyncio.run(generate_aura_identity_image(scene_category="desk"))
        self.assertNotIn("references/", url)
        self.assertNotIn("Collage", url)
        self.assertNotIn("master_identity", url)

if __name__ == "__main__":
    unittest.main()

