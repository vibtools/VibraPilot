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


class FakePage:
    def __init__(self, url: str, *, opener=None, closed=False):
        self.url = url
        self._opener = opener
        self._closed = closed
        self.front = 0

    def is_closed(self):
        return self._closed

    @property
    def opener(self):
        return self._opener

    def bring_to_front(self):
        self.front += 1


def make_worker(target="https://app.example.test/start"):
    return AutomationWorker(
        TaskState(slot_id=21, target_url=target),
        dict(DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        initial_url=target,
    )


def test_startup_prefers_target_origin_then_non_internal_page():
    worker = make_worker()
    blank = FakePage("about:blank")
    other = FakePage("https://other.test/home")
    target = FakePage("https://app.example.test/dashboard")
    assert worker._select_preferred_page([blank, other, target]) is target

    worker.state.target_url = ""
    worker.initial_url = ""
    assert worker._select_preferred_page([blank, other]) is other


def test_new_page_policy_does_not_let_unrelated_tab_steal_processing_page():
    worker = make_worker()
    active = FakePage("https://app.example.test/work")
    worker.active_page = active
    worker.processing_event.set()

    unrelated = FakePage("https://news.example/home")
    assert worker._should_adopt_new_page(unrelated) is False

    popup = FakePage("https://app.example.test/popup", opener=active)
    assert worker._should_adopt_new_page(popup) is True


def test_safe_identity_excludes_query_and_fragment():
    worker = make_worker()
    page = FakePage("https://app.example.test/org/team?token=SECRET#frag")
    identity = worker._safe_page_identity(page, pages=[page])
    assert "SECRET" not in identity
    assert "?" not in identity
    assert "#" not in identity
    assert "host=app.example.test" in identity
    assert "path=/org/team" in identity

def test_idle_new_tab_becomes_adoptable_after_navigation():
    worker = make_worker()
    worker.active_page = FakePage("https://app.example.test/current")
    new_tab = FakePage("about:blank")
    assert worker._should_adopt_new_page(new_tab) is False
    new_tab.url = "https://app.example.test/after-login"
    assert worker._should_adopt_new_page(new_tab) is True
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert 'page.on("framenavigated", frame_navigated_handler)' in source
