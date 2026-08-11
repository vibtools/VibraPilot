#!/usr/bin/env python3
"""Static release verifier for VibraPilot Vib Tools desktop edition.

This verifier deliberately avoids importing PySide6 so it can run in lightweight
CI environments. It verifies the frozen Vib Tools design contract, backend API
parity against the preserved v1.0.6 source baseline, Phase-02 Secure Licora API v2
client integration, and key safety invariants.
"""
from __future__ import annotations

import ast
import hashlib
import json
import py_compile
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "vibrapilot"
PRIVATE_BASELINE = ROOT / "project" / "research" / "source_baseline" / "VibraPilot_v1.0.6_original_app.py"
BACKEND_CONTRACT = ROOT / "config" / "verification" / "backend_v1.0.6_contract.json"
FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "phase02_step002_v1.0.6.4_fix_scope.json"
PRODUCTION_SCOPE_CONTRACT = ROOT / "config" / "verification" / "production_mt_lr_v1.0.6.5_scope.json"
CURRENT_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.7_vp_prod_mt_lr_verification_fix_scope.json"
WINDOWS_SQLITE_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.7_windows_sqlite_concurrency_fix_scope.json"
WORKFLOW_INPUTS_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.8_workflow_inputs_scope.json"
WORKFLOW_INPUTS_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.9_workflow_inputs_verification_fix_scope.json"
LICENSE_LOGIN_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.10_license_login_fix_scope.json"
QT_FOCUS_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.11_qt_focus_lifecycle_fix_scope.json"
BROWSER_UI_LIFECYCLE_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.12_browser_ui_lifecycle_scope.json"
PHASE01_VERIFICATION_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.13_phase01_verification_ci_fix_scope.json"
MANAGED_BROWSER_CLOSED_TASK_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.14_managed_persistent_browser_closed_task_scope.json"
WORKSPACE_PERSISTENCE_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.15_workspace_persistence_scope.json"
WORKSPACE_PERSISTENCE_VERIFICATION_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.16_workspace_persistence_verification_fix_scope.json"
BROWSER_CAPABILITIES_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.17_browser_capabilities_scope.json"
TASKS_UI_POLISH_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.17_tasks_ui_polish_scope.json"
BROWSER_FOUNDATION_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.18_browser_foundation_scope.json"
BROWSER_FOUNDATION_VERIFICATION_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.19_browser_foundation_verification_fix_scope.json"
CHROME_WEBSTORE_EXTENSION_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.19_chrome_webstore_extension_install_fix_scope.json"
PR04_SHARE_INVITE_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.20_pr04_share_invite_workflow_extraction_scope.json"
PR04_CI_PORTABILITY_FIX_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.21_pr04_ci_portability_fix_scope.json"
PR05_MASTER_WORKFLOW_GATE_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.22_pr05_master_workflow_gate_scope.json"
PR06_WORKFLOW_STATE_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.23_pr06_workflow_state_atomic_switch_scope.json"
PR07_WORKFLOW_SHOWCASE_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.24_pr07_workflow_showcase_scope.json"
PR08_DYNAMIC_WORKFLOW_INPUTS_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.25_pr08_dynamic_workflow_inputs_scope.json"
PR09_DATA_COMPATIBILITY_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.26_pr09_data_persistence_reporting_compatibility_scope.json"
PR10_WORKFLOW_ERROR_RECOVERY_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.27_pr10_workflow_error_recovery_scope.json"
PR11_WINDOWS_MULTITASK_SCOPE_CONTRACT = ROOT / "config" / "verification" / "v1.0.6.28_pr11_windows_multitask_regression_scope.json"
APP_CONFIG_ROOT = ROOT / "config" / "AppConfig"
APP_CONFIG_APP = APP_CONFIG_ROOT / "app.py"

EXPECTED_BRAND_HASHES = {
    "vib_validation_app/tokens.py": "cdae402dccdb8e916f274ea5fa0b8ec1a6505fab6043462d35af8a93e1468a02",
    "vib_validation_app/styles.py": "83729e5b0e811e6b0cc4943dc729cbcf0cad92657eacbaebaacc0e0f56e3877b",
    "vib_validation_app/widgets.py": "5f13404bc98a053edb1ebd63760cd185632cbe84041594b7c4f5821043a3495d",
    "vib_validation_app/button_contract.py": "89bd33cbbfa00497a223e6ea5493e8aa4745d556e23447e28a0001c673381ce0",
    "vib_validation_app/focus_manager.py": "a073051b05cbd2442b0bdec0a1251cf8185b54cbb71e755cc25c2ee85ce7f86e",
    "frozen_design_source/CURRENT_FOUNDATION_TOKENS.json": "cbf1636b53a85c30dae839379653b6bbe0d0065e8f37cd919acaeb0c491e7616",
    "vib_validation_app/assets/icons/check.svg": "4aea38b95354030a63723f7e7f975e4d6a5b8a4f132a4bcda9a1a71a26c692e8",
    "vib_validation_app/assets/icons/chevron-down.svg": "d1a1f4bb388efe49cd5eff9d69361bdbac45d520e34ca4d11ed39b4256de87f6",
    "vib_validation_app/assets/icons/chevron-right.svg": "d27e0e90a22a13c5e8819cc6fef6336af4b610dc56446eb8199520bd36c2647c",
    "vib_validation_app/assets/icons/eye-off.svg": "e7b5de55df91771e85ab883f8ec317e952c1564903ccafb9d9722f2dd5061966",
    "vib_validation_app/assets/icons/eye.svg": "7619e35daa0f07351d52ca767a34ef83dc28b1ab854d9ce3bde7fa1531220316",
    "vib_validation_app/assets/icons/file.svg": "97cebfee4e4ba941551bbb8cee82091f1bc503f391382031804b65eae20f9d54",
    "vib_validation_app/assets/icons/folder.svg": "aecea0312a8cc0d2262a2a4eecd0341f53143259ea414db608d5372c432febd2",
    "vib_validation_app/assets/icons/minus.svg": "e09274e14616fe817b871cf923f05927e8b20b950d18f0bd0e208df1409d7747",
    "vib_validation_app/assets/icons/search.svg": "9df656e9653d7f14dec864af3d3b759e4fa105725dacbcab6c538f988c45b3ff",
}

CORE_CLASSES = [
    "SettingsManager", "LicenseManager", "TaskItem", "TaskState", "AutomationWorker",
    "SecurityChallenge", "SessionVerificationError", "TestModeRequired",
    "TestSendLimitReached", "SendClickOutcomeUncertain", "InviteRejected",
]


def fail(msg: str) -> None:
    raise SystemExit(f"VERIFY FAILED: {msg}")


