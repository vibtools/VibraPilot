# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.10**

Version **1.0.6.10** is the scope-locked license-login forensic fix promoted from exact GitHub v1.0.6.9 commit `cd6ec96736626256daeed1d36775d21e90abf7ee` and clean v1.0.6.9 baseline archive SHA-256 `fe5ebed39608735dc72674a7342cb5f68afa3831afb94b8b944d210464d27805`.

The runtime change surface is limited to `src/vibrapilot/backend.py` and `src/vibrapilot/qt_app.py`. `LicenseManager` device/session persistence, activation recovery and logout sequencing plus `MainWindow.start_license_recheck` are the only approved behavioral surfaces. Licora wire protocol (`licensing_v2.py`), public endpoint/key configuration, browser/task/workflow/report logic and ActivationPage visual design remain frozen.

Version **1.0.6.9** remains the historical Workflow Inputs persistence verification/fix release.

## Release documentation policy

Every production update must include:

1. synchronized runtime/package/build/documentation version metadata,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise entry in `UPDATE_LOG.md`,
4. a detailed per-update note under `docs/updates/`,
5. README/configuration documentation for user-visible or operational changes, and
6. verification/tests that encode the approved new invariants and preserve frozen behavior.

The preserved source under `project/research/source_baseline/` remains a private forensic comparison baseline when present. Private development/runtime records remain gitignored; public verification and release archives must not include `project/`, `AppData/`, `Logs/`, `Reports/`, `FailedData/`, `__pycache__/` or `.pytest_cache/`.
