from __future__ import annotations

import unittest

from vibrapilot.app_config import SUPPORT


class SupportConfigTest(unittest.TestCase):
    def test_confirmed_public_support_links(self):
        self.assertEqual(SUPPORT.website_url, "https://vib.tools/")
        self.assertEqual(SUPPORT.support_email, "support@vib.tools")
        self.assertEqual(SUPPORT.contact_url, "https://vib.tools/contact")
        self.assertEqual(SUPPORT.repository_url, "https://github.com/vibtools/VibraPilot")
        self.assertIn("/docs", SUPPORT.documentation_url)
        self.assertTrue(SUPPORT.about_support_links)

    def test_unconfirmed_endpoints_remain_blank(self):
        self.assertEqual(SUPPORT.developer_portal_url, "")
        self.assertEqual(SUPPORT.help_center_url, "")
        self.assertEqual(SUPPORT.user_guide_url, "")
        self.assertEqual(SUPPORT.privacy_url, "")
        self.assertEqual(SUPPORT.terms_url, "")


if __name__ == "__main__":
    unittest.main()
