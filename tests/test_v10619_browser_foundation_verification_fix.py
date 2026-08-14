from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibrapilot.browser_diagnostics import (
    EXPECTED_PLAYWRIGHT_VERSION,
    browser_diagnostics_summary,
    browser_diagnostics_warnings,
    build_browser_diagnostics,
    sanitize_diagnostic_text,
    sanitize_launch_kwargs,
)

ROOT = Path(__file__).resolve().parents[1]


class BrowserFoundationVerificationFixTest(unittest.TestCase):
    def _settings(self) -> dict[str, object]:
        return {
            "sandbox_enabled": False,
            "allow_chromium_fallback": True,
            "persistent_profile_directory": "",
            "http_cache_enabled": False,
            "viewport_width": 1280,
            "viewport_height": 720,
            "device_scale_factor": 1.0,
            "proxy": "",
            "dns_host_resolver_rules": "",
            "user_agent": "",
        }

    def test_scope_contract_and_frozen_sandbox_boundary(self) -> None:
        scope = json.loads(
            (
                ROOT
                / "config/verification/v1.0.6.19_browser_foundation_verification_fix_scope.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            scope["plan_id"],
            "VP-BROWSER-FOUNDATION-STABILIZATION-001-VERIFICATION-FIX",
        )
        self.assertEqual(scope["official_baseline"], "VibraPilot v1.0.6.18")
        self.assertEqual(
            scope["official_baseline_archive_sha256"],
            "d18277ea00ae581ede45c8d3e647cd0f41625aeb0d5b8aad71715c19e4e29ae9",
        )
        self.assertEqual(scope["target_version"], "1.0.6.19")
        self.assertFalse(scope["sandbox_default_change_applied"])
        self.assertEqual(
            set(scope["allowed_runtime_source_changes"]),
            {"src/vibrapilot/backend.py", "src/vibrapilot/browser_diagnostics.py"},
        )
        defaults = json.loads(
            (ROOT / "config/settings.defaults.json").read_text(encoding="utf-8")
        )
        current_scope = ROOT / "config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json"
        self.assertIs(defaults["sandbox_enabled"], True if current_scope.is_file() else False)

    def test_nested_launch_kwargs_preserve_json_types(self) -> None:
        result = sanitize_launch_kwargs(
            {
                "channel": "chrome",
                "viewport": {"width": 1280, "height": 720},
                "device_scale_factor": 1.0,
                "headless": False,
            }
        )
        self.assertEqual(result["viewport"], {"width": 1280, "height": 720})
        self.assertEqual(result["device_scale_factor"], 1.0)
        self.assertIs(result["headless"], False)

    def test_fallback_diagnostic_text_redacts_secret_switches_and_proxy_credentials(self) -> None:
        value = (
            "Browser launch failed: --api-key=secret-value "
            "--proxy-server=http://alice:password@example.test:8080"
        )
        sanitized = sanitize_diagnostic_text(value)
        self.assertNotIn("secret-value", sanitized)
        self.assertNotIn("alice:password", sanitized)
        self.assertIn("--api-key=<redacted>", sanitized)
        self.assertIn("http://<redacted>@example.test:8080", sanitized)

    def test_playwright_runtime_mismatch_is_explicit_and_non_fatal(self) -> None:
        with (
            patch(
                "vibrapilot.browser_diagnostics.playwright_package_version",
                return_value="1.60.0",
            ),
            patch(
                "vibrapilot.browser_diagnostics.discover_google_chrome",
                return_value=__import__("vibrapilot.chrome_runtime", fromlist=["ChromeRuntimeInfo"]).ChromeRuntimeInfo(
                    True, "available", Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                    "151", "Google Chrome", "programfiles", publisher="Google LLC", signature_trusted=True
                ),
            ),
            patch(
                "vibrapilot.browser_diagnostics.collect_windows_browser_process",
                return_value={
                    "status": "found",
                    "profile_path": r"C:\Profiles\slot_1",
                    "pid": 10,
                    "executable_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    "command_line": "chrome.exe --no-sandbox",
                },
            ),
            patch(
                "vibrapilot.browser_diagnostics.collect_cdp_browser_metadata",
                return_value={"product": "Chrome/151.0.7922.76"},
            ),
            patch(
                "vibrapilot.browser_diagnostics.collect_page_environment",
                return_value={"webdriver": True},
            ),
        ):
            record = build_browser_diagnostics(
                slot_id=1,
                settings=self._settings(),
                requested_launch_kwargs={"channel": "chrome"},
                effective_launch_kwargs={"channel": "chrome"},
                context=object(),
                page=object(),
                user_data_dir=Path(r"C:\Profiles\slot_1"),
                fallback_used=False,
                fallback_reason="",
                persistent_context=True,
            )
        self.assertEqual(record["playwright"]["expected_version"], EXPECTED_PLAYWRIGHT_VERSION)
        self.assertEqual(record["playwright"]["actual_version"], "1.60.0")
        self.assertFalse(record["playwright"]["matches_expected"])
        warnings = browser_diagnostics_warnings(record)
        self.assertEqual(len(warnings), 1)
        self.assertIn("1.60.0", warnings[0])
        self.assertIn(EXPECTED_PLAYWRIGHT_VERSION, warnings[0])
        self.assertIn("mismatch", browser_diagnostics_summary(record))

    def test_expected_playwright_version_matches_project_dependency(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn(f'"playwright=={EXPECTED_PLAYWRIGHT_VERSION}"', pyproject)
        self.assertIn(f"playwright=={EXPECTED_PLAYWRIGHT_VERSION}", requirements)

    def test_sandbox_default_remains_frozen_without_sandbox_on_acceptance(self) -> None:
        defaults = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
        current_scope = ROOT / "config/verification/v1.0.6.31_chrome_only_browser_runtime_scope.json"
        self.assertIs(defaults["sandbox_enabled"], True if current_scope.is_file() else False)


if __name__ == "__main__":
    unittest.main()
