from __future__ import annotations

import tempfile
import ast
from dataclasses import dataclass
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.task_runtime_store import TaskRuntimeStore

@dataclass
class Item:
    email: str
    name: str = ""
    status: str = "pending"
    attempts: int = 0
    message: str = ""
    result: str = ""

class ReportIntegrityTest(unittest.TestCase):
    def test_per_task_filters_and_latest_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            store = TaskRuntimeStore(Path(temp) / "store.sqlite3")
            runs = []
            for slot in (1,2):
                run = store.start_run(
                    slot_id=slot,target_url="https://example.test",source_file=f"{slot}.txt",
                    source_fingerprint=str(slot),items=[Item(f"u{slot}@example.com")],created_at=f"t{slot}"
                )
                runs.append(run)
                store.upsert_result(run,0,{"timestamp":f"t{slot}","slot_id":slot,"email":f"u{slot}@example.com","status":"success","message":"ok","attempts":1,"target_url":"https://example.test","result":"sent"})
            self.assertEqual(len(store.results(limit=None)),2)
            self.assertEqual(len(store.results(slot_id=1,limit=None)),1)
            self.assertEqual(store.results(slot_id=2,limit=None)[0]["email"],"u2@example.com")
            self.assertEqual(store.result_slot_ids(),[1,2])


    def test_ui_report_events_are_coalesced_per_poll_tick(self):
        source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        main = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
        add = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "add_report_row")
        poll = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "poll_queue")
        add_source = ast.unparse(add)
        poll_source = ast.unparse(poll)
        self.assertIn("self._report_dirty = True", add_source)
        self.assertNotIn("self.refresh_report_table()", add_source)
        self.assertIn("if self._report_dirty", poll_source)
        self.assertIn("self.refresh_report_table()", poll_source)

if __name__ == "__main__":
    unittest.main()
