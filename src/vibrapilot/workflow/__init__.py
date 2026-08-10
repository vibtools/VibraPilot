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
    WorkflowStateCorruptError,
    WorkflowStateError,
    WorkflowSwitchBlockedError,
    WorkflowSwitchError,
)
from .manager import WorkflowManager
from .state import (
    DEFAULT_ACTIVE_WORKFLOW_ID,
    TRANSACTION_COMMITTED,
    TRANSACTION_PREPARED,
    WORKFLOW_STATE_SCHEMA_VERSION,
    WorkflowState,
    WorkflowStateStore,
    WorkflowSwitchTransaction,
)
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
    "WorkflowState",
    "WorkflowStateCorruptError",
    "WorkflowStateError",
    "WorkflowStateStore",
    "WorkflowSwitchBlockedError",
    "WorkflowSwitchError",
    "WorkflowSwitchTransaction",
    "WORKFLOW_STATE_SCHEMA_VERSION",
    "DEFAULT_ACTIVE_WORKFLOW_ID",
    "TRANSACTION_PREPARED",
    "TRANSACTION_COMMITTED",
    "builtin_workflow_manifests",
    "builtin_workflow_runtime_factories",
    "create_builtin_registry",
]
