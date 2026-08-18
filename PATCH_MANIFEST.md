# VibraPilot v1.0.6.43 — Phase 2 Forensic Closure Replace-Ready Patch

## Official baseline

- Input: `VibraPilot_Official_v1.0.6.42_Baseline(1).zip`
- Input SHA-256: `0713798e061b0eef15c1a1d4cb52e1347687f7498419b9ab1a79b3017f31dae1`
- Baseline version: `1.0.6.42`
- Baseline branch commit: `8c3e9a137ecf852aa152dba0590414e7f8f6209d`
- Baseline Git tree: `c61a9864e99659bf0a3d3cb229e1ad6e5e85cb69`
- Target version: `1.0.6.43`

## Corrective scope

- restart-free historical workflow-switch compatibility service;
- lifecycle transaction root/type and workflow-identity fail-closed validation;
- schema-v2 workspace Task-shell preservation when workflow identity is unresolved/unavailable;
- unresolved legacy unfinished-run package-mutation blocking;
- same-session live lifecycle transaction blocking for package mutation, Task creation and browser start;
- Default Workflow UI semantics replacing residual global `ACTIVE` wording;
- removal of one duplicated staging-directory setup statement.

## Production source changes

- `src/vibrapilot/qt_app.py`
- `src/vibrapilot/workflow/plugin_loader.py`
- `src/vibrapilot/workspace_state.py`

Chrome prerequisite/runtime/installer/AuthentiCode, Plugin API 1, backend worker logic, runtime DB schema-v2 implementation, power, licensing, settings defaults, dependencies, CI and portable packaging are frozen from v1.0.6.42.

## Verification evidence

- v1.0.6.42 baseline: repository verifier PASS; pytest 541 passed / 6 skipped / 105 subtests; unittest 201 OK / 6 skipped; compileall PASS.
- tests-first v1.0.6.43 reproduction: 8 concrete failures reproduced / 1 guard already passing.
- corrected v1.0.6.43 closure tests: 9 PASS.
- targeted historical/current correction gate: 123 PASS.
- broader Phase-1/Phase-2/persistence/Chrome gate: 190 PASS.
- frozen SHA audit: PASS.
- metadata/current scope tests: 13 PASS; repository verifier PASS.
- final full pytest: 550 passed, 6 skipped, 105 subtests passed.
- final full unittest: 201 OK, 6 skipped.
- compileall: PASS.
- `git diff --check`: PASS.
- deleted files: 0.

## Delta inventory

- Public changed/new files: 30
- Private/local `project/` files: 15
- Total Delta entries: 45
- `project/**` is local/private only and must never be staged/pushed.

## External gates

Windows live acceptance and GitHub v1.0.6.43 CI remain PENDING and are not claimed PASS.
