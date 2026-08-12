"""Atomic per-Task workflow configuration/runtime UI state."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .schemas import WorkflowTaskSchema, WorkflowSchemaError, normalize_task_values

WORKFLOW_TASK_STATE_SCHEMA_VERSION = 1


class WorkflowTaskStateError(RuntimeError):
    pass


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool, float)):
        return value
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    raise WorkflowTaskStateError(f"Unsupported workflow Task state value type: {type(value).__name__}.")


class WorkflowTaskStateStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"schema_version": WORKFLOW_TASK_STATE_SCHEMA_VERSION, "tasks": {}}

    def _decode(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise WorkflowTaskStateError("Workflow Task state root must be a JSON object.")
        if payload.get("schema_version") != WORKFLOW_TASK_STATE_SCHEMA_VERSION:
            raise WorkflowTaskStateError("Unsupported Workflow Task state schema version.")
        tasks = payload.get("tasks")
        if not isinstance(tasks, dict):
            raise WorkflowTaskStateError("Workflow Task state tasks must be a JSON object.")
        clean: dict[str, dict[str, Any]] = {}
        for raw_slot, entry in tasks.items():
            try:
                slot = str(max(1, int(raw_slot)))
            except (TypeError, ValueError) as exc:
                raise WorkflowTaskStateError("Workflow Task state contains an invalid slot ID.") from exc
            if not isinstance(entry, dict):
                raise WorkflowTaskStateError(f"Workflow Task state entry must be an object: {slot}.")
            workflow_id = str(entry.get("workflow_id", "")).strip()
            if not workflow_id:
                raise WorkflowTaskStateError(f"Workflow Task state has no workflow_id: {slot}.")
            values = entry.get("values", {})
            metrics = entry.get("metrics", {})
            payloads = entry.get("payloads", [])
            step = str(entry.get("step", "") or "")
            if not isinstance(values, dict) or not isinstance(metrics, dict) or not isinstance(payloads, list):
                raise WorkflowTaskStateError(f"Workflow Task state entry is malformed: {slot}.")
            clean[slot] = {
                "workflow_id": workflow_id,
                "values": _json_safe(values),
                "metrics": _json_safe(metrics),
                "payloads": _json_safe(payloads),
                "step": step,
            }
        return {"schema_version": WORKFLOW_TASK_STATE_SCHEMA_VERSION, "tasks": clean}

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
            raise WorkflowTaskStateError(f"Workflow Task state could not be read: {exc}") from exc
        return self._decode(payload)

    def entry_for(
        self,
        workflow_id: str,
        slot_id: int,
        schema: WorkflowTaskSchema,
    ) -> dict[str, Any]:
        state = self.load_or_create()
        entry = state["tasks"].get(str(max(1, int(slot_id))))
        raw_values: dict[str, Any] = {}
        metrics: dict[str, Any] = {}
        payloads: list[Any] = []
        step = ""
        if entry and entry.get("workflow_id") == workflow_id:
            raw_values = dict(entry.get("values", {}))
            metrics = dict(entry.get("metrics", {}))
            payloads = list(entry.get("payloads", []))
            step = str(entry.get("step", "") or "")
        try:
            values = normalize_task_values(
                schema,
                raw_values,
                coerce=False,
                fill_defaults=True,
                enforce_required=False,
            )
        except WorkflowSchemaError as exc:
            raise WorkflowTaskStateError(str(exc)) from exc
        return {"values": values, "metrics": metrics, "payloads": payloads, "step": step}

    def save_task_values(
        self,
        workflow_id: str,
        slot_id: int,
        schema: WorkflowTaskSchema,
        values: Mapping[str, Any],
        *,
        coerce: bool,
        payloads: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        try:
            normalized = normalize_task_values(schema, values, coerce=coerce, fill_defaults=True)
        except WorkflowSchemaError as exc:
            raise WorkflowTaskStateError(str(exc)) from exc
        state = self.load_or_create()
        slot = str(max(1, int(slot_id)))
        previous = state["tasks"].get(slot, {})
        entry = {
            "workflow_id": workflow_id,
            "values": normalized,
            "metrics": dict(previous.get("metrics", {})) if previous.get("workflow_id") == workflow_id else {},
            "payloads": list(payloads) if payloads is not None else (
                list(previous.get("payloads", [])) if previous.get("workflow_id") == workflow_id else []
            ),
            "step": str(previous.get("step", "") or "") if previous.get("workflow_id") == workflow_id else "",
        }
        state["tasks"][slot] = _json_safe(entry)
        self.save_state(state)
        return dict(entry)

    def update_runtime(
        self,
        workflow_id: str,
        slot_id: int,
        *,
        step: str | None = None,
        metric_key: str | None = None,
        metric_value: Any = None,
    ) -> None:
        state = self.load_or_create()
        slot = str(max(1, int(slot_id)))
        entry = state["tasks"].get(slot)
        if not entry or entry.get("workflow_id") != workflow_id:
            entry = {"workflow_id": workflow_id, "values": {}, "metrics": {}, "payloads": [], "step": ""}
        if step is not None:
            entry["step"] = str(step)
        if metric_key is not None:
            entry.setdefault("metrics", {})[str(metric_key)] = _json_safe(metric_value)
        state["tasks"][slot] = entry
        self.save_state(state)

    def remove_task(self, slot_id: int) -> None:
        state = self.load_or_create()
        state["tasks"].pop(str(max(1, int(slot_id))), None)
        self.save_state(state)

    def clear_all(self) -> None:
        self.save_state(self._empty())

    def save_state(self, state: dict[str, Any]) -> None:
        clean = self._decode(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(clean, handle, indent=2, sort_keys=True, ensure_ascii=False)
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
