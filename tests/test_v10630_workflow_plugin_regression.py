from __future__ import annotations

from pathlib import Path

from vibrapilot.workflow import WorkflowManager

ROOT = Path(__file__).resolve().parents[1]
BACKEND = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
QT = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")


def test_share_invite_remains_builtin_and_one_active_workflow_model_remains():
    manager = WorkflowManager.with_builtin_workflows(active_workflow_id="share_invite")
    assert [m.workflow_id for m in manager.list_workflows()] == ["share_invite"]
    assert manager.workflow_origin("share_invite") == "builtin"
    assert manager.active_workflow_id == "share_invite"
    assert 'active_workflow_id=self.app.active_workflow_id' in QT
    assert 'def request_workflow_switch(' in QT


def test_core_browser_and_share_invite_specialized_path_are_retained():
    assert 'self.playwright.chromium.launch_persistent_context' in BACKEND
    assert 'launch_args["channel"] = "chrome"' in BACKEND
    assert 'if self._is_share_invite_workflow()' in BACKEND
    assert 'def _process_generic_workflow_item' in BACKEND
    assert 'workflow_error_decision' in BACKEND
