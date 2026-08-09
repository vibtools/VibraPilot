## v1.0.6.14 managed-profile acceptance

For the v1.0.6.14 candidate, keep the verified Phase-01 browser lifecycle gate and additionally verify that a Task reopens the same VibraPilot-managed profile after browser/app restart, Task profiles remain isolated, personal Chrome `User Data` paths are blocked, and **Open Closed Tasks** restores deliberately closed Task data/progress without opening the browser or starting/sending automatically. Browser-history persistence must be checked with real Chrome on Windows before baseline freeze.

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
11. For v1.0.6.11 production acceptance, navigate/focus across Activation, Workspace, Workflow Inputs, App Settings and Browser Settings and require zero `libshiboken`, `QObject::eventFilter` or `Internal C++ object ... already deleted` traceback output.
12. For v1.0.6.13 acceptance, run the v1.0.6.12 browser lifecycle live gate unchanged: open a Task browser, manually close the browser/window, verify `Browser: Closed`, `Login: Not Verified`, Dashboard Browser Ready decrement, then reopen it; also verify the first workspace is fully visible after activation. Require both pytest and the standard-library unittest compatibility step to pass on Windows/GitHub CI.

On first Secure API v2 activation, VibraPilot creates and DPAPI-protects a persistent P-256 device identity. In v1.0.6.10 the default Windows license/device state lives under `%LOCALAPPDATA%\Vib Tools\VibraPilot` so clean source/application folders do not generate a different key for the same old device ID. Historical install-relative protected caches are migrated once when the durable cache is absent; an explicit `VIB_TOOLS_DATA_DIR` remains authoritative.

## Production task recovery

Long-running task progress and authoritative recipient outcomes are stored locally in `AppData/task_runtime.sqlite3`. Recovery never automatically opens a browser or sends a recipient; the operator must restore the task, open/login/verify the browser session and explicitly resume. Ambiguous post-Send outcomes remain manual-review-only and are never automatically retried.

## Workflow Inputs

Workflow/form values are configured from the dedicated **Workflow Inputs** page. Existing values saved under `default_full_name`, `default_number`, `fallback_name` and `update_click_count` are preserved. **Default Target URL** remains in App Settings, while browser/runtime controls remain in Browser Settings. A failed Workflow Inputs Save/Reset operation is contained at the page boundary and restores the prior in-memory values. The current Share Invite backend remains unchanged; moving these values does not itself add a new browser consumer for them.
