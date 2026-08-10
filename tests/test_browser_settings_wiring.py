from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QT_PATH = ROOT / "src" / "vibrapilot" / "qt_app.py"
BACKEND_PATH = ROOT / "src" / "vibrapilot" / "backend.py"
DEFAULTS_PATH = ROOT / "config" / "settings.defaults.json"
SHARE_INVITE_PATH = ROOT / "src" / "vibrapilot" / "workflow" / "share_invite" / "workflow.py"


def _browser_groups() -> dict[str, list[str]]:
    tree = ast.parse(QT_PATH.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.AnnAssign)
        and isinstance(item.target, ast.Name)
        and item.target.id == "BROWSER_SETTING_GROUPS"
    )
    return ast.literal_eval(node.value)


def _browser_ui_keys() -> set[str]:
    return {key for keys in _browser_groups().values() for key in keys}


def _automation_worker_source() -> str:
    text = BACKEND_PATH.read_text(encoding="utf-8")
    tree = ast.parse(text)
    worker = next(
        item
        for item in tree.body
        if isinstance(item, ast.ClassDef) and item.name == "AutomationWorker"
    )
    return ast.get_source_segment(text, worker) or ""


def test_every_browser_ui_setting_has_a_real_runtime_consumer():
    runtime_source = BACKEND_PATH.read_text(encoding="utf-8")
    if SHARE_INVITE_PATH.is_file():
        runtime_source += "\n" + SHARE_INVITE_PATH.read_text(encoding="utf-8")
    missing = {
        key
        for key in _browser_ui_keys()
        if key != "browser_slot_default" and f'"{key}"' not in runtime_source
    }
    assert not missing, f"Browser Settings without backend/runtime consumer: {sorted(missing)}"


def test_browser_settings_are_grouped_as_advanced_master_controls():
    groups = _browser_groups()
    for required in (
        "Browser Engine & Binary",
        "Persistent Profile & Session",
        "Window & Display",
        "Locale & Region",
        "Permissions",
        "Downloads",
        "Navigation & DOM",
        "Identity & Proxy",
        "Resource Loading & Media",
        "Security & Network",
        "Extensions",
        "DevTools & Debugging",
        "Launch Arguments & Environment",
        "Performance",
        "Logging & Diagnostics",
        "Crash Recovery",
    ):
        assert required in groups


def test_api_request_timeout_is_not_misrepresented_as_browser_setting():
    ui = QT_PATH.read_text(encoding="utf-8")
    assert "request_timeout" not in _browser_ui_keys()
    assert '"request_timeout",' in ui
    assert "license/API validation requests" in ui


def test_saved_browser_settings_are_synchronized_to_active_workers():
    ui = QT_PATH.read_text(encoding="utf-8")
    backend = BACKEND_PATH.read_text(encoding="utf-8")
    assert "worker.settings = dict(self.settings.data)" in ui
    assert 'worker.control_queue.put(' in ui
    assert '("settings", {"settings": dict(self.settings.data)})' in ui
    assert 'if command == "settings":' in backend
    assert "self.context.set_default_navigation_timeout(" in backend
    assert "self.context.set_default_timeout(" in backend
    assert "self.context.set_offline(" in backend
    assert "self.context.set_extra_http_headers(" in backend
    assert "self.context.set_geolocation(" in backend
    assert "self.context.grant_permissions(" in backend


def test_resource_blocking_reads_live_worker_settings():
    backend = BACKEND_PATH.read_text(encoding="utf-8")
    route_start = backend.index("def route_handler(route):")
    route_end = backend.index("self.resource_route_handler = route_handler", route_start)
    block = backend[route_start:route_end]
    for key in ("block_images", "block_fonts", "block_media"):
        assert f'"{key}"' in block


def test_http_cache_control_is_real_and_reconfigures_routing():
    backend = BACKEND_PATH.read_text(encoding="utf-8")
    assert '"http_cache_enabled"' in backend
    assert 'self.context.unroute(' in backend
    assert 'self.resource_route_handler' in backend
    assert 'not bool(' in backend


def test_master_launch_controls_are_real_backend_inputs():
    backend = _automation_worker_source()
    for marker in (
        "launch_persistent_context",
        '"browser_executable_path"',
        '"persistent_user_data_dir"',
        '"gpu_enabled"',
        '"sandbox_enabled"',
        '"window_width"',
        '"window_position_x"',
        '"remote_debugging_port"',
        '"additional_chromium_args"',
        '"browser_env_json"',
        '"extensions_enabled"',
        '"background_throttling_enabled"',
        '"renderer_process_limit"',
        '"auto_restart_browser_on_crash"',
    ):
        assert marker in backend


