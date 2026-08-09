from __future__ import annotations

import sys
import os
import queue
import json
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("VIB_TOOLS_DATA_DIR", tempfile.mkdtemp(prefix="vibrapilot-master-browser-test-"))


# Standard-library unittest discovery does not consume pytest's ``pythonpath``
# configuration. Add the repository ``src`` layout explicitly so the documented
# direct unittest command works without shell-specific PYTHONPATH setup.
_TEST_ROOT = Path(__file__).resolve().parents[1]
_TEST_SRC = _TEST_ROOT / "src"
if str(_TEST_SRC) not in sys.path:
    sys.path.insert(0, str(_TEST_SRC))

from vibrapilot.backend import (
    DEFAULT_SETTINGS,
    AutomationWorker,
    TaskState,
    effective_ignored_default_args,
)


def _worker(**overrides):
    settings = dict(DEFAULT_SETTINGS)
    settings.update(overrides)
    return AutomationWorker(
        TaskState(slot_id=1, target_url="https://example.test/"),
        settings,
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        "https://example.test/",
    )


def test_context_arguments_cover_master_emulation_and_permissions():
    worker = _worker(
        no_viewport=False,
        viewport_width=1440,
        viewport_height=900,
        screen_width=1920,
        screen_height=1080,
        device_scale_factor=1.25,
        locale="en-GB",
        timezone_id="Asia/Dhaka",
        geolocation_enabled=True,
        geolocation_latitude=23.8103,
        geolocation_longitude=90.4125,
        geolocation_accuracy=25.0,
        permission_notifications=True,
        permission_clipboard_read=True,
        permission_geolocation=True,
        accept_downloads=False,
        ignore_https_errors=True,
        javascript_enabled=False,
        has_touch=True,
        is_mobile=True,
        offline=True,
        service_workers="block",
        strict_selectors=True,
        color_scheme="dark",
        reduced_motion="reduce",
        forced_colors="active",
        contrast="more",
        accept_language="en-GB,en;q=0.9",
        extra_http_headers_json='{"X-Test":"yes"}',
    )
    args = worker.context_arguments()
    assert args["viewport"] == {"width": 1440, "height": 900}
    assert args["screen"] == {"width": 1920, "height": 1080}
    assert args["device_scale_factor"] == 1.25
    assert args["locale"] == "en-GB"
    assert args["timezone_id"] == "Asia/Dhaka"
    assert args["geolocation"]["latitude"] == 23.8103
    assert set(args["permissions"]) == {"notifications", "clipboard-read", "geolocation"}
    assert args["accept_downloads"] is False
    assert args["ignore_https_errors"] is True
    assert args["java_script_enabled"] is False
    assert args["has_touch"] is True
    assert args["is_mobile"] is True
    assert args["offline"] is True
    assert args["service_workers"] == "block"
    assert args["strict_selectors"] is True
    assert args["color_scheme"] == "dark"
    assert args["reduced_motion"] == "reduce"
    assert args["forced_colors"] == "active"
    assert args["contrast"] == "more"
    assert args["extra_http_headers"]["X-Test"] == "yes"
    assert args["extra_http_headers"]["Accept-Language"] == "en-GB,en;q=0.9"


def test_context_arguments_keep_browser_defaults_when_optional_values_are_unset():
    worker = _worker()
    args = worker.context_arguments()
    assert args["viewport"] == {"width": 1280, "height": 720}
    assert "screen" not in args
    assert "locale" not in args
    assert "timezone_id" not in args
    assert "geolocation" not in args
    assert "permissions" not in args
    assert "color_scheme" not in args
    assert "reduced_motion" not in args
    assert "forced_colors" not in args
    assert "contrast" not in args


def test_client_certificate_json_is_wired_into_context_arguments(tmp_path):
    cert_file = tmp_path / "client.pem"
    key_file = tmp_path / "client.key"
    cert_file.write_text("certificate", encoding="utf-8")
    key_file.write_text("key", encoding="utf-8")
    worker = _worker(
        client_certificates_json=json.dumps(
            [
                {
                    "origin": "https://secure.example.test",
                    "certPath": str(cert_file),
                    "keyPath": str(key_file),
                }
            ]
        )
    )
    args = worker.context_arguments()
    assert args["client_certificates"][0]["origin"] == "https://secure.example.test"
    assert args["client_certificates"][0]["certPath"] == str(cert_file.resolve())
    assert args["client_certificates"][0]["keyPath"] == str(key_file.resolve())


def test_persistent_profile_and_extension_controls_are_source_wired():
    backend = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "vibrapilot"
        / "backend.py"
    ).read_text(encoding="utf-8")
    assert "launch_persistent_context(" in backend
    assert "--profile-directory=" in backend
    assert "--disable-extensions-except=" in backend
    assert "--load-extension=" in backend
    assert "fallback_ephemeral" in backend
    assert "BrowserProfilesTemp" in backend


