from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.13_phase01_verification_ci_fix_scope.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class V10613Phase01VerificationFixTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scope = json.loads(SCOPE.read_text(encoding="utf-8"))

    def test_scope_locks_exact_v10612_baseline_and_no_runtime_changes(self):
        self.assertEqual(
            self.scope["official_baseline_archive_sha256"],
            "becd6add21d377e98e458ce856c9c3baa710a113459bde0c737507c122c2a9b5",
        )
        self.assertEqual(
            self.scope["official_baseline_github_commit"],
            "a9cfec319285db2fb9fbff8d4bf0ede8ac87686b",
        )
        self.assertEqual(self.scope["target_version"], "1.0.6.13")
        self.assertEqual(self.scope["allowed_runtime_source_changes"], [])

    def test_phase01_runtime_and_task_store_are_byte_frozen(self):
        current_scope = ROOT / "config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json"
        pr08_scope = ROOT / "config/verification/v1.0.6.25_pr08_dynamic_workflow_inputs_scope.json"
        current_allowed = set()
        if current_scope.is_file():
            current_allowed = set(json.loads(current_scope.read_text(encoding="utf-8")).get("allowed_runtime_source_changes", []))
        if pr08_scope.is_file():
            current_allowed |= set(json.loads(pr08_scope.read_text(encoding="utf-8")).get("allowed_production_source_changes", []))
        for relative, expected in self.scope["frozen_runtime_file_sha256"].items():
            if relative in current_allowed:
                continue
            self.assertEqual(sha256(ROOT / relative), expected, relative)

    def test_concurrency_test_is_correctness_guard_not_15_second_throughput_sla(self):
        path = ROOT / "tests" / "test_task_runtime_store.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        timeout_value = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "CONCURRENT_STORE_TEST_TIMEOUT_SECONDS":
                        timeout_value = ast.literal_eval(node.value)
        self.assertEqual(float(self.scope["concurrency_test_timeout_seconds"]), 60.0)
        self.assertGreaterEqual(float(timeout_value), 60.0)
        self.assertIn("time.monotonic()", source)
        self.assertIn("ignore_cleanup_errors=True", source)
        self.assertNotIn("thread.join(timeout=15)", source)

    def test_phase01_contract_remains_present_and_unchanged(self):
        phase01 = ROOT / "config" / "verification" / "v1.0.6.12_browser_ui_lifecycle_scope.json"
        self.assertEqual(
            sha256(phase01),
            self.scope["frozen_runtime_file_sha256"][
                "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json"
            ],
        )


if __name__ == "__main__":
    unittest.main()
