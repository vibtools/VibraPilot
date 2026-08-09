from __future__ import annotations
import hashlib
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED={
'vib_validation_app/tokens.py':'cdae402dccdb8e916f274ea5fa0b8ec1a6505fab6043462d35af8a93e1468a02',
'vib_validation_app/styles.py':'83729e5b0e811e6b0cc4943dc729cbcf0cad92657eacbaebaacc0e0f56e3877b',
'vib_validation_app/widgets.py':'5f13404bc98a053edb1ebd63760cd185632cbe84041594b7c4f5821043a3495d',
'vib_validation_app/button_contract.py':'89bd33cbbfa00497a223e6ea5493e8aa4745d556e23447e28a0001c673381ce0',
'vib_validation_app/focus_manager.py':'a073051b05cbd2442b0bdec0a1251cf8185b54cbb71e755cc25c2ee85ce7f86e',
'frozen_design_source/CURRENT_FOUNDATION_TOKENS.json':'cbf1636b53a85c30dae839379653b6bbe0d0065e8f37cd919acaeb0c491e7616',
}

class BrandContractTest(unittest.TestCase):
    def test_frozen_source_exact(self):
        for rel,expected in EXPECTED.items():
            actual=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
            self.assertEqual(actual,expected,rel)

    def test_application_consumes_frozen_contract(self):
        text=(ROOT/'src/vibrapilot/qt_app.py').read_text(encoding='utf-8')
        self.assertIn('app_qss("dark")',text)
        self.assertIn('apply_nav_button_contract',text)
        self.assertIn('install_keyboard_focus_ring',text)
        self.assertNotIn('customtkinter',text.lower())

if __name__ == '__main__': unittest.main()
