from __future__ import annotations

import ast
import json
import os
import queue
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskState


class FakeEventTarget:
    def __init__(self) -> None:
        self.handlers: dict[str, list] = {}

    def on(self, name: str, handler) -> None:
        self.handlers.setdefault(name, []).append(handler)

    def fire(self, name: str, *args) -> None:
        for handler in list(self.handlers.get(name, [])):
            handler(*args)


class FakePage(FakeEventTarget):
    def __init__(self, closed: bool = False) -> None:
        super().__init__()
        self.closed = closed

    def is_closed(self) -> bool:
        return self.closed

    def close_manually(self) -> None:
        self.closed = True
        self.fire("close", self)


class FakeContext(FakeEventTarget):
    def __init__(self, pages=None) -> None:
        super().__init__()
        self.pages = list(pages or [])


class FakeBrowser(FakeEventTarget):
    def __init__(self, connected: bool = True) -> None:
        super().__init__()
        self.connected = connected

    def is_connected(self) -> bool:
        return self.connected

    def disconnect_manually(self) -> None:
        self.connected = False
        self.fire("disconnected", self)


class BrowserLifecycleBackendTest(unittest.TestCase):
    def make_worker(self) -> AutomationWorker:
        settings = dict(DEFAULT_SETTINGS)
        state = TaskState(slot_id=7, target_url="https://example.test")
        return AutomationWorker(
            state,
            settings,
            queue.Queue(),
            threading.Event(),
            threading.Event(),
            initial_url="https://example.test",
        )

    @staticmethod
    def drain(worker: AutomationWorker):
        result = []
        while True:
            try:
                result.append(worker.ui_queue.get_nowait())
            except queue.Empty:
                return result

    def test_owner_probe_requires_live_page_and_connected_nonpersistent_browser(self):
        worker = self.make_worker()
        page = FakePage()
        worker.active_page = page
        worker.context = FakeContext([page])
        worker.browser = FakeBrowser(True)
        worker.persistent_context_mode = False
        self.assertTrue(worker._browser_objects_ready())

        page.closed = True
        self.assertFalse(worker._browser_objects_ready())

        page.closed = False
        worker.browser.connected = False
        self.assertFalse(worker._browser_objects_ready())

    def test_ui_readiness_consumes_thread_safe_event_not_playwright_wrappers(self):
        worker = self.make_worker()
        worker.browser_ready_event.set()
        worker.browser = SimpleNamespace(is_connected=lambda: (_ for _ in ()).throw(AssertionError("cross-thread browser access")))
        worker.active_page = SimpleNamespace(is_closed=lambda: (_ for _ in ()).throw(AssertionError("cross-thread page access")))
        self.assertTrue(worker.is_browser_ready())
        worker.browser_ready_event.clear()
        self.assertFalse(worker.is_browser_ready())

    def test_manual_active_page_close_without_replacement_clears_browser_and_login(self):
        worker = self.make_worker()
        page = FakePage()
        context = FakeContext([page])
        browser = FakeBrowser(True)
        worker.context = context
        worker.browser = browser
        worker.active_page = page
        worker._attach_browser_lifecycle_events()
        worker._attach_page_lifecycle_events(page)
        worker._set_browser_lifecycle_state("OPEN")
        worker.login_verified_event.set()
        self.drain(worker)

        page.close_manually()

        self.assertFalse(worker.browser_ready_event.is_set())
        self.assertFalse(worker.login_verified_event.is_set())
        self.assertIsNone(worker.active_page)
        events = self.drain(worker)
        self.assertTrue(any(kind == "browser" and payload["status"] == "Closed" for kind, payload in events))
        self.assertTrue(any(kind == "login" and payload["verified"] is False for kind, payload in events))

    def test_manual_active_page_close_uses_another_live_page_but_requires_reverification(self):
        worker = self.make_worker()
        page = FakePage()
        replacement = FakePage()
        context = FakeContext([page, replacement])
        worker.context = context
        worker.browser = FakeBrowser(True)
        worker.active_page = page
        worker._attach_page_lifecycle_events(page)
        worker._set_browser_lifecycle_state("OPEN")
        worker.login_verified_event.set()
        self.drain(worker)

        page.close_manually()

        self.assertIs(worker.active_page, replacement)
        self.assertTrue(worker.browser_ready_event.is_set())
        self.assertFalse(worker.login_verified_event.is_set())
        events = self.drain(worker)
        self.assertFalse(any(kind == "browser" and payload["status"] == "Closed" for kind, payload in events))
        self.assertTrue(any(kind == "login" and payload["verified"] is False for kind, payload in events))

    def test_context_close_marks_browser_unavailable(self):
        worker = self.make_worker()
        page = FakePage()
        context = FakeContext([page])
        worker.context = context
        worker.browser = FakeBrowser(True)
        worker.active_page = page
        worker._attach_browser_lifecycle_events()
        worker._set_browser_lifecycle_state("OPEN")
        worker.login_verified_event.set()
        self.drain(worker)

        context.fire("close", context)

        self.assertFalse(worker.browser_ready_event.is_set())
        self.assertFalse(worker.login_verified_event.is_set())
        events = self.drain(worker)
        self.assertTrue(any(kind == "browser" and payload["status"] == "Closed" for kind, payload in events))

    def test_browser_disconnect_marks_browser_unavailable(self):
        worker = self.make_worker()
        page = FakePage()
        context = FakeContext([page])
        browser = FakeBrowser(True)
        worker.context = context
        worker.browser = browser
        worker.active_page = page
        worker._attach_browser_lifecycle_events()
        worker._set_browser_lifecycle_state("OPEN")
        worker.login_verified_event.set()
        self.drain(worker)

        browser.disconnect_manually()

        self.assertFalse(worker.browser_ready_event.is_set())
        self.assertFalse(worker.login_verified_event.is_set())

    def test_lifecycle_event_registration_is_idempotent(self):
        worker = self.make_worker()
        page = FakePage()
        context = FakeContext([page])
        browser = FakeBrowser(True)
        worker.context = context
        worker.browser = browser
        worker.active_page = page
        worker._attach_browser_lifecycle_events()
        worker._attach_browser_lifecycle_events()
        worker._attach_page_lifecycle_events(page)
        worker._attach_page_lifecycle_events(page)
        self.assertEqual(len(browser.handlers.get("disconnected", [])), 1)
        self.assertEqual(len(context.handlers.get("close", [])), 1)
        self.assertEqual(len(page.handlers.get("close", [])), 1)


class BrowserLifecycleSourceContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.backend_text = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        self.qt_text = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.qt_tree = ast.parse(self.qt_text)


    def test_current_scope_contract_identifies_exact_baseline_and_runtime_surface(self):
        scope = json.loads((ROOT / "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json").read_text(encoding="utf-8"))
        self.assertEqual(scope["plan_id"], "VP-BROWSER-UI-LIFECYCLE-001")
        self.assertEqual(scope["official_baseline"], "VibraPilot v1.0.6.11")
        self.assertEqual(scope["official_baseline_archive_sha256"], "9ecb7cd66f24832c3555d219a6f8aaf47358877dd417eeb703b5a755964fc90a")
        self.assertEqual(scope["official_baseline_github_commit"], "8670415b1df221ebeeb7d8f3fba4f991a91d43ec")
        self.assertEqual(scope["target_version"], "1.0.6.12")
        self.assertEqual(set(scope["allowed_runtime_source_changes"]), {"src/vibrapilot/backend.py", "src/vibrapilot/qt_app.py"})
        self.assertTrue(scope["no_new_dependency"])
        self.assertTrue(scope["no_database_schema_change"])
        self.assertTrue(scope["no_browser_settings_change"])
        self.assertTrue(scope["no_ui_redesign"])

    def test_task_ui_owns_one_stateful_browser_action_and_separate_close_task(self):
        self.assertIn('self.browser_action_button = button("Open Browser", "primary")', self.qt_text)
        self.assertIn('self.browser_action_button.clicked.connect(self.browser_action)', self.qt_text)
        self.assertIn('action.setText("Close Browser")', self.qt_text)
        self.assertIn('close_btn = button("Close Task", "danger")', self.qt_text)
        self.assertIn('self.close_browser(wait=False)', self.qt_text)

    def test_browser_action_contract_has_all_four_states(self):
        for marker in ('"Closed"', '"Opening"', '"Open"', '"Closing"'):
            self.assertIn(marker, self.qt_text)
        self.assertIn('action.setText("Opening...")', self.qt_text)
        self.assertIn('action.setText("Closing...")', self.qt_text)

    def test_workspace_transition_uses_safe_screen_fit_without_persistence(self):
        self.assertIn("def _fit_workspace_to_screen(self)", self.qt_text)
        self.assertIn("screen.availableGeometry()", self.qt_text)
        self.assertIn("self._fit_workspace_to_screen()", self.qt_text)
        self.assertNotIn("restoreGeometry(", self.qt_text)
        self.assertNotIn("saveGeometry(", self.qt_text)

    def test_phase_does_not_change_browser_profile_defaults(self):
        defaults = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
        self.assertFalse(defaults["use_persistent_context"])
        self.assertFalse(defaults["restore_previous_session"])
        self.assertFalse(defaults["extensions_enabled"])

    def test_backend_preserves_current_auto_restart_setting_path(self):
        self.assertIn('"auto_restart_browser_on_crash"', self.backend_text)
        self.assertIn('"browser_restart_max_attempts"', self.backend_text)
        self.assertIn('"browser_restart_delay"', self.backend_text)


try:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    from vibrapilot.qt_app import TaskSlotWidget
except Exception:  # pragma: no cover - source audit environments may omit PySide6
    QApplication = None
    TaskSlotWidget = None


@unittest.skipIf(QApplication is None, "PySide6 runtime is not installed")
class BrowserLifecycleQtTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def make_slot(self):
        class Settings:
            data = dict(DEFAULT_SETTINGS)

            def get(self, key, default=None):
                return self.data.get(key, default)

        fake = SimpleNamespace(settings=Settings())
        slot = TaskSlotWidget(fake, 1)
        return slot

    def test_browser_button_renders_deterministic_state_actions(self):
        slot = self.make_slot()
        try:
            expected = {
                "Closed": ("Open Browser", True),
                "Opening": ("Opening...", False),
                "Open": ("Close Browser", True),
                "Closing": ("Closing...", False),
            }
            for state, (text, enabled) in expected.items():
                slot._render_browser_status(state)
                self.assertEqual(slot.browser_action_button.text(), text)
                self.assertEqual(slot.browser_action_button.isEnabled(), enabled)
        finally:
            slot.deleteLater()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
