from __future__ import annotations

from pathlib import Path

from vibrapilot.workflow import (
    WorkflowFieldSchema,
    WorkflowFormSchema,
    WorkflowSettingsStateStore,
    WorkflowTaskSchema,
    WorkflowTaskStateStore,
)


def test_per_workflow_settings_are_namespaced_and_atomic(tmp_path: Path):
    schemas = {
        "a": WorkflowFormSchema("a", "A", (WorkflowFieldSchema("retry", "Retry", "integer", 1),)),
        "b": WorkflowFormSchema("b", "B", (WorkflowFieldSchema("retry", "Retry", "integer", 2),)),
    }
    store = WorkflowSettingsStateStore(tmp_path / "workflow_settings.json", schema_resolver=schemas.__getitem__)
    store.load_or_create()
    store.save_workflow_values("a", {"retry": 7}, coerce=True)
    store.save_workflow_values("b", {"retry": 8}, coerce=True)
    state = store.load_existing()
    assert store.values_for("a", state=state)["retry"] == 7
    assert store.values_for("b", state=state)["retry"] == 8


def test_task_state_keeps_values_metrics_payloads_and_step_then_can_clear(tmp_path: Path):
    schema = WorkflowTaskSchema(
        "a", "Task",
        settings=(WorkflowFieldSchema("url", "URL", "url", "", role="target_url"),),
    )
    store = WorkflowTaskStateStore(tmp_path / "workflow_task_state.json")
    store.save_task_values("a", 3, schema, {"url": "https://example.test"}, coerce=True, payloads=[{"id": 1}])
    store.update_runtime("a", 3, step="Submitting")
    store.update_runtime("a", 3, metric_key="created", metric_value=4)
    entry = store.entry_for("a", 3, schema)
    assert entry["values"]["url"] == "https://example.test"
    assert entry["payloads"] == [{"id": 1}]
    assert entry["step"] == "Submitting"
    assert entry["metrics"]["created"] == 4
    store.clear_all()
    assert store.load_existing()["tasks"] == {}


def test_required_blank_values_are_allowed_at_rest_but_enforced_on_save(tmp_path: Path):
    settings_schema = WorkflowFormSchema(
        "a", "A", (WorkflowFieldSchema("token", "Token", required=True),)
    )
    settings_store = WorkflowSettingsStateStore(
        tmp_path / "workflow_settings_required.json",
        schema_resolver=lambda _workflow_id: settings_schema,
    )
    assert settings_store.values_for("a") == {"token": ""}

    task_schema = WorkflowTaskSchema(
        "a",
        "Task",
        settings=(
            WorkflowFieldSchema(
                "url", "URL", "url", "", required=True, role="target_url"
            ),
        ),
    )
    task_store = WorkflowTaskStateStore(tmp_path / "workflow_task_state_required.json")
    assert task_store.entry_for("a", 1, task_schema)["values"] == {"url": ""}

    import pytest
    from vibrapilot.workflow import WorkflowSettingsStateError, WorkflowTaskStateError

    with pytest.raises(WorkflowSettingsStateError, match="Token is required"):
        settings_store.save_workflow_values("a", {"token": ""}, coerce=True)
    with pytest.raises(WorkflowTaskStateError, match="URL is required"):
        task_store.save_task_values("a", 1, task_schema, {"url": ""}, coerce=True)
