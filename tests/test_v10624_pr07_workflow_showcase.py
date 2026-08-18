from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from vibrapilot.workflow import WorkflowManager, WorkflowManifest, WorkflowRegistry
from _v10636_manifest_fixture import SHARE_INVITE_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src/vibrapilot/qt_app.py"
QT_TEXT = QT_PATH.read_text(encoding="utf-8")
QT_TREE = ast.parse(QT_TEXT, filename=str(QT_PATH))
SCOPE_PATH = ROOT / "config/verification/v1.0.6.24_pr07_workflow_showcase_scope.json"
PR10_SCOPE_PATH = ROOT / "config/verification/v1.0.6.27_pr10_workflow_error_recovery_scope.json"
V10630_SCOPE_PATH = ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json"
V10631_SCOPE_PATH = ROOT / "config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json"


def _scope() -> dict:
    return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))


def _assignment(name: str):
    for node in QT_TREE.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment: {name}")


def _main_window_method(name: str) -> ast.FunctionDef:
    cls = next(node for node in QT_TREE.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _source(name: str) -> str:
    return ast.get_source_segment(QT_TEXT, _main_window_method(name)) or ""


def test_scope_pins_exact_pr06_release_baseline_and_target():
    s = _scope()
    assert s["plan_id"] == "VP-PR07-WORKFLOW-SHOWCASE-001"
    assert s["official_baseline_archive_sha256"] == "bafc6d672447afbf02bf3a8c06f8b9992239d9943cb178f6fdec00ff1d6939f6"
    assert s["baseline_github_commit"] == "0959c00d014d71909726b0e886aaaa88e38f3eae"
    assert s["baseline_ci_result"] == "PASS"
    assert s["baseline_version"] == "1.0.6.23"
    assert s["target_version"] == "1.0.6.24"


def test_production_source_scope_is_qt_app_only():
    scope = _scope()
    assert scope["allowed_production_source_changes"] == ["src/vibrapilot/qt_app.py"]
    assert set(scope["approved_mainwindow_method_changes"]) == {
        "_create_nav_button", "_register_pages", "navigate", "make_workflows_page",
        "_workflow_logo_path", "_workflow_card", "refresh_workflow_showcase",
        "_activate_workflow_from_showcase",
    }


def test_workflows_navigation_exists_once_in_exact_order():
    nav = _assignment("NAV_SECTIONS")
    if V10630_SCOPE_PATH.is_file():
        assert nav == ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Workflow Settings", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]
    else:
        assert nav == ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]
    assert nav.count("Workflows") == 1


def test_existing_navigation_shortcuts_are_not_renumbered():
    assert _assignment("VIEW_NAV_SHORTCUTS") == {
        "Dashboard": "Ctrl+1",
        "Tasks": "Ctrl+2",
        "Reports": "Ctrl+3",
        "Live Logs": "Ctrl+4",
        "App Settings": "Ctrl+5",
        "Browser Settings": "Ctrl+6",
    }


def test_workflows_page_is_registered_between_tasks_and_workflow_inputs():
    source = _source("_register_pages")
    assert source.index('(\"Tasks\", self.make_tasks_page)') < source.index('(\"Workflows\", self.make_workflows_page)')
    assert source.index('(\"Workflows\", self.make_workflows_page)') < source.index('(\"Workflow Inputs\", self.make_workflow_inputs_page)')


def test_navigation_refreshes_workflow_showcase_on_entry():
    source = _source("navigate")
    assert 'elif name == "Workflows":' in source
    assert "self.refresh_workflow_showcase()" in source


def test_showcase_renders_registry_entries_instead_of_hardcoded_catalog():
    source = _source("refresh_workflow_showcase")
    assert "self.workflow_catalog.list_workflows()" in source
    assert "for manifest in manifests:" in source
    assert "Share Invite" not in source


def test_v10636_production_registry_contains_zero_builtin_workflows():
    manager = WorkflowManager.with_builtin_workflows()
    assert manager.list_workflows() == ()
    registry_text = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    assert "SHARE_INVITE_MANIFEST" not in registry_text
    assert "return ()" in registry_text
    assert "other_workflow" not in registry_text


def test_share_invite_card_metadata_is_manifest_owned():
    assert SHARE_INVITE_MANIFEST.name == "Share Invite"
    assert SHARE_INVITE_MANIFEST.description == "Authenticated Test Mode Share Invite workflow."
    assert SHARE_INVITE_MANIFEST.version == "1.0"
    assert SHARE_INVITE_MANIFEST.logo == "assets/logo.png"


def test_card_preserves_manifest_identity_version_source_logo_and_readable_description_copy():
    source = _source("_workflow_card")
    for marker in ("manifest.name", "manifest.workflow_id", "manifest.version", "_workflow_logo_path(manifest)"):
        assert marker in source
    assert "manifest.description" in source
    assert 'setObjectName("WorkflowDescription")' in source
    assert "workflow_origin" in source


def test_active_workflow_uses_status_badge_without_duplicate_disabled_active_action():
    source = _source("_workflow_card")
    assert 'status_badge("DEFAULT" if is_active else "AVAILABLE"' in source
    assert 'button("Active", "secondary")' not in source
    assert 'action.setObjectName("WorkflowActiveButton")' not in source


def test_invalid_persisted_state_disables_activation_and_does_not_migrate():
    refresh = _source("refresh_workflow_showcase")
    card_source = _source("_workflow_card")
    assert "self.workflow_state_store.load_existing()" in refresh
    assert "load_or_migrate" not in refresh
    assert 'button("Unavailable", "secondary")' in card_source
    # PR-10 explicitly supersedes the old unavailable-only state with a
    # user-confirmed recovery action; normal Activate is still impossible.
    assert "recovery_available" in card_source
    assert "elif not state_available:" in card_source


