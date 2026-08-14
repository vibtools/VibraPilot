from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _trusted(publisher: str = "Google LLC"):
    from src.vibrapilot.windows_authenticode import WindowsAuthenticodeInfo
    return WindowsAuthenticodeInfo(True, publisher, f"CN={publisher}", 0, "trusted")


def test_playwright_chrome_channel_candidate_order_includes_homedrive_fallbacks():
    from src.vibrapilot.chrome_runtime import _playwright_channel_candidates

    rows = _playwright_channel_candidates(
        {
            "LOCALAPPDATA": r"C:\\Users\\u\\AppData\\Local",
            "PROGRAMFILES": r"C:\\Program Files",
            "PROGRAMFILES(X86)": r"C:\\Program Files (x86)",
            "HOMEDRIVE": "D:",
        }
    )
    assert [name for name, _ in rows] == [
        "localappdata",
        "programfiles",
        "programfiles_x86",
        "homedrive_programfiles",
        "homedrive_programfiles_x86",
    ]
    assert all(
        str(path).replace("\\", "/").lower().endswith("google/chrome/application/chrome.exe")
        for _, path in rows
    )


def test_discovery_fails_closed_on_invalid_first_channel_target_instead_of_skipping(tmp_path):
    from src.vibrapilot.chrome_runtime import discover_google_chrome

    first = tmp_path / "local" / "chrome.exe"
    second = tmp_path / "programfiles" / "chrome.exe"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b"fake")
    second.write_bytes(b"real")

    def metadata(path: Path):
        return ("Chromium", "151") if path == first.resolve() else ("Google Chrome", "151")

    result = discover_google_chrome(
        candidate_paths=[("localappdata", first), ("programfiles", second)],
        metadata_reader=metadata,
        authenticode_reader=lambda _path: _trusted(),
        platform_name="nt",
    )
    assert result.available is False
    assert result.status == "untrusted_channel_target"
    assert result.executable_path == first.resolve()


def test_google_chrome_product_metadata_without_trusted_google_signature_is_rejected(tmp_path):
    from src.vibrapilot.chrome_runtime import discover_google_chrome
    from src.vibrapilot.windows_authenticode import WindowsAuthenticodeInfo

    chrome = tmp_path / "chrome.exe"
    chrome.write_bytes(b"MZ")
    result = discover_google_chrome(
        candidate_paths=[("localappdata", chrome)],
        metadata_reader=lambda _path: ("Google Chrome", "151"),
        authenticode_reader=lambda _path: WindowsAuthenticodeInfo(
            False, "", "", 0x800B0100, "signature invalid"
        ),
        platform_name="nt",
    )
    assert result.available is False
    assert result.status == "untrusted_channel_target"
    assert "Authenticode" in result.detail or "signature" in result.detail


def test_google_chrome_wrong_publisher_is_rejected_even_with_valid_signature(tmp_path):
    from src.vibrapilot.chrome_runtime import discover_google_chrome

    chrome = tmp_path / "chrome.exe"
    chrome.write_bytes(b"MZ")
    result = discover_google_chrome(
        candidate_paths=[("localappdata", chrome)],
        metadata_reader=lambda _path: ("Google Chrome", "151"),
        authenticode_reader=lambda _path: _trusted("Example Corp"),
        platform_name="nt",
    )
    assert result.available is False
    assert "Example Corp" in result.detail


def test_installer_url_policy_requires_exact_google_path():
    from src.vibrapilot.chrome_installer import validate_download_url

    with pytest.raises(ValueError):
        validate_download_url(
            "https://dl.google.com/evil/googlechromestandaloneenterprise64.msi"
        )
    with pytest.raises(ValueError):
        validate_download_url(
            "https://dl.google.com/dl/chrome/install/x/googlechromestandaloneenterprise64.msi"
        )


def test_windows_installer_1602_is_user_cancellation_not_generic_failure():
    from src.vibrapilot.chrome_installer import ChromeInstallError, _installer_execution_result

    with pytest.raises(ChromeInstallError) as exc:
        _installer_execution_result(1602)
    assert exc.value.code == "installer_cancelled"


def test_diagnostics_requires_measured_process_path_to_match_trusted_chrome():
    from src.vibrapilot.browser_diagnostics import _classify_engine, browser_runtime_policy_status
    from src.vibrapilot.chrome_runtime import ChromeRuntimeInfo

    trusted = ChromeRuntimeInfo(
        True,
        "available",
        Path(r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"),
        "151",
        "Google Chrome",
        "programfiles",
        publisher="Google LLC",
        signature_trusted=True,
    )
    engine, evidence = _classify_engine(
        requested_channel="chrome",
        requested_executable=None,
        fallback_used=False,
        process={"executable_path": r"C:\\Users\\u\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe"},
        trusted_runtime=trusted,
    )
    assert engine == "untrusted_chrome_executable"
    assert browser_runtime_policy_status(engine) == "violation"
    assert "not_equal" in evidence


def test_diagnostics_channel_inference_without_process_evidence_is_unverified():
    from src.vibrapilot.browser_diagnostics import _classify_engine, browser_runtime_policy_status
    from src.vibrapilot.chrome_runtime import ChromeRuntimeInfo

    engine, _ = _classify_engine(
        requested_channel="chrome",
        requested_executable=None,
        fallback_used=False,
        process={},
        trusted_runtime=ChromeRuntimeInfo(False, "not_found"),
    )
    assert engine == "google_chrome_channel_unverified"
    assert browser_runtime_policy_status(engine) == "unverified"


def test_qt_installer_coordinator_preserves_active_dialog_and_nondroppable_security_stages():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    show_start = source.index("    def show_chrome_required_dialog(")
    show_end = source.index("    def ensure_chrome_ready(", show_start)
    show = source[show_start:show_end]
    assert "if not self.chrome_install_is_active():" in show
    assert "dialog.set_missing(current.detail)" in show

    recheck_start = source.index("    def recheck_chrome_prerequisite(")
    recheck_end = source.index("    def _queue_chrome_install_progress(", recheck_start)
    assert "if self.chrome_install_is_active():" in source[recheck_start:recheck_end]

    queue_start = source.index("    def _queue_chrome_install_progress(")
    queue_end = source.index("    def start_chrome_install(", queue_start)
    queue_source = source[queue_start:queue_end]
    assert 'if progress.stage == "downloading":' in queue_source
    assert "self.ui_queue.put_nowait(event)" in queue_source
    assert "self.ui_queue.put(event)" in queue_source


def test_installer_cancelled_result_is_rendered_as_cancelled_warning():
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    start = source.index("    def _handle_chrome_install_result(")
    end = source.index("    def _persistent_profile_claim(", start)
    block = source[start:end]
    assert '"installer_cancelled"' in block
    assert 'self._chrome_install_state = "cancelled"' in block


def test_frozen_build_dependency_workflow_and_persistence_surfaces_are_unchanged():
    # v1.0.6.33 forensic closure must not turn into a build/workflow refactor.
    import json

    scope = json.loads(
        (ROOT / "config/verification/v1.0.6.32_chrome_prerequisite_install_scope.json").read_text(encoding="utf-8")
    )
    assert scope["frozen_file_sha256"]["build.py"]
    assert scope["frozen_file_sha256"]["requirements.txt"]
    assert scope["frozen_file_sha256"]["requirements-build.txt"]
    assert scope["frozen_file_sha256"][".github/workflows/ci.yml"]
