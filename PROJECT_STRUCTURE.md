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
