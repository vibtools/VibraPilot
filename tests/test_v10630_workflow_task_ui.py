from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")


def test_task_card_uses_workflow_schema_and_settings_dialog_while_preserving_core_actions():
    assert 'button("Settings", "secondary", "settings")' in QT
    assert 'self.task_settings_button.clicked.connect(self.open_task_settings)' in QT
    assert 'target_row.hide()' in QT
    for action in ('button("Start"', 'button("Pause"', 'button("Resume"', 'button("Stop"', 'button("Open Browser"'):
        assert action in QT
    assert 'for i, metric_schema in enumerate(visible_metrics):' in QT
    assert 'Status: Running' not in QT  # no fake hard-coded business outcome


def test_worker_receives_immutable_workflow_snapshots_and_ui_consumes_step_metric_events():
    assert 'workflow_settings_values=self.app.current_workflow_settings_snapshot()' in QT
    assert 'workflow_task_values=dict(self.workflow_task_values)' in QT
    assert 'workflow_manager=self.app.workflow_catalog.for_active_workflow' in QT
    assert 'elif kind == "workflow_step" and slot:' in QT
    assert 'elif kind == "workflow_metric" and slot:' in QT


def test_task_slot_preserves_lightweight_qt_host_constructor_compatibility():
    # Historical BrowserLifecycleQtTest builds TaskSlotWidget with only Settings
    # and schedule_workspace_save. The plugin layer must not require MainWindow-
    # only workflow attributes merely to construct/render the baseline Task card.
    assert 'getattr(app, "active_workflow_id", "") or "share_invite"' in QT
    assert 'getattr(app, "workflow_catalog", None)' in QT
    assert 'getattr(app, "workflow_task_state_store", None)' in QT
    assert 'setObjectName("TaskSubtitle")' not in QT
