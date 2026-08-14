# VibraPilot v1.0.6.32 Phase 2 — Replace-Ready Delta Manifest

## Classification

- Official functional baseline: `v1.0.6.31`
- Baseline Git commit: `fc9081b0f760ac6b380b8c574680fc2c15764be0`
- Target version: `1.0.6.32`
- Branch: `feature/v1.0.6.32-chrome-prerequisite-install`
- Update: `Phase 2 — Chrome Prerequisite UX + Secure Install`
- Implementation: `IMPLEMENTED / AUTOMATED VERIFIED`
- Owner Windows missing-Chrome/install/UAC acceptance: `PENDING`
- Build/package work: `NOT PERFORMED / DEFERRED`

## Functional changes

- Re-checks for genuine installed Google Chrome at app startup, before every new Open Browser request and again in the backend before Playwright startup.
- Adds one process-owned **Google Chrome Required** dialog with explicit Download & Install, Re-check and Not Now actions.
- Performs no download or install without the user's explicit Download & Install action.
- Downloads the code-owned Stable x64 Enterprise MSI from `https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi` with HTTPS/host/path enforcement.
- Uses atomic `.part` download promotion and records SHA-256 evidence.
- Requires Windows WinVerifyTrust Authenticode trust and signer publisher `Google LLC` before installer execution.
- Elevates only Windows Installer via `runas`; distinguishes UAC cancellation/elevation/installer failures.
- Requires post-install genuine Google Chrome path/product/version re-detection before browser automation becomes available.
- Prevents concurrent duplicate prerequisite installers and blocks app/dialog close while an elevated install is active.
- Preserves v1.0.6.31 Chrome-only launch, `fallback=no`, sandbox mandatory ON, normal HTTP cache defaults and managed `BrowserProfiles/slot_N` profiles.

## Preserved / frozen

- Playwright automation and all workflow/Share Invite behavior.
- Licensing/device identity.
- TaskRuntimeStore, workspace and report schemas.
- Browser diagnostics schema.
- `config/settings.defaults.json` (no new user-editable installer/security switches).
- `requirements.txt`, `requirements-build.txt` (no dependency change).
- `.github/workflows/ci.yml`.
- `build.py`, Nuitka/WiX/installer/package surfaces.

## Automated evidence

```text
compileall: PASS
Phase-02 targeted + Phase-01 regression: PASS
Repository verification: PASS
Full pytest: 431 passed, 6 skipped, 113 subtests passed
Unittest: 200 OK, 6 skipped
Phase-02 source diagnostic: PASS
Frozen-surface SHA verification: PASS
Windows secure install/UAC runtime acceptance: OWNER PENDING
```

## Delta safety

- File deletions: `0`
- Runtime `AppData`: excluded
- Logs/Reports/FailedData: excluded
- `.git`: excluded
- caches/`__pycache__`/`.pyc`: excluded
- build artifacts: excluded
- `project/` is private/local-only, remains gitignored and must never be force-added or pushed.

## Apply

Extract the ZIP at the v1.0.6.31 project root and choose **Replace All**. Run the provided verification/Windows acceptance sequence before commit/push.
