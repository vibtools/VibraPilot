"""Deterministic registry for source-controlled built-in VibraPilot workflows."""
from __future__ import annotations

from collections.abc import Iterable

from .contracts import (
    DuplicateWorkflowError,
    UnknownWorkflowError,
    WorkflowManifest,
    WorkflowRuntimeFactory,
)


class WorkflowRegistry:
    """In-memory registry with no discovery, filesystem scanning, or dynamic imports."""

    def __init__(self, manifests: Iterable[WorkflowManifest] = ()) -> None:
        self._manifests: dict[str, WorkflowManifest] = {}
        self.register_many(manifests)

    def register(self, manifest: WorkflowManifest) -> WorkflowManifest:
        if not isinstance(manifest, WorkflowManifest):
            raise TypeError("manifest must be a WorkflowManifest")
        if manifest.workflow_id in self._manifests:
            raise DuplicateWorkflowError(
                f"workflow_id already registered: {manifest.workflow_id}"
            )
        self._manifests[manifest.workflow_id] = manifest
        return manifest

    def register_many(self, manifests: Iterable[WorkflowManifest]) -> tuple[WorkflowManifest, ...]:
        pending = tuple(manifests)
        staged_ids = set(self._manifests)
        for manifest in pending:
            if not isinstance(manifest, WorkflowManifest):
                raise TypeError("all manifests must be WorkflowManifest instances")
            if manifest.workflow_id in staged_ids:
                raise DuplicateWorkflowError(
                    f"workflow_id already registered: {manifest.workflow_id}"
                )
            staged_ids.add(manifest.workflow_id)
        for manifest in pending:
            self._manifests[manifest.workflow_id] = manifest
        return pending

    def list_workflows(self) -> tuple[WorkflowManifest, ...]:
        return tuple(self._manifests[key] for key in sorted(self._manifests))

    def get(self, workflow_id: str) -> WorkflowManifest | None:
        return self._manifests.get(workflow_id)

    def require(self, workflow_id: str) -> WorkflowManifest:
        manifest = self.get(workflow_id)
        if manifest is None:
            raise UnknownWorkflowError(f"unknown workflow_id: {workflow_id}")
        return manifest

    def __contains__(self, workflow_id: object) -> bool:
        return isinstance(workflow_id, str) and workflow_id in self._manifests

    def __len__(self) -> int:
        return len(self._manifests)


def builtin_workflow_manifests() -> tuple[WorkflowManifest, ...]:
    """Return the deterministic, source-controlled built-in workflow set."""
    from .share_invite import SHARE_INVITE_MANIFEST

    return (SHARE_INVITE_MANIFEST,)


def create_builtin_registry() -> WorkflowRegistry:
    """Build a registry containing only VibraPilot's source-controlled workflows."""
    return WorkflowRegistry(builtin_workflow_manifests())


def builtin_workflow_runtime_factories() -> dict[str, WorkflowRuntimeFactory]:
    """Return the explicit source-controlled built-in runtime factory map.

    The map is intentionally authored in code. No manifest value, filesystem scan,
    Python entry-point discovery, or arbitrary import participates in resolution.
    """
    from .share_invite import ShareInviteWorkflow

    return {"share_invite": ShareInviteWorkflow}