def test_chromium_launch_master_flags_are_source_wired():
    backend = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "vibrapilot"
        / "backend.py"
    ).read_text(encoding="utf-8")
    assert '"chromium_sandbox": bool(' in backend
    for marker in (
        "--window-size=",
        "--window-position=",
        "--disable-gpu",
        "--disable-popup-blocking",
        "--mute-audio",
        "--remote-debugging-address=127.0.0.1",
        "--auto-open-devtools-for-tabs",
        "--disable-background-timer-throttling",
        "--renderer-process-limit=",
        "--host-resolver-rules=",
        "--force-webrtc-ip-handling-policy=",
        "--restore-last-session",
        "--enable-features",
        "--disable-features",
        "--enable-blink-features",
        "--disable-blink-features",
    ):
        assert marker in backend


def test_devtools_auto_open_uses_chromium_switch_not_removed_playwright_kwarg():
    backend = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "vibrapilot"
        / "backend.py"
    ).read_text(encoding="utf-8")
    assert 'browser_args.append("--auto-open-devtools-for-tabs")' in backend
    assert '"devtools": bool(' not in backend




def test_audio_enabled_overrides_playwright_headless_mute_default():
    enabled = dict(DEFAULT_SETTINGS)
    enabled["audio_enabled"] = True
    ignored = effective_ignored_default_args(enabled, extensions_enabled=False)
    assert "--mute-audio" in ignored

    disabled = dict(DEFAULT_SETTINGS)
    disabled["audio_enabled"] = False
    ignored = effective_ignored_default_args(disabled, extensions_enabled=False)
    assert "--mute-audio" not in ignored

def test_popup_setting_overrides_playwright_default_arg():
    blocked = dict(DEFAULT_SETTINGS)
    blocked["allow_popups"] = False
    ignored = effective_ignored_default_args(blocked, extensions_enabled=False)
    assert "--disable-popup-blocking" in ignored

    allowed = dict(DEFAULT_SETTINGS)
    allowed["allow_popups"] = True
    ignored = effective_ignored_default_args(allowed, extensions_enabled=False)
    assert "--disable-popup-blocking" not in ignored


def test_background_throttling_setting_overrides_playwright_defaults():
    enabled = dict(DEFAULT_SETTINGS)
    enabled["background_throttling_enabled"] = True
    ignored = effective_ignored_default_args(enabled, extensions_enabled=False)
    for arg in (
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ):
        assert arg in ignored

    disabled = dict(DEFAULT_SETTINGS)
    disabled["background_throttling_enabled"] = False
    ignored = effective_ignored_default_args(disabled, extensions_enabled=False)
    for arg in (
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ):
        assert arg not in ignored




def test_extension_loading_uses_full_playwright_chromium_channel():
    backend = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "vibrapilot"
        / "backend.py"
    ).read_text(encoding="utf-8")
    assert 'elif extensions_enabled:' in backend
    assert 'launch_args["channel"] = "chromium"' in backend
    assert 'persistent_args.get("channel") == "chrome"' in backend

def test_extension_mode_suppresses_playwright_disable_extensions_default():
    settings = dict(DEFAULT_SETTINGS)
    ignored = effective_ignored_default_args(settings, extensions_enabled=True)
    assert "--disable-extensions" in ignored


def test_removed_duplicate_browser_aliases_are_not_defaults():
    assert "hardware_acceleration_enabled" not in DEFAULT_SETTINGS
    assert "disable_image_font_media_loading" not in DEFAULT_SETTINGS


def test_generated_context_arguments_match_installed_playwright_api(tmp_path):
    import inspect
    from playwright.sync_api import Browser

    cert_file = tmp_path / "client.pem"
    key_file = tmp_path / "client.key"
    cert_file.write_text("certificate", encoding="utf-8")
    key_file.write_text("key", encoding="utf-8")
    video_dir = tmp_path / "video"
    har_dir = tmp_path / "har"
    worker = _worker(
        no_viewport=False,
        screen_width=1920,
        screen_height=1080,
        locale="en-US",
        timezone_id="UTC",
        geolocation_enabled=True,
        permission_notifications=True,
        accept_downloads=True,
        ignore_https_errors=True,
        javascript_enabled=True,
        user_agent="VibraPilot-Test",
        proxy="http://127.0.0.1:8080",
        proxy_bypass="localhost",
        extra_http_headers_json='{"X-Audit":"1"}',
        strict_selectors=True,
        service_workers="block",
        client_certificates_json=json.dumps([
            {
                "origin": "https://secure.example.test",
                "certPath": str(cert_file),
                "keyPath": str(key_file),
            }
        ]),
        record_har_enabled=True,
        record_har_directory=str(har_dir),
        record_video_enabled=True,
        record_video_directory=str(video_dir),
        record_video_width=1280,
        record_video_height=720,
        base_url="https://example.test/",
    )
    generated = set(worker.context_arguments())
    supported = set(inspect.signature(Browser.new_context).parameters) - {"self"}
    assert generated <= supported, f"Unsupported Playwright context kwargs: {sorted(generated - supported)}"
