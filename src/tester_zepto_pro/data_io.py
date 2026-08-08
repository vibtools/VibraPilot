"""Data import/export helpers for Tester Zepto Pro.

Behavior is preserved from the v1.0.6 TaskSlotFrame/App data paths:
TXT/CSV/XLSX/XLS input, optional case-insensitive e-mail deduplication,
formula-safe CSV/XLSX report export, and the same validation rules.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any

import pandas as pd

from .backend import EMAIL_RE, TaskItem, safe_spreadsheet_rows


def rows_from_df(df: pd.DataFrame) -> list[TaskItem]:
    lowered = {str(c).lower().strip(): c for c in df.columns}
    email_col = lowered.get("email") or lowered.get("mail") or df.columns[0]
    name_col = lowered.get("name") or lowered.get("full_name") or lowered.get("fullname")
    rows: list[TaskItem] = []
    for _, row in df.iterrows():
        email = str(row.get(email_col, "")).strip()
        name = str(row.get(name_col, "")).strip() if name_col else ""
        if email and EMAIL_RE.match(email):
            rows.append(TaskItem(email=email, name="" if name.lower() == "nan" else name))
    return rows


def parse_data(path: Path) -> list[TaskItem]:
    rows: list[TaskItem] = []
    suffix = path.suffix.lower()
    if suffix == ".txt":
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            email = line.strip().split(",")[0].strip()
            if email and EMAIL_RE.match(email):
                rows.append(TaskItem(email=email))
    elif suffix == ".csv":
        rows = rows_from_df(pd.read_csv(path))
    elif suffix in {".xlsx", ".xls"}:
        rows = rows_from_df(pd.read_excel(path))
    else:
        raise ValueError("Unsupported file type. Use TXT, CSV, XLSX, or XLS.")
    if not rows:
        raise ValueError("No valid email records were found.")
    return rows


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
