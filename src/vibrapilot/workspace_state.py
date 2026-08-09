"""Crash-safe workspace metadata persistence for VibraPilot.

This module owns only lightweight application-workspace metadata. Task recipient
rows, processing progress/results, browser profiles, licensing state and secrets
remain owned by their existing subsystems.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any


WORKSPACE_STATE_SCHEMA_VERSION = 1


class WorkspaceStateStore:
    """Atomic JSON workspace metadata store with safe corruption fallback."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.warning = ""

    def _quarantine(self, reason: str) -> None:
        if not self.path.exists():
            self.warning = reason
            return
        backup = self.path.with_name(
            f"{self.path.name}.corrupt-{uuid.uuid4().hex}"
        )
        try:
            self.path.replace(backup)
            self.warning = f"{reason} Quarantined as {backup.name}."
        except OSError:
            self.warning = reason

    @staticmethod
    def _normalize_task(entry: Any) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None
        try:
            slot_id = int(entry.get("slot_id", 0))
        except (TypeError, ValueError):
            return None
        if slot_id <= 0:
            return None
        return {
            "slot_id": slot_id,
            "run_id": str(entry.get("run_id", "") or ""),
            "target_url": str(entry.get("target_url", "") or ""),
        }

    @staticmethod
    def _normalize_window(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            value = {}

        def integer(name: str, default: int) -> int:
            try:
                return int(value.get(name, default))
            except (TypeError, ValueError):
                return default

        return {
            "x": integer("x", 0),
            "y": integer("y", 0),
            "width": max(1, integer("width", 1)),
            "height": max(1, integer("height", 1)),
            "maximized": bool(value.get("maximized", False)),
        }

    def load(self) -> dict[str, Any] | None:
        """Return normalized workspace metadata, or ``None`` for safe fallback."""
        self.warning = ""
        if not self.path.exists():
            return None
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            self._quarantine(f"Workspace state could not be read: {exc}.")
            return None
        if not isinstance(raw, dict):
            self._quarantine("Workspace state root was not a JSON object.")
            return None
        try:
            schema_version = int(raw.get("schema_version", 0))
        except (TypeError, ValueError):
            schema_version = 0
        if schema_version != WORKSPACE_STATE_SCHEMA_VERSION:
            self._quarantine(
                f"Unsupported workspace state schema {schema_version}; expected "
                f"{WORKSPACE_STATE_SCHEMA_VERSION}."
            )
            return None

        tasks: list[dict[str, Any]] = []
        seen_slots: set[int] = set()
        raw_tasks = raw.get("active_tasks", [])
        if isinstance(raw_tasks, list):
            for item in raw_tasks:
                normalized = self._normalize_task(item)
                if normalized is None:
                    continue
                slot_id = int(normalized["slot_id"])
                if slot_id in seen_slots:
                    continue
                seen_slots.add(slot_id)
                tasks.append(normalized)

        try:
            next_slot_id = max(1, int(raw.get("next_slot_id", 1)))
        except (TypeError, ValueError):
            next_slot_id = 1

        return {
            "schema_version": WORKSPACE_STATE_SCHEMA_VERSION,
            "saved_at": str(raw.get("saved_at", "") or ""),
            "active_tasks": tasks,
            "next_slot_id": next_slot_id,
            "selected_page": str(raw.get("selected_page", "Dashboard") or "Dashboard"),
            "window": self._normalize_window(raw.get("window", {})),
        }

    def save(self, state: dict[str, Any]) -> None:
        """Atomically replace ``state.json`` with normalized metadata."""
        if not isinstance(state, dict):
            raise TypeError("Workspace state must be a dictionary.")
        payload = {
            "schema_version": WORKSPACE_STATE_SCHEMA_VERSION,
            "saved_at": str(state.get("saved_at", "") or ""),
            "active_tasks": [],
            "next_slot_id": max(1, int(state.get("next_slot_id", 1))),
            "selected_page": str(state.get("selected_page", "Dashboard") or "Dashboard"),
            "window": self._normalize_window(state.get("window", {})),
        }
        seen_slots: set[int] = set()
        for item in state.get("active_tasks", []):
            normalized = self._normalize_task(item)
            if normalized is None:
                continue
            slot_id = int(normalized["slot_id"])
            if slot_id in seen_slots:
                continue
            seen_slots.add(slot_id)
            payload["active_tasks"].append(normalized)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        data = json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
        try:
            with tmp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
