# VibraPilot v1.0.6.30 Workflow Plugin System — Startup/UI Repair Delta Manifest

Patch status: **IMPLEMENTATION VERIFIED / REPLACE-READY / WINDOWS STARTUP RECHECK REQUIRED**
Patch type: **targeted repair delta over the pushed v1.0.6.30 candidate**

## Repair Baseline Freeze

- Product: VibraPilot
- Version: `1.0.6.30`
- Baseline branch: `v10630-workflow-plugin-system`
- Baseline GitHub commit: `e0a080062a4ddb783dc94568801358ce2e01598c`
- Baseline parent: `fff8160157d4d9b68b2d28b11105b0f7f38ed17d`
- Baseline commit message: `feat(workflows): add trusted plugin loading and dynamic workflow controls`
- GitHub write by assistant: **NO**

## Primary Error

- ID: `V10630-MAINWINDOW-STATICMETHOD-STARTUP-001`
- Reproduction: `py run.py`
- Failure: `TypeError: MainWindow._transaction_root_has_directories() takes 1 positional argument but 2 were given`
- Exact path: workspace construction → Workflows page registration → workflow card → workflow recovery blocker.
- Root cause: v1.0.6.30 dropped the frozen `@staticmethod` decorator from `MainWindow._transaction_root_has_directories(root)`. Instance invocation therefore injected `self` in addition to the explicit path argument.
- UI effect: workspace shell construction aborted before initial Task creation, leaving a partially built shell that appeared as a broken/blank UI.

## Scope-Locked Fix

- Restore the exact frozen `@staticmethod` descriptor only.
- Add a generic AST regression that detects any `self.<method>(...)` target whose descriptor/signature cannot accept instance binding.
- Extend the v1.0.6.30 post-apply verifier with the same descriptor contract.
- Record the repair in v1.0.6.30 scope/changelog/README/update/verification documentation.
- Correct the previously observed patch-manifest trailing whitespace and verification-document EOF formatting.
- No workflow business logic, browser engine, Task lifecycle, persistence schema, licensing, report logic, global design tokens, palette, or unrelated UI behavior is changed.

## Forensic Findings

- The pushed GitHub branch is exactly one commit ahead of PR-11 baseline and contains the approved 55-file v1.0.6.30 feature delta.
- Global UI design assignments remain unchanged except approved navigation/browser-settings ownership changes; `TaskSlotWidget.task_qss` only adds the approved Task Settings button selector.
- The uploaded full baseline archive contains unrelated PR-12 packaging/runtime/private-development material and is not byte-equivalent to the clean public v1.0.6.30 branch. This repair delta therefore targets the GitHub candidate commit above and does not delete or rewrite unrelated PR-12/private files.
- No fake/demo production workflow was found; the invoice-like workflow remains test-only.

## Verification

```text
clean candidate pre-repair pytest: 402 passed, 5 skipped, 113 subtests
targeted affected repair matrix: 40 passed
post-repair compileall: PASS
post-repair full pytest: 403 passed, 5 skipped, 113 subtests
post-repair unittest: 200 OK, 5 skipped
descriptor consistency audit: PASS
```

Final Windows/PySide6 `py run.py` startup acceptance remains an owner-side runtime gate because the repair environment does not provide PySide6.

## Required Commit Message

`fix(ui): restore workflow recovery startup contract`

## Payload

`DELTA_FILE_LIST.txt` lists the eight project-relative replacement files. `SHA256SUMS.txt` covers those files plus this manifest and the delta file list.
