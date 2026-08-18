from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.power_management import SystemSleepGuard


class FakeBackend:
    def __init__(self):
        self.acquires = 0
        self.releases = 0

    def acquire(self):
        self.acquires += 1
        return True

    def release(self):
        self.releases += 1


def test_sleep_guard_reference_owns_by_task_token():
    backend = FakeBackend()
    guard = SystemSleepGuard(backend=backend)

    assert guard.acquire("task-1") is True
    assert guard.acquire("task-1") is True
    assert guard.acquire("task-2") is True
    assert backend.acquires == 1
    assert guard.owner_count == 2

    guard.release("task-1")
    assert backend.releases == 0
    assert guard.owner_count == 1

    guard.release("task-2")
    assert backend.releases == 1
    assert guard.owner_count == 0


def test_release_all_is_idempotent():
    backend = FakeBackend()
    guard = SystemSleepGuard(backend=backend)
    guard.acquire("a")
    guard.acquire("b")
    guard.release_all()
    guard.release_all()
    assert backend.acquires == 1
    assert backend.releases == 1
    assert guard.owner_count == 0
