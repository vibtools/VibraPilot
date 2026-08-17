"""Atomic per-workflow Workflow Input persistence for VibraPilot."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from ..workflow_inputs import (
    WorkflowInputSchema,
    WorkflowInputSchemaError,
    normalize_workflow_input_values,
)
from .schemas import (
    WorkflowFormSchema,
    WorkflowSchemaError,
    normalize_form_values,
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

    def __init__(
        self,
        path: Path,
        *,
        schema_resolver: Callable[[str], WorkflowInputSchema | WorkflowFormSchema] | None = None,
    ):
        self.path = Path(path)
        self.schema_resolver = schema_resolver

    def _resolve_schema(self, workflow_id: str) -> WorkflowInputSchema | WorkflowFormSchema:
        if self.schema_resolver is None:
            raise WorkflowInputStateError(
                f"Workflow Input schema resolver is unavailable for {workflow_id!r}."
            )
        try:
            return self.schema_resolver(workflow_id)
        except (WorkflowInputSchemaError, WorkflowSchemaError) as exc:
            raise WorkflowInputStateError(str(exc)) from exc
        except Exception as exc:
            raise WorkflowInputStateError(
                f"Workflow Input schema is unavailable for {workflow_id!r}: {exc}"
            ) from exc

    @staticmethod
    def _normalize(
        schema: WorkflowInputSchema | WorkflowFormSchema,
        values: Mapping[str, Any],
        *,
        coerce: bool,
        fill_defaults: bool,
        enforce_required: bool = True,
    ) -> dict[str, Any]:
        try:
            if isinstance(schema, WorkflowFormSchema):
                return normalize_form_values(
                    schema,
                    values,
                    coerce=coerce,
                    fill_defaults=fill_defaults,
                    enforce_required=enforce_required,
                )
            return normalize_workflow_input_values(
                schema, values, coerce=coerce, fill_defaults=fill_defaults
            )
        except (WorkflowInputSchemaError, WorkflowSchemaError) as exc:
            raise WorkflowInputStateError(str(exc)) from exc

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
            clean_values: dict[str, Any] = {}
            for key, value in values.items():
                if not isinstance(key, str) or not key:
                    raise WorkflowInputStateError(
                        f"Workflow Input state contains an invalid field key: {workflow_id}."
                    )
                if value is not None and not isinstance(value, (str, int, bool, float)):
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
        schema = self._resolve_schema(workflow_id)
        raw = current.workflows.get(workflow_id, {})
        return self._normalize(
            schema,
            raw,
            coerce=False,
            fill_defaults=True,
            enforce_required=False,
        )

    def load_or_migrate(
        self,
        *,
        legacy_share_invite_values: Mapping[str, Any],
        active_workflow_id: str | None = "share_invite",
        preserve_legacy_share_invite: bool = True,
    ) -> WorkflowInputState:
        """Create canonical input state without requiring Share Invite to be built in.

        The historical Share Invite values are preserved only as migration data;
        active external workflows obtain their defaults from their installed schema.
        """
        if self.path.exists():
            return self.load_existing()
        workflows: dict[str, dict[str, Any]] = {}
        active = str(active_workflow_id or "").strip()
        if preserve_legacy_share_invite:
            legacy_values = {
                str(key): value for key, value in legacy_share_invite_values.items()
                if isinstance(key, str) and value is not None and isinstance(value, (str, int, bool, float))
            }
            if active == "share_invite" and self.schema_resolver is not None:
                try:
                    schema = self._resolve_schema("share_invite")
                except WorkflowInputStateError:
                    # The externalized package may not be installed yet. Preserve
                    # migration data verbatim and validate it only after install.
                    workflows["share_invite"] = legacy_values
                else:
                    workflows["share_invite"] = self._normalize(
                        schema, legacy_values, coerce=True, fill_defaults=True
                    )
            else:
                # Keep scalar legacy data inert until the external Share Invite
                # package is installed; schema validation happens when it is used.
                workflows["share_invite"] = legacy_values
        if active and active != "share_invite":
            schema = self._resolve_schema(active)
            workflows[active] = self._normalize(
                schema, schema.defaults(), coerce=False, fill_defaults=True, enforce_required=False
            )
        state = WorkflowInputState(
            schema_version=WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            workflows=workflows,
        )
        self.save_state(state)
        return state

    def recover_workflow_defaults(
        self, workflow_id: str
    ) -> tuple[WorkflowInputState, Path | None]:
        schema = self._resolve_schema(workflow_id)
        defaults = self._normalize(
            schema,
            schema.defaults(),
            coerce=False,
            fill_defaults=True,
            enforce_required=False,
        )

        quarantine: Path | None = None
        if self.path.exists():
            quarantine = self.path.with_name(
                f"{self.path.name}.corrupt-{uuid.uuid4().hex}"
            )
            try:
                os.replace(self.path, quarantine)
            except OSError as exc:
                raise WorkflowInputStateError(
                    f"Workflow Input state could not be quarantined for recovery: {exc}"
                ) from exc

        recovered = WorkflowInputState(
            schema_version=WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            workflows={workflow_id: defaults},
        )
        try:
            self.save_state(recovered)
        except Exception:
            if quarantine is not None and quarantine.is_file() and not self.path.exists():
                try:
                    os.replace(quarantine, self.path)
                except OSError as restore_exc:
                    raise WorkflowInputStateError(
                        f"Workflow Input recovery failed and original state could not be restored: "
                        f"{restore_exc}"
                    ) from restore_exc
            raise
        return recovered, quarantine

    def rollback_recovery(self, quarantine: Path | None) -> None:
        try:
            if self.path.exists():
                self.path.unlink()
            if quarantine is not None:
                quarantine = Path(quarantine)
                if not quarantine.is_file():
                    raise WorkflowInputStateError(
                        f"Workflow Input recovery rollback evidence is missing: {quarantine.name}"
                    )
                os.replace(quarantine, self.path)
        except WorkflowInputStateError:
            raise
        except OSError as exc:
            raise WorkflowInputStateError(
                f"Workflow Input recovery rollback failed: {exc}"
            ) from exc

    def save_workflow_values(
        self,
        workflow_id: str,
        values: Mapping[str, Any],
        *,
        coerce: bool,
    ) -> WorkflowInputState:
        current = self.load_existing()
        schema = self._resolve_schema(workflow_id)
        normalized = self._normalize(
            schema, values, coerce=coerce, fill_defaults=True
        )
        workflows = current.copy_workflows()
        workflows[workflow_id] = normalized
        updated = WorkflowInputState(
            schema_version=WORKFLOW_INPUT_STATE_SCHEMA_VERSION,
            workflows=workflows,
        )
        self.save_state(updated)
        return updated

    def save_state(self, state: WorkflowInputState) -> None:
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
