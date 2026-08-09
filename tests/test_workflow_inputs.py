from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import DEFAULT_SETTINGS, SettingsManager
from vibrapilot.workflow_inputs import WORKFLOW_INPUT_FIELDS, WORKFLOW_INPUT_KEYS


class WorkflowInputsTest(unittest.TestCase):
    EXPECTED_KEYS = (
        "default_full_name",
        "default_number",
        "fallback_name",
        "update_click_count",
    )

    def test_exact_existing_setting_keys_are_exposed(self):
        self.assertEqual(WORKFLOW_INPUT_KEYS, self.EXPECTED_KEYS)
        self.assertEqual(tuple(field.key for field in WORKFLOW_INPUT_FIELDS), self.EXPECTED_KEYS)
        self.assertEqual(len(set(WORKFLOW_INPUT_KEYS)), len(WORKFLOW_INPUT_KEYS))
        self.assertNotIn("default_target_url", WORKFLOW_INPUT_KEYS)
        for key in WORKFLOW_INPUT_KEYS:
            self.assertIn(key, DEFAULT_SETTINGS)
            self.assertEqual(DEFAULT_SETTINGS[key], "")

    def test_existing_saved_values_survive_settings_manager_load(self):
        saved = {
            "default_full_name": "Existing Person",
            "default_number": "+8801700000000",
            "fallback_name": "Existing Fallback",
            "update_click_count": "3",
            "default_target_url": "https://example.test/kept",
            "theme_mode": "Dark",
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            path.write_text(json.dumps(saved), encoding="utf-8")
            manager = SettingsManager(path)
            for key in self.EXPECTED_KEYS:
                self.assertEqual(manager.get(key), saved[key])
            self.assertEqual(manager.get("default_target_url"), saved["default_target_url"])
            self.assertEqual(manager.get("theme_mode"), saved["theme_mode"])

    def test_workflow_metadata_contains_no_fake_workflow_selector(self):
        text = (SRC / "vibrapilot" / "workflow_inputs.py").read_text(encoding="utf-8")
        self.assertNotIn("workflow_id", text)
        self.assertNotIn("workflow_selector", text)
        self.assertNotIn("default_target_url", text)


if __name__ == "__main__":
    unittest.main()
