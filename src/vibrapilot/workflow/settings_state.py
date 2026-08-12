"""Atomic per-workflow Workflow Settings persistence."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from .schemas import WorkflowFormSchema, WorkflowSchemaError, normalize_form_values

WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION = 1


class WorkflowSettingsStateError(RuntimeError):
    pass


class WorkflowSettingsStateStore:
    def __init__(
        self,
        path: Path,
        *,
        schema_resolver: Callable[[str], WorkflowFormSchema],
    ) -> None:
        self.path = Path(path)
        self.schema_resolver = schema_resolver

    def _empty(self) -> dict[str, Any]:
        return {"schema_version": WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION, "workflows": {}}

    def _decode(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise WorkflowSettingsStateError("Workflow Settings state root must be a JSON object.")
        if payload.get("schema_version") != WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION:
            raise WorkflowSettingsStateError("Unsupported Workflow Settings state schema version.")
        workflows = payload.get("workflows")
        if not isinstance(workflows, dict):
            raise WorkflowSettingsStateError("Workflow Settings workflows must be a JSON object.")
        clean: dict[str, dict[str, Any]] = {}
        for workflow_id, entry in workflows.items():
            if not isinstance(workflow_id, str) or not workflow_id.strip() or not isinstance(entry, dict):
                raise WorkflowSettingsStateError("Workflow Settings state contains an invalid workflow entry.")
            values = entry.get("values", {})
            if not isinstance(values, dict):
                raise WorkflowSettingsStateError(
                    f"Workflow Settings values must be an object: {workflow_id}."
                )
            clean_values: dict[str, Any] = {}
            for key, value in values.items():
                if not isinstance(key, str) or not key:
                    raise WorkflowSettingsStateError(
                        f"Workflow Settings contains an invalid key: {workflow_id}."
                    )
                if value is not None and not isinstance(value, (str, int, bool, float)):
                    raise WorkflowSettingsStateError(
                        f"Workflow Settings contains an invalid value: {workflow_id}.{key}."
                    )
                clean_values[key] = value
            clean[workflow_id] = clean_values
        return {"schema_version": WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION, "workflows": clean}

    def load_or_create(self) -> dict[str, Any]:
        if not self.path.exists():
            state = self._empty()
            self.save_state(state)
            return state
        return self.load_existing()

    def load_existing(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowSettingsStateError(
                f"Workflow Settings state could not be read: {exc}"
            ) from exc
        return self._decode(payload)

    def values_for(self, workflow_id: str, *, state: dict[str, Any] | None = None) -> dict[str, Any]:
        current = state if state is not None else self.load_or_create()
        try:
            schema = self.schema_resolver(workflow_id)
            raw = current["workflows"].get(workflow_id, {})
            return normalize_form_values(
                schema,
                raw,
                coerce=False,
                fill_defaults=True,
                enforce_required=False,
            )
        except WorkflowSchemaError as exc:
            raise WorkflowSettingsStateError(str(exc)) from exc

    def save_workflow_values(
        self,
        workflow_id: str,
        values: Mapping[str, Any],
        *,
        coerce: bool,
    ) -> dict[str, Any]:
        current = self.load_or_create()
        try:
            schema = self.schema_resolver(workflow_id)
            normalized = normalize_form_values(schema, values, coerce=coerce, fill_defaults=True)
        except WorkflowSchemaError as exc:
            raise WorkflowSettingsStateError(str(exc)) from exc
        workflows = {key: dict(value) for key, value in current["workflows"].items()}
        workflows[workflow_id] = normalized
        updated = {"schema_version": WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION, "workflows": workflows}
        self.save_state(updated)
        return updated

    def save_state(self, state: dict[str, Any]) -> None:
        if not isinstance(state, dict) or state.get("schema_version") != WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION:
            raise WorkflowSettingsStateError("Unsupported Workflow Settings state schema version.")
        workflows = state.get("workflows")
        if not isinstance(workflows, dict):
            raise WorkflowSettingsStateError("Workflow Settings workflows must be a JSON object.")
        payload = {
            "schema_version": WORKFLOW_SETTINGS_STATE_SCHEMA_VERSION,
            "workflows": {
                workflow_id: {"values": dict(values)}
                for workflow_id, values in workflows.items()
            },
        }
        # Validate the exact on-disk shape before committing it.
        self._decode(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            os.replace(temporary, self.path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
