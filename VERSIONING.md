# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.11**

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
