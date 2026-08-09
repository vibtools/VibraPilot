from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskItem, TaskState
from vibrapilot.task_runtime_store import TaskRuntimeStore
import queue
import threading

@dataclass
class Item:
    email: str
    name: str = ""
    status: str = "pending"
    attempts: int = 0
    message: str = ""
    result: str = ""

class TaskRecoveryTest(unittest.TestCase):
    def test_completed_run_is_not_offered_for_recovery(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskRuntimeStore(Path(temp) / "store.sqlite3")
            run_id = store.start_run(
                slot_id=1,target_url="https://example.test",source_file="x.txt",
                source_fingerprint="abc",items=[Item("a@example.com")],created_at="t0"
            )
            store.mark_completed(run_id, "Completed", "t1")
            self.assertFalse(any(row["run_id"] == run_id for row in store.recoverable_runs()))

    def test_stopped_run_retains_items_and_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskRuntimeStore(Path(temp) / "store.sqlite3")
            run_id = store.start_run(
                slot_id=3,target_url="https://example.test",source_file="x.txt",
                source_fingerprint="abc",items=[Item("a@example.com"),Item("b@example.com")],created_at="t0"
            )
            store.save_progress(
                run_id=run_id,current_index=1,total=2,success_count=1,failed_count=0,
                send_limit_used=1,task_status="Stopped",manual_review_required=False,
                updated_at="t1",target_url="https://example.test"
            )
            run = store.load_run(run_id)
            self.assertEqual(run["current_index"], 1)
            self.assertEqual(len(run["items"]), 2)
            self.assertTrue(any(row["run_id"] == run_id for row in store.recoverable_runs()))


    def test_send_click_attempt_is_durable_manual_review_before_click_returns(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskRuntimeStore(Path(temp) / "store.sqlite3")
            state = TaskState(slot_id=5, items=[TaskItem("a@example.com")])
            run_id = store.start_run(
                slot_id=5, target_url="https://example.test", source_file="x.txt",
                source_fingerprint="abc", items=state.items, created_at="t0"
            )
            state.run_id = run_id
            worker = AutomationWorker(
                state, dict(DEFAULT_SETTINGS), queue.Queue(), threading.Event(),
                threading.Event(), initial_url="https://example.test", runtime_store=store
            )
            worker._register_send_click_attempt()
            recovered = store.load_run(run_id)
            self.assertEqual(recovered["send_limit_used"], 1)
            self.assertEqual(recovered["manual_review_required"], 1)
            self.assertEqual(recovered["current_index"], 0)
            self.assertEqual(recovered["items"][0]["status"], "interrupted")
            self.assertIn("Manual review", recovered["items"][0]["message"])


    def test_corrupt_runtime_store_is_quarantined_without_app_startup_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "store.sqlite3"
            path.write_bytes(b"not-a-sqlite-database")
            store = TaskRuntimeStore(path)
            self.assertTrue(path.is_file())
            self.assertIn("quarantined", store.recovery_warning)
            self.assertEqual(store.recoverable_runs(), [])
            backups = list(Path(temp).glob("store.sqlite3.corrupt-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), b"not-a-sqlite-database")

    def test_unsupported_run_schema_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskRuntimeStore(Path(temp) / "store.sqlite3")
            run_id = store.start_run(
                slot_id=7, target_url="https://example.test", source_file="x.txt",
                source_fingerprint="abc", items=[Item("a@example.com")], created_at="t0"
            )
            with store._connection() as conn:
                conn.execute("UPDATE runs SET schema_version=0 WHERE run_id=?", (run_id,))
            self.assertIsNone(store.load_run(run_id))
            self.assertFalse(any(row["run_id"] == run_id for row in store.recoverable_runs()))

if __name__ == "__main__":
    unittest.main()
