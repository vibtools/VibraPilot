from __future__ import annotations
import ast
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

    def test_safety_constants(self):
        text = PROD.read_text(encoding="utf-8")
        self.assertIn('DEFAULT_TEST_SEND_LIMIT = int(DEFAULT_SETTINGS["max_test_send_limit"])', text)
        self.assertNotIn("MAX_TEST_SEND_LIMIT", text)
        self.assertIn("class SendClickOutcomeUncertain", text)
        self.assertIn("def assert_test_mode", text)


if __name__ == "__main__":
    unittest.main()
