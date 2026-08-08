from __future__ import annotations

import unittest

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
