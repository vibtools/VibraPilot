from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from vibrapilot.workflow import (
    DuplicateWorkflowError,
    UnknownWorkflowError,
    WorkflowManager,
    WorkflowManifest,
    WorkflowManifestError,
    WorkflowRegistry,
)

ROOT = Path(__file__).resolve().parents[1]
SCOPE = ROOT / "config" / "verification" / "v1.0.7.0_pr02_pr03_workflow_foundation_scope.json"


def _manifest(workflow_id: str = "alpha") -> WorkflowManifest:
    return WorkflowManifest(
        workflow_id=workflow_id,
        name="Alpha Workflow",
        description="Source-controlled test workflow metadata.",
        version="1.0.0",
        logo="assets/logo.png",
        entrypoint="alpha_workflow",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_valid_manifest_normalizes_text_and_keeps_safe_metadata():
    manifest = WorkflowManifest(
        workflow_id="alpha_1",
        name="  Alpha Workflow  ",
        description="  Description  ",
        version="1.2.3",
        logo="assets/logo.png",
        entrypoint="alpha_workflow",
    )
    assert manifest.workflow_id == "alpha_1"
    assert manifest.name == "Alpha Workflow"
    assert manifest.description == "Description"
    assert manifest.logo == "assets/logo.png"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("workflow_id", ""),
        ("workflow_id", "Alpha"),
        ("workflow_id", "../alpha"),
        ("name", " "),
        ("description", ""),
        ("version", "v1.0"),
        ("version", "1.2.3.4.5"),
        ("logo", "../logo.png"),
        ("logo", "/absolute/logo.png"),
        ("logo", r"assets\\logo.png"),
        ("entrypoint", "module:Class"),
        ("entrypoint", "../module"),
    ],
)
def test_invalid_manifest_metadata_fails_closed(field: str, value: str):
    values = {
        "workflow_id": "alpha",
        "name": "Alpha",
        "description": "Description",
        "version": "1.0",
        "logo": "assets/logo.png",
        "entrypoint": "alpha_workflow",
    }
    values[field] = value
    with pytest.raises(WorkflowManifestError):
        WorkflowManifest(**values)


def test_registry_registers_lists_and_resolves_deterministically():
    registry = WorkflowRegistry([_manifest("beta"), _manifest("alpha")])
    assert [item.workflow_id for item in registry.list_workflows()] == ["alpha", "beta"]
    assert registry.get("alpha") is not None
    assert registry.require("beta").workflow_id == "beta"
    assert len(registry) == 2


def test_duplicate_registration_is_rejected_without_replacing_existing_entry():
    first = _manifest("alpha")
    registry = WorkflowRegistry([first])
    with pytest.raises(DuplicateWorkflowError):
        registry.register(_manifest("alpha"))
    assert registry.require("alpha") is first


def test_register_many_is_atomic_on_duplicate():
    registry = WorkflowRegistry([_manifest("alpha")])
    with pytest.raises(DuplicateWorkflowError):
        registry.register_many([_manifest("beta"), _manifest("alpha")])
    assert [item.workflow_id for item in registry.list_workflows()] == ["alpha"]


def test_unknown_workflow_fails_closed():
    registry = WorkflowRegistry()
    assert registry.get("missing") is None
    with pytest.raises(UnknownWorkflowError):
        registry.require("missing")


def test_manager_is_read_only_registry_facade_with_no_default_workflows():
    manager = WorkflowManager()
    assert manager.list_workflows() == ()
    assert manager.get_workflow("share_invite") is None
    with pytest.raises(UnknownWorkflowError):
        manager.require_workflow("share_invite")


def test_manager_resolves_only_explicitly_registered_builtin_metadata():
    registry = WorkflowRegistry([_manifest("alpha")])
    manager = WorkflowManager(registry)
    assert manager.require_workflow("alpha").name == "Alpha Workflow"


def test_framework_has_no_external_discovery_or_dynamic_import_apis():
    forbidden_names = {
        "import_module",
        "entry_points",
        "iter_modules",
        "walk_packages",
        "exec",
        "eval",
    }
    for relative in (
        "src/vibrapilot/workflow/contracts.py",
        "src/vibrapilot/workflow/registry.py",
        "src/vibrapilot/workflow/manager.py",
    ):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        assert forbidden_names.isdisjoint(used | attrs)


def test_approved_frozen_production_files_are_byte_identical():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    for relative, expected in scope["frozen_file_sha256"].items():
        assert _sha256(ROOT / relative) == expected, relative


def test_scope_contract_keeps_pr03_framework_only():
    scope = json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["baseline_sha256"] == "ee2431e3ee4d56697e9127b463ee904806e35853e41abbd2c082b4101f727682"
    assert scope["runtime_version_unchanged"] == "1.0.6.19"
    assert scope["captcha_status"] == "DEFERRED"
    assert scope["share_invite_extraction_authorized"] is False
    assert scope["external_plugin_system_authorized"] is False
    assert scope["active_workflow_persistence_authorized"] is False
