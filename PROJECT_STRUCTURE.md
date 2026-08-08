# Project Structure

```text
.github/workflows/           CI
assets/                      Application assets
config/                      Source-controlled application/runtime configuration and public machine contracts
  AppConfig/                 Authoritative non-secret app/About/support/social metadata
docs/                        Public product documentation and per-release update notes
frozen_design_source/        Official frozen Vib Tools token JSON
project/                     Private local development workspace (gitignored; never required by CI)
scripts/                     Launch and repository-verification helpers
src/vibrapilot/              Production application
  app_config.py              Validated read-only AppConfig facade
  backend.py                 v1.0.6 automation baseline + approved browser-settings hardening; current release v1.0.6.2
  data_io.py                 Input/export adapters
  qt_app.py                  Vib Tools PySide6 interface
tests/                       Static/runtime contract tests
vib_validation_app/          Exact supplied Vib Tools design-system modules
CHANGELOG.md                  Cumulative release history
UPDATE_LOG.md                 Concise production update index
VERSIONING.md                 Release/version documentation policy
build.py                      Windows x64 release builder
run.py                        Source launcher
```
