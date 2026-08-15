from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibrapilot import backend
from vibrapilot.workflow import WorkflowManager, WorkflowRuntime
from vibrapilot.workflow.share_invite import (
    SHARE_INVITE_MANIFEST,
    ShareInviteRuntimeErrors,
    ShareInviteWorkflow,
    load_manifest,
)
from vibrapilot.workflow.share_invite.workflow import (
    SHARE_INVITE_EMAIL_RE,
    SHARE_INVITE_SELECTORS,
)

ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.20_pr04_share_invite_workflow_extraction_scope.json"
PR04_CI_FIX_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.21_pr04_ci_portability_fix_scope.json"
PR06_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.23_pr06_workflow_state_atomic_switch_scope.json"
PR08_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.25_pr08_dynamic_workflow_inputs_scope.json"
V10630_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.30_workflow_plugin_system_scope.json"
V10631_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.31_chrome_only_browser_runtime_scope.json"
V10635_SCOPE_PATH = ROOT / "config" / "verification" / "v1.0.6.35_workflow_scoped_test_safety_scope.json"
BASELINE_BACKEND = ROOT / "project" / "research" / "source_baseline" / "VibraPilot_v1.0.6_original_app.py"

ALG = "canonical-semantic-ast-v2"


def _canonical(value):
    if isinstance(value, ast.AST):
        fields = []
        for name, child in ast.iter_fields(value):
            if child is None or child == [] or child == ():
                continue
            fields.append([name, _canonical(child)])
        return [value.__class__.__name__, fields]
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    return value


def _ast_hash(node: ast.AST) -> str:
    payload = json.dumps(
        _canonical(node), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(ALG.encode("ascii") + b"\0" + payload).hexdigest()


def _backend_nodes():
    tree = ast.parse((ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8"))
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    worker = classes["AutomationWorker"]
    methods = {
        node.name: node
        for node in worker.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assignments = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = node
    return classes, methods, assignments


def _scope() -> dict:
    return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))


def _ci_fix_scope() -> dict:
    return json.loads(PR04_CI_FIX_SCOPE_PATH.read_text(encoding="utf-8"))


def _strip_annotations(function: ast.FunctionDef) -> ast.FunctionDef:
    function = copy.deepcopy(function)
    for argument in (
        *function.args.posonlyargs,
        *function.args.args,
        *function.args.kwonlyargs,
    ):
        argument.annotation = None
    if function.args.vararg is not None:
        function.args.vararg.annotation = None
    if function.args.kwarg is not None:
        function.args.kwarg.annotation = None
    function.returns = None
    return function


_ERROR_REFERENCE_MAP = {
    "security_challenge": "SecurityChallenge",
    "session_verification_error": "SessionVerificationError",
    "test_mode_required": "TestModeRequired",
    "test_send_limit_reached": "TestSendLimitReached",
    "invite_rejected": "InviteRejected",
}


class _ExtractedWorkflowParityNormalizer(ast.NodeTransformer):
    """Map workflow host/dependency indirection back to the frozen worker AST."""

    def visit_Attribute(self, node: ast.Attribute):
        node = self.generic_visit(node)
        if (
            isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
            and node.value.attr == "host"
        ):
            return ast.copy_location(
                ast.Attribute(
                    value=ast.Name(id="self", ctx=ast.Load()),
                    attr=node.attr,
                    ctx=node.ctx,
                ),
                node,
            )
        if (
            isinstance(node.value, ast.Attribute)
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "self"
            and node.value.attr == "errors"
            and node.attr in _ERROR_REFERENCE_MAP
        ):
            return ast.copy_location(
                ast.Name(id=_ERROR_REFERENCE_MAP[node.attr], ctx=ast.Load()), node
            )
        return node

    def visit_Name(self, node: ast.Name):
        if node.id == "SHARE_INVITE_SELECTORS":
            node.id = "SELECTORS"
        elif node.id == "SHARE_INVITE_EMAIL_RE":
            node.id = "EMAIL_RE"
        return node

    def visit_Call(self, node: ast.Call):
        node = self.generic_visit(node)
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr == "_setting"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
            return ast.copy_location(
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Attribute(
                            value=ast.Name(id="self", ctx=ast.Load()),
                            attr="settings",
                            ctx=ast.Load(),
                        ),
                        attr="get",
                        ctx=ast.Load(),
                    ),
                    args=[
                        ast.Constant(value=key),
                        ast.Subscript(
                            value=ast.Name(id="DEFAULT_SETTINGS", ctx=ast.Load()),
                            slice=ast.Constant(value=key),
                            ctx=ast.Load(),
                        ),
                    ],
                    keywords=[],
                ),
                node,
            )
        return node


