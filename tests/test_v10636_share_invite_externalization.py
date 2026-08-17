from __future__ import annotations

import json
from pathlib import Path

from vibrapilot.workflow.manager import WorkflowManager
from vibrapilot.workflow.registry import builtin_workflow_manifests, builtin_workflow_runtime_factories
from vibrapilot.workflow.state import WORKFLOW_STATE_SCHEMA_VERSION, WorkflowStateStore

ROOT = Path(__file__).resolve().parents[1]


def test_core_has_zero_builtin_workflows():
    assert builtin_workflow_manifests() == ()
    assert builtin_workflow_runtime_factories() == {}
    assert WorkflowManager.with_builtin_workflows().list_workflows() == ()


def test_fresh_zero_workflow_state_is_valid(tmp_path: Path):
    store = WorkflowStateStore(tmp_path / "workflow_state.json", manager=WorkflowManager())
    state = store.load_or_migrate()
    assert WORKFLOW_STATE_SCHEMA_VERSION == 2
    assert state.active_workflow_id is None
    assert state.revision == 1
    assert store.load_existing().active_workflow_id is None


def test_legacy_share_invite_state_migrates_without_quarantine_when_package_missing(tmp_path: Path):
    path = tmp_path / "workflow_state.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_workflow_id": "share_invite",
                "revision": 7,
                "updated_at": "2026-08-15T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    store = WorkflowStateStore(path, manager=WorkflowManager())
    state = store.load_or_migrate()
    assert state.schema_version == 2
    assert state.active_workflow_id == "share_invite"
    assert state.revision == 7
    assert not list(tmp_path.glob("workflow_state.json.corrupt-*"))
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 2
    assert persisted["active_workflow_id"] == "share_invite"


def test_core_source_contains_no_share_invite_runtime_import_or_implicit_task_fallback():
    backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    qt = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    registry = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    manager = (ROOT / "src/vibrapilot/workflow/manager.py").read_text(encoding="utf-8")
    assert "from .workflow.share_invite" not in backend
    assert "ShareInviteWorkflow" not in backend
    assert 'or "share_invite"' not in qt
    assert "SHARE_INVITE_MANIFEST" not in registry
    assert '"share_invite": share_' not in manager


def test_source_controlled_share_invite_runtime_directory_is_removed():
    assert not (ROOT / "src/vibrapilot/workflow/share_invite").exists()


def test_plugin_manager_can_be_empty_and_can_load_only_external_plugins(tmp_path: Path):
    manager = WorkflowManager.with_available_workflows(workflow_root=tmp_path)
    assert manager.list_workflows() == ()
    assert manager.active_workflow_id is None


def _dummy_manager(workflow_id: str = "dummy_flow") -> WorkflowManager:
    from vibrapilot.workflow.contracts import WorkflowManifest
    from vibrapilot.workflow.registry import WorkflowRegistry
    from vibrapilot.workflow.schemas import WorkflowFormSchema, WorkflowTaskSchema

    manifest = WorkflowManifest(
        workflow_id=workflow_id,
        name="Dummy Flow",
        description="Dummy workflow for v1.0.6.36 state tests.",
        version="1.0",
        logo="assets/logo.png",
        entrypoint="create_workflow",
    )

    class Runtime:
        def __init__(self, host=None, **_kwargs):
            self.host = host

        def session_ready(self, page):
            return True

        def ensure_session(self):
            return None

        def execute_item(self, item):
            return "ok"

        def prepare_retry(self):
            return None

    Runtime.manifest = manifest

    return WorkflowManager(
        WorkflowRegistry((manifest,)),
        runtime_factories={workflow_id: Runtime},
        input_schemas={workflow_id: WorkflowFormSchema(workflow_id, "Inputs", ())},
        settings_schemas={workflow_id: WorkflowFormSchema(workflow_id, "Settings", ())},
        task_schemas={workflow_id: WorkflowTaskSchema(workflow_id, "Task", ())},
        workflow_origins={workflow_id: "plugin"},
    )


def test_valid_zero_workflow_state_cannot_be_overwritten_through_recovery(tmp_path: Path):
    from vibrapilot.workflow.contracts import WorkflowStateError

    manager = _dummy_manager()
    store = WorkflowStateStore(tmp_path / "workflow_state.json", manager=manager)
    state = store.load_or_migrate()
    assert state.active_workflow_id is None
    try:
        store.recover_active_workflow("dummy_flow")
    except WorkflowStateError as exc:
        assert "valid canonical state already exists" in str(exc)
    else:  # pragma: no cover - fail-closed guard
        raise AssertionError("valid zero-workflow state was overwritten by recovery")
    assert store.load_existing().active_workflow_id is None


