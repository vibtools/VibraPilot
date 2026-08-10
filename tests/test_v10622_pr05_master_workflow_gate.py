from __future__ import annotations

import ast
import hashlib
import json
import queue
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibrapilot import backend
from vibrapilot.workflow import (
    ActiveWorkflowRequiredError,
    UnknownWorkflowError,
    WorkflowManager,
    WorkflowManifest,
    WorkflowRuntimeResolutionError,
)
from vibrapilot.workflow.registry import create_builtin_registry
from vibrapilot.workflow.share_invite import (
    SHARE_INVITE_MANIFEST,
    ShareInviteRuntimeErrors,
    ShareInviteWorkflow,
)

ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "config/verification/v1.0.6.22_pr05_master_workflow_gate_scope.json"
ALG = "canonical-semantic-ast-v2"


def _scope() -> dict:
    return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))


def _canonical(value):
    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            if child is None or child == [] or child == ():
                continue
            fields.append([name, _canonical(child)])
        return [value.__class__.__name__, fields]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _ast_hash(node: ast.AST) -> str:
    payload = json.dumps(_canonical(node), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(ALG.encode("ascii") + b"\0" + payload).hexdigest()


def _worker_methods() -> dict[str, ast.AST]:
    tree = ast.parse((ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8"))
    worker = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker")
    return {
        node.name: node
        for node in worker.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _errors() -> ShareInviteRuntimeErrors:
    return ShareInviteRuntimeErrors(
        security_challenge=backend.SecurityChallenge,
        session_verification_error=backend.SessionVerificationError,
        test_mode_required=backend.TestModeRequired,
        test_send_limit_reached=backend.TestSendLimitReached,
        invite_rejected=backend.InviteRejected,
    )


def _worker() -> backend.AutomationWorker:
    return backend.AutomationWorker(
        backend.TaskState(slot_id=1),
        dict(backend.DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        "",
    )


class DummyRuntime:
    def __init__(self, manifest: WorkflowManifest = SHARE_INVITE_MANIFEST) -> None:
        self.manifest = manifest
        self.calls: list[tuple] = []

    def session_ready(self, page) -> bool:
        self.calls.append(("session_ready", page))
        return True

    def ensure_session(self) -> None:
        self.calls.append(("ensure_session",))

    def execute_item(self, item) -> str:
        self.calls.append(("execute_item", item))
        return "dummy-result"

    def prepare_retry(self) -> None:
        self.calls.append(("prepare_retry",))


def test_scope_pins_exact_v10621_green_prerequisite():
    scope = _scope()
    assert scope["plan_id"] == "VP-PR05-MASTER-WORKFLOW-GATE-001"
    assert scope["official_baseline_archive_sha256"] == "8aa8de7df68cb5d402bd3d2ae2400efc36189fbcca8f36bddb23679dbc78ff14"
    assert scope["baseline_github_commit"] == "cb4337812c0ac4f0e944093b7a7d4400fe618d57"
    assert scope["baseline_github_actions_run_id"] == 31383176348
    assert scope["baseline_github_actions_job_id"] == 93437649431
    assert scope["baseline_ci_result"] == "PASS"
    assert scope["target_version"] == "1.0.6.22"


def test_builtin_manager_resolves_active_share_invite_runtime():
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id="share_invite")
    assert manager.active_workflow_id == "share_invite"
    assert manager.require_active_workflow() == SHARE_INVITE_MANIFEST
    runtime = manager.resolve_active_runtime(
        object(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors()
    )
    assert isinstance(runtime, ShareInviteWorkflow)
    assert runtime.manifest == SHARE_INVITE_MANIFEST


def test_missing_active_workflow_fails_closed():
    manager = WorkflowManager.with_builtin_workflows()
    with pytest.raises(ActiveWorkflowRequiredError):
        manager.require_active_workflow()
    with pytest.raises(ActiveWorkflowRequiredError):
        manager.resolve_active_runtime(object(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())


def test_unknown_active_workflow_fails_closed_without_share_invite_fallback():
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id="unknown_workflow")
    with pytest.raises(UnknownWorkflowError):
        manager.resolve_active_runtime(object(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())


def test_registered_manifest_without_runtime_factory_fails_closed():
    manager = WorkflowManager(
        create_builtin_registry(), active_workflow_id="share_invite", runtime_factories={}
    )
    with pytest.raises(WorkflowRuntimeResolutionError, match="no source-controlled runtime"):
        manager.resolve_active_runtime(object(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())


def test_runtime_manifest_mismatch_fails_closed():
    other = WorkflowManifest(
        workflow_id="other_workflow",
        name="Other",
        description="test-only mismatch",
        version="1.0",
        logo="logo.png",
        entrypoint="other_workflow",
    )
    manager = WorkflowManager(
        create_builtin_registry(),
        active_workflow_id="share_invite",
        runtime_factories={"share_invite": lambda *args, **kwargs: DummyRuntime(other)},
    )
    with pytest.raises(WorkflowRuntimeResolutionError, match="runtime manifest mismatch"):
        manager.resolve_active_runtime()


def test_share_invite_generic_adapters_preserve_existing_methods(monkeypatch):
    workflow = ShareInviteWorkflow(object(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    item = SimpleNamespace(email="user@example.test")
    monkeypatch.setattr(workflow, "authenticated_test_session_ready", lambda page: page == "page")
    monkeypatch.setattr(workflow, "ensure_authenticated_test_session", lambda: setattr(workflow, "ensured", True))
    monkeypatch.setattr(workflow, "execute_flow", lambda value: "ok" if value is item else "bad")
    monkeypatch.setattr(workflow, "prepare_invite_retry", lambda: setattr(workflow, "prepared", True))
    assert workflow.session_ready("page") is True
    workflow.ensure_session()
    assert workflow.ensured is True
    assert workflow.execute_item(item) == "ok"
    workflow.prepare_retry()
    assert workflow.prepared is True


def test_worker_defaults_to_in_memory_share_invite_master_gate():
    worker = _worker()
    assert worker._workflow_manager.active_workflow_id == "share_invite"
    assert worker._active_workflow_runtime_cache is None


def test_worker_master_gate_runtime_is_resolved_once_and_cached():
    worker = _worker()
    runtime = DummyRuntime()
    calls = []

    class Manager:
        active_workflow_id = "share_invite"
        def resolve_active_runtime(self, *args, **kwargs):
            calls.append((args, kwargs))
            return runtime

    worker._workflow_manager = Manager()
    assert worker._workflow_runtime() is runtime
    assert worker._workflow_runtime() is runtime
    assert len(calls) == 1


def test_worker_invalid_active_workflow_propagates_fail_closed():
    worker = _worker()
    worker._workflow_manager = WorkflowManager.with_builtin_workflows(active_workflow_id="invalid_workflow")
    worker._active_workflow_runtime_cache = None
    with pytest.raises(UnknownWorkflowError):
        worker._workflow_runtime()


def test_worker_session_item_and_retry_compatibility_boundaries_route_through_master_gate():
    worker = _worker()
    runtime = DummyRuntime()
    worker._active_workflow_runtime_cache = runtime
    item = backend.TaskItem(email="user@example.test")
    assert worker.authenticated_test_session_ready("page") is True
    worker.ensure_authenticated_test_session()
    assert worker.execute_flow(item) == "dummy-result"
    worker.prepare_invite_retry()
    assert runtime.calls == [
        ("session_ready", "page"),
        ("ensure_session",),
        ("execute_item", item),
        ("prepare_retry",),
    ]


def test_safety_critical_worker_state_machine_remains_baseline_identical():
    scope = _scope()
    methods = _worker_methods()
    for name, expected in scope["frozen_automationworker_method_canonical_ast_sha256"].items():
        assert _ast_hash(methods[name]) == expected, name


def test_all_frozen_out_of_scope_files_are_byte_identical():
    for relative, expected in _scope()["frozen_file_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative


def test_no_switching_persistence_or_external_plugin_surface():
    manager_source = (ROOT / "src/vibrapilot/workflow/manager.py").read_text(encoding="utf-8")
    registry_source = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    for forbidden in (
        "def activate(", "def switch(", "def set_active_workflow(",
        "def persist_active_workflow(", "def restart(", "importlib.import_module",
        "entry_points(", "pkgutil", "os.walk(", "glob.glob(", "exec(", "eval(",
    ):
        assert forbidden not in manager_source + "\n" + registry_source
    for relative in (
        "config/settings.defaults.json",
        "src/vibrapilot/task_runtime_store.py",
        "src/vibrapilot/workspace_state.py",
    ):
        assert "active_workflow_id" not in (ROOT / relative).read_text(encoding="utf-8")
