"""Historical PR-04 contract supersession for v1.0.6.36 externalization.

The operational Share Invite runtime is deliberately no longer source-controlled
inside VibraPilot Core. Exact runtime/package parity is verified by the separate
Share_Invite_v1.0 artifact verifier delivered with v1.0.6.36.
"""
from pathlib import Path

from vibrapilot.workflow import WorkflowManager, builtin_workflow_manifests, builtin_workflow_runtime_factories

ROOT = Path(__file__).resolve().parents[1]


def test_pr04_historical_scope_evidence_is_retained():
    assert (ROOT / "config/verification/v1.0.6.20_pr04_share_invite_workflow_extraction_scope.json").is_file()


def test_v10636_core_contains_zero_builtin_workflows():
    assert builtin_workflow_manifests() == ()
    assert builtin_workflow_runtime_factories() == {}
    assert WorkflowManager.with_builtin_workflows().list_workflows() == ()


def test_share_invite_operational_source_is_not_in_core_repository():
    assert not (ROOT / "src/vibrapilot/workflow/share_invite").exists()


def test_backend_has_no_share_invite_runtime_type_dependency():
    source = (ROOT / "src/vibrapilot/backend.py").read_text(encoding="utf-8")
    assert "from .workflow.share_invite" not in source
    assert "ShareInviteWorkflow" not in source
    assert "_share_invite_runtime" not in source
    assert "_is_share_invite_workflow" not in source


def test_registry_has_no_share_invite_import_or_factory():
    source = (ROOT / "src/vibrapilot/workflow/registry.py").read_text(encoding="utf-8")
    assert "SHARE_INVITE_MANIFEST" not in source
    assert "ShareInviteWorkflow" not in source
    assert "return ()" in source


def test_share_invite_schema_authority_is_not_registered_in_core():
    inputs = (ROOT / "src/vibrapilot/workflow_inputs.py").read_text(encoding="utf-8")
    schemas = (ROOT / "src/vibrapilot/workflow/schemas.py").read_text(encoding="utf-8")
    assert "SHARE_INVITE_INPUT_SCHEMA" not in inputs
    assert "WORKFLOW_INPUT_SCHEMAS" not in inputs
    assert "builtin_share_invite_settings_schema" not in schemas
    assert "builtin_share_invite_task_schema" not in schemas
