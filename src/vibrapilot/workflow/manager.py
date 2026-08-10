"""Read-only workflow manager foundation for PR-03.

The manager resolves registered built-in workflow metadata only. It deliberately
has no active-workflow persistence, switching, restart, UI, task, or browser side
effects in this phase.
"""
from __future__ import annotations

from .contracts import WorkflowManifest
from .registry import WorkflowRegistry


class WorkflowManager:
    """Minimal facade over the built-in workflow registry."""

    def __init__(self, registry: WorkflowRegistry | None = None) -> None:
        self._registry = registry if registry is not None else WorkflowRegistry()

    @property
    def registry(self) -> WorkflowRegistry:
        return self._registry

    def list_workflows(self) -> tuple[WorkflowManifest, ...]:
        return self._registry.list_workflows()

    def get_workflow(self, workflow_id: str) -> WorkflowManifest | None:
        return self._registry.get(workflow_id)

    def require_workflow(self, workflow_id: str) -> WorkflowManifest:
        return self._registry.require(workflow_id)
