from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AboutConfigBindingTest(unittest.TestCase):
    def test_about_page_consumes_central_config(self):
        ui = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        markers = [
            "page_header(ABOUT.page_title)",
            "identity = card(APP.display_name)",
            "ABOUT.edition_label",
            "APP.version",
            "if SUPPORT.support_email:",
            "for link_label, url in SUPPORT.about_support_links:",
            "for social_link in ENABLED_SOCIAL_LINKS:",
        ]
        for marker in markers:
            self.assertIn(marker, ui)

    def test_activation_branding_consumes_appconfig(self):
        ui = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.assertIn('QLabel(f"{APP.display_name} Activation")', ui)
        self.assertNotIn('QLabel(f"Enter your license key to unlock {APP.display_name}")', ui)
        self.assertNotIn("Secured by Licora Activation Engine", ui)
        self.assertIn("application.setOrganizationName(APP.company_name)", ui)
        self.assertIn("application.setOrganizationDomain(APP.organization_domain)", ui)


if __name__ == "__main__":
    unittest.main()
