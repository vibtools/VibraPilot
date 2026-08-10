## v1.0.6.19 browser foundation verification/fix

The uploaded v1.0.6.18 baseline contains real Windows launch evidence confirming Google Chrome Stable, the managed profile and `--no-sandbox`, plus a Playwright runtime/version mismatch (`1.60.0` captured vs `1.61.0` required). v1.0.6.19 hardens diagnostics without changing browser policy.

See `updates/v1.0.6.19-browser-foundation-verification-fix.md`, `verification/V1.0.6.19_BROWSER_FOUNDATION_FORENSIC_VERIFICATION.md`, and the updated `forensic/` records.

## v1.0.6.18 browser foundation stabilization

See `updates/v1.0.6.18-browser-foundation-stabilization.md`, `verification/V1.0.6.18_BROWSER_FOUNDATION_VERIFICATION.md` and `forensic/`. Windows-only tests remain pending.

## v1.0.6.17 browser capabilities

The current candidate adds durable browser downloads, user-controlled website file chooser handling and unpacked extension manifest validation while preserving the managed browser, workspace, Closed Task, licensing and Razorpay/Test Mode contracts. See `updates/v1.0.6.17-browser-capabilities.md` and `verification/V1.0.6.17_BROWSER_CAPABILITIES_VERIFICATION.md`.

## v1.0.6.16 verification fix

The v1.0.6.15 workspace runtime is unchanged; v1.0.6.16 fixes the historical Qt fixture and records forensic CI verification.

## v1.0.6.15 workspace persistence

The current candidate restores normal active Task cards, selected page and safe window geometry from atomic workspace metadata while reusing the unchanged SQLite Task runtime data. Browser/login/workflow/Send remain closed until explicit user action. See `updates/v1.0.6.15-workspace-persistence.md` and `verification/V1.0.6.15_WORKSPACE_PERSISTENCE_VERIFICATION.md`.

# VibraPilot Documentation

This documentation accompanies **VibraPilot v1.0.6.19 — Browser Foundation verification/fix candidate**.

Start with:

- [Getting Started](getting-started/README.md)
- [v1.0.6.13 Phase-01 Verification/CI Fix](updates/v1.0.6.13-phase01-verification-ci-fix.md)
- [v1.0.6.13 Phase-01 Forensic Verification](verification/V1.0.6.13_PHASE01_FORENSIC_VERIFICATION.md)
- [AppConfig Architecture](configuration/APPCONFIG.md)
- [Licora Secure API v2 Integration](guides/LICENSING.md)
- [Public Backend / CI Verification Contract](verification/BACKEND_CONTRACT.md)
- [v1.0.6.12 Browser UI/Lifecycle Update](updates/v1.0.6.12-browser-ui-lifecycle.md)
- [v1.0.6.12 Browser UI/Lifecycle Verification](verification/V1.0.6.12_BROWSER_UI_LIFECYCLE_VERIFICATION.md)
- [v1.0.6.11 Qt Focus Lifecycle Fix](updates/v1.0.6.11-qt-focus-lifecycle-fix.md)
- [v1.0.6.11 Qt Focus Lifecycle Verification](verification/V1.0.6.11_QT_FOCUS_LIFECYCLE_VERIFICATION.md)
- [v1.0.6.10 License Login Durability/Recovery](updates/v1.0.6.10-license-login-durability-recovery-fix.md)
- [v1.0.6.10 License Login Forensic Verification](verification/V1.0.6.10_LICENSE_LOGIN_FORENSIC_VERIFICATION.md)
- [v1.0.6.9 Workflow Inputs Verification/Fix](updates/v1.0.6.9-workflow-inputs-verification-fix.md)
- [v1.0.6.9 Workflow Inputs Forensic Verification](verification/V1.0.6.9_WORKFLOW_INPUTS_FORENSIC_VERIFICATION.md)
- [v1.0.6.8 Workflow Inputs](updates/v1.0.6.8-workflow-inputs-separation.md)
- [v1.0.6.8 Workflow Inputs Verification](verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md)
- [v1.0.6.7 Verification/Fix](updates/v1.0.6.7-vp-prod-mt-lr-verification-fix.md)
- [v1.0.6.7 Forensic Verification](verification/V1.0.6.7_VP_PROD_MT_LR_FORENSIC_VERIFICATION.md)
- [v1.0.6.5 Production Runtime Update](updates/v1.0.6.5-production-multi-task-long-run-stability.md)
- [v1.0.6.5 Production Runtime Verification](verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md)
- [v1.0.6.4 Phase-02-Step-002 Verification/Fix](updates/v1.0.6.4-phase-02-step-002-verification-fix.md)
- [v1.0.6.4 Forensic Verification](verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md)

User-frozen v1.0.6.12 archive SHA-256 `becd6add21d377e98e458ce856c9c3baa710a113459bde0c737507c122c2a9b5` and GitHub v1.0.6.12 commit `a9cfec319285db2fb9fbff8d4bf0ede8ac87686b` are the Official Baseline Freeze for the v1.0.6.13 Phase-01 verification/CI correction. The v1.0.6.13 correction authorizes no production runtime source changes. User-frozen v1.0.6.11 archive SHA-256 `9ecb7cd66f24832c3555d219a6f8aaf47358877dd417eeb703b5a755964fc90a` and GitHub v1.0.6.11 commit `8670415b1df221ebeeb7d8f3fba4f991a91d43ec` are the Official Baseline Freeze for the v1.0.6.12 Browser UI/lifecycle phase. GitHub v1.0.6.10 commit `d712a9d04fa62e5e3a0df9c00a99c1315052bd05` remains the baseline history for the v1.0.6.11 Qt focus lifecycle fix. GitHub v1.0.6.9 commit `cd6ec96736626256daeed1d36775d21e90abf7ee` remains the baseline history for the v1.0.6.10 licensing forensic fix. GitHub v1.0.6.8 remains the baseline history for the v1.0.6.9 Workflow Inputs verification/fix. The final v1.0.6.7 verification and Windows SQLite correction remain the baseline history for the v1.0.6.8 Workflow Inputs separation. The v1.0.6.5 production-hardening records remain historical context. The v1.0.6.4 Phase-02 verification/fix remains the preceding licensing/session baseline, while the original v1.0.6.3 Phase-02 implementation note remains historical and is superseded by the later forensic records where they conflict. Historical Phase-01/v1.0.6.1 notes remain under `updates/` and `verification/`.

Private development records live under the local `project/` workspace. Runtime `AppData/`, `Logs/`, `Reports/` and `FailedData/` are private/gitignored and must not be included in release-source archives.
- Windows SQLite concurrency correction: `updates/v1.0.6.7-windows-sqlite-concurrency-fix.md`
- Windows SQLite concurrency verification: `verification/V1.0.6.7_WINDOWS_SQLITE_CONCURRENCY_VERIFICATION.md`
