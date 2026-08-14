from __future__ import annotations

import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_v10632_installer_policy_is_google_owned_https_and_not_user_configurable():
    from src.vibrapilot.chrome_installer import GOOGLE_CHROME_ENTERPRISE_MSI_URL, validate_download_url

    assert GOOGLE_CHROME_ENTERPRISE_MSI_URL == (
        "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"
    )
    assert validate_download_url(GOOGLE_CHROME_ENTERPRISE_MSI_URL) == GOOGLE_CHROME_ENTERPRISE_MSI_URL
    for bad in (
        "http://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi",
        "https://example.com/googlechromestandaloneenterprise64.msi",
        "https://dl.google.com.evil.example/googlechromestandaloneenterprise64.msi",
    ):
        with pytest.raises(ValueError):
            validate_download_url(bad)


def test_v10632_download_is_atomic_cancel_safe_and_hashes_payload(tmp_path):
    from src.vibrapilot.chrome_installer import download_google_chrome_msi

    class Response:
        headers = {"Content-Length": "6"}
        def __init__(self):
            self._chunks = [b"abc", b"123", b""]
        def read(self, _size):
            return self._chunks.pop(0)
        def geturl(self):
            return "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False

    result = download_google_chrome_msi(
        tmp_path,
        opener=lambda *_args, **_kwargs: Response(),
    )
    assert result.path.is_file()
    assert result.path.read_bytes() == b"abc123"
    assert len(result.sha256) == 64
    assert result.bytes_downloaded == 6
    assert not (tmp_path / (result.path.name + ".part")).exists()


def test_v10632_download_cancellation_never_promotes_partial_file(tmp_path):
    from src.vibrapilot.chrome_installer import ChromeInstallError, download_google_chrome_msi

    cancel = threading.Event()
    class Response:
        headers = {}
        def __init__(self):
            self.calls = 0
        def read(self, _size):
            self.calls += 1
            cancel.set()
            return b"partial" if self.calls == 1 else b""
        def geturl(self):
            return "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi"
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False

    with pytest.raises(ChromeInstallError) as exc:
        download_google_chrome_msi(tmp_path, opener=lambda *_args, **_kwargs: Response(), cancel_event=cancel)
    assert exc.value.code == "cancelled"
    assert not list(tmp_path.glob("*.msi"))
    assert not list(tmp_path.glob("*.part"))


def test_v10632_authenticode_requires_trust_and_google_llc(monkeypatch, tmp_path):
    from src.vibrapilot import chrome_installer

    msi = tmp_path / "googlechromestandaloneenterprise64.msi"
    msi.write_bytes(b"msi")
    monkeypatch.setattr(chrome_installer, "winverifytrust_file", lambda _path: (True, 0, "trusted"))
    monkeypatch.setattr(chrome_installer, "read_authenticode_publisher", lambda _path: ("Google LLC", "CN=Google LLC"))
    result = chrome_installer.verify_google_chrome_installer(msi)
    assert result.trusted is True
    assert result.publisher == "Google LLC"

    monkeypatch.setattr(chrome_installer, "read_authenticode_publisher", lambda _path: ("Example Corp", "CN=Example Corp"))
    with pytest.raises(chrome_installer.ChromeInstallError) as exc:
        chrome_installer.verify_google_chrome_installer(msi)
    assert exc.value.code == "wrong_publisher"


def test_v10632_invalid_authenticode_fails_closed(monkeypatch, tmp_path):
    from src.vibrapilot import chrome_installer

    msi = tmp_path / "googlechromestandaloneenterprise64.msi"
    msi.write_bytes(b"msi")
    monkeypatch.setattr(chrome_installer, "winverifytrust_file", lambda _path: (False, 123, "bad"))
    with pytest.raises(chrome_installer.ChromeInstallError) as exc:
        chrome_installer.verify_google_chrome_installer(msi)
    assert exc.value.code == "signature_invalid"


def test_v10632_install_orchestrator_requires_post_install_google_chrome(tmp_path):
    from src.vibrapilot.chrome_installer import (
        AuthenticodeResult,
        ChromeInstallError,
        DownloadResult,
        InstallerExecutionResult,
        install_google_chrome,
    )
    from src.vibrapilot.chrome_runtime import ChromeRuntimeInfo

    msi = tmp_path / "googlechromestandaloneenterprise64.msi"
    msi.write_bytes(b"x")
    download = DownloadResult(msi, "a" * 64, 1, "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi")

    with pytest.raises(ChromeInstallError) as exc:
        install_google_chrome(
            temp_root=tmp_path,
            downloader=lambda *_args, **_kwargs: download,
            verifier=lambda _path: AuthenticodeResult(True, "Google LLC", "CN=Google LLC", 0, "valid"),
            runner=lambda _path: InstallerExecutionResult(0, False),
            discovery=lambda: ChromeRuntimeInfo(False, "not_found"),
        )
    assert exc.value.code == "post_install_not_found"


def test_v10632_install_orchestrator_success_returns_runtime(tmp_path):
    from src.vibrapilot.chrome_installer import (
        AuthenticodeResult,
        DownloadResult,
        InstallerExecutionResult,
        install_google_chrome,
    )
    from src.vibrapilot.chrome_runtime import ChromeRuntimeInfo

    msi = tmp_path / "googlechromestandaloneenterprise64.msi"
    msi.write_bytes(b"x")
    download = DownloadResult(msi, "a" * 64, 1, "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi")
    runtime = ChromeRuntimeInfo(True, "available", tmp_path / "chrome.exe", "151", "Google Chrome", "test")
    result = install_google_chrome(
        temp_root=tmp_path,
        downloader=lambda *_args, **_kwargs: download,
        verifier=lambda _path: AuthenticodeResult(True, "Google LLC", "CN=Google LLC", 0, "valid"),
        runner=lambda _path: InstallerExecutionResult(0, False),
        discovery=lambda: runtime,
    )
    assert result.status == "installed"
    assert result.runtime is runtime


def test_v10632_runtime_helper_raises_specific_error_when_missing(monkeypatch):
    from src.vibrapilot import chrome_runtime

    monkeypatch.setattr(chrome_runtime, "discover_google_chrome", lambda: chrome_runtime.ChromeRuntimeInfo(False, "not_found"))
    with pytest.raises(chrome_runtime.ChromeRuntimeRequiredError):
        chrome_runtime.require_google_chrome()


def test_v10632_qt_source_has_startup_open_browser_and_single_installer_coordinator():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    for marker in (
        "class ChromeRequiredDialog(QDialog):",
        "def check_chrome_prerequisite_on_startup(self) -> None:",
        "def ensure_chrome_ready(self, *, interactive: bool = True) -> bool:",
        "def start_chrome_install(self) -> None:",
        'QTimer.singleShot(250, self.check_chrome_prerequisite_on_startup)',
        'elif kind == "chrome_install_progress":',
        'elif kind == "chrome_install_result":',
        "self.app.ensure_chrome_ready(interactive=True)",
    ):
        assert marker in source


def test_v10632_backend_has_defense_in_depth_chrome_prerequisite_guard():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    launch_start = source.index("    def launch_browser(self) -> None:")
    launch_end = source.index("    def context_arguments(", launch_start)
    launch = source[launch_start:launch_end]
    assert "require_google_chrome()" in launch
    assert launch.index("require_google_chrome()") < launch.index("sync_playwright().start()")
    assert 'launch_args["channel"] = "chrome"' in launch
    assert 'launch_args["channel"] = "chromium"' not in launch
