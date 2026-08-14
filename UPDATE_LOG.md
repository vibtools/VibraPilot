## v1.0.6.31 — Phase 1 Chrome-Only Runtime Foundation — 2026-08-14

Phase 1 changes only the browser runtime policy foundation: Google Chrome only, mandatory sandboxing, HTTP cache enabled by default, persisted-policy migration, Chrome discovery foundation, Browser Settings policy/status cleanup, and diagnostic policy enforcement. No build/package work or Chrome installer UX is included.

## v1.0.6.30 — Workflow Plugin System — 2026-08-12

Adds trusted local workflow package loading and a unified workflow catalog; extends existing Workflow Inputs with workflow selection; adds per-workflow settings, declarative Task Settings, workflow step/metrics and Core-owned dynamic UI rendering. Existing one-active-workflow switching, Share Invite behavior, browser engine, persistence/recovery, reports/logs and licensing remain preserved. Global Default Target URL is no longer used for new Tasks, and required data-safety behavior is always enforced. Post-apply repair history now includes both the lightweight `TaskSlotWidget` host-compatibility correction and the startup/UI recovery correction that restores `MainWindow._transaction_root_has_directories` as the frozen static helper.

## v1.0.6.28 — PR-11 E2E Windows / Multi-Task Regression — 2026-08-10

Adds verification-only target-Windows acceptance tooling for browser lifecycle, capabilities, Sandbox OFF/ON compatibility, Chrome/fallback identity, and 1/2/4-Task isolation. No production runtime/source change is introduced.

## v1.0.6.27 — PR-10 Workflow Error Handling / Recovery — 2026-08-10

Adds explicit fail-closed workflow-state and Workflow Input recovery, crash-safe recovery transaction handling and active-runtime preflight without changing frozen Task/Browser/Share Invite/database/report behavior.

## v1.0.6.26 — PR-09 Workflow Data/Persistence/Reporting Compatibility — 2026-08-10

Verification-only compatibility release candidate. It formally locks the existing schema-v1 active-workflow runtime model, switch clear/preserve boundary, import parity and report/export behavior. No production runtime or database schema change is introduced.

## v1.0.6.25 — PR-08 Dynamic Workflow Inputs + Per-Workflow Persistence — 2026-08-10

Adds source-controlled dynamic Workflow Input schemas and canonical atomic per-workflow persistence while preserving the existing Share Invite compatibility keys as mirrors. Existing values migrate once when `workflow_inputs.json` is absent; canonical values survive workflow switches and newly created workers receive an immutable validated snapshot. Production registry remains `share_invite` only and PR-09 remains not started.

## v1.0.6.24 — PR-07 Workflow Showcase Page — 2026-08-10

Adds a metadata-driven Workflows page for registered built-in workflows and active-state display while keeping PR-06 switching authoritative. Production registry remains `share_invite` only; PR-08 inputs and all Browser/licensing/CAPTCHA/schema work stay out of scope.

## v1.0.6.23 — PR-06 Workflow State Persistence + Atomic Switch/Restart — 2026-08-10

PR-06 promotes the existing locally verified workflow-state implementation. VibraPilot now persists one active built-in workflow, fails closed on invalid persisted identity, injects that identity into workers, and provides an atomic application-level switch/restart service for later Workflow UI.

A real switch validates the target and built-in runtime, blocks running/manual-review/concurrent/invalid states, requires confirmation, stages rollback material, clears only the approved workflow-scoped state, atomically commits `workflow_state.json`, and restarts only after commit. PREPARED and COMMITTED crash states recover deterministically. Same-workflow activation is a no-op.

No Browser, Task/report/database schema, licensing, dependency, CAPTCHA or production-registry behavior is redesigned in this release.

## v1.0.6.22 — PR-05 Master Workflow Gate — 2026-08-10

PR-05 introduces one in-memory Master Workflow execution gate. `AutomationWorker` resolves the active built-in workflow through `WorkflowManager`, while existing Share Invite compatibility methods route session verification, item execution and safe retry preparation through the resolved runtime. Invalid/missing workflows fail closed with no silent Share Invite fallback.

No workflow switching/persistence/UI, database/workspace/report schema, browser, settings, licensing, dependency or CAPTCHA changes are included.

## v1.0.6.20 — PR-04 Share Invite workflow extraction — 2026-08-10

