# Fiskl Reference and Workflow Forensic Audit

## Executive result

The supplied `Fiskl.zip` is a six-entry reference archive containing one workflow specification, one saved HTML DOM, one logo and two screenshots. It contains no executable source. The evidence is sufficient to implement a standalone VibraPilot Plugin API 1 workflow without changing VibraPilot Core. The completed package is `Fiskl_Invoice_Sender_v1.0.0.vpworkflow`, SHA-256 `1a7ce3a3cad954bc28fec2410c0094a8356e533310dfbb92fc64c83bd6686f3d`.

Live authenticated invoice delivery was not executed during this audit because no Fiskl account/session or authorization to send a real invoice was supplied. Package/schema/install behavior and all repository regressions were verified locally; owner-controlled Windows/Fiskl acceptance remains the final external-service gate.

## Evidence integrity

| Evidence | Result |
| --- | --- |
| `Fiskl.zip` | 319,588 bytes; SHA-256 `6f26f1439185fa2a2a3e3ee9d358b96196506829b08485e668ba3fbcb7308935` |
| Archive safety | 6 entries; 623,110 uncompressed bytes; no absolute/traversal paths; compression ratio 1.96 |
| `WORKFLOW.md` | SHA-256 `43b7cac3e163cbf4aeb48cfa5b60fb6c492067dab9b67f8339c9082c95cb6565` |
| `DOM.html` | SHA-256 `54557859575f1a9a08290dbdce26c7f81c7c21f35d6f244820603dd96e4e341f` |
| Target screenshot | SHA-256 `2e6e55f1bebfca7a2dbbebd74635ffcd75b7c18cbb1666dc09b4f29eec0dcd34` |
| Success screenshot | SHA-256 `e2dda437f9ced09b0f34cdedafe16dba0fb842215c5bf76d0128a9633d6143ca` |

The supplied VibraPilot baseline and GitHub `main` both resolve to signed merge commit `315e089fd60dfa6f0b5263834260cf7071bbd971` and tag `v1.0.6.44`. The uploaded local checkout contained pre-existing modifications to `LICENSE`, `NOTICE` and three maintenance/start scripts. Those files were treated as user-owned evidence and were not used or overwritten; the workflow candidate was created from a clean clone of the exact commit.

## Findings and closure

### FISKL-01: captured sensitive data in saved DOM, medium

The DOM contains a personal recipient address, invoice/customer details, a payment link and an expiring AWS S3 pre-signed asset URL containing credential/signature query material. Even after expiry, this capture should not be published or packaged.

Closure: no DOM, screenshot, invoice/customer value, personal email or signed URL is included in workflow source or the installable package. A regression test scans text package sources for the identified sensitive markers.

### FISKL-02: recipient selector drift between specification and captured state, medium

The specification shows `placeholder="Enter recipient email addresses"`; the captured DOM shows an empty placeholder after a recipient chip exists. A placeholder-only selector would fail during repeat batches.

Closure: recipient discovery is anchored to `label[for='email-to']` and the local field container, independent of placeholder state. Existing chips are removed and verified empty before every batch.

### FISKL-03: transient success notification creates duplicate-send risk, high

The success toast is short-lived. A normal wait that begins after clicking can miss it and retry a successful invoice.

Closure: a DOM `MutationObserver` is armed before the click and retains new toast events after their nodes disappear. Only text containing `Invoice sent successfully` confirms success.

### FISKL-04: post-click timeout is not safe to retry automatically, critical

When the click may have reached Fiskl but no result is observed, replay could send the same invoice twice.

Closure: workflow state is marked manual-review-required and durably checkpointed before Playwright invokes the button click. A missing or ambiguous result after dispatch stops automatic replay. Confirmed test-send phase markers also prevent replay of an already confirmed normal batch after restart.

### FISKL-05: invoice URL is account/invoice-specific, high

The captured `/dashboard/invoices/350821` value cannot be a production target.

Closure: there is no fixed target URL. Session readiness accepts only HTTPS `app.fiskl.com` pages matching dynamic `/dashboard/invoices/{id}` and requires the live Email controls. The workflow never navigates or reloads the page.

### FISKL-06: stale recipient/form state can alter the intended send, high

Prior recipients or stale subject/message values could make a successful operation semantically wrong.

Closure: all previous chips are removed, each new address is individually confirmed, the final batch is compared exactly and subject/message values are read back before the send control is resolved.

### FISKL-07: normal and periodic test sends need separate crash-safe phases, high

A test send performed after a normal batch creates two external effects inside one Task item. A crash between them could otherwise replay the normal batch.

Closure: the item result stores `normal_confirmed` and the number of confirmed test phases. Recovery resumes only the missing phase. Test operations are scheduled from confirmed normal-recipient interval crossings.

## Implementation boundary

- Added standalone `workflows/fiskl_invoice_sender/` source only.
- Added no `src/vibrapilot` production change.
- Added no library/framework/dependency.
- Added no UI, UX, API, persistence, licensing, browser-profile or GitHub Actions change.
- Used the existing Plugin API 1 declarative forms, runtime host, Task persistence, workflow metrics and lifecycle management.
- Disabled context recycling, per-item reopening and Core item delay only inside the Fiskl worker-local settings snapshot so the no-reload/no-reopen requirement remains workflow-scoped.

## Verification record

| Check | Result |
| --- | --- |
| Python warning-as-error compilation | Pass |
| Workflow targeted tests | 12 passed |
| Full repository pytest | 565 passed, 6 skipped, 105 subtests passed |
| Repository invariant verifier | Pass, 8/8 stages |
| Git whitespace/error check | Pass |
| Plugin API inspection | Pass |
| Atomic temporary installation | Pass |
| Runtime factory and task data loader resolution | Pass |
| Archive members/path/symlink/size validation | Pass |
| Sensitive reference marker exclusion | Pass |

The six skipped tests are existing environment/platform skips and are unrelated to the Fiskl workflow.

## Owner acceptance checklist

1. Install the package whose SHA-256 matches this report.
2. Configure and load a non-production recipient list before opening the Task browser.
3. Sign in manually, open a test invoice, expand Email and verify `Fiskl Page` becomes verified.
4. Test one normal batch with `Per Sending Total Email = 1` and confirm exactly one recipient in Fiskl History and the mailbox.
5. Test a two-batch run and confirm old recipient chips are removed between batches without page reload.
6. Configure one test email and a small interval; confirm test phases and workflow metrics.
7. Simulate a confirmed Fiskl rejection and verify bounded retry.
8. Interrupt the page/network immediately after clicking; verify Manual Review Required and no automatic replay.
9. Minimize/hide the Chrome window and verify processing continues while the system remains awake under existing Core behavior.

Do not use production recipients until these owner-controlled acceptance checks pass against the current Fiskl deployment.
