"""Fiskl invoice sending workflow for VibraPilot Plugin API 1.

The workflow owns only Fiskl-specific data parsing, page verification, form
interaction and notification classification. VibraPilot Core remains the owner
of browser/task lifecycle, persistence, pause/stop controls and reporting.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$")
FISKL_HOST = "app.fiskl.com"
INVOICE_PATH_RE = re.compile(r"^/dashboard/invoices/[^/?#]+/?$")

SELECTORS: dict[str, tuple[str, ...]] = {
    "subject": (
        "#email-subject",
        "input[placeholder='Enter email subject']",
    ),
    "message": (
        "#email-message",
        "textarea[placeholder='Enter your message...']",
    ),
    "send": (
        "button[data-ee-role='save-and-send'][data-ee-group='invoice-edit']",
        "button[data-ee-role='save-and-send']",
        "button:has-text('Resend Invoice')",
    ),
    "toast": (
        "[data-sonner-toast]",
        "ol[data-sonner-toaster] > li",
    ),
}

SUCCESS_TEXT = "invoice sent successfully"
FAILURE_WORDS = (
    "error",
    "failed",
    "failure",
    "unable",
    "could not",
    "limit reached",
    "too many",
    "network",
)
TOAST_MONITOR_KEY = "__vibrapilotFisklToastState"
RESULT_PREFIX = "fiskl-v1:"


class FisklWorkflowError(RuntimeError):
    """Base class for deterministic workflow failures."""


class FisklPageNotReady(FisklWorkflowError):
    """Raised when the active page is not the required Fiskl invoice page."""


class ConfirmedSendFailure(FisklWorkflowError):
    """Raised when Fiskl explicitly reports that a send failed."""


class SendOutcomeUncertain(FisklWorkflowError):
    """Raised after a click when success/failure cannot be proven safely."""


class InvalidWorkflowData(FisklWorkflowError, ValueError):
    """Raised for invalid recipient or workflow input data."""


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_email(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or text.casefold() == "nan" or not EMAIL_RE.fullmatch(text):
        return None
    return text


def _rows_from_table(path: Path) -> tuple[list[Any], int]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = list(csv.reader(handle))
        if not rows:
            return [], 0
        header = [str(value).strip().casefold() for value in rows[0]]
        email_index = next(
            (
                index
                for index, value in enumerate(header)
                if value in {"email", "mail", "email_address", "email address"}
            ),
            0,
        )
        data_rows = (
            rows[1:]
            if any(value in {"email", "mail", "email_address", "email address"} for value in header)
            else rows
        )
        return [row[email_index] if email_index < len(row) else "" for row in data_rows], len(
            data_rows
        )

    if suffix in {".xlsx", ".xls"}:
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover - required by VibraPilot
            raise InvalidWorkflowData(
                "Spreadsheet support requires VibraPilot's pandas dependency."
            ) from exc
        frame = pd.read_excel(path)
        if frame.empty and not len(frame.columns):
            return [], 0
        lowered = {str(column).strip().casefold(): column for column in frame.columns}
        column = next(
            (
                lowered[key]
                for key in ("email", "mail", "email_address", "email address")
                if key in lowered
            ),
            frame.columns[0],
        )
        return list(frame[column]), len(frame.index)

    raise InvalidWorkflowData("Unsupported file type. Use TXT, CSV, XLSX or XLS.")


def _load_addresses(path: Path) -> tuple[list[str], int]:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        values = [re.split(r"[,;\t]", line, maxsplit=1)[0] for line in lines]
        source_rows = len(lines)
    else:
        values, source_rows = _rows_from_table(path)
    addresses = [email for value in values if (email := _valid_email(value)) is not None]
    return addresses, source_rows


def _deduplicate(addresses: Iterable[str]) -> tuple[list[str], int]:
    accepted: list[str] = []
    seen: set[str] = set()
    duplicate_count = 0
    for email in addresses:
        key = email.casefold()
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        accepted.append(email)
    return accepted, duplicate_count


def _positive_batch_size(task_values: Mapping[str, Any]) -> int:
    try:
        value = int(task_values.get("per_sending_total_email", 8))
    except (TypeError, ValueError) as exc:
        raise InvalidWorkflowData("Per Sending Total Email must be a positive integer.") from exc
    if value < 1:
        raise InvalidWorkflowData("Per Sending Total Email must be at least 1.")
    return value


def load_task_data(
    path: Path,
    task_values: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Load, validate and batch a VibraPilot recipient file."""
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise InvalidWorkflowData(f"Email list file does not exist: {source}")
    addresses, source_rows = _load_addresses(source)
    valid_rows = len(addresses)
    remove_duplicates = bool(dict(context or {}).get("remove_duplicates", False))
    duplicate_rows = 0
    if remove_duplicates:
        addresses, duplicate_rows = _deduplicate(addresses)
    if not addresses:
        raise InvalidWorkflowData("No valid email addresses were found in the selected file.")

    batch_size = _positive_batch_size(task_values)
    items: list[dict[str, Any]] = []
    for offset in range(0, len(addresses), batch_size):
        batch = addresses[offset : offset + batch_size]
        number = len(items) + 1
        items.append(
            {
                "email": ", ".join(batch),
                "name": f"Fiskl batch {number}",
                "emails_json": json.dumps(batch, separators=(",", ":")),
                "recipient_count": len(batch),
                "batch_number": number,
            }
        )

    invalid_rows = max(0, source_rows - valid_rows)
    summary = (
        f"{source.name} • {len(addresses)} recipients in {len(items)} batch(es)"
        f" • invalid {invalid_rows} • duplicates removed {duplicate_rows}"
    )
    return {
        "items": items,
        "source_fingerprint": _file_sha256(source),
        "summary": summary,
    }


