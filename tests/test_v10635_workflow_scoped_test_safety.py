from pathlib import Path

from vibrapilot.workflow.manager import WorkflowManager
from vibrapilot.workflow.schemas import WorkflowFieldSchema, WorkflowFormSchema
from vibrapilot.workflow.settings_state import WorkflowSettingsStateStore

ROOT = Path(__file__).resolve().parents[1]
QT = (ROOT / 'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
BACKEND = (ROOT / 'src/vibrapilot/backend.py').read_text(encoding='utf-8')
SCHEMAS = (ROOT / 'src/vibrapilot/workflow/schemas.py').read_text(encoding='utf-8')
RUNTIME_STORE = (ROOT / 'src/vibrapilot/task_runtime_store.py').read_text(encoding='utf-8')


def _share_settings_fixture() -> WorkflowFormSchema:
    """Metadata-only fixture preserving the v1.0.6.35 settings contract."""
    return WorkflowFormSchema(
        workflow_id='share_invite',
        title='Share Invite Settings',
        fields=(
            WorkflowFieldSchema(
                key='max_test_send_limit',
                label='Max Test Send Limit',
                kind='integer',
                default=50,
                minimum=0,
                maximum=500000,
            ),
        ),
    )


def test_v10636_supersedes_builtin_share_settings_authority():
    assert WorkflowManager.with_builtin_workflows().list_workflows() == ()
    assert 'builtin_share_invite_settings_schema' not in SCHEMAS
    assert 'builtin_share_invite_task_schema' not in SCHEMAS


def test_workflow_settings_store_still_persists_external_share_limit(tmp_path: Path):
    schema = _share_settings_fixture()
    store = WorkflowSettingsStateStore(
        tmp_path / 'workflow_settings.json',
        schema_resolver=lambda workflow_id: schema if workflow_id == 'share_invite' else None,
    )
    state = store.save_workflow_values('share_invite', {'max_test_send_limit': 321}, coerce=False)
    assert store.values_for('share_invite', state=state)['max_test_send_limit'] == 321


def test_global_authorized_testing_gate_remains_removed_from_task_start_and_app_settings():
    assert 'Enable authorized testing mode in App Settings before running automation.' not in QT
    assert '"Test Safety Settings": ["authorized_testing_only", "max_test_send_limit"]' not in QT


def test_sidebar_remains_workflow_neutral():
    assert 'Vib Tools • Authorized Test Mode' not in QT
    assert 'Vib Tools • Authorized Automation' in QT


def test_core_session_wording_remains_workflow_neutral():
    assert 'Authenticated Test Mode page verified.' not in BACKEND
    assert 'Open the authenticated Target URL in Test Mode.' not in BACKEND
    assert 'Workflow session verified.' in BACKEND


def test_v10636_moves_real_test_mode_enforcement_out_of_core():
    assert not (ROOT / 'src/vibrapilot/workflow/share_invite/workflow.py').exists()
    assert 'def assert_test_mode' not in BACKEND
    assert 'ShareInviteWorkflow' not in BACKEND


def test_worker_send_limit_still_reads_workflow_settings_snapshot():
    assert 'self.workflow_settings_values.get("max_test_send_limit"' in BACKEND


def test_legacy_login_test_mode_status_remains_recoverable():
    assert '"Login/Test Mode Required"' in RUNTIME_STORE


def test_task_widget_send_limit_resolution_keeps_lightweight_host_compatibility():
    assert 'def _resolved_test_send_limit(self) -> int:' in QT
    assert 'getattr(self.app, "workflow_test_send_limit", None)' in QT
    assert 'if not self.task_schema.uses_test_send_limit:' in QT
    assert 'getter("max_test_send_limit", DEFAULT_TEST_SEND_LIMIT)' in QT
    assert 'self.app.workflow_test_send_limit(self.workflow_id)' not in QT
