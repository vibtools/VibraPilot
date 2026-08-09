# Changelog

## v1.0.6.8 — VP-WORKFLOW-INPUTS-001 — 2026-08-09

### Added

- Added a dedicated top-level **Workflow Inputs** page and a form-metadata-only `src/vibrapilot/workflow_inputs.py` module.
- Added isolated Save/Reset handling for the existing workflow input keys.

### Changed

- Moved `default_full_name`, `default_number`, `fallback_name` and `update_click_count` out of the App Settings UI without renaming or migrating their persisted keys.
- Preserved the existing View shortcuts for Dashboard, Tasks, Reports, Live Logs, App Settings and Browser Settings while inserting Workflow Inputs after Tasks.

### Preserved

- `default_target_url` remains in App Settings. Backend worker logic, Browser Settings, task workflow, selectors, SQLite runtime persistence and Licora Secure API v2 are unchanged.
- No fake/single-option workflow selector is included.

### Verification

- Added `config/verification/v1.0.6.8_workflow_inputs_scope.json` plus workflow-input persistence/UI/scope regression tests.
- Added `docs/updates/v1.0.6.8-workflow-inputs-separation.md` and `docs/verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md`.

### Windows SQLite concurrent-write verification correction

- Fixed a Windows-only multi-worker persistence contention failure where four concurrent task writers could exceed the 15-second verification window and leave a temporary SQLite file handle active during test cleanup.
- Added process-local write serialization before SQLite's WAL writer lock and an atomic recipient/result/progress transaction used by the worker hot path.
- Preserved FULL-synchronous WAL durability; no `synchronous=NORMAL/OFF` durability downgrade is used.
- Scope remains limited to `TaskRuntimeStore` concurrent-write persistence and the two directly connected worker persistence methods.


## v1.0.6.7 — VP-PROD-MT-LR-001 forensic verification/fix — 2026-08-08

### Fixed

- Removed a duplicated `@classmethod` decorator from `TaskSlotWidget.task_qss`; the double descriptor made the startup stylesheet call fail with `TypeError` before the main UI could open.
- Made critical worker UI-event backpressure shutdown-aware so a saturated 4096-event queue cannot keep a stopping/closing worker alive indefinitely. Normal-operation critical events still apply backpressure.
- Persist the pre-Send manual-review crash marker into both the task item and authoritative result ledger before Playwright invokes the Send click.
- Clarified the Task metric label to **Send Attempts / Limit** while preserving the existing conservative send-click counting semantics.
- Added a source-archive verifier that rejects runtime/private/cache paths and unsafe ZIP members before a source baseline is published.

### Packaging

- The user-frozen v1.0.6.5 ZIP was found to contain gitignored runtime/private data (`AppData`, Logs, private `project/` records and Python caches) despite the v1.0.6.5 release-hygiene contract. v1.0.6.7 release/baseline packaging excludes those paths; existing runtime data remains preserved when applying the source delta to a working installation.

### Preserved

- `LicenseManager`, Licora API v2, P-256/RS256 behavior, Razorpay Share Invite selectors/Send sequence, Browser Settings contract, `ActivationPage`, `TaskRuntimeStore`, data-import semantics and all unrelated UI/UX remain unchanged.

### Verification

- Added `config/verification/v1.0.6.7_vp_prod_mt_lr_verification_fix_scope.json` anchored to the exact uploaded v1.0.6.5 ZIP SHA-256.
- Added regression coverage for startup decorator correctness, shutdown queue saturation, pre-click result-ledger durability and clean source-ZIP verification.
- Added `scripts/verify_source_archive.py` for future source baseline/release ZIP validation.

## v1.0.6.5 — VP-PROD-MT-LR-001 production runtime hardening — 2026-08-08

### Added

- Added SQLite-backed per-task runtime/checkpoint/result persistence with unique run IDs, atomic state updates and restart recovery discovery.
- Added import reconciliation counters for source, valid, invalid, duplicate and accepted rows.
- Added Task filtering to Reports and disk-backed full result export while keeping the visible table bounded to recent outcomes.
- Added a configurable `max_concurrent_tasks` production guard with approved default `4`.
- Added shared-persistent-profile collision protection for concurrent task launches.
- Added production scope/soak/recovery/report/worker/queue regression tests.

