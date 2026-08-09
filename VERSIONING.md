## v1.0.6.14 scope identity

Version **1.0.6.14** is the scope-locked managed-persistent-browser and Closed Task recovery candidate based on verified v1.0.6.13 GitHub commit `5f082df8d1226710c095d4a8e591fb153c02c1c3`. Runtime changes are limited to `src/vibrapilot/backend.py`, `src/vibrapilot/qt_app.py`, `src/vibrapilot/task_runtime_store.py` and `config/settings.defaults.json`; SQLite schema version 1 is preserved.

# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release candidate: **1.0.6.14**

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
