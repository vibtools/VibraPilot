from __future__ import annotations

import ast
import csv
import json
import sqlite3
import sys
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import TaskItem, safe_spreadsheet_rows
from vibrapilot.data_io import export_report_csv, export_report_excel, parse_data_with_audit
from vibrapilot.task_runtime_store import SCHEMA_VERSION, TaskRuntimeStore
from vibrapilot.workspace_state import WORKSPACE_STATE_SCHEMA_VERSION, WorkspaceStateStore

SCOPE = json.loads((ROOT / "config/verification/v1.0.6.26_pr09_data_persistence_reporting_compatibility_scope.json").read_text(encoding="utf-8"))
QT_SOURCE = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
REGISTRY_SOURCE = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
DATA_IO_SOURCE = (ROOT / "src/vibrapilot/data_io.py").read_text(encoding="utf-8")


def _mainwindow_method_source(name: str) -> str:
    tree = ast.parse(QT_SOURCE)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow":
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == name:
                    return ast.get_source_segment(QT_SOURCE, item) or ""
    raise AssertionError(f"MainWindow method missing: {name}")


def _table_columns(db: Path, table: str) -> list[str]:
    with sqlite3.connect(db) as conn:
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def test_scope_locks_no_runtime_change_and_schema_v1():
    assert SCOPE["baseline_github_commit"] == "8b62a48982f1497c272a68cb3b428f5bd1b0d3c0"
    assert SCOPE["target_version"] == "1.0.6.26"
    assert SCOPE["allowed_production_source_changes"] == []
    assert SCOPE["production_runtime_changes"] == "none"
    assert SCOPE["task_runtime_schema_version"] == 1
    assert SCOPE["workflow_id_database_column"] is False
    assert SCOPE["database_migration"] is False
    assert SCOPE["pr10_not_started"] is True


def test_task_runtime_sqlite_schema_phase2_successor_adds_only_workflow_provenance(tmp_path):
    db = tmp_path / "task_runtime.sqlite3"
    TaskRuntimeStore(db)
    assert SCHEMA_VERSION == 2
    assert _table_columns(db, "runs") == [
        "run_id", "schema_version", "slot_id", "workflow_id", "target_url", "source_file",
        "source_fingerprint", "current_index", "total", "success_count",
        "failed_count", "send_limit_used", "task_status",
        "manual_review_required", "created_at", "updated_at", "completed_at",
    ]
    assert _table_columns(db, "items") == [
        "run_id", "item_index", "email", "name", "status", "attempts", "message", "result",
    ]
    assert _table_columns(db, "results") == [
        "run_id", "item_index", "timestamp", "slot_id", "workflow_id", "email", "status",
        "message", "attempts", "target_url", "result",
    ]
    with sqlite3.connect(db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"runs", "items", "results"}


def test_taskitem_contract_remains_backward_compatible_and_report_adds_workflow_provenance():
    assert [f.name for f in fields(TaskItem)] == SCOPE["taskitem_fields"]
    # Historical PR-09 report columns remain documented, while v1.0.6.42 adds
    # workflow_id as the single provenance column required by true multiworkflow.
    expected = SCOPE["live_report_columns"]
    assert expected == ["timestamp", "slot_id", "email", "status", "message", "attempts", "target_url", "result"]
    assert 'columns = ["timestamp", "slot_id", "workflow_id", "email", "status", "message", "attempts", "target_url", "result"]' in QT_SOURCE


def test_import_contract_preserves_txt_csv_xlsx_and_xls(tmp_path):
    txt = tmp_path / "rows.txt"
    txt.write_text("alpha@example.com\ninvalid\nbeta@example.com\n", encoding="utf-8")
    audit = parse_data_with_audit(txt, remove_duplicates=False)
    assert [i.email for i in audit.items] == ["alpha@example.com", "beta@example.com"]

    frame = pd.DataFrame({"email": ["alpha@example.com", "bad", "beta@example.com"], "name": ["A", "X", "B"]})
    csv_path = tmp_path / "rows.csv"
    frame.to_csv(csv_path, index=False)
    csv_audit = parse_data_with_audit(csv_path, remove_duplicates=False)
    assert [(i.email, i.name) for i in csv_audit.items] == [("alpha@example.com", "A"), ("beta@example.com", "B")]

    xlsx = tmp_path / "rows.xlsx"
    frame.to_excel(xlsx, index=False)
    xlsx_audit = parse_data_with_audit(xlsx, remove_duplicates=False)
    assert [(i.email, i.name) for i in xlsx_audit.items] == [("alpha@example.com", "A"), ("beta@example.com", "B")]

    xls = tmp_path / "rows.xls"
    xls.write_bytes(b"test-only-xls-placeholder")
    with patch("vibrapilot.data_io.pd.read_excel", return_value=frame):
        xls_audit = parse_data_with_audit(xls, remove_duplicates=False)
    assert [(i.email, i.name) for i in xls_audit.items] == [("alpha@example.com", "A"), ("beta@example.com", "B")]
    assert 'suffix in {".xlsx", ".xls"}' in DATA_IO_SOURCE


