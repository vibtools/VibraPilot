from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from vibrapilot import backend

SCOPE = json.loads((ROOT / "config/verification/v1.0.6.29_pr12_packaging_scope.json").read_text(encoding="utf-8"))

spec = importlib.util.spec_from_file_location("pr12_build", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(build)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PR12PackagingScopeTest(unittest.TestCase):
    def test_scope_identity_and_toolchain(self):
        self.assertEqual(SCOPE["plan_id"], "VP-PR12-PACKAGING-001")
        self.assertEqual(SCOPE["official_baseline_archive_sha256"], "e8fb841a9127eccf3302a840d7c414fdee7a30e16ba735d2080fc999a5af88c3")
        self.assertEqual(SCOPE["baseline_github_commit"], "fff8160157d4d9b68b2d28b11105b0f7f38ed17d")
        self.assertEqual(SCOPE["target_version"], "1.0.6.29")
        self.assertEqual(SCOPE["allowed_production_source_changes"], ["src/vibrapilot/backend.py"])
        self.assertEqual(SCOPE["nuitka_version"], "4.1.3")
        self.assertEqual(SCOPE["wix_version"], "6.0.2")
        self.assertEqual(SCOPE["build_execution"], "github_actions_only")
        self.assertTrue(SCOPE["github_actions_packaging"])
        self.assertFalse(SCOPE["local_pc_build"])
        self.assertFalse(SCOPE["local_pc_wix_required"])
        self.assertTrue(SCOPE["wix_ci_ephemeral_install"])
        self.assertFalse(SCOPE["wix_eula_acceptance_automated"])
        self.assertEqual(SCOPE["error_fix_verify_max_cycles_per_primary_error"], 2)

    def test_out_of_scope_production_files_are_byte_frozen(self):
        for rel, expected in SCOPE["frozen_production_sha256"].items():
            self.assertEqual(sha256(ROOT / rel), expected, rel)
        for rel, expected in SCOPE["frozen_runtime_and_policy_sha256"].items():
            self.assertEqual(sha256(ROOT / rel), expected, rel)

    def test_backend_change_is_confined_to_packaged_root_block(self):
        text = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        start = text.index("# PR-12 packaging compatibility:")
        end = text.index("DATA_ROOT_DIR = (\n")
        normalized = text[:start] + "<PR12_AUTHORIZED_PACKAGED_ROOT_BLOCK>\n" + text[end:]
        self.assertEqual(hashlib.sha256(normalized.encode()).hexdigest(), SCOPE["backend_normalized_frozen_sha256"])
        self.assertIn("_NUITKA_COMPILED = __compiled__", text[start:end])
        self.assertIn('getattr(_NUITKA_COMPILED, "containing_dir", None)', text[start:end])
        self.assertIn('getattr(sys, "frozen", False)', text[start:end])
        self.assertIn('getattr(sys, "_MEIPASS"', text[start:end])

    def test_application_root_resolution_preserves_nuitka_pyinstaller_source_order(self):
        text = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
        block = text[text.index("# PR-12 packaging compatibility:"):text.index("DATA_ROOT_DIR = (\n")]
        self.assertLess(block.index("_NUITKA_COMPILED is not None"), block.index('getattr(sys, "frozen", False)'))
        self.assertLess(block.index('getattr(sys, "frozen", False)'), block.index('Path(__file__).resolve().parents[2]'))
        self.assertNotIn("def _application_root_dir", block)
        self.assertEqual(backend.ROOT_DIR, ROOT.resolve())

    def test_build_requirements_pin_nuitka_and_remove_pyinstaller(self):
        text = (ROOT / "requirements-build.txt").read_text(encoding="utf-8")
        self.assertIn("Nuitka==4.1.3", text)
        self.assertNotIn("pyinstaller", text.lower())

    def test_build_pipeline_is_nuitka_standalone_and_wix_602(self):
        text = (ROOT / "build.py").read_text(encoding="utf-8")
        for marker in (
            'NUITKA_VERSION = "4.1.3"', 'WIX_VERSION = "6.0.2"',
            '"--mode=standalone"', '"--enable-plugin=pyside6"',
            '"--windows-console-mode=disable"', '"--mingw64"',
            '"--assume-yes-for-downloads"', '"ms-playwright"',
            '"msi", "validate"', 'GITHUB_ACTIONS',
            '"provider": "github_actions"', '"google_chrome_preferred": True',
        ):
            self.assertIn(marker, text)
        self.assertNotIn("PyInstaller", text)
        self.assertNotIn("pyinstaller", text.lower())
        self.assertIn("never installs WiX or accepts WiX license/EULA terms automatically", text)
        self.assertIn("package builds are authorized only in GitHub Actions", text)

    def test_msi_version_mapping(self):
        self.assertEqual(build.msi_product_version("1.0.6.29"), "1.0.629")
        self.assertEqual(build.msi_product_version("1.0.6.30"), "1.0.630")
        self.assertEqual(build.msi_product_version("1.0.7.0"), "1.0.700")
        with self.assertRaises(build.BuildError):
            build.msi_product_version("1.0.6")

    def test_wix_authoring_is_per_user_with_upgrade_and_no_runtime_cleanup(self):
        path = ROOT / "installer/VibraPilot.wxs"
        tree = ET.parse(path)
        ns = {"w": "http://wixtoolset.org/schemas/v4/wxs"}
        package = tree.getroot().find("w:Package", ns)
        self.assertIsNotNone(package)
        self.assertEqual(package.attrib["Scope"], "perUser")
        self.assertEqual(package.attrib["Version"], "$(var.MsiVersion)")
        self.assertEqual(package.attrib["UpgradeCode"], SCOPE["msi_upgrade_code"])
        self.assertIsNotNone(package.find("w:MajorUpgrade", ns))
        standard = package.find("w:StandardDirectory[@Id='PerUserProgramFilesFolder']", ns)
        self.assertIsNotNone(standard)
        text = path.read_text(encoding="utf-8")
        for forbidden in ("AppData", "BrowserProfiles", "Downloads", "Reports", "FailedData", "RemoveFile", "RemoveFolder"):
            self.assertNotIn(forbidden, text)

    def test_generated_wix_components_are_deterministic_and_registry_keyed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "payload"
            (root / "sub").mkdir(parents=True)
            (root / "VibraPilot.exe").write_bytes(b"exe")
            (root / "sub" / "x.dat").write_bytes(b"data")
            a = Path(td) / "a.wxs"
            b = Path(td) / "b.wxs"
            build.generate_wix_file_fragment(root, a)
            build.generate_wix_file_fragment(root, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            text = a.read_text(encoding="utf-8")
            self.assertIn('Directory="INSTALLFOLDER"', text)
            self.assertIn('Root="HKCU"', text)
            self.assertIn('KeyPath="yes"', text)
            self.assertIn('!(bindpath.PayloadRoot)', text)

    def test_pr12_github_packaging_workflow_and_pr13_boundary(self):
        self.assertFalse(SCOPE["cl_automation_implemented"])
        self.assertTrue(SCOPE["pr13_not_started"])
        self.assertTrue(SCOPE["pr14_not_started"])
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("CL Automation", ci)
        workflow = (ROOT / ".github/workflows/pr12-package-build.yml").read_text(encoding="utf-8")
        self.assertIn("name: PR-12 Package Build", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("branches: ['pr12-*']", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("runs-on: windows-2025", workflow)
        self.assertIn("python-version: '3.12.10'", workflow)
        self.assertIn("wix --version 6.0.2", workflow)
        self.assertIn("python build.py", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("VibraPilot-1.0.6.29-PR12-Windows-x64", workflow)
        self.assertNotIn("CL Automation", workflow)
        self.assertNotIn("tags:", workflow)
        self.assertNotIn("release", workflow.lower().split("name: pr-12 package build", 1)[0])

    def test_pc_acceptance_runner_never_builds_or_requires_wix(self):
        text = (ROOT / "scripts/diagnostics/pr12_packaging_acceptance_runner.py").read_text(encoding="utf-8")
        self.assertIn("never builds the application", text)
        self.assertIn("--artifacts", text)
        self.assertIn("MANUAL PACKAGED-BROWSER ACCEPTANCE REQUIRED", text)
        self.assertIn("Type PASS and press Enter", text)
        self.assertNotIn("python build.py", text)
        self.assertNotIn("locate_wix", text)
        self.assertNotIn("WIX_EXE", text)

    def test_ci_artifact_verifier_requires_github_provenance(self):
        text = (ROOT / "scripts/diagnostics/pr12_ci_package_artifact_verify.py").read_text(encoding="utf-8")
        self.assertIn("PR12 CI ARTIFACT VERIFY: PASS", text)
        self.assertIn("github_actions", text)
        self.assertIn("PR-12 Package Build", text)


if __name__ == "__main__":
    unittest.main()
