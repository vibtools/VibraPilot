# VibraPilot v1.0.6.33 — Phase-01 + Phase-02 Browser Forensic Closure Delta

## Classification

- Frozen source baseline: `VibraPilot_v1.0.6.32_BASELINE.zip`
- Baseline SHA-256: `fdc18905084f41f9418d239f5e8f0ab632fa114c05b065835dcc126d32a1664f`
- Baseline Git commit: `a001f67972c47832a5e59af5f9350a0409e7eab6`
- Target version: `1.0.6.33`
- Recommended branch: `hotfix/v1.0.6.33-browser-forensic-closure`
- Update: Phase-01 + Phase-02 A–Z forensic confirmed-defect closure
- Build/package: `NOT PERFORMED / DEFERRED`

## Confirmed closures

- Bind Chrome preflight to Playwright 1.61.0's actual Windows Chrome-channel target order.
- Require Windows Authenticode trust and `Google LLC` publisher identity for installed `chrome.exe`.
- Require the exact approved Google Enterprise MSI HTTPS path.
- Treat Windows Installer exit 1602 as user cancellation.
- Make installer security/lifecycle stage events non-droppable while retaining droppable byte-progress updates.
- Preserve active installer dialog/coordinator state across concurrent Open Browser/Re-check requests.
- Require measured process executable equality with the trusted Chrome target for diagnostic compliance.
- Synchronize current-state documentation and remove the v1.0.6.32 Chrome runtime EOF hygiene defect.

## Preserved/frozen

- Playwright `channel="chrome"`; no Chromium fallback/custom browser executable.
- Mandatory sandbox and HTTP cache defaults.
- Managed `BrowserProfiles/slot_N` behavior.
- Workflows/Share Invite, licensing, TaskRuntimeStore/workspace/report schemas.
- `config/settings.defaults.json`, `requirements.txt`, `requirements-build.txt`, `.github/workflows/ci.yml`, `build.py`.
- No CAPTCHA bypass, stealth or fingerprint spoofing.

## Automated evidence

```text
Uploaded baseline SHA/hygiene: PASS
Untouched baseline verifier: PASS
Untouched baseline pytest: 431 passed, 6 skipped, 113 subtests
Untouched baseline unittest: 200 OK, 6 skipped
Targeted Phase-01/02 + forensic closure: PASS
Repository verification: PASS
Full pytest: 442 passed, 6 skipped, 113 subtests
Full unittest: 200 OK, 6 skipped
compileall: PASS
v1.0.6.33 source diagnostic: PASS (Windows acceptance not run in audit environment)
```

## Owner Windows gate

Before Git publication, confirm trusted installed Chrome signer/publisher evidence and normal Open → Close → Open behavior. The full missing-Chrome download/UAC/install path remains an owner Windows acceptance gate and must not be represented as live-PASS until actually exercised on a safe Windows environment.

## Delta safety

- File deletions: `0`
- Private `project/`: absent from frozen baseline and absent from this public delta
- Runtime AppData/Logs/Reports/FailedData: excluded
- caches/pyc/.git/build artifacts: excluded
