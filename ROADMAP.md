# VibraPilot Roadmap

## Phase-01 implementation candidate — v1.0.6.12

`VP-BROWSER-UI-LIFECYCLE-001` is implemented at source level: manual page/context/browser close now converges to truthful Task browser state, the primary browser action transitions between Open/Close states, browser-only close preserves Task/data, Login and Dashboard readiness synchronize with lifecycle state, and the first workspace is centered/clamped after activation. Windows live browser-close/geometry acceptance remains required before this phase is marked VERIFIED.

**Next after verification:** Phase-02 `VP-MANAGED-PERSISTENT-BROWSER-001`. Persistent-profile defaults and managed profile architecture remain unchanged in Phase-01.

## Verified Qt lifecycle milestone — v1.0.6.11

The shared keyboard-focus manager is hardened against deleted PySide6 wrappers and delayed-tooltip lifetime races without changing the frozen visual focus contract. Windows live runtime verification remains the final platform gate before treating this correction as production-accepted.

## Verified licensing milestone — v1.0.6.10

License-login state is durable across clean Windows application/source folders, P-256 device identity survives session-cache loss, current Licora `DEVICE_KEY_MISMATCH`/`DEVICE_REVOKED` states have bounded recovery, and logout/recheck behavior is aligned with production server semantics.

## Verified Workflow Inputs baseline — v1.0.6.9

Forensic verification of `VP-WORKFLOW-INPUTS-001` against GitHub v1.0.6.8. The page separation, keys, values, `default_target_url` ownership and frozen backend/browser/API-v2 boundaries remain intact. Save/Reset persistence failures are now contained and rolled back at the Workflow Inputs page boundary.

## Completed UI ownership milestone — v1.0.6.8

`VP-WORKFLOW-INPUTS-001`: moved the four existing workflow/form settings into a dedicated Workflow Inputs page while preserving keys, saved values and backend behavior. No fake workflow selector was added; `default_target_url` remains in App Settings.

## Verified production baseline — v1.0.6.7

Forensic verification/fix of the completed `VP-PROD-MT-LR-001` milestone. Corrected the startup stylesheet descriptor, bounded-queue shutdown liveness, pre-Send crash-result-ledger durability and source-baseline packaging verification without changing the approved automation workflow, licensing protocol, Browser Settings or design foundation.

## Completed production milestone — v1.0.6.5

`VP-PROD-MT-LR-001`: Multiple Task + Long-Run Worker Stability + Data Integrity / Recovery.

Implemented scope: per-task runtime persistence/recovery, input reconciliation, functional sequential batch boundaries, seconds-based autosave, context-recycle correction, deterministic worker shutdown, bounded UI event processing, scalable authoritative reporting, Task report filtering, concurrent-worker guard, shared persistent-profile collision guard and clean release-package enforcement.

Out-of-scope behavior remains frozen, including Licora API v2, Razorpay Share Invite selectors/Send sequence, Test Mode/security controls, ActivationPage, Browser Settings contract and visual design foundation.
