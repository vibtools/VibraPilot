# VibraPilot v1.0.6.31 — Chrome-Only Runtime Foundation


## v1.0.6.31 Phase 1

The browser runtime is now policy-locked to system-installed Google Chrome through Playwright's branded Chrome channel. Sandbox is mandatory, HTTP cache is enabled by default, Chromium/custom-binary escape paths are disabled, and Browser Settings expose the policy as read-only runtime status while retaining the existing managed persistent-profile architecture. Chrome prerequisite download/install UX remains Phase 2; build/installer changes remain deferred.

## Current development candidate

Official Baseline Freeze: **v1.0.6.30 / Workflow Plugin System**, commit `c86b6faebd58be9bff61cc8fdc12c76dda49a975`. Current candidate: **v1.0.6.31 / Phase 1 Chrome-Only Runtime Foundation**. The Phase-1 browser update is implemented and automated-source verified; owner Windows Chrome acceptance remains required before Phase 1 is formally closed.

v1.0.6.30 remains the frozen non-browser behavior baseline: trusted local workflow plugins and dynamic Workflow/Task configuration preserve the existing one-active-workflow atomic switch/restart model.

Core continues to own Task lifecycle, browser lifecycle/profiles, retry/backoff, persistence/recovery, reports/logs and licensing. Workflow packages provide validated metadata/schemas plus trusted Python business logic. JSON remains declarative only; there is no JSON Playwright interpreter, per-Task mixed workflow mode, marketplace, sandbox or automatic dependency installation in this release.

Startup repair note: the pushed v1.0.6.30 candidate `e0a080062a4ddb783dc94568801358ce2e01598c` exposed a Workflows-page startup regression after the frozen `@staticmethod` descriptor was dropped from `_transaction_root_has_directories`. The repair restores only that descriptor and adds regression verification; no UI design tokens, browser workflow, Task lifecycle, or workflow business behavior is redesigned.

# VibraPilot v1.0.6.23 — PR-06 Workflow State Persistence + Atomic Switch/Restart

## Current release

VibraPilot v1.0.6.23 promotes the locally verified PR-06 workflow-state and atomic switch/restart implementation on top of the v1.0.6.22 PR-05 Master Workflow Gate.

PR-06 persists exactly one built-in `active_workflow_id` in schema-v1 `AppData/workflow_state.json`, migrates only genuinely missing state to `share_invite`, fails closed on corrupt/unsupported/unknown state, injects the active identity into `AutomationWorker`, and exposes an application-level switch service for later Workflow UI.

Real workflow switches are blocked while Tasks are running or manual review is required, require explicit confirmation, preserve the approved global/browser/license/profile surfaces, stage rollback state before destructive workflow-scoped clearing, atomically commit the new workflow state, and restart only after commit. Interrupted PREPARED/COMMITTED transactions recover deterministically. Production still contains only the built-in **Share Invite** workflow; PR-07 owns the future Workflow Showcase UI and PR-08 owns dynamic per-workflow inputs.

## Browser acceptance boundary

PR-06 does not change browser launch/configuration, persistent profiles, downloads/uploads, extensions, licensing, Task/report/database schemas or CAPTCHA/security-challenge behavior. Remaining target-Windows browser acceptance for Sandbox policy, storage/history persistence, extension persistence, lifecycle/process-kill recovery and real 1/2/4 Task matrices remains a separate carried acceptance track before final v1.0.7.0 production approval.

## v1.0.6.20 — PR-04 Share Invite workflow extraction

PR-04 moves the verified Share Invite-specific session, selector, modal, Send and result logic behind `src/vibrapilot/workflow/share_invite/` and registers its manifest as VibraPilot's first source-controlled built-in workflow. `AutomationWorker` retains thin compatibility delegation, while its safety-critical `process_item`, `_register_send_click_attempt`, batch and report control paths remain behaviorally frozen.

This release does **not** add workflow switching, active-workflow persistence, a Workflow page, dynamic Workflow Inputs, schema changes, browser changes or CAPTCHA/stealth behavior. Current Share Invite Test Mode, retry, SecurityChallenge, uncertain-Send/manual-review and report/result semantics are preserved.

## v1.0.6.19 Browser foundation forensic verification/fix

v1.0.6.19 verifies the v1.0.6.18 browser-foundation implementation against the uploaded v1.0.6.18 baseline and its captured Windows browser evidence. The evidence confirms Google Chrome Stable `151.0.7922.76` was launched from `C:\Program Files\Google\Chrome\Application\chrome.exe`, using the managed `slot_1` profile with no Chromium fallback, and confirms `--no-sandbox` on the real process command line while `sandbox_enabled=false`.

