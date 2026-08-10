#!/usr/bin/env python3
"""Validate a VibraPilot browser-foundation diagnostic JSON record.

This is verification tooling only. It does not launch, modify, or configure Chrome.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXPECTED_PLAYWRIGHT_VERSION = "1.61.0"


def load_record(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Diagnostic root must be a JSON object.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        default="Logs/BrowserDiagnostics/slot_1_latest.json",
        help="Path to a slot_N_latest.json browser diagnostic record.",
    )
    args = parser.parse_args()
    path = Path(args.path)
    if not path.is_file():
        print(f"EVIDENCE NOT FOUND: {path}")
        return 2

    try:
        record = load_record(path)
    except Exception as exc:
        print(f"INVALID EVIDENCE: {exc}")
        return 2

    actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
    launch = record.get("launch") if isinstance(record.get("launch"), dict) else {}
    requested = record.get("requested") if isinstance(record.get("requested"), dict) else {}
    playwright = record.get("playwright") if isinstance(record.get("playwright"), dict) else {}

    runtime_version = str(
        playwright.get("actual_version")
        or record.get("playwright_python_version")
        or "unknown"
    )
    expected_version = str(playwright.get("expected_version") or EXPECTED_PLAYWRIGHT_VERSION)
    command_line = str(actual.get("command_line") or "")

    print(f"Evidence: {path}")
    print(f"Engine: {actual.get('engine') or 'NOT VERIFIED'}")
    print(f"Product: {actual.get('product') or 'NOT VERIFIED'}")
    print(f"Executable: {actual.get('executable_path') or 'NOT VERIFIED'}")
    print(f"Profile: {actual.get('profile_path') or requested.get('profile_path') or 'NOT VERIFIED'}")
    print(f"Fallback used: {bool(launch.get('fallback_used'))}")
    print(f"Sandbox requested: {bool(requested.get('sandbox_enabled'))}")
    print(f"Command line contains --no-sandbox: {'--no-sandbox' in command_line}")
    print(f"Playwright runtime: {runtime_version}")
    print(f"Playwright required: {expected_version}")

    failures: list[str] = []
    if runtime_version == "unknown":
        failures.append("Playwright runtime version is not captured.")
    elif runtime_version != expected_version:
        failures.append(
            f"Playwright runtime mismatch: runtime={runtime_version}, required={expected_version}."
        )
    if not actual.get("engine"):
        failures.append("Actual browser engine is not classified.")
    if not actual.get("product"):
        failures.append("Browser product/version is not captured.")
    if requested.get("persistent_context") and not (
        actual.get("profile_path") or requested.get("profile_path")
    ):
        failures.append("Persistent browser profile path is not captured.")

    if failures:
        print("RESULT: PARTIAL / ACTION REQUIRED")
        for item in failures:
            print(f"- {item}")
        return 1

    print("RESULT: EVIDENCE STRUCTURE PASS")
    print("Note: this validates captured evidence, not Sandbox-ON/CAPTCHA/capability acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
