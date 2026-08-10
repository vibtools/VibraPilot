## v1.0.6.24 — PR-07 Workflow Showcase Page — 2026-08-10

### Added
- New top-level **Workflows** page between Tasks and Workflow Inputs.
- Metadata-driven cards for source-controlled built-in workflows only.
- Authoritative active-workflow status and fail-closed unavailable state.
- Activation UI delegates exclusively to the existing PR-06 atomic workflow switch service.

### Preserved
- Production registry still contains only `share_invite`; no fake/demo/placeholder workflow is added.
- PR-06 state schema, atomic switch/restart/recovery semantics, Task/report/workspace schemas, Browser, licensing, dependencies and CAPTCHA policy remain unchanged.
- Dynamic per-workflow Workflow Inputs remain PR-08 scope.

## v1.0.6.23 — PR-06 Workflow State Persistence + Atomic Switch/Restart — 2026-08-10

### Added
- Schema-v1 `AppData/workflow_state.json` persisting exactly one active built-in workflow identity.
- Absence-only first migration to `share_invite`; corrupt, unsupported and unknown persisted states fail closed.
- Atomic application-level workflow switch transaction with explicit blockers/confirmation, rollback staging, commit-point state replacement and deterministic interrupted-transaction recovery.
- Active workflow identity injection into `AutomationWorker` with no silent Share Invite fallback.
- Restart-after-commit behavior with fail-closed manual-restart handling when post-commit spawn fails.
- PR-06 verification contract and regression coverage.

### Preserved
- Share Invite selectors/Send/Test Mode/retry/manual-review behavior and safety-critical worker paths.
- TaskRuntimeStore, workspace, result/report and settings schemas.
- Browser launch/configuration, persistent profiles, download/upload/extension behavior, licensing and CAPTCHA/security-challenge policy.
- Production registry remains source-controlled and contains only `share_invite`.

### Deferred
- PR-07 Workflow Showcase UI.
- PR-08 dynamic per-workflow Workflow Inputs.
- PR-09 workflow-aware data/report schemas.
- Remaining Browser Windows technical acceptance remains a separate carried track.

## v1.0.6.22 — PR-05 Master Workflow Gate Integration — 2026-08-10

### Added
- In-memory active built-in workflow identity with fail-closed resolution through `WorkflowManager`.
- Source-controlled built-in runtime factory resolution for the existing `share_invite` workflow.
- Generic workflow session, item execution and retry adapters used by `AutomationWorker` through one Master Workflow Gate.
- PR-05 scope contract and dedicated gate/fail-closed regression tests.

### Preserved
- Share Invite selectors, Test Mode/session semantics, email verification, retry/backoff, Test Send Limit, `SecurityChallenge`, `InviteRejected`, uncertain-Send/manual-review and duplicate-send protection are unchanged.
- `process_item`, `process_batch`, `_register_send_click_attempt`, report/persistence schemas, UI/UX, settings, browser lifecycle/configuration, licensing and CAPTCHA policy remain unchanged.
- Active workflow persistence/switching, Workflow UI and dynamic Workflow Inputs remain out of scope for later phases.

## v1.0.6.21 — PR-04 Windows/Python 3.12 CI parity verification fix — 2026-08-10

### Fixed
- Replaced Python-minor-sensitive raw `ast.dump()` parity hashing with `canonical-semantic-ast-v2`; PR-04 runtime source remained unchanged.

## v1.0.6.20 — PR-04 Share Invite workflow extraction — 2026-08-10

### Added
- First source-controlled built-in workflow package under `src/vibrapilot/workflow/share_invite/` with validated manifest and existing VibraPilot logo.
- Explicit built-in registry factory and minimal runtime workflow protocol.
- PR-04 machine-readable scope/parity contract and dedicated extraction tests.

### Changed
- Share Invite-specific browser/session/modal/Send/result methods are encapsulated in `ShareInviteWorkflow`; `AutomationWorker` preserves thin compatibility delegation.

### Preserved
- Safety-critical retry/manual-review state machine, selectors, Test Mode enforcement, exception identity, task/report/persistence schemas, UI, settings, licensing and Chrome/Playwright behavior are unchanged.
- CAPTCHA/security-challenge root-cause work remains deferred under PR-02.

## v1.0.6.19 — Chrome Web Store extension-install follow-up — 2026-08-09

### Confirmed root cause
- Normal VibraPilot Chrome sessions left Playwright's default `--disable-extensions` switch active when explicit unpacked-extension mode was off. Chromium maps that disabled extension-service state to the Chrome Web Store error `Installation is not enabled`.

