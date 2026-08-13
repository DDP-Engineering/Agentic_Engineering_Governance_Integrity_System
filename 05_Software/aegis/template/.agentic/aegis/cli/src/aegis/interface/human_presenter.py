#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    human_presenter.py
@brief   Render concise human-readable operation results.
@details Presents the same result values consumed by the JSON presenter.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from aegis.domain.results import OperationResult

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

_MAX_LINE_LENGTH = 239
_MAX_LABEL_LENGTH = 48
_MAX_DATA_FIELDS = 24
_MAX_SECTION_ITEMS = 20
_MAX_OPERATION_ITEMS = 64
_MAX_INLINE_ITEMS = 8

# -----------------------------------------------------------------------------
# LOCAL HELPERS
# -----------------------------------------------------------------------------


def _clip(text: str, limit: int = _MAX_LINE_LENGTH) -> str:
    """@brief Keep one rendered value on one bounded line."""
    flattened = " ".join(text.splitlines()).replace("\t", " ")
    if len(flattened) <= limit:
        return flattened
    return flattened[: max(0, limit - 3)].rstrip() + "..."


def _line(label: str, value: object) -> str:
    """@brief Build one labelled line within the human output bound."""
    prefix = f"{_clip(label, _MAX_LABEL_LENGTH)}: "
    return prefix + _clip(str(value), _MAX_LINE_LENGTH - len(prefix))


def _bullet(value: object, *, indent: int = 2) -> str:
    """@brief Build one bounded indented list item."""
    prefix = f"{' ' * indent}- "
    return prefix + _clip(str(value), _MAX_LINE_LENGTH - len(prefix))


def _scalar(value: object) -> str:
    """@brief Render one ordinary scalar without JSON punctuation."""
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    return _clip(str(value))


def _is_scalar(value: object) -> bool:
    """@return True when a value is suitable for direct one-line rendering."""
    return value is None or isinstance(value, (str, int, float, bool))


def _inline_value(value: object) -> str | None:
    """@brief Render only small, shallow collections inline."""
    if _is_scalar(value):
        return _scalar(value)
    if isinstance(value, (list, tuple)):
        if len(value) > _MAX_INLINE_ITEMS or not all(map(_is_scalar, value)):
            return None
        rendered = ", ".join(_scalar(item) for item in value)
        return rendered if len(rendered) <= 120 else None
    if isinstance(value, dict):
        if len(value) > _MAX_INLINE_ITEMS or not all(
            _is_scalar(item) for item in value.values()
        ):
            return None
        rendered = ", ".join(
            f"{key}={_scalar(value[key])}" for key in sorted(value, key=str)
        )
        return rendered if len(rendered) <= 120 else None
    return None


def _summary(value: object, detail_reference: str | None) -> str:
    """@brief Describe a nested value without serializing its contents."""
    if isinstance(value, dict):
        count = len(value)
        description = f"{count} field{'s' if count != 1 else ''}"
    elif isinstance(value, (list, tuple)):
        count = len(value)
        description = f"{count} item{'s' if count != 1 else ''}"
    else:
        description = f"{type(value).__name__} value"
    if detail_reference:
        description += f"; see {detail_reference}"
    return description


def _render_operations(lines: list[str], operations: list[object]) -> None:
    """@brief Preserve the useful root operation catalog."""
    lines.append("operations:")
    for operation in operations[:_MAX_OPERATION_ITEMS]:
        if not isinstance(operation, dict):
            lines.append(_bullet(_summary(operation, None)))
            continue
        availability = "available" if operation.get("implemented") else "unavailable"
        value = (
            f"{operation.get('command', 'unknown')}: "
            f"{operation.get('operation', 'unknown')} ({availability})"
        )
        lines.append(_bullet(value))
    omitted = len(operations) - _MAX_OPERATION_ITEMS
    if omitted > 0:
        lines.append(_bullet(f"{omitted} more operations"))


def _render_arguments(lines: list[str], key: str, arguments: list[object]) -> None:
    """@brief Preserve bounded command-help argument listings."""
    lines.append(f"{key}:")
    for argument in arguments[:_MAX_SECTION_ITEMS]:
        if not isinstance(argument, dict):
            lines.append(_bullet(_summary(argument, None)))
            continue
        name = argument.get("name", "unknown")
        description = argument.get("description", "")
        lines.append(_bullet(f"{name} - {description}".rstrip(" -")))
    omitted = len(arguments) - _MAX_SECTION_ITEMS
    if omitted > 0:
        lines.append(_bullet(f"{omitted} more arguments"))


def _render_machine_input(
    lines: list[str], value: dict[object, object], detail_reference: str | None
) -> None:
    """@brief Preserve actionable structured-input help without dumping JSON."""
    lines.append("machine_input:")
    source = value.get("source")
    if _is_scalar(source):
        lines.append(_line("  source", _scalar(source)))
    fields = value.get("data_fields")
    if isinstance(fields, list):
        lines.append("  data_fields:")
        for field in fields[:_MAX_SECTION_ITEMS]:
            if not isinstance(field, dict):
                lines.append(_bullet(_summary(field, detail_reference), indent=4))
                continue
            name = field.get("name", "unknown")
            field_type = field.get("type", "unknown")
            necessity = "required" if field.get("required") else "optional"
            description = field.get("description", "")
            rendered = f"{name} ({field_type}, {necessity}) - {description}"
            lines.append(_bullet(rendered.rstrip(" -"), indent=4))
        omitted = len(fields) - _MAX_SECTION_ITEMS
        if omitted > 0:
            lines.append(_bullet(f"{omitted} more data fields", indent=4))
    constraints = value.get("constraints")
    inline_constraints = _inline_value(constraints)
    if inline_constraints is not None:
        lines.append(_line("  constraints", inline_constraints or "none"))
    elif constraints is not None:
        lines.append(_line("  constraints", _summary(constraints, detail_reference)))


