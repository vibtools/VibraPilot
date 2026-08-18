from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import (
    DEFAULT_SETTINGS,
    SettingsManager,
    _PLAYWRIGHT_BACKGROUND_THROTTLING_ARGS,
    effective_ignored_default_args,
)


def test_v2_default_disables_background_throttling():
    assert DEFAULT_SETTINGS["browser_runtime_policy_version"] == 2
    assert DEFAULT_SETTINGS["background_throttling_enabled"] is False


def test_legacy_policy_is_migrated_once_to_production_safe_background(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"browser_runtime_policy_version": 1, "background_throttling_enabled": True}),
        encoding="utf-8",
    )
    manager = SettingsManager(path)
    assert manager.data["browser_runtime_policy_version"] == 2
    assert manager.data["background_throttling_enabled"] is False

    manager.data["background_throttling_enabled"] = True
    manager.save()
    reloaded = SettingsManager(path)
    assert reloaded.data["browser_runtime_policy_version"] == 2
    assert reloaded.data["background_throttling_enabled"] is True


def test_background_throttling_off_keeps_playwright_anti_throttle_defaults_enabled():
    settings = dict(DEFAULT_SETTINGS)
    settings["background_throttling_enabled"] = False
    ignored = effective_ignored_default_args(settings, extensions_enabled=False)
    for arg in _PLAYWRIGHT_BACKGROUND_THROTTLING_ARGS:
        assert arg not in ignored
