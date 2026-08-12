from __future__ import annotations

import ast
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

def test_mainwindow_bound_method_descriptors_are_consistent():
    """Prevent startup crashes from instance-bound helper signature/decorator drift."""
    tree = ast.parse(QT)
    main_window = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "MainWindow"
    )
    methods = {
        node.name: node
        for node in main_window.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    self_calls = {
        node.func.attr
        for node in ast.walk(main_window)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
    }
    invalid = []
    for name in sorted(self_calls):
        method = methods.get(name)
        if method is None:
            continue
        decorators = {ast.unparse(value) for value in method.decorator_list}
        args = [arg.arg for arg in method.args.args]
        if "staticmethod" in decorators or "classmethod" in decorators:
            continue
        if not args or args[0] != "self":
            invalid.append((name, args, sorted(decorators)))
    assert invalid == []
    helper = methods["_transaction_root_has_directories"]
    assert [ast.unparse(value) for value in helper.decorator_list] == ["staticmethod"]
    assert [arg.arg for arg in helper.args.args] == ["root"]
