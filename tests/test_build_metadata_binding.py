from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuildMetadataBindingTest(unittest.TestCase):
    def test_build_consumes_appconfig_identity(self):
        build = (ROOT / "build.py").read_text(encoding="utf-8")
        self.assertIn("from config.AppConfig.app import APP_NAME, VERSION", build)
        self.assertIn("APP_VERSION = VERSION", build)
        self.assertIn('"config/AppConfig"', build)

    def test_backend_keeps_legacy_constant_interface_as_config_aliases(self):
        backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        for marker in [
            "DISPLAY_APP_NAME = APP.display_name",
            "APP_NAME = APP.app_name",
            "APP_VERSION = APP.version",
            "APP_AUTHOR = APP.author_name",
            "RELEASE_DATE = APP.release_date",
        ]:
            self.assertIn(marker, backend)


if __name__ == "__main__":
    unittest.main()
