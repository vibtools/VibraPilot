#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / "config" / "verification" / "v1.0.6.34_ui_compact_polish_scope.json"
QT = ROOT / "src" / "vibrapilot" / "qt_app.py"
WIDGETS = ROOT / "vib_validation_app" / "widgets.py"
STYLES = ROOT / "vib_validation_app" / "styles.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"V1.0.6.34 UI COMPACT POLISH VERIFY: FAIL — {message}")


scope = json.loads(SCOPE.read_text(encoding="utf-8"))
if scope.get("plan_id") != "VP-V10634-UI-COMPACT-POLISH-001":
    fail("scope plan mismatch")
if scope.get("target_version") != "1.0.6.34":
    fail("target version mismatch")
if scope.get("allowed_production_source_changes") != ["src/vibrapilot/qt_app.py", "vib_validation_app/widgets.py", "vib_validation_app/styles.py"]:
    fail("production UI scope mismatch")
for relative, expected in scope.get("frozen_file_sha256", {}).items():
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected:
        fail(f"frozen surface drift: {relative}")
qt = QT.read_text(encoding="utf-8")
widgets = WIDGETS.read_text(encoding="utf-8")
styles = STYLES.read_text(encoding="utf-8")
for text in (
    "Live overview of browser slots, automation progress, license state and next actions.",
    "Independent authorized Test Mode browser slots with file import, controls and live counters.",
    "Built-in and trusted local workflow plugins share the existing one-active-workflow control plane.",
    "Configure isolated global inputs for any installed workflow without activating it.",
    "Workflow-owned global configuration is isolated per installed workflow.",
    "Advanced Playwright controls for the managed Google Chrome runtime.",
):
    if text in qt:
        fail(f"decorative description remains: {text}")
for marker in (
    'panel.setMinimumWidth(280)',
    'panel.setMaximumWidth(360)',
    'columns = 1 if compact else (3 if wide else 2)',
    'status_badge("ACTIVE" if is_active else "AVAILABLE"',
):
    if marker not in qt:
        fail(f"workflow grid marker missing: {marker}")
if 'description: str = ""' not in widgets or "if description:" not in widgets:
    fail("optional page-header contract missing")
if "QFrame#WorkflowCard {{" not in styles or "border: 2px solid {c['border']};" not in styles or "background: {c['surface']};" not in styles:
    fail("workflow card 2px tokenized surface border contract missing")
for marker in ("Google Chrome Required", "Windows Authenticode", "Google LLC", "Chromium Fallback: Disabled"):
    if marker not in qt:
        fail(f"security/runtime evidence removed: {marker}")
print("V1.0.6.34 UI COMPACT POLISH VERIFY: SOURCE POLICY PASS")
print("Baseline: v1.0.6.33 / dc149f768451383747ed02dc96607a4cfb4a3fb2")
print("Target: v1.0.6.34")
print("Production UI files: src/vibrapilot/qt_app.py, vib_validation_app/widgets.py, vib_validation_app/styles.py")
print("Backend/browser/workflow/licensing/persistence/build: frozen")
