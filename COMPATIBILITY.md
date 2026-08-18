# v1.0.6.42 Phase 2 Workflow Lifecycle / Multiworkflow Compatibility

- Baseline compatibility: v1.0.6.41; external Plugin API 1 is unchanged.
- Existing workflow packages remain loadable; same-ID package installation now routes through a strict-newer update path instead of blind replacement.
- Default workflow state is preserved but now controls new Task creation only; existing Tasks keep immutable workflow identity.
- Workspace and runtime storage migrate from schema v1 to v2 while preserving completed legacy history without inventing workflow identity.
- Browser profile isolation, Chrome-only runtime, Chrome secure install, licensing, Windows power management, settings defaults, dependencies, CI and portable packaging are unchanged.
- No new top-level UI page is added.

---

# v1.0.6.41 Phase 1 Active-Page Origin Closure Compatibility

- Baseline compatibility: v1.0.6.40; external Plugin API 1 workflows remain unchanged.
- HTTPS omitted port and explicit `:443` are treated as the same target origin.
- HTTP omitted port and explicit `:80` are treated as the same target origin.
- Non-default ports remain distinct origins.
- Session-required/sessionless behavior, Chrome background policy v2, Windows sleep guard, persistence, licensing, CI and portable packaging are unchanged.
- Phase 2 workflow lifecycle/per-Task multiworkflow remains out of scope and is now planned for v1.0.6.42.

---

# v1.0.6.40 Phase 1 Forensic Closure Compatibility

- Baseline compatibility is v1.0.6.39; Plugin API 1 and external workflow contracts are unchanged.
- `requires_session=true` and `requires_session=false` semantics remain those introduced in v1.0.6.39; the closure only fixes exception/recycle boundaries.
- Browser runtime policy v2 and `background_throttling_enabled=false` remain unchanged.
- `src/vibrapilot/power_management.py` is byte-frozen from v1.0.6.39; only worker ownership/release use is corrected.
- Task runtime, workspace, reports, licensing, Chrome installer, dependencies, CI and portable release architecture are unchanged.
- Phase 2 workflow lifecycle/per-Task multiworkflow implementation remains out of scope and shifts to v1.0.6.41.

---

# v1.0.6.39 Phase 1 Compatibility Addendum

- Baseline compatibility: v1.0.6.38 external workflows and Plugin API 1 remain supported.
- `requires_session=true`: existing Login Verification behavior is preserved.
- `requires_session=false`: Core login polling, fake Login state and pre-Start session enforcement are bypassed.
- Browser runtime policy v2 defaults `background_throttling_enabled` to `false`; a one-time migration normalizes older persisted policy state.
- Windows processing Tasks request system-awake state without forcing the display on; non-Windows behavior is a no-op.
- Existing global active-workflow/switch architecture is unchanged; true per-Task multiworkflow remains Phase 2.
- v1.0.6.39 is LOCAL VERIFIED / WINDOWS ACCEPTANCE PENDING until the target-Windows acceptance matrix passes.

---

# v1.0.6.38 Portable Runtime Root Compatibility

The only production source change is `src/vibrapilot/runtime_environment.py`. In Nuitka standalone execution, packaged data now resolves from the directory containing the launched `VibraPilot.exe`. Historical PyInstaller `_MEIPASS` handling and source-checkout root handling remain unchanged.

No browser engine/policy, managed profile, Chrome installer, Authenticode, workflow API/business logic, licensing protocol, TaskRuntimeStore/schema, workspace, report/export, download/upload, dependency, general CI or UI/UX behavior change is introduced.

# v1.0.6.37 Portable Release Compatibility

- Target: Windows 10/11 x64.
- Build: Python 3.12 x64 + Nuitka 4.1.3 standalone OneDir.
- Target machines do not require Python, but do require a supported Google Chrome installation (or the existing explicit Chrome prerequisite/install flow).
- Playwright driver runtime is packaged; Playwright Chromium/browser binaries are not.
- Existing external `.vpworkflow` packages remain runtime-loaded and must be owner-tested in the RC before public release.
- No MSI/WiX installer is produced.

# v1.0.6.36 Workflow Compatibility

- Workflow Plugin API remains version 1. Existing trusted external workflows continue to use `create_workflow`; existing `load_task_items` loaders remain valid.
- A new optional `load_task_data` hook may return rows plus source fingerprint/summary metadata, and a runtime may optionally own specialized `process_item` orchestration.
- Workflow-state schema v1 remains readable. Legacy `active_workflow_id = "share_invite"` is migrated to schema v2 without quarantine while the external Share Invite package is absent.
- Fresh installations may legitimately have no active workflow. Browser, licensing, TaskRuntime/workspace schemas and external DMARC behavior are unchanged.

# v1.0.6.35 Compatibility

- Existing `settings.json` keys `authorized_testing_only` and `max_test_send_limit` remain readable for compatibility, but the authorization key is no longer a Task-start gate.
- The legacy global send-limit value is used only as a one-time migration source for `share_invite.max_test_send_limit`.
- Existing Share Invite runtime behavior and Test Mode verification remain compatible.

