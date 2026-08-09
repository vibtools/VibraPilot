"""Data import/export helpers for VibraPilot.

Behavior is preserved from the v1.0.6 TaskSlotFrame/App data paths:
TXT/CSV/XLSX/XLS input, optional case-insensitive e-mail deduplication,
formula-safe CSV/XLSX report export, and the same validation rules.

v1.0.6.5 adds import reconciliation metadata without changing accepted e-mail
validation semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Any

import pandas as pd

from .backend import EMAIL_RE, TaskItem, safe_spreadsheet_rows
from .task_runtime_store import file_sha256


@dataclass(frozen=True)
class ImportAudit:
    items: list[TaskItem]
    source_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    accepted_rows: int
    source_fingerprint: str


def _valid_task(email: str, name: str = "") -> TaskItem | None:
    email = str(email).strip()
    name = str(name).strip()
    if email and EMAIL_RE.match(email):
        return TaskItem(email=email, name="" if name.lower() == "nan" else name)
    return None


def rows_from_df(df: pd.DataFrame) -> list[TaskItem]:
    lowered = {str(c).lower().strip(): c for c in df.columns}
    email_col = lowered.get("email") or lowered.get("mail") or df.columns[0]
    name_col = lowered.get("name") or lowered.get("full_name") or lowered.get("fullname")
    rows: list[TaskItem] = []
    for _, row in df.iterrows():
        task = _valid_task(
            row.get(email_col, ""),
            row.get(name_col, "") if name_col else "",
        )
        if task is not None:
            rows.append(task)
    return rows


def parse_data(path: Path) -> list[TaskItem]:
    """Preserved baseline parser returning valid rows only."""
    return parse_data_with_audit(path, remove_duplicates=False).items


def parse_data_with_audit(path: Path, *, remove_duplicates: bool) -> ImportAudit:
    """Parse input while reporting exact source/invalid/duplicate reconciliation."""
    path = Path(path)
    suffix = path.suffix.lower()
    valid: list[TaskItem] = []
    source_rows = 0

    if suffix == ".txt":
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        source_rows = len(lines)
        for line in lines:
            email = line.strip().split(",")[0].strip()
            task = _valid_task(email)
            if task is not None:
                valid.append(task)
    elif suffix == ".csv":
        df = pd.read_csv(path)
        source_rows = len(df.index)
        valid = rows_from_df(df)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
        source_rows = len(df.index)
        valid = rows_from_df(df)
    else:
        raise ValueError("Unsupported file type. Use TXT, CSV, XLSX, or XLS.")

    if not valid:
        raise ValueError("No valid email records were found.")

    valid_rows = len(valid)
    invalid_rows = max(0, source_rows - valid_rows)
    unique = deduplicate_items(valid)
    duplicate_rows = valid_rows - len(unique)
    accepted = unique if remove_duplicates else valid

    return ImportAudit(
        items=accepted,
        source_rows=source_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        accepted_rows=len(accepted),
        source_fingerprint=file_sha256(path),
    )


def deduplicate_items(items: Iterable[TaskItem]) -> list[TaskItem]:
    seen: set[str] = set()
    unique: list[TaskItem] = []
    for item in items:
        key = item.email.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def export_report_csv(rows: list[dict[str, Any]], path: Path) -> None:
    pd.DataFrame(safe_spreadsheet_rows(rows)).to_csv(path, index=False)


def export_report_excel(rows: list[dict[str, Any]], path: Path) -> None:
    pd.DataFrame(safe_spreadsheet_rows(rows)).to_excel(path, index=False)
