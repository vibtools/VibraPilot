"""Core contracts for VibraPilot workflow manifests and runtimes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Callable, Protocol, runtime_checkable

_WORKFLOW_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){0,3}$")
_ENTRYPOINT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


class WorkflowError(RuntimeError):
    """Base error for the workflow framework."""


class WorkflowManifestError(WorkflowError, ValueError):
    """Raised when source-controlled workflow metadata is invalid."""


class WorkflowRegistrationError(WorkflowError):
    """Raised when a workflow cannot be registered safely."""


class DuplicateWorkflowError(WorkflowRegistrationError):
    """Raised when a registry receives the same workflow ID more than once."""


class UnknownWorkflowError(WorkflowError, LookupError):
    """Raised when a requested workflow ID is not registered."""


class ActiveWorkflowRequiredError(WorkflowError):
    """Raised when execution is attempted without a configured active workflow."""


class WorkflowRuntimeResolutionError(WorkflowError):
    """Raised when a workflow runtime cannot be resolved safely."""


class WorkflowStateError(WorkflowError):
    """Raised when persistent active-workflow state cannot be used safely."""


class WorkflowStateCorruptError(WorkflowStateError):
    """Raised after corrupt/invalid workflow state is quarantined fail-closed."""


class WorkflowSwitchError(WorkflowError):
    """Raised when an atomic workflow switch cannot complete safely."""


class WorkflowSwitchBlockedError(WorkflowSwitchError):
    """Raised when workflow switching is blocked before destructive mutation."""


class WorkflowRecoveryError(WorkflowError):
    """Raised when explicit workflow recovery cannot complete safely."""


class WorkflowRecoveryBlockedError(WorkflowRecoveryError):
    """Raised when workflow recovery is blocked before destructive mutation."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise WorkflowManifestError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise WorkflowManifestError(f"{field_name} must not be empty")
    return normalized


def _relative_asset_path(value: str, field_name: str) -> str:
    normalized = _required_text(value, field_name)
    if "\\" in normalized:
        raise WorkflowManifestError(f"{field_name} must use forward-slash relative paths")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise WorkflowManifestError(f"{field_name} must be a safe relative path")
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class WorkflowManifest:
    """Validated metadata for one workflow."""

    workflow_id: str
    name: str
    description: str
    version: str
    logo: str
    entrypoint: str

    def __post_init__(self) -> None:
        workflow_id = _required_text(self.workflow_id, "workflow_id")
        if not _WORKFLOW_ID_RE.fullmatch(workflow_id):
            raise WorkflowManifestError(
                "workflow_id must be lowercase snake_case and start with a letter"
            )

        name = _required_text(self.name, "name")
        description = _required_text(self.description, "description")
        version = _required_text(self.version, "version")
        if not _VERSION_RE.fullmatch(version):
            raise WorkflowManifestError("version must contain 1 to 4 numeric dot-separated parts")

        logo = _relative_asset_path(self.logo, "logo")
        entrypoint = _required_text(self.entrypoint, "entrypoint")
        if not _ENTRYPOINT_RE.fullmatch(entrypoint):
            raise WorkflowManifestError(
                "entrypoint must be a source-controlled symbolic identifier, not an import path"
            )

        object.__setattr__(self, "workflow_id", workflow_id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "logo", logo)
        object.__setattr__(self, "entrypoint", entrypoint)


@runtime_checkable
class WorkflowRuntime(Protocol):
    """Minimum generic execution contract for one workflow runtime."""

    manifest: WorkflowManifest

    def session_ready(self, page: Any) -> bool:
        """Return whether the current browser page satisfies this workflow's session gate."""
        ...

    def ensure_session(self) -> None:
        """Fail closed unless the current browser session is ready for this workflow."""
        ...

    def execute_item(self, item: Any) -> str:
        """Execute one existing task item using this workflow."""
        ...

    def prepare_retry(self) -> None:
        """Restore deterministic workflow state before a safe pre-Send retry."""
        ...


WorkflowRuntimeFactory = Callable[..., WorkflowRuntime]
