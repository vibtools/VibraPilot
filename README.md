# VibraPilot v1.0.6.4 — Vib Tools Browser Automation Desktop

**VibraPilot v1.0.6.4** is the Phase-02-Step-002 verification/fix release built from the user-frozen **v1.0.6.3 Official Baseline**. It retains the Secure Licora API v2 architecture introduced in v1.0.6.3 while correcting verified session-continuity, refresh-recovery, startup-restore and release-packaging defects found during the forensic audit. The validated browser workflow, selectors, Playwright/browser behavior, task/report contract, safety controls and frozen Vib Tools UI foundation remain unchanged.

## Application areas

- **License Activation** — device-bound Licora API v2 activation and periodic server revalidation.
- **Dashboard** — task, runtime, license and usage overview.
- **Tasks** — independent browser task slots, data loading and processing controls.
- **Reports** — searchable results with CSV/Excel export.
- **Live Logs** — operational log viewer, save and clear actions.
- **App Settings** — safety, application, task-processing and licensing/network settings.
- **Browser Settings** — advanced persisted Playwright/Chromium controls.
- **About** — product, support and runtime information.

## Secure Licora API v2

Public licensing configuration is centralized in:

```text
config/AppConfig/licensing_public.py
```

It contains only non-secret values: `https://mxflow.shop`, App ID `vibrapilot`, the four `/api/v2/` endpoint paths, the expected signing-key ID and the **server RSA public signing key** used for local access-token verification.

The client flow is:

```text
P-256 device key → activate → RS256 access token + rotating refresh token
                 → status → refresh/rotate → status → deactivate
```

VibraPilot signs API v2 requests with the locally generated P-256 device private key. The server private signing key never leaves Licora. Sensitive local licensing material is protected with Windows DPAPI and persisted atomically in schema-v2 `AppData/license.json`. The P-256 device identity is persistent across logout, license switching and restart; session tokens and the protected license are cleared on logout.

The active source contains **no Licora API v1 master/shared API key** and no `/api/verify.php` desktop authentication flow. See `docs/guides/LICENSING.md`.

## Phase-02 scope freeze

Phase-02-Step-002 is explicitly scope-locked. The original v1.0.6.2 semantic freeze remains active, and `config/verification/phase02_step002_v1.0.6.4_fix_scope.json` additionally byte-locks operational files outside the approved v1.0.6.3 verification/fix surface. Canonical AST hashes in `config/verification/phase02_step002_scope.json` prove that these baseline areas remain unchanged:

- `AutomationWorker`
- `SELECTORS`
- `TaskItem`
- `TaskState`
- `ActivationPage`
- `BROWSER_SETTING_GROUPS`

The existing site-specific authorized workflow is still the built-in workflow. No selector redesign, browser-engine refactor, UI redesign, task/report redesign or general workflow-framework extraction is included in this release.

## AppConfig architecture

Public/non-secret application configuration lives under:

```text
config/AppConfig/
├── app.py
├── about.py
├── support.py
├── social.py
└── licensing_public.py
```

`src/vibrapilot/app_config.py` validates those modules and exposes read-only runtime objects including `APP`, `ABOUT`, `SUPPORT`, social links and `LICENSING`.

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

`cryptography` is required for P-256 request proofs and RS256 token verification.

## Windows build

Use 64-bit Python 3.12 on Windows:

```powershell
python build.py
```

The builder produces the `VibraPilot` PyInstaller ONEDIR application and release archive under `release/`.

## Change and audit history

- Cumulative release history: `CHANGELOG.md`
- Concise update log: `UPDATE_LOG.md`
- Versioning discipline: `VERSIONING.md`
- v1.0.6.4 verification/fix note: `docs/updates/v1.0.6.4-phase-02-step-002-verification-fix.md`
- v1.0.6.4 forensic verification: `docs/verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md`
- Historical v1.0.6.3 Phase-02 note: `docs/updates/v1.0.6.3-phase-02-step-002-secure-licensing.md`
- Historical v1.0.6.3 verification: `docs/verification/PHASE02_STEP002_V1.0.6.3_VERIFICATION.md`
- Licensing contract: `docs/guides/LICENSING.md`
- AppConfig architecture: `docs/configuration/APPCONFIG.md`
- Public backend/CI contract: `docs/verification/BACKEND_CONTRACT.md`

Historical Phase-01 and v1.0.6.1 notes remain under `docs/updates/` and `docs/verification/`.

## Verification

```powershell
python scripts/verify_repository.py
python -m pytest -q
python -m unittest discover -s tests -p "test_*.py" -v
```

`pyproject.toml` configures pytest to import from `src`. The unittest modules now bootstrap the repository `src` layout themselves, so the same direct unittest command works in Command Prompt and PowerShell without shell-specific `PYTHONPATH` syntax.

The verifier checks the frozen Vib Tools design source, backend parity contract, Phase-02 scope hashes, AppConfig/static metadata consistency, Secure API v2 public-key/endpoint invariants, secret hygiene, safety behavior, branding/icons and repository structure.

Public documentation belongs under `docs/`. The local `project/` tree and runtime `AppData/`, `Logs/`, `Reports/` and `FailedData/` trees are private/gitignored and are not release-source inputs.

## License

GPL-3.0-only. See `LICENSE` and `NOTICE`.

Maintained by **Vib Tools** — https://vib.tools/
