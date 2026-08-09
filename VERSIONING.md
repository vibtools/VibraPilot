# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration/security maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.4**

The user-supplied **v1.0.6.3** archive is the Official Baseline Freeze for this verification cycle. **v1.0.6.4** is the scope-locked Phase-02-Step-002 verification/fix promotion. It retains the Secure Licora API v2 design from v1.0.6.3 and corrects only verified licensing/session continuity, refresh ambiguity recovery, startup restore/recheck behavior, verification coverage and release-package hygiene.

The original Phase-02 semantic freeze remains machine-checked through `config/verification/phase02_step002_scope.json`. `AutomationWorker`, `SELECTORS`, `TaskItem`, `TaskState`, `ActivationPage` and `BROWSER_SETTING_GROUPS` must keep their v1.0.6.2 canonical AST hashes. The v1.0.6.4 fix boundary is additionally locked by `config/verification/phase02_step002_v1.0.6.4_fix_scope.json`, which records the exact SHA-256 of the user-frozen v1.0.6.3 archive and byte-locks operational files outside the approved fix surface.

## Release documentation policy

Every production update must include:

1. synchronized runtime/package/build/documentation version metadata,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise entry in `UPDATE_LOG.md`,
4. a detailed per-update note under `docs/updates/`,
5. README/configuration documentation for user-visible or operational changes, and
6. verification/tests that encode the approved new invariants and preserve frozen behavior.

The preserved source under `project/research/source_baseline/` remains a private forensic comparison baseline when present. Private development/runtime records remain gitignored; public verification and release archives must not include `project/`, `AppData/`, `Logs/`, `Reports/`, `FailedData/`, `__pycache__/` or `.pytest_cache/`.
