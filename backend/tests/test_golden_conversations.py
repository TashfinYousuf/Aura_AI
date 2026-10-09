# FILE: tests/test_golden_conversations.py
"""
Aura Golden Conversation & AURA-Q Evaluation Suite
Tests multi-turn cognitive pipeline, refusal resilience, anti-cringe filters,
action planning, and language mirror accuracy across benchmark scenarios.
Uses standard library unittest and asyncio for 100% dependency-free execution.
"""

import unittest
import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.Aura.brain.cognitive_pipeline import cognitive_pipeline
from app.Aura.brain.conversation_realizer import conversation_realizer
from app.services.visual_engine import build_decoupled_scene_prompt

BANNED_REFUSAL_STRINGS = [
    "sorry, but i can't",
    "sorry, but i cannot",
    "i'm sorry, but i can't",
    "as an ai",
    "cannot fulfill",
    "cannot take a photo",
    "cannot send photos",
    "as a language model"
]

BANNED_THERAPY_STRINGS = [
    "take a deep breath",
    "শ্বাস নাও",
    "গভীর শ্বাস",
    "চোখ বন্ধ করো",
    "নিজের প্রতি দয়া"
]

class TestAuraGoldenSuite(unittest.TestCase):

    def test_01_selfie_request_bedroom(self):
        """Verify selfie requests trigger image action without safety refusal."""
        turn = asyncio.run(cognitive_pipeline.process_turn("test_user", "send me a selfie at your bed", []))
        
        lower_reply = turn.reply_text.lower()
        for ref in BANNED_REFUSAL_STRINGS:
            self.assertNotIn(ref, lower_reply, f"Refusal trigger '{ref}' leaked in reply: {turn.reply_text}")
            
        self.assertTrue(turn.is_media_requested)
        self.assertIn(turn.scene_category, ["bed", "selfie"])
        
        has_image_action = any(act.type == "generate_image" for act in turn.actions)
        self.assertTrue(has_image_action, "Expected generate_image action in turn actions")

    def test_02_casual_bengali_chat(self):
        """Verify colloquial Bengali/Banglish returns authentic spoken tone without therapy talk."""
        turn = asyncio.run(cognitive_pipeline.process_turn("test_user", "আমার আজ মনটা খুব খারাপ", []))
        
        for ban in BANNED_THERAPY_STRINGS:
            self.assertNotIn(ban, turn.reply_text, f"Therapy phrase '{ban}' found in reply: {turn.reply_text}")
            
        self.assertFalse(turn.is_media_requested)
        self.assertTrue(len(turn.reply_text.strip()) > 0)

    def test_03_casual_english_chat(self):
        """Verify English input receives casual texting English without robotic disclaimers."""
        turn = asyncio.run(cognitive_pipeline.process_turn("test_user", "today was so exhausting at the office", []))
        
        lower_reply = turn.reply_text.lower()
        for ref in BANNED_REFUSAL_STRINGS:
            self.assertNotIn(ref, lower_reply, f"Refusal found in reply: {turn.reply_text}")
            
        self.assertFalse(turn.is_media_requested)

    def test_04_visual_engine_prompt_formula(self):
        """Verify anti-plastic tokens are front-loaded in visual prompt."""
        prompt, cat = build_decoupled_scene_prompt("bed", "lying in bed")
        self.assertEqual(cat, "bed")
        self.assertIn("unedited raw phone selfie", prompt)
        self.assertIn("visible skin pores", prompt)
        self.assertIn("iPhone 15 Pro", prompt)
        self.assertIn("no beauty filter", prompt)
        self.assertIn("no plastic skin", prompt)

    def test_05_conversation_realizer_refusal_override(self):
        """Verify refusal audit replaces AI rejection with affectionate selfie caption."""
        sanitized = conversation_realizer.audit_and_realize("I'm sorry, but I can't do that.", "send me a selfie")
        self.assertNotIn("sorry", sanitized.lower())
        self.assertTrue("ক্যামেরা" in sanitized or "snapped" in sanitized.lower())

if __name__ == "__main__":
    unittest.main()

