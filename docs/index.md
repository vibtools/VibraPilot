# VibraPilot Documentation — v1.0.6.41 Phase 1 Active-Page Origin Closure

- Update: `docs/updates/v1.0.6.41-phase1-active-page-origin-closure.md`
- Verification: `docs/verification/V1.0.6.41_PHASE1_ACTIVE_PAGE_ORIGIN_CLOSURE.md`
- Scope contract: `config/verification/v1.0.6.41_phase1_active_page_origin_closure_scope.json`
- Phase 2 remains not started; next planned implementation version: v1.0.6.42.

---

# VibraPilot Documentation — v1.0.6.40 Phase 1 Forensic Closure

- Update: `docs/updates/v1.0.6.40-phase1-forensic-closure-fix.md`
- Verification: `docs/verification/V1.0.6.40_PHASE1_FORENSIC_CLOSURE_FIX.md`
- Scope contract: `config/verification/v1.0.6.40_phase1_forensic_closure_fix_scope.json`
- Official owner-frozen baseline: v1.0.6.39 / `7bd6428a89607df34dc96fbed28d1b2ac20b9365`.
- Classification: Phase 1 corrective forensic closure only.
- Phase 2 Workflow Lifecycle & True Multiworkflow: NOT STARTED; planned version moved to v1.0.6.41.

## Historical v1.0.6.39 Phase 1

- Update: `docs/updates/v1.0.6.39-runtime-reliability-session-policy.md`
- Verification: `docs/verification/V1.0.6.39_RUNTIME_RELIABILITY_SESSION_POLICY.md`
- Scope contract: `config/verification/v1.0.6.39_runtime_reliability_session_policy_scope.json`
- GitHub main commit: `7bd6428a89607df34dc96fbed28d1b2ac20b9365`; CI run `32153560933` succeeded.

---

# v1.0.6.38 Portable Runtime Root Fix

- Update: `docs/updates/v1.0.6.38-portable-runtime-root-fix.md`
- Verification: `docs/verification/V1.0.6.38_PORTABLE_RUNTIME_ROOT_FIX.md`
- Baseline source: v1.0.6.37 / `299e93a89db3d30505350f474f79eefc330ee923`.
- Exact fix: Nuitka OneDir packaged resources resolve from the launched executable directory.
- Architecture preserved: Windows 2022 + Python 3.12 x64 + Nuitka 4.1.3 standalone OneDir; system Google Chrome; no bundled Chromium; no WiX/MSI.

# v1.0.6.37 Portable Nuitka OneDir Release Packaging

- Update: `docs/updates/v1.0.6.37-portable-release-packaging.md`
- Verification: `docs/verification/V1.0.6.37_PORTABLE_RELEASE_PACKAGING.md`
- Baseline: v1.0.6.36 FINAL / `40b9b65d3900760d919167dc6711a4fcd494f010`.
- Output: GitHub Actions Windows x64 Nuitka standalone OneDir portable ZIP; system Google Chrome only; no bundled Chromium; no WiX/MSI.

# v1.0.6.36 Share Invite Workflow Externalization

- Update: `docs/updates/v1.0.6.36-share-invite-externalization.md`
- Verification: `docs/verification/V1.0.6.36_SHARE_INVITE_EXTERNALIZATION.md`

## v1.0.6.35 Workflow-Scoped Test Safety Isolation

- Update: `docs/updates/v1.0.6.35-workflow-scoped-test-safety.md`
- Verification: `docs/verification/V1.0.6.35_WORKFLOW_SCOPED_TEST_SAFETY.md`
- Frozen input: v1.0.6.34 / `a0e3621e831d402649ab55859e00b59d5f0ad634`.

# v1.0.6.34 UI-Only Compact Polish

- Update: `docs/updates/v1.0.6.34-ui-compact-polish.md`
- Verification: `docs/verification/V1.0.6.34_UI_COMPACT_POLISH.md`
- Frozen baseline: v1.0.6.33 / `dc149f768451383747ed02dc96607a4cfb4a3fb2`

# v1.0.6.33 Browser Forensic Closure

- Update: `docs/updates/v1.0.6.33-browser-forensic-closure.md`
- Verification: `docs/verification/V1.0.6.33_BROWSER_FORENSIC_CLOSURE.md`
- A–Z forensic audit: `docs/forensic/V1.0.6.33_PHASE01_PHASE02_AZ_FORENSIC_AUDIT.md`
- Scope compliance: `docs/verification/V1.0.6.33_SCOPE_COMPLIANCE_MATRIX.md`
- Frozen audit baseline: v1.0.6.32 / `a001f67972c47832a5e59af5f9350a0409e7eab6`

# VibraPilot Documentation — v1.0.6.32 Chrome Prerequisite Secure Install

Current functional candidate: **v1.0.6.32 / Phase 2 Chrome Prerequisite UX + Secure Install**. Official functional baseline: **v1.0.6.31 / Phase 1 COMPLETE** at `fc9081b0f760ac6b380b8c574680fc2c15764be0`.

- `updates/v1.0.6.32-chrome-prerequisite-install.md`
- `verification/V1.0.6.32_CHROME_PREREQUISITE_INSTALL.md`

# VibraPilot Documentation — v1.0.6.31 Chrome-Only Runtime Foundation

