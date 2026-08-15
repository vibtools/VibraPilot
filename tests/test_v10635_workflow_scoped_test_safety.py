from pathlib import Path

from vibrapilot.workflow.manager import WorkflowManager
from vibrapilot.workflow.settings_state import WorkflowSettingsStateStore

ROOT = Path(__file__).resolve().parents[1]
QT = (ROOT / 'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
BACKEND = (ROOT / 'src/vibrapilot/backend.py').read_text(encoding='utf-8')
SHARE = (ROOT / 'src/vibrapilot/workflow/share_invite/workflow.py').read_text(encoding='utf-8')
RUNTIME_STORE = (ROOT / 'src/vibrapilot/task_runtime_store.py').read_text(encoding='utf-8')


def test_share_invite_send_limit_is_workflow_setting():
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id='share_invite')
    schema = manager.settings_schema('share_invite')
    field = schema.field_map()['max_test_send_limit']
    assert field.kind == 'integer'
    assert field.default == 50
    assert field.minimum == 0


def test_workflow_settings_store_can_persist_share_invite_limit(tmp_path: Path):
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id='share_invite')
    store = WorkflowSettingsStateStore(
        tmp_path / 'workflow_settings.json',
        schema_resolver=manager.settings_schema,
    )
    state = store.save_workflow_values('share_invite', {'max_test_send_limit': 321}, coerce=False)
    assert store.values_for('share_invite', state=state)['max_test_send_limit'] == 321


def test_global_authorized_testing_gate_is_removed_from_task_start_and_app_settings():
    assert 'Enable authorized testing mode in App Settings before running automation.' not in QT
    assert '"Test Safety Settings": ["authorized_testing_only", "max_test_send_limit"]' not in QT


def test_sidebar_is_workflow_neutral():
    assert 'Vib Tools • Authorized Test Mode' not in QT
    assert 'Vib Tools • Authorized Automation' in QT


def test_core_session_wording_is_workflow_neutral():
    assert 'Authenticated Test Mode page verified.' not in BACKEND
    assert 'Open the authenticated Target URL in Test Mode.' not in BACKEND
    assert 'self.emit("status", {"status": "Login Required"})' in BACKEND
    assert 'Workflow session verified.' in BACKEND


def test_share_invite_real_test_mode_enforcement_is_preserved():
    assert 'def assert_test_mode' in SHARE
    assert 'Test Mode banner is required before every Send operation.' in SHARE
    assert 'Authenticated Test Mode page verified.' in SHARE


def test_worker_send_limit_reads_workflow_settings_snapshot():
    assert 'self.workflow_settings_values.get("max_test_send_limit"' in BACKEND


def test_login_required_is_recoverable_without_test_mode_language():
    assert '"Login/Test Mode Required"' in RUNTIME_STORE  # legacy persisted runs remain recoverable


def test_task_widget_send_limit_resolution_keeps_lightweight_host_compatibility():
    assert 'def _resolved_test_send_limit(self) -> int:' in QT
    assert 'getattr(self.app, "workflow_test_send_limit", None)' in QT
    assert 'if not self.task_schema.uses_test_send_limit:' in QT
    assert 'getter("max_test_send_limit", DEFAULT_TEST_SEND_LIMIT)' in QT
    assert 'self.app.workflow_test_send_limit(self.workflow_id)' not in QT
