from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src" / "vibrapilot" / "qt_app.py"
PLUGIN_PATH = ROOT / "src" / "vibrapilot" / "workflow" / "plugin_loader.py"


def _mainwindow_method_source(name: str) -> str:
    text = QT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(text, method) or ""


def test_legacy_request_workflow_switch_is_restart_free_compatibility_path():
    source = _mainwindow_method_source("request_workflow_switch")
    assert "request_default_workflow_switch" in source
    assert "_spawn_workflow_restart" not in source
    assert "_clear_workflow_scoped_state" not in source
    assert "_finalize_committed_workflow_switch" not in source
    assert "QTimer.singleShot(0, self.close)" not in source


def test_lifecycle_transaction_root_file_fails_closed_with_controlled_error(tmp_path: Path):
    from vibrapilot.workflow import WorkflowPluginInstallError, recover_workflow_lifecycle_transactions

    root = tmp_path / "Workflows"
    root.mkdir()
    (root / ".transactions").write_text("not-a-directory", encoding="utf-8")
    with pytest.raises(WorkflowPluginInstallError, match="transaction root"):
        recover_workflow_lifecycle_transactions(root)


def test_lifecycle_recovery_rejects_unsafe_workflow_id_before_path_use(tmp_path: Path):
    from vibrapilot.workflow import WorkflowPluginInstallError, recover_workflow_lifecycle_transactions

    root = tmp_path / "Workflows"
    tx = root / ".transactions" / "bad-update"
    tx.mkdir(parents=True)
    (tx / "transaction.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "PREPARED",
                "action": "update",
                "workflow_id": "../escape",
                "target_version": "2.0.0",
                "created_at": "2026-08-18T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(WorkflowPluginInstallError, match="identity"):
        recover_workflow_lifecycle_transactions(root)
    assert tx.exists()


def test_schema_v2_workspace_missing_workflow_identity_blocks_preserving_save(tmp_path: Path):
    from vibrapilot.workspace_state import WorkspaceStateStore

    path = tmp_path / "state.json"
    original = {
        "schema_version": 2,
        "saved_at": "now",
        "active_tasks": [
            {"slot_id": 4, "workflow_id": "", "run_id": "run4", "target_url": "https://example.test"}
        ],
        "next_slot_id": 5,
        "selected_page": "Tasks",
        "window": {},
    }
    path.write_text(json.dumps(original), encoding="utf-8")
    store = WorkspaceStateStore(path)
    state = store.load()
    assert state is not None
    assert state["active_tasks"] == []
    assert store.migration_blocked is True
    assert "workflow identity" in store.warning.lower()
    assert json.loads(path.read_text(encoding="utf-8"))["active_tasks"][0]["run_id"] == "run4"


def test_unavailable_workspace_workflow_blocks_autosave_instead_of_erasing_task_shell():
    source = _mainwindow_method_source("_restore_active_workspace_tasks")
    unavailable = source[source.index("if not workflow_id or self.workflow_catalog.get_workflow(workflow_id) is None:"):]
    unavailable = unavailable[: unavailable.index("if run_id and run_id in closed_run_ids:")]
    assert "self.workspace_store.migration_blocked = True" in unavailable
    assert "workflow identity" in unavailable.lower()


def test_unresolved_legacy_recoverable_run_blocks_workflow_package_mutation():
    source = _mainwindow_method_source("_workflow_reference_block_reason")
    assert "_resolve_legacy_workspace_workflow_identity" in source
    assert "unresolved" in source.lower()


def test_live_lifecycle_transaction_blocks_new_tasks_and_browser_open():
    add_task = _mainwindow_method_source("add_task")
    can_open = _mainwindow_method_source("can_open_task_browser")
    assert "_workflow_lifecycle_block_reason" in add_task
    assert "_workflow_lifecycle_block_reason" in can_open


def test_phase2_visible_global_workflow_identity_is_labeled_default_not_active():
    qt = QT_PATH.read_text(encoding="utf-8")
    assert 'workflow_card = card("Default Workflow")' in qt
    card_source = _mainwindow_method_source("_workflow_card")
    assert '"DEFAULT" if is_active else "AVAILABLE"' in card_source
    assert "Active workflow runtime unavailable" not in _mainwindow_method_source("refresh_workflow_showcase")


def test_install_workflow_package_has_single_staging_parent_creation():
    text = PLUGIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    method = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "install_workflow_package")
    source = ast.get_source_segment(text, method) or ""
    assert source.count("staging_parent.mkdir(parents=True, exist_ok=True)") == 1
