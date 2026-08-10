# v1.0.6.19 Verification Addendum

The v1.0.6.18 baseline now contributes actual Windows launch evidence. The `--no-sandbox` chain is runtime-confirmed for Sandbox-OFF, Google Chrome Stable identity is confirmed for the captured run, and Chromium fallback was not used.

A new confirmed environment issue is present: the captured Windows runtime used Playwright `1.60.0` while the source project requires `1.61.0`. v1.0.6.19 surfaces this mismatch and hardens evidence handling; it does not modify launch policy.

CAPTCHA causality and the remaining Windows browser capability/lifecycle matrix remain unverified.

# P0 Browser Forensic Audit Summary — v1.0.6.18

v1.0.6.18 implements the P0 browser evidence foundation. Confirmed architecture facts: Sandbox is disabled in current config and passed to Playwright; Chrome launch can fall back to Chromium. CAPTCHA has no confirmed causal root cause. Existing capability/lifecycle code is preserved pending real Windows reproduction.

The candidate makes engine/fallback/sandbox/profile/browser-environment evidence observable without claiming blocked Windows tests pass.