### Fixed
- Playwright's global `--disable-extensions` default is now always filtered. `extensions_enabled` remains limited to VibraPilot's explicit unpacked side-loading mode.

### Preserved
- Download/upload implementation, managed profiles, Chrome policy, sandbox, browser diagnostics, workflow, TaskRuntimeStore/WorkspaceState schemas, licensing and UI are unchanged.
- Version metadata remains `1.0.6.19`; this is a scope-locked follow-up patch against the official v1.0.6.19 baseline.

## v1.0.6.19 — Browser foundation verification / diagnostics hardening — 2026-08-09

### Confirmed
- Uploaded Windows evidence confirms actual Google Chrome Stable `151.0.7922.76` at `C:\Program Files\Google\Chrome\Application\chrome.exe`, `fallback_used=false`, the managed `slot_1` profile, and a real process command line containing `--no-sandbox`.
- The same evidence exposes a runtime dependency mismatch: Playwright Python `1.60.0` was running while project metadata pins `1.61.0`.

### Fixed
- Browser diagnostics now report expected-vs-actual Playwright compatibility and emit a non-fatal warning on mismatch.
- Diagnostic fallback/error text is sanitized before persistence/logging, including secret-bearing switches and proxy credentials.
- Nested launch diagnostic values retain their JSON scalar types instead of coercing numeric/boolean evidence to strings.
- Added a standalone evidence validator for `Logs/BrowserDiagnostics/slot_N_latest.json`.

### Preserved
- `sandbox_enabled` source default remains unchanged because Sandbox-ON Windows acceptance is still not provided.
- No browser launch policy, fallback behavior, profile architecture, download/upload/extension behavior, workflow, TaskRuntimeStore/WorkspaceState schema, licensing or UI behavior changes.

## v1.0.6.18 — Browser foundation stabilization — 2026-08-09

### Added
- Structured browser identity, fallback, profile, sandbox, CDP and Windows-process diagnostics.
- Non-invasive browser environment evidence for controlled normal-Chrome comparison.

### Preserved
- Existing Chrome-preferred fallback policy, profiles, capabilities, lifecycle, persistence, licensing, Test Mode and workflow. Sandbox default unchanged pending Windows acceptance.

## v1.0.6.17 — Browser capabilities — 2026-08-09

### Added
- Durable browser download lifecycle using Playwright `Download.save_as()` with safe filenames and non-destructive collision handling.
- Blank Download Directory now uses a durable per-Task VibraPilot-managed download folder; explicit configured paths remain unchanged.
- Existing Task card now includes **Downloads** to open the effective Task download directory.
- Generic page file-chooser bridge for explicit user-selected single files, multiple files, or directory upload when requested by the webpage.
- Request-ID protection and lifecycle cleanup prevent stale file-chooser responses from crossing Tasks/pages.
- Unpacked extension directories now validate `manifest.json` existence and JSON object structure at Browser Settings save and browser launch boundaries.

### Preserved
- No Browser Settings keys/defaults changed. No database/workspace schema changed. No automatic upload, Chrome Web Store automation, master workflow engine, Razorpay selector/Send change, licensing change, managed-profile change or new application page.

## v1.0.6.16 — Workspace persistence verification / CI fix — 2026-08-09

### Fixed

- Corrected the historical v1.0.6.12 Qt lifecycle test fixture so it provides the v1.0.6.15 `schedule_workspace_save` MainWindow contract when constructing `TaskSlotWidget` in isolation.
- Removed known trailing whitespace from `UPDATE_LOG.md`.

### Verification / compatibility

- **No production runtime source changes.** The v1.0.6.15 runtime/database/browser/workflow implementation remains byte-frozen.
- GitHub Actions job `93315001000` failed from stale test-fixture interface drift, not a production runtime/database defect.

# Changelog

## v1.0.6.15 — Active workspace persistence — 2026-08-09

### Added

- Added atomic `AppData/state.json` workspace metadata persistence through the dedicated `WorkspaceStateStore` module.
- Restores normal active Task cards with stable slot IDs/order, latest Target URL, run identity and existing SQLite-backed progress/data after restart, logout/re-login or license-invalid workspace teardown.
- Persists the selected application page and safe workspace window geometry/maximized state with multi-monitor clamping.

### Safety / compatibility

