from __future__ import annotations

import hashlib
import json
import os
import queue
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskState
from vibrapilot.browser_capabilities import (
    collision_safe_download_path,
    default_managed_download_root,
    normalize_extension_paths,
    resolve_task_download_directory,
    sanitize_download_filename,
    validate_unpacked_extension_directories,
)

SCOPE = ROOT / "config/verification/v1.0.6.17_browser_capabilities_scope.json"


class BrowserCapabilityHelpersTest(unittest.TestCase):
    def test_scope_identity_and_frozen_surfaces(self):
        scope = json.loads(SCOPE.read_text(encoding="utf-8"))
        self.assertEqual(scope["plan_id"], "VP-BROWSER-CAPABILITIES-001")
        self.assertEqual(scope["official_baseline"], "VibraPilot v1.0.6.16")
        self.assertEqual(
            scope["official_baseline_github_commit"],
            "fd0cbe6e8f3fc37f92bdf49396364ce74583fd1e",
        )
        self.assertEqual(scope["official_baseline_github_actions_run"], 31342562832)
        self.assertEqual(scope["target_version"], "1.0.6.17")
        self.assertTrue(scope["no_database_schema_change"])
        self.assertEqual(scope["required_taskruntime_schema_version"], 1)
        self.assertTrue(scope["no_workspace_schema_change"])
        self.assertTrue(scope["no_settings_key_change"])
        self.assertTrue(scope["no_new_dependency"])
        for relative, expected in scope["approved_target_file_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)
        for relative, expected in scope["frozen_file_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected, relative)

    def test_download_filename_is_safe_and_collision_is_non_destructive(self):
        self.assertEqual(sanitize_download_filename(r"../../CON?.pdf"), "CON_.pdf")
        self.assertEqual(sanitize_download_filename(".."), "download")
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "report.pdf").write_bytes(b"old")
            (directory / "report (1).pdf").write_bytes(b"old2")
            candidate = collision_safe_download_path(directory, "report.pdf")
            self.assertEqual(candidate.name, "report (2).pdf")
            self.assertEqual((directory / "report.pdf").read_bytes(), b"old")

    def test_download_directory_preserves_custom_semantics_and_isolates_blank_default(self):
        with tempfile.TemporaryDirectory() as td:
            app_data = Path(td) / "AppData"
            custom = resolve_task_download_directory(
                {"downloads_path": "custom-downloads"}, 2, app_data
            )
            self.assertEqual(custom, (app_data / "custom-downloads").resolve())
            first = resolve_task_download_directory({"downloads_path": ""}, 1, app_data)
            second = resolve_task_download_directory({"downloads_path": ""}, 2, app_data)
            self.assertNotEqual(first, second)
            self.assertEqual(first.name, "slot_1")
            self.assertEqual(second.name, "slot_2")

    def test_vib_tools_data_dir_override_keeps_managed_downloads_under_appdata(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"VIB_TOOLS_DATA_DIR": td}, clear=False
        ):
            app_data = Path(td) / "AppData"
            self.assertEqual(default_managed_download_root(app_data), app_data.resolve() / "Downloads")

    def test_extension_paths_are_normalized_deduplicated_and_manifest_validated(self):
        with tempfile.TemporaryDirectory() as td:
            extension = Path(td) / "ext"
            extension.mkdir()
            (extension / "manifest.json").write_text(
                json.dumps({"manifest_version": 3, "name": "Test", "version": "1.0"}),
                encoding="utf-8",
            )
            raw = f"{extension};{extension}\n"
            normalized = normalize_extension_paths(raw)
            self.assertEqual(normalized, [extension.resolve()])
            self.assertEqual(validate_unpacked_extension_directories(raw), [extension.resolve()])

            (extension / "manifest.json").write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                validate_unpacked_extension_directories(str(extension))

            (extension / "manifest.json").unlink()
            with self.assertRaisesRegex(ValueError, "manifest.json"):
                validate_unpacked_extension_directories(str(extension))


