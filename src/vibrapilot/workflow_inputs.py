"""Workflow-specific input metadata for VibraPilot.

This module deliberately contains form metadata only. It does not own browser,
Playwright, task-worker, selector, persistence, or licensing behavior. Existing
settings keys remain the source of truth so values saved by earlier releases are
preserved when their UI ownership moves from App Settings to Workflow Inputs.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowInputField:
    """One existing settings-backed value exposed by the Workflow Inputs page."""

    key: str
    label: str
    placeholder: str = ""
    help_text: str = ""


WORKFLOW_INPUT_FIELDS: tuple[WorkflowInputField, ...] = (
    WorkflowInputField(
        key="default_full_name",
        label="Default Full Name",
        help_text="Workflow-specific full-name value stored under the existing default_full_name setting key.",
    ),
    WorkflowInputField(
        key="default_number",
        label="Default Number",
        help_text="Workflow-specific number value stored under the existing default_number setting key.",
    ),
    WorkflowInputField(
        key="fallback_name",
        label="Fallback Name",
        help_text="Workflow-specific fallback name stored under the existing fallback_name setting key.",
    ),
    WorkflowInputField(
        key="update_click_count",
        label="Update Click Count",
        help_text="Preserved workflow value stored under the existing update_click_count setting key.",
    ),
)

WORKFLOW_INPUT_KEYS: tuple[str, ...] = tuple(field.key for field in WORKFLOW_INPUT_FIELDS)
