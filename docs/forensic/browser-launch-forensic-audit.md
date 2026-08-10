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