class AutomationWorkerCapabilityTest(unittest.TestCase):
    def make_worker(self, *, slot_id: int = 1, settings: dict | None = None):
        merged = dict(DEFAULT_SETTINGS)
        if settings:
            merged.update(settings)
        return AutomationWorker(
            TaskState(slot_id=slot_id, target_url="https://example.test/"),
            merged,
            queue.Queue(),
            __import__("threading").Event(),
            __import__("threading").Event(),
            "https://example.test/",
        )

    def test_download_event_uses_save_as_and_keeps_previous_file(self):
        worker = self.make_worker()

        class Download:
            suggested_filename = "report.pdf"

            def __init__(self):
                self.saved = None

            def save_as(self, path):
                self.saved = Path(path)
                self.saved.write_bytes(b"new")

        with tempfile.TemporaryDirectory() as td, patch(
            "vibrapilot.backend.ensure_task_download_directory", return_value=Path(td)
        ):
            directory = Path(td)
            (directory / "report.pdf").write_bytes(b"old")
            download = Download()
            worker._handle_download(download)
            self.assertEqual(download.saved.name, "report (1).pdf")
            self.assertEqual((directory / "report.pdf").read_bytes(), b"old")
            self.assertEqual(download.saved.read_bytes(), b"new")
            events = [worker.ui_queue.get_nowait(), worker.ui_queue.get_nowait()]
            self.assertEqual(events[0][0], "download")
            self.assertEqual(events[0][1]["status"], "started")
            self.assertEqual(events[1][1]["status"], "saved")

    def test_filechooser_requires_matching_request_id_and_explicit_selection(self):
        worker = self.make_worker()

        class Element:
            def get_attribute(self, name):
                return None

        class Chooser:
            element = Element()

            def __init__(self):
                self.selected = None

            def is_multiple(self):
                return False

            def set_files(self, value):
                self.selected = value

        chooser = Chooser()
        page = object()
        worker._handle_file_chooser(page, chooser)
        kind, payload = worker.ui_queue.get_nowait()
        self.assertEqual(kind, "browser_file_chooser")
        self.assertNotIn("paths", payload)
        request_id = payload["request_id"]

        worker._apply_file_chooser_selection(
            {"request_id": "stale", "paths": [__file__], "cancelled": False}
        )
        self.assertIsNone(chooser.selected)
        self.assertEqual(worker._pending_file_chooser_request_id, request_id)

        worker._apply_file_chooser_selection(
            {"request_id": request_id, "paths": [__file__], "cancelled": False}
        )
        self.assertEqual(Path(chooser.selected), Path(__file__).resolve())
        self.assertIsNone(worker._pending_file_chooser_request_id)

    def test_directory_filechooser_and_cancel_clear_pending_request(self):
        worker = self.make_worker()

        class Element:
            def get_attribute(self, name):
                return "" if name == "webkitdirectory" else None

        class Chooser:
            element = Element()

            def __init__(self):
                self.selected = None

            def is_multiple(self):
                return True

            def set_files(self, value):
                self.selected = value

        with tempfile.TemporaryDirectory() as td:
            chooser = Chooser()
            worker._handle_file_chooser(object(), chooser)
            _, payload = worker.ui_queue.get_nowait()
            self.assertTrue(payload["directory"])
            worker._apply_file_chooser_selection(
                {"request_id": payload["request_id"], "paths": [td], "cancelled": False}
            )
            self.assertEqual(Path(chooser.selected), Path(td).resolve())
            self.assertIsNone(worker._pending_file_chooser_request_id)

            chooser2 = Chooser()
            worker._handle_file_chooser(object(), chooser2)
            payload2 = None
            while payload2 is None:
                kind2, candidate = worker.ui_queue.get_nowait()
                if kind2 == "browser_file_chooser":
                    payload2 = candidate
            worker._apply_file_chooser_selection(
                {"request_id": payload2["request_id"], "paths": [], "cancelled": True}
            )
            self.assertIsNone(chooser2.selected)
            self.assertIsNone(worker._pending_file_chooser_request_id)

    def test_backend_and_ui_source_contain_only_approved_capability_bridges(self):
        backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        qt = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.assertIn('page.on("download", self._handle_download)', backend)
        self.assertIn('page.on("filechooser"', backend)
        self.assertIn('download.save_as(str(destination))', backend)
        self.assertIn('"filechooser_response"', backend)
        self.assertIn('button("Downloads", "secondary", "folder")', qt)
        self.assertIn('QFileDialog.getOpenFileName', qt)
        self.assertIn('QFileDialog.getOpenFileNames', qt)
        self.assertIn('QFileDialog.getExistingDirectory', qt)
        self.assertNotIn('set_input_files(', qt)


if __name__ == "__main__":
    unittest.main()
