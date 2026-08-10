"""Fail-closed manager for source-controlled built-in workflow execution.

PR-05 adds one in-memory active-workflow identity and runtime resolution gate.
It deliberately does not persist, switch, activate, restart, discover, or load
workflows dynamically; those responsibilities remain outside this phase.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import (
    ActiveWorkflowRequiredError,
    WorkflowManifest,
    WorkflowRuntime,
    WorkflowRuntimeFactory,
    WorkflowRuntimeResolutionError,
)
from .registry import (
    WorkflowRegistry,
    builtin_workflow_runtime_factories,
    create_builtin_registry,
)


class WorkflowManager:
    """Resolve one immutable in-memory active built-in workflow safely."""

    def __init__(
        self,
        registry: WorkflowRegistry | None = None,
        *,
        active_workflow_id: str | None = None,
        runtime_factories: Mapping[str, WorkflowRuntimeFactory] | None = None,
    ) -> None:
        self._registry = registry if registry is not None else WorkflowRegistry()
        normalized = "" if active_workflow_id is None else str(active_workflow_id).strip()
        self._active_workflow_id = normalized or None
        self._runtime_factories = dict(runtime_factories or {})

    @property
    def registry(self) -> WorkflowRegistry:
        return self._registry

    @property
    def active_workflow_id(self) -> str | None:
        """Return the run-scoped active workflow ID; no mutator exists in PR-05."""
        return self._active_workflow_id

    @classmethod
    def with_builtin_workflows(
        cls, *, active_workflow_id: str | None = None
    ) -> "WorkflowManager":
        """Create a manager exposing only source-controlled built-in workflows."""
        return cls(
            create_builtin_registry(),
            active_workflow_id=active_workflow_id,
            runtime_factories=builtin_workflow_runtime_factories(),
        )

    def list_workflows(self) -> tuple[WorkflowManifest, ...]:
        return self._registry.list_workflows()

    def get_workflow(self, workflow_id: str) -> WorkflowManifest | None:
        return self._registry.get(workflow_id)

    def require_workflow(self, workflow_id: str) -> WorkflowManifest:
        return self._registry.require(workflow_id)

    def require_active_workflow(self) -> WorkflowManifest:
        workflow_id = self._active_workflow_id
        if workflow_id is None:
            raise ActiveWorkflowRequiredError(
                "automation blocked: no active built-in workflow is configured"
            )
        return self.require_workflow(workflow_id)

    def resolve_active_runtime(self, *args: Any, **kwargs: Any) -> WorkflowRuntime:
        manifest = self.require_active_workflow()
        factory = self._runtime_factories.get(manifest.workflow_id)
        if factory is None:
            raise WorkflowRuntimeResolutionError(
                f"no source-controlled runtime is registered for workflow_id: {manifest.workflow_id}"
            )
        runtime = factory(*args, **kwargs)
        if not isinstance(runtime, WorkflowRuntime):
            raise WorkflowRuntimeResolutionError(
                f"runtime does not satisfy WorkflowRuntime for workflow_id: {manifest.workflow_id}"
            )
        runtime_manifest = getattr(runtime, "manifest", None)
        if runtime_manifest != manifest:
            raise WorkflowRuntimeResolutionError(
                f"runtime manifest mismatch for workflow_id: {manifest.workflow_id}"
            )
        return runtime
