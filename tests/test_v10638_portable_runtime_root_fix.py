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

SCOPE = ROOT / "config/verification/v1.0.6.38_portable_runtime_root_fix_scope.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_scope_locks_exact_failed_rc_and_single_production_file():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["plan_id"] == "VP-V10638-PORTABLE-RUNTIME-ROOT-FIX-001"
    assert scope["baseline_version"] == "1.0.6.37"
    assert scope["target_version"] == "1.0.6.38"
    assert scope["baseline_source_commit"] == "299e93a89db3d30505350f474f79eefc330ee923"
    assert scope["user_supplied_baseline_archive_sha256"] == "007d339193e7f02bc316514e82512174034d611c889a327580f59a32a24bfddb"
    assert scope["failed_portable_run_id"] == 32056816056
    assert scope["failed_portable_job_id"] == 95468779983
    assert scope["diagnostics_artifact_id"] == 9297920798
    assert scope["allowed_production_source_changes"] == ["src/vibrapilot/runtime_environment.py"]


def test_nuitka_onedir_root_is_executable_directory_not_containing_dir(tmp_path):
    old_marker = runtime_environment.__dict__.get("__compiled__")
    had_marker = "__compiled__" in runtime_environment.__dict__
    old_argv0 = sys.argv[0]
    dist = tmp_path / "VibraPilot-1.0.6.38-Windows-x64-Portable"
    dist.mkdir()
    (dist / "config").mkdir()
    (dist / "config" / "settings.defaults.json").write_text("{}\n", encoding="utf-8")
    runtime_environment.__dict__["__compiled__"] = SimpleNamespace(containing_dir=str(tmp_path))
    sys.argv[0] = str(dist / "VibraPilot.exe")
    try:
        assert runtime_environment.is_packaged_runtime() is True
        assert runtime_environment.application_root() == dist.resolve()
        assert (runtime_environment.application_root() / "config/settings.defaults.json").is_file()
        assert runtime_environment.application_root() != tmp_path.resolve()
    finally:
        sys.argv[0] = old_argv0
        if had_marker:
            runtime_environment.__dict__["__compiled__"] = old_marker
        else:
            runtime_environment.__dict__.pop("__compiled__", None)


def test_pyinstaller_and_source_root_contracts_remain_unchanged(tmp_path):
    old_marker = runtime_environment.__dict__.pop("__compiled__", None)
    had_frozen = hasattr(sys, "frozen")
    old_frozen = getattr(sys, "frozen", None)
    had_meipass = hasattr(sys, "_MEIPASS")
    old_meipass = getattr(sys, "_MEIPASS", None)
    try:
        setattr(sys, "frozen", True)
        setattr(sys, "_MEIPASS", str(tmp_path))
        assert runtime_environment.application_root() == tmp_path.resolve()
        delattr(sys, "frozen")
        if hasattr(sys, "_MEIPASS"):
            delattr(sys, "_MEIPASS")
        assert runtime_environment.is_packaged_runtime() is False
        assert runtime_environment.application_root() == ROOT
    finally:
        if old_marker is not None:
            runtime_environment.__dict__["__compiled__"] = old_marker
        if had_frozen:
            setattr(sys, "frozen", old_frozen)
        elif hasattr(sys, "frozen"):
            delattr(sys, "frozen")
        if had_meipass:
            setattr(sys, "_MEIPASS", old_meipass)
        elif hasattr(sys, "_MEIPASS"):
            delattr(sys, "_MEIPASS")


def test_v10638_freezes_runtime_and_build_surfaces_outside_root_helper():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    for relative, expected in scope["frozen_file_sha256"].items():
        assert _sha256(ROOT / relative) == expected, relative
    runtime_source = (ROOT / "src/vibrapilot/runtime_environment.py").read_text(encoding="utf-8")
    assert "Path(sys.argv[0]).resolve().parent" in runtime_source
    assert "return Path(containing_dir).resolve()" not in runtime_source


def test_portable_architecture_remains_nuitka_onedir_chrome_only_no_wix():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    inv = scope["portable_invariants"]
    assert inv == {"build_host":"windows-2022","python":"3.12 x64","nuitka":"4.1.3","mode":"standalone OneDir","system_google_chrome_only":True,"bundled_playwright_chromium":False,"wix_msi":False}
    workflow = (ROOT / ".github/workflows/portable-release.yml").read_text(encoding="utf-8")
    builder = (ROOT / "scripts/packaging/build_portable_nuitka.py").read_text(encoding="utf-8")
    assert "runs-on: windows-2022" in workflow
    assert '"--mode=standalone"' in builder
    assert '"--playwright-include-browser=none"' in builder
    assert "playwright install chromium" not in workflow.lower()
    assert "playwright install chromium" not in builder.lower()
    assert "wix" not in workflow.lower()
    assert "msi" not in workflow.lower()


def test_portable_verifier_reports_current_appconfig_version_dynamically():
    source = (ROOT / "scripts/packaging/verify_portable_release.py").read_text(encoding="utf-8")
    assert 'print(f"V{VERSION} PORTABLE RELEASE VERIFY: PASS")' in source
    assert 'print(f"V{VERSION} PORTABLE RELEASE VERIFY: FAIL — {exc}")' in source
    assert "V1.0.6.37 PORTABLE RELEASE VERIFY" not in source
