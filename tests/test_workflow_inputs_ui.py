from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src" / "vibrapilot" / "qt_app.py"
QT_TEXT = QT_PATH.read_text(encoding="utf-8")
QT_TREE = ast.parse(QT_TEXT, filename=str(QT_PATH))


def _assignment(name: str):
    for node in QT_TREE.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"missing assignment: {name}")


def _main_window_method(name: str) -> ast.FunctionDef:
    cls = next(node for node in QT_TREE.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _source(name: str) -> str:
    return ast.get_source_segment(QT_TEXT, _main_window_method(name)) or ""


class WorkflowInputsUiTest(unittest.TestCase):
    EXPECTED_KEYS = (
        "default_full_name",
        "default_number",
        "fallback_name",
        "update_click_count",
    )

    def test_navigation_adds_real_workflow_inputs_page_without_shifting_existing_shortcuts(self):
        self.assertEqual(
            _assignment("NAV_SECTIONS"),
            (["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Workflow Settings", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]
             if (ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json").is_file()
             else ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]),
        )
        self.assertEqual(
            _assignment("VIEW_NAV_SHORTCUTS"),
            {
                "Dashboard": "Ctrl+1",
                "Tasks": "Ctrl+2",
                "Reports": "Ctrl+3",
                "Live Logs": "Ctrl+4",
                "App Settings": "Ctrl+5",
                "Browser Settings": "Ctrl+6",
            },
        )
        register = _source("_register_pages")
        self.assertIn('(\"Workflow Inputs\", self.make_workflow_inputs_page)', register)

    def test_app_settings_no_longer_owns_workflow_fields_and_keeps_default_target_url(self):
        source = _source("make_settings_page")
        for key in self.EXPECTED_KEYS:
            self.assertNotIn(key, source)
        self.assertNotIn("Legacy Contact Settings (Preserved)", source)
        if (ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json").is_file():
            self.assertNotIn("default_target_url", source)
        else:
            self.assertIn("default_target_url", source)

    def test_workflow_page_is_dynamic_without_fake_selector(self):
        source = _source("make_workflow_inputs_page") + _source("refresh_workflow_input_widgets")
        self.assertIn('page_header(\n                "Workflow Inputs"', source)
        self.assertIn("schema.fields", source)
        self.assertNotIn("WORKFLOW_INPUT_FIELDS", source)
        if (ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json").is_file():
            self.assertIn("workflow_input_selector", source)
        else:
            self.assertNotIn("Workflow:", source)
        self.assertNotIn("default_target_url", source)

    def test_save_and_reset_delegate_to_per_workflow_persistence_only(self):
        save_source = _source("save_workflow_inputs")
        reset_source = _source("reset_workflow_inputs")
        persist_source = _source("_persist_workflow_input_values") if (ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json").is_file() else _source("_persist_active_workflow_input_values")
        self.assertIn("_collect_workflow_input_values", save_source)
        self.assertIn("schema.defaults()", reset_source)
        self.assertIn("save_workflow_values", persist_source)
        self.assertNotIn("default_target_url", save_source + reset_source + persist_source)
        self.assertNotIn("browser_setting_widgets", save_source + reset_source + persist_source)
        self.assertNotIn("setting_widgets", save_source + reset_source + persist_source)


if __name__ == "__main__":
    unittest.main()
