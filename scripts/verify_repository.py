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
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[target.id] = node
    return out


def dump_node(node: ast.AST, *, annotate_field_names: bool = False) -> str:
    return ast.dump(node, annotate_fied_names=annotate_field_names, include_attributes=False)


def canonical_ast_payload(value: object) -> object:
    """Return a minor-stable semantic AST payload for parity hashing.

    CPython adds new Am®éÜj×