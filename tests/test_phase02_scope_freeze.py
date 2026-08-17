from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "config/verification/phase02_step002_scope.json").read_text(encoding="utf-8")
)
ALGORITHM = "canonical-semantic-ast-v2"


def _canonical(value):
    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            if child is None or child == [] or child == ():
                continue
            fields.append([name, _canonical(child)])
        return [value.__class__.__name__, fields]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _hash(node: ast.AST) -> str:
    payload = json.dumps(
        _canonical(node), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(ALGORITHM.encode("ascii") + b"\0" + payload).hexdigest()


class Phase02ScopeFreezeTest(unittest.TestCase):
    def test_frozen_automation_and_ui_contract(self):
        self.assertEqual(CONTRACT["ast_hash_algorithm"], ALGORITHM)
        backend = ast.parse((ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8"))
        qt = ast.parse((ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8"))
        backend_classes = {
            node.name: node for node in backend.body if isinstance(node, ast.ClassDef)
        }
        qt_classes = {node.name: node for node in qt.body if isinstance(node, ast.ClassDef)}
        backend_assignments = {}
        for node in backend.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        backend_assignments[target.id] = node
        qt_ann = {
            node.target.id: node
            for node in qt.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        actual = {
            "backend.TaskItem": _hash(backend_classes["TaskItem"]),
            "qt_app.ActivationPage": _hash(qt_classes["ActivationPage"]),
            "qt_app.BROWSER_SETTING_GROUPS": _hash(qt_ann["BROWSER_SETTING_GROUPS"]),
        }
        if "SELECTORS" in backend_assignments:
            actual["backend.SELECTORS"] = _hash(backend_assignments["SELECTORS"])
        current_scope = ROOT / "config/verification/v1.0.6.30_workflow_plugin_system_scope.json"
        authorized = {"qt_app.BROWSER_SETTING_GROUPS"} if current_scope.is_file() else set()
        v10636_scope = ROOT / "config/verification/v1.0.6.36_share_invite_externalization_scope.json"
        if v10636_scope.is_file():
            authorized.add("backend.SELECTORS")
        ui_scope = ROOT / "config/verification/v1.0.6.34_ui_compact_polish_scope.json"
        if ui_scope.is_file():
            ui_data = json.loads(ui_scope.read_text(encoding="utf-8"))
            if "src/vibrapilot/qt_app.py" in ui_data.get("allowed_production_source_changes", []):
                authorized.add("qt_app.ActivationPage")
        for key, value in actual.items():
            if key in authorized:
                continue
            self.assertEqual(value, CONTRACT["frozen_ast_sha256"][key], key)


if __name__ == "__main__":
    unittest.main()
