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

from vibrapilot.app_config import ENABLED_SOCIAL_LINKS, SOCIAL_BY_PLATFORM


class SocialConfigTest(unittest.TestCase):
    def test_official_public_social_presence_is_configured(self):
        expected = {
            "github": "https://github.com/vibtools",
            "x": "https://x.com/vibtools",
            "facebook": "https://www.facebook.com/vib.tools",
            "instagram": "https://www.instagram.com/vibtools",
            "reddit": "https://www.reddit.com/user/VibTools/",
            "tiktok": "https://www.tiktok.com/@vibtools",
            "gitlab": "https://gitlab.com/vibtools",
        }
        self.assertEqual(set(SOCIAL_BY_PLATFORM), set(expected))
        for platform, url in expected.items():
            link = SOCIAL_BY_PLATFORM[platform]
            self.assertTrue(link.enabled)
            self.assertEqual(link.display_name, "Vib Tools")
            self.assertEqual(link.url, url)
            self.assertIn(link, ENABLED_SOCIAL_LINKS)


if __name__ == "__main__":
    unittest.main()
