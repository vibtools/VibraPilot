# Changelog

## v1.0.6.1 — GitHub CI deterministic backend-contract fix — 2026-08-08

### Fixed

- Replaced Python-version-dependent raw `ast.dump()` backend implementation hashes with a canonical semantic AST hash format.
- Regenerated frozen class/helper contract hashes from the private v1.0.6 source baseline without changing production backend source.
- Added contract-algorithm metadata so stale/incompatible verification contracts fail explicitly.
- Added regression coverage for production contract hashes and empty version-specific AST fields such as `type_params`.
- Upgraded GitHub CI to Node 24-native `actions/checkout@v5` and `actions/setup-python@v6`, removing the deprecated Node 20 action warning from the repository workflow.

### Repository policy

- Public CI documentation remains under `docs/`.
- Private development/source-baseline material remains under gitignored `project/` and is optional for local cross-checking only.

### Preserved

- Application version remains **1.0.6.1**.
- `src/vibrapilot/backend.py` and all runtime application/browser/workflow behavior are unchanged.

## v1.0.6.1 — GitHub CI repository hygiene and private-baseline decoupling — 2026-08-08

### Fixed

- Removed GitHub CI's dependency on the gitignored private `project/` workspace.
- Added `config/verification/backend_v1.0.6_contract.json` as the public machine-readable backend parity contract.
- Updated backend contract tests and repository verification to work in clean public checkouts while retaining optional private-baseline cross-checks during local development.
- Removed private `project/` files from public required-file checks and fixed public documentation links that pointed into `project/`.
- Upgraded CI to Node 24-native `actions/checkout@v5` and `actions/setup-python@v6`.
- Removed stale pre-rebrand source/launcher paths that conflict with VibraPilot repository hygiene and branding contract tests.

### Repository policy

- `docs/` is the public documentation surface.
- `project/` is the private development workspace, remains gitignored, and is never a CI dependency.

### Preserved

- Application version remains **1.0.6.1**.
- Runtime application/browser/workflow behavior is unchanged.

## v1.0.6.1 — GitHub Actions cross-platform verification fix — 2026-08-08

### Fixed

- Fixed Windows GitHub Actions false-positive frozen-design hash failures caused by checkout line-ending conversion from LF to CRLF.
- Frozen Vib Tools text-contract hashes are now computed from canonical LF content, so identical source no longer appears as design drift solely because of runner platform.
- Added `.gitattributes` rules that keep source/configuration/documentation text on LF and explicitly protect binary assets from line-ending normalization.
- Fixed the Windows CI contract-test import path by setting `PYTHONPATH` to the repository `src` directory, preventing the next-step `ModuleNotFoundError: vibrapilot` after static verification succeeds.

### Preserved

- No runtime application, browser automation, workflow, selector, settings, licensing, UI behavior or frozen design-source content was changed.
- Application version remains **1.0.6.1**.

## Branding Baseline — VibraPilot — 2026-08-08

### Changed

- Renamed the product identity from the legacy product name to **VibraPilot**.
- Renamed the production Python package to `src/vibrapilot/`.
- Renamed Windows build/release output and the PowerShell launcher to **VibraPilot**.
- Rebranded runtime window titles, activation copy, About/product metadata, documentation manifests and project metadata.
- Wired the source-controlled VibraPilot logo/icon from `assets/icons/` into the activation view, main header, titlebar, QApplication and Windows taskbar identity.
- Added root icon assets to the PyInstaller data bundle.

### Preserved

- Application version remains **1.0.6.1**.
- No workflow, selector, browser automation, task, dashboard, report, settings, license-validation, retry, safety, data, persistence or shutdown behavior was changed by this branding baseline.
- The current site-specific workflow remains intact as the existing built-in workflow; Third-party site names remain only where technically required by the preserved built-in workflow or attribution.

### Documentation

- Updated README, CHANGELOG, UPDATE_LOG, VERSIONING, NOTICE, citation/docs manifests, project metadata, forensic documentation and path references for the VibraPilot identity.
- Added `docs/updates/v1.0.6.1-vibrapilot-branding.md`.

## 1.0.6.1 — Browser Settings Production Hardening — 2026-08-07

### Fixed

- Audited the complete Browser Settings page against the project-pinned Playwright 1.61/Chromium runtime contract.
- Fixed **Allow Popups** so the UI value overrides Playwright's built-in `--disable-popup-blocking` default.
- Fixed **Background Throttling Enabled** so enabled state suppresses Playwright's built-in background-throttling-disabling arguments.
- Fixed unpacked **Extension Loading** by suppressing Playwright's built-in `--disable-extensions` default and selecting Playwright's full `chromium` channel for extension sessions when no custom executable is supplied.
- Fixed **DevTools Auto Open** for the project-pinned Playwright 1.61 API by using Chromium's `--auto-open-devtools-for-tabs` switch instead of the removed `launch(devtools=...)` keyword.
- Fixed **Audio Enabled** in headless mode so ON suppresses Playwright's automatic `--mute-audio` default and OFF remains explicitly muted in both headed and headless launches.
- Extended Chrome-channel to bundled-Chromium fallback to persistent browser-context launches.
- Restricted **Restore Previous Browser Session** to persistent-context mode where session restoration is meaningful.
- Browser Settings now re-render from backend `SettingsManager` values after save/reset so UI values match persisted runtime configuration.
- Added dependency validation so session restore cannot be saved with a non-persistent profile or contradictory window-position coordinates.

### Removed

- Removed Browser Settings informational/read-only cards; the page now contains editable runtime-backed controls only.
- Removed duplicate `hardware_acceleration_enabled`; `gpu_enabled` is now the single **GPU / Hardware Acceleration Enabled** control. Existing installations migrate the previous effective GPU state.
- Removed the hidden legacy `disable_image_font_media_loading` runtime key after one-time migration to the explicit Image/Font/Media blocking controls.

### Documentation

- Updated product version to **1.0.6.1** across runtime/build/package metadata.
- Expanded README browser lifecycle/application semantics.
- Added `UPDATE_LOG.md`, `docs/updates/v1.0.6.1.md`, and the 147-control `docs/updates/v1.0.6.1-browser-settings-audit.md`.
- Established cumulative CHANGELOG + per-release Markdown update-note policy for subsequent production releases.

### Preserved

- v1.0.6 baseline automation workflow and all 54 `AutomationWorker` methods.
- existing site-specific selectors and business workflow.
- Licensing, dashboard, tasks, reports and live-log behavior outside the approved browser-settings scope.

## 1.0.6 — Vib Tools Desktop UI Edition

### Added

- Official Vib Tools PySide6 desktop interface with Dashboard, Tasks, Reports, Live Logs, App Settings, advanced Browser Settings and About pages.
- Exact frozen Vib Tools design modules and token source with SHA-256 drift verification.
- Centered Vib Tools license activation experience.
- Static repository verifier and backend/design parity tests.
- Deterministic Windows x64 ONEDIR build/release pipeline.
- Forensic design audit and feature parity documentation.

### Preserved

- VibraPilot v1.0.6 core backend class/method contract.
- All 54 `AutomationWorker` methods.
- Licora activation/revalidation behavior.
- Test Mode/send-limit safety behavior.
- Browser/session/retry/persistence/reporting logic.
- TXT/CSV/XLSX/XLS data support and CSV/Excel export.

### Changed

- Replaced legacy CustomTkinter UI with the official Vib Tools PySide6 design contract.
- License base URL and API-key configuration are source-controlled constants rather than a PowerShell/environment injection flow.
