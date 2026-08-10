# VibraPilot Documentation — v1.0.6.25 PR-08 Candidate

Current release baseline: **v1.0.6.24 / PR-07 — RELEASE COMPLETE**. Current development candidate: **v1.0.6.25 / PR-08 Dynamic Workflow Inputs + per-workflow persistence**.

PR-08 introduces source-controlled declarative input schemas and canonical atomic per-workflow persistence while preserving Share Invite compatibility mirrors and all PR-06/PR-07 workflow behavior. Production remains `share_invite` only; PR-09 workflow-aware Task/data/report compatibility remains not started.

Candidate documents:
- `updates/v1.0.6.25-pr08-dynamic-workflow-inputs.md`
- `verification/V1.0.6.25_PR08_DYNAMIC_WORKFLOW_INPUTS.md`

# VibraPilot Documentation

## Current release

- Official Release Baseline: **VibraPilot v1.0.6.23 — PR-06 Workflow State Persistence + Atomic Switch/Restart**.
- Previous release: **v1.0.6.22 — PR-05 Master Workflow Gate**.

### PR-06 documentation

v1.0.6.23 persists one active built-in workflow and adds fail-closed atomic switch/restart infrastructure. Production still contains only `share_invite`; PR-07 owns Workflow Showcase UI and PR-08 owns dynamic per-workflow inputs.

See:

- `updates/v1.0.6.23-pr06-workflow-state-atomic-switch.md`
- `verification/V1.0.6.23_PR06_WORKFLOW_STATE_ATOMIC_SWITCH.md`

### PR-05 historical release

PR-05 remains the historical v1.0.6.22 Master Workflow Gate release. Its version-specific update and verification documents remain immutable historical evidence.

## Browser automation status

Browser capabilities are substantially implemented, including managed profiles, lifecycle synchronization, durable downloads, explicit file chooser uploads, unpacked extension validation and diagnostics. Full target-Windows technical acceptance remains incomplete for the documented remaining persistence/Sandbox/crash/multi-Task matrices. CAPTCHA causality remains deferred/unverified.

## Historical documentation

Older version-specific update and verification files remain historical evidence. They may describe the state at the time they were written and are not the authoritative current project ledger.

Private current development/governance records live under `project/`; they are not runtime dependencies and must not be included in clean public release artifacts.
