from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from vibrapilot.workflow import (
    WorkflowRecoveryBlockedError,
    WorkflowRecoveryError,
    builtin_workflow_manifests,
    builtin_workflow_runtime_factories,
)
from vibrapilot.workflow.input_state import WorkflowInputStateStore

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src/vibrapilot/qt_app.py"

FROZEN = {
    "src/vibrapilot/backend.py": "5bc5393a92688110e941dc3f50454954de84156fe819261116d2598ffb44a089",
    "src/vibrapilot/workflow/manager.py": "2cc8818eb0f450b6759d5eb7731c00fb3f6cc0ae8369d9fd35782f7fb3816f38",
    "src/vibrapilot/workflow/registry.py": "347665e84d61f9d3012d8930ed70fc3679e13789bfac05868246b7f2706dc6bd",
    "src/vibrapilot/workflow/share_invite/workflow.py": "72010397d5b091cb1a01c47e3e63a5c4b88b49a90c2b370ea3e42f2bc8f122f5",
    "src/vibrapilot/workflow_inputs.py": "1359b52e3afdf3b42155e2c0eba9c52f4c708ebe4e8c5ccde3398e4c60f99810",
    "src/vibrapilot/task_runtime_store.py": "b4b581c936479a6a3f334170c033bae53f1d216e562cc1aff8b3e54e728dcf26",
    "src/vibrapilot/workspace_state.py": "7b4af52a304b449504ed1a8b7333ed4738fac08a49cf431acb60e57936219ccd",
    "src/vibrapilot/data_io.py": "ac8adddec1cfc2ba6784562c7f85e18ceb4da6d7906edac3296f79ed48af3c31",
    "src/vibrapilot/browser_capabilities.py": "8f256cbde7c1674c297547d0b2bf91a8a5641d4d28598833428ada828b76d4df",
    "src/vibrapilot/browser_diagnostics.py": "b7024e40858cca56e03de574c3c0331f3d6f39cb7ee057eeb713d62c9f465e5b",
    "src/vibrapilot/licensing_v2.py": "36435d05593785b7ec02310dcf2d031342524e95d5be6212591a09277699a91b",
    "config/settings.defaults.json": "64c0377a5a84167bdd480b8302d3ca7ac7c9b0db89d56df0d118bf5566444b76",
    "requirements.txt": "92890827d0d19fe07168cf801d15c96cf48b846813d7f687a04531e40ed2b083",
    "requirements-build.txt": "39d98aacb5781de72933397e6c431b83a4b62aa1177798600db1907c8def53eb",
    ".github/workflows/ci.yml": "a722955f9860315f77abdeb8b75cd1bfc269db24e8d46d437dd678917ba258a3",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _main_window_methods() -> dict[str, ast.FunctionDef]:
    tree = ast.parse(QT_PATH.read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    return {
        node.name: node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _method_source(name: str) -> str:
    methods = _main_window_methods()
    return ast.get_source_segment(QT_PATH.read_text(encoding="utf-8"), methods[name]) or ""


def test_recovery_errors_are_distinct_framework_errors():
    assert issubclass(WorkflowRecoveryBlockedError, WorkflowRecoveryError)
    contracts = (ROOT / "src/vibrapilot/workflow/contracts.py").read_text(encoding="utf-8")
    assert "class WorkflowRecoveryError(WorkflowError):" in contracts
    assert "class WorkflowRecoveryBlockedError(WorkflowRecoveryError):" in contracts


def test_production_registry_remains_share_invite_only_with_one_factory():
    manifests = builtin_workflow_manifests()
    factories = builtin_workflow_runtime_factories()
    assert [manifest.workflow_id for manifest in manifests] == ["share_invite"]
    assert set(factories) == {"share_invite"}


def test_approved_frozen_runtime_surfaces_remain_byte_identical():
    scope_paths = (
        ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json",
        ROOT / "config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json",
    )
    current_authorized: set[str] = set()
    for scope_path in scope_paths:
        scope = json.loads(scope_path.read_text(encoding="utf-8")) if scope_path.is_file() else {}
        current_authorized.update(scope.get("allowed_production_source_changes", []))
        current_authorized.update(scope.get("authorized_nonproduction_files", []))
    for rel, expected in FROZEN.items():
        if rel in current_authorized:
            continue
        assert _sha(ROOT / rel) == expected, rel


def test_active_runtime_factory_is_preflighted_before_worker_creation():
    can_open = _method_source("can_open_task_browser")
    open_browser = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert "runtime_error = self._refresh_workflow_runtime_error()" in can_open
    assert "Browser creation is blocked before worker startup" in can_open
    task_method = ast.get_source_segment(
        open_browser,
        next(
            node
            for node in ast.walk(ast.parse(open_browser))
            if isinstance(node, ast.FunctionDef) and node.name == "open_browser"
        ),
    ) or ""
    assert task_method.index("self.app.can_open_task_browser(self)") < task_method.index("AutomationWorker(")


def test_runtime_error_blocks_browser_but_is_not_a_switch_away_blocker():
    can_open = _method_source("can_open_task_browser")
    switch_block = _method_source("_workflow_switch_block_reason")
    switch = _method_source("request_workflow_switch")
    assert "self.workflow_runtime_error" in can_open or "_refresh_workflow_runtime_error" in can_open
    assert "workflow_runtime_error" not in switch_block
    assert "require_runtime_factory(target)" in switch


def test_unresolved_recovery_hard_blocks_browser_and_switching():
    can_open = _method_source("can_open_task_browser")
    switch_block = _method_source("_workflow_switch_block_reason")
    recovery_block = _method_source("_workflow_recovery_block_reason")
    assert "self.workflow_recovery_error" in can_open
    assert "self.workflow_recovery_error" in switch_block
    assert "WorkflowSwitch transaction is still present" in recovery_block
    assert "WorkflowRecovery transaction is still present" in recovery_block


def test_state_recovery_uses_exact_pr09_clear_scope_and_preserves_input_store():
    source = QT_PATH.read_text(encoding="utf-8")
    paths = _method_source("_workflow_switch_paths")
    recover = _method_source("request_workflow_state_recovery")
    assert "TASK_RUNTIME_DB" in paths
    assert '"-wal"' in paths and '"-shm"' in paths
    assert "APP_STATE_FILE" in paths and "SETTINGS_FILE" in paths
    assert 'glob("slot_*_checkpoint.json")' in paths
    assert "workflow_inputs.json" not in paths
    assert "WorkflowRecoveryTransaction(" in recover
    assert "self._clear_workflow_scoped_state(workspace_snapshot)" in recover
    assert "self.workflow_state_store.recover_active_workflow(target)" in recover
    assert "transaction.rollback()" in recover


def test_state_recovery_requires_target_manifest_runtime_and_input_schema():
    recover = _method_source("request_workflow_state_recovery")
    assert "self.workflow_catalog.require_workflow(target)" in recover
    assert "self.workflow_catalog.require_runtime_factory(target)" in recover
    current_scope = ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json"
    if current_scope.is_file():
        assert "self.workflow_catalog.input_schema(target)" in recover
        assert "self.workflow_catalog.settings_schema(target)" in recover
        assert "self.workflow_catalog.task_schema(target)" in recover
    else:
        assert "workflow_input_schema_for(target)" in recover
    assert "_confirm_workflow_state_recovery(target)" in recover


def test_workflows_page_exposes_recover_only_when_state_unavailable():
    card = _method_source("_workflow_card")
    refresh = _method_source("refresh_workflow_showcase")
    assert 'button(f"Recover as {manifest.name}"' in card
    assert "not state_available" in card
    assert "runtime_available" in card and "schema_available" in card
    assert "Workflow State Recovery Required" in refresh
    assert "Manual repair is required" in refresh


def test_input_recovery_quarantines_corrupt_state_and_uses_defaults_not_legacy(tmp_path: Path):
    path = tmp_path / "workflow_inputs.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 999,
                "workflows": {
                    "share_invite": {
                        "values": {
                            "default_full_name": "must-not-survive",
                            "default_number": "legacy-like-value",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    store = WorkflowInputStateStore(path)
    recovered, quarantine = store.recover_workflow_defaults("share_invite")
    assert quarantine is not None and quarantine.is_file()
    values = store.values_for("share_invite", state=recovered)
    assert values == {
        "default_full_name": "",
        "default_number": "",
        "fallback_name": "",
        "update_click_count": "",
    }
    assert "must-not-survive" in quarantine.read_text(encoding="utf-8")


def test_input_recovery_rollback_restores_original_corrupt_bytes(tmp_path: Path):
    path = tmp_path / "workflow_inputs.json"
    original = b"{broken-input-state"
    path.write_bytes(original)
    store = WorkflowInputStateStore(path)
    _, quarantine = store.recover_workflow_defaults("share_invite")
    assert path.is_file() and quarantine is not None
    store.rollback_recovery(quarantine)
    assert path.read_bytes() == original
    assert not quarantine.exists()


def test_input_recovery_ui_is_explicit_and_live_worker_blocked():
    make_page = _method_source("make_workflow_inputs_page")
    refresh = _method_source("refresh_workflow_input_widgets")
    blocker = _method_source("_workflow_input_recovery_block_reason")
    recover = _method_source("recover_workflow_inputs")
    assert 'button("Recover Workflow Inputs"' in make_page
    assert "workflow_input_recover_button.setVisible(True)" in refresh
    assert "task.worker and task.worker.is_alive()" in blocker
    assert "recover_workflow_defaults" in recover
    current_scope = ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json"
    if current_scope.is_file():
        assert "Workflow Input" in recover
    else:
        assert "Legacy Share Invite" in recover
    assert "rollback_recovery" in recover


def test_recovery_does_not_touch_pr11_or_packaging_implementation():
    source = QT_PATH.read_text(encoding="utf-8")
    assert "Nuitka" not in source
    assert "WiX" not in source
    assert "CL Automation" not in source
    registry = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    assert "other_workflow" not in registry
