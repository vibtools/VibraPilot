"""Built-in workflow framework foundation for VibraPilot.

PR-03 exposes contracts, a deterministic registry, and a read-only manager. No
workflow is registered or activated here; the existing Share Invite automation
remains in its frozen v1.0.6.19 execution path until PR-04/PR-05.
"""
from .contracts import (
    DuplicateWorkflowError,
    UnknownWorkflowError,
    WorkflowError,
    WorkflowManifest,
    WorkflowManifestError,
    WorkflowRegistrationError,
)
from .manager import WorkflowManager
from .registry import WorkflowRegistry

__all__ = [
    "DuplicateWorkflowError",
    "UnknownWorkflowError",
    "WorkflowError",
    "WorkflowManager",
    "WorkflowManifest",
    "WorkflowManifestError",
    "WorkflowRegistrationError",
    "WorkflowRegistry",
]
