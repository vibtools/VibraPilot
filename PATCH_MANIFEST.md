# VibraPilot v1.0.6.35 — Workflow-Scoped Test Safety Isolation Delta

## Classification

- Frozen source baseline: `VibraPilot_v1.0.6.34_BASELINE.zip`
- Baseline Git commit: `a0e3621e831d402649ab55859e00b59d5f0ad634`
- Baseline ZIP SHA-256: `91566da389aa05ea65e08a60d6ae56321d23dbf88fa26f87b22542e7cc0d3a70`
- Target version: `1.0.6.35`
- Recommended branch: `fix/v1.0.6.35-workflow-scoped-test-safety`
- Release classification: Workflow-Scoped Test Safety Isolation

## Confirmed root cause

The legacy single-workflow Razorpay/Test Mode safety controls remained global after VibraPilot became a multi-workflow host. `TaskSlotWidget.start()` therefore blocked unrelated workflows when the legacy `authorized_testing_only` setting was false.

## Production changes

- `src/vibrapilot/qt_app.py` — removes the global authorization gate/Test Safety card, migrates the legacy send limit once, and resolves workflow-owned limits.
  It also preserves historical/lightweight Qt host compatibility when `workflow_test_send_limit()` is not present on a test host object.
- `src/vibrapilot/backend.py` — consumes immutable workflow settings for Test Send limits and uses workflow-neutral Core session wording.
- `src/vibrapilot/workflow/manager.py` — registers Share Invite Workflow Settings.
- `src/vibrapilot/workflow/schemas.py` — defines `max_test_send_limit` as a Share Invite integer setting.

The Share Invite runtime implementation itself is byte-frozen, including live Test Mode banner verification and the pre-Send Test Mode assertion.

## Compatibility

The legacy `authorized_testing_only` and `max_test_send_limit` App settings keys remain readable so existing settings files do not break. The authorization key is inert for Task Start; the old send-limit value is only a one-time migration source when Share Invite has no namespaced value yet.

## Automated verification

- Frozen v1.0.6.34 baseline verifier: PASS
- Frozen v1.0.6.34 pytest: 454 passed, 6 skipped, 107 subtests
- v1.0.6.35 targeted contract: 9 passed
- v1.0.6.35 full pytest: 463 passed, 6 skipped, 106 subtests
- Repository verifier: PASS
- stdlib unittest: 200 OK, 6 skipped
- compileall: PASS
- v1.0.6.35 source-policy diagnostic: PASS

## Delta safety

- File deletions: 0
- Private `project/`: excluded
- AppData/Logs/Reports/FailedData: excluded
- caches/pyc/.git/build artifacts: excluded
