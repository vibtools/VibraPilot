"""Cross-packager runtime location helpers for VibraPilot portable builds.

The historical Windows builder used PyInstaller, while v1.0.6.37 introduced a
Nuitka standalone/OneDir release path. Nuitka deliberately does not set
``sys.frozen``. For data files shipped *inside* the standalone distribution,
Nuitka documents the directory of ``sys.argv[0]`` as the program-adjacent
runtime location; ``__compiled__.containing_dir`` instead describes the
directory containing the compiled artifact/dist container and can therefore be
one level above the copied OneDir payload.

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

    Source mode keeps the historical repository-root contract. PyInstaller
    keeps the existing ``_MEIPASS`` behavior. Nuitka standalone resolves to
    the directory containing the launched executable so adjacent ``config/``,
    ``assets/`` and other packaged data remain inside the copied OneDir folder.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)).resolve()

    if _nuitka_compiled_marker() is not None:
        return Path(sys.argv[0]).resolve().parent

    return Path(__file__).resolve().parents[2]
