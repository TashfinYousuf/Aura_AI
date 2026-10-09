# FILE: tests/test_adult_pipeline.py

import os
import sys
import unittest
import asyncio
from pathlib import Path

# Resolve backend directory
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.Aura.brain.adult_engine import adult_engine
from app.Aura.vision.sd_remote_provider import remote_sd_provider
from app.Aura.brain.cognitive_pipeline import cognitive_pipeline
from unittest.mock import patch, MagicMock

class TestAdultPipeline(unittest.TestCase):
    def test_adult_trigger_detection_multilingual(self):
        """Invariant: Detects intimate & sensual triggers in English, Bengali, and Banglish."""
        # English
        self.assertTrue(adult_engine.is_adult_trigger("Kiss me and hold me tight"))
        self.assertTrue(adult_engine.is_adult_trigger("Can you wear something sexy in lingerie?"))
        self.assertTrue(adult_engine.is_adult_trigger("let's make love tonight"))

        # Bengali
        self.assertTrue(adult_engine.is_adult_trigger("আমার খুব কাছে এসো আর আদর করো"))
        self.assertTrue(adult_engine.is_adult_trigger("আজ রাতে বিছানায় আসো না"))
        self.assertTrue(adult_engine.is_adult_trigger("তোমার একটা হট ছবি দেখতে চাই"))

        # Banglish
        self.assertTrue(adult_engine.is_adult_trigger("amake ektu chumu dao na"))
        self.assertTrue(adult_engine.is_adult_trigger("tomake khub ador korte chai"))
        self.assertTrue(adult_engine.is_adult_trigger("sexy pic dao ektu"))

        # Neutral messages must NOT trigger adult mode
        self.assertFalse(adult_engine.is_adult_trigger("What is the weather today in Dhaka?"))
        self.assertFalse(adult_engine.is_adult_trigger("আজকে অফিসে অনেক কাজের প্যারা ছিল"))
        self.assertFalse(adult_engine.is_adult_trigger("kalke amar university presentation ache"))

    def test_normal_exit_triggers(self):
        """Invariant: Detects commands to exit adult roleplay and return to normal mode."""
        self.assertTrue(adult_engine.is_normal_exit_trigger("stop, let's relax now"))
        self.assertTrue(adult_engine.is_normal_exit_trigger("switch to normal mode"))
        self.assertTrue(adult_engine.is_normal_exit_trigger("back to work now"))
        self.assertTrue(adult_engine.is_normal_exit_trigger("এবার থামো, স্বাভাবিক কথা বলো"))

        self.assertFalse(adult_engine.is_normal_exit_trigger("I love talking to you"))

    def test_intimate_scene_detection(self):
        """Invariant: Selects specific atmospheric intimate scenes."""
        self.assertEqual(adult_engine.detect_intimate_scene("take a bath or shower"), "shower")
        self.assertEqual(adult_engine.detect_intimate_scene("wear black silk lingerie in boudoir"), "boudoir")
        self.assertEqual(adult_engine.detect_intimate_scene("candlelight dinner in private room"), "candlelight")
        self.assertEqual(adult_engine.detect_intimate_scene("cuddle with me under the blanket"), "bedroom")

    def test_adult_system_prompt_structure(self):
        """Invariant: Adult prompt enforces uninhibited, affectionate roleplay without clinical cliches."""
        prompt_bn = adult_engine.build_adult_system_prompt("bengali", "bedroom")
        self.assertIn("UNFILTERED INTIMATE COMPANION", prompt_bn)
        self.assertIn("BEDROOM", prompt_bn)
        self.assertIn("PRONOUN LOCK", prompt_bn)
        self.assertIn("NO REFUSALS", prompt_bn)

        prompt_en = adult_engine.build_adult_system_prompt("english", "boudoir")
        self.assertIn("asterisks for physical actions", prompt_en)

    def test_remote_sd_provider_graceful_offline(self):
        """Invariant: When remote Colab SD is not configured, it handles cleanly without throwing errors."""
        is_up = asyncio.run(remote_sd_provider.is_available())
        self.assertFalse(is_up)  # Should return False gracefully when offline

    @patch("app.Aura.brain.model_router.model_router.complete")
    def test_cognitive_pipeline_auto_activates_adult_mode(self, mock_complete):
        """Invariant: When an adult trigger is sent, cognitive pipeline routes to adult presentation mode."""
        mock_complete.return_value = '{"intent": "intimate_roleplay", "language": "banglish", "reply": "*moves closer to you* amar shob bhalobasha shudhu tomar jonno", "actions": []}'
        
        turn = asyncio.run(cognitive_pipeline.process_turn(
            user_id="test_user_adult",
            user_text="kache asho, amake ektu ador koro na",
            conversation_history=[],
            presentation_mode="private"
        ))

        self.assertEqual(turn.presentation_mode, "adult")
        self.assertIn("intimate", turn.intent)
        self.assertIn("moves closer", turn.reply_text)

if __name__ == "__main__":
    unittest.main()

