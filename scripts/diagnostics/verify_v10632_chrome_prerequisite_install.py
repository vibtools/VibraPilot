#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.vibrapilot.chrome_installer import (  # noqa: E402
    GOOGLE_CHROME_ALLOWED_DOWNLOAD_HOSTS,
    GOOGLE_CHROME_ENTERPRISE_MSI_URL,
    GOOGLE_CHROME_EXPECTED_PUBLISHER,
    validate_download_url,
)
from src.vibrapilot.chrome_runtime import discover_google_chrome  # noqa: E402


def fail(message: str) -> None:
    raise SystemExit("V1.0.6.32 CHROME PREREQUISITE VERIFY: FAIL — " + message)


def main() -> int:
    try:
        validate_download_url(GOOGLE_CHROME_ENTERPRISE_MSI_URL)
    except ValueError as exc:
        fail(str(exc))
    if GOOGLE_CHROME_ALLOWED_DOWNLOAD_HOSTS != frozenset({"dl.google.com"}):
        fail("download host allowlist drift")
    if GOOGLE_CHROME_EXPECTED_PUBLISHER != "Google LLC":
        fail("publisher policy drift")

    backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    qt = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    installer = (ROOT / "src/vibrapilot/chrome_installer.py").read_text(encoding="utf-8")
    authenticode = (ROOT / "src/vibrapilot/windows_authenticode.py").read_text(encoding="utf-8")
    for marker in (
        "require_google_chrome()",
        'launch_args["channel"] = "chrome"',
    ):
        if marker not in backend:
            fail("backend marker missing: " + marker)
    for marker in (
        "class ChromeRequiredDialog(QDialog):",
        "check_chrome_prerequisite_on_startup",
        "start_chrome_install",
        "chrome_install_progress",
    ):
        if marker not in qt:
            fail("UI marker missing: " + marker)
    for marker in ('info.lpVerb = "runas"', 'GOOGLE_CHROME_EXPECTED_PUBLISHER = "Google LLC"'):
        if marker not in installer:
            fail("installer security marker missing: " + marker)
    for marker in ("WinVerifyTrust", "inspect_windows_authenticode"):
        if marker not in authenticode:
            fail("shared Authenticode security marker missing: " + marker)

    runtime = discover_google_chrome()
    print("V1.0.6.32 CHROME PREREQUISITE VERIFY: SOURCE POLICY PASS")
    print(f"Platform: {sys.platform}")
    print(f"Official installer: {GOOGLE_CHROME_ENTERPRISE_MSI_URL}")
    print(f"Required publisher: {GOOGLE_CHROME_EXPECTED_PUBLISHER}")
    print(f"Chrome discovery status: {runtime.status}")
    if runtime.available:
        print(f"Chrome: {runtime.executable_path}")
        print(f"Version: {runtime.version or 'Unavailable'}")
        print(f"Product: {runtime.product_name or 'Unavailable'}")
    else:
        print("Chrome: not detected (the app should show the prerequisite UX on Windows)")
        if runtime.detail:
            print(f"Detail: {runtime.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
