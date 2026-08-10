"""Built-in workflow framework for VibraPilot.

PR-04 adds the verified Share Invite workflow as the first deterministic built-in
workflow. Workflow activation, switching and active-workflow persistence remain
out of scope until later explicitly approved phases.
"""
from .contracts import (
    ActiveWorkflowRequiredError,
    DuplicateWorkflowError,
    UnknownWorkflowError,
    WorkflowError,
    WorkflowManifest,
    WorkflowManifestError,
    WorkflowRegistrationError,
    WorkflowRuntime,
    WorkflowRuntimeFactory,
    WorkflowRuntimeResolutionError,
)
from .manager import WorkflowManager
from .registry import (
    WorkflowRegistry,
    builtin_workflow_manifests,
    builtin_workflow_runtime_factories,
    create_builtin_registry,
)

__all__ = [
    "ActiveWorkflowRequiredError",
    "DuplicateWorkflowError",
    "UnknownWorkflowError",
    "WorkflowError",
    "WorkflowManager",
    "WorkflowManifest",
    "WorkflowManifestError",
    "WorkflowRegistrationError",
    "WorkflowRegistry",
    "WorkflowRuntime",
    "WorkflowRuntimeFactory",
    "WorkflowRuntimeResolutionError",
    "builtin_workflow_manifests",
    "builtin_workflow_runtime_factories",
    "create_builtin_registry",
]
