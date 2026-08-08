from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VibraPilotBrandingTest(unittest.TestCase):
    def test_runtime_brand_identity_and_icons(self):
        backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        ui = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        build = (ROOT / "build.py").read_text(encoding="utf-8")
        self.assertIn('DISPLAY_APP_NAME = "VibraPilot"', backend)
        self.assertIn('APP_NAME = "VibraPilot"', backend)
        self.assertIn('QLabel("VibraPilot Activation")', ui)
        self.assertIn('application.setWindowIcon(application_icon())', ui)
        self.assertIn('self.setWindowIcon(application_icon())', ui)
        self.assertIn('SetCurrentProcessExplicitAppUserModelID', ui)
        self.assertIn('APP_NAME = "VibraPilot"', build)
        self.assertTrue((ROOT / "assets/icons/app.ico").is_file())
        self.assertTrue((ROOT / "assets/icons/app.png").is_file())

    def test_package_and_launcher_are_rebranded(self):
        self.assertTrue((ROOT / "src/vibrapilot/backend.py").is_file())
        legacy_pkg = "".join(chr(x) for x in [116,101,115,116,101,114,95,122,101,112,116,111,95,112,114,111])
        legacy_launcher = "".join(chr(x) for x in [83,116,97,114,116,45,84,101,115,116,101,114,90,101,112,116,111,80,114,111,46,112,115,49])
        self.assertFalse((ROOT / "src" / legacy_pkg).exists())
        self.assertTrue((ROOT / "scripts/Start-VibraPilot.ps1").is_file())
        self.assertFalse((ROOT / "scripts" / legacy_launcher).exists())

    def test_docs_no_legacy_product_identity(self):
        legacy = (
            "".join(chr(x) for x in [84,101,115,116,101,114,32,90,101,112,116,111,32,80,114,111]),
            "".join(chr(x) for x in [84,101,115,116,101,114,90,101,112,116,111,80,114,111]),
            "".join(chr(x) for x in [116,101,115,116,101,114,95,122,101,112,116,111,95,112,114,111]),
        )
        for path in [
            ROOT / "README.md",
            ROOT / "CHANGELOG.md",
            ROOT / "UPDATE_LOG.md",
            ROOT / "VERSIONING.md",
            ROOT / "docs/index.md",
        ]:
            text = path.read_text(encoding="utf-8")
            for value in legacy:
                self.assertNotIn(value, text, f"legacy identity in {path}")


if __name__ == "__main__":
    unittest.main()