def test_first_activation_from_none_is_atomic_commit_not_recovery(tmp_path: Path):
    manager = _dummy_manager()
    store = WorkflowStateStore(tmp_path / "workflow_state.json", manager=manager)
    original = store.load_or_migrate()
    activated = store.commit_active_workflow(
        "dummy_flow", expected_current_workflow_id=None
    )
    assert original.active_workflow_id is None
    assert activated.active_workflow_id == "dummy_flow"
    assert activated.revision == original.revision + 1
    assert store.load_existing() == activated


def test_unknown_nonlegacy_workflow_state_remains_fail_closed_and_quarantined(tmp_path: Path):
    from vibrapilot.workflow.contracts import WorkflowStateCorruptError

    path = tmp_path / "workflow_state.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "active_workflow_id": "unknown_flow",
                "revision": 2,
                "updated_at": "2026-08-15T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    store = WorkflowStateStore(path, manager=WorkflowManager())
    try:
        store.load_or_migrate()
    except WorkflowStateCorruptError as exc:
        assert "unknown workflow_id" in str(exc)
        assert "quarantined as" in str(exc)
    else:  # pragma: no cover - fail-closed guard
        raise AssertionError("unknown non-legacy workflow state was accepted")
    assert not path.exists()
    assert len(list(tmp_path.glob("workflow_state.json.corrupt-*"))) == 1


def test_generic_rich_task_data_hook_preserves_metadata_and_validates_rows(tmp_path: Path):
    from vibrapilot.workflow.contracts import WorkflowManifest
    from vibrapilot.workflow.registry import WorkflowRegistry

    manifest = WorkflowManifest(
        workflow_id="rich_flow",
        name="Rich Flow",
        description="Rich loader test.",
        version="1.0",
        logo="assets/logo.png",
        entrypoint="create_workflow",
    )
    manager = WorkflowManager(
        WorkflowRegistry((manifest,)),
        task_data_loaders={
            "rich_flow": lambda path, task_values, context: {
                "items": [{"email": "person@example.com", "row": 1}],
                "source_fingerprint": "sha256:test",
                "summary": "one valid row",
            }
        },
    )
    loaded = manager.load_task_data(
        "rich_flow", tmp_path / "data.txt", {}, context={"remove_duplicates": True}
    )
    assert loaded == (
        [{"email": "person@example.com", "row": 1}],
        "sha256:test",
        "one valid row",
    )


def test_plugin_api1_legacy_task_item_loader_remains_supported(tmp_path: Path):
    from vibrapilot.workflow.contracts import WorkflowManifest
    from vibrapilot.workflow.registry import WorkflowRegistry

    manifest = WorkflowManifest(
        workflow_id="legacy_loader",
        name="Legacy Loader",
        description="API1 loader fallback test.",
        version="1.0",
        logo="assets/logo.png",
        entrypoint="create_workflow",
    )
    manager = WorkflowManager(
        WorkflowRegistry((manifest,)),
        task_item_loaders={
            "legacy_loader": lambda path, task_values: [
                {"email": "legacy@example.com"}
            ]
        },
    )
    loaded = manager.load_task_data("legacy_loader", tmp_path / "data.txt", {})
    assert loaded == ([{"email": "legacy@example.com"}], None, None)


def test_share_invite_is_not_reserved_by_core_anymore():
    from vibrapilot.workflow.registry import builtin_workflow_manifests

    reserved = {item.workflow_id for item in builtin_workflow_manifests()}
    assert "share_invite" not in reserved


def test_backend_uses_optional_workflow_processing_hook_and_generic_fallback():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert 'hook = getattr(runtime, "process_item", None)' in source
    assert "hook(index, item)" in source
    assert "self._process_generic_workflow_item(index, item)" in source
    assert "def _is_share_invite_workflow" not in source
    assert "def _share_invite_runtime" not in source


def test_missing_externalized_package_is_recoverable_not_corrupt_ui_state():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert "Workflow package required" in source
    assert "Install the matching trusted .vpworkflow package" in source



def test_worker_start_preflight_uses_generic_workflow_session_gate():
    """P0 regression: Start must not call the removed Share Invite compatibility alias."""
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert "self.ensure_authenticated_test_session()" not in source
    assert "self.ensure_workflow_session()" in source


def test_automation_worker_has_no_dangling_direct_self_method_calls():
    """Catch extraction regressions where a removed worker method is still called directly."""
    import ast

    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    worker = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker"
    )
    methods = {
        node.name
        for node in worker.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    direct_self_calls = {
        node.func.attr
        for node in ast.walk(worker)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
    }
    dangling = sorted(direct_self_calls - methods)
    assert dangling == []
