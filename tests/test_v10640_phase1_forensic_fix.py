from __future__ import annotations

import queue
import threading
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import vibrapilot.backend as backend
from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskItem, TaskState
from vibrapilot.workflow.contracts import WorkflowManifest
from vibrapilot.workflow.manager import WorkflowManager
from vibrapilot.workflow.registry import WorkflowRegistry
from vibrapilot.workflow.schemas import WorkflowTaskSchema


MANIFEST = WorkflowManifest(
    workflow_id="v10640_fixture",
    name="v1.0.6.40 fixture",
    description="Phase 1 forensic fix fixture",
    version="1.0.0",
    logo="assets/logo.png",
    entrypoint="create_workflow",
)


class Runtime:
    def __init__(self, host):
        self.host = host
        self.manifest = MANIFEST
        self.session_calls = 0

    def session_ready(self, page):
        self.session_calls += 1
        return True

    def ensure_session(self):
        return None

    def execute_item(self, item):
        return "ok"

    def prepare_retry(self):
        return None


class FakeGuard:
    def __init__(self):
        self.acquired = []
        self.released = []

    def acquire(self, owner):
        self.acquired.append(owner)
        return True

    def release(self, owner):
        self.released.append(owner)


def make_worker(*, requires_session=True):
    manager = WorkflowManager(
        WorkflowRegistry((MANIFEST,)),
        active_workflow_id=MANIFEST.workflow_id,
        runtime_factories={MANIFEST.workflow_id: lambda host, **kwargs: Runtime(host)},
        task_schemas={
            MANIFEST.workflow_id: WorkflowTaskSchema(
                workflow_id=MANIFEST.workflow_id,
                title="Task",
                requires_session=requires_session,
            )
        },
    )
    return AutomationWorker(
        TaskState(slot_id=40),
        dict(DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        initial_url="https://example.test/",
        active_workflow_id=MANIFEST.workflow_id,
        workflow_manager=manager,
    )


def test_power_guard_is_released_if_batch_setup_fails(monkeypatch):
    worker = make_worker(requires_session=False)
    guard = FakeGuard()
    monkeypatch.setattr(backend, "SYSTEM_SLEEP_GUARD", guard)
    emitted = {"count": 0}

    def emit_once_then_succeed(*args, **kwargs):
        emitted["count"] += 1
        if emitted["count"] == 1:
            raise RuntimeError("setup boom")

    monkeypatch.setattr(worker, "emit", emit_once_then_succeed)
    monkeypatch.setattr(worker, "save_failed", lambda: None)
    monkeypatch.setattr(worker, "_save_runtime_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "emit_progress", lambda *args, **kwargs: None)

    worker.process_batch()

    assert worker.state.status == "Failed"
    assert guard.acquired == [worker._power_guard_owner]
    assert guard.released == [worker._power_guard_owner]
    assert worker.processing_event.is_set() is False


def test_force_reprobe_can_run_during_processing_for_recycle():
    worker = make_worker(requires_session=True)
    worker.browser_ready_event.set()
    worker.processing_event.set()
    worker.active_page = object()

    assert worker.refresh_login_verification(force_emit=True, allow_while_processing=True) is True
    runtime = worker._active_workflow_runtime_cache
    assert runtime is not None
    assert runtime.session_calls == 1
    assert worker.login_verified_event.is_set() is True


def test_nonpersistent_and_persistent_recycle_use_forced_reprobe_contract():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert source.count("allow_while_processing=True") >= 2


def test_malformed_http_port_is_fail_safe_for_page_selection():
    worker = make_worker(requires_session=False)
    assert worker._origin_from_url("https://example.test:notaport/path") is None


def test_normal_login_poll_still_suppresses_probe_while_processing():
    worker = make_worker(requires_session=True)
    worker.browser_ready_event.set()
    worker.processing_event.set()
    worker.active_page = object()

    assert worker.refresh_login_verification(force_emit=True) is False
    assert worker._active_workflow_runtime_cache is None


def test_recycle_contract_blocks_next_item_if_required_session_reprobe_fails():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert "if recycle_session_ready is False:" in source
    assert "session_blocked = True" in source


def test_dashboard_uses_login_verification_label_not_verified_not_required_phrase():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert '("Login Verified", "Login Verification")' in source


def test_power_guard_release_precedes_fallible_finalization_work(monkeypatch):
    worker = make_worker(requires_session=False)
    guard = FakeGuard()
    monkeypatch.setattr(backend, "SYSTEM_SLEEP_GUARD", guard)
    monkeypatch.setattr(worker, "emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "emit_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "_save_runtime_progress", lambda *args, **kwargs: None)

    def fail_final_save():
        raise RuntimeError("finalization boom")

    monkeypatch.setattr(worker, "save_failed", fail_final_save)

    try:
        worker.process_batch()
    except RuntimeError as exc:
        assert str(exc) == "finalization boom"
    else:
        raise AssertionError("expected finalization failure")

    assert guard.acquired == [worker._power_guard_owner]
    assert guard.released == [worker._power_guard_owner]
    assert worker.processing_event.is_set() is False


def test_failed_required_session_reprobe_stops_before_next_item(monkeypatch):
    worker = make_worker(requires_session=True)
    worker.state.items = [TaskItem("one@example.test"), TaskItem("two@example.test")]
    worker.state.run_id = "closure-run"
    processed = []

    def succeed(index, item):
        processed.append(index)
        item.status = "success"
        item.attempts = 1
        item.message = "confirmed"
        item.result = "ok"
        worker.state.success_count += 1

    monkeypatch.setattr(worker, "process_item", succeed)
    monkeypatch.setattr(worker, "maybe_recycle_context", lambda: False)
    monkeypatch.setattr(worker, "emit", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "emit_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "_save_runtime_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "_save_runtime_item", lambda *args, **kwargs: None)
    monkeypatch.setattr(worker, "save_unprocessed", lambda: None)
    monkeypatch.setattr(worker, "save_failed", lambda: None)
    monkeypatch.setattr(worker, "interruptible_sleep", lambda *args, **kwargs: None)

    worker.process_batch()

    assert processed == [0]
    assert worker.state.current_index == 1
    assert worker.state.status == "Blocked"
