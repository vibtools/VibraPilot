#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vibrapilot.chrome_installer import (
    GOOGLE_CHROME_APPROVED_DOWNLOAD_PATH,
    GOOGLE_CHROME_ENTERPRISE_MSI_URL,
    GOOGLE_CHROME_EXPECTED_PUBLISHER,
    validate_download_url,
)
from src.vibrapilot.chrome_runtime import discover_google_chrome


def main() -> int:
    if validate_download_url(GOOGLE_CHROME_ENTERPRISE_MSI_URL) != GOOGLE_CHROME_ENTERPRISE_MSI_URL:
        raise SystemExit("V1.0.6.33 VERIFY FAILED: official installer URL policy mismatch")
    if GOOGLE_CHROME_APPROVED_DOWNLOAD_PATH != "/dl/chrome/install/googlechromestandaloneenterprise64.msi":
        raise SystemExit("V1.0.6.33 VERIFY FAILED: approved installer path mismatch")
    print("V1.0.6.33 BROWSER FORENSIC CLOSURE VERIFY: SOURCE POLICY PASS")
    print(f"Platform: {os.name}")
    print(f"Official installer: {GOOGLE_CHROME_ENTERPRISE_MSI_URL}")
    print(f"Required publisher: {GOOGLE_CHROME_EXPECTED_PUBLISHER}")
    runtime = discover_google_chrome()
    print(f"Chrome discovery status: {runtime.status}")
    if os.name == "nt":
        if not runtime.available:
            print(f"Chrome detail: {runtime.detail or 'not available'}")
            return 2
        print(f"Chrome: {runtime.executable_path}")
        print(f"Version: {runtime.version or 'unavailable'}")
        print(f"Product: {runtime.product_name or 'unavailable'}")
        print(f"Publisher: {runtime.publisher or 'unavailable'}")
        print(f"Authenticode trusted: {'yes' if runtime.signature_trusted else 'no'}")
        if runtime.publisher.casefold() != GOOGLE_CHROME_EXPECTED_PUBLISHER.casefold() or not runtime.signature_trusted:
            return 3
    else:
        print("Windows runtime acceptance: NOT RUN on this platform")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
