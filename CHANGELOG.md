## v1.0.6.32 — Chrome Prerequisite UX + Secure Install — 2026-08-14

- Adds startup, Open Browser and backend Google Chrome prerequisite checks on top of the v1.0.6.31 Chrome-only runtime foundation.
- Adds a user-consented **Google Chrome Required** dialog with Download & Install, Re-check and Not Now actions.
- Downloads only the code-owned Stable x64 Google Enterprise MSI over HTTPS from `dl.google.com`, using atomic partial-file handling and SHA-256 evidence.
- Requires Windows Authenticode trust and signer publisher **Google LLC** before any installer execution.
- Runs the verified MSI through elevated Windows Installer, handles UAC cancellation/failure distinctly, and requires post-install genuine Google Chrome re-detection.
- Preserves Playwright Chrome-only launch, mandatory sandbox, normal cache default, managed profiles, workflows, licensing, persistence and all non-browser functionality.
- Build/Nuitka/WiX/package changes remain deferred.

## v1.0.6.31 — Chrome-Only Runtime Foundation — 2026-08-14

- Enforced Playwright `channel="chrome"` as the only production browser engine; removed Chrome-to-Playwright-Chromium retry paths.
- Made Chromium sandboxing mandatory for browser launch and changed the source/default migration policy to sandbox enabled.
- Changed normal HTTP cache policy to enabled by default while preserving explicit resource-blocking/cache controls.
- Added a versioned browser-runtime policy migration so stale settings cannot re-enable fallback, custom executable selection, sandbox-off, or unpacked Chromium extension mode.
- Added Windows Google Chrome discovery/identity foundation in `src/vibrapilot/chrome_runtime.py`.
- Removed browser-engine/fallback/sandbox/custom-binary/unpacked-extension controls from editable Browser Settings and replaced them with a read-only Chrome-only runtime policy/status card.
- Extended diagnostics with a Chrome-only policy compliance result while preserving the existing diagnostics schema and historical engine classifications.
- Preserved application-managed persistent profiles, Task isolation, workflows, licensing, persistence, downloads/uploads, and build/installer surfaces.
- Chrome download/install UX is intentionally deferred to the separately approved Phase 2. Build-system Chromium cleanup is also deferred until all functional updates are complete.

## v1.0.6.30 — Workflow Plugin System — 2026-08-12

### Added
- Trusted local `.vpworkflow` loading with manifest/schema/API validation, staging and atomic install into VibraPilot-managed workflow storage.
- Unified built-in + installed workflow catalog while preserving the existing one-active-workflow switch/restart model.
- Workflow-selector based Workflow Inputs, a new Workflow Settings page, declarative Task inputs/settings, Workflow Step and workflow-defined metric rendering.
- Atomic per-workflow settings and per-Task workflow configuration/runtime UI state stores.

### Changed
- Task cards keep Core lifecycle controls but move Target URL/data/extra configuration into Core-rendered Task Settings.
- App Settings now exposes user-facing global processing/UI/output controls only; failed/unprocessed-data preservation and running-task close confirmation are always enforced.
- New Tasks no longer inherit a global default Target URL; URL requirements are workflow/task-schema controlled.

### Fixed
- Restored the frozen `@staticmethod` descriptor on `MainWindow._transaction_root_has_directories(root)`, preventing the v1.0.6.30 Workflows-page registration crash that left the workspace shell half-built.
- Added descriptor-level startup regression verification so instance-bound helper signature/decorator drift is caught even when PySide6 runtime tests are unavailable.

### Preserved
- Share Invite business selectors/sequence, browser lifecycle and profile isolation, TaskRuntimeStore schema, atomic workflow switch/recovery, reports/logs, licensing/device identity and existing CI remain preserved.
- Lightweight `TaskSlotWidget` construction used by the frozen browser-lifecycle regression harness remains compatible when MainWindow-only workflow host attributes are absent.

## v1.0.6.28 — PR-11 E2E Windows / Multi-Task Regression — 2026-08-10

### Added
- Verification-only target-Windows acceptance runner with sanitized evidence and resumable 35-gate matrix.
- Harmless localhost download/upload/storage fixtures for real browser capability checks.
- Read-only PR-11 evidence verifier and zero-production-source freeze contract.

### Preserved
- Production `src/vibrapilot/**`, Browser/Task/workflow recovery behavior, schemas, licensing, dependencies, CI workflow and defaults remain frozen. PR-12 packaging is not started.

## v1.0.6.27 — PR-10 Workflow Error Handling / Recovery — 2026-08-10

### Added
- Explicit user-confirmed workflow-state recovery with crash-safe PREPARED/COMMITTED staging.
- Explicit Workflow Input recovery from source-controlled defaults with forensic quarantine preservation.
- Distinct `workflow_recovery_error` and `workflow_runtime_error` control-plane domains.
- Active source-controlled runtime-factory preflight before browser worker creation.

