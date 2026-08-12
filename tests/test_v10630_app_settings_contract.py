from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
QT = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
BACKEND = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")


def test_global_target_url_is_blank_and_storage_controls_exist():
    assert DEFAULTS["default_target_url"] == ""
    assert DEFAULTS["export_path"] == ""
    assert DEFAULTS["saved_logs_path"] == ""
    assert '"Storage & Output": ["export_path", "saved_logs_path", "downloads_path"]' in QT


def test_safety_controls_are_always_on_and_not_user_toggle_settings():
    assert DEFAULTS["save_failed_data"] is True
    assert DEFAULTS["save_unprocessed_data_on_close"] is True
    assert DEFAULTS["confirm_before_close_while_running"] is True
    settings_method = QT.split('def make_settings_page', 1)[1].split('def make_about_page', 1)[0]
    for hidden in ("save_failed_data", "save_unprocessed_data_on_close", "confirm_before_close_while_running", "license_recheck_minutes", "request_timeout", "default_target_url"):
        assert f'"{hidden}"' not in settings_method
    close_method = QT.split('def closeEvent', 1)[1].split('def main', 1)[0]
    assert 'if running:' in close_method
    assert 'confirm_before_close_while_running' not in close_method
    save_failed = BACKEND.split('def save_failed', 1)[1].split('def save_unprocessed', 1)[0]
    assert 'save_failed_data' not in save_failed
