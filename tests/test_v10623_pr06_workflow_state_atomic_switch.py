from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from vibrapilot.workflow import (
    WorkflowManager,
    WorkflowManifest,
    WorkflowRegistry,
    WorkflowStateCorruptError,
    WorkflowStateStore,
    WorkflowSwitchError,
    WorkflowSwitchTransaction,
)
from _v10636_manifest_fixture import SHARE_INVITE_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "config/verification/v1.0.6.23_pr06_workflow_state_atomic_switch_scope.json"
ALG = "canonical-semantic-ast-v2"


class DummyRuntime:
    def __init__(self, manifest: WorkflowManifest) -> None:
        self.manifest = manifest

    def session_ready(self, page) -> bool:
        return True

    def ensure_session(self) -> None:
        return None

    def execute_item(self, item) -> str:
        return "ok"

    def prepare_retry(self) -> None:
        return None


def _other_manifest() -> WorkflowManifest:
    return WorkflowManifest(
        workflow_id="other_workflow",
        name="Other Workflow",
        description="Synthetic test-only workflow for PR-06 switching infrastructure.",
        version="1.0",
        logo="assets/other.png",
        entrypoint="other_workflow",
    )


def _manager_with_two() -> WorkflowManager:
    other = _other_manifest()
    return WorkflowManager(
        WorkflowRegistry([SHARE_INVITE_MANIFEST, other]),
        runtime_factories={
            "share_invite": lambda *args, **kwargs: DummyRuntime(SHARE_INVITE_MANIFEST),
            "other_workflow": lambda *args, **kwargs: DummyRuntime(other),
        },
    )


def _scope() -> dict:
    return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))