Historical Phase 1: **v1.0.6.31 / Chrome-Only Runtime Foundation — COMPLETE**. The v1.0.6.30 Workflow Plugin System remains preserved as the non-browser behavior baseline.

- `updates/v1.0.6.31-chrome-only-runtime-foundation.md`
- `verification/V1.0.6.31_CHROME_ONLY_RUNTIME_FOUNDATION.md`


Phase 1 was promoted to `main` at `fc9081b0f760ac6b380b8c574680fc2c15764be0` with owner Windows acceptance and post-merge CI PASS. Current functional candidate is **v1.0.6.32 / Chrome Prerequisite UX + Secure Install**.

v1.0.6.30 documents trusted local `.vpworkflow` loading, unified built-in/external workflow resolution, Workflow Inputs/Settings schemas, Task Settings, workflow step/metrics and compatibility-preserving Core integration.

- `updates/v1.0.6.30-workflow-plugin-system.md`
- `verification/V1.0.6.30_WORKFLOW_PLUGIN_SYSTEM.md`

# VibraPilot Documentation — v1.0.6.28 PR-11 Candidate

Current release baseline: **v1.0.6.27 / PR-10 — RELEASE COMPLETE**. Current development candidate: **v1.0.6.28 / PR-11 E2E Windows / Multi-Task Regression**.

PR-11 adds verification-only Windows acceptance tooling and evidence contracts. Production runtime source remains byte-frozen; PR-12 Packaging is not started.

- `updates/v1.0.6.28-pr11-windows-multitask-regression.md`
- `verification/V1.0.6.28_PR11_WINDOWS_MULTITASK_REGRESSION.md`

# VibraPilot Documentation — v1.0.6.27 PR-10 Candidate

Current release baseline: **v1.0.6.26 / PR-09 — RELEASE COMPLETE**. Current development candidate: **v1.0.6.27 / PR-10 Workflow Error Handling / Recovery**.

PR-10 adds explicit user-confirmed workflow control-plane recovery and active-runtime preflight while preserving Task/database/report/Browser/Share Invite behavior. Production remains `share_invite` only; PR-11 is not started.

- `updates/v1.0.6.27-pr10-workflow-error-recovery.md`
- `verification/V1.0.6.27_PR10_WORKFLOW_ERROR_RECOVERY.md`

# VibraPilot Documentation — v1.0.6.26 PR-09 Candidate

Current release baseline: **v1.0.6.25 / PR-08 — RELEASE COMPLETE**. Current development candidate: **v1.0.6.26 / PR-09 Workflow Data/Persistence/Reporting Compatibility**.

PR-09 verifies wrong-workflow recovery prevention, switch clear/preserve boundaries, schema-v1 TaskRuntimeStore compatibility, current import formats and report/export parity without production runtime/schema changes. Production remains `share_invite` only; PR-10 remains not started.

- `updates/v1.0.6.26-pr09-data-persistence-reporting-compatibility.md`
- `verification/V1.0.6.26_PR09_DATA_PERSISTENCE_REPORTING_COMPATIBILITY.md`

Current release baseline: **v1.0.6.24 / PR-07 — RELEASE COMPLETE**. Current development candidate: **v1.0.6.25 / PR-08 Dynamic Workflow Inputs + per-workflow persistence**.

PR-08 introduces source-controlled declarative input schemas and canonical atomic per-workflow persistence while preserving Share Invite compatibility mirrors and all PR-06/PR-07 workflow behavior. Production remains `share_invite` only; PR-09 workflow-aware Task/data/report compatibility remains not started.

Candidate documents:
- `updates/v1.0.6.25-pr08-dynamic-workflow-inputs.md`
- `verification/V1.0.6.25_PR08_DYNAMIC_WORKFLOW_INPUTS.md`

# VibraPilot Documentation

## Current release

- Official Release Baseline: **VibraPilot v1.0.6.23 — PR-06 Workflow State Persistence + Atomic Switch/Restart**.
- Previous release: **v1.0.6.22 — PR-05 Master Workflow Gate**.

### PR-06 documentation

v1.0.6.23 persists one active built-in workflow and adds fail-closed atomic switch/restart infrastructure. Production still contains only `share_invite`; PR-07 owns Workflow Showcase UI and PR-08 owns dynamic per-workflow inputs.

See:

- `updates/v1.0.6.23-pr06-workflow-state-atomic-switch.md`
- `verification/V1.0.6.23_PR06_WORKFLOW_STATE_ATOMIC_SWITCH.md`

### PR-05 historical release

PR-05 remains the historical v1.0.6.22 Master Workflow Gate release. Its version-specific update and verification documents remain immutable historical evidence.

## Browser automation status

Browser capabilities are substantially implemented, including managed profiles, lifecycle synchronization, durable downloads, explicit file chooser uploads, unpacked extension validation and diagnostics. Full target-Windows technical acceptance remains incomplete for the documented remaining persistence/Sandbox/crash/multi-Task matrices. CAPTCHA causality remains deferred/unverified.

## Historical documentation

Older version-specific update and verification files remain historical evidence. They may describe the state at the time they were written and are not the authoritative current project ledger.

Private current development/governance records live under `project/`; they are not runtime dependencies and must not be included in clean public release artifacts.
