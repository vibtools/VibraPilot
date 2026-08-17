# VibraPilot v1.0.6.38 — Portable OneDir Runtime Root Fix Delta

## Classification

- Authoritative user input snapshot: `Updated_Baseline.zip`
- Input snapshot SHA-256: `007d339193e7f02bc316514e82512174034d611c889a327580f59a32a24bfddb`
- Embedded tracked source branch: `main`
- Embedded/GitHub source commit: `299e93a89db3d30505350f474f79eefc330ee923`
- Embedded Git tree: `d946c22d40bf4e919989b7473cacf0c3926f10ee`
- Baseline source version: `1.0.6.37`
- Target version: `1.0.6.38`
- Recommended branch: `fix/v1.0.6.38-portable-runtime-root`
- Classification: defect-only portable runtime-location correction

## Exact failure evidence

Second GitHub Actions portable RC:

- Workflow run: `32056816056`
- Job: `95468779983`
- Source SHA: `299e93a89db3d30505350f474f79eefc330ee923`
- Startup diagnostics artifact: `9297920798`
- Diagnostics artifact SHA-256: `4e26c5b3f9683cd3422e178d1cd7472ac8057286f6bf683880aca3b772fe9ec0`
- Built RC ZIP SHA-256: `d2afb06bacb807987ef3f5e010b801f644a4127997ee0b9ca9331ab9e41e0f5a`
- Built RC ZIP bytes: `116450399`
- Built RC files: `827`

Before startup, source verification, full tests, Nuitka compilation, OneDir creation, ZIP/checksum verification, no-Chromium enforcement and no-WiX/MSI enforcement all passed.

Captured stderr then proved:

`RuntimeError: Settings defaults could not be loaded: ...\release\config\settings.defaults.json`

The verified payload contained the file at:

`...\release\VibraPilot-1.0.6.37-Windows-x64-Portable\config\settings.defaults.json`

Therefore the packaged application root was exactly one directory too high.

## Root cause

`src/vibrapilot/runtime_environment.py` used `__compiled__.containing_dir` as the data root for Nuitka standalone execution. For this copied OneDir layout that value described the directory containing the portable/dist folder, not the directory containing `VibraPilot.exe` and its adjacent packaged resources.

The v1.0.6.38 correction is exactly:

```python
if _nuitka_compiled_marker() is not None:
    return Path(sys.argv[0]).resolve().parent
```

PyInstaller `_MEIPASS` behavior and source-mode repository-root behavior are preserved.

## Scope lock

Only one production runtime file is modified:

- `src/vibrapilot/runtime_environment.py`

The following domains remain byte/behavior frozen from the tracked v1.0.6.37 source baseline:

- backend business logic
- Qt UI/UX behavior
- Chrome discovery/launch policy
- secure Chrome installer and Authenticode validation
- browser profiles and diagnostics schema
- workflow business logic and Plugin API
- Share Invite and DMARC external packages
- Licora licensing protocol/device identity
- TaskRuntimeStore/database schema
- workspace schema
- reports/exports
- download/upload bridge
- runtime dependencies
- general CI workflow
- portable workflow architecture/build host
- Nuitka and Playwright versions

## Portable architecture preserved

- GitHub Actions host: `windows-2022`
- Python: `3.12 x64`
- Nuitka: `4.1.3`
- Mode: standalone OneDir
- Playwright browser inclusion: `none`
- Browser: verified system Google Chrome only
- Playwright control driver: packaged
- Bundled Chromium/Chrome: forbidden
- WiX/MSI: not produced
- Manual `workflow_dispatch`: RC build
- exact version tag: release publication path after all build/smoke gates pass

The v1.0.6.37 diagnostic startup-smoke hardening is retained unchanged: source `PYTHONPATH/PYTHONHOME` is removed from the packaged smoke and RC-only forced stdout/stderr is available on failure.

## Version/documentation changes

Version identity is synchronized to `1.0.6.38` across AppConfig, package metadata, citation/project/docs manifests and release documentation. Portable verifier status text now derives from `AppConfig.VERSION` rather than carrying a stale literal v1.0.6.37 identity.

Historical v1.0.6.37 update/verification documents record the failed second RC and its superseding v1.0.6.38 root fix.

## Authoritative input snapshot hygiene

`Updated_Baseline.zip` is accepted as the user's authoritative input snapshot and its embedded tracked source is exact commit `299e93a...`; however, the ZIP is a workspace snapshot and must not itself be published as a clean source baseline.

Observed ZIP content includes:

- 778 total entries
- 91 `.git/` entries
- 25 private `project/` entries
- 11 `AppData/` entries
- 27 `Logs/` entries
- 1 `Reports/` entry
- 1 `FailedData/` entry
- 212 `__pycache__/` entries
- 8 `.pytest_cache/` entries
- stray command-output placeholders: `-D`, `-n`, `RUN_ID`, `VibraPilot-Windows-x64-Portable-Startup-Diagnostics`

None of those private/runtime/cache/workspace-only paths are part of this Delta.

## Forensic verification performed

Against a clean `git archive` of embedded HEAD `299e93a...`:

- targeted v1.0.6.38/v1.0.6.37/AppConfig/build-metadata tests: `24 passed`
- repository verifier: PASS
- full pytest: `482 passed, 6 skipped, 106 subtests passed`
- standard-library unittest: `201 OK, 6 skipped`
- compileall: PASS
- only one production `src/vibrapilot/**` file changed: `runtime_environment.py`
- frozen backend/Qt/TaskRuntime/Chrome/CI/workflow/dependency hashes: PASS via v1.0.6.38 regression contract
- no fake/demo/placeholder implementation marker in current portable runtime/build surfaces
- no dependency change
- no portable GitHub workflow change
- no WiX/MSI addition
- no Chromium/Chrome bundle addition
- no deletion required

Synthetic licensing/network/corrupt-store/browser warnings emitted by negative-path tests are expected test fixtures; authoritative suites passed.

## Remaining real Windows release gate

Source-level correction is verified, but v1.0.6.38 must **not** be called FINAL/FROZEN solely from this non-Windows sealing environment. Final freeze requires:

1. Windows owner local acceptance of this Delta.
2. PR CI green.
3. fast-forward promotion to `main` and post-merge CI green.
4. a fresh `Portable Windows Release` `workflow_dispatch` from v1.0.6.38 `main`.
5. Nuitka OneDir compile + forensic verifier + packaged startup smoke green.
6. downloaded RC live Windows acceptance, including system Chrome and representative external workflow behavior.
7. only then: clean source-only v1.0.6.38 baseline ZIP + SHA-256 and official freeze.
8. public version tag/release only after owner acceptance.

## Delta safety

- Required deletions: none
- `project/`: excluded
- `.git/`: excluded
- AppData/Logs/Reports/FailedData: excluded
- caches/pyc: excluded
- browser profile/runtime data: excluded
- built EXE/OneDir/ZIP output: excluded
- external workflow packages: excluded and unchanged