### Preserved
- PR-09 Task/database/workspace/report schemas, Share Invite runtime, Browser behavior, licensing, CAPTCHA policy, dependencies and CI remain unchanged. Production registry remains `share_invite` only. PR-11 remains NOT STARTED.

## v1.0.6.26 — PR-09 Workflow Data/Persistence/Reporting Compatibility — 2026-08-10

### Verified
- Current one-active-workflow + clear-on-real-switch model prevents wrong-workflow Task/runtime recovery without a SQLite schema change.
- `TaskRuntimeStore.SCHEMA_VERSION` remains 1; no `workflow_id` table/column or migration is added.
- Current TaskItem/import/report/export contracts remain backward compatible.
- Real switches clear live Task/runtime/results while preserving exported Reports, FailedData, Logs and canonical per-workflow Workflow Inputs.

### Preserved
- Production runtime source is unchanged. Production registry remains `share_invite` only. Browser/licensing/CAPTCHA/dependencies/CI are unchanged. PR-10 remains NOT STARTED.

## v1.0.6.25 — PR-08 Dynamic Workflow Inputs + Per-Workflow Persistence — 2026-08-10

### Added
- Source-controlled declarative Workflow Input schemas with `text`, `integer`, `boolean` and `choice` field kinds.
- Canonical schema-v1 `AppData/workflow_inputs.json` with atomic same-directory replacement and per-workflow value isolation.
- Absence-only migration of existing Share Invite values from the four historical compatibility keys.
- Dynamic active-workflow Workflow Inputs rendering and active-workflow-only Save/Reset.
- Immutable validated Workflow Input snapshots supplied to newly created `AutomationWorker` instances.

### Preserved
- Production registry remains `share_invite` only.
- PR-06 workflow-state/switch transaction, Share Invite runtime, Browser/licensing/CAPTCHA behavior, Task/workspace/report schemas, dependencies and CI workflow remain frozen.
- The four historical Share Invite settings keys remain compatibility mirrors; canonical per-workflow values survive workflow switches.

### Deferred
- PR-09 workflow-aware Task/data/report compatibility remains NOT STARTED.

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

- Promoted the existing Playwright persistent-context implementation into the standard managed browser mode while preserving Google Chrome channel behavior and all existing Test Mode/workflow safety controls.
- Added deterministic per-Task managed profile ownership using the existing Task slot ID.
- Added **Open Closed Tasks** to the existing Tasks page; no new page was introduced.
- Added deliberate Closed Task persistence/reopen behavior using the existing `TaskRuntimeStore` tables and schema version 1.

### Changed

- `use_persistent_context` source default is now `true`; `restore_previous_session` remains `false`.
- Blank persistent-profile paths resolve to a durable VibraPilot-managed browser-profile root on Windows; explicit `VIB_TOOLS_DATA_DIR` deployments remain authoritative.
- Exact untouched legacy persistent-browser defaults migrate to the new managed default without overwriting customized persistent-profile configurations.
- Persistent internal context recycling is guarded as an intentional lifecycle transition and re-verifies login state after relaunch.

### Safety / compatibility

- Rejects the user's normal Google Chrome `User Data` tree and its descendants.
- Legacy VibraPilot profile migration is one-way only when the managed destination does not already exist; profiles are never merged or silently deleted.
- Closing a Task does not delete its managed browser profile. Reopened Tasks retain the same slot ID/run ID and therefore the same managed profile identity.
- No database schema change, dependency change, extension/download/upload feature change, CAPTCHA bypass, stealth/fingerprint change, automatic browser launch, automatic workflow start, automatic Send or permanent Task deletion feature.


## v1.0.6.13 — Phase-01 verification / CI stability correction — 2026-08-09

### Fixed

- Corrected the Windows GitHub Actions false-negative in `TaskRuntimeStoreTest.test_four_worker_threads_persist_independent_results_without_cross_run_leak`.
- Replaced the test-only 15-second storage throughput threshold with a bounded 60-second deadlock guard appropriate for FULL-synchronous SQLite WAL writes on variable hosted Windows storage.
- Prevented a timeout failure from being obscured by a secondary `TemporaryDirectory` `WinError 32` cleanup exception.
- Added a v1.0.6.13 verification scope contract proving that the v1.0.6.12 Phase-01 runtime (`backend.py`, `qt_app.py`) and `task_runtime_store.py` are byte-frozen.

### Verified

- GitHub Actions run `31331345666` had repository verification PASS, dependency installation PASS and pytest **176 passed, 1 skipped, 138 subtests passed** before the duplicate unittest compatibility step hit the old 15-second threshold.
- Phase-01 browser lifecycle tests in that run passed.
- No runtime behavior, database schema, browser profile defaults, Browser Settings, Licora protocol, selectors or workflow behavior is changed by this correction.

### Packaging

