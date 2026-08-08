#!/usr/bin/env python3
"""
Tester Zepto Pro - Authorized Test Mode Invite Automation
Version: 1.0.6.1
Author: Vib.tools

Feature-preserving backend extracted from Tester Zepto Pro v1.0.6.

The automation, licensing, persistence, safety, retry, reporting-row, browser lifecycle,
and data protection logic are preserved for the Vib Tools PySide6 desktop UI edition.
"""

from __future__ import annotations

import base64
import csv
import ctypes
import hashlib
import json
import logging
import os
import queue
import random
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import requests


DISPLAY_APP_NAME = "Tester Zepto Pro"
APP_NAME = "Razorpay (Vib.Tools)"
APP_VERSION = "1.0.6.1"
APP_AUTHOR = "Vib.tools"
RELEASE_DATE = "2026-08-07"
# Private deployment license configuration.
# Set these two values before building/distributing the application.
# The API key is intentionally read only from this source constant; no PowerShell
# or process-environment injection is used for license authentication.
LICENSE_API_BASE_URL = "https://mxflow.shop"
LICENSE_API_KEY = "eca024779ccb6c901ae28de6819c32a6838efacf8423266b854e2dd6eca89273"
LICENSE_VERIFY_URL = f"{LICENSE_API_BASE_URL.rstrip('/')}/api/verify.php"

ROOT_DIR = (
    Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2]
)
DATA_ROOT_DIR = (
    Path(os.environ.get("VIB_TOOLS_DATA_DIR", ROOT_DIR)).expanduser().resolve()
)
APP_DATA_DIR = DATA_ROOT_DIR / "AppData"
FAILED_DATA_DIR = DATA_ROOT_DIR / "FailedData"
REPORTS_DIR = DATA_ROOT_DIR / "Reports"
LOGS_DIR = DATA_ROOT_DIR / "Logs"
for folder in (APP_DATA_DIR, FAILED_DATA_DIR, REPORTS_DIR, LOGS_DIR):
    folder.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = APP_DATA_DIR / "settings.json"
LICENSE_FILE = APP_DATA_DIR / "license.json"
APP_STATE_FILE = APP_DATA_DIR / "state.json"
LOG_FILE = LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# Packaged Playwright browser location. The Windows builder places Chromium next
# to the executable under ``ms-playwright``; Playwright reads this variable when
# ``sync_playwright`` is imported lazily by AutomationWorker.launch_browser().
if getattr(sys, "frozen", False):
    bundled_browsers = ROOT_DIR / "ms-playwright"
    if bundled_browsers.exists():
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(bundled_browsers))

DEFAULT_SETTINGS_FILE = ROOT_DIR / "config" / "settings.defaults.json"


def _load_default_settings() -> dict[str, Any]:
    """Load source-controlled user setting defaults.

    Defaults live outside Python source so the Settings UI and runtime share one
    configuration baseline. A missing or malformed file is a packaging error, not
    a reason to silently substitute hidden values.
    """
    try:
        raw = json.loads(DEFAULT_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Settings defaults could not be loaded: {DEFAULT_SETTINGS_FILE}"
        ) from exc
    if not isinstance(raw, dict) or not raw:
        raise RuntimeError("Settings defaults must be a non-empty JSON object.")
    return raw


DEFAULT_SETTINGS: dict[str, Any] = _load_default_settings()
DEFAULT_TEST_SEND_LIMIT = int(DEFAULT_SETTINGS["max_test_send_limit"])


SELECTORS = {
    # Mandatory authenticated Test Mode marker. Automation fails closed without it.
    "test_mode_banner": [
        "[data-testid='test-mode-banner']",
        ".highlight-test-mode-container [data-testid='test-mode-banner']",
        ".highlight-test-mode-container .trapezoid",
    ],
    # Share entry point on the already-authenticated target page.
    "share_button": [
        "button.Button--small.Button--primary.Button:has(i.i-share-outline)",
        "button:has(i.i-share-outline):has-text('Share')",
        "button.Button--primary:has-text('Share')",
        "button:has-text('Share')",
    ],
    # Share modal controls supplied by the target application's DOM.
    "share_modal_title": [
        "div.modal-header h3.modal-title:has-text('Share Link')",
        "h3.modal-title:has-text('Share Link')",
        "text=Share Link",
    ],
    "share_modal_close": [
        "button[data-testid='modal-header-close-btn']",
        "div.modal-header button.close",
    ],
    "share_email": [
        "form.Form.Share-section input[name='email'][type='email'][placeholder='Email']",
        "input[name='email'][type='email'][placeholder='Email']",
        "input[name='email'][type='email']",
    ],
    "share_send": [
        "form.Form.Share-section button[type='submit']:has-text('Send')",
        "button.Button--Link.Button--transparent.Button[type='submit']:has-text('Send')",
        "button[type='submit']:has(b:has-text('Send'))",
        "button[type='submit']:has-text('Send')",
    ],
    "invite_success": [
        "div.Notification.Notification--success[data-testid='Notification--success']",
        "[data-testid='Notification--success']",
        ".Notification--success",
    ],
    "invite_error": [
        "[data-testid='Notification--error']",
        ".Notification--error",
        ".Notification--danger",
        ".Notification--warning",
        ".errorMessage",
        ".validation-error",
    ],
    # Legacy selectors are preserved for backward-compatible configuration/data files.
    "contact_name_label": ["label[for='name']", "text=Contact Name:"],
    "phone_label": ["label[for='phone']", "text=Phone:"],
    "fax_label": ["label[for='fax']", "text=Fax:"],
    "email_label": ["label[for='email']", "text=Email:"],
    "name": ["input[name='name']", "input#name", "input[id='name/']"],
    "phone": ["input[name='phone']", "input#phone", "input[id='phone/']"],
    "fax": ["input[name='fax']", "input#fax", "input[id='fax/']"],
    "email": ["input[name='email']", "input#email", "input[id='email/']"],
    "update": [
        "input[name='confirmbutton'][value='Update']",
        "input[type='submit'][value='Update']",
        "#confirmbutton",
        "input[id='confirmbutton/']",
    ],
    "success": [
        "#notificationMsg",
        "div#notificationMsg",
        "text=The information was successfully updated",
    ],
    "error": [
        "#errorMsg",
        ".error",
        ".errorMessage",
        ".validation-error",
        "text=Error",
    ],
}

SECURITY_PATTERNS = [
    "captcha",
    "cloudflare",
    "verify you are human",
    "security challenge",
    "bot detection",
    "turnstile",
]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_test_send_limit(value: Any) -> int:
    """Return a Settings-controlled non-negative per-run Test Mode send limit."""
    parsed = int(value)
    if parsed < 0:
        raise ValueError("Maximum Test Send Limit must be 0 or greater; 0 disables sending.")
    return parsed


def safe_test_send_limit(value: Any) -> int:
    """Normalize persisted Test Mode limits; 0 explicitly disables sending."""
    try:
        return validate_test_send_limit(value)
    except (TypeError, ValueError):
        logging.warning(
            "Invalid persisted max_test_send_limit=%r; using safe default %s.",
            value,
            DEFAULT_TEST_SEND_LIMIT,
        )
        return DEFAULT_TEST_SEND_LIMIT


def _protect_local_secret(value: str) -> str:
    """Protect a secret with Windows DPAPI; return blank on unsupported platforms."""
    if os.name != "nt" or not value:
        return ""

    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    raw = value.encode("utf-8")
    raw_buffer = ctypes.create_string_buffer(raw)
    input_blob = DataBlob(
        len(raw), ctypes.cast(raw_buffer, ctypes.POINTER(ctypes.c_ubyte))
    )
    output_blob = DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DataBlob),
        wintypes.LPCWSTR,
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "Vib Tools License",
        None,
        None,
        None,
        0x01,  # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        protected = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return base64.b64encode(protected).decode("ascii")
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _unprotect_local_secret(value: str) -> str:
    """Unprotect a Windows DPAPI value created by :func:`_protect_local_secret`."""
    if os.name != "nt" or not value:
        return ""

    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
        ]

    protected = base64.b64decode(value.encode("ascii"), validate=True)
    protected_buffer = ctypes.create_string_buffer(protected)
    input_blob = DataBlob(
        len(protected),
        ctypes.cast(protected_buffer, ctypes.POINTER(ctypes.c_ubyte)),
    )
    output_blob = DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DataBlob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(DataBlob),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        0x01,  # CRYPTPROTECT_UI_FORBIDDEN
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        raw = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return raw.decode("utf-8")
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _strict_server_boolean(value: Any) -> bool:
    """Interpret license-server booleans without treating non-empty strings as true."""
    if value is True or value == 1:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return False


def _strict_local_boolean(value: Any, *, default: bool = False) -> bool:
    """Normalize persisted booleans without allowing arbitrary truthy strings."""
    if isinstance(value, bool):
        return value
    if value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


def safe_spreadsheet_cell(value: Any) -> Any:
    """Neutralize spreadsheet-formula prefixes in exported user-controlled text."""
    if not isinstance(value, str):
        return value
    if value.startswith(("\t", "\r")) or value.lstrip(" ").startswith(
        ("=", "+", "-", "@")
    ):
        return "'" + value
    return value


def safe_spreadsheet_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: safe_spreadsheet_cell(value) for key, value in row.items()}
        for row in rows
    ]


def _license_url_is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https" and bool(parsed.netloc):
        return True
    if not getattr(sys, "frozen", False):
        return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    return False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)[:80] or "data"


_PLAYWRIGHT_POPUP_BLOCKING_ARG = "--disable-popup-blocking"
_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG = "--disable-extensions"
_PLAYWRIGHT_MUTE_AUDIO_ARG = "--mute-audio"
_PLAYWRIGHT_BACKGROUND_THROTTLING_ARGS = (
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
)


def effective_ignored_default_args(
    settings: dict[str, Any], *, extensions_enabled: bool
) -> list[str]:
    """Resolve Browser Settings against Playwright's Chromium defaults."""
    raw = str(
        settings.get("ignored_default_args", DEFAULT_SETTINGS["ignored_default_args"])
    ).strip()
    ignored = shlex.split(raw, posix=(os.name != "nt")) if raw else []

    def add(value: str) -> None:
        if value not in ignored:
            ignored.append(value)

    def remove(value: str) -> None:
        while value in ignored:
            ignored.remove(value)

    if bool(settings.get("allow_popups", DEFAULT_SETTINGS["allow_popups"])):
        remove(_PLAYWRIGHT_POPUP_BLOCKING_ARG)
    else:
        add(_PLAYWRIGHT_POPUP_BLOCKING_ARG)

    if bool(
        settings.get(
            "background_throttling_enabled",
            DEFAULT_SETTINGS["background_throttling_enabled"],
        )
    ):
        for arg in _PLAYWRIGHT_BACKGROUND_THROTTLING_ARGS:
            add(arg)
    else:
        for arg in _PLAYWRIGHT_BACKGROUND_THROTTLING_ARGS:
            remove(arg)

    if extensions_enabled:
        add(_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG)

    # Playwright adds --mute-audio automatically for headless Chromium. Make
    # Audio Enabled authoritative by filtering that default when audio is on.
    # When audio is disabled, keep Playwright's default available; launch_browser()
    # also appends --mute-audio explicitly so headed and headless modes agree.
    if bool(settings.get("audio_enabled", DEFAULT_SETTINGS["audio_enabled"])):
        add(_PLAYWRIGHT_MUTE_AUDIO_ARG)
    else:
        remove(_PLAYWRIGHT_MUTE_AUDIO_ARG)

    return ignored


