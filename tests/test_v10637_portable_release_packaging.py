from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot import runtime_environment


def test_scope_contract_is_exact_portable_only_boundary():
    scope = json.loads(
        (ROOT / "config/verification/v1.0.6.37_portable_release_packaging_scope.json").read_text(
            encoding="utf-8"
        )
    )
    assert scope["baseline_version"] == "1.0.6.36"
    assert scope["target_version"] == "1.0.6.37"
    assert scope["baseline_github_commit"] == "40b9b65d3900760d919167dc6711a4fcd494f010"
    assert scope["official_baseline_archive_sha256"] == "19f06990ae4b209da28159a25eced0b5be297579b907bcd60d79a3f3fe197ef5"
    assert scope["nuitka_version"] == "4.1.3"
    assert scope["nuitka_mode"] == "standalone"
    assert scope["distribution_format"] == "OneDir"
    assert scope["system_google_chrome_only"] is True
    assert scope["bundled_playwright_chromium"] is False
    assert scope["wix_msi_enabled"] is False
    assert scope["allowed_production_source_changes"] == [
        "src/vibrapilot/runtime_environment.py",
        "src/vibrapilot/backend.py",
        "src/vibrapilot/qt_app.py",
    ]


def test_portable_requirements_pin_nuitka_without_replacing_historical_builder():
    portable = (ROOT / "requirements-portable.txt").read_text(encoding="utf-8")
    historical = (ROOT / "requirements-build.txt").read_text(encoding="utf-8")
    assert "-r requirements.txt" in portable
    assert "Nuitka==4.1.3" in portable
    assert "pyinstaller==6.21.0" in historical


def test_nuitka_builder_is_standalone_onedir_and_never_installs_browser():
    source = (ROOT / "scripts/packaging/build_portable_nuitka.py").read_text(encoding="utf-8")
    for marker in (
        '"--mode=standalone"',
        '"--enable-plugin=pyside6"',
        '"--windows-console-mode=disable"',
        '"--include-package=playwright"',
        '"--include-distribution-metadata=playwright"',
        '"--playwright-include-browser=none"',
        '"--force-stdout-spec={PROGRAM_BASE}.stdout.log"',
        '"--force-stderr-spec={PROGRAM_BASE}.stderr.log"',
        "diagnostic_build_enabled",
        "validate_compiled_runtime",
        'browser_binaries = {"chrome.exe", "chromium.exe", "headless_shell.exe"}',
    ):
        assert marker in source
    assert "playwright install chromium" not in source
    assert '"-m", "playwright", "install"' not in source
    assert "ms-playwright" in source  # rejection-only policy marker
    assert "PyInstaller" not in source
    assert "candle.exe" not in source
    assert "light.exe" not in source
    assert "wix build" not in source.lower()


def test_portable_verifier_requires_driver_but_rejects_browser_and_wix_payloads():
    source = (ROOT / "scripts/packaging/verify_portable_release.py").read_text(encoding="utf-8")
    assert '"playwright/driver/node.exe"' in source
    assert '"playwright/driver/package/cli.js"' in source
    assert '"chrome.exe", "chromium.exe", "headless_shell.exe"' in source
    assert '".msi", ".wixobj", ".wixpdb", ".wxs"' in source
    assert '"ms-playwright"' in source
    assert '".playwright-browsers"' in source


def test_github_action_builds_candidate_and_only_tag_path_publishes_release():
    workflow = (ROOT / ".github/workflows/portable-release.yml").read_text(encoding="utf-8")
    for marker in (
        "workflow_dispatch:",
        "tags: ['v*']",
        "runs-on: windows-2022",
        "python-version: '3.12'",
        "architecture: 'x64'",
        "build_portable_nuitka.py",
        "verify_portable_release.py",
        "actions/upload-artifact@v4",
        "VIBRAPILOT_PORTABLE_DIAGNOSTICS",
        "Remove-Item Env:PYTHONPATH",
        "Remove-Item Env:PYTHONHOME",
        'PYTHONNOUSERSITE = "1"',
        "VibraPilot-Windows-x64-Portable-Startup-Diagnostics",
        "if: failure()",
        "if: startsWith(github.ref, 'refs/tags/v')",
        "gh release create",
        "expected = f\"v{VERSION}\"",
    ):
        assert marker in workflow
    assert "wix" not in workflow.lower()
    assert "msi" not in workflow.lower()
    assert "playwright install chromium" not in workflow.lower()


def test_source_runtime_root_remains_repository_root():
    marker = runtime_environment.__dict__.pop("__compiled__", None)
    had_frozen = hasattr(sys, "frozen")
    old_frozen = getattr(sys, "frozen", None)
    try:
        if had_frozen:
            delattr(sys, "frozen")
        assert runtime_environment.is_packaged_runtime() is False
        assert runtime_environment.application_root() == ROOT
    finally:
        if marker is not None:
            runtime_environment.__dict__["__compiled__"] = marker
        if had_frozen:
            setattr(sys, "frozen", old_frozen)


