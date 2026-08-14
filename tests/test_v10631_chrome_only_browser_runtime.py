from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _v10632_satisfy_new_chrome_prerequisite_guard(monkeypatch):
    """Keep historical v1.0.6.31 launch-policy tests focused on fallback semantics.

    v1.0.6.32 adds a separate, independently tested installed-Chrome prerequisite
    guard before Playwright startup.  These historical tests inject a satisfied
    prerequisite so they continue exercising the v1.0.6.31 launch behavior.
    """
    monkeypatch.setattr("src.vibrapilot.backend.require_google_chrome", lambda: object())


def test_v10631_source_defaults_are_chrome_only_and_secure():
    defaults = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
    assert defaults["browser_runtime_policy_version"] == 1
    assert defaults["use_chrome_channel"] is True
    assert defaults["allow_chromium_fallback"] is False
    assert defaults["browser_executable_path"] == ""
    assert defaults["sandbox_enabled"] is True
    assert defaults["http_cache_enabled"] is True
    assert defaults["extensions_enabled"] is False


def test_v10631_legacy_settings_migrate_to_mandatory_chrome_policy(tmp_path):
    from src.vibrapilot.backend import SettingsManager

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "use_chrome_channel": False,
                "allow_chromium_fallback": True,
                "browser_executable_path": r"C:\\Chromium\\chrome.exe",
                "sandbox_enabled": False,
                "http_cache_enabled": False,
                "extensions_enabled": True,
                "extension_paths": r"C:\\keep\\historical-extension",
            }
        ),
        encoding="utf-8",
    )
    settings = SettingsManager(path)
    assert settings.get("browser_runtime_policy_version") == 1
    assert settings.get("use_chrome_channel") is True
    assert settings.get("allow_chromium_fallback") is False
    assert settings.get("browser_executable_path") == ""
    assert settings.get("sandbox_enabled") is True
    assert settings.get("http_cache_enabled") is True
    assert settings.get("extensions_enabled") is False
    assert settings.get("extension_paths") == r"C:\\keep\\historical-extension"


def test_v10631_mandatory_policy_cannot_be_bypassed_by_current_settings_file(tmp_path):
    from src.vibrapilot.backend import SettingsManager

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "browser_runtime_policy_version": 1,
                "use_chrome_channel": False,
                "allow_chromium_fallback": True,
                "browser_executable_path": r"C:\\Other\\browser.exe",
                "sandbox_enabled": False,
                "extensions_enabled": True,
                "http_cache_enabled": False,
            }
        ),
        encoding="utf-8",
    )
    settings = SettingsManager(path)
    assert settings.get("use_chrome_channel") is True
    assert settings.get("allow_chromium_fallback") is False
    assert settings.get("browser_executable_path") == ""
    assert settings.get("sandbox_enabled") is True
    assert settings.get("extensions_enabled") is False
    # HTTP cache is a normal user setting after the one-time v1.0.6.31 migration.
    assert settings.get("http_cache_enabled") is False


def test_v10631_browser_settings_ui_cannot_select_engine_fallback_or_sandbox_off():
    from tests.test_browser_settings_wiring import _browser_ui_keys

    keys = _browser_ui_keys()
    for forbidden in (
        "browser_executable_path",
        "use_chrome_channel",
        "allow_chromium_fallback",
        "sandbox_enabled",
        "extensions_enabled",
        "extension_paths",
    ):
        assert forbidden not in keys


def test_v10631_backend_contains_no_chromium_launch_escape_paths():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert 'launch_args["channel"] = "chrome"' in source
    assert 'launch_args["channel"] = "chromium"' not in source
    assert 'fallback_args.pop("channel", None)' not in source
    assert 'launch_args.pop("channel", None)' not in source
    assert 'launch_args["executable_path"]' not in source
    assert '"chromium_sandbox": True' in source


