"""Fail-closed manager for trusted installed workflow execution."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from .contracts import (
    ActiveWorkflowRequiredError,
    WorkflowManifest,
    WorkflowRuntime,
    WorkflowRuntimeFactory,
    WorkflowRuntimeResolutionError,
)
from .plugin_loader import (
    WorkflowPluginIssue,
    load_installed_workflows,
)
from .registry import (
    WorkflowRegistry,
    builtin_workflow_manifests,
    builtin_workflow_runtime_factories,
    create_builtin_registry,
)
from .schemas import (
    WorkflowFormSchema,
    WorkflowTaskSchema,
)

TaskItemLoader = Callable[[Path, Mapping[str, Any]], list[Mapping[str, Any]]]


class WorkflowManager:
    """Resolve one immutable active workflow from a validated unified catalog."""

    def __init__(
        self,
        registry: WorkflowRegistry | None = None,
        *,
        active_workflow_id: str | None = None,
        runtime_factories: Mapping[str, WorkflowRuntimeFactory] | None = None,
        input_schemas: Mapping[str, WorkflowFormSchema] | None = None,
        settings_schemas: Mapping[str, WorkflowFormSchema] | None = None,
        task_schemas: Mapping[str, WorkflowTaskSchema] | None = None,
        workflow_origins: Mapping[str, str] | None = None,
        workflow_roots: Mapping[str, Path] | None = None,
        task_item_loaders: Mapping[str, TaskItemLoader] | None = None,
        task_data_loaders: Mapping[str, Callable[..., Any]] | None = None,
        plugin_issues: tuple[WorkflowPluginIssue, ...] = (),
    ) -> None:
        self._registry = registry if registry is not None else WorkflowRegistry()
        normalized = "" if active_workflow_id is None else str(active_workflow_id).strip()
        self._active_workflow_id = normalized or None
        self._runtime_factories = dict(runtime_factories or {})
        self._input_schemas = dict(input_schemas or {})
        self._settings_schemas = dict(settings_schemas or {})
        self._task_schemas = dict(task_schemas or {})
        self._workflow_origins = dict(workflow_origins or {})
        self._workflow_roots = {key: Path(value) for key, value in dict(workflow_roots or {}).items()}
        self._task_item_loaders = dict(task_item_loaders or {})
        self._task_data_loaders = dict(task_data_loaders or {})
        self._plugin_issues = tuple(plugin_issues)

    @property
    def registry(self) -> WorkflowRegistry:
        return self._registry

    @property
    def active_workflow_id(self) -> str | None:
        return self._active_workflow_id

    @property
    def plugin_issues(self) -> tuple[WorkflowPluginIssue, ...]:
        return self._plugin_issues

    @classmethod
    def with_builtin_workflows(
        cls, *, active_workflow_id: str | None = None
    ) -> "WorkflowManager":
        """Compatibility constructor: v1.0.6.36 intentionally has zero built-ins."""
        return cls(
            create_builtin_registry(),
            active_workflow_id=active_workflow_id,
            runtime_factories=builtin_workflow_runtime_factories(),
        )

    @classmethod
    def with_available_workflows(
        cls,
        *,
        workflow_root: Path,
        active_workflow_id: str | None = None,
    ) -> "WorkflowManager":
        """Build the catalog from validated local plugins only."""
        manager = cls.with_builtin_workflows(active_workflow_id=active_workflow_id)
        reserved = {manifest.workflow_id for manifest in builtin_workflow_manifests()}
        plugins, issues = load_installed_workflows(
            workflow_root,
            reserved_workflow_ids=reserved,
        )
        registry = WorkflowRegistry(manager.list_workflows())
        factories = dict(manager._runtime_factories)
        inputs = dict(manager._input_schemas)
        settings = dict(manager._settings_schemas)
        tasks = dict(manager._task_schemas)
        origins = dict(manager._workflow_origins)
        roots = dict(manager._workflow_roots)
        loaders = dict(manager._task_item_loaders)
        data_loaders = dict(manager._task_data_loaders)
        for plugin in plugins:
            registry.register(plugin.manifest)
            workflow_id = plugin.manifest.workflow_id
            factories[workflow_id] = plugin.runtime_factory
            inputs[workflow_id] = plugin.input_schema
            settings[workflow_id] = plugin.settings_schema
            tasks[workflow_id] = plugin.task_schema
            origins[workflow_id] = "plugin"
            roots[workflow_id] = plugin.root
            if plugin.task_item_loader is not None:
                loaders[workflow_id] = plugin.task_item_loader
            if plugin.task_data_loader is not None:
                data_loaders[workflow_id] = plugin.task_data_loader
        return cls(
            registry,
            active_workflow_id=active_workflow_id,
            runtime_factories=factories,
            input_schemas=inputs,
            settings_schemas=settings,
            task_schemas=tasks,
            workflow_origins=origins,
            workflow_roots=roots,
            task_item_loaders=loaders,
            task_data_loaders=data_loaders,
            plugin_issues=issues,
        )

    def for_active_workflow(self, workflow_id: str | None) -> "WorkflowManager":
        """Clone the validated catalog with one run-scoped active identity."""
        return WorkflowManager(
            self._registry,
            active_workflow_id=workflow_id,
            runtime_factories=self._runtime_factories,
            input_schemas=self._input_schemas,
            settings_schemas=self._settings_schemas,
            task_schemas=self._task_schemas,
            workflow_origins=self._workflow_origins,
            workflow_roots=self._workflow_roots,
            task_item_loaders=self._task_item_loaders,
            task_data_loaders=self._task_data_loaders,
            plugin_issues=self._plugin_issues,
        )

    def list_workflows(self) -> tuple[WorkflowManifest, ...]:
        return self._registry.list_workflows()

    def get_workflow(self, workflow_id: str) -> WorkflowManifest | None:
        return self._registry.get(workflow_id)

    def require_workflow(self, workflow_id: str) -> WorkflowManifest:
        return self._registry.require(workflow_id)

    def workflow_origin(self, workflow_id: str) -> str:
        self.require_workflow(workflow_id)
        return self._workflow_origins.get(workflow_id, "unknown")

    def workflow_root(self, workflow_id: str) -> Path:
        self.require_workflow(workflow_id)
        root = self._workflow_roots.get(workflow_id)
        if root is None:
            raise WorkflowRuntimeResolutionError(
                f"workflow asset root is unavailable for workflow_id: {workflow_id}"
            )
        return Path(root)

    def workflow_asset_path(self, workflow_id: str, relative_path: str) -> Path | None:
        root = self.workflow_root(workflow_id).resolve()
        candidate = (root / relative_path).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        return candidate if candidate.is_file() else None

    def input_schema(self, workflow_id: str) -> WorkflowFormSchema:
        self.require_workflow(workflow_id)
        schema = self._input_schemas.get(workflow_id)
        if schema is None:
            raise WorkflowRuntimeResolutionError(
                f"workflow input schema is unavailable for workflow_id: {workflow_id}"
            )
        return schema

    def settings_schema(self, workflow_id: str) -> WorkflowFormSchema:
        self.require_workflow(workflow_id)
        schema = self._settings_schemas.get(workflow_id)
        if schema is None:
            raise WorkflowRuntimeResolutionError(
                f"workflow settings schema is unavailable for workflow_id: {workflow_id}"
            )
        return schema

    def task_schema(self, workflow_id: str) -> WorkflowTaskSchema:
        self.require_workflow(workflow_id)
        schema = self._task_schemas.get(workflow_id)
        if schema is None:
            raise WorkflowRuntimeResolutionError(
                f"workflow Task schema is unavailable for workflow_id: {workflow_id}"
            )
        return schema

    def load_task_items(
        self,
        workflow_id: str,
        path: Path,
        task_values: Mapping[str, Any],
    ) -> list[dict[str, Any]] | None:
        """Call an optional trusted plugin data loader and validate JSON-safe rows."""
        self.require_workflow(workflow_id)
        loader = self._task_item_loaders.get(workflow_id)
        if loader is None:
            return None
        raw = loader(Path(path), dict(task_values))
        if not isinstance(raw, list):
            raise WorkflowRuntimeResolutionError(
                f"load_task_items must return a list for workflow_id: {workflow_id}"
            )
        rows: list[dict[str, Any]] = []
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise WorkflowRuntimeResolutionError(
                    f"load_task_items row {index} is not an object for workflow_id: {workflow_id}"
                )
            row: dict[str, Any] = {}
            for key, value in item.items():
                key = str(key)
                if value is not None and not isinstance(value, (str, int, bool, float)):
                    raise WorkflowRuntimeResolutionError(
                        f"load_task_items row {index} contains unsupported value type for key {key!r}."
                    )
                row[key] = value
            rows.append(row)
        if not rows:
            raise WorkflowRuntimeResolutionError(
                f"load_task_items returned no Task rows for workflow_id: {workflow_id}"
            )
        return rows

    def load_task_data(
        self,
        workflow_id: str,
        path: Path,
        task_values: Mapping[str, Any],
        *,
        context: Mapping[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None, str | None] | None:
        """Load workflow Task rows plus optional fingerprint/summary metadata.

        Existing Plugin API 1 ``load_task_items`` workflows remain supported; the
        richer ``load_task_data`` hook is optional and used only when present.
        """
        self.require_workflow(workflow_id)
        loader = self._task_data_loaders.get(workflow_id)
        if loader is None:
            rows = self.load_task_items(workflow_id, path, task_values)
            if rows is None:
                return None
            return rows, None, None
        raw = loader(Path(path), dict(task_values), dict(context or {}))
        if not isinstance(raw, Mapping):
            raise WorkflowRuntimeResolutionError(
                f"load_task_data must return an object for workflow_id: {workflow_id}"
            )
        items = raw.get("items")
        if not isinstance(items, list) or not items:
            raise WorkflowRuntimeResolutionError(
                f"load_task_data must return a non-empty items list for workflow_id: {workflow_id}"
            )
        rows: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise WorkflowRuntimeResolutionError(
                    f"load_task_data row {index} is not an object for workflow_id: {workflow_id}"
                )
            row: dict[str, Any] = {}
            for key, value in item.items():
                key = str(key)
                if value is not None and not isinstance(value, (str, int, bool, float)):
                    raise WorkflowRuntimeResolutionError(
                        f"load_task_data row {index} contains unsupported value type for key {key!r}."
                    )
                row[key] = value
            rows.append(row)
        fingerprint_raw = raw.get("source_fingerprint")
        summary_raw = raw.get("summary")
        fingerprint = None if fingerprint_raw in {None, ""} else str(fingerprint_raw)
        summary = None if summary_raw in {None, ""} else str(summary_raw)
        return rows, fingerprint, summary

    def require_active_workflow(self) -> WorkflowManifest:
        workflow_id = self._active_workflow_id
        if workflow_id is None:
            raise ActiveWorkflowRequiredError(
                "automation blocked: no active workflow is configured"
            )
        return self.require_workflow(workflow_id)

    def require_runtime_factory(self, workflow_id: str) -> WorkflowRuntimeFactory:
        manifest = self.require_workflow(workflow_id)
        factory = self._runtime_factories.get(manifest.workflow_id)
        if factory is None:
            raise WorkflowRuntimeResolutionError(
                f"no validated runtime is registered for workflow_id: {manifest.workflow_id}"
            )
        return factory

    def resolve_active_runtime(self, *args: Any, **kwargs: Any) -> WorkflowRuntime:
        manifest = self.require_active_workflow()
        factory = self._runtime_factories.get(manifest.workflow_id)
        if factory is None:
            raise WorkflowRuntimeResolutionError(
                f"no validated runtime is registered for workflow_id: {manifest.workflow_id}"
            )
        try:
            runtime = factory(*args, **kwargs)
        except Exception as exc:
            raise WorkflowRuntimeResolutionError(
                f"workflow runtime creation failed for {manifest.workflow_id}: {exc}"
            ) from exc
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
