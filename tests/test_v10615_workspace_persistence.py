from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.task_runtime_store import SCHEMA_VERSION
from vibrapilot.workspace_state import (
    WORKSPACE_STATE_SCHEMA_VERSION,
    WorkspaceStateStore,
)


class WorkspaceStateStoreTest(unittest.TestCase):
    def test_atomic_round_trip_preserves_only_workspace_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = WorkspaceStateStore(path)
            store.save(
                {
                    "saved_at": "2026-08-09 15:00:00",
                    "active_tasks": [
                        {"slot_id": 3, "workflow_id": "workflow_a", "run_id": "run-3", "target_url": "https://example.test/a"},
                        {"slot_id": 1, "workflow_id": "workflow_b", "run_id": "", "target_url": "https://example.test/b"},
                    ],
                    "next_slot_id": 7,
                    "selected_page": "Tasks",
                    "window": {
                        "x": 120,
                        "y": 80,
                        "width": 1366,
                        "height": 768,
                        "maximized": False,
                    },
                    # Unknown/sensitive values must never be serialized by this store.
                    "license_key": "do-not-store",
                    "recipient_rows": ["do-not-duplicate"],
                }
            )
            loaded = store.load()
            self.assertEqual(loaded["schema_version"], WORKSPACE_STATE_SCHEMA_VERSION)
            self.assertEqual([row["slot_id"] for row in loaded["active_tasks"]], [3, 1])
            self.assertEqual(loaded["next_slot_id"], 7)
            self.assertEqual(loaded["selected_page"], "Tasks")
            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("license_key", raw)
            self.assertNotIn("do-not-store", raw)
            self.assertNotIn("recipient_rows", raw)
            self.assertFalse(list(Path(td).glob(".*.tmp")))

    def test_missing_state_uses_safe_first_run_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            store = WorkspaceStateStore(Path(td) / "state.json")
            self.assertIsNone(store.load())
            self.assertEqual(store.warning, "")

    def test_corrupt_state_is_quarantined_without_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            store = WorkspaceStateStore(path)
            self.assertIsNone(store.load())
            self.assertFalse(path.exists())
            self.assertTrue(list(Path(td).glob("state.json.corrupt-*")))
            self.assertIn("could not be read", store.warning)

    def test_unsupported_schema_is_quarantined(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
            store = WorkspaceStateStore(path)
            self.assertIsNone(store.load())
            self.assertTrue(list(Path(td).glob("state.json.corrupt-*")))
            self.assertIn("Unsupported workspace state schema", store.warning)

    def test_duplicate_or_invalid_task_slots_are_ignored_safely(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "active_tasks": [
                            {"slot_id": 2, "run_id": "a", "target_url": "u1"},
                            {"slot_id": 2, "run_id": "b", "target_url": "u2"},
                            {"slot_id": 0, "run_id": "bad", "target_url": "u3"},
                        ],
                        "next_slot_id": 1,
                        "selected_page": "Tasks",
                        "window": {},
                    }
                ),
                encoding="utf-8",
            )
            # v1.0.6.42 migrates legacy workspace rows only through an explicit
            # workflow-identity resolver; this test remains focused on duplicate/invalid slots.
            loaded = WorkspaceStateStore(
                path, legacy_workflow_resolver=lambda slot_id, _run_id: "legacy_workflow"
            ).load()
            self.assertEqual(
                loaded["active_tasks"],
                [{"slot_id": 2, "workflow_id": "legacy_workflow", "run_id": "a", "target_url": "u1"}],
            )


class WorkspacePersistenceScopeTest(unittest.TestCase):
    def test_runtime_database_schema_phase2_successor_is_workflow_aware(self):
        # v1.0.6.42 intentionally supersedes the v1 schema to persist immutable
        # per-Task workflow provenance without changing unrelated runtime behavior.
        self.assertEqual(SCHEMA_VERSION, 2)

    def test_qt_workspace_contract_contains_required_safe_restore_paths(self):
        text = (ROOT / "src" / "vibrapilot" / "qt_app.py").read_text(encoding="utf-8")
        for marker in (
            "WorkspaceStateStore(",
            "legacy_workflow_resolver=self._resolve_legacy_workspace_workflow_identity",
            "def schedule_workspace_save",
            "def save_workspace_state",
            "def _restore_active_workspace_tasks",
            "def _restore_workspace_geometry",
            "self._workspace_restored_run_ids",
            "if run_id in self._workspace_restored_run_ids",
            "self.save_workspace_state()",
            "self.url.editingFinished.connect(self.app.schedule_workspace_save)",
        ):
            self.assertIn(marker, text)
        self.assertIn('slot._render_browser_status("Closed")', text)
        self.assertIn('slot._set_metric("Login", "Not Verified")', text)

    def test_workspace_module_has_no_browser_or_licensing_dependencies(self):
        text = (ROOT / "src" / "vibrapilot" / "workspace_state.py").read_text(encoding="utf-8")
        for forbidden in (
            "playwright",
            "LicenseManager",
            "licensing_v2",
            "TaskRuntimeStore",
            "QApplication",
            "PySide6",
        ):
            self.assertNotIn(forbidden, text)

    def test_scope_manifest_records_no_schema_or_settings_key_change(self):
        scope = json.loads(
            (ROOT / "config" / "verification" / "v1.0.6.15_workspace_persistence_scope.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(scope["no_database_schema_change"])
        self.assertTrue(scope["no_settings_key_change"])
        self.assertTrue(scope["no_auto_browser_start"])
        self.assertTrue(scope["no_auto_workflow_start"])
        self.assertTrue(scope["no_auto_send"])
        self.assertTrue(scope["closed_tasks_must_remain_closed"])
        self.assertEqual(
            scope["allowed_runtime_source_changes"],
            ["src/vibrapilot/qt_app.py", "src/vibrapilot/workspace_state.py"],
        )


if __name__ == "__main__":
    unittest.main()