def _parse_test_emails(value: Any) -> tuple[str, ...]:
    raw = str(value or "").strip()
    if not raw:
        return ()
    parts = [part.strip() for part in re.split(r"[,;\n]+", raw) if part.strip()]
    invalid = [part for part in parts if _valid_email(part) is None]
    if invalid:
        raise InvalidWorkflowData("Test Email contains one or more invalid email addresses.")
    unique, _duplicates = _deduplicate(parts)
    return tuple(unique)


class FisklInvoiceWorkflow:
    """Trusted Fiskl-specific runtime hosted by one VibraPilot Task worker."""

    session_instruction = (
        "In the opened Chrome window, sign in to Fiskl and open the invoice that should be sent. "
        "Keep that invoice page active; VibraPilot will not navigate or reload it."
    )
    blocked_task_status = "Fiskl Page Required"
    empty_batch_message = "No remaining Fiskl email batches to process."

    def __init__(self, host: Any, **_kwargs: Any) -> None:
        self.host = host
        self._total_recipients = self._calculate_total_recipients()
        self._sent_recipients = self._calculate_confirmed_recipients()
        self._failed_recipients = self._calculate_failed_recipients()
        self._test_sends = self._calculate_confirmed_test_sends()
        # This workflow's written contract forbids page/context reopening and
        # owns its own deterministic post-send delay. These are worker-local
        # settings snapshots; application/global settings are not modified.
        host.settings["re_open_after_success_per_order"] = False
        host.settings["browser_context_recycle_after_n_items"] = 0
        host.settings["browser_context_recycle_after_n_minutes"] = 0
        host.settings["delay_between_items_min"] = 0
        host.settings["delay_between_items_max"] = 0
        self._publish_metrics()

    def _task_value(self, key: str, default: Any = None) -> Any:
        return self.host.workflow_task_values.get(key, default)

    def _input_value(self, key: str, default: Any = None) -> Any:
        return self.host.workflow_input_values.get(key, default)

    def _setting_value(self, key: str, default: Any = None) -> Any:
        return self.host.workflow_settings_values.get(key, default)

    def _selector_timeout(self) -> int:
        return max(1000, int(self.host.settings.get("selector_timeout", 10000)))

    def _probe_timeout(self) -> int:
        return max(0, min(2000, int(self.host.settings.get("standard_dom_probe_timeout", 600))))

    def _max_retry(self) -> int:
        return max(0, int(self.host.settings.get("max_retry_per_item", 2)))

    def _retry_delay(self, attempt: int) -> float:
        minimum = max(0.0, float(self.host.settings.get("retry_delay_min", 1.0)))
        maximum = max(minimum, float(self.host.settings.get("retry_delay_max", 10.0)))
        multiplier = max(1.0, float(self.host.settings.get("backoff_multiplier", 2.0)))
        return min(maximum, minimum * (multiplier ** max(0, attempt - 1)))

    def _confirmation_timeout(self) -> float:
        return max(3.0, self._selector_timeout() / 1000.0)

    def _active_page(self) -> Any:
        page = getattr(self.host, "active_page", None)
        if page is None or page.is_closed():
            raise FisklPageNotReady("The active browser page is unavailable.")
        return page

    @staticmethod
    def _url_is_invoice(url: str) -> bool:
        try:
            parsed = urlparse(str(url or ""))
        except ValueError:
            return False
        return (
            parsed.scheme == "https"
            and parsed.hostname == FISKL_HOST
            and bool(INVOICE_PATH_RE.fullmatch(parsed.path))
        )

    def _page_has_controls(self, page: Any) -> bool:
        return (
            self.host.any_visible(page, list(SELECTORS["subject"]), timeout=self._probe_timeout())
            and self.host.any_visible(
                page, list(SELECTORS["message"]), timeout=self._probe_timeout()
            )
            and self.host.any_visible(page, list(SELECTORS["send"]), timeout=self._probe_timeout())
            and self._recipient_input(page, required=False) is not None
        )

    def session_ready(self, page: Any) -> bool:
        if page is None or page.is_closed() or not self._url_is_invoice(getattr(page, "url", "")):
            return False
        try:
            return self._page_has_controls(page)
        except Exception:  # noqa: BLE001 - Playwright errors are runtime-specific.
            return False

    def ensure_session(self) -> None:
        page = self._active_page()
        if self.session_ready(page):
            return
        raise FisklPageNotReady(
            "Open the intended https://app.fiskl.com/dashboard/invoices/{id} page and expand its Email section. "
            "The workflow will not reload, navigate or perform a separate login action."
        )

    def _recipient_container(self, page: Any, *, timeout: int | None = None) -> Any:
        label = page.locator("label[for='email-to']").first
        label.wait_for(
            state="visible",
            timeout=self._selector_timeout() if timeout is None else max(0, int(timeout)),
        )
        return label.locator("xpath=../..")

    def _recipient_input(self, page: Any, *, required: bool = True) -> Any | None:
        try:
            container = self._recipient_container(
                page,
                timeout=None if required else self._probe_timeout(),
            )
            locator = container.locator("input[type='text']").last
            if required:
                locator.wait_for(state="visible", timeout=self._selector_timeout())
            elif not locator.is_visible(timeout=self._probe_timeout()):
                return None
            return locator
        except Exception:  # noqa: BLE001 - Normalize locator failures at this boundary.
            if required:
                raise FisklPageNotReady(
                    "The Fiskl recipient input is not visible in the Email section."
                )
            return None

    def _recipient_chip_values(self, page: Any) -> list[str]:
        container = self._recipient_container(page)
        chips = container.locator("span[title='Double-click to edit this address']")
        values: list[str] = []
        for index in range(chips.count()):
            value = str(
                chips.nth(index).text_content(timeout=self._selector_timeout()) or ""
            ).strip()
            if value:
                values.append(value)
        return values

    def _clear_recipients(self, page: Any) -> None:
        container = self._recipient_container(page)
        for _ in range(10000):
            buttons = container.locator("button[aria-label='Remove']")
            if buttons.count() == 0:
                break
            buttons.first.click(timeout=self._selector_timeout())
            self.host.interruptible_sleep(0.05)
        else:  # pragma: no cover - defensive upper bound
            raise FisklWorkflowError("Recipient clearing exceeded its safety bound.")
        if self._recipient_chip_values(page):
            raise FisklWorkflowError("Existing Fiskl recipients could not be cleared safely.")

    def _add_recipients(self, page: Any, emails: tuple[str, ...]) -> None:
        self._clear_recipients(page)
        input_box = self._recipient_input(page)
        for email in emails:
            input_box.fill(email, timeout=self._selector_timeout())
            input_box.press("Enter", timeout=self._selector_timeout())
            deadline = time.monotonic() + max(1.0, self._probe_timeout() / 1000.0)
            while time.monotonic() < deadline:
                actual = {value.casefold() for value in self._recipient_chip_values(page)}
                if email.casefold() in actual:
                    break
                self.host.interruptible_sleep(0.05)
            else:
                raise FisklWorkflowError(
                    "Fiskl did not confirm a recipient after Enter was pressed."
                )
        actual_values = self._recipient_chip_values(page)
        if [value.casefold() for value in actual_values] != [value.casefold() for value in emails]:
            raise FisklWorkflowError(
                "The final Fiskl recipient list does not exactly match the requested batch."
            )

    def _fill_and_verify(
        self, page: Any, selectors: tuple[str, ...], value: str, label: str
    ) -> None:
        last_error: Exception | None = None
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=self._selector_timeout())
                locator.fill(value, timeout=self._selector_timeout())
                actual = str(locator.input_value(timeout=self._selector_timeout()))
                if actual != value:
                    raise FisklWorkflowError(f"{label} verification failed after filling.")
                return
            except Exception as exc:  # noqa: BLE001 - Try the next verified selector.
                last_error = exc
        raise FisklWorkflowError(f"Could not fill and verify {label}: {last_error}")

    def _visible_send_button(self, page: Any) -> Any:
        last_error: Exception | None = None
        for selector in SELECTORS["send"]:
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="visible", timeout=self._selector_timeout())
                if locator.is_enabled(timeout=self._selector_timeout()):
                    return locator
            except Exception as exc:  # noqa: BLE001 - Try the next verified selector.
                last_error = exc
        raise FisklWorkflowError(f"The enabled Resend Invoice button was not found: {last_error}")

    def _arm_toast_monitor(self, page: Any) -> int:
        state = page.evaluate(
            """
            (key) => {
              const root = window;
              const shared = root[key] || {seq: 0, events: [], seen: new WeakMap()};
              if (!shared.seen) shared.seen = new WeakMap();
              if (shared.observer) shared.observer.disconnect();
              const record = (node) => {
                if (!node || node.nodeType !== Node.ELEMENT_NODE) return;
                const candidates = [];
                if (node.matches && node.matches('[data-sonner-toast]')) candidates.push(node);
                if (node.querySelectorAll) candidates.push(...node.querySelectorAll('[data-sonner-toast]'));
                for (const toast of candidates) {
                  const text = (toast.textContent || '').replace(/\\s+/g, ' ').trim();
                  if (!text) continue;
                  const fingerprint = `${text}|${toast.getAttribute('data-mounted') || ''}|${toast.getAttribute('data-visible') || ''}|${toast.getAttribute('data-removed') || ''}`;
                  if (shared.seen.get(toast) === fingerprint) continue;
                  shared.seen.set(toast, fingerprint);
                  shared.seq += 1;
                  shared.events.push({seq: shared.seq, text});
                  if (shared.events.length > 20) shared.events.shift();
                }
              };
              shared.observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                  if (mutation.type === 'childList') {
                    for (const node of mutation.addedNodes) record(node);
                  }
                  record(mutation.target && mutation.target.nodeType === Node.ELEMENT_NODE
                    ? mutation.target.closest?.('[data-sonner-toast]') || mutation.target
                    : null);
                }
              });
              shared.observer.observe(document.documentElement, {
                subtree: true, childList: true, characterData: true, attributes: true,
                attributeFilter: ['data-mounted', 'data-visible', 'data-removed', 'class', 'style']
              });
              root[key] = shared;
              return shared.seq;
            }
            """,
            TOAST_MONITOR_KEY,
        )
        return int(state or 0)

    def _toast_events_after(self, page: Any, sequence: int) -> list[str]:
        events = page.evaluate(
            """
            ([key, sequence]) => {
              const state = window[key] || {events: []};
              return state.events.filter((event) => event.seq > sequence).map((event) => event.text || '');
            }
            """,
            [TOAST_MONITOR_KEY, int(sequence)],
        )
        return [str(value).strip() for value in (events or []) if str(value).strip()]

    def _wait_for_send_result(self, page: Any, sequence: int) -> None:
        deadline = time.monotonic() + self._confirmation_timeout()
        last_event = ""
        while time.monotonic() < deadline:
            if self.host.stop_event.is_set() or self.host.close_event.is_set():
                raise SendOutcomeUncertain(
                    "Processing stopped before the send outcome was confirmed."
                )
            self.host.wait_if_paused()
            for text in self._toast_events_after(page, sequence):
                normalized = text.casefold()
                last_event = text
                if SUCCESS_TEXT in normalized:
                    return
                if any(word in normalized for word in FAILURE_WORDS):
                    raise ConfirmedSendFailure(f"Fiskl reported: {text}")
            self.host.interruptible_sleep(0.1)
        detail = f" Last notification: {last_event}" if last_event else ""
        raise SendOutcomeUncertain(
            "Fiskl did not provide a definitive success or failure notification after Send."
            + detail
        )

    def _mark_outcome_uncertain(self, index: int, item: Any, phase: str) -> None:
        item.message = f"{phase} send click started; confirmation is pending."
        self.host.state.manual_review_required = True
        saver = getattr(self.host, "_save_runtime_item", None)
        if callable(saver):
            saver(index, item, item.message)
        progress = getattr(self.host, "_save_runtime_progress", None)
        if callable(progress):
            progress(force=True)

    def _mark_outcome_confirmed(self) -> None:
        self.host.state.manual_review_required = False
        progress = getattr(self.host, "_save_runtime_progress", None)
        if callable(progress):
            progress(force=True)

    def _send_once(self, index: int, item: Any, emails: tuple[str, ...], phase: str) -> None:
        page = self._active_page()
        if not self.session_ready(page):
            raise FisklPageNotReady(
                "The active Fiskl invoice page or Email controls are no longer ready."
            )
        subject = str(self._input_value("email_subject", ""))
        message = str(self._input_value("email_message", ""))
        if not subject.strip():
            raise InvalidWorkflowData("Email Subject is required.")
        if not message.strip():
            raise InvalidWorkflowData("Email Message is required.")
        if not emails or any(_valid_email(value) is None for value in emails):
            raise InvalidWorkflowData("The current send batch contains an invalid email address.")

        self.host.set_workflow_step(f"Preparing {phase} send ({len(emails)} recipient(s))")
        self._add_recipients(page, emails)
        self._fill_and_verify(page, SELECTORS["subject"], subject, "Email Subject")
        self._fill_and_verify(page, SELECTORS["message"], message, "Email Message")
        button = self._visible_send_button(page)
        sequence = self._arm_toast_monitor(page)
        self._mark_outcome_uncertain(index, item, phase)
        try:
            button.click(timeout=self._selector_timeout())
        except Exception as exc:
            raise SendOutcomeUncertain(
                f"The {phase} Resend Invoice click may have been dispatched, but Playwright did not confirm it."
            ) from exc
        self.host.set_workflow_step(f"Confirming {phase} send")
        self._wait_for_send_result(page, sequence)
        self._mark_outcome_confirmed()
        self.host.log(f"Fiskl confirmed the {phase} invoice send to {len(emails)} recipient(s).")

    def _send_with_retry(self, index: int, item: Any, emails: tuple[str, ...], phase: str) -> None:
        maximum = self._max_retry()
        for attempt in range(1, maximum + 2):
            if self.host.stop_event.is_set() or self.host.close_event.is_set():
                raise FisklWorkflowError("Processing was stopped before the next send.")
            self.host.wait_if_paused()
            item.attempts = max(item.attempts, attempt)
            try:
                self._send_once(index, item, emails, phase)
                return
            except SendOutcomeUncertain:
                raise
            except (InvalidWorkflowData, FisklPageNotReady):
                raise
            except ConfirmedSendFailure as exc:
                self._mark_outcome_confirmed()
                if attempt > maximum:
                    raise
                self.host.log(
                    f"Fiskl {phase} send was explicitly rejected; retry {attempt}/{maximum} scheduled: {exc}",
                    "WARNING",
                )
            except Exception as exc:
                if attempt > maximum:
                    raise ConfirmedSendFailure(
                        f"Fiskl {phase} form preparation failed after {attempt} attempt(s): {exc}"
                    ) from exc
                self.host.log(
                    f"Fiskl {phase} pre-send attempt {attempt}/{maximum + 1} failed: {exc}",
                    "WARNING",
                )
            self.prepare_retry()
            self.host.interruptible_sleep(self._retry_delay(attempt))

    @staticmethod
    def _decode_result(value: Any) -> dict[str, Any]:
        text = str(value or "")
        if not text.startswith(RESULT_PREFIX):
            return {"normal_confirmed": False, "tests_confirmed": 0}
        try:
            payload = json.loads(text[len(RESULT_PREFIX) :])
        except (TypeError, ValueError, json.JSONDecodeError):
            return {"normal_confirmed": False, "tests_confirmed": 0}
        return {
            "normal_confirmed": bool(payload.get("normal_confirmed", False)),
            "tests_confirmed": max(0, int(payload.get("tests_confirmed", 0))),
        }

    @staticmethod
    def _encode_result(*, normal_confirmed: bool, tests_confirmed: int) -> str:
        return RESULT_PREFIX + json.dumps(
            {
                "normal_confirmed": bool(normal_confirmed),
                "tests_confirmed": max(0, int(tests_confirmed)),
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    def _payload_at(self, index: int) -> dict[str, Any]:
        payloads = getattr(self.host, "workflow_item_payloads", ())
        if 0 <= index < len(payloads):
            return dict(payloads[index])
        items = getattr(self.host.state, "items", ())
        if 0 <= index < len(items):
            emails = [
                part.strip()
                for part in str(getattr(items[index], "email", "")).split(",")
                if part.strip()
            ]
            if emails:
                return {
                    "email": ", ".join(emails),
                    "emails_json": json.dumps(emails, separators=(",", ":")),
                    "recipient_count": len(emails),
                    "batch_number": index + 1,
                }
        raise InvalidWorkflowData("The current Task payload is unavailable.")

    def _emails_at(self, index: int) -> tuple[str, ...]:
        payload = self._payload_at(index)
        try:
            values = json.loads(str(payload.get("emails_json", "[]")))
        except json.JSONDecodeError as exc:
            raise InvalidWorkflowData("The current Task recipient batch is corrupt.") from exc
        if not isinstance(values, list):
            raise InvalidWorkflowData("The current Task recipient batch is invalid.")
        emails = tuple(str(value).strip() for value in values)
        if not emails or any(_valid_email(value) is None for value in emails):
            raise InvalidWorkflowData("The current Task recipient batch contains invalid data.")
        return emails

    def _recipients_before_index(self, index: int) -> int:
        items = getattr(self.host.state, "items", ())
        total = 0
        for position in range(min(max(0, index), len(items))):
            result = self._decode_result(getattr(items[position], "result", ""))
            if result["normal_confirmed"]:
                total += max(0, int(self._payload_at(position).get("recipient_count", 0)))
        return total

    def _calculate_total_recipients(self) -> int:
        items = getattr(self.host.state, "items", ())
        return sum(
            max(0, int(self._payload_at(index).get("recipient_count", 0)))
            for index in range(len(items))
        )

    def _calculate_confirmed_recipients(self) -> int:
        items = getattr(self.host.state, "items", ())
        return sum(
            max(0, int(self._payload_at(index).get("recipient_count", 0)))
            for index, item in enumerate(items)
            if self._decode_result(getattr(item, "result", ""))["normal_confirmed"]
        )

    def _calculate_failed_recipients(self) -> int:
        items = getattr(self.host.state, "items", ())
        return sum(
            max(0, int(self._payload_at(index).get("recipient_count", 0)))
            for index, item in enumerate(items)
            if getattr(item, "status", "") == "failed"
            and not self._decode_result(getattr(item, "result", ""))["normal_confirmed"]
        )

    def _tests_due_for_index(self, index: int) -> int:
        try:
            interval = int(self._setting_value("after_send_test_email", 0))
        except (TypeError, ValueError) as exc:
            raise InvalidWorkflowData(
                "After Send Test Email must be a non-negative integer."
            ) from exc
        test_emails = _parse_test_emails(self._setting_value("test_emails", ""))
        if interval < 0:
            raise InvalidWorkflowData("After Send Test Email must be a non-negative integer.")
        if interval == 0 or not test_emails:
            return 0
        before = self._recipients_before_index(index)
        after = before + len(self._emails_at(index))
        return max(0, (after // interval) - (before // interval))

    def _calculate_confirmed_test_sends(self) -> int:
        items = getattr(self.host.state, "items", ())
        return sum(
            self._decode_result(getattr(item, "result", ""))["tests_confirmed"] for item in items
        )

    def _publish_metrics(self) -> None:
        self.host.set_workflow_metric("total_recipients", self._total_recipients)
        self.host.set_workflow_metric("sent_recipients", self._sent_recipients)
        self.host.set_workflow_metric("failed_recipients", self._failed_recipients)
        self.host.set_workflow_metric(
            "remaining_recipients",
            max(0, self._total_recipients - self._sent_recipients - self._failed_recipients),
        )
        self.host.set_workflow_metric("test_sends", self._test_sends)

    def _persist_phase_result(self, index: int, item: Any) -> None:
        saver = getattr(self.host, "_save_runtime_item", None)
        if callable(saver):
            saver(index, item, item.message)
        progress = getattr(self.host, "_save_runtime_progress", None)
        if callable(progress):
            progress(force=True)

    def _delay_after_send(self) -> None:
        try:
            delay = max(0, int(self._task_value("sending_delay", 0)))
        except (TypeError, ValueError) as exc:
            raise InvalidWorkflowData("Sending Delay must be a non-negative integer.") from exc
        if delay:
            self.host.set_workflow_step(f"Waiting {delay} second(s) before the next send")
            self.host.interruptible_sleep(delay)

    def process_item(self, index: int, item: Any) -> None:
        """Execute one persisted recipient batch with restart-safe test-send phases."""
        item.status = "processing"
        item.message = "Fiskl invoice batch processing started"
        emails: tuple[str, ...] = ()
        result = self._decode_result(getattr(item, "result", ""))
        tests_due = 0
        try:
            emails = self._emails_at(index)
            tests_due = self._tests_due_for_index(index)
            test_emails = _parse_test_emails(self._setting_value("test_emails", ""))
            self._total_recipients = self._calculate_total_recipients()
            if not result["normal_confirmed"]:
                self._send_with_retry(index, item, emails, "normal")
                result["normal_confirmed"] = True
                item.result = self._encode_result(
                    normal_confirmed=True,
                    tests_confirmed=result["tests_confirmed"],
                )
                item.message = f"Normal send confirmed for {len(emails)} recipient(s)"
                self._sent_recipients += len(emails)
                self._publish_metrics()
                self._persist_phase_result(index, item)
                if tests_due or index + 1 < len(getattr(self.host.state, "items", ())):
                    self._delay_after_send()

            while result["tests_confirmed"] < tests_due:
                ordinal = result["tests_confirmed"] + 1
                self._send_with_retry(index, item, test_emails, f"test {ordinal}/{tests_due}")
                result["tests_confirmed"] = ordinal
                self._test_sends += 1
                item.result = self._encode_result(
                    normal_confirmed=True,
                    tests_confirmed=result["tests_confirmed"],
                )
                item.message = f"Periodic test send {ordinal}/{tests_due} confirmed"
                self._publish_metrics()
                self._persist_phase_result(index, item)
                if result["tests_confirmed"] < tests_due or index + 1 < len(
                    getattr(self.host.state, "items", ())
                ):
                    self._delay_after_send()

            item.status = "success"
            item.message = f"Fiskl invoice sent to {len(emails)} recipient(s)" + (
                f" with {tests_due} periodic test send(s)" if tests_due else ""
            )
            self.host.state.manual_review_required = False
            self.host.state.success_count += 1
            self.host.set_workflow_step("Batch confirmed")
        except SendOutcomeUncertain as exc:
            item.status = "interrupted"
            item.message = f"Manual review required: {exc}"
            self.host.state.manual_review_required = True
            self.host.set_workflow_step("Manual review required")
            self.host.log(item.message, "ERROR")
        except FisklPageNotReady as exc:
            item.status = "blocked"
            item.message = str(exc)
            self.host.state.manual_review_required = False
            self.host.set_workflow_step("Fiskl page unavailable")
            self.host.log(item.message, "ERROR")
        except (InvalidWorkflowData, ConfirmedSendFailure, FisklWorkflowError) as exc:
            item.status = "failed"
            item.message = str(exc)
            self.host.state.manual_review_required = False
            self.host.state.failed_count += 1
            if not result["normal_confirmed"]:
                self._failed_recipients += len(emails)
            self._publish_metrics()
            self.host.set_workflow_step("Batch failed")
            self.host.log(item.message, "ERROR")
        except Exception as exc:  # noqa: BLE001 - Final fail-closed runtime boundary.
            item.status = "failed"
            item.message = f"Unexpected Fiskl workflow failure: {type(exc).__name__}: {exc}"
            self.host.state.manual_review_required = False
            self.host.state.failed_count += 1
            if not result["normal_confirmed"]:
                self._failed_recipients += len(emails)
            self._publish_metrics()
            self.host.set_workflow_step("Batch failed")
            self.host.log(item.message, "ERROR")

    def execute_item(self, item: Any) -> str:
        """Protocol adapter; specialized orchestration is owned by process_item."""
        index = max(0, int(self.host.state.current_index))
        self._send_once(index, item, self._emails_at(index), "normal")
        return "Fiskl invoice send confirmed"

    def prepare_retry(self) -> None:
        """Restore only the Fiskl form; never reload, navigate or reopen the page."""
        page = self._active_page()
        if not self.session_ready(page):
            raise FisklPageNotReady(
                "The active Fiskl invoice page is unavailable during retry recovery."
            )
        self._clear_recipients(page)

    def error_decision(self, exc: Exception) -> str:
        if isinstance(exc, SendOutcomeUncertain):
            return "MANUAL_REVIEW"
        if isinstance(exc, FisklPageNotReady):
            return "STOP_TASK"
        if isinstance(exc, InvalidWorkflowData):
            return "FAIL_ITEM"
        if isinstance(exc, ConfirmedSendFailure):
            return "RETRY"
        return "FAIL_ITEM"


def create_workflow(host: Any, **kwargs: Any) -> FisklInvoiceWorkflow:
    return FisklInvoiceWorkflow(host, **kwargs)
