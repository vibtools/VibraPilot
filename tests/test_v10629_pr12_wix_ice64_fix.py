from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build

SPEC = importlib.util.spec_from_file_location(
    "pr12_package_build", ROOT / "scripts/packaging/pr12_package_build.py"
)
adapter = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(adapter)

SCOPE = json.loads(
    (ROOT / "config/verification/v1.0.6.29_pr12_wix_ice64_root_cause_scope.json")
    .read_text(encoding="utf-8")
)
BASELINE = json.loads(
    (ROOT / "config/verification/v1.0.6.29_pr12_prefx_forensic_baseline.json")
    .read_text(encoding="utf-8")
)


class PR12WixIce64FixTest(unittest.TestCase):
    def test_forensic_baseline_and_root_cause_scope_are_exact(self):
        self.assertEqual(BASELINE["commit_sha"], "ac387257792863c58216cf1fca31dff0af9d889d")
        self.assertEqual(BASELINE["tree_sha"], "51a7186b29344827cc4626d3f72a9e5d844caff5")
        self.assertEqual(SCOPE["primary_error_id"], "PR12-PACKAGING-ICE64-001")
        self.assertEqual(SCOPE["fatal_code"], "WIX0204 / ICE64")
        self.assertEqual(SCOPE["current_cycle"], 1)
        self.assertFalse(SCOPE["production_runtime_changes_allowed"])
        self.assertFalse(SCOPE["build_py_changes_allowed"])
        self.assertFalse(SCOPE["installer_static_wxs_changes_allowed"])
        self.assertFalse(SCOPE["recursive_or_wildcard_uninstall_cleanup_allowed"])

    def test_payload_directory_inventory_includes_all_ancestors_once(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "a/b/c").mkdir(parents=True)
            (payload / "a/b/c/x.dll").write_bytes(b"x")
            (payload / "a/y.dat").write_bytes(b"y")
            self.assertEqual(adapter._payload_directories(payload), ["a", "a/b", "a/b/c"])

    def test_generated_wix_has_empty_folder_cleanup_for_static_and_nested_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "a/b").mkdir(parents=True)
            (payload / "VibraPilot.exe").write_bytes(b"exe")
            (payload / "a/b/x.dll").write_bytes(b"x")
            generated = Path(td) / "files.wxs"
            build.generate_wix_file_fragment(payload, generated)
            adapter._augment_generated_wix(payload, generated)
            text = generated.read_text(encoding="utf-8")

            self.assertEqual(text.count("<RemoveFolder"), 5)
            for directory in ("INSTALLFOLDER", "VibToolsFolder", "PerUserProgramFilesFolder"):
                self.assertIn(f'Directory="{directory}" On="uninstall"', text)
            self.assertIn('Subdirectory="a"', text)
            self.assertIn('Subdirectory="a\\b"', text)
            self.assertNotIn('On="install"', text)
            self.assertNotIn('On="both"', text)
            self.assertNotIn("RemoveFolderEx", text)
            self.assertNotIn("<RemoveFile", text)

    def test_cleanup_authoring_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "z/a").mkdir(parents=True)
            (payload / "z/a/x.dat").write_bytes(b"x")
            a = Path(td) / "a.wxs"
            b = Path(td) / "b.wxs"
            build.generate_wix_file_fragment(payload, a)
            build.generate_wix_file_fragment(payload, b)
            adapter._augment_generated_wix(payload, a)
            adapter._augment_generated_wix(payload, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_workflow_runs_targeted_fix_test_then_adapter_not_direct_build(self):
        workflow = (ROOT / ".github/workflows/pr12-package-build.yml").read_text(encoding="utf-8")
        self.assertIn("python tests/test_v10629_pr12_wix_ice64_fix.py", workflow)
        self.assertIn("run: python scripts/packaging/pr12_package_build.py", workflow)
        self.assertNotIn("run: python build.py", workflow)
        self.assertNotIn("CL Automation", workflow)
        self.assertNotIn("tags:", workflow)


if __name__ == "__main__":
    unittest.main()
