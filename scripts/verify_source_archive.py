#!/usr/bin/env python3
"""Verify that a VibraPilot source ZIP is clean and safe to publish as a baseline.

This verifier does not modify the archive. It rejects runtime/private/cache paths,
unsafe ZIP member names, and archives that do not contain the expected public source
layout. A single enclosing directory is accepted, as are project-root-relative ZIPs.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import PurePosixPath, Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_SCOPE = ROOT / "config" / "verification" / "production_mt_lr_v1.0.6.5_scope.json"

DEFAULT_FORBIDDEN = {
    "AppData",
    "FailedData",
    "Reports",
    "Logs",
    "project",
    "__pycache__",
    ".pytest_cache",
}
REQUIRED = {
    "README.md",
    "pyproject.toml",
    "src/vibrapilot/backend.py",
    "src/vibrapilot/qt_app.py",
    "config/AppConfig/app.py",
}


def _forbidden_paths() -> set[str]:
    try:
        payload = json.loads(PRODUCTION_SCOPE.read_text(encoding="utf-8"))
        values = payload.get("forbidden_release_top_level_paths", [])
        result = {str(value).strip("/") for value in values if str(value).strip("/")}
        return result or set(DEFAULT_FORBIDDEN)
    except Exception:
        return set(DEFAULT_FORBIDDEN)


def _safe_parts(name: str) -> tuple[str, ...]:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe ZIP member path: {name}")
    if path.parts and ":" in path.parts[0]:
        raise ValueError(f"unsafe ZIP member path: {name}")
    return path.parts


def _project_relative_paths(names: list[str]) -> list[PurePosixPath]:
    parts_list = [_safe_parts(name) for name in names if name and not name.endswith("/")]
    if not parts_list:
        raise ValueError("archive contains no files")

    top = {parts[0] for parts in parts_list if parts}
    has_root_file = any(len(parts) == 1 for parts in parts_list)
    strip_prefix = len(top) == 1 and not has_root_file
    paths: list[PurePosixPath] = []
    for parts in parts_list:
        relative = parts[1:] if strip_prefix else parts
        if not relative:
            continue
        paths.append(PurePosixPath(*relative))
    return paths


def verify_archive(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            bad_crc = archive.testzip()
            if bad_crc:
                errors.append(f"ZIP CRC failure: {bad_crc}")
            try:
                members = _project_relative_paths(archive.namelist())
            except ValueError as exc:
                return [str(exc)]
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"invalid ZIP archive: {exc}"]

    forbidden = _forbidden_paths()
    member_strings = {member.as_posix() for member in members}
    for member in members:
        parts = member.parts
        if not parts:
            continue
        if parts[0] in forbidden:
            errors.append(f"forbidden release path: {member.as_posix()}")
        if any(part in {"__pycache__", ".pytest_cache"} for part in parts):
            errors.append(f"cache path in release archive: {member.as_posix()}")
        if member.suffix.lower() in {".pyc", ".pyo"}:
            errors.append(f"compiled Python cache in release archive: {member.as_posix()}")

    missing = sorted(REQUIRED - member_strings)
    if missing:
        errors.append("missing required source files: " + ", ".join(missing))
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="Source ZIP to verify")
    args = parser.parse_args(argv)
    errors = verify_archive(args.archive)
    if errors:
        for error in errors:
            print(f"SOURCE ARCHIVE VERIFY FAILED: {error}", file=sys.stderr)
        return 1
    print(f"Source archive verification passed: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
