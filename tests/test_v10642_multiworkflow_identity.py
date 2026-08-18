from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src" / "vibrapilot" / "qt_app.py"


def _method_source(name: str) -> str:
    text = QT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(text, node) or ""


def _task_method_source(name: str) -> str:
    text = QT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TaskSlotWidget")
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ast.get_source_segment(text, node) or ""


def test_task_slot_accepts_immutable_explicit_workflow_identity_with_legacy_default_compatibility():
    source = QT_PATH.read_text(encoding="utf-8")
    assert 'def __init__(self, app: "MainWindow", slot_id: int, workflow_id: str | None = None)' in source
    assert 'self.workflow_id = str(workflow_id or getattr(app, "active_workflow_id", "") or "compatibility_host")' in source


def test_worker_creation_uses_task_owned_workflow_not_app_global_workflow():
    source = _task_method_source("open_browser")
    assert "active_workflow_id=self.workflow_id" in source
    assert "for_active_workflow(self.workflow_id)" in source
    assert "current_workflow_input_snapshot(self.workflow_id)" in source
    assert "current_workflow_settings_snapshot(self.workflow_id)" in source
    assert "active_workflow_id=self.app.active_workflow_id" not in source


def test_restart_free_default_workflow_activation_does_not_clear_tasks_or_spawn_process():
    source = _method_source("request_default_workflow_switch")
    assert "commit_default_workflow" in source
    assert "_reload_workflow_catalog" in source
    assert "_spawn_workflow_restart" not in source
    assert "_clear_workflow_scoped_state" not in source
    assert "self.tasks.clear" not in source


def test_add_task_can_bind_selected_workflow_and_task_cards_show_workflow_identity():
    source = QT_PATH.read_text(encoding="utf-8")
    assert "def _select_workflow_for_new_task" in source
    assert "def _add_task_with_id(self, slot_id: int, workflow_id: str | None = None)" in source
    assert "Workflow:" in source
    assert "workflow_version" in source


def test_workflows_page_exposes_update_remove_and_deactivate_without_new_top_level_page():
    source = QT_PATH.read_text(encoding="utf-8")
    for marker in (
        'button("Update", "secondary")',
        'button("Remove", "danger")',
        'button("Deactivate", "secondary")',
        "def update_workflow_plugin",
        "def remove_workflow_plugin",
        "def deactivate_default_workflow",
    ):
        assert marker in source
    assert 'NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Workflow Settings", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]' in source



def test_lifecycle_blocker_ignores_completed_closed_history_but_blocks_unfinished_closed_task():
    source = _method_source("_workflow_reference_block_reason")
    assert "self.runtime_store.recoverable_runs()" in source
    assert "self.runtime_store.closed_runs()" in source
    assert 'if row.get("completed_at") is None' in source
    assert "recoverable/unfinished closed Task runtime(s)" in source


def test_two_workers_keep_independent_workflow_identity_and_report_provenance(tmp_path):
    import queue
    import threading
    from _v10630_plugin_fixture import write_plugin_package
    from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskItem, TaskState
    from vibrapilot.workflow import WorkflowManager, inspect_workflow_package, install_workflow_package

    root = tmp_path / "Workflows"
    for workflow_id in ("workflow_a", "workflow_b"):
        package = write_plugin_package(tmp_path / f"{workflow_id}.vpworkflow", workflow_id)
        install_workflow_package(inspect_workflow_package(package), root, reserved_workflow_ids=set())
    catalog = WorkflowManager.with_available_workflows(workflow_root=root)

    workers = []
    for slot_id, workflow_id in ((1, "workflow_a"), (2, "workflow_b")):
        worker = AutomationWorker(
            TaskState(slot_id=slot_id),
            dict(DEFAULT_SETTINGS),
            queue.Queue(),
            threading.Event(),
            threading.Event(),
            "https://example.test",
            active_workflow_id=workflow_id,
            workflow_manager=catalog.for_active_workflow(workflow_id),
        )
        workers.append(worker)

    assert workers[0]._workflow_manager.active_workflow_id == "workflow_a"
    assert workers[1]._workflow_manager.active_workflow_id == "workflow_b"
    assert workers[0].report_row(TaskItem("a@example.com"), "")["workflow_id"] == "workflow_a"
    assert workers[1].report_row(TaskItem("b@example.com"), "")["workflow_id"] == "workflow_b"


def test_default_workflow_switch_requires_explicit_confirmation_and_never_restarts_tasks():
    activate = _method_source("_activate_workflow_from_showcase")
    confirm = _method_source("_confirm_default_workflow_switch")
    assert "_confirm_default_workflow_switch" in activate
    assert "Existing Tasks keep their current workflow identities" in confirm
    assert "_spawn_workflow_restart" not in activate + confirm
    assert "_clear_workflow_scoped_state" not in activate + confirm


def test_active_unavailable_workflow_still_exposes_deactivate_escape_path():
    source = _method_source("_workflow_card")
    assert "if is_active:" in source
    active_block = source[source.index("if is_active:"):source.index("elif recovery_available:")]
    assert 'button("Deactivate", "secondary")' in active_block
    assert 'badge.setText("UNAVAILABLE")' in active_block
    assert 'button("Unavailable", "secondary")' not in active_block


def test_initial_default_task_slots_do_not_open_repeated_workflow_selector_dialogs():
    text = QT_PATH.read_text(encoding="utf-8")
    marker = "# Preserve baseline first-workspace behavior"
    assert marker in text
    segment = text[text.index(marker) - 250:text.index(marker) + 800]
    assert "self._add_task_with_id(candidate, self.active_workflow_id)" in segment
    assert "self.add_task()" not in segment
