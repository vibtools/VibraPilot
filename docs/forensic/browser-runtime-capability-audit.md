# v1.0.6.19 Evidence Addendum

The uploaded v1.0.6.18 baseline proves one real Windows browser launch, not the complete capability matrix.

Runtime-confirmed for the captured launch:

- actual Google Chrome process detected;
- managed persistent profile path detected;
- no fallback in that launch;
- effective `--no-sandbox` process flag detected.

Still not evidenced by the uploaded baseline:

- Sandbox-ON;
- manual-close/process-kill lifecycle;
- cookies/session/LocalStorage/IndexedDB/history persistence;
- real download;
- real upload/file chooser;
- unpacked extension runtime/persistence;
- 2–4 simultaneous Task isolation.

These remain RUNTIME EVIDENCE REQUIRED and must not be treated as PASS.

# Browser Runtime Capability Audit — v1.0.6.18

Existing v1.0.6.17 browser lifecycle, managed profile, download, upload/filechooser, unpacked-extension, workspace and Closed Task implementations are preserved. This phase adds evidence only.

Real Windows tests remain **RUNTIME TEST BLOCKED** in the current environment: Open/Close, manual close, forced process termination, session/cookie/localStorage/IndexedDB/history persistence, download, upload, unpacked extension and 1/2/4 Task isolation. Blocked tests are not PASS.

On Windows, retain Live Logs plus `Logs/BrowserDiagnostics/slot_N_latest.json` for every test. Reproduce a failure before changing validation-only behavior.
