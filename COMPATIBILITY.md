# Compatibility

## Supported release target

- Windows 10/11 x64
- Python 3.12 x64 for source/build workflows
- PySide6 6.7+
- Chromium installed through Playwright 1.61
- Licora v5.2.1+ Secure API v2 server contract for desktop licensing

## Runtime dependencies

The source environment requires PySide6, pandas, requests, `cryptography`, Playwright, openpyxl, xlrd and defusedxml. `cryptography` supplies P-256 device proof and RS256 access-token verification. `build.py` packages an ONEDIR Windows application and copies the Playwright Chromium browser alongside it.

## Licensing platform behavior

Persistent sensitive licensing data uses Windows DPAPI and therefore the production licensing cache is Windows-user-bound. The persistent P-256 device key is retained across logout/license switching to preserve the Licora device binding, while protected license/session tokens are cleared on logout. Public Licora configuration and the pinned server public signing key are portable source metadata; the server private signing key is never a client dependency.

## UI fidelity

The official UI source contract is reused exactly. Windows DPI scaling and font rasterization may create minor rendered-pixel differences between machines; release acceptance should be performed at the deployment DPI/resolution.
