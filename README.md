# VibraPilot v1.0.6.2 — Vib Tools Browser Automation Desktop

**VibraPilot v1.0.6.2** is the verified Phase-01 configuration baseline for the Vib Tools desktop automation application. It preserves the validated browser workflow, selectors, browser logic, safety controls, Licora v1 licensing behavior, reporting and task-processing contract.

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

## Phase-01 AppConfig architecture

Public/non-secret application metadata is centralized under `config/AppConfig/`:

```text
config/AppConfig/
├── app.py
├── about.py
├── support.py
└── social.py
```

`src/vibrapilot/app_config.py` validates those modules and exposes a read-only facade to runtime consumers. `app.py` is the authoritative source for application identity/version/owner/license metadata; About, support/documentation and social/community content are separated by responsibility. Runtime compatibility constants and build metadata consume this central configuration rather than maintaining independent application-name/version literals.

Static package/document manifests remain synchronized mirrors and are checked by `scripts/verify_repository.py`. Phase-01 intentionally contains **no Licora API key, API URL migration or licensing-protocol change**. See `docs/configuration/APPCONFIG.md`.

### v1.0.6.2 Phase-01 verification baseline

The forensic completion pass removed stale active pre-rebrand source/launcher paths, replaced an unverified developer-portal value with an intentionally blank configuration, populated the confirmed Vib Tools support/contact and official social links, and strengthened AppConfig validation for dates, versions, sequence content, email and social enabled flags. No Phase-02 licensing implementation is included.

## Current built-in workflow

The existing site-specific workflow is preserved exactly as a current built-in workflow. site-specific URLs/selectors remain only where technically required by that workflow; they are third-party workflow details, **not** the VibraPilot product identity. Future framework work can isolate this workflow behind a workflow/template boundary without changing the browser engine.

## Browser Settings contract

The advanced Browser Settings surface remains the v1.0.6.1 production-hardened configuration layer. Editable settings map to real Playwright/Chromium consumers and apply at their supported runtime, context, launch, or persistent-profile lifecycle boundary.

## License API configuration

Phase-01 does not modify licensing. The existing Licora deployment constants remain in:

```text
src/vibrapilot/backend.py
```

They are intentionally excluded from `config/AppConfig/`. Secure public licensing configuration and Licora API v2 are reserved for Phase-02. Production credentials should not be treated as safely hidden merely because they are embedded in a desktop client; Phase-02 will move to the approved stronger client/server trust model.

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
- AppConfig architecture: `docs/configuration/APPCONFIG.md`
- Phase-01 AppConfig update note: `docs/updates/v1.0.6.1-phase-01-appconfig.md`
- v1.0.6.2 Phase-01 verification/fix note: `docs/updates/v1.0.6.2-phase-01-verification-fix.md`

## Verification

```powershell
python scripts/verify_repository.py
python -m pytest -q
```

The verifier checks the frozen Vib Tools design source, the public backend parity contract, AppConfig/static-metadata consistency, safety invariants, branding metadata, icon assets, UI integration, version metadata and repository hygiene. Frozen text-contract hashing is line-ending canonicalized. Backend implementation parity uses a canonical semantic AST contract that omits empty/version-specific AST fields, so the same source verifies consistently across supported Python minor versions such as the Python 3.12 GitHub runner. `.gitattributes` pins repository text to LF, GitHub Actions exposes `src` through `PYTHONPATH`, and the CI workflow uses Node 24-native `actions/checkout@v5` and `actions/setup-python@v6`.

Public documentation belongs under `docs/`. The local `project/` tree is a private development workspace, remains gitignored, and is never a required CI input.

## License

GPL-3.0-only. See `LICENSE` and `NOTICE`.

Maintained by **Vib Tools** — https://vib.tools/
