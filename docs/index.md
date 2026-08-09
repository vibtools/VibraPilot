# VibraPilot Documentation

This documentation accompanies **VibraPilot v1.0.6.8 — VP-WORKFLOW-INPUTS-001**.

Start with:

- [Getting Started](getting-started/README.md)
- [AppConfig Architecture](configuration/APPCONFIG.md)
- [Licora Secure API v2 Integration](guides/LICENSING.md)
- [Public Backend / CI Verification Contract](verification/BACKEND_CONTRACT.md)
- [v1.0.6.8 Workflow Inputs](updates/v1.0.6.8-workflow-inputs-separation.md)
- [v1.0.6.8 Workflow Inputs Verification](verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md)
- [v1.0.6.7 Verification/Fix](updates/v1.0.6.7-vp-prod-mt-lr-verification-fix.md)
- [v1.0.6.7 Forensic Verification](verification/V1.0.6.7_VP_PROD_MT_LR_FORENSIC_VERIFICATION.md)
- [v1.0.6.5 Production Runtime Update](updates/v1.0.6.5-production-multi-task-long-run-stability.md)
- [v1.0.6.5 Production Runtime Verification](verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md)
- [v1.0.6.4 Phase-02-Step-002 Verification/Fix](updates/v1.0.6.4-phase-02-step-002-verification-fix.md)
- [v1.0.6.4 Forensic Verification](verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md)

The final v1.0.6.7 verification and Windows SQLite correction form the immediate baseline for the v1.0.6.8 Workflow Inputs separation. The v1.0.6.5 production-hardening records remain historical context. The v1.0.6.4 Phase-02 verification/fix remains the preceding licensing/session baseline, while the original v1.0.6.3 Phase-02 implementation note remains historical and is superseded by the later forensic records where they conflict. Historical Phase-01/v1.0.6.1 notes remain under `updates/` and `verification/`.

Private development records live under the local `project/` workspace. Runtime `AppData/`, `Logs/`, `Reports/` and `FailedData/` are private/gitignored and must not be included in release-source archives.
- Windows SQLite concurrency correction: `updates/v1.0.6.7-windows-sqlite-concurrency-fix.md`
- Windows SQLite concurrency verification: `verification/V1.0.6.7_WINDOWS_SQLITE_CONCURRENCY_VERIFICATION.md`
