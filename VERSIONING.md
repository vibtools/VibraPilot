# Versioning

VibraPilot uses a four-segment production release version for hardening/configuration maintenance on top of the validated v1.0.6 automation baseline.

Current release: **1.0.6.2**

The **2026-08-08 VibraPilot branding baseline** and initial Phase-01 AppConfig centralization were delivered on v1.0.6.1 without changing browser-automation behavior. The subsequent Phase-01 forensic verification found repository contamination and configuration-completeness/validation defects. The user explicitly approved promotion of the corrected, fully verified configuration baseline to **v1.0.6.2**.

v1.0.6.2 changes only Phase-01 configuration ownership/content validation, repository hygiene required by the existing branding contract, synchronized metadata and documentation. It does **not** change the validated `AutomationWorker`, `LicenseManager`, selectors, Browser Settings, task/report/safety/retry/persistence behavior or Licora v1 protocol. Licora API v2 remains a separately approved Phase-02 feature.

## Release documentation policy

Every production update must include:

1. the runtime/package version update when a release version changes,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise cumulative note in `UPDATE_LOG.md`,
4. a detailed per-update Markdown note under `docs/updates/`,
5. README changes when user-visible identity, behavior, configuration or operational requirements change, and
6. verification/test updates that describe the new invariant.

The preserved source under `project/research/source_baseline/` remains the forensic comparison baseline. Private development records remain under gitignored `project/`; public documentation remains under `docs/`.
