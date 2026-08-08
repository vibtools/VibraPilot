# Versioning

VibraPilot uses a four-segment production release version when a hardening patch is issued without changing the validated v1.0.6 automation baseline.

Current release: **1.0.6.1**

The **2026-08-08 VibraPilot branding baseline** does not increment the runtime version because it is intentionally limited to product identity, documentation, package/build naming and icon/logo integration. Runtime workflow behavior remains the validated v1.0.6.1 contract.

## Release documentation policy

Every production update must include:

1. the runtime/package version update when runtime behavior changes,
2. a cumulative entry in `CHANGELOG.md`,
3. a concise cumulative note in `UPDATE_LOG.md`,
4. a detailed per-update Markdown note under `docs/updates/`,
5. README changes when user-visible identity, behavior, configuration or operational requirements change, and
6. verification/test updates that describe the new invariant.

The preserved source under `project/research/source_baseline/` remains the forensic comparison baseline. Branding-only metadata may be normalized to the VibraPilot identity, while class/method inventory remains the comparison contract.