Extracted the current verified Share Invite implementation into the first source-controlled built-in workflow without redesigning its behavior. Added `share_invite/manifest.json`, workflow-local logo, runtime implementation, deterministic built-in registration, parity scope contract and dedicated tests. Existing `AutomationWorker` safety state machine, Test Mode/Send/retry/manual-review behavior, browser lifecycle, UI, schemas, settings, licensing and CAPTCHA policy remain unchanged.

Detailed note: `docs/updates/v1.0.6.20-pr04-share-invite-workflow-extraction.md`
Verification: `docs/verification/V1.0.6.20_PR04_SHARE_INVITE_WORKFLOW_PARITY.md`

## v1.0.6.19 — Chrome Web Store extension installation forensic fix — 2026-08-09

Dedicated forensic tracing confirms that Playwright's default `--disable-extensions` remained active in normal Chrome mode because VibraPilot filtered it only when explicit unpacked-extension loading was enabled. Chromium's installer maps that extension-service-disabled state to `INSTALL_NOT_ENABLED`, displayed by Chrome Web Store as `Installation is not enabled`.

The minimal runtime fix changes only `effective_ignored_default_args()` so the global Playwright disable-extensions switch is always filtered. Existing unpacked extension loading, downloads/uploads, profiles, sandbox, policy, workflow, database schemas, licensing and UI remain unchanged. Real post-fix Chrome Web Store installation and download regression require a fresh Windows browser launch.

Forensic record: `docs/forensic/chrome-webstore-extension-install-forensic-fix.md`

## v1.0.6.19 — Browser foundation forensic verification/fix — 2026-08-09

Audited the exact uploaded v1.0.6.18 baseline SHA `d18277ea00ae581ede45c8d3e647cd0f41625aeb0d5b8aad71715c19e4e29ae9`. Real Windows evidence confirms Google Chrome Stable, the managed Task profile and the effective `--no-sandbox` command line. It also reveals Playwright runtime `1.60.0` versus the source-required `1.61.0`.

The patch changes only browser-foundation diagnostics/runtime logging plus verification tooling: dependency mismatch is explicit, fallback diagnostic text is sanitized, nested launch-value types are preserved, and an evidence validator is added. Sandbox default and all validation-only browser behaviors remain frozen pending Windows evidence.

Detailed note: `docs/updates/v1.0.6.19-browser-foundation-verification-fix.md`
Verification: `docs/verification/V1.0.6.19_BROWSER_FOUNDATION_FORENSIC_VERIFICATION.md`

## v1.0.6.18 — VP-BROWSER-FOUNDATION-STABILIZATION-001 — 2026-08-09

Browser diagnostics implemented from v1.0.6.17 baseline SHA `02d8d70a9c11365922121440edc0d6da8328ba3b9dcfb73fcc1f0885a05a38bf`. Windows-only validation remains pending; no blocked test is reported as PASS.

## v1.0.6.17 — VP-BROWSER-CAPABILITIES-001 — 2026-08-09

Implemented the approved browser-capabilities phase against the verified v1.0.6.16 baseline commit `fd0cbe6e8f3fc37f92bdf49396364ce74583fd1e` and GitHub Actions run `31342562832`. Runtime changes are limited to `backend.py`, `qt_app.py` and new `browser_capabilities.py`.

Detailed note: `docs/updates/v1.0.6.17-browser-capabilities.md`
Verification: `docs/verification/V1.0.6.17_BROWSER_CAPABILITIES_VERIFICATION.md`

## v1.0.6.16 — Workspace persistence verification / CI fix — 2026-08-09

Re-verified v1.0.6.15 against Windows CMD and GitHub Actions job `93315001000`. The only executable CI failure was a historical v1.0.6.12 Qt test fixture missing the new `MainWindow.schedule_workspace_save` callback. Production runtime and database implementation are unchanged.

Detailed note: `docs/updates/v1.0.6.16-workspace-persistence-verification-fix.md`
Verification: `docs/verification/V1.0.6.16_WORKSPACE_PERSISTENCE_FORENSIC_VERIFICATION.md`

## v1.0.6.15 — Workspace persistence — 2026-08-09

