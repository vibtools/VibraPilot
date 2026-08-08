from __future__ import annotations
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'project/research/source_baseline/VibraPilot_v1.0.6_original_app.py'
PROD = ROOT / 'src/vibrapilot/backend.py'
CORE = ['SettingsManager','LicenseManager','TaskItem','TaskState','AutomationWorker','SecurityChallenge','SessionVerificationError','TestModeRequired','TestSendLimitReached','SendClickOutcomeUncertain','InviteRejected']

def methods(path: Path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    return {n.name:[x.name for x in n.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))] for n in tree.body if isinstance(n,ast.ClassDef)}

class BackendParityTest(unittest.TestCase):
    def test_core_method_inventory_matches_v106(self):
        old,new=methods(BASE),methods(PROD)
        for cls in CORE:
            self.assertEqual(old[cls],new[cls],cls)
        self.assertEqual(len(new['AutomationWorker']),54)

    def test_safety_constants(self):
        text=PROD.read_text(encoding='utf-8')
        self.assertIn('DEFAULT_TEST_SEND_LIMIT = int(DEFAULT_SETTINGS["max_test_send_limit"])',text)
        self.assertNotIn('MAX_TEST_SEND_LIMIT',text)
        self.assertIn('class SendClickOutcomeUncertain',text)
        self.assertIn('def assert_test_mode',text)

if __name__ == '__main__': unittest.main()
