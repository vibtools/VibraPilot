# Project Structure

```text
.github/workflows/           CI
assets/                      Application assets
config/                      Source-controlled runtime defaults
docs/                        Product documentation and per-release update notes
frozen_design_source/        Official frozen Vib Tools token JSON
project/research/            Forensic audit and preserved v1.0.6 source baseline
project/specifications/      Feature-parity specification
scripts/                     Launch and repository-verification helpers
src/vibrapilot/        Production application
  backend.py                 v1.0.6 baseline + approved v1.0.6.1 browser-settings hardening
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
