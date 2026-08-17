from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibrapilot.workflow.input_state import (
    WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
    WorkflowInputStateError,
    WorkflowInputStateStore,
)
from vibrapilot.workflow_inputs import (
    WorkflowInputField,
    WorkflowInputSchema,
    WorkflowInputSchemaError,
    normalize_workflow_input_values,
)


SHARE_SCHEMA = WorkflowInputSchema(
    workflow_id="share_invite",
    title="Share Invite Inputs",
    fields=(
        WorkflowInputField("default_full_name", "Default Full Name", default=""),
        WorkflowInputField("default_number", "Default Number", default=""),
        WorkflowInputField("fallback_name", "Fallback Name", default=""),
        WorkflowInputField("update_click_count", "Update Click Count", default=""),
    ),
)

def _store(path: Path, extra: dict[str, WorkflowInputSchema] | None = None) -> WorkflowInputStateStore:
    schemas = {"share_invite": SHARE_SCHEMA}
    if extra:
        schemas.update(extra)
    return WorkflowInputStateStore(path, schema_resolver=schemas.__getitem__)


LEGACY = {
    "default_full_name": "Existing Person",
    "default_number": "+8801700000000",
    "fallback_name": "Existing Fallback",
    "update_click_count": "3",
}


def test_absence_only_migration_preserves_existing_share_invite_values(tmp_path: Path):
    path = tmp_path / "workflow_inputs.json"
    store = _store(path)
    state = store.load_or_migrate(legacy_share_invite_values=LEGACY)
    assert state.schema_version == 1
    assert store.values_for("share_invite", state=state) == LEGACY
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload == {
        "schema_version": 1,
        "workflows": {"share_invite": {"values": LEGACY}},
    }
    assert not path.with_name(path.name + ".tmp").exists()


def test_existing_store_never_re_migrates_from_legacy_settings(tmp_path: Path):
    path = tmp_path / "workflow_inputs.json"
    store = _store(path)
    store.load_or_migrate(legacy_share_invite_values=LEGACY)
    different = {key: "new-legacy" for key in LEGACY}
    state = store.load_or_migrate(legacy_share_invite_values=different)
    assert store.values_for("share_invite", state=state) == LEGACY


def test_corrupt_and_unsupported_state_fail_closed_without_recreation(tmp_path: Path):
    path = tmp_path / "workflow_inputs.json"
    path.write_text("{broken", encoding="utf-8")
    store = _store(path)
    with pytest.raises(WorkflowInputStateError):
        store.load_or_migrate(legacy_share_invite_values=LEGACY)
    assert path.read_text(encoding="utf-8") == "{broken"

    path.write_text(json.dumps({"schema_version": 999, "workflows": {}}), encoding="utf-8")
    with pytest.raises(WorkflowInputStateError):
        store.load_existing()
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 999


def test_missing_current_fields_use_defaults_and_stale_fields_are_inert(tmp_path: Path):
    path = tmp_path / "workflow_inputs.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
                "workflows": {
                    "share_invite": {
                        "values": {
                            "default_full_name": "Only Name",
                            "stale_old_field": "must-not-enter-runtime",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    store = _store(path)
    values = store.values_for("share_invite")
    assert values == {
        "default_full_name": "Only Name",
        "default_number": "",
        "fallback_name": "",
        "update_click_count": "",
    }
    updated = store.save_workflow_values("share_invite", values, coerce=False)
    assert "stale_old_field" not in updated.workflows["share_invite"]


def test_per_workflow_values_are_isolated_with_test_only_synthetic_schema(tmp_path: Path):
    synthetic = WorkflowInputSchema(
        workflow_id="synthetic_test",
        title="Synthetic Inputs",
        fields=(
            WorkflowInputField("count", "Count", kind="integer", default=1, minimum=0, maximum=10),
            WorkflowInputField("enabled", "Enabled", kind="boolean", default=False),
            WorkflowInputField("mode", "Mode", kind="choice", default="a", choices=("a", "b")),
        ),
    )
    path = tmp_path / "workflow_inputs.json"
    store = _store(path, {synthetic.workflow_id: synthetic})
    store.load_or_migrate(legacy_share_invite_values=LEGACY)
    store.save_workflow_values(
        "synthetic_test",
        {"count": "4", "enabled": "yes", "mode": "b"},
        coerce=True,
    )
    assert store.values_for("synthetic_test") == {"count": 4, "enabled": True, "mode": "b"}
    assert store.values_for("share_invite") == LEGACY
    store.save_workflow_values(
        "share_invite",
        {**LEGACY, "default_full_name": "Changed Share"},
        coerce=False,
    )
    assert store.values_for("synthetic_test") == {"count": 4, "enabled": True, "mode": "b"}


def test_schema_validation_rejects_duplicate_keys_invalid_kinds_and_bad_constraints():
    with pytest.raises(WorkflowInputSchemaError):
        WorkflowInputSchema(
            workflow_id="synthetic_test",
            title="Duplicate",
            fields=(WorkflowInputField("a", "A"), WorkflowInputField("a", "Again")),
        )
    with pytest.raises(WorkflowInputSchemaError):
        WorkflowInputField("bad", "Bad", kind="file")
    with pytest.raises(WorkflowInputSchemaError):
        WorkflowInputField("count", "Count", kind="integer", default=1, minimum=10, maximum=2)
    with pytest.raises(WorkflowInputSchemaError):
        WorkflowInputField("mode", "Mode", kind="choice", default="x", choices=("a", "b"))


def test_schema_normalization_never_returns_stale_keys_or_executable_structures():
    schema = WorkflowInputSchema(
        workflow_id="synthetic_test",
        title="Synthetic",
        fields=(WorkflowInputField("name", "Name", default=""),),
    )
    assert normalize_workflow_input_values(
        schema, {"name": "safe", "callback": "import.module:run"}, coerce=False
    ) == {"name": "safe"}
