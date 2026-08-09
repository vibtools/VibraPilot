# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.5**

The exact user-supplied **`VibraPilot_v1.0.6.4_Latest_Updated_Baseline.zip`** (SHA-256 `ea65bd89d908c5db8edfcf01e6b7c5e11410ffe57a98044f9e8913477f9e89e6`) is the Official Baseline Freeze for `VP-PROD-MT-LR-001`. Version **1.0.6.5** is the approved production runtime hardening promotion for Multiple Task, long-run worker stability and data integrity/recovery.

The current production scope is machine-checked through `config/verification/production_mt_lr_v1.0.6.5_scope.json`. The approved runtime surface is limited to `backend.py`, `qt_app.py`, `data_io.py`, the new `task_runtime_store.py` and `config/settings.defaults.json`, plus required tests/verifier/version/documentation records. Licora API v2, selectors, ActivationPage, Browser Settings and out-of-scope files/settings remain frozen by hash/AST contracts. Historical Phase-02 scope manifests remain retained as prior-release evidence.

## Release documentation policy

Every production update must include:

1. synchronized runtime/package/build/documentation version metadata,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise entry in `UPDATE_LOG.md`,
4. a detailed per-update note under `docs/updates/`,
5. README/configuration documentation for user-visible or operational changes, and
6. verification/tests that encode the approved new invariants and preserve frozen behavior.

The preserved source under `project/research/source_baseline/` remains a private forensic comparison baseline when present. Private development/runtime records remain gitignored; public verification and release archives must not include `project/`, `AppData/`, `Logs/`, `Reports/`, `FailedData/`, `__pycache__/` or `.pytest_cache/`.
