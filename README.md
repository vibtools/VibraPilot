# VibraPilot v1.0.6.8 — Vib Tools Browser Automation Desktop

**VibraPilot v1.0.6.8** is the approved `VP-WORKFLOW-INPUTS-001` UI-ownership separation release built from the final v1.0.6.7 baseline. It moves the four existing workflow/form values out of App Settings into a dedicated **Workflow Inputs** page while preserving the same settings keys, saved values, backend behavior, Browser Settings, task workflow and Licora Secure API v2.


## Workflow Inputs separation

`VP-WORKFLOW-INPUTS-001` adds a dedicated **Workflow Inputs** page after Tasks. The page owns the existing `default_full_name`, `default_number`, `fallback_name` and `update_click_count` values through the existing `SettingsManager` keys. `default_target_url` remains in App Settings. No workflow selector is shown while only one real workflow exists, and the new `workflow_inputs.py` module contains form metadata only.

## Windows SQLite concurrency verification

The v1.0.6.7 verification baseline includes a follow-up Windows concurrency correction for the local SQLite task runtime store. In-process writers are serialized before SQLite's WAL writer lock, and per-recipient item/result/progress persistence uses one atomic transaction on the worker hot path. This keeps `PRAGMA synchronous` at SQLite's durable default instead of weakening crash durability to improve test speed.

## Application areas

- **License Activation** — device-bound Licora API v2 activation and periodic server revalidation.
- **Dashboard** — task, runtime, license and usage overview.
- **Tasks** — independent browser task slots, data loading and processing controls.
- **Workflow Inputs** — workflow/form values kept separate from application and browser configuration.
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

## Production runtime hardening

`VP-PROD-MT-LR-001` adds a local SQLite-backed task runtime store (`AppData/task_runtime.sqlite3`) and keeps each task identified by its own `run_id`, recipient set and result ledger. Processing remains sequential inside each task; `batch_size` defines checkpoint boundaries and does **not** introduce parallel recipient sending. `auto_save_interval` is now interpreted in seconds, with `0` disabling timed autosave while finalized recipient outcomes are still persisted immediately.

Production behavior now includes:

- input reconciliation for source/valid/invalid/duplicate/accepted rows;
- atomic task/checkpoint persistence and restart recovery without automatic sending;
- explicit manual-review handling for ambiguous post-Send outcomes;
- correct item/time Browser Context recycling after successful or failed finalized recipients;
- deterministic worker shutdown that retains live worker references until cleanup finishes;
- a bounded 4096-event UI queue and a maximum 250 events processed per UI timer tick;
- one authoritative current outcome per `run_id + item_index`, with full export backed by the runtime ledger;
- Reports filtering by Task;
- a default maximum of 4 simultaneously active task workers; and
- a persistent-profile collision guard when multiple tasks would claim the same shared profile.

The v1.0.6.5 production-hardening milestone itself added no permanent top-level page; its recovery flow remains in Tasks plus transient dialogs. v1.0.6.8 later adds only the approved Workflow Inputs configuration page.

## v1.0.6.7 forensic corrections

The v1.0.6.7 verification pass corrects four operational defects without redesigning the v1.0.6.5 production architecture: the Task-card stylesheet classmethod now binds correctly at startup, saturated critical UI events can exit during an explicit worker stop/close, the conservative pre-Send manual-review marker is immediately represented in the authoritative result ledger, and the Task metric explicitly labels the counter as **Send Attempts / Limit**.

Source baseline ZIPs can be checked with:

```powershell
python scripts/verify_source_archive.py path\to\VibraPilot-source.zip
```

The verifier rejects `AppData/`, `FailedData/`, `Reports/`, `Logs/`, private `project/`, Python caches and unsafe ZIP paths. Applying a delta to an existing working installation does **not** delete runtime `AppData`; the exclusion rule applies to distributable source baseline/release archives.

## Production scope freeze

The approved production boundary is machine-checked by `config/verification/production_mt_lr_v1.0.6.5_scope.json`. It identifies the exact v1.0.6.4 baseline archive, approved runtime surface and parameters, and freezes out-of-scope files/settings plus canonical AST contracts for `LicenseManager`, `SELECTORS`, `ActivationPage` and `BROWSER_SETTING_GROUPS`. The Phase-02 licensing scope manifests remain historical evidence.

The existing site-specific authorized Share Invite workflow is unchanged: no selector redesign, Send-flow redesign, stealth/anti-bot implementation, licensing-protocol change or browser-engine replacement is included in this release.

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
- v1.0.6.8 Workflow Inputs note: `docs/updates/v1.0.6.8-workflow-inputs-separation.md`
- v1.0.6.8 Workflow Inputs verification: `docs/verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md`
- v1.0.6.7 verification/fix note: `docs/updates/v1.0.6.7-vp-prod-mt-lr-verification-fix.md`
- v1.0.6.7 forensic verification: `docs/verification/V1.0.6.7_VP_PROD_MT_LR_FORENSIC_VERIFICATION.md`
- v1.0.6.5 production-hardening note: `docs/updates/v1.0.6.5-production-multi-task-long-run-stability.md`
- v1.0.6.5 production verification: `docs/verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md`
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

The verifier checks the frozen Vib Tools design source, backend parity contract, production scope hashes/settings, AppConfig/static metadata consistency, Secure API v2 public-key/endpoint invariants, secret hygiene, safety behavior, branding/icons and repository structure.

Public documentation belongs under `docs/`. The local `project/` tree and runtime `AppData/`, `Logs/`, `Reports/` and `FailedData/` trees are private/gitignored and are not release-source inputs.

## License

GPL-3.0-only. See `LICENSE` and `NOTICE`.

Maintained by **Vib Tools** — https://vib.tools/
