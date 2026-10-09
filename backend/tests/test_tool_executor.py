# FILE: tests/test_tool_executor.py

import os
import sys
import unittest
from pathlib import Path

# Resolve backend directory
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.Aura.tools.tool_executor import tool_registry, ToolRiskTier

class TestToolExecutionFramework(unittest.TestCase):
    def test_safe_calculator_execution(self):
        res = tool_registry.execute("calculator", {"expression": "25 * 4 + 10"})
        self.assertTrue(res.success)
        self.assertEqual(res.result, "110")
        self.assertEqual(res.risk_tier, ToolRiskTier.LOW)

    def test_safe_calculator_blocks_malicious_code(self):
        # Should sanitize and avoid running malicious code
        res = tool_registry.execute("calculator", {"expression": "__import__('os').system('ls')"})
        self.assertNotIn("system", str(res.result))

    def test_get_current_time(self):
        res = tool_registry.execute("get_time", {})
        self.assertTrue(res.success)
        self.assertIn("Current time is", res.result)

    def test_unknown_tool_graceful_handling(self):
        res = tool_registry.execute("non_existent_tool", {})
        self.assertFalse(res.success)
        self.assertIn("not found", res.error)

if __name__ == "__main__":
    unittest.main()