### Fixed

- Made `batch_size` a real sequential checkpoint boundary without introducing parallel Send operations.
- Made `auto_save_interval` a real seconds-based periodic persistence setting; finalized recipient outcomes remain immediately durable.
- Fixed Browser Context item/time recycle accounting so successful finalized recipients contribute to recycling thresholds.
- Made worker shutdown deterministic; UI/task references are retained when browser cleanup exceeds the wait window.
- Bounded the shared UI event queue to 4096 entries and limited each UI timer drain to 250 events.
- Replaced unbounded duplicate report-event accumulation with one authoritative latest outcome per recipient/run item.
- Preserved ambiguous post-Send outcomes as manual-review recovery state; automatic retry remains forbidden.

### Preserved

- Licora API v2, P-256/RS256 behavior, `LicenseManager`, Razorpay Share Invite selectors/Send sequence, Test Mode/security rules, `ActivationPage`, Browser Settings contract, branding and Vib Tools design foundation remain outside the approved runtime surface.

### Documentation

- Added `docs/updates/v1.0.6.5-production-multi-task-long-run-stability.md`.
- Added `docs/verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md`.
- Synchronized README, UPDATE_LOG, VERSIONING, PROJECT_STRUCTURE, COMPATIBILITY, ROADMAP and documentation index.

## v1.0.6.4 — Phase-02-Step-002 forensic verification/fix — 2026-08-08

### Fixed

- Persist the P-256 device private key before the first activation request and retain the same device key across logout, license switching and restart, preventing server/client public-key drift after ambiguous activation/deactivation outcomes.
- Persistently invalidate ambiguous one-shot refresh credentials before fresh activation recovery so a restart cannot replay an old refresh token.
- Separate long-running API validation from the short UI-facing license state lock; dashboard license reads no longer wait behind remote HTTP I/O.
- Restore protected legacy/v2 license sessions through the existing activation shell at startup and allow periodic recheck to refresh an expired access token instead of stopping when the local token expires.
- Cache successfully verified access-token state so frequent dashboard polling does not repeatedly parse the pinned RSA key and verify the same RS256 token.
- Add crash-safer license-cache writes using flush/fsync before atomic `os.replace()`.
- Correct release-source hygiene after the supplied v1.0.6.3 archive was found to contain gitignored runtime/private/cache paths.
- Configure pytest source imports so the documented plain `python -m pytest -q` invocation matches repository behavior.
- Make the documented direct `python -m unittest discover -s tests -p "test_*.py" -v` command self-contained by bootstrapping the repository `src` layout inside the ten unittest modules that import `vibrapilot`; this removes the Command Prompt/PowerShell `PYTHONPATH` mismatch without changing runtime application code.

### Verification

- Added a v1.0.6.4 fix-scope contract anchored to the exact SHA-256 of the user-frozen v1.0.6.3 archive.
- Expanded LicenseManager tests for pre-request key durability, key continuity, ambiguous refresh persistence, state-lock non-blocking behavior, corrupt-cache fail-closed behavior and atomic-save cleanup.
- Expanded API v2 protocol/crypto tests for stable server error propagation, network/redirect/non-JSON/protocol failure, token header/claim/time/device mismatches and invalid signatures.
- Added release-path checks that reject `AppData`, `Logs`, `Reports`, `FailedData`, `project`, `__pycache__` and `.pytest_cache` from the clean public baseline.

### Preserved

- `AutomationWorker`, selectors, `TaskItem`, `TaskState`, `ActivationPage`, Browser Settings contract, data/report behavior, safety/retry controls, Playwright workflow and the public `licensing_v2.py` protocol implementation remain outside the approved fix surface.

### Documentation

- Added `docs/updates/v1.0.6.4-phase-02-step-002-verification-fix.md`.
- Added `docs/verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md`.
- Synchronized README, licensing/getting-started guidance, versioning, documentation index and release metadata.

