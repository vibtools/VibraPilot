# Update Log

## VibraPilot branding baseline — 2026-08-08

Brand-only transition on top of the validated **v1.0.6.1** runtime. Product/package/build names, documentation and visible application branding now use **VibraPilot**. Existing workflow and backend behavior remain unchanged. Existing site-specific implementation details are retained only for the current built-in workflow.

Detailed note: `docs/updates/v1.0.6.1-vibrapilot-branding.md`

## v1.0.6.1 — 2026-08-07

Browser Settings production-hardening release. The advanced Browser Settings page was audited end to end, read-only/non-setting UI cards were removed, Playwright-default-argument conflicts for popup blocking/background throttling/extensions/headless audio were corrected, persistent Chrome fallback and full-Chromium extension launch selection were completed, the removed Playwright 1.61 `devtools` launch keyword was replaced with Chromium's real DevTools switch, duplicate/hidden browser aliases were migrated away, and saved controls now refresh from backend-persisted values.

Full technical note: `docs/updates/v1.0.6.1.md`

A–Z Browser Settings binding audit: `docs/updates/v1.0.6.1-browser-settings-audit.md`
