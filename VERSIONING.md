# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.9**

Version **1.0.6.9** is the scope-locked forensic verification/fix promotion of GitHub v1.0.6.8 commit `82fc678fe4d3e8aab9c11ff3e54cf4455e0d3203`. The v1.0.6.8 source tree is the Official Baseline Freeze for this cycle; the canonical normalized source-tree fingerprint is `8358ffdca13bedd491ee319aae299fdf9ff636e6cb74caf7dbb53c389d94f6b7`.

The v1.0.6.9 runtime change surface is limited to the two `MainWindow` methods `save_workflow_inputs` and `reset_workflow_inputs` in `qt_app.py`. All other v1.0.6.8 runtime files and MainWindow methods are frozen. The fix adds rollback/exception containment only; settings keys, values on successful persistence, Workflow Inputs ownership, backend behavior, Browser Settings, task workflow and API v2 remain preserved.

Version **1.0.6.8** remains the historical approved `VP-WORKFLOW-INPUTS-001` UI-ownership separation release.

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
