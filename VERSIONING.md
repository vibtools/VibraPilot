# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.8**

Version **1.0.6.8** is the approved `VP-WORKFLOW-INPUTS-001` release. Its baseline is the final v1.0.6.7 tree after the Windows SQLite concurrency correction, canonical tree fingerprint `84d22fd2c1fef38cbf49024f7d3b2c9ec250e3389dd2b479192735fb2419bb89`.

The v1.0.6.8 runtime scope is limited to `qt_app.py` plus the new form-metadata-only `workflow_inputs.py`; existing workflow settings keys/values, backend behavior, Browser Settings, task workflow and API v2 remain preserved.

The exact user-supplied **`VibraPilot v1.0.6.5.zip`** (SHA-256 `f391099de9d0d117d190b2898b96d5e90b3f102541cf8efa217f9e9fbfbed118`) is the Official Baseline Freeze for the v1.0.6.7 verification/fix cycle. Version **1.0.6.7** preserves the approved `VP-PROD-MT-LR-001` architecture and corrects only verified startup, worker-shutdown backpressure, crash-result-ledger and source-package hygiene defects plus synchronized wording/version records.

The original production scope remains recorded in `config/verification/production_mt_lr_v1.0.6.5_scope.json`. The current correction boundary is additionally machine-checked by `config/verification/v1.0.6.7_vp_prod_mt_lr_verification_fix_scope.json`, which freezes `LicenseManager`, selectors, `ActivationPage`, Browser Settings, `MainWindow`, `TaskRuntimeStore`, import logic and all non-approved `AutomationWorker` methods against the uploaded v1.0.6.5 baseline.

## Release documentation policy

Every production update must include:

1. synchronized runtime/package/build/documentation version metadata,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise entry in `UPDATE_LOG.md`,
4. a detailed per-update note under `docs/updates/`,
5. README/configuration documentation for user-visible or operational changes, and
6. verification/tests that encode the approved new invariants and preserve frozen behavior.

The preserved source under `project/research/source_baseline/` remains a private forensic comparison baseline when present. Private development/runtime records remain gitignored; public verification and release archives must not include `project/`, `AppData/`, `Logs/`, `Reports/`, `FailedData/`, `__pycache__/` or `.pytest_cache/`.