def _extracted_method_semantic_hash(function: ast.FunctionDef) -> str:
    normalized = _ExtractedWorkflowParityNormalizer().visit(
        _strip_annotations(function)
    )
    normalized = ast.fix_missing_locations(normalized)
    return _ast_hash(normalized)


def _errors() -> ShareInviteRuntimeErrors:
    return ShareInviteRuntimeErrors(
        security_challenge=backend.SecurityChallenge,
        session_verification_error=backend.SessionVerificationError,
        test_mode_required=backend.TestModeRequired,
        test_send_limit_reached=backend.TestSendLimitReached,
        invite_rejected=backend.InviteRejected,
    )


class FakePage:
    def __init__(self, url: str = "https://example.test/share") -> None:
        self.url = url

    def is_closed(self) -> bool:
        return False


class FakeEvent:
    def __init__(self, set_value: bool = False) -> None:
        self.value = set_value

    def is_set(self) -> bool:
        return self.value

    def set(self) -> None:
        self.value = True

    def clear(self) -> None:
        self.value = False


class FakeHost:
    def __init__(self) -> None:
        self.settings = dict(backend.DEFAULT_SETTINGS)
        self.stop_event = FakeEvent()
        self.close_event = FakeEvent()
        self.pause_event = FakeEvent()
        self.login_verified_event = FakeEvent()
        self.active_page = FakePage()
        self.state = SimpleNamespace(target_url="https://example.test/share")
        self.run_send_count = 0
        self.run_send_limit = 10
        self.calls: list[tuple] = []

    def wait_if_paused(self):
        self.calls.append(("wait_if_paused",))

    def detect_security(self, page):
        self.calls.append(("detect_security", page))

    def any_visible(self, page, selectors, timeout=0):
        self.calls.append(("any_visible", tuple(selectors), timeout))
        return True

    def first_visible_text(self, page, selectors):
        if tuple(selectors) == tuple(SHARE_INVITE_SELECTORS["test_mode_banner"]):
            return "TEST MODE"
        return ""

    def safe_goto(self, page, url):
        self.calls.append(("safe_goto", url))
        page.url = url

    def emit(self, kind, payload):
        self.calls.append(("emit", kind, dict(payload)))

    def log(self, message, level="INFO"):
        self.calls.append(("log", message, level))

    def interruptible_sleep(self, seconds):
        self.calls.append(("sleep", seconds))

    def click_first(self, page, selectors, label, before_click=None):
        self.calls.append(("click_first", tuple(selectors), label))
        if before_click is not None:
            before_click()

    def fill_first(self, page, selectors, value, label):
        self.calls.append(("fill_first", tuple(selectors), value, label))

    def _register_send_click_attempt(self):
        self.run_send_count += 1
        self.calls.append(("register_send",))


def test_manifest_and_logo_are_real_source_controlled_assets():
    scope = _scope()
    assert load_manifest() == SHARE_INVITE_MANIFEST
    assert SHARE_INVITE_MANIFEST.workflow_id == "share_invite"
    assert SHARE_INVITE_MANIFEST.entrypoint == "share_invite"
    logo = ROOT / "src/vibrapilot/workflow/share_invite" / SHARE_INVITE_MANIFEST.logo
    approved_logo = ROOT / scope["approved_logo_source"]
    assert logo.is_file()
    assert hashlib.sha256(logo.read_bytes()).hexdigest() == scope["approved_logo_sha256"]
    assert logo.read_bytes() == approved_logo.read_bytes()


def test_first_builtin_registry_contains_only_share_invite_and_default_manager_remains_empty():
    assert WorkflowManager().list_workflows() == ()
    manager = WorkflowManager.with_builtin_workflows()
    assert [item.workflow_id for item in manager.list_workflows()] == ["share_invite"]
    assert manager.require_workflow("share_invite") == SHARE_INVITE_MANIFEST


def test_share_invite_runtime_satisfies_minimum_workflow_contract():
    workflow = ShareInviteWorkflow(
        FakeHost(), default_settings=backend.DEFAULT_SETTINGS, errors=_errors()
    )
    assert isinstance(workflow, WorkflowRuntime)
    assert workflow.manifest == SHARE_INVITE_MANIFEST


def test_share_invite_selectors_and_priority_are_exact_baseline_values():
    scope = _scope()
    assert SHARE_INVITE_SELECTORS == scope["share_invite_selector_baseline"]
    for key, selectors in SHARE_INVITE_SELECTORS.items():
        assert backend.SELECTORS[key] == selectors


def test_email_regex_is_exact_baseline_pattern():
    assert SHARE_INVITE_EMAIL_RE.pattern == backend.EMAIL_RE.pattern == _scope()["email_regex"]


