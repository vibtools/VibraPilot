## PR-05 Master Workflow Gate — v1.0.6.22

PR-05 routes workflow-specific session, item execution and retry preparation through a validated in-memory active built-in workflow. The initial/current active workflow is `share_invite`, and invalid resolution fails closed without fallback.

**Next after PR-05 release verification:** PR-06 Workflow State Persistence + Atomic Switch / Restart. PR-05 intentionally does not persist or switch workflows and adds no Workflow UI.

## PR-04 CI closure — v1.0.6.21

PR-04 implementation remains behaviorally frozen from v1.0.6.20. v1.0.6.21 addresses only the Windows/Python 3.12 parity-test portability failure from Actions run `31379910982`. PR-05 remains blocked until the v1.0.6.21 GitHub CI gate is green and PR-04 is formally closed.

## PR-04 Share Invite workflow extraction — v1.0.6.20

PR-04 converts the existing verified Share Invite automation into VibraPilot's first source-controlled built-in workflow. The extraction preserves Test Mode, selector order, Send/retry/manual-review semantics, `SecurityChallenge`, existing exceptions and report/data contracts.

**Next after PR-04 release verification:** PR-05 Master Workflow Gate Integration. PR-04 intentionally does not add switching, active-workflow persistence, Workflow UI or dynamic Workflow Inputs.

## Browser Foundation verification/fix — v1.0.6.19

v1.0.6.18 Windows evidence now confirms actual Google Chrome Stable, managed profile identity and the Sandbox-OFF `--no-sandbox` process command line. v1.0.6.19 hardens evidence correctness and surfaces the detected Playwright `1.60.0` vs required `1.61.0` runtime mismatch.

Remaining browser-foundation gates: reinstall/verify exact Playwright `1.61.0`, run Sandbox-ON acceptance, controlled normal-Chrome vs VibraPilot CAPTCHA comparison, real download/upload/unpacked-extension tests, cookie/localStorage/IndexedDB/history persistence, manual-close/process-kill lifecycle, and 1/2/4 Task isolation. Master Workflow Engine work remains blocked until those foundation gates are explicitly accepted.

## Phase-1 Browser Foundation Stabilization — v1.0.6.18 Candidate

Identity/fallback/sandbox evidence is implemented. Windows Sandbox/CAPTCHA/capability/lifecycle/multi-Task acceptance remains required before Master Workflow Engine work.

## Phase-04 implementation candidate — v1.0.6.17

`VP-BROWSER-CAPABILITIES-001` is implemented from the verified v1.0.6.16 baseline. The scope is limited to durable downloads, explicit site-triggered file chooser handling, and unpacked-extension validation. It does not add workflow-defined uploads, download history/database UI, Chrome Web Store automation, stealth/CAPTCHA behavior, or settings/schema changes.

**Next after v1.0.6.17 verification:** `VP-MASTER-WORKFLOW-ENGINE-001`.

## Phase-03 verification/fix — v1.0.6.16

`VP-WORKSPACE-PERSISTENCE-001` runtime remains byte-frozen from v1.0.6.15. GitHub Actions job `93315001000` failed because the historical v1.0.6.12 Qt fixture lacked `schedule_workspace_save`. v1.0.6.16 corrects verification only.

**Next after v1.0.6.16 verified:** `VP-BROWSER-CAPABILITIES-001`.

## Phase-03 implementation candidate — v1.0.6.15

v1.0.6.14 `VP-MANAGED-PERSISTENT-BROWSER-001` plus `VP-CLOSED-TASK-RECOVERY-001` is treated as the verified baseline after the supplied Windows/manual gate and green GitHub Actions run `31337925846`.

The v1.0.6.15 candidate implements the remaining `VP-WORKSPACE-PERSISTENCE-001` scope: automatic restoration of normal active Task cards, stable slot/order/Target URL references, existing SQLite-backed Task data/progress, selected application page and safe workspace geometry. Browsers, login, workflows and Send remain explicit user actions. Deliberately Closed Tasks remain closed and continue to use **Open Closed Tasks**.

**Next after v1.0.6.15 verification:** `VP-BROWSER-CAPABILITIES-001`.

## Phase-02 implementation candidate — v1.0.6.14

Phase-01 `VP-BROWSER-UI-LIFECYCLE-001` is **VERIFIED** by the supplied Windows/manual browser lifecycle gate and green GitHub Actions run for v1.0.6.13.

The current v1.0.6.14 candidate implements `VP-MANAGED-PERSISTENT-BROWSER-001` plus the approved amendment `VP-CLOSED-TASK-RECOVERY-001`: durable app-managed persistent browser profiles, stable Task-slot profile ownership/isolation, personal Chrome profile rejection, safe legacy VibraPilot profile migration, persistent-recycle lifecycle compatibility, and deliberate Closed Task archive/reopen without a database schema change.

**Next after v1.0.6.14 verification:** continue the remaining `VP-WORKSPACE-PERSISTENCE-001` scope for normal active-workspace restoration. Closed Task recovery is already completed as an approved subset and must not be reimplemented.

# VibraPilot Roadmap

## Phase-01 verification correction candidate — v1.0.6.13

GitHub Actions verified the v1.0.6.12 Phase-01 browser lifecycle implementation through repository verification and the complete pytest suite. The remaining CI failure was not a Phase-01 runtime regression: the duplicate unittest pass exceeded a test-only 15-second SQLite concurrency threshold on hosted Windows storage.

v1.0.6.13 freezes the Phase-01 runtime byte-for-byte and corrects only that verification harness. Phase-01 remains in **VERIFICATION** until the v1.0.6.13 Windows live browser lifecycle/geometry gate and the new GitHub Actions run are green.

**Next after Phase-01 VERIFIED:** `VP-MANAGED-PERSISTENT-BROWSER-001`.

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
