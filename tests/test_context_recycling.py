from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ContextRecyclingTest(unittest.TestCase):
    def test_success_and_failed_items_feed_recycle_accounting(self):
        tree = ast.parse((ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8"))
        worker = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker")
        process = next(node for node in worker.body if isinstance(node, ast.FunctionDef) and node.name == "process_batch")
        source = ast.unparse(process)
        self.assertIn('if item.status in {\'success\', \'failed\'}', source)
        self.assertIn('self.maybe_recycle_context()', source)

if __name__ == "__main__":
    unittest.main()
