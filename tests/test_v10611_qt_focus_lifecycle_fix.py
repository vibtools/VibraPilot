from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOCUS = ROOT / "vib_validation_app" / "focus_manager.py"
SCOPE = ROOT / "config" / "verification" / "v1.0.6.11_qt_focus_lifecycle_fix_scope.json"


class V10611FocusLifecycleStaticTest(unittest.TestCase):
    def test_scope_locks_exact_v10610_baseline_and_runtime_surface(self):
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
        self.assertEqual(data["plan_id"], "VP-QT-FOCUS-LIFECYCLE-001")
        self.assertEqual(data["target_version"], "1.0.6.11")
        self.assertEqual(
            data["official_baseline_github_commit"],
            "d712a9d04fa62e5e3a0df9c00a99c1315052bd05",
        )
        self.assertEqual(
            data["official_baseline_archive_sha256"],
            "d818aa1d4ee3492df810fb29034999293b47c343444469b32ceebbbb92f5e044",
        )
        self.assertEqual(data["allowed_runtime_source_changes"], ["vib_validation_app/focus_manager.py"])
        self.assertTrue(data["preserve_visual_focus_behavior"])
        self.assertTrue(data["preserve_frozen_design_tokens"])
        self.assertTrue(data["no_new_dependency"])
        self.assertTrue(data["no_ui_redesign"])

    def test_focus_manager_approved_hash_and_lifetime_guards(self):
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
        actual = hashlib.sha256(FOCUS.read_bytes()).hexdigest()
        self.assertEqual(actual, data["approved_focus_manager_sha256"])
        text = FOCUS.read_text(encoding="utf-8")
        self.assertIn("from shiboken6 import isValid", text)
        self.assertIn("def _is_live_widget", text)
        self.assertIn("QEvent.Type.Destroy", text)
        self.assertIn("QEvent.Type.DeferredDelete", text)
        self.assertIn("if not self._is_live_widget(widget):", text)
        self.assertNotIn("except Exception:", text)

    def test_visual_focus_contract_is_unchanged_in_source(self):
        text = FOCUS.read_text(encoding="utf-8")
        self.assertIn('widget.setProperty("keyboardFocus", "true" if enabled else "false")', text)
        self.assertIn("style.unpolish(widget)", text)
        self.assertIn("style.polish(widget)", text)
        self.assertIn("widget.update()", text)
        self.assertIn("QTimer.singleShot(180", text)

    def test_frozen_out_of_scope_files_match_baseline_hashes(self):
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
        current_scope = ROOT / "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json"
        current_phase_scope = ROOT / "config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json"
        pr08_scope = ROOT / "config/verification/v1.0.6.25_pr08_dynamic_workflow_inputs_scope.json"
        current_allowed = set()
        if current_scope.is_file():
            current_allowed |= set(json.loads(current_scope.read_text(encoding="utf-8")).get("allowed_runtime_source_changes", []))
        if current_phase_scope.is_file():
            current_allowed |= set(json.loads(current_phase_scope.read_text(encoding="utf-8")).get("allowed_runtime_source_changes", []))
        if pr08_scope.is_file():
            current_allowed |= set(json.loads(pr08_scope.read_text(encoding="utf-8")).get("allowed_production_source_changes", []))
        for relative, expected in data["frozen_file_sha256"].items():
            if relative in current_allowed:
                continue
            with self.subTest(relative=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), relative)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected, relative)

    def test_focus_manager_changes_are_limited_to_lifetime_methods(self):
        tree = ast.parse(FOCUS.read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "KeyboardFocusRingManager")
        methods = {node.name for node in cls.body if isinstance(node, ast.FunctionDef)}
        self.assertIn("_is_live_widget", methods)
        self.assertIn("_set_keyboard_focus", methods)
        self.assertIn("_show_focus_tooltip", methods)
        self.assertIn("_apply_property", methods)
        self.assertIn("eventFilter", methods)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication, QLineEdit
    from shiboken6 import isValid
    from vib_validation_app.focus_manager import KeyboardFocusRingManager
    _QT_AVAILABLE = True
except Exception:
    _QT_AVAILABLE = False


@unittest.skipUnless(_QT_AVAILABLE, "PySide6/Shiboken6 runtime is not installed in this environment")
class V10611FocusLifecycleQtRuntimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _delete(widget):
        widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()

    def test_deleted_focused_widget_does_not_break_next_focus(self):
        manager = KeyboardFocusRingManager(self.app)
        old = QLineEdit()
        manager._set_keyboard_focus(old, True)
        self.assertEqual(old.property("keyboardFocus"), "true")
        self._delete(old)
        self.assertFalse(isValid(old))

        new = QLineEdit()
        manager._set_keyboard_focus(new, True)
        self.assertIs(manager._focused_widget, new)
        self.assertEqual(new.property("keyboardFocus"), "true")
        self._delete(new)

    def test_delayed_tooltip_callback_ignores_deleted_widget(self):
        manager = KeyboardFocusRingManager(self.app)
        widget = QLineEdit()
        widget.setToolTip("focus tooltip")
        self._delete(widget)
        self.assertFalse(isValid(widget))
        manager._show_focus_tooltip(widget)

    def test_property_helper_preserves_visual_property_for_live_widget(self):
        manager = KeyboardFocusRingManager(self.app)
        widget = QLineEdit()
        self.assertTrue(manager._apply_property(widget, True))
        self.assertEqual(widget.property("keyboardFocus"), "true")
        self.assertTrue(manager._apply_property(widget, False))
        self.assertEqual(widget.property("keyboardFocus"), "false")
        self._delete(widget)

    def test_repeated_focus_delete_transition_is_stable(self):
        manager = KeyboardFocusRingManager(self.app)
        previous = None
        for _ in range(40):
            widget = QLineEdit()
            manager._set_keyboard_focus(widget, True)
            if previous is not None:
                self.assertFalse(isValid(previous))
            previous = widget
            self._delete(widget)
        next_widget = QLineEdit()
        manager._set_keyboard_focus(next_widget, True)
        self.assertEqual(next_widget.property("keyboardFocus"), "true")
        self._delete(next_widget)


if __name__ == "__main__":
    unittest.main()
