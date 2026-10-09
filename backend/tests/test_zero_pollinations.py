# FILE: tests/test_zero_pollinations.py

import os
import sys
import unittest
from pathlib import Path

class TestZeroPollinations(unittest.TestCase):
    def test_no_pollinations_in_backend_code(self):
        """Invariant: Zero occurrences of pollinations in backend python code."""
        current = Path(__file__).resolve()
        root = current.parent if current.parent.name == "backend" else current.parent.parent
        if (root / "backend").exists():
            root = root / "backend"
        violations = []

        for p in root.rglob("*.py"):
            # Skip virtual environments, test files, or cache dirs
            if "venv" in str(p) or "__pycache__" in str(p) or "test_" in p.name:
                continue
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "pollinations" in content.lower():
                    violations.append(str(p))

        self.assertEqual(
            violations,
            [],
            f"FATAL: Pollinations was found in the following files: {violations}"
        )

if __name__ == "__main__":
    unittest.main()

