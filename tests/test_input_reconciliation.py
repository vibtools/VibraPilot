from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot.data_io import parse_data, parse_data_with_audit


class InputReconciliationTest(unittest.TestCase):
    def test_txt_reconciliation_preserves_baseline_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.txt"
            path.write_text(
                "a@example.com\ninvalid\nA@example.com\nb@example.com\n\n",
                encoding="utf-8",
            )
            baseline = parse_data(path)
            audit = parse_data_with_audit(path, remove_duplicates=True)
            self.assertEqual(len(baseline), 3)
            self.assertEqual(audit.source_rows, 5)
            self.assertEqual(audit.valid_rows, 3)
            self.assertEqual(audit.invalid_rows, 2)
            self.assertEqual(audit.duplicate_rows, 1)
            self.assertEqual(audit.accepted_rows, 2)
            self.assertEqual([item.email for item in audit.items], ["a@example.com", "b@example.com"])
            self.assertEqual(len(audit.source_fingerprint), 64)
            retained = parse_data_with_audit(path, remove_duplicates=False)
            self.assertEqual(retained.duplicate_rows, 1)
            self.assertEqual(retained.accepted_rows, 3)


if __name__ == "__main__":
    unittest.main()
