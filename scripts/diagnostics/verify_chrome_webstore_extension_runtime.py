#!/usr/bin/env python3
"""Validate Chrome Web Store extension-install runtime evidence.

Read-only verification tooling. It never launches, configures, or modifies Chrome.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


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
        help="Path to slot_N_latest.json browser diagnostic evidence.",
    )
    parser.add_argument(
        "--extension-id",
        default="",
        help="Optional Chrome Web Store extension ID to verify in the managed profile after manual installation.",
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
    effective = launch.get("effective_kwargs") if isinstance(launch.get("effective_kwargs"), dict) else {}
    command_line = str(actual.get("command_line") or "")
    profile_path = str(actual.get("profile_path") or requested.get("profile_path") or "")
    profile_directory = str(requested.get("profile_directory") or "Default")

    print(f"Evidence: {path}")
    print(f"Engine: {actual.get('engine') or 'NOT VERIFIED'}")
    print(f"Product: {actual.get('product') or 'NOT VERIFIED'}")
    print(f"Executable: {actual.get('executable_path') or 'NOT VERIFIED'}")
    print(f"Profile: {profile_path or 'NOT VERIFIED'}")
    print(f"Fallback used: {bool(launch.get('fallback_used'))}")
    print(f"Command line contains --disable-extensions: {'--disable-extensions' in command_line}")
    print(f"Download acceptance configured: {bool(effective.get('accept_downloads'))}")

    failures: list[str] = []
    if not command_line:
        failures.append("Actual browser process command line is not captured.")
    elif "--disable-extensions" in command_line:
        failures.append("Chrome is still launched with --disable-extensions.")

    extension_id = args.extension_id.strip()
    if extension_id:
        if not profile_path:
            failures.append("Managed profile path is not captured; extension persistence cannot be checked.")
        else:
            extension_dir = Path(profile_path) / (profile_directory or "Default") / "Extensions" / extension_id
            print(f"Extension directory: {extension_dir}")
            print(f"Extension installed in profile: {extension_dir.is_dir()}")
            if not extension_dir.is_dir():
                failures.append(f"Extension ID {extension_id} was not found in the managed profile.")

    if failures:
        print("RESULT: FAIL / ACTION REQUIRED")
        for item in failures:
            print(f"- {item}")
        return 1

    print("RESULT: EXTENSION-SERVICE LAUNCH EVIDENCE PASS")
    if extension_id:
        print("Manual Chrome Web Store installation is also present in the managed profile.")
    else:
        print("Run again with --extension-id <ID> after a manual Chrome Web Store install to verify installation persistence.")
    print("Note: download runtime success must still be confirmed with a real downloaded file after applying the patch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