def _canonical(value):
    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            if child is None or child == [] or child == ():
                continue
            fields.append([name, _canonical(child)])
        return [value.__class__.__name__, fields]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _ast_hash(node: ast.AST) -> str:
    payload = json.dumps(
        _canonical(node), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(ALG.encode("ascii") + b"\0" + payload).hexdigest()


def _worker_methods() -> dict[str, ast.AST]:
    tree = ast.parse((ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8"))
    worker = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker"
    )
    return {
        node.name: node
        for node in worker.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_scope_pins_exact_pr05_green_baseline_and_target():
    scope = _scope()
    assert scope["plan_id"] == "VP-PR06-WORKFLOW-STATE-ATOMIC-SWITCH-001"
    assert scope["official_baseline_archive"] == "VibraPilot_v1.0.6.22_Baseline_PR05.zip"
    assert scope["official_baseline_archive_sha256"] == "c5c2e3826cb4de9a1789215325cc95854f06483c87b99ca59ffeb07f3e4416a5"
    assert scope["baseline_github_commit"] == "e5763852249d86db35d9838a61f276eada823f08"
    assert scope["baseline_github_actions_run_id"] == 31389336441
    assert scope["baseline_github_actions_job_id"] == 93457046273
    assert scope["baseline_ci_result"] == "PASS"
    assert scope["baseline_version"] == "1.0.6.22"
    assert scope["target_version"] == "1.0.6.23"


def test_v10636_fresh_state_defaults_to_no_active_workflow(tmp_path: Path):
    path = tmp_path / "workflow_state.json"
    store = WorkflowStateStore(path, manager=_manager_with_two())
    state = store.load_or_migrate()
    assert state.schema_version == 2
    assert state.active_workflow_id is None
    assert state.revision == 1


def test_explicit_legacy_default_migrates_once_to_share_invite(tmp_path: Path):
    path = tmp_path / "workflow_state.json"
    store = WorkflowStateStore(path, manager=_manager_with_two(), default_workflow_id="share_invite")
    state = store.load_or_migrate()
    assert state.schema_version == 2
    assert state.active_workflow_id == "share_invite"
    assert state.revision == 1
    first_bytes = path.read_bytes()
    assert store.load_or_migrate() == state
    assert path.read_bytes() == first_bytes


def test_persisted_workflow_survives_reload_and_revision_increments(tmp_path: Path):
    store = WorkflowStateStore(tmp_path / "workflow_state.json", manager=_manager_with_two(), default_workflow_id="share_invite")
    first = store.load_or_migrate()
    second = store.commit_active_workflow(
        "other_workflow", expected_current_workflow_id=first.active_workflow_id
    )
    assert second.active_workflow_id == "other_workflow"
    assert second.revision == 2
    reloaded = WorkflowStateStore(store.path, manager=_manager_with_two(), default_workflow_id="share_invite").load_existing()
    assert reloaded.active_workflow_id == "other_workflow"
    assert reloaded.revision == 2


def test_corrupt_state_is_quarantined_and_does_not_become_first_run(tmp_path: Path):
    path = tmp_path / "workflow_state.json"
    path.write_text("{broken", encoding="utf-8")
    store = WorkflowStateStore(path, manager=_manager_with_two(), default_workflow_id="share_invite")
    with pytest.raises(WorkflowStateCorruptError):
        store.load_or_migrate()
    assert not path.exists()
    assert list(tmp_path.glob("workflow_state.json.corrupt-*"))
    with pytest.raises(WorkflowStateCorruptError, match="quarantined corrupt state"):
        store.load_or_migrate()


def test_unknown_persisted_workflow_is_quarantined_fail_closed(tmp_path: Path):
    path = tmp_path / "workflow_state.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_workflow_id": "unknown_workflow",
                "revision": 3,
                "updated_at": "2026-08-10T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    store = WorkflowStateStore(path, manager=_manager_with_two(), default_workflow_id="share_invite")
    with pytest.raises(WorkflowStateCorruptError, match="unknown workflow_id"):
        store.load_existing()
    assert not path.exists()
    assert list(tmp_path.glob("workflow_state.json.corrupt-*"))


def test_state_commit_detects_concurrent_current_workflow_change(tmp_path: Path):
    store = WorkflowStateStore(tmp_path / "workflow_state.json", manager=_manager_with_two(), default_workflow_id="share_invite")
    store.load_or_migrate()
    with pytest.raises(WorkflowSwitchError, match="changed during switch"):
        store.commit_active_workflow(
            "other_workflow", expected_current_workflow_id="other_workflow"
        )
    assert store.load_existing().active_workflow_id == "share_invite"


def test_transaction_rollback_restores_exact_file_existence_and_content(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    existing = data / "settings.json"
    existing.write_bytes(b"before")
    absent = data / "state.json"
    tx = WorkflowSwitchTransaction(
        data_root=data,
        transaction_root=data / "WorkflowSwitch",
        old_workflow_id="share_invite",
        target_workflow_id="other_workflow",
    )
    tx.prepare([existing, absent])
    existing.write_bytes(b"after")
    absent.write_bytes(b"created")
    tx.rollback()
    assert existing.read_bytes() == b"before"
    assert not absent.exists()
    assert not tx.path.exists()


def test_prepared_crash_recovery_rolls_back_when_old_workflow_is_authoritative(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager_with_two(), default_workflow_id="share_invite")
    store.load_or_migrate()
    settings = data / "settings.json"
    settings.write_bytes(b"old-settings")
    tx = WorkflowSwitchTransaction(
        data_root=data,
        transaction_root=data / "WorkflowSwitch",
        old_workflow_id="share_invite",
        target_workflow_id="other_workflow",
    )
    tx.prepare([settings])
    settings.write_bytes(b"cleared-settings")
    actions = WorkflowSwitchTransaction.recover_all(
        data_root=data,
        transaction_root=data / "WorkflowSwitch",
        state_store=store,
    )
    assert settings.read_bytes() == b"old-settings"
    assert actions and actions[0].startswith("rolled back prepared transaction")


def test_committed_crash_recovery_keeps_new_data_and_cleans_staging(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    store = WorkflowStateStore(data / "workflow_state.json", manager=_manager_with_two(), default_workflow_id="share_invite")
    store.load_or_migrate()
    settings = data / "settings.json"
    settings.write_bytes(b"old-settings")
    tx = WorkflowSwitchTransaction(
        data_root=data,
        transaction_root=data / "WorkflowSwitch",
        old_workflow_id="share_invite",
        target_workflow_id="other_workflow",
    )
    tx.prepare([settings])
    settings.write_bytes(b"new-workflow-settings")
    store.commit_active_workflow(
        "other_workflow", expected_current_workflow_id="share_invite"
    )
    # Simulate a crash after state commit but before transaction.mark_committed().
    actions = WorkflowSwitchTransaction.recover_all(
        data_root=data,
        transaction_root=data / "WorkflowSwitch",
        state_store=store,
    )
    assert settings.read_bytes() == b"new-workflow-settings"
    assert store.load_existing().active_workflow_id == "other_workflow"
    assert actions and actions[0].startswith("cleaned committed transaction")


def test_transaction_rejects_paths_outside_appdata(tmp_path: Path):
    data = tmp_path / "AppData"
    data.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    tx = WorkflowSwitchTransaction(
        data_root=data,
        transaction_root=data / "WorkflowSwitch",
        old_workflow_id="share_invite",
        target_workflow_id="other_workflow",
    )
    with pytest.raises(WorkflowSwitchError, match="escapes AppData"):
        tx.prepare([outside])
    assert not tx.path.exists()


def test_manager_preflight_requires_explicit_source_controlled_runtime_factory():
    manager = _manager_with_two()
    assert callable(manager.require_runtime_factory("share_invite"))
    without_runtime = WorkflowManager(
        WorkflowRegistry([SHARE_INVITE_MANIFEST]), runtime_factories={}
    )
    with pytest.raises(Exception, match="no validated runtime"):
        without_runtime.require_runtime_factory("share_invite")


def test_backend_worker_has_no_hardcoded_share_invite_fallback():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert "active_workflow_id: str | None = None" in source
    assert "active_workflow_id=active_workflow_id" in source
    assert 'active_workflow_id="share_invite"' not in source


def test_qt_injects_authoritative_task_workflow_into_worker():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert 'APP_DATA_DIR / "workflow_state.json"' in source
    # v1.0.6.42 intentionally supersedes the PR-06 global run identity: the
    # persisted app workflow is now only the default for new Tasks.
    assert "active_workflow_id=self.workflow_id" in source
    assert "workflow_manager=self.app.workflow_catalog.for_active_workflow(self.workflow_id)" in source
    assert "WorkflowSwitchTransaction.recover_all(" in source
    assert "def request_workflow_switch(" in source
    assert "def request_default_workflow_switch(" in source


def test_same_workflow_is_noop_before_confirmation_or_mutation():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    method = next(
        n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "request_workflow_switch"
    )
    segment = ast.get_source_segment(source, method) or ""
    # v1.0.6.42+ supersedes destructive global switching: the historical service
    # remains as a compatibility wrapper over the restart-free default workflow.
    assert "request_default_workflow_switch(target)" in segment
    assert "if target != self.active_workflow_id:" in segment
    assert "_spawn_workflow_restart" not in segment
    assert "_clear_workflow_scoped_state" not in segment

def test_switch_blockers_confirmation_commit_and_restart_order_are_present():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
    methods = {
        n.name: ast.get_source_segment(source, n) or ""
        for n in cls.body if isinstance(n, ast.FunctionDef)
    }
    switch = methods["request_workflow_switch"]
    assert "_workflow_runtime_error_for(target)" in switch
    assert "_confirm_default_workflow_switch(target)" in switch
    assert "request_default_workflow_switch(target)" in switch
    assert "_spawn_workflow_restart" not in switch
    # Historical destructive transaction primitives remain only for explicit
    # workflow-state recovery compatibility, not normal Phase-2 switching.
    recovery = methods["request_workflow_state_recovery"]
    for marker in (
        "_settle_workflow_workers()",
        "transaction.prepare(",
        "_clear_workflow_scoped_state(",
        "transaction.mark_committed()",
        "_spawn_workflow_restart()",
    ):
        assert marker in recovery

def test_clear_policy_is_explicit_and_preserve_paths_are_not_deleted():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    main_window = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    methods = {
        node.name: node
        for node in main_window.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    switch_paths = ast.get_source_segment(source, methods["_workflow_switch_paths"]) or ""
    clear_state = ast.get_source_segment(source, methods["_clear_workflow_scoped_state"]) or ""
    switch_boundary = switch_paths + "\n" + clear_state

    for marker in (
        'Path(str(TASK_RUNTIME_DB) + "-wal")',
        'Path(str(TASK_RUNTIME_DB) + "-shm")',
        'APP_DATA_DIR.glob("slot_*_checkpoint.json")',
        "for key in WORKFLOW_INPUT_KEYS",
        '"active_tasks": []',
        '"next_slot_id": 1',
    ):
        assert marker in switch_boundary

    for forbidden_delete in (
        "LICENSE_FILE.unlink",
        "DEVICE_IDENTITY_FILE.unlink",
        "REPORTS_DIR",
        "FAILED_DATA_DIR",
        "LOGS_DIR",
        "BrowserProfiles",
        "Downloads",
        "Extensions",
    ):
        assert forbidden_delete not in switch_boundary


def test_v10636_registry_has_no_fake_or_builtin_production_workflow():
    registry = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    assert "other_workflow" not in registry
    assert "SHARE_INVITE_MANIFEST" not in registry
    assert "return ()" in registry


def test_frozen_out_of_scope_files_are_byte_identical_to_v10622_baseline():
    pr08_authorized_supersession = {"src/vibrapilot/workflow_inputs.py"}
    # v1.0.6.42 approved Phase-2 successor surface; all other PR-06 frozen hashes remain enforced.
    v10642_authorized_supersession = {
        "src/vibrapilot/backend.py",
        "src/vibrapilot/qt_app.py",
        "src/vibrapilot/task_runtime_store.py",
        "src/vibrapilot/workspace_state.py",
        "src/vibrapilot/workflow/__init__.py",
        "src/vibrapilot/workflow/plugin_loader.py",
        "src/vibrapilot/workflow/state.py",
    }
    v10630_path = ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json"
    v10630 = json.loads(v10630_path.read_text(encoding="utf-8")) if v10630_path.is_file() else {}
    v10631_path = ROOT / "config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json"
    v10631 = json.loads(v10631_path.read_text(encoding="utf-8")) if v10631_path.is_file() else {}
    v10636_path = ROOT / "config/verification/v1.0.6.36_share_invite_externalization_scope.json"
    v10636 = json.loads(v10636_path.read_text(encoding="utf-8")) if v10636_path.is_file() else {}
    current_authorized = (
        pr08_authorized_supersession
        | v10642_authorized_supersession
        | set(v10630.get("allowed_production_source_changes", []))
        | set(v10630.get("authorized_nonproduction_files", []))
        | set(v10631.get("allowed_production_source_changes", []))
        | set(v10631.get("authorized_nonproduction_files", []))
        | set(v10636.get("allowed_production_source_changes", []))
        | set(v10636.get("authorized_nonproduction_files", []))
        | set(v10636.get("deleted_production_paths", []))
    )
    for relative, expected in _scope()["frozen_file_sha256"].items():
        if relative in current_authorized:
            continue
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, relative


def test_safety_critical_worker_methods_remain_baseline_identical():
    methods = _worker_methods()
    current_path = ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json"
    current = json.loads(current_path.read_text(encoding="utf-8")) if current_path.is_file() else {}
    v10631_path = ROOT / "config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json"
    v10631 = json.loads(v10631_path.read_text(encoding="utf-8")) if v10631_path.is_file() else {}
    authorized_methods = (
        set(current.get("authorized_automationworker_method_changes", []))
        | set(v10631.get("authorized_automationworker_method_changes", []))
        # v1.0.6.42 adds only workflow provenance to report_row; other frozen
        # AutomationWorker safety methods remain byte/AST protected here.
        | {"report_row"}
    )
    for name, expected in _scope()["frozen_automationworker_method_canonical_ast_sha256"].items():
        if name in authorized_methods:
            continue
        assert _ast_hash(methods[name]) == expected, name


def test_scope_forbids_schema_browser_licensing_plugin_and_captcha_changes():
    scope = _scope()
    for key in (
        "no_new_ui_page",
        "no_workflow_showcase_ui",
        "no_dynamic_workflow_inputs",
        "no_task_database_schema_change",
        "no_workspace_schema_change",
        "no_report_schema_change",
        "no_browser_change",
        "no_dependency_change",
        "no_licensing_change",
        "captcha_out_of_scope",
        "external_plugin_loading_prohibited",
        "manifest_controlled_dynamic_import_prohibited",
    ):
        assert scope[key] is True
