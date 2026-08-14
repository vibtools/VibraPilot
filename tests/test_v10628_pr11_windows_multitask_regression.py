from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "scripts" / "diagnostics" / "pr11_windows_acceptance_runner.py"
VERIFY_PATH = ROOT / "scripts" / "diagnostics" / "verify_pr11_windows_evidence.py"
SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.28_pr11_windows_multitask_regression_scope.json"
V10630_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.30_workflow_plugin_system_scope.json"
V10631_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.31_chrome_only_browser_runtime_scope.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PR11WindowsAcceptanceToolingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_module(RUNNER_PATH, "pr11_acceptance_runner")

    def test_exact_35_gate_matrix_and_fallback_gate_is_residual_eligible(self):
        self.assertEqual(len(self.runner.GATES), 35)
        ids = [gate[0] for gate in self.runner.GATES]
        self.assertEqual(ids, [f"G{i:02d}" for i in range(1, 36)])
        mandatory = {gate_id: required for gate_id, _title, required in self.runner.GATES}
        self.assertFalse(mandatory["G33"])
        self.assertTrue(all(mandatory[g] for g in ids if g != "G33"))

    def test_status_vocabulary_is_exact_and_residual_needs_explicit_owner_acceptance(self):
        self.assertEqual(
            self.runner.ALLOWED_STATUSES,
            {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "OWNER_ACCEPTED_RESIDUAL"},
        )
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            gates = {
                gate_id: {
                    "title": title, "mandatory": required, "status": "NOT_RUN",
                    "note": "", "updated_at": None, "owner_accepted": False, "evidence": [],
                }
                for gate_id, title, required in self.runner.GATES
            }
            self.runner.write_json_atomic(run_dir / "gates.json", {"schema_version": 1, "gates": gates})
            with self.assertRaises(ValueError):
                self.runner.record_gate(run_dir, "G33", "OWNER_ACCEPTED_RESIDUAL", "blocked safely")
            self.runner.record_gate(
                run_dir, "G33", "OWNER_ACCEPTED_RESIDUAL", "owner accepted fallback residual",
                owner_accepted=True,
            )
            saved = self.runner.load_json(run_dir / "gates.json")
            self.assertTrue(saved["gates"]["G33"]["owner_accepted"])

    def test_summary_fails_on_fail_and_blocks_on_mandatory_not_run(self):
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            gates = {
                gate_id: {
                    "title": title, "mandatory": required, "status": "PASS",
                    "note": "", "updated_at": None, "owner_accepted": False, "evidence": [],
                }
                for gate_id, title, required in self.runner.GATES
            }
            self.runner.write_json_atomic(run_dir / "gates.json", {"schema_version": 1, "gates": gates})
            status, problems = self.runner.summarize(run_dir)
            self.assertEqual(status, "PASS")
            self.assertEqual(problems, [])
            self.runner.record_gate(run_dir, "G22", "NOT_RUN", "")
            status, _ = self.runner.summarize(run_dir)
            self.assertEqual(status, "BLOCKED")
            self.runner.record_gate(run_dir, "G22", "FAIL", "reproducible")
            status, _ = self.runner.summarize(run_dir)
            self.assertEqual(status, "FAIL")

    def test_fixture_download_is_deterministic(self):
        payload = self.runner.TEST_DOWNLOAD
        self.assertEqual(payload, b"VibraPilot PR-11 deterministic download fixture\n")
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "38c5b4f69c4105ac8bbdfdea8ebaaf6e526710f23de445acd91b7487bef4842e",
        )

    def test_browser_capture_keeps_only_sanitized_identity_fields(self):
        raw = {
            "slot_id": 2,
            "actual": {
                "engine": "google_chrome", "product": "Chrome/140", "pid": 123,
                "executable_path": r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "profile_path": r"D:\\safe\\BrowserProfiles\\slot_2",
                "command_line": "--token=SECRET --password=SECRET",
                "cookies": ["SECRET"],
            },
            "requested": {"profile_path": r"D:\\safe\\BrowserProfiles\\slot_2", "sandbox_enabled": False},
            "launch": {"fallback_used": False, "fallback_reason": ""},
            "playwright": {"actual_version": "1.61.0", "expected_version": "1.61.0"},
        }
        clean = self.runner.sanitize_browser_record(raw)
        blob = json.dumps(clean)
        self.assertNotIn("SECRET", blob)
        self.assertNotIn("command_line", blob)
        self.assertNotIn("cookies", blob)
        self.assertEqual(clean["actual"]["pid"], 123)
        self.assertEqual(clean["actual"]["engine"], "google_chrome")

    def test_safe_kill_requires_exact_pid_and_managed_profile_marker(self):
        text = RUNNER_PATH.read_text(encoding="utf-8")
        self.assertIn('if not isinstance(pid, int) or pid <= 0 or pid != expected_pid:', text)
        self.assertIn('if "BrowserProfiles" not in profile and "VibraPilot" not in profile:', text)
        self.assertIn('["taskkill", "/PID", str(pid), "/T", "/F"]', text)
        self.assertNotIn('taskkill", "/IM", "chrome.exe"', text)

    def test_runner_never_writes_production_defaults_or_deletes_runtime_roots(self):
        text = RUNNER_PATH.read_text(encoding="utf-8")
        forbidden_mutations = [
            'settings.defaults.json", "w"',
            'shutil.rmtree(data_root',
            'shutil.rmtree(root / "AppData"',
            'BrowserProfiles).unlink',
            'chrome.exe", "/F"',
        ]
        for marker in forbidden_mutations:
            self.assertNotIn(marker, text)
        self.assertIn('AppData" / "PR11Acceptance"', text)

    def test_scope_contract_freezes_zero_production_changes(self):
        scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(scope["plan_id"], "VP-PR11-WINDOWS-MULTITASK-E2E-001")
        self.assertEqual(scope["baseline_version"], "1.0.6.27")
        self.assertEqual(scope["target_version"], "1.0.6.28")
        self.assertEqual(scope["allowed_production_source_changes"], [])
        self.assertEqual(scope["production_runtime_changes"], "none")
        self.assertEqual(scope["production_workflows"], ["share_invite"])
        self.assertEqual(scope["evidence_status_values"], [
            "PASS", "FAIL", "BLOCKED", "NOT_RUN", "OWNER_ACCEPTED_RESIDUAL"
        ])
        self.assertTrue(scope["captcha_deferred_unverified"])
        self.assertFalse(scope["packaging_implementation"])
        self.assertTrue(scope["pr12_not_started"])

    def test_evidence_verifier_is_read_only_and_requires_all_mandatory_gates(self):
        text = VERIFY_PATH.read_text(encoding="utf-8")
        self.assertIn('MANDATORY = {f"G{i:02d}" for i in range(1, 36)} - {"G33"}', text)
        self.assertIn('if gate in MANDATORY and status != "PASS" and status != "OWNER_ACCEPTED_RESIDUAL":', text)
        self.assertNotIn("write_text(", text)
        self.assertNotIn("unlink(", text)
        self.assertNotIn("rmtree(", text)