def sha256(path: Path) -> str:
    """Return a cross-platform stable SHA-256 for frozen text contract files.

    Git may materialize LF-tracked text as CRLF on Windows when no explicit
    checkout policy is present. The frozen design contract is source-content
    based, so canonicalize CRLF to LF before hashing instead of treating the
    checkout platform as a design change.
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def top_functions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def class_methods(path: Path) -> dict[str, list[str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: dict[str, list[str]] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            out[node.name] = [
                n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]
    return out


def function_nodes(path: Path) -> dict[str, ast.FunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

def class_nodes(path: Path) -> dict[str, ast.ClassDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}

def assignment_nodes(path: Path) -> dict[str, ast.Assign]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: dict[str, ast.Assign] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    out[target.id] = node
    return out

def annotated_assignment_nodes(path: Path) -> dict[str, ast.AnnAssign]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.target.id: node
        for node in tree.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    try:
                        return ast.literal_eval(node.value)
                    except Exception:
                        return None
    return None


AST_HASH_ALGORITHM = "canonical-semantic-ast-v2"


def _canonical_ast_value(value):
    """Return a Python-version-stable semantic representation of an AST value.

    CPython may add optional/empty AST fields between minor versions (for example
    ``type_params`` on ClassDef/FunctionDef). Raw ``ast.dump()`` output therefore
    is not a portable release hash. Empty/None fields are omitted while real
    semantic values and node types remain part of the contract.
    """
    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            if child is None or child == [] or child == ():
                continue
            fields.append([name, _canonical_ast_value(child)])
        return [value.__class__.__name__, fields]
    if isinstance(value, list):
        return [_canonical_ast_value(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical_ast_value(item) for item in value]
    return value


def ast_contract_sha(node: ast.AST) -> str:
    payload = json.dumps(
        _canonical_ast_value(node),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(AST_HASH_ALGORITHM.encode("ascii") + b"\0" + payload).hexdigest()


if not PR06_WORKFLOW_STATE_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.23 PR-06 workflow-state scope contract is missing")
try:
    pr06_scope = json.loads(PR06_WORKFLOW_STATE_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.23 PR-06 workflow-state scope contract is invalid: {exc}")
if pr06_scope.get("plan_id") != "VP-PR06-WORKFLOW-STATE-ATOMIC-SWITCH-001":
    fail("v1.0.6.23 PR-06 plan identifier mismatch")
if pr06_scope.get("official_baseline_archive_sha256") != "c5c2e3826cb4de9a1789215325cc95854f06483c87b99ca59ffeb07f3e4416a5":
    fail("v1.0.6.23 PR-06 official baseline archive mismatch")
if pr06_scope.get("baseline_github_commit") != "e5763852249d86db35d9838a61f276eada823f08":
    fail("v1.0.6.23 PR-06 baseline GitHub commit mismatch")
if pr06_scope.get("baseline_github_actions_run_id") != 31389336441 or pr06_scope.get("baseline_ci_result") != "PASS":
    fail("v1.0.6.23 PR-06 prerequisite CI evidence mismatch")
if pr06_scope.get("target_version") != "1.0.6.23":
    fail("v1.0.6.23 PR-06 target mismatch")
pr06_allowed_files = set(pr06_scope.get("allowed_runtime_source_changes", []))

if not PR07_WORKFLOW_SHOWCASE_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.24 PR-07 Workflow Showcase scope contract is missing")
try:
    pr07_scope = json.loads(PR07_WORKFLOW_SHOWCASE_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.24 PR-07 Workflow Showcase scope contract is invalid: {exc}")
if pr07_scope.get("plan_id") != "VP-PR07-WORKFLOW-SHOWCASE-001":
    fail("v1.0.6.24 PR-07 plan identifier mismatch")
if pr07_scope.get("official_baseline_archive_sha256") != "bafc6d672447afbf02bf3a8c06f8b9992239d9943cb178f6fdec00ff1d6939f6":
    fail("v1.0.6.24 PR-07 official baseline archive mismatch")
if pr07_scope.get("baseline_github_commit") != "0959c00d014d71909726b0e886aaaa88e38f3eae":
    fail("v1.0.6.24 PR-07 baseline GitHub commit mismatch")
if pr07_scope.get("baseline_github_actions_run_id") != 31425661879 or pr07_scope.get("baseline_ci_result") != "PASS":
    fail("v1.0.6.24 PR-07 prerequisite CI evidence mismatch")
if pr07_scope.get("target_version") != "1.0.6.24":
    fail("v1.0.6.24 PR-07 target mismatch")
if pr07_scope.get("allowed_production_source_changes") != ["src/vibrapilot/qt_app.py"]:
    fail("v1.0.6.24 PR-07 production source scope mismatch")
pr07_allowed_main = set(pr07_scope.get("approved_mainwindow_method_changes", []))
if pr07_allowed_main != {
    "_create_nav_button", "_register_pages", "navigate", "make_workflows_page",
    "_workflow_logo_path", "_workflow_card", "refresh_workflow_showcase",
    "_activate_workflow_from_showcase",
}:
    fail("v1.0.6.24 PR-07 MainWindow method scope mismatch")

if not PR08_DYNAMIC_WORKFLOW_INPUTS_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.25 PR-08 Dynamic Workflow Inputs scope contract is missing")
try:
    pr08_scope = json.loads(PR08_DYNAMIC_WORKFLOW_INPUTS_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.25 PR-08 scope contract is invalid: {exc}")
if pr08_scope.get("plan_id") != "VP-PR08-DYNAMIC-WORKFLOW-INPUTS-001":
    fail("v1.0.6.25 PR-08 plan identifier mismatch")
if pr08_scope.get("official_baseline_archive_sha256") != "d20b3152a84870f36a794f862578718955c935b113bf7a4d8dd5bcd9b4a16d3d":
    fail("v1.0.6.25 PR-08 official baseline archive mismatch")
if pr08_scope.get("baseline_github_commit") != "39e089da94d8d7fcb0126e46a9dd4e259956f531":
    fail("v1.0.6.25 PR-08 baseline GitHub commit mismatch")
if pr08_scope.get("target_version") != "1.0.6.25":
    fail("v1.0.6.25 PR-08 target mismatch")
pr08_allowed_files = set(pr08_scope.get("allowed_production_source_changes", []))
if pr08_allowed_files != {
    "src/vibrapilot/workflow_inputs.py",
    "src/vibrapilot/workflow/input_state.py",
    "src/vibrapilot/qt_app.py",
    "src/vibrapilot/backend.py",
}:
    fail("v1.0.6.25 PR-08 production source scope mismatch")
if pr08_scope.get("canonical_input_state_path") != "AppData/workflow_inputs.json":
    fail("v1.0.6.25 PR-08 canonical persistence path mismatch")

if not PR10_WORKFLOW_ERROR_RECOVERY_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.27 PR-10 workflow error/recovery scope contract is missing")
try:
    pr10_scope = json.loads(PR10_WORKFLOW_ERROR_RECOVERY_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.27 PR-10 scope contract is invalid: {exc}")
pr10_allowed_files = set(pr10_scope.get("allowed_production_source_changes", []))
if pr08_scope.get("input_state_schema_version") != 1:
    fail("v1.0.6.25 PR-08 input-state schema mismatch")
if pr08_scope.get("supported_field_kinds") != ["text", "integer", "boolean", "choice"]:
    fail("v1.0.6.25 PR-08 supported field-kind contract mismatch")
pr08_allowed_worker = {"__init__"}
pr08_allowed_task = {"open_browser"}
pr08_allowed_main = {
    "_legacy_share_invite_input_values",
    "_rehydrate_legacy_workflow_input_mirror",
    "_initialize_workflow_input_state",
    "_reload_active_workflow_inputs",
    "current_workflow_input_snapshot",
    "_workflow_input_widget",
    "_workflow_input_widget_value",
    "make_workflow_inputs_page",
    "refresh_workflow_input_widgets",
    "_collect_workflow_input_values",
    "_persist_active_workflow_input_values",
    "save_workflow_inputs",
    "reset_workflow_inputs",
    "can_open_task_browser",
    "_workflow_switch_block_reason",
    "_confirm_workflow_switch",
}

print("[1/8] Python syntax")
for path in sorted(ROOT.rglob("*.py")):
    if any(part in {".venv", "build", "dist", "release", "__pycache__"} for part in path.parts):
        continue
    py_compile.compile(str(path), doraise=True)

print("[2/8] Exact Vib Tools frozen design-source hashes")
for rel, expected in EXPECTED_BRAND_HASHES.items():
    path = ROOT / rel
    if not path.is_file():
        fail(f"missing brand contract file: {rel}")
    actual = sha256(path)
    if actual != expected:
        fail(f"brand contract drift in {rel}: {actual} != {expected}")

print("[3/8] Frozen token values")
tokens = json.loads((ROOT / "frozen_design_source" / "CURRENT_FOUNDATION_TOKENS.json").read_text(encoding="utf-8"))
# Source-of-truth fields that identify the approved Vib Tools desktop contract.
checks = {
    ("theme", "mode"): "dark_only",
    ("theme", "font_family"): "Segoe UI Variable",
    ("theme", "fallback_font"): "Segoe UI",
    ("colors", "window_background"): "#090D14",
    ("colors", "surface"): "#111722",
    ("colors", "primary"): "#2563EB",
    ("colors", "secondary_accent"): "#38BDF8",
}
for keys, expected in checks.items():
    cur = tokens
    for key in keys:
        cur = cur[key]
    if cur != expected:
        fail(f"token {'.'.join(keys)} changed: {cur!r}")

print("[4/8] Core backend class/method parity")
if not BACKEND_CONTRACT.is_file():
    fail("public backend parity contract is missing")
try:
    backend_contract = json.loads(BACKEND_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"public backend parity contract is invalid: {exc}")

production = class_methods(SRC / "backend.py")
production_nodes = class_nodes(SRC / "backend.py")
if backend_contract.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail(
        "backend contract AST hash algorithm mismatch: "
        f"{backend_contract.get('ast_hash_algorithm')!r} != {AST_HASH_ALGORITHM!r}"
    )

expected_methods = backend_contract.get("core_method_inventory", {})
production_intentional_classes = {"TaskState", "AutomationWorker"}
for cls in CORE_CLASSES:
    if cls not in production:
        fail(f"missing core class {cls}")
    if cls not in expected_methods:
        fail(f"backend contract missing core class {cls}")
    if cls in production_intentional_classes:
        continue
    if production[cls] != expected_methods[cls]:
        fail(
            f"backend method drift in {cls}: "
            f"contract={expected_methods[cls]} production={production[cls]}"
        )

for cls, expected_sha in backend_contract.get("frozen_class_ast_sha256", {}).items():
    if cls in production_intentional_classes:
        continue
    node = production_nodes.get(cls)
    if node is None:
        fail(f"missing frozen backend class {cls}")
    actual_sha = ast_contract_sha(node)
    if actual_sha != expected_sha:
        fail(f"backend implementation drift in core class {cls}")

production_helpers = top_functions(SRC / "backend.py")
expected_helpers = list(backend_contract.get("top_level_helpers", []))
allowed_helpers = set(backend_contract.get("allowed_additional_helpers", []))
if [name for name in production_helpers if name not in allowed_helpers] != expected_helpers:
    fail(
        "top-level backend helper drift: "
        f"contract={expected_helpers} production={production_helpers}"
    )
production_function_nodes = function_nodes(SRC / "backend.py")
for name, expected_sha in backend_contract.get("frozen_helper_ast_sha256", {}).items():
    node = production_function_nodes.get(name)
    if node is None:
        fail(f"missing frozen backend helper {name}")
    if ast_contract_sha(node) != expected_sha:
        fail(f"backend helper implementation drift in {name}")

# v1.0.6.10 license-login verification/fix scope anchored to the exact promoted
# v1.0.6.9 GitHub baseline. Historical scope contracts remain evidence, while
# this contract authorizes only the current licensing/session surface.
if not LICENSE_LOGIN_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.10 license-login fix scope contract is missing")
try:
    license_fix_scope = json.loads(LICENSE_LOGIN_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.10 license-login fix scope contract is invalid: {exc}")
if license_fix_scope.get("official_baseline_github_commit") != "cd6ec96736626256daeed1d36775d21e90abf7ee":
    fail("v1.0.6.10 license scope does not identify the exact GitHub v1.0.6.9 baseline")
if license_fix_scope.get("official_baseline_archive_sha256") != "fe5ebed39608735dc72674a7342cb5f68afa3831afb94b8b944d210464d27805":
    fail("v1.0.6.10 license scope baseline archive mismatch")
if license_fix_scope.get("target_version") != "1.0.6.10":
    fail("v1.0.6.10 license scope target mismatch")
license_allowed_files = set(license_fix_scope.get("allowed_runtime_source_changes", []))
license_allowed_lm_methods = set(license_fix_scope.get("approved_licensemanager_method_changes", []))
license_allowed_mw_methods = set(license_fix_scope.get("approved_mainwindow_method_changes", []))
if license_allowed_files != {"src/vibrapilot/backend.py", "src/vibrapilot/qt_app.py"}:
    fail("v1.0.6.10 license runtime surface mismatch")

# v1.0.6.14 combines the explicitly approved managed-persistent-browser phase
# with the amended Closed Task recovery scope. It supersedes historical locks
# only for the exact runtime/settings methods and files listed in this contract.
if not MANAGED_BROWSER_CLOSED_TASK_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.14 managed browser / Closed Task scope contract is missing")
try:
    managed_scope = json.loads(
        MANAGED_BROWSER_CLOSED_TASK_SCOPE_CONTRACT.read_text(encoding="utf-8")
    )
except Exception as exc:
    fail(f"v1.0.6.14 managed browser / Closed Task scope contract is invalid: {exc}")
if managed_scope.get("plan_ids") != [
    "VP-MANAGED-PERSISTENT-BROWSER-001", "VP-CLOSED-TASK-RECOVERY-001"
]:
    fail("v1.0.6.14 managed browser / Closed Task plan identifiers mismatch")
if managed_scope.get("official_baseline") != "VibraPilot v1.0.6.13":
    fail("v1.0.6.14 baseline version mismatch")
if managed_scope.get("official_baseline_github_commit") != "5f082df8d1226710c095d4a8e591fb153c02c1c3":
    fail("v1.0.6.14 GitHub baseline mismatch")
if managed_scope.get("target_version") != "1.0.6.14":
    fail("v1.0.6.14 target mismatch")
managed_allowed_files = set(managed_scope.get("allowed_runtime_source_changes", []))
if managed_allowed_files != {
    "src/vibrapilot/backend.py",
    "src/vibrapilot/qt_app.py",
    "src/vibrapilot/task_runtime_store.py",
    "config/settings.defaults.json",
}:
    fail("v1.0.6.14 runtime/settings surface mismatch")
managed_allowed_settingsmanager = set(managed_scope.get("approved_settingsmanager_method_changes", []))
managed_allowed_worker = set(managed_scope.get("approved_automationworker_method_changes", []))
managed_allowed_runtime_store = set(managed_scope.get("approved_taskruntime_method_changes", []))
managed_allowed_task = set(managed_scope.get("approved_taskslotwidget_method_changes", []))
managed_allowed_main = set(managed_scope.get("approved_mainwindow_method_changes", []))
if not managed_scope.get("no_database_schema_change") or managed_scope.get("required_schema_version") != 1:
    fail("v1.0.6.14 must preserve TaskRuntimeStore schema version 1")
if not managed_scope.get("no_new_dependency") or not managed_scope.get("no_new_page"):
    fail("v1.0.6.14 dependency/page boundary mismatch")

# v1.0.6.17 VP-BROWSER-CAPABILITIES-001 authorizes only browser capability
# runtime surfaces while preserving every settings key and persistence schema.
if not BROWSER_CAPABILITIES_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.17 browser capabilities scope contract is missing")
try:
    capability_scope = json.loads(BROWSER_CAPABILITIES_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.17 browser capabilities scope contract is invalid: {exc}")
if capability_scope.get("plan_id") != "VP-BROWSER-CAPABILITIES-001":
    fail("v1.0.6.17 browser capabilities plan identifier mismatch")
if capability_scope.get("official_baseline") != "VibraPilot v1.0.6.16":
    fail("v1.0.6.17 browser capabilities baseline version mismatch")
if capability_scope.get("official_baseline_github_commit") != "fd0cbe6e8f3fc37f92bdf49396364ce74583fd1e":
    fail("v1.0.6.17 browser capabilities GitHub baseline mismatch")
if capability_scope.get("official_baseline_github_actions_run") != 31342562832:
    fail("v1.0.6.17 browser capabilities GitHub Actions baseline mismatch")
if capability_scope.get("target_version") != "1.0.6.17":
    fail("v1.0.6.17 browser capabilities target mismatch")
capability_allowed_files = set(capability_scope.get("allowed_runtime_source_changes", []))
capability_allowed_worker = set(capability_scope.get("approved_automationworker_method_changes", []))
capability_allowed_task = set(capability_scope.get("approved_taskslotwidget_method_changes", []))
capability_allowed_main = set(capability_scope.get("approved_mainwindow_method_changes", []))
if capability_allowed_files != {
    "src/vibrapilot/backend.py",
    "src/vibrapilot/qt_app.py",
    "src/vibrapilot/browser_capabilities.py",
}:
    fail("v1.0.6.17 browser capabilities runtime surface mismatch")
if not capability_scope.get("no_database_schema_change") or capability_scope.get("required_taskruntime_schema_version") != 1:
    fail("v1.0.6.17 must preserve TaskRuntimeStore schema version 1")
if not capability_scope.get("no_workspace_schema_change") or not capability_scope.get("no_settings_key_change"):
    fail("v1.0.6.17 workspace/settings boundary mismatch")
if not capability_scope.get("no_new_dependency") or not capability_scope.get("no_new_page"):
    fail("v1.0.6.17 dependency/page boundary mismatch")

# The current user-approved patch is presentation-only and supersedes the
# historical v1.0.6.17 qt_app hash only for Tasks-page UI methods. Browser
# capability runtime behavior and every non-UI surface remain frozen.
if not TASKS_UI_POLISH_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.17 Tasks-page UI polish scope contract is missing")
try:
    tasks_ui_scope = json.loads(TASKS_UI_POLISH_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.17 Tasks-page UI polish scope contract is invalid: {exc}")
if tasks_ui_scope.get("official_baseline") != "VibraPilot v1.0.6.17":
    fail("Tasks-page UI polish baseline version mismatch")
if tasks_ui_scope.get("official_baseline_github_commit") != "6d29224d38d15d6b744d334585d6eb28de8314c8":
    fail("Tasks-page UI polish GitHub baseline mismatch")
if tasks_ui_scope.get("target_version") != "1.0.6.17" or tasks_ui_scope.get("version_bump_authorized"):
    fail("Tasks-page UI polish version boundary mismatch")
tasks_ui_allowed_files = set(tasks_ui_scope.get("allowed_runtime_source_changes", []))
tasks_ui_allowed_task = set(tasks_ui_scope.get("approved_taskslotwidget_ui_methods", []))
tasks_ui_allowed_main = set(tasks_ui_scope.get("approved_mainwindow_ui_methods", []))
if tasks_ui_allowed_files != {"src/vibrapilot/qt_app.py"}:
    fail("Tasks-page UI polish runtime surface mismatch")
if not all(
    tasks_ui_scope.get(key)
    for key in (
        "no_backend_change", "no_database_schema_change", "no_workspace_schema_change",
        "no_settings_change", "no_other_page_change", "no_new_dependency",
        "no_new_page", "no_workflow_change", "no_browser_capability_change",
        "no_licensing_change",
    )
):
    fail("Tasks-page UI polish preservation boundary mismatch")
for relative, expected_sha in tasks_ui_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"Tasks-page UI polish approved target mismatch: {relative}")

# v1.0.6.20 PR-04 authorizes only the existing Share Invite extraction boundary.
if not PR04_SHARE_INVITE_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.20 PR-04 Share Invite scope contract is missing")
try:
    pr04_scope = json.loads(PR04_SHARE_INVITE_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.20 PR-04 scope contract is invalid: {exc}")
if pr04_scope.get("plan_id") != "VP-PR04-SHARE-INVITE-WORKFLOW-EXTRACTION-001":
    fail("v1.0.6.20 PR-04 plan identifier mismatch")
if pr04_scope.get("official_baseline_github_commit") != "999212b947583927204535f59832f1379d9306f4":
    fail("v1.0.6.20 PR-04 GitHub baseline mismatch")
if pr04_scope.get("target_version") != "1.0.6.20":
    fail("v1.0.6.20 PR-04 target mismatch")
pr04_allowed_files = set(pr04_scope.get("allowed_runtime_source_changes", []))
pr04_allowed_worker = set(pr04_scope.get("approved_automationworker_method_changes", []))
if "src/vibrapilot/backend.py" not in pr04_allowed_files:
    fail("v1.0.6.20 PR-04 backend delegation boundary missing")
for key in (
    "no_ui_change", "no_database_schema_change", "no_workspace_schema_change",
    "no_settings_change", "no_browser_configuration_change", "no_dependency_change",
    "captcha_out_of_scope", "workflow_switching_out_of_scope",
    "active_workflow_persistence_out_of_scope",
):
    if pr04_scope.get(key) is not True:
        fail(f"v1.0.6.20 PR-04 boundary missing: {key}")

# v1.0.6.21 PR-04 CI portability correction: runtime stays frozen; only the
# Python-minor-stable semantic verification contract changes.
if not PR04_CI_PORTABILITY_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.21 PR-04 CI portability fix scope contract is missing")
try:
    pr04_ci_fix_scope = json.loads(PR04_CI_PORTABILITY_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.21 PR-04 CI portability scope contract is invalid: {exc}")
if pr04_ci_fix_scope.get("plan_id") != "VP-PR04-CI-PORTABILITY-001":
    fail("v1.0.6.21 PR-04 CI portability plan identifier mismatch")
if pr04_ci_fix_scope.get("target_version") != "1.0.6.21":
    fail("v1.0.6.21 PR-04 CI portability target mismatch")
if pr04_ci_fix_scope.get("semantic_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.21 PR-04 CI portability AST algorithm mismatch")
if hashlib.sha256(PR04_SHARE_INVITE_SCOPE_CONTRACT.read_bytes()).hexdigest() != pr04_ci_fix_scope.get("historical_pr04_scope_sha256"):
    fail("v1.0.6.21 historical PR-04 scope contract drift detected")

# v1.0.6.22 PR-05 adds only the approved in-memory Master Workflow Gate.
if not PR05_MASTER_WORKFLOW_GATE_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.22 PR-05 Master Workflow Gate scope contract is missing")
try:
    pr05_scope = json.loads(PR05_MASTER_WORKFLOW_GATE_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.22 PR-05 scope contract is invalid: {exc}")
if pr05_scope.get("plan_id") != "VP-PR05-MASTER-WORKFLOW-GATE-001":
    fail("v1.0.6.22 PR-05 plan identifier mismatch")
if pr05_scope.get("official_baseline_archive_sha256") != "8aa8de7df68cb5d402bd3d2ae2400efc36189fbcca8f36bddb23679dbc78ff14":
    fail("v1.0.6.22 PR-05 baseline archive mismatch")
if pr05_scope.get("baseline_github_commit") != "cb4337812c0ac4f0e944093b7a7d4400fe618d57":
    fail("v1.0.6.22 PR-05 baseline GitHub commit mismatch")
if pr05_scope.get("baseline_github_actions_run_id") != 31383176348 or pr05_scope.get("baseline_ci_result") != "PASS":
    fail("v1.0.6.22 PR-05 prerequisite CI evidence mismatch")
if pr05_scope.get("target_version") != "1.0.6.22":
    fail("v1.0.6.22 PR-05 target mismatch")
if pr05_scope.get("initial_active_workflow_id") != "share_invite":
    fail("v1.0.6.22 PR-05 initial active workflow mismatch")
for key in (
    "no_workflow_switching", "no_active_workflow_persistence", "no_new_ui",
    "no_settings_change", "no_database_schema_change", "no_workspace_schema_change",
    "no_report_schema_change", "no_browser_change", "no_dependency_change",
    "no_licensing_change", "captcha_out_of_scope", "external_plugin_loading_prohibited",
    "manifest_controlled_dynamic_import_prohibited",
):
    if pr05_scope.get(key) is not True:
        fail(f"v1.0.6.22 PR-05 preservation boundary mismatch: {key}")
pr05_allowed_files = set(pr05_scope.get("allowed_runtime_source_changes", []))

if not BROWSER_FOUNDATION_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.18 browser foundation scope contract is missing")
browser_foundation_scope = json.loads(BROWSER_FOUNDATION_SCOPE_CONTRACT.read_text(encoding="utf-8"))
if browser_foundation_scope.get("plan_id") != "VP-BROWSER-FOUNDATION-STABILIZATION-001":
    fail("v1.0.6.18 browser foundation plan mismatch")
if browser_foundation_scope.get("official_baseline_archive_sha256") != "02d8d70a9c11365922121440edc0d6da8328ba3b9dcfb73fcc1f0885a05a38bf":
    fail("v1.0.6.18 baseline hash mismatch")
if browser_foundation_scope.get("target_version") != "1.0.6.18":
    fail("v1.0.6.18 target mismatch")
browser_foundation_allowed_files = set(browser_foundation_scope.get("allowed_runtime_source_changes", []))
if browser_foundation_allowed_files != {
    "src/vibrapilot/backend.py",
    "src/vibrapilot/qt_app.py",
    "src/vibrapilot/browser_diagnostics.py",
}:
    fail("v1.0.6.18 runtime surface mismatch")
if browser_foundation_scope.get("sandbox_default_change_applied"):
    fail("sandbox default changed without Windows acceptance")

if not BROWSER_FOUNDATION_VERIFICATION_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.19 browser foundation verification/fix scope contract is missing")
browser_foundation_fix_scope = json.loads(
    BROWSER_FOUNDATION_VERIFICATION_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8")
)
if browser_foundation_fix_scope.get("plan_id") != "VP-BROWSER-FOUNDATION-STABILIZATION-001-VERIFICATION-FIX":
    fail("v1.0.6.19 browser foundation verification/fix plan mismatch")
if browser_foundation_fix_scope.get("official_baseline_archive_sha256") != "d18277ea00ae581ede45c8d3e647cd0f41625aeb0d5b8aad71715c19e4e29ae9":
    fail("v1.0.6.19 browser foundation baseline hash mismatch")
if browser_foundation_fix_scope.get("target_version") != "1.0.6.19":
    fail("v1.0.6.19 browser foundation target mismatch")
browser_foundation_fix_allowed_files = set(
    browser_foundation_fix_scope.get("allowed_runtime_source_changes", [])
)
if browser_foundation_fix_allowed_files != {
    "src/vibrapilot/backend.py",
    "src/vibrapilot/browser_diagnostics.py",
}:
    fail("v1.0.6.19 browser foundation verification/fix runtime surface mismatch")
if browser_foundation_fix_scope.get("sandbox_default_change_applied"):
    fail("v1.0.6.19 sandbox default changed without Sandbox-ON acceptance")

for relative, expected_sha in browser_foundation_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in browser_foundation_fix_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.18 target runtime mismatch: {relative}")
for relative, expected_sha in browser_foundation_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.18 frozen drift: {relative}")
if not CHROME_WEBSTORE_EXTENSION_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.19 Chrome Web Store extension fix scope contract is missing")
chrome_webstore_fix_scope = json.loads(
    CHROME_WEBSTORE_EXTENSION_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8")
)
if chrome_webstore_fix_scope.get("plan_id") != "VP-CHROME-WEBSTORE-EXTENSION-INSTALL-FIX-001":
    fail("v1.0.6.19 Chrome Web Store extension fix plan mismatch")
if chrome_webstore_fix_scope.get("official_baseline_archive_sha256") != "731c68b36fd863957be4dc205f48a666b5bf8a36872adf44c834a8e54ec1f685":
    fail("v1.0.6.19 Chrome Web Store extension fix baseline hash mismatch")
if chrome_webstore_fix_scope.get("target_version") != "1.0.6.19":
    fail("v1.0.6.19 Chrome Web Store extension fix target mismatch")
chrome_webstore_fix_allowed_files = set(
    chrome_webstore_fix_scope.get("allowed_runtime_source_changes", [])
)
if chrome_webstore_fix_allowed_files != {"src/vibrapilot/backend.py"}:
    fail("v1.0.6.19 Chrome Web Store extension fix runtime surface mismatch")
if not chrome_webstore_fix_scope.get("preserve_downloads"):
    fail("Chrome Web Store extension fix must preserve downloads")
if not chrome_webstore_fix_scope.get("no_policy_change"):
    fail("Chrome Web Store extension fix must not change Chrome policy")

for relative, expected_sha in browser_foundation_fix_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in chrome_webstore_fix_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.19 target runtime mismatch: {relative}")
for relative, expected_sha in browser_foundation_fix_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.19 frozen drift: {relative}")
for relative, expected_sha in chrome_webstore_fix_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"Chrome Web Store extension fix target runtime mismatch: {relative}")
for relative, expected_sha in chrome_webstore_fix_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"Chrome Web Store extension fix frozen drift: {relative}")

for relative, expected_sha in capability_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in tasks_ui_allowed_files or relative in browser_foundation_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.17 approved target runtime mismatch: {relative}")
for relative, expected_sha in capability_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.17 frozen file drift detected: {relative}")

# v1.0.6.15 VP-WORKSPACE-PERSISTENCE-001 supersedes the historical qt_app
# hash only for the explicitly approved workspace-persistence surface.
if not WORKSPACE_PERSISTENCE_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.15 workspace persistence scope contract is missing")
try:
    workspace_scope = json.loads(
        WORKSPACE_PERSISTENCE_SCOPE_CONTRACT.read_text(encoding="utf-8")
    )
except Exception as exc:
    fail(f"v1.0.6.15 workspace persistence scope contract is invalid: {exc}")
if workspace_scope.get("plan_ids") != ["VP-WORKSPACE-PERSISTENCE-001"]:
    fail("v1.0.6.15 workspace persistence plan identifier mismatch")
if workspace_scope.get("official_baseline") != "VibraPilot v1.0.6.14":
    fail("v1.0.6.15 workspace baseline version mismatch")
if workspace_scope.get("official_baseline_github_commit") != "b3c9314ca3dc2599eaa28f4c6abf558e629b0837":
    fail("v1.0.6.15 workspace GitHub baseline mismatch")
if workspace_scope.get("official_baseline_github_actions_run") != 31337925846:
    fail("v1.0.6.15 workspace GitHub Actions baseline mismatch")
if workspace_scope.get("target_version") != "1.0.6.15":
    fail("v1.0.6.15 workspace target mismatch")
workspace_allowed_files = set(workspace_scope.get("allowed_runtime_source_changes", []))
workspace_allowed_main = set(workspace_scope.get("approved_mainwindow_method_changes", []))
workspace_allowed_task = set(workspace_scope.get("approved_taskslotwidget_method_changes", []))
if workspace_allowed_files != {
    "src/vibrapilot/qt_app.py", "src/vibrapilot/workspace_state.py"
}:
    fail("v1.0.6.15 workspace runtime surface mismatch")
if not workspace_scope.get("no_database_schema_change") or workspace_scope.get("required_taskruntime_schema_version") != 1:
    fail("v1.0.6.15 must preserve TaskRuntimeStore schema version 1")
if not workspace_scope.get("no_settings_key_change") or not workspace_scope.get("no_new_dependency"):
    fail("v1.0.6.15 settings/dependency boundary mismatch")
if not workspace_scope.get("closed_tasks_must_remain_closed"):
    fail("v1.0.6.15 must preserve Closed Task archive semantics")
for key in ("no_auto_browser_start", "no_auto_login_assumption", "no_auto_workflow_start", "no_auto_send"):
    if workspace_scope.get(key) is not True:
        fail(f"v1.0.6.15 safety boundary missing: {key}")
for relative, expected_sha in workspace_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.15 approved target runtime mismatch: {relative}")
for relative, expected_sha in workspace_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.15 frozen file drift detected: {relative}")

if not WORKSPACE_PERSISTENCE_VERIFICATION_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.16 workspace verification-fix scope contract is missing")
workspace_fix_scope = json.loads(WORKSPACE_PERSISTENCE_VERIFICATION_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
if workspace_fix_scope.get("official_baseline_github_commit") != "564dc159856e2e3255a1d8c101086e291bdca110" or workspace_fix_scope.get("target_version") != "1.0.6.16":
    fail("v1.0.6.16 verification scope identity mismatch")
if workspace_fix_scope.get("no_production_runtime_change") is not True or workspace_fix_scope.get("required_taskruntime_schema_version") != 1:
    fail("v1.0.6.16 runtime/database boundary mismatch")
for relative, expected_sha in workspace_fix_scope.get("runtime_byte_frozen_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.16 production runtime drift detected: {relative}")
if "schedule_workspace_save=lambda: None" not in (ROOT / "tests/test_v10612_browser_ui_lifecycle.py").read_text(encoding="utf-8"):
    fail("v1.0.6.16 Qt fixture workspace-save callback is missing")

for relative, expected_sha in managed_scope.get("approved_target_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in workspace_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.14 approved target runtime mismatch: {relative}")
for relative, expected_sha in managed_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.14 frozen file drift detected: {relative}")

# v1.0.6.12 VP-BROWSER-UI-LIFECYCLE-001 supersedes only the approved
# browser-lifecycle methods in backend/qt_app. Historical manifests remain
# immutable evidence for every other method and file.
if not BROWSER_UI_LIFECYCLE_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.12 browser UI lifecycle scope contract is missing")
try:
    browser_ui_scope = json.loads(BROWSER_UI_LIFECYCLE_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.12 browser UI lifecycle scope contract is invalid: {exc}")
if browser_ui_scope.get("plan_id") != "VP-BROWSER-UI-LIFECYCLE-001":
    fail("v1.0.6.12 browser UI lifecycle plan identifier mismatch")
if browser_ui_scope.get("official_baseline") != "VibraPilot v1.0.6.11":
    fail("v1.0.6.12 browser UI lifecycle baseline version mismatch")
if browser_ui_scope.get("official_baseline_archive_sha256") != "9ecb7cd66f24832c3555d219a6f8aaf47358877dd417eeb703b5a755964fc90a":
    fail("v1.0.6.12 browser UI lifecycle baseline archive mismatch")
if browser_ui_scope.get("official_baseline_github_commit") != "8670415b1df221ebeeb7d8f3fba4f991a91d43ec":
    fail("v1.0.6.12 browser UI lifecycle GitHub baseline mismatch")
if browser_ui_scope.get("target_version") != "1.0.6.12":
    fail("v1.0.6.12 browser UI lifecycle target mismatch")
browser_ui_allowed_files = set(browser_ui_scope.get("allowed_runtime_source_changes", []))
if browser_ui_allowed_files != {"src/vibrapilot/backend.py", "src/vibrapilot/qt_app.py"}:
    fail("v1.0.6.12 browser UI lifecycle runtime surface mismatch")
browser_ui_allowed_worker = set(browser_ui_scope.get("approved_automationworker_method_changes", []))
browser_ui_allowed_task = set(browser_ui_scope.get("approved_taskslotwidget_method_changes", []))
browser_ui_allowed_main = set(browser_ui_scope.get("approved_mainwindow_method_changes", []))
for relative, expected_sha in browser_ui_scope.get("approved_runtime_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in managed_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.12 approved runtime file mismatch: {relative}")
for relative, expected_sha in browser_ui_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in managed_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.12 browser UI out-of-scope file drift detected: {relative}")

# v1.0.6.13 is a verification/CI correction on top of the exact promoted
# v1.0.6.12 Phase-01 tree. It authorizes no production runtime source changes.
if not PHASE01_VERIFICATION_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.13 Phase-01 verification fix scope contract is missing")
try:
    phase01_verify_scope = json.loads(
        PHASE01_VERIFICATION_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8")
    )
except Exception as exc:
    fail(f"v1.0.6.13 Phase-01 verification fix scope contract is invalid: {exc}")
if phase01_verify_scope.get("plan_id") != "VP-BROWSER-UI-LIFECYCLE-001-VERIFICATION-FIX":
    fail("v1.0.6.13 Phase-01 verification fix plan identifier mismatch")
if phase01_verify_scope.get("official_baseline") != "VibraPilot v1.0.6.12":
    fail("v1.0.6.13 Phase-01 verification fix baseline version mismatch")
if phase01_verify_scope.get("official_baseline_archive_sha256") != "becd6add21d377e98e458ce856c9c3baa710a113459bde0c737507c122c2a9b5":
    fail("v1.0.6.13 Phase-01 verification fix baseline archive mismatch")
if phase01_verify_scope.get("official_baseline_github_commit") != "a9cfec319285db2fb9fbff8d4bf0ede8ac87686b":
    fail("v1.0.6.13 Phase-01 verification fix GitHub baseline mismatch")
if phase01_verify_scope.get("target_version") != "1.0.6.13":
    fail("v1.0.6.13 Phase-01 verification fix target mismatch")
if phase01_verify_scope.get("allowed_runtime_source_changes") != []:
    fail("v1.0.6.13 Phase-01 verification fix must not authorize runtime source changes")
for relative, expected_sha in phase01_verify_scope.get("frozen_runtime_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in managed_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.13 frozen runtime drift detected: {relative}")

# v1.0.6.11 VP-QT-FOCUS-LIFECYCLE-001 authorizes exactly one design-runtime
# implementation file. Historical scope manifests remain immutable evidence;
# this current scope supersedes their old focus_manager byte hash only.
if not QT_FOCUS_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.11 Qt focus lifecycle scope contract is missing")
try:
    qt_focus_scope = json.loads(QT_FOCUS_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.11 Qt focus lifecycle scope contract is invalid: {exc}")
if qt_focus_scope.get("plan_id") != "VP-QT-FOCUS-LIFECYCLE-001":
    fail("v1.0.6.11 Qt focus scope plan identifier mismatch")
if qt_focus_scope.get("official_baseline_github_commit") != "d712a9d04fa62e5e3a0df9c00a99c1315052bd05":
    fail("v1.0.6.11 Qt focus scope does not identify the exact GitHub v1.0.6.10 baseline")
if qt_focus_scope.get("official_baseline_archive_sha256") != "d818aa1d4ee3492df810fb29034999293b47c343444469b32ceebbbb92f5e044":
    fail("v1.0.6.11 Qt focus scope baseline archive mismatch")
if qt_focus_scope.get("official_baseline_tree_sha256") != "b136737c935a4d7c072f44b6df8f57e71bb396bb7c5f29bf2636f5027cee1f3d":
    fail("v1.0.6.11 Qt focus scope baseline tree mismatch")
if qt_focus_scope.get("target_version") != "1.0.6.11":
    fail("v1.0.6.11 Qt focus scope target mismatch")
qt_focus_allowed_files = set(qt_focus_scope.get("allowed_runtime_source_changes", []))
if qt_focus_allowed_files != {"vib_validation_app/focus_manager.py"}:
    fail("v1.0.6.11 Qt focus runtime surface mismatch")
if qt_focus_scope.get("approved_focus_manager_sha256") != EXPECTED_BRAND_HASHES["vib_validation_app/focus_manager.py"]:
    fail("v1.0.6.11 approved focus-manager hash does not match the current design contract")
for relative, expected_sha in qt_focus_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in browser_ui_allowed_files or relative in managed_allowed_files or relative in workspace_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.11 Qt focus out-of-scope file drift detected: {relative}")

# VP-PROD-MT-LR-001 production scope lock. The v1.0.6.4 Phase-02 manifest remains
# historical evidence while the current verifier enforces the approved v1.0.6.5 scope.
if not PRODUCTION_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.5 production scope contract is missing")
try:
    production_scope = json.loads(PRODUCTION_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.5 production scope contract is invalid: {exc}")
if production_scope.get("official_baseline_archive_sha256") != "ea65bd89d908c5db8edfcf01e6b7c5e11410ffe57a98044f9e8913477f9e89e6":
    fail("production scope contract does not identify the approved v1.0.6.4 baseline")
if production_scope.get("target_version") != "1.0.6.5":
    fail("production scope target version must be 1.0.6.5")
settings_defaults_for_scope = json.loads((ROOT / "config" / "settings.defaults.json").read_text(encoding="utf-8"))
for approved_key in production_scope.get("approved_new_setting_keys", []):
    settings_defaults_for_scope.pop(approved_key, None)
for key, change in managed_scope.get("approved_settings_default_changes", {}).items():
    if isinstance(change, dict) and "from" in change:
        settings_defaults_for_scope[key] = change["from"]
settings_scope_payload = json.dumps(
    settings_defaults_for_scope, sort_keys=True, separators=(",", ":"), ensure_ascii=False
).encode("utf-8")
if hashlib.sha256(settings_scope_payload).hexdigest() != production_scope.get("baseline_settings_canonical_sha256"):
    fail("production scope changed an existing settings default outside the approved new setting")
for relative, expected_sha in production_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in qt_focus_allowed_files or relative in managed_allowed_files or relative in workspace_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file():
        fail(f"production-scope frozen file is missing: {relative}")
    actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual_sha != expected_sha:
        fail(f"production out-of-scope file drift detected: {relative}")

production_ast = production_scope.get("frozen_ast_sha256", {})
if production_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("production scope AST hash algorithm mismatch")
qt_nodes = class_nodes(ROOT / "src" / "vibrapilot" / "qt_app.py")
backend_assignment_nodes = assignment_nodes(SRC / "backend.py")
qt_ann_nodes = annotated_assignment_nodes(ROOT / "src" / "vibrapilot" / "qt_app.py")
checks = {
    "backend.LicenseManager": production_nodes.get("LicenseManager"),
    "backend.SELECTORS": backend_assignment_nodes.get("SELECTORS"),
    "qt_app.ActivationPage": qt_nodes.get("ActivationPage"),
    "qt_app.BROWSER_SETTING_GROUPS": qt_ann_nodes.get("BROWSER_SETTING_GROUPS"),
}
for name, node in checks.items():
    if name == "backend.LicenseManager" and "src/vibrapilot/backend.py" in license_allowed_files:
        continue
    expected_sha = production_ast.get(name)
    if node is None or not expected_sha or ast_contract_sha(node) != expected_sha:
        fail(f"production out-of-scope AST drift detected: {name}")

automation_worker_node = production_nodes.get("AutomationWorker")
if automation_worker_node is None:
    fail("production AutomationWorker class is missing")
automation_worker_methods = {
    node.name: node
    for node in automation_worker_node.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}
for method_name, expected_sha in production_scope.get("frozen_automationworker_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_worker or method_name in browser_ui_allowed_worker or method_name in managed_allowed_worker or method_name in capability_allowed_worker or method_name in pr04_allowed_worker:
        continue
    node = automation_worker_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"production out-of-scope AutomationWorker method drift detected: {method_name}")

# VP-WORKFLOW-INPUTS-001 is anchored to the final v1.0.6.7 tree, which is the
# clean v1.0.6.7 Official Baseline plus its approved Windows SQLite fix delta.
if not WORKFLOW_INPUTS_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.8 Workflow Inputs scope contract is missing")
try:
    workflow_inputs_scope = json.loads(WORKFLOW_INPUTS_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.8 Workflow Inputs scope contract is invalid: {exc}")
expected_workflow_components = {
    "VibraPilot_v1.0.6.7_Official_Baseline.zip": "76dbc63cd9c033f1b471e4624d3b6f704a3c5552b4ce3a081fabb99c6b0b72e6",
    "VibraPilot_v1.0.6.7_Windows-SQLite-Concurrency-Fix_Replace-Ready_Delta.zip": "bd6dc9aa6df6c7aa2a71b762318442192dcb6870f0b29ca9339a74019114b996",
}
if workflow_inputs_scope.get("official_baseline_components") != expected_workflow_components:
    fail("v1.0.6.8 Workflow Inputs scope baseline components mismatch")
if workflow_inputs_scope.get("official_baseline_tree_sha256") != "84d22fd2c1fef38cbf49024f7d3b2c9ec250e3389dd2b479192735fb2419bb89":
    fail("v1.0.6.8 Workflow Inputs scope final v1.0.6.7 tree mismatch")
if workflow_inputs_scope.get("target_version") != "1.0.6.8":
    fail("v1.0.6.8 Workflow Inputs scope target version mismatch")
workflow_allowed_files = set(workflow_inputs_scope.get("allowed_runtime_source_changes", []))
workflow_release_files = set(workflow_inputs_scope.get("approved_release_metadata_changes", []))
workflow_approved_mainwindow = set(workflow_inputs_scope.get("approved_mainwindow_method_changes", []))

# Follow-up v1.0.6.7 Windows SQLite concurrency fix is anchored to the clean
# v1.0.6.7 Official Baseline and may supersede only the explicitly authorized
# file/method locks from the earlier verification scope.
if not WINDOWS_SQLITE_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.7 Windows SQLite fix scope contract is missing")
try:
    windows_sqlite_fix_scope = json.loads(WINDOWS_SQLITE_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.7 Windows SQLite fix scope contract is invalid: {exc}")
if windows_sqlite_fix_scope.get("official_baseline_archive_sha256") != "76dbc63cd9c033f1b471e4624d3b6f704a3c5552b4ce3a081fabb99c6b0b72e6":
    fail("v1.0.6.7 Windows SQLite fix scope baseline mismatch")
if windows_sqlite_fix_scope.get("target_version") != "1.0.6.7":
    fail("v1.0.6.7 Windows SQLite fix scope target version mismatch")
followup_allowed_files = set(windows_sqlite_fix_scope.get("allowed_runtime_source_changes", []))
followup_allowed_worker = set(windows_sqlite_fix_scope.get("approved_automationworker_method_changes", []))

# v1.0.6.7 verification/fix scope anchored to the exact user-frozen v1.0.6.5 ZIP.
if not CURRENT_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.7 verification/fix scope contract is missing")
try:
    current_fix_scope = json.loads(CURRENT_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.7 verification/fix scope contract is invalid: {exc}")
if current_fix_scope.get("official_baseline_archive_sha256") != "f391099de9d0d117d190b2898b96d5e90b3f102541cf8efa217f9e9fbfbed118":
    fail("v1.0.6.7 fix scope does not identify the exact uploaded v1.0.6.5 baseline")
if current_fix_scope.get("target_version") != "1.0.6.7":
    fail("v1.0.6.7 fix scope target version mismatch")
for relative, expected_sha in current_fix_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if (
        relative in followup_allowed_files
        or relative in workflow_allowed_files
        or relative in workflow_release_files
        or relative in qt_focus_allowed_files
        or relative in managed_allowed_files
        or relative in workspace_allowed_files
        or relative in capability_allowed_files
    ):
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.7 out-of-scope file drift detected: {relative}")
if current_fix_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.7 fix-scope AST hash algorithm mismatch")
current_ast = current_fix_scope.get("frozen_ast_sha256", {})
current_checks = {
    "backend.LicenseManager": production_nodes.get("LicenseManager"),
    "backend.SELECTORS": backend_assignment_nodes.get("SELECTORS"),
    "qt_app.ActivationPage": qt_nodes.get("ActivationPage"),
    "qt_app.MainWindow": qt_nodes.get("MainWindow"),
    "qt_app.BROWSER_SETTING_GROUPS": qt_ann_nodes.get("BROWSER_SETTING_GROUPS"),
}
for name, node in current_checks.items():
    if name == "backend.LicenseManager" and "src/vibrapilot/backend.py" in license_allowed_files:
        continue
    if name == "qt_app.MainWindow" and (workflow_approved_mainwindow or license_allowed_mw_methods or browser_ui_allowed_main or managed_allowed_main or workspace_allowed_main or capability_allowed_main or tasks_ui_allowed_main):
        continue
    expected_sha = current_ast.get(name)
    if node is None or not expected_sha or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.7 out-of-scope AST drift detected: {name}")
allowed_current_worker = set(current_fix_scope.get("approved_automationworker_method_changes", []))
for method_name, expected_sha in current_fix_scope.get("frozen_automationworker_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_worker or method_name in browser_ui_allowed_worker or method_name in managed_allowed_worker or method_name in capability_allowed_worker or method_name in pr04_allowed_worker:
        continue
    if method_name in allowed_current_worker:
        fail(f"v1.0.6.7 fix scope incorrectly freezes an approved worker method: {method_name}")
    if method_name in followup_allowed_worker:
        continue
    node = automation_worker_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.7 out-of-scope AutomationWorker method drift detected: {method_name}")

# Enforce the later Windows SQLite fix boundary against the clean v1.0.6.7 baseline.
for relative, expected_sha in windows_sqlite_fix_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in workflow_allowed_files or relative in workflow_release_files or relative in qt_focus_allowed_files or relative in browser_ui_allowed_files or relative in managed_allowed_files or relative in workspace_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected_sha:
        fail(f"v1.0.6.7 Windows SQLite fix out-of-scope file drift detected: {relative}")
if windows_sqlite_fix_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.7 Windows SQLite fix AST hash algorithm mismatch")
followup_ast = windows_sqlite_fix_scope.get("frozen_ast_sha256", {})
for name, node in current_checks.items():
    if name == "backend.LicenseManager" and "src/vibrapilot/backend.py" in license_allowed_files:
        continue
    if name == "qt_app.MainWindow" and (workflow_approved_mainwindow or license_allowed_mw_methods or browser_ui_allowed_main or managed_allowed_main or workspace_allowed_main or capability_allowed_main or tasks_ui_allowed_main):
        continue
    expected_sha = followup_ast.get(name)
    if node is None or not expected_sha or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.7 Windows SQLite fix out-of-scope AST drift detected: {name}")
for method_name, expected_sha in windows_sqlite_fix_scope.get("frozen_automationworker_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_worker or method_name in browser_ui_allowed_worker or method_name in managed_allowed_worker or method_name in capability_allowed_worker or method_name in pr04_allowed_worker:
        continue
    if method_name in followup_allowed_worker:
        fail(f"v1.0.6.7 Windows SQLite fix incorrectly freezes an approved worker method: {method_name}")
    node = automation_worker_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.7 Windows SQLite fix out-of-scope AutomationWorker drift: {method_name}")

# Enforce VP-WORKFLOW-INPUTS-001 against the final v1.0.6.7 baseline.
for relative, expected_sha in workflow_inputs_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in license_allowed_files or relative in qt_focus_allowed_files or relative in browser_ui_allowed_files or relative in managed_allowed_files or relative in workspace_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected_sha:
        fail(f"v1.0.6.8 Workflow Inputs out-of-scope file drift detected: {relative}")
if workflow_inputs_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.8 Workflow Inputs scope AST hash algorithm mismatch")
workflow_fixed_ast = workflow_inputs_scope.get("frozen_ast_sha256", {})
workflow_ast_checks = {
    "backend.LicenseManager": production_nodes.get("LicenseManager"),
    "backend.AutomationWorker": production_nodes.get("AutomationWorker"),
    "backend.TaskItem": production_nodes.get("TaskItem"),
    "backend.TaskState": production_nodes.get("TaskState"),
    "backend.SELECTORS": backend_assignment_nodes.get("SELECTORS"),
    "qt_app.ActivationPage": qt_nodes.get("ActivationPage"),
    "qt_app.BROWSER_SETTING_GROUPS": qt_ann_nodes.get("BROWSER_SETTING_GROUPS"),
}
for name, node in workflow_ast_checks.items():
    if name == "backend.LicenseManager" and "src/vibrapilot/backend.py" in license_allowed_files:
        continue
    if name == "backend.AutomationWorker" and (browser_ui_allowed_worker or capability_allowed_worker or pr04_allowed_worker):
        continue
    expected_sha = workflow_fixed_ast.get(name)
    if node is None or not expected_sha or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.8 Workflow Inputs out-of-scope AST drift detected: {name}")

main_window = qt_nodes.get("MainWindow")
if main_window is None:
    fail("v1.0.6.8 Workflow Inputs MainWindow is missing")
main_window_methods = {
    node.name: node
    for node in main_window.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}
for method_name, expected_sha in workflow_inputs_scope.get("frozen_mainwindow_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_main or method_name in pr07_allowed_main or method_name in license_allowed_mw_methods or method_name in browser_ui_allowed_main or method_name in managed_allowed_main or method_name in workspace_allowed_main or method_name in capability_allowed_main or method_name in tasks_ui_allowed_main or method_name in tasks_ui_allowed_main or method_name in tasks_ui_allowed_main:
        continue
    if method_name in workflow_approved_mainwindow:
        fail(f"v1.0.6.8 Workflow Inputs scope incorrectly freezes approved MainWindow method: {method_name}")
    node = main_window_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.8 Workflow Inputs out-of-scope MainWindow method drift detected: {method_name}")

task_slot = qt_nodes.get("TaskSlotWidget")
if task_slot is None:
    fail("v1.0.6.8 Workflow Inputs TaskSlotWidget is missing")
task_slot_methods = {
    node.name: node
    for node in task_slot.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}
for method_name, expected_sha in workflow_inputs_scope.get("frozen_taskslotwidget_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_task or method_name in browser_ui_allowed_task or method_name in managed_allowed_task or method_name in workspace_allowed_task or method_name in capability_allowed_task or method_name in tasks_ui_allowed_task or method_name in tasks_ui_allowed_task:
        continue
    node = task_slot_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.8 Workflow Inputs TaskSlotWidget drift detected: {method_name}")

# v1.0.6.9 verifies the promoted v1.0.6.8 Workflow Inputs release and permits
# only the two page-local persistence error handlers to change.
if not WORKFLOW_INPUTS_FIX_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.9 Workflow Inputs verification/fix scope contract is missing")
try:
    workflow_fix_scope = json.loads(WORKFLOW_INPUTS_FIX_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.9 Workflow Inputs verification/fix scope contract is invalid: {exc}")
if workflow_fix_scope.get("official_baseline_github_commit") != "82fc678fe4d3e8aab9c11ff3e54cf4455e0d3203":
    fail("v1.0.6.9 fix scope does not identify the exact GitHub v1.0.6.8 baseline commit")
if workflow_fix_scope.get("official_baseline_tree_fingerprint") != "8358ffdca13bedd491ee319aae299fdf9ff636e6cb74caf7dbb53c389d94f6b7":
    fail("v1.0.6.9 Workflow Inputs baseline tree fingerprint mismatch")
if workflow_fix_scope.get("target_version") != "1.0.6.9":
    fail("v1.0.6.9 Workflow Inputs fix scope target version mismatch")
if workflow_fix_scope.get("allowed_runtime_source_changes") != ["src/vibrapilot/qt_app.py"]:
    fail("v1.0.6.9 Workflow Inputs fix runtime surface mismatch")
workflow_fix_approved_methods = set(workflow_fix_scope.get("approved_mainwindow_method_changes", []))
if workflow_fix_approved_methods != {"save_workflow_inputs", "reset_workflow_inputs"}:
    fail("v1.0.6.9 approved MainWindow method surface mismatch")
for relative, expected_sha in workflow_fix_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in license_allowed_files or relative in qt_focus_allowed_files or relative in browser_ui_allowed_files or relative in managed_allowed_files or relative in workspace_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected_sha:
        fail(f"v1.0.6.9 Workflow Inputs out-of-scope file drift detected: {relative}")
if workflow_fix_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.9 Workflow Inputs fix AST hash algorithm mismatch")
for method_name, expected_sha in workflow_fix_scope.get("frozen_mainwindow_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_main or method_name in pr07_allowed_main or method_name in license_allowed_mw_methods or method_name in browser_ui_allowed_main or method_name in managed_allowed_main or method_name in workspace_allowed_main or method_name in capability_allowed_main or method_name in tasks_ui_allowed_main or method_name in tasks_ui_allowed_main or method_name in tasks_ui_allowed_main:
        continue
    if method_name in workflow_fix_approved_methods:
        fail(f"v1.0.6.9 fix scope incorrectly freezes approved MainWindow method: {method_name}")
    node = main_window_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.9 Workflow Inputs out-of-scope MainWindow drift detected: {method_name}")

# v1.0.6.10 exact current scope verification.
for relative, expected_sha in license_fix_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr04_allowed_files:
        continue
    if relative in qt_focus_allowed_files or relative in managed_allowed_files or relative in workspace_allowed_files or relative in capability_allowed_files or relative in capability_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected_sha:
        fail(f"v1.0.6.10 license out-of-scope file drift detected: {relative}")
if license_fix_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.10 license scope AST hash algorithm mismatch")
license_ast_checks = {
    "backend.SELECTORS": backend_assignment_nodes.get("SELECTORS"),
    "backend.TaskItem": production_nodes.get("TaskItem"),
    "backend.TaskState": production_nodes.get("TaskState"),
    "backend.AutomationWorker": production_nodes.get("AutomationWorker"),
    "qt_app.ActivationPage": qt_nodes.get("ActivationPage"),
    "qt_app.BROWSER_SETTING_GROUPS": qt_ann_nodes.get("BROWSER_SETTING_GROUPS"),
}
for name, expected_sha in license_fix_scope.get("frozen_ast_sha256", {}).items():
    if name == "backend.AutomationWorker" and (browser_ui_allowed_worker or capability_allowed_worker or pr04_allowed_worker):
        continue
    node = license_ast_checks.get(name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.10 license out-of-scope AST drift detected: {name}")
license_manager_node = production_nodes.get("LicenseManager")
if license_manager_node is None:
    fail("v1.0.6.10 LicenseManager is missing")
license_manager_methods = {
    node.name: node for node in license_manager_node.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}
for method_name, expected_sha in license_fix_scope.get("frozen_licensemanager_method_ast_sha256", {}).items():
    if method_name in license_allowed_lm_methods:
        fail(f"v1.0.6.10 license scope incorrectly freezes approved LicenseManager method: {method_name}")
    node = license_manager_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.10 out-of-scope LicenseManager drift: {method_name}")
for method_name, expected_sha in license_fix_scope.get("frozen_mainwindow_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_main or method_name in pr07_allowed_main or method_name in browser_ui_allowed_main or method_name in managed_allowed_main or method_name in workspace_allowed_main or method_name in capability_allowed_main or method_name in tasks_ui_allowed_main or method_name in tasks_ui_allowed_main:
        continue
    if method_name in license_allowed_mw_methods:
        fail(f"v1.0.6.10 license scope incorrectly freezes approved MainWindow method: {method_name}")
    node = main_window_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.10 out-of-scope MainWindow drift: {method_name}")

# v1.0.6.12 exact current browser UI/lifecycle scope verification.
if browser_ui_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.12 browser UI lifecycle AST hash algorithm mismatch")
current_scope_ast = {
    "backend.LicenseManager": production_nodes.get("LicenseManager"),
    "backend.TaskItem": production_nodes.get("TaskItem"),
    "backend.TaskState": production_nodes.get("TaskState"),
    "backend.SELECTORS": backend_assignment_nodes.get("SELECTORS"),
    "qt_app.ActivationPage": qt_nodes.get("ActivationPage"),
    "qt_app.BROWSER_SETTING_GROUPS": qt_ann_nodes.get("BROWSER_SETTING_GROUPS"),
}
for name, expected_sha in browser_ui_scope.get("frozen_ast_sha256", {}).items():
    node = current_scope_ast.get(name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.12 browser UI frozen AST drift detected: {name}")
for method_name, expected_sha in browser_ui_scope.get("frozen_automationworker_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_worker or method_name in managed_allowed_worker or method_name in capability_allowed_worker or method_name in pr04_allowed_worker:
        continue
    node = automation_worker_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.12 browser UI out-of-scope AutomationWorker drift: {method_name}")
for method_name, expected_sha in browser_ui_scope.get("frozen_taskslotwidget_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_task or method_name in managed_allowed_task or method_name in workspace_allowed_task or method_name in capability_allowed_task or method_name in tasks_ui_allowed_task:
        continue
    node = task_slot_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.12 browser UI out-of-scope TaskSlotWidget drift: {method_name}")
for method_name, expected_sha in browser_ui_scope.get("frozen_mainwindow_method_ast_sha256", {}).items():
    if method_name in pr08_allowed_main or method_name in pr07_allowed_main or method_name in managed_allowed_main or method_name in workspace_allowed_main or method_name in capability_allowed_main or method_name in tasks_ui_allowed_main:
        continue
    node = main_window_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.12 browser UI out-of-scope MainWindow drift: {method_name}")

# Local developer check: when the private project workspace is present, prove that
# the published machine contract still describes the private v1.0.6 baseline.
if PRIVATE_BASELINE.is_file():
    private_methods = class_methods(PRIVATE_BASELINE)
    private_nodes = class_nodes(PRIVATE_BASELINE)
    private_function_nodes = function_nodes(PRIVATE_BASELINE)
    for cls in CORE_CLASSES:
        if private_methods.get(cls) != expected_methods.get(cls):
            fail(f"public backend contract no longer matches private baseline for {cls}")
    for cls, expected_sha in backend_contract.get("frozen_class_ast_sha256", {}).items():
        node = private_nodes.get(cls)
        if node is None or ast_contract_sha(node) != expected_sha:
            fail(f"public frozen-class contract no longer matches private baseline for {cls}")
    for name, expected_sha in backend_contract.get("frozen_helper_ast_sha256", {}).items():
        node = private_function_nodes.get(name)
        if node is None or ast_contract_sha(node) != expected_sha:
            fail(f"public frozen-helper contract no longer matches private baseline for {name}")

# Current PR-04 exact boundary verification.
for relative, expected_sha in pr04_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.20 PR-04 frozen file drift detected: {relative}")
if pr04_scope.get("ast_hash_algorithm") != AST_HASH_ALGORITHM:
    fail("v1.0.6.20 PR-04 AST hash algorithm mismatch")
pr04_backend_ast = pr04_scope.get("frozen_backend_ast_sha256", {})
backend_assignments_current = assignment_nodes(SRC / "backend.py")
for name, expected_sha in pr04_backend_ast.items():
    if name == "SELECTORS":
        node = backend_assignments_current.get("SELECTORS")
    else:
        node = production_nodes.get(name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.20 PR-04 frozen backend AST drift detected: {name}")
for method_name, expected_sha in pr04_scope.get("frozen_automationworker_method_ast_sha256", {}).items():
    node = automation_worker_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.20 PR-04 safety-critical worker drift detected: {method_name}")


for relative, expected_sha in pr04_ci_fix_scope.get("frozen_runtime_support_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    if relative in pr05_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.21 runtime/support drift detected outside approved PR-05 scope: {relative}")

for relative, expected_sha in pr05_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files:
        continue
    if relative in pr06_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.22 PR-05 frozen file drift detected: {relative}")
for method_name, expected_sha in pr05_scope.get("frozen_automationworker_method_canonical_ast_sha256", {}).items():
    node = automation_worker_methods.get(method_name)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.22 PR-05 safety-critical worker drift detected: {method_name}")

print("[5/8] AppConfig, licensing and safety invariants")
backend_text = (SRC / "backend.py").read_text(encoding="utf-8")
qt_text = (SRC / "qt_app.py").read_text(encoding="utf-8")
build_text = (ROOT / "build.py").read_text(encoding="utf-8")
package_init_text = (SRC / "__init__.py").read_text(encoding="utf-8")

for relative, expected_sha in pr06_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files or relative in pr10_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.23 PR-06 frozen file drift detected: {relative}")
for method_name, expected_sha in pr06_scope.get("frozen_automationworker_method_canonical_ast_sha256", {}).items():
    worker_node = production_nodes.get("AutomationWorker")
    node = next((item for item in worker_node.body if isinstance(item, ast.FunctionDef) and item.name == method_name), None)
    if node is None or ast_contract_sha(node) != expected_sha:
        fail(f"v1.0.6.23 PR-06 safety-critical worker drift detected: {method_name}")
for key in (
    "same_workflow_noop", "corrupt_state_fail_closed", "unknown_state_fail_closed",
    "no_silent_share_invite_fallback", "switch_block_running_tasks",
    "switch_block_manual_review", "switch_block_concurrent_transaction",
    "confirmation_required_for_real_switch", "precommit_rollback_required",
    "workflow_state_replace_is_commit_point", "postcommit_restart_failure_does_not_rollback",
    "source_and_frozen_restart_supported", "automatic_restart_loop_prohibited",
    "no_new_ui_page", "no_workflow_showcase_ui", "no_dynamic_workflow_inputs",
    "no_task_database_schema_change", "no_workspace_schema_change", "no_report_schema_change",
    "no_browser_change", "no_dependency_change", "no_licensing_change",
    "captcha_out_of_scope", "external_plugin_loading_prohibited",
    "manifest_controlled_dynamic_import_prohibited",
):
    if pr06_scope.get(key) is not True:
        fail(f"v1.0.6.23 PR-06 boundary missing: {key}")

for relative, expected_sha in pr07_scope.get("frozen_file_sha256", {}).items():
    if relative in pr08_allowed_files or relative in pr10_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.24 PR-07 frozen file drift detected: {relative}")
for key in (
    "no_fake_demo_placeholder_workflows", "no_dynamic_workflow_inputs",
    "no_workflow_engine_change", "no_workflow_state_schema_change",
    "no_task_database_schema_change", "no_workspace_schema_change",
    "no_report_schema_change", "no_browser_change", "no_licensing_change",
    "captcha_out_of_scope", "no_dependency_change", "no_ci_workflow_change",
    "external_plugin_loading_prohibited", "filesystem_workflow_discovery_prohibited",
    "manifest_controlled_dynamic_import_prohibited",
):
    if pr07_scope.get(key) is not True:
        fail(f"v1.0.6.24 PR-07 boundary missing: {key}")

required_nav = 'NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]'
if required_nav not in qt_text:
    fail("v1.0.6.24 PR-07 Workflows navigation order mismatch")
for marker in (
    "def make_workflows_page(self) -> QWidget:",
    "self.workflow_catalog.list_workflows()",
    "self.workflow_catalog.require_runtime_factory(manifest.workflow_id)",
    "self.request_workflow_switch(workflow_id)",
    'elif name == "Workflows":',
    "self.refresh_workflow_showcase()",
):
    if marker not in qt_text:
        fail(f"v1.0.6.24 PR-07 UI integration marker missing: {marker}")
registry_text = (SRC / "workflow" / "registry.py").read_text(encoding="utf-8")
if "return (SHARE_INVITE_MANIFEST,)" not in registry_text or "other_workflow" in registry_text:
    fail("v1.0.6.24 PR-07 production workflow registry drift detected")

for relative, expected_sha in pr08_scope.get("frozen_file_sha256", {}).items():
    if relative in pr10_allowed_files:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.25 PR-08 frozen file drift detected: {relative}")
for key in (
    "no_second_or_fake_workflow", "no_dynamic_workflow_actions",
    "no_workflow_state_schema_change", "no_atomic_switch_redesign",
    "no_task_database_schema_change", "no_workspace_schema_change",
    "no_report_schema_change", "no_browser_change", "no_licensing_change",
    "captcha_out_of_scope", "no_dependency_change", "no_ci_workflow_change",
    "pr09_not_started", "external_plugin_loading_prohibited",
    "filesystem_workflow_discovery_prohibited",
    "manifest_controlled_dynamic_import_prohibited",
    "arbitrary_callback_execution_prohibited",
):
    if pr08_scope.get(key) is not True:
        fail(f"v1.0.6.25 PR-08 boundary missing: {key}")
workflow_inputs_text_current = (SRC / "workflow_inputs.py").read_text(encoding="utf-8")
input_state_text_current = (SRC / "workflow" / "input_state.py").read_text(encoding="utf-8")
for marker in (
    "WORKFLOW_INPUT_SCHEMAS",
    'workflow_id="share_invite"',
    'WORKFLOW_INPUT_STATE_SCHEMA_VERSION = 1',
    'APP_DATA_DIR / "workflow_inputs.json"',
    "workflow_input_values=self.app.current_workflow_input_snapshot()",
    "self.workflow_input_state_error",
):
    if marker not in (workflow_inputs_text_current + input_state_text_current + qt_text):
        fail(f"v1.0.6.25 PR-08 integration marker missing: {marker}")
for forbidden in ("importlib", "entry_points", "__import__", "eval(", "exec("):
    if forbidden in workflow_inputs_text_current + input_state_text_current:
        fail(f"v1.0.6.25 PR-08 executable/discovery surface detected: {forbidden}")

if not PR09_DATA_COMPATIBILITY_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.26 PR-09 data/persistence/reporting compatibility scope contract is missing")
try:
    pr09_scope = json.loads(PR09_DATA_COMPATIBILITY_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.26 PR-09 scope contract is invalid: {exc}")
if pr09_scope.get("plan_id") != "VP-PR09-DATA-PERSISTENCE-REPORTING-COMPAT-001":
    fail("v1.0.6.26 PR-09 plan identifier mismatch")
if pr09_scope.get("official_baseline_archive_sha256") != "05c98db56204bf4ee057fe9422da3dd20695a91ae8fad13419ec9f3ad32fe353":
    fail("v1.0.6.26 PR-09 official baseline archive mismatch")
if pr09_scope.get("baseline_github_commit") != "8b62a48982f1497c272a68cb3b428f5bd1b0d3c0":
    fail("v1.0.6.26 PR-09 baseline GitHub commit mismatch")
if pr09_scope.get("target_version") != "1.0.6.26":
    fail("v1.0.6.26 PR-09 target mismatch")
if pr09_scope.get("allowed_production_source_changes") != [] or pr09_scope.get("production_runtime_changes") != "none":
    fail("v1.0.6.26 PR-09 must not authorize production runtime source changes")
for key, expected in {
    "one_active_workflow": True,
    "task_runtime_schema_version": 1,
    "workflow_id_database_column": False,
    "database_migration": False,
    "taskitem_redesign": False,
    "workspace_schema_change": False,
    "report_schema_change": False,
    "dynamic_task_import_schema": False,
    "cross_workflow_live_report_history": False,
    "real_switch_clears_live_task_runtime": True,
    "real_switch_clears_live_results": True,
    "same_workflow_zero_mutation": True,
    "cancelled_or_blocked_switch_zero_mutation": True,
    "precommit_rollback_preserves_old_runtime": True,
    "postcommit_old_runtime_resurrection_prohibited": True,
    "exported_reports_preserved": True,
    "failed_data_preserved": True,
    "logs_preserved": True,
    "canonical_workflow_inputs_preserved": True,
    "no_browser_change": True,
    "no_licensing_change": True,
    "captcha_out_of_scope": True,
    "no_dependency_change": True,
    "no_ci_workflow_change": True,
    "pr10_not_started": True,
}.items():
    if pr09_scope.get(key) != expected:
        fail(f"v1.0.6.26 PR-09 boundary mismatch: {key}")
if pr09_scope.get("production_workflows") != ["share_invite"]:
    fail("v1.0.6.26 PR-09 production workflow registry contract mismatch")
if pr09_scope.get("canonical_workflow_inputs_path") != "AppData/workflow_inputs.json":
    fail("v1.0.6.26 PR-09 canonical Workflow Input preservation path mismatch")
if pr09_scope.get("live_report_columns") != ["timestamp", "slot_id", "email", "status", "message", "attempts", "target_url", "result"]:
    fail("v1.0.6.26 PR-09 live report column contract mismatch")
if pr09_scope.get("taskitem_fields") != ["email", "name", "status", "attempts", "message", "result"]:
    fail("v1.0.6.26 PR-09 TaskItem contract mismatch")
pr10_allowed = set(pr10_allowed_files)
for relative, expected_sha in pr09_scope.get("frozen_file_sha256", {}).items():
    if relative in pr10_allowed:
        continue
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.26 PR-09 frozen production/runtime drift detected: {relative}")
for marker in (
    'SCHEMA_VERSION = 1',
    'CREATE TABLE IF NOT EXISTS runs',
    'CREATE TABLE IF NOT EXISTS items',
    'CREATE TABLE IF NOT EXISTS results',
):
    if marker not in (SRC / "task_runtime_store.py").read_text(encoding="utf-8"):
        fail(f"v1.0.6.26 PR-09 TaskRuntimeStore compatibility marker missing: {marker}")
if "workflow_id" in (SRC / "task_runtime_store.py").read_text(encoding="utf-8"):
    fail("v1.0.6.26 PR-09 must not add workflow_id to TaskRuntimeStore")
for marker in (
    'Path(str(TASK_RUNTIME_DB) + "-wal")',
    'Path(str(TASK_RUNTIME_DB) + "-shm")',
    'APP_DATA_DIR.glob("slot_*_checkpoint.json")',
    '"active_tasks": []',
    '"next_slot_id": 1',
    'self.report_rows = []',
    'return "already_active"',
    'return "cancelled"',
    'transaction.rollback()',
):
    if marker not in qt_text:
        fail(f"v1.0.6.26 PR-09 switch compatibility marker missing: {marker}")
for forbidden in ("REPORTS_DIR", "FAILED_DATA_DIR", "LOGS_DIR"):
    clear_start = qt_text.index("def _clear_workflow_scoped_state")
    clear_end = qt_text.index("def _restore_after_failed_workflow_switch", clear_start)
    if forbidden in qt_text[clear_start:clear_end]:
        fail(f"v1.0.6.26 PR-09 preserved path entered destructive clear routine: {forbidden}")

if pr10_scope.get("plan_id") != "VP-PR10-WORKFLOW-ERROR-RECOVERY-001":
    fail("v1.0.6.27 PR-10 plan identifier mismatch")
if pr10_scope.get("official_baseline_archive_sha256") != "1e464918eb8d9aa5e89170144a2c020e2374b5d8dd9c9563ab6676cdc167e569":
    fail("v1.0.6.27 PR-10 official baseline mismatch")
if pr10_scope.get("baseline_github_commit") != "e0e443a7cac808b1e0fa22749307e641b288869d":
    fail("v1.0.6.27 PR-10 baseline GitHub commit mismatch")
if pr10_scope.get("target_version") != "1.0.6.27":
    fail("v1.0.6.27 PR-10 target mismatch")
expected_pr10_allowed = {
    "src/vibrapilot/workflow/contracts.py",
    "src/vibrapilot/workflow/state.py",
    "src/vibrapilot/workflow/input_state.py",
    "src/vibrapilot/workflow/recovery.py",
    "src/vibrapilot/workflow/__init__.py",
    "src/vibrapilot/qt_app.py",
}
if pr10_allowed != expected_pr10_allowed:
    fail("v1.0.6.27 PR-10 production source scope mismatch")
for key, expected in {
    "workflow_state_schema_version": 1,
    "workflow_input_state_schema_version": 1,
    "workflow_recovery_transaction_schema_version": 1,
    "automatic_workflow_state_recovery": False,
    "automatic_workflow_input_recovery": False,
    "legacy_input_remigration_during_recovery": False,
    "runtime_factory_preflight_before_browser": True,
    "runtime_error_blocks_browser": True,
    "runtime_error_alone_blocks_switch_away": False,
    "unresolved_switch_transaction_hard_blocks_recovery": True,
    "unresolved_recovery_transaction_hard_blocks_automation": True,
    "input_recovery_uses_source_defaults": True,
    "input_recovery_preserves_quarantine": True,
    "input_recovery_blocked_with_live_worker": True,
    "input_recovery_rolls_back_on_compatibility_save_failure": True,
    "task_runtime_schema_version": 1,
    "task_database_schema_change": False,
    "workspace_schema_change": False,
    "report_schema_change": False,
    "share_invite_runtime_change": False,
    "browser_change": False,
    "licensing_change": False,
    "captcha_bypass_change": False,
    "dependency_change": False,
    "ci_workflow_change": False,
    "new_or_fake_workflow": False,
    "pr11_not_started": True,
    "packaging_implementation": False,
}.items():
    if pr10_scope.get(key) != expected:
        fail(f"v1.0.6.27 PR-10 boundary mismatch: {key}")
if pr10_scope.get("production_workflows") != ["share_invite"]:
    fail("v1.0.6.27 PR-10 production registry contract mismatch")
if pr10_scope.get("error_domains") != [
    "workflow_state_error", "workflow_input_state_error",
    "workflow_recovery_error", "workflow_runtime_error",
]:
    fail("v1.0.6.27 PR-10 error-domain contract mismatch")
for relative, expected_sha in pr10_scope.get("frozen_file_sha256", {}).items():
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.27 PR-10 frozen surface drift detected: {relative}")
recovery_text = (SRC / "workflow" / "recovery.py").read_text(encoding="utf-8")
for marker in (
    'WORKFLOW_RECOVERY_TRANSACTION_SCHEMA_VERSION = 1',
    'RECOVERY_PREPARED = "PREPARED"',
    'RECOVERY_COMMITTED = "COMMITTED"',
    'class WorkflowRecoveryTransaction:',
    'def recover_active_workflow(self, target_workflow_id: str)',
    'def recover_workflow_defaults(',
    'self.workflow_recovery_error',
    'self.workflow_runtime_error',
    'def request_workflow_state_recovery(',
    'button("Recover Workflow Inputs"',
    'runtime_error = self._refresh_workflow_runtime_error()',
):
    if marker not in (recovery_text + (SRC / "workflow" / "state.py").read_text(encoding="utf-8") + (SRC / "workflow" / "input_state.py").read_text(encoding="utf-8") + qt_text):
        fail(f"v1.0.6.27 PR-10 recovery marker missing: {marker}")
for forbidden in ("Nuitka", "WiX", "CL Automation"):
    if forbidden in qt_text + recovery_text:
        fail(f"v1.0.6.27 PR-10 packaging implementation leaked into runtime: {forbidden}")

if not PR11_WINDOWS_MULTITASK_SCOPE_CONTRACT.is_file():
    fail("v1.0.6.28 PR-11 Windows / Multi-Task Regression scope contract is missing")
try:
    pr11_scope = json.loads(PR11_WINDOWS_MULTITASK_SCOPE_CONTRACT.read_text(encoding="utf-8"))
except Exception as exc:
    fail(f"v1.0.6.28 PR-11 scope contract is invalid: {exc}")
if pr11_scope.get("plan_id") != "VP-PR11-WINDOWS-MULTITASK-E2E-001":
    fail("v1.0.6.28 PR-11 plan identifier mismatch")
if pr11_scope.get("official_baseline_archive_sha256") != "06370a3959a60d848e7051435e10835162ab21a579296d0506be2f2eb54d7df1":
    fail("v1.0.6.28 PR-11 official baseline mismatch")
if pr11_scope.get("baseline_github_commit") != "5ec078deb1304ace70bc88879cab2b300f88cde4":
    fail("v1.0.6.28 PR-11 baseline GitHub commit mismatch")
if pr11_scope.get("target_version") != "1.0.6.28":
    fail("v1.0.6.28 PR-11 target mismatch")
if pr11_scope.get("production_runtime_changes") != "none":
    fail("v1.0.6.28 PR-11 must remain verification-first with no production runtime changes")
if pr11_scope.get("allowed_production_source_changes") != []:
    fail("v1.0.6.28 PR-11 production source scope must remain empty")
if pr11_scope.get("task_matrix") != [1, 2, 4]:
    fail("v1.0.6.28 PR-11 1/2/4 Task matrix mismatch")
if pr11_scope.get("production_workflows") != ["share_invite"]:
    fail("v1.0.6.28 PR-11 production registry contract mismatch")
if pr11_scope.get("evidence_status_values") != [
    "PASS", "FAIL", "BLOCKED", "NOT_RUN", "OWNER_ACCEPTED_RESIDUAL",
]:
    fail("v1.0.6.28 PR-11 evidence status vocabulary mismatch")
for key, expected in {
    "sandbox_default": False,
    "sandbox_on_test_may_not_change_default": True,
    "allow_chromium_fallback_default": True,
    "captcha_deferred_unverified": True,
    "stealth_or_fingerprint_spoofing": False,
    "global_chrome_process_kill_forbidden": True,
    "managed_exact_pid_kill_only": True,
    "product_defect_requires_scope_amendment": True,
    "harness_error_max_fix_verify_cycles": 2,
    "task_runtime_schema_version": 1,
    "workflow_recovery_transaction_schema_version": 1,
    "packaging_implementation": False,
    "pr12_not_started": True,
}.items():
    if pr11_scope.get(key) != expected:
        fail(f"v1.0.6.28 PR-11 boundary mismatch: {key}")
expected_pr11_production = sorted(
    path.relative_to(ROOT).as_posix()
    for path in SRC.rglob("*")
    if path.is_file()
    and "__pycache__" not in path.parts
    and path.suffix != ".pyc"
)
pr11_hashes = pr11_scope.get("frozen_production_sha256", {})
if sorted(pr11_hashes) != expected_pr11_production:
    fail("v1.0.6.28 PR-11 frozen production inventory mismatch")
for relative, expected_sha in pr11_hashes.items():
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.28 PR-11 production source drift detected: {relative}")
for relative, expected_sha in pr11_scope.get("frozen_nonproduction_runtime_sha256", {}).items():
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        fail(f"v1.0.6.28 PR-11 frozen runtime/config drift detected: {relative}")
pr11_runner = ROOT / "scripts" / "diagnostics" / "pr11_windows_acceptance_runner.py"
pr11_evidence_verifier = ROOT / "scripts" / "diagnostics" / "verify_pr11_windows_evidence.py"
for path in (pr11_runner, pr11_evidence_verifier):
    if not path.is_file():
        fail(f"v1.0.6.28 PR-11 verification tooling missing: {path.relative_to(ROOT)}")
pr11_runner_text = pr11_runner.read_text(encoding="utf-8")
for marker in (
    'ALLOWED_STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "OWNER_ACCEPTED_RESIDUAL"}',
    'default_evidence_root(root: Path)',
    '"AppData" / "PR11Acceptance"',
    'TEST_DOWNLOAD = b"VibraPilot PR-11 deterministic download fixture\\n"',
    'def safe_kill_from_diagnostic(',
    '["taskkill", "/PID", str(pid), "/T", "/F"]',
    'if pid <= 0 or pid != expected_pid' if False else 'pid != expected_pid',
    'Do not retry it away',
):
    if marker not in pr11_runner_text:
        fail(f"v1.0.6.28 PR-11 runner marker missing: {marker}")
for forbidden in (
    'taskkill", "/IM", "chrome.exe"',
    'shutil.rmtree(root / "AppData"',
    'settings.defaults.json", "w"',
):
    if forbidden in pr11_runner_text:
        fail(f"v1.0.6.28 PR-11 unsafe runner behavior detected: {forbidden}")

app_version = literal_assignment(APP_CONFIG_APP, "VERSION")
app_id = literal_assignment(APP_CONFIG_APP, "APP_ID")
app_name = literal_assignment(APP_CONFIG_APP, "APP_NAME")
display_name = literal_assignment(APP_CONFIG_APP, "DISPLAY_NAME")
description = literal_assignment(APP_CONFIG_APP, "DESCRIPTION")
owner_name = literal_assignment(APP_CONFIG_APP, "OWNER_NAME")
license_identifier = literal_assignment(APP_CONFIG_APP, "LICENSE_IDENTIFIER")
homepage_url = literal_assignment(APP_CONFIG_APP, "HOMEPAGE_URL")
repository_url = literal_assignment(APP_CONFIG_APP, "REPOSITORY_URL")
if app_version != "1.0.6.28":
    fail("AppConfig VERSION must be 1.0.6.28 for the PR-11 Windows / Multi-Task Regression candidate")
for name, value in {
    "APP_ID": app_id,
    "APP_NAME": app_name,
    "DISPLAY_NAME": display_name,
    "DESCRIPTION": description,
    "OWNER_NAME": owner_name,
    "LICENSE_IDENTIFIER": license_identifier,
    "HOMEPAGE_URL": homepage_url,
    "REPOSITORY_URL": repository_url,
}.items():
    if not isinstance(value, str) or not value.strip():
        fail(f"AppConfig {name} must be a non-empty literal string")

support_config = APP_CONFIG_ROOT / "support.py"
social_config = APP_CONFIG_ROOT / "social.py"
about_config = APP_CONFIG_ROOT / "about.py"
if literal_assignment(support_config, "SUPPORT_EMAIL") != "support@vib.tools":
    fail("Phase-01 SUPPORT_EMAIL must use the confirmed Vib Tools support address")
if literal_assignment(support_config, "CONTACT_URL") != "https://vib.tools/contact":
    fail("Phase-01 CONTACT_URL must use the confirmed Vib Tools contact endpoint")
if literal_assignment(support_config, "DEVELOPER_PORTAL_URL") != "":
    fail("Unverified developer portal URLs must remain blank")
social_links = literal_assignment(social_config, "SOCIAL_LINKS")
expected_social = {
    "GitHub": "https://github.com/vibtools",
    "X": "https://x.com/vibtools",
    "Facebook": "https://www.facebook.com/vib.tools",
    "Instagram": "https://www.instagram.com/vibtools",
    "Reddit": "https://www.reddit.com/user/VibTools/",
    "TikTok": "https://www.tiktok.com/@vibtools",
    "GitLab": "https://gitlab.com/vibtools",
}
if not isinstance(social_links, tuple):
    fail("Phase-01 SOCIAL_LINKS must be a literal tuple")
actual_social = {
    item.get("platform"): item.get("url")
    for item in social_links
    if isinstance(item, dict) and item.get("enabled") is True
}
if actual_social != expected_social:
    fail(f"Phase-01 official social-link contract drift: {actual_social}")
for field in (
    "COMPANY_LEGAL_NAME", "COMPANY_DISPLAY_NAME", "COMPANY_DESCRIPTION",
    "COMPANY_WEBSITE_LABEL", "SUPPORT_TEAM_NAME",
):
    if literal_assignment(about_config, field) is None:
        fail(f"Phase-01 About company metadata field missing: {field}")

for app_config_path in APP_CONFIG_ROOT.glob("*.py"):
    app_config_text = app_config_path.read_text(encoding="utf-8")
    for forbidden_secret_name in ("LICENSE_API_KEY", "LICENSE_VERIFY_URL", "BEGIN PRIVATE KEY"):
        if forbidden_secret_name in app_config_text:
            fail(
                f"Phase-02 AppConfig contains forbidden licensing secret/legacy marker: "
                f"{app_config_path.name}:{forbidden_secret_name}"
            )
licensing_public = APP_CONFIG_ROOT / "licensing_public.py"
if not licensing_public.is_file():
    fail("Phase-02 public Licora API v2 configuration is missing")
licora_base = literal_assignment(licensing_public, "LICORA_API_BASE_URL")
licora_version = literal_assignment(licensing_public, "LICORA_API_VERSION")
licora_protocol = literal_assignment(licensing_public, "LICORA_PROTOCOL")
licora_app_id = literal_assignment(licensing_public, "LICORA_APP_ID")
licora_key_id = literal_assignment(licensing_public, "LICORA_SIGNING_KEY_ID")
licora_public_pem = literal_assignment(licensing_public, "LICORA_SIGNING_PUBLIC_KEY_PEM")
licora_public_sha = literal_assignment(licensing_public, "LICORA_SIGNING_PUBLIC_KEY_SHA256")
if not isinstance(licora_base, str) or not licora_base.startswith("https://"):
    fail("Licora API v2 base URL must be source-controlled HTTPS public configuration")
if licora_version != 2 or licora_protocol != "licora-api-v2":
    fail("Licora public protocol must be Secure API v2")
if licora_app_id != app_id or licora_app_id != "vibrapilot":
    fail("Licora App ID must match authoritative VibraPilot APP_ID")
if not isinstance(licora_key_id, str) or not licora_key_id.strip():
    fail("Licora signing key ID is missing")
if not isinstance(licora_public_pem, str) or "BEGIN PUBLIC KEY" not in licora_public_pem or "PRIVATE KEY" in licora_public_pem:
    fail("Licora pinned signing material must contain only the public key")
if not isinstance(licora_public_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", licora_public_sha):
    fail("Licora public-key SHA-256 must be a 64-character lowercase hex digest")
normalized_public = licora_public_pem if licora_public_pem.endswith("\n") else licora_public_pem + "\n"
if hashlib.sha256(normalized_public.encode("ascii")).hexdigest() != licora_public_sha:
    fail("Licora pinned public-key SHA-256 does not match the configured PEM")
for endpoint_name in ("LICORA_ACTIVATE_PATH", "LICORA_STATUS_PATH", "LICORA_REFRESH_PATH", "LICORA_DEACTIVATE_PATH"):
    endpoint = literal_assignment(licensing_public, endpoint_name)
    if not isinstance(endpoint, str) or not endpoint.startswith("/api/v2/") or not endpoint.endswith(".php"):
        fail(f"invalid Licora API v2 endpoint path: {endpoint_name}")

for marker in [
    "DISPLAY_APP_NAME = APP.display_name",
    "APP_NAME = APP.app_name",
    "APP_VERSION = APP.version",
    "APP_AUTHOR = APP.author_name",
    "RELEASE_DATE = APP.release_date",
]:
    if marker not in backend_text:
        fail(f"backend must consume authoritative AppConfig metadata: {marker}")
if "__version__ = APP.version" not in package_init_text:
    fail("package __version__ must consume AppConfig VERSION")
if "from config.AppConfig.app import APP_NAME, VERSION" not in build_text or "APP_VERSION = VERSION" not in build_text:
    fail("build name/version must consume AppConfig metadata")

app_config_facade_text = (SRC / "app_config.py").read_text(encoding="utf-8")
for marker in (
    "date.fromisoformat(text)",
    "_VERSION_RE.fullmatch(text)",
    '_optional_email("SUPPORT_EMAIL"',
    "if not isinstance(enabled, bool):",
    '_required_text_tuple("TARGET_FEATURES"',
    "class LicensingPublicInfo:",
    "LICENSING = LicensingPublicInfo(",
):
    if marker not in app_config_facade_text:
        fail(f"Phase-01 AppConfig validation marker missing: {marker}")
launcher_text = (ROOT / "scripts" / "Start-VibraPilot.ps1").read_text(encoding="utf-8")
if "VibraPilot-1.0.6.28-Windows-x64" not in launcher_text:
    fail("VibraPilot launcher must target the current v1.0.6.28 candidate path")

pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
project_meta = pyproject.get("project", {})
if project_meta.get("name") != app_id:
    fail("pyproject name must match AppConfig APP_ID")
if project_meta.get("version") != app_version:
    fail("pyproject version must match AppConfig VERSION")
if project_meta.get("description") != description:
    fail("pyproject description must match AppConfig DESCRIPTION")
if (project_meta.get("license") or {}).get("text") != license_identifier:
    fail("pyproject license must match AppConfig LICENSE_IDENTIFIER")
authors = project_meta.get("authors") or []
if not authors or authors[0].get("name") != owner_name:
    fail("pyproject author must match AppConfig OWNER_NAME")
project_urls = project_meta.get("urls") or {}
if project_urls.get("Homepage") != homepage_url:
    fail("pyproject Homepage must match AppConfig HOMEPAGE_URL")
if project_urls.get("Repository") != repository_url:
    fail("pyproject Repository must match AppConfig REPOSITORY_URL")

citation_text = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
if f"version: {app_version}" not in citation_text:
    fail("CITATION version must match AppConfig VERSION")
if f'license: {license_identifier}' not in citation_text:
    fail("CITATION license must match AppConfig LICENSE_IDENTIFIER")
vibproject = json.loads((ROOT / "vibproject.ygit").read_text(encoding="utf-8"))
if vibproject["project"]["version"] != app_version or vibproject["project"]["displayName"] != display_name:
    fail("vibproject identity/version must match AppConfig")
if vibproject["organization"]["company"] != owner_name:
    fail("vibproject company must match AppConfig OWNER_NAME")
if vibproject["license"]["spdx"] != license_identifier:
    fail("vibproject license must match AppConfig LICENSE_IDENTIFIER")
docs_manifest = json.loads((ROOT / "docs" / "docs.manifest.ygit").read_text(encoding="utf-8"))
if docs_manifest["documentation"]["version"] != app_version:
    fail("documentation manifest version must match AppConfig VERSION")

settings_defaults = json.loads((ROOT / "config" / "settings.defaults.json").read_text(encoding="utf-8"))
if settings_defaults.get("max_test_send_limit") != 50:
    fail("source-controlled default Test Send Limit must remain 50")
if settings_defaults.get("max_concurrent_tasks") != 4:
    fail("VP-PROD-MT-LR-001 max_concurrent_tasks default must be 4")
if settings_defaults.get("batch_size") != 1:
    fail("existing batch_size default must remain 1")
if settings_defaults.get("auto_save_interval") != 10:
    fail("existing auto_save_interval default must remain 10 seconds")
if settings_defaults.get("use_persistent_context") is not True:
    fail("v1.0.6.14 managed persistent browser default must be enabled")
if settings_defaults.get("restore_previous_session") is not False:
    fail("v1.0.6.14 must not enable previous-tab/session restoration by default")
if literal_assignment(SRC / "task_runtime_store.py", "SCHEMA_VERSION") != 1:
    fail("v1.0.6.14 must preserve TaskRuntimeStore SCHEMA_VERSION = 1")
production_runtime_store = SRC / "task_runtime_store.py"
if not production_runtime_store.is_file():
    fail("VP-PROD-MT-LR-001 task runtime store module is missing")
production_runtime_text = production_runtime_store.read_text(encoding="utf-8")
for marker in (
    "class TaskRuntimeStore", "PRAGMA journal_mode=WAL", "PRAGMA foreign_keys=ON",
    "def recoverable_runs", "def skip_current_manual_review", "def upsert_result",
    "self._write_lock = threading.RLock()", "def _write_connection",
    "def persist_item_result_progress",
):
    if marker not in production_runtime_text:
        fail(f"production runtime-store invariant missing: {marker}")
for forbidden_sqlite_durability in ("PRAGMA synchronous=NORMAL", "PRAGMA synchronous=OFF"):
    if forbidden_sqlite_durability in production_runtime_text:
        fail(f"Windows SQLite fix must not weaken durability: {forbidden_sqlite_durability}")
for marker in (
    "UI_QUEUE_CAPACITY = 4096", "UI_QUEUE_MAX_EVENTS_PER_TICK = 250",
    "queue.Queue(maxsize=UI_QUEUE_CAPACITY)", "max_concurrent_tasks",
    "offer_task_recovery", "can_open_task_browser",
):
    if marker not in qt_text:
        fail(f"production UI/runtime invariant missing: {marker}")
for marker in (
    "TASK_RUNTIME_DB", "stopped_event", "auto_save_interval", "batch_size",
    "maybe_recycle_context", "manual_review_required",
):
    if marker not in backend_text:
        fail(f"production worker/runtime invariant missing: {marker}")

# v1.0.6.7 verified corrections: startup style binding, shutdown-safe queue backpressure,
# crash-marker result durability, user-facing Send-attempt semantics and source ZIP hygiene.
if qt_text.count("@classmethod\n    @classmethod\n    def task_qss"):
    fail("TaskSlotWidget.task_qss has a duplicated @classmethod decorator")
for marker in (
    'visible_metric_name = "Send Attempts / Limit" if name == "Send Limit" else name',
    "TaskSlotWidget.task_qss()",
):
    if marker not in qt_text:
        fail(f"v1.0.6.7 UI correction marker missing: {marker}")
for marker in (
    "dropping saturated critical UI event during shutdown",
    "self.stop_event.is_set() or self.close_event.is_set()",
    "self.runtime_store.persist_item_result_progress(",
):
    if marker not in backend_text:
        fail(f"v1.0.6.7 worker/data-integrity correction marker missing: {marker}")
licensing_client_path = SRC / "licensing_v2.py"
if not licensing_client_path.is_file():
    fail("Phase-02 Licora API v2 client module is missing")
licensing_client_text = licensing_client_path.read_text(encoding="utf-8")
active_licensing_text = backend_text + "\n" + licensing_client_text + "\n" + licensing_public.read_text(encoding="utf-8")
for forbidden_marker in (
    "LICENSE_API_KEY =", "VIB_TOOLS_LICENSE_API_KEY", '"X-API-Key"',
    "/api/verify.php", "REPLACE_WITH_YOUR_LICORA_API_KEY", "BEGIN PRIVATE KEY",
):
    if forbidden_marker in active_licensing_text:
        fail(f"Phase-02 active licensing source contains forbidden legacy/secret marker: {forbidden_marker}")
for marker in [
    "LicoraV2Client", "generate_device_key_material", "load_device_key_material",
    "ec.SECP256R1()", "padding.PKCS1v15()", "hashes.SHA256()",
    'headers["Authorization"] = "Bearer " + access_token',
    "LICENSING.activate_path", "LICENSING.status_path", "LICENSING.refresh_path",
    "LICENSING.deactivate_path", "device_private_key_protected",
    "refresh_token_protected", "os.replace(temporary, LICENSE_FILE)",
]:
    if marker not in active_licensing_text:
        fail(f"required Secure API v2 invariant marker missing: {marker}")
for marker in ['assert_test_mode', 'SendClickOutcomeUncertain', 'safe_spreadsheet_cell']:
    if marker not in backend_text:
        fail(f"required frozen backend invariant marker missing: {marker}")
requirements_text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
requirements_build_text = (ROOT / "requirements-build.txt").read_text(encoding="utf-8")
if "cryptography" not in requirements_text or "cryptography" not in requirements_build_text:
    fail("cryptography must be declared for runtime and build dependencies")

# Approved Settings-page/runtime scope.
for key in ("default_full_name", "default_number", "fallback_name", "update_click_count"):
    if settings_defaults.get(key) != "":
        fail(f"legacy contact default must be blank: {key}")
if 'DEFAULT_SETTINGS_FILE = ROOT_DIR / "config" / "settings.defaults.json"' not in backend_text:
    fail("settings defaults must be source-controlled outside Python literals")
if 'if parsed < 0:' not in backend_text:
    fail("Test Send Limit must accept Settings-controlled non-negative values")
if 'MAX_TEST_SEND_LIMIT' in backend_text:
    fail("Test Send Limit must not have a hardcoded upper ceiling in application code")

# Workflow Inputs current ownership contract. Historical v1.0.6.8/9 keys remain
# compatibility aliases, while PR-08 supersedes the fixed-form/settings-backed
# implementation with source-controlled schemas + canonical per-workflow state.
workflow_inputs_path = SRC / "workflow_inputs.py"
workflow_input_state_path = SRC / "workflow" / "input_state.py"
if not workflow_inputs_path.is_file():
    fail("Workflow Inputs schema module is missing")
if not workflow_input_state_path.is_file():
    fail("PR-08 Workflow Input state module is missing")
workflow_inputs_text = workflow_inputs_path.read_text(encoding="utf-8")
workflow_input_state_text = workflow_input_state_path.read_text(encoding="utf-8")
expected_workflow_keys = ("default_full_name", "default_number", "fallback_name", "update_click_count")
for key in expected_workflow_keys:
    if f'key="{key}"' not in workflow_inputs_text:
        fail(f"Workflow Inputs compatibility field key is missing: {key}")
if 'default_target_url' in workflow_inputs_text:
    fail("default_target_url must not move into Workflow Inputs")
for marker in (
    "class WorkflowInputSchema",
    "WORKFLOW_INPUT_SCHEMAS",
    'workflow_id="share_invite"',
    'WORKFLOW_INPUT_KINDS = frozenset({"text", "integer", "boolean", "choice"})',
):
    if marker not in workflow_inputs_text:
        fail(f"PR-08 Workflow Input schema marker missing: {marker}")
for marker in (
    "class WorkflowInputStateStore",
    "WORKFLOW_INPUT_STATE_SCHEMA_VERSION = 1",
    "os.replace(temporary, self.path)",
    "def load_or_migrate",
    "def save_workflow_values",
):
    if marker not in workflow_input_state_text:
        fail(f"PR-08 Workflow Input persistence marker missing: {marker}")
for forbidden in ("importlib", "entry_points", "__import__", "eval(", "exec("):
    if forbidden in workflow_inputs_text + workflow_input_state_text:
        fail(f"Workflow Input schema/persistence contains forbidden executable discovery surface: {forbidden}")
nav_sections = literal_assignment(ROOT / "src" / "vibrapilot" / "qt_app.py", "NAV_SECTIONS")
if nav_sections != ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]:
    fail("Workflow Inputs / PR-07 navigation order mismatch")
for method_name in (
    "make_workflow_inputs_page", "refresh_workflow_input_widgets",
    "save_workflow_inputs", "reset_workflow_inputs",
    "_persist_active_workflow_input_values", "current_workflow_input_snapshot",
):
    if method_name not in main_window_methods:
        fail(f"PR-08 Workflow Inputs MainWindow method is missing: {method_name}")
settings_page_source = ast.get_source_segment(qt_text, main_window_methods["make_settings_page"]) or ""
workflow_page_source = (
    (ast.get_source_segment(qt_text, main_window_methods["make_workflow_inputs_page"]) or "")
    + (ast.get_source_segment(qt_text, main_window_methods["refresh_workflow_input_widgets"]) or "")
)
for key in expected_workflow_keys:
    if key in settings_page_source:
        fail(f"workflow input remains exposed by App Settings: {key}")
if 'default_target_url' not in settings_page_source:
    fail("default_target_url must remain in App Settings")
if "schema.fields" not in workflow_page_source or "WORKFLOW_INPUT_FIELDS" in workflow_page_source:
    fail("PR-08 Workflow Inputs page is not rendered from the active declarative schema")
if 'Workflow:' in workflow_page_source:
    fail("Workflow Inputs must not add a workflow selector")
if 'Legacy Contact Settings (Preserved)' in qt_text:
    fail("legacy workflow/contact fields must no longer be owned by App Settings UI")

persist_workflow_source = ast.get_source_segment(
    qt_text, main_window_methods["_persist_active_workflow_input_values"]
) or ""
save_workflow_source = ast.get_source_segment(qt_text, main_window_methods["save_workflow_inputs"]) or ""
reset_workflow_source = ast.get_source_segment(qt_text, main_window_methods["reset_workflow_inputs"]) or ""
for marker in (
    "previous_state = self.workflow_input_state_store.load_existing()",
    "save_workflow_values",
    "save_state(previous_state)",
    "for key, value in previous_legacy.items()",
):
    if marker not in persist_workflow_source:
        fail(f"PR-08 Workflow Input transaction marker missing: {marker}")
if "_collect_workflow_input_values" not in save_workflow_source:
    fail("PR-08 Save must collect only active-schema Workflow Inputs")
if "schema.defaults()" not in reset_workflow_source:
    fail("PR-08 Reset must use active source-controlled schema defaults")
for source in (save_workflow_source, reset_workflow_source):
    if '"Workflow Inputs error"' not in source or '"error"' not in source:
        fail("Workflow Inputs Save/Reset must contain and report persistence errors")

# v1.0.6.10 license-login durability/recovery invariants.
for marker in (
    "LICENSE_STATE_DIR = _default_license_state_dir()",
    "DEVICE_IDENTITY_FILE = LICENSE_STATE_DIR / \"device_identity.json\"",
    "_migrate_legacy_license_file()",
    "DEVICE_KEY_MISMATCH",
    "DEVICE_REVOKED",
    "self._remote_logout_done.wait",
    "license_validation_failure_is_transient",
):
    if marker not in backend_text and marker not in qt_text:
        fail(f"v1.0.6.10 license-login marker missing: {marker}")
for forbidden in license_fix_scope.get("forbidden_client_markers", []):
    if forbidden in backend_text or forbidden in (SRC / "licensing_v2.py").read_text(encoding="utf-8"):
        fail(f"v1.0.6.10 forbidden license client marker present: {forbidden}")

# Dedicated Browser Settings scope.
qt_tree_for_browser_settings = ast.parse(qt_text)
browser_groups_node = next(
    node
    for node in qt_tree_for_browser_settings.body
    if isinstance(node, ast.AnnAssign)
    and isinstance(node.target, ast.Name)
    and node.target.id == "BROWSER_SETTING_GROUPS"
)
browser_groups = ast.literal_eval(browser_groups_node.value)
browser_keys = {key for keys in browser_groups.values() for key in keys}
missing_browser_defaults = sorted(browser_keys - set(settings_defaults))
if missing_browser_defaults:
    fail(f"Browser Settings defaults missing: {missing_browser_defaults}")
worker_node_for_browser_settings = next(
    node
    for node in ast.parse(backend_text).body
    if isinstance(node, ast.ClassDef) and node.name == "AutomationWorker"
)
worker_source_for_browser_settings = ast.get_source_segment(
    backend_text, worker_node_for_browser_settings
) or ""
helper_node_for_browser_settings = next(
    node
    for node in ast.parse(backend_text).body
    if isinstance(node, ast.FunctionDef) and node.name == "effective_ignored_default_args"
)
helper_source_for_browser_settings = ast.get_source_segment(
    backend_text, helper_node_for_browser_settings
) or ""
share_invite_runtime_path = SRC / "workflow" / "share_invite" / "workflow.py"
share_invite_runtime_source = (
    share_invite_runtime_path.read_text(encoding="utf-8")
    if share_invite_runtime_path.is_file()
    else ""
)
runtime_browser_source = (
    worker_source_for_browser_settings
    + helper_source_for_browser_settings
    + share_invite_runtime_source
)
if len(browser_keys) != 147:
    fail(f"v1.0.6.1 Browser Settings control count drift: {len(browser_keys)} != 147")
missing_runtime_consumers = sorted(
    key
    for key in browser_keys
    if key != "browser_slot_default"
    and f'"{key}"' not in runtime_browser_source
)
if missing_runtime_consumers:
    fail(
        "Browser Settings controls without browser/runtime consumer: "
        f"{missing_runtime_consumers}"
    )
if '"browser_slot_default", DEFAULT_SETTINGS["browser_slot_default"]' not in qt_text:
    fail("Browser Slot Default must have a real workspace-initialization consumer")
for marker in [
    'def make_browser_settings_page(self) -> QWidget:',
    'def save_browser_settings(self) -> None:',
    'def reset_browser_settings(self) -> None:',
    '"Browser Settings": "search"',
]:
    if marker not in qt_text:
        fail(f"Browser Settings UI marker missing: {marker}")
for key in (
    "navigation_wait_until",
    "allow_chromium_fallback",
    "block_images",
    "preserve_storage_state_on_recycle",
    "use_persistent_context",
    "browser_executable_path",
    "record_har_enabled",
):
    if key not in browser_keys:
        fail(f"Browser Settings key missing from UI groups: {key}")
for marker in [
    "navigation_wait_until",
    "network_idle_timeout",
    "block_images",
    "allow_chromium_fallback",
    "preserve_storage_state_on_recycle",
    "scroll_before_interaction",
    "launch_persistent_context",
    "browser_executable_path",
    "persistent_user_data_dir",
    "device_scale_factor",
    "locale",
    "timezone_id",
    "permissions",
    "accept_downloads",
    "record_har_path",
    "additional_chromium_args",
    "auto_restart_browser_on_crash",
]:
    if marker not in backend_text:
        fail(f"Browser Settings runtime marker missing: {marker}")
if '"Network": ["request_timeout"' in qt_text or '"request_timeout": "Request / Network Timeout' in qt_text:
    fail("license/API request_timeout must not be exposed as a Playwright Browser Setting")
for fake_key in (
    "safe_browsing_enabled",
    "password_manager_enabled",
    "autofill_enabled",
    "screen_color_depth",
    "platform_spoof",
    "origin_trials_enabled",
    "hardware_acceleration_enabled",
    "disable_image_font_media_loading",
):
    if fake_key in browser_keys:
        fail(f"fake/legacy Browser Settings control must not be exposed: {fake_key}")
    if fake_key in settings_defaults:
        fail(f"fake/legacy Browser Settings default must not remain active: {fake_key}")
for forbidden_ui in (
    "Runtime Browser Contract (Informational)",
    "Chrome Policy / Profile-managed Features (Informational)",
):
    if forbidden_ui in qt_text:
        fail(f"read-only non-setting card must not appear in Browser Settings: {forbidden_ui}")
for marker in (
    "def effective_ignored_default_args(",
    '_PLAYWRIGHT_POPUP_BLOCKING_ARG = "--disable-popup-blocking"',
    '_PLAYWRIGHT_DISABLE_EXTENSIONS_ARG = "--disable-extensions"',
    '_PLAYWRIGHT_MUTE_AUDIO_ARG = "--mute-audio"',
    '"--disable-background-timer-throttling"',
    'extensions_enabled=extensions_enabled',
    'browser_args.append("--auto-open-devtools-for-tabs")',
    'launch_args["channel"] = "chromium"',
    'persistent_args.get("channel") == "chrome"',
):
    if marker not in backend_text:
        fail(f"Playwright/Chromium browser-authority marker missing: {marker}")
if 'if bool(settings.get("audio_enabled", DEFAULT_SETTINGS["audio_enabled"])):' not in helper_source_for_browser_settings:
    fail("Audio Enabled must override Playwright headless --mute-audio through ignored default args")
if '"devtools": bool(' in backend_text:
    fail("Playwright 1.61 removed launch(devtools=...); use the Chromium DevTools switch instead")
if 'elif name == "Browser Settings":' not in qt_text or qt_text.count("self.refresh_browser_settings_widgets()") < 3:
    fail("Browser Settings must refresh from SettingsManager on navigation, save and reset")
for marker in [
    '"App Settings": "settings"',
    '"Workflow Inputs": "file"',
    '("Workflow Inputs", self.make_workflow_inputs_page)',
    '("App Settings", self.make_settings_page)',
    'worker.control_queue.put(("settings", {"settings": dict(self.settings.data)}))',
    'if command == "settings":',
]:
    if marker not in (qt_text + backend_text):
        fail(f"Browser/App Settings wiring marker missing: {marker}")

print("[6/8] Vib Tools UI integration contract")
for marker in [
    'app_qss("dark") + ActivationPage.activation_qss()',
    "apply_nav_button_contract",
    "install_keyboard_focus_ring",
    "CONST.sidebar_width",
    'NAV_SECTIONS = ["Dashboard", "Tasks", "Workflows", "Workflow Inputs", "Reports", "Live Logs", "App Settings", "Browser Settings", "About"]',
]:
    if marker not in qt_text:
        fail(f"required branded UI integration marker missing: {marker}")
if "customtkinter" in qt_text.lower() or "ctk." in qt_text:
    fail("new UI must not use the legacy CustomTkinter layer")
# Scope-locked v1.0.6 activation window contract.
activation_source = qt_text[qt_text.index("class ActivationPage(QWidget):"):qt_text.index("class TaskSlotWidget", qt_text.index("class ActivationPage(QWidget):"))]
activation_markers = [
    'WINDOW_BACKGROUND = "#0F172A"',
    'SURFACE = "#1E293B"',
    'BORDER = "#334155"',
    'PRIMARY = "#3B82F6"',
    'PRIMARY_HOVER = "#2563EB"',
    'TEXT_PRIMARY = "#F8FAFC"',
    'TEXT_SECONDARY = "#94A3B8"',
    'SUCCESS = "#10B981"',
    'root.setContentsMargins(40, 40, 40, 40)',
    'brand_icon = brand_icon_label(48, APP.display_name)',
    'QLabel(f"{APP.display_name} Activation")',
    'QLabel(f"Enter your license key to unlock {APP.display_name}")',
    'QLabel("Email Address (Optional)")',
    'line_input("name@example.com"',
    'setPlaceholderText("VT-XXXX-XXXX-XXXX-XXXX")',
    'setFixedHeight(44)',
    'button("Activate License", "primary")',
    'QLabel("🔒 Secured by Licora Activation Engine")',
]
for marker in activation_markers:
    if marker not in activation_source:
        fail(f"activation-window contract marker missing: {marker}")
for forbidden in [
    "Validation:",
    "Activate / Login",
    "Vib Tools official desktop UI • Dark-first frozen design contract",
    'f"{DISPLAY_APP_NAME}  •  v{APP_VERSION}"',
]:
    if forbidden in activation_source:
        fail(f"legacy/debug activation-window marker still present: {forbidden}")
for marker in [
    "self.setFixedSize(460, 560)",
    "self._center_login_window()",
    "self.setMaximumSize(16777215, 16777215)",
    "self.setMinimumSize(CONST.min_window_width, CONST.min_window_height)",
]:
    if marker not in qt_text:
        fail(f"activation/workspace window-state marker missing: {marker}")

# Successful activation must transition exactly once into a live workspace.
transition_markers = [
    "self._transition_requested = False",
    "if self._transition_requested:",
    "self._transition_requested = True",
    "self._workspace_active = False",
    "self._workspace_transitioning = False",
    "if self._workspace_active or self._workspace_transitioning:",
    "self.setMinimumSize(0, 0)",
    "self.activation_page = None",
    "activation_page = self.activation_page",
    "if activation_page is not None and not self._workspace_active:",
]
for marker in transition_markers:
    if marker not in qt_text:
        fail(f"activation/workspace lifecycle marker missing: {marker}")

show_workspace_source = qt_text[qt_text.index("    def show_workspace(self) -> None:"):qt_text.index("    def _build_menu_bar", qt_text.index("    def show_workspace(self) -> None:"))]
if show_workspace_source.index("self._build_shell()") > show_workspace_source.index("self._fit_workspace_to_screen()"):
    fail("workspace geometry must be applied only after the live shell is built")
if "tl = hbox(toolbar," in qt_text or "cl = hbox(controls," in qt_text:
    fail("workspace card must not receive a second top-level Qt layout")

# Central QSS remains the only direct style application in the application UI.
style_calls = len(re.findall(r"\.setStyleSheet\s*\(", qt_text))
if style_calls != 1:
    fail(f"expected exactly one central setStyleSheet call, found {style_calls}")

print("[7/8] Private-secret and source hygiene")
for path in ROOT.rglob("*"):
    if not path.is_file() or any(part in {".git", ".venv", "build", "dist", "release", "__pycache__"} for part in path.parts):
        continue
    if path.suffix.lower() in {".zip", ".exe", ".ico", ".png", ".jpg", ".jpeg", ".gif", ".pdf"}:
        continue
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    scan_text = text
    if re.search(r"(?i)(?:api[_ -]?key|x-api-key)\s*[:=]\s*['\"](?!REPLACE_|YOUR_|example|demo)[A-Za-z0-9_-]{32,}['\"]", scan_text):
        fail(f"possible hard-coded real API key in {path.relative_to(ROOT)}")
    if re.search(
        r"-----BEGIN (?:RSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]+-----END (?:RSA )?PRIVATE KEY-----",
        scan_text,
    ):
        fail(f"private signing/key material present in {path.relative_to(ROOT)}")
for forbidden in ["includes/config.local.php", ".licora-encryption.key", ".env.production"]:
    if (ROOT / forbidden).exists():
        fail(f"private deployment artifact present: {forbidden}")


for marker in [
    'DISPLAY_APP_NAME = APP.display_name',
    'APP_NAME = APP.app_name',
    'QLabel(f"{APP.display_name} Activation")',
    'page_header(ABOUT.page_title, ABOUT.page_subtitle)',
    'for link_label, url in SUPPORT.about_support_links:',
    'for social_link in ENABLED_SOCIAL_LINKS:',
    'application.setWindowIcon(application_icon())',
    'self.setWindowIcon(application_icon())',
    'SetCurrentProcessExplicitAppUserModelID',
]:
    if marker not in (qt_text + backend_text):
        fail(f"VibraPilot branding/icon marker missing: {marker}")

# v1.0.6.11 Qt focus-lifecycle invariants.
focus_manager_text = (ROOT / "vib_validation_app" / "focus_manager.py").read_text(encoding="utf-8")
for marker in (
    "from shiboken6 import isValid",
    "def _is_live_widget",
    "QEvent.Type.Destroy",
    "QEvent.Type.DeferredDelete",
    "if not self._is_live_widget(widget):",
    'widget.setProperty("keyboardFocus", "true" if enabled else "false")',
    "QTimer.singleShot(180",
):
    if marker not in focus_manager_text:
        fail(f"v1.0.6.11 Qt focus lifecycle marker missing: {marker}")
if "except Exception:" in focus_manager_text:
    fail("v1.0.6.11 focus manager must not hide unrelated exceptions with a broad handler")

# v1.0.6.12 Browser UI/lifecycle invariants.
for marker in [
    'self._browser_lifecycle_state = "CLOSED"',
    'def _browser_objects_ready(self) -> bool:',
    'browser.on("disconnected", browser_disconnected)',
    'context.on("close", context_closed)',
    'page.on("close", page_closed)',
    'self.browser_action_button = button("Open Browser", "primary")',
    'action.setText("Close Browser")',
    'self.close_browser(wait=False)',
    'def _fit_workspace_to_screen(self) -> None:',
    'screen.availableGeometry()',
]:
    if marker not in (backend_text + qt_text):
        fail(f"v1.0.6.12 browser UI/lifecycle marker missing: {marker}")
settings_defaults = json.loads((ROOT / "config" / "settings.defaults.json").read_text(encoding="utf-8"))
if browser_ui_scope.get("no_browser_settings_change") is not True:
    fail("v1.0.6.12 historical scope must record no Browser Settings change")
if managed_scope.get("approved_settings_default_changes", {}).get("use_persistent_context") != {"from": False, "to": True}:
    fail("v1.0.6.14 must explicitly authorize the managed persistent default change")
if settings_defaults.get("use_persistent_context") is not True:
    fail("v1.0.6.14 managed persistent browser mode must be enabled by default")
if settings_defaults.get("restore_previous_session") is not False:
    fail("v1.0.6.14 must not enable previous-session restoration")
if settings_defaults.get("extensions_enabled") is not False:
    fail("v1.0.6.14 must not change extension defaults")

print("[8/8] Required project files")
required = [
    "README.md", "CHANGELOG.md", "UPDATE_LOG.md", "VERSIONING.md", "LICENSE", "NOTICE", "pyproject.toml", "requirements.txt", "requirements-build.txt",
    "run.py", "build.py", "config/settings.defaults.json", "config/__init__.py", "config/AppConfig/__init__.py",
    "config/AppConfig/app.py", "config/AppConfig/about.py", "config/AppConfig/support.py", "config/AppConfig/social.py",
    "config/AppConfig/licensing_public.py", "config/verification/phase02_step002_scope.json", "config/verification/phase02_step002_v1.0.6.4_fix_scope.json",
    "config/verification/production_mt_lr_v1.0.6.5_scope.json",
    "config/verification/v1.0.6.7_vp_prod_mt_lr_verification_fix_scope.json",
    "config/verification/v1.0.6.7_windows_sqlite_concurrency_fix_scope.json",
    "config/verification/v1.0.6.8_workflow_inputs_scope.json",
    "config/verification/v1.0.6.9_workflow_inputs_verification_fix_scope.json",
    "config/verification/v1.0.6.10_license_login_fix_scope.json",
    "config/verification/v1.0.6.11_qt_focus_lifecycle_fix_scope.json",
    "config/verification/v1.0.6.12_browser_ui_lifecycle_scope.json",
    "config/verification/v1.0.6.13_phase01_verification_ci_fix_scope.json",
    "config/verification/v1.0.6.14_managed_persistent_browser_closed_task_scope.json",
    "config/verification/v1.0.6.15_workspace_persistence_scope.json",
    "config/verification/v1.0.6.16_workspace_persistence_verification_fix_scope.json",
    "config/verification/v1.0.6.17_browser_capabilities_scope.json",
    "config/verification/v1.0.6.25_pr08_dynamic_workflow_inputs_scope.json",
    "config/verification/v1.0.6.26_pr09_data_persistence_reporting_compatibility_scope.json",
    "config/verification/v1.0.6.27_pr10_workflow_error_recovery_scope.json",
    "config/verification/v1.0.6.28_pr11_windows_multitask_regression_scope.json",
    "src/vibrapilot/app_config.py", "src/vibrapilot/backend.py", "src/vibrapilot/licensing_v2.py", "src/vibrapilot/data_io.py", "src/vibrapilot/task_runtime_store.py",
    "src/vibrapilot/qt_app.py", "src/vibrapilot/workflow_inputs.py", "src/vibrapilot/workflow/input_state.py", "src/vibrapilot/workflow/recovery.py", "src/vibrapilot/workspace_state.py", "src/vibrapilot/browser_capabilities.py", "config/verification/backend_v1.0.6_contract.json", "docs/index.md",
    "docs/verification/BACKEND_CONTRACT.md", "docs/updates/v1.0.6.1.md", "docs/updates/v1.0.6.1-browser-settings-audit.md",
    "docs/updates/v1.0.6.1-vibrapilot-branding.md", "docs/updates/v1.0.6.1-github-ci-repository-hygiene-fix.md",
    "docs/updates/v1.0.6.1-github-ci-deterministic-ast-contract-fix.md",
    "docs/configuration/APPCONFIG.md", "docs/updates/v1.0.6.1-phase-01-appconfig.md",
    "docs/updates/v1.0.6.2-phase-01-verification-fix.md",
    "docs/verification/PHASE01_V1.0.6.2_VERIFICATION.md", "docs/verification/PHASE02_STEP002_V1.0.6.3_VERIFICATION.md",
    "docs/verification/PHASE02_STEP002_V1.0.6.4_FORENSIC_VERIFICATION.md",
    "docs/verification/V1.0.6.5_PRODUCTION_RUNTIME_VERIFICATION.md",
    "docs/verification/V1.0.6.7_VP_PROD_MT_LR_FORENSIC_VERIFICATION.md",
    "docs/verification/V1.0.6.7_WINDOWS_SQLITE_CONCURRENCY_VERIFICATION.md",
    "docs/verification/V1.0.6.8_WORKFLOW_INPUTS_VERIFICATION.md",
    "docs/verification/V1.0.6.9_WORKFLOW_INPUTS_FORENSIC_VERIFICATION.md",
    "docs/verification/V1.0.6.10_LICENSE_LOGIN_FORENSIC_VERIFICATION.md",
    "docs/verification/V1.0.6.11_QT_FOCUS_LIFECYCLE_VERIFICATION.md",
    "docs/verification/V1.0.6.12_BROWSER_UI_LIFECYCLE_VERIFICATION.md",
    "docs/verification/V1.0.6.13_PHASE01_FORENSIC_VERIFICATION.md",
    "docs/verification/V1.0.6.14_MANAGED_PERSISTENT_BROWSER_CLOSED_TASK_VERIFICATION.md",
    "docs/verification/V1.0.6.15_WORKSPACE_PERSISTENCE_VERIFICATION.md",
    "docs/verification/V1.0.6.16_WORKSPACE_PERSISTENCE_FORENSIC_VERIFICATION.md",
    "docs/verification/V1.0.6.17_BROWSER_CAPABILITIES_VERIFICATION.md",
    "docs/verification/V1.0.6.25_PR08_DYNAMIC_WORKFLOW_INPUTS.md",
    "docs/updates/v1.0.6.25-pr08-dynamic-workflow-inputs.md",
    "docs/verification/V1.0.6.26_PR09_DATA_PERSISTENCE_REPORTING_COMPATIBILITY.md",
    "docs/updates/v1.0.6.26-pr09-data-persistence-reporting-compatibility.md",
    "docs/verification/V1.0.6.27_PR10_WORKFLOW_ERROR_RECOVERY.md",
    "docs/updates/v1.0.6.27-pr10-workflow-error-recovery.md",
    "docs/verification/V1.0.6.28_PR11_WINDOWS_MULTITASK_REGRESSION.md",
    "docs/updates/v1.0.6.28-pr11-windows-multitask-regression.md",
    "docs/updates/v1.0.6.3-phase-02-step-002-secure-licensing.md", "docs/updates/v1.0.6.4-phase-02-step-002-verification-fix.md",
    "docs/updates/v1.0.6.5-production-multi-task-long-run-stability.md",
    "docs/updates/v1.0.6.7-vp-prod-mt-lr-verification-fix.md",
    "docs/updates/v1.0.6.7-windows-sqlite-concurrency-fix.md",
    "docs/updates/v1.0.6.8-workflow-inputs-separation.md",
    "docs/updates/v1.0.6.9-workflow-inputs-verification-fix.md",
    "docs/updates/v1.0.6.10-license-login-durability-recovery-fix.md",
    "docs/updates/v1.0.6.11-qt-focus-lifecycle-fix.md",
    "docs/updates/v1.0.6.12-browser-ui-lifecycle.md",
    "docs/updates/v1.0.6.13-phase01-verification-ci-fix.md",
    "docs/updates/v1.0.6.14-managed-persistent-browser-closed-task-recovery.md",
    "docs/updates/v1.0.6.15-workspace-persistence.md",
    "docs/updates/v1.0.6.16-workspace-persistence-verification-fix.md",
    "docs/updates/v1.0.6.17-browser-capabilities.md",
    "scripts/verify_source_archive.py", "tests/test_v1067_verification_fix.py", "tests/test_app_config_validation.py",
    "tests/test_licensing_v2_crypto.py", "tests/test_licensing_v2_client.py", "tests/test_license_manager_v2.py", "tests/test_phase02_scope_freeze.py", "tests/test_phase02_step002_fix_scope.py",
    "tests/test_production_scope_freeze.py", "tests/test_task_runtime_store.py", "tests/test_task_recovery.py",
    "tests/test_multi_task_isolation.py", "tests/test_long_run_worker_stability.py", "tests/test_report_integrity.py",
    "tests/test_input_reconciliation.py", "tests/test_context_recycling.py", "tests/test_worker_shutdown.py",
    "tests/test_ui_queue_backpressure.py",
    "tests/test_workflow_inputs.py", "tests/test_workflow_inputs_ui.py", "tests/test_workflow_inputs_scope.py",
    "tests/test_v1069_workflow_inputs_verification_fix.py",
    "tests/test_v10610_license_login_fix.py",
    "tests/test_v10611_qt_focus_lifecycle_fix.py",
    "tests/test_v10612_browser_ui_lifecycle.py",
    "tests/test_v10613_phase01_verification_fix.py",
    "tests/test_v10614_managed_persistent_browser.py",
    "tests/test_v10615_workspace_persistence.py",
    "tests/test_v10616_workspace_persistence_verification_fix.py",
    "tests/test_v10617_browser_capabilities.py",
    "tests/test_v10625_pr08_dynamic_workflow_inputs.py",
    "tests/test_v10625_pr08_workflow_input_state.py",
    "tests/test_v10626_pr09_data_persistence_reporting_compatibility.py",
    "tests/test_v10627_pr10_workflow_error_recovery.py",
    "tests/test_v10627_pr10_workflow_recovery_transaction.py",
    "tests/test_v10628_pr11_windows_multitask_regression.py",
    "scripts/diagnostics/pr11_windows_acceptance_runner.py",
    "scripts/diagnostics/verify_pr11_windows_evidence.py",
    "scripts/maintenance/Apply-v1.0.6.2-Phase01-Fix.cmd",
    "scripts/maintenance/PHASE01_V1.0.6.2_DELETE_PATHS.txt",
    "assets/icons/app.ico", "assets/icons/app.png", ".github/workflows/ci.yml",
]
for rel in required:
    if not (ROOT / rel).is_file():
        fail(f"required public repository file missing: {rel}")

gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
if not re.search(r"(?m)^project/$", gitignore_text):
    fail("private project/ workspace must remain gitignored")
if (ROOT / "src" / "tester_zepto_pro").exists():
    fail("stale pre-rebrand source package must not remain in the public repository")
if (ROOT / "scripts" / "Start-TesterZeptoPro.ps1").exists():
    fail("stale pre-rebrand launcher must not remain in the public repository")

print("Repository verification passed.")