The same Windows evidence records Playwright Python `1.60.0` although the project pins `1.61.0`. v1.0.6.19 makes this dependency mismatch explicit in diagnostics/Live Logs, improves diagnostic redaction and nested-value fidelity, and adds evidence-validation tooling. Browser policy, Sandbox source default, profiles, workflows, database/workspace schemas, capabilities and UI remain unchanged. Sandbox-ON, CAPTCHA causality and the remaining capability/lifecycle matrix still require real Windows evidence before any behavioral change.

## v1.0.6.18 Browser foundation stabilization

Adds scope-locked browser identity/fallback/sandbox diagnostics without changing browser policy, workflow, profiles, capabilities, persistence or Task UI. Sandbox source default remains unchanged pending Windows acceptance.

## v1.0.6.17 Browser capabilities

`VP-BROWSER-CAPABILITIES-001` adds durable site-initiated browser downloads, explicit user-controlled website file chooser handling, and stronger unpacked-extension validation without changing Browser Settings keys or any Razorpay/Test Mode workflow. Blank Download Directory now resolves to a durable per-Task VibraPilot-managed folder; explicit download paths retain their prior semantics. Each Task card adds a **Downloads** action that opens its effective folder.

Website uploads remain strictly user-driven: VibraPilot reacts only to a page file chooser, opens a native Qt file/directory picker, and sends the selected paths back to the same pending chooser through an opaque request ID. Selected local upload paths are not written to settings, workspace state, TaskRuntimeStore or reports. Extensions remain unpacked-directory only and require the existing persistent Chromium-compatible launch model.

## v1.0.6.16 Workspace persistence verification fix

This release verifies the complete v1.0.6.15 workspace-persistence implementation and corrects only the stale historical Qt test fixture. Production runtime behavior remains unchanged.

## v1.0.6.15 Active workspace persistence

VibraPilot now restores the user's normal active workspace after restart without automatically opening browsers or running automation. Active Task cards return with the same slot identity/order, latest Target URL and existing SQLite-backed recipient/progress state; the selected page and safe workspace geometry also persist. Deliberately Closed Tasks remain archived and continue to return only through **Open Closed Tasks**. Workspace metadata is stored atomically in the existing `AppData/state.json` path and contains no license secrets, browser cookies or duplicate recipient rows.

**VibraPilot v1.0.6.14** is the scope-locked implementation candidate for `VP-MANAGED-PERSISTENT-BROWSER-001` plus the explicitly amended `VP-CLOSED-TASK-RECOVERY-001`, built from the verified v1.0.6.13 baseline commit `5f082df8d1226710c095d4a8e591fb153c02c1c3`.

## v1.0.6.14 Managed persistent browser + Closed Task recovery

VibraPilot now uses its existing Playwright persistent-context engine as the default browser-session model. With a blank profile path, each Task owns a dedicated application-managed browser profile under the durable Windows per-user VibraPilot data root; an explicit `VIB_TOOLS_DATA_DIR` remains authoritative. The application rejects the user's normal Google Chrome `User Data` tree, preserves per-Task profile isolation, retains shared-profile collision protection, and safely migrates a legacy VibraPilot-managed profile only when the new destination does not already exist. `restore_previous_session` remains disabled, and browser/workflow/Send never auto-start.

The Tasks page also adds **Open Closed Tasks**. **Close Task** now persists the Task snapshot before removing its card, using the existing `TaskRuntimeStore` schema and the same run ID. Reopening closed Tasks restores the original slot ID, uploaded recipient records, Target URL, current index, success/failed/remaining progress, send-limit usage, manual-review state and result continuity while keeping the browser closed. The stable slot ID therefore reconnects the restored Task to the same managed browser profile without deleting or copying browser-profile data. No permanent-delete feature is introduced.

Phase-01 browser Open/Close lifecycle, Test Mode/security checks, Razorpay Share Invite selectors/Send flow, licensing, reporting, Workflow Inputs and SQLite schema version 1 remain preserved. Browser history persistence and live Chrome profile continuity require the v1.0.6.14 Windows acceptance gate before this candidate is frozen as the next Official Baseline.


**VibraPilot v1.0.6.13** is the verification/CI-stability correction built from the exact user-frozen v1.0.6.12 archive SHA-256 `becd6add21d377e98e458ce856c9c3baa710a113459bde0c737507c122c2a9b5` and GitHub v1.0.6.12 commit `a9cfec319285db2fb9fbff8d4bf0ede8ac87686b`. The v1.0.6.12 Phase-01 browser lifecycle runtime is byte-frozen in this correction; no production runtime source file changes.

