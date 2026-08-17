from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from vibrapilot.workflow import (
    ActiveWorkflowRequiredError,
    UnknownWorkflowError,
    WorkflowManager,
    WorkflowManifest,
    WorkflowRegistry,
    WorkflowRuntimeResolutionError,
)

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.22_pr05_master_workflow_gate_scope.json"


MANIFEST = WorkflowManifest(
    workflow_id="synthetic_gate",
    name="Synthetic Gate",
    description="Test-only generic workflow.",
    version="1.0",
    logo="assets/logo.png",
    entrypoint="create_workflow",
)


class DummyRuntime:
    manifest = MANIFEST
    def session_ready(self, page): return True
    def ensure_session(self): return None
    def execute_item(self, item): return "ok"
    def prepare_retry(self): return None


def _manager(active: str | None = None, *, factory=True):
    factories = {MANIFEST.workflow_id: (lambda *a, **k: DummyRuntime())} if factory else {}
    return WorkflowManager(
        WorkflowRegistry([MANIFEST]),
        active_workflow_id=active,
        runtime_factories=factories,
    )


def test_zero_builtin_manager_is_a_valid_empty_catalog():
    manager = WorkflowManager.with_builtin_workflows()
    assert manager.list_workflows() == ()
    assert manager.active_workflow_id is None


def test_generic_manager_resolves_validated_runtime():
    manager = _manager(MANIFEST.workflow_id)
    runtime = manager.resolve_active_runtime(object())
    assert isinstance(runtime, DummyRuntime)
    assert runtime.manifest == MANIFEST


def test_missing_active_workflow_fails_closed():
    manager = _manager()
    with pytest.raises(ActiveWorkflowRequiredError):
        manager.require_active_workflow()
    with pytest.raises(ActiveWorkflowRequiredError):
        manager.resolve_active_runtime()


def test_unknown_active_workflow_fails_closed_without_fallback():
    manager = _manager("unknown_workflow")
    with pytest.raises(UnknownWorkflowError):
        manager.resolve_active_runtime()


def test_missing_runtime_factory_fails_closed():
    manager = _manager(MANIFEST.workflow_id, factory=False)
    with pytest.raises(WorkflowRuntimeResolutionError, match="no validated runtime"):
        manager.resolve_active_runtime()


def test_runtime_manifest_mismatch_fails_closed():
    wrong = WorkflowManifest(
        workflow_id="other", name="Other", description="Other", version="1.0",
        logo="assets/logo.png", entrypoint="create_workflow"
    )
    class WrongRuntime(DummyRuntime):
        manifest = wrong
    manager = WorkflowManager(
        WorkflowRegistry([MANIFEST]), active_workflow_id=MANIFEST.workflow_id,
        runtime_factories={MANIFEST.workflow_id: lambda *a, **k: WrongRuntime()},
    )
    with pytest.raises(WorkflowRuntimeResolutionError, match="manifest mismatch"):
        manager.resolve_active_runtime()


def test_worker_master_gate_has_no_share_invite_fallback_or_type_dependency():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert "active_workflow_id: str | None = None" in source
    assert "active_workflow_id=active_workflow_id" in source
    assert 'active_workflow_id="share_invite"' not in source
    assert "self._workflow_manager.resolve_active_runtime(" in source
    assert "ShareInviteWorkflow" not in source


def test_worker_generic_boundaries_route_through_master_gate():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    for marker in (
        "return self._workflow_runtime().session_ready(page)",
        "self._workflow_runtime().ensure_session()",
        "return self._workflow_runtime().execute_item(item)",
        "self._workflow_runtime().prepare_retry()",
    ):
        assert marker in source


def test_active_workflow_persistence_stays_out_of_settings_task_and_workspace_schemas():
    for relative in (
        "config/settings.defaults.json",
        "src/vibrapilot/task_runtime_store.py",
        "src/vibrapilot/workspace_state.py",
    ):
        assert "active_workflow_id" not in (ROOT / relative).read_text(encoding="utf-8")
    manager_tree = ast.parse((ROOT / "src/vibrapilot/workflow/manager.py").read_text(encoding="utf-8"))
    cls = next(n for n in manager_tree.body if isinstance(n, ast.ClassDef) and n.name == "WorkflowManager")
    methods = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
    assert not methods & {"activate", "switch", "restart", "persist_active_workflow", "set_active_workflow"}


def test_historical_pr05_scope_evidence_remains_intact():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["target_version"] == "1.0.6.22"
    assert scope["baseline_ci_result"] == "PASS"
