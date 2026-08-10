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
