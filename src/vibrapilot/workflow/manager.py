"""Read-only built-in workflow manager.

The manager resolves source-controlled workflow metadata only. PR-04 exposes the
Share Invite manifest through the explicit built-in factory while retaining no
active-workflow persistence, switching, restart, UI, task, or browser side effects.
"""
from __future__ import annotations

from .contracts import WorkflowManifest
from .registry import WorkflowRegistry, create_builtin_registry


class WorkflowManager:
    """Minimal facade over the built-in workflow registry."""

    def __init__(self, registry: WorkflowRegistry | None = None) -> None:
        self._registry = registry if registry is not None else WorkflowRegistry()

    @property
    def registry(self) -> WorkflowRegistry:
        return self._registry

    @classmethod
    def with_builtin_workflows(cls) -> "WorkflowManager":
        """Create a manager exposing only source-controlled built-in workflows."""
        return cls(create_builtin_registry())

    def list_workflows(self) -> tuple[WorkflowManifest, ...]:
        return self._registry.list_workflows()

    def get_workflow(self, workflow_id: str) -> WorkflowManifest | None:
        return self._registry.get(workflow_id)

    def require_workflow(self, workflow_id: str) -> WorkflowManifest:
        return self._registry.require(workflow_id)