- Browsers, login verification, workflows and Send never auto-start during workspace restoration.
- Deliberately Closed Tasks remain archived and are still restored only through **Open Closed Tasks**.
- Existing `TaskRuntimeStore` schema version 1, managed browser profiles, licensing, selectors, Browser Settings and Phase-01 lifecycle remain unchanged.
- Corrupt or unsupported workspace JSON is quarantined and startup falls back to the existing first-run/crash-recovery path.


## v1.0.6.14 — Managed persistent browser + Closed Task recovery — 2026-08-09

### Added

- Promoted the existing Playwright persistent-context implementation into the standard managed browser mode while preserving Google Chrome preference and the existing explicit Chromium fallback policy.
- Blank Profile Directory now resolves to an application-managed persistent profile per Task under the durable VibraPilot data root; explicit custom profile paths retain their prior shared-profile semantics.
- Added managed-profile collision protection, stable `slot_N` identity, safe legacy managed-profile migration, and refusal to use the user's normal Google Chrome `User Data` tree.
- Added **Open Closed Tasks** to the existing Tasks page. Closed Tasks remain stored in the existing SQLite schema and can be reopened with their original run/slot identity, recipient records, progress, Target URL, send-attempt limit usage, manual-review state and result continuity.

### Preserved

- `restore_previous_session` remains disabled; reopening the application or a Closed Task never auto-starts a browser, workflow, login verification or Send.
- No SQLite table/column/schema version change, no permanent-delete operation, no browser-context/signature change and no profile copying/deletion are introduced.
- Phase-01 Open/Close lifecycle, App/Browser Settings, Workflow Inputs, selectors, Test Mode/security checks, licensing, reporting and existing Task processing semantics are preserved.

## v1.0.6.13 — Phase-01 verification / CI stability correction — 2026-08-09

### Fixed

- Reclassified the four-worker SQLite stress test as a correctness/deadlock guard instead of a fixed 15-second storage-throughput SLA.
- Extended the bounded completion guard to 60 seconds so hosted Windows runners are not treated as failed while still making durable SQLite progress.
- Added cleanup retry handling for transient Windows file-sharing locks during temporary-directory teardown after a failed/slow concurrency assertion.

### Verified

- Exact v1.0.6.12 baseline archive SHA-256 and GitHub commit are pinned in `config/verification/v1.0.6.13_phase01_verification_ci_fix_scope.json`.
- `src/vibrapilot/**`, `config/settings.defaults.json`, `requirements.txt`, `requirements-build.txt` and `.github/workflows/ci.yml` are frozen byte-for-byte from the v1.0.6.12 release candidate.
- Re-ran repository verification, the full test suite and standard-library unittest discovery after the harness correction.

### Preserved

- No application runtime, browser lifecycle, Browser Settings, Task UI, workflow/selectors, licensing, persistence/database schema or dependency behavior changes.

## v1.0.6.12 — Browser UI/lifecycle hardening — 2026-08-09

### Fixed

- Task browser status is now an explicit lifecycle: **Closed → Opening → Open → Closing → Closed**.
- The Tasks browser action switches between **Open Browser**, **Opening...**, **Close Browser**, and **Closing...** without reusing the separate **Close Task** action.
- Manual page/context/browser closure synchronizes back to the Task UI through worker-side callbacks, clears stale Browser Ready/login-verification state, and allows reopening the browser without discarding Task/data state.
- Open and Close browser actions are guarded during transitions to prevent overlapping lifecycle commands.
- Application shutdown and logout wait for active browser workers to finish their real cleanup path instead of silently clearing worker references after a fixed timeout.
- Unexpected browser closure optionally performs one bounded automatic restart when the existing Browser Settings policy is enabled; manual close never triggers that restart.
- Activation-to-Workspace transition now safely fits and centers the main window inside the current screen's available geometry instead of reusing the compact activation window's old top-left coordinate.

### Preserved

- No Browser Settings defaults changed.
- Managed persistent profiles, download/upload/extension architecture, and CAPTCHA/stealth changes remain outside this phase.
- Existing Razorpay selectors, Test Mode/security-challenge gates, licensing, Workflow Inputs, reporting and Task processing semantics are preserved.

## v1.0.6.11 — Qt focus lifecycle hardening — 2026-08-09

### Fixed

- Cleared stale focus-ring widget references when Qt emits `destroyed` during Activation-to-Workspace or other widget teardown paths.
- Guarded all focus-manager event, refresh, polish and delayed-tooltip paths with `shiboken6.isValid(...)` before touching the wrapped QWidget.
- Restricted the lifetime correction to `vib_validation_app/focus_manager.py`; application runtime, backend, settings, workflows and `qt_app.py` remain frozen.

### Verification

