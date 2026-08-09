from __future__ import annotations

from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WorkerShutdownTest(unittest.TestCase):
    def test_ui_keeps_live_worker_reference_after_timeout(self):
        tree = ast.parse((ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "TaskSlotWidget")
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "close_browser")
        source = ast.unparse(method)
        self.assertIn("worker.stopped_event.wait", source)
        self.assertIn("Closing / Worker Busy", source)
        self.assertIn("return False", source)


    def test_logout_and_license_invalid_keep_live_worker_references(self):
        tree = ast.parse((ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "MainWindow")
        logout = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "logout")
        finalize = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_finalize_license_invalid_transition")
        logout_source = ast.unparse(logout)
        finalize_source = ast.unparse(finalize)
        self.assertIn("if not task.close_browser(wait=True)", logout_source)
        self.assertIn("Logout was cancelled to avoid orphaning live workers", logout_source)
        self.assertIn("if worker.is_alive()", finalize_source)
        self.assertIn("QTimer.singleShot(200", finalize_source)
        self.assertIn("self.tasks.clear()", finalize_source)

if __name__ == "__main__":
    unittest.main()
