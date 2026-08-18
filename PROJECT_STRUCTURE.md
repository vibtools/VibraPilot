# v1.0.6.39 Phase 1 Structure Addendum

New/updated Phase 1 surfaces:

```text
src/vibrapilot/power_management.py
config/verification/v1.0.6.39_runtime_reliability_session_policy_scope.json
tests/test_v10639_workflow_scoped_session_policy.py
tests/test_v10639_background_runtime_policy.py
tests/test_v10639_windows_sleep_guard.py
tests/test_v10639_active_page_ownership.py
tests/test_v10639_browser_resilience.py
tests/test_v10639_background_multitask_contract.py
docs/updates/v1.0.6.39-runtime-reliability-session-policy.md
docs/verification/V1.0.6.39_RUNTIME_RELIABILITY_SESSION_POLICY.md
```

Existing workflow loader/state/switch, licensing, persistence, report, CI and portable packaging structures remain unchanged in Phase 1.

---

# Project Structure — v1.0.6.38 Portable Runtime Root Fix

```text
src/vibrapilot/runtime_environment.py
    Single approved production correction: Nuitka OneDir data root follows the launched executable directory.

config/verification/v1.0.6.38_portable_runtime_root_fix_scope.json
tests/test_v10638_portable_runtime_root_fix.py
docs/updates/v1.0.6.38-portable-runtime-root-fix.md
docs/verification/V1.0.6.38_PORTABLE_RUNTIME_ROOT_FIX.md
    Scope, regression and forensic evidence for the v1.0.6.38 correction.
```

The v1.0.6.37 `portable-release.yml`, Nuitka builder, system-Chrome-only policy and no-WiX/MSI boundary remain structurally unchanged.

# Project Structure — v1.0.6.37 Portable Nuitka Release

```text
.github/workflows/portable-release.yml     Manual/tag portable Windows build
requirements-portable.txt                 Runtime + pinned Nuitka build dependencies
scripts/packaging/build_portable_nuitka.py
                                           Windows x64 Nuitka OneDir builder/ZIP sealer
scripts/packaging/verify_portable_release.py
                                           Portable payload/ZIP/checksum policy verifier
src/vibrapilot/runtime_environment.py     PyInstaller/Nuitka packaged-root compatibility shim
```

The historical `build.py` PyInstaller builder remains in the source tree for compatibility/history but is not used by the v1.0.6.37 GitHub portable release workflow.

# v1.0.6.36 Share Invite Workflow Externalization Structure

- VibraPilot Core contains zero source-controlled built-in workflows; installed trusted plugins form the runtime catalog.
- `src/vibrapilot/workflow/state.py` schema v2 represents `active_workflow_id: null` as a valid zero-workflow state and migrates the formerly built-in `share_invite` identity without quarantine.
- `src/vibrapilot/workflow/manager.py` and `plugin_loader.py` retain Plugin API 1 and add only optional backward-compatible rich data / specialized processing integration needed by the externalized Share Invite workflow.
- `src/vibrapilot/backend.py` resolves generic workflow runtimes and no longer imports or type-checks `ShareInviteWorkflow`.
- The standalone `Share_Invite_v1.0.vpworkflow` artifact is distributed separately from the Core source baseline.

## Historical v1.0.6.35 structure

- `src/vibrapilot/workflow/manager.py` registers Share Invite's namespaced Workflow Settings schema.
- `src/vibrapilot/workflow/schemas.py` defines the Share Invite Test Send limit field.
- `src/vibrapilot/qt_app.py` removes the global Test Safety card/gate and performs one-time migration.
- `src/vibrapilot/backend.py` consumes workflow-scoped send-limit snapshots and emits workflow-neutral session status.

# v1.0.6.33 Browser Forensic Closure

`src/vibrapilot/windows_authenticode.py` centralizes Windows file trust/publisher evidence for both installed Chrome and the approved Chrome MSI. No workflow, persistence, licensing, dependency, CI or build structure changed.

# Project Structure — v1.0.6.32 Chrome Prerequisite Secure Install

v1.0.6.32 adds `src/vibrapilot/chrome_installer.py` as the isolated secure prerequisite installer service. `chrome_runtime.py` remains responsible for installed Google Chrome discovery/identity; `qt_app.py` owns explicit consent/UI coordination; `backend.py` owns the final pre-Playwright fail-closed guard. No workflow, persistence, licensing, dependency, CI or build structure is changed.

# Project Structure — v1.0.6.31 Chrome-Only Runtime Foundation

v1.0.6.31 adds `src/vibrapilot/chrome_runtime.py` and updates the existing browser runtime/settings/diagnostics surfaces while retaining the v1.0.6.30 workflow, Task, persistence, licensing and managed-profile architecture.

```text
src/vibrapilot/workflow/
  plugin_loader.py          Trusted `.vpworkflow` inspection/staging/install/catalog loading
  schemas.py                Non-executable Workflow Inputs/Settings/Task UI schema contracts
  settings_state.py         Atomic per-workflow settings persistence
  task_state.py             Atomic per-Task workflow config/step/metric persistence
  manager.py                Unified built-in + installed workflow catalog/runtime resolution
  input_state.py            Per-workflow input persistence with unified schema resolver

%LOCALAPPDATA%/Vib Tools/VibraPilot/Workflows/
  <workflow_id>/            Installed trusted external workflow package
```