def test_v10631_resource_routing_defaults_do_not_disable_http_cache():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    route_start = source.index("route_required = (")
    route_end = source.index("if route_required:", route_start)
    route_source = source[route_start:route_end]
    assert '"block_images"' in route_source
    assert '"block_fonts"' in route_source
    assert '"block_media"' in route_source
    assert '"http_cache_enabled"' in route_source
    defaults = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
    assert defaults["http_cache_enabled"] is True


def test_v10631_chrome_runtime_discovery_accepts_only_google_chrome(tmp_path):
    from src.vibrapilot.chrome_runtime import discover_google_chrome

    chrome = tmp_path / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_bytes(b"stub")

    result = discover_google_chrome(
        candidate_paths=[("test", chrome)],
        metadata_reader=lambda _path: ("Google Chrome", "151.0.0.0"),
        platform_name="nt",
    )
    assert result.available is True
    assert result.status == "available"
    assert result.product_name == "Google Chrome"
    assert result.version == "151.0.0.0"
    assert result.executable_path == chrome.resolve()


def test_v10631_chrome_runtime_rejects_non_google_product(tmp_path):
    from src.vibrapilot.chrome_runtime import discover_google_chrome

    chrome = tmp_path / "chrome.exe"
    chrome.write_bytes(b"stub")
    result = discover_google_chrome(
        candidate_paths=[("test", chrome)],
        metadata_reader=lambda _path: ("Chromium", "151.0"),
        platform_name="nt",
    )
    assert result.available is False
    assert result.status == "not_found"


def test_v10631_diagnostics_marks_non_google_runtime_as_policy_violation():
    from src.vibrapilot.browser_diagnostics import browser_runtime_policy_status

    assert browser_runtime_policy_status("google_chrome") == "compliant"
    assert browser_runtime_policy_status("google_chrome_channel") == "compliant"
    assert browser_runtime_policy_status("playwright_chromium") == "violation"
    assert browser_runtime_policy_status("playwright_chromium_fallback") == "violation"
    assert browser_runtime_policy_status("custom_chromium_executable") == "violation"


def _worker_for_launch(tmp_path, **overrides):
    import queue
    import threading
    from src.vibrapilot.backend import DEFAULT_SETTINGS, AutomationWorker, TaskState

    settings = dict(DEFAULT_SETTINGS)
    settings.update(
        {
            "use_persistent_context": False,
            "accept_downloads": False,
            "traces_dir": "",
            "persistent_user_data_dir": str(tmp_path / "profile"),
            **overrides,
        }
    )
    return AutomationWorker(
        TaskState(slot_id=1, target_url="https://example.test/"),
        settings,
        queue.Queue(),
        threading.Event(),
        threading.Event(),
        "https://example.test/",
    )


class _FakeChromium:
    def __init__(self):
        self.launch_calls = []
        self.persistent_calls = []
        self.launch_error = None
        self.persistent_error = None
        self.browser_result = object()
        self.context_result = type("Ctx", (), {"browser": object()})()

    def launch(self, **kwargs):
        self.launch_calls.append(dict(kwargs))
        if self.launch_error:
            raise self.launch_error
        return self.browser_result

    def launch_persistent_context(self, user_data_dir, **kwargs):
        self.persistent_calls.append((user_data_dir, dict(kwargs)))
        if self.persistent_error:
            raise self.persistent_error
        return self.context_result


class _FakePlaywright:
    def __init__(self, chromium):
        self.chromium = chromium


def test_v10631_fresh_launch_failure_does_not_retry_chromium(tmp_path, monkeypatch):
    worker = _worker_for_launch(tmp_path)
    fake = _FakeChromium()
    fake.launch_error = RuntimeError("chrome unavailable")
    worker.playwright = _FakePlaywright(fake)
    monkeypatch.setattr(worker, "new_context", lambda **_kwargs: None)
    monkeypatch.setattr(worker, "_capture_browser_foundation_diagnostics", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="does not fall back to Chromium"):
        worker.launch_browser()

    assert len(fake.launch_calls) == 1
    assert fake.launch_calls[0]["channel"] == "chrome"
    assert fake.launch_calls[0]["chromium_sandbox"] is True


