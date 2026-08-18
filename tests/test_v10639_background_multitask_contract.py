from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.backend import DEFAULT_SETTINGS


def test_four_task_limit_and_no_focus_loss_pause_contract():
    assert DEFAULT_SETTINGS["max_concurrent_tasks"] == 4
    source = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    main = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow")
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {"focusOutEvent", "hideEvent"}
        for node in main.body
    )


def test_power_guard_is_tied_to_process_batch_not_window_focus():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    worker = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker")
    process_batch = next(node for node in worker.body if isinstance(node, ast.FunctionDef) and node.name == "process_batch")
    text = ast.unparse(process_batch)
    assert "SYSTEM_SLEEP_GUARD.acquire" in text
    assert "SYSTEM_SLEEP_GUARD.release" in text
