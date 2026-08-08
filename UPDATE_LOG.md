# Update Log

## v1.0.6.2 — Phase-01 forensic verification and completion — 2026-08-08

Phase-01 verification/fix scope only. Removed stale pre-rebrand active paths that broke the repository contract, completed confirmed About/support/social configuration, strengthened AppConfig validation, synchronized release metadata and promoted the verified baseline to **1.0.6.2**. Automation, licensing, browser/task and UI-design behavior remain unchanged.

Detailed note: `docs/updates/v1.0.6.2-phase-01-verification-fix.md`

## v1.0.6.1 — Phase-01 AppConfig centralization — 2026-08-08

Configuration-architecture update only. Application identity, About/company content, confirmed public support/documentation links and social/community metadata now live under `config/AppConfig/` and are exposed through a validated runtime facade. Backend compatibility constants and build/package identity consume that source, while verifier/tests prevent static metadata drift. Licensing transport/API credentials and all automation/runtime behavior remain unchanged and are reserved for Phase-02.

Detailed note: `docs/updates/v1.0.6.1-phase-01-appconfig.md`

## v1.0.6.1 — GitHub CI deterministic backend-contract fix — 2026-08-08

CI/repository-verification maintenance only. Backend implementation parity hashes now use a canonical semantic AST representation instead of Python-version-dependent raw `ast.dump()` text. This prevents Python 3.12 GitHub runners from reporting false `TaskItem` implementation drift when the backend source is unchanged. The CI workflow also uses Node 24-native `actions/checkout@v5` and `actions/setup-python@v6`. Runtime application behavior is unchanged.

Detailed note: `docs/updates/v1.0.6.1-github-ci-deterministic-ast-contract-fix.md`

## v1.0.6.1 — GitHub CI repository hygiene fix — 2026-08-08

CI/repository-only maintenance. Public verification no longer depends on the private gitignored `project/` workspace. A machine-readable backend parity contract now lives under `config/verification/`, public documentation/CI guidance lives under `docs/`, Node 24-native GitHub Actions replace the deprecated Node 20 actions, and stale pre-rebrand tracked source paths are removed from the clean repository state. Runtime application behavior is unchanged.

Detailed note: `docs/updates/v1.0.6.1-github-ci-repository-hygiene-fix.md`

## v1.0.6.1 — GitHub Actions verification portability fix — 2026-08-08

CI-only maintenance update. The repository verifier now canonicalizes CRLF to LF when hashing frozen text design-contract files, preventing Windows Actions checkout from producing false design-drift failures. `.gitattributes` now pins source/config/documentation text to LF while preserving binary files as binary. The Windows CI job also exports the repository `src` directory through `PYTHONPATH`, so contract tests can import `vibrapilot` without an install step. Runtime application behavior is unchanged.

Detailed note: `docs/updates/v1.0.6.1-github-actions-line-ending-fix.md`

## VibraPilot branding baseline — 2026-08-08

Brand-only transition on top of the validated **v1.0.6.1** runtime. Product/package/build names, documentation and visible application branding now use **VibraPilot**. Existing workflow and backend behavior remain unchanged. Existing site-specific implementation details are retained only for the current built-in workflow.

Detailed note: `docs/updates/v1.0.6.1-vibrapilot-branding.md`

## v1.0.6.1 — 2026-08-07

Browser Settings production-hardening release. The advanced Browser Settings page was audited end to end, read-only/non-setting UI cards were removed, Playwright-default-argument conflicts for popup blocking/background throttling/extensions/headless audio were corrected, persistent Chrome fallback and full-Chromium extension launch selection were completed, the removed Playwright 1.61 `devtools` launch keyword was replaced with Chromium's real DevTools switch, duplicate/hidden browser aliases were migrated away, and saved controls now refresh from backend-persisted values.

Full technical note: `docs/updates/v1.0.6.1.md`

A–Z Browser Settings binding audit: `docs/updates/v1.0.6.1-browser-settings-audit.md`
