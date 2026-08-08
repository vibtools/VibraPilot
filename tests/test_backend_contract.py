from __future__ import annotations
import ast
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_BASE = ROOT / "project/research/source_baseline/VibraPilot_v1.0.6_original_app.py"
CONTRACT = ROOT / "config/verification/backend_v1.0.6_contract.json"
PROD = ROOT / "src/vibrapilot/backend.py"
CORE = [
    "SettingsManager", "LicenseManager", "TaskItem", "TaskState", "AutomationWorker",
    "SecurityChallenge", "SessionVerificationError", "TestModeRequired",
    "TestSendLimitReached", "SendClickOutcomeUncertain", "InviteRejected",
]




AST_HASH_ALGORITHM = "canonical-semantic-ast-v2"


def canonical_ast_value(value):
    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            if child is None or child == [] or child == ():
                continue
            fields.append([name, canonical_ast_value(child)])
        return [value.__class__.__name__, fields]
    if isinstance(value, list):
        return [canonical_ast_value(item) for item in value]
    if isinstance(value, tuple):
        return [canonical_ast_value(item) for item in value]
    return value


def stable_ast_sha(node: ast.AST) -> str:
    payload = json.dumps(
        canonical_ast_value(node), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(AST_HASH_ALGORITHM.encode("ascii") + b"\0" + payload).hexdigest()


def nodes(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    return classes, functions

def methods(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        n.name: [x.name for x in n.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for n in tree.body if isinstance(n, ast.ClassDef)
    }


class BackendParityTest(unittest.TestCase):
    def test_core_method_inventory_matches_public_contract(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        expected = contract["core_method_inventory"]
        current = methods(PROD)
        for cls in CORE:
            self.assertEqual(expected[cls], current[cls], cls)
        self.assertEqual(
            len(current["AutomationWorker"]),
            contract["automation_worker_method_count"],
        )

    def test_public_contract_matches_private_baseline_when_available(self):
        if not PRIVATE_BASE.is_file():
            self.skipTest("private project/ baseline is intentionally absent from public CI")
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        private = methods(PRIVATE_BASE)
        for cls in CORE:
            self.assertEqual(contract["core_method_inventory"][cls], private[cls], cls)


    def test_canonical_ast_contract_matches_production(self):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(AST_HASH_ALGORITHM, contract.get("ast_hash_algorithm"))
        classes, functions = nodes(PROD)
        for cls, expected in contract["frozen_class_ast_sha256"].items():
            self.assertEqual(expected, stable_ast_sha(classes[cls]), cls)
        for name, expected in contract["frozen_helper_ast_sha256"].items():
            self.assertEqual(expected, stable_ast_sha(functions[name]), name)

    def test_canonical_ast_hash_ignores_empty_version_specific_fields(self):
        node = ast.parse("class Example:\n    pass\n").body[0]
        before = stable_ast_sha(node)
        # Python 3.12+ exposes an empty ClassDef.type_params field. The contract
        # intentionally ignores empty optional fields so Python minor versions
        # cannot create false implementation drift.
        if hasattr(node, "type_params"):
            node.type_params = []
        self.assertEqual(before, stable_ast_sha(node))

    def test_safety_constants(self):
        text = PROD.read_text(encoding="utf-8")
        self.assertIn('DEFAULT_TEST_SEND_LIMIT = int(DEFAULT_SETTINGS["max_test_send_limit"])', text)
        self.assertNotIn("MAX_TEST_SEND_LIMIT", text)
        self.assertIn("class SendClickOutcomeUncertain", text)
        self.assertIn("def assert_test_mode", text)


if __name__ == "__main__":
    unittest.main()
