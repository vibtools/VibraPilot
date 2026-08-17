# VibraPilot v1.0.6.36 — Share Invite Workflow Externalization Delta

## Classification

- Frozen source baseline: `VibraPilot_v1.0.6.35_BASELINE.zip`
- Baseline Git commit: `c5511a82ddf164bfacdfad5aa12ebf75ad56a1da`
- Baseline ZIP SHA-256: `c5be0d2221ee580360c32066a29462cba75eb330b8e408bb9dcea780e6d9f229`
- Target version: `1.0.6.36`
- Recommended branch: `feature/v1.0.6.36-share-invite-externalization`
- Release classification: Share Invite Workflow Externalization Only

## Locked outcome

VibraPilot Core has zero source-controlled built-in workflows. A fresh application may remain in a valid zero-active-workflow state. Share Invite is distributed separately as `Share_Invite_v1.0.vpworkflow` with the same `share_invite` identity and frozen v1.0.6.35 automation/safety semantics.

## Production changes

- `src/vibrapilot/workflow/registry.py` — empty built-in manifest/runtime registry.
- `src/vibrapilot/workflow/manager.py` — plugin-only catalog plus backward-compatible optional rich task-data hook.
- `src/vibrapilot/workflow/state.py` — workflow-state schema v2 with valid `active_workflow_id = null` and legacy `share_invite` migration.
- `src/vibrapilot/workflow/contracts.py` — generic optional workflow-owned processing contract support.
- `src/vibrapilot/workflow/input_state.py` and `src/vibrapilot/workflow_inputs.py` — remove Core ownership of Share Invite schemas while retaining legacy migration mirrors.
- `src/vibrapilot/workflow/schemas.py` — removes built-in Share Invite schema builders.
- `src/vibrapilot/workflow/plugin_loader.py` — Plugin API remains 1; optional `load_task_data` discovery is backward-compatible with existing `load_task_items` plugins.
- `src/vibrapilot/backend.py` — removes direct ShareInviteWorkflow runtime/type dispatch; optional runtime `process_item` owns specialized workflow orchestration while the generic path remains unchanged.
- `src/vibrapilot/qt_app.py` — zero-workflow-safe UI/control plane, first activation from `None`, package-required recovery UX, and generic task-data loading.

## Source-controlled workflow deletion

The following v1.0.6.35 built-in files are intentionally removed:

- `src/vibrapilot/workflow/share_invite/__init__.py`
- `src/vibrapilot/workflow/share_invite/logo.png`
- `src/vibrapilot/workflow/share_invite/manifest.json`
- `src/vibrapilot/workflow/share_invite/workflow.py`

Because normal ZIP overlay cannot delete old files, `DELETE_BEFORE_APPLY.txt` is mandatory.

## Standalone Share Invite artifact

The Share Invite package is intentionally separate from the Core Delta. It uses Workflow Plugin API 1, `workflow_id = share_invite`, and contains executable Python. It must pass the normal VibraPilot inspection/trust/install flow; it is not silently installed by migration.

Sealed standalone package SHA-256: `6fe7f95bdf8bce5f9e22cfb2d375bafb8d5af857af5b9d1460c3cb5d372e1c50`.

Frozen-parity verification covers the v1.0.6.35 selector map, Share runtime methods, specialized item processing, schema identity, Test Mode gate, pre-Send safety, send accounting, retry/manual-review behavior, and audited task-data loading contract.

## Existing-user migration

- Existing schema-v1 `active_workflow_id = share_invite` is upgraded without quarantine.
- Canonical per-workflow Input/Settings values remain preserved.
- If Share Invite is not installed, Core reports that the matching trusted package is required rather than treating the state as corrupt.
- Installing the external package with the same `share_invite` identity resolves the existing state.
- A fresh install with no workflows receives a valid zero-active-workflow state.

## Compatibility

- Workflow Plugin API remains `1`.
- Existing API-1 workflows using `load_task_items` remain supported.
- DMARC Digests v1.0.1 coexists with Share Invite in the plugin-only catalog.
- Existing active-to-active transactional workflow switching remains fail-closed.
- First activation `None -> installed workflow` uses the normal atomic workflow-state commit path.

## Explicitly frozen

Chrome runtime/install/Authenticode, Playwright/browser profiles/diagnostics, licensing/Licora, TaskRuntime DB schema, workspace schema, reports/export, downloads/upload bridge, dependencies, CI workflow, build/Nuitka/WiX, URL workflow loading, workflow update/replace and workflow uninstall are outside this release.

## Verification performed before sealing

- Frozen v1.0.6.35 baseline SHA/integrity: PASS
- Frozen baseline repository verifier: PASS
- Frozen baseline pytest: `463 passed, 6 skipped, 106 subtests`
- v1.0.6.36 repository verifier: PASS
- v1.0.6.36 pytest: `462 passed, 6 skipped, 106 subtests`
- stdlib unittest: `200 OK, 6 skipped`
- compileall: PASS
- v1.0.6.36 source-policy diagnostic: PASS
- standalone Share Invite package/schema/install + frozen-runtime parity verifier: PASS
- pristine baseline scope comparison: unauthorized changed files `0`

Windows live acceptance is still required before Git publication.

## Delta safety

- Private `project/`: excluded
- AppData/Logs/Reports/FailedData: excluded
- BrowserProfiles: excluded
- caches/pyc/.git/build artifacts: excluded
- Standalone Share Invite package: separate artifact, not embedded in Core Delta
- DMARC package: not embedded or modified