## v1.0.6.33 browser forensic compatibility

Windows browser automation requires the exact Playwright Chrome-channel target to pass ProductName, WinVerifyTrust and Google LLC publisher validation. Existing Playwright 1.61.0, managed profiles, sandbox/cache policy and workflow behavior are retained.

## v1.0.6.32 Chrome prerequisite/install compatibility

VibraPilot continues to require Windows x64 and genuine system-installed Google Chrome. If Chrome is missing, non-browser app functions remain available while browser automation is blocked. The optional in-app prerequisite recovery uses Google's Stable x64 Enterprise MSI, validates Windows Authenticode and Google LLC signer identity, elevates only Windows Installer through UAC, and re-detects genuine Chrome before enabling browser automation. Phase-01 sandbox/cache/managed-profile behavior is unchanged.

## v1.0.6.31 Chrome-only runtime compatibility

VibraPilot now requires the branded Google Chrome runtime for browser launch. The Playwright automation layer and VibraPilot-managed persistent `slot_N` profiles are preserved. Playwright Chromium fallback, arbitrary browser executable selection, and VibraPilot unpacked Chromium side-loading are no longer accepted runtime paths. Existing profile-installed Chrome extensions are not removed. Sandbox is mandatory. HTTP cache is enabled by default; explicit Playwright routing for resource blocking or operator-disabled cache can still affect cache behavior. Chrome auto-download/install is not part of Phase 1. Advanced browser arguments remain available except policy-conflicting sandbox-disable, unpacked-extension side-loading and alternate user-data-dir overrides, which fail closed.

## v1.0.6.30 workflow plugin compatibility

v1.0.6.30 extends the existing source-controlled workflow framework with trusted local plugin discovery/installation without replacing the one-active-workflow state model. Built-in Share Invite remains registered and behaviorally preserved. External plugins use plugin API version 1 and declarative JSON for Inputs/Settings/Task UI while executable business logic remains Python. Invalid/incompatible plugins fail closed. Existing browser, TaskRuntimeStore, workspace/report, licensing/device, Chrome-preferred/Chromium-fallback and managed-profile contracts remain preserved.

## v1.0.6.28 PR-11 compatibility

PR-11 is verification-first and preserves every production `src/vibrapilot/**` file byte-for-byte from v1.0.6.27. Target acceptance covers Windows x64 / CPython 3.12 / Playwright 1.61.0 / Chrome Stable, 1/2/4-Task isolation, browser lifecycle, downloads/uploads/storage/extensions, Sandbox OFF/ON compatibility and observable fallback behavior.

## v1.0.6.27 PR-10 compatibility

PR-10 preserves workflow-state schema v1, Workflow Input schema v1, TaskRuntimeStore schema v1, TaskItem/workspace/report/export contracts and Share Invite execution. Recovery reuses the PR-09 live Task/runtime clear boundary; canonical per-workflow Workflow Inputs and exported durable artifacts remain preserved.

## v1.0.6.26 PR-09 compatibility

PR-09 preserves the current `TaskItem`, TaskRuntimeStore schema-v1 `runs/items/results` database, workspace schema and report/export columns. No `workflow_id` database/report column is introduced because successful real workflow switches clear live Task/runtime/results before the target workflow becomes operational. Exported Reports/FailedData/Logs and canonical per-workflow Workflow Inputs remain preserved.

## v1.0.6.25 PR-08 compatibility

PR-08 retains the four historical Share Invite Workflow Input settings keys as compatibility mirrors while moving canonical persistence to schema-v1 `AppData/workflow_inputs.json`. Existing Share Invite values migrate once when the canonical store is absent. PR-06 workflow-state/switch/restart semantics, Share Invite runtime, TaskRuntimeStore/workspace/report schemas, Browser/licensing/CAPTCHA behavior, dependencies and CI remain unchanged. Production registry still contains only `share_invite`.

## v1.0.6.24 PR-07 compatibility

PR-07 adds only the Workflows navigation/page surface in `qt_app.py`. It preserves PR-06 workflow-state/switch/restart semantics, the single `share_invite` production registry, existing Workflow Inputs behavior, Task/workspace/report/database schemas, Browser behavior, licensing, dependencies and CAPTCHA/security-challenge policy.

## v1.0.6.23 PR-06 compatibility

PR-06 adds a separate schema-v1 workflow-state file and atomic workflow switch/restart orchestration while preserving existing browser, licensing, TaskRuntimeStore, workspace and report/result schema compatibility.

The production registry remains source-controlled and contains only `share_invite`. PR-06 does not add a Workflow Showcase page, dynamic per-workflow inputs, workflow-aware database columns/tables, browser behavior changes, dependency changes or CAPTCHA/security-challenge bypass behavior.

## v1.0.6.22 PR-05 compatibility