Implemented `VP-WORKSPACE-PERSISTENCE-001` against the verified v1.0.6.14 baseline. VibraPilot now stores lightweight active-workspace metadata atomically in the existing `APP_STATE_FILE`, restores visible Task slots/order and their existing SQLite runtime state, preserves selected-page and safe window geometry, and saves before clean exit/logout/license-invalid teardown. Restored Tasks always return with Browser Closed and Login Not Verified; automation never starts automatically.

Closed Task recovery from v1.0.6.14 remains separate and unchanged. No TaskRuntimeStore schema, Browser Settings, profile architecture, licensing, workflow or dependency change is included.

Detailed note: `docs/updates/v1.0.6.15-workspace-persistence.md`
Verification: `docs/verification/V1.0.6.15_WORKSPACE_PERSISTENCE_VERIFICATION.md`

## v1.0.6.14 — Managed persistent browser + Closed Task recovery — 2026-08-09

Implemented the approved `VP-MANAGED-PERSISTENT-BROWSER-001` scope together with the explicitly amended `VP-CLOSED-TASK-RECOVERY-001`. The existing persistent-context browser path is now the managed default, blank profile roots use a durable per-user VibraPilot location on Windows, personal Chrome `User Data` paths are blocked, stable slot IDs own isolated browser profiles, and internal persistent-context recycling is synchronized with the verified Phase-01 lifecycle.

`Close Task` now archives the exact Task runtime snapshot before removing the card. **Open Closed Tasks** restores deliberately closed Tasks with the same slot ID/run ID, recipient rows, progress/counts, target URL, send-limit/manual-review state and result continuity; browser/workflow/Send remain closed/stopped until explicit user action. Existing SQLite schema version 1 is unchanged.

Detailed note: `docs/updates/v1.0.6.14-managed-persistent-browser-closed-task-recovery.md`
Verification: `docs/verification/V1.0.6.14_MANAGED_PERSISTENT_BROWSER_CLOSED_TASK_VERIFICATION.md`

# Update Log

## v1.0.6.13 — Phase-01 verification/CI correction — 2026-08-09

Verified the complete v1.0.6.12 `VP-BROWSER-UI-LIFECYCLE-001` implementation against the uploaded baseline and GitHub Actions run `31331345666`. No Phase-01 runtime regression was found. The only failing CI step was the duplicated standard-library unittest run, where the four-worker SQLite correctness test's fixed 15-second wall-clock threshold was too strict for hosted Windows FULL-synchronous WAL I/O and produced a secondary `WinError 32` cleanup error.

v1.0.6.13 changes no production runtime source. It hardens only the verification harness, adds an exact no-runtime-change scope lock, synchronizes documentation/version metadata, and records the uploaded baseline archive hygiene finding.

Detailed note: `docs/updates/v1.0.6.13-phase01-verification-ci-fix.md`
Verification: `docs/verification/V1.0.6.13_PHASE01_FORENSIC_VERIFICATION.md`

## v1.0.6.12 — VP-BROWSER-UI-LIFECYCLE-001 — 2026-08-09

Implemented truthful Task browser lifecycle state, manual page/context/browser close detection, deterministic Open/Close Browser action, browser-only close that preserves Task/data, Login/Dashboard readiness synchronization and safe first-workspace center/clamp. Phase-02 managed persistent browser/profile work remains explicitly out of scope.

Detailed note: `docs/updates/v1.0.6.12-browser-ui-lifecycle.md`
Verification: `docs/verification/V1.0.6.12_BROWSER_UI_LIFECYCLE_VERIFICATION.md`

## v1.0.6.11 — Qt focus lifecycle — 2026-08-09

Corrected the Windows PySide6 focus-manager lifetime race that could dereference an already-deleted `QLineEdit`/`QWidget` wrapper during page transitions or delayed tooltip handling. The patch changes only `vib_validation_app/focus_manager.py` at runtime and preserves all visual focus behavior and application workflows.

Detailed note: `docs/updates/v1.0.6.11-qt-focus-lifecycle-fix.md`
Verification: `docs/verification/V1.0.6.11_QT_FOCUS_LIFECYCLE_VERIFICATION.md`

## v1.0.6.10 — License login durability/recovery — 2026-08-09

Corrected production license-login persistence and recovery against the current Licora API v2 server: durable LocalAppData licensing state, independent DPAPI device identity, `DEVICE_KEY_MISMATCH`/`DEVICE_REVOKED` recovery, logout/re-login ordering and transient recheck handling. The API v2 wire protocol, browser/task/workflow behavior and ActivationPage visual design remain frozen.

