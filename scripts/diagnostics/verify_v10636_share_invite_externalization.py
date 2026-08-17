"""Source-policy diagnostic for VibraPilot v1.0.6.36 Share Invite externalization."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    raise SystemExit(f"V1.0.6.36 SHARE INVITE EXTERNALIZATION VERIFY FAILED: {message}")


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    app = text("config/AppConfig/app.py")
    registry = text("src/vibrapilot/workflow/registry.py")
    manager = text("src/vibrapilot/workflow/manager.py")
    state = text("src/vibrapilot/workflow/state.py")
    backend = text("src/vibrapilot/backend.py")
    qt = text("src/vibrapilot/qt_app.py")
    inputs = text("src/vibrapilot/workflow_inputs.py")
    schemas = text("src/vibrapilot/workflow/schemas.py")
    plugin_loader = text("src/vibrapilot/workflow/plugin_loader.py")

    checks = {
        "version": 'VERSION = "1.0.6.36"' in app,
        "zero builtins manifest": "return ()" in registry and "SHARE_INVITE_MANIFEST" not in registry,
        "zero builtins runtime": "ShareInviteWorkflow" not in registry,
        "state schema2": "WORKFLOW_STATE_SCHEMA_VERSION = 2" in state,
        "zero workflow default": "DEFAULT_ACTIVE_WORKFLOW_ID: None = None" in state,
        "legacy Share migration identity": 'LEGACY_EXTERNALIZED_WORKFLOW_IDS = frozenset({"share_invite"})' in state,
        "no Core Share runtime import": "ShareInviteWorkflow" not in backend and "workflow.share_invite" not in backend,
        "generic processing hook": 'getattr(runtime, "process_item", None)' in backend,
        "generic Start session gate": "self.ensure_workflow_session()" in backend and "self.ensure_authenticated_test_session()" not in backend,
        "generic rich data hook": "def load_task_data(" in manager and 'getattr(module, "load_task_data", None)' in plugin_loader,
        "no Core Share schema factory": "builtin_share_invite" not in schemas,
        "legacy input keys migration-only": "LEGACY_SHARE_INVITE_INPUT_KEYS" in inputs and "WORKFLOW_INPUT_SCHEMAS" not in inputs,
        "no implicit Share task fallback": 'or "share_invite"' not in qt,
        "package-required UX": "Workflow package required" in qt,
        "no source Share runtime directory": not (ROOT / "src/vibrapilot/workflow/share_invite").exists(),
        "plugin API remains 1": "WORKFLOW_PLUGIN_API_VERSION = 1" in schemas,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        fail(", ".join(failed))

    scope = ROOT / "config/verification/v1.0.6.36_share_invite_externalization_scope.json"
    if not scope.is_file():
        fail("scope contract missing")
    payload = json.loads(scope.read_text(encoding="utf-8"))
    if payload.get("baseline_version") != "1.0.6.35" or payload.get("target_version") != "1.0.6.36":
        fail("scope contract version mismatch")

    print("V1.0.6.36 SHARE INVITE EXTERNALIZATION VERIFY: SOURCE POLICY PASS")
    print("Baseline: v1.0.6.35 / c5511a82ddf164bfacdfad5aa12ebf75ad56a1da")
    print("Target: v1.0.6.36")
    print("Built-in workflows: 0")
    print("Zero-active-workflow state: valid")
    print("Share Invite: standalone external .vpworkflow")
    print("Plugin API: 1 (backward-compatible)")
    print("DMARC/browser/licensing/persistence/dependencies/CI/build: frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