- Added targeted fake-wrapper tests plus the real PySide6 `deleteLater()` regression reproducer for the previously observed `Internal C++ object already deleted` failure class.
- Re-ran repository verification, the full test suite and standard-library unittest discovery after the focus lifecycle fix.

## v1.0.6.10 — License login durability and recovery — 2026-08-09

### Fixed

- Secure Licora API v2 session storage now uses the per-user VibraPilot data root on Windows (`%LOCALAPPDATA%\Vib Tools\VibraPilot`) unless `VIB_TOOLS_DATA_DIR` explicitly overrides it.
- Existing install-relative `AppData/license.json` is migrated atomically into the durable per-user state location after successful decrypt/validation.
- Device P-256 identity is persisted separately in DPAPI-protected `device_identity.json`, so stale/corrupt session state no longer silently replaces the device key/device ID.
- `DEVICE_KEY_MISMATCH` and `DEVICE_REVOKED` perform one bounded restart-safe recovery attempt using the same P-256 key with a fresh device ID.
- `LIMIT_REACHED` after a rejected device identity now stops with an explicit stale-device cleanup message instead of retrying and consuming additional server slots.
- Confirmed logout waits for deactivation and rotates the revoked device ID without generating a replacement P-256 key; the next login retains the existing secure key identity.
- New activation cannot overtake an in-flight background deactivation request.
- Temporary network, rate-limit and server-response failures no longer invalidate a still-locally-valid signed access-token session during background re-check.

### Preserved

- Secure Licora API v2 request/response envelope, RS256 access-token verification, P-256 device request signing, refresh-token rotation and server URL/endpoint contract remain unchanged.
- No browser, Task workflow, selectors, Workflow Inputs, App/Browser Settings UI, reporting or dependency changes.

## v1.0.6.9 — Workflow Inputs verification / persistence fix — 2026-08-09

### Fixed

- `Save Workflow Inputs` now snapshots the four workflow values before applying UI edits and restores the snapshot if the settings write fails.
- `Reset Workflow Inputs` now catches settings-save failures, restores the exact pre-reset values, refreshes the page and reports the error instead of leaving an in-memory partial reset.

### Preserved

- The dedicated Workflow Inputs page, field set and no-selector scope remain unchanged from v1.0.6.8.
- Backend automation behavior, selectors, browser launch/context behavior, App/Browser Settings, task/report/persistence schemas, licensing and dependencies remain byte-frozen from the official v1.0.6.8 baseline.
- The four Workflow Inputs remain settings-backed values only; this release does not add a new browser-workflow consumer.

## v1.0.6.8 — Workflow Inputs separation — 2026-08-09

### Added

- Dedicated top-level **Workflow Inputs** page between Tasks and Reports.
- Existing `default_full_name`, `default_number`, `fallback_name` and `update_click_count` settings are now edited only from the dedicated Workflow Inputs page.
- Added workflow-input Save and Reset actions without introducing a workflow selector while only one workflow exists.

### Changed

- Removed the four workflow-specific values from **App Settings**.
- `default_target_url` remains in App Settings as an application/task-level value.

### Preserved

- Existing backend, browser, task, persistence, licensing, reports and automation behavior remain unchanged.
- Browser Settings remain browser-only and unchanged.
- No workflow fields were added to browser settings.

## v1.0.6.7 — Windows SQLite concurrent-task hardening — 2026-08-09

### Fixed

- Serialized in-process `TaskRuntimeStore` writers with a shared lock before SQLite's WAL writer lock.
- Kept `PRAGMA synchronous` at SQLite's durable default rather than weakening disk-flush guarantees.
- Added a four-writer Windows concurrency regression gate with explicit lock/thread failure detection.

### Preserved

- No changes to TaskRuntimeStore schema, workspace contract, UI, browser, workflow, selectors, license protocol or public APIs.
- Existing per-recipient atomic item/result/progress persistence remains unchanged.

## v1.0.6.7 — VP-PROD-MT-LR-001 verification fixes — 2026-08-09

### Fixed

- Corrected the Task-card frozen stylesheet binding so the application can construct Tasks normally at startup.
- Allowed blocked critical UI-event producers to exit during an explicit worker stop/close instead of waiting forever on a saturated UI queue.
- Made the conservative pre-Send manual-review state immediately authoritative in the result ledger as well as the item row.
- Corrected the Task metric label to **Send Attempts / Limit**.

### Preserved

- No changes to selector order, Test Mode checks, retry limits, browser lifecycle, `TaskRuntimeStore` schema, context recycle semantics or licensing protocol.

