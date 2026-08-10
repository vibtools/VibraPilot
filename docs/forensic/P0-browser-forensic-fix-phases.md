# P0 Browser Forensic Fix Phases

1. **Chrome Launch & Sandbox Stabilization** — v1.0.6.18 diagnostics implemented; Windows Sandbox-ON gate pending.
2. **Chrome Identity & Fallback Control** — identity observability implemented; final product policy depends on Windows evidence.
3. **CAPTCHA Root-Cause Resolution** — NOT VERIFIED; controlled comparison only.
4. **Browser Runtime Capability Stabilization** — validate first; fix only reproduced failures.
5. **Profile & Persistence Stabilization** — validate cookies/localStorage/IndexedDB/history; runtime-data relocation remains separate scope.
6. **Browser Lifecycle & UI State Synchronization** — stress validation first.
7. **Multi-Task Browser Isolation** — 1/2/4 Task validation.
8. **Regression & Production Validation** — Windows + CI + exact delta gate before baseline freeze.