Core `backend.py` still owns worker lifecycle, retry/backoff, browser ownership and persistence orchestration. Core `qt_app.py` renders workflow schemas and owns all PySide UI widgets; plugins do not directly mutate application UI.

# Project Structure — v1.0.6.28 PR-11 Candidate

PR-11 adds only verification contract/tests and `scripts/diagnostics/pr11_windows_acceptance_runner.py` plus `verify_pr11_windows_evidence.py`. Production `src/vibrapilot/**` structure is unchanged from v1.0.6.27.

# Project Structure — v1.0.6.27 PR-10 Candidate

PR-10 adds `src/vibrapilot/workflow/recovery.py` for explicit crash-safe workflow recovery and updates only the approved workflow control-plane/UI modules. Backend, TaskRuntimeStore, workspace/data I/O, Share Invite runtime, Browser and licensing modules remain frozen.

# Project Structure — v1.0.6.26 PR-09 Candidate

PR-09 adds verification contracts/tests only; production runtime structure is unchanged from v1.0.6.25. `task_runtime_store.py`, `workspace_state.py`, `data_io.py`, workflow runtime/state modules and UI/backend remain frozen.

# Project Structure — v1.0.6.25 PR-08 Candidate

PR-08 adds `src/vibrapilot/workflow/input_state.py` for canonical atomic per-workflow Workflow Input persistence and expands `workflow_inputs.py` into the source-controlled declarative schema authority. `qt_app.py` renders the active schema dynamically and `backend.py` stores an immutable worker input snapshot.

```text
src/vibrapilot/
  backend.py                 Existing AutomationWorker + PR-08 immutable input snapshot
  qt_app.py                  Dynamic Workflow Inputs UI/migration/mirror/gating wiring
  workflow_inputs.py         Source-controlled declarative Workflow Input schemas
  workflow/
    input_state.py           PR-08 schema-v1 atomic per-workflow input persistence
    state.py                 PR-06 workflow-state + atomic switch/recovery (frozen)
    registry.py              Built-in registry; `share_invite` only (frozen)
    share_invite/            Current production workflow (frozen)
```

Current top-level UI pages remain: Dashboard, Tasks, Workflows, Workflow Inputs, Reports, Live Logs, App Settings, Browser Settings, About.

# Project Structure — v1.0.6.24 PR-07 Candidate

PR-07 adds no new production module. `src/vibrapilot/qt_app.py` now exposes a Workflows page between Tasks and Workflow Inputs. Workflow engine/state/registry/runtime modules remain unchanged from v1.0.6.23.

Current top-level UI pages: Dashboard, Tasks, **Workflows**, Workflow Inputs, Reports, Live Logs, App Settings, Browser Settings, About.

# Project Structure — v1.0.6.23 PR-06 Release

```text
.github/workflows/           Public CI workflow
assets/                      Application assets
config/                      Source-controlled application/runtime configuration
  AppConfig/                 Public app/About/support/social/Licora configuration
  verification/              Version/phase verification contracts
docs/                        Public documentation and historical release evidence
frozen_design_source/        Frozen Vib Tools design tokens
project/                     Private development/governance workspace; not runtime/public release input
scripts/                     Launch/repository/source-archive verification helpers
src/vibrapilot/
  app_config.py              Validated AppConfig facade
  backend.py                 Settings/licensing/task model/AutomationWorker/browser automation runtime
  browser_capabilities.py    Download path/filename and unpacked-extension helpers
  browser_diagnostics.py     Browser/environment/process diagnostics
  data_io.py                 Import reconciliation and report export
  licensing_v2.py            Licora Secure API v2 cryptographic client
  qt_app.py                  PySide6 application shell, Tasks, settings, PR-06 switch orchestration
  task_runtime_store.py      SQLite runs/items/results persistence
  workflow_inputs.py         Four existing settings-backed Workflow Input metadata fields
  workspace_state.py         Atomic workspace metadata persistence
  workflow/
    contracts.py             Workflow contracts/errors/runtime protocol
    registry.py              Deterministic built-in registry
    manager.py               Fail-closed active workflow runtime resolution
    state.py                 PR-06 persisted active state + switch transaction/recovery
    share_invite/            Only current production workflow
      manifest.json
      workflow.py
      logo.png
tests/                       Regression/security/scope/forensic contract tests
vib_validation_app/          Frozen design-system support modules
build.py                     Windows x64 release builder
run.py                       Source launcher
```

## Current UI pages

Dashboard, Tasks, Workflow Inputs, Reports, Live Logs, App Settings, Browser Settings and About. There is no Workflow Showcase page in v1.0.6.23; PR-07 owns that UI.

## Public/private release boundary

`project/`, runtime `AppData/`, `Logs/`, `Reports/`, `FailedData/`, caches and compiled Python files must remain excluded from clean public release-source artifacts.

Workflow cards now use a dedicated 2px tokenized border together with the shared surface and radius tokens so compact tiles remain visually distinct from the workflow page background.
