# Compatibility

## Supported release target

- Windows 10/11 x64
- Python 3.12 x64 for source/build workflows
- PySide6 6.7+
- Chromium installed through Playwright 1.61

## Runtime dependencies

The source environment requires PySide6, pandas, requests, Playwright, openpyxl, xlrd and defusedxml. `build.py` packages an ONEDIR Windows application and copies the Playwright Chromium browser alongside it.

## UI fidelity

The official UI source contract is reused exactly. Windows DPI scaling and font rasterization may create minor rendered-pixel differences between machines; release acceptance should be performed at the deployment DPI/resolution.
