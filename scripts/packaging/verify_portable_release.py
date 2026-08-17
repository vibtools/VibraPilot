#!/usr/bin/env python3
"""Forensically verify a VibraPilot Nuitka portable OneDir release artifact."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for candidate in (SRC, ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from config.AppConfig.app import APP_NAME, VERSION

PORTABLE_NAME = f"{APP_NAME}-{VERSION}-Windows-x64-Portable"
FORBIDDEN_DIR_NAMES = {
    ".git",
    "project",
    "AppData",
    "Logs",
    "Reports",
    "FailedData",
    "BrowserProfiles",
    "__pycache__",
    ".pytest_cache",
    "ms-playwright",
    ".playwright-browsers",
}
FORBIDDEN_SUFFIXES = {".msi", ".wixobj", ".wixpdb", ".wxs"}
FORBIDDEN_BROWSER_BINARIES = {"chrome.exe", "chromium.exe", "headless_shell.exe"}
REQUIRED_RELATIVE_FILES = {
    f"{APP_NAME}.exe",
    "config/settings.defaults.json",
    "frozen_design_source/CURRENT_FOUNDATION_TOKENS.json",
    "playwright/driver/node.exe",
    "playwright/driver/package/cli.js",
    "SHA256SUMS.json",
    "BUILD-INFO.json",
    "PORTABLE_README.txt",
}


class VerificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_tree(release_dir: Path) -> dict[str, object]:
    release_dir = release_dir.resolve()
    if release_dir.name != PORTABLE_NAME:
        raise VerificationError(
            f"Portable directory name mismatch: expected {PORTABLE_NAME}, found {release_dir.name}."
        )
    if not release_dir.is_dir():
        raise VerificationError(f"Portable directory does not exist: {release_dir}")

    files = [path for path in release_dir.rglob("*") if path.is_file()]
    relative_files = {path.relative_to(release_dir).as_posix() for path in files}
    missing = sorted(REQUIRED_RELATIVE_FILES - relative_files)
    if missing:
        raise VerificationError(f"Required portable files missing: {missing}")

    for path in release_dir.rglob("*"):
        rel = path.relative_to(release_dir)
        if FORBIDDEN_DIR_NAMES.intersection(rel.parts):
            raise VerificationError(f"Forbidden private/runtime directory present: {rel.as_posix()}")
        if path.is_file() and path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise VerificationError(f"WiX/MSI payload present: {rel.as_posix()}")
        if path.is_file() and path.name.lower() in FORBIDDEN_BROWSER_BINARIES:
            raise VerificationError(f"Bundled Chrome/Chromium binary present: {rel.as_posix()}")

    manifest = json.loads((release_dir / "SHA256SUMS.json").read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise VerificationError("SHA256SUMS.json must contain a non-empty object.")
    mismatches: list[str] = []
    for relative, expected in manifest.items():
        path = release_dir / Path(relative)
        if not path.is_file() or sha256(path) != str(expected):
            mismatches.append(relative)
    if mismatches:
        raise VerificationError(f"Portable file checksum mismatch: {mismatches}")

    info = json.loads((release_dir / "BUILD-INFO.json").read_text(encoding="utf-8"))
    if info.get("format") != "Nuitka-Standalone-OneDir":
        raise VerificationError("BUILD-INFO format is not Nuitka-Standalone-OneDir.")
    if info.get("version") != VERSION:
        raise VerificationError("BUILD-INFO version mismatch.")
    if info.get("bundled_browser") is not False:
        raise VerificationError("BUILD-INFO must record bundled_browser=false.")
    if info.get("system_google_chrome_required") is not True:
        raise VerificationError("BUILD-INFO must record system Google Chrome prerequisite.")
    if info.get("wix_msi") is not False:
        raise VerificationError("BUILD-INFO must record wix_msi=false.")

    total_bytes = sum(path.stat().st_size for path in files)
    return {
        "portable_directory": str(release_dir),
        "file_count": len(files),
        "uncompressed_bytes": total_bytes,
        "manifest_entries": len(manifest),
        "bundled_chromium": False,
        "wix_msi": False,
    }


def verify_zip(zip_path: Path, release_dir: Path) -> dict[str, object]:
    zip_path = zip_path.resolve()
    if not zip_path.is_file():
        raise VerificationError(f"Portable ZIP does not exist: {zip_path}")
    with zipfile.ZipFile(zip_path) as archive:
        bad = archive.testzip()
        if bad:
            raise VerificationError(f"ZIP CRC failure: {bad}")
        names = [name for name in archive.namelist() if not name.endswith("/")]
    expected_prefix = release_dir.name + "/"
    if not names or any(not name.startswith(expected_prefix) for name in names):
        raise VerificationError("Portable ZIP contains files outside its single top-level folder.")
    return {
        "zip_path": str(zip_path),
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": sha256(zip_path),
        "zip_file_entries": len(names),
    }


def verify_sha_file(zip_path: Path, sha_file: Path, actual_digest: str) -> None:
    if not sha_file.is_file():
        raise VerificationError(f"ZIP SHA-256 file is missing: {sha_file}")
    fields = sha_file.read_text(encoding="ascii").strip().split()
    if not fields or fields[0].lower() != actual_digest.lower():
        raise VerificationError("ZIP SHA-256 sidecar does not match the ZIP.")
    if len(fields) >= 2 and Path(fields[-1]).name != zip_path.name:
        raise VerificationError("ZIP SHA-256 sidecar filename does not match the ZIP.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-dir", type=Path, required=True)
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument("--sha256", dest="sha_path", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    result = verify_tree(args.release_dir)
    zip_result = verify_zip(args.zip_path, args.release_dir)
    verify_sha_file(args.zip_path, args.sha_path, str(zip_result["zip_sha256"]))
    result.update(zip_result)
    result["status"] = "PASS"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("V1.0.6.37 PORTABLE RELEASE VERIFY: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except VerificationError as exc:
        print(f"V1.0.6.37 PORTABLE RELEASE VERIFY: FAIL — {exc}")
        raise SystemExit(1)
