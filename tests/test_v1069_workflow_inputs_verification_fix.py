from __future__ import annotations

import ast
import json
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src" / "vibrapilot" / "qt_app.py"
QT_TEXT = QT_PATH.read_text(encoding="utf-8")
QT_TREE = ast.parse(QT_TEXT, filename=str(QT_PATH))
KEYS = ("default_full_name", "default_number", "fallback_name", "update_click_count")
DEFAULTS = {key: "" for key in KEYS}


def _method_node(name: str) -> ast.FunctionDef:
    cls = next(node for node in QT_TREE.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _compiled_method(name: str, *, confirm: bool = True, messages: list | None = None):
    node = _method_node(name)
    isolated = ast.Module(body=[node], type_ignores=[])
    ast.fix_missing_locations(isolated)
    captured = messages if messages is not None else []

    def _message(_self, title, message, level="info"):
        captured.append((title, str(message), level))

    def _confirm(*_args, **_kwargs):
        return confirm

    namespace = {
        "WORKFLOW_INPUT_KEYS": KEYS,
        "DEFAULT_SETTINGS": DEFAULTS,
        "_message": _message,
        "_confirm": _confirm,
        "Any": object,
    }
    exec(compile(isolated, str(QT_PATH), "exec"), namespace)
    return namespace[name]


class _FailingSettings:
    def __init__(self, values):
        self.data = dict(values)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def save(self):
        raise PermissionError("synthetic settings write failure")


class _FakeWindow:
    def __init__(self, values):
        self.settings = _FailingSettings(values)
        self.workflow_input_widgets = {key: f"new-{key}" for key in KEYS}
        self.refresh_count = 0
        self.logs = []

    def _widget_value(self, _key, widget):
        return widget

    def parse_setting_value(self, _key, value):
        return value

    def refresh_workflow_input_widgets(self):
        self.refresh_count += 1

    def log_ui(self, message):
        self.logs.append(message)


class V1069WorkflowInputsVerificationFixTest(unittest.TestCase):
    def test_save_failure_restores_preexisting_in_memory_values_and_surfaces_error(self):
        old = {key: f"old-{key}" for key in KEYS}
        window = _FakeWindow(old)
        messages = []
        method = types.MethodType(_compiled_method("save_workflow_inputs", messages=messages), window)

        method()

        self.assertEqual(window.settings.data, old)
        self.assertEqual(window.refresh_count, 1)
        self.assertFalse(window.logs)
        self.assertTrue(messages)
        self.assertEqual(messages[-1][0], "Workflow Inputs error")
        self.assertEqual(messages[-1][2], "error")

    def test_reset_failure_is_caught_and_restores_preexisting_values(self):
        old = {key: f"old-{key}" for key in KEYS}
        window = _FakeWindow(old)
        messages = []
        method = types.MethodType(_compiled_method("reset_workflow_inputs", messages=messages), window)

        method()

        self.assertEqual(window.settings.data, old)
        self.assertEqual(window.refresh_count, 1)
        self.assertFalse(window.logs)
        self.assertTrue(messages)
        self.assertEqual(messages[-1][0], "Workflow Inputs error")
        self.assertEqual(messages[-1][2], "error")

    def test_reset_cancel_does_not_mutate_or_attempt_persistence(self):
        old = {key: f"old-{key}" for key in KEYS}
        window = _FakeWindow(old)
        messages = []
        method = types.MethodType(
            _compiled_method("reset_workflow_inputs", confirm=False, messages=messages), window
        )

        method()

        self.assertEqual(window.settings.data, old)
        self.assertEqual(window.refresh_count, 0)
        self.assertFalse(messages)


    def test_v1069_scope_locks_exact_github_v1068_baseline_and_runtime_surface(self):
        scope = ROOT / "config" / "verification" / "v1.0.6.9_workflow_inputs_verification_fix_scope.json"
        data = json.loads(scope.read_text(encoding="utf-8"))
        self.assertEqual(
            data["official_baseline_github_commit"],
            "82fc678fe4d3e8aab9c11ff3e54cf4455e0d3203",
        )
        self.assertEqual(
            data["official_baseline_tree_fingerprint"],
            "8358ffdca13bedd491ee319aae299fdf9ff636e6cb74caf7dbb53c389d94f6b7",
        )
        self.assertEqual(data["target_version"], "1.0.6.9")
        self.assertEqual(data["allowed_runtime_source_changes"], ["src/vibrapilot/qt_app.py"])
        self.assertEqual(
            set(data["approved_mainwindow_method_changes"]),
            {"save_workflow_inputs", "reset_workflow_inputs"},
        )

    def test_v1068_historical_scope_and_workflow_metadata_remain_present(self):
        historical = ROOT / "config" / "verification" / "v1.0.6.8_workflow_inputs_scope.json"
        self.assertTrue(historical.is_file())
        data = json.loads(historical.read_text(encoding="utf-8"))
        self.assertEqual(data["target_version"], "1.0.6.8")
        metadata = (ROOT / "src" / "vibrapilot" / "workflow_inputs.py").read_text(encoding="utf-8")
        self.assertNotIn("workflow_selector", metadata)
        self.assertNotIn("default_target_url", metadata)


if __name__ == "__main__":
    unittest.main()
