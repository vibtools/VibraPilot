"""Trusted local workflow-plugin inspection, installation and loading.

External workflow Python executes in-process with VibraPilot permissions and is
therefore never imported during package inspection. The UI must obtain explicit
user trust before calling ``install_workflow_package``.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import uuid
import zipfile
from typing import Any, Callable, Mapping

from .contracts import WorkflowManifest, WorkflowRuntimeFactory
from .schemas import (
    WORKFLOW_PLUGIN_API_VERSION,
    WorkflowFormSchema,
    WorkflowSchemaError,
    WorkflowTaskSchema,
    load_form_schema,
    load_task_schema,
)

MAX_WORKFLOW_PACKAGE_FILES = 512
MAX_WORKFLOW_PACKAGE_UNCOMPRESSED_BYTES = 64 * 1024 * 1024
MAX_WORKFLOW_SOURCE_BYTES = 2 * 1024 * 1024
MAX_WORKFLOW_JSON_BYTES = 1024 * 1024
_REQUIRED = ("manifest.json", "workflow.py", "inputs.json", "settings.json", "task.json")
_ALLOWED_TOP_LEVEL = set(_REQUIRED) | {"assets", "README.md", "README.txt"}
_INSTALL_METADATA = ".vibrapilot-plugin.json"


class WorkflowPluginError(RuntimeError):
    pass


class WorkflowPluginValidationError(WorkflowPluginError, ValueError):
    pass


class WorkflowPluginInstallError(WorkflowPluginError):
    pass


@dataclass(frozen=True, slots=True)
class WorkflowPackageInspection:
    package_path: Path
    package_sha256: str
    manifest: WorkflowManifest
    plugin_api: int
    root_prefix: str
    input_schema: WorkflowFormSchema
    settings_schema: WorkflowFormSchema
    task_schema: WorkflowTaskSchema


@dataclass(frozen=True, slots=True)
class InstalledWorkflowPlugin:
    manifest: WorkflowManifest
    plugin_api: int
    root: Path
    runtime_factory: WorkflowRuntimeFactory
    input_schema: WorkflowFormSchema
    settings_schema: WorkflowFormSchema
    task_schema: WorkflowTaskSchema
    task_item_loader: Callable[[Path, Mapping[str, Any]], list[Mapping[str, Any]]] | None


@dataclass(frozen=True, slots=True)
class WorkflowPluginIssue:
    path: str
    message: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_workflow_plugin_root(app_data_dir: Path) -> Path:
    """Return the durable per-user external workflow directory."""
    app_data_dir = Path(app_data_dir).expanduser().resolve()
    if os.environ.get("VIB_TOOLS_DATA_DIR"):
        return app_data_dir / "Workflows"
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local:
            return Path(local).expanduser().resolve() / "Vib Tools" / "VibraPilot" / "Workflows"
    return app_data_dir / "Workflows"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_archive_name(name: str) -> PurePosixPath:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        raise WorkflowPluginValidationError("Workflow package contains an invalid archive path.")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise WorkflowPluginValidationError(f"Unsafe workflow package path: {name!r}.")
    if path.parts and ":" in path.parts[0]:
        raise WorkflowPluginValidationError(f"Unsafe workflow package drive path: {name!r}.")
    return path


def _zip_is_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_IFMT((info.external_attr >> 16) & 0xFFFF) == stat.S_IFLNK


def _package_members(archive: zipfile.ZipFile) -> tuple[list[zipfile.ZipInfo], str]:
    infos = [info for info in archive.infolist() if not info.is_dir()]
    if not infos:
        raise WorkflowPluginValidationError("Workflow package is empty.")
    if len(infos) > MAX_WORKFLOW_PACKAGE_FILES:
        raise WorkflowPluginValidationError("Workflow package contains too many files.")
    total = sum(max(0, int(info.file_size)) for info in infos)
    if total > MAX_WORKFLOW_PACKAGE_UNCOMPRESSED_BYTES:
        raise WorkflowPluginValidationError("Workflow package exceeds the safe uncompressed-size limit.")
    paths: list[PurePosixPath] = []
    for info in infos:
        if _zip_is_symlink(info):
            raise WorkflowPluginValidationError(f"Workflow package symlinks are not allowed: {info.filename}.")
        paths.append(_safe_archive_name(info.filename))

    names = {path.as_posix() for path in paths}
    if all(required in names for required in _REQUIRED):
        prefix = ""
    else:
        roots = {path.parts[0] for path in paths if len(path.parts) > 1}
        candidates = [root for root in roots if all(f"{root}/{required}" in names for required in _REQUIRED)]
        if len(candidates) != 1:
            raise WorkflowPluginValidationError(
                "Workflow package must contain the required files at archive root or inside one top-level folder."
            )
        prefix = candidates[0] + "/"

    for path in paths:
        rel = path.as_posix()
        if prefix:
            if not rel.startswith(prefix):
                raise WorkflowPluginValidationError("Workflow package mixes files outside its package root.")
            rel = rel[len(prefix):]
        parts = PurePosixPath(rel).parts
        top = parts[0]
        if top not in _ALLOWED_TOP_LEVEL:
            raise WorkflowPluginValidationError(f"Unsupported workflow package top-level entry: {top}.")
        if rel.endswith(".py") and rel != "workflow.py":
            raise WorkflowPluginValidationError(
                "Only the fixed workflow.py executable module is supported in this plugin API."
            )
    return infos, prefix


def _read_zip_file(
    archive: zipfile.ZipFile,
    prefix: str,
    name: str,
    *,
    maximum: int,
) -> bytes:
    full = prefix + name
    try:
        info = archive.getinfo(full)
    except KeyError as exc:
        raise WorkflowPluginValidationError(f"Workflow package is missing {name}.") from exc
    if info.file_size > maximum:
        raise WorkflowPluginValidationError(f"Workflow package file is too large: {name}.")
    data = archive.read(info)
    if len(data) > maximum:
        raise WorkflowPluginValidationError(f"Workflow package file is too large: {name}.")
    return data


def _decode_json(data: bytes, name: str) -> Any:
    try:
        return json.loads(data.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WorkflowPluginValidationError(f"Workflow package {name} is not valid UTF-8 JSON.") from exc


def _manifest_from_payload(payload: Any) -> tuple[WorkflowManifest, int]:
    if not isinstance(payload, dict):
        raise WorkflowPluginValidationError("Workflow manifest root must be a JSON object.")
    allowed = {
        "workflow_id",
        "name",
        "description",
        "version",
        "logo",
        "entrypoint",
        "plugin_api",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise WorkflowPluginValidationError(
            "Unsupported workflow manifest keys: " + ", ".join(sorted(map(str, unknown)))
        )
    try:
        plugin_api = int(payload.get("plugin_api", 0))
    except (TypeError, ValueError) as exc:
        raise WorkflowPluginValidationError("Workflow plugin_api must be an integer.") from exc
    if plugin_api != WORKFLOW_PLUGIN_API_VERSION:
        raise WorkflowPluginValidationError(
            f"Unsupported Workflow Plugin API {plugin_api}; VibraPilot requires {WORKFLOW_PLUGIN_API_VERSION}."
        )
    manifest_payload = {key: payload.get(key) for key in (
        "workflow_id", "name", "description", "version", "logo", "entrypoint"
    )}
    try:
        manifest = WorkflowManifest(**manifest_payload)
    except Exception as exc:
        raise WorkflowPluginValidationError(f"Workflow manifest is invalid: {exc}") from exc
    if manifest.entrypoint != "create_workflow":
        raise WorkflowPluginValidationError(
            "External workflow entrypoint must be the fixed symbol 'create_workflow'."
        )
    return manifest, plugin_api


def inspect_workflow_package(package_path: Path) -> WorkflowPackageInspection:
    path = Path(package_path).expanduser().resolve()
    if not path.is_file():
        raise WorkflowPluginValidationError(f"Workflow package does not exist: {path}.")
    if path.suffix.lower() not in {".vpworkflow", ".zip"}:
        raise WorkflowPluginValidationError("Workflow package must use .vpworkflow or .zip.")
    try:
        with zipfile.ZipFile(path) as archive:
            _infos, prefix = _package_members(archive)
            manifest, plugin_api = _manifest_from_payload(
                _decode_json(_read_zip_file(archive, prefix, "manifest.json", maximum=MAX_WORKFLOW_JSON_BYTES), "manifest.json")
            )
            source = _read_zip_file(archive, prefix, "workflow.py", maximum=MAX_WORKFLOW_SOURCE_BYTES)
            try:
                ast.parse(source.decode("utf-8-sig"), filename="workflow.py")
            except (UnicodeError, SyntaxError) as exc:
                raise WorkflowPluginValidationError(f"Workflow Python source is invalid: {exc}") from exc
            inputs_payload = _decode_json(
                _read_zip_file(archive, prefix, "inputs.json", maximum=MAX_WORKFLOW_JSON_BYTES), "inputs.json"
            )
            settings_payload = _decode_json(
                _read_zip_file(archive, prefix, "settings.json", maximum=MAX_WORKFLOW_JSON_BYTES), "settings.json"
            )
            task_payload = _decode_json(
                _read_zip_file(archive, prefix, "task.json", maximum=MAX_WORKFLOW_JSON_BYTES), "task.json"
            )
            try:
                input_schema = load_form_schema(
                    inputs_payload, workflow_id=manifest.workflow_id, default_title=f"{manifest.name} Inputs"
                )
                settings_schema = load_form_schema(
                    settings_payload, workflow_id=manifest.workflow_id, default_title=f"{manifest.name} Settings"
                )
                task_schema = load_task_schema(
                    task_payload, workflow_id=manifest.workflow_id, default_title=f"{manifest.name} Task Settings"
                )
            except WorkflowSchemaError as exc:
                raise WorkflowPluginValidationError(str(exc)) from exc
            logo_name = prefix + manifest.logo
            try:
                logo_info = archive.getinfo(logo_name)
            except KeyError as exc:
                raise WorkflowPluginValidationError(
                    f"Workflow logo declared by manifest was not found: {manifest.logo}."
                ) from exc
            if logo_info.is_dir() or _zip_is_symlink(logo_info):
                raise WorkflowPluginValidationError("Workflow logo must be a regular packaged file.")
    except zipfile.BadZipFile as exc:
        raise WorkflowPluginValidationError("Workflow package is not a valid ZIP archive.") from exc
    return WorkflowPackageInspection(
        package_path=path,
        package_sha256=_sha256(path),
        manifest=manifest,
        plugin_api=plugin_api,
        root_prefix=prefix,
        input_schema=input_schema,
        settings_schema=settings_schema,
        task_schema=task_schema,
    )


def _load_json_file(path: Path, label: str) -> Any:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise WorkflowPluginValidationError(f"Could not read {label}: {exc}") from exc
    if len(data) > MAX_WORKFLOW_JSON_BYTES:
        raise WorkflowPluginValidationError(f"Workflow file is too large: {label}.")
    return _decode_json(data, label)


def _validate_directory(root: Path) -> tuple[WorkflowManifest, int, WorkflowFormSchema, WorkflowFormSchema, WorkflowTaskSchema]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise WorkflowPluginValidationError(f"Workflow directory does not exist: {root}.")
    allowed_top = _ALLOWED_TOP_LEVEL | {_INSTALL_METADATA}
    for child in root.iterdir():
        if child.name not in allowed_top:
            raise WorkflowPluginValidationError(
                f"Unsupported installed workflow top-level entry: {child.name}."
            )
    for path in root.rglob("*"):
        if path.is_symlink():
            raise WorkflowPluginValidationError(f"Workflow directory symlinks are not allowed: {path}.")
        if path.is_file() and path.suffix.lower() == ".py" and path.name != "workflow.py":
            raise WorkflowPluginValidationError("Only the fixed workflow.py executable module is supported.")
    for name in _REQUIRED:
        if not (root / name).is_file():
            raise WorkflowPluginValidationError(f"Workflow directory is missing {name}.")
    manifest, plugin_api = _manifest_from_payload(_load_json_file(root / "manifest.json", "manifest.json"))
    try:
        input_schema = load_form_schema(
            _load_json_file(root / "inputs.json", "inputs.json"),
            workflow_id=manifest.workflow_id,
            default_title=f"{manifest.name} Inputs",
        )
        settings_schema = load_form_schema(
            _load_json_file(root / "settings.json", "settings.json"),
            workflow_id=manifest.workflow_id,
            default_title=f"{manifest.name} Settings",
        )
        task_schema = load_task_schema(
            _load_json_file(root / "task.json", "task.json"),
            workflow_id=manifest.workflow_id,
            default_title=f"{manifest.name} Task Settings",
        )
    except WorkflowSchemaError as exc:
        raise WorkflowPluginValidationError(str(exc)) from exc
    logo = (root / manifest.logo).resolve()
    try:
        logo.relative_to(root)
    except ValueError as exc:
        raise WorkflowPluginValidationError("Workflow logo escapes its plugin directory.") from exc
    if not logo.is_file() or logo.is_symlink():
        raise WorkflowPluginValidationError(f"Workflow logo was not found: {manifest.logo}.")
    source = root / "workflow.py"
    if source.stat().st_size > MAX_WORKFLOW_SOURCE_BYTES:
        raise WorkflowPluginValidationError("workflow.py exceeds the safe source-size limit.")
    try:
        ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    except (UnicodeError, SyntaxError) as exc:
        raise WorkflowPluginValidationError(f"Workflow Python source is invalid: {exc}") from exc
    return manifest, plugin_api, input_schema, settings_schema, task_schema


def load_workflow_directory(root: Path) -> InstalledWorkflowPlugin:
    root = Path(root).expanduser().resolve()
    manifest, plugin_api, input_schema, settings_schema, task_schema = _validate_directory(root)
    source = root / "workflow.py"
    module_name = f"vibrapilot_external_workflow_{manifest.workflow_id}_{hashlib.sha256(str(root).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, source)
    if spec is None or spec.loader is None:
        raise WorkflowPluginValidationError(f"Could not create loader for {source}.")
    module = importlib.util.module_from_spec(spec)
    before_path = list(sys.path)
    before_dont_write_bytecode = sys.dont_write_bytecode
    path_mutated = False
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception as exc:
        raise WorkflowPluginValidationError(
            f"Workflow Python module failed during trusted import: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        path_mutated = sys.path != before_path
        if path_mutated:
            sys.path[:] = before_path
        sys.dont_write_bytecode = before_dont_write_bytecode
        shutil.rmtree(root / "__pycache__", ignore_errors=True)
    if path_mutated:
        raise WorkflowPluginValidationError("Workflow plugin attempted to mutate sys.path.")
    factory = getattr(module, manifest.entrypoint, None)
    if not callable(factory):
        raise WorkflowPluginValidationError(
            f"Workflow entrypoint is missing or not callable: {manifest.entrypoint}."
        )
    try:
        signature = inspect.signature(factory)
    except (TypeError, ValueError):
        signature = None
    if signature is not None:
        params = tuple(signature.parameters.values())
        if not params:
            raise WorkflowPluginValidationError("Workflow create_workflow entrypoint must accept the host argument.")

    task_loader = getattr(module, "load_task_items", None)
    if task_loader is not None and not callable(task_loader):
        raise WorkflowPluginValidationError("Optional load_task_items must be callable.")

    def runtime_factory(*args: Any, **kwargs: Any):
        runtime = factory(*args, **kwargs)
        runtime_manifest = getattr(runtime, "manifest", None)
        if runtime_manifest is None:
            try:
                setattr(runtime, "manifest", manifest)
            except Exception as exc:
                raise WorkflowPluginValidationError(
                    "External workflow runtime must expose a manifest attribute."
                ) from exc
        elif runtime_manifest != manifest:
            raise WorkflowPluginValidationError(
                f"External runtime manifest mismatch for {manifest.workflow_id}."
            )
        return runtime

    return InstalledWorkflowPlugin(
        manifest=manifest,
        plugin_api=plugin_api,
        root=root,
        runtime_factory=runtime_factory,
        input_schema=input_schema,
        settings_schema=settings_schema,
        task_schema=task_schema,
        task_item_loader=task_loader,
    )


def install_workflow_package(
    inspection: WorkflowPackageInspection,
    workflow_root: Path,
    *,
    reserved_workflow_ids: set[str] | frozenset[str],
) -> InstalledWorkflowPlugin:
    if inspection.plugin_api != WORKFLOW_PLUGIN_API_VERSION:
        raise WorkflowPluginInstallError("Workflow package inspection is no longer compatible.")
    workflow_id = inspection.manifest.workflow_id
    if workflow_id in set(reserved_workflow_ids):
        raise WorkflowPluginInstallError(
            f"Workflow ID {workflow_id!r} is reserved by a built-in workflow."
        )
    root = Path(workflow_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / workflow_id
    if destination.exists():
        raise WorkflowPluginInstallError(
            f"Workflow {workflow_id!r} is already installed; update/replace is not supported in this release."
        )
    staging_parent = root / ".staging"
    staging_parent.mkdir(parents=True, exist_ok=True)
    staging = staging_parent / f"{workflow_id}-{uuid.uuid4().hex}"
    staging.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(inspection.package_path) as archive:
            infos, prefix = _package_members(archive)
            if prefix != inspection.root_prefix:
                raise WorkflowPluginInstallError("Workflow package changed after inspection.")
            current_sha = _sha256(inspection.package_path)
            if current_sha != inspection.package_sha256:
                raise WorkflowPluginInstallError("Workflow package changed after inspection.")
            for info in infos:
                rel_name = info.filename[len(prefix):] if prefix else info.filename
                rel = _safe_archive_name(rel_name)
                target = (staging / Path(*rel.parts)).resolve()
                try:
                    target.relative_to(staging)
                except ValueError as exc:
                    raise WorkflowPluginInstallError("Workflow extraction escaped staging directory.") from exc
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info, "r") as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        metadata = {
            "schema_version": 1,
            "workflow_id": workflow_id,
            "package_sha256": inspection.package_sha256,
            "installed_at": _utc_now(),
            "plugin_api": inspection.plugin_api,
        }
        (staging / _INSTALL_METADATA).write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        loaded = load_workflow_directory(staging)
        if loaded.manifest != inspection.manifest:
            raise WorkflowPluginInstallError("Staged workflow manifest differs from inspected package.")
        os.replace(staging, destination)
        return load_workflow_directory(destination)
    except WorkflowPluginError:
        raise
    except Exception as exc:
        raise WorkflowPluginInstallError(str(exc)) from exc
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        try:
            if staging_parent.is_dir() and not any(staging_parent.iterdir()):
                staging_parent.rmdir()
        except OSError:
            pass


def load_installed_workflows(
    workflow_root: Path,
    *,
    reserved_workflow_ids: set[str] | frozenset[str],
) -> tuple[tuple[InstalledWorkflowPlugin, ...], tuple[WorkflowPluginIssue, ...]]:
    root = Path(workflow_root).expanduser().resolve()
    if not root.exists():
        return (), ()
    if not root.is_dir():
        return (), (WorkflowPluginIssue(str(root), "Workflow plugin root is not a directory."),)
    plugins: list[InstalledWorkflowPlugin] = []
    issues: list[WorkflowPluginIssue] = []
    seen = set(reserved_workflow_ids)
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        try:
            plugin = load_workflow_directory(path)
            workflow_id = plugin.manifest.workflow_id
            if workflow_id in seen:
                raise WorkflowPluginValidationError(
                    f"Duplicate/reserved workflow ID: {workflow_id}."
                )
            seen.add(workflow_id)
            plugins.append(plugin)
        except Exception as exc:
            issues.append(
                WorkflowPluginIssue(
                    str(path),
                    f"{type(exc).__name__}: {exc}",
                )
            )
    return tuple(plugins), tuple(issues)
