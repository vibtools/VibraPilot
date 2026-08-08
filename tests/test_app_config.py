from __future__ import annotations

import unittest
from pathlib import Path
from urllib.parse import urlparse

from vibrapilot.app_config import APP, ABOUT, ENABLED_SOCIAL_LINKS, SOCIAL_LINKS, SUPPORT

ROOT = Path(__file__).resolve().parents[1]


class AppConfigTest(unittest.TestCase):
    def test_authoritative_identity(self):
        self.assertEqual(APP.app_id, "vibrapilot")
        self.assertEqual(APP.app_name, "VibraPilot")
        self.assertEqual(APP.display_name, "VibraPilot")
        self.assertEqual(APP.version, "1.0.6.2")
        self.assertEqual(APP.owner_name, "Vib Tools")
        self.assertEqual(APP.license_identifier, "GPL-3.0-only")
        self.assertEqual(APP.updated_date, "2026-08-08")
        self.assertTrue(APP.target_features)
        self.assertTrue(APP.target_users)

    def test_public_urls_are_https_when_configured(self):
        urls = [
            APP.homepage_url,
            APP.repository_url,
            SUPPORT.website_url,
            SUPPORT.developer_portal_url,
            SUPPORT.contact_url,
            SUPPORT.repository_url,
            SUPPORT.documentation_url,
            SUPPORT.getting_started_url,
            SUPPORT.user_guide_url,
            SUPPORT.faq_url,
            SUPPORT.issues_url,
            SUPPORT.releases_url,
            SUPPORT.changelog_url,
            SUPPORT.security_url,
            SUPPORT.license_url,
        ]
        for url in filter(None, urls):
            parsed = urlparse(url)
            self.assertEqual(parsed.scheme, "https", url)
            self.assertTrue(parsed.netloc, url)

    def test_about_and_social_metadata_are_populated(self):
        self.assertEqual(ABOUT.page_title, "About")
        self.assertEqual(ABOUT.company_title, "Vib Tools")
        self.assertEqual(ABOUT.company_display_name, "Vib Tools")
        self.assertTrue(ABOUT.company_profile_description)
        self.assertTrue(ABOUT.design_contract_items)
        self.assertTrue(SOCIAL_LINKS)
        self.assertTrue(ENABLED_SOCIAL_LINKS)
        self.assertEqual(ENABLED_SOCIAL_LINKS[0].platform, "GitHub")

    def test_phase01_config_contains_no_license_transport_secret(self):
        for path in sorted((ROOT / "config/AppConfig").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("LICENSE_API_KEY", text, path)
            self.assertNotIn("LICENSE_API_BASE_URL", text, path)
            self.assertNotIn("LICENSE_VERIFY_URL", text, path)


if __name__ == "__main__":
    unittest.main()
