# v1.0.6.43 Version Boundary

- Official input: v1.0.6.42.
- Target: v1.0.6.43.
- Classification: Phase-2 forensic closure only; no new feature scope.
- Production changes are restricted to the three files explicitly authorized by `config/verification/v1.0.6.43_phase2_forensic_closure_scope.json`.
- v1.0.6.43 becomes the next local development baseline only after final automated verification and Delta sealing; public release status still requires GitHub CI and Windows live acceptance.

---

# v1.0.6.42 Version Boundary

- Baseline: v1.0.6.41 / `615fe1148431b90334e9ff3f9ae02b37a36bd1d8`.
- Target: v1.0.6.42.
- Classification: Phase 2 Workflow Lifecycle Management + True Multiworkflow + Chrome prerequisite final verification.
- External Plugin API remains 1.
- Workspace state schema advances 1 → 2 for per-Task workflow identity.
- Task runtime database schema advances 1 → 2 for run/result workflow provenance.
- No dependency, CI, portable packaging or licensing version boundary change.

---

# Current Candidate — v1.0.6.41 Phase 1 Active-Page Origin Closure

- Official input baseline: **v1.0.6.40**, commit `7e6f4cc7abf49e08d4a94124ebffa97bb7794137`.
- Target: **v1.0.6.41**.
- Production change: one method boundary in `src/vibrapilot/backend.py` (`AutomationWorker._origin_from_url`).
- No dependency, runtime-setting, UI, workflow, persistence, licensing, CI or packaging changes.
- Phase 2 is **NOT STARTED** and moves to **v1.0.6.42** because v1.0.6.41 is consumed by this closure.
- v1.0.6.41 becomes the next internal baseline only after delta sealing and required automated verification; GitHub CI/Windows live acceptance remain separately recorded gates.

---

# Current Candidate — v1.0.6.40 Phase 1 Forensic Closure

- Official owner-frozen baseline: **v1.0.6.39**, commit `7bd6428a89607df34dc96fbed28d1b2ac20b9365`, tree `074780843a9f6ed62d974123339020b86353d716`.
- Target: **v1.0.6.40**.
- Classification: Phase 1 forensic verification/corrective closure only.
- Allowed production source corrections: `src/vibrapilot/backend.py`, `src/vibrapilot/qt_app.py`.
- Phase 2 is **NOT STARTED** and, because v1.0.6.40 is consumed by this closure release, its planned version becomes **v1.0.6.41**.
- v1.0.6.40 becomes the next baseline only after the replace-ready candidate and required verification gates pass; GitHub publication/CI status must be recorded separately rather than inferred.

---

# Current Candidate — v1.0.6.39 Phase 1

- Frozen source baseline: v1.0.6.38 / `bc894115f505b7b9ecbc15a235b91d37a9693cec`.
- Target: v1.0.6.39.
- Scope: Runtime Reliability & Workflow-Scoped Session Policy only.
- Local automated verification: GREEN.
- Windows live acceptance: PENDING.
- GitHub publication/tag/release: NOT STARTED for v1.0.6.39.
- Phase 2 workflow lifecycle/true multiworkflow: NOT STARTED.

A v1.0.6.39 release may be tagged only after target-Windows acceptance, GitHub PR/CI, portable RC and release gates are green. The historical version records below are retained unchanged as release evidence.

---

# Current portable fix candidate — v1.0.6.38

`v1.0.6.38` is a defect-only packaging/runtime-location increment from the v1.0.6.37 portable release candidate. It fixes the exact packaged data-root failure proven by GitHub Actions run `32056816056`; it does not redesign the portable architecture or reopen application business logic.

Freeze rule: v1.0.6.38 becomes the official next baseline only after PR CI, post-merge main CI, a fresh `workflow_dispatch` Nuitka OneDir build, packaged startup smoke, owner Windows portable acceptance, and a clean source baseline ZIP + SHA-256 all pass.

# Current packaging candidate — v1.0.6.37

`v1.0.6.37` is a packaging/release-infrastructure increment from the frozen v1.0.6.36 functional baseline. It introduces the first supported Nuitka standalone OneDir portable Windows artifact and does not reopen v1.0.6.36.

# Current Version — 1.0.6.36

`1.0.6.36` is the Share Invite Workflow Externalization release. The frozen source baseline contains zero built-in workflows; Share Invite is distributed separately as `Share_Invite_v1.0.vpworkflow`.

# Versioning — v1.0.6.35 Workflow-Scoped Test Safety

- Frozen baseline: **v1.0.6.34**, commit `a0e3621e831d402649ab55859e00b59d5f0ad634`, ZIP SHA-256 `91566da389aa05ea65e08a60d6ae56321d23dbf88fa26f87b22542e7cc0d3a70`.
- Current candidate: **v1.0.6.35 / Workflow-Scoped Test Safety Isolation**.
- Share Invite retains real Test Mode enforcement; global workflow host semantics are neutral.

# v1.0.6.33 — Browser Forensic Closure Candidate