def test_report_exports_keep_current_columns_and_formula_safety(tmp_path):
    row = {
        "timestamp": "2026-08-10 10:00:00", "slot_id": 1, "email": "alpha@example.com",
        "status": "success", "message": "=unsafe", "attempts": 1,
        "target_url": "https://example.com", "result": "+formula",
    }
    safe = safe_spreadsheet_rows([row])[0]
    assert safe["message"] == "'=unsafe"
    assert safe["result"] == "'+formula"

    csv_path = tmp_path / "report.csv"
    xlsx_path = tmp_path / "report.xlsx"
    export_report_csv([row], csv_path)
    export_report_excel([row], xlsx_path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == SCOPE["live_report_columns"]
        exported = next(reader)
        assert exported["message"] == "'=unsafe"
    exported_xlsx = pd.read_excel(xlsx_path)
    assert list(exported_xlsx.columns) == SCOPE["live_report_columns"]
    assert exported_xlsx.loc[0, "message"] == "'=unsafe"


def test_workspace_schema_remains_lightweight_with_task_only_workflow_namespace(tmp_path):
    assert WORKSPACE_STATE_SCHEMA_VERSION == 2
    path = tmp_path / "state.json"
    store = WorkspaceStateStore(path)
    store.save({
        "saved_at": "now", "active_tasks": [{"slot_id": 2, "run_id": "r", "target_url": "u", "workflow_id": "workflow_a"}],
        "next_slot_id": 3, "selected_page": "Reports",
        "window": {"x": 1, "y": 2, "width": 800, "height": 600, "maximized": False},
        "workflow_id": "top-level-must-not-persist",
    })
    loaded = store.load()
    assert loaded is not None
    assert set(loaded) == {"schema_version", "saved_at", "active_tasks", "next_slot_id", "selected_page", "window"}
    assert "workflow_id" not in loaded
    assert loaded["active_tasks"][0]["workflow_id"] == "workflow_a"


def test_switch_clear_and_preserve_boundary_is_exact_and_no_wrong_workflow_recovery_path():
    switch_paths = _mainwindow_method_source("_workflow_switch_paths")
    clear_state = _mainwindow_method_source("_clear_workflow_scoped_state")
    switch = _mainwindow_method_source("request_workflow_switch")

    for marker in (
        "TASK_RUNTIME_DB", 'Path(str(TASK_RUNTIME_DB) + "-wal")', 'Path(str(TASK_RUNTIME_DB) + "-shm")',
        'APP_DATA_DIR.glob("slot_*_checkpoint.json")', '"active_tasks": []', '"next_slot_id": 1',
        "self.report_rows = []",
    ):
        assert marker in (switch_paths + clear_state)
    for preserved in ("REPORTS_DIR", "FAILED_DATA_DIR", "LOGS_DIR", "WORKFLOW_INPUT_STATE_FILE"):
        assert preserved not in switch_paths
        assert preserved not in clear_state
    assert "for key in WORKFLOW_INPUT_KEYS" in clear_state
    assert "transaction.prepare(self._workflow_switch_paths())" in switch
    assert "transaction.rollback()" in switch
    assert "self._restore_after_failed_workflow_switch(settings_snapshot)" in switch
    assert "old data must not be" in switch and "restored" in switch


def test_same_workflow_cancel_and_blockers_precede_destructive_clear():
    switch = _mainwindow_method_source("request_workflow_switch")
    assert switch.index('if target == current:') < switch.index("transaction.prepare")
    assert switch.index('return "already_active"') < switch.index("transaction.prepare")
    assert switch.index("_workflow_switch_block_reason()") < switch.index("transaction.prepare")
    assert switch.index('_confirm_workflow_switch(current, target)') < switch.index("transaction.prepare")
    assert switch.index('return "cancelled"') < switch.index("transaction.prepare")

    blocker = _mainwindow_method_source("_workflow_switch_block_reason")
    for marker in ("workflow_state_error", "workflow_input_state_error", "is_running()", "manual_review_required"):
        assert marker in blocker


def test_historical_pr09_contract_is_preserved_but_v10636_registry_is_zero_builtin():
    assert "return (SHARE_INVITE_MANIFEST,)" not in REGISTRY_SOURCE
    assert 'ShareInviteWorkflow' not in REGISTRY_SOURCE
    assert "return ()" in REGISTRY_SOURCE
    # Historical PR-09 scope evidence is immutable; v1.0.6.36 intentionally supersedes
    # only the production built-in-workflow assumption.
    assert SCOPE["production_workflows"] == ["share_invite"]
    assert SCOPE["pr10_not_started"] is True
    assert SCOPE["cross_workflow_live_report_history"] is False
    assert SCOPE["dynamic_task_import_schema"] is False
