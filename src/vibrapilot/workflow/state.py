"""Persistent active-workflow state and atomic switch transaction support."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .contracts import (
    WorkflowStateError,
    WorkflowStateCorruptError,
    WorkflowSwitchError,
    UnknownWorkflowError,
)
from .manager import WorkflowManager

WORKFLOW_STATE_SCHEMA_VERSION = 2
WORKFLOW_SWITCH_TRANSACTION_SCHEMA_VERSION = 1
DEFAULT_ACTIVE_WORKFLOW_ID: None = None
LEGACY_EXTERNALIZED_WORKFLOW_IDS = frozenset({"share_invite"})
TRANSACTION_PREPARED = "PREPARED"
TRANSACTION_COMMITTED = "COMMITTED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    data = json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


@dataclass(frozen=True, slots=True)
class WorkflowState:
    schema_version: int
    active_workflow_id: str | None
    revision: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": int(self.schema_version),
            "active_workflow_id": self.active_workflow_id,
            "revision": int(self.revision),
            "updated_at": self.updated_at,
        }


class WorkflowStateStore:
    """Fail-closed atomic state with a legitimate zero-active-workflow state.

    v1 state containing the formerly built-in ``share_invite`` identity is migrated
    without quarantine even when that external package is not installed yet.
    """

    def __init__(
        self,
        path: Path,
        *,
        manager: WorkflowManager | None = None,
        default_workflow_id: str | None = DEFAULT_ACTIVE_WORKFLOW_ID,
    ) -> None:
        self.path = Path(path)
        self.manager = manager or WorkflowManager.with_builtin_workflows()
        self.default_workflow_id = (
            str(default_workflow_id).strip() if default_workflow_id is not None else None
        )

    def _validate_workflow_id(
        self, workflow_id: str, *, allow_unresolved_legacy: bool = False
    ) -> str:
        normalized = str(workflow_id).strip()
        if not normalized:
            raise WorkflowStateCorruptError("workflow state active_workflow_id is empty")
        try:
            self.manager.require_workflow(normalized)
        except UnknownWorkflowError as exc:
            if allow_unresolved_legacy and normalized in LEGACY_EXTERNALIZED_WORKFLOW_IDS:
                return normalized
            raise WorkflowStateCorruptError(
                f"workflow state references unknown workflow_id: {normalized}"
            ) from exc
        return normalized

    def _quarantine(self, reason: str) -> None:
        if not self.path.exists():
            raise WorkflowStateCorruptError(reason)
        backup = self.path.with_name(f"{self.path.name}.corrupt-{uuid.uuid4().hex}")
        try:
            os.replace(self.path, backup)
        except OSError as exc:
            raise WorkflowStateCorruptError(
                f"{reason}; workflow state could not be quarantined: {exc}"
            ) from exc
        raise WorkflowStateCorruptError(f"{reason}; quarantined as {backup.name}")

    def _has_quarantined_state(self) -> bool:
        pattern = f"{self.path.name}.corrupt-*"
        return any(self.path.parent.glob(pattern))

    def _parse(self, raw: Any) -> tuple[WorkflowState, bool]:
        if not isinstance(raw, dict):
            raise WorkflowStateCorruptError("workflow state root is not a JSON object")
        try:
            schema_version = int(raw.get("schema_version", 0))
        except (TypeError, ValueError) as exc:
            raise WorkflowStateCorruptError("workflow state schema_version is invalid") from exc
        if schema_version not in {1, WORKFLOW_STATE_SCHEMA_VERSION}:
            raise WorkflowStateCorruptError(
                f"unsupported workflow state schema {schema_version}; expected 1 or {WORKFLOW_STATE_SCHEMA_VERSION}"
            )
        migrated = schema_version == 1
        raw_workflow_id = raw.get("active_workflow_id")
        if schema_version == WORKFLOW_STATE_SCHEMA_VERSION and raw_workflow_id is None:
            workflow_id: str | None = None
        else:
            workflow_id = self._validate_workflow_id(
                raw_workflow_id or "", allow_unresolved_legacy=True
            )
        try:
            revision = int(raw.get("revision", 0))
        except (TypeError, ValueError) as exc:
            raise WorkflowStateCorruptError("workflow state revision is invalid") from exc
        if revision < 1:
            raise WorkflowStateCorruptError("workflow state revision must be at least 1")
        updated_at = str(raw.get("updated_at", "") or "").strip()
        if not updated_at:
            raise WorkflowStateCorruptError("workflow state updated_at is missing")
        return (
            WorkflowState(
                schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
                active_workflow_id=workflow_id,
                revision=revision,
                updated_at=updated_at,
            ),
            migrated,
        )

    def load_existing(self) -> WorkflowState:
        """Load state; migrate schema v1 in place without losing its workflow identity."""
        if not self.path.exists():
            raise WorkflowStateError("workflow state file is missing")
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError) as exc:
            self._quarantine(f"workflow state could not be read: {exc}")
            raise AssertionError("unreachable")
        try:
            state, migrated = self._parse(raw)
        except WorkflowStateCorruptError as exc:
            self._quarantine(str(exc))
            raise AssertionError("unreachable")
        if migrated:
            _atomic_write_json(self.path, state.to_dict())
        return state

    def load_or_migrate(self) -> WorkflowState:
        """Load current state or create a legitimate zero-workflow state."""
        if self.path.exists():
            return self.load_existing()
        if self._has_quarantined_state():
            raise WorkflowStateCorruptError(
                "workflow state is absent but quarantined corrupt state exists; automatic recovery is blocked"
            )
        workflow_id: str | None = None
        if self.default_workflow_id:
            workflow_id = self._validate_workflow_id(
                self.default_workflow_id, allow_unresolved_legacy=True
            )
        state = WorkflowState(
            schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
            active_workflow_id=workflow_id,
            revision=1,
            updated_at=_now_iso(),
        )
        _atomic_write_json(self.path, state.to_dict())
        return state

    def recover_active_workflow(self, target_workflow_id: str) -> WorkflowState:
        """Explicitly create canonical state after user-confirmed recovery.

        A valid zero-workflow state is still canonical and must never be overwritten
        through the recovery path. First activation from ``None`` belongs to
        :meth:`commit_active_workflow`; recovery is reserved for unavailable or
        quarantined state. Invalid existing state is quarantined by ``load_existing``
        before the explicit recovery can proceed.
        """
        if self.path.exists():
            try:
                current = self.load_existing()
            except WorkflowStateError:
                if self.path.exists():
                    raise
            else:
                raise WorkflowStateError(
                    "workflow state recovery refused because valid canonical state already exists: "
                    f"{current.active_workflow_id}"
                )
        target = self._validate_workflow_id(target_workflow_id)
        state = WorkflowState(
            schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
            active_workflow_id=target,
            revision=1,
            updated_at=_now_iso(),
        )
        _atomic_write_json(self.path, state.to_dict())
        return state

    def commit_active_workflow(
        self,
        target_workflow_id: str,
        *,
        expected_current_workflow_id: str | None,
    ) -> WorkflowState:
        """Atomically commit a validated target, including first activation from None."""
        current = self.load_existing()
        expected = (
            str(expected_current_workflow_id).strip()
            if expected_current_workflow_id is not None
            else None
        )
        if current.active_workflow_id != expected:
            raise WorkflowSwitchError(
                "workflow state changed during switch transaction; commit aborted"
            )
        target = self._validate_workflow_id(target_workflow_id)
        state = WorkflowState(
            schema_version=WORKFLOW_STATE_SCHEMA_VERSION,
            active_workflow_id=target,
            revision=current.revision + 1,
            updated_at=_now_iso(),
        )
        _atomic_write_json(self.path, state.to_dict())
        return state


@dataclass(frozen=True, slots=True)
class WorkflowSwitchBackupEntry:
    relative_path: str
    existed: bool


class WorkflowSwitchTransaction:
    """Filesystem rollback staging for one workflow switch.

    The transaction stores only files explicitly supplied by the application.
    Browser profiles, exports, logs, licensing files, and arbitrary AppData files
    are never discovered or copied implicitly.
    """

    def __init__(
        self,
        *,
        data_root: Path,
        transaction_root: Path,
        old_workflow_id: str,
        target_workflow_id: str,
        transaction_id: str | None = None,
    ) -> None:
        self.data_root = Path(data_root).resolve()
        self.transaction_root = Path(transaction_root)
        self.transaction_id = transaction_id or uuid.uuid4().hex
        self.path = self.transaction_root / self.transaction_id
        self.backup_root = self.path / "backup"
        self.manifest_path = self.path / "transaction.json"
        self.old_workflow_id = str(old_workflow_id).strip()
        self.target_workflow_id = str(target_workflow_id).strip()
        self.entries: list[WorkflowSwitchBackupEntry] = []
        if not self.old_workflow_id or not self.target_workflow_id:
            raise ValueError("workflow IDs must not be empty")

    def _relative(self, path: Path) -> Path:
        resolved = Path(path).resolve()
        try:
            return resolved.relative_to(self.data_root)
        except ValueError as exc:
            raise WorkflowSwitchError(
                f"workflow switch path escapes AppData boundary: {resolved}"
            ) from exc

    def _manifest_payload(self, status: str) -> dict[str, Any]:
        return {
            "schema_version": WORKFLOW_SWITCH_TRANSACTION_SCHEMA_VERSION,
            "transaction_id": self.transaction_id,
            "status": status,
            "old_workflow_id": self.old_workflow_id,
            "target_workflow_id": self.target_workflow_id,
            "created_at": _now_iso(),
            "entries": [
                {"relative_path": entry.relative_path, "existed": entry.existed}
                for entry in self.entries
            ],
        }

    def prepare(self, paths: Iterable[Path]) -> None:
        """Stage rollback copies and atomically mark the transaction PREPARED."""
        if self.path.exists():
            raise WorkflowSwitchError("workflow switch transaction already exists")
        self.backup_root.mkdir(parents=True, exist_ok=False)
        entries: list[WorkflowSwitchBackupEntry] = []
        seen: set[str] = set()
        try:
            for value in paths:
                relative = self._relative(Path(value))
                key = relative.as_posix()
                if key in seen:
                    continue
                seen.add(key)
                source = self.data_root / relative
                existed = source.is_file()
                entries.append(WorkflowSwitchBackupEntry(key, existed))
                if existed:
                    destination = self.backup_root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            self.entries = entries
            _atomic_write_json(self.manifest_path, self._manifest_payload(TRANSACTION_PREPARED))
        except BaseException:
            shutil.rmtree(self.path, ignore_errors=True)
            raise

    def mark_committed(self) -> None:
        if not self.manifest_path.is_file():
            raise WorkflowSwitchError("workflow switch transaction is not prepared")
        _atomic_write_json(self.manifest_path, self._manifest_payload(TRANSACTION_COMMITTED))

    def rollback(self) -> None:
        """Restore every staged path to its exact pre-transaction existence state."""
        for entry in self.entries:
            destination = self.data_root / Path(entry.relative_path)
            backup = self.backup_root / Path(entry.relative_path)
            if entry.existed:
                if not backup.is_file():
                    raise WorkflowSwitchError(
                        f"workflow switch rollback backup is missing: {entry.relative_path}"
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                tmp = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.restore")
                try:
                    shutil.copy2(backup, tmp)
                    os.replace(tmp, destination)
                finally:
                    if tmp.exists():
                        try:
                            tmp.unlink()
                        except OSError:
                            pass
            elif destination.exists():
                destination.unlink()
        self.cleanup()

    def cleanup(self) -> None:
        shutil.rmtree(self.path, ignore_errors=False) if self.path.exists() else None

    @classmethod
    def recover_all(
        cls,
        *,
        data_root: Path,
        transaction_root: Path,
        state_store: WorkflowStateStore,
    ) -> list[str]:
        """Recover stale PREPARED transactions and clean committed transactions."""
        root = Path(transaction_root)
        if not root.exists():
            return []
        actions: list[str] = []
        for directory in sorted(path for path in root.iterdir() if path.is_dir()):
            manifest_path = directory / "transaction.json"
            if not manifest_path.is_file():
                raise WorkflowSwitchError(
                    f"workflow switch transaction manifest is missing: {directory.name}"
                )
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise WorkflowSwitchError(
                    f"workflow switch transaction manifest is invalid: {directory.name}: {exc}"
                ) from exc
            if int(raw.get("schema_version", 0)) != WORKFLOW_SWITCH_TRANSACTION_SCHEMA_VERSION:
                raise WorkflowSwitchError(
                    f"unsupported workflow switch transaction schema: {directory.name}"
                )
            entries_raw = raw.get("entries")
            if not isinstance(entries_raw, list):
                raise WorkflowSwitchError(
                    f"workflow switch transaction entries are invalid: {directory.name}"
                )
            transaction = cls(
                data_root=data_root,
                transaction_root=root,
                old_workflow_id=str(raw.get("old_workflow_id", "")),
                target_workflow_id=str(raw.get("target_workflow_id", "")),
                transaction_id=directory.name,
            )
            transaction.entries = [
                WorkflowSwitchBackupEntry(
                    str(item.get("relative_path", "")), bool(item.get("existed", False))
                )
                for item in entries_raw
                if isinstance(item, dict) and str(item.get("relative_path", ""))
            ]
            try:
                current = state_store.load_existing()
            except WorkflowStateError:
                raise
            if current.active_workflow_id == transaction.target_workflow_id:
                transaction.cleanup()
                actions.append(f"cleaned committed transaction {directory.name}")
                continue
            if current.active_workflow_id == transaction.old_workflow_id:
                transaction.rollback()
                actions.append(f"rolled back prepared transaction {directory.name}")
                continue
            raise WorkflowSwitchError(
                f"ambiguous workflow switch transaction {directory.name}: active workflow "
                f"{current.active_workflow_id!r} matches neither old nor target"
            )
        try:
            root.rmdir()
        except OSError:
            pass
        return actions
