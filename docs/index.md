# VibraPilot Documentation — v1.0.6.24 PR-07 Candidate

Current release baseline: **v1.0.6.23 / PR-06**. Current development candidate: **v1.0.6.24 / PR-07 Workflow Showcase Page**.

PR-07 exposes source-controlled built-in workflow metadata through a Workflows page and delegates activation to the existing PR-06 atomic switch service. Production still contains only `share_invite`; PR-08 dynamic Workflow Inputs remain not started.

Candidate documents:
- `updates/v1.0.6.24-pr07-workflow-showcase.md`
- `verification/V1.0.6.24_PR07_WORKFLOW_SHOWCASE.md`

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
