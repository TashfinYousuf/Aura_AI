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
        self.assertIn("ক্যামেরা অন করলাম", realized)

    def test_therapy_talk_stripped(self):
        """Invariant: Canned therapy clichés are cleanly eliminated."""
        raw_text = "Take a deep breath. As an AI language model, I am here to assist you. I hear you!"
        realized = conversation_realizer.audit_and_realize(raw_text, "I'm stressed")
        self.assertNotIn("take a deep breath", realized.lower())
        self.assertNotIn("as an ai language model", realized.lower())
        self.assertNotIn("i am here to assist you", realized.lower())

if __name__ == "__main__":
    unittest.main()