@pytest.mark.parametrize("email", ["", "invalid", "a@", "@example.test", "a b@example.test"])
def test_invalid_email_is_blocked_before_workflow_browser_actions(email: str):
    host = FakeHost()
    workflow = ShareInviteWorkflow(host, default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    with pytest.raises(ValueError, match="Invite email is blank or invalid"):
        workflow.execute_flow(SimpleNamespace(email=email))
    assert host.calls == []


def test_execute_flow_preserves_share_invite_order_and_result_string(monkeypatch):
    host = FakeHost()
    workflow = ShareInviteWorkflow(host, default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    order: list[str] = []
    monkeypatch.setattr(workflow, "assert_test_mode", lambda page: order.append("assert_test_mode"))
    monkeypatch.setattr(workflow, "ensure_share_entry", lambda page: order.append("ensure_share_entry"))
    monkeypatch.setattr(workflow, "open_share_modal", lambda page: order.append("open_share_modal"))
    monkeypatch.setattr(workflow, "fill_invite_email", lambda page, email: order.append("fill_invite_email"))
    monkeypatch.setattr(workflow, "arm_invite_notification_monitor", lambda page: order.append("arm_monitor") or {"seq": 0})
    monkeypatch.setattr(workflow, "submit_share_invite", lambda page, email, state: order.append("submit_share_invite"))
    result = workflow.execute_flow(SimpleNamespace(email="user@example.test"))
    assert order == [
        "assert_test_mode",
        "ensure_share_entry",
        "open_share_modal",
        "fill_invite_email",
        "arm_monitor",
        "submit_share_invite",
    ]
    assert result == "https://example.test/share | invite=sent"


def test_submit_rechecks_email_and_uses_existing_send_attempt_callback(monkeypatch):
    host = FakeHost()
    workflow = ShareInviteWorkflow(host, default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    monkeypatch.setattr(workflow, "assert_test_mode", lambda page: host.calls.append(("assert_test_mode",)))
    monkeypatch.setattr(workflow, "input_value_first", lambda page, selectors, label: "user@example.test")
    monkeypatch.setattr(workflow, "wait_invite_result", lambda page, state: host.calls.append(("wait_result",)))
    workflow.submit_share_invite(host.active_page, "user@example.test", {"seq": 0})
    assert ("register_send",) in host.calls
    assert host.run_send_count == 1
    click_index = next(i for i, call in enumerate(host.calls) if call[0] == "click_first")
    register_index = host.calls.index(("register_send",))
    wait_index = host.calls.index(("wait_result",))
    assert click_index < register_index < wait_index


def test_submit_blocks_mismatched_email_before_send(monkeypatch):
    host = FakeHost()
    workflow = ShareInviteWorkflow(host, default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    monkeypatch.setattr(workflow, "assert_test_mode", lambda page: None)
    monkeypatch.setattr(workflow, "input_value_first", lambda page, selectors, label: "other@example.test")
    with pytest.raises(RuntimeError, match="Blank or mismatched invite submission"):
        workflow.submit_share_invite(host.active_page, "user@example.test", {"seq": 0})
    assert not any(call[0] == "click_first" for call in host.calls)
    assert host.run_send_count == 0


def test_send_limit_uses_existing_backend_exception_identity(monkeypatch):
    host = FakeHost()
    host.run_send_count = host.run_send_limit
    workflow = ShareInviteWorkflow(host, default_settings=backend.DEFAULT_SETTINGS, errors=_errors())
    monkeypatch.setattr(workflow, "assert_test_mode", lambda page: None)
    monkeypatch.setattr(workflow, "input_value_first", lambda page, selectors, label: "user@example.test")
    with pytest.raises(backend.TestSendLimitReached):
        workflow.submit_share_invite(host.active_page, "user@example.test", {"seq": 0})


def test_all_extracted_share_invite_methods_are_semantically_identical_to_baseline():
    scope = _ci_fix_scope()
    tree = ast.parse(
        (ROOT / "src/vibrapilot/workflow/share_invite/workflow.py").read_text(
            encoding="utf-8"
        )
    )
    workflow_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ShareInviteWorkflow"
    )
    methods = {
        node.name: node
        for node in workflow_class.body
        if isinstance(node, ast.FunctionDef)
    }
    for name, expected in scope[
        "baseline_extracted_method_canonical_ast_sha256"
    ].items():
        assert _extracted_method_semantic_hash(methods[name]) == expected, name


def test_backend_compatibility_methods_delegate_to_share_invite_runtime():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    for method in (
        "test_mode_banner_ready", "authenticated_test_session_ready",
        "wait_for_authenticated_test_session", "ensure_authenticated_test_session",
        "assert_test_mode", "execute_flow", "ensure_share_entry", "share_button_ready",
        "wait_for_share_button", "share_modal_ready", "close_existing_share_modal",
        "open_share_modal", "prepare_invite_retry", "fill_invite_email",
        "input_value_first", "arm_invite_notification_monitor", "submit_share_invite",
        "wait_invite_result",
    ):
        assert f"def {method}" in source
    # PR-05 preserves these compatibility methods but moves runtime construction
    # behind WorkflowManager; direct ShareInviteWorkflow construction in backend is
    # intentionally no longer required.
    assert "WorkflowManager.with_builtin_workflows" in source
    assert "resolve_active_runtime(" in source
    assert "ShareInviteRuntimeErrors(" in source


def test_safety_critical_worker_methods_remain_ast_identical_to_approved_baseline():
    scope = _scope()
    _, methods, _ = _backend_nodes()
    current = json.loads(V10630_SCOPE_PATH.read_text(encoding="utf-8")) if V10630_SCOPE_PATH.is_file() else {}
    v10635 = json.loads(V10635_SCOPE_PATH.read_text(encoding="utf-8")) if V10635_SCOPE_PATH.is_file() else {}
    authorized = (
        set(current.get("authorized_automationworker_method_changes", []))
        | set(v10635.get("authorized_automationworker_method_changes", []))
    )
    for name, expected in scope["frozen_automationworker_method_ast_sha256"].items():
        if name in authorized:
            continue
        assert _ast_hash(methods[name]) == expected, name


def test_backend_selectors_and_exception_classes_remain_ast_frozen():
    scope = _scope()
    classes, _, assignments = _backend_nodes()
    for name, expected in scope["frozen_backend_ast_sha256"].items():
        node = assignments["SELECTORS"] if name == "SELECTORS" else classes[name]
        assert _ast_hash(node) == expected, name


def test_pr04_frozen_runtime_files_are_byte_identical():
    scope = _scope()
    superseded = set()
    if PR06_SCOPE_PATH.is_file():
        pr06_scope = json.loads(PR06_SCOPE_PATH.read_text(encoding="utf-8"))
        superseded.update(pr06_scope.get("allowed_runtime_source_changes", []))
    if PR08_SCOPE_PATH.is_file():
        pr08_scope = json.loads(PR08_SCOPE_PATH.read_text(encoding="utf-8"))
        superseded.update(pr08_scope.get("allowed_production_source_changes", []))
    if V10630_SCOPE_PATH.is_file():
        current = json.loads(V10630_SCOPE_PATH.read_text(encoding="utf-8"))
        superseded.update(current.get("allowed_production_source_changes", []))
        superseded.update(current.get("authorized_nonproduction_files", []))
    if V10631_SCOPE_PATH.is_file():
        current = json.loads(V10631_SCOPE_PATH.read_text(encoding="utf-8"))
        superseded.update(current.get("allowed_production_source_changes", []))
        superseded.update(current.get("authorized_nonproduction_files", []))
    for relative, expected in scope["frozen_file_sha256"].items():
        if relative in superseded:
            continue
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == expected, relative


def test_no_external_plugin_or_manifest_driven_dynamic_import_surface():
    texts = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/vibrapilot/workflow/registry.py",
            "src/vibrapilot/workflow/manager.py",
            "src/vibrapilot/workflow/share_invite/__init__.py",
        )
    )
    for forbidden in (
        "importlib.import_module", "pkgutil", "entry_points(", "os.walk(",
        "glob.glob(", "exec(", "eval(",
    ):
        assert forbidden not in texts


def test_pr05_allows_only_in_memory_active_workflow_resolution_without_switching_or_persistence():
    workflow_tree = ROOT / "src/vibrapilot/workflow"
    manager_text = (workflow_tree / "manager.py").read_text(encoding="utf-8")
    assert "active_workflow_id" in manager_text
    manager_tree = ast.parse(manager_text)
    manager_class = next(node for node in manager_tree.body if isinstance(node, ast.ClassDef) and node.name == "WorkflowManager")
    method_names = {node.name for node in manager_class.body if isinstance(node, ast.FunctionDef)}
    assert {"require_active_workflow", "resolve_active_runtime"} <= method_names
    assert not method_names & {"activate", "switch", "restart", "persist_active_workflow", "set_active_workflow"}
    for relative in (
        ROOT / "config/settings.defaults.json",
        ROOT / "src/vibrapilot/task_runtime_store.py",
        ROOT / "src/vibrapilot/workspace_state.py",
    ):
        assert "active_workflow_id" not in relative.read_text(encoding="utf-8")
