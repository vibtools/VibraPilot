# VibraPilot v1.0.6.30 Workflow Plugin System — Replace-Ready Delta Manifest

Patch status: **IMPLEMENTATION VERIFIED / REPLACE-READY / GITHUB NOT WRITTEN**  
Patch type: **replace-ready delta over the exact Official Baseline Freeze**

## Official Baseline Freeze

- Product: VibraPilot
- Baseline version: `1.0.6.28`
- Baseline GitHub commit: `fff8160157d4d9b68b2d28b11105b0f7f38ed17d`
- Baseline GitHub tree: `1712f05f9815c2fef4ef557d1bde3b17f7c62890`
- Baseline status: PR-11 release baseline
- PR-12/v1.0.6.29 packaging implementation: **not imported into this functional delta**

## Candidate

- Target version: `1.0.6.30`
- Plan: `VP-V10630-WORKFLOW-PLUGIN-SYSTEM-001`
- Required commit message: `feat(workflows): add trusted plugin loading and dynamic workflow controls`
- Delivery mode: Replace-Ready Delta ZIP only
- GitHub write by assistant: **NO**

## Implemented Scope

- Preserves the existing one-active-workflow atomic switch/restart/recovery model.
- Extends the built-in workflow catalog with validated trusted external `.vpworkflow` packages.
- Adds managed external workflow installation under the VibraPilot application-data workflow root.
- Adds plugin API v1, package/schema/runtime validation, staged atomic install and fail-closed incompatible-plugin handling.
- Keeps Python as the workflow business/browser logic runtime; JSON remains declarative configuration only.
- Adds workflow-selectable global Workflow Inputs and a new Workflow Settings page with isolated persistence.
- Adds workflow-controlled Task schema, compact Task card, `Task Settings`, workflow step and workflow metrics.
- Keeps Core Task status, threading, browser lifecycle, retry/backoff, persistence, recovery, reports, logs and licensing Core-owned.
- Moves task-specific Target URL/data configuration behind Task Settings; new Tasks no longer consume a global default Target URL.
- Simplifies App Settings while retaining authorized testing and send-limit controls; failed/unprocessed data preservation and running-task close confirmation are enforced as safety behavior.
- Keeps the existing Share Invite workflow selectors/business sequence frozen.
- Does not add per-Task mixed workflows, a JSON Playwright interpreter, marketplace, sandbox, automatic dependencies, plugin uninstall/update, or an invented second production workflow.

## Verification Evidence

```text
compileall: PASS
targeted v1.0.6.30 plugin/config matrix: PASS
affected historical + v1.0.6.30 matrix: 195 passed, 41 subtests passed
historical PR05-PR11 regression: 94/94 PASS
final full pytest after Cycle-1 post-apply compatibility repair: 402 passed, 5 skipped, 113 subtests passed
full unittest discover: 200 tests OK, 5 skipped
scripts/verify_repository.py: PASS
frozen runtime SHA-256 contract: PASS
private project/ exclusion: PASS
PR-12 packaging-surface exclusion: PASS
```

The test-only invoice-like plugin fixture exists only under `tests/`; no fake/demo second production workflow is installed or registered.

Post-apply Windows evidence identified `V10630-QT-TASKSLOT-FAKEAPP-COMPAT-001`; Cycle-1 restores the frozen lightweight Qt TaskSlotWidget host contract without changing production MainWindow workflow behavior. Owner-side Windows/PySide6 full-test confirmation is required after applying the repair delta.

## Frozen / Unchanged

The scope contract freezes the existing Share Invite runtime, workflow registry/contracts/state/recovery modules, browser capabilities, TaskRuntimeStore, workspace state and `.github/workflows/ci.yml`. Browser Chrome-preferred/Chromium-fallback behavior, managed browser profiles, licensing protocol/device identity, report columns, CAPTCHA boundary and packaging remain outside this functional change.

## Payload

`DELTA_FILE_LIST.txt` is the authoritative project-relative replacement/addition list. It contains no `project/` path. `SHA256SUMS.txt` records SHA-256 for every payload file plus `PATCH_MANIFEST.md` and `DELTA_FILE_LIST.txt`.
