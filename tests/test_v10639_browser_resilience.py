from __future__ import annotations

import queue
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskState


def make_worker():
    return AutomationWorker(
        TaskState(slot_id=31),
        dict(DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        initial_url="",
    )


def test_auto_restart_is_only_safe_when_not_processing_or_manual_review():
    worker = make_worker()
    assert worker._browser_restart_is_safe() is True
    worker.processing_event.set()
    assert worker._browser_restart_is_safe() is False
    worker.processing_event.clear()
    worker.state.manual_review_required = True
    assert worker._browser_restart_is_safe() is False


def test_default_crash_restart_policy_remains_off():
    assert DEFAULT_SETTINGS["auto_restart_browser_on_crash"] is False
