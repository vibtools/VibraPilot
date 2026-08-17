# VibraPilot v1.0.6.37 — Portable Nuitka OneDir Release Packaging Delta

## Classification

- Frozen source baseline: `VibraPilot_v1.0.6.36_BASELINE_FINAL.zip`
- Baseline Git commit: `40b9b65d3900760d919167dc6711a4fcd494f010`
- Baseline ZIP SHA-256: `19f06990ae4b209da28159a25eced0b5be297579b907bcd60d79a3f3fe197ef5`
- Target version: `1.0.6.37`
- Recommended branch: `feature/v1.0.6.37-portable-nuitka-release`
- Release classification: Portable Windows Release Packaging Only

## Locked outcome

VibraPilot gains a dedicated GitHub Actions release path that builds a Windows x64 portable standalone OneDir application with pinned Nuitka 4.1.3. The portable archive uses the installed/verified system Google Chrome runtime and does not bundle Playwright Chromium, Google Chrome, WiX, MSI, or any installer payload.

The historical PyInstaller `build.py` and `requirements-build.txt` are preserved for compatibility/history but are not used by the new portable release workflow.

## Portable build path

The new packaging path is:

`GitHub Actions (Windows + Python 3.12 x64) -> source verification/tests -> Nuitka 4.1.3 standalone OneDir -> portable payload verification -> startup smoke -> ZIP + SHA-256 -> Actions artifact`

Manual `workflow_dispatch` creates a release candidate only. A version tag may publish a GitHub Release only when the tag exactly equals `v{AppConfig.VERSION}`.

## Browser boundary

- No `python -m playwright install chromium` command exists in the portable builder or workflow.
- Nuitka's built-in Playwright standalone support retains the Playwright control driver (`playwright/driver/node.exe` and `playwright/driver/package/cli.js`).
- `--playwright-include-browser=none` explicitly disables Playwright browser inclusion.
- Portable verification rejects `chrome.exe`, `chromium.exe`, `headless_shell.exe`, `ms-playwright`, `.playwright-browsers`, private/runtime state, WiX intermediates, and MSI payloads.
- Existing VibraPilot system Google Chrome discovery/install/Authenticode/runtime policy remains unchanged.

## Minimal runtime packaging compatibility

Nuitka deliberately does not use the historical PyInstaller `sys.frozen` contract. A small cross-packager helper is therefore introduced:

- `src/vibrapilot/runtime_environment.py` — detects source, PyInstaller and Nuitka packaged execution and resolves the packaged application root.
- `src/vibrapilot/backend.py` — uses that shared application root and packaged predicate for existing packaged-resource and licensing-environment decisions.
- `src/vibrapilot/qt_app.py` — uses the same packaged predicate for the existing workflow restart path.

No Chrome launch selectors/policy, workflow business logic, licensing protocol, persistence schema, Task DB schema, reporting, download/upload behavior, or general UI behavior is redesigned.

## New release infrastructure

- `.github/workflows/portable-release.yml`
- `requirements-portable.txt`
- `scripts/packaging/build_portable_nuitka.py`
- `scripts/packaging/verify_portable_release.py`
- `config/verification/v1.0.6.37_portable_release_packaging_scope.json`
- `tests/test_v10637_portable_release_packaging.py`
- v1.0.6.37 update/verification documentation

## Version metadata

The public source metadata is synchronized to `1.0.6.37` across AppConfig, `pyproject.toml`, `CITATION.cff`, project/docs manifests, and release documentation.

## Explicitly frozen

- Chrome discovery policy and launch behavior
- Chrome installer and Authenticode validation
- browser profiles and browser-diagnostics schema
- workflow runtime business logic and Workflow Plugin API
- Share Invite and DMARC external workflow packages
- Licora licensing protocol/device identity behavior
- Task runtime database schema
- workspace persistence schema
- reports/export
- download/upload bridge
- application feature/UI behavior
- WiX/MSI/installer work

## Source verification performed before sealing

