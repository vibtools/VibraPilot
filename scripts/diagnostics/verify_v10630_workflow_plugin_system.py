#!/usr/bin/env python3
"""Read-only post-apply verifier for the v1.0.6.30 Workflow Plugin System delta."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.30_workflow_plugin_system_scope.json"
SHA_FILE = ROOT / "SHA256SUMS.txt"
DELTA_LIST = ROOT / "DELTA_FILE_LIST.txt"
EXPECTED_VERSION = "1.0.6.30"
EXPECTED_BASELINE_COMMIT = "fff8160157d4d9b68b2d28b11105b0f7f38ed17d"
EXPECTED_BASELINE_TREE = "1712f05f9815c2fef4ef557d1bde3b17f7c62890"


def fail(message: str) -> "NoReturn":
    raise SystemExit(f"V10630 VERIFY: FAIL — {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_scope() -> dict:
    if not SCOPE.is_file():
        fail(f"scope file missing: {SCOPE.relative_to(ROOT)}")
    try:
        data = json.loads(SCOPE.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"scope file invalid: {exc}")
    expected = {
        "plan_id": "VP-V10630-WORKFLOW-PLUGIN-SYSTEM-001",
        "baseline_version": "1.0.6.28",
        "target_version": EXPECTED_VERSION,
        "baseline_github_commit": EXPECTED_BASELINE_COMMIT,
        "baseline_github_tree": EXPECTED_BASELINE_TREE,
        "one_active_workflow": True,
        "trusted_python_plugins": True,
        "workflow_plugin_api_version": 1,
        "plugin_sandbox": False,
        "json_playwright_interpreter": False,
        "per_task_mixed_workflows": False,
        "marketplace": False,
        "automatic_dependency_install": False,
        "production_second_workflow_invented": False,
        "github_write_by_assistant": False,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            fail(f"scope mismatch: {key}={data.get(key)!r}, expected {value!r}")
    return data


def verify_version() -> None:
    app_text = (ROOT / "config" / "AppConfig" / "app.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', app_text, re.MULTILINE)
    if not match or match.group(1) != EXPECTED_VERSION:
        fail("AppConfig VERSION mismatch")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    if pyproject.get("project", {}).get("version") != EXPECTED_VERSION:
        fail("pyproject version mismatch")


def verify_frozen(scope: dict) -> None:
    hashes = scope.get("frozen_runtime_sha256", {})
    for relative in scope.get("frozen_runtime_surfaces", []):
        path = ROOT / relative
        expected = hashes.get(relative)
        if not path.is_file() or not expected:
            fail(f"frozen runtime evidence missing: {relative}")
        actual = sha256(path)
        if actual != expected:
            fail(f"frozen runtime drift: {relative}")


def verify_delta_hygiene(scope: dict) -> None:
    if not DELTA_LIST.is_file():
        fail("DELTA_FILE_LIST.txt missing")
    payload = [line.strip() for line in DELTA_LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(payload) != len(set(payload)):
        fail("DELTA_FILE_LIST.txt contains duplicate paths")
    allowed = set(scope.get("allowed_production_source_changes", [])) | set(
        scope.get("authorized_nonproduction_files", [])
    )
    for relative in payload:
        if relative.startswith("project/") or "/project/" in relative:
            fail(f"private project path is forbidden in delta: {relative}")
        if relative not in allowed:
            fail(f"delta path is outside approved scope: {relative}")
        if not (ROOT / relative).is_file():
            fail(f"delta file missing after apply: {relative}")
    for relative in scope.get("frozen_runtime_surfaces", []):
        if relative in payload:
            fail(f"frozen runtime file must not be in delta: {relative}")
    for relative in (
        ".github/workflows/pr12-package-build.yml",
        "config/verification/v1.0.6.29_pr12_packaging_scope.json",
        "installer/VibraPilot.wxs",
        "tests/test_v10629_pr12_packaging.py",
    ):
        if (ROOT / relative).exists():
            fail(f"PR-12 packaging surface must not be imported by this functional baseline: {relative}")


def verify_checksums() -> None:
    if not SHA_FILE.is_file():
        fail("SHA256SUMS.txt missing")
    checked = 0
    for raw in SHA_FILE.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            expected, relative = raw.split(None, 1)
        except ValueError:
            fail(f"malformed SHA256SUMS line: {raw!r}")
        relative = relative.removeprefix("./")
        path = ROOT / relative
        if not path.is_file():
            fail(f"checksummed file missing: {relative}")
        actual = sha256(path)
        if actual != expected:
            fail(f"checksum mismatch: {relative}")
        checked += 1
    if checked < 10:
        fail("SHA256SUMS.txt contains too few verified files")


def run_command(command: list[str]) -> None:
    env = dict(os.environ)
    current = env.get("PYTHONPATH", "")
    prefixes = [str(ROOT / "src"), str(ROOT)]
    if current:
        prefixes.append(current)
    env["PYTHONPATH"] = os.pathsep.join(prefixes)
    proc = subprocess.run(command, cwd=ROOT, env=env)
    if proc.returncode != 0:
        fail(f"command failed ({proc.returncode}): {' '.join(command)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full-tests", action="store_true", help="also run full pytest and unittest suites")
    args = parser.parse_args()

    scope = load_scope()
    verify_version()
    verify_frozen(scope)
    verify_delta_hygiene(scope)
    verify_checksums()
    run_command([sys.executable, "scripts/verify_repository.py"])
    if args.full_tests:
        run_command([sys.executable, "-m", "pytest", "-q"])
        run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])

    print("V10630 VERIFY: PASS")
    print(f"VERSION={EXPECTED_VERSION}")
    print(f"BASELINE_COMMIT={EXPECTED_BASELINE_COMMIT}")
    print("GITHUB_WRITE=NO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
