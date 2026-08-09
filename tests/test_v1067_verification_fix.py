from __future__ import annotations

import ast
import importlib.util
import queue
import sys
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import AutomationWorker, DEFAULT_SETTINGS, TaskItem, TaskState


class _Store:
    def __init__(self):
        self.saved = []
        self.results = []
        self.progress = []

    def save_item(self, run_id, item_index, item):
        self.saved.append((run_id, item_index, item.status, item.message))

    def upsert_result(self, run_id, item_index, row):
        self.results.append((run_id, item_index, dict(row)))

    def save_progress(self, **kwargs):
        self.progress.append(dict(kwargs))

    def persist_item_result_progress(self, *, run_id, item_index, item, result_row, **progress):
        self.saved.append((run_id, item_index, item.status, item.message))
        if result_row is not None:
            self.results.append((run_id, item_index, dict(result_row)))
        self.progress.append(dict(progress, run_id=run_id))


class V1067VerificationFixTest(unittest.TestCase):
    def test_task_qss_has_exactly_one_classmethod_decorator(self):
        tree = ast.parse((ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TaskSlotWidget")
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "task_qss")
        decorators = [
            node.id for node in method.decorator_list if isinstance(node, ast.Name)
        ]
        self.assertEqual(decorators, ["classmethod"])

    def test_send_attempt_metric_wording_is_unambiguous(self):
        text = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        self.assertIn('visible_metric_name = "Send Attempts / Limit" if name == "Send Limit" else name', text)

    def test_saturated_critical_event_exits_after_close_request(self):
        events = queue.Queue(maxsize=1)
        events.put(("occupied", {}))
        worker = AutomationWorker(
            TaskState(slot_id=7),
            dict(DEFAULT_SETTINGS),
            events,
            threading.Event(),
            threading.Event(),
            initial_url="",
        )
        thread = threading.Thread(target=lambda: worker.emit("item", {"status": "success"}))
        thread.start()
        time.sleep(0.05)
        self.assertTrue(thread.is_alive())
        worker.request_close()
        thread.join(timeout=1.5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(events.qsize(), 1)

    def test_pre_click_crash_marker_is_authoritative_in_result_ledger(self):
        store = _Store()
        state = TaskState(
            slot_id=3,
            items=[TaskItem("user@example.com")],
            run_id="run-1",
        )
        worker = AutomationWorker(
            state,
            dict(DEFAULT_SETTINGS),
            queue.Queue(),
            threading.Event(),
            threading.Event(),
            initial_url="",
            runtime_store=store,
        )
        worker._register_send_click_attempt()
        self.assertTrue(state.manual_review_required)
        self.assertEqual(state.items[0].status, "interrupted")
        self.assertEqual(len(store.results), 1)
        _, index, row = store.results[0]
        self.assertEqual(index, 0)
        self.assertEqual(row["status"], "interrupted")
        self.assertEqual(row["run_id"], "run-1")

    def test_source_archive_verifier_rejects_runtime_paths_and_accepts_clean_source(self):
        spec = importlib.util.spec_from_file_location(
            "verify_source_archive", ROOT / "scripts/verify_source_archive.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        required = {
            "README.md": "# x\n",
            "pyproject.toml": "[project]\nname='x'\n",
            "src/vibrapilot/backend.py": "# backend\n",
            "src/vibrapilot/qt_app.py": "# qt\n",
            "config/AppConfig/app.py": "VERSION='x'\n",
        }
        with tempfile.TemporaryDirectory() as temp:
            clean = Path(temp) / "clean.zip"
            with zipfile.ZipFile(clean, "w") as zf:
                for name, content in required.items():
                    zf.writestr(name, content)
            self.assertEqual(module.verify_archive(clean), [])

            dirty = Path(temp) / "dirty.zip"
            with zipfile.ZipFile(dirty, "w") as zf:
                for name, content in required.items():
                    zf.writestr(f"VibraPilot/{name}", content)
                zf.writestr("VibraPilot/AppData/license.json", "{}")
                zf.writestr("VibraPilot/__pycache__/run.pyc", "x")
            errors = module.verify_archive(dirty)
            self.assertTrue(any("AppData/license.json" in error for error in errors))
            self.assertTrue(any("__pycache__" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
