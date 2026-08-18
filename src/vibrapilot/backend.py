#!/usr/bin/env python3
"""
VibraPilot - Authorized Browser Automation
Version: 1.0.6.10
Author: Vib.tools

Feature-preserving backend carried forward from the validated v1.0.6 baseline.

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
import secrets
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
from types import MappingProxyType, SimpleNamespace
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from .app_config import APP
from .licensing_v2 import (
    LicoraV2Client,
    LicoraV2Error,
    generate_device_key_material,
    load_device_key_material,
)
from .task_runtime_store import TaskRuntimeStore
from .browser_capabilities import (
    collision_safe_download_path,
    ensure_task_download_directory,
)
from .chrome_runtime import require_google_chrome
from .browser_diagnostics import (
    browser_diagnostics_summary,
    browser_diagnostics_warnings,
    build_browser_diagnostics,
    persist_browser_diagnostics,
    sanitize_diagnostic_text,
)
from .workflow import WorkflowManager, WorkflowRuntime, WorkflowRuntimeResolutionError
from .runtime_environment import application_root, is_packaged_runtime
from .power_management import SYSTEM_SLEEP_GUARD

DISPLAY_APP_NAME = APP.display_name
APP_NAME = APP.app_name
APP_VERSION = APP.version
APP_AUTHOR = APP.author_name
RELEASE_DATE = APP.release_date
# Secure licensing transport is owned by config/AppConfig/licensing_public.py.
# No API v1 shared/master key is embedded in VibraPilot Phase-02.

ROOT_DIR = application_root()
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
LEGACY_LICENSE_FILE = APP_DATA_DIR / "license.json"


def _default_license_state_dir() -> Path:
    """Return the durable per-user license-state directory.

    Source checkouts and clean application upgrades may move between folders, but
    a Licora device key must outlive that installation path.  An explicit
    ``VIB_TOOLS_DATA_DIR`` deployment remains authoritative; otherwise Windows
    stores licensing state below LOCALAPPDATA.
    """
    if os.environ.get("VIB_TOOLS_DATA_DIR"):
        return APP_DATA_DIR
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base).expanduser().resolve() / "Vib Tools" / "VibraPilot"
    return APP_DATA_DIR


LICENSE_STATE_DIR = _default_license_state_dir()
LICENSE_FILE = LICENSE_STATE_DIR / "license.json"
DEVICE_IDENTITY_FILE = LICENSE_STATE_DIR / "device_identity.json"
APP_STATE_FILE = APP_DATA_DIR / "state.json"
TASK_RUNTIME_DB = APP_DATA_DIR / "task_runtime.sqlite3"
LOG_FILE = LOGS_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# Legacy packaged builds may place a Playwright browser under ``ms-playwright``.
# Preserve that historical compatibility if the directory exists. The v1.0.6.37
# Nuitka portable release intentionally does not bundle a browser.
if is_packaged_runtime():
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

# Serializes final-name selection + save_as across Task workers that may share an
# explicitly configured download directory. No download history/state is stored.
_DOWNLOAD_SAVE_LOCK = threading.Lock()


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



def _legacy_device_id() -> str:
    """Return the pre-v1.0.6.10 deterministic device identifier."""
    raw = f"{uuid.getnode()}-{os.getenv('COMPUTERNAME', '')}-{os.getenv('USERNAME', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _current_machine_anchor() -> str:
    """Return a non-secret machine anchor used to reject copied device state.

    Windows MachineGuid is substantially more stable across network-adapter or
    username changes than the historical device-ID input.  Only its application-
    scoped SHA-256 digest is persisted.  On non-Windows verification hosts we use
    the historical local identifier as a deterministic fallback.
    """
    material = ""
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                material = str(winreg.QueryValueEx(key, "MachineGuid")[0]).strip()
        except Exception:
            material = ""
    if not material:
        material = _legacy_device_id()
    return hashlib.sha256(f"{APP.app_id}:{material}".encode("utf-8")).hexdigest()


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        path.name + f".tmp.{os.getpid()}.{threading.get_ident()}"
    )
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            temporary.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def _migrate_legacy_license_file() -> None:
    """Copy the install-relative v1.0.6.9 cache to durable license storage once."""
    try:
        if LICENSE_FILE == LEGACY_LICENSE_FILE or LICENSE_FILE.exists() or not LEGACY_LICENSE_FILE.is_file():
            return
        raw = LEGACY_LICENSE_FILE.read_bytes()
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = LICENSE_FILE.with_name(
            LICENSE_FILE.name + f".migrate.{os.getpid()}.{threading.get_ident()}"
        )
        try:
            with temporary.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, LICENSE_FILE)
        finally:
            temporary.unlink(missing_ok=True)
        logging.info("Migrated protected Licora state to durable per-user storage.")
    except Exception:
        # Migration failure must not delete or corrupt the legacy cache.  Activation
        # can still continue with explicit user input and report persistence errors.
        logging.exception("Unable to migrate legacy Licora license state")


def _read_device_identity() -> dict[str, Any] | None:
    if not DEVICE_IDENTITY_FILE.is_file():
        return None
    raw = json.loads(DEVICE_IDENTITY_FILE.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("device identity cache must be a JSON object")
    if int(raw.get("schema_version", 0) or 0) != 1 or raw.get("app_id") != APP.app_id:
        raise ValueError("device identity cache schema/application mismatch")
    machine_anchor = str(raw.get("machine_anchor", "")).strip()
    if machine_anchor and machine_anchor != _current_machine_anchor():
        raise ValueError("device identity cache belongs to a different Windows machine")
    device_id = str(raw.get("device_id", "")).strip().lower()
    if not re.fullmatch(r"[0-9a-f]{24}", device_id):
        raise ValueError("device identity cache contains an invalid device ID")
    protected_key = str(raw.get("device_private_key_protected", "")).strip()
    if not protected_key:
        raise ValueError("device identity cache is missing the protected private key")
    private_key = _unprotect_local_secret(protected_key)
    material = load_device_key_material(private_key)
    fingerprint = str(raw.get("device_public_key_fingerprint", "")).strip()
    if fingerprint and fingerprint != material.public_key_fingerprint:
        raise ValueError("device identity cache fingerprint mismatch")
    return {
        "device_id": device_id,
        "private_key_pem": material.private_key_pem,
        "fingerprint": material.public_key_fingerprint,
        "recovery_rotations": max(0, int(raw.get("recovery_rotations", 0) or 0)),
    }


def _write_device_identity(
    *,
    device_id: str,
    private_key_pem: str,
    fingerprint: str,
    recovery_rotations: int,
) -> None:
    protected = _protect_local_secret(private_key_pem) if private_key_pem else ""
    if os.name == "nt" and private_key_pem and not protected:
        raise RuntimeError("Windows DPAPI failed to protect device private key.")
    _atomic_json_write(
        DEVICE_IDENTITY_FILE,
        {
            "schema_version": 1,
            "app_id": APP.app_id,
            "device_id": device_id,
            "device_private_key_protected": protected,
            "device_public_key_fingerprint": fingerprint,
            "machine_anchor": _current_machine_anchor(),
            "recovery_rotations": max(0, int(recovery_rotations)),
            "saved_at": now_str(),
        },
    )


def license_validation_failure_is_transient(code: str) -> bool:
    """Return whether a failed remote check is non-authoritative/transient."""
    return str(code or "").upper() in {
        "NETWORK_ERROR",
        "INVALID_SERVER_RESPONSE",
        "RATE_LIMITED",
        "API_V2_NOT_READY",
        "INTERNAL_ERROR",
    }


def _license_error_message(exc: LicoraV2Error) -> str:
    """Return concise activation-shell text while retaining the stable error code."""
    code = str(exc.code or "LICORA_V2_ERROR")
    messages = {
        "NETWORK_ERROR": "Licora server is unreachable. Check your connection and retry.",
        "INVALID_SERVER_RESPONSE": "Licora returned an invalid response. Please retry shortly.",
        "RATE_LIMITED": "Too many license requests. Please wait and retry.",
        "DEVICE_LIMIT_REACHED": "Device limit reached. Remove a stale device in Licora and retry.",
        "DEVICE_REVOKED": "This device registration is revoked and requires recovery.",
        "DEVICE_KEY_MISMATCH": "This device registration uses a different key and requires recovery.",
        "APP_VERSION_UNSUPPORTED": "This VibraPilot version is not accepted by Licora.",
        "INVALID_LICENSE": "The license key is not valid.",
    }
    return f"{messages.get(code, exc.message)} ({code})"


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
    if not is_packaged_runtime():
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

    # Keep Chrome's extension subsystem enabled for normal browser use,
    # including Chrome Web Store installs. ``extensions_enabled`` controls
    # VibraPilot's explicit unpacked side-loading mode; it must not leave
    # Playwright's global --disable-extensions default active when that mode
    # is off.
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


def _enforce_browser_runtime_policy(data: dict[str, Any]) -> None:
    """Apply the non-bypassable browser identity/security policy version."""
    # v1.0.6.39 promotes policy v2. Identity/security values remain mandatory;
    # the v2 migration separately moves background throttling to a production-safe
    # default while leaving the operator free to change it after migration.
    data["browser_runtime_policy_version"] = 2
    data["use_chrome_channel"] = True
    data["allow_chromium_fallback"] = False
    data["browser_executable_path"] = ""
    data["sandbox_enabled"] = True
    data["extensions_enabled"] = False


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
        for key, minimum in (("batch_size", 1), ("auto_save_interval", 0), ("max_concurrent_tasks", 1)):
            try:
                self.data[key] = max(minimum, int(self.data.get(key, DEFAULT_SETTINGS[key])))
            except (TypeError, ValueError):
                self.data[key] = int(DEFAULT_SETTINGS[key])
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

        # v1.0.6.14 managed-browser migration: an exact untouched v1.0.6.13
        # persistent-profile bundle is promoted to the new managed persistent
        # default. Any customized persistent-profile value keeps user intent.
        legacy_persistent_defaults = {
            "use_persistent_context": False,
            "persistent_user_data_dir": "",
            "dedicated_profile_per_task": True,
            "persistent_profile_directory": "",
            "profile_lock_policy": "fail",
            "persist_profile_between_runs": True,
            "persist_profile_cache": True,
            "restore_previous_session": False,
        }
        if raw and all(raw.get(key) == value for key, value in legacy_persistent_defaults.items()):
            self.data["use_persistent_context"] = True

        # v1.0.6.31 Chrome-only runtime policy. The first migration promotes
        # ordinary HTTP caching; mandatory browser identity/security values are
        # enforced on every load so stale/manual settings cannot re-enable a
        # Chromium/custom-binary or sandbox-disabled launch path.
        try:
            browser_policy_version = int(raw.get("browser_runtime_policy_version", 0) or 0)
        except (TypeError, ValueError):
            browser_policy_version = 0
        if browser_policy_version < 1:
            self.data["http_cache_enabled"] = True
        # v1.0.6.39 policy v2: migrate any pre-v2 persisted setting to the
        # production-safe background automation default exactly once. After this
        # save, users may explicitly re-enable Chrome background throttling.
        if browser_policy_version < 2:
            self.data["background_throttling_enabled"] = False

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

        _enforce_browser_runtime_policy(self.data)

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
        _enforce_browser_runtime_policy(self.data)
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
    """Licora Secure API v2 activation/session manager.

    The public method surface is preserved from the v1 baseline while the
    implementation migrates to device-bound P-256 proofs, RS256-verified access
    tokens and rotating refresh credentials. Windows DPAPI protects all locally
    persisted secrets; no Licora API v1 shared/master key is used.
    """

    def __init__(self, settings: SettingsManager):
        self.settings = settings
        self.license_key = ""
        self.license_hash = ""
        self.user_email = ""
        self.activated_until: str | None = None
        self.schema_version = 2
        self.protocol = "licora-api-v2"
        self.app_id = APP.app_id
        self.device_private_key_pem = ""
        self.device_public_key_fingerprint = ""
        self.access_token = ""
        self.refresh_token = ""
        self.access_expires_at = 0
        self.refresh_expires_at: str | None = None
        self._lock = threading.RLock()
        # Network validation is serialized separately from the short-lived state
        # lock so the Qt/UI thread never waits on a remote Licora request simply
        # because it needs to read the current activation state.
        self._validation_lock = threading.Lock()
        self._state_generation = 0
        self._verified_access_token = ""
        self._verified_access_expires_at = 0
        self._token_verifier = None
        self._device_id = ""
        self._device_recovery_rotations = 0
        self._last_validation_code = "NOT_VALIDATED"
        self._remote_logout_done = threading.Event()
        self._remote_logout_done.set()
        _migrate_legacy_license_file()
        self.load()

    def load(self) -> None:
        identity_loaded = False
        with self._lock:
            try:
                identity = _read_device_identity()
                if identity:
                    self._device_id = str(identity["device_id"])
                    self.device_private_key_pem = str(identity["private_key_pem"])
                    self.device_public_key_fingerprint = str(identity["fingerprint"])
                    self._device_recovery_rotations = int(identity["recovery_rotations"])
                    identity_loaded = True
            except Exception:
                logging.exception("Failed to load durable Licora device identity")

            if not LICENSE_FILE.exists():
                return
            try:
                data = json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("license cache must be a JSON object")

                protected_key = str(data.get("license_key_protected", "")).strip()
                legacy_plaintext_key = str(data.get("license_key", "")).strip()
                self.license_key = ""
                if protected_key:
                    self.license_key = _unprotect_local_secret(protected_key)
                elif legacy_plaintext_key:
                    # One-way migration input from pre-Phase-02 caches. It is never
                    # written back as plaintext by save().
                    self.license_key = legacy_plaintext_key

                self.license_hash = str(data.get("license_hash", "")).strip()
                self.user_email = str(data.get("user_email", "")).strip()
                self.activated_until = data.get("activated_until")
                self.schema_version = int(data.get("schema_version", 1) or 1)
                self.protocol = str(data.get("protocol", "")).strip() or (
                    "licora-api-v2" if self.schema_version >= 2 else "legacy-v1-cache"
                )
                self.app_id = str(data.get("app_id", APP.app_id)).strip() or APP.app_id
                self.access_expires_at = int(data.get("access_expires_at", 0) or 0)
                self.refresh_expires_at = data.get("refresh_expires_at")

                protected_device_key = str(
                    data.get("device_private_key_protected", "")
                ).strip()
                protected_access = str(data.get("access_token_protected", "")).strip()
                protected_refresh = str(data.get("refresh_token_protected", "")).strip()
                session_device_key = (
                    _unprotect_local_secret(protected_device_key)
                    if protected_device_key
                    else ""
                )
                self.access_token = (
                    _unprotect_local_secret(protected_access) if protected_access else ""
                )
                self.refresh_token = (
                    _unprotect_local_secret(protected_refresh) if protected_refresh else ""
                )

                expected_hash = (
                    hashlib.sha256(self.license_key.encode()).hexdigest()
                    if self.license_key
                    else ""
                )
                if self.license_key and self.license_hash not in {"", expected_hash}:
                    raise ValueError("stored license key hash mismatch")
                if self.license_key:
                    self.license_hash = expected_hash

                stored_device_id = str(data.get("device_id", "")).strip().lower()
                stored_anchor = str(data.get("machine_anchor", "")).strip()
                cache_is_foreign = False
                if stored_anchor and stored_anchor != _current_machine_anchor():
                    cache_is_foreign = True
                elif (
                    not stored_anchor
                    and stored_device_id
                    and not identity_loaded
                    and stored_device_id != _legacy_device_id()
                ):
                    # Preserve the pre-v1.0.6.10 anti-copy check for old caches.
                    cache_is_foreign = True

                if cache_is_foreign:
                    logging.warning(
                        "Stored license cache belongs to a different device identity; "
                        "the protected license key is retained for re-activation."
                    )
                    session_device_key = ""
                    self.access_token = ""
                    self.refresh_token = ""
                    self.access_expires_at = 0
                    self.refresh_expires_at = None

                if session_device_key:
                    material = load_device_key_material(session_device_key)
                    stored_fingerprint = str(
                        data.get("device_public_key_fingerprint", "")
                    ).strip()
                    if stored_fingerprint and stored_fingerprint != material.public_key_fingerprint:
                        raise ValueError("stored device key fingerprint mismatch")

                    if identity_loaded:
                        if (
                            material.public_key_fingerprint
                            != self.device_public_key_fingerprint
                            or (stored_device_id and stored_device_id != self._device_id)
                        ):
                            # The durable device identity is authoritative across app
                            # upgrades. Do not let a stale per-install session replace it.
                            logging.warning(
                                "Discarding stale Licora session credentials that do not "
                                "match the durable device identity."
                            )
                            self.access_token = ""
                            self.refresh_token = ""
                            self.access_expires_at = 0
                            self.refresh_expires_at = None
                    else:
                        self.device_private_key_pem = material.private_key_pem
                        self.device_public_key_fingerprint = material.public_key_fingerprint
                        self._device_id = stored_device_id or _legacy_device_id()
                        self._device_recovery_rotations = max(
                            0, int(data.get("device_recovery_rotations", 0) or 0)
                        )
                        _write_device_identity(
                            device_id=self._device_id,
                            private_key_pem=self.device_private_key_pem,
                            fingerprint=self.device_public_key_fingerprint,
                            recovery_rotations=self._device_recovery_rotations,
                        )
                        identity_loaded = True

                if self.app_id != APP.app_id or (
                    self.schema_version >= 2 and self.protocol != "licora-api-v2"
                ):
                    raise ValueError("stored Licora API v2 application identity mismatch")
                self._verified_access_token = ""
                self._verified_access_expires_at = 0
            except Exception:
                # Fail closed for corrupted/tampered session state, but preserve a
                # separately protected durable device identity when one was loaded.
                self.license_key = ""
                self.license_hash = ""
                self.user_email = ""
                self.activated_until = None
                self.schema_version = 2
                self.protocol = "licora-api-v2"
                self.app_id = APP.app_id
                if not identity_loaded:
                    self._device_id = ""
                    self.device_private_key_pem = ""
                    self.device_public_key_fingerprint = ""
                    self._device_recovery_rotations = 0
                self.access_token = ""
                self.refresh_token = ""
                self.access_expires_at = 0
                self.refresh_expires_at = None
                self._verified_access_token = ""
                self._verified_access_expires_at = 0
                self._token_verifier = None
                logging.exception("Failed to load protected Licora API v2 license data")

    def save(self) -> None:
        with self._lock:
            license_hash = (
                hashlib.sha256(self.license_key.encode()).hexdigest()
                if self.license_key
                else self.license_hash
            )
            self.license_hash = license_hash

            protected_key = _protect_local_secret(self.license_key) if self.license_key else ""
            protected_device = (
                _protect_local_secret(self.device_private_key_pem)
                if self.device_private_key_pem
                else ""
            )
            protected_access = (
                _protect_local_secret(self.access_token) if self.access_token else ""
            )
            protected_refresh = (
                _protect_local_secret(self.refresh_token) if self.refresh_token else ""
            )
            if os.name == "nt":
                required_pairs = (
                    (self.license_key, protected_key, "license key"),
                    (self.device_private_key_pem, protected_device, "device private key"),
                    (self.access_token, protected_access, "access token"),
                    (self.refresh_token, protected_refresh, "refresh token"),
                )
                for raw, protected, label in required_pairs:
                    if raw and not protected:
                        raise RuntimeError(f"Windows DPAPI failed to protect {label}.")

            if self.device_private_key_pem:
                if not self._device_id:
                    self._device_id = _legacy_device_id()
                _write_device_identity(
                    device_id=self._device_id,
                    private_key_pem=self.device_private_key_pem,
                    fingerprint=self.device_public_key_fingerprint,
                    recovery_rotations=self._device_recovery_rotations,
                )

            payload = {
                "schema_version": 2,
                "protocol": "licora-api-v2",
                "app_id": APP.app_id,
                "license_key_protected": protected_key,
                "license_hash": license_hash,
                "user_email": self.user_email,
                "device_id": self.device_id(),
                "device_private_key_protected": protected_device,
                "device_public_key_fingerprint": self.device_public_key_fingerprint,
                "device_recovery_rotations": int(self._device_recovery_rotations),
                "machine_anchor": _current_machine_anchor(),
                "access_token_protected": protected_access,
                "refresh_token_protected": protected_refresh,
                "access_expires_at": int(self.access_expires_at or 0),
                "refresh_expires_at": self.refresh_expires_at,
                "activated_until": self.activated_until,
                "saved_at": now_str(),
            }
            _atomic_json_write(LICENSE_FILE, payload)

    def device_id(self) -> str:
        return self._device_id or _legacy_device_id()

    def validate(self, license_key: str, email: str) -> tuple[bool, str]:
        license_key = license_key.strip().upper()
        email = email.strip()

        def outcome(ok: bool, message: str, code: str) -> tuple[bool, str]:
            with self._lock:
                self._last_validation_code = str(code or "LICORA_V2_ERROR")
            return ok, message

        if len(license_key) < 8:
            return outcome(False, "License key must be at least 8 characters.", "INPUT_ERROR")
        if email and not EMAIL_RE.match(email):
            return outcome(False, "Please enter a valid email address.", "INPUT_ERROR")

        request_timeout = min(
            300.0,
            max(
                1.0,
                float(
                    self.settings.get(
                        "request_timeout", DEFAULT_SETTINGS["request_timeout"]
                    )
                ),
            ),
        )

        # Explicit logout performs best-effort server deactivation in the background.
        # A new activation must not overtake that request and then be revoked by the
        # stale logout thread after it succeeds.
        if not self._remote_logout_done.wait(timeout=request_timeout + 1.0):
            return outcome(
                False,
                "Previous license logout is still finishing. Please retry shortly.",
                "LOGOUT_PENDING",
            )

        try:
            client = LicoraV2Client(app_version=APP_VERSION, timeout=request_timeout)
        except LicoraV2Error as exc:
            logging.error("Licora API v2 configuration rejected: %s", exc.code)
            return outcome(
                False,
                f"Secure licensing configuration error ({exc.code}).",
                exc.code,
            )

        # Only one remote validation/refresh/activation sequence may mutate the
        # rotating credential state at a time. The separate state lock remains free
        # while network I/O is in flight so UI reads cannot freeze behind HTTP.
        with self._validation_lock:
            with self._lock:
                # Re-check while holding both the remote-validation lock and the
                # short state lock.  Logout clears this event while holding
                # ``_lock``; without this second check a validate() call that passed
                # the earlier wait could still acquire ``_validation_lock`` ahead of
                # the queued deactivation thread and reactivate the just-revoked ID.
                if not self._remote_logout_done.is_set():
                    return outcome(
                        False,
                        "Previous license logout is still finishing. Please retry shortly.",
                        "LOGOUT_PENDING",
                    )
                generation = self._state_generation
                previous_license = self.license_key
                previous_access = self.access_token
                previous_private_key = self.device_private_key_pem
                previous_device_id = self.device_id()
                same_license = previous_license == license_key and bool(previous_license)

                key_was_generated = False
                if self.device_private_key_pem:
                    try:
                        material = load_device_key_material(self.device_private_key_pem)
                    except LicoraV2Error:
                        material = generate_device_key_material()
                        key_was_generated = True
                        self._device_id = _legacy_device_id()
                        self._device_recovery_rotations = 0
                        self.access_token = ""
                        self.refresh_token = ""
                        self.access_expires_at = 0
                        self.refresh_expires_at = None
                        self._verified_access_token = ""
                        self._verified_access_expires_at = 0
                else:
                    material = generate_device_key_material()
                    key_was_generated = True
                    if not self._device_id:
                        self._device_id = _legacy_device_id()

                self.device_private_key_pem = material.private_key_pem
                self.device_public_key_fingerprint = material.public_key_fingerprint

                if previous_license and previous_license != license_key:
                    # A license switch clears only license/session state. The P-256
                    # device identity remains persistent. If the previous server-side
                    # deactivation succeeds, a future switch back is recovered through
                    # the revoked-device identity rollover below.
                    self.license_key = ""
                    self.license_hash = ""
                    self.user_email = ""
                    self.activated_until = None
                    self.access_token = ""
                    self.refresh_token = ""
                    self.access_expires_at = 0
                    self.refresh_expires_at = None
                    self._verified_access_token = ""
                    self._verified_access_expires_at = 0

                # Persist a newly generated P-256 device key before any activation
                # request can register it server-side. The separate durable identity
                # file survives clean source/application upgrades and session-cache
                # corruption.
                if key_was_generated or (previous_license and previous_license != license_key):
                    try:
                        self.save()
                    except Exception as exc:
                        logging.exception("Unable to persist the secure Licora device identity")
                        return outcome(
                            False,
                            f"Unable to persist secure device identity: {exc}",
                            "LOCAL_PERSISTENCE_ERROR",
                        )

                access_token = self.access_token if same_license else ""
                refresh_token = self.refresh_token if same_license else ""
                private_key_pem = self.device_private_key_pem
                fingerprint = self.device_public_key_fingerprint
                device_id = self.device_id()

            if previous_license and previous_license != license_key and previous_access and previous_private_key:
                try:
                    client.deactivate(
                        access_token=previous_access,
                        device_id=previous_device_id,
                        private_key_pem=previous_private_key,
                    )
                except Exception:
                    logging.info(
                        "Previous Licora API v2 session could not be deactivated during license switch.",
                        exc_info=True,
                    )

            with self._lock:
                if self._state_generation != generation:
                    return outcome(False, "License session changed locally.", "SESSION_CHANGED")

            # First prefer the existing short-lived access credential. The request
            # still performs server-side status validation and device proof.
            if same_license and access_token:
                try:
                    claims = client.verify_access_token(
                        access_token,
                        expected_device_id=device_id,
                        expected_device_fingerprint=fingerprint,
                    )
                    status = client.status(
                        access_token=access_token,
                        device_id=device_id,
                        private_key_pem=private_key_pem,
                    )
                    license_info = status.get("license", {})
                    activated_until = (
                        license_info.get("expires_at")
                        if isinstance(license_info, dict)
                        else None
                    )
                    with self._lock:
                        if self._state_generation != generation:
                            return outcome(False, "License session changed locally.", "SESSION_CHANGED")
                        self.license_key = license_key
                        self.license_hash = hashlib.sha256(license_key.encode()).hexdigest()
                        self.user_email = email
                        self.activated_until = activated_until or self.activated_until
                        self.schema_version = 2
                        self.protocol = "licora-api-v2"
                        self.app_id = APP.app_id
                        self.access_token = access_token
                        self.access_expires_at = claims.expires_at
                        self._verified_access_token = access_token
                        self._verified_access_expires_at = claims.expires_at
                        self._token_verifier = client
                        self.save()
                    return outcome(True, "Secure license session verified.", "OK")
                except LicoraV2Error as exc:
                    recoverable_status = exc.code in {"DEVICE_REVOKED", "INVALID_DEVICE_PROOF"}
                    token_invalid = exc.code in {"TOKEN_EXPIRED", "TOKEN_NOT_YET_VALID", "INVALID_TOKEN"}
                    if not token_invalid and not recoverable_status:
                        logging.warning("Licora API v2 status failed: %s", exc.code)
                        return outcome(False, _license_error_message(exc), exc.code)
                    with self._lock:
                        if self._state_generation != generation:
                            return outcome(False, "License session changed locally.", "SESSION_CHANGED")
                        if self.access_token == access_token:
                            self.access_token = ""
                            self.access_expires_at = 0
                            self._verified_access_token = ""
                            self._verified_access_expires_at = 0
                        if recoverable_status:
                            self.refresh_token = ""
                            self.refresh_expires_at = None
                        self.save()
                    access_token = ""
                    if recoverable_status:
                        refresh_token = ""
                        logging.warning(
                            "Licora status requires device re-activation recovery: %s",
                            exc.code,
                        )

            # Refresh is one-shot because Licora rotates refresh credentials. If a
            # network failure makes the result ambiguous, persistently discard the
            # old token before activation recovery so a restart can never replay it.
            if same_license and refresh_token:
                try:
                    refreshed = client.refresh(
                        refresh_token=refresh_token,
                        device_id=device_id,
                        private_key_pem=private_key_pem,
                    )
                    claims_raw = refreshed["verified_claims"]
                    new_access = str(refreshed["access_token"])
                    new_refresh = str(refreshed["refresh_token"])
                    status = client.status(
                        access_token=new_access,
                        device_id=device_id,
                        private_key_pem=private_key_pem,
                    )
                    license_info = status.get("license", {})
                    activated_until = (
                        license_info.get("expires_at")
                        if isinstance(license_info, dict)
                        else None
                    )
                    with self._lock:
                        if self._state_generation != generation:
                            return outcome(False, "License session changed locally.", "SESSION_CHANGED")
                        self.license_key = license_key
                        self.license_hash = hashlib.sha256(license_key.encode()).hexdigest()
                        self.user_email = email
                        self.activated_until = activated_until or self.activated_until
                        self.schema_version = 2
                        self.protocol = "licora-api-v2"
                        self.app_id = APP.app_id
                        self.access_token = new_access
                        self.refresh_token = new_refresh
                        self.access_expires_at = int(claims_raw["exp"])
                        self.refresh_expires_at = refreshed.get("refresh_expires_at")
                        self._verified_access_token = new_access
                        self._verified_access_expires_at = int(claims_raw["exp"])
                        self._token_verifier = client
                        self.save()
                    return outcome(True, "Secure license session refreshed.", "OK")
                except LicoraV2Error as exc:
                    logging.warning("Licora API v2 refresh failed: %s", exc.code)
                    with self._lock:
                        if self._state_generation != generation:
                            return outcome(False, "License session changed locally.", "SESSION_CHANGED")
                        # Clear the exact one-shot credential on disk before any
                        # re-activation attempt. The server may already have rotated
                        # it even when the response was lost in transit.
                        if self.refresh_token == refresh_token:
                            self.refresh_token = ""
                        self.access_token = ""
                        self.access_expires_at = 0
                        self.refresh_expires_at = None
                        self._verified_access_token = ""
                        self._verified_access_expires_at = 0
                        try:
                            self.save()
                        except Exception as save_exc:
                            logging.exception("Failed to persist discarded Licora refresh credentials")
                            return outcome(
                                False,
                                f"Unable to persist secure refresh state: {save_exc}",
                                "LOCAL_PERSISTENCE_ERROR",
                            )

            def activate_once(active_device_id: str) -> dict[str, Any]:
                return client.activate(
                    license_key=license_key,
                    device_id=active_device_id,
                    private_key_pem=private_key_pem,
                )

            try:
                try:
                    activated = activate_once(device_id)
                except LicoraV2Error as first_exc:
                    if first_exc.code not in {"DEVICE_KEY_MISMATCH", "DEVICE_REVOKED"}:
                        raise

                    # The current Licora server binds a credential fingerprint to a
                    # client-provided device ID, and deactivation permanently revokes
                    # that ID.  If the old private key was lost in an install-local
                    # cache, or a previous logout successfully revoked the ID, the
                    # client cannot prove/restore that old record.  Rotate to one new
                    # stable device ID and retry exactly once.  The new ID is persisted
                    # before transmission so an ambiguous response is restart-safe.
                    with self._lock:
                        if self._state_generation != generation:
                            return outcome(False, "License session changed locally.", "SESSION_CHANGED")
                        self._device_id = secrets.token_hex(12)
                        self._device_recovery_rotations += 1
                        self.access_token = ""
                        self.refresh_token = ""
                        self.access_expires_at = 0
                        self.refresh_expires_at = None
                        self._verified_access_token = ""
                        self._verified_access_expires_at = 0
                        self.save()
                        device_id = self._device_id
                    logging.warning(
                        "Licora device identity recovery: %s -> new device id (%s).",
                        first_exc.code,
                        device_id,
                    )
                    try:
                        activated = activate_once(device_id)
                    except LicoraV2Error as recovery_exc:
                        if (
                            first_exc.code == "DEVICE_KEY_MISMATCH"
                            and recovery_exc.code == "DEVICE_LIMIT_REACHED"
                        ):
                            return outcome(
                                False,
                                "A stale registered device still occupies the license limit. "
                                "Remove that old device in Licora, then retry. (DEVICE_LIMIT_REACHED)",
                                recovery_exc.code,
                            )
                        raise recovery_exc

                claims_raw = activated["verified_claims"]
                new_access = str(activated["access_token"])
                new_refresh = str(activated["refresh_token"])
                with self._lock:
                    if self._state_generation != generation:
                        stale_activation = True
                    else:
                        stale_activation = False
                        license_info = activated.get("license", {})
                        self.activated_until = (
                            license_info.get("expires_at")
                            if isinstance(license_info, dict)
                            else None
                        )
                        self.license_key = license_key
                        self.license_hash = hashlib.sha256(license_key.encode()).hexdigest()
                        self.user_email = email
                        self.schema_version = 2
                        self.protocol = "licora-api-v2"
                        self.app_id = APP.app_id
                        self.access_token = new_access
                        self.refresh_token = new_refresh
                        self.access_expires_at = int(claims_raw["exp"])
                        self.refresh_expires_at = activated.get("refresh_expires_at")
                        self._verified_access_token = new_access
                        self._verified_access_expires_at = int(claims_raw["exp"])
                        self._token_verifier = client
                        self.save()
                if stale_activation:
                    try:
                        client.deactivate(
                            access_token=new_access,
                            device_id=device_id,
                            private_key_pem=private_key_pem,
                        )
                    except Exception:
                        logging.info(
                            "Stale Licora activation could not be deactivated after a local session change.",
                            exc_info=True,
                        )
                    return outcome(False, "License session changed locally.", "SESSION_CHANGED")
                logging.info("Licora API v2 license activated for %s", email or "local user")
                return outcome(True, "License activated securely.", "OK")
            except LicoraV2Error as exc:
                logging.warning(
                    "Licora API v2 activation rejected: code=%s request_id=%s",
                    exc.code,
                    exc.request_id or "n/a",
                )
                return outcome(False, _license_error_message(exc), exc.code)
            except Exception as exc:
                logging.exception("Secure remote license validation failed")
                return outcome(False, f"License validation failed: {exc}", "UNEXPECTED_ERROR")

    def is_activated(self) -> bool:
        with self._lock:
            license_key = self.license_key
            license_hash = self.license_hash
            access_token = self.access_token
            private_key_pem = self.device_private_key_pem
            cached_token = self._verified_access_token
            cached_expiry = int(self._verified_access_expires_at or 0)
            verifier = self._token_verifier
            protocol = self.protocol
            app_id = self.app_id

        if (
            not license_key
            or not access_token
            or not private_key_pem
            or protocol != "licora-api-v2"
            or app_id != APP.app_id
        ):
            return False
        expected_hash = hashlib.sha256(license_key.encode()).hexdigest()
        if not license_hash or license_hash != expected_hash:
            return False

        now = int(time.time())
        if cached_token == access_token and cached_expiry > now:
            return True

        try:
            material = load_device_key_material(private_key_pem)
            if verifier is None:
                verifier = LicoraV2Client(app_version=APP_VERSION, timeout=1.0)
            claims = verifier.verify_access_token(
                access_token,
                expected_device_id=self.device_id(),
                expected_device_fingerprint=material.public_key_fingerprint,
            )
            with self._lock:
                if self.access_token == access_token:
                    self.access_expires_at = claims.expires_at
                    self._verified_access_token = access_token
                    self._verified_access_expires_at = claims.expires_at
                    self._token_verifier = verifier
            return True
        except Exception:
            return False

    def logout(self) -> None:
        with self._lock:
            access_token = self.access_token
            private_key_pem = self.device_private_key_pem
            device_id = self.device_id()
            request_timeout = min(
                300.0,
                max(
                    1.0,
                    float(
                        self.settings.get(
                            "request_timeout", DEFAULT_SETTINGS["request_timeout"]
                        )
                    ),
                ),
            )
            self._state_generation += 1
            logout_generation = self._state_generation
            self.license_key = ""
            self.license_hash = ""
            self.user_email = ""
            self.activated_until = None
            self.access_token = ""
            self.refresh_token = ""
            self.access_expires_at = 0
            self.refresh_expires_at = None
            self._verified_access_token = ""
            self._verified_access_expires_at = 0
            self._last_validation_code = "LOGGED_OUT"
            needs_remote_deactivate = bool(access_token and private_key_pem)
            if needs_remote_deactivate:
                self._remote_logout_done.clear()
            else:
                self._remote_logout_done.set()
            try:
                if self.device_private_key_pem:
                    self.save()
                else:
                    LICENSE_FILE.unlink(missing_ok=True)
            except Exception:
                logging.exception("Failed to persist local Licora logout state")
                try:
                    LICENSE_FILE.unlink(missing_ok=True)
                except Exception:
                    logging.exception("Failed to remove protected Licora API v2 license file")

        if not needs_remote_deactivate:
            return

        def revoke_remote() -> None:
            deactivated = False
            try:
                # Serialize server deactivation with validate(). A subsequent login
                # waits on _remote_logout_done and therefore cannot be revoked by a
                # stale logout request after its own activation succeeds.
                with self._validation_lock:
                    LicoraV2Client(
                        app_version=APP_VERSION, timeout=request_timeout
                    ).deactivate(
                        access_token=access_token,
                        device_id=device_id,
                        private_key_pem=private_key_pem,
                    )
                    deactivated = True
            except Exception:
                # Local logout must never be blocked by an unavailable server or an
                # already-expired/revoked access token. If the outcome was ambiguous,
                # keeping the old device ID lets the next activation safely discover
                # whether server-side recovery is necessary.
                logging.info(
                    "Licora API v2 remote deactivation was not completed during logout.",
                    exc_info=True,
                )
            finally:
                if deactivated:
                    with self._lock:
                        if (
                            self._state_generation == logout_generation
                            and not self.license_key
                        ):
                            # Licora deactivation permanently revokes the old device
                            # ID. Rotate only after confirmed success so same-device
                            # re-login works even for a one-device license.
                            self._device_id = secrets.token_hex(12)
                            self._device_recovery_rotations += 1
                            try:
                                self.save()
                            except Exception:
                                logging.exception(
                                    "Failed to persist post-logout Licora device identity rotation"
                                )
                self._remote_logout_done.set()

        threading.Thread(target=revoke_remote, daemon=True).start()

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
    run_id: str = ""
    source_file: str = ""
    source_fingerprint: str = ""
    manual_review_required: bool = False
    send_limit_used: int = 0

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
        runtime_store: TaskRuntimeStore | None = None,
        active_workflow_id: str | None = None,
        workflow_input_values: dict[str, Any] | None = None,
        workflow_settings_values: dict[str, Any] | None = None,
        workflow_task_values: dict[str, Any] | None = None,
        workflow_item_payloads: list[dict[str, Any]] | None = None,
        workflow_manager: WorkflowManager | None = None,
    ):
        super().__init__(daemon=True, name=f"slot-{state.slot_id}-browser-worker")
        self.state = state
        self.settings = dict(settings)
        self.ui_queue = ui_queue
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.initial_url = initial_url
        self.runtime_store = runtime_store
        # PR-08: capture an immutable per-worker snapshot of the active
        # workflow's validated inputs. Existing workers are intentionally not
        # live-mutated when Workflow Inputs are saved.
        self.workflow_input_values = MappingProxyType(dict(workflow_input_values or {}))
        self.workflow_settings_values = MappingProxyType(dict(workflow_settings_values or {}))
        self.workflow_task_values = MappingProxyType(dict(workflow_task_values or {}))
        self.workflow_item_payloads = tuple(
            MappingProxyType(dict(payload)) for payload in (workflow_item_payloads or [])
        )
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
        self.stopped_event = threading.Event()
        self.last_login_probe_at = 0.0
        self.last_autosave_at = time.monotonic()
        self.run_send_count = max(0, int(self.state.send_limit_used))
        self.run_send_limit = 0
        self.persistent_context_mode = False
        self.temporary_profile_dir: Path | None = None
        self.active_profile_dir: Path | None = None
        self.browser_restart_count = 0
        self.resource_route_handler = None
        # Phase-01 browser lifecycle truth is owned by this worker thread and
        # exposed to the UI through thread-safe Events/status messages.  Qt must
        # never need to inspect Playwright objects directly.
        self._browser_lifecycle_lock = threading.RLock()
        self._browser_lifecycle_state = "CLOSED"
        self._context_transitioning = False
        self._lifecycle_browser_id: int | None = None
        self._lifecycle_context_id: int | None = None
        self._lifecycle_page_ids: set[int] = set()
        self._configured_page_ids: set[int] = set()
        self._power_guard_owner = f"task:{self.state.slot_id}:worker:{id(self)}"
        # A FileChooser wrapper is retained only inside the Playwright owner
        # thread. Qt receives an opaque request ID and returns local paths through
        # the command queue, so no Playwright object crosses thread boundaries.
        self._pending_file_chooser = None
        self._pending_file_chooser_request_id: str | None = None
        self._pending_file_chooser_page_id: int | None = None
        self.browser_launch_diagnostics: dict[str, Any] = {}
        # Phase 2: each Task owns an immutable workflow identity and injects a
        # manager clone bound to that identity. None/unknown values remain fail-closed
        # at the existing Master Workflow Gate; no workflow-specific fallback lives
        # inside AutomationWorker.
        if workflow_manager is not None:
            requested_workflow_id = (
                None if active_workflow_id is None else (str(active_workflow_id).strip() or None)
            )
            if workflow_manager.active_workflow_id != requested_workflow_id:
                raise WorkflowRuntimeResolutionError(
                    "worker workflow catalog active identity does not match active_workflow_id"
                )
            self._workflow_manager = workflow_manager
        else:
            self._workflow_manager = WorkflowManager.with_builtin_workflows(
                active_workflow_id=active_workflow_id
            )
        self._active_workflow_runtime_cache: WorkflowRuntime | None = None
        self.run_send_limit = self._resolved_workflow_test_send_limit()

    def emit(self, kind: str, payload: dict[str, Any]) -> None:
        payload["slot_id"] = self.state.slot_id
        event = (kind, payload)
        critical = {"item", "security", "browser", "login", "done", "license_invalid", "download", "browser_file_chooser"}
        if kind not in critical:
            try:
                self.ui_queue.put_nowait(event)
            except queue.Full:
                logging.warning("Slot %s: coalescible UI event dropped under backpressure: %s", self.state.slot_id, kind)
            return
        # Critical lifecycle/result events apply backpressure during normal operation.
        # During an explicit stop/close, the runtime store is authoritative for item
        # outcomes, so a saturated UI queue must not keep the worker alive forever.
        while True:
            try:
                self.ui_queue.put(event, timeout=0.5)
                return
            except queue.Full:
                if self.stop_event.is_set() or self.close_event.is_set():
                    logging.warning(
                        "Slot %s: dropping saturated critical UI event during shutdown: %s",
                        self.state.slot_id,
                        kind,
                    )
                    return
                logging.warning(
                    "Slot %s: waiting for UI queue capacity for critical event: %s",
                    self.state.slot_id,
                    kind,
                )

    def log(self, message: str, level: str = "INFO") -> None:
        logging.log(
            getattr(logging, level, logging.INFO),
            "Slot %s: %s",
            self.state.slot_id,
            message,
        )
        self.emit("log", {"message": message, "level": level, "timestamp": now_str()})

    def _save_runtime_progress(self, *, force: bool = False) -> None:
        if self.runtime_store is None or not self.state.run_id:
            return
        interval = max(0.0, float(self.settings.get("auto_save_interval", DEFAULT_SETTINGS["auto_save_interval"])))
        now = time.monotonic()
        if not force and interval > 0 and (now - self.last_autosave_at) < interval:
            return
        if not force and interval == 0:
            return
        self.runtime_store.save_progress(
            run_id=self.state.run_id,
            current_index=self.state.current_index,
            total=self.state.total,
            success_count=self.state.success_count,
            failed_count=self.state.failed_count,
            send_limit_used=self.run_send_count,
            task_status=self.state.status,
            manual_review_required=self.state.manual_review_required,
            updated_at=now_str(),
            target_url=self.state.target_url,
        )
        self.last_autosave_at = now

    def _save_runtime_item(self, index: int, item: TaskItem, message: str) -> None:
        if self.runtime_store is not None and self.state.run_id:
            row = None if item.status == "processing" else self.report_row(item, message, item_index=index)
            self.runtime_store.persist_item_result_progress(
                run_id=self.state.run_id,
                item_index=index,
                item=item,
                result_row=row,
                current_index=self.state.current_index,
                total=self.state.total,
                success_count=self.state.success_count,
                failed_count=self.state.failed_count,
                send_limit_used=self.run_send_count,
                task_status=self.state.status,
                manual_review_required=self.state.manual_review_required,
                updated_at=now_str(),
                target_url=self.state.target_url,
            )
            self.last_autosave_at = time.monotonic()
            return
        self._save_runtime_progress(force=True)

    def request_start(self, settings: dict[str, Any], target_url: str) -> None:
        self.control_queue.put(
            ("start", {"settings": dict(settings), "target_url": target_url})
        )

    def request_focus(self) -> None:
        self.control_queue.put(("focus", {}))

    def request_file_chooser_selection(
        self, request_id: str, paths: list[str] | None, *, cancelled: bool = False
    ) -> None:
        """Queue a user-selected browser upload response without touching Playwright."""
        self.control_queue.put(
            (
                "filechooser_response",
                {
                    "request_id": str(request_id),
                    "paths": list(paths or []),
                    "cancelled": bool(cancelled),
                },
            )
        )

    def request_close(self) -> None:
        self.close_event.set()
        self.stop_event.set()
        self.pause_event.clear()
        self.control_queue.put(("close", {}))

    def _set_browser_lifecycle_state(self, state: str) -> None:
        """Publish one deterministic browser lifecycle state to the UI.

        Playwright objects remain worker-thread owned.  Other threads consume
        only ``browser_ready_event`` and emitted state, avoiding cross-thread
        calls into Page/Browser wrappers.
        """
        normalized = str(state).strip().upper()
        if normalized not in {"CLOSED", "OPENING", "OPEN", "CLOSING"}:
            raise ValueError(f"Unsupported browser lifecycle state: {state}")
        with self._browser_lifecycle_lock:
            previous = self._browser_lifecycle_state
            self._browser_lifecycle_state = normalized
            if normalized == "OPEN":
                self.browser_ready_event.set()
            else:
                self.browser_ready_event.clear()
                self.login_verified_event.clear()
            changed = previous != normalized
        if changed:
            self.emit("browser", {"status": normalized.title()})

    def _live_context_pages(self, *, exclude=None) -> list[Any]:
        context = self.context
        if context is None:
            return []
        try:
            pages = list(context.pages)
        except Exception:
            return []
        live: list[Any] = []
        for page in pages:
            if page is exclude:
                continue
            try:
                if not page.is_closed():
                    live.append(page)
            except Exception:
                continue
        return live

    @staticmethod
    def _page_url(page) -> str:
        try:
            return str(getattr(page, "url", "") or "")
        except Exception:
            return ""

    @staticmethod
    def _is_internal_page_url(url: str) -> bool:
        normalized = str(url or "").strip().lower()
        return not normalized or normalized in {"about:blank", "chrome://newtab/"} or normalized.startswith("chrome://")

    def _page_is_usable(self, page) -> bool:
        if page is None:
            return False
        try:
            if page.is_closed():
                return False
        except Exception:
            return False
        return not self._is_internal_page_url(self._page_url(page))

    @staticmethod
    def _origin_from_url(url: str) -> tuple[str, str, int | None] | None:
        try:
            parsed = urlparse(str(url or ""))
            scheme = parsed.scheme.lower()
            host = (parsed.hostname or "").lower()
            port = parsed.port
        except (TypeError, ValueError):
            return None
        if scheme not in {"http", "https"} or not host:
            return None
        # Browser origins treat an omitted default port and its explicit
        # equivalent as the same origin (HTTP :80, HTTPS :443). Canonicalize
        # those representations so deterministic page ownership cannot fall
        # through to an unrelated usable tab solely because one URL spells
        # the default port explicitly. Non-default ports remain significant.
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            port = None
        return (scheme, host, port)

    def _select_preferred_page(
        self, pages: list[Any], *, preferred_url: str | None = None
    ):
        """Choose a deterministic owned page without workflow-specific host rules."""
        live: list[Any] = []
        for page in pages:
            try:
                if page is not None and not page.is_closed():
                    live.append(page)
            except Exception:
                continue
        if not live:
            return None

        preferred = preferred_url
        if preferred is None:
            preferred = self.state.target_url or self.initial_url
        target_origin = self._origin_from_url(preferred or "")
        if target_origin is not None:
            same_origin = [
                page
                for page in live
                if self._origin_from_url(self._page_url(page)) == target_origin
                and self._page_is_usable(page)
            ]
            if same_origin:
                return same_origin[-1]

        usable = [page for page in live if self._page_is_usable(page)]
        if usable:
            return usable[-1]
        return live[0]

    @staticmethod
    def _page_opener(page):
        try:
            opener = getattr(page, "opener", None)
            return opener() if callable(opener) else opener
        except Exception:
            return None

    def _should_adopt_new_page(self, page) -> bool:
        if not self._page_is_usable(page):
            return False
        if self.active_page is None:
            return True
        if not self.processing_event.is_set():
            return True
        return self._page_opener(page) is self.active_page

    def _safe_page_identity(self, page, *, pages: list[Any] | None = None) -> str:
        url = self._page_url(page)
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme or "unknown"
            host = parsed.hostname or ""
            path = parsed.path or "/"
        except Exception:
            scheme, host, path = "unknown", "", "/"
        if pages is None:
            pages = self._live_context_pages()
        index = 0
        for offset, candidate in enumerate(pages, start=1):
            if candidate is page:
                index = offset
                break
        return f"page={index or '?'} scheme={scheme} host={host or '-'} path={path}"

    def _adopt_active_page(self, page, *, reason: str, clear_session: bool = True) -> bool:
        if page is None:
            return False
        try:
            if page.is_closed():
                return False
        except Exception:
            return False
        previous = self.active_page
        if previous is page:
            return True
        self.active_page = page
        if clear_session and self.workflow_requires_session():
            self.login_verified_event.clear()
            self.emit(
                "login",
                {
                    "verified": False,
                    "message": "The controlled browser page changed; verify the workflow session again.",
                },
            )
        self.log(
            f"Browser page ownership changed ({reason}): {self._safe_page_identity(page)}",
            "INFO",
        )
        return True

    def _mark_browser_unavailable(self, reason: str = "") -> None:
        """Clear browser/login readiness once for an external lifecycle loss."""
        self._clear_pending_file_chooser(reason or "Browser session closed.", log_event=True)
        was_login_verified = self.login_verified_event.is_set()
        with self._browser_lifecycle_lock:
            was_available = self._browser_lifecycle_state != "CLOSED"
        self._set_browser_lifecycle_state("CLOSED")
        if self.workflow_requires_session() and (was_login_verified or (reason and was_available)):
            self.emit(
                "login",
                {
                    "verified": False,
                    "message": reason or "Browser session closed; login verification was cleared.",
                },
            )

    def _browser_objects_ready(self) -> bool:
        """Owner-thread health probe for the controlled browser/page objects."""
        context = self.context
        if context is None:
            return False
        page = self.active_page
        try:
            page_closed = page is None or page.is_closed()
        except Exception:
            page_closed = True
        if page_closed:
            live_pages = self._live_context_pages(exclude=page)
            if not live_pages:
                return False
            replacement = self._select_preferred_page(
                live_pages, preferred_url=self._page_url(page)
            )
            if replacement is None:
                return False
            self._adopt_active_page(
                replacement, reason="active page health failover", clear_session=True
            )
        if self.persistent_context_mode:
            return True
        browser = self.browser
        if browser is None:
            return False
        try:
            return bool(browser.is_connected())
        except Exception:
            return False

    def _attach_browser_lifecycle_events(self) -> None:
        """Attach idempotent Browser/Context close events to the live objects."""
        browser = self.browser
        if browser is not None and id(browser) != self._lifecycle_browser_id:
            self._lifecycle_browser_id = id(browser)

            def browser_disconnected(_browser=None) -> None:
                if browser is not self.browser or self.close_event.is_set():
                    return
                self._mark_browser_unavailable("Browser closed outside the application.")

            browser.on("disconnected", browser_disconnected)

        context = self.context
        if context is not None and id(context) != self._lifecycle_context_id:
            self._lifecycle_context_id = id(context)

            def context_closed(_context=None) -> None:
                if (
                    context is not self.context
                    or self._context_transitioning
                    or self.close_event.is_set()
                    or self._browser_lifecycle_state in {"OPENING", "CLOSING"}
                ):
                    return
                self._mark_browser_unavailable("Browser context closed outside the application.")

            context.on("close", context_closed)

    def _attach_page_lifecycle_events(self, page) -> None:
        """Track manual closure of the active controlled page without UI polling."""
        if page is None or id(page) in self._lifecycle_page_ids:
            return
        self._lifecycle_page_ids.add(id(page))

        def page_closed(_page=None) -> None:
            self._lifecycle_page_ids.discard(id(page))
            self._configured_page_ids.discard(id(page))
            if self._pending_file_chooser_page_id == id(page):
                self._clear_pending_file_chooser(
                    "Pending browser file selection was cancelled because its page closed.",
                    log_event=True,
                )
            if (
                self._context_transitioning
                or self.close_event.is_set()
                or self._browser_lifecycle_state in {"OPENING", "CLOSING"}
                or page is not self.active_page
            ):
                return
            live_pages = self._live_context_pages(exclude=page)
            if live_pages:
                replacement = self._select_preferred_page(
                    live_pages, preferred_url=self._page_url(page)
                )
                if replacement is not None:
                    self._adopt_active_page(
                        replacement, reason="active page closed failover", clear_session=True
                    )
                    return
            self.active_page = None
            self._mark_browser_unavailable("The controlled browser page was closed manually.")

        page.on("close", page_closed)

    def _clear_pending_file_chooser(self, reason: str = "", *, log_event: bool = False) -> None:
        request_id = self._pending_file_chooser_request_id
        self._pending_file_chooser = None
        self._pending_file_chooser_request_id = None
        self._pending_file_chooser_page_id = None
        if request_id and log_event:
            self.log(
                reason or "Pending browser file selection was cancelled because the browser state changed.",
                "WARNING",
            )

    def _handle_file_chooser(self, page, chooser) -> None:
        """Publish a site-initiated file chooser request without selecting files automatically."""
        if self._pending_file_chooser_request_id:
            self._clear_pending_file_chooser(
                "A newer browser file selection request replaced the previous pending request.",
                log_event=True,
            )
        request_id = uuid.uuid4().hex
        try:
            multiple = bool(chooser.is_multiple())
        except Exception:
            multiple = False
        directory = False
        try:
            element = chooser.element
            directory = (
                element.get_attribute("webkitdirectory") is not None
                or element.get_attribute("directory") is not None
            )
        except Exception:
            directory = False

        self._pending_file_chooser = chooser
        self._pending_file_chooser_request_id = request_id
        self._pending_file_chooser_page_id = id(page)
        self.emit(
            "browser_file_chooser",
            {
                "request_id": request_id,
                "multiple": multiple,
                "directory": directory,
            },
        )

    def _apply_file_chooser_selection(self, payload: dict[str, Any]) -> None:
        request_id = str(payload.get("request_id", ""))
        if not request_id or request_id != self._pending_file_chooser_request_id:
            self.log("Ignored a stale browser file selection response.", "WARNING")
            return
        chooser = self._pending_file_chooser
        if chooser is None:
            self._clear_pending_file_chooser()
            return
        if bool(payload.get("cancelled", False)):
            self._clear_pending_file_chooser()
            self.log("Browser file selection was cancelled by the user.")
            return

        paths = [Path(str(value)).expanduser().resolve() for value in payload.get("paths", []) if str(value).strip()]
        try:
            multiple = bool(chooser.is_multiple())
        except Exception:
            multiple = False
        directory = False
        try:
            element = chooser.element
            directory = (
                element.get_attribute("webkitdirectory") is not None
                or element.get_attribute("directory") is not None
            )
        except Exception:
            directory = False

        if not paths:
            self._clear_pending_file_chooser()
            self.log("Browser file selection was cancelled by the user.")
            return
        if directory:
            if len(paths) != 1 or not paths[0].is_dir():
                self._clear_pending_file_chooser()
                self.log("Browser directory selection was rejected because the selected directory is no longer available.", "ERROR")
                return
            files_arg: str | list[str] = str(paths[0])
        else:
            if any(not path.is_file() for path in paths):
                self._clear_pending_file_chooser()
                self.log("Browser file selection was rejected because a selected file is no longer available.", "ERROR")
                return
            if not multiple and len(paths) != 1:
                self._clear_pending_file_chooser()
                self.log("Browser file selection rejected multiple files for a single-file input.", "ERROR")
                return
            files_arg = [str(path) for path in paths] if multiple else str(paths[0])

        try:
            chooser.set_files(files_arg)
        except Exception as exc:
            self._clear_pending_file_chooser()
            self.log(
                f"Browser file selection failed ({exc.__class__.__name__}).",
                "ERROR",
            )
            return
        selected_count = len(paths)
        self._clear_pending_file_chooser()
        self.log(
            "Browser directory selected for upload."
            if directory
            else f"Browser file selection applied ({selected_count} file{'s' if selected_count != 1 else ''})."
        )

    def _handle_download(self, download) -> None:
        suggested = str(getattr(download, "suggested_filename", "") or "download")
        self.emit(
            "download",
            {"status": "started", "filename": suggested},
        )
        if not bool(self.settings.get("accept_downloads", DEFAULT_SETTINGS["accept_downloads"])):
            self.emit(
                "download",
                {
                    "status": "failed",
                    "filename": suggested,
                    "message": "Accept Downloads is disabled in Browser Settings.",
                },
            )
            return
        try:
            directory = ensure_task_download_directory(
                self.settings, self.state.slot_id, APP_DATA_DIR
            )
            with _DOWNLOAD_SAVE_LOCK:
                destination = collision_safe_download_path(directory, suggested)
                download.save_as(str(destination))
            self.emit(
                "download",
                {
                    "status": "saved",
                    "filename": destination.name,
                    "directory": str(directory),
                },
            )
        except Exception as exc:
            self.emit(
                "download",
                {
                    "status": "failed",
                    "filename": suggested,
                    "message": f"{exc.__class__.__name__}: {exc}",
                },
            )

    def is_browser_ready(self) -> bool:
        """Return the thread-safe lifecycle truth exposed to the UI."""
        return self.browser_ready_event.is_set()

    def is_processing(self) -> bool:
        return self.processing_event.is_set()

    def is_login_verified(self) -> bool:
        return self.login_verified_event.is_set()

    def workflow_requires_session(self) -> bool:
        """Return the active Task schema session policy as the Core authority."""
        workflow_id = self._workflow_manager.active_workflow_id
        if not workflow_id:
            # Compatibility/direct-worker constructions predate workflow-neutral
            # production tasks. Treat an absent schema as session-required so
            # historical browser lifecycle safety remains fail-closed.
            return True
        try:
            return bool(self._workflow_manager.task_schema(workflow_id).requires_session)
        except Exception:
            # Production workers are created only for a validated active workflow.
            # If that invariant is unexpectedly lost, fail closed rather than
            # silently bypassing a workflow-declared authentication requirement.
            return True

    def ensure_workflow_session_if_required(self) -> None:
        """Apply the pre-Start session gate only to session-required workflows."""
        if self.workflow_requires_session():
            self.ensure_workflow_session()

    def _browser_restart_is_safe(self) -> bool:
        """Allow automatic browser restart only at an idle, outcome-safe checkpoint."""
        return (
            not self.processing_event.is_set()
            and not bool(self.state.manual_review_required)
            and not self.close_event.is_set()
        )

    def run(self) -> None:
        restart_attempts = 0
        try:
            self._set_browser_lifecycle_state("OPENING")
            self.launch_browser()
            self._set_browser_lifecycle_state("OPEN")
            if self.workflow_requires_session():
                self.state.status = "Login Required"
                self.emit("status", {"status": "Login Required"})
                self.emit(
                    "login",
                    {"verified": False, "message": "Complete login in the opened browser."},
                )
            else:
                self.state.status = "Ready"
                self.emit("status", {"status": "Ready"})

            while not self.close_event.is_set():
                try:
                    command, payload = self.control_queue.get(timeout=0.2)
                except queue.Empty:
                    if not self._browser_objects_ready():
                        self._mark_browser_unavailable("Browser was closed outside the application.")
                        if (
                            bool(
                                self.settings.get(
                                    "auto_restart_browser_on_crash",
                                    DEFAULT_SETTINGS["auto_restart_browser_on_crash"],
                                )
                            )
                            and self._browser_restart_is_safe()
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
                                self._set_browser_lifecycle_state("OPENING")
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
                                self._set_browser_lifecycle_state("OPEN")
                                if self.workflow_requires_session():
                                    self.emit(
                                        "login",
                                        {
                                            "verified": False,
                                            "message": "Browser restarted. Verify the current login session.",
                                        },
                                    )
                                continue
                        if self.state.status not in {
                            "Completed",
                            "Failed",
                            "Stopped",
                            "Test Send Limit Reached",
                            "Login/Test Mode Required",
                        }:
                            self.state.status = "Ready"
                            self.emit("status", {"status": "Ready"})
                        self.log(
                            "Browser closed outside the application; the Task was kept for reopening.",
                            "WARNING",
                        )
                        break
                    restart_attempts = 0
                    if self.workflow_requires_session():
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
                    if self.workflow_requires_session():
                        self.refresh_login_verification(force_emit=True)
                    continue
                if command == "filechooser_response":
                    self._apply_file_chooser_selection(payload)
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
                    self.run_send_count = max(0, int(self.state.send_limit_used))
                    self.run_send_limit = self._resolved_workflow_test_send_limit()
                    self.last_autosave_at = time.monotonic()
                    self._save_runtime_progress(force=True)
                    try:
                        self.ensure_workflow_session_if_required()
                        if self._uses_test_send_limit():
                            self.emit(
                                "send_limit", {"used": self.run_send_count, "limit": self.run_send_limit}
                            )
                        self.process_batch()
                    except SessionVerificationError as exc:
                        if self.workflow_requires_session():
                            runtime = self._workflow_runtime()
                            self.state.status = str(getattr(runtime, "blocked_task_status", "Login Required"))
                            self.login_verified_event.clear()
                            self.log(str(exc), "ERROR")
                            self.emit("login", {"verified": False, "message": str(exc)})
                            self.emit("status", {"status": "Login Required"})
                        else:
                            self.state.status = "Failed"
                            self.log(
                                f"Sessionless workflow raised SessionVerificationError: {exc}",
                                "ERROR",
                            )
                            self.emit("status", {"status": "Failed"})
        except Exception as exc:
            self.state.status = "Browser Failed"
            self.log(f"Browser worker failed: {exc}", "ERROR")
            self.emit("status", {"status": "Browser Failed"})
        finally:
            self.processing_event.clear()
            self._set_browser_lifecycle_state("CLOSED")
            self.cleanup()
            self.stopped_event.set()
            self.emit("done", {"status": self.state.status})

    def _workflow_runtime(self) -> WorkflowRuntime:
        """Resolve the active validated workflow through the master workflow gate."""
        runtime = self._active_workflow_runtime_cache
        if runtime is None:
            # Plugin API 1 compatibility: existing workflows may consume the legacy
            # exception namespace. Core no longer imports or knows a Share Invite runtime type.
            errors = SimpleNamespace(
                security_challenge=SecurityChallenge,
                session_verification_error=SessionVerificationError,
                test_mode_required=TestModeRequired,
                test_send_limit_reached=TestSendLimitReached,
                invite_rejected=InviteRejected,
            )
            runtime = self._workflow_manager.resolve_active_runtime(
                self,
                default_settings=DEFAULT_SETTINGS,
                errors=errors,
            )
            self._active_workflow_runtime_cache = runtime
        return runtime

    def workflow_session_ready(self, page) -> bool:
        return self._workflow_runtime().session_ready(page)

    def workflow_session_instruction(self) -> str:
        runtime = self._workflow_runtime()
        return str(
            getattr(
                runtime,
                "session_instruction",
                "Complete the workflow-required browser session, then wait for Login Verified and click Start.",
            )
        )

    def ensure_workflow_session(self) -> None:
        self._workflow_runtime().ensure_session()

    def execute_workflow_item(self, item: TaskItem) -> str:
        return self._workflow_runtime().execute_item(item)

    def prepare_workflow_retry(self) -> None:
        self._workflow_runtime().prepare_retry()

    def _uses_test_send_limit(self) -> bool:
        workflow_id = self._workflow_manager.active_workflow_id
        if not workflow_id:
            return False
        return bool(self._workflow_manager.task_schema(workflow_id).uses_test_send_limit)

    def _resolved_workflow_test_send_limit(self) -> int:
        workflow_id = self._workflow_manager.active_workflow_id
        if not workflow_id:
            # Compatibility for direct legacy worker construction used by recovery tests.
            # Production workers always receive an explicit active workflow identity.
            return safe_test_send_limit(
                self.workflow_settings_values.get(
                    "max_test_send_limit",
                    self.settings.get("max_test_send_limit", DEFAULT_TEST_SEND_LIMIT),
                )
            )
        if not self._uses_test_send_limit():
            return 0
        return safe_test_send_limit(
            self.workflow_settings_values.get("max_test_send_limit", DEFAULT_TEST_SEND_LIMIT)
        )

    def current_workflow_item_payload(self) -> dict[str, Any]:
        """Return the detached plugin payload matching the current Task item index."""
        index = max(0, int(self.state.current_index))
        if index >= len(self.workflow_item_payloads):
            return {}
        return dict(self.workflow_item_payloads[index])

    def set_workflow_step(self, step: str) -> None:
        """Publish workflow-owned step text without mutating the Core Task status."""
        self.emit("workflow_step", {"step": str(step or "")})

    def set_workflow_metric(self, key: str, value: Any) -> None:
        """Publish one workflow-declared metric value to the Core UI renderer."""
        self.emit("workflow_metric", {"key": str(key), "value": value})

    def workflow_error_decision(self, exc: Exception) -> str:
        """Resolve an optional trusted runtime error decision; unknown errors fail closed."""
        runtime = self._workflow_runtime()
        hook = getattr(runtime, "error_decision", None)
        if hook is None:
            return "FAIL_ITEM"
        decision = str(hook(exc)).strip().upper()
        if decision not in {"RETRY", "FAIL_ITEM", "MANUAL_REVIEW", "STOP_TASK"}:
            raise WorkflowRuntimeResolutionError(
                f"workflow error_decision returned unsupported value: {decision!r}"
            )
        return decision

    def refresh_login_verification(
        self, force_emit: bool = False, *, allow_while_processing: bool = False
    ) -> bool:
        if not self.workflow_requires_session():
            # Sessionless workflows must never construct/probe a runtime merely
            # for Core login state; their browser readiness is independent.
            self.login_verified_event.clear()
            return False
        if (
            (self.processing_event.is_set() and not allow_while_processing)
            or not self.browser_ready_event.is_set()
        ):
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
            verified = self.workflow_session_ready(self.active_page)
        except Exception as exc:
            verified = False
            self.log(
                "Workflow session probe failed: "
                f"workflow={self._workflow_manager.active_workflow_id or '-'} "
                f"{self._safe_page_identity(self.active_page)} "
                f"error={exc.__class__.__name__}",
                "WARNING",
            )
        previous = self.login_verified_event.is_set()
        if verified:
            self.login_verified_event.set()
        else:
            self.login_verified_event.clear()
        if force_emit or verified != previous:
            message = (
                "Workflow session verified."
                if verified
                else "Workflow session is not verified. Prepare the authenticated browser session required by this workflow."
            )
            self.emit("login", {"verified": verified, "message": message})
            if not self.processing_event.is_set():
                self.state.status = "Login Verified" if verified else "Login Required"
                self.emit("status", {"status": self.state.status})
        return verified


    def process_batch(self) -> None:
        self.processing_event.set()
        try:
            sleep_guard_acquired = SYSTEM_SLEEP_GUARD.acquire(self._power_guard_owner)
            if not sleep_guard_acquired:
                self.log(
                    "System sleep guard could not be acquired; automation will continue without OS sleep inhibition.",
                    "WARNING",
                )
            self.state.status = "Running"
            self.emit("status", {"status": "Running"})
            self.emit_progress()
            self._save_runtime_progress(force=True)
            limit_reached = False
            session_blocked = False
            processing_interrupted = False
            batch_size = max(1, int(self.settings.get("batch_size", DEFAULT_SETTINGS["batch_size"])))
            finalized_in_batch = 0
            if self.state.current_index >= self.state.total:
                self.state.status = "Completed"
                runtime = self._workflow_runtime()
                self.log(
                    str(getattr(runtime, "empty_batch_message", "No remaining workflow items to process.")),
                    "WARNING",
                )
                self._save_runtime_progress(force=True)
                if self.runtime_store is not None and self.state.run_id:
                    self.runtime_store.mark_completed(self.state.run_id, "Completed", now_str())
                self.emit("status", {"status": "Completed"})
                return

            for index in range(self.state.current_index, self.state.total):
                if self.stop_event.is_set() or self.close_event.is_set():
                    self.log("Stop requested; saving unprocessed data.")
                    break
                self.wait_if_paused()
                self._save_runtime_progress()
                if self.stop_event.is_set() or self.close_event.is_set():
                    break

                item = self.state.items[index]
                self.process_item(index, item)
                self._save_runtime_item(index, item, item.message)
                if item.status != "processing":
                    self.emit("item", self.report_row(item, item.message, item_index=index))
                if item.status in {"success", "failed"}:
                    self.state.current_index = index + 1
                    finalized_in_batch += 1
                    self._save_runtime_progress(force=True)
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
                # Preserve same-page behavior while fixing production recycle accounting:
                # every safely finalized item contributes to item/time recycle thresholds.
                if item.status == "success" and bool(
                    self.settings.get(
                        "re_open_after_success_per_order",
                        DEFAULT_SETTINGS["re_open_after_success_per_order"],
                    )
                ):
                    self.reopen_active_page()
                if item.status in {"success", "failed"}:
                    recycle_session_ready = self.maybe_recycle_context()
                    # Historical/internal overrides may return None. Only an
                    # explicit False from the v1.0.6.40 recycle contract means
                    # a required session was actively re-probed and failed.
                    if recycle_session_ready is False:
                        session_blocked = True
                        break

                if finalized_in_batch >= batch_size:
                    self._save_runtime_progress(force=True)
                    if self.runtime_store is not None:
                        self.runtime_store.checkpoint()
                    finalized_in_batch = 0

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
                runtime = self._workflow_runtime()
                self.state.status = str(getattr(runtime, "blocked_task_status", "Blocked"))
                self.save_unprocessed()
            elif processing_interrupted:
                self.state.status = "Interrupted"
                self.save_unprocessed()
            elif self.stop_event.is_set() or self.close_event.is_set():
                self.state.status = "Stopped"
                # v1.0.6.30 safety contract: unprocessed user data is always preserved.
                self.save_unprocessed()
            else:
                self.state.status = "Completed"
            self._save_runtime_progress(force=True)
            if self.runtime_store is not None and self.state.run_id:
                self.runtime_store.mark_completed(self.state.run_id, self.state.status, now_str())
            visible_status = (
                "Login Required"
                if self.state.status == "Login/Test Mode Required"
                else self.state.status
            )
            self.emit("status", {"status": visible_status})
        except Exception as exc:
            self.state.status = "Failed"
            self.log(f"Task failed: {exc}", "ERROR")
            self._save_runtime_progress(force=True)
            self.emit("status", {"status": "Failed"})
            self.save_unprocessed()
        finally:
            # Release process-level sleep inhibition before any fallible final
            # persistence/UI work so worker-finalization errors cannot strand
            # a Windows system-awake request.
            self.processing_event.clear()
            SYSTEM_SLEEP_GUARD.release(self._power_guard_owner)
            self.save_failed()
            self._save_runtime_progress(force=True)
            self.emit_progress()
            self.emit("done", {"status": self.state.status})

    def interruptible_sleep(self, seconds: float) -> None:
        end = time.monotonic() + max(0.0, seconds)
        while time.monotonic() < end:
            if self.stop_event.is_set() or self.close_event.is_set():
                return
            self.wait_if_paused()
            self._save_runtime_progress()
            time.sleep(0.1)

    def wait_if_paused(self) -> None:
        pause_announced = self.state.status == "Paused"
        while (
            self.pause_event.is_set()
            and not self.stop_event.is_set()
            and not self.close_event.is_set()
        ):
            if not pause_announced:
                self.state.status = "Paused"
                self.emit("status", {"status": "Paused"})
                self._save_runtime_progress(force=True)
                pause_announced = True
            else:
                self._save_runtime_progress()
            time.sleep(0.2)
        if (
            not self.stop_event.is_set()
            and not self.close_event.is_set()
            and self.processing_event.is_set()
            and self.state.status == "Paused"
        ):
            self.state.status = "Running"
            self.emit("status", {"status": "Running"})

    @staticmethod
    def default_managed_browser_profile_root() -> Path:
        """Return VibraPilot's durable application-owned browser-profile root."""
        if os.environ.get("VIB_TOOLS_DATA_DIR"):
            return APP_DATA_DIR / "BrowserProfiles"
        if sys.platform.startswith("win"):
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                return (
                    Path(base).expanduser().resolve()
                    / "Vib Tools"
                    / "VibraPilot"
                    / "BrowserProfiles"
                )
        return APP_DATA_DIR / "BrowserProfiles"

    @staticmethod
    def _normalized_profile_path(path: Path) -> str:
        try:
            resolved = path.expanduser().resolve(strict=False)
        except Exception:
            resolved = path.expanduser().absolute()
        return str(resolved).replace("\\", "/").rstrip("/").casefold()

    @classmethod
    def validate_managed_browser_profile_path(cls, path: Path) -> None:
        """Reject the operator's everyday Chrome User Data tree."""
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return
        candidate = cls._normalized_profile_path(path)
        chrome_roots = (
            Path(local_app_data) / "Google" / "Chrome" / "User Data",
            Path(local_app_data) / "Google" / "Chrome Beta" / "User Data",
            Path(local_app_data) / "Google" / "Chrome Dev" / "User Data",
            Path(local_app_data) / "Google" / "Chrome SxS" / "User Data",
        )
        for root in chrome_roots:
            normalized_root = cls._normalized_profile_path(root)
            if candidate == normalized_root or candidate.startswith(normalized_root + "/"):
                raise ValueError(
                    "VibraPilot cannot use your everyday Google Chrome User Data profile. "
                    "Leave Persistent User Data Directory blank for the managed profile, "
                    "or choose a separate automation-only directory."
                )

    @classmethod
    def resolve_persistent_user_data_dir(
        cls, settings: dict[str, Any], slot_id: int
    ) -> Path:
        """Resolve the stable User Data Directory claimed by one persistent Task."""
        raw = str(
            settings.get(
                "persistent_user_data_dir",
                DEFAULT_SETTINGS["persistent_user_data_dir"],
            )
        ).strip()
        if raw:
            base = Path(raw).expanduser()
            if not base.is_absolute():
                base = APP_DATA_DIR / base
        else:
            base = cls.default_managed_browser_profile_root()
        if bool(
            settings.get(
                "dedicated_profile_per_task",
                DEFAULT_SETTINGS["dedicated_profile_per_task"],
            )
        ):
            base = base / f"slot_{int(slot_id)}"
        cls.validate_managed_browser_profile_path(base)
        return base.resolve()

    def _migrate_legacy_managed_profile_if_needed(self, target: Path) -> bool:
        """Move only a legacy VibraPilot profile into the managed root when safe."""
        raw = str(
            self.settings.get(
                "persistent_user_data_dir",
                DEFAULT_SETTINGS["persistent_user_data_dir"],
            )
        ).strip()
        if raw or os.environ.get("VIB_TOOLS_DATA_DIR"):
            return False
        legacy = APP_DATA_DIR / "BrowserProfiles"
        if bool(
            self.settings.get(
                "dedicated_profile_per_task",
                DEFAULT_SETTINGS["dedicated_profile_per_task"],
            )
        ):
            legacy = legacy / f"slot_{self.state.slot_id}"
        try:
            if legacy.resolve() == target.resolve() or not legacy.exists() or target.exists():
                return False
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy), str(target))
            return True
        except Exception as exc:
            raise RuntimeError(
                f"Legacy VibraPilot browser profile could not be migrated from {legacy} to {target}: {exc}"
            ) from exc

    def _capture_browser_foundation_diagnostics(
        self,
        *,
        requested_launch_kwargs: dict[str, Any],
        effective_launch_kwargs: dict[str, Any],
        user_data_dir: Path | None,
        fallback_used: bool,
        fallback_reason: str,
    ) -> None:
        """Capture non-fatal browser identity/environment evidence."""
        if self.context is None or self.active_page is None:
            return
        try:
            record = build_browser_diagnostics(
                slot_id=self.state.slot_id, settings=self.settings,
                requested_launch_kwargs=requested_launch_kwargs,
                effective_launch_kwargs=effective_launch_kwargs,
                context=self.context, page=self.active_page,
                user_data_dir=user_data_dir,
                fallback_used=fallback_used, fallback_reason=fallback_reason,
                persistent_context=self.persistent_context_mode,
            )
            self.browser_launch_diagnostics = record
            timestamped, _latest = persist_browser_diagnostics(
                LOGS_DIR, self.state.slot_id, record
            )
            self.log(browser_diagnostics_summary(record))
            for warning in browser_diagnostics_warnings(record):
                self.log(warning, "WARNING")
            self.log(f"Browser diagnostics evidence saved: {timestamped}")
        except Exception as exc:
            self.log(f"Browser diagnostics could not be collected: {exc}", "WARNING")

    def launch_browser(self) -> None:
        from playwright.sync_api import sync_playwright

        # v1.0.6.32 defense-in-depth prerequisite gate. UI preflight is not
        # authoritative because Chrome can be removed between the click and worker launch.
        require_google_chrome()

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
            parsed_extra_args = shlex.split(extra_args, posix=(os.name != "nt"))
            forbidden_prefixes = (
                "--no-sandbox",
                "--disable-sandbox",
                "--disable-setuid-sandbox",
                "--load-extension",
                "--disable-extensions-except",
                "--user-data-dir",
            )
            for argument in parsed_extra_args:
                lowered = str(argument).strip().lower()
                if any(
                    lowered == prefix or lowered.startswith(prefix + "=")
                    for prefix in forbidden_prefixes
                ):
                    raise RuntimeError(
                        "Chrome-only runtime policy blocks the browser argument "
                        f"{argument!r}. Sandbox, managed profiles and Chromium "
                        "extension side-loading cannot be overridden."
                    )
            browser_args.extend(parsed_extra_args)

        # v1.0.6.31: unpacked extension side-loading previously required
        # Playwright Chromium. Chrome-only policy keeps Chrome's normal extension
        # subsystem enabled but disables VibraPilot's explicit Chromium side-load mode.
        extensions_enabled = False

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
            "chromium_sandbox": True,
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

        if bool(
            self.settings.get("accept_downloads", DEFAULT_SETTINGS["accept_downloads"])
        ):
            dl_dir = ensure_task_download_directory(
                self.settings, self.state.slot_id, APP_DATA_DIR
            )
            launch_args["downloads_path"] = str(dl_dir)

        traces_dir_text = str(
            self.settings.get("traces_dir", DEFAULT_SETTINGS["traces_dir"])
        ).strip()
        if traces_dir_text:
            traces_dir = Path(traces_dir_text).expanduser()
            if not traces_dir.is_absolute():
                traces_dir = LOGS_DIR / traces_dir
            traces_dir.mkdir(parents=True, exist_ok=True)
            launch_args["traces_dir"] = str(traces_dir.resolve())

        # v1.0.6.31 browser identity is not user-selectable. Playwright's
        # branded Chrome channel is the only accepted launch target.
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
            if bool(
                self.settings.get(
                    "persist_profile_between_runs",
                    DEFAULT_SETTINGS["persist_profile_between_runs"],
                )
            ):
                user_data_dir = self.resolve_persistent_user_data_dir(
                    self.settings, self.state.slot_id
                )
                if self._migrate_legacy_managed_profile_if_needed(user_data_dir):
                    self.log(
                        f"Legacy VibraPilot browser profile migrated to {user_data_dir}."
                    )
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
                    self.temporary_profile_dir = user_data_dir

            self.validate_managed_browser_profile_path(user_data_dir)
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
            requested_persistent_args = dict(persistent_args)
            effective_persistent_args = dict(persistent_args)
            persistent_error: Exception | None = None
            try:
                self.context = self.playwright.chromium.launch_persistent_context(
                    str(user_data_dir.resolve()),
                    **persistent_args,
                )
            except Exception as exc:
                persistent_error = exc

            if self.context is not None:
                self.browser = self.context.browser
                self.log(
                    f"Persistent Google Chrome context launched for task {self.state.slot_id}."
                )
            else:
                policy = str(
                    self.settings.get(
                        "profile_lock_policy",
                        DEFAULT_SETTINGS["profile_lock_policy"],
                    )
                ).strip().lower()
                if policy != "fallback_ephemeral":
                    if persistent_error is not None:
                        raise RuntimeError(
                            "Google Chrome persistent context could not be opened. "
                            "VibraPilot v1.0.6.31 does not fall back to Chromium."
                        ) from persistent_error
                    raise RuntimeError("Google Chrome persistent context could not be opened.")
                self.log(
                    "Persistent Google Chrome context could not be opened; falling back "
                    "to an ephemeral Google Chrome context without changing browser engine.",
                    "WARNING",
                )
                self.persistent_context_mode = False
                self.context = None
                self.browser = None
                ephemeral_args = dict(launch_args)
                try:
                    self.browser = self.playwright.chromium.launch(**ephemeral_args)
                except Exception as exc:
                    raise RuntimeError(
                        "Google Chrome could not be opened. VibraPilot v1.0.6.31 "
                        "does not fall back to Chromium."
                    ) from exc
                effective_persistent_args = dict(ephemeral_args)

            self.new_context(initial_url=startup_url)
            self._capture_browser_foundation_diagnostics(
                requested_launch_kwargs=requested_persistent_args,
                effective_launch_kwargs=effective_persistent_args,
                user_data_dir=(user_data_dir if self.persistent_context_mode else None),
                fallback_used=False,
                fallback_reason="",
            )
            return

        requested_launch_args = dict(launch_args)
        effective_launch_args = dict(launch_args)
        try:
            self.browser = self.playwright.chromium.launch(**launch_args)
            self.log(
                "Fresh Google Chrome launched; authenticated session will be retained for this task."
            )
        except Exception as exc:
            raise RuntimeError(
                "Google Chrome could not be opened. VibraPilot v1.0.6.31 "
                "does not fall back to Chromium."
            ) from exc
        self.new_context(initial_url=startup_url)
        self._capture_browser_foundation_diagnostics(
            requested_launch_kwargs=requested_launch_args,
            effective_launch_kwargs=effective_launch_args,
            user_data_dir=None,
            fallback_used=False,
            fallback_reason="",
        )

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
                self._clear_pending_file_chooser(
                    "Pending browser file selection was cancelled because the browser context changed.",
                    log_event=True,
                )
                self._context_transitioning = True
                try:
                    self.context.close()
                except Exception:
                    pass
                finally:
                    self._context_transitioning = False
                self._lifecycle_page_ids.clear()
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

        def attach_page_events(page, *, consider_ownership: bool = False) -> None:
            if page is None:
                return
            page_id = id(page)
            if page_id in self._configured_page_ids:
                if consider_ownership and self._should_adopt_new_page(page):
                    self._adopt_active_page(page, reason="new browser page", clear_session=True)
                return
            self._configured_page_ids.add(page_id)
            self._attach_page_lifecycle_events(page)

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

            def frame_navigated_handler(frame):
                try:
                    if frame is not page.main_frame:
                        return
                except Exception:
                    pass
                if self._should_adopt_new_page(page):
                    self._adopt_active_page(
                        page, reason="browser page navigation", clear_session=True
                    )

            page.on("framenavigated", frame_navigated_handler)

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
            page.on("download", self._handle_download)
            page.on("filechooser", lambda chooser, attached_page=page: self._handle_file_chooser(attached_page, chooser))
            if consider_ownership and self._should_adopt_new_page(page):
                self._adopt_active_page(page, reason="new browser page", clear_session=True)

        self._attach_browser_lifecycle_events()
        self.context.on(
            "page",
            lambda page: attach_page_events(page, consider_ownership=True),
        )
        pages = list(self.context.pages)
        if using_precreated_persistent_context and pages:
            # Restored pages existed before the Context page listener, so every
            # live page gets lifecycle/event wiring before one deterministic owner
            # is selected.
            for restored_page in pages:
                attach_page_events(restored_page, consider_ownership=False)
            selected_page = self._select_preferred_page(pages)
            if selected_page is not None:
                self._adopt_active_page(
                    selected_page, reason="persistent startup selection", clear_session=False
                )
        else:
            # New pages are configured through the BrowserContext page event.
            created_page = self.context.new_page()
            attach_page_events(created_page, consider_ownership=False)
            self._adopt_active_page(created_page, reason="new context page", clear_session=False)

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
        old_page = self.active_page
        try:
            if old_page and not old_page.is_closed():
                current_url = old_page.url or current_url
        except Exception:
            pass
        # This is an intentional maintenance transition. Create/adopt the
        # replacement before closing the old page so lifecycle callbacks cannot
        # temporarily classify the managed browser as externally closed.
        self._context_transitioning = True
        try:
            replacement = self.context.new_page()
            self._adopt_active_page(
                replacement, reason="planned page reopen", clear_session=True
            )
            if current_url.startswith(("http://", "https://")):
                self.safe_goto(replacement, current_url)
            try:
                if old_page and old_page is not replacement and not old_page.is_closed():
                    old_page.close()
            except Exception:
                pass
        finally:
            self._context_transitioning = False

    def maybe_recycle_context(self) -> bool:
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
            return True

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
            old_initial_url = self.initial_url
            self._clear_pending_file_chooser(
                "Pending browser file selection was cancelled because the browser context recycled.",
                log_event=True,
            )
            self._context_transitioning = True
            try:
                try:
                    if self.context:
                        self.context.close()
                except Exception:
                    pass
                self.context = None
                self.browser = None
                self.active_page = None
                self.initial_url = current_url if restore_page else ""
                self.launch_browser()
            finally:
                self.initial_url = old_initial_url
                self._context_transitioning = False
            # The recycle is an internal maintenance transition, not a manual
            # Browser Close. Session-required workflows must re-verify against
            # the relaunched managed profile; sessionless workflows do not enter
            # the Core Login Verification path at all.
            self.login_verified_event.clear()
            if self.workflow_requires_session():
                return self.refresh_login_verification(
                    force_emit=True, allow_while_processing=True
                )
            return True

        self.new_context(
            storage_state=storage_state,
            initial_url=current_url if restore_page else "",
        )
        self.login_verified_event.clear()
        if self.workflow_requires_session():
            return self.refresh_login_verification(
                force_emit=True, allow_while_processing=True
            )
        return True

    def _process_generic_workflow_item(self, index: int, item: TaskItem) -> None:
        """Run one item for a workflow that does not provide specialized orchestration."""
        max_retry_raw = self.workflow_settings_values.get(
            "max_retry",
            self.settings.get("max_retry_per_item", DEFAULT_SETTINGS["max_retry_per_item"]),
        )
        try:
            max_retry = max(0, int(max_retry_raw))
        except (TypeError, ValueError):
            max_retry = max(0, int(DEFAULT_SETTINGS["max_retry_per_item"]))
        item.status = "processing"
        self.log(
            f"Workflow {self._workflow_manager.active_workflow_id} item {index + 1} processing started."
        )
        self.set_workflow_step("Processing item")
        self._save_runtime_item(index, item, "Workflow item processing started")
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
            try:
                result = self.execute_workflow_item(item)
                item.status = "success"
                item.result = str(result)
                item.message = "Workflow item completed"
                self.state.manual_review_required = False
                self.state.success_count += 1
                return
            except Exception as exc:
                item.message = str(exc)
                try:
                    decision = self.workflow_error_decision(exc)
                except Exception as decision_exc:
                    item.status = "failed"
                    item.message = (
                        f"Workflow error handling failed closed: {decision_exc}; original error: {exc}"
                    )
                    self.state.failed_count += 1
                    self.log(item.message, "ERROR")
                    return

                if decision == "MANUAL_REVIEW":
                    item.status = "interrupted"
                    self.state.manual_review_required = True
                    item.message = f"Manual review required: {exc}"
                    self.save_checkpoint()
                    self.log(item.message, "ERROR")
                    return
                if decision == "STOP_TASK":
                    item.status = "blocked"
                    item.message = f"Workflow blocked the Task: {exc}"
                    self.log(item.message, "ERROR")
                    return
                if decision == "FAIL_ITEM":
                    item.status = "failed"
                    self.state.manual_review_required = False
                    self.state.failed_count += 1
                    self.log(
                        f"Workflow item {index + 1} failed closed on attempt {attempt}: {exc}",
                        "WARNING",
                    )
                    return

                # RETRY is the only decision that can reach this point.
                if attempt > max_retry:
                    item.status = "failed"
                    self.state.manual_review_required = False
                    self.state.failed_count += 1
                    return
                self.prepare_workflow_retry()
                try:
                    retry_min = max(
                        0.0,
                        float(
                            self.workflow_settings_values.get(
                                "retry_delay_min",
                                self.settings.get("retry_delay_min", DEFAULT_SETTINGS["retry_delay_min"]),
                            )
                        ),
                    )
                    retry_max = max(
                        retry_min,
                        float(
                            self.workflow_settings_values.get(
                                "retry_delay_max",
                                self.settings.get("retry_delay_max", DEFAULT_SETTINGS["retry_delay_max"]),
                            )
                        ),
                    )
                    multiplier = max(
                        1.0,
                        float(
                            self.workflow_settings_values.get(
                                "backoff_multiplier",
                                self.settings.get("backoff_multiplier", DEFAULT_SETTINGS["backoff_multiplier"]),
                            )
                        ),
                    )
                except (TypeError, ValueError):
                    retry_min = max(0.0, float(DEFAULT_SETTINGS["retry_delay_min"]))
                    retry_max = max(retry_min, float(DEFAULT_SETTINGS["retry_delay_max"]))
                    multiplier = max(1.0, float(DEFAULT_SETTINGS["backoff_multiplier"]))
                delay = min(retry_max, retry_min * (multiplier ** (attempt - 1)))
                self.interruptible_sleep(delay)
                attempt += 1

    def process_item(self, index: int, item: TaskItem) -> None:
        """Delegate specialized item orchestration to the active workflow when supplied."""
        runtime = self._workflow_runtime()
        hook = getattr(runtime, "process_item", None)
        if callable(hook):
            hook(index, item)
            return
        self._process_generic_workflow_item(index, item)

    def _register_send_click_attempt(self) -> None:
        """Reserve a Send attempt immediately before Playwright invokes click()."""
        if self.run_send_count >= self.run_send_limit:
            raise TestSendLimitReached(
                f"Maximum Test Mode send limit reached ({self.run_send_limit} Send clicks for this run)."
            )
        self.run_send_count += 1
        self.state.send_limit_used = self.run_send_count
        # This callback runs immediately before Playwright invokes click().  Persist a
        # conservative manual-review marker first so a hard process crash after this
        # point can never resume by automatically retrying a possibly-sent recipient.
        self.state.manual_review_required = True
        index = max(0, int(self.state.current_index))
        if self.runtime_store is not None and self.state.run_id and index < self.state.total:
            current = self.state.items[index]
            current.status = "interrupted"
            current.message = (
                "Send click attempt started; a definitive success/rejection is not yet "
                "persisted. Manual review is required after an unexpected process stop."
            )
            self.runtime_store.persist_item_result_progress(
                run_id=self.state.run_id,
                item_index=index,
                item=current,
                result_row=self.report_row(current, current.message, item_index=index),
                current_index=self.state.current_index,
                total=self.state.total,
                success_count=self.state.success_count,
                failed_count=self.state.failed_count,
                send_limit_used=self.run_send_count,
                task_status=self.state.status,
                manual_review_required=True,
                updated_at=now_str(),
                target_url=self.state.target_url,
            )
            self.last_autosave_at = time.monotonic()
        else:
            self._save_runtime_progress(force=True)
        self.emit(
            "send_limit", {"used": self.run_send_count, "limit": self.run_send_limit}
        )

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

    def report_row(self, item: TaskItem, message: str, item_index: int | None = None) -> dict[str, Any]:
        return {
            "timestamp": now_str(),
            "slot_id": self.state.slot_id,
            "workflow_id": self._workflow_manager.active_workflow_id or "",
            "email": item.email,
            "status": item.status,
            "message": message,
            "attempts": item.attempts,
            "target_url": self.state.target_url,
            "result": item.result,
            "run_id": self.state.run_id,
            "item_index": self.state.current_index if item_index is None else int(item_index),
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
        """Persist crash-safe task state; SQLite is authoritative, JSON is compatibility output."""
        self._save_runtime_progress(force=True)
        if self.runtime_store is not None and self.state.run_id:
            for index, item in enumerate(self.state.items):
                self.runtime_store.save_item(self.state.run_id, index, item)
        data = {
            "schema_version": 2,
            "run_id": self.state.run_id,
            "slot_id": self.state.slot_id,
            "target_url": self.state.target_url,
            "source_file": self.state.source_file,
            "source_fingerprint": self.state.source_fingerprint,
            "current_index": self.state.current_index,
            "success_count": self.state.success_count,
            "failed_count": self.state.failed_count,
            "send_limit_used": self.run_send_count,
            "manual_review_required": self.state.manual_review_required,
            "items": [item.__dict__ for item in self.state.items],
            "saved_at": now_str(),
        }
        path = APP_DATA_DIR / f"slot_{self.state.slot_id}_checkpoint.json"
        temp = path.with_suffix(path.suffix + ".tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)

    def save_failed(self, items: list[TaskItem] | None = None) -> None:
        # v1.0.6.30 safety contract: failed user data is always preserved.
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
        self._clear_pending_file_chooser(
            "Pending browser file selection was cancelled because the Task browser closed.",
            log_event=False,
        )
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
