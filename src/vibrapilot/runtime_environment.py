"""Cross-packager runtime location helpers for VibraPilot portable builds.

The historical Windows builder used PyInstaller, while v1.0.6.37 introduces a
Nuitka standalone/OneDir release path.  Nuitka deliberately does not set
``sys.frozen``; its ``__compiled__.containing_dir`` attribute is the supported
way to locate the standalone distribution directory.

This module centralizes that packaging distinction without changing application
business logic.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _nuitka_compiled_marker() -> Any | None:
    try:
        return __compiled__  # type: ignore[name-defined]  # Nuitka injected at compile time.
    except NameError:
        return None


def is_packaged_runtime() -> bool:
    """Return True for supported PyInstaller or Nuitka packaged execution."""
    return bool(getattr(sys, "frozen", False) or _nuitka_compiled_marker() is not None)


def application_root() -> Path:
    """Return the directory that owns packaged runtime data files.

    Source mode keeps the historical repository-root contract.  PyInstaller
    keeps the existing ``_MEIPASS`` behavior.  Nuitka standalone resolves to
    the generated ``.dist`` directory via ``__compiled__.containing_dir``.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)).resolve()

    marker = _nuitka_compiled_marker()
    if marker is not None:
        containing_dir = getattr(marker, "containing_dir", None)
        if containing_dir:
            return Path(containing_dir).resolve()
        return Path(sys.argv[0]).resolve().parent

    return Path(__file__).resolve().parents[2]
