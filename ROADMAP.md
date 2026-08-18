# Current Roadmap — v1.0.6.41 Phase 1 Active-Page Origin Closure

## Phase 1 seal — v1.0.6.41

v1.0.6.40 was re-audited against the locked Phase 1 plan. The only newly reproduced implementation defect was default-port origin non-canonicalization in deterministic active-page selection. v1.0.6.41 fixes only that defect and adds regression/verification evidence. No Phase 2 functionality is included.

## Phase 2 — v1.0.6.42

**NOT STARTED.** Workflow Update/Replace, Remove/Unload/Deactivate, restart-free switch, per-Task workflow identity and true simultaneous different-workflow execution remain frozen. v1.0.6.41 is consumed by this Phase 1 forensic seal, so Phase 2 advances to v1.0.6.42 without scope expansion.

---

# Current Roadmap — v1.0.6.40 Phase 1 Forensic Closure

## Phase 1 closure — v1.0.6.40

The v1.0.6.39 Phase 1 implementation has been forensically audited against the locked plan. v1.0.6.40 is reserved only for the proven corrective gaps: guaranteed sleep-guard cleanup, enforceable required-session recycle verification, fail-safe page-origin parsing, exact session UI wording and stronger verification evidence.

No Phase 2 implementation is included.

## Phase 2 — v1.0.6.41

**NOT STARTED.** Workflow Update/Replace, Remove/Unload/Deactivate, restart-free switch, per-Task workflow identity and true simultaneous different-workflow execution remain frozen. The former v1.0.6.40 Phase 2 version slot is superseded by this v1.0.6.40 forensic closure, so Phase 2 advances to v1.0.6.41 without any scope expansion.

---

# Current — v1.0.6.38 Portable Runtime Root Fix

- Input source baseline: v1.0.6.37 / `299e93a89db3d30505350f474f79eefc330ee923`.
- Scope: correct the proven Nuitka OneDir packaged data root only; all application business behavior remains frozen.
- Portable architecture remains GitHub Actions Windows 2022 → Python 3.12 x64 → Nuitka 4.1.3 standalone OneDir → system Google Chrome; no bundled Chromium; no WiX/MSI.
- Next gate: source/PR CI → main CI → fresh RC build → startup smoke → owner Windows portable acceptance → clean v1.0.6.38 baseline freeze.

# Current — v1.0.6.37 Portable Nuitka OneDir Release

- Frozen input: v1.0.6.36 FINAL / `40b9b65d3900760d919167dc6711a4fcd494f010`.
- Scope: GitHub Actions Windows x64 Nuitka standalone OneDir portable ZIP only.
- System Google Chrome remains the sole production browser; no bundled Chromium.
- WiX/MSI is explicitly skipped.
- First gate is a manually dispatched RC artifact followed by owner Windows acceptance before tag release.

# Current — v1.0.6.36 Share Invite Externalization

- Complete the workflow-neutral Core by shipping Share Invite as a standalone trusted workflow package.
- Preserve one-active-workflow switching, existing plugin compatibility and all browser/licensing/persistence boundaries.
- URL workflow installation remains deferred to a later separately scoped update.

# VibraPilot Roadmap — v1.0.6.35 Workflow-Scoped Test Safety

- Baseline: v1.0.6.34 / `a0e3621e831d402649ab55859e00b59d5f0ad634`.
- Scope: remove legacy global Test Mode coupling from the multi-workflow host while preserving Share Invite's workflow-owned safety enforcement.
- Build/Nuitka/WiX remain deferred.

# VibraPilot Roadmap — v1.0.6.33 Forensic Closure

- Frozen audit baseline: **v1.0.6.32**, commit `a001f67972c47832a5e59af5f9350a0409e7eab6`.
- Current hotfix candidate: **v1.0.6.33**, confirmed-defect browser forensic closure only.
- Phase-01 and Phase-02 functional scope remains locked; build/Nuitka/WiX/package track remains deferred.

# VibraPilot Roadmap — v1.0.6.32 Chrome Prerequisite Secure Install

- Official baseline: **v1.0.6.31 / Phase 1 COMPLETE**, commit `fc9081b0f760ac6b380b8c574680fc2c15764be0`.
- Current functional candidate: **v1.0.6.32 / Phase 2 Chrome Prerequisite UX + Secure Install**.
- Phase 2 implements startup/Open Browser/backend prerequisite checks, explicit user-consented official Google MSI download, Authenticode + Google LLC signer validation, elevated Windows Installer execution and post-install Chrome re-detection.
- Chrome-only runtime, sandbox, cache defaults, managed profiles, workflows, licensing and persistence remain preserved.
- Build-system Chromium cleanup, Nuitka, WiX and release packaging remain deferred until this functional phase is fully accepted.

# VibraPilot Roadmap — v1.0.6.31 Chrome-Only Runtime Foundation

