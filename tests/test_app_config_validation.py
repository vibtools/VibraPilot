from __future__ import annotations

import unittest

from vibrapilot.app_config import (
    _date,
    _optional_email,
    _optional_url,
    _required_text_tuple,
    _version,
)


class AppConfigValidationTest(unittest.TestCase):
    def test_valid_calendar_date(self):
        self.assertEqual(_date("DATE", "2026-08-08"), "2026-08-08")
        with self.assertRaises(RuntimeError):
            _date("DATE", "2026-02-31")
        with self.assertRaises(RuntimeError):
            _date("DATE", "20260808")

    def test_version_contract(self):
        self.assertEqual(_version("VERSION", "1.0.6.2"), "1.0.6.2")
        self.assertEqual(_version("VERSION", "1.2.3"), "1.2.3")
        with self.assertRaises(RuntimeError):
            _version("VERSION", "v1.0.6.2")

    def test_required_sequence_rejects_blank_entries(self):
        self.assertEqual(_required_text_tuple("ITEMS", ("one", "two")), ("one", "two"))
        with self.assertRaises(RuntimeError):
            _required_text_tuple("ITEMS", ())
        with self.assertRaises(RuntimeError):
            _required_text_tuple("ITEMS", ("one", ""))

    def test_public_endpoint_validation(self):
        self.assertEqual(_optional_url("URL", "https://vib.tools/"), "https://vib.tools/")
        self.assertEqual(_optional_url("URL", ""), "")
        with self.assertRaises(RuntimeError):
            _optional_url("URL", "http://vib.tools/")
        self.assertEqual(_optional_email("EMAIL", "support@vib.tools"), "support@vib.tools")
        with self.assertRaises(RuntimeError):
            _optional_email("EMAIL", "not-an-email")


if __name__ == "__main__":
    unittest.main()
