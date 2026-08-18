from __future__ import annotations

import json
import os
import queue
import sys
import tempfile
import threading
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault(
    "VIB_TOOLS_DATA_DIR", tempfile.mkdtemp(prefix="vibrapilot-v10614-test-")
)

import vibrapilot.backend as backend
from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, SettingsManager, TaskItem, TaskState
from vibrapilot.task_runtime_store import CLOSED_STATUS_PREFIX, SCHEMA_VERSION, TaskRuntimeStore


@dataclass
class Item:
    email: str
    name: str = ""
    status: str = "pending"
    attempts: int = 0
    message: str = ""
    result: str = ""


class ManagedPersistentBrowserContractTest(unittest.TestCase):
    def test_default_managed_persistent_mode_is_enabled_without_session_tab_restore(self):
        self.assertTrue(DEFAULT_SETTINGS["use_persistent_context"])
        self.assertTrue(DEFAULT_SETTINGS["dedicated_profile_per_task"])
        self.assertTrue(DEFAULT_SETTINGS["persist_profile_between_runs"])
        self.assertTrue(DEFAULT_SETTINGS["persist_profile_cache"])
        self.assertEqual(DEFAULT_SETTINGS["profile_lock_policy"], "fail")
        self.assertFalse(DEFAULT_SETTINGS["restore_previous_session"])

    def test_exact_legacy_default_bundle_promotes_to_managed_persistent_mode(self):
        old_bundle = {
            "use_persistent_context": False,
            "persistent_user_data_dir": "",
            "dedicated_profile_per_task": True,
            "persistent_profile_directory": "",
            "profile_lock_policy": "fail",
            "persist_profile_between_runs": True,
            "persist_profile_cache": True,
            "restore_previous_session": False,
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "settings.json"
            path.write_text(json.dumps(old_bundle), encoding="utf-8")
            manager = SettingsManager(path)
            self.assertTrue(manager.get("use_persistent_context"))
            persisted = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(persisted["use_persistent_context"])

    def test_custom_persistent_configuration_is_not_overwritten_by_legacy_migration(self):
        custom = {
            "use_persistent_context": False,
            "persistent_user_data_dir": "CustomAutomationProfile",
            "dedicated_profile_per_task": True,
            "persistent_profile_directory": "",
            "profile_lock_policy": "fail",
            "persist_profile_between_runs": True,
            "persist_profile_cache": True,
            "restore_previous_session": False,
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "settings.json"
            path.write_text(json.dumps(custom), encoding="utf-8")
            manager = SettingsManager(path)
            self.assertFalse(manager.get("use_persistent_context"))
            self.assertEqual(manager.get("persistent_user_data_dir"), "CustomAutomationProfile")

    def test_vib_tools_data_dir_override_remains_authoritative(self):
        settings = dict(DEFAULT_SETTINGS)
        settings["persistent_user_data_dir"] = ""
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(
            os.environ, {"VIB_TOOLS_DATA_DIR": td}, clear=False
        ):
            # APP_DATA_DIR is intentionally fixed at process import time. The contract
            # for an explicit deployment override is the application's APP_DATA_DIR.
            expected = (backend.APP_DATA_DIR / "BrowserProfiles" / "slot_3").resolve()
            actual = AutomationWorker.resolve_persistent_user_data_dir(settings, 3)
            self.assertEqual(actual, expected)

    def test_windows_managed_root_uses_localappdata_when_no_explicit_override(self):
        settings = dict(DEFAULT_SETTINGS)
        settings["persistent_user_data_dir"] = ""
        with tempfile.TemporaryDirectory() as local, mock.patch.dict(
            os.environ, {"LOCALAPPDATA": local}, clear=False
        ):
            prior = os.environ.pop("VIB_TOOLS_DATA_DIR", None)
            try:
                with mock.patch.object(backend.sys, "platform", "win32"):
                    path = AutomationWorker.resolve_persistent_user_data_dir(settings, 4)
            finally:
                if prior is not None:
                    os.environ["VIB_TOOLS_DATA_DIR"] = prior
            self.assertEqual(
                path,
                (Path(local) / "Vib Tools" / "VibraPilot" / "BrowserProfiles" / "slot_4").resolve(),
            )

    def test_personal_google_chrome_user_data_tree_is_rejected(self):
        with tempfile.TemporaryDirectory() as local, mock.patch.dict(
            os.environ, {"LOCALAPPDATA": local}, clear=False
        ):
            root = Path(local) / "Google" / "Chrome" / "User Data"
            for candidate in (root, root / "Default", root / "Profile 1"):
                with self.assertRaises(ValueError):
                    AutomationWorker.validate_managed_browser_profile_path(candidate)
            AutomationWorker.validate_managed_browser_profile_path(
                Path(local) / "Vib Tools" / "VibraPilot" / "BrowserProfiles" / "slot_1"
            )

    def test_task_slots_resolve_to_isolated_managed_user_data_directories(self):
        settings = dict(DEFAULT_SETTINGS)
        settings["persistent_user_data_dir"] = ""
        a = AutomationWorker.resolve_persistent_user_data_dir(settings, 1)
        b = AutomationWorker.resolve_persistent_user_data_dir(settings, 2)
        self.assertNotEqual(a, b)
        self.assertEqual(a.name, "slot_1")
        self.assertEqual(b.name, "slot_2")

    def test_shared_profile_claim_resolves_to_same_user_data_directory(self):
        settings = dict(DEFAULT_SETTINGS)
        settings["dedicated_profile_per_task"] = False
        a = AutomationWorker.resolve_persistent_user_data_dir(settings, 1)
        b = AutomationWorker.resolve_persistent_user_data_dir(settings, 2)
        self.assertEqual(a, b)

    def test_safe_legacy_vibrapilot_slot_profile_migrates_once(self):
        settings = dict(DEFAULT_SETTINGS)
        state = TaskState(slot_id=7)
        worker = AutomationWorker(
            state,
            settings,
            queue.Queue(),
            threading.Event(),
            threading.Event(),
            "https://example.test/",
        )
        legacy = backend.APP_DATA_DIR / "BrowserProfiles" / "slot_7"
        managed_parent = Path(tempfile.mkdtemp(prefix="vibrapilot-managed-root-"))
        target = managed_parent / "slot_7"
        if legacy.exists():
            import shutil
            shutil.rmtree(legacy, ignore_errors=True)
        legacy.mkdir(parents=True, exist_ok=True)
        (legacy / "marker.txt").write_text("legacy", encoding="utf-8")
        prior = os.environ.pop("VIB_TOOLS_DATA_DIR", None)
        try:
            self.assertTrue(worker._migrate_legacy_managed_profile_if_needed(target))
            self.assertFalse(legacy.exists())
            self.assertEqual((target / "marker.txt").read_text(encoding="utf-8"), "legacy")
            self.assertFalse(worker._migrate_legacy_managed_profile_if_needed(target))
        finally:
            if prior is not None:
                os.environ["VIB_TOOLS_DATA_DIR"] = prior

    def test_persistent_internal_recycle_is_guarded_and_reverifies_login(self):
        settings = dict(DEFAULT_SETTINGS)
        settings["browser_context_recycle_after_n_items"] = 1
        settings["browser_context_recycle_after_n_minutes"] = 0
        state = TaskState(slot_id=1, target_url="https://example.test/")
        worker = AutomationWorker(
            state,
            settings,
            queue.Queue(),
            threading.Event(),
            threading.Event(),
            "https://example.test/",
        )
        worker.persistent_context_mode = True
        observations: list[tuple[str, bool]] = []

        class Context:
            def close(self_inner):
                observations.append(("close", worker._context_transitioning))

        worker.context = Context()
        worker.active_page = None

        def launch():
            observations.append(("launch", worker._context_transitioning))
            worker.context = object()

        def verify(*, force_emit=False, allow_while_processing=False):
            observations.append(("verify", worker._context_transitioning))
            self.assertTrue(force_emit)
            self.assertTrue(allow_while_processing)

        worker.launch_browser = launch  # type: ignore[method-assign]
        worker.refresh_login_verification = verify  # type: ignore[method-assign]
        worker.maybe_recycle_context()
        self.assertEqual(observations[0], ("close", True))
        self.assertEqual(observations[1], ("launch", True))
        self.assertEqual(observations[2], ("verify", False))
        self.assertFalse(worker._context_transitioning)


class ClosedTaskRecoveryContractTest(unittest.TestCase):
    def _start(self, store: TaskRuntimeStore, *, slot_id: int = 5) -> str:
        return store.start_run(
            slot_id=slot_id,
            target_url="https://example.test/task",
            source_file="emails.csv",
            source_fingerprint="fp",
            items=[Item("a@example.com", status="success"), Item("b@example.com")],
            created_at="t0",
        )

    def test_close_and_reopen_preserve_schema_items_progress_and_run_identity(self):
        with tempfile.TemporaryDirectory() as td:
            store = TaskRuntimeStore(Path(td) / "store.sqlite3")
            # v1.0.6.42 intentionally migrates TaskRuntimeStore to schema v2 for
            # workflow provenance; this test continues to protect close/reopen semantics.
            self.assertEqual(SCHEMA_VERSION, 2)
            run_id = self._start(store)
            items = [
                Item("a@example.com", status="success", attempts=1, result="sent"),
                Item("b@example.com", status="pending"),
            ]
            store.close_run(
                run_id=run_id,
                task_status="Stopped",
                timestamp="t1",
                current_index=1,
                total=2,
                success_count=1,
                failed_count=0,
                send_limit_used=1,
                manual_review_required=False,
                target_url="https://example.test/task",
                items=items,
            )
            closed = store.closed_runs()
            self.assertEqual([row["run_id"] for row in closed], [run_id])
            self.assertEqual(store.closed_slot_ids(), [5])
            self.assertFalse(any(row["run_id"] == run_id for row in store.recoverable_runs()))
            archived = store.load_run(run_id)
            self.assertTrue(str(archived["task_status"]).startswith(CLOSED_STATUS_PREFIX))
            self.assertEqual(archived["current_index"], 1)
            self.assertEqual(archived["success_count"], 1)
            self.assertEqual(archived["send_limit_used"], 1)
            self.assertEqual(archived["items"][0]["result"], "sent")

            reopened = store.reopen_closed_run(run_id, "t2")
            self.assertIsNotNone(reopened)
            self.assertEqual(reopened["run_id"], run_id)
            self.assertEqual(reopened["slot_id"], 5)
            self.assertEqual(reopened["task_status"], "Stopped")
            self.assertEqual(reopened["current_index"], 1)
            self.assertEqual(len(reopened["items"]), 2)
            self.assertEqual(store.closed_runs(), [])

    def test_completed_task_can_be_closed_and_reopened_without_losing_completion(self):
        with tempfile.TemporaryDirectory() as td:
            store = TaskRuntimeStore(Path(td) / "store.sqlite3")
            run_id = self._start(store, slot_id=8)
            store.mark_completed(run_id, "Completed", "t1")
            run = store.load_run(run_id)
            items = [Item(**{k: row[k] for k in ("email", "name", "status", "attempts", "message", "result")}) for row in run["items"]]
            store.close_run(
                run_id=run_id,
                task_status="Completed",
                timestamp="t2",
                current_index=2,
                total=2,
                success_count=2,
                failed_count=0,
                send_limit_used=2,
                manual_review_required=False,
                target_url=run["target_url"],
                items=items,
            )
            reopened = store.reopen_closed_run(run_id, "t3")
            self.assertEqual(reopened["task_status"], "Completed")
            self.assertEqual(reopened["completed_at"], "t1")

    def test_session_only_closed_status_reopens_as_safe_resumable_status(self):
        with tempfile.TemporaryDirectory() as td:
            store = TaskRuntimeStore(Path(td) / "store.sqlite3")
            run_id = self._start(store, slot_id=12)
            run = store.load_run(run_id)
            items = [Item(**{k: row[k] for k in ("email", "name", "status", "attempts", "message", "result")}) for row in run["items"]]
            store.close_run(
                run_id=run_id,
                task_status="Login Verified",
                timestamp="t1",
                current_index=1,
                total=2,
                success_count=1,
                failed_count=0,
                send_limit_used=1,
                manual_review_required=False,
                target_url=run["target_url"],
                items=items,
            )
            reopened = store.reopen_closed_run(run_id, "t2")
            self.assertEqual(reopened["task_status"], "Stopped")
            self.assertTrue(any(row["run_id"] == run_id for row in store.recoverable_runs()))

    def test_zero_item_task_can_be_archived_with_existing_schema(self):
        with tempfile.TemporaryDirectory() as td:
            store = TaskRuntimeStore(Path(td) / "store.sqlite3")
            run_id = store.start_run(
                slot_id=11,
                target_url="https://example.test/blank",
                source_file="",
                source_fingerprint="",
                items=[],
                created_at="t0",
            )
            store.close_run(
                run_id=run_id,
                task_status="Ready",
                timestamp="t1",
                current_index=0,
                total=0,
                success_count=0,
                failed_count=0,
                send_limit_used=0,
                manual_review_required=False,
                target_url="https://example.test/blank",
                items=[],
            )
            self.assertEqual(store.closed_slot_ids(), [11])
            reopened = store.reopen_closed_run(run_id, "t2")
            self.assertEqual(reopened["total"], 0)
            self.assertEqual(reopened["task_status"], "Ready")

    def test_ui_source_has_open_closed_tasks_without_new_page_or_auto_start(self):
        text = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.assertIn('button("Open Closed Tasks", "secondary")', text)
        self.assertIn("def open_closed_tasks(self) -> None:", text)
        self.assertIn("self.runtime_store.reopen_closed_run", text)
        self.assertIn("slot.restore_runtime(run, preserve_task_status=True)", text)
        self.assertIn('slot._render_browser_status("Closed")', text)
        self.assertNotIn('navigate("Closed Tasks")', text)


if __name__ == "__main__":
    unittest.main()