def test_master_context_controls_are_real_backend_inputs():
    backend = _automation_worker_source()
    for marker in (
        '"viewport_width"',
        '"screen_width"',
        '"device_scale_factor"',
        '"locale"',
        '"timezone_id"',
        '"geolocation_enabled"',
        '"permission_notifications"',
        '"accept_downloads"',
        '"ignore_https_errors"',
        '"javascript_enabled"',
        '"color_scheme"',
        '"reduced_motion"',
        '"service_workers"',
        '"extra_http_headers_json"',
        '"record_har_enabled"',
        '"page_init_script_enabled"',
    ):
        assert marker in backend


def test_persistent_session_recycle_controls_are_wired():
    backend = _automation_worker_source()
    assert "storage_state(" in backend
    assert "indexed_db=preserve_indexeddb" in backend
    for key in (
        "preserve_cookies_on_recycle",
        "preserve_local_storage_on_recycle",
        "preserve_indexeddb_on_recycle",
        "persist_profile_cache",
        "restore_previous_session",
    ):
        assert f'"{key}"' in backend


def test_browser_logging_controls_are_not_ui_only():
    backend = _automation_worker_source()
    assert 'page.on("console"' in backend
    assert 'page.on("request"' in backend
    assert 'page.on("response"' in backend
    assert '"browser_console_logging"' in backend
    assert '"network_event_logging"' in backend
    assert '"record_har_path"' in backend
    assert '"crash_dumps_directory"' in backend


def test_navigation_places_app_settings_above_advanced_browser_settings():
    ui = QT_PATH.read_text(encoding="utf-8")
    marker = 'NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]'
    assert marker in ui
    assert '("App Settings", self.make_settings_page)' in ui
    assert '("Browser Settings", self.make_browser_settings_page)' in ui


def test_app_reset_does_not_reset_browser_settings():
    ui = QT_PATH.read_text(encoding="utf-8")
    start = ui.index("    def reset_settings(self) -> None:")
    end = ui.index("\n    # ---------- report ----------", start)
    block = ui[start:end]
    assert "self.settings.reset()" not in block
    assert "for key, widget in self.setting_widgets.items():" in block
    assert "Browser Settings were preserved" in block


def test_browser_settings_page_contains_only_editable_runtime_backed_controls():
    ui = QT_PATH.read_text(encoding="utf-8")
    assert "Runtime Browser Contract (Informational)" not in ui
    assert "Chrome Policy / Profile-managed Features (Informational)" not in ui
    for fake_key in (
        "safe_browsing_enabled",
        "password_manager_enabled",
        "autofill_enabled",
        "screen_color_depth",
        "platform_spoof",
        "origin_trials_enabled",
        "hardware_acceleration_enabled",
        "disable_image_font_media_loading",
    ):
        assert fake_key not in _browser_ui_keys()


def test_browser_settings_ui_refreshes_from_backend_values_after_save_reset_and_navigation():
    ui = QT_PATH.read_text(encoding="utf-8")
    assert "def refresh_browser_settings_widgets(self) -> None:" in ui
    assert ui.count("self.refresh_browser_settings_widgets()") >= 3
    assert 'elif name == "Browser Settings":' in ui
    assert "value = self.settings.get(key, DEFAULT_SETTINGS[key])" in ui


def test_playwright_default_arg_conflicts_are_resolved_in_backend():
    backend = BACKEND_PATH.read_text(encoding="utf-8")
    assert "def effective_ignored_default_args(" in backend
    assert '_PLAYWRIGHT_POPUP_BLOCKING_ARG = "--disable-popup-blocking"' in backend
    assert '_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG = "--disable-extensions"' in backend
    assert '"--disable-background-timer-throttling"' in backend
    assert 'extensions_enabled=extensions_enabled' in backend


def test_hidden_legacy_browser_aliases_are_migration_only():
    backend = BACKEND_PATH.read_text(encoding="utf-8")
    ui_keys = _browser_ui_keys()
    assert "hardware_acceleration_enabled" not in ui_keys
    assert "disable_image_font_media_loading" not in ui_keys
    assert 'self.data.pop("hardware_acceleration_enabled", None)' in backend
    assert 'self.data.pop("disable_image_font_media_loading", None)' in backend


def test_context_recycle_minutes_rejects_negative_ui_values():
    ui = QT_PATH.read_text(encoding="utf-8")
    assert '"browser_context_recycle_after_n_minutes": 0' in ui


def test_browser_settings_validate_conditional_controls_to_avoid_ui_only_values():
    qt = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "vibrapilot"
        / "qt_app.py"
    ).read_text(encoding="utf-8")
    assert "Window Position X and Y must both be -1 (automatic) or both be 0 or greater." in qt
    assert "Restore Previous Browser Session requires Persist Profile Between Runs." in qt

