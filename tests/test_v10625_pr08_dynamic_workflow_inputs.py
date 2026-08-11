from __future__ import annotations

import ast
import hashlib
import json
import queue
import threading
from pathlib import Path

import pytest

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskState
from vibrapilot.workflow import WorkflowManager
from vibrapilot.workflow_inputs import (
    SHARE_INVITE_INPUT_SCHEMA,
    WORKFLOW_INPUT_FIELDS,
    WORKFLOW_INPUT_KEYS,
    WORKFLOW_INPUT_SCHEMAS,
    workflow_input_schema_for,
)

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src/vibrapilot/qt_app.py"
QT_TEXT = QT_PATH.read_text(encoding="utf-8")
QT_TREE = ast.parse(QT_TEXT, filename=str(QT_PATH))
SCOPE = json.loads(
    (ROOT / "config/verification/v1.0.6.25_pr08_dynamic_workflow_inputs_scope.json").read_text(encoding="utf-8")
)
PR10_SCOPE = json.loads(
    (ROOT / "config/verification/v1.0.6.27_pr10_workflow_error_recovery_scope.json").read_text(encoding="utf-8")
)


def _main_method(name: str) -> ast.FunctionDef:
    cls = next(n for n in QT_TREE.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _task_method(name: str) -> ast.FunctionDef:
    cls = next(n for n in QT_TREE.body if isinstance(n, ast.ClassDef) and n.name == "TaskSlotWidget")
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _source(node: ast.AST) -> str:
    return ast.get_source_segment(QT_TEXT, node) or ""


def test_scope_locks_pr07_release_and_exact_pr08_production_surface():
    assert SCOPE["official_baseline_archive_sha256"] == "d20b3152a84870f36a794f862578718955c935b113bf7a4d8dd5bcd9b4a16d3d"
    assert SCOPE["baseline_github_commit"] == "39e089da94d8d7fcb0126e46a9dd4e259956f531"
    assert SCOPE["target_version"] == "1.0.6.25"
    assert SCOPE["allowed_production_source_changes"] == [
        "src/vibrapilot/workflow_inputs.py",
        "src/vibrapilot/workflow/input_state.py",
        "src/vibrapilot/qt_app.py",
        "src/vibrapilot/backend.py",
    ]


def test_production_registry_and_input_schema_contain_only_share_invite():
    assert [m.workflow_id for m in WorkflowManager.with_builtin_workflows().list_workflows()] == ["share_invite"]
    assert list(WORKFLOW_INPUT_SCHEMAS) == ["share_invite"]
    assert workflow_input_schema_for("share_invite") is SHARE_INVITE_INPUT_SCHEMA
    assert WORKFLOW_INPUT_KEYS == (
        "default_full_name", "default_number", "fallback_name", "update_click_count"
    )
    assert tuple(field.key for field in WORKFLOW_INPUT_FIELDS) == WORKFLOW_INPUT_KEYS


def test_dynamic_page_renders_active_schema_not_fixed_global_tuple():
    make = _source(_main_method("make_workflow_inputs_page"))
    refresh = _source(_main_method("refresh_workflow_input_widgets"))
    reload_source = _source(_main_method("_reload_active_workflow_inputs"))
    assert "workflow_input_schema_for(self.active_workflow_id)" in reload_source
    assert "for row, field in enumerate(schema.fields):" in refresh
    assert "WORKFLOW_INPUT_FIELDS" not in make + refresh
    assert "Workflow:" not in make + refresh
    assert "default_target_url" not in make + refresh


def test_dynamic_renderer_supports_only_approved_declarative_widget_kinds():
    source = _source(_main_method("_workflow_input_widget"))
    for kind in ('field.kind == "text"', 'field.kind == "integer"', 'field.kind == "boolean"', 'field.kind == "choice"'):
        assert kind in source
    for forbidden in ("QFileDialog", "importlib", "__import__", "eval(", "exec(", "callback"):
        assert forbidden not in source


def test_ui_save_reset_are_active_workflow_only_and_canonical_store_owned():
    save = _source(_main_method("save_workflow_inputs"))
    reset = _source(_main_method("reset_workflow_inputs"))
    persist = _source(_main_method("_persist_active_workflow_input_values"))
    assert "_collect_workflow_input_values" in save
    assert "schema.defaults()" in reset
    assert "save_workflow_values" in persist
    assert "save_state(previous_state)" in persist
    assert "settings.save()" not in save + reset
    assert "default_target_url" not in save + reset + persist


def test_input_state_error_blocks_browser_opening_and_real_workflow_switches():
    browser = _source(_main_method("can_open_task_browser"))
    blocker = _source(_main_method("_workflow_switch_block_reason"))
    assert "self.workflow_input_state_error" in browser
    assert "self.workflow_input_state_error" in blocker
    assert "fail-closed" in browser


def test_pr06_switch_boundary_keeps_legacy_clear_but_not_canonical_input_store():
    paths = _source(_main_method("_workflow_switch_paths"))
    clear = _source(_main_method("_clear_workflow_scoped_state"))
    confirm = _source(_main_method("_confirm_workflow_switch"))
    assert "for key in WORKFLOW_INPUT_KEYS" in clear
    assert "workflow_inputs.json" not in paths + clear
    assert "Canonical per-workflow Workflow Input values will be preserved" in confirm


def test_new_workers_receive_snapshot_without_live_worker_mutation_path():
    open_browser = _source(_task_method("open_browser"))
    assert "workflow_input_values=self.app.current_workflow_input_snapshot()" in open_browser
    for source in (
        _source(_main_method("save_workflow_inputs")),
        _source(_main_method("_persist_active_workflow_input_values")),
    ):
        assert "worker.workflow_input_values" not in source
        assert '("workflow_input_values"' not in source


def test_automationworker_snapshot_is_detached_and_immutable():
    original = {"default_full_name": "Snapshot Name"}
    worker = AutomationWorker(
        TaskState(slot_id=1),
        dict(DEFAULT_SETTINGS),
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        "https://example.test",
        active_workflow_id="share_invite",
        workflow_input_values=original,
    )
    original["default_full_name"] = "Mutated Outside"
    assert worker.workflow_input_values["default_full_name"] == "Snapshot Name"
    with pytest.raises(TypeError):
        worker.workflow_input_values["default_full_name"] = "Nope"  # type: ignore[index]


def test_share_invite_runtime_and_pr06_workflow_engine_are_frozen():
    pr10_authorized = set(PR10_SCOPE["allowed_production_source_changes"])
    pr12_scope_path = ROOT / "config/verification/v1.0.6.29_pr12_packaging_scope.json"
    pr12 = json.loads(pr12_scope_path.read_text(encoding="utf-8")) if pr12_scope_path.is_file() else {}
    current_authorized = pr10_authorized | set(pr12.get("allowed_production_source_changes", [])) | set(pr12.get("authorized_nonproduction_files", []))
    for relative, expected in SCOPE["frozen_file_sha256"].items():
        if relative in current_authorized:
            continue
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative


def test_no_dynamic_actions_plugins_or_pr09_schema_work_enter_pr08():
    workflow_inputs_text = (ROOT / "src/vibrapilot/workflow_inputs.py").read_text(encoding="utf-8")
    input_state_text = (ROOT / "src/vibrapilot/workflow/input_state.py").read_text(encoding="utf-8")
    combined = workflow_inputs_text + input_state_text
    for forbidden in ("importlib", "entry_points", "rglob(", "glob(", "eval(", "exec(", "action_callback"):
        assert forbidden not in combined
    for key in (
        "no_task_database_schema_change", "no_workspace_schema_change", "no_report_schema_change",
        "no_browser_change", "no_licensing_change", "captcha_out_of_scope", "no_dependency_change",
        "no_ci_workflow_change", "pr09_not_started",
    ):
        assert SCOPE[key] is True
