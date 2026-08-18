from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_workspace_v2_persists_workflow_id_and_migrates_v1_with_resolver(tmp_path: Path):
    import json
    from vibrapilot.workspace_state import WorkspaceStateStore, WORKSPACE_STATE_SCHEMA_VERSION

    assert WORKSPACE_STATE_SCHEMA_VERSION == 2
    path = tmp_path / "state.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "saved_at": "now",
        "active_tasks": [{"slot_id": 3, "run_id": "run3", "target_url": "https://x"}],
        "next_slot_id": 4,
        "selected_page": "Tasks",
        "window": {"x": 1, "y": 2, "width": 800, "height": 600, "maximized": False},
    }), encoding="utf-8")
    store = WorkspaceStateStore(path, legacy_workflow_resolver=lambda slot, run: "workflow_a" if slot == 3 else None)
    state = store.load()
    assert state is not None
    assert state["schema_version"] == 2
    assert state["active_tasks"][0]["workflow_id"] == "workflow_a"
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 2


def test_workspace_v1_unresolved_task_is_not_assigned_an_arbitrary_workflow(tmp_path: Path):
    import json
    from vibrapilot.workspace_state import WorkspaceStateStore

    path = tmp_path / "state.json"
    path.write_text(json.dumps({
        "schema_version": 1,
        "saved_at": "now",
        "active_tasks": [{"slot_id": 1, "run_id": "legacy", "target_url": ""}],
        "next_slot_id": 2,
        "selected_page": "Tasks",
        "window": {},
    }), encoding="utf-8")
    store = WorkspaceStateStore(path, legacy_workflow_resolver=lambda _slot, _run: None)
    state = store.load()
    assert state is not None
    assert state["active_tasks"] == []
    assert "workflow identity" in store.warning.lower()
    assert store.migration_blocked is True
    # Fail closed without rewriting away the unresolved legacy Task shell.
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1


def test_task_runtime_store_v2_persists_workflow_provenance_and_filters_results(tmp_path: Path):
    from vibrapilot.task_runtime_store import TaskRuntimeStore, SCHEMA_VERSION

    assert SCHEMA_VERSION == 2
    store = TaskRuntimeStore(tmp_path / "store.sqlite3")
    item = SimpleNamespace(email="a@example.com", name="A", status="pending", attempts=0, message="", result="")
    run_id = store.start_run(
        slot_id=1,
        workflow_id="workflow_a",
        target_url="https://example.test",
        source_file="x.txt",
        source_fingerprint="abc",
        items=[item],
        created_at="2026-08-18 00:00:00",
    )
    store.upsert_result(run_id, 0, {
        "timestamp": "2026-08-18 00:00:01", "slot_id": 1, "workflow_id": "workflow_a",
        "email": "a@example.com", "status": "success", "message": "", "attempts": 1,
        "target_url": "https://example.test", "result": "ok",
    })
    run = store.load_run(run_id)
    assert run and run["workflow_id"] == "workflow_a"
    assert store.results(workflow_id="workflow_a")[0]["workflow_id"] == "workflow_a"
    assert store.results(workflow_id="workflow_b") == []
    assert store.result_workflow_ids() == ["workflow_a"]


