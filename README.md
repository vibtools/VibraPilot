# VibraPilot v1.0.6.1 — Vib Tools Browser Automation Desktop

**VibraPilot** is the new product name for the validated v1.0.6.1 Vib Tools desktop automation application. This branding transition does **not** change the current automation workflow, selectors, browser logic, safety controls, licensing behavior, reporting, or task-processing contract.

The current build still contains the existing site-specific authorized test workflow as its built-in workflow. The product identity is now **VibraPilot** so this codebase can serve as the frozen starting point for the planned reusable browser-automation and email/record-processing framework without pretending that the workflow has already been generalized.

## Application areas

- **License Activation** — Licora activation and periodic revalidation.
- **Dashboard** — task, runtime, license and usage overview.
- **Tasks** — independent browser task slots, data loading and processing controls.
- **Reports** — searchable results with CSV/Excel export.
- **Live Logs** — operational log viewer, save and clear actions.
- **App Settings** — safety, application, task-processing and license/API settings.
- **Browser Settings** — advanced persisted Playwright/Chromium controls.
- **About** — product and runtime information.

## Branding baseline

The v1.0.6.1 runtime behavior remains frozen. This update changes only product identity/documentation and application icon/logo integration:

- Product/display name: **VibraPilot**
- Python package: `src/vibrapilot/`
- Windows executable/release name: `VibraPilot`
- Launcher: `scripts/Start-VibraPilot.ps1`
- Login/activation branding: VibraPilot logo + name
- Main-window/header branding: VibraPilot logo + name
- Windows titlebar/taskbar icon: `assets/icons/app.ico`
- In-app logo image: `assets/icons/app.png`

The `assets/icons/` artwork is source-controlled and packaged into the Windows application.

## Current built-in workflow

The existing site-specific workflow is preserved exactly as a current built-in workflow. site-specific URLs/selectors remain only where technically required by that workflow; they are third-party workflow details, **not** the VibraPilot product identity. Future framework work can isolate this workflow behind a workflow/template boundary without changing the browser engine.

## Browser Settings contract

The advanced Browser Settings surface remains the v1.0.6.1 production-hardened configuration layer. Editable settings map to real Playwright/Chromium consumers and apply at their supported runtime, context, launch, or persistent-profile lifecycle boundary.

## License API configuration

Before a private/production build, review the private Licora deployment constants in:

```text
src/vibrapilot/backend.py
```

Do not publish production secrets. Desktop-embedded secrets must still be protected server-side with scope, rate limiting and revocation.

## Development

Requires Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python scripts/verify_repository.py
python -m pytest -q
python run.py
```

## Windows build

Use 64-bit Python 3.12 on Windows:

```powershell
python build.py
```

The builder produces a `VibraPilot` PyInstaller ONEDIR application and checksum-protected release ZIP under `release/`.

## Change and audit history

- Cumulative release history: `CHANGELOG.md`
- Detailed update index: `UPDATE_LOG.md`
- Versioning/update discipline: `VERSIONING.md`
- v1.0.6.1 release note: `docs/updates/v1.0.6.1.md`
- Browser Settings A–Z binding audit: `docs/updates/v1.0.6.1-browser-settings-audit.md`
- VibraPilot branding baseline note: `docs/updates/v1.0.6.1-vibrapilot-branding.md`
- Public CI/backend verification contract: `docs/verification/BACKEND_CONTRACT.md`

## Verification

```powershell
python scripts/verify_repository.py
python -m pytest -q
```

The verifier checks the frozen Vib Tools design source, the public backend parity contract, safety invariants, branding metadata, icon assets, UI integration, version metadata and repository hygiene. Frozen text-contract hashing is line-ending canonicalized, and `.gitattributes` pins repository text to LF so verification is deterministic on Windows and Linux runners. GitHub Actions exposes `src` through `PYTHONPATH` for source-layout contract tests and uses Node 24-native official GitHub Actions.

Public documentation belongs under `docs/`. The local `project/` tree is a private development workspace, remains gitignored, and is never a required CI input.

## License

GPL-3.0-only. See `LICENSE` and `NOTICE`.

Maintained by **Vib Tools** — https://vib.tools/
