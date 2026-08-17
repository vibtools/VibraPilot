"""Declarative workflow-extension schemas for VibraPilot v1.0.6.30.

The schema layer is intentionally non-executable. Trusted workflow Python owns
business/browser behavior, while JSON only declares forms, Task controls and
visible metrics that VibraPilot's core UI renders.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping
from urllib.parse import urlparse

WORKFLOW_PLUGIN_API_VERSION = 1
WORKFLOW_FIELD_KINDS = frozenset(
    {
        "text",
        "multiline",
        "integer",
        "decimal",
        "boolean",
        "choice",
        "date",
        "url",
        "file",
        "directory",
    }
)
WORKFLOW_TASK_FIELD_ROLES = frozenset(
    {"generic", "target_url", "data_file", "attachment", "output_directory"}
)
WORKFLOW_METRIC_SOURCES = frozenset(
    {
        "core_login",
        "core_send_limit",
        "core_total",
        "core_success",
        "core_failed",
        "core_remaining",
        "workflow",
    }
)
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class WorkflowSchemaError(ValueError):
    """Raised when declarative workflow UI/configuration schema is invalid."""


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowSchemaError(f"{label} must be a non-empty string.")
    return value.strip()


def _schema_key(value: Any, label: str) -> str:
    key = _required_text(value, label)
    if not _KEY_RE.fullmatch(key):
        raise WorkflowSchemaError(
            f"{label} must be lowercase snake_case and start with a letter: {key!r}."
        )
    return key


@dataclass(frozen=True, slots=True)
class WorkflowFieldSchema:
    key: str
    label: str
    kind: str = "text"
    default: Any = ""
    placeholder: str = ""
    help_text: str = ""
    required: bool = False
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None
    role: str = "generic"

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _schema_key(self.key, "field key"))
        object.__setattr__(self, "label", _required_text(self.label, "field label"))
        kind = str(self.kind).strip().lower()
        if kind not in WORKFLOW_FIELD_KINDS:
            raise WorkflowSchemaError(
                f"Unsupported workflow field kind {self.kind!r} for {self.key}."
            )
        object.__setattr__(self, "kind", kind)
        role = str(self.role or "generic").strip().lower()
        if role not in WORKFLOW_TASK_FIELD_ROLES:
            raise WorkflowSchemaError(
                f"Unsupported Task field role {self.role!r} for {self.key}."
            )
        object.__setattr__(self, "role", role)
        if isinstance(self.minimum, bool) or isinstance(self.maximum, bool):
            raise WorkflowSchemaError(f"minimum/maximum must be integers for {self.key}.")
        if self.minimum is not None and not isinstance(self.minimum, int):
            raise WorkflowSchemaError(f"minimum must be an integer for {self.key}.")
        if self.maximum is not None and not isinstance(self.maximum, int):
            raise WorkflowSchemaError(f"maximum must be an integer for {self.key}.")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.maximum < self.minimum
        ):
            raise WorkflowSchemaError(f"maximum is lower than minimum for {self.key}.")
        if kind != "integer" and (self.minimum is not None or self.maximum is not None):
            raise WorkflowSchemaError(
                f"minimum/maximum are only supported for integer fields: {self.key}."
            )
        choices = tuple(self.choices)
        if kind == "choice":
            if not choices:
                raise WorkflowSchemaError(f"Choice field has no choices: {self.key}.")
            if len(set(choices)) != len(choices):
                raise WorkflowSchemaError(f"Choice field has duplicate choices: {self.key}.")
            if not all(isinstance(value, str) and value for value in choices):
                raise WorkflowSchemaError(
                    f"Choice values must be non-empty strings: {self.key}."
                )
        elif choices:
            raise WorkflowSchemaError(
                f"choices are only supported for choice fields: {self.key}."
            )
        object.__setattr__(self, "choices", choices)
        # Required runtime/user values may intentionally start blank; validate
        # source defaults for type/format without treating blank as submitted data.
        if not (self.required and self.default == ""):
            normalize_field_value(self, self.default, coerce=False)


@dataclass(frozen=True, slots=True)
class WorkflowFormSchema:
    workflow_id: str
    title: str
    fields: tuple[WorkflowFieldSchema, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", _schema_key(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "title", _required_text(self.title, "schema title"))
        fields = tuple(self.fields)
        keys = tuple(field.key for field in fields)
        if len(keys) != len(set(keys)):
            raise WorkflowSchemaError(
                f"Duplicate field key in workflow schema {self.workflow_id}."
            )
        object.__setattr__(self, "fields", fields)

    def defaults(self) -> dict[str, Any]:
        return {field.key: field.default for field in self.fields}

    def field_map(self) -> dict[str, WorkflowFieldSchema]:
        return {field.key: field for field in self.fields}


@dataclass(frozen=True, slots=True)
class WorkflowMetricSchema:
    key: str
    label: str
    source: str = "workflow"
    visible: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", _schema_key(self.key, "metric key"))
        object.__setattr__(self, "label", _required_text(self.label, "metric label"))
        source = str(self.source).strip().lower()
        if source not in WORKFLOW_METRIC_SOURCES:
            raise WorkflowSchemaError(
                f"Unsupported metric source {self.source!r} for {self.key}."
            )
        object.__setattr__(self, "source", source)


@dataclass(frozen=True, slots=True)
class WorkflowTaskSchema:
    workflow_id: str
    title: str
    inputs: tuple[WorkflowFieldSchema, ...] = ()
    settings: tuple[WorkflowFieldSchema, ...] = ()
    metrics: tuple[WorkflowMetricSchema, ...] = ()
    single_item: bool = False
    requires_session: bool = True
    uses_test_send_limit: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "workflow_id", _schema_key(self.workflow_id, "workflow_id"))
        object.__setattr__(self, "title", _required_text(self.title, "Task schema title"))
        inputs = tuple(self.inputs)
        settings = tuple(self.settings)
        metrics = tuple(self.metrics)
        keys = [field.key for field in (*inputs, *settings)]
        if len(keys) != len(set(keys)):
            raise WorkflowSchemaError(
                f"Task input/settings field keys must be unique for {self.workflow_id}."
            )
        metric_keys = [metric.key for metric in metrics]
        if len(metric_keys) != len(set(metric_keys)):
            raise WorkflowSchemaError(
                f"Task metric keys must be unique for {self.workflow_id}."
            )
        roles = [field.role for field in (*inputs, *settings) if field.role != "generic"]
        for unique_role in ("target_url", "data_file", "output_directory"):
            if roles.count(unique_role) > 1:
                raise WorkflowSchemaError(
                    f"Task schema may define at most one {unique_role} field for {self.workflow_id}."
                )
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "settings", settings)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "single_item", bool(self.single_item))
        object.__setattr__(self, "requires_session", bool(self.requires_session))
        object.__setattr__(self, "uses_test_send_limit", bool(self.uses_test_send_limit))

    @property
    def fields(self) -> tuple[WorkflowFieldSchema, ...]:
        return self.inputs + self.settings

    def defaults(self) -> dict[str, Any]:
        return {field.key: field.default for field in self.fields}

    def field_map(self) -> dict[str, WorkflowFieldSchema]:
        return {field.key: field for field in self.fields}

    def role_field(self, role: str) -> WorkflowFieldSchema | None:
        normalized = str(role).strip().lower()
        return next((field for field in self.fields if field.role == normalized), None)


def normalize_field_value(
    field: WorkflowFieldSchema,
    value: Any,
    *,
    coerce: bool,
    enforce_required: bool = True,
) -> Any:
    kind = field.kind
    if kind in {"text", "multiline", "date", "url", "file", "directory", "decimal"}:
        if coerce:
            value = "" if value is None else str(value)
        if not isinstance(value, str):
            raise WorkflowSchemaError(f"{field.label} must be text.")
        if enforce_required and field.required and not value.strip():
            raise WorkflowSchemaError(f"{field.label} is required.")
        stripped = value.strip()
        if kind == "date" and stripped:
            try:
                date.fromisoformat(stripped)
            except ValueError as exc:
                raise WorkflowSchemaError(
                    f"{field.label} must use YYYY-MM-DD format."
                ) from exc
        if kind == "url" and stripped:
            parsed = urlparse(stripped)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise WorkflowSchemaError(
                    f"{field.label} must be a valid http/https URL."
                )
        if kind == "decimal" and stripped:
            try:
                Decimal(stripped)
            except InvalidOperation as exc:
                raise WorkflowSchemaError(f"{field.label} must be a decimal number.") from exc
        return value

    if kind == "integer":
        if coerce:
            if isinstance(value, bool):
                raise WorkflowSchemaError(f"{field.label} must be an integer.")
            try:
                value = int(str(value).strip())
            except (TypeError, ValueError) as exc:
                raise WorkflowSchemaError(f"{field.label} must be an integer.") from exc
        if isinstance(value, bool) or not isinstance(value, int):
            raise WorkflowSchemaError(f"{field.label} must be an integer.")
        if field.minimum is not None and value < field.minimum:
            raise WorkflowSchemaError(
                f"{field.label} must be {field.minimum} or greater."
            )
        if field.maximum is not None and value > field.maximum:
            raise WorkflowSchemaError(
                f"{field.label} must be {field.maximum} or lower."
            )
        return value

    if kind == "boolean":
        if coerce and not isinstance(value, bool):
            text = str(value).strip().lower()
            if text in {"true", "1", "yes", "y", "on"}:
                value = True
            elif text in {"false", "0", "no", "n", "off"}:
                value = False
        if not isinstance(value, bool):
            raise WorkflowSchemaError(f"{field.label} must be true or false.")
        return value

    if kind == "choice":
        if coerce and not isinstance(value, str):
            value = str(value)
        if not isinstance(value, str) or value not in field.choices:
            raise WorkflowSchemaError(
                f"{field.label} must be one of: {', '.join(field.choices)}."
            )
        return value

    raise WorkflowSchemaError(f"Unsupported workflow field kind: {kind!r}.")


def normalize_form_values(
    schema: WorkflowFormSchema,
    values: Mapping[str, Any],
    *,
    coerce: bool,
    fill_defaults: bool = True,
    enforce_required: bool = True,
) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise WorkflowSchemaError(
            f"Values for {schema.workflow_id} must be a mapping."
        )
    normalized: dict[str, Any] = {}
    for field in schema.fields:
        if field.key in values:
            raw = values[field.key]
        elif fill_defaults:
            raw = field.default
        else:
            raise WorkflowSchemaError(
                f"Missing workflow value: {schema.workflow_id}.{field.key}."
            )
        normalized[field.key] = normalize_field_value(
            field, raw, coerce=coerce, enforce_required=enforce_required
        )
    return normalized


def normalize_task_values(
    schema: WorkflowTaskSchema,
    values: Mapping[str, Any],
    *,
    coerce: bool,
    fill_defaults: bool = True,
    enforce_required: bool = True,
) -> dict[str, Any]:
    form = WorkflowFormSchema(schema.workflow_id, schema.title, schema.fields)
    return normalize_form_values(
        form,
        values,
        coerce=coerce,
        fill_defaults=fill_defaults,
        enforce_required=enforce_required,
    )


def _field_from_json(payload: Any) -> WorkflowFieldSchema:
    if not isinstance(payload, Mapping):
        raise WorkflowSchemaError("Workflow field definition must be a JSON object.")
    allowed = {
        "key",
        "label",
        "kind",
        "default",
        "placeholder",
        "help_text",
        "required",
        "choices",
        "minimum",
        "maximum",
        "role",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise WorkflowSchemaError(
            "Unsupported workflow field keys: " + ", ".join(sorted(map(str, unknown)))
        )
    choices = payload.get("choices", ())
    if isinstance(choices, list):
        choices = tuple(choices)
    return WorkflowFieldSchema(
        key=payload.get("key", ""),
        label=payload.get("label", ""),
        kind=payload.get("kind", "text"),
        default=payload.get("default", ""),
        placeholder=str(payload.get("placeholder", "") or ""),
        help_text=str(payload.get("help_text", "") or ""),
        required=bool(payload.get("required", False)),
        choices=tuple(choices or ()),
        minimum=payload.get("minimum"),
        maximum=payload.get("maximum"),
        role=payload.get("role", "generic"),
    )


def load_form_schema(
    payload: Any,
    *,
    workflow_id: str,
    default_title: str,
) -> WorkflowFormSchema:
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise WorkflowSchemaError("Workflow form schema root must be a JSON object.")
    allowed = {"title", "fields"}
    unknown = set(payload) - allowed
    if unknown:
        raise WorkflowSchemaError(
            "Unsupported workflow form schema keys: "
            + ", ".join(sorted(map(str, unknown)))
        )
    fields_raw = payload.get("fields", [])
    if not isinstance(fields_raw, list):
        raise WorkflowSchemaError("Workflow form fields must be a JSON array.")
    fields = tuple(_field_from_json(item) for item in fields_raw)
    return WorkflowFormSchema(
        workflow_id=workflow_id,
        title=str(payload.get("title", default_title) or default_title),
        fields=fields,
    )


def _metric_from_json(payload: Any) -> WorkflowMetricSchema:
    if not isinstance(payload, Mapping):
        raise WorkflowSchemaError("Workflow metric definition must be a JSON object.")
    allowed = {"key", "label", "source", "visible"}
    unknown = set(payload) - allowed
    if unknown:
        raise WorkflowSchemaError(
            "Unsupported workflow metric keys: " + ", ".join(sorted(map(str, unknown)))
        )
    return WorkflowMetricSchema(
        key=payload.get("key", ""),
        label=payload.get("label", ""),
        source=payload.get("source", "workflow"),
        visible=bool(payload.get("visible", True)),
    )


def load_task_schema(
    payload: Any,
    *,
    workflow_id: str,
    default_title: str,
) -> WorkflowTaskSchema:
    if payload is None:
        payload = {}
    if not isinstance(payload, Mapping):
        raise WorkflowSchemaError("Workflow Task schema root must be a JSON object.")
    allowed = {
        "title",
        "inputs",
        "settings",
        "metrics",
        "single_item",
        "requires_session",
        "uses_test_send_limit",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise WorkflowSchemaError(
            "Unsupported workflow Task schema keys: "
            + ", ".join(sorted(map(str, unknown)))
        )
    inputs_raw = payload.get("inputs", [])
    settings_raw = payload.get("settings", [])
    metrics_raw = payload.get("metrics", [])
    if not isinstance(inputs_raw, list) or not isinstance(settings_raw, list):
        raise WorkflowSchemaError("Task inputs/settings must be JSON arrays.")
    if not isinstance(metrics_raw, list):
        raise WorkflowSchemaError("Task metrics must be a JSON array.")
    return WorkflowTaskSchema(
        workflow_id=workflow_id,
        title=str(payload.get("title", default_title) or default_title),
        inputs=tuple(_field_from_json(item) for item in inputs_raw),
        settings=tuple(_field_from_json(item) for item in settings_raw),
        metrics=tuple(_metric_from_json(item) for item in metrics_raw),
        single_item=bool(payload.get("single_item", False)),
        requires_session=bool(payload.get("requires_session", True)),
        uses_test_send_limit=bool(payload.get("uses_test_send_limit", False)),
    )


def coerce_legacy_input_schema(schema: Any) -> WorkflowFormSchema:
    """Adapt the frozen PR-08 source-controlled schema without changing it."""
    fields: list[WorkflowFieldSchema] = []
    for field in tuple(getattr(schema, "fields", ())):
        fields.append(
            WorkflowFieldSchema(
                key=field.key,
                label=field.label,
                kind=field.kind,
                default=field.default,
                placeholder=getattr(field, "placeholder", ""),
                help_text=getattr(field, "help_text", ""),
                required=bool(getattr(field, "required", False)),
                choices=tuple(getattr(field, "choices", ()) or ()),
                minimum=getattr(field, "minimum", None),
                maximum=getattr(field, "maximum", None),
            )
        )
    return WorkflowFormSchema(
        workflow_id=str(schema.workflow_id),
        title=str(schema.title),
        fields=tuple(fields),
    )
