"""Scoped browser capability helpers for VibraPilot.

This module owns path/manifest validation only. Playwright objects remain owned by
``AutomationWorker`` and Qt widgets remain owned by ``qt_app``.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

_INVALID_WINDOWS_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_WINDOWS_BASENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def default_managed_download_root(app_data_dir: Path) -> Path:
    """Return the durable default download root without changing settings keys.

    Explicit ``VIB_TOOLS_DATA_DIR`` deployments remain rooted in AppData, matching
    existing VibraPilot deployment semantics. Normal Windows installs use the same
    durable per-user product root as managed browser/licensing state.
    """
    app_data_dir = Path(app_data_dir).expanduser().resolve()
    if os.environ.get("VIB_TOOLS_DATA_DIR"):
        return app_data_dir / "Downloads"
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local:
            return Path(local).expanduser().resolve() / "Vib Tools" / "VibraPilot" / "Downloads"
    return app_data_dir / "Downloads"


def resolve_task_download_directory(
    settings: Mapping[str, Any],
    slot_id: int,
    app_data_dir: Path,
) -> Path:
    """Resolve the effective durable download directory for one Task.

    An explicit ``downloads_path`` preserves the baseline shared-path semantics.
    Only the blank/default path is converted into an app-managed per-Task folder.
    """
    raw = str(settings.get("downloads_path", "")).strip()
    app_data_dir = Path(app_data_dir).expanduser().resolve()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = app_data_dir / path
        return path.resolve()
    return (default_managed_download_root(app_data_dir) / f"slot_{max(1, int(slot_id))}").resolve()


def ensure_task_download_directory(
    settings: Mapping[str, Any],
    slot_id: int,
    app_data_dir: Path,
) -> Path:
    path = resolve_task_download_directory(settings, slot_id, app_data_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_download_filename(name: str, fallback: str = "download") -> str:
    """Return a Windows-safe leaf filename with traversal/reserved-name removal."""
    leaf = Path(str(name or "").replace("\\", "/")).name
    leaf = _INVALID_WINDOWS_FILENAME_CHARS.sub("_", leaf).strip().rstrip(". ")
    if not leaf:
        leaf = fallback

    suffix = Path(leaf).suffix
    stem = Path(leaf).stem if suffix else leaf
    if stem.upper() in _RESERVED_WINDOWS_BASENAMES:
        stem = f"_{stem}"
    leaf = f"{stem}{suffix}" if suffix else stem

    # Keep room for collision suffixes and normal Windows path limits.
    if len(leaf) > 180:
        suffix = Path(leaf).suffix
        limit = max(1, 180 - len(suffix))
        stem = Path(leaf).stem[:limit].rstrip(". ") or fallback
        leaf = f"{stem}{suffix}"
    return leaf or fallback


def collision_safe_download_path(directory: Path, suggested_filename: str) -> Path:
    """Return a non-existing destination path without overwriting prior downloads."""
    directory = Path(directory)
    filename = sanitize_download_filename(suggested_filename)
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    path = Path(filename)
    stem = path.stem or "download"
    suffix = path.suffix
    index = 1
    while True:
        candidate = directory / f"{stem} ({index}){suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def normalize_extension_paths(raw: str) -> list[Path]:
    """Normalize semicolon/newline-separated unpacked extension directories."""
    paths: list[Path] = []
    seen: set[str] = set()
    for part in re.split(r"[;\n]+", str(raw or "")):
        part = part.strip()
        if not part:
            continue
        path = Path(part).expanduser().resolve()
        key = os.path.normcase(str(path))
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def validate_unpacked_extension_directories(raw: str) -> list[Path]:
    """Validate unpacked extension directories and their manifest JSON structure."""
    paths = normalize_extension_paths(raw)
    if not paths:
        raise ValueError("Extension Loading is enabled but Extension Directories is empty.")
    for path in paths:
        if not path.is_dir():
            raise ValueError(f"Extension directory does not exist: {path}")
        manifest = path / "manifest.json"
        if not manifest.is_file():
            raise ValueError(f"Extension manifest.json was not found: {manifest}")
        try:
            parsed = json.loads(manifest.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            raise ValueError(f"Extension manifest.json is invalid JSON: {manifest}") from exc
        if not isinstance(parsed, dict):
            raise ValueError(f"Extension manifest.json must contain a JSON object: {manifest}")
    return paths