- The uploaded v1.0.6.12 development ZIP contains runtime/cache/private-development material and is therefore not a clean public source archive.
- v1.0.6.13 release-source artifacts must exclude runtime/cache paths; the private `project/` workspace remains development-only.

## v1.0.6.12 — Browser UI/lifecycle hardening — 2026-08-09

### Fixed

- Added deterministic `Closed / Opening / Open / Closing` browser lifecycle state for every Task.
- Added owner-thread page/context/browser close detection so manual closure clears browser/login readiness without stale `Browser: Open` state.
- Converted the existing primary browser action between **Open Browser** and **Close Browser** while preserving **Close Task** as a separate action.
- Kept Task/data/runtime state when only the browser is closed.
- Synchronized browser close state with Login and Dashboard Browser Ready counters.
- Centered/clamped the first workspace geometry after activation so the large workspace opens fully on-screen.

### Preserved

- Razorpay Share Invite selectors/Send workflow, Test Mode/security rules, retry/backoff, TaskRuntimeStore schema, Reports, Workflow Inputs, Browser Settings defaults, Licora API v2, ActivationPage visual design, Qt focus lifecycle hardening and browser auto-restart policy.
- No persistent-profile productization, downloads, uploads, extensions, stealth/CAPTCHA behavior or new UI page.

### Verification

- Added `VP-BROWSER-UI-LIFECYCLE-001` scope contract and backend/UI lifecycle regression coverage.
- Source-level regression is required to remain green; Windows live manual-close and geometry verification is the final platform gate.

## v1.0.6.11 — Qt focus lifecycle verification/fix — 2026-08-09

### Fixed

- Guarded keyboard-focus property/style operations with Shiboken object-validity checks so deleted PySide6 QWidget wrappers are never dereferenced after page transitions.
- Cleared stale focused-widget state when Qt begins `Destroy`/`DeferredDelete` processing.
- Guarded delayed keyboard-focus tooltip callbacks against widgets deleted during the 180 ms timer window.
- Preserved the exact `keyboardFocus` property values, repolish sequence, keyboard/mouse modality behavior, focus-ring visuals and frozen token values.

### Preserved

- `src/vibrapilot/backend.py`, `src/vibrapilot/qt_app.py`, licensing, ActivationPage, Browser Settings, Tasks, Workflow Inputs, Reports, browser automation and all dependencies remain unchanged.

### Verification

- Added the `VP-QT-FOCUS-LIFECYCLE-001` scope contract plus static and PySide6 runtime regression coverage for deleted-focused-widget transitions and delayed tooltips.

## v1.0.6.10 — License login durability/recovery forensic fix — 2026-08-09

### Fixed

- Moved default Windows license/session persistence out of the install/source folder into durable per-user LocalAppData, with one-time migration from the historical `AppData/license.json` cache.
- Added a separately DPAPI-protected persistent device identity so a corrupt/missing session cache does not destroy the P-256 key and recreate the same device ID with a different fingerprint.
- Added one restart-safe recovery attempt for production `DEVICE_KEY_MISMATCH` and `DEVICE_REVOKED` activation states; stale active-device limit conflicts are surfaced explicitly without retry loops.
- Serialized background logout deactivation against new activation and rotate the device ID only after confirmed remote revocation, preventing stale logout from revoking a fresh login.
- Background license recheck now preserves a still-locally-valid access-token session across transient network, invalid-response, rate-limit, API-not-ready and server-error conditions.

### Preserved

- Licora API v2 request/signature/token protocol, endpoint paths, pinned server RSA public key, selectors, browser/task/workflow/report behavior and ActivationPage visual design are unchanged.

### Verification

- Added the v1.0.6.10 scope lock and regression coverage for legacy-state migration, corrupt-session identity survival, device mismatch/revoked recovery, logout ordering and transient recheck classification.

## v1.0.6.9 — VP-WORKFLOW-INPUTS-001 forensic verification/fix — 2026-08-09

### Fixed

- Fixed Workflow Inputs Save failure handling so a failed settings write restores the exact pre-save in-memory values instead of leaving unsaved values authoritative.
- Fixed Workflow Inputs Reset failure handling so persistence errors are contained, the exact pre-reset values are restored, the page is refreshed, and the exception does not escape into the Qt event path.

### Verified / Preserved

- Verified GitHub v1.0.6.8 commit `82fc678fe4d3e8aab9c11ff3e54cf4455e0d3203` against the approved `VP-WORKFLOW-INPUTS-001` scope.
- Preserved the same four setting keys and successful saved-value behavior; `default_target_url` remains in App Settings and no fake workflow selector exists.
- Preserved `workflow_inputs.py`, backend worker, selectors, Browser Settings, task/recovery/runtime store and Licora Secure API v2 unchanged.

### Documentation / Verification

- Added the v1.0.6.9 Workflow Inputs verification-fix scope contract, regression tests, update note and forensic verification report.

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
