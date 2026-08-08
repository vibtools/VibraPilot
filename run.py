#!/usr/bin/env python3
"""Launch VibraPilot — Vib Tools Desktop UI Edition."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibrapilot.qt_app import main

if __name__ == "__main__":
    raise SystemExit(main())