def test_runtime_availability_uses_existing_fail_closed_factory_resolution():
    source = _source("_workflow_card")
    assert "self.workflow_catalog.require_runtime_factory(manifest.workflow_id)" in source
    assert "except WorkflowError:" in source


def test_valid_inactive_workflow_activation_delegates_only_to_restart_free_phase2_service():
    source = _source("_activate_workflow_from_showcase")
    # v1.0.6.42 keeps the showcase thin but supersedes the restart-required PR-06
    # UI path with the approved default-for-new-Tasks service.
    assert "self.request_default_workflow_switch(resolved)" in source
    assert source.count("request_default_workflow_switch(") == 1
    assert "_confirm_default_workflow_switch(resolved)" in source
    for forbidden in ("WorkflowSwitchTransaction(", "commit_active_workflow(", "_confirm_workflow_switch(", "transaction.prepare(", "_spawn_workflow_restart("):
        assert forbidden not in source


def test_activation_handler_preserves_phase2_default_switch_status_ownership():
    source = _source("_activate_workflow_from_showcase")
    for status in ("already_active", "activated", "switched"):
        assert status in source
    assert "committed_restart_required" not in source


def test_logo_resolution_is_deterministic_and_has_no_discovery():
    source = _source("_workflow_logo_path")
    if V10630_SCOPE_PATH.is_file():
        assert "self.workflow_catalog.workflow_asset_path" in source
    else:
        assert '"src" / "vibrapilot" / "workflow" / manifest.workflow_id' in source
    assert "manifest.logo" in source
    for forbidden in ("glob(", "rglob(", "iterdir(", "importlib", "__import__", "entry_points"):
        assert forbidden not in source


def test_no_fake_demo_placeholder_or_coming_soon_production_cards():
    showcase = _source("refresh_workflow_showcase") + _source("_workflow_card")
    for marker in ("Demo Workflow", "Placeholder Workflow", "Coming Soon", "other_workflow"):
        assert marker not in showcase


def test_pr08_dynamic_inputs_are_not_implemented_in_showcase():
    source = _source("make_workflows_page") + _source("_workflow_card") + _source("refresh_workflow_showcase")
    for marker in ("WORKFLOW_INPUT_FIELDS", "WORKFLOW_INPUT_KEYS", "default_full_name", "default_number", "fallback_name", "update_click_count"):
        assert marker not in source


def test_synthetic_workflow_can_exist_in_tests_without_production_registration():
    synthetic = WorkflowManifest(
        workflow_id="synthetic_test",
        name="Synthetic Test",
        description="Test-only manifest.",
        version="1.0",
        logo="logo.png",
        entrypoint="synthetic_test",
    )
    registry = WorkflowRegistry([SHARE_INVITE_MANIFEST, synthetic])
    assert [m.workflow_id for m in registry.list_workflows()] == ["share_invite", "synthetic_test"]
    assert WorkflowManager.with_builtin_workflows().list_workflows() == ()


def test_frozen_runtime_config_dependency_and_ci_files_are_byte_identical():
    pr08_authorized_supersession = {
        "src/vibrapilot/backend.py",
        "src/vibrapilot/workflow_inputs.py",
    }
    pr10_authorized_supersession = set(
        json.loads(PR10_SCOPE_PATH.read_text(encoding="utf-8"))["allowed_production_source_changes"]
    )
    v10630 = json.loads(V10630_SCOPE_PATH.read_text(encoding="utf-8")) if V10630_SCOPE_PATH.is_file() else {}
    v10631 = json.loads(V10631_SCOPE_PATH.read_text(encoding="utf-8")) if V10631_SCOPE_PATH.is_file() else {}
    v10636_path = ROOT / "config/verification/v1.0.6.36_share_invite_externalization_scope.json"
    v10636 = json.loads(v10636_path.read_text(encoding="utf-8")) if v10636_path.is_file() else {}
    # v1.0.6.42 approved Phase-2 successor files; dependency/CI and every other
    # PR-07 frozen surface remain hash-enforced.
    v10642_authorized_supersession = {
        "src/vibrapilot/qt_app.py",
        "src/vibrapilot/task_runtime_store.py",
        "src/vibrapilot/workspace_state.py",
        "src/vibrapilot/workflow/__init__.py",
        "src/vibrapilot/workflow/plugin_loader.py",
        "src/vibrapilot/workflow/state.py",
    }
    current_authorized = (pr08_authorized_supersession | pr10_authorized_supersession | v10642_authorized_supersession
        | set(v10630.get("allowed_production_source_changes", [])) | set(v10630.get("authorized_nonproduction_files", []))
        | set(v10631.get("allowed_production_source_changes", [])) | set(v10631.get("authorized_nonproduction_files", []))
        | set(v10636.get("allowed_production_source_changes", [])) | set(v10636.get("authorized_nonproduction_files", []))
        | set(v10636.get("deleted_production_paths", [])))
    for relative, expected in _scope()["frozen_file_sha256"].items():
        if relative in current_authorized:
            continue
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative


def test_scope_explicitly_forbids_out_of_scope_surfaces():
    s = _scope()
    for key in (
        "no_fake_demo_placeholder_workflows",
        "no_dynamic_workflow_inputs",
        "no_workflow_engine_change",
        "no_workflow_state_schema_change",
        "no_task_database_schema_change",
        "no_workspace_schema_change",
        "no_report_schema_change",
        "no_browser_change",
        "no_licensing_change",
        "captcha_out_of_scope",
        "no_dependency_change",
        "no_ci_workflow_change",
        "external_plugin_loading_prohibited",
        "filesystem_workflow_discovery_prohibited",
        "manifest_controlled_dynamic_import_prohibited",
    ):
        assert s[key] is True
