"""Source-controlled Workflow Input schemas for VibraPilot.

PR-08 makes this module the declarative schema authority for Workflow Inputs.
Schemas are ordinary source-controlled Python data only: no manifest-driven
imports, callbacks, filesystem discovery, or executable field actions are
supported here.  The historical ``WORKFLOW_INPUT_FIELDS`` and
``WORKFLOW_INPUT_KEYS`` symbols remain as Share Invite compatibility aliases so
older verification contracts and PR-06's legacy settings clear boundary keep
working without redefining persistence ownership.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


WORKFLOW_INPUT_KINDS = frozenset({"text", "integer", "boolean", "choice"})
_FIELD_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_WORKFLOW_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class WorkflowInputSchemaError(ValueError):
    """Raised when a source-controlled schema or value is invalid."""


@dataclass(frozen=True, slots=True)
class WorkflowInputField:
    """One declarative Workflow Input field."""

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

    def __post_init__(self) -> None:
        if not _FIELD_KEY_RE.fullmatch(self.key):
            raise WorkflowInputSchemaError(f"Invalid Workflow Input key: {self.key!r}")
        if not self.label.strip():
            raise WorkflowInputSchemaError(f"Workflow Input label is empty: {self.key}")
        if self.kind not in WORKFLOW_INPUT_KINDS:
            raise WorkflowInputSchemaError(
                f"Unsupported Workflow Input kind {self.kind!r} for {self.key}."
            )
        if self.minimum is not None and isinstance(self.minimum, bool):
            raise WorkflowInputSchemaError(f"minimum must be an integer for {self.key}.")
        if self.maximum is not None and isinstance(self.maximum, bool):
            raise WorkflowInputSchemaError(f"maximum must be an integer for {self.key}.")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.maximum < self.minimum
        ):
            raise WorkflowInputSchemaError(f"maximum is lower than minimum for {self.key}.")
        if self.kind != "integer" and (self.minimum is not None or self.maximum is not None):
            raise WorkflowInputSchemaError(
                f"minimum/maximum are only supported for integer fields: {self.key}."
            )
        if self.kind == "choice":
            if not self.choices:
                raise WorkflowInputSchemaError(f"Choice field has no choices: {self.key}.")
            if len(set(self.choices)) != len(self.choices):
                raise WorkflowInputSchemaError(f"Choice field has duplicate choices: {self.key}.")
            if not all(isinstance(choice, str) and choice for choice in self.choices):
                raise WorkflowInputSchemaError(f"Choice values must be non-empty strings: {self.key}.")
        elif self.choices:
            raise WorkflowInputSchemaError(
                f"choices are only supported for choice fields: {self.key}."
            )
        # Validate source defaults strictly at import/schema-construction time.
        validate_workflow_input_value(self, self.default, coerce=False)


@dataclass(frozen=True, slots=True)
class WorkflowInputSchema:
    """Declarative Workflow Input schema for one source-controlled workflow."""

    workflow_id: str
    title: str
    fields: tuple[WorkflowInputField, ...] = ()

    def __post_init__(self) -> None:
        if not _WORKFLOW_ID_RE.fullmatch(self.workflow_id):
            raise WorkflowInputSchemaError(f"Invalid workflow ID: {self.workflow_id!r}")
        if not self.title.strip():
            raise WorkflowInputSchemaError(
                f"Workflow Input schema title is empty: {self.workflow_id}."
            )
        keys = tuple(field.key for field in self.fields)
        if len(keys) != len(set(keys)):
            raise WorkflowInputSchemaError(
                f"Duplicate Workflow Input field key in {self.workflow_id}."
            )

    @property
    def field_keys(self) -> tuple[str, ...]:
        return tuple(field.key for field in self.fields)

    def field_map(self) -> dict[str, WorkflowInputField]:
        return {field.key: field for field in self.fields}

    def defaults(self) -> dict[str, Any]:
        return {field.key: field.default for field in self.fields}


def validate_workflow_input_value(
    field: WorkflowInputField,
    value: Any,
    *,
    coerce: bool,
) -> Any:
    """Validate/normalize one value using only declarative field metadata."""

    if field.kind == "text":
        if coerce:
            if value is None:
                value = ""
            elif not isinstance(value, str):
                value = str(value)
        if not isinstance(value, str):
            raise WorkflowInputSchemaError(f"{field.label} must be text.")
        if field.required and not value.strip():
            raise WorkflowInputSchemaError(f"{field.label} is required.")
        return value

    if field.kind == "integer":
        if coerce:
            if isinstance(value, bool):
                raise WorkflowInputSchemaError(f"{field.label} must be an integer.")
            try:
                value = int(str(value).strip())
            except (TypeError, ValueError) as exc:
                raise WorkflowInputSchemaError(f"{field.label} must be an integer.") from exc
        if isinstance(value, bool) or not isinstance(value, int):
            raise WorkflowInputSchemaError(f"{field.label} must be an integer.")
        if field.minimum is not None and value < field.minimum:
            raise WorkflowInputSchemaError(
                f"{field.label} must be {field.minimum} or greater."
            )
        if field.maximum is not None and value > field.maximum:
            raise WorkflowInputSchemaError(
                f"{field.label} must be {field.maximum} or lower."
            )
        return value

    if field.kind == "boolean":
        if coerce and not isinstance(value, bool):
            text = str(value).strip().lower()
            if text in {"true", "1", "yes", "y", "on"}:
                value = True
            elif text in {"false", "0", "no", "n", "off"}:
                value = False
        if not isinstance(value, bool):
            raise WorkflowInputSchemaError(f"{field.label} must be true or false.")
        return value

    if field.kind == "choice":
        if coerce and not isinstance(value, str):
            value = str(value)
        if not isinstance(value, str) or value not in field.choices:
            raise WorkflowInputSchemaError(
                f"{field.label} must be one of: {', '.join(field.choices)}."
            )
        return value

    # Construction-time validation already prevents this branch.
    raise WorkflowInputSchemaError(f"Unsupported Workflow Input kind: {field.kind!r}")


def normalize_workflow_input_values(
    schema: WorkflowInputSchema,
    values: Mapping[str, Any],
    *,
    coerce: bool,
    fill_defaults: bool = True,
) -> dict[str, Any]:
    """Return only current-schema values; stale stored keys are ignored."""

    if not isinstance(values, Mapping):
        raise WorkflowInputSchemaError(
            f"Workflow Input values for {schema.workflow_id} must be a mapping."
        )
    normalized: dict[str, Any] = {}
    for field in schema.fields:
        if field.key in values:
            raw = values[field.key]
        elif fill_defaults:
            raw = field.default
        else:
            raise WorkflowInputSchemaError(
                f"Missing Workflow Input value: {schema.workflow_id}.{field.key}."
            )
        normalized[field.key] = validate_workflow_input_value(
            field, raw, coerce=coerce
        )
    return normalized


SHARE_INVITE_INPUT_SCHEMA = WorkflowInputSchema(
    workflow_id="share_invite",
    title="Share Invite Inputs",
    fields=(
        WorkflowInputField(
            key="default_full_name",
            label="Default Full Name",
            help_text="Workflow-specific full-name value preserved under the existing Share Invite compatibility key.",
        ),
        WorkflowInputField(
            key="default_number",
            label="Default Number",
            help_text="Workflow-specific number value preserved under the existing Share Invite compatibility key.",
        ),
        WorkflowInputField(
            key="fallback_name",
            label="Fallback Name",
            help_text="Workflow-specific fallback name preserved under the existing Share Invite compatibility key.",
        ),
        WorkflowInputField(
            key="update_click_count",
            label="Update Click Count",
            help_text="Preserved Share Invite workflow value under the existing compatibility key.",
        ),
    ),
)


WORKFLOW_INPUT_SCHEMAS: dict[str, WorkflowInputSchema] = {
    SHARE_INVITE_INPUT_SCHEMA.workflow_id: SHARE_INVITE_INPUT_SCHEMA,
}


def workflow_input_schema_for(workflow_id: str) -> WorkflowInputSchema:
    """Resolve one explicitly source-controlled schema; never discover/import it."""

    key = str(workflow_id).strip()
    try:
        return WORKFLOW_INPUT_SCHEMAS[key]
    except KeyError as exc:
        raise WorkflowInputSchemaError(
            f"No source-controlled Workflow Input schema is registered for {key!r}."
        ) from exc


# Historical compatibility aliases.  These remain Share Invite-specific by
# design; PR-08's dynamic page uses ``workflow_input_schema_for`` instead.
WORKFLOW_INPUT_FIELDS: tuple[WorkflowInputField, ...] = SHARE_INVITE_INPUT_SCHEMA.fields
WORKFLOW_INPUT_KEYS: tuple[str, ...] = SHARE_INVITE_INPUT_SCHEMA.field_keys