def test_qt_workspace_snapshot_restore_reports_and_dashboard_are_workflow_aware():
    text = (Path(__file__).resolve().parents[1] / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert '"workflow_id": task.workflow_id' in text
    assert '_add_task_with_id(slot_id, workflow_id)' in text
    assert 'self.report_workflow = combo_box(["All Workflows"])' in text
    assert '"workflow_id"' in text[text.index("def make_reports_page"):text.index("def make_logs_page")]
    assert "result_workflow_ids" in text
    assert "workflow_groups" in text


def test_task_runtime_store_migrates_v1_database_without_inventing_workflow_identity(tmp_path: Path):
    import sqlite3
    from vibrapilot.task_runtime_store import TaskRuntimeStore, SCHEMA_VERSION

    path = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE runs (
            run_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL, slot_id INTEGER NOT NULL,
            target_url TEXT NOT NULL DEFAULT '', source_file TEXT NOT NULL DEFAULT '',
            source_fingerprint TEXT NOT NULL DEFAULT '', current_index INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0, success_count INTEGER NOT NULL DEFAULT 0,
            failed_count INTEGER NOT NULL DEFAULT 0, send_limit_used INTEGER NOT NULL DEFAULT 0,
            task_status TEXT NOT NULL DEFAULT 'Ready', manual_review_required INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT
        );
        CREATE TABLE items (
            run_id TEXT NOT NULL, item_index INTEGER NOT NULL, email TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '', PRIMARY KEY(run_id,item_index)
        );
        CREATE TABLE results (
            run_id TEXT NOT NULL, item_index INTEGER NOT NULL, timestamp TEXT NOT NULL,
            slot_id INTEGER NOT NULL, email TEXT NOT NULL, status TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0,
            target_url TEXT NOT NULL DEFAULT '', result TEXT NOT NULL DEFAULT '', PRIMARY KEY(run_id,item_index)
        );
        """
    )
    conn.execute(
        "INSERT INTO runs(run_id,schema_version,slot_id,target_url,source_file,source_fingerprint,current_index,total,success_count,failed_count,send_limit_used,task_status,manual_review_required,created_at,updated_at,completed_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("legacy-run", 1, 3, "https://legacy", "", "", 1, 1, 1, 0, 0, "Completed", 0, "t0", "t1", "t1"),
    )
    conn.execute(
        "INSERT INTO items(run_id,item_index,email,name,status,attempts,message,result) VALUES(?,?,?,?,?,?,?,?)",
        ("legacy-run", 0, "old@example.com", "Old", "success", 1, "", "ok"),
    )
    conn.execute(
        "INSERT INTO results(run_id,item_index,timestamp,slot_id,email,status,message,attempts,target_url,result) VALUES(?,?,?,?,?,?,?,?,?,?)",
        ("legacy-run", 0, "t1", 3, "old@example.com", "success", "", 1, "https://legacy", "ok"),
    )
    conn.commit()
    conn.close()

    store = TaskRuntimeStore(path)
    run = store.load_run("legacy-run")
    assert run is not None
    assert run["schema_version"] == SCHEMA_VERSION == 2
    assert run["workflow_id"] == ""
    results = store.results()
    assert results[0]["workflow_id"] == ""
    assert results[0]["email"] == "old@example.com"

    with sqlite3.connect(path) as check:
        assert "workflow_id" in {row[1] for row in check.execute("PRAGMA table_info(runs)")}
        assert "workflow_id" in {row[1] for row in check.execute("PRAGMA table_info(results)")}


def test_report_export_preserves_workflow_provenance_column(tmp_path: Path):
    import csv
    from vibrapilot.data_io import export_report_csv

    path = tmp_path / "multiworkflow.csv"
    export_report_csv(
        [{
            "timestamp": "t", "slot_id": 1, "workflow_id": "workflow_a",
            "email": "a@example.com", "status": "success", "message": "", "attempts": 1,
            "target_url": "https://example.test", "result": "ok",
        }],
        path,
    )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        assert "workflow_id" in reader.fieldnames
        assert next(reader)["workflow_id"] == "workflow_a"


def test_mainwindow_does_not_overwrite_workspace_while_legacy_workflow_identity_is_unresolved():
    text = (Path(__file__).resolve().parents[1] / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert text.count("self.workspace_store.migration_blocked") >= 2
    recovery_tail = text[text.index("QTimer.singleShot(0, self.offer_task_recovery)") - 220:text.index("QTimer.singleShot(0, self.offer_task_recovery)") + 80]
    assert "self.active_workflow_id" not in recovery_tail


def test_legacy_report_rows_are_labeled_unknown_without_inventing_database_identity():
    text = (Path(__file__).resolve().parents[1] / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert 'display["workflow_id"] = "Legacy / Unknown"' in text
    assert "self._report_display_row(row)" in text