## v1.0.6.5 — Production multi-task / long-run hardening — 2026-08-09

### Added

- Added SQLite-backed `TaskRuntimeStore` with WAL journaling, foreign-key integrity and unique item identity per `run_id + item_index`.
- Added source/valid/invalid/duplicate import accounting and explicit reconciliation metrics.
- Added resumable per-Task progress with persisted `current_index`, success/failed counts, send-limit usage and manual-review state.
- Added conservative `manual_review_required` handling for ambiguous post-Send outcomes so unknown send results are never auto-retried.
- Added Browser Context recycling by finalized item count and elapsed minutes with storage-state preservation and Target URL restoration.
- Added deterministic worker stop/join behavior and close guards so live worker references are not cleared before cleanup completes.
- Added a bounded UI event queue (`4096`) and a maximum `250` events consumed per UI timer tick.
- Added authoritative full-result loading from SQLite with current-result uniqueness and Task-filtered Reports.
- Added `max_concurrent_tasks` scheduling with a default limit of `4` and persistent-profile collision protection.
- Added release-source archive hygiene verification that rejects runtime/private/cache paths and unsafe ZIP entries.

### Preserved

- Existing site-specific selectors, browser launch signature/defaults, Test Mode checks, retry policy, Test Send Limit, Licora API v2 contract, existing Settings keys, layout/components and source formats remain unchanged.
- No fake UI page, permanent discard/delete operation, migration workflow or packaging-only shortcut was introduced.

## v1.0.6.4 — Phase-02 Step-002 verification / fix — 2026-08-08

### Fixed

- `LicenseManager.load()` now rejects locally tampered or expired RS256 access-token payloads after DPAPI decryption.
- `LicenseManager.logout()` now waits for confirmed `/deactivate` success before clearing the protected local session.
- Local file/state removal during logout now occurs only after confirmed server-side deactivation.

### Preserved

- `config/AppConfig/licensing_public.py`, the Licora API v2 request/response contract, P-256/RS256 cryptographic scheme, activation flow, UI, browser automation, tasks, settings, workflows and dependencies remain unchanged.

### Verification

- Added machine-readable fix scope and frozen-file hashes for all prohibited files.
- Added targeted regression tests for token-tamper rejection and deactivate-before-clear semantics.
- Re-ran static repository verification, full pytest and standard-library unittest discovery.

## v1.0.6.3 — Phase-02 Step-002 Secure Licora API v2 — 2026-08-08

### Added

- Added `config/AppConfig/licensing_public.py` containing only public Licora API v2 configuration and the server RSA public signing key.
- Added `src/vibrapilot/licensing_v2.py` with P-256 device-key generation, canonical request signing, RS256 access-token verification, refresh-token rotation support and Windows DPAPI helpers.
- Added protected local license persistence for normalized license, user email, device ID, P-256 private key, signed access token and rotating refresh token.
- Added background `status` / refresh revalidation through the Secure Licora API v2 contract.
- Added browser-independent unit coverage for token verification, crypto helpers and license-manager behavior.

### Changed

- `LicenseManager` now uses `/api/v2/activate`, `/api/v2/status`, `/api/v2/refresh` and `/api/v2/deactivate` instead of the former legacy verify API.
- License login and re-check paths enforce the API v2 envelope, request ID / timestamp, device ID, app ID and nonce contract.

### Removed

- Removed desktop reliance on the former shared/master Licora API v1 secret and `/api/verify.php` flow.
- Removed the real API key from tracked desktop source/configuration.

### Preserved

- Activation screen layout, normal workspace UI, browser automation, tasks, settings, reports, workflow safety and business logic remain unchanged.

## v1.0.6.2 — Phase-01 verification / fix — 2026-08-08

### Fixed

- Added `qt_app.py` to the public repository verifier's required-file set.
- Added explicit `config/AppConfig` completeness checks to the repository verifier.
- Removed the stale `src/vibrapilot/legacy_ui.py` shim after confirming there were no imports or runtime dependencies.
- Removed generated `src/vibrapilot/__pycache__/` bytecode from the project tree.
- Extended AppConfig tests to cover Support and Social modules and reject mixed product version/date sources.

### Verification

- Re-ran compile verification, repository verification, full pytest and standard-library unittest discovery.
- Re-checked browser/settings/report/workflow contracts against the official v1.0.6.1 baseline.

### Preserved

- No runtime application behavior, browser automation, settings semantics, workflow/selectors, licensing API, retry/safety logic, reports, persistence or frozen design-source behavior changed.

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