## v1.0.6.3 — Phase-02-Step-002 Secure Licora API v2 client — 2026-08-08

### Added

- Added `config/AppConfig/licensing_public.py` with the production HTTPS Licora base URL, `vibrapilot` App ID, API v2 endpoint paths and pinned RSA public signing key/fingerprint.
- Added `src/vibrapilot/licensing_v2.py` implementing P-256 device proof, exact canonical request signing, RS256 access-token verification and activate/status/refresh/deactivate flows.
- Added schema-v2 protected licensing persistence, rotating refresh credentials, atomic writes and legacy-cache migration.
- Added Phase-02 crypto/protocol/persistence tests and a canonical AST scope-freeze contract.

### Changed

- Replaced the active desktop API v1 shared/master-key licensing flow with Licora Secure API v2.
- Promoted the verified Phase-02-Step-002 source version to **1.0.6.3**.
- App Settings now describes the Secure API v2 trust model instead of a private embedded API-key deployment.

### Security

- Removed active client dependence on `X-API-Key`, API v1 Bearer/shared credentials and `/api/verify.php`.
- Pinned only the Licora server **public** signing key; no server private key is present in the project.
- Windows DPAPI protects the license key, P-256 device private key, access token and refresh token before persistence.
- Refresh tokens are one-time rotating credentials and are not blindly replayed after ambiguous failures.

### Preserved

- `AutomationWorker`, selectors, `TaskItem`, `TaskState`, ActivationPage, Browser Settings contract and validated task/report/safety/browser behavior are unchanged from v1.0.6.2.

### Documentation

- Added `docs/updates/v1.0.6.3-phase-02-step-002-secure-licensing.md`.
- Added `docs/verification/PHASE02_STEP002_V1.0.6.3_VERIFICATION.md`.
- Updated README, licensing guide, AppConfig documentation, versioning and release metadata.

## v1.0.6.2 — Phase-01 forensic verification and completion — 2026-08-08

### Fixed

- Removed stale active pre-rebrand source/launcher paths that survived an overwrite-only local merge and caused repository verification/tests to fail.
- Completed the approved Phase-01 support/social configuration using only confirmed Vib Tools public endpoints; removed the unverified developer-portal value.
- Completed the approved About/company metadata fields and bound verified company/support content to the existing About-page structure.
- Hardened AppConfig validation for real calendar dates, numeric release versions, required string sequences, support email format and strict boolean social flags.
- Added regression coverage for the completed AppConfig validation and current support/social contract.

### Version

- Promoted the verified configuration baseline to **1.0.6.2**.
- The validated browser automation, Licora v1 licensing behavior, selectors, Browser Settings, task/report/safety/retry/persistence logic and frozen Vib Tools UI contract remain unchanged.
- Licora API v2 and `licensing_public.py` remain reserved for Phase-02.

### Documentation

- Added `docs/updates/v1.0.6.2-phase-01-verification-fix.md`.
- Updated README, UPDATE_LOG, VERSIONING, AppConfig documentation, documentation manifests and private `project/` forensic records.

## v1.0.6.1 — Phase-01 AppConfig centralization — 2026-08-08

### Added

- Added authoritative `config/AppConfig/` modules for application identity, About/company copy, public support/documentation URLs and social/community metadata.
- Added `src/vibrapilot/app_config.py` as the validated read-only runtime facade.
- Added AppConfig/static-metadata, About binding, support/social and build-binding regression coverage.
- Added public AppConfig architecture/update documentation and private gitignored Phase-01 development records.

### Changed

- Backend compatibility constants, package version metadata and Windows build name/version now consume the central AppConfig source.
- Activation/company identity and About-page content now resolve from AppConfig while preserving the established UI design and displayed product identity.
- Repository verification now enforces AppConfig completeness, metadata consistency and the Phase-01 licensing boundary.

### Preserved

- Application version remains **1.0.6.1**.
- Licora URL/API key/request contract, `LicenseManager`, `AutomationWorker`, selectors, Browser Settings, task/report/safety/retry/persistence behavior and frozen design source are unchanged.
- Licora API v2 and licensing-public configuration remain reserved for Phase-02.

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
