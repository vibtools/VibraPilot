from __future__ import annotations

import ast
import hashlib
import json
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
from vibrapilot.workflow.share_invite import SHARE_INVITE_MANIFEST, ShareInviteRuntimeErrors, ShareInviteWorkflow

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.22_pr05_master_workflow_gate_scope.json"


def _errors():
    class SecurityChallenge(Exception): pass
    class SessionVerificationError(Exception): pass
    class TestModeRequired(Exception): pass
    class TestSendLimitReached(Exception): pass
    class InviteRejected(Exception): pass
    return ShareInviteRuntimeErrors(
        security_challenge=SecurityChallenge,
        session_verification_error=SessionVerificationError,
        test_mode_required=TestModeRequired,
        test_send_limit_reached=TestSendLimitReached,
        invite_rejected=InviteRejected,
    )


def _host():
    return SimpleNamespace(settings={}, state=SimpleNamespace(target_url="https://example.test"))


def test_builtin_manager_resolves_current_share_invite_runtime():
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id="share_invite")
    runtime = manager.resolve_active_runtime(_host(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    assert isinstance(runtime, ShareInviteWorkflow)
    assert runtime.manifest == SHARE_INVITE_MANIFEST
    assert manager.active_workflow_id == "share_invite"


def test_missing_active_workflow_fails_closed():
    manager = WorkflowManager.with_builtin_workflows()
    with pytest.raises(ActiveWorkflowRequiredError):
        manager.require_active_workflow()
    with pytest.raises(ActiveWorkflowRequiredError):
        manager.resolve_active_runtime(_host(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())


def test_unknown_active_workflow_fails_closed_without_fallback():
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id="unknown_workflow")
    with pytest.raises(UnknownWorkflowError):
        manager.resolve_active_runtime(_host(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())


def test_missing_runtime_factory_fails_closed():
    manager = WorkflowManager(create_builtin_registry(), active_workflow_id="share_invite", runtime_factories={})
    with pytest.raises(WorkflowRuntimeResolutionError):
        manager.resolve_active_runtime(_host(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors())


def test_runtime_manifest_mismatch_fails_closed():
    wrong_manifest = WorkflowManifest(
        workflow_id="other", name="Other", description="Other", version="1.0", logo="logo.png", entrypoint="other"
    )
    class WrongRuntime:
        manifest = wrong_manifest
        def session_ready(self, page): return True
        def ensure_session(self): return None
        def execute_item(self, item): return "x"
        def prepare_retry(self): return None
    manager = WorkflowManager(
        create_builtin_registry(), active_workflow_id="share_invite", runtime_factories={"share_invite": lambda *a, **k: WrongRuntime()}
    )
    with pytest.raises(WorkflowRuntimeResolutionError):
        manager.resolve_active_runtime()


def test_share_invite_generic_adapters_delegate_exact_existing_methods(monkeypatch):
    workflow = object.__new__(ShareInviteWorkflow)
    calls = []
    monkeypatch.setattr(workflow, "authenticated_test_session_ready", lambda page: calls.append(("ready", page)) or True)
    monkeypatch.setattr(workflow, "ensure_authenticated_test_session", lambda: calls.append(("ensure", None)))
    monkeypatch.setattr(workflow, "execute_flow", lambda item: calls.append(("execute", item)) or "ok")
    monkeypatch.setattr(workflow, "prepare_invite_retry", lambda: calls.append(("retry", None)))
    page = object(); item = object()
    assert workflow.session_ready(page) is True
    workflow.ensure_session()
    assert workflow.execute_item(item) == "ok"
    workflow.prepare_retry()
    assert calls == [("ready", page), ("ensure", None), ("execute", item), ("retry", None)]


def test_worker_master_gate_accepts_application_owned_active_workflow_identity():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert "active_workflow_id: str | None = None" in source
    assert "active_workflow_id=active_workflow_id" in source
    assert 'active_workflow_id="share_invite"' not in source
    assert "self._workflow_manager.resolve_active_runtime(" in source
    assert "self._active_workflow_runtime_cache" in source


def test_worker_compatibility_boundaries_route_through_master_gate():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    for marker in (
        "return self.workflow_session_ready(page)",
        "self.ensure_workflow_session()",
        "return self.execute_workflow_item(item)",
        "self.prepare_workflow_retry()",
    ):
        assert marker in source


def test_pr06_persistence_does_not_leak_into_pr05_settings_task_or_workspace_schemas():
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
    state_source = (ROOT / "src/vibrapilot/workflow/state.py").read_text(encoding="utf-8")
    assert '"active_workflow_id"' in state_source
    assert 'workflow_state.json' in (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")


def test_no_external_plugin_or_dynamic_manifest_import_surface():
    text = "\n".join((ROOT / p).read_text(encoding="utf-8") for p in (
        "src/vibrapilot/workflow/registry.py",
        "src/vibrapilot/workflow/manager.py",
        "src/vibrapilot/workflow/contracts.py",
    ))
    for forbidden in ("importlib.import_module", "pkgutil", "entry_points(", "os.walk(", "glob.glob(", "exec(", "eval("):
        assert forbidden not in text


def test_scope_contract_matches_official_baseline_and_phase_boundaries():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["official_baseline_archive_sha256"] == "8aa8de7df68cb5d402bd3d2ae2400efc36189fbcca8f36bddb23679dbc78ff14"
    assert scope["baseline_github_commit"] == "cb4337812c0ac4f0e944093b7a7d4400fe618d57"
    assert scope["baseline_github_actions_run_id"] == 31383176348
    assert scope["baseline_ci_result"] == "PASS"
    assert scope["target_version"] == "1.0.6.22"
    assert scope["initial_active_workflow_id"] == "share_invite"
    for key in ("no_workflow_switching", "no_active_workflow_persistence", "no_new_ui", "no_settings_change", "no_database_schema_change", "no_workspace_schema_change", "no_report_schema_change", "no_browser_change", "no_dependency_change", "no_licensing_change", "captcha_out_of_scope", "external_plugin_loading_prohibited", "manifest_controlled_dynamic_import_prohibited"):
        assert scope[key] is True
