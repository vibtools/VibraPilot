from __future__ import annotations

import sys
from pathlib import Path
import unittest


# Standard-library unittest discovery does not consume pytest's ``pythonpath``
# configuration. Add the repository ``src`` layout explicitly so the documented
# direct unittest command works without shell-specific PYTHONPATH setup.
_TEST_ROOT = Path(__file__).resolve().parents[1]
_TEST_SRC = _TEST_ROOT / "src"
if str(_TEST_SRC) not in sys.path:
    sys.path.insert(0, str(_TEST_SRC))

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