`v1.0.6.32` is the immutable forensic input baseline. `v1.0.6.33` is a patch release containing only confirmed Phase-01/Phase-02 defect closures.

# Versioning — v1.0.6.32 Phase 2 Candidate

- Official functional baseline: **v1.0.6.31 / Chrome-Only Runtime Foundation**, commit `fc9081b0f760ac6b380b8c574680fc2c15764be0`.
- Current development candidate: **v1.0.6.32 / Chrome Prerequisite UX + Secure Install**.
- v1.0.6.31 Phase 1 is complete and promoted to `main` with owner Windows acceptance and post-merge CI PASS.
- v1.0.6.32 is not functionally complete until automated verification, owner Windows missing-Chrome/install/UAC acceptance, PR CI and main promotion all pass.
- Build-system Chromium cleanup and EXE/MSI packaging remain a separate future approved track.

# Versioning — v1.0.6.31 Phase 1 Candidate

- Official Baseline Freeze: **v1.0.6.30 / Workflow Plugin System**, commit `c86b6faebd58be9bff61cc8fdc12c76dda49a975`.
- Current development candidate: **v1.0.6.31 / Chrome-Only Runtime Foundation**.
- v1.0.6.31 is **COMPLETE / OWNER WINDOWS ACCEPTED / PR+MAIN CI PASS**.
- Phase 2 Chrome prerequisite/download/install UX is implemented separately as the **v1.0.6.32** candidate; it is not part of v1.0.6.31.
- Build-system Chromium cleanup and EXE/MSI packaging remain deferred until functional updates are complete.
- The separate historical v1.0.6.29 PR-12 packaging lineage is not imported into this functional delta.

# Versioning — PR-11 Candidate

- Current release baseline: **v1.0.6.27 / PR-10**.
- Current development candidate: **v1.0.6.28 / PR-11 E2E Windows / Multi-Task Regression**.
- v1.0.6.28 is not RELEASE COMPLETE until target-Windows mandatory acceptance is PASS (or each residual is explicitly owner-accepted), owner local acceptance is PASS, exact GitHub publication completes and Windows/Python 3.12 CI passes.
- Production `src/vibrapilot/**` remains byte-frozen from v1.0.6.27.

# Versioning — PR-10 Candidate

- Current release baseline: **v1.0.6.26 / PR-09**.
- Current development candidate: **v1.0.6.27 / PR-10 Workflow Error Handling / Recovery**.
- v1.0.6.27 is not RELEASE COMPLETE until owner local acceptance, exact GitHub publication and Windows/Python 3.12 CI PASS.

# Versioning — PR-09 Candidate

- Current release baseline: **v1.0.6.25 / PR-08**.
- Current development candidate: **v1.0.6.26 / PR-09 Workflow Data/Persistence/Reporting Compatibility**.
- v1.0.6.26 is not RELEASE COMPLETE until owner local acceptance, exact GitHub publication and Windows/Python 3.12 CI PASS.

- Current release baseline: **v1.0.6.24 / PR-07**.
- Current development candidate: **v1.0.6.25 / PR-08 Dynamic Workflow Inputs + per-workflow persistence**.
- v1.0.6.25 is not RELEASE COMPLETE until owner local acceptance, exact GitHub publication and Windows/Python 3.12 CI PASS.

## Current baseline classification — 2026-08-10

- **Official Release Baseline:** v1.0.6.23 / PR-06 Workflow State + Atomic Switch/Restart.
- **Previous Official Release:** v1.0.6.22 / PR-05 / GitHub `e5763852249d86db35d9838a61f276eada823f08`.
- **Final planned production line:** v1.0.7.0.

v1.0.6.23 preserves the v1.0.6.22 Master Workflow Gate and promotes only the approved workflow-state persistence and atomic switch/restart infrastructure. Browser technical acceptance remains a separate carried release track.

## v1.0.6.22 — PR-05 Master Workflow Gate

Scope-locked fourth-segment production update from official v1.0.6.21 baseline `8aa8de7df68cb5d402bd3d2ae2400efc36189fbcca8f36bddb23679dbc78ff14` and GitHub commit `cb4337812c0ac4f0e944093b7a7d4400fe618d57`. PR-05 adds only the in-memory Master Workflow execution gate and fail-closed built-in runtime resolution. Active workflow persistence/switching remains reserved for PR-06.

## v1.0.6.20 — PR-04 Share Invite workflow extraction

Scope-locked fourth-segment production update from the reconciled PR-02/PR-03 v1.0.6.19 baseline at GitHub commit `999212b947583927204535f59832f1379d9306f4`. PR-04 extracts the existing Share Invite implementation behind the built-in workflow framework while preserving the safety-critical worker state machine and all out-of-scope application behavior.

Workflow switching, active-workflow persistence, Workflow UI/dynamic inputs and CAPTCHA changes remain outside this release.

## v1.0.6.19 — Browser foundation verification/fix

Verification/fix release based on uploaded v1.0.6.18 baseline SHA-256 `d18277ea00ae581ede45c8d3e647cd0f41625aeb0d5b8aad71715c19e4e29ae9`.

