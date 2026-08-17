"""Verify the standalone Share Invite workflow package and optional v1.0.6.35 parity."""
from __future__ import annotations

import ast
import json
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for entry in (ROOT, SRC):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from vibrapilot.workflow.plugin_loader import (  # noqa: E402
    inspect_workflow_package,
    install_workflow_package,
)
from vibrapilot.workflow.registry import builtin_workflow_manifests  # noqa: E402

EXPECTED_MANIFEST = {
    "workflow_id": "share_invite",
    "name": "Share Invite",
    "description": "Authenticated Test Mode Share Invite workflow.",
    "version": "1.0",
    "logo": "assets/logo.png",
    "entrypoint": "create_workflow",
    "plugin_api": 1,
}
EXPECTED_INPUT_KEYS = (
    "default_full_name",
    "default_number",
    "fallback_name",
    "update_click_count",
)
EXPECTED_SETTING_KEYS = ("max_test_send_limit",)
EXPECTED_TASK_INPUTS = ("target_url", "data_file")
EXPECTED_METRICS = ("login", "send_limit", "total", "success", "failed", "remaining")
ERROR_MAP = {
    "session_verification_error": "SessionVerificationError",
    "test_mode_required": "TestModeRequired",
    "test_send_limit_reached": "TestSendLimitReached",
    "invite_rejected": "InviteRejected",
}


def fail(message: str) -> None:
    raise SystemExit(f"SHARE INVITE WORKFLOW v1.0 VERIFY FAILED: {message}")


def _read_package(package: Path, name: str) -> bytes:
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        if name in names:
            return archive.read(name)
        candidates = [member for member in names if member.endswith("/" + name)]
        if len(candidates) != 1:
            fail(f"package entry not uniquely available: {name}")
        return archive.read(candidates[0])


def _class(tree: ast.AST, name: str) -> ast.ClassDef:
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    fail(f"class not found: {name}")
    raise AssertionError


def _method(cls: ast.ClassDef, name: str) -> ast.FunctionDef:
    for node in cls.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    fail(f"method not found: {cls.name}.{name}")
    raise AssertionError


def _assignment_value(tree: ast.AST, name: str) -> Any:
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return ast.literal_eval(node.value)
    fail(f"assignment not found: {name}")


class _BaselineErrorNormalizer(ast.NodeTransformer):
    def visit_Attribute(self, node: ast.Attribute):  # noqa: N802
        self.generic_visit(node)
        value = node.value
        if (
            isinstance(value, ast.Attribute)
            and value.attr == "errors"
            and isinstance(value.value, ast.Name)
            and value.value.id == "self"
            and node.attr in ERROR_MAP
        ):
            return ast.copy_location(ast.Name(id=ERROR_MAP[node.attr], ctx=node.ctx), node)
        return node


class _ProcessHookNormalizer(ast.NodeTransformer):
    def visit_Name(self, node: ast.Name):  # noqa: N802
        if node.id == "host":
            return ast.copy_location(ast.Name(id="self", ctx=node.ctx), node)
        return node


def _normalized_method(node: ast.FunctionDef, *, baseline: bool = False) -> str:
    node = deepcopy(node)
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
        node.body = node.body[1:]
    if baseline:
        node = _BaselineErrorNormalizer().visit(node)
    ast.fix_missing_locations(node)
    return ast.dump(node, include_attributes=False)


def _strip_signature_annotations(node: ast.FunctionDef) -> None:
    node.returns = None
    for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
        arg.annotation = None
    if node.args.vararg is not None:
        node.args.vararg.annotation = None
    if node.args.kwarg is not None:
        node.args.kwarg.annotation = None


def _normalized_process_baseline(node: ast.FunctionDef) -> str:
    node = deepcopy(node)
    _strip_signature_annotations(node)
    if node.body and isinstance(node.body[0], ast.If):
        # v1.0.6.35 Core first dispatched non-Share workflows to the generic path.
        node.body = node.body[1:]
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        node.body = node.body[1:]
    ast.fix_missing_locations(node)
    return ast.dump(node, include_attributes=False)


def _normalized_process_external(node: ast.FunctionDef) -> str:
    node = deepcopy(node)
    _strip_signature_annotations(node)
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        node.body = node.body[1:]
    if node.body and isinstance(node.body[0], ast.Assign):
        target = node.body[0].targets[0] if node.body[0].targets else None
        if isinstance(target, ast.Name) and target.id == "host":
            node.body = node.body[1:]
    node = _ProcessHookNormalizer().visit(node)
    ast.fix_missing_locations(node)
    return ast.dump(node, include_attributes=False)


