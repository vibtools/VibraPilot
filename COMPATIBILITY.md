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

## Production task runtime storage

`VP-PROD-MT-LR-001` uses Python's standard-library `sqlite3` module for the local `AppData/task_runtime.sqlite3` task/recovery/result ledger; no external database service or new Python package is required. The store is local to the configured VibraPilot data root and uses short-lived connections, WAL mode, foreign-key enforcement and a busy timeout for multiple worker threads.

Multiple task workers remain independent Playwright owners. The approved default concurrent-worker limit is 4, and a shared persistent browser profile cannot be claimed by two active tasks at the same time.

## v1.0.6.7 verification/fix compatibility

The v1.0.6.7 correction keeps Python 3.12, Windows x64, PySide6, Playwright, Licora API v2 and the v1.0.6.5 local SQLite runtime schema unchanged. No runtime dependency was added. `scripts/verify_source_archive.py` uses only the Python standard library. Existing `AppData` is preserved when applying the delta; clean source baseline archives must exclude runtime/private/cache paths.

## v1.0.6.8 Workflow Inputs compatibility

No runtime dependency, browser engine, SQLite schema, licensing protocol or settings-key migration is introduced. Existing `settings.json` values for `default_full_name`, `default_number`, `fallback_name` and `update_click_count` load unchanged through `SettingsManager`; only their UI ownership moves to Workflow Inputs.


## v1.0.6.9 Workflow Inputs verification/fix compatibility

No dependency, settings-key, browser engine, SQLite schema, licensing protocol, selector or task-workflow change is introduced. The only runtime correction is page-local Save/Reset failure containment in `qt_app.py`; successful persistence behavior and the v1.0.6.8 Workflow Inputs ownership model are unchanged.


## v1.0.6.10 license-state compatibility

On Windows without an explicit `VIB_TOOLS_DATA_DIR`, licensing state is stored under `%LOCALAPPDATA%\Vib Tools\VibraPilot`. Existing install-relative `AppData/license.json` is copied once when the durable cache does not yet exist. Sensitive license, P-256 private-key and token values remain Windows-DPAPI protected. No new Python/runtime dependency or Licora API endpoint is introduced.
