"""Verified Share Invite workflow extracted from ``AutomationWorker`` in PR-04.

The workflow deliberately depends on the existing worker for browser primitives,
state, persistence callbacks, pause/stop events, and logging. It owns only the
Share Invite-specific selectors/session checks/modal/send/result logic that was
previously embedded in ``backend.AutomationWorker``.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from ..contracts import WorkflowManifest
from . import SHARE_INVITE_MANIFEST


SHARE_INVITE_SELECTORS: dict[str, list[str]] = {
    "test_mode_banner": [
        "[data-testid='test-mode-banner']",
        ".highlight-test-mode-container [data-testid='test-mode-banner']",
        ".highlight-test-mode-container .trapezoid",
    ],
    "share_button": [
        "button.Button--small.Button--primary.Button:has(i.i-share-outline)",
        "button:has(i.i-share-outline):has-text('Share')",
        "button.Button--primary:has-text('Share')",
        "button:has-text('Share')",
    ],
    "share_modal_title": [
        "div.modal-header h3.modal-title:has-text('Share Link')",
        "h3.modal-title:has-text('Share Link')",
        "text=Share Link",
    ],
    "share_modal_close": [
        "button[data-testid='modal-header-close-btn']",
        "div.modal-header button.close",
    ],
    "share_email": [
        "form.Form.Share-section input[name='email'][type='email'][placeholder='Email']",
        "input[name='email'][type='email'][placeholder='Email']",
        "input[name='email'][type='email']",
    ],
    "share_send": [
        "form.Form.Share-section button[type='submit']:has-text('Send')",
        "button.Button--Link.Button--transparent.Button[type='submit']:has-text('Send')",
        "button[type='submit']:has(b:has-text('Send'))",
        "button[type='submit']:has-text('Send')",
    ],
    "invite_success": [
        "div.Notification.Notification--success[data-testid='Notification--success']",
        "[data-testid='Notification--success']",
        ".Notification--success",
    ],
    "invite_error": [
        "[data-testid='Notification--error']",
        ".Notification--error",
        ".Notification--danger",
        ".Notification--warning",
        ".errorMessage",
        ".validation-error",
    ],
}

SHARE_INVITE_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class ShareInviteRuntimeErrors:
    """References to the existing backend exception classes; no replacement types."""

    security_challenge: type[Exception]
    session_verification_error: type[Exception]
    test_mode_required: type[Exception]
    test_send_limit_reached: type[Exception]
    invite_rejected: type[Exception]


class ShareInviteWorkflow:
    """The first source-controlled built-in VibraPilot workflow."""

    manifest: WorkflowManifest = SHARE_INVITE_MANIFEST

    def __init__(
        self,
        host: Any,
        *,
        default_settings: dict[str, Any],
        errors: ShareInviteRuntimeErrors,
    ) -> None:
        self.host = host
        self.default_settings = default_settings
        self.errors = errors

    def _setting(self, key: str) -> Any:
        return self.host.settings.get(key, self.default_settings[key])

    def test_mode_banner_ready(self, page) -> bool:
        if not page or page.is_closed():
            return False
        if not self.host.any_visible(
            page,
            SHARE_INVITE_SELECTORS["test_mode_banner"],
            timeout=max(0, int(self._setting("short_dom_probe_timeout"))),
        ):
            return False
        text = self.host.first_visible_text(
            page, SHARE_INVITE_SELECTORS["test_mode_banner"]
        ).upper()
        return "TEST MODE" in text

    def authenticated_test_session_ready(self, page) -> bool:
        return bool(
            page
            and not page.is_closed()
            and self.test_mode_banner_ready(page)
            and self.share_button_ready(page)
        )

    def wait_for_authenticated_test_session(self) -> bool:
        max_retry = max(0, int(self._setting("max_selector_retry")))
        for attempt in range(max_retry + 1):
            self.host.detect_security(self.host.active_page)
            if self.authenticated_test_session_ready(self.host.active_page):
                self.host.login_verified_event.set()
                self.host.emit(
                    "login",
                    {
                        "verified": True,
                        "message": "Authenticated Test Mode page verified.",
                    },
                )
                return True
            if attempt < max_retry:
                self.host.log(
                    f"Login/Test Mode verification retry {attempt + 1}/{max_retry}.",
                    "WARNING",
                )
                self.host.interruptible_sleep(
                    max(0.2, float(self._setting("retry_delay_min")))
                )
        return False

    def ensure_authenticated_test_session(self) -> None:
        if self.authenticated_test_session_ready(self.host.active_page):
            self.host.login_verified_event.set()
            self.host.emit(
                "login",
                {"verified": True, "message": "Authenticated Test Mode page verified."},
            )
            return

        self.host.log(
            "Authenticated Test Mode page was not detected on the current tab; opening the configured Target URL.",
            "WARNING",
        )
        self.host.safe_goto(self.host.active_page, self.host.state.target_url)
        if self.wait_for_authenticated_test_session():
            return

        self.host.login_verified_event.clear()
        if not self.test_mode_banner_ready(self.host.active_page):
            raise self.errors.session_verification_error(
                "Automation blocked: the Test Mode banner was not detected. Complete login and open the Target URL in Test Mode."
            )
        raise self.errors.session_verification_error(
            "Automation blocked: login could not be verified because the authenticated Share page was not detected."
        )

    def assert_test_mode(self, page) -> None:
        if self.test_mode_banner_ready(page):
            return
        self.host.login_verified_event.clear()
        self.host.emit(
            "login",
            {
                "verified": False,
                "message": "Automation blocked because the Test Mode banner disappeared or was not detected.",
            },
        )
        raise self.errors.test_mode_required(
            "Automation blocked: Test Mode banner is required before every Send operation."
        )

    def execute_flow(self, item: Any) -> str:
        email = item.email.strip()
        if not email or not SHARE_INVITE_EMAIL_RE.fullmatch(email):
            raise ValueError(
                "Invite email is blank or invalid; submission was blocked."
            )
        if self.host.stop_event.is_set() or self.host.close_event.is_set():
            raise RuntimeError("Processing was stopped.")

        page = self.host.active_page
        self.host.wait_if_paused()
        self.assert_test_mode(page)
        self.ensure_share_entry(page)
        self.open_share_modal(page)
        self.fill_invite_email(page, email)
        notification_state = self.arm_invite_notification_monitor(page)
        self.submit_share_invite(page, email, notification_state)
        return f"{page.url} | invite=sent"

    def session_ready(self, page: Any) -> bool:
        """Generic PR-05 session gate adapter; Share Invite semantics are unchanged."""
        return self.authenticated_test_session_ready(page)

    def ensure_session(self) -> None:
        """Generic PR-05 session enforcement adapter."""
        self.ensure_authenticated_test_session()

    def execute_item(self, item: Any) -> str:
        """Generic PR-05 item execution adapter."""
        return self.execute_flow(item)

    def prepare_retry(self) -> None:
        """Generic PR-05 pre-Send retry adapter."""
        self.prepare_invite_retry()

    def ensure_share_entry(self, page) -> None:
        """Use the pre-opened authenticated Test Mode page first; fail closed otherwise."""
        if self.authenticated_test_session_ready(page):
            self.host.login_verified_event.set()
            return
        self.host.log(
            "Authenticated Share page was not found on the current tab; opening the configured Target URL.",
            "WARNING",
        )
        self.host.safe_goto(page, self.host.state.target_url)
        if not self.wait_for_authenticated_test_session():
            if not self.test_mode_banner_ready(page):
                raise self.errors.test_mode_required(
                    "Automation blocked: Test Mode banner was not detected after opening the Target URL."
                )
            raise self.errors.session_verification_error(
                "Automation blocked: authenticated Share page was not detected after login verification retries."
            )

    def share_button_ready(self, page) -> bool:
        return self.host.any_visible(
            page,
            SHARE_INVITE_SELECTORS["share_button"],
            timeout=max(0, int(self._setting("standard_dom_probe_timeout"))),
        )

    def wait_for_share_button(self, page) -> bool:
        max_retry = max(0, int(self._setting("max_selector_retry")))
        for attempt in range(max_retry + 1):
            self.host.detect_security(page)
            if self.share_button_ready(page):
                return True
            if attempt < max_retry:
                self.host.log(
                    f"Share button lookup retry {attempt + 1}/{max_retry}.", "WARNING"
                )
                try:
                    self.host.safe_goto(page, self.host.state.target_url)
                except Exception as exc:
                    self.host.log(f"Target URL retry failed: {exc}", "WARNING")
                self.host.interruptible_sleep(
                    max(0.0, float(self._setting("network_error_retry_delay")))
                )
        return False

    def share_modal_ready(self, page) -> bool:
        required_groups = (
            SHARE_INVITE_SELECTORS["share_modal_title"],
            SHARE_INVITE_SELECTORS["share_email"],
            SHARE_INVITE_SELECTORS["share_send"],
        )
        return all(
            self.host.any_visible(
                page,
                selectors,
                timeout=max(0, int(self._setting("standard_dom_probe_timeout"))),
            )
            for selectors in required_groups
        )

    def close_existing_share_modal(self, page) -> None:
        if not self.host.any_visible(
            page,
            SHARE_INVITE_SELECTORS["share_modal_title"],
            timeout=max(0, int(self._setting("modal_state_probe_timeout"))),
        ):
            return
        try:
            self.host.click_first(
                page,
                SHARE_INVITE_SELECTORS["share_modal_close"],
                "Share modal close",
            )
            for _ in range(max(0, int(self._setting("modal_close_poll_count")))):
                if not self.host.any_visible(
                    page,
                    SHARE_INVITE_SELECTORS["share_modal_title"],
                    timeout=max(0, int(self._setting("modal_close_probe_timeout"))),
                ):
                    return
                self.host.interruptible_sleep(
                    max(0.0, float(self._setting("modal_close_poll_interval")))
                )
        except Exception as exc:
            self.host.log(
                f"Existing Share modal could not be closed cleanly: {exc}", "WARNING"
            )

    def open_share_modal(self, page) -> None:
        self.close_existing_share_modal(page)
        self.ensure_share_entry(page)
        self.host.click_first(page, SHARE_INVITE_SELECTORS["share_button"], "Share")

        max_retry = max(0, int(self._setting("max_selector_retry")))
        for attempt in range(max_retry + 1):
            self.host.detect_security(page)
            if self.share_modal_ready(page):
                self.host.log(
                    "Share Link modal opened and all required controls were detected."
                )
                return
            if attempt < max_retry:
                self.host.log(
                    f"Share modal validation retry {attempt + 1}/{max_retry}.",
                    "WARNING",
                )
                self.host.interruptible_sleep(
                    max(0.1, float(self._setting("retry_delay_min")))
                )
        raise RuntimeError(
            "Share Link modal did not expose its title, email input, and Send button."
        )

    def prepare_invite_retry(self) -> None:
        """Return the page to a deterministic state without reloading after a confirmed success."""
        if (
            self.host.stop_event.is_set()
            or self.host.close_event.is_set()
            or not self.host.active_page
        ):
            return
        try:
            self.close_existing_share_modal(self.host.active_page)
        except Exception:
            pass
        if not self.share_button_ready(self.host.active_page):
            try:
                self.host.safe_goto(self.host.active_page, self.host.state.target_url)
            except Exception as exc:
                self.host.log(f"Invite retry recovery navigation failed: {exc}", "WARNING")

    def fill_invite_email(self, page, email: str) -> None:
        """Fill and verify the exact email value so blank or stale submissions cannot proceed."""
        if not email or not SHARE_INVITE_EMAIL_RE.fullmatch(email):
            raise ValueError(
                "Invite email is blank or invalid; submission was blocked."
            )
        self.host.fill_first(
            page, SHARE_INVITE_SELECTORS["share_email"], "", "Clear invite email"
        )
        self.host.fill_first(
            page, SHARE_INVITE_SELECTORS["share_email"], email, "Invite email"
        )
        actual = self.input_value_first(
            page, SHARE_INVITE_SELECTORS["share_email"], "Invite email"
        ).strip()
        if not actual or actual.casefold() != email.casefold():
            raise RuntimeError(
                f"Invite email verification failed before Send. Expected '{email}', found '{actual or '<blank>'}'."
            )

    def input_value_first(self, page, selectors: list[str], label: str) -> str:
        last_error = None
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                locator.wait_for(
                    state="visible",
                    timeout=max(1000, int(self._setting("selector_timeout"))),
                )
                return str(
                    locator.input_value(
                        timeout=max(1000, int(self._setting("selector_timeout")))
                    )
                )
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"Could not read {label}: {last_error}")

    def arm_invite_notification_monitor(self, page) -> dict[str, Any]:
        """Track a new success transition so a stale success node cannot confirm the next email."""
        try:
            state = page.evaluate(
                """
                () => {
                    const selector = '[data-testid="Notification--success"]';
                    const isShown = (el) => !!el && (
                        el.classList.contains('Notification__show') ||
                        (getComputedStyle(el).display !== 'none' &&
                         getComputedStyle(el).visibility !== 'hidden' &&
                         Number(getComputedStyle(el).opacity || '1') > 0)
                    );
                    if (!window.__testerInviteNotificationState) {
                        window.__testerInviteNotificationState = {seq: 0, shown: false, text: ''};
                    }
                    const current = document.querySelector(selector);
                    const shared = window.__testerInviteNotificationState;
                    shared.shown = isShown(current);
                    shared.text = current ? (current.textContent || '').trim() : '';
                    if (window.__testerInviteNotificationObserver) {
                        window.__testerInviteNotificationObserver.disconnect();
                    }
                    window.__testerInviteNotificationObserver = new MutationObserver(() => {
                        const el = document.querySelector(selector);
                        const shown = isShown(el);
                        const text = el ? (el.textContent || '').trim() : '';
                        if (shown && (!shared.shown || text !== shared.text)) {
                            shared.seq += 1;
                        }
                        shared.shown = shown;
                        shared.text = text;
                    });
                    window.__testerInviteNotificationObserver.observe(document.documentElement, {
                        subtree: true,
                        childList: true,
                        characterData: true,
                        attributes: true,
                        attributeFilter: ['class', 'style']
                    });
                    return {seq: shared.seq, shown: shared.shown, text: shared.text};
                }
                """
            )
            if isinstance(state, dict):
                return state
        except Exception as exc:
            self.host.log(
                f"Success notification monitor fallback enabled: {exc}", "WARNING"
            )
        return {"seq": 0, "shown": False, "text": ""}

    def submit_share_invite(
        self, page, email: str, notification_state: dict[str, Any]
    ) -> None:
        self.host.detect_security(page)
        self.assert_test_mode(page)
        actual = self.input_value_first(
            page, SHARE_INVITE_SELECTORS["share_email"], "Invite email"
        ).strip()
        if not actual or actual.casefold() != email.casefold():
            raise RuntimeError(
                "Blank or mismatched invite submission was blocked immediately before Send."
            )
        if self.host.run_send_count >= self.host.run_send_limit:
            raise self.errors.test_send_limit_reached(
                f"Maximum Test Mode send limit reached ({self.host.run_send_limit} Send clicks for this run)."
            )
        self.host.click_first(
            page,
            SHARE_INVITE_SELECTORS["share_send"],
            "Send invite",
            before_click=self.host._register_send_click_attempt,
        )
        self.wait_invite_result(page, notification_state)
        self.host.log(
            "Invite was confirmed by a new success notification; continuing without page reload."
        )

    def wait_invite_result(self, page, notification_state: dict[str, Any]) -> None:
        timeout_ms = max(1000, int(self._setting("selector_timeout")))
        deadline = time.monotonic() + (timeout_ms / 1000.0)
        start_seq = int(notification_state.get("seq", 0))
        was_shown = bool(notification_state.get("shown", False))
        last_error_text = ""

        while time.monotonic() < deadline:
            if self.host.stop_event.is_set() or self.host.close_event.is_set():
                raise RuntimeError(
                    "Invite confirmation wait was cancelled because processing stopped."
                )
            self.host.wait_if_paused()
            self.host.detect_security(page)

            try:
                current = page.evaluate(
                    """
                    () => {
                        const state = window.__testerInviteNotificationState || {seq: 0, shown: false, text: ''};
                        return {seq: state.seq || 0, shown: !!state.shown, text: state.text || ''};
                    }
                    """
                )
                if isinstance(current, dict):
                    current_seq = int(current.get("seq", 0))
                    current_shown = bool(current.get("shown", False))
                    if current_seq > start_seq or (not was_shown and current_shown):
                        return
            except Exception:
                if not was_shown and self.host.any_visible(
                    page,
                    SHARE_INVITE_SELECTORS["invite_success"],
                    timeout=max(0, int(self._setting("notification_visibility_timeout"))),
                ):
                    return

            last_error_text = self.host.first_visible_text(
                page, SHARE_INVITE_SELECTORS["invite_error"]
            )
            if last_error_text:
                raise self.errors.invite_rejected(
                    f"Invite send failed: {last_error_text}"
                )
            self.host.interruptible_sleep(
                max(0.0, float(self._setting("notification_poll_interval")))
            )

        if last_error_text:
            raise RuntimeError(f"Invite send failed: {last_error_text}")
        raise RuntimeError("A new success notification was not detected after Send.")
