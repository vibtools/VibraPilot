from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "config/verification/phase02_step002_v1.0.6.4_fix_scope.json").read_text(
        encoding="utf-8"
    )
)
PRODUCTION_SCOPE = json.loads(
    (ROOT / "config/verification/production_mt_lr_v1.0.6.5_scope.json").read_text(encoding="utf-8")
)


class Phase02Step002FixScopeTest(unittest.TestCase):
    def test_v1063_operational_files_outside_fix_scope_are_byte_identical(self):
        allowed = set(PRODUCTION_SCOPE["allowed_runtime_source_changes"])
        current_focus_scope = ROOT / "config/verification/v1.0.6.11_qt_focus_lifecycle_fix_scope.json"
        if current_focus_scope.is_file():
            allowed.add("vib_validation_app/focus_manager.py")
        current_browser_scope = ROOT / "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json"
        if current_browser_scope.is_file():
            allowed.update(json.loads(current_browser_scope.read_text(encoding="utf-8")).get("allowed_runtime_source_changes", []))
        ui_scope = ROOT / "config/verification/v1.0.6.34_ui_compact_polish_scope.json"
        if ui_scope.is_file():
            allowed.update(json.loads(ui_scope.read_text(encoding="utf-8")).get("allowed_production_source_changes", []))
        for relative, expected in CONTRACT["frozen_file_sha256"].items():
            if relative in allowed:
                continue
            with self.subTest(path=relative):
                path = ROOT / relative
                self.assertTrue(path.is_file(), relative)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_release_forbidden_paths_are_declared_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for top in CONTRACT["forbidden_release_top_level_paths"]:
            if top.startswith("."):
                marker = top + "/"
            else:
                marker = top + "/"
            with self.subTest(path=top):
                self.assertIn(marker, ignore)


if __name__ == "__main__":
    unittest.main()
