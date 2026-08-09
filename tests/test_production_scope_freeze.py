from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads(
    (ROOT / "config/verification/production_mt_lr_v1.0.6.5_scope.json").read_text(encoding="utf-8")
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
    payload = json.dumps(_canonical(node), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(ALGORITHM.encode("ascii") + b"\0" + payload).hexdigest()


class ProductionScopeFreezeTest(unittest.TestCase):
    def test_baseline_identity_and_approved_parameters(self):
        self.assertEqual(
            CONTRACT["official_baseline_archive_sha256"],
            "ea65bd89d908c5db8edfcf01e6b7c5e11410ffe57a98044f9e8913477f9e89e6",
        )
        self.assertEqual(CONTRACT["target_version"], "1.0.6.5")
        self.assertEqual(CONTRACT["approved_parameters"]["max_concurrent_tasks_default"], 4)
        self.assertEqual(CONTRACT["approved_parameters"]["ui_queue_capacity"], 4096)
        self.assertEqual(CONTRACT["approved_parameters"]["auto_save_interval_unit"], "seconds")


    def test_existing_settings_defaults_are_unchanged(self):
        settings = json.loads((ROOT / "config/settings.defaults.json").read_text(encoding="utf-8"))
        for key in CONTRACT.get("approved_new_setting_keys", []):
            settings.pop(key, None)
        current_scope = ROOT / "config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json"
        if current_scope.is_file():
            current = json.loads(current_scope.read_text(encoding="utf-8"))
            for key, change in current.get("approved_settings_default_changes", {}).items():
                settings[key] = change["from"]
        payload = json.dumps(settings, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            CONTRACT["baseline_settings_canonical_sha256"],
        )

    def test_out_of_scope_files_and_ast_are_frozen(self):
        current_focus_scope = ROOT / "config/verification/v1.0.6.11_qt_focus_lifecycle_fix_scope.json"
        current_browser_scope = ROOT / "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json"
        browser_data = json.loads(current_browser_scope.read_text(encoding="utf-8")) if current_browser_scope.is_file() else {}
        current_phase_scope = ROOT / "config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json"
        phase_data = json.loads(current_phase_scope.read_text(encoding="utf-8")) if current_phase_scope.is_file() else {}
        approved_worker = set(browser_data.get("approved_automationworker_method_changes", [])) | set(phase_data.get("approved_automationworker_method_changes", []))
        current_allowed = set(phase_data.get("allowed_runtime_source_changes", []))
        for relative, expected in CONTRACT["frozen_file_sha256"].items():
            if current_focus_scope.is_file() and relative == "vib_validation_app/focus_manager.py":
                continue
            if relative in current_allowed:
                continue
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected)

        backend = ast.parse((ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8"))
        qt = ast.parse((ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8"))
        bclasses = {n.name: n for n in backend.body if isinstance(n, ast.ClassDef)}
        qclasses = {n.name: n for n in qt.body if isinstance(n, ast.ClassDef)}
        assigns = {}
        for node in backend.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigns[target.id] = node
        anns = {
            n.target.id: n for n in qt.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
        }
        actual = {
            "backend.LicenseManager": _hash(bclasses["LicenseManager"]),
            "backend.SELECTORS": _hash(assigns["SELECTORS"]),
            "qt_app.ActivationPage": _hash(qclasses["ActivationPage"]),
            "qt_app.BROWSER_SETTING_GROUPS": _hash(anns["BROWSER_SETTING_GROUPS"]),
        }
        expected = dict(CONTRACT["frozen_ast_sha256"])
        current_license_scope = ROOT / "config/verification/v1.0.6.10_license_login_fix_scope.json"
        if current_license_scope.is_file():
            # v1.0.6.10 explicitly authorizes LicenseManager changes while preserving
            # every other historical production AST contract.
            actual.pop("backend.LicenseManager", None)
            expected.pop("backend.LicenseManager", None)
        self.assertEqual(actual, expected)

        worker = bclasses["AutomationWorker"]
        worker_methods = {
            node.name: node for node in worker.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for method_name, expected in CONTRACT.get("frozen_automationworker_method_ast_sha256", {}).items():
            if method_name in approved_worker:
                continue
            with self.subTest(worker_method=method_name):
                self.assertIn(method_name, worker_methods)
                self.assertEqual(_hash(worker_methods[method_name]), expected)


if __name__ == "__main__":
    unittest.main()