def _render_finding(finding: dict[str, object]) -> tuple[str, ...]:
    """@brief Render each actionable finding field on its own bounded line."""
    label = finding.get("label") or finding.get("code", "unknown")
    severity = finding.get("severity")
    summary = finding.get("summary") or finding.get("message")
    code = finding.get("code")
    observation = finding.get("observation")
    consequence = finding.get("consequence")
    path = finding.get("path") or finding.get("artifact")
    lines = [_line("Finding", label)]
    if severity:
        lines.append(_line("  Severity", severity))
    if code:
        lines.append(_line("  Code", code))
    if summary:
        lines.append(_line("  Summary", summary))
    if observation:
        lines.append(_line("  Observation", observation))
    if consequence:
        lines.append(_line("  Consequence", consequence))
    if path:
        lines.append(_line("  Path", path))
    return tuple(lines)


def _render_artifact(artifact: dict[str, object]) -> str:
    """@brief Render the action and durable location of one artifact."""
    action = artifact.get("action", "observed")
    path = artifact.get("path") or artifact.get("uri") or "unknown"
    artifact_type = artifact.get("type")
    value = f"{action} {path}"
    if artifact_type:
        value += f" ({artifact_type})"
    return _line("Artifact", value)


def _render_next_action(action: dict[str, object]) -> str:
    """@brief Render one bounded operation, arguments, and reason."""
    operation = action.get("operation", "unknown")
    arguments = action.get("arguments", {})
    reason = action.get("reason")
    inline_arguments = _inline_value(arguments)
    value = str(operation)
    if inline_arguments:
        value += f" ({inline_arguments})"
    elif arguments:
        value += f" ({_summary(arguments, None)})"
    if reason:
        value += f" - {reason}"
    return _line("Next", value)

# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def render_human(result: OperationResult) -> str:
    """
    @brief Render stable semantic labels without duplicating application policy.
    @param[in] result Presentation-neutral operation result.
    @return Plain text ending without a newline.
    """
    lines = [
        _line("Message", result.message),
        _line("Operation", result.operation),
        _line("Status", result.operation_status),
        _line("Product", f"{result.product} {result.product_version}"),
    ]
    if result.run_id is not None:
        lines.append(_line("Run", result.run_id))
    if result.stage is not None:
        lines.append(_line("Stage", result.stage))
    if result.revision is not None:
        lines.append(_line("Revision", result.revision))
    if result.outcome is not None:
        lines.append(_line("Outcome", result.outcome))

    detail_reference = result.details_ref
    if detail_reference is None:
        detail_reference = next(
            (
                str(artifact["path"])
                for artifact in result.artifacts
                if artifact.get("path")
            ),
            None,
        )

    data_items = list(result.data.items())
    for key, value in data_items[:_MAX_DATA_FIELDS]:
        if key == "operations" and isinstance(value, list):
            _render_operations(lines, value)
            continue
        if key in {"required_arguments", "optional_arguments"} and isinstance(
            value, list
        ):
            _render_arguments(lines, key, value)
            continue
        if key == "machine_input" and isinstance(value, dict):
            _render_machine_input(lines, value, detail_reference)
            continue
        inline = _inline_value(value)
        rendered = inline if inline is not None else _summary(value, detail_reference)
        lines.append(_line(str(key), rendered))
    omitted_data = len(data_items) - _MAX_DATA_FIELDS
    if omitted_data > 0:
        lines.append(_line("Data", f"{omitted_data} more fields omitted"))

    for finding in result.findings[:_MAX_SECTION_ITEMS]:
        lines.extend(_render_finding(finding))
    if len(result.findings) > _MAX_SECTION_ITEMS:
        lines.append(
            _line("Findings", f"{len(result.findings) - _MAX_SECTION_ITEMS} more")
        )
    for artifact in result.artifacts[:_MAX_SECTION_ITEMS]:
        lines.append(_render_artifact(artifact))
    if len(result.artifacts) > _MAX_SECTION_ITEMS:
        lines.append(
            _line("Artifacts", f"{len(result.artifacts) - _MAX_SECTION_ITEMS} more")
        )
    if result.error is not None:
        error_value = f"{result.error.code} - {result.error.summary}"
        if result.error.field:
            error_value += f" (field={result.error.field})"
        if result.error.path:
            error_value += f" (path={result.error.path})"
        if result.error.retryable:
            error_value += " (retryable=true)"
        if result.error.details:
            error_value += f" ({_summary(result.error.details, detail_reference)})"
        lines.append(_line("Error", error_value))
    for action in result.next_actions[:3]:
        lines.append(_render_next_action(action))
    if result.truncated or len(result.next_actions) > 3:
        lines.append("Truncated: true")
    if result.details_ref is not None:
        lines.append(_line("Details", result.details_ref))
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
