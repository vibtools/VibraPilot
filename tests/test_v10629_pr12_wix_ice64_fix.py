from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
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
    (ROOT / "config/verification/v1.0.6.29_pr12_cycle2_directory_identity_fix_scope.json")
    .read_text(encoding="utf-8")
)
NS = {"w": "http://wixtoolset.org/schemas/v4/wxs"}


class PR12WixIce64Cycle2FixTest(unittest.TestCase):
    def test_cycle2_baseline_and_scope_are_exact(self):
        self.assertEqual(SCOPE["plan_id"], "VP-PR12-CYCLE2-WIX-DIRECTORY-IDENTITY-001")
        self.assertEqual(SCOPE["baseline_commit"], "23b55b3d7a175c24fa9630340ab57ff6786d785a")
        self.assertEqual(SCOPE["baseline_tree"], "b1ffcf4c25971e588442f8c31e3eaadbe6242d78")
        self.assertEqual(SCOPE["cycle1_workflow_run"], 31554989777)
        self.assertEqual(SCOPE["cycle1_result"], "FAIL")
        self.assertEqual(SCOPE["primary_error_id"], "PR12-PACKAGING-ICE64-001")
        self.assertEqual(SCOPE["fatal_code"], "WIX0204 / ICE64")
        self.assertEqual(SCOPE["current_cycle"], 2)
        self.assertTrue(SCOPE["cycle2_is_final_allowed_cycle"])
        self.assertFalse(SCOPE["production_runtime_changes_allowed"])
        self.assertFalse(SCOPE["build_py_changes_allowed"])
        self.assertFalse(SCOPE["installer_static_wxs_changes_allowed"])
        self.assertFalse(SCOPE["existing_ci_workflow_changes_allowed"])
        self.assertFalse(SCOPE["github_push_by_assistant_allowed"])
        self.assertFalse(SCOPE["github_pr_by_assistant_allowed"])

    def test_payload_directory_inventory_includes_all_ancestors_once(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "a/b/c").mkdir(parents=True)
            (payload / "a/b/c/x.dll").write_bytes(b"x")
            (payload / "a/y.dat").write_bytes(b"y")
            self.assertEqual(adapter._payload_directories(payload), ["a", "a/b", "a/b/c"])

    def test_explicit_directory_tree_eliminates_inline_subdirectory_authoring(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "a/b").mkdir(parents=True)
            (payload / "VibraPilot.exe").write_bytes(b"exe")
            (payload / "a/b/x.dll").write_bytes(b"x")
            generated = Path(td) / "files.wxs"
            adapter.generate_explicit_wix_file_fragment(payload, generated)
            text = generated.read_text(encoding="utf-8")

            self.assertNotIn("Subdirectory=", text)
            self.assertIn('<DirectoryRef Id="INSTALLFOLDER">', text)
            self.assertIn(f'<Directory Id="{adapter._directory_id("a")}" Name="a">', text)
            self.assertIn(f'<Directory Id="{adapter._directory_id("a/b")}" Name="b">', text)
            self.assertIn(
                f'Directory="{adapter._directory_id("a/b")}">',
                text,
            )
            self.assertNotIn("RemoveFolderEx", text)
            self.assertNotIn("<RemoveFile", text)

    def test_every_explicit_payload_directory_has_same_identity_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "a/b/c").mkdir(parents=True)
            (payload / "z").mkdir(parents=True)
            (payload / "root.exe").write_bytes(b"root")
            (payload / "a/b/c/x.dll").write_bytes(b"x")
            (payload / "z/y.dat").write_bytes(b"y")
            generated = Path(td) / "files.wxs"
            adapter.generate_explicit_wix_file_fragment(payload, generated)

            root = ET.parse(generated).getroot()
            explicit_ids = {
                node.attrib["Id"]
                for node in root.findall(".//w:Directory", NS)
            }
            expected_ids = {
                adapter._directory_id(relative)
                for relative in adapter._payload_directories(payload)
            }
            self.assertEqual(explicit_ids, expected_ids)

            cleanup_targets: set[str] = set()
            for component in root.findall(".//w:Component", NS):
                component_directory = component.attrib.get("Directory")
                for remove in component.findall("w:RemoveFolder", NS):
                    cleanup_targets.add(remove.attrib.get("Directory", component_directory))

            self.assertTrue(expected_ids.issubset(cleanup_targets))
            for static_id in ("INSTALLFOLDER", "VibToolsFolder", "PerUserProgramFilesFolder"):
                self.assertIn(static_id, cleanup_targets)

    def test_file_components_reference_root_or_explicit_directory_ids_only(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "alpha/beta").mkdir(parents=True)
            (payload / "root.exe").write_bytes(b"root")
            (payload / "alpha/beta/nested.dll").write_bytes(b"nested")
            generated = Path(td) / "files.wxs"
            adapter.generate_explicit_wix_file_fragment(payload, generated)

            root = ET.parse(generated).getroot()
            explicit_ids = {
                node.attrib["Id"]
                for node in root.findall(".//w:Directory", NS)
            }
            file_component_dirs = set()
            for component in root.findall(".//w:Component", NS):
                if component.find("w:File", NS) is not None:
                    file_component_dirs.add(component.attrib["Directory"])
            self.assertEqual(
                file_component_dirs,
                {"INSTALLFOLDER", adapter._directory_id("alpha/beta")},
            )
            self.assertTrue(file_component_dirs.issubset(explicit_ids | {"INSTALLFOLDER"}))

    def test_generation_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            payload = Path(td) / "payload"
            (payload / "z/a").mkdir(parents=True)
            (payload / "z/a/x.dat").write_bytes(b"x")
            (payload / "b.dat").write_bytes(b"b")
            a = Path(td) / "a.wxs"
            b = Path(td) / "b.wxs"
            adapter.generate_explicit_wix_file_fragment(payload, a)
            adapter.generate_explicit_wix_file_fragment(payload, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_existing_workflow_runs_targeted_test_then_adapter_only(self):
        workflow = (ROOT / ".github/workflows/pr12-package-build.yml").read_text(encoding="utf-8")
        self.assertIn("python tests/test_v10629_pr12_wix_ice64_fix.py", workflow)
        self.assertIn("run: python scripts/packaging/pr12_package_build.py", workflow)
        self.assertNotIn("run: python build.py", workflow)
        self.assertNotIn("CL Automation", workflow)
        self.assertNotIn("tags:", workflow)


if __name__ == "__main__":
    unittest.main()