class PR11FrozenRuntimeContractTest(unittest.TestCase):
    def test_no_pr11_production_runtime_source_change_is_permitted(self):
        scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
        hashes = scope["frozen_production_sha256"]
        current = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "src" / "vibrapilot").rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
        )
        v10630_scope = json.loads(V10630_SCOPE_PATH.read_text(encoding="utf-8")) if V10630_SCOPE_PATH.is_file() else {}
        v10631_scope = json.loads(V10631_SCOPE_PATH.read_text(encoding="utf-8")) if V10631_SCOPE_PATH.is_file() else {}
        current_allowed = (
            set(v10630_scope.get("allowed_production_source_changes", []))
            | set(v10631_scope.get("allowed_production_source_changes", []))
        )
        historical = set(hashes)
        current_set = set(current)
        self.assertTrue(historical.issubset(current_set), sorted(historical - current_set))
        self.assertTrue((current_set - historical).issubset(current_allowed), sorted(current_set - historical - current_allowed))
        for rel, expected in hashes.items():
            if rel in current_allowed:
                continue
            actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, rel)

    def test_settings_dependencies_and_ci_are_frozen(self):
        scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
        v10630_scope = json.loads(V10630_SCOPE_PATH.read_text(encoding="utf-8")) if V10630_SCOPE_PATH.is_file() else {}
        v10631_scope = json.loads(V10631_SCOPE_PATH.read_text(encoding="utf-8")) if V10631_SCOPE_PATH.is_file() else {}
        current_allowed = (
            set(v10630_scope.get("authorized_nonproduction_files", []))
            | set(v10631_scope.get("authorized_nonproduction_files", []))
        )
        for rel, expected in scope["frozen_nonproduction_runtime_sha256"].items():
            if rel in current_allowed:
                continue
            actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, rel)


if __name__ == "__main__":
    unittest.main()
