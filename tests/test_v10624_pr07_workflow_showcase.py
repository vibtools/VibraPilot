from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from vibrapilot.workflow import WorkflowManager, WorkflowManifest, WorkflowRegistry
from vibrapilot.workflow.share_invite import SHARE_INVITE_MANIFEST

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


def test_current_production_registry_contains_only_share_invite():
    manager = WorkflowManager.with_builtin_workflows()
    assert [m.workflow_id for m in manager.list_workflows()] == ["share_invite"]
    registry_text = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    assert "return (SHARE_INVITE_MANIFEST,)" in registry_text
    assert "other_workflow" not in registry_text


def test_share_invite_card_metadata_is_manifest_owned():
    assert SHARE_INVITE_MANIFEST.name == "Share Invite"
    assert SHARE_INVITE_MANIFEST.description == "Authenticated Test Mode Share Invite workflow."
    assert SHARE_INVITE_MANIFEST.version == "1.0"
    assert SHARE_INVITE_MANIFEST.logo == "logo.png"


def test_card_displays_manifest_name_description_id_version_and_logo():
    source = _source("_workflow_card")
    for marker in ("manifest.name", "manifest.description", "manifest.workflow_id", "manifest.version", "_workflow_logo_path(manifest)"):
        assert marker in source


def test_active_workflow_is_rendered_as_disabled_active_action():
    source = _source("_workflow_card")
    assert 'button("Active", "secondary")' in source
    assert 'action.setObjectName("WorkflowActiveButton")' in source
    assert "action.setEnabled(False)" in source


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


def test_valid_inactive_workflow_activation_delegates_only_to_pr06_service():
    source = _source("_activate_workflow_from_showcase")
    assert "self.request_workflow_switch(workflow_id)" in source
    assert source.count("request_workflow_switch(") == 1
    for forbidden in ("WorkflowSwitchTransaction(", "commit_active_workflow(", "_confirm_workflow_switch(", "transaction.prepare("):
        assert forbidden not in source


def test_activation_handler_preserves_pr06_status_ownership():
    source = _source("_activate_workflow_from_showcase")
    for status in ("already_active", "cancelled", "committed_restart_required", "switched"):
        assert status in source


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
    assert [m.workflow_id for m in WorkflowManager.with_builtin_workflows().list_workflows()] == ["share_invite"]


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
    current_authorized = (pr08_authorized_supersession | pr10_authorized_supersession
        | set(v10630.get("allowed_production_source_changes", [])) | set(v10630.get("authorized_nonproduction_files", []))
        | set(v10631.get("allowed_production_source_changes", [])) | set(v10631.get("authorized_nonproduction_files", [])))
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