def test_v10631_persistent_launch_failure_does_not_retry_chromium(tmp_path, monkeypatch):
    worker = _worker_for_launch(
        tmp_path,
        use_persistent_context=True,
        profile_lock_policy="fail",
        persist_profile_between_runs=True,
        dedicated_profile_per_task=False,
    )
    fake = _FakeChromium()
    fake.persistent_error = RuntimeError("persistent chrome unavailable")
    worker.playwright = _FakePlaywright(fake)
    monkeypatch.setattr(worker, "new_context", lambda **_kwargs: None)
    monkeypatch.setattr(worker, "_capture_browser_foundation_diagnostics", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="does not fall back to Chromium"):
        worker.launch_browser()

    assert len(fake.persistent_calls) == 1
    assert fake.persistent_calls[0][1]["channel"] == "chrome"
    assert fake.persistent_calls[0][1]["chromium_sandbox"] is True
    assert fake.launch_calls == []


def test_v10631_profile_ephemeral_fallback_keeps_google_chrome_engine(tmp_path, monkeypatch):
    worker = _worker_for_launch(
        tmp_path,
        use_persistent_context=True,
        profile_lock_policy="fallback_ephemeral",
        persist_profile_between_runs=True,
        dedicated_profile_per_task=False,
    )
    fake = _FakeChromium()
    fake.persistent_error = RuntimeError("profile locked")
    worker.playwright = _FakePlaywright(fake)
    monkeypatch.setattr(worker, "new_context", lambda **_kwargs: None)
    monkeypatch.setattr(worker, "_capture_browser_foundation_diagnostics", lambda **_kwargs: None)

    worker.launch_browser()

    assert len(fake.persistent_calls) == 1
    assert len(fake.launch_calls) == 1
    assert fake.persistent_calls[0][1]["channel"] == "chrome"
    assert fake.launch_calls[0]["channel"] == "chrome"
    assert fake.launch_calls[0]["chromium_sandbox"] is True


def test_v10631_settings_set_cannot_turn_off_mandatory_browser_policy(tmp_path):
    from src.vibrapilot.backend import SettingsManager

    settings = SettingsManager(tmp_path / "settings.json")
    settings.set("sandbox_enabled", False)
    settings.set("allow_chromium_fallback", True)
    settings.set("use_chrome_channel", False)
    settings.set("browser_executable_path", r"C:\\Other\\browser.exe")
    settings.set("extensions_enabled", True)

    assert settings.get("sandbox_enabled") is True
    assert settings.get("allow_chromium_fallback") is False
    assert settings.get("use_chrome_channel") is True
    assert settings.get("browser_executable_path") == ""
    assert settings.get("extensions_enabled") is False


def test_v10631_chrome_validation_fails_closed_without_product_metadata(tmp_path):
    from src.vibrapilot.chrome_runtime import validate_google_chrome_executable

    chrome = tmp_path / "Google" / "Chrome" / "Application" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_bytes(b"MZ")

    assert validate_google_chrome_executable(chrome, "") is False


@pytest.mark.parametrize(
    "unsafe_argument",
    [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--load-extension=C:\\tmp\\extension",
        "--disable-extensions-except=C:\\tmp\\extension",
        "--user-data-dir=C:\\OtherProfile",
    ],
)
def test_v10631_additional_args_cannot_bypass_chrome_only_policy(tmp_path, monkeypatch, unsafe_argument):
    worker = _worker_for_launch(
        tmp_path,
        additional_chromium_args=unsafe_argument,
    )
    fake = _FakeChromium()
    worker.playwright = _FakePlaywright(fake)
    monkeypatch.setattr(worker, "new_context", lambda **_kwargs: None)
    monkeypatch.setattr(worker, "_capture_browser_foundation_diagnostics", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="Chrome-only runtime policy blocks"):
        worker.launch_browser()

    assert fake.launch_calls == []
    assert fake.persistent_calls == []