PR-05 preserves the current Share Invite runtime contract and all external Task/report/persistence behavior while inserting a fail-closed in-memory Master Workflow Gate. Existing browser lifecycle, profiles, downloads/uploads/extensions, App/Browser Settings, Workflow Inputs UI, database/workspace schemas, licensing protocol and dependency versions are unchanged.

No active workflow persistence or switching is introduced; `share_invite` remains the only current built-in workflow runtime.

## v1.0.6.20 PR-04 Share Invite compatibility

PR-04 preserves the existing Share Invite external/runtime behavior while moving workflow-specific implementation ownership behind `ShareInviteWorkflow`. Existing selectors and priority, Test Mode checks, email validation, retry/backoff limits, Test Send Limit, SecurityChallenge handling, post-Send manual-review/no-duplicate-retry behavior, exception identities, TaskItem/report result contracts and persistence schemas remain compatible.

No UI page, App/Browser Settings contract, Chrome/Playwright launch policy, dependency, SQLite schema, licensing protocol, workflow switching or active-workflow persistence changes are introduced.

## v1.0.6.19 browser-foundation verification compatibility

No dependency declaration, database/workspace schema, settings key, browser launch policy, profile behavior, Task UI, workflow or licensing protocol changes. The required Playwright version remains exactly `1.61.0`; diagnostics now warn when the actual runtime differs. Existing Windows PowerShell/CIM process evidence remains non-fatal.

## v1.0.6.18 browser-foundation compatibility

No dependency, database/workspace schema, settings-key, Task UI or workflow change. Optional Windows process evidence uses PowerShell/CIM; diagnostic failure is non-fatal.

## v1.0.6.17 browser-capability compatibility

Existing `accept_downloads`, `downloads_path`, `extensions_enabled` and `extension_paths` settings retain their keys. Blank download paths now resolve to a durable managed per-Task folder; explicit paths keep prior semantics. Browser uploads require a webpage-triggered file chooser and explicit user selection. Unpacked extensions remain persistent-context Chromium capabilities; branded Chrome side-loading restrictions remain enforced.

## v1.0.6.16 verification compatibility

The v1.0.6.15 workspace runtime contract is unchanged. The historical Qt lifecycle fixture now models the workspace-save callback introduced by v1.0.6.15.

## v1.0.6.15 workspace-state compatibility

Workspace metadata uses schema version 1 in `AppData/state.json`. Missing/corrupt/unsupported state safely falls back to the existing v1.0.6.14 startup/recovery behavior. Active Task data continues to come from the unchanged TaskRuntimeStore schema version 1, and managed browser profiles remain keyed by the restored slot ID.

## v1.0.6.14 managed-profile / Closed Task compatibility

- Windows default blank persistent-profile root is application-managed and durable; explicit `VIB_TOOLS_DATA_DIR` remains supported.
- The user's everyday Google Chrome `User Data` profile is intentionally rejected.
- `use_persistent_context` is enabled by default while `restore_previous_session` remains disabled.
- Existing advanced profile-lock/fallback, Chrome-channel, profile-cache and per-Task profile settings remain supported.
- TaskRuntimeStore schema remains version 1. Closed Tasks use the existing `task_status` field and existing run/item/result records.
- Phase-01 browser lifecycle, licensing, workflow selectors/Test Mode, reporting, Workflow Inputs and dependencies remain compatible.

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


## v1.0.6.11 Qt focus lifecycle compatibility

No Python dependency, PySide6 version range, UI visual token, application page, settings key, browser engine, SQLite schema, licensing protocol, selector or task/workflow behavior changes. The only runtime change is deleted-QObject lifetime guarding in `vib_validation_app/focus_manager.py`; Shiboken is already shipped as part of the existing PySide6 runtime.


## v1.0.6.12 Browser UI/lifecycle compatibility

No Python dependency, Browser Settings key/default, SQLite schema, Licora protocol, selector, Razorpay Send sequence, Workflow Inputs contract, ActivationPage visual design or managed-persistent-profile behavior changes. The worker now owns browser lifecycle truth through thread-safe readiness events and page/context/browser close callbacks; the Qt Task UI consumes those events to render a deterministic Open/Close browser action. First-workspace geometry is centered/clamped to the current screen only; persistent window geometry remains reserved for a later workspace-persistence phase.
## v1.0.6.13 Phase-01 verification/CI compatibility

No production runtime dependency, Python version, SQLite schema, WAL durability setting, browser engine, Browser Settings key/default, persistent-profile behavior, Licora protocol, selector, Task workflow, Workflow Inputs behavior or UI runtime implementation changes.

The four-worker runtime-store test remains a concurrency correctness/isolation test. Its deadlock guard is 60 seconds so variable hosted Windows storage latency does not become a false throughput requirement. Production `TaskRuntimeStore` remains byte-identical to v1.0.6.12.

The uploaded v1.0.6.12 development archive is not a clean public source package because it contains runtime/cache/private-development paths. Clean public source verification remains governed by `scripts/verify_source_archive.py`.

Workflow cards now use a dedicated 2px tokenized border together with the shared surface and radius tokens so compact tiles remain visually distinct from the workflow page background.