- Official Baseline Freeze: **v1.0.6.30 / Workflow Plugin System**, commit `c86b6faebd58be9bff61cc8fdc12c76dda49a975`.
- Historical Phase 1 candidate: **v1.0.6.31 / Chrome-Only Runtime Foundation**.
- Phase 1 status: **COMPLETE / OWNER WINDOWS ACCEPTED / PR+MAIN CI PASS**.
- Phase 1 locks browser launch to branded Google Chrome, mandates sandboxing, enables normal HTTP cache by default, removes Chromium/custom-binary runtime escape paths, migrates stale browser policy settings, and adds Chrome runtime discovery/status foundation.
- Preserve the v1.0.6.30 Workflow Plugin System, one-active-workflow switch/recovery model, Tasks, persistence, licensing, reports, downloads/uploads and managed browser profiles outside the approved browser policy surface.
- Next functional phase was promoted to **v1.0.6.32 / Phase 2 Chrome Prerequisite UX + Secure Install** and is now the current approved implementation candidate.
- Build-system Chromium cleanup and EXE/MSI packaging remain deferred until all functional updates are complete.

# VibraPilot Roadmap — PR-11 Candidate

- Current release baseline: **v1.0.6.27 / PR-10 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.28 / PR-11 E2E Windows / Multi-Task Regression**.
- PR-11 scope: target-Windows evidence and 1/2/4-Task regression only; production runtime/source changes are zero unless a separately approved defect amendment is issued.
- PR-12 Packaging: **NOT STARTED**.
- Future CL Automation / Nuitka OneDir / WiX MSI requirement remains recorded for PR-12 only; no packaging implementation is authorized in PR-11.

# VibraPilot Roadmap — PR-10 Candidate

- Current release baseline: **v1.0.6.26 / PR-09 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.27 / PR-10 Workflow Error Handling / Recovery**.
- PR-10 scope: explicit control-plane recovery, recovery transaction safety and active-runtime preflight only.
- PR-11 E2E Windows / Multi-Task Regression: **NOT STARTED**.
- Future CL Automation / Nuitka OneDir / WiX MSI requirement remains recorded for packaging only; no packaging implementation is authorized in PR-10.

# VibraPilot Roadmap — PR-09 Candidate

- Current release baseline: **v1.0.6.25 / PR-08 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.26 / PR-09 Workflow Data/Persistence/Reporting Compatibility**.
- PR-09 is verification-only at production-runtime level: no database migration, no workflow_id columns, no Task/report/workspace schema redesign.
- PR-10 Workflow Error Handling / Recovery: **NOT STARTED**.

- Current release baseline: **v1.0.6.24 / PR-07 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.25 / PR-08 Dynamic Workflow Inputs + per-workflow persistence**.
- PR-08 scope: source-controlled input schemas, dynamic active-workflow renderer, canonical per-workflow persistence, legacy Share Invite migration/mirror, and immutable worker input snapshots.
- Production registry remains `share_invite` only.
- PR-09 workflow-aware Task/data/report compatibility: **NOT STARTED**.

# VibraPilot Roadmap — Current View

## Current identities

- Official release: **v1.0.6.23 / PR-06 Workflow State + Atomic Switch/Restart**.
- Previous release: **v1.0.6.22 / PR-05 Master Workflow Gate**.
- Final planned production line: **v1.0.7.0**.

## Current progression

| Phase | Status |
|---|---|
| Browser Foundation development gate | CLOSED by owner; technical Windows acceptance still open |
| CAPTCHA decision | DEFERRED / unverified |
| Workflow contracts/registry | complete |
| Share Invite extraction/parity | release complete |
| Master Workflow Gate | release complete v1.0.6.22 |
| Workflow State + Atomic Switch/Restart | **release complete v1.0.6.23** |
| Workflow Showcase UI | not started |
| Dynamic per-workflow inputs | not started |
| Workflow-aware data/reporting | not started |
| Error/recovery hardening | not started |
| Windows E2E / multi-Task final acceptance | not started |
| Packaging / final CI / v1.0.7.0 freeze | not started |

## Browser technical acceptance track

Source implementation is substantial, but the remaining target-Windows download/upload/extension persistence, Sandbox policy, web-storage/history persistence, manual-close/crash/process-kill and real 1/2/4 Task acceptance must still be closed or explicitly accepted before final production approval.

## Next phase rule

PR-07 Workflow Showcase UI does not start automatically. It requires a fresh forensic plan, scope lock and explicit owner approval after PR-06 release closure.

## Next approved continuation

- Phase 2: Chrome prerequisite detection, user-facing required-Chrome UX, secure official download/install, re-detection and Windows acceptance.
- Later separate build-system track: remove packaged Chromium assets/downloads, then build and validate EXE/MSI.