Detailed note: `docs/updates/v1.0.6.10-license-login-durability-recovery-fix.md`
Verification: `docs/verification/V1.0.6.10_LICENSE_LOGIN_FORENSIC_VERIFICATION.md`

## v1.0.6.9 — Workflow Inputs forensic verification/fix — 2026-08-09

Verified the full v1.0.6.8 `VP-WORKFLOW-INPUTS-001` separation and corrected only two page-local persistence-error paths: failed Save and Reset operations now restore the exact prior in-memory values, and Reset write failures no longer propagate into the Qt event path. Backend/browser/task/API-v2 behavior remains frozen.

Detailed note: `docs/updates/v1.0.6.9-workflow-inputs-verification-fix.md`
Verification: `docs/verification/V1.0.6.9_WORKFLOW_INPUTS_FORENSIC_VERIFICATION.md`

## v1.0.6.8 — VP-WORKFLOW-INPUTS-001 — 2026-08-09

Separated workflow/form values from App Settings into a dedicated Workflow Inputs page while retaining the same setting keys and saved values. `default_target_url`, backend/task/browser behavior and Licora API v2 remain unchanged, and no fake single-option workflow selector was added.

Detailed note: `docs/updates/v1.0.6.8-workflow-inputs-separation.md`
Verification: `docs/verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md`

## v1.0.6.7 Windows SQLite concurrency verification correction

Corrected the verified Windows four-worker `TaskRuntimeStore` contention/file-handle failure without changing the application version or unrelated runtime behavior. Concurrent workers now serialize local SQLite write transactions before the WAL writer lock, and the high-frequency recipient/result/progress persistence path commits atomically in one transaction.


## v1.0.6.7 — VP-PROD-MT-LR-001 forensic verification/fix — 2026-08-08

Verified the user-frozen v1.0.6.5 production-hardening baseline and corrected only confirmed defects: a startup-blocking duplicated classmethod descriptor, shutdown liveness under a saturated bounded UI queue, missing pre-Send crash-marker result-ledger persistence, ambiguous Send-limit wording and incomplete source-archive hygiene enforcement. Runtime/private data is excluded from the clean v1.0.6.7 baseline while working-installation runtime data remains untouched by the delta.

Detailed note: `docs/updates/v1.0.6.7-vp-prod-mt-lr-verification-fix.md`
Forensic report: `docs/verification/V1.0.6.7_VP_PROD_MT_LR_FORENSIC_VERIFICATION.md`

## v1.0.6.5 — VP-PROD-MT-LR-001 production runtime hardening — 2026-08-08

Hardened Multiple Task and long-running processing with per-task crash-safe runtime persistence/recovery, input reconciliation, functional seconds-based autosave and sequential batch boundaries, corrected Browser Context recycling, deterministic worker shutdown, bounded UI event processing, scalable one-recipient-one-outcome reporting, Task-scoped Reports filtering, concurrent-worker limits and shared-profile collision protection. Licora API v2, selectors, Send workflow, Browser Settings contract and visual foundation remain frozen.

Detailed note: `docs/updates/v1.0.6.5-production-multi-task-long-run-stability.md`
Verification report: `docs/verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md`

## v1.0.6.4 — Phase-02-Step-002 forensic verification/fix — 2026-08-08

Audited the user-frozen v1.0.6.3 archive and corrected only verified Phase-02-Step-002 defects: persistent device-key continuity, pre-request device-key durability, one-shot refresh ambiguity persistence, non-blocking license validation state access, startup secure-session restore, expired-token periodic recheck, cached local token verification and release-package privacy/hygiene. Expanded crypto/protocol/persistence/scope tests and synchronized version/documentation metadata. The validated automation/browser/task/report/safety/UI foundation remains frozen. A follow-up verification-only portability correction makes direct standard-library unittest discovery import the `src` layout without requiring shell-specific `PYTHONPATH` syntax; runtime application files remain untouched.

Detailed note: `docs/updates/v1.0.6.4-phase-02-step-002-verification-fix.md`
Forensic report: `docs/verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md`

## v1.0.6.3 — Phase-02-Step-002 Secure Licora API v2 client — 2026-08-08

