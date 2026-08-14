#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for import_root in (ROOT, SRC):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from vibrapilot.chrome_runtime import discover_google_chrome


def fail(message: str) -> None:
    raise SystemExit(f"V1.0.6.31 CHROME-ONLY VERIFY: FAIL — {message}")


def main() -> int:
    defaults = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
    expected = {
        "browser_runtime_policy_version": 1,
        "use_chrome_channel": True,
        "allow_chromium_fallback": False,
        "browser_executable_path": "",
        "sandbox_enabled": True,
        "http_cache_enabled": True,
        "extensions_enabled": False,
    }
    for key, value in expected.items():
        if defaults.get(key) != value:
            fail(f"default mismatch: {key}={defaults.get(key)!r}")
    backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    for forbidden in (
        'launch_args["channel"] = "chromium"',
        'fallback_args.pop("channel", None)',
        'launch_args.pop("channel", None)',
        'launch_args["executable_path"]',
        '--load-extension=',
    ):
        if forbidden in backend:
            fail(f"forbidden launch marker present: {forbidden}")
    if 'launch_args["channel"] = "chrome"' not in backend or '"chromium_sandbox": True' not in backend:
        fail("mandatory Chrome/sandbox launch markers missing")

    runtime = discover_google_chrome()
    print("V1.0.6.31 CHROME-ONLY VERIFY: SOURCE POLICY PASS")
    print(f"Platform: {os.name}")
    print(f"Chrome discovery status: {runtime.status}")
    if runtime.available:
        print(f"Chrome: {runtime.executable_path}")
        print(f"Version: {runtime.version or 'unavailable'}")
        print(f"Product: {runtime.product_name or 'Google Chrome'}")
        return 0
    if os.name == "nt":
        print("Windows runtime acceptance: BLOCKED — Google Chrome not detected")
        return 2
    print("Windows runtime acceptance: NOT RUN on this platform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
