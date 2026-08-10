# Chrome Web Store Extension Installation — Dedicated Forensic Root-Cause Fix

## Scope

Baseline: **VibraPilot v1.0.6.19**

Baseline archive SHA-256:

`731c68b36fd863957be4dc205f48a666b5bf8a36872adf44c834a8e54ec1f685`

GitHub baseline commit:

`dca5bc8a12185cdbcc31e7dc77057a31038fdd86`

This investigation is intentionally limited to the Chrome Web Store message:

`Installation is not enabled`

Download, profile, sandbox, workflow, database, licensing and unrelated browser behavior are not changed.

## Observed runtime evidence

The user reproduced the Chrome Web Store message in Google Chrome Stable while normal browser download continued to work.

Available Phase-1 Windows process evidence recorded the Chrome command line with:

`--disable-extensions`

and without:

`--disable-extensions-except`

The same evidence identifies the managed Task profile and Google Chrome executable. The later v1.0.6.19 source kept this default-argument behavior unchanged.

## Source trace

`src/vibrapilot/backend.py::effective_ignored_default_args()` defines:

`_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG = "--disable-extensions"`

Before this fix it filtered that Playwright default only when VibraPilot's explicit unpacked-extension mode was enabled:

```python
if extensions_enabled:
    add(_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG)
```

The baseline default is:

```json
"extensions_enabled": false
```

Therefore normal Chrome mode left Playwright's `--disable-extensions` default active.

`AutomationWorker.launch_browser()` passes the resulting list as Playwright `ignore_default_args`.

## Chromium root-cause chain

Chromium source defines `IDS_EXTENSION_INSTALL_NOT_ENABLED` as the user-facing string `Installation is not enabled`.

Chromium CRX installer returns `INSTALL_NOT_ENABLED` when its extension service reports extensions disabled.

Chromium's extension-service tests explicitly verify that the `kDisableExtensions` command-line switch causes the extension service to report extensions disabled.

Therefore the project-specific causal chain is:

```text
extensions_enabled=false
→ effective_ignored_default_args() does not filter Playwright --disable-extensions
→ Playwright starts Chrome with --disable-extensions
→ Chromium ExtensionService is disabled
→ Chrome Web Store installation reaches INSTALL_NOT_ENABLED
→ "Installation is not enabled"
```

## Root cause

**CONFIRMED**

The message is caused by Playwright's global `--disable-extensions` default remaining active during normal VibraPilot Chrome sessions.

It is not necessary to invoke a Chrome policy, profile corruption or download restriction to explain the observed message.

No VibraPilot source code was found that writes Chrome enterprise ExtensionSettings, ExtensionInstallAllowlist or ExtensionInstallBlocklist policy for this behavior.

## Minimal fix

Change only the default-argument filter:

- Always filter Playwright's global `--disable-extensions` default.
- Keep `extensions_enabled` responsible only for VibraPilot's explicit unpacked side-loading mode and its `--disable-extensions-except` / `--load-extension` arguments.

No settings key or default changes are required.

## Download preservation

Download runtime code and `browser_capabilities.py` remain byte-frozen. `accept_downloads=true` remains unchanged.

The extension-service fix does not alter download routing, download directories, `Download.save_as()`, upload handling or file chooser behavior.

## Verification

Source/regression acceptance requires:

1. `effective_ignored_default_args(..., extensions_enabled=False)` contains `--disable-extensions` in the ignored-default list.
2. unpacked extension mode still filters the same Playwright default exactly once.
3. browser-capability runtime source remains byte-frozen.
4. repository verifier passes.
5. full pytest/unittest passes.

Windows runtime acceptance requires a new browser launch after applying the patch:

1. `Logs\BrowserDiagnostics\slot_1_latest.json` must show no effective `--disable-extensions` switch.
2. Chrome Web Store must no longer show `Installation is not enabled` for a normal install attempt.
3. The selected extension must appear under the managed Task profile after installation.
4. Close/reopen Browser and verify the extension remains installed.
5. Download a real test file and verify the existing download path still works.

Use:

```cmd
python scripts/diagnostics/verify_chrome_webstore_extension_runtime.py --extension-id <CHROME_WEB_STORE_EXTENSION_ID>
```

Real Windows Web Store installation remains **RUNTIME VERIFICATION REQUIRED** until this post-fix test is executed on the target Windows machine.

## Primary sources used for the forensic mapping

- Chromium `extensions/strings/extensions_strings.grd` — `IDS_EXTENSION_INSTALL_NOT_ENABLED`.
- Chromium `extensions/browser/crx_installer.cc` — `INSTALL_NOT_ENABLED` branch when extensions are disabled.
- Chromium `chrome/browser/extensions/extension_service_unittest.cc` — `kDisableExtensions` makes the extension service disabled.
- Playwright v1.61 Chromium default switch list — includes `--disable-extensions`.
