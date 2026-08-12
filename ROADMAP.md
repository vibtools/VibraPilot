# VibraPilot Roadmap — v1.0.6.30 Workflow Plugin System

- Official implementation baseline: **v1.0.6.28 / PR-11 — RELEASE COMPLETE**, commit `fff8160157d4d9b68b2d28b11105b0f7f38ed17d`.
- Current functional target: **v1.0.6.30 / Trusted Workflow Plugin System**.
- Preserve one active workflow at a time; existing atomic switch/restart/recovery remains authoritative.
- Add trusted local `.vpworkflow` loading, unified catalog, Workflow Inputs/Settings selectors, Task Settings schemas and workflow step/metrics.
- Keep Core Task/Browser/retry/persistence/report/log/licensing behavior authoritative.
- Deferred: per-Task mixed workflows, JSON automation interpreter, marketplace, sandbox, automatic dependencies, remote plugin updates and arbitrary plugin UI code.

# VibraPilot Roadmap — PR-11 Candidate

- Current release baseline: **v1.0.6.27 / PR-10 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.28 / PR-11 E2E Windows / Multi-Task Regression**.
- PR-11 scope: target-Windows evidence and 1/2/4-Task regression only; production runtime/source changes are zero unless a separately approved defect amendment is issued.
- PR-12 Packaging: **NOT STARTED**.
- Future CL Automation / Nuitka OneDir / WiX MSI requirement remains recorded for PR-12 only; no packaging implementation is authorized in PR-11.

# VibraPilot Roadmap — PR-10 Candidate

- Current release baseline: **v1.0.6.26 / PR-09 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.27 / PR-10 Workflow Error Handling / Recovery**.
- PR-10 scope: explicit control-plane recovery, recovery transaction safety and active-runtime preflight only.
- PR-11 E2E Windows / Multi-Task Regression: **NOT STARTED**.
- Future CL Automation / Nuitka OneDir / WiX MSI requirement remains recorded for packaging only; no packaging implementation is authorized in PR-10.

# VibraPilot Roadmap — PR-09 Candidate

- Current release baseline: **v1.0.6.25 / PR-08 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.26 / PR-09 Workflow Data/Persistence/Reporting Compatibility**.
- PR-09 is verification-only at production-runtime level: no database migration, no workflow_id columns, no Task/report/workspace schema redesign.
- PR-10 Workflow Error Handling / Recovery: **NOT STARTED**.

- Current release baseline: **v1.0.6.24 / PR-07 — RELEASE COMPLETE**.
- Current development candidate: **v1.0.6.25 / PR-08 Dynamic Workflow Inputs + per-workflow persistence**.
- PR-08 scope: source-controlled input schemas, dynamic active-workflow renderer, canonical per-workflow persistence, legacy Share Invite migration/mirror, and immutable worker input snapshots.
- Production registry remains `share_invite` only.
- PR-09 workflow-aware Task/data/report compatibility: **NOT STARTED**.

# VibraPilot Roadmap — Current View

## Current identities

- Official release: **v1.0.6.23 / PR-06 Workflow State + Atomic Switch/Restart**.
- Previous release: **v1.0.6.22 / PR-05 Master Workflow Gate**.
- Final planned production line: **v1.0.7.0**.

## Current progression

| Phase | Status |
|---|---|
| Browser Foundation development gate | CLOSED by owner; technical Windows acceptance still open |
| CAPTCHA decision | DEFERRED / unverified |
| Workflow contracts/registry | complete |
| Share Invite extraction/parity | release complete |
| Master Workflow Gate | release complete v1.0.6.22 |
| Workflow State + Atomic Switch/Restart | **release complete v1.0.6.23** |
| Workflow Showcase UI | not started |
| Dynamic per-workflow inputs | not started |
| Workflow-aware data/reporting | not started |
| Error/recovery hardening | not started |
| Windows E2E / multi-Task final acceptance | not started |
| Packaging / final CI / v1.0.7.0 freeze | not started |

## Browser technical acceptance track

Source implementation is substantial, but the remaining target-Windows download/upload/extension persistence, Sandbox policy, web-storage/history persistence, manual-close/crash/process-kill and real 1/2/4 Task acceptance must still be closed or explicitly accepted before final production approval.

## Next phase rule

PR-07 Workflow Showcase UI does not start automatically. It requires a fresh forensic plan, scope lock and explicit owner approval after PR-06 release closure.
