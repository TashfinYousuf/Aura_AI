# FILE: tests/test_voice_and_reference_synth.py

import os
import sys
import unittest
import asyncio
from pathlib import Path

# Resolve backend directory robustly
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.voice_ssml import (
    clean_spoken_text_for_tts,
    detect_voice_parameters,
    VOICE_CONFIG
)
from app.services.visual_engine import (
    generate_aura_identity_image,
    validate_deliverable_asset,
    AssetBoundaryViolationError,
    get_reference_vault_images,
    STATIC_DIR
)

class TestVoiceAndReferenceSynth(unittest.TestCase):

    def test_voice_emoji_and_punctuation_stripping(self):
        """Invariant: Emojis, dari, and ellipses are purged so TTS never reads symbols aloud."""
        raw_bengali = "এই নাও, মাত্র তোমার জন্যই ক্যামেরা অন করলাম... কেমন লাগছে বলো? 🙈✨"
        cleaned = clean_spoken_text_for_tts(raw_bengali)
        
        # Must not contain emojis
        self.assertNotIn("🙈", cleaned)
        self.assertNotIn("✨", cleaned)
        # Must not contain ellipses that cause 'dot dot dot'
        self.assertNotIn("...", cleaned)
        self.assertNotIn("..", cleaned)

        voice, rate, pitch = detect_voice_parameters(cleaned)
        # Must use Tanisha bn
        self.assertEqual(voice, "bn-IN-TanishaaNeural")

    def test_voice_dari_replaced_with_clean_pause(self):
        """Invariant: Bengali dari (।) must not be spoken as a literal symbol."""
        raw_text = "আজকে মনটা খুব খারাপ। একটু কথা বলবে? 🥺"
        cleaned = clean_spoken_text_for_tts(raw_text)
        
        self.assertNotIn("।", cleaned)
        self.assertNotIn("🥺", cleaned)
        self.assertIn(".", cleaned)

    def test_voice_banglish_routes_to_tanisha(self):
        """Invariant: Banglish speech routes to Tanisha bn for authentic South Asian pronunciation."""
        raw_banglish = "Ei to kaj korchi, tumi kemon acho? ✨"
        cleaned = clean_spoken_text_for_tts(raw_banglish)
        voice, rate, pitch = detect_voice_parameters(cleaned)
        
        self.assertEqual(voice, "bn-IN-TanishaaNeural")

    def test_voice_english_routes_to_emma(self):
        """Invariant: English conversation routes to canonical young conversational English voice."""
        raw_english = "*smiles* Just finished my coffee, how are you? ☕"
        cleaned = clean_spoken_text_for_tts(raw_english)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("☕", cleaned)
        
        voice, rate, pitch = detect_voice_parameters(cleaned)
        self.assertEqual(voice, "en-US-EmmaNeural")

    def test_reference_vault_discovery(self):
        """Invariant: Visual engine catalogs all reference images from static/references/."""
        refs = get_reference_vault_images()
        self.assertTrue(len(refs) > 0, "Reference vault must discover images in static/references/")
        ref_names = [r.name for r in refs]
        self.assertTrue("Aura_1.png" in ref_names or "Aura 1.png" in ref_names)

    def test_fresh_selfie_generation_from_reference_vault(self):
        """Invariant: Image generation synthesizes freshly created deliverable matching context."""
        scenes = ["desk", "bed", "cafe", "evening"]
        for scene in scenes:
            url = asyncio.run(generate_aura_identity_image(scene_category=scene, user_text=f"send me a {scene} selfie"))
            
            # Assert file exists and is in deliverable static directories
            self.assertTrue(url.startswith("/static/generated/aura/") or url.startswith("/static/selfies/"))
            file_name = url.split("/")[-1]
            full_path = (STATIC_DIR / file_name) if (STATIC_DIR / file_name).exists() else (Path(__file__).resolve().parent.parent / "backend" / "app" / "static" / "generated" / "aura" / file_name)
            self.assertTrue(full_path.exists(), f"Generated image file must exist on disk: {full_path}")
            self.assertTrue(full_path.stat().st_size > 10000, "Generated image must have valid file size")

            # Assert security invariant
            validated = validate_deliverable_asset(url)
            self.assertEqual(validated, url)
            self.assertNotIn("references", url)
            self.assertNotIn("collage", url.lower())

if __name__ == "__main__":
    unittest.main()