def verify_package(package: Path) -> None:
    inspection = inspect_workflow_package(package)
    manifest_payload = json.loads(_read_package(package, "manifest.json").decode("utf-8"))
    if manifest_payload != EXPECTED_MANIFEST:
        fail("manifest does not match the approved Share Invite v1.0 contract")
    if inspection.manifest.workflow_id != "share_invite" or inspection.plugin_api != 1:
        fail("workflow identity/plugin API mismatch")
    if tuple(field.key for field in inspection.input_schema.fields) != EXPECTED_INPUT_KEYS:
        fail("input schema keys drifted")
    if tuple(field.key for field in inspection.settings_schema.fields) != EXPECTED_SETTING_KEYS:
        fail("settings schema keys drifted")
    if tuple(field.key for field in inspection.task_schema.inputs) != EXPECTED_TASK_INPUTS:
        fail("Task input schema drifted")
    if tuple(metric.key for metric in inspection.task_schema.metrics) != EXPECTED_METRICS:
        fail("Task metrics drifted")
    if not inspection.task_schema.requires_session or not inspection.task_schema.uses_test_send_limit:
        fail("Share Invite session/Test Mode send-limit safety flags drifted")

    source = _read_package(package, "workflow.py").decode("utf-8-sig")
    tree = ast.parse(source, filename="workflow.py")
    if _assignment_value(tree, "SHARE_INVITE_SELECTORS") is None:
        fail("Share Invite selectors missing")
    for marker in (
        "Test Mode banner is required before every Send operation.",
        "Blank or mismatched invite submission was blocked immediately before Send.",
        "before_click=self.host._register_send_click_attempt",
        "Automatic retry was blocked to prevent a duplicate invite.",
        "A new success notification was not detected after Send.",
        "def process_item",
        "def load_task_data",
    ):
        if marker not in source:
            fail(f"required safety/parity marker missing: {marker}")

    reserved = {manifest.workflow_id for manifest in builtin_workflow_manifests()}
    if "share_invite" in reserved:
        fail("Core still reserves share_invite as a built-in workflow")
    with tempfile.TemporaryDirectory(prefix="vp-share-verify-") as temp:
        installed = install_workflow_package(inspection, Path(temp), reserved_workflow_ids=reserved)
        if installed.manifest.workflow_id != "share_invite":
            fail("installed workflow identity mismatch")
        if installed.task_data_loader is None:
            fail("rich Share Invite data loader was not loaded")
        runtime = installed.runtime_factory(object())
        for method in ("session_ready", "ensure_session", "execute_item", "prepare_retry", "process_item"):
            if not callable(getattr(runtime, method, None)):
                fail(f"external runtime method missing: {method}")

    print(f"Package SHA-256: {inspection.package_sha256}")
    print("Package/schema/install contract: PASS")


def verify_baseline_parity(package: Path, baseline_zip: Path) -> None:
    with zipfile.ZipFile(baseline_zip) as archive:
        old_share = archive.read("src/vibrapilot/workflow/share_invite/workflow.py").decode("utf-8")
        old_backend = archive.read("src/vibrapilot/backend.py").decode("utf-8")
    new_share = _read_package(package, "workflow.py").decode("utf-8-sig")

    old_tree = ast.parse(old_share)
    new_tree = ast.parse(new_share)
    old_cls = _class(old_tree, "ShareInviteWorkflow")
    new_cls = _class(new_tree, "ShareInviteWorkflow")

    if _assignment_value(old_tree, "SHARE_INVITE_SELECTORS") != _assignment_value(new_tree, "SHARE_INVITE_SELECTORS"):
        fail("selector map differs from frozen v1.0.6.35")

    old_methods = {
        node.name
        for node in old_cls.body
        if isinstance(node, ast.FunctionDef) and node.name != "__init__"
    }
    expected_external_methods = old_methods | {"process_item"}
    actual_external_methods = {
        node.name for node in new_cls.body if isinstance(node, ast.FunctionDef) and node.name != "__init__"
    }
    if not expected_external_methods.issubset(actual_external_methods):
        fail("external runtime is missing one or more frozen Share Invite methods")

    for name in sorted(old_methods):
        old_method = _method(old_cls, name)
        new_method = _method(new_cls, name)
        if _normalized_method(old_method, baseline=True) != _normalized_method(new_method):
            fail(f"frozen Share Invite method parity drift: {name}")

    backend_tree = ast.parse(old_backend)
    worker = _class(backend_tree, "AutomationWorker")
    old_process = _method(worker, "process_item")
    new_process = _method(new_cls, "process_item")
    if _normalized_process_baseline(old_process) != _normalized_process_external(new_process):
        fail("Share Invite specialized process_item orchestration differs from v1.0.6.35")

    print("Frozen v1.0.6.35 Share Invite selector/runtime/process parity: PASS")


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print("Usage: verify_share_invite_workflow_v10.py SHARE_INVITE.vpworkflow [VibraPilot_v1.0.6.35_BASELINE.zip]", file=sys.stderr)
        return 2
    package = Path(sys.argv[1]).expanduser().resolve()
    verify_package(package)
    if len(sys.argv) == 3:
        verify_baseline_parity(package, Path(sys.argv[2]).expanduser().resolve())
    print("SHARE INVITE WORKFLOW v1.0 VERIFY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
