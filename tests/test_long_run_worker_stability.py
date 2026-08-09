from __future__ import annotations

from pathlib import Path
import queue
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskItem, TaskState


class SinkQueue:
    def put(self, item, timeout=None):
        return None
    def put_nowait(self, item):
        return None


class FakeStore:
    def __init__(self):
        self.items = 0
        self.progress = []
        self.results = {}
        self.completed = []
        self.checkpoints = 0
    def save_item(self, run_id, item_index, item):
        self.items += 1
    def save_progress(self, **kwargs):
        self.progress.append(kwargs)
    def upsert_result(self, run_id, item_index, row):
        self.results[(run_id, item_index)] = dict(row)
    def persist_item_result_progress(self, *, run_id, item_index, item, result_row, **progress):
        self.items += 1
        if result_row is not None:
            self.results[(run_id, item_index)] = dict(result_row)
        self.progress.append(dict(progress, run_id=run_id))
    def mark_completed(self, run_id, status, timestamp):
        self.completed.append((run_id, status))
    def checkpoint(self):
        self.checkpoints += 1


class FastSuccessWorker(AutomationWorker):
    def __init__(self, state, settings, store):
        super().__init__(
            state,
            settings,
            SinkQueue(),
            threading.Event(),
            threading.Event(),
            initial_url="https://example.test/",
            runtime_store=store,
        )
        self.recycle_calls = 0
    def process_item(self, index, item):
        item.status = "success"
        item.attempts = 1
        item.message = "confirmed"
        item.result = "sent"
        self.state.success_count += 1
    def maybe_recycle_context(self):
        self.recycle_calls += 1
    def interruptible_sleep(self, seconds):
        return None


class LongRunWorkerStabilityTest(unittest.TestCase):
    def test_mocked_100k_sequential_run_has_no_count_or_index_drift(self):
        count = 100_000
        state = TaskState(
            slot_id=1,
            target_url="https://example.test/",
            items=[TaskItem(f"u{i}@example.com") for i in range(count)],
            run_id="soak-run",
        )
        settings = dict(DEFAULT_SETTINGS)
        settings.update({"batch_size": 250, "auto_save_interval": 10})
        store = FakeStore()
        worker = FastSuccessWorker(state, settings, store)
        worker.process_batch()
        self.assertEqual(state.current_index, count)
        self.assertEqual(state.success_count, count)
        self.assertEqual(state.failed_count, 0)
        self.assertEqual(state.remaining, 0)
        self.assertEqual(state.status, "Completed")
        self.assertEqual(worker.recycle_calls, count)
        self.assertEqual(len(store.results), count)
        self.assertEqual(store.checkpoints, 400)
        self.assertIn(("soak-run", "Completed"), store.completed)


    def test_auto_save_interval_is_seconds_and_zero_disables_timed_save(self):
        state = TaskState(slot_id=2, items=[TaskItem("a@example.com")], run_id="autosave-run")
        settings = dict(DEFAULT_SETTINGS)
        settings["auto_save_interval"] = 10
        store = FakeStore()
        worker = FastSuccessWorker(state, settings, store)
        worker.last_autosave_at = time.monotonic()
        worker._save_runtime_progress()
        self.assertEqual(len(store.progress), 0)
        worker.last_autosave_at -= 10.1
        worker._save_runtime_progress()
        self.assertEqual(len(store.progress), 1)

        disabled = dict(settings)
        disabled["auto_save_interval"] = 0
        store2 = FakeStore()
        worker2 = FastSuccessWorker(state, disabled, store2)
        worker2.last_autosave_at -= 100
        worker2._save_runtime_progress()
        self.assertEqual(len(store2.progress), 0)
        worker2._save_runtime_progress(force=True)
        self.assertEqual(len(store2.progress), 1)

    def test_worker_stopped_event_is_set_after_cleanup_path(self):
        state = TaskState(slot_id=9)
        worker = AutomationWorker(
            state,
            dict(DEFAULT_SETTINGS),
            queue.Queue(),
            threading.Event(),
            threading.Event(),
            initial_url="",
        )
        worker.launch_browser = lambda: (_ for _ in ()).throw(RuntimeError("synthetic launch failure"))
        worker.start()
        worker.join(timeout=3)
        self.assertFalse(worker.is_alive())
        self.assertTrue(worker.stopped_event.is_set())


if __name__ == "__main__":
    unittest.main()
