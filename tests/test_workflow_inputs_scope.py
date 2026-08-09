from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.8_workflow_inputs_scope.json"


class WorkflowInputsScopeTest(unittest.TestCase):
    def test_scope_identifies_final_v1067_baseline_and_exact_runtime_surface(self):
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
        self.assertEqual(data["target_version"], "1.0.6.8")
        self.assertEqual(
            data["official_baseline_tree_sha256"],
            "84d22fd2c1fef38cbf49024f7d3b2c9ec250e3389dd2b479192735fb2419bb89",
        )
        self.assertEqual(
            data["allowed_runtime_source_changes"],
            ["src/vibrapilot/qt_app.py", "src/vibrapilot/workflow_inputs.py"],
        )
        self.assertEqual(
            data["moved_setting_keys"],
            ["default_full_name", "default_number", "fallback_name", "update_click_count"],
        )
        self.assertEqual(data["do_not_move"], ["default_target_url"])
        self.assertTrue(data["preserve_setting_keys"])
        self.assertTrue(data["preserve_saved_values"])
        self.assertTrue(data["no_fake_workflow_selector"])

    def test_frozen_runtime_files_match_final_v1067_baseline_contract(self):
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
        current_license_scope = ROOT / "config/verification/v1.0.6.10_license_login_fix_scope.json"
        current_focus_scope = ROOT / "config/verification/v1.0.6.11_qt_focus_lifecycle_fix_scope.json"
        current_browser_scope = ROOT / "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json"
        current_phase_scope = ROOT / "config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json"
        browser_allowed = set()
        if current_browser_scope.is_file():
            browser_allowed |= set(json.loads(current_browser_scope.read_text(encoding="utf-8")).get("allowed_runtime_source_changes", []))
        if current_phase_scope.is_file():
            browser_allowed |= set(json.loads(current_phase_scope.read_text(encoding="utf-8")).get("allowed_runtime_source_changes", []))
        for relative, expected in data["frozen_file_sha256"].items():
            if current_license_scope.is_file() and relative == "src/vibrapilot/backend.py":
                continue
            if current_focus_scope.is_file() and relative == "vib_validation_app/focus_manager.py":
                continue
            if relative in browser_allowed:
                continue
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            raw = path.read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected, relative)

    def test_backend_and_browser_contract_are_not_part_of_the_approved_ui_change(self):
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
        frozen = set(data["frozen_file_sha256"])
        self.assertIn("src/vibrapilot/backend.py", frozen)
        self.assertIn("src/vibrapilot/task_runtime_store.py", frozen)
        self.assertIn("src/vibrapilot/licensing_v2.py", frozen)
        self.assertIn("config/settings.defaults.json", frozen)
        self.assertNotIn("src/vibrapilot/qt_app.py", frozen)


if __name__ == "__main__":
    unittest.main()