## v1.0.6.13 Phase-01 verification / CI stability correction

GitHub Actions run `31331345666` proved the v1.0.6.12 repository verifier, dependency installation, full pytest suite and all Phase-01 browser lifecycle tests green. The only failing step was the second, standard-library `unittest` pass: the four-worker SQLite correctness stress test used a fixed 15-second completion threshold, and a hosted Windows runner exceeded that wall-clock threshold while threads were still making durable progress. The assertion then exited while a writer still held the SQLite file, creating a secondary `WinError 32` during temporary-directory cleanup.

v1.0.6.13 corrects only that verification harness: the concurrency test now uses a bounded 60-second deadlock guard and cleanup-tolerant temporary directory semantics. It remains a correctness/isolation test rather than an artificial storage-throughput SLA. `TaskRuntimeStore`, Phase-01 browser runtime, licensing, Browser Settings, Workflow Inputs, selectors and Task workflow are unchanged.

The uploaded v1.0.6.12 development archive also contains runtime/cache/private-development material, so it is valid as the forensic input baseline but not as a clean public source artifact. v1.0.6.13 release-source packaging must exclude runtime/cache paths, and public source must exclude the private `project/` workspace.

## v1.0.6.12 Browser UI/lifecycle hardening

Task browser state is now modeled as **Closed → Opening → Open → Closing → Closed**. The worker owns Playwright lifecycle truth and maps active-page close, context close and browser disconnect events back to the Task UI without requiring the Qt thread to inspect Playwright Page/Browser wrappers. The Task browser action changes deterministically between **Open Browser**, **Opening...**, **Close Browser** and **Closing...** while **Close Task** remains a separate destructive Task action.

Manual browser closure clears login verification, removes stale Browser Ready state from the Dashboard, and preserves the Task/data so the browser can be opened again. The existing browser auto-restart policy remains authoritative for unexpected closure when enabled. Successful Activation-to-Workspace transition now fits and centers the workspace inside the current screen's available geometry instead of expanding from the compact activation window's old top-left position.

This phase does **not** enable managed persistent profiles, change Browser Settings defaults, add downloads/uploads/extensions, change Razorpay selectors/Send behavior, or alter Licora API v2. Windows live browser-lifecycle verification remains the final platform acceptance gate before v1.0.6.12 becomes the next Official Baseline Freeze.

## v1.0.6.11 Qt focus lifecycle correction

The focus-ring manager now validates that a Python PySide6 wrapper still owns a live C++ QWidget before applying dynamic properties, repolishing styles or showing a delayed tooltip. Stale focused-widget references are cleared when Qt begins widget destruction, while valid keyboard and mouse focus behavior remains exactly the same. This directly addresses the Windows runtime `libshiboken: Internal C++ object ... already deleted` traceback seen during Activation-to-Workspace and other widget-lifecycle transitions.

## v1.0.6.10 License login durability and recovery

On Windows, protected licensing state now migrates from the historical install-relative `AppData/license.json` into a durable per-user `%LOCALAPPDATA%\Vib Tools\VibraPilot` location unless an explicit `VIB_TOOLS_DATA_DIR` deployment is configured. A separate DPAPI-protected device-identity record preserves the P-256 private key and stable device ID across clean source/application folders and session-cache corruption.

When the production Licora server reports `DEVICE_KEY_MISMATCH` or `DEVICE_REVOKED`, VibraPilot performs one restart-safe device-ID recovery attempt with the existing P-256 key. If a stale active device already fills the license limit, the client stops and gives an explicit Licora stale-device cleanup message instead of looping or silently consuming slots. Confirmed logout deactivation rotates the now-revoked device ID before the next login, while a new login cannot overtake the background deactivation request. Temporary network/rate-limit/server-response failures no longer force an otherwise locally valid access-token session to logout.


## v1.0.6.9 Workflow Inputs verification/fix

The v1.0.6.9 verification pass found no selector, browser, task, licensing or workflow-engine drift in v1.0.6.8. The four Workflow Inputs remain settings-backed values only; because backend behavior was explicitly frozen in `VP-WORKFLOW-INPUTS-001`, this release does not add a new browser consumer for `default_full_name`, `default_number`, `fallback_name` or `update_click_count`.

Two page-local error paths were corrected: a failed **Save Workflow Inputs** write no longer leaves unsaved values in `SettingsManager.data`, and a failed **Reset Workflow Inputs** write is caught, rolls the four keys back to their exact pre-reset values, refreshes the page, and reports the error. `default_target_url` remains in App Settings and no workflow selector is added.

