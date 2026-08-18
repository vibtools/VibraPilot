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
from vibrapilot.workflow.contracts import WorkflowManifest
from vibrapilot.workflow.manager import WorkflowManager
from vibrapilot.workflow.registry import WorkflowRegistry
from vibrapilot.workflow.schemas import WorkflowTaskSchema


class Runtime:
    def __init__(self, host):
        self.host = host
        self.manifest = MANIFEST
        self.ensure_calls = 0
        self.session_calls = 0

    def session_ready(self, page):
        self.session_calls += 1
        return True

    def ensure_session(self):
        self.ensure_calls += 1

    def execute_item(self, item):
        return "ok"

    def prepare_retry(self):
        return None


MANIFEST = WorkflowManifest(
    workflow_id="session_fixture",
    name="Session Fixture",
    description="Session policy test workflow.",
    version="1.0.0",
    logo="assets/logo.png",
    entrypoint="create_workflow",
)


def make_worker(*, requires_session: bool) -> AutomationWorker:
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
        TaskState(slot_id=11),
        dict(DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        initial_url="https://example.test/",
        active_workflow_id=MANIFEST.workflow_id,
        workflow_manager=manager,
    )


def test_sessionless_contract_skips_core_probe_and_prestart_ensure():
    worker = make_worker(requires_session=False)
    assert worker.workflow_requires_session() is False
    worker.browser_ready_event.set()
    worker.state.status = "Ready"
    worker.workflow_session_ready = lambda page: (_ for _ in ()).throw(AssertionError("must not probe"))
    assert worker.refresh_login_verification(force_emit=True) is False
    assert worker.state.status == "Ready"
    assert worker.login_verified_event.is_set() is False

    worker.ensure_workflow_session_if_required()
    assert worker._active_workflow_runtime_cache is None


def test_session_required_contract_preserves_probe_and_ensure():
    worker = make_worker(requires_session=True)
    assert worker.workflow_requires_session() is True
    worker.browser_ready_event.set()
    assert worker.refresh_login_verification(force_emit=True) is True
    assert worker.login_verified_event.is_set() is True
    runtime = worker._active_workflow_runtime_cache
    assert runtime is not None
    assert runtime.session_calls == 1

    worker.ensure_workflow_session_if_required()
    assert runtime.ensure_calls == 1
