# v1.0.6.19 Windows Evidence Addendum

The uploaded v1.0.6.18 baseline contains real Windows evidence under `Logs/BrowserDiagnostics/slot_1_latest.json`.

Confirmed runtime values:

- Google Chrome executable: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Chrome product/version: `Chrome/151.0.7922.76`
- Engine classification: `google_chrome`
- Fallback: `false`
- Managed profile: `C:\Users\Vib Tools\AppData\Local\Vib Tools\VibraPilot\BrowserProfiles\slot_1`
- Sandbox requested: `false`
- Effective process command line contains `--no-sandbox`
- Playwright Python runtime: `1.60.0`
- Project-required Playwright: `1.61.0`

This upgrades the Sandbox-OFF launch chain from source/dependency-only evidence to **runtime-confirmed process evidence**. Sandbox-ON compatibility is still NOT VERIFIED.

v1.0.6.19 does not change Sandbox policy. It hardens evidence redaction/fidelity and makes the Playwright runtime mismatch explicit.

# Browser Launch / Sandbox / Identity Forensic Audit — v1.0.6.18

Baseline: VibraPilot v1.0.6.17, SHA-256 `02d8d70a9c11365922121440edc0d6da8328ba3b9dcfb73fcc1f0885a05a38bf`.

## Confirmed baseline chain
`TaskSlotWidget.open_browser()` → `AutomationWorker.launch_browser()` → Playwright `launch_persistent_context()` → requested `channel="chrome"` → optional existing Chromium fallback.

Current source keeps `sandbox_enabled=false`; the worker passes it as `chromium_sandbox=False`. The Windows final process command line still requires runtime evidence.

## v1.0.6.18 evidence implementation
After a successful launch the worker writes `Logs/BrowserDiagnostics/slot_N_*.json` and `slot_N_latest.json`, plus a compact Live Logs line. Evidence includes requested/effective engine, fallback state/reason, Playwright version, managed profile, sandbox state, CDP product/version, CDP command line when exposed, Windows process executable/PID/command line when matched by profile, and non-invasive page environment values.

Diagnostics are non-fatal and observational. They do not change browser policy or fingerprints.

## Sandbox conditional
The approved `config/settings.defaults.json` Sandbox-ON change is **not applied** because real Windows Sandbox-ON acceptance cannot run here. Source default remains byte-frozen.

Root-cause status: application-side Sandbox-OFF chain CONFIRMED; exact user's Windows warning chain RUNTIME EVIDENCE REQUIRED.