## Workflow Inputs separation

`VP-WORKFLOW-INPUTS-001` adds a dedicated **Workflow Inputs** page after Tasks. The page owns the existing `default_full_name`, `default_number`, `fallback_name` and `update_click_count` values through the existing `SettingsManager` keys. `default_target_url` remains in App Settings. No workflow selector is shown while only one real workflow exists, and the new `workflow_inputs.py` module contains form metadata only.

## Windows SQLite concurrency verification

The v1.0.6.7 verification baseline includes a follow-up Windows concurrency correction for the local SQLite task runtime store. In-process writers are serialized before SQLite's WAL writer lock, and per-recipient item/result/progress persistence uses one atomic transaction on the worker hot path. This keeps `PRAGMA synchronous` at SQLite's durable default instead of weakening crash durability to improve test speed.

## Application areas

- **License Activation** — device-bound Licora API v2 activation and periodic server revalidation.
- **Dashboard** — task, runtime, license and usage overview.
- **Tasks** — independent browser task slots, data loading and processing controls.
- **Workflow Inputs** — workflow/form values kept separate from application and browser configuration.
- **Reports** — searchable results with CSV/Excel export.
- **Live Logs** — operational log viewer, save and clear actions.
- **App Settings** — safety, application, task-processing and licensing/network settings.
- **Browser Settings** — advanced persisted Playwright/Chromium controls.
- **About** — product, support and runtime information.

## Secure Licora API v2

Public licensing configuration is centralized in:

```text
config/AppConfig/licensing_public.py
```

It contains only non-secret values: `https://mxflow.shop`, App ID `vibrapilot`, the four `/api/v2/` endpoint paths, the expected signing-key ID and the **server RSA public signing key** used for local access-token verification.

The client flow is:

```text
P-256 device key → activate → RS256 access token + rotating refresh token
                 → status → refresh/rotate → status → deactivate
```

VibraPilot signs API v2 requests with the locally generated P-256 device private key. The server private signing key never leaves Licora. Sensitive local licensing material is protected with Windows DPAPI. By default on Windows, session state is persisted atomically in `%LOCALAPPDATA%\Vib Tools\VibraPilot\license.json` and the durable P-256 identity in `device_identity.json`; an explicit `VIB_TOOLS_DATA_DIR` remains authoritative. The historical install-relative `AppData/license.json` is migration input only. The P-256 device identity is persistent across logout, license switching and restart; session tokens and the protected license are cleared on logout.

The active source contains **no Licora API v1 master/shared API key** and no `/api/verify.php` desktop authentication flow. See `docs/guides/LICENSING.md`.

## Production runtime hardening

`VP-PROD-MT-LR-001` adds a local SQLite-backed task runtime store (`AppData/task_runtime.sqlite3`) and keeps each task identified by its own `run_id`, recipient set and result ledger. Processing remains sequential inside each task; `batch_size` defines checkpoint boundaries and does **not** introduce parallel recipient sending. `auto_save_interval` is now interpreted in seconds, with `0` disabling timed autosave while finalized recipient outcomes are still persisted immediately.

Production behavior now includes:

- input reconciliation for source/valid/invalid/duplicate/accepted rows;
- atomic task/checkpoint persistence and restart recovery without automatic sending;
- explicit manual-review handling for ambiguous post-Send outcomes;
- correct item/time Browser Context recycling after successful or failed finalized recipients;
- deterministic worker shutdown that retains live worker references until cleanup finishes;
- a bounded 4096-event UI queue and a maximum 250 events processed per UI timer tick;
- one authoritative current outcome per `run_id + item_index`, with full export backed by the runtime ledger;
- Reports filtering by Task;
- a default maximum of 4 simultaneously active task workers; and
- a persistent-profile collision guard when multiple tasks would claim the same shared profile.

The v1.0.6.5 production-hardening milestone itself added no permanent top-level page; its recovery flow remains in Tasks plus transient dialogs. v1.0.6.8 later adds only the approved Workflow Inputs configuration page.

## v1.0.6.7 forensic corrections

The v1.0.6.7 verification pass corrects four operational defects without redesigning the v1.0.6.5 production architecture: the Task-card stylesheet classmethod now binds correctly at startup, saturated critical UI events can exit during an explicit worker stop/close, the conservative pre-Send manual-review marker is immediately represented in the authoritative result ledger, and the Task metric explicitly labels the counter as **Send Attempts / Limit**.

Source baseline ZIPs can be checked with:

```powershell
python scripts/verify_source_archive.py path\to\VibraPilot-source.zip
```

