# Phase-02-Step-002 Forensic Verification — VibraPilot v1.0.6.4

**Official baseline:** user-supplied `VibraPilot v1.0.6.3.zip`  
**Baseline SHA-256:** `eec7ed0c5579f4a997c513f78c24ac93b1d814e6d6f8cb06c37d5fb064602078`  
**Date:** 2026-08-08  
**Scope:** latest Phase-02-Step-002 implementation verification/fix only

## Baseline reconstruction

The uploaded v1.0.6.3 archive passed ZIP integrity checking. Excluding gitignored runtime/private/cache paths, its source content matched the previously verified v1.0.6.3 Phase-02-Step-002 source. The archive itself was not release-clean because it included ignored runtime/private/cache trees such as `AppData/`, `Logs/`, `project/`, `__pycache__/` and `.pytest_cache/`. Runtime secret values were treated as private and were not copied into the corrected release.

Before the v1.0.6.4 correction, `compileall`, repository verification and the CI-style unittest suite passed. The documented plain pytest command exposed a repository import-path mismatch because pytest had not been configured with `src`. A later Windows Command Prompt verification also exposed that the documented unittest setup used PowerShell-only `$env:PYTHONPATH` syntax; when that line failed, direct unittest discovery could not import the `src/vibrapilot` package. Both are verification/test-runner portability defects rather than application licensing-protocol defects.

## Verified defects and root causes

- P-256 device identity was generated/cleared at session boundaries instead of being a persistent installation identity.
- Fresh device-key material was saved only after activation success, making response-loss recovery unsafe.
- Ambiguous refresh invalidation was not persisted before fresh-activation recovery.
- Remote validation held the same lock used by UI-facing state reads.
- Startup only checked local token validity and did not initiate protected session restore.
- Periodic recheck required `is_activated()` and therefore stopped once the access token expired.
- Repeated `is_activated()` calls could repeat RSA public-key parsing and RS256 verification for the same access token.
- The supplied archive included private/runtime/cache data contrary to `.gitignore` and release-source policy.
- The plain pytest command in documentation did not match import behavior.
- Standard-library unittest discovery depended on an external `PYTHONPATH`, while the documented setup line used PowerShell-only syntax and failed when pasted into Windows Command Prompt.

## Corrected invariants

1. P-256 device key material is DPAPI-protected, persistent and saved before first activation I/O.
2. Logout/license switch clears license/session credentials but retains the same device key.
3. Ambiguous refresh credentials are invalidated and atomically persisted before recovery activation.
4. Long-running validation is serialized separately from short state reads; stale background results cannot overwrite a later local session change.
5. Startup uses the existing activation shell for protected v2/legacy restore without changing `ActivationPage`.
6. Periodic recheck enters validation whenever a protected/current license exists, including after access-token expiry.
7. Verified access-token state is cached only for the same token until verified expiry.
8. Cache writes flush/fsync before atomic replace.
9. Official release outputs exclude all forbidden runtime/private/cache paths.
10. Plain pytest imports the `src` package through `pyproject.toml`.
11. Test modules that import `vibrapilot` bootstrap the repository `src` directory themselves, so direct unittest discovery is shell-independent and requires no external `PYTHONPATH`.

## Frozen-scope verification

The original canonical AST hashes remain enforced for:

- `AutomationWorker`
- `SELECTORS`
- `TaskItem`
- `TaskState`
- `ActivationPage`
- `BROWSER_SETTING_GROUPS`

`config/verification/phase02_step002_v1.0.6.4_fix_scope.json` additionally records the exact uploaded baseline archive SHA-256 and byte-locks operational files outside `src/vibrapilot/backend.py` and `src/vibrapilot/qt_app.py`.

## Final automated verification

Forensic working tree with the private comparison baseline present:

```text
python -m compileall -q .                         PASS
python scripts/verify_repository.py               PASS
python -m pytest -q                               98 passed, 61 subtests passed
python -m unittest discover -s tests -p "test_*.py" -v   56 tests, OK
```

Clean public/release-source staging with private `project/` intentionally absent:

```text
python -m compileall -q .                         PASS
python scripts/verify_repository.py               PASS
python -m pytest -q                               97 passed, 1 skipped, 61 subtests passed
python -m unittest discover -s tests -p "test_*.py" -v   56 tests, OK, 1 skipped
```

The single clean-staging skip is the optional comparison against the private gitignored `project/` baseline. The source-controlled backend contract, original Phase-02 AST freeze and v1.0.6.4 file-scope contract remain active in public verification.

The source delta against the official v1.0.6.3 baseline contains **26 modified files, 4 added files and 0 deleted files** after excluding the baseline's runtime/private/cache paths. Runtime application source changes are limited to `src/vibrapilot/backend.py` and `src/vibrapilot/qt_app.py`; all other changed files are approved version metadata, verification/tests or synchronized documentation.

## Platform-specific limitation

The forensic environment is not the supported Windows 10/11 x64 + Python 3.12 + PySide6/PyInstaller runtime. Source compilation, repository verification and unit/protocol/crypto/scope tests can be proven here; a genuine Windows GUI startup, DPAPI round-trip with a real Windows account and PyInstaller Windows build must be executed on Windows before a binary release is promoted.
