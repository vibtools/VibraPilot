from __future__ import annotations

from pathlib import Path
import ast
import queue
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskState

class UiQueueBackpressureTest(unittest.TestCase):
    def test_bounded_queue_and_bounded_drain_contract(self):
        text = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.assertIn("UI_QUEUE_CAPACITY = 4096", text)
        self.assertIn("UI_QUEUE_MAX_EVENTS_PER_TICK = 250", text)
        self.assertIn("queue.Queue(maxsize=UI_QUEUE_CAPACITY)", text)
        self.assertIn("while processed < UI_QUEUE_MAX_EVENTS_PER_TICK", text)


    def test_critical_result_event_applies_backpressure_instead_of_dropping(self):
        events = queue.Queue(maxsize=1)
        events.put(("occupied", {}))
        worker = AutomationWorker(
            TaskState(slot_id=4), dict(DEFAULT_SETTINGS), events,
            threading.Event(), threading.Event(), initial_url=""
        )
        thread = threading.Thread(target=lambda: worker.emit("item", {"status": "success"}))
        thread.start()
        time.sleep(0.05)
        self.assertTrue(thread.is_alive())
        events.get_nowait()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        kind, payload = events.get_nowait()
        self.assertEqual(kind, "item")
        self.assertEqual(payload["slot_id"], 4)

    def test_noncritical_progress_event_drops_when_queue_is_full(self):
        events = queue.Queue(maxsize=1)
        events.put(("occupied", {}))
        worker = AutomationWorker(
            TaskState(slot_id=6), dict(DEFAULT_SETTINGS), events,
            threading.Event(), threading.Event(), initial_url=""
        )
        started = time.monotonic()
        worker.emit("progress", {"progress": 0.5})
        self.assertLess(time.monotonic() - started, 0.2)
        self.assertEqual(events.qsize(), 1)

if __name__ == "__main__":
    unittest.main()