Migrated VibraPilot licensing from the embedded Licora API v1 shared/master-key flow to device-bound Secure API v2 with P-256 request proof, pinned RS256 server-token verification, rotating refresh tokens, DPAPI-protected schema-v2 persistence and legacy-cache migration. The validated automation/browser/task/report/UI foundation remains scope-frozen.

Detailed note: `docs/updates/v1.0.6.3-phase-02-step-002-secure-licensing.md`

## v1.0.6.2 — Phase-01 forensic verification and completion — 2026-08-08

Phase-01 verification/fix scope only. Removed stale pre-rebrand active paths that broke the repository contract, completed confirmed About/support/social configuration, strengthened AppConfig validation, synchronized release metadata and promoted the verified baseline to **1.0.6.2**. Automation, licensing, browser/task and UI-design behavior remain unchanged.

Detailed note: `docs/updates/v1.0.6.2-phase-01-verification-fix.md`

## v1.0.6.1 — Phase-01 AppConfig centralization — 2026-08-08

Configuration-architecture update only. Application identity, About/company content, confirmed public support/documentation links and social/community metadata now live under `config/AppConfig/` and are exposed through a validated runtime facade. Backend compatibility constants and build/package identity consume that source, while verifier/tests prevent static metadata drift. Licensing transport/API credentials and all automation/runtime behavior remain unchanged and are reserved for Phase-02.

Detailed note: `docs/updates/v1.0.6.1-phase-01-appconfig.md`

## v1.0.6.1 — GitHub CI deterministic backend-contract fix — 2026-08-08

CI/repository-verification maintenance only. Backend implementation parity hashes now use a canonical semantic AST representation instead of Python-version-dependent raw `ast.dump()` text. This prevents Python 3.12 GitHub runners from reporting false `TaskItem` implementation drift when the backend source is unchanged. The CI workflow also uses Node 24-native `actions/checkout@v5` and `actions/setup-python@v6`. Runtime application behavior is unchanged.

Detailed note: `docs/updates/v1.0.6.1-github-ci-deterministic-ast-contract-fix.md`

## v1.0.6.1 — GitHub CI repository hygiene fix — 2026-08-08

CI/repository-only maintenance. Public verification no longer depends on the private gitignored `project/` workspace. A machine-readable backend parity contract now lives under `config/verification/`, public documentation/CI guidance lives under `docs/`, Node 24-native GitHub Actions replace the deprecated Node 20 actions, and stale pre-rebrand tracked source paths are removed from the clean repository state. Runtime application behavior is unchanged.

Detailed note: `docs/updates/v1.0.6.1-github-ci-repository-hygiene-fix.md`

## v1.0.6.1 — GitHub Actions verification portability fix — 2026-08-08

CI-only maintenance update. The repository verifier now canonicalizes CRLF to LF when hashing frozen text design-contract files, preventing Windows Actions checkout from producing false design-drift failures. `.gitattributes` now pins source/config/documentation text to LF while preserving binary files as binary. The Windows CI job also exports the repository `src` directory through `PYTHONPATH`, so contract tests can import `vibrapilot` without an install step. Runtime application behavior is unchanged.

Detailed note: `docs/updates/v1.0.6.1-github-actions-line-ending-fix.md`

## VibraPilot branding baseline — 2026-08-08

Brand-only transition on top of the validated **v1.0.6.1** runtime. Product/package/build names, documentation and visible application branding now use **VibraPilot**. Existing workflow and backend behavior remain unchanged. Existing site-specific implementation details are retained only for the current built-in workflow.

Detailed note: `docs/updates/v1.0.6.1-vibrapilot-branding.md`

## v1.0.6.1 — 2026-08-07

Browser Settings production-hardening release. The advanced Browser Settings page was audited end to end, read-only/non-setting UI cards were removed, Playwright-default-argument conflicts for popup blocking/background throttling/extensions/headless audio were corrected, persistent Chrome fallback and full-Chromium extension launch selection were completed, the removed Playwright 1.61 `devtools` launch keyword was replaced with Chromium's real DevTools switch, duplicate/hidden browser aliases were migrated away, and saved controls now refresh from backend-persisted values.

Full technical note: `docs/updates/v1.0.6.1.md`

A–Z Browser Settings binding audit: `docs/updates/v1.0.6.1-browser-settings-audit.md`
