"""Crash-safe local task runtime store for VibraPilot production task processing.

This module owns only local task/checkpoint/result persistence.  It has no browser,
network, licensing, selector or UI responsibilities.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
RECOVERABLE_STATUSES = {
    "Ready", "Running", "Paused", "Stopped", "Interrupted", "Failed",
    "Login/Test Mode Required", "Test Send Limit Reached", "Manual Review Required",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TaskRuntimeStore:
    """SQLite-backed task state/result ledger safe for multiple worker threads."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._schema_lock = threading.Lock()
        self.recovery_warning = ""
        try:
            self._ensure_schema()
        except sqlite3.DatabaseError as exc:
            if not self._is_corruption_error(exc):
                raise
            self._quarantine_corrupt_store(exc)
            self._ensure_schema()

    @staticmethod
    def _is_corruption_error(exc: BaseException) -> bool:
        message = str(exc).lower()
        return any(
            marker in message
            for marker in ("not a database", "database disk image is malformed", "malformed database")
        )

    def _quarantine_corrupt_store(self, exc: BaseException) -> None:
        if not self.path.exists():
            raise exc
        token = uuid.uuid4().hex
        backup = self.path.with_name(f"{self.path.name}.corrupt-{token}")
        self.path.replace(backup)
        for suffix in ("-wal", "-shm"):
            companion = Path(str(self.path) + suffix)
            if companion.exists():
                companion.replace(Path(str(backup) + suffix))
        self.recovery_warning = (
            f"Corrupt task runtime store was quarantined as {backup.name}; "
            "a clean runtime store was created."
        )
        logging.error("%s Original error: %s", self.recovery_warning, exc)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._schema_lock:
            with self._connection() as conn:
                conn.executescript(
                    """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    slot_id INTEGER NOT NULL,
                    target_url TEXT NOT NULL DEFAULT '',
                    source_file TEXT NOT NULL DEFAULT '',
                    source_fingerprint TEXT NOT NULL DEFAULT '',
                    current_index INTEGER NOT NULL DEFAULT 0,
                    total INTEGER NOT NULL DEFAULT 0,
                    success_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    send_limit_used INTEGER NOT NULL DEFAULT 0,
                    task_status TEXT NOT NULL DEFAULT 'Ready',
                    manual_review_required INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_runs_slot_status
                    ON runs(slot_id, task_status, updated_at);

                CREATE TABLE IF NOT EXISTS items (
                    run_id TEXT NOT NULL,
                    item_index INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    name TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(run_id, item_index),
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS results (
                    run_id TEXT NOT NULL,
                    item_index INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    slot_id INTEGER NOT NULL,
                    email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    target_url TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(run_id, item_index),
                    FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_results_slot_status
                    ON results(slot_id, status, timestamp);
                    """
                )

    @staticmethod
    def new_run_id() -> str:
        return uuid.uuid4().hex

    def start_run(
        self,
        *,
        slot_id: int,
        target_url: str,
        source_file: str,
        source_fingerprint: str,
        items: Iterable[Any],
        created_at: str,
        run_id: str | None = None,
    ) -> str:
        run_id = run_id or self.new_run_id()
        item_rows = list(items)
        with self._connection() as conn:
            conn.execute(
                "UPDATE runs SET task_status='Discarded', updated_at=? "
                "WHERE slot_id=? AND completed_at IS NULL AND task_status!='Discarded'",
                (created_at, int(slot_id)),
            )
            conn.execute(
                """INSERT INTO runs(
                    run_id,schema_version,slot_id,target_url,source_file,source_fingerprint,
                    current_index,total,success_count,failed_count,send_limit_used,task_status,
                    manual_review_required,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id, SCHEMA_VERSION, int(slot_id), target_url, source_file,
                    source_fingerprint, 0, len(item_rows), 0, 0, 0, "Ready", 0,
                    created_at, created_at,
                ),
            )
            conn.executemany(
                """INSERT INTO items(
                    run_id,item_index,email,name,status,attempts,message,result
                ) VALUES(?,?,?,?,?,?,?,?)""",
                [
                    (
                        run_id, index, str(getattr(item, "email", "")),
                        str(getattr(item, "name", "")), str(getattr(item, "status", "pending")),
                        int(getattr(item, "attempts", 0)), str(getattr(item, "message", "")),
                        str(getattr(item, "result", "")),
                    )
                    for index, item in enumerate(item_rows)
                ],
            )
        return run_id

    def save_progress(
        self,
        *,
        run_id: str,
        current_index: int,
        total: int,
        success_count: int,
        failed_count: int,
        send_limit_used: int,
        task_status: str,
        manual_review_required: bool,
        updated_at: str,
        target_url: str | None = None,
    ) -> None:
        if not run_id:
            return
        with self._connection() as conn:
            if target_url is None:
                conn.execute(
                    """UPDATE runs SET current_index=?,total=?,success_count=?,failed_count=?,
                       send_limit_used=?,task_status=?,manual_review_required=?,updated_at=?
                       WHERE run_id=?""",
                    (
                        max(0, int(current_index)), max(0, int(total)),
                        max(0, int(success_count)), max(0, int(failed_count)),
                        max(0, int(send_limit_used)), str(task_status),
                        1 if manual_review_required else 0, updated_at, run_id,
                    ),
                )
            else:
                conn.execute(
                    """UPDATE runs SET current_index=?,total=?,success_count=?,failed_count=?,
                       send_limit_used=?,task_status=?,manual_review_required=?,updated_at=?,target_url=?
                       WHERE run_id=?""",
                    (
                        max(0, int(current_index)), max(0, int(total)),
                        max(0, int(success_count)), max(0, int(failed_count)),
                        max(0, int(send_limit_used)), str(task_status),
                        1 if manual_review_required else 0, updated_at, str(target_url), run_id,
                    ),
                )

    def save_item(self, run_id: str, item_index: int, item: Any) -> None:
        if not run_id:
            return
        with self._connection() as conn:
            conn.execute(
                """UPDATE items SET email=?,name=?,status=?,attempts=?,message=?,result=?
                   WHERE run_id=? AND item_index=?""",
                (
                    str(getattr(item, "email", "")), str(getattr(item, "name", "")),
                    str(getattr(item, "status", "pending")), int(getattr(item, "attempts", 0)),
                    str(getattr(item, "message", "")), str(getattr(item, "result", "")),
                    run_id, int(item_index),
                ),
            )

    def upsert_result(self, run_id: str, item_index: int, row: dict[str, Any]) -> None:
        if not run_id:
            return
        with self._connection() as conn:
            conn.execute(
                """INSERT INTO results(
                    run_id,item_index,timestamp,slot_id,email,status,message,attempts,target_url,result
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id,item_index) DO UPDATE SET
                    timestamp=excluded.timestamp,slot_id=excluded.slot_id,email=excluded.email,
                    status=excluded.status,message=excluded.message,attempts=excluded.attempts,
                    target_url=excluded.target_url,result=excluded.result""",
                (
                    run_id, int(item_index), str(row.get("timestamp", "")),
                    int(row.get("slot_id", 0)), str(row.get("email", "")),
                    str(row.get("status", "")), str(row.get("message", "")),
                    int(row.get("attempts", 0)), str(row.get("target_url", "")),
                    str(row.get("result", "")),
                ),
            )

    def mark_completed(self, run_id: str, status: str, timestamp: str) -> None:
        if not run_id:
            return
        completed = timestamp if status == "Completed" else None
        with self._connection() as conn:
            conn.execute(
                "UPDATE runs SET task_status=?,updated_at=?,completed_at=? WHERE run_id=?",
                (status, timestamp, completed, run_id),
            )

    def discard_run(self, run_id: str, timestamp: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "UPDATE runs SET task_status='Discarded',manual_review_required=0,updated_at=? WHERE run_id=?",
                (timestamp, run_id),
            )

    def recoverable_runs(self) -> list[dict[str, Any]]:
        placeholders = ",".join("?" for _ in RECOVERABLE_STATUSES)
        query = (
            "SELECT * FROM runs WHERE schema_version=? AND completed_at IS NULL AND task_status IN ("
            + placeholders
            + ") ORDER BY updated_at DESC"
        )
        with self._connection() as conn:
            rows = conn.execute(
                query, (SCHEMA_VERSION, *tuple(sorted(RECOVERABLE_STATUSES)))
            ).fetchall()
            return [dict(row) for row in rows]

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            run = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if run is None or int(run["schema_version"]) != SCHEMA_VERSION:
                return None
            items = conn.execute(
                "SELECT * FROM items WHERE run_id=? ORDER BY item_index", (run_id,)
            ).fetchall()
        data = dict(run)
        data["items"] = [dict(row) for row in items]
        return data

    def skip_current_manual_review(self, run_id: str, timestamp: str) -> None:
        """Advance an ambiguous current item only after explicit operator review/skip."""
        data = self.load_run(run_id)
        if not data:
            return
        index = int(data.get("current_index", 0))
        items = data.get("items", [])
        if index < 0 or index >= len(items):
            return
        item = dict(items[index])
        message = str(item.get("message", "")).strip()
        suffix = "Manual review completed; recipient skipped without automatic retry."
        item["message"] = f"{message} {suffix}".strip()
        item["status"] = "interrupted"
        with self._connection() as conn:
            conn.execute(
                "UPDATE items SET status=?,message=? WHERE run_id=? AND item_index=?",
                (item["status"], item["message"], run_id, index),
            )
            conn.execute(
                "UPDATE runs SET current_index=?,manual_review_required=0,task_status='Stopped',updated_at=? WHERE run_id=?",
                (index + 1, timestamp, run_id),
            )
            conn.execute(
                """INSERT INTO results(run_id,item_index,timestamp,slot_id,email,status,message,attempts,target_url,result)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(run_id,item_index) DO UPDATE SET timestamp=excluded.timestamp,status=excluded.status,
                   message=excluded.message,attempts=excluded.attempts,result=excluded.result""",
                (
                    run_id, index, timestamp, int(data.get("slot_id", 0)),
                    str(item.get("email", "")), "interrupted", item["message"],
                    int(item.get("attempts", 0)), str(data.get("target_url", "")),
                    str(item.get("result", "")),
                ),
            )

    def results(
        self,
        *,
        slot_id: int | None = None,
        status: str | None = None,
        search: str = "",
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if slot_id is not None:
            clauses.append("slot_id=?")
            params.append(int(slot_id))
        if status and status != "All":
            clauses.append("status=?")
            params.append(status)
        if search:
            needle = f"%{search.lower()}%"
            clauses.append(
                "(lower(email) LIKE ? OR lower(status) LIKE ? OR lower(message) LIKE ? "
                "OR lower(target_url) LIKE ? OR lower(result) LIKE ?)"
            )
            params.extend([needle] * 5)
        sql = "SELECT timestamp,slot_id,email,status,message,attempts,target_url,result,run_id,item_index FROM results"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY timestamp DESC, slot_id DESC, item_index DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(max(0, int(limit)))
        with self._connection() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def result_slot_ids(self) -> list[int]:
        with self._connection() as conn:
            rows = conn.execute("SELECT DISTINCT slot_id FROM results ORDER BY slot_id").fetchall()
        return [int(row[0]) for row in rows]

    def clear_results(self) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM results")

    def checkpoint(self) -> None:
        """Checkpoint the local WAL at an explicit sequential batch boundary."""
        with self._connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchall()

    def close(self) -> None:
        """Compatibility hook; connections are intentionally short-lived per operation."""
        return None
