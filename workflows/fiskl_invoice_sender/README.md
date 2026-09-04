# Fiskl Invoice Sender v1.0.0

Trusted VibraPilot Plugin API 1 workflow for sending the currently open Fiskl invoice to an uploaded email list in configurable recipient batches.

## Install

1. Build `Fiskl_Invoice_Sender_v1.0.0.vpworkflow` from this directory or use the verified artifact supplied with the release.
2. In VibraPilot, open **Workflows**, choose **Load Workflow**, inspect the package summary and approve the trusted Python workflow.
3. Set it as the default for newly created Tasks or select it when creating a Task.

Workflow Python executes with VibraPilot's process permissions. Install only the artifact whose SHA-256 matches the verified release value.

## Configure

- **Workflow Inputs:** Email Subject and Email Message.
- **Workflow Settings:** optional comma-separated Test Email addresses and the confirmed-recipient interval for periodic test sends. Set the interval to `0` to disable.
- **Task Settings:** Email List, informational Target URL, Sending Delay and Per Sending Total Email.

## Run

Configure the workflow, create the Task and load the recipient file first. Then open the Task browser, sign in to Fiskl manually, create or open the intended invoice, expand **Email** and start the Task. The workflow uses that active page. It does not navigate, reload, close or reopen the page.

The accepted recipient formats are TXT, CSV, XLSX and XLS. CSV/spreadsheet data may use `email`, `mail`, `email_address` or `email address`; otherwise the first column is used.

## Safety

- Recipients, subject and message are verified before every click.
- A pre-click checkpoint prevents automatic replay when the send outcome is uncertain.
- Confirmed Fiskl failures may retry using VibraPilot's existing retry/backoff settings.
- A transient Sonner toast observer captures `Invoice sent successfully` even when the notification disappears quickly.
- Context recycling and per-item page reopening are disabled only in this workflow's worker-local settings snapshot.
- The supplied DOM capture, signed URLs, invoice data and example personal email are not included in the package.
