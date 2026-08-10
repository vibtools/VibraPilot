"""Atomic per-workflow Workflow Input persistence for VibraPilot PR-08."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping

from ..workflow_inputs import (
    WorkflowInputSchemaError,
    normalize_workflow_input_values,
    workflow_input_schema_for,
)


WORKFLOW_INPUT_STATE_SCHEMA_VERSION = 1


class WorkflowInputStateError(RuntimeError):
    """Raised when authoritative Workflow Input persistence is unavailable."""


@dataclass(frozen=True, slots=True)
class WorkflowInputState:
    schema_version: int
    workflows: dict[str, dict[str, Any]]

    def copy_workflows(self) -> dict[str, dict[str, Any]]:
        return {
            workflow_id: dict(values)
            for workflow_id, values in self.workflows.items()
        }


class WorkflowInputStateStore:
    """Own ``AppData/workflow_inputs.json`` using fail-closed atomic writes."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _decode(self, payload: Any) -> WorkflowInputState:
        if not isinstance(payload, dict):
            raise WorkflowInputStateError("Workflow Input state root must be a JSON object.")
        if payload.get("schema_version") != WORKFLOW_INPUT_STATE_SCHEMA_VERSION:
            raise WorkflowInputStateError(
                "Unsupported Workflow Input state schema version."
            )
        workflows_payload = payload.get("workflows")
        if not isinstance(workflows_payload, dict):
            raise WorkflowInputStateError("Workflow Input state workflows must be a JSON object.")

        workflows: dict[str, dict[str, Any]] = {}
        for workflow_id, entry in workflows_payload.items():
            if not isinstance(workflow_id, str) or not workflow_id.strip():
                raise WorkflowInputStateError("Workflow Input state contains an invalid workflow ID.")
            if not isinstance(entry, dict):
                raise WorkflowInputStateError(
                    f"Workflow Input state entry must be an object: {workflow_id}."
                )
            values = entry.get("values")
            if not isinstance(values, dict):
                raise WorkflowInputStateError(
                    f"Workflow Input values must be an object: {workflow_id}."
                )
            # Keep unknown/stale keys as inert JSON data until the workflow is
            # actively resolved against its source-controlled schema.  Reject
            # nested/executable-shaped structures at the persistence boundary.
            clean_values: dict[str, Any] = {}
            for key, value in values.items():
                if not isinstance(key, str) or not key:
                    raise WorkflowInputStateError(
                        f"Workflow Input state contains an invalid field key: {workflow_id}."
                    )
                if value is not None and not isinstance(value, (str, int, bool)):
                    raise WorkflowInputStateError(
                        f"Workflow Input state contains an invalid field value: {workflow_id}.{key}."
                    )
                clean_values[key] = value
            workflows[workflow_id] = clean_values
        return WorkflowInputState(
            schema_version=WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            workflows=workflows,
        )

    def load_existing(self) -> WorkflowInputState:
        if not self.path.is_file():
            raise WorkflowInputStateError(
                f"Workflow Input state file is missing: {self.path}."
            )
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowInputStateError(
                f"Workflow Input state could not be read: {exc}"
            ) from exc
        return self._decode(payload)

    def values_for(
        self,
        workflow_id: str,
        *,
        state: WorkflowInputState | None = None,
    ) -> dict[str, Any]:
        current = state if state is not None else self.load_existing()
        try:
            schema = workflow_input_schema_for(workflow_id)
            raw = current.workflows.get(workflow_id, {})
            # Stored values are strict by type. Missing current fields are filled
            # from source-controlled defaults; stale keys are ignored.
            return normalize_workflow_input_values(
                schema, raw, coerce=False, fill_defaults=True
            )
        except WorkflowInputSchemaError as exc:
            raise WorkflowInputStateError(str(exc)) from exc

    def load_or_migrate(
        self,
        *,
        legacy_share_invite_values: Mapping[str, Any],
    ) -> WorkflowInputState:
        if self.path.exists():
            return self.load_existing()
        try:
            schema = workflow_input_schema_for("share_invite")
            migrated = normalize_workflow_input_values(
                schema,
                legacy_share_invite_values,
                coerce=True,
                fill_defaults=True,
            )
        except WorkflowInputSchemaError as exc:
            raise WorkflowInputStateError(
                f"Legacy Share Invite Workflow Inputs could not be migrated: {exc}"
            ) from exc
        state = WorkflowInputState(
            schema_version=WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            workflows={"share_invite": migrated},
        )
        self.save_state(state)
        return state

    def save_workflow_values(
        self,
        workflow_id: str,
        values: Mapping[str, Any],
        *,
        coerce: bool,
    ) -> WorkflowInputState:
        current = self.load_existing()
        try:
            schema = workflow_input_schema_for(workflow_id)
            normalized = normalize_workflow_input_values(
                schema, values, coerce=coerce, fill_defaults=True
            )
        except WorkflowInputSchemaError as exc:
            raise WorkflowInputStateError(str(exc)) from exc
        workflows = current.copy_workflows()
        # Successful Save/Reset rewrites exactly the current schema keys, which
        # deterministically drops stale fields for this workflow only.
        workflows[workflow_id] = normalized
        updated = WorkflowInputState(
            schema_version=WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            workflows=workflows,
        )
        self.save_state(updated)
        return updated

    def save_state(self, state: WorkflowInputState) -> None:
        # Re-decode our own serialized shape before committing it so callers
        # cannot use this rollback/helper surface to persist malformed state.
        payload = {
            "schema_version": WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            "workflows": {
                workflow_id: {"values": dict(values)}
                for workflow_id, values in state.workflows.items()
            },
        }
        self._decode(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise WorkflowInputStateError(
                f"Workflow Input state could not be saved atomically: {exc}"
            ) from exc
