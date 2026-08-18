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
    def __init__(self, url: str):
        self.url = url

    def is_closed(self):
        return False


def make_worker(target: str = "https://app.example.test/start") -> AutomationWorker:
    return AutomationWorker(
        TaskState(slot_id=41, target_url=target),
        dict(DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        initial_url=target,
    )


def test_default_http_and_https_ports_are_canonicalized_to_browser_origin():
    origin = AutomationWorker._origin_from_url
    assert origin("https://app.example.test/path") == origin(
        "https://app.example.test:443/other"
    )
    assert origin("http://app.example.test/path") == origin(
        "http://app.example.test:80/other"
    )


def test_nondefault_ports_remain_distinct_origins():
    origin = AutomationWorker._origin_from_url
    assert origin("https://app.example.test/path") != origin(
        "https://app.example.test:444/other"
    )
    assert origin("http://app.example.test/path") != origin(
        "http://app.example.test:8080/other"
    )


def test_startup_prefers_equivalent_default_port_target_over_unrelated_last_tab():
    worker = make_worker("https://app.example.test/start")
    target = FakePage("https://app.example.test:443/dashboard")
    unrelated = FakePage("https://other.example.test/home")
    assert worker._select_preferred_page([target, unrelated]) is target


def test_malformed_port_stays_fail_safe_after_canonicalization():
    assert AutomationWorker._origin_from_url(
        "https://app.example.test:notaport/path"
    ) is None
