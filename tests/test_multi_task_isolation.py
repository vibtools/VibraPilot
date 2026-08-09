from __future__ import annotations

from pathlib import Path
import ast
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import TaskItem, TaskState


class MultiTaskIsolationTest(unittest.TestCase):
    def test_task_states_do_not_share_recipient_lists_or_run_identity(self):
        a = TaskState(slot_id=1, items=[TaskItem("a@example.com")], run_id="run-a")
        b = TaskState(slot_id=2, items=[TaskItem("b@example.com")], run_id="run-b")
        a.items[0].status = "success"
        a.current_index = 1
        a.success_count = 1
        self.assertEqual(b.items[0].status, "pending")
        self.assertEqual(b.current_index, 0)
        self.assertEqual(b.success_count, 0)
        self.assertNotEqual(a.run_id, b.run_id)
        self.assertIsNot(a.items, b.items)



    def test_ui_enforces_concurrent_worker_and_shared_profile_guards(self):
        tree = ast.parse((ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8"))
        main = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
        can_open = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "can_open_task_browser")
        claim = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "_persistent_profile_claim")
        can_source = ast.unparse(can_open)
        claim_source = ast.unparse(claim)
        self.assertIn("max_concurrent_tasks", can_source)
        self.assertIn("len(active) >= limit", can_source)
        self.assertIn("Another running task already owns the same persistent browser profile", can_source)
        self.assertIn("resolve_persistent_user_data_dir", claim_source)
        self.assertIn("persist_profile_between_runs", claim_source)

if __name__ == "__main__":
    unittest.main()