- Frozen v1.0.6.36 baseline SHA/integrity: PASS
- Final source-tree repository verifier: PASS
- v1.0.6.37 targeted packaging/runtime compatibility tests: `31 passed, 1 skipped`
- Final source-tree pytest: `474 passed, 6 skipped, 106 subtests`
- Final source-tree standard-library unittest: `201 OK, 6 skipped`
- compileall: PASS
- Baseline-vs-candidate scope comparison: no unauthorized production file identified
- No source-controlled built-in workflow reintroduced
- No Playwright browser installation command introduced
- No WiX/MSI packaging path introduced

## Required Windows RC gate

This Delta does not claim that a Windows Nuitka binary was compiled inside the source-sealing environment. The first actual portable build is intentionally performed by the new Windows GitHub Actions `workflow_dispatch` path after the source patch is committed/merged.

Before a public `v1.0.6.37` tag/release, the Actions candidate must pass:

- Nuitka compile and packaged artifact verifier
- startup smoke
- clean-folder Windows launch
- licensing
- external workflow install/activation
- verified system Google Chrome launch/profile persistence
- controlled DMARC run
- controlled Share Invite Test Mode run
- workflow restart/persistence
- Logs/Reports/AppData behavior
- clean shutdown
- ZIP size/SHA/largest-file review

## Delta safety

- Required deletions: none
- Private `project/`: excluded
- AppData/Logs/Reports/FailedData: excluded
- BrowserProfiles: excluded
- caches/pyc/.git/build artifacts: excluded
- bundled Chromium/Chrome: excluded
- WiX/MSI: excluded
- Share Invite/DMARC workflow packages: separate and unchanged

## PR #17 attempt-1 CI stability correction

- Failed Actions run/job: `32044012728` / `95428147713`.
- Classification: verification timing false-negative, not a production task-runtime regression.
- The concurrent SQLite correctness test inherited a fixed 60-second total-completion watchdog from the v1.0.6.13 CI fix. The 2026 hosted Windows runner exceeded that bound while the finite writer threads were still completing.
- `src/vibrapilot/task_runtime_store.py` remains byte-frozen at SHA-256 `b4b581c936479a6a3f334170c033bae53f1d216e562cc1aff8b3e54e728dcf26`.
- The test-only deadlock guard is widened to 300 seconds. Successful runs do not wait for the guard.
- The new portable release workflow is pinned to `windows-2022` so the compiler host does not drift with the `windows-latest` label; the historical general CI workflow itself is unchanged.
- No application business logic, database schema, browser, workflow, licensing, persistence, reporting, Chromium, WiX, or MSI behavior changes are authorized by this correction.

## Portable RC startup diagnostic correction — run 32048312168

- Failed Actions run/job: `32048312168` / `95441285784` on pinned `windows-2022`.
- Source verification, full pytest/unittest, Nuitka 4.1.3 standalone compilation, OneDir creation, ZIP creation, SHA-256 generation, and the portable forensic verifier all passed before the startup gate.
- Candidate evidence before smoke: 827 files, 324,244,118 uncompressed bytes, 116,446,695 ZIP bytes, ZIP SHA-256 `90f95746a381d089d4ad3fe399f0087cabcba28ea9d26abc680cc95d3c0ad65c`, `bundled_chromium=false`, `wix_msi=false`.
- The packaged executable exited with code `1` before the 12-second smoke checkpoint.
- The failed workflow had `--windows-console-mode=disable`, no forced stdout/stderr capture, no application-log dump, and skipped artifact upload after the smoke failure. Therefore the failed run does not contain the underlying Python traceback; no production runtime root cause is asserted without that evidence.
- Manual `workflow_dispatch` RC builds now embed Nuitka forced stdout/stderr files only for diagnostic acceptance. Version-tag builds keep the normal console-disabled release behavior without forced diagnostic files.
- The packaged smoke clears inherited `PYTHONPATH` and `PYTHONHOME`, sets `PYTHONNOUSERSITE=1`, and uses only the disposable `VIB_TOOLS_DATA_DIR` so the acceptance run cannot accidentally consume the live checkout.
- Failed startup diagnostics are uploaded separately with `if: failure()`; a failed smoke still blocks the normal candidate artifact and all release publication.
- Production `src/`, workflow/browser/licensing/task persistence behavior, Chromium policy, WiX/MSI scope, and version identity are unchanged by this correction.
