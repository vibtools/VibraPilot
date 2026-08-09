# Getting Started

1. Install Python 3.12 x64 on Windows 10/11.
2. Create and activate a virtual environment.
3. Run `python -m pip install -r requirements.txt`.
4. Run `python -m playwright install chromium`.
5. Do **not** add a Licora API v1 shared/master key. Secure licensing public configuration and the pinned server RSA public key are already defined in `config/AppConfig/licensing_public.py`.
6. Run `python scripts/verify_repository.py`.
7. Run `python -m pytest -q`.
8. Run `python -m unittest discover -s tests -p "test_*.py" -v`. The test modules bootstrap the repository `src` layout directly, so no shell-specific `PYTHONPATH` command is required in Command Prompt or PowerShell.
9. For any source ZIP intended to become a release/baseline, run `python scripts/verify_source_archive.py path\to\VibraPilot-source.zip` and require a PASS before distribution or freezing.
10. Launch with `python run.py`.

On first successful Secure API v2 activation, VibraPilot creates and persistently protects a P-256 device key through Windows DPAPI. Existing protected pre-v2 license caches are restored through the existing activation shell and migrated only after successful API v2 server validation.

## Production task recovery

Long-running task progress and authoritative recipient outcomes are stored locally in `AppData/task_runtime.sqlite3`. Recovery never automatically opens a browser or sends a recipient; the operator must restore the task, open/login/verify the browser session and explicitly resume. Ambiguous post-Send outcomes remain manual-review-only and are never automatically retried.

## Workflow Inputs

Workflow/form values are configured from the dedicated **Workflow Inputs** page. Existing values saved under `default_full_name`, `default_number`, `fallback_name` and `update_click_count` are preserved. **Default Target URL** remains in App Settings, while browser/runtime controls remain in Browser Settings. A failed Workflow Inputs Save/Reset operation is contained at the page boundary and restores the prior in-memory values. The current Share Invite backend remains unchanged; moving these values does not itself add a new browser consumer for them.
