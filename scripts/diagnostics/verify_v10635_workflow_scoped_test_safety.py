#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "config/verification/v1.0.6.35_workflow_scoped_test_safety_scope.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fail(message: str) -> None:
    raise SystemExit("V1.0.6.35 WORKFLOW-SCOPED TEST SAFETY VERIFY: FAIL — " + message)


scope = json.loads(SCOPE.read_text(encoding="utf-8"))
if scope.get("target_version") != "1.0.6.35":
    fail("target version mismatch")
for relative, expected in scope.get("frozen_file_sha256", {}).items():
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected:
        fail(f"frozen surface drift: {relative}")

qt = (ROOT / "src/vibrapilot/qt_app.py").read_text(encoding="utf-8")
backend = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
manager = (ROOT / "src/vibrapilot/workflow/manager.py").read_text(encoding="utf-8")
schemas = (ROOT / "src/vibrapilot/workflow/schemas.py").read_text(encoding="utf-8")
share = (ROOT / "src/vibrapilot/workflow/share_invite/workflow.py").read_text(encoding="utf-8")

if "Enable authorized testing mode in App Settings before running automation." in qt:
    fail("legacy global authorization gate remains")
if '"Test Safety Settings": ["authorized_testing_only", "max_test_send_limit"]' in qt:
    fail("legacy global Test Safety settings card remains")
if "Vib Tools • Authorized Test Mode" in qt:
    fail("global sidebar still claims Test Mode")
if "Vib Tools • Authorized Automation" not in qt:
    fail("workflow-neutral sidebar marker missing")
if "builtin_share_invite_settings_schema()" not in manager:
    fail("Share Invite Workflow Settings registration missing")
for marker in ('key="max_test_send_limit"', 'label="Max Test Send Limit"'):
    if marker not in schemas:
        fail(f"Share Invite workflow setting missing: {marker}")
if 'self.workflow_settings_values.get("max_test_send_limit"' not in backend:
    fail("worker is not using workflow-scoped send limit")
if "Workflow session verified." not in backend:
    fail("workflow-neutral session message missing")
for marker in ("def assert_test_mode", "Test Mode banner is required before every Send operation."):
    if marker not in share:
        fail(f"Share Invite Test Mode safety missing: {marker}")

print("V1.0.6.35 WORKFLOW-SCOPED TEST SAFETY VERIFY: SOURCE POLICY PASS")
print("Baseline: v1.0.6.34 / a0e3621e831d402649ab55859e00b59d5f0ad634")
print("Target: v1.0.6.35")
print("Global Authorized Testing gate: retired")
print("Share Invite Max Test Send Limit: workflow-scoped")
print("Share Invite live Test Mode enforcement: preserved")
print("Browser/licensing/persistence/dependencies/CI/build: frozen")