class SettingsManager:
    def __init__(self, path: Path):
        self.path = path
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self) -> dict[str, Any]:
        raw: dict[str, Any] = {}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    raw = loaded
                    self.data.update(raw)
            except Exception:
                logging.exception("Failed to load settings; defaults used")

        # Clear only the exact historical bundled contact placeholders. Custom
        # values entered by a user are preserved.
        legacy_placeholders = {
            "default_full_name": "**GPL Licensed** — This software is distributed under the GNU General Public License (GPL). For more information, visit https://vib.tools/.",
            "default_number": "For Support Whatapp : +880 1795-470603",
            "fallback_name": "**GPL Licensed** — This software is distributed under the GNU General Public License (GPL). For more information, visit https://vib.tools/.",
            "update_click_count": 1,
        }
        for key, old_value in legacy_placeholders.items():
            if self.data.get(key) == old_value and DEFAULT_SETTINGS.get(key, "") == "":
                self.data[key] = ""

        self.data["max_test_send_limit"] = safe_test_send_limit(
            self.data.get("max_test_send_limit", DEFAULT_TEST_SEND_LIMIT)
        )
        self.data["authorized_testing_only"] = _strict_local_boolean(
            self.data.get("authorized_testing_only"), default=False
        )

        # Browser settings migration/normalization. Legacy hidden controls are
        # converted to explicit Browser Settings and then removed.
        if raw.get("disable_image_font_media_loading") is True and not any(
            key in raw for key in ("block_images", "block_fonts", "block_media")
        ):
            self.data["block_images"] = True
            self.data["block_fonts"] = True
            self.data["block_media"] = True
        self.data.pop("disable_image_font_media_loading", None)

        # v1.0.6 briefly exposed Hardware Acceleration and GPU as two switches
        # even though both controlled the same Chromium --disable-gpu flag.
        if "hardware_acceleration_enabled" in raw:
            old_hardware = _strict_local_boolean(
                raw.get("hardware_acceleration_enabled"), default=True
            )
            old_gpu = _strict_local_boolean(
                self.data.get("gpu_enabled"),
                default=bool(DEFAULT_SETTINGS["gpu_enabled"]),
            )
            self.data["gpu_enabled"] = bool(old_hardware and old_gpu)
        self.data.pop("hardware_acceleration_enabled", None)

        browser_bool_keys = (
            "headless",
            "use_chrome_channel",
            "allow_chromium_fallback",
            "start_maximized",
            "no_viewport",
            "wait_for_network_idle",
            "block_images",
            "block_fonts",
            "block_media",
            "preserve_storage_state_on_recycle",
            "restore_page_after_context_recycle",
            "auto_focus_browser_on_open",
            "auto_dismiss_browser_dialogs",
            "scroll_before_interaction",
            "re_open_after_success_per_order",
            "use_persistent_context",
            "dedicated_profile_per_task",
            "persist_profile_between_runs",
            "persist_profile_cache",
            "gpu_enabled",
            "sandbox_enabled",
            "geolocation_enabled",
            "has_touch",
            "is_mobile",
            "javascript_enabled",
            "permission_notifications",
            "permission_clipboard_read",
            "permission_clipboard_write",
            "permission_camera",
            "permission_microphone",
            "permission_geolocation",
            "accept_downloads",
            "ignore_https_errors",
            "allow_popups",
            "extensions_enabled",
            "restore_previous_session",
            "offline",
            "audio_enabled",
            "hardware_video_decode_enabled",
            "devtools_auto_open",
            "background_throttling_enabled",
            "browser_console_logging",
            "network_event_logging",
            "chromium_logging_enabled",
            "record_har_enabled",
            "auto_restart_browser_on_crash",
            "preserve_cookies_on_recycle",
            "preserve_local_storage_on_recycle",
            "preserve_indexeddb_on_recycle",
            "page_init_script_enabled",
            "strict_selectors",
            "handle_sigint",
            "handle_sigterm",
            "handle_sighup",
            "bypass_csp",
            "record_video_enabled",
            "http_cache_enabled",
        )
        for key in browser_bool_keys:
            if key in DEFAULT_SETTINGS:
                self.data[key] = _strict_local_boolean(
                    self.data.get(key), default=bool(DEFAULT_SETTINGS[key])
                )

        enum_defaults = {
            "navigation_wait_until": {"commit", "domcontentloaded", "load", "networkidle"},
            "profile_lock_policy": {"fail", "fallback_ephemeral"},
            "color_scheme": {"default", "light", "dark", "no-preference"},
            "reduced_motion": {"default", "reduce", "no-preference"},
            "forced_colors": {"default", "active", "none"},
            "contrast": {"default", "more", "no-preference"},
            "service_workers": {"allow", "block"},
            "webrtc_ip_policy": {
                "default",
                "default_public_interface_only",
                "default_public_and_private_interfaces",
                "disable_non_proxied_udp",
            },
            "autoplay_policy": {
                "default",
                "no-user-gesture-required",
                "user-gesture-required",
                "document-user-activation-required",
            },
            "record_har_mode": {"full", "minimal"},
            "record_har_content": {"embed", "attach", "omit"},
        }
        for key, allowed in enum_defaults.items():
            value = str(self.data.get(key, DEFAULT_SETTINGS[key])).strip().lower()
            if value not in allowed:
                value = str(DEFAULT_SETTINGS[key]).strip().lower()
            self.data[key] = value

        level_name = str(self.data.get("log_level", DEFAULT_SETTINGS["log_level"])).upper()
        if level_name not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
            level_name = str(DEFAULT_SETTINGS["log_level"]).upper()
        self.data["log_level"] = level_name
        logging.getLogger().setLevel(getattr(logging, level_name, logging.INFO))

        # v1.0.6 private deployment: the validation URL is source-controlled and
        # is no longer user-editable or persisted in settings.json.
        self.data.pop("license_validation_url", None)
        self.save()
        return self.data

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def reset(self) -> None:
        self.data = dict(DEFAULT_SETTINGS)
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()


