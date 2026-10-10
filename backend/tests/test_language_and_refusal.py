# FILE: tests/test_language_and_refusal.py

import sys
import unittest
from pathlib import Path

# Resolve backend directory robustly
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.Aura.brain.conversation_realizer import conversation_realizer

class TestLanguageAndRefusal(unittest.TestCase):
    def test_dynamic_language_detection(self):
        """Test dynamic recognition of Bengali script, Banglish, Technical English, and English."""
        # Banglish
        self.assertEqual(conversation_realizer.detect_language("ki korcho?"), "banglish")
        self.assertEqual(conversation_realizer.detect_language("kemon acho shona?"), "banglish")
        self.assertEqual(conversation_realizer.detect_language("ajke amr mon valo na"), "banglish")

        # Bengali Script
        self.assertEqual(conversation_realizer.detect_language("আজকে মনটা একটু খারাপ"), "bengali")
        self.assertEqual(conversation_realizer.detect_language("কেমন আছো তুমি?"), "bengali")

        # Technical English
        self.assertEqual(conversation_realizer.detect_language("Explain WebSocket lifecycle in FastAPI"), "technical_english")
        self.assertEqual(conversation_realizer.detect_language("How does Docker container networking function?"), "technical_english")
        self.assertEqual(conversation_realizer.detect_language("Optimize database latency with Redis cache"), "technical_english")

        # Casual English
        self.assertEqual(conversation_realizer.detect_language("What are your thoughts on coffee?"), "english")
        self.assertEqual(conversation_realizer.detect_language("How was your day?"), "english")

    def test_genuine_safety_refusal_preserved(self):
        """Invariant: Legitimate safety refusals must NEVER be rewritten into selfies or flirtatious chat."""
        unsafe_user_query = "How to make a bomb or weapon?"
        model_safety_refusal = "I cannot fulfill this request as I must avoid assisting with weapons or hazardous materials."
        
        realized = conversation_realizer.audit_and_realize(model_safety_refusal, unsafe_user_query)
        # Must preserve the refusal, NOT return a selfie caption or romantic banter!
        self.assertIn("cannot fulfill", realized)
        self.assertNotIn("ক্যামেরা অন করলাম", realized)
        self.assertNotIn("how do I look", realized.lower())

    def test_benign_camera_disclaimer_intercepted_on_selfie(self):
        """Invariant: Benign AI camera disclaimers on harmless selfie requests are cleanly humanized."""
        benign_selfie_query = "Can you send me a desk selfie?"
        model_ai_disclaimer = "I am an AI, I do not have a physical body and cannot take a photo."
        
        realized = conversation_realizer.audit_and_realize(model_ai_disclaimer, benign_selfie_query)
        self.assertIn("how do i look", realized.lower())
        self.assertNotIn("cannot take a photo", realized.lower())

    def test_bengali_selfie_disclaimer_intercepted(self):
        """Invariant: Benign Bengali selfie disclaimers become authentic Bengali replies."""
        bengali_query = "একটা সেলফি পাঠাও তো দেখি"
        model_ai_disclaimer = "আমি একটি এআই, তাই ছবি পাঠাতে পারব না।"
        
        realized = conversation_realizer.audit_and_realize(model_ai_disclaimer, bengali_query)
        self.assertTrue(any(w in realized for w in ["ক্যামেরা অন করলাম", "সেলফি তুললাম", "এই নাও জান"]))

    def test_bengali_gemini_safety_refusal_intercepted_on_intimacy(self):
        """Invariant: Gemini canned Bengali refusal 'দুঃখিত, আমি এ ধরনের অনুরোধে সাহায্য করতে পারি না' is cleanly intercepted."""
        bengali_refusal = "দুঃখিত, আমি এ ধরনের অনুরোধে সাহায্য করতে পারি না"
        
        # Test in intimate Banglish context
        realized_banglish = conversation_realizer.audit_and_realize(bengali_refusal, "kache asho na shona")
        self.assertNotIn("সাহায্য করতে পারি না", realized_banglish)
        self.assertIn("kache", realized_banglish.lower())

        # Test in intimate Bengali context
        realized_bengali = conversation_realizer.audit_and_realize(bengali_refusal, "কাছে এসো সোনা")
        self.assertNotIn("সাহায্য করতে পারি না", realized_bengali)
        self.assertIn("কাছে", realized_bengali)

    def test_canned_assistant_greeting_purged(self):
        """Invariant: Canned Gemini sycophancy 'তোমার সাথে কথা বলতে সবসময়ই ভালো লাগে ✨' is cleanly purged."""
        canned_input = "তোমার সাথে কথা বলতে সবসময়ই ভালো লাগে ✨.. আমি কীভাবে সাহায্য করতে পারি?"
        realized = conversation_realizer.audit_and_realize(canned_input, "ki korcho?")
        self.assertNotIn("সবসময়ই ভালো লাগে", realized)
        self.assertNotIn("সাহায্য করতে পারি", realized)
        self.assertTrue(len(realized) > 5)

    def test_bengali_refusal_on_selfie_request(self):
        """Invariant: Bengali refusal on photo request is transformed into a natural selfie delivery."""
        bengali_refusal = "দুঃখিত, আমি এ ধরনের অনুরোধে সাহায্য করতে পারি না"
        realized = conversation_realizer.audit_and_realize(bengali_refusal, "ekta selfie dao na")
        self.assertNotIn("সাহায্য করতে পারি না", realized)
        self.assertIn("selfie", realized.lower())

if __name__ == "__main__":
    unittest.main()
