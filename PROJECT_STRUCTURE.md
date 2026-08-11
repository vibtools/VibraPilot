# Project Structure — v1.0.6.29 PR-12 Candidate

PR-12 adds `installer/VibraPilot.wxs`, `.github/workflows/pr12-package-build.yml`, CI artifact verification, PC artifact/install acceptance tooling, and replaces the Windows build implementation in `build.py`. Packaging compilation is GitHub Actions-only. The only production runtime source change is the authorized Nuitka packaged-root compatibility block in `src/vibrapilot/backend.py`.

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
