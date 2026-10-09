# FILE: tests/test_telegram_single_brain.py

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Resolve backend directory robustly
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.unified_state import UniversalMessage
from app.services.visual_engine import AssetBoundaryViolationError

class TestTelegramSingleBrain(unittest.TestCase):
    def test_no_legacy_brain_imports_in_telegram_adapter(self):
        """Invariant: Telegram adapter must not import legacy separate brains."""
        adapter_path = backend_dir / "app" / "integrations" / "telegram_adapter.py"
        with open(adapter_path, "r", encoding="utf-8") as f:
            code = f.read()

        forbidden_imports = [
            "generate_candidate_reply",
            "naturalize_and_audit",
            "realize_conversational_response",
            "build_system_prompt"
        ]
        for term in forbidden_imports:
            self.assertNotIn(term, code, f"Forbidden legacy import '{term}' found in telegram_adapter.py")

        self.assertIn("from app.Aura.brain.cognitive_pipeline import cognitive_pipeline", code)
        self.assertIn("validate_deliverable_asset", code)

    def test_telegram_photo_blocks_reference_leak(self):
        """Invariant: send_telegram_photo must raise AssetBoundaryViolationError on reference paths."""
        import asyncio
        from app.integrations.telegram_adapter import send_telegram_photo

        mock_client = AsyncMock()
        # Even if someone accidentally passed a reference path, it must be intercepted
        with self.assertRaises(AssetBoundaryViolationError):
            asyncio.run(send_telegram_photo(mock_client, 123456, "/static/references/Aura Collage.png"))

if __name__ == "__main__":
    unittest.main()