def test_nuitka_runtime_uses_compiled_containing_dir(tmp_path):
    old = runtime_environment.__dict__.get("__compiled__")
    had = "__compiled__" in runtime_environment.__dict__
    runtime_environment.__dict__["__compiled__"] = SimpleNamespace(containing_dir=str(tmp_path))
    try:
        assert runtime_environment.is_packaged_runtime() is True
        assert runtime_environment.application_root() == tmp_path.resolve()
    finally:
        if had:
            runtime_environment.__dict__["__compiled__"] = old
        else:
            runtime_environment.__dict__.pop("__compiled__", None)


def test_pyinstaller_runtime_contract_is_still_supported(tmp_path):
    had_frozen = hasattr(sys, "frozen")
    old_frozen = getattr(sys, "frozen", None)
    had_meipass = hasattr(sys, "_MEIPASS")
    old_meipass = getattr(sys, "_MEIPASS", None)
    try:
        setattr(sys, "frozen", True)
        setattr(sys, "_MEIPASS", str(tmp_path))
        assert runtime_environment.is_packaged_runtime() is True
        assert runtime_environment.application_root() == tmp_path.resolve()
    finally:
        if had_frozen:
            setattr(sys, "frozen", old_frozen)
        else:
            delattr(sys, "frozen")
        if had_meipass:
            setattr(sys, "_MEIPASS", old_meipass)
        else:
            delattr(sys, "_MEIPASS")


def test_backend_and_restart_use_cross_packager_predicate():
    backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    qt = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    assert "ROOT_DIR = application_root()" in backend
    assert "if not is_packaged_runtime():" in backend
    assert "if is_packaged_runtime():" in backend
    assert "if is_packaged_runtime():" in qt
    assert 'getattr(sys, "frozen", False)' not in qt


def test_ci_stability_fix_keeps_production_store_frozen_and_widens_only_test_guard():
    scope = json.loads(
        (ROOT / "config/verification/v1.0.6.37_portable_release_packaging_scope.json").read_text(
            encoding="utf-8"
        )
    )
    correction = scope["ci_stability_correction"]
    assert correction["classification"] == "verification-only; no production runtime change"
    assert correction["concurrent_store_test_timeout_seconds"] == 300.0
    assert correction["general_ci_workflow_changed"] is False
    assert correction["portable_build_runner"] == "windows-2022"
    assert correction["production_task_runtime_store_changed"] is False
    assert correction["application_business_logic_changed"] is False

    runtime_store = ROOT / "src/vibrapilot/task_runtime_store.py"
    assert hashlib.sha256(runtime_store.read_bytes()).hexdigest() == scope["frozen_task_runtime_store_sha256"]

    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    portable = (ROOT / ".github/workflows/portable-release.yml").read_text(encoding="utf-8")
    assert "runs-on: windows-latest" in ci  # historical general CI intentionally untouched
    assert "runs-on: windows-2022" in portable
    assert "windows-latest" not in portable

    stress = (ROOT / "tests/test_task_runtime_store.py").read_text(encoding="utf-8")
    assert "CONCURRENT_STORE_TEST_TIMEOUT_SECONDS = 300.0" in stress


def test_rc_startup_diagnostic_correction_is_nonproduction_and_fail_closed():
    scope = json.loads(
        (ROOT / "config/verification/v1.0.6.37_portable_release_packaging_scope.json").read_text(
            encoding="utf-8"
        )
    )
    correction = scope["portable_startup_diagnostic_correction"]
    assert correction["failed_run_id"] == 32048312168
    assert correction["failed_job_id"] == 95441285784
    assert correction["nuitka_compile_passed"] is True
    assert correction["artifact_forensic_verifier_passed"] is True
    assert correction["startup_exit_code"] == 1
    assert correction["production_source_changed"] is False
    assert correction["tag_release_behavior_changed"] is False
    assert correction["diagnostic_capture_only_on_workflow_dispatch"] is True
    assert correction["clean_smoke_environment"] is True

    workflow = (ROOT / ".github/workflows/portable-release.yml").read_text(encoding="utf-8")
    assert 'if ("${{ github.event_name }}" -eq "workflow_dispatch")' in workflow
    assert '$env:VIBRAPILOT_PORTABLE_DIAGNOSTICS = "1"' in workflow
    assert 'Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue' in workflow
    assert 'Remove-Item Env:PYTHONHOME -ErrorAction SilentlyContinue' in workflow
    assert 'name: VibraPilot-Windows-x64-Portable-Startup-Diagnostics' in workflow
    assert 'if: failure()' in workflow
    assert 'VibraPilot.stderr.log' in workflow
    assert 'VibraPilot.stdout.log' in workflow

    builder = (ROOT / "scripts/packaging/build_portable_nuitka.py").read_text(encoding="utf-8")
    assert 'VIBRAPILOT_PORTABLE_DIAGNOSTICS' in builder
    assert '--force-stdout-spec={PROGRAM_BASE}.stdout.log' in builder
    assert '--force-stderr-spec={PROGRAM_BASE}.stderr.log' in builder
