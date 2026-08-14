from __future__ import annotations

import hashlib
import json
from pathlib import Path

from vibrapilot.backend import DEFAULT_SETTINGS, effective_ignored_default_args


ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.19_chrome_webstore_extension_install_fix_scope.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_normal_browser_mode_keeps_chrome_extension_service_enabled():
    settings = dict(DEFAULT_SETTINGS)
    settings["extensions_enabled"] = False
    ignored = effective_ignored_default_args(settings, extensions_enabled=False)
    assert "--disable-extensions" in ignored


def test_legacy_extension_argument_does_not_disable_normal_chrome_extension_service():
    settings = dict(DEFAULT_SETTINGS)
    ignored = effective_ignored_default_args(settings, extensions_enabled=True)
    assert ignored.count("--disable-extensions") == 1


def test_download_configuration_and_capability_runtime_are_frozen():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["preserve_downloads"] is True
    assert DEFAULT_SETTINGS["accept_downloads"] is True
    expected = scope["frozen_file_sha256"]["src/vibrapilot/browser_capabilities.py"]
    assert _sha256(ROOT / "src" / "vibrapilot" / "browser_capabilities.py") == expected


def test_fix_scope_changes_only_backend_runtime():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["allowed_runtime_source_changes"] == ["src/vibrapilot/backend.py"]
    assert scope["actual_runtime_source_changes"] == ["src/vibrapilot/backend.py"]
    assert scope["no_policy_change"] is True
    assert scope["no_profile_change"] is True
    assert scope["no_settings_key_change"] is True
    assert scope["no_new_dependency"] is True