The verifier rejects `AppData/`, `FailedData/`, `Reports/`, `Logs/`, private `project/`, Python caches and unsafe ZIP paths. Applying a delta to an existing working installation does **not** delete runtime `AppData`; the exclusion rule applies to distributable source baseline/release archives.

## Production scope freeze

The approved production boundary is machine-checked by `config/verification/production_mt_lr_v1.0.6.5_scope.json`. It identifies the exact v1.0.6.4 baseline archive, approved runtime surface and parameters, and freezes out-of-scope files/settings plus canonical AST contracts for `LicenseManager`, `SELECTORS`, `ActivationPage` and `BROWSER_SETTING_GROUPS`. The Phase-02 licensing scope manifests remain historical evidence.

The existing site-specific authorized Share Invite workflow is unchanged: no selector redesign, Send-flow redesign, stealth/anti-bot implementation, licensing-protocol change or browser-engine replacement is included in this release.

## AppConfig architecture

Public/non-secret application configuration lives under:

```text
config/AppConfig/
├── app.py
├── about.py
├── support.py
├── social.py
└── licensing_public.py
```

`src/vibrapilot/app_config.py` validates those modules and exposes read-only runtime objects including `APP`, `ABOUT`, `SUPPORT`, social links and `LICENSING`.

## Development

Requires Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts/verify_repository.py
python -m pytest -q
python run.py
```

`cryptography` is required for P-256 request proofs and RS256 token verification.

## Windows build

Use 64-bit Python 3.12 on Windows:

```powershell
python build.py
```

The builder produces the `VibraPilot` PyInstaller ONEDIR application and release archive under `release/`.

## Change and audit history

- Cumulative release history: `CHANGELOG.md`
- Concise update log: `UPDATE_LOG.md`
- Versioning discipline: `VERSIONING.md`
- v1.0.6.9 Workflow Inputs verification/fix note: `docs/updates/v1.0.6.9-workflow-inputs-verification-fix.md`
- v1.0.6.9 Workflow Inputs forensic verification: `docs/verification/V1.0.6.9_WORKFLOW_INPUTS_FORENSIC_VERIFICATION.md`
- v1.0.6.8 Workflow Inputs note: `docs/updates/v1.0.6.8-workflow-inputs-separation.md`
- v1.0.6.8 Workflow Inputs verification: `docs/verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md`
- v1.0.6.7 verification/fix note: `docs/updates/v1.0.6.7-vp-prod-mt-lr-verification-fix.md`
- v1.0.6.7 forensic verification: `docs/verification/V1.0.6.7_VP_PROD_MT_LR_FORENSIC_VERIFICATION.md`
- v1.0.6.5 production-hardening note: `docs/updates/v1.0.6.5-production-multi-task-long-run-stability.md`
- v1.0.6.5 production verification: `docs/verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md`
- v1.0.6.4 verification/fix note: `docs/updates/v1.0.6.4-phase-02-step-002-verification-fix.md`
- v1.0.6.4 forensic verification: `docs/verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md`
- Historical v1.0.6.3 Phase-02 note: `docs/updates/v1.0.6.3-phase-02-step-002-secure-licensing.md`
- Historical v1.0.6.3 verification: `docs/verification/PHASE02_STEP002_V1.0.6.3_VERIFICATION.md`
- Licensing contract: `docs/guides/LICENSING.md`
- AppConfig architecture: `docs/configuration/APPCONFIG.md`
- Public backend/CI contract: `docs/verification/BACKEND_CONTRACT.md`

Historical Phase-01 and v1.0.6.1 notes remain under `docs/updates/` and `docs/verification/`.

## Verification

```powershell
python scripts/verify_repository.py
python -m pytest -q
python -m unittest discover -s tests -p "test_*.py" -v
```

`pyproject.toml` configures pytest to import from `src`. The unittest modules now bootstrap the repository `src` layout themselves, so the same direct unittest command works in Command Prompt and PowerShell without shell-specific `PYTHONPATH` syntax.

The verifier checks the frozen Vib Tools design source, backend parity contract, production scope hashes/settings, AppConfig/static metadata consistency, Secure API v2 public-key/endpoint invariants, secret hygiene, safety behavior, branding/icons and repository structure.

Public documentation belongs under `docs/`. The local `project/` tree and runtime `AppData/`, `Logs/`, `Reports/` and `FailedData/` trees are private/gitignored and are not release-source inputs.

## License

GPL-3.0-only. See `LICENSE` and `NOTICE`.

Maintained by **Vib Tools** — https://vib.tools/