class LicenseManager:
    """Activation manager with remote validation and protected local persistence.

    Production builds require an HTTPS validation endpoint. Windows builds protect
    the locally cached license key with the current-user DPAPI profile.
    """

    def __init__(self, settings: SettingsManager):
        self.settings = settings
        self.license_key = ""
        self.license_hash = ""
        self.user_email = ""
        self.activated_until: str | None = None
        self.load()

    def load(self) -> None:
        if not LICENSE_FILE.exists():
            return
        try:
            data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
            protected_key = str(data.get("license_key_protected", "")).strip()
            legacy_plaintext_key = str(data.get("license_key", "")).strip()
            self.license_key = ""
            if protected_key:
                self.license_key = _unprotect_local_secret(protected_key)
            elif legacy_plaintext_key:
                self.license_key = legacy_plaintext_key

            self.license_hash = str(data.get("license_hash", "")).strip()
            self.user_email = str(data.get("user_email", "")).strip()
            self.activated_until = data.get("activated_until")

            expected_hash = (
                hashlib.sha256(self.license_key.encode()).hexdigest()
                if self.license_key
                else ""
            )
            if self.license_key and self.license_hash not in {"", expected_hash}:
                logging.error(
                    "Stored license key hash mismatch; local activation was rejected."
                )
                self.license_key = ""
                self.license_hash = ""
            elif self.license_key:
                self.license_hash = expected_hash
                self.save()
        except Exception:
            self.license_key = ""
            self.license_hash = ""
            self.user_email = ""
            self.activated_until = None
            logging.exception("Failed to load protected license data")

    def save(self) -> None:
        license_hash = (
            hashlib.sha256(self.license_key.encode()).hexdigest()
            if self.license_key
            else self.license_hash
        )
        self.license_hash = license_hash
        protected_key = ""
        if self.license_key:
            try:
                protected_key = _protect_local_secret(self.license_key)
            except Exception:
                logging.exception(
                    "Failed to protect the license key with Windows DPAPI"
                )
        LICENSE_FILE.write_text(
            json.dumps(
                {
                    "license_key_protected": protected_key,
                    "license_hash": license_hash,
                    "user_email": self.user_email,
                    "activated_until": self.activated_until,
                    "device_id": self.device_id(),
                    "saved_at": now_str(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def device_id(self) -> str:
        raw = f"{uuid.getnode()}-{os.getenv('COMPUTERNAME', '')}-{os.getenv('USERNAME', '')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def validate(self, license_key: str, email: str) -> tuple[bool, str]:
        license_key = license_key.strip()
        email = email.strip()
        if len(license_key) < 8:
            return False, "License key must be at least 8 characters."
        if email and not EMAIL_RE.match(email):
            return False, "Please enter a valid email address."
        url = LICENSE_VERIFY_URL.strip()
        api_key = LICENSE_API_KEY.strip()
        if not api_key or api_key == "REPLACE_WITH_YOUR_LICORA_API_KEY":
            return False, "License API key is not configured in app.py."
        if url:
            if not _license_url_is_allowed(url):
                return False, "License validation URL must use HTTPS."
            try:
                device_hash = self.device_id()
                request_payload = {
                    "license_key": license_key,
                    "email": email,
                    "device_hash": device_hash,
                    "device_id": device_hash,
                    "app_id": APP_NAME,
                    "app_name": APP_NAME,
                    "app_version": APP_VERSION,
                    "version": APP_VERSION,
                }
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": f"{APP_NAME}/{APP_VERSION}",
                }
                request_payload["api_key"] = api_key
                headers["X-API-Key"] = api_key
                headers["Authorization"] = f"Bearer {api_key}"
                request_timeout = min(
                    300.0,
                    max(1.0, float(self.settings.get("request_timeout", DEFAULT_SETTINGS["request_timeout"]))),
                )
                # Bandit B113 false positive: request_timeout is explicitly bounded above.
                response = requests.post(  # nosec B113
                    url,
                    json=request_payload,
                    headers=headers,
                    timeout=request_timeout,
                )
                try:
                    payload = response.json()
                except Exception:
                    payload = {}
                if response.status_code != 200:
                    server_message = (
                        payload.get("message") if isinstance(payload, dict) else ""
                    )
                    if server_message:
                        return (
                            False,
                            f"License server returned HTTP {response.status_code}: {server_message}",
                        )
                    return (
                        False,
                        f"License server returned HTTP {response.status_code}.",
                    )
                if not isinstance(payload, dict):
                    return False, "License server returned an invalid response."
                if "valid" in payload:
                    is_valid = _strict_server_boolean(payload.get("valid"))
                elif "success" in payload:
                    is_valid = _strict_server_boolean(payload.get("success"))
                else:
                    is_valid = False
                if not is_valid:
                    return False, str(payload.get("message", "License rejected."))
                license_info = (
                    payload.get("license", {})
                    if isinstance(payload.get("license"), dict)
                    else {}
                )
                self.activated_until = (
                    payload.get("activated_until")
                    or payload.get("expires_at")
                    or license_info.get("expires")
                    or license_info.get("expires_at")
                )
                if self.activated_until:
                    try:
                        expiry = datetime.strptime(
                            str(self.activated_until)[:10], "%Y-%m-%d"
                        )
                    except (TypeError, ValueError):
                        return (
                            False,
                            "License server returned an invalid expiration date.",
                        )
                    if expiry.date() < datetime.now().date():
                        return False, "License has expired."
            except Exception as exc:
                logging.exception("Remote license validation failed")
                return False, f"License validation failed: {exc}"
        else:
            if getattr(sys, "frozen", False):
                return (
                    False,
                    "License validation URL is required for production builds.",
                )
            self.activated_until = (datetime.now() + timedelta(days=365)).strftime(
                "%Y-%m-%d"
            )
        self.license_key = license_key
        self.license_hash = hashlib.sha256(license_key.encode()).hexdigest()
        self.user_email = email
        self.save()
        logging.info("License validated for %s", email or "local user")
        return True, "License activated successfully."

    def is_activated(self) -> bool:
        if not self.license_key:
            return False
        expected_hash = hashlib.sha256(self.license_key.encode()).hexdigest()
        if not self.license_hash or self.license_hash != expected_hash:
            return False
        if not self.activated_until:
            return True
        try:
            expiry = datetime.strptime(str(self.activated_until)[:10], "%Y-%m-%d")
        except (TypeError, ValueError):
            return False
        return expiry.date() >= datetime.now().date()

    def logout(self) -> None:
        self.license_key = ""
        self.license_hash = ""
        self.user_email = ""
        self.activated_until = None
        try:
            LICENSE_FILE.unlink(missing_ok=True)
        except Exception:
            logging.exception("Failed to remove license file")


@dataclass
class TaskItem:
    email: str
    name: str = ""
    status: str = "pending"
    attempts: int = 0
    message: str = ""
    result: str = ""


@dataclass
class TaskState:
    slot_id: int
    target_url: str = ""
    items: list[TaskItem] = field(default_factory=list)
    current_index: int = 0
    success_count: int = 0
    failed_count: int = 0
    status: str = "Ready"
    created_at: str = field(default_factory=now_str)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.current_index)

    @property
    def progress(self) -> float:
        return (self.current_index / self.total) if self.total else 0.0


class AutomationWorker(threading.Thread):
    """Persistent per-task Playwright owner.

    Playwright's synchronous objects stay inside this thread for their entire
    lifetime. The browser opens once, preserves the authenticated session, and
    accepts controlled start/focus/close commands from the UI thread.
    """

    def __init__(
        self,
        state: TaskState,
        settings: dict[str, Any],
        ui_queue: queue.Queue,
        stop_event: threading.Event,
        pause_event: threading.Event,
        initial_url: str,
    ):
        super().__init__(daemon=True, name=f"slot-{state.slot_id}-browser-worker")
        self.state = state
        self.settings = dict(settings)
        self.ui_queue = ui_queue
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.initial_url = initial_url
        self.browser = None
        self.context = None
        self.active_page = None
        self.playwright = None
        self.context_created_at = time.monotonic()
        self.context_item_count = 0
        self.control_queue: queue.Queue = queue.Queue()
        self.browser_ready_event = threading.Event()
        self.login_verified_event = threading.Event()
        self.processing_event = threading.Event()
        self.close_event = threading.Event()
        self.last_login_probe_at = 0.0
        self.run_send_count = 0
        self.run_send_limit = safe_test_send_limit(
            self.settings.get("max_test_send_limit", DEFAULT_SETTINGS["max_test_send_limit"])
        )
        self.persistent_context_mode = False
        self.temporary_profile_dir: Path | None = None
        self.active_profile_dir: Path | None = None
        self.browser_restart_count = 0
        self.resource_route_handler = None

    def emit(self, kind: str, payload: dict[str, Any]) -> None:
        payload["slot_id"] = self.state.slot_id
        self.ui_queue.put((kind, payload))

    def log(self, message: str, level: str = "INFO") -> None:
        logging.log(
            getattr(logging, level, logging.INFO),
            "Slot %s: %s",
            self.state.slot_id,
            message,
        )
        self.emit("log", {"message": message, "level": level, "timestamp": now_str()})

    def request_start(self, settings: dict[str, Any], target_url: str) -> None:
        self.control_queue.put(
            ("start", {"settings": dict(settings), "target_url": target_url})
        )

    def request_focus(self) -> None:
        self.control_queue.put(("focus", {}))

    def request_close(self) -> None:
        self.close_event.set()
        self.stop_event.set()
        self.pause_event.clear()
        self.control_queue.put(("close", {}))

    def is_browser_ready(self) -> bool:
        if not self.browser_ready_event.is_set():
            return False
        if self.persistent_context_mode:
            return bool(self.context and self.active_page and not self.active_page.is_closed())
        return bool(self.browser and self.browser.is_connected())

    def is_processing(self) -> bool:
        return self.processing_event.is_set()

    def is_login_verified(self) -> bool:
        return self.login_verified_event.is_set()

    def run(self) -> None:
        restart_attempts = 0
        try:
            self.launch_browser()
            self.browser_ready_event.set()
            self.state.status = "Login Required"
            self.emit("browser", {"status": "Open"})
            self.emit("status", {"status": "Login Required"})
            self.emit(
                "login",
                {"verified": False, "message": "Complete login in the opened browser."},
            )

            while not self.close_event.is_set():
                try:
                    command, payload = self.control_queue.get(timeout=0.2)
                except queue.Empty:
                    if not self.is_browser_ready():
                        if bool(
                            self.settings.get(
                                "auto_restart_browser_on_crash",
                                DEFAULT_SETTINGS["auto_restart_browser_on_crash"],
                            )
                        ):
                            max_restarts = max(
                                0,
                                int(
                                    self.settings.get(
                                        "browser_restart_max_attempts",
                                        DEFAULT_SETTINGS["browser_restart_max_attempts"],
                                    )
                                ),
                            )
                            if restart_attempts < max_restarts:
                                restart_attempts += 1
                                self.browser_restart_count += 1
                                delay = max(
                                    0.0,
                                    float(
                                        self.settings.get(
                                            "browser_restart_delay",
                                            DEFAULT_SETTINGS["browser_restart_delay"],
                                        )
                                    ),
                                )
                                self.log(
                                    f"Browser closed unexpectedly; automatic restart "
                                    f"{restart_attempts}/{max_restarts} scheduled.",
                                    "WARNING",
                                )
                                self.interruptible_sleep(delay)
                                try:
                                    if self.context:
                                        self.context.close()
                                except Exception:
                                    pass
                                try:
                                    if self.browser:
                                        self.browser.close()
                                except Exception:
                                    pass
                                self.context = None
                                self.browser = None
                                self.active_page = None
                                self.launch_browser()
                                self.browser_ready_event.set()
                                self.emit("browser", {"status": "Open"})
                                self.emit(
                                    "login",
                                    {
                                        "verified": False,
                                        "message": "Browser restarted. Verify the current login session.",
                                    },
                                )
                                continue
                        raise RuntimeError(
                            "Browser was closed outside the application."
                        ) from None
                    restart_attempts = 0
                    self.refresh_login_verification()
                    continue

                if command == "close":
                    break
                if command == "settings":
                    self.settings = dict(payload.get("settings", self.settings))
                    # Context default timeouts and supported mutable context options
                    # are updated inside the Playwright owner thread.
                    if self.context:
                        self.context.set_default_navigation_timeout(
                            max(
                                1000,
                                int(
                                    self.settings.get(
                                        "page_navigation_timeout",
                                        DEFAULT_SETTINGS["page_navigation_timeout"],
                                    )
                                ),
                            )
                        )
                        self.context.set_default_timeout(
                            max(
                                1000,
                                int(
                                    self.settings.get(
                                        "selector_timeout",
                                        DEFAULT_SETTINGS["selector_timeout"],
                                    )
                                ),
                            )
                        )
                        try:
                            self.context.set_offline(
                                bool(
                                    self.settings.get(
                                        "offline", DEFAULT_SETTINGS["offline"]
                                    )
                                )
                            )
                        except Exception as exc:
                            self.log(f"Could not update offline mode live: {exc}", "WARNING")

                        try:
                            headers: dict[str, str] = {}
                            raw_headers = str(
                                self.settings.get(
                                    "extra_http_headers_json",
                                    DEFAULT_SETTINGS["extra_http_headers_json"],
                                )
                            ).strip()
                            if raw_headers:
                                loaded_headers = json.loads(raw_headers)
                                if isinstance(loaded_headers, dict):
                                    headers.update(
                                        {
                                            str(k): str(v)
                                            for k, v in loaded_headers.items()
                                        }
                                    )
                            accept_language = str(
                                self.settings.get(
                                    "accept_language",
                                    DEFAULT_SETTINGS["accept_language"],
                                )
                            ).strip()
                            if accept_language:
                                headers["Accept-Language"] = accept_language
                            self.context.set_extra_http_headers(headers)
                        except Exception as exc:
                            self.log(
                                f"Could not update browser HTTP headers live: {exc}",
                                "WARNING",
                            )

                        try:
                            if bool(
                                self.settings.get(
                                    "geolocation_enabled",
                                    DEFAULT_SETTINGS["geolocation_enabled"],
                                )
                            ):
                                self.context.set_geolocation(
                                    {
                                        "latitude": float(
                                            self.settings.get(
                                                "geolocation_latitude",
                                                DEFAULT_SETTINGS["geolocation_latitude"],
                                            )
                                        ),
                                        "longitude": float(
                                            self.settings.get(
                                                "geolocation_longitude",
                                                DEFAULT_SETTINGS["geolocation_longitude"],
                                            )
                                        ),
                                        "accuracy": max(
                                            0.0,
                                            float(
                                                self.settings.get(
                                                    "geolocation_accuracy",
                                                    DEFAULT_SETTINGS["geolocation_accuracy"],
                                                )
                                            ),
                                        ),
                                    }
                                )
                            else:
                                self.context.set_geolocation(None)
                        except Exception as exc:
                            self.log(
                                f"Could not update geolocation live: {exc}", "WARNING"
                            )

                        try:
                            self.context.clear_permissions()
                            permissions = []
                            permission_map = (
                                ("permission_notifications", "notifications"),
                                ("permission_clipboard_read", "clipboard-read"),
                                ("permission_clipboard_write", "clipboard-write"),
                                ("permission_camera", "camera"),
                                ("permission_microphone", "microphone"),
                                ("permission_geolocation", "geolocation"),
                            )
                            for key, permission in permission_map:
                                if bool(
                                    self.settings.get(key, DEFAULT_SETTINGS[key])
                                ):
                                    permissions.append(permission)
                            if permissions:
                                self.context.grant_permissions(permissions)
                        except Exception as exc:
                            self.log(
                                f"Could not update browser permissions live: {exc}",
                                "WARNING",
                            )

                        try:
                            if self.resource_route_handler is not None:
                                try:
                                    self.context.unroute(
                                        "**/*", self.resource_route_handler
                                    )
                                except Exception:
                                    pass
                                route_required = (
                                    not bool(
                                        self.settings.get(
                                            "http_cache_enabled",
                                            DEFAULT_SETTINGS["http_cache_enabled"],
                                        )
                                    )
                                    or bool(
                                        self.settings.get(
                                            "block_images",
                                            DEFAULT_SETTINGS["block_images"],
                                        )
                                    )
                                    or bool(
                                        self.settings.get(
                                            "block_fonts",
                                            DEFAULT_SETTINGS["block_fonts"],
                                        )
                                    )
                                    or bool(
                                        self.settings.get(
                                            "block_media",
                                            DEFAULT_SETTINGS["block_media"],
                                        )
                                    )
                                )
                                if route_required:
                                    self.context.route(
                                        "**/*", self.resource_route_handler
                                    )
                        except Exception as exc:
                            self.log(
                                f"Could not update HTTP cache/resource routing live: {exc}",
                                "WARNING",
                            )
                    self.log(
                        "Browser runtime settings synchronized from Browser Settings."
                    )
                    continue
                if command == "focus":
                    self.bring_browser_to_front()
                    self.refresh_login_verification(force_emit=True)
                    continue
                if command == "start":
                    if self.processing_event.is_set():
                        self.log(
                            "Start request ignored because the task is already processing.",
                            "WARNING",
                        )
                        continue
                    self.settings = dict(payload.get("settings", self.settings))
                    self.state.target_url = str(
                        payload.get("target_url", self.state.target_url)
                    ).strip()
                    self.stop_event.clear()
                    self.pause_event.clear()
                    self.run_send_count = 0
                    self.run_send_limit = safe_test_send_limit(
                        self.settings.get(
                            "max_test_send_limit", DEFAULT_TEST_SEND_LIMIT
                        )
                    )
                    try:
                        self.ensure_authenticated_test_session()
                        self.emit(
                            "send_limit", {"used": 0, "limit": self.run_send_limit}
                        )
                        self.process_batch()
                    except SessionVerificationError as exc:
                        self.state.status = "Login/Test Mode Required"
                        self.login_verified_event.clear()
                        self.log(str(exc), "ERROR")
                        self.emit("login", {"verified": False, "message": str(exc)})
                        self.emit("status", {"status": self.state.status})
        except Exception as exc:
            self.state.status = "Browser Failed"
            self.log(f"Browser worker failed: {exc}", "ERROR")
            self.emit("status", {"status": "Browser Failed"})
        finally:
            self.processing_event.clear()
            self.browser_ready_event.clear()
            self.login_verified_event.clear()
            self.cleanup()
            self.emit("browser", {"status": "Closed"})
            self.emit("done", {"status": self.state.status})

    def test_mode_banner_ready(self, page) -> bool:
        if not page or page.is_closed():
            return False
        if not self.any_visible(
            page,
            SELECTORS["test_mode_banner"],
            timeout=max(0, int(self.settings.get("short_dom_probe_timeout", DEFAULT_SETTINGS["short_dom_probe_timeout"]))),
        ):
            return False
        text = self.first_visible_text(page, SELECTORS["test_mode_banner"]).upper()
        return "TEST MODE" in text

    def authenticated_test_session_ready(self, page) -> bool:
        return bool(
            page
            and not page.is_closed()
            and self.test_mode_banner_ready(page)
            and self.share_button_ready(page)
        )

    def refresh_login_verification(self, force_emit: bool = False) -> bool:
        if self.processing_event.is_set() or not self.browser_ready_event.is_set():
            return self.login_verified_event.is_set()
        now = time.monotonic()
        poll_interval = max(
            0.0,
            float(
                self.settings.get(
                    "login_state_poll_interval",
                    DEFAULT_SETTINGS["login_state_poll_interval"],
                )
            ),
        )
        if not force_emit and now - self.last_login_probe_at < poll_interval:
            return self.login_verified_event.is_set()
        self.last_login_probe_at = now
        verified = False
        try:
            verified = self.authenticated_test_session_ready(self.active_page)
        except Exception:
            verified = False
        previous = self.login_verified_event.is_set()
        if verified:
            self.login_verified_event.set()
        else:
            self.login_verified_event.clear()
        if force_emit or verified != previous:
            message = (
                "Authenticated Test Mode page verified."
                if verified
                else "Login is not verified. Open the authenticated Target URL in Test Mode."
            )
            self.emit("login", {"verified": verified, "message": message})
            if not self.processing_event.is_set():
                self.state.status = "Login Verified" if verified else "Login Required"
                self.emit("status", {"status": self.state.status})
        return verified

    def wait_for_authenticated_test_session(self) -> bool:
        max_retry = max(0, int(self.settings.get("max_selector_retry", DEFAULT_SETTINGS["max_selector_retry"])))
        for attempt in range(max_retry + 1):
            self.detect_security(self.active_page)
            if self.authenticated_test_session_ready(self.active_page):
                self.login_verified_event.set()
                self.emit(
                    "login",
                    {
                        "verified": True,
                        "message": "Authenticated Test Mode page verified.",
                    },
                )
                return True
            if attempt < max_retry:
                self.log(
                    f"Login/Test Mode verification retry {attempt + 1}/{max_retry}.",
                    "WARNING",
                )
                self.interruptible_sleep(
                    max(0.2, float(self.settings.get("retry_delay_min", DEFAULT_SETTINGS["retry_delay_min"])))
                )
        return False

    def ensure_authenticated_test_session(self) -> None:
        if self.authenticated_test_session_ready(self.active_page):
            self.login_verified_event.set()
            self.emit(
                "login",
                {"verified": True, "message": "Authenticated Test Mode page verified."},
            )
            return

        self.log(
            "Authenticated Test Mode page was not detected on the current tab; opening the configured Target URL.",
            "WARNING",
        )
        self.safe_goto(self.active_page, self.state.target_url)
        if self.wait_for_authenticated_test_session():
            return

        self.login_verified_event.clear()
        if not self.test_mode_banner_ready(self.active_page):
            raise SessionVerificationError(
                "Automation blocked: the Test Mode banner was not detected. Complete login and open the Target URL in Test Mode."
            )
        raise SessionVerificationError(
            "Automation blocked: login could not be verified because the authenticated Share page was not detected."
        )

    def assert_test_mode(self, page) -> None:
        if self.test_mode_banner_ready(page):
            return
        self.login_verified_event.clear()
        self.emit(
            "login",
            {
                "verified": False,
                "message": "Automation blocked because the Test Mode banner disappeared or was not detected.",
            },
        )
        raise TestModeRequired(
            "Automation blocked: Test Mode banner is required before every Send operation."
        )

    def process_batch(self) -> None:
        self.processing_event.set()
        self.state.status = "Running"
        self.emit("status", {"status": "Running"})
        self.emit_progress()
        limit_reached = False
        session_blocked = False
        processing_interrupted = False
        try:
            if self.state.current_index >= self.state.total:
                self.state.status = "Completed"
                self.log("No remaining email records to process.", "WARNING")
                self.emit("status", {"status": "Completed"})
                return

            for index in range(self.state.current_index, self.state.total):
                if self.stop_event.is_set() or self.close_event.is_set():
                    self.log("Stop requested; saving unprocessed data.")
                    break
                self.wait_if_paused()
                if self.stop_event.is_set() or self.close_event.is_set():
                    break

                item = self.state.items[index]
                self.process_item(index, item)
                if item.status in {"success", "failed"}:
                    self.state.current_index = index + 1
                else:
                    self.state.current_index = index
                    self.emit_progress(item)
                    if item.status == "limit_reached":
                        limit_reached = True
                        break
                    if item.status == "blocked":
                        session_blocked = True
                        break
                    if item.status in {"interrupted", "unprocessed"}:
                        processing_interrupted = True
                        break

                self.emit_progress(item)
                # Preserve the default same-page workflow. The existing Settings
                # switch may explicitly request a fresh page after each confirmed success.
                if item.status == "success":
                    if bool(
                        self.settings.get(
                            "re_open_after_success_per_order",
                            DEFAULT_SETTINGS["re_open_after_success_per_order"],
                        )
                    ):
                        self.reopen_active_page()
                else:
                    self.maybe_recycle_context()

                delay_min = max(
                    0.0, float(self.settings.get("delay_between_items_min", DEFAULT_SETTINGS["delay_between_items_min"]))
                )
                delay_max = max(
                    delay_min, float(self.settings.get("delay_between_items_max", DEFAULT_SETTINGS["delay_between_items_max"]))
                )
                self.interruptible_sleep(random.uniform(delay_min, delay_max))

            if limit_reached:
                self.state.status = "Test Send Limit Reached"
                self.save_unprocessed()
            elif session_blocked:
                self.state.status = "Login/Test Mode Required"
                self.save_unprocessed()
            elif processing_interrupted:
                self.state.status = "Interrupted"
                self.save_unprocessed()
            elif self.stop_event.is_set() or self.close_event.is_set():
                self.state.status = "Stopped"
                if bool(self.settings.get("save_unprocessed_data_on_close", DEFAULT_SETTINGS["save_unprocessed_data_on_close"])):
                    self.save_unprocessed()
            else:
                self.state.status = "Completed"
            self.emit("status", {"status": self.state.status})
        except Exception as exc:
            self.state.status = "Failed"
            self.log(f"Task failed: {exc}", "ERROR")
            self.emit("status", {"status": "Failed"})
            self.save_unprocessed()
        finally:
            self.save_failed()
            self.processing_event.clear()
            self.emit_progress()
            self.emit("done", {"status": self.state.status})

    def interruptible_sleep(self, seconds: float) -> None:
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            if self.stop_event.is_set() or self.close_event.is_set():
                return
            self.wait_if_paused()
            time.sleep(0.1)

    def wait_if_paused(self) -> None:
        while (
            self.pause_event.is_set()
            and not self.stop_event.is_set()
            and not self.close_event.is_set()
        ):
            self.state.status = "Paused"
            self.emit("status", {"status": "Paused"})
            time.sleep(0.2)
        if (
            not self.stop_event.is_set()
            and not self.close_event.is_set()
            and self.processing_event.is_set()
            and self.state.status == "Paused"
        ):
            self.state.status = "Running"
            self.emit("status", {"status": "Running"})

    def launch_browser(self) -> None:
        from playwright.sync_api import sync_playwright

        if self.playwright is None:
            self.playwright = sync_playwright().start()

        browser_args: list[str] = []

        if bool(
            self.settings.get(
                "start_maximized", DEFAULT_SETTINGS["start_maximized"]
            )
        ):
            browser_args.append("--start-maximized")

        window_width = int(
            self.settings.get("window_width", DEFAULT_SETTINGS["window_width"])
        )
        window_height = int(
            self.settings.get("window_height", DEFAULT_SETTINGS["window_height"])
        )
        if window_width > 0 and window_height > 0:
            browser_args.append(f"--window-size={window_width},{window_height}")

        window_x = int(
            self.settings.get(
                "window_position_x", DEFAULT_SETTINGS["window_position_x"]
            )
        )
        window_y = int(
            self.settings.get(
                "window_position_y", DEFAULT_SETTINGS["window_position_y"]
            )
        )
        if window_x >= 0 and window_y >= 0:
            browser_args.append(f"--window-position={window_x},{window_y}")

        if not bool(
            self.settings.get("gpu_enabled", DEFAULT_SETTINGS["gpu_enabled"])
        ):
            browser_args.append("--disable-gpu")

        # Playwright adds --disable-popup-blocking by default. This setting is
        # made authoritative together with effective_ignored_default_args().
        if bool(
            self.settings.get("allow_popups", DEFAULT_SETTINGS["allow_popups"])
        ):
            browser_args.append(_PLAYWRIGHT_POPUP_BLOCKING_ARG)

        if not bool(
            self.settings.get("audio_enabled", DEFAULT_SETTINGS["audio_enabled"])
        ):
            browser_args.append(_PLAYWRIGHT_MUTE_AUDIO_ARG)

        autoplay_policy = str(
            self.settings.get(
                "autoplay_policy", DEFAULT_SETTINGS["autoplay_policy"]
            )
        ).strip()
        if autoplay_policy and autoplay_policy != "default":
            browser_args.append(f"--autoplay-policy={autoplay_policy}")

        if not bool(
            self.settings.get(
                "hardware_video_decode_enabled",
                DEFAULT_SETTINGS["hardware_video_decode_enabled"],
            )
        ):
            browser_args.append("--disable-accelerated-video-decode")

        remote_debugging_port = max(
            0,
            int(
                self.settings.get(
                    "remote_debugging_port",
                    DEFAULT_SETTINGS["remote_debugging_port"],
                )
            ),
        )
        if remote_debugging_port > 0:
            browser_args.append(f"--remote-debugging-port={remote_debugging_port}")
            browser_args.append("--remote-debugging-address=127.0.0.1")

        # Playwright 1.61 no longer exposes a BrowserType.launch(devtools=...)
        # parameter. Keep the Browser Settings control real by using Chromium's
        # supported auto-open DevTools command-line switch instead.
        if bool(
            self.settings.get(
                "devtools_auto_open", DEFAULT_SETTINGS["devtools_auto_open"]
            )
        ):
            browser_args.append("--auto-open-devtools-for-tabs")

        if not bool(
            self.settings.get(
                "background_throttling_enabled",
                DEFAULT_SETTINGS["background_throttling_enabled"],
            )
        ):
            browser_args.extend(_PLAYWRIGHT_BACKGROUND_THROTTLING_ARGS)

        renderer_limit = max(
            0,
            int(
                self.settings.get(
                    "renderer_process_limit",
                    DEFAULT_SETTINGS["renderer_process_limit"],
                )
            ),
        )
        if renderer_limit > 0:
            browser_args.append(f"--renderer-process-limit={renderer_limit}")

        dns_rules = str(
            self.settings.get(
                "dns_host_resolver_rules",
                DEFAULT_SETTINGS["dns_host_resolver_rules"],
            )
        ).strip()
        if dns_rules:
            browser_args.append(f"--host-resolver-rules={dns_rules}")

        webrtc_policy = str(
            self.settings.get(
                "webrtc_ip_policy", DEFAULT_SETTINGS["webrtc_ip_policy"]
            )
        ).strip()
        if webrtc_policy and webrtc_policy != "default":
            browser_args.append(
                f"--force-webrtc-ip-handling-policy={webrtc_policy}"
            )

        if bool(
            self.settings.get(
                "restore_previous_session",
                DEFAULT_SETTINGS["restore_previous_session"],
            )
        ) and bool(
            self.settings.get(
                "use_persistent_context", DEFAULT_SETTINGS["use_persistent_context"]
            )
        ):
            browser_args.append("--restore-last-session")

        feature_args = (
            ("enable_chrome_features", "--enable-features"),
            ("disable_chrome_features", "--disable-features"),
            ("enable_blink_features", "--enable-blink-features"),
            ("disable_blink_features", "--disable-blink-features"),
        )
        for key, flag in feature_args:
            value = str(self.settings.get(key, DEFAULT_SETTINGS[key])).strip()
            if value:
                browser_args.append(f"{flag}={value}")

        extra_args = str(
            self.settings.get(
                "additional_chromium_args",
                DEFAULT_SETTINGS["additional_chromium_args"],
            )
        ).strip()
        if extra_args:
            browser_args.extend(
                shlex.split(extra_args, posix=(os.name != "nt"))
            )

        extensions_enabled = bool(
            self.settings.get(
                "extensions_enabled", DEFAULT_SETTINGS["extensions_enabled"]
            )
        )
        extension_paths_raw = str(
            self.settings.get(
                "extension_paths", DEFAULT_SETTINGS["extension_paths"]
            )
        ).strip()
        extension_paths: list[str] = []
        if extension_paths_raw:
            for part in re.split(r"[;\n]+", extension_paths_raw):
                part = part.strip()
                if part:
                    extension_paths.append(str(Path(part).expanduser().resolve()))
        if extensions_enabled:
            if not bool(
                self.settings.get(
                    "use_persistent_context",
                    DEFAULT_SETTINGS["use_persistent_context"],
                )
            ):
                raise RuntimeError(
                    "Extension Loading requires Persistent Browser Context."
                )
            executable_path = str(
                self.settings.get(
                    "browser_executable_path",
                    DEFAULT_SETTINGS["browser_executable_path"],
                )
            ).strip()
            if bool(
                self.settings.get(
                    "use_chrome_channel",
                    DEFAULT_SETTINGS["use_chrome_channel"],
                )
            ) and not executable_path:
                raise RuntimeError(
                    "Chrome extension side-loading requires bundled/custom Chromium. "
                    "Disable Google Chrome Channel or provide a compatible Chromium executable."
                )
            if not extension_paths:
                raise RuntimeError(
                    "Extension Loading is enabled but no extension directory was configured."
                )
            joined_extensions = ",".join(extension_paths)
            browser_args.extend(
                [
                    f"--disable-extensions-except={joined_extensions}",
                    f"--load-extension={joined_extensions}",
                ]
            )

        launch_env = dict(os.environ)
        env_text = str(
            self.settings.get(
                "browser_env_json", DEFAULT_SETTINGS["browser_env_json"]
            )
        ).strip()
        if env_text:
            parsed_env = json.loads(env_text)
            if not isinstance(parsed_env, dict):
                raise RuntimeError("Browser Environment JSON must be a JSON object.")
            for key, value in parsed_env.items():
                launch_env[str(key)] = str(value)

        chromium_log_file = str(
            self.settings.get(
                "chromium_log_file", DEFAULT_SETTINGS["chromium_log_file"]
            )
        ).strip()
        if bool(
            self.settings.get(
                "chromium_logging_enabled",
                DEFAULT_SETTINGS["chromium_logging_enabled"],
            )
        ):
            browser_args.append("--enable-logging")
            if chromium_log_file:
                log_path = Path(chromium_log_file).expanduser()
                if not log_path.is_absolute():
                    log_path = LOGS_DIR / log_path
                log_path.parent.mkdir(parents=True, exist_ok=True)
                launch_env["CHROME_LOG_FILE"] = str(log_path.resolve())

        crash_dumps_directory = str(
            self.settings.get(
                "crash_dumps_directory",
                DEFAULT_SETTINGS["crash_dumps_directory"],
            )
        ).strip()
        if crash_dumps_directory:
            crash_dir = Path(crash_dumps_directory).expanduser()
            if not crash_dir.is_absolute():
                crash_dir = LOGS_DIR / crash_dir
            crash_dir.mkdir(parents=True, exist_ok=True)
            browser_args.append(f"--crash-dumps-dir={crash_dir.resolve()}")

        launch_args: dict[str, Any] = {
            "headless": bool(
                self.settings.get("headless", DEFAULT_SETTINGS["headless"])
            ),
            "slow_mo": max(
                0,
                int(
                    self.settings.get(
                        "slow_mo_delay", DEFAULT_SETTINGS["slow_mo_delay"]
                    )
                ),
            ),
            "timeout": max(
                1000,
                int(
                    self.settings.get(
                        "browser_launch_timeout",
                        DEFAULT_SETTINGS["browser_launch_timeout"],
                    )
                ),
            ),
            "env": launch_env,
            "chromium_sandbox": bool(
                self.settings.get(
                    "sandbox_enabled", DEFAULT_SETTINGS["sandbox_enabled"]
                )
            ),
            "handle_sigint": bool(
                self.settings.get("handle_sigint", DEFAULT_SETTINGS["handle_sigint"])
            ),
            "handle_sigterm": bool(
                self.settings.get("handle_sigterm", DEFAULT_SETTINGS["handle_sigterm"])
            ),
            "handle_sighup": bool(
                self.settings.get("handle_sighup", DEFAULT_SETTINGS["handle_sighup"])
            ),
        }
        if browser_args:
            launch_args["args"] = browser_args

        ignored_default_args = effective_ignored_default_args(
            self.settings, extensions_enabled=extensions_enabled
        )
        if ignored_default_args:
            launch_args["ignore_default_args"] = ignored_default_args

        downloads_path = str(
            self.settings.get(
                "downloads_path", DEFAULT_SETTINGS["downloads_path"]
            )
        ).strip()
        if downloads_path:
            dl_dir = Path(downloads_path).expanduser()
            if not dl_dir.is_absolute():
                dl_dir = APP_DATA_DIR / dl_dir
            dl_dir.mkdir(parents=True, exist_ok=True)
            launch_args["downloads_path"] = str(dl_dir.resolve())

        traces_dir_text = str(
            self.settings.get("traces_dir", DEFAULT_SETTINGS["traces_dir"])
        ).strip()
        if traces_dir_text:
            traces_dir = Path(traces_dir_text).expanduser()
            if not traces_dir.is_absolute():
                traces_dir = LOGS_DIR / traces_dir
            traces_dir.mkdir(parents=True, exist_ok=True)
            launch_args["traces_dir"] = str(traces_dir.resolve())

        executable_path = str(
            self.settings.get(
                "browser_executable_path",
                DEFAULT_SETTINGS["browser_executable_path"],
            )
        ).strip()
        if executable_path:
            launch_args["executable_path"] = str(
                Path(executable_path).expanduser().resolve()
            )
        elif extensions_enabled:
            # Playwright documents unpacked extension testing against its full
            # Chromium channel (persistent context required). This also keeps
            # extension loading functional in headless mode instead of falling
            # back to the separate headless shell.
            launch_args["channel"] = "chromium"
        elif bool(
            self.settings.get(
                "use_chrome_channel", DEFAULT_SETTINGS["use_chrome_channel"]
            )
        ):
            launch_args["channel"] = "chrome"

        startup_url = str(
            self.settings.get(
                "browser_startup_url", DEFAULT_SETTINGS["browser_startup_url"]
            )
        ).strip() or self.initial_url

        use_persistent = bool(
            self.settings.get(
                "use_persistent_context",
                DEFAULT_SETTINGS["use_persistent_context"],
            )
        )
        self.persistent_context_mode = use_persistent

        if use_persistent:
            profile_base_raw = str(
                self.settings.get(
                    "persistent_user_data_dir",
                    DEFAULT_SETTINGS["persistent_user_data_dir"],
                )
            ).strip()
            if profile_base_raw:
                profile_base = Path(profile_base_raw).expanduser()
                if not profile_base.is_absolute():
                    profile_base = APP_DATA_DIR / profile_base
            else:
                profile_base = APP_DATA_DIR / "BrowserProfiles"

            if bool(
                self.settings.get(
                    "persist_profile_between_runs",
                    DEFAULT_SETTINGS["persist_profile_between_runs"],
                )
            ):
                user_data_dir = profile_base
            else:
                user_data_dir = (
                    APP_DATA_DIR
                    / "BrowserProfilesTemp"
                    / f"slot_{self.state.slot_id}_{int(time.time() * 1000)}"
                )
                self.temporary_profile_dir = user_data_dir

            if bool(
                self.settings.get(
                    "dedicated_profile_per_task",
                    DEFAULT_SETTINGS["dedicated_profile_per_task"],
                )
            ):
                user_data_dir = user_data_dir / f"slot_{self.state.slot_id}"
                if self.temporary_profile_dir is not None:
                    self.temporary_profile_dir = user_data_dir

            user_data_dir.mkdir(parents=True, exist_ok=True)
            self.active_profile_dir = user_data_dir

            profile_directory = str(
                self.settings.get(
                    "persistent_profile_directory",
                    DEFAULT_SETTINGS["persistent_profile_directory"],
                )
            ).strip()
            if profile_directory:
                launch_args.setdefault("args", []).append(
                    f"--profile-directory={profile_directory}"
                )

            if not bool(
                self.settings.get(
                    "persist_profile_cache",
                    DEFAULT_SETTINGS["persist_profile_cache"],
                )
            ):
                profile_dir = user_data_dir / (profile_directory or "Default")
                cache_candidates = [
                    profile_dir / "Cache",
                    profile_dir / "Code Cache",
                    profile_dir / "GPUCache",
                    profile_dir / "DawnCache",
                    user_data_dir / "ShaderCache",
                    user_data_dir / "GrShaderCache",
                ]
                for cache_path in cache_candidates:
                    try:
                        if cache_path.exists():
                            shutil.rmtree(cache_path, ignore_errors=True)
                    except Exception as exc:
                        self.log(
                            f"Could not clear persistent-profile cache {cache_path}: {exc}",
                            "WARNING",
                        )

            persistent_args = dict(launch_args)
            persistent_args.update(self.context_arguments())
            persistent_error: Exception | None = None
            try:
                self.context = self.playwright.chromium.launch_persistent_context(
                    str(user_data_dir.resolve()),
                    **persistent_args,
                )
            except Exception as exc:
                persistent_error = exc
                if persistent_args.get("channel") == "chrome" and bool(
                    self.settings.get(
                        "allow_chromium_fallback",
                        DEFAULT_SETTINGS["allow_chromium_fallback"],
                    )
                ):
                    fallback_args = dict(persistent_args)
                    fallback_args.pop("channel", None)
                    self.log(
                        f"Chrome channel persistent launch unavailable; falling back "
                        f"to bundled Chromium. Detail: {exc}",
                        "WARNING",
                    )
                    try:
                        self.context = self.playwright.chromium.launch_persistent_context(
                            str(user_data_dir.resolve()),
                            **fallback_args,
                        )
                        persistent_error = None
                    except Exception as fallback_exc:
                        persistent_error = fallback_exc

            if self.context is not None:
                self.browser = self.context.browser
                self.log(
                    f"Persistent browser context launched for task {self.state.slot_id}."
                )
            else:
                policy = str(
                    self.settings.get(
                        "profile_lock_policy",
                        DEFAULT_SETTINGS["profile_lock_policy"],
                    )
                ).strip().lower()
                if policy != "fallback_ephemeral" or extensions_enabled:
                    if persistent_error is not None:
                        raise persistent_error
                    raise RuntimeError("Persistent browser context could not be opened.")
                self.log(
                    f"Persistent context could not be opened; falling back to an "
                    f"ephemeral browser context. Detail: {persistent_error}",
                    "WARNING",
                )
                self.persistent_context_mode = False
                self.context = None
                self.browser = None
                ephemeral_args = dict(launch_args)
                self.browser = self.playwright.chromium.launch(**ephemeral_args)

            self.new_context(initial_url=startup_url)
            return

        try:
            self.browser = self.playwright.chromium.launch(**launch_args)
            self.log(
                "Fresh browser launched; authenticated session will be retained for this task."
            )
        except Exception as exc:
            if launch_args.get("channel") and bool(
                self.settings.get(
                    "allow_chromium_fallback",
                    DEFAULT_SETTINGS["allow_chromium_fallback"],
                )
            ):
                launch_args.pop("channel", None)
                self.log(
                    f"Chrome channel unavailable; falling back to bundled Chromium. Detail: {exc}",
                    "WARNING",
                )
                self.browser = self.playwright.chromium.launch(**launch_args)
            else:
                raise
        self.new_context(initial_url=startup_url)

    def context_arguments(
        self, storage_state: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        context_args: dict[str, Any] = {}

        user_agent = str(
            self.settings.get("user_agent", DEFAULT_SETTINGS["user_agent"])
        ).strip()
        if user_agent:
            context_args["user_agent"] = user_agent

        proxy_server = str(
            self.settings.get("proxy", DEFAULT_SETTINGS["proxy"])
        ).strip()
        if proxy_server:
            proxy_config: dict[str, Any] = {"server": proxy_server}
            proxy_bypass = str(
                self.settings.get(
                    "proxy_bypass", DEFAULT_SETTINGS["proxy_bypass"]
                )
            ).strip()
            if proxy_bypass:
                proxy_config["bypass"] = proxy_bypass
            context_args["proxy"] = proxy_config

        no_viewport = bool(
            self.settings.get("no_viewport", DEFAULT_SETTINGS["no_viewport"])
        )
        if no_viewport:
            context_args["no_viewport"] = True
        else:
            viewport_width = max(
                1,
                int(
                    self.settings.get(
                        "viewport_width", DEFAULT_SETTINGS["viewport_width"]
                    )
                ),
            )
            viewport_height = max(
                1,
                int(
                    self.settings.get(
                        "viewport_height", DEFAULT_SETTINGS["viewport_height"]
                    )
                ),
            )
            context_args["viewport"] = {
                "width": viewport_width,
                "height": viewport_height,
            }
            screen_width = int(
                self.settings.get(
                    "screen_width", DEFAULT_SETTINGS["screen_width"]
                )
            )
            screen_height = int(
                self.settings.get(
                    "screen_height", DEFAULT_SETTINGS["screen_height"]
                )
            )
            if screen_width > 0 and screen_height > 0:
                context_args["screen"] = {
                    "width": screen_width,
                    "height": screen_height,
                }

        device_scale_factor = float(
            self.settings.get(
                "device_scale_factor",
                DEFAULT_SETTINGS["device_scale_factor"],
            )
        )
        if device_scale_factor > 0:
            context_args["device_scale_factor"] = device_scale_factor

        locale = str(
            self.settings.get("locale", DEFAULT_SETTINGS["locale"])
        ).strip()
        if locale:
            context_args["locale"] = locale

        timezone_id = str(
            self.settings.get("timezone_id", DEFAULT_SETTINGS["timezone_id"])
        ).strip()
        if timezone_id:
            context_args["timezone_id"] = timezone_id

        if bool(
            self.settings.get(
                "geolocation_enabled",
                DEFAULT_SETTINGS["geolocation_enabled"],
            )
        ):
            context_args["geolocation"] = {
                "latitude": float(
                    self.settings.get(
                        "geolocation_latitude",
                        DEFAULT_SETTINGS["geolocation_latitude"],
                    )
                ),
                "longitude": float(
                    self.settings.get(
                        "geolocation_longitude",
                        DEFAULT_SETTINGS["geolocation_longitude"],
                    )
                ),
                "accuracy": max(
                    0.0,
                    float(
                        self.settings.get(
                            "geolocation_accuracy",
                            DEFAULT_SETTINGS["geolocation_accuracy"],
                        )
                    ),
                ),
            }

        permissions = []
        permission_map = (
            ("permission_notifications", "notifications"),
            ("permission_clipboard_read", "clipboard-read"),
            ("permission_clipboard_write", "clipboard-write"),
            ("permission_camera", "camera"),
            ("permission_microphone", "microphone"),
            ("permission_geolocation", "geolocation"),
        )
        for key, permission in permission_map:
            if bool(self.settings.get(key, DEFAULT_SETTINGS[key])):
                permissions.append(permission)
        if permissions:
            context_args["permissions"] = permissions

        context_args["accept_downloads"] = bool(
            self.settings.get(
                "accept_downloads", DEFAULT_SETTINGS["accept_downloads"]
            )
        )
        context_args["ignore_https_errors"] = bool(
            self.settings.get(
                "ignore_https_errors",
                DEFAULT_SETTINGS["ignore_https_errors"],
            )
        )
        context_args["java_script_enabled"] = bool(
            self.settings.get(
                "javascript_enabled",
                DEFAULT_SETTINGS["javascript_enabled"],
            )
        )
        context_args["bypass_csp"] = bool(
            self.settings.get("bypass_csp", DEFAULT_SETTINGS["bypass_csp"])
        )
        context_args["has_touch"] = bool(
            self.settings.get("has_touch", DEFAULT_SETTINGS["has_touch"])
        )
        context_args["is_mobile"] = bool(
            self.settings.get("is_mobile", DEFAULT_SETTINGS["is_mobile"])
        )
        context_args["offline"] = bool(
            self.settings.get("offline", DEFAULT_SETTINGS["offline"])
        )
        context_args["service_workers"] = str(
            self.settings.get(
                "service_workers", DEFAULT_SETTINGS["service_workers"]
            )
        )
        context_args["strict_selectors"] = bool(
            self.settings.get(
                "strict_selectors", DEFAULT_SETTINGS["strict_selectors"]
            )
        )

        base_url = str(
            self.settings.get("base_url", DEFAULT_SETTINGS["base_url"])
        ).strip()
        if base_url:
            context_args["base_url"] = base_url

        color_scheme = str(
            self.settings.get(
                "color_scheme", DEFAULT_SETTINGS["color_scheme"]
            )
        ).strip()
        if color_scheme != "default":
            context_args["color_scheme"] = color_scheme

        reduced_motion = str(
            self.settings.get(
                "reduced_motion", DEFAULT_SETTINGS["reduced_motion"]
            )
        ).strip()
        if reduced_motion != "default":
            context_args["reduced_motion"] = reduced_motion

        forced_colors = str(
            self.settings.get(
                "forced_colors", DEFAULT_SETTINGS["forced_colors"]
            )
        ).strip()
        if forced_colors != "default":
            context_args["forced_colors"] = forced_colors

        contrast = str(
            self.settings.get("contrast", DEFAULT_SETTINGS["contrast"])
        ).strip()
        if contrast != "default":
            context_args["contrast"] = contrast

        headers: dict[str, str] = {}
        raw_headers = str(
            self.settings.get(
                "extra_http_headers_json",
                DEFAULT_SETTINGS["extra_http_headers_json"],
            )
        ).strip()
        if raw_headers:
            parsed_headers = json.loads(raw_headers)
            if not isinstance(parsed_headers, dict):
                raise RuntimeError(
                    "Extra HTTP Headers JSON must be a JSON object."
                )
            headers.update(
                {str(key): str(value) for key, value in parsed_headers.items()}
            )
        accept_language = str(
            self.settings.get(
                "accept_language", DEFAULT_SETTINGS["accept_language"]
            )
        ).strip()
        if accept_language:
            headers["Accept-Language"] = accept_language
        if headers:
            context_args["extra_http_headers"] = headers

        client_certificates_text = str(
            self.settings.get(
                "client_certificates_json",
                DEFAULT_SETTINGS["client_certificates_json"],
            )
        ).strip()
        if client_certificates_text and client_certificates_text != "[]":
            client_certificates = json.loads(client_certificates_text)
            if not isinstance(client_certificates, list):
                raise RuntimeError("Client Certificates setting must be a JSON array.")
            normalized_certificates: list[dict[str, Any]] = []
            for item in client_certificates:
                if not isinstance(item, dict):
                    raise RuntimeError(
                        "Every Client Certificates entry must be a JSON object."
                    )
                normalized = dict(item)
                for path_key in ("certPath", "keyPath", "pfxPath"):
                    path_value = str(normalized.get(path_key, "")).strip()
                    if path_value:
                        normalized[path_key] = str(
                            Path(path_value).expanduser().resolve()
                        )
                normalized_certificates.append(normalized)
            if normalized_certificates:
                context_args["client_certificates"] = normalized_certificates

        if bool(
            self.settings.get(
                "record_har_enabled", DEFAULT_SETTINGS["record_har_enabled"]
            )
        ):
            har_dir_text = str(
                self.settings.get(
                    "record_har_directory",
                    DEFAULT_SETTINGS["record_har_directory"],
                )
            ).strip()
            har_dir = (
                Path(har_dir_text).expanduser()
                if har_dir_text
                else LOGS_DIR / "BrowserHAR"
            )
            if not har_dir.is_absolute():
                har_dir = LOGS_DIR / har_dir
            har_dir.mkdir(parents=True, exist_ok=True)
            har_path = har_dir / (
                f"slot_{self.state.slot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.har"
            )
            context_args["record_har_path"] = str(har_path.resolve())
            context_args["record_har_mode"] = str(
                self.settings.get(
                    "record_har_mode", DEFAULT_SETTINGS["record_har_mode"]
                )
            )
            context_args["record_har_content"] = str(
                self.settings.get(
                    "record_har_content",
                    DEFAULT_SETTINGS["record_har_content"],
                )
            )
            har_filter = str(
                self.settings.get(
                    "record_har_url_filter",
                    DEFAULT_SETTINGS["record_har_url_filter"],
                )
            ).strip()
            if har_filter:
                context_args["record_har_url_filter"] = har_filter

        if bool(
            self.settings.get(
                "record_video_enabled", DEFAULT_SETTINGS["record_video_enabled"]
            )
        ):
            video_dir_text = str(
                self.settings.get(
                    "record_video_directory",
                    DEFAULT_SETTINGS["record_video_directory"],
                )
            ).strip()
            video_dir = (
                Path(video_dir_text).expanduser()
                if video_dir_text
                else LOGS_DIR / "BrowserVideo"
            )
            if not video_dir.is_absolute():
                video_dir = LOGS_DIR / video_dir
            video_dir.mkdir(parents=True, exist_ok=True)
            context_args["record_video_dir"] = str(video_dir.resolve())
            video_width = int(
                self.settings.get(
                    "record_video_width", DEFAULT_SETTINGS["record_video_width"]
                )
            )
            video_height = int(
                self.settings.get(
                    "record_video_height", DEFAULT_SETTINGS["record_video_height"]
                )
            )
            if video_width > 0 and video_height > 0:
                context_args["record_video_size"] = {
                    "width": video_width,
                    "height": video_height,
                }

        if storage_state:
            context_args["storage_state"] = storage_state
        return context_args

    def new_context(
        self, storage_state: dict[str, Any] | None = None, initial_url: str = ""
    ) -> None:
        using_precreated_persistent_context = bool(
            self.persistent_context_mode and self.context is not None
        )

        if not using_precreated_persistent_context:
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
            if not self.browser:
                raise RuntimeError("Browser instance is not available.")
            self.context = self.browser.new_context(
                **self.context_arguments(storage_state)
            )

        self.context.set_default_navigation_timeout(
            max(
                1000,
                int(
                    self.settings.get(
                        "page_navigation_timeout",
                        DEFAULT_SETTINGS["page_navigation_timeout"],
                    )
                ),
            )
        )
        self.context.set_default_timeout(
            max(
                1000,
                int(
                    self.settings.get(
                        "selector_timeout", DEFAULT_SETTINGS["selector_timeout"]
                    )
                ),
            )
        )

        # Optional page initialization script. This is a local file selected by
        # the operator and is applied at the BrowserContext level before pages.
        if bool(
            self.settings.get(
                "page_init_script_enabled",
                DEFAULT_SETTINGS["page_init_script_enabled"],
            )
        ):
            init_script_path = str(
                self.settings.get(
                    "page_init_script_path",
                    DEFAULT_SETTINGS["page_init_script_path"],
                )
            ).strip()
            if init_script_path:
                script_file = Path(init_script_path).expanduser().resolve()
                if not script_file.is_file():
                    raise RuntimeError(
                        f"Page Initialization Script not found: {script_file}"
                    )
                self.context.add_init_script(path=str(script_file))

        # Resource routing is installed only when the operator explicitly keeps
        # HTTP cache disabled or blocks a resource class. Playwright routing
        # disables the browser HTTP cache, so the Browser Settings control must
        # be authoritative rather than a UI-only preference.
        def route_handler(route):
            resource_type = route.request.resource_type
            should_block = (
                (
                    resource_type == "image"
                    and (
                        bool(
                            self.settings.get(
                                "block_images", DEFAULT_SETTINGS["block_images"]
                            )
                        )
                    )
                )
                or (
                    resource_type == "font"
                    and (
                        bool(
                            self.settings.get(
                                "block_fonts", DEFAULT_SETTINGS["block_fonts"]
                            )
                        )
                    )
                )
                or (
                    resource_type == "media"
                    and (
                        bool(
                            self.settings.get(
                                "block_media", DEFAULT_SETTINGS["block_media"]
                            )
                        )
                    )
                )
            )
            if should_block:
                route.abort()
            else:
                route.continue_()

        self.resource_route_handler = route_handler
        route_required = (
            not bool(
                self.settings.get(
                    "http_cache_enabled", DEFAULT_SETTINGS["http_cache_enabled"]
                )
            )
            or bool(self.settings.get("block_images", DEFAULT_SETTINGS["block_images"]))
            or bool(self.settings.get("block_fonts", DEFAULT_SETTINGS["block_fonts"]))
            or bool(self.settings.get("block_media", DEFAULT_SETTINGS["block_media"]))
        )
        if route_required:
            self.context.route("**/*", self.resource_route_handler)

        self.context_created_at = time.monotonic()
        self.context_item_count = 0

        def attach_page_events(page) -> None:
            def dialog_handler(dialog):
                if bool(
                    self.settings.get(
                        "auto_dismiss_browser_dialogs",
                        DEFAULT_SETTINGS["auto_dismiss_browser_dialogs"],
                    )
                ):
                    self.log(f"Dialog detected: {dialog.message}", "WARNING")
                    dialog.dismiss()
                else:
                    self.log(
                        f"Dialog detected and left for manual handling: {dialog.message}",
                        "WARNING",
                    )

            page.on("dialog", dialog_handler)

            def console_handler(message):
                if bool(
                    self.settings.get(
                        "browser_console_logging",
                        DEFAULT_SETTINGS["browser_console_logging"],
                    )
                ):
                    level = (
                        "ERROR"
                        if str(message.type).lower() == "error"
                        else "WARNING"
                        if str(message.type).lower() == "warning"
                        else "INFO"
                    )
                    self.log(
                        f"Browser console [{message.type}]: {message.text}",
                        level,
                    )

            page.on("console", console_handler)

            def page_error_handler(error):
                if bool(
                    self.settings.get(
                        "browser_console_logging",
                        DEFAULT_SETTINGS["browser_console_logging"],
                    )
                ):
                    self.log(f"Browser page error: {error}", "ERROR")

            page.on("pageerror", page_error_handler)

            def request_handler(request):
                if bool(
                    self.settings.get(
                        "network_event_logging",
                        DEFAULT_SETTINGS["network_event_logging"],
                    )
                ):
                    self.log(
                        f"Browser request: {request.method} {request.url}",
                        "INFO",
                    )

            def response_handler(response):
                if bool(
                    self.settings.get(
                        "network_event_logging",
                        DEFAULT_SETTINGS["network_event_logging"],
                    )
                ):
                    self.log(
                        f"Browser response: {response.status} {response.url}",
                        "INFO",
                    )

            def request_failed_handler(request):
                if bool(
                    self.settings.get(
                        "network_event_logging",
                        DEFAULT_SETTINGS["network_event_logging"],
                    )
                ):
                    self.log(
                        f"Browser request failed: {request.method} {request.url}",
                        "WARNING",
                    )

            page.on("request", request_handler)
            page.on("response", response_handler)
            page.on("requestfailed", request_failed_handler)

        self.context.on("page", attach_page_events)
        pages = list(self.context.pages)
        if using_precreated_persistent_context and pages:
            if bool(
                self.settings.get(
                    "restore_previous_session",
                    DEFAULT_SETTINGS["restore_previous_session"],
                )
            ):
                self.active_page = pages[-1]
            else:
                self.active_page = pages[0]
            # Pages restored with a persistent profile existed before this
            # listener was registered, so attach handlers explicitly.
            attach_page_events(self.active_page)
        else:
            # New pages are configured through the BrowserContext page event.
            self.active_page = self.context.new_page()

        should_open_initial_url = initial_url.startswith(("http://", "https://"))
        if (
            using_precreated_persistent_context
            and bool(
                self.settings.get(
                    "restore_previous_session",
                    DEFAULT_SETTINGS["restore_previous_session"],
                )
            )
            and self.active_page
            and not self.active_page.is_closed()
            and self.active_page.url
            and self.active_page.url not in {"about:blank", "chrome://newtab/"}
        ):
            should_open_initial_url = False

        if should_open_initial_url:
            try:
                self.safe_goto(self.active_page, initial_url)
            except Exception as exc:
                self.log(
                    f"Initial URL could not be opened automatically: {exc}",
                    "WARNING",
                )

        if bool(
            self.settings.get(
                "auto_focus_browser_on_open",
                DEFAULT_SETTINGS["auto_focus_browser_on_open"],
            )
        ):
            self.bring_browser_to_front()

    def bring_browser_to_front(self) -> None:
        try:
            if self.active_page and not self.active_page.is_closed():
                self.active_page.bring_to_front()
        except Exception as exc:
            self.log(f"Could not focus browser window: {exc}", "WARNING")

    def reopen_active_page(self) -> None:
        current_url = self.state.target_url
        try:
            if self.active_page and not self.active_page.is_closed():
                current_url = self.active_page.url or current_url
                self.active_page.close()
        except Exception:
            pass
        # BrowserContext page event wiring configured in new_context() attaches
        # dialog, console and network handlers to this replacement page.
        self.active_page = self.context.new_page()
        if current_url.startswith(("http://", "https://")):
            self.safe_goto(self.active_page, current_url)

    def maybe_recycle_context(self) -> None:
        self.context_item_count += 1
        n_limit = max(
            0,
            int(
                self.settings.get(
                    "browser_context_recycle_after_n_items",
                    DEFAULT_SETTINGS["browser_context_recycle_after_n_items"],
                )
            ),
        )
        min_limit = max(
            0.0,
            float(
                self.settings.get(
                    "browser_context_recycle_after_n_minutes",
                    DEFAULT_SETTINGS["browser_context_recycle_after_n_minutes"],
                )
            ),
        )
        should_recycle = (n_limit > 0 and self.context_item_count >= n_limit) or (
            min_limit > 0
            and (time.monotonic() - self.context_created_at) / 60 >= min_limit
        )
        if not should_recycle:
            return

        current_url = self.state.target_url
        storage_state = None
        preserve_state = bool(
            self.settings.get(
                "preserve_storage_state_on_recycle",
                DEFAULT_SETTINGS["preserve_storage_state_on_recycle"],
            )
        )
        restore_page = bool(
            self.settings.get(
                "restore_page_after_context_recycle",
                DEFAULT_SETTINGS["restore_page_after_context_recycle"],
            )
        )
        try:
            if self.active_page and not self.active_page.is_closed():
                current_url = self.active_page.url or current_url

            if preserve_state and not self.persistent_context_mode:
                preserve_indexeddb = bool(
                    self.settings.get(
                        "preserve_indexeddb_on_recycle",
                        DEFAULT_SETTINGS["preserve_indexeddb_on_recycle"],
                    )
                )
                storage_state = self.context.storage_state(
                    indexed_db=preserve_indexeddb
                )
                if isinstance(storage_state, dict):
                    if not bool(
                        self.settings.get(
                            "preserve_cookies_on_recycle",
                            DEFAULT_SETTINGS["preserve_cookies_on_recycle"],
                        )
                    ):
                        storage_state["cookies"] = []
                    for origin in storage_state.get("origins", []):
                        if not bool(
                            self.settings.get(
                                "preserve_local_storage_on_recycle",
                                DEFAULT_SETTINGS["preserve_local_storage_on_recycle"],
                            )
                        ):
                            origin["localStorage"] = []
                        if not preserve_indexeddb:
                            origin.pop("indexedDB", None)
        except Exception as exc:
            self.log(
                f"Could not capture browser storage state before recycle: {exc}",
                "WARNING",
            )

        self.log(
            "Recycling browser context"
            + (
                " while preserving configured session storage."
                if preserve_state
                else "."
            )
        )

        if self.persistent_context_mode:
            try:
                if self.context:
                    self.context.close()
            except Exception:
                pass
            self.context = None
            self.browser = None
            self.active_page = None
            old_initial_url = self.initial_url
            try:
                self.initial_url = current_url if restore_page else ""
                self.launch_browser()
            finally:
                self.initial_url = old_initial_url
            return

        self.new_context(
            storage_state=storage_state,
            initial_url=current_url if restore_page else "",
        )

    def process_item(self, index: int, item: TaskItem) -> None:
        max_retry = max(0, int(self.settings.get("max_retry_per_item", DEFAULT_SETTINGS["max_retry_per_item"])))
        item.status = "processing"
        self.emit("item", self.report_row(item, "Share invite processing started"))
        attempt = 1
        while attempt <= max_retry + 1:
            if self.stop_event.is_set() or self.close_event.is_set():
                item.status = "unprocessed"
                return
            self.wait_if_paused()
            if self.stop_event.is_set() or self.close_event.is_set():
                item.status = "unprocessed"
                return

            item.attempts = attempt
            send_count_before = self.run_send_count
            try:
                result = self.execute_flow(item)
                item.status = "success"
                item.result = result
                item.message = "Share invite confirmed"
                self.state.success_count += 1
                self.log(f"Invite success: {item.email} -> {result}")
                self.emit("item", self.report_row(item, item.message))
                return
            except TestSendLimitReached as exc:
                item.status = "limit_reached"
                item.message = str(exc)
                self.log(str(exc), "WARNING")
                self.emit("item", self.report_row(item, item.message))
                return
            except (TestModeRequired, SessionVerificationError) as exc:
                item.status = "blocked"
                item.message = str(exc)
                self.login_verified_event.clear()
                self.log(str(exc), "ERROR")
                self.emit("login", {"verified": False, "message": str(exc)})
                self.emit("item", self.report_row(item, item.message))
                return
            except SecurityChallenge as exc:
                item.status = "interrupted"
                if self.run_send_count > send_count_before:
                    item.message = (
                        "A security challenge appeared after a Send click attempt. "
                        "Automatic retry was blocked to prevent a duplicate invite. "
                        f"Complete the challenge and review the target manually. Detail: {exc}"
                    )
                    self.save_checkpoint()
                    self.log(item.message, "ERROR")
                    self.emit("security", {"message": item.message})
                    self.emit("item", self.report_row(item, item.message))
                    return

                item.message = str(exc)
                self.pause_event.set()
                self.save_checkpoint()
                self.log(f"Security challenge detected; task paused: {exc}", "WARNING")
                self.emit("security", {"message": str(exc)})
                self.wait_if_paused()
                if self.stop_event.is_set() or self.close_event.is_set():
                    item.status = "unprocessed"
                    return
                item.status = "processing"
                self.log(
                    "Security challenge pause cleared; retrying the current record."
                )
                continue
            except InviteRejected as exc:
                item.message = str(exc)
                self.log(
                    f"Confirmed invite rejection on attempt {attempt} for {item.email}: {exc}",
                    "WARNING",
                )
            except Exception as exc:
                item.message = str(exc)
                if self.run_send_count > send_count_before:
                    item.status = "interrupted"
                    item.message = (
                        "Send was clicked, but a definitive success or rejection was not "
                        "confirmed. Automatic retry was blocked to prevent a duplicate invite. "
                        f"Detail: {exc}"
                    )
                    self.save_checkpoint()
                    self.log(item.message, "ERROR")
                    self.emit("item", self.report_row(item, item.message))
                    return
                self.log(
                    f"Invite attempt {attempt} failed before Send for {item.email}: {exc}",
                    "WARNING",
                )

            if attempt <= max_retry:
                self.prepare_invite_retry()
                retry_min = max(0.0, float(self.settings.get("retry_delay_min", DEFAULT_SETTINGS["retry_delay_min"])))
                retry_max = max(
                    retry_min, float(self.settings.get("retry_delay_max", DEFAULT_SETTINGS["retry_delay_max"]))
                )
                delay = min(
                    retry_max,
                    retry_min
                    * (
                        max(1.0, float(self.settings.get("backoff_multiplier", DEFAULT_SETTINGS["backoff_multiplier"])))
                        ** (attempt - 1)
                    ),
                )
                self.interruptible_sleep(delay)
                attempt += 1
                continue

            item.status = "failed"
            self.state.failed_count += 1
            self.emit("item", self.report_row(item, item.message))
            return

    def execute_flow(self, item: TaskItem) -> str:
        email = item.email.strip()
        if not email or not EMAIL_RE.fullmatch(email):
            raise ValueError(
                "Invite email is blank or invalid; submission was blocked."
            )
        if self.stop_event.is_set() or self.close_event.is_set():
            raise RuntimeError("Processing was stopped.")

        page = self.active_page
        self.wait_if_paused()
        self.assert_test_mode(page)
        self.ensure_share_entry(page)
        self.open_share_modal(page)
        self.fill_invite_email(page, email)
        notification_state = self.arm_invite_notification_monitor(page)
        self.submit_share_invite(page, email, notification_state)
        return f"{page.url} | invite=sent"

    def ensure_share_entry(self, page) -> None:
        """Use the pre-opened authenticated Test Mode page first; fail closed otherwise."""
        if self.authenticated_test_session_ready(page):
            self.login_verified_event.set()
            return
        self.log(
            "Authenticated Share page was not found on the current tab; opening the configured Target URL.",
            "WARNING",
        )
        self.safe_goto(page, self.state.target_url)
        if not self.wait_for_authenticated_test_session():
            if not self.test_mode_banner_ready(page):
                raise TestModeRequired(
                    "Automation blocked: Test Mode banner was not detected after opening the Target URL."
                )
            raise SessionVerificationError(
                "Automation blocked: authenticated Share page was not detected after login verification retries."
            )

    def share_button_ready(self, page) -> bool:
        return self.any_visible(
            page,
            SELECTORS["share_button"],
            timeout=max(0, int(self.settings.get("standard_dom_probe_timeout", DEFAULT_SETTINGS["standard_dom_probe_timeout"]))),
        )

    def wait_for_share_button(self, page) -> bool:
        max_retry = max(0, int(self.settings.get("max_selector_retry", DEFAULT_SETTINGS["max_selector_retry"])))
        for attempt in range(max_retry + 1):
            self.detect_security(page)
            if self.share_button_ready(page):
                return True
            if attempt < max_retry:
                self.log(
                    f"Share button lookup retry {attempt + 1}/{max_retry}.", "WARNING"
                )
                try:
                    self.safe_goto(page, self.state.target_url)
                except Exception as exc:
                    self.log(f"Target URL retry failed: {exc}", "WARNING")
                self.interruptible_sleep(
                    max(0.0, float(self.settings.get("network_error_retry_delay", DEFAULT_SETTINGS["network_error_retry_delay"])))
                )
        return False

    def share_modal_ready(self, page) -> bool:
        required_groups = (
            SELECTORS["share_modal_title"],
            SELECTORS["share_email"],
            SELECTORS["share_send"],
        )
        return all(
            self.any_visible(
                page, selectors,
                timeout=max(0, int(self.settings.get("standard_dom_probe_timeout", DEFAULT_SETTINGS["standard_dom_probe_timeout"]))),
            )
            for selectors in required_groups
        )

    def close_existing_share_modal(self, page) -> None:
        if not self.any_visible(
            page,
            SELECTORS["share_modal_title"],
            timeout=max(0, int(self.settings.get("modal_state_probe_timeout", DEFAULT_SETTINGS["modal_state_probe_timeout"]))),
        ):
            return
        try:
            self.click_first(page, SELECTORS["share_modal_close"], "Share modal close")
            for _ in range(
                max(0, int(self.settings.get("modal_close_poll_count", DEFAULT_SETTINGS["modal_close_poll_count"])))
            ):
                if not self.any_visible(
                    page,
                    SELECTORS["share_modal_title"],
                    timeout=max(0, int(self.settings.get("modal_close_probe_timeout", DEFAULT_SETTINGS["modal_close_probe_timeout"]))),
                ):
                    return
                self.interruptible_sleep(
                    max(0.0, float(self.settings.get("modal_close_poll_interval", DEFAULT_SETTINGS["modal_close_poll_interval"])))
                )
        except Exception as exc:
            self.log(
                f"Existing Share modal could not be closed cleanly: {exc}", "WARNING"
            )

    def open_share_modal(self, page) -> None:
        self.close_existing_share_modal(page)
        self.ensure_share_entry(page)
        self.click_first(page, SELECTORS["share_button"], "Share")

        max_retry = max(0, int(self.settings.get("max_selector_retry", DEFAULT_SETTINGS["max_selector_retry"])))
        for attempt in range(max_retry + 1):
            self.detect_security(page)
            if self.share_modal_ready(page):
                self.log(
                    "Share Link modal opened and all required controls were detected."
                )
                return
            if attempt < max_retry:
                self.log(
                    f"Share modal validation retry {attempt + 1}/{max_retry}.",
                    "WARNING",
                )
                self.interruptible_sleep(
                    max(0.1, float(self.settings.get("retry_delay_min", DEFAULT_SETTINGS["retry_delay_min"])))
                )
        raise RuntimeError(
            "Share Link modal did not expose its title, email input, and Send button."
        )

    def prepare_invite_retry(self) -> None:
        """Return the page to a deterministic state without reloading after a confirmed success."""
        if (
            self.stop_event.is_set()
            or self.close_event.is_set()
            or not self.active_page
        ):
            return
        try:
            self.close_existing_share_modal(self.active_page)
        except Exception:
            pass
        if not self.share_button_ready(self.active_page):
            try:
                self.safe_goto(self.active_page, self.state.target_url)
            except Exception as exc:
                self.log(f"Invite retry recovery navigation failed: {exc}", "WARNING")

    def fill_invite_email(self, page, email: str) -> None:
        """Fill and verify the exact email value so blank or stale submissions cannot proceed."""
        if not email or not EMAIL_RE.fullmatch(email):
            raise ValueError(
                "Invite email is blank or invalid; submission was blocked."
            )
        self.fill_first(page, SELECTORS["share_email"], "", "Clear invite email")
        self.fill_first(page, SELECTORS["share_email"], email, "Invite email")
        actual = self.input_value_first(
            page, SELECTORS["share_email"], "Invite email"
        ).strip()
        if not actual or actual.casefold() != email.casefold():
            raise RuntimeError(
                f"Invite email verification failed before Send. Expected '{email}', found '{actual or '<blank>'}'."
            )

    def input_value_first(self, page, selectors: list[str], label: str) -> str:
        last_error = None
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(
                    state="visible",
                    timeout=max(
                        1000, int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"]))
                    ),
                )
                return str(
                    locator.input_value(
                        timeout=max(
                            1000, int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"]))
                        )
                    )
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Could not read {label}: {last_error}")

    def arm_invite_notification_monitor(self, page) -> dict[str, Any]:
        """Track a new success transition so a stale success node cannot confirm the next email."""
        try:
            state = page.evaluate(
                """
                () => {
                    const selector = '[data-testid="Notification--success"]';
                    const isShown = (el) => !!el && (
                        el.classList.contains('Notification__show') ||
                        (getComputedStyle(el).display !== 'none' &&
                         getComputedStyle(el).visibility !== 'hidden' &&
                         Number(getComputedStyle(el).opacity || '1') > 0)
                    );
                    if (!window.__testerInviteNotificationState) {
                        window.__testerInviteNotificationState = {seq: 0, shown: false, text: ''};
                    }
                    const current = document.querySelector(selector);
                    const shared = window.__testerInviteNotificationState;
                    shared.shown = isShown(current);
                    shared.text = current ? (current.textContent || '').trim() : '';
                    if (window.__testerInviteNotificationObserver) {
                        window.__testerInviteNotificationObserver.disconnect();
                    }
                    window.__testerInviteNotificationObserver = new MutationObserver(() => {
                        const el = document.querySelector(selector);
                        const shown = isShown(el);
                        const text = el ? (el.textContent || '').trim() : '';
                        if (shown && (!shared.shown || text !== shared.text)) {
                            shared.seq += 1;
                        }
                        shared.shown = shown;
                        shared.text = text;
                    });
                    window.__testerInviteNotificationObserver.observe(document.documentElement, {
                        subtree: true,
                        childList: true,
                        characterData: true,
                        attributes: true,
                        attributeFilter: ['class', 'style']
                    });
                    return {seq: shared.seq, shown: shared.shown, text: shared.text};
                }
                """
            )
            if isinstance(state, dict):
                return state
        except Exception as exc:
            self.log(f"Success notification monitor fallback enabled: {exc}", "WARNING")
        return {"seq": 0, "shown": False, "text": ""}

    def _register_send_click_attempt(self) -> None:
        """Reserve a Send attempt immediately before Playwright invokes click()."""
        if self.run_send_count >= self.run_send_limit:
            raise TestSendLimitReached(
                f"Maximum Test Mode send limit reached ({self.run_send_limit} Send clicks for this run)."
            )
        self.run_send_count += 1
        self.emit(
            "send_limit", {"used": self.run_send_count, "limit": self.run_send_limit}
        )

    def submit_share_invite(
        self, page, email: str, notification_state: dict[str, Any]
    ) -> None:
        self.detect_security(page)
        self.assert_test_mode(page)
        actual = self.input_value_first(
            page, SELECTORS["share_email"], "Invite email"
        ).strip()
        if not actual or actual.casefold() != email.casefold():
            raise RuntimeError(
                "Blank or mismatched invite submission was blocked immediately before Send."
            )
        if self.run_send_count >= self.run_send_limit:
            raise TestSendLimitReached(
                f"Maximum Test Mode send limit reached ({self.run_send_limit} Send clicks for this run)."
            )
        self.click_first(
            page,
            SELECTORS["share_send"],
            "Send invite",
            before_click=self._register_send_click_attempt,
        )
        self.wait_invite_result(page, notification_state)
        self.log(
            "Invite was confirmed by a new success notification; continuing without page reload."
        )

    def wait_invite_result(self, page, notification_state: dict[str, Any]) -> None:
        timeout_ms = max(1000, int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"])))
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        start_seq = int(notification_state.get("seq", 0))
        was_shown = bool(notification_state.get("shown", False))
        last_error_text = ""

        while time.monotonic() < deadline:
            if self.stop_event.is_set() or self.close_event.is_set():
                raise RuntimeError(
                    "Invite confirmation wait was cancelled because processing stopped."
                )
            self.wait_if_paused()
            self.detect_security(page)

            try:
                current = page.evaluate(
                    """
                    () => {
                        const state = window.__testerInviteNotificationState || {seq: 0, shown: false, text: ''};
                        return {seq: state.seq || 0, shown: !!state.shown, text: state.text || ''};
                    }
                    """
                )
                if isinstance(current, dict):
                    current_seq = int(current.get("seq", 0))
                    current_shown = bool(current.get("shown", False))
                    if current_seq > start_seq or (not was_shown and current_shown):
                        return
            except Exception:
                if not was_shown and self.any_visible(
                    page,
                    SELECTORS["invite_success"],
                    timeout=max(0, int(self.settings.get("notification_visibility_timeout", DEFAULT_SETTINGS["notification_visibility_timeout"]))),
                ):
                    return

            last_error_text = self.first_visible_text(page, SELECTORS["invite_error"])
            if last_error_text:
                raise InviteRejected(f"Invite send failed: {last_error_text}")
            self.interruptible_sleep(
                max(0.0, float(self.settings.get("notification_poll_interval", DEFAULT_SETTINGS["notification_poll_interval"])))
            )

        if last_error_text:
            raise RuntimeError(f"Invite send failed: {last_error_text}")
        raise RuntimeError("A new success notification was not detected after Send.")

    def safe_goto(self, page, url: str) -> None:
        if not url.startswith(("http://", "https://")):
            raise ValueError("Target URL must begin with http:// or https://")
        nav_retry = max(
            0,
            int(self.settings.get("max_navigation_retry", DEFAULT_SETTINGS["max_navigation_retry"])),
            int(self.settings.get("connection_retry_count", DEFAULT_SETTINGS["connection_retry_count"])),
        )
        last_error = None
        for attempt in range(nav_retry + 1):
            if self.stop_event.is_set() or self.close_event.is_set():
                raise RuntimeError(
                    "Navigation cancelled because processing was stopped."
                )
            try:
                wait_until = str(
                    self.settings.get(
                        "navigation_wait_until",
                        DEFAULT_SETTINGS["navigation_wait_until"],
                    )
                ).strip().lower()
                page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=max(
                        1000, int(self.settings.get("page_navigation_timeout", DEFAULT_SETTINGS["page_navigation_timeout"]))
                    ),
                )
                if bool(
                    self.settings.get(
                        "wait_for_network_idle",
                        DEFAULT_SETTINGS["wait_for_network_idle"],
                    )
                ) and wait_until != "networkidle":
                    try:
                        page.wait_for_load_state(
                            "networkidle",
                            timeout=max(0, int(self.settings.get("network_idle_timeout", DEFAULT_SETTINGS["network_idle_timeout"]))),
                        )
                    except Exception:
                        pass
                return
            except Exception as exc:
                last_error = exc
                self.log(
                    f"Navigation retry {attempt + 1}/{nav_retry + 1} failed: {exc}",
                    "WARNING",
                )
                if attempt < nav_retry:
                    self.interruptible_sleep(
                        max(
                            0.0,
                            float(self.settings.get("network_error_retry_delay", DEFAULT_SETTINGS["network_error_retry_delay"])),
                        )
                    )
        raise RuntimeError(f"Navigation failed: {last_error}")

    def click_first(
        self,
        page,
        selectors: list[str],
        label: str,
        before_click: Callable[[], None] | None = None,
    ) -> None:
        max_retry = max(0, int(self.settings.get("max_selector_retry", DEFAULT_SETTINGS["max_selector_retry"])))
        last_error = None
        for attempt in range(max_retry + 1):
            self.detect_security(page)
            for selector in selectors:
                try:
                    locator = page.locator(selector).first
                    locator.wait_for(
                        state="visible",
                        timeout=max(
                            1000, int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"]))
                        ),
                    )
                    if bool(
                        self.settings.get(
                            "scroll_before_interaction",
                            DEFAULT_SETTINGS["scroll_before_interaction"],
                        )
                    ):
                        locator.scroll_into_view_if_needed()
                    if before_click is not None:
                        before_click()
                        try:
                            locator.click(
                                timeout=max(
                                    1000,
                                    int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"])),
                                )
                            )
                        except Exception as exc:
                            raise SendClickOutcomeUncertain(
                                f"{label} click may have been dispatched, but Playwright "
                                "did not confirm the click outcome."
                            ) from exc
                    else:
                        locator.click(
                            timeout=max(
                                1000,
                                int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"])),
                            )
                        )
                    self.log(f"Clicked {label} using selector: {selector}")
                    return
                except (TestSendLimitReached, SendClickOutcomeUncertain):
                    raise
                except Exception as exc:
                    last_error = exc
            if attempt < max_retry:
                retry_min = max(0.0, float(self.settings.get("retry_delay_min", DEFAULT_SETTINGS["retry_delay_min"])))
                retry_max = max(
                    retry_min, float(self.settings.get("retry_delay_max", DEFAULT_SETTINGS["retry_delay_max"]))
                )
                self.interruptible_sleep(random.uniform(retry_min, retry_max))
        raise RuntimeError(f"Could not click {label}: {last_error}")

    def fill_first(self, page, selectors: list[str], value: str, label: str) -> None:
        last_error = None
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(
                    state="visible",
                    timeout=max(
                        1000, int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"]))
                    ),
                )
                locator.fill(
                    value,
                    timeout=max(
                        1000, int(self.settings.get("selector_timeout", DEFAULT_SETTINGS["selector_timeout"]))
                    ),
                )
                self.log(f"Filled {label} using selector: {selector}")
                return
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Could not fill {label}: {last_error}")

    def any_visible(self, page, selectors: list[str], timeout: int = 1000) -> bool:
        for selector in selectors:
            try:
                if page.locator(selector).first.is_visible(timeout=timeout):
                    return True
            except Exception:
                pass
        return False

    def first_visible_text(self, page, selectors: list[str]) -> str:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(
                    timeout=max(0, int(self.settings.get("visible_text_timeout", DEFAULT_SETTINGS["visible_text_timeout"])))
                ):
                    return (
                        locator.text_content(
                            timeout=max(0, int(self.settings.get("text_content_timeout", DEFAULT_SETTINGS["text_content_timeout"])))
                        )
                        or ""
                    ).strip()
            except Exception:
                pass
        return ""

    def detect_security(self, page) -> None:
        # Kept conservative to avoid bypass attempts or false positives.
        try:
            title = (page.title() or "").lower()
            body_text = (
                page.locator("body").inner_text(
                    timeout=max(0, int(self.settings.get("security_body_read_timeout", DEFAULT_SETTINGS["security_body_read_timeout"])))
                )
                or ""
            ).lower()
            body_limit = max(0, int(self.settings.get("security_body_text_limit", DEFAULT_SETTINGS["security_body_text_limit"])))
            challenge_text = f"{title}\n{body_text[:body_limit]}"
            if any(pattern in challenge_text for pattern in SECURITY_PATTERNS):
                raise SecurityChallenge(
                    "A browser security challenge was detected. Complete it manually, then press Resume."
                )
        except SecurityChallenge:
            raise
        except Exception:
            pass

    def build_name(self, item: TaskItem) -> str:
        if item.name and len(item.name.split()) >= 2:
            return item.name.strip()
        default_name = str(self.settings.get("default_full_name", DEFAULT_SETTINGS["default_full_name"])).strip()
        if default_name:
            return default_name
        return self.name_from_email(item.email, force_two_parts=True)

    def name_from_email(self, email: str, force_two_parts: bool = True) -> str:
        username = email.split("@", 1)[0]
        parts = [p for p in re.split(r"[._\-+0-9]+", username) if p]
        if len(parts) >= 2:
            return f"{parts[0].capitalize()} {parts[1].capitalize()}"
        first = (parts[0] if parts else "Test").capitalize()
        domain = (
            email.split("@", 1)[1].split(".", 1)[0].capitalize()
            if "@" in email
            else "User"
        )
        return f"{first} {domain}" if force_two_parts else first

    def report_row(self, item: TaskItem, message: str) -> dict[str, Any]:
        return {
            "timestamp": now_str(),
            "slot_id": self.state.slot_id,
            "email": item.email,
            "status": item.status,
            "message": message,
            "attempts": item.attempts,
            "target_url": self.state.target_url,
            "result": item.result,
        }

    def emit_progress(self, item: TaskItem | None = None) -> None:
        self.emit(
            "progress",
            {
                "current": self.state.current_index,
                "total": self.state.total,
                "success": self.state.success_count,
                "failed": self.state.failed_count,
                "remaining": self.state.remaining,
                "progress": self.state.progress,
            },
        )

    def save_checkpoint(self) -> None:
        data = {
            "slot_id": self.state.slot_id,
            "target_url": self.state.target_url,
            "current_index": self.state.current_index,
            "items": [item.__dict__ for item in self.state.items],
            "saved_at": now_str(),
        }
        (APP_DATA_DIR / f"slot_{self.state.slot_id}_checkpoint.json").write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )

    def save_failed(self, items: list[TaskItem] | None = None) -> None:
        if not bool(self.settings.get("save_failed_data", DEFAULT_SETTINGS["save_failed_data"])):
            return
        items = items or [i for i in self.state.items if i.status == "failed"]
        if not items:
            return
        path = (
            FAILED_DATA_DIR
            / f"slot_{self.state.slot_id}_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["email", "name", "status", "attempts", "message", "result"],
            )
            writer.writeheader()
            for item in items:
                writer.writerow(
                    {
                        key: safe_spreadsheet_cell(value)
                        for key, value in item.__dict__.items()
                    }
                )
        self.log(f"Failed data saved: {path.name}")

    def save_unprocessed(self) -> None:
        items = [
            i
            for i in self.state.items[self.state.current_index :]
            if i.status
            in {
                "pending",
                "processing",
                "unprocessed",
                "interrupted",
                "blocked",
                "limit_reached",
            }
        ]
        if not items:
            return
        path = (
            APP_DATA_DIR
            / f"slot_{self.state.slot_id}_unprocessed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        path.write_text("\n".join(i.email for i in items), encoding="utf-8")
        self.log(f"Unprocessed data saved: {path.name}")

    def cleanup(self) -> None:
        self.log("Closing browser resources.")
        closed_ids: set[int] = set()
        for obj in (self.context, self.browser):
            try:
                if obj and id(obj) not in closed_ids:
                    closed_ids.add(id(obj))
                    obj.close()
            except Exception:
                pass
        self.context = None
        self.browser = None
        self.active_page = None
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        self.playwright = None

        if (
            self.active_profile_dir is not None
            and not bool(
                self.settings.get(
                    "persist_profile_cache",
                    DEFAULT_SETTINGS["persist_profile_cache"],
                )
            )
        ):
            profile_directory = str(
                self.settings.get(
                    "persistent_profile_directory",
                    DEFAULT_SETTINGS["persistent_profile_directory"],
                )
            ).strip()
            profile_dir = self.active_profile_dir / (profile_directory or "Default")
            cache_candidates = [
                profile_dir / "Cache",
                profile_dir / "Code Cache",
                profile_dir / "GPUCache",
                profile_dir / "DawnCache",
                self.active_profile_dir / "ShaderCache",
                self.active_profile_dir / "GrShaderCache",
            ]
            for cache_path in cache_candidates:
                try:
                    if cache_path.exists():
                        shutil.rmtree(cache_path, ignore_errors=True)
                except Exception:
                    pass

        if self.temporary_profile_dir is not None:
            try:
                shutil.rmtree(self.temporary_profile_dir, ignore_errors=True)
            except Exception:
                pass
            self.temporary_profile_dir = None
        self.active_profile_dir = None


class SecurityChallenge(Exception):
    pass


class SessionVerificationError(Exception):
    pass


class TestModeRequired(SessionVerificationError):
    pass


class TestSendLimitReached(Exception):
    pass


class SendClickOutcomeUncertain(RuntimeError):
    """A Send click may have reached the page, so retrying could duplicate it."""


class InviteRejected(Exception):
    """The target explicitly rejected an invite, so a controlled retry is safe."""
