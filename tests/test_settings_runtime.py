from __future__ import annotations

import sys
import json
import os
import tempfile
from pathlib import Path

# Keep test runtime writes outside the repository.
os.environ.setdefault("VIB_TOOLS_DATA_DIR", tempfile.mkdtemp(prefix="vibrapilot-settings-test-"))


# Standard-library unittest discovery does not consume pytest's ``pythonpath``
# configuration. Add the repository ``src`` layout explicitly so the documented
# direct unittest command works without shell-specific PYTHONPATH setup.
_TEST_ROOT = Path(__file__).resolve().parents[1]
_TEST_SRC = _TEST_ROOT / "src"
if str(_TEST_SRC) not in sys.path:
    sys.path.insert(0, str(_TEST_SRC))

from vibrapilot.backend import (
    DEFAULT_SETTINGS,
    SettingsManager,
    safe_test_send_limit,
    validate_test_send_limit,
)


def test_contact_defaults_are_blank():
    for key in ("default_full_name", "default_number", "fallback_name", "update_click_count"):
        assert DEFAULT_SETTINGS[key] == ""


def test_switches_and_values_round_trip():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        manager = SettingsManager(path)
        manager.set("headless", True)
        manager.set("remove_duplicate_rows", False)
        manager.set("default_target_url", "https://example.test/task")
        reloaded = SettingsManager(path)
        assert reloaded.get("headless") is True
        assert reloaded.get("remove_duplicate_rows") is False
        assert reloaded.get("default_target_url") == "https://example.test/task"


def test_legacy_contact_placeholders_are_migrated_only_when_exact():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        path.write_text(json.dumps({
            "default_full_name": "**GPL Licensed** — This software is distributed under the GNU General Public License (GPL). For more information, visit https://vib.tools/.",
            "default_number": "For Support Whatapp : +880 1795-470603",
            "fallback_name": "Custom Fallback",
            "update_click_count": 1,
        }), encoding="utf-8")
        manager = SettingsManager(path)
        assert manager.get("default_full_name") == ""
        assert manager.get("default_number") == ""
        assert manager.get("fallback_name") == "Custom Fallback"
        assert manager.get("update_click_count") == ""


def test_test_send_limit_is_settings_controlled_without_hardcoded_ceiling():
    assert validate_test_send_limit(0) == 0
    assert validate_test_send_limit(600) == 600
    assert validate_test_send_limit(50_000) == 50_000
    assert validate_test_send_limit(500_000) == 500_000
    assert safe_test_send_limit(50_000) == 50_000


def test_negative_test_send_limit_falls_back_to_default():
    assert safe_test_send_limit(-1) == DEFAULT_SETTINGS["max_test_send_limit"]


def test_large_settings_controlled_send_limit_round_trips_exactly():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        manager = SettingsManager(path)
        manager.set("max_test_send_limit", 500_000)
        reloaded = SettingsManager(path)
        assert reloaded.get("max_test_send_limit") == 500_000
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["max_test_send_limit"] == 500_000


def test_browser_settings_defaults_and_round_trip():
    expected_defaults = {
        "headless": False,
        "use_chrome_channel": True,
        "allow_chromium_fallback": True,
        "start_maximized": False,
        "no_viewport": False,
        "navigation_wait_until": "domcontentloaded",
        "wait_for_network_idle": True,
        "network_idle_timeout": 8000,
        "block_images": False,
        "block_fonts": False,
        "block_media": False,
        "preserve_storage_state_on_recycle": True,
        "restore_page_after_context_recycle": True,
        "auto_focus_browser_on_open": True,
        "auto_dismiss_browser_dialogs": True,
        "scroll_before_interaction": True,
    }
    for key, expected in expected_defaults.items():
        assert DEFAULT_SETTINGS[key] == expected

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        manager = SettingsManager(path)
        manager.set("headless", True)
        manager.set("navigation_wait_until", "load")
        manager.set("network_idle_timeout", 12000)
        manager.set("block_images", True)
        manager.set("preserve_storage_state_on_recycle", False)
        reloaded = SettingsManager(path)
        assert reloaded.get("headless") is True
        assert reloaded.get("navigation_wait_until") == "load"
        assert reloaded.get("network_idle_timeout") == 12000
        assert reloaded.get("block_images") is True
        assert reloaded.get("preserve_storage_state_on_recycle") is False


def test_legacy_combined_resource_blocking_migrates_to_explicit_toggles():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        path.write_text(json.dumps({"disable_image_font_media_loading": True}), encoding="utf-8")
        manager = SettingsManager(path)
        assert manager.get("block_images") is True
        assert manager.get("block_fonts") is True
        assert manager.get("block_media") is True
        assert manager.get("disable_image_font_media_loading") is None
        persisted = json.loads(path.read_text(encoding="utf-8"))
        assert "disable_image_font_media_loading" not in persisted


def test_duplicate_hardware_acceleration_alias_migrates_to_effective_gpu_state():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        path.write_text(
            json.dumps({"hardware_acceleration_enabled": False, "gpu_enabled": True}),
            encoding="utf-8",
        )
        manager = SettingsManager(path)
        assert manager.get("gpu_enabled") is False
        assert manager.get("hardware_acceleration_enabled") is None
        persisted = json.loads(path.read_text(encoding="utf-8"))
        assert "hardware_acceleration_enabled" not in persisted


def test_master_browser_settings_defaults_preserve_existing_runtime_behavior():
    expected_defaults = {
        "use_persistent_context": True,
        "headless": False,
        "use_chrome_channel": True,
        "allow_chromium_fallback": True,
        "gpu_enabled": True,
        "sandbox_enabled": False,
        "start_maximized": False,
        "no_viewport": False,
        "viewport_width": 1280,
        "viewport_height": 720,
        "device_scale_factor": 1.0,
        "javascript_enabled": True,
        "accept_downloads": True,
        "ignore_https_errors": False,
        "extensions_enabled": False,
        "devtools_auto_open": False,
        "remote_debugging_port": 0,
        "background_throttling_enabled": True,
        "browser_console_logging": False,
        "network_event_logging": False,
        "record_har_enabled": False,
        "auto_restart_browser_on_crash": False,
    }
    for key, expected in expected_defaults.items():
        assert DEFAULT_SETTINGS[key] == expected


def test_master_browser_settings_round_trip_exactly():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "settings.json"
        manager = SettingsManager(path)
        values = {
            "browser_executable_path": r"C:\\Chrome\\chrome.exe",
            "use_persistent_context": True,
            "persistent_user_data_dir": r"C:\\BrowserProfiles",
            "window_width": 1440,
            "window_height": 900,
            "locale": "en-GB",
            "timezone_id": "Asia/Dhaka",
            "geolocation_enabled": True,
            "geolocation_latitude": 23.8103,
            "geolocation_longitude": 90.4125,
            "permission_notifications": True,
            "downloads_path": r"C:\\Downloads",
            "ignore_https_errors": True,
            "service_workers": "block",
            "remote_debugging_port": 9222,
            "browser_console_logging": True,
            "record_har_enabled": True,
            "auto_restart_browser_on_crash": True,
        }
        for key, value in values.items():
            manager.set(key, value)
        reloaded = SettingsManager(path)
        for key, value in values.items():
            assert reloaded.get(key) == value
