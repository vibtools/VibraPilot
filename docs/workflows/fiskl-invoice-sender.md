# Fiskl Invoice Sender Workflow

## Scope and architecture

Fiskl Invoice Sender is a standalone trusted Plugin API 1 package. It adds no Core module, UI page, API, dependency, persistence schema or browser technology. VibraPilot Core continues to own browser and Task lifecycle, pause/stop behavior, worker isolation, recovery storage, reports and logs. The workflow owns only recipient parsing and batching, Fiskl page readiness, form interaction, notification classification and workflow metrics.

## Installation

Load `Fiskl_Invoice_Sender_v1.0.0.vpworkflow` from the existing **Workflows** page. Review the manifest, version and SHA-256 before approving installation. Set the installed workflow as the default only if new Tasks should use it automatically; existing Tasks retain their immutable workflow identity.

## Configuration

### Workflow Inputs

- **Email Subject:** required subject used for normal and periodic test sends.
- **Email Message:** required message used for normal and periodic test sends.

### Workflow Settings

- **Test Email:** optional comma/semicolon/newline-separated addresses. Multiple test addresses are sent together in one periodic test operation.
- **After Send Test Email:** number of confirmed normal recipients per periodic test operation. `0` or an empty Test Email value disables test sends. If one normal batch crosses multiple intervals, the corresponding number of persisted test phases is run without replaying the confirmed normal batch.

### Task Settings

- **Email List:** required TXT, CSV, XLSX or XLS source.
- **Target URL:** informational compatibility value. `#` and blank values are accepted; runtime always uses the active page.
- **Sending Delay:** non-negative seconds between confirmed send operations.
- **Per Sending Total Email:** positive maximum number of normal recipients per send operation.

## Execution flow

1. The operator configures Workflow Inputs/Settings, creates the Task and loads the recipient file.
2. The operator opens the managed browser and manually signs in to Fiskl.
3. The operator creates or opens the intended dynamic `/dashboard/invoices/{id}` page and expands Email.
4. The workflow verifies HTTPS host, dynamic invoice path, recipient input, subject, message and enabled Resend Invoice button.
5. Existing recipient chips are removed, then each batch address is entered and verified individually.
6. Subject and message are filled and read back exactly.
7. A transient notification observer and durable uncertain-outcome checkpoint are armed before the click.
8. `Invoice sent successfully` confirms the phase. Explicit failure notifications may retry. Missing confirmation after a dispatched click requires manual review.
9. Confirmed recipients and optional test phases are persisted before the next operation.

No workflow path calls page navigation, reload, browser close or browser reopen.

## Plugin API surface

- `create_workflow(host, **kwargs)` creates the trusted runtime.
- `load_task_data(path, task_values, context)` validates, optionally deduplicates and batches recipient data.
- Runtime protocol: `session_ready`, `ensure_session`, `execute_item`, `prepare_retry`.
- Optional runtime hooks used: `process_item`, `error_decision`.
- Core host services used: active page, pause/stop events, worker-local settings snapshot, logging, workflow metrics and durable runtime progress callbacks.

## Troubleshooting

- **Fiskl Page Required:** keep the intended `https://app.fiskl.com/dashboard/invoices/{id}` tab active and expand Email. The workflow intentionally will not navigate for you.
- **Recipient input is not visible:** expand the Fiskl Email panel and confirm the invoice page is fully loaded.
- **Manual review required:** verify in Fiskl History and the recipient mailbox whether the last click sent the invoice. Resume only after choosing the appropriate existing recovery action; the workflow will not automatically replay an uncertain click.
- **Explicit failure retries exhausted:** inspect the Task log for the Fiskl notification, network condition or sending limit and restart the remaining Task items after the site is available.
- **No valid addresses:** use TXT lines or a CSV/spreadsheet email column containing syntactically valid addresses.

## Forensic source notes

The supplied reference ZIP contained documentation, a full saved DOM, a logo and two screenshots, with no executable code. The DOM also contained one personal email address and an expiring signed object-storage URL. Neither value nor the captured invoice/customer data is copied into the production package or repository source.
