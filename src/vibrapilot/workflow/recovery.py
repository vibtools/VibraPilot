"""Crash-safe explicit workflow recovery transaction support for PR-10.

This module stages only paths supplied explicitly by the application. It does
not discover browser profiles, reports, logs, license state, Workflow Inputs,
or arbitrary AppData content.
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .contracts import WorkflowRecoveryError, WorkflowStateError
from .state import WorkflowStateStore

WORKFLOW_RECOVERY_TRANSACTION_SCHEMA_VERSION = 1
RECOVERY_PREPARED = "PREPARED"
RECOVERY_COMMITTED = "COMMITTED"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    data = json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


@dataclass(frozen=True, slots=True)
class WorkflowRecoveryBackupEntry:
    relative_path: str
    existed: bool


class WorkflowRecoveryTransaction:
    """Rollback staging for explicit recovery from unavailable workflow state."""

    def __init__(
        self,
        *,
        data_root: Path,
        transaction_root: Path,
        target_workflow_id: str,
        transaction_id: str | None = None,
    ) -> None:
        self.data_root = Path(data_root).resolve()
        self.transaction_root = Path(transaction_root)
        self.transaction_id = transaction_id or uuid.uuid4().hex
        self.path = self.transaction_root / self.transaction_id
        self.backup_root = self.path / "backup"
        self.manifest_path = self.path / "transaction.json"
        self.target_workflow_id = str(target_workflow_id).strip()
        self.entries: list[WorkflowRecoveryBackupEntry] = []
        if not self.target_workflow_id:
            raise ValueError("target_workflow_id must not be empty")

    def _relative(self, path: Path) -> Path:
        resolved = Path(path).resolve()
        try:
            return resolved.relative_to(self.data_root)
        except ValueError as exc:
            raise WorkflowRecoveryError(
                f"workflow recovery path escapes AppData boundary: {resolved}"
            ) from exc

    def _manifest_payload(self, status: str) -> dict[str, Any]:
        return {
            "schema_version": WORKFLOW_RECOVERY_TRANSACTION_SCHEMA_VERSION,
            "transaction_id": self.transaction_id,
            "status": status,
            "target_workflow_id": self.target_workflow_id,
            "created_at": _now_iso(),
            "entries": [
                {"relative_path": item.relative_path, "existed": item.existed}
                for item in self.entries
            ],
        }

    def prepare(self, paths: Iterable[Path]) -> None:
        if self.path.exists():
            raise WorkflowRecoveryError("workflow recovery transaction already exists")
        self.backup_root.mkdir(parents=True, exist_ok=False)
        entries: list[WorkflowRecoveryBackupEntry] = []
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
                entries.append(WorkflowRecoveryBackupEntry(key, existed))
                if existed:
                    destination = self.backup_root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
            self.entries = entries
            _atomic_write_json(self.manifest_path, self._manifest_payload(RECOVERY_PREPARED))
        except BaseException:
            shutil.rmtree(self.path, ignore_errors=True)
            raise

    def mark_committed(self) -> None:
        if not self.manifest_path.is_file():
            raise WorkflowRecoveryError("workflow recovery transaction is not prepared")
        _atomic_write_json(self.manifest_path, self._manifest_payload(RECOVERY_COMMITTED))

    def rollback(self) -> None:
        for entry in self.entries:
            destination = self.data_root / Path(entry.relative_path)
            backup = self.backup_root / Path(entry.relative_path)
            if entry.existed:
                if not backup.is_file():
                    raise WorkflowRecoveryError(
                        f"workflow recovery rollback backup is missing: {entry.relative_path}"
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name(
                    f".{destination.name}.{uuid.uuid4().hex}.restore"
                )
                try:
                    shutil.copy2(backup, temporary)
                    os.replace(temporary, destination)
                finally:
                    if temporary.exists():
                        try:
                            temporary.unlink()
                        except OSError:
                            pass
            elif destination.exists():
                destination.unlink()
        self.cleanup()

    def cleanup(self) -> None:
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=False)

    @classmethod
    def recover_all(
        cls,
        *,
        data_root: Path,
        transaction_root: Path,
        state_store: WorkflowStateStore,
    ) -> list[str]:
        """Resolve stale recovery transactions without guessing ambiguous state."""
        root = Path(transaction_root)
        if not root.exists():
            return []
        actions: list[str] = []
        for directory in sorted(path for path in root.iterdir() if path.is_dir()):
            manifest_path = directory / "transaction.json"
            if not manifest_path.is_file():
                raise WorkflowRecoveryError(
                    f"workflow recovery transaction manifest is missing: {directory.name}"
                )
            try:
                raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise WorkflowRecoveryError(
                    f"workflow recovery transaction manifest is invalid: {directory.name}: {exc}"
                ) from exc
            if int(raw.get("schema_version", 0)) != WORKFLOW_RECOVERY_TRANSACTION_SCHEMA_VERSION:
                raise WorkflowRecoveryError(
                    f"unsupported workflow recovery transaction schema: {directory.name}"
                )
            status = str(raw.get("status", "")).strip()
            if status not in {RECOVERY_PREPARED, RECOVERY_COMMITTED}:
                raise WorkflowRecoveryError(
                    f"workflow recovery transaction status is invalid: {directory.name}"
                )
            target = str(raw.get("target_workflow_id", "")).strip()
            entries_raw = raw.get("entries")
            if not target or not isinstance(entries_raw, list):
                raise WorkflowRecoveryError(
                    f"workflow recovery transaction is structurally invalid: {directory.name}"
                )
            transaction = cls(
                data_root=data_root,
                transaction_root=root,
                target_workflow_id=target,
                transaction_id=directory.name,
            )
            transaction.entries = [
                WorkflowRecoveryBackupEntry(
                    str(item.get("relative_path", "")), bool(item.get("existed", False))
                )
                for item in entries_raw
                if isinstance(item, dict) and str(item.get("relative_path", ""))
            ]
            if len(transaction.entries) != len(entries_raw):
                raise WorkflowRecoveryError(
                    f"workflow recovery transaction entries are invalid: {directory.name}"
                )

            if not state_store.path.is_file():
                if status == RECOVERY_COMMITTED:
                    raise WorkflowRecoveryError(
                        f"committed workflow recovery has no canonical workflow state: {directory.name}"
                    )
                transaction.rollback()
                actions.append(f"rolled back prepared recovery {directory.name}")
                continue

            try:
                current = state_store.load_existing()
            except WorkflowStateError as exc:
                raise WorkflowRecoveryError(
                    f"workflow recovery cannot determine canonical state for {directory.name}: {exc}"
                ) from exc
            if current.active_workflow_id != transaction.target_workflow_id:
                raise WorkflowRecoveryError(
                    f"ambiguous workflow recovery transaction {directory.name}: active workflow "
                    f"{current.active_workflow_id!r} does not match target "
                    f"{transaction.target_workflow_id!r}"
                )
            transaction.cleanup()
            actions.append(f"cleaned committed recovery {directory.name}")

        try:
            root.rmdir()
        except OSError:
            pass
        return actions