Runtime changes are limited to `src/vibrapilot/backend.py` and `src/vibrapilot/browser_diagnostics.py`. The v1.0.6.18 launch policy is preserved. Sandbox default is not changed because Sandbox-ON Windows acceptance remains unavailable. No dependency declaration, database/workspace schema, Browser Settings key, UI page, workflow or licensing behavior changes.

v1.0.6.19 is the next Official Development Baseline Freeze after source/delta verification; Windows Sandbox-ON/CAPTCHA/capability gates remain explicit pending acceptance.

## v1.0.6.18 — Browser foundation stabilization

Candidate from official v1.0.6.17 baseline. Windows browser acceptance is required before the next Official Baseline Freeze.

## v1.0.6.17 — Browser capabilities

Production feature release for `VP-BROWSER-CAPABILITIES-001`. The v1.0.6.16 workspace-persistence verification baseline is preserved outside the explicitly approved browser capability surfaces. No settings-key, TaskRuntimeStore-schema, WorkspaceState-schema or dependency change is included.

## v1.0.6.16 — Workspace persistence verification fix

Patch release preserving v1.0.6.15 production runtime byte-for-byte while correcting CI/test-harness compatibility and documentation formatting.

## v1.0.6.15 — Workspace persistence

Patch release for `VP-WORKSPACE-PERSISTENCE-001`. No TaskRuntimeStore schema, settings-key, browser-profile or dependency change. The version remains a candidate until Windows runtime and GitHub CI acceptance are green.

## v1.0.6.14 scope identity

Version **1.0.6.14** is the scope-locked managed-persistent-browser and Closed Task recovery candidate based on verified v1.0.6.13 GitHub commit `5f082df8d1226710c095d4a8e591fb153c02c1c3`. Runtime changes are limited to `src/vibrapilot/backend.py`, `src/vibrapilot/qt_app.py`, `src/vibrapilot/task_runtime_store.py` and `config/settings.defaults.json`; SQLite schema version 1 is preserved.

# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.23**

Version **1.0.6.13** is the verification/CI-stability correction anchored to uploaded v1.0.6.12 archive SHA-256 `becd6add21d377e98e458ce856c9c3baa710a113459bde0c737507c122c2a9b5` and GitHub v1.0.6.12 commit `a9cfec319285db2fb9fbff8d4bf0ede8ac87686b`.

It authorizes **no production runtime source changes**. The v1.0.6.12 `backend.py`, `qt_app.py`, `task_runtime_store.py`, Browser Settings defaults, licensing, selectors, workflow and persistence schema are frozen. The only functional correction is to the Windows concurrency verification harness and its scope/metadata/documentation.

Version **1.0.6.12** is the scope-locked `VP-BROWSER-UI-LIFECYCLE-001` candidate built from user-frozen v1.0.6.11 archive SHA-256 `9ecb7cd66f24832c3555d219a6f8aaf47358877dd417eeb703b5a755964fc90a` and GitHub v1.0.6.11 commit `8670415b1df221ebeeb7d8f3fba4f991a91d43ec`.

The approved runtime surface is limited to browser lifecycle methods in `src/vibrapilot/backend.py` and Task/browser/workspace lifecycle methods in `src/vibrapilot/qt_app.py`. Managed persistent profiles, Browser Settings defaults, task persistence schema, site-specific workflow logic, licensing and visual design remain frozen.

Version **1.0.6.11** remains the verified Qt focus-lifecycle baseline until the v1.0.6.12 Windows live gate passes.

Version **1.0.6.11** is the scope-locked `VP-QT-FOCUS-LIFECYCLE-001` correction promoted from exact GitHub v1.0.6.10 commit `d712a9d04fa62e5e3a0df9c00a99c1315052bd05` and clean v1.0.6.10 baseline archive SHA-256 `d818aa1d4ee3492df810fb29034999293b47c343444469b32ceebbbb92f5e044`.

The runtime change surface is exactly `vib_validation_app/focus_manager.py`. It hardens PySide6 C++ object lifetime checks for stale focused widgets and delayed tooltips while preserving the frozen visual focus behavior. Backend, licensing, ActivationPage, browser/task/workflow/report logic, settings and dependencies remain frozen.

Version **1.0.6.10** remains the historical license-login durability/recovery release, and **1.0.6.9** remains the historical Workflow Inputs persistence verification/fix release.

## Release documentation policy

Every production update must include:

1. synchronized runtime/package/build/documentation version metadata,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise entry in `UPDATE_LOG.md`,
4. a detailed per-update note under `docs/updates/`,
5. README/configuration documentation for user-visible or operational changes, and
6. verification/tests that encode the approved new invariants and preserve frozen behavior.

The preserved source under `project/research/source_baseline/` remains a private forensic comparison baseline when present. Private development/runtime records remain gitignored; public verification and release archives must not include `project/`, `AppData/`, `Logs/`, `Reports/`, `FailedData/`, `__pycache__/` or `.pytest_cache/`.
