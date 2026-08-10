## v1.0.6.17 browser capability surface

- `src/vibrapilot/browser_capabilities.py` — download-path/filename and unpacked-extension validation helpers.
- `src/vibrapilot/backend.py` — Playwright download/filechooser lifecycle integration and backend extension validation.
- `src/vibrapilot/qt_app.py` — Task Downloads action, native chooser UI, event rendering, save-time extension validation.
- `config/verification/v1.0.6.17_browser_capabilities_scope.json` — machine-readable scope lock.
- `tests/test_v10617_browser_capabilities.py` — regression contract.

No new database table, settings key or application page is added.

## v1.0.6.16 verification surface

- `config/verification/v1.0.6.16_workspace_persistence_verification_fix_scope.json`
- `tests/test_v10616_workspace_persistence_verification_fix.py`
- `docs/updates/v1.0.6.16-workspace-persistence-verification-fix.md`
- `docs/verification/V1.0.6.16_WORKSPACE_PERSISTENCE_FORENSIC_VERIFICATION.md`

## v1.0.6.15 workspace persistence addition

- `src/vibrapilot/workspace_state.py` — atomic lightweight workspace metadata store.
- `AppData/state.json` — runtime workspace metadata path already reserved by the baseline; no recipient rows, browser profile data or licensing secrets are stored here.
- `config/verification/v1.0.6.15_workspace_persistence_scope.json` — scope lock.
- `tests/test_v10615_workspace_persistence.py` — workspace persistence regression contract.

## v1.0.6.14 current implementation surface

```text
config/settings.defaults.json   Managed persistent browser enabled by default
config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json
src/vibrapilot/backend.py       Managed profile resolver/migration + persistent recycle compatibility
src/vibrapilot/qt_app.py        Profile validation + Open Closed Tasks / Task archive-reopen UI
src/vibrapilot/task_runtime_store.py  Closed Task lifecycle using existing schema v1
tests/test_v10614_managed_persistent_browser.py
```

No new application page, database table/column, dependency or permanent Task-delete feature is introduced.

# Project Structure

```text
.github/workflows/           CI
assets/                      Application assets
config/                      Source-controlled application/runtime configuration and public machine contracts
  AppConfig/                 Public app/About/support/social + Licora API v2 public configuration
  verification/              Backend, historical scope locks, Phase-01 lifecycle and current v1.0.6.13 verification-fix contracts
docs/                        Public product documentation and per-release update notes
frozen_design_source/        Official frozen Vib Tools token JSON
project/                     Private local development workspace (gitignored; never required by CI)
scripts/                     Launch, repository verification and clean source-archive verification helpers
src/vibrapilot/              Production application
  app_config.py              Validated read-only AppConfig facade
  licensing_v2.py            Secure Licora API v2 protocol/cryptographic client
  backend.py                 validated automation + production worker/runtime wiring; v1.0.6.12 browser lifecycle runtime (byte-frozen in v1.0.6.13)
  data_io.py                 Input/export adapters + import reconciliation
  task_runtime_store.py       SQLite task/checkpoint/result persistence
  workflow_inputs.py          Workflow/form input metadata only
  qt_app.py                  Vib Tools PySide6 interface; v1.0.6.12 Task browser lifecycle/geometry runtime (byte-frozen in v1.0.6.13)
tests/                       Static/runtime/security/scope contract tests
vib_validation_app/          Vib Tools design-system modules; v1.0.6.11 approves focus-manager lifetime correction only
CHANGELOG.md                  Cumulative release history
UPDATE_LOG.md                 Concise production update index
VERSIONING.md                 Release/version documentation policy
build.py                      Windows x64 release builder
run.py                        Source launcher
```
