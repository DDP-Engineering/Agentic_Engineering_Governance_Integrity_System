#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Model exact lifecycle plans and safe repository-relative paths."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


class PlanError(ValueError):
    """Report invalid plan or payload data without leaking a traceback."""


PLAN_SCHEMA = "waegis.lifecycle.plan"
PLAN_SCHEMA_VERSION = 1
PLAN_OPERATIONS = {
    "repository_init.plan",
    "install.plan",
    "upgrade.plan",
    "remove.plan",
}
ACTION_KINDS = {"git_init", "write", "delete"}


def safe_relative(value: str) -> str:
    """Normalize and validate one repository-relative POSIX path."""
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise PlanError(f"Unsafe repository-relative path: {value!r}")
    normalized = path.as_posix()
    if normalized in {".", ""}:
        raise PlanError(f"Unsafe repository-relative path: {value!r}")
    return normalized


@dataclass(frozen=True, slots=True)
class Action:
    """Describe one exact write or deletion and its ownership."""

    kind: str
    path: str
    ownership: str
    content: bytes | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-ready action."""
        result: dict[str, Any] = {
            "kind": self.kind,
            "path": safe_relative(self.path),
            "ownership": self.ownership,
        }
        if self.content is not None:
            result["sha256"] = hashlib.sha256(self.content).hexdigest()
            result["content_base64"] = base64.b64encode(self.content).decode("ascii")
        return result


def canonical_plan(plan: dict[str, Any]) -> bytes:
    """Serialize one plan to stable UTF-8 JSON bytes."""
    return (
        json.dumps(
            plan,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def plan_digest(data: bytes) -> str:
    """Return the byte-exact authorization digest."""
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def parse_canonical_plan(data: bytes) -> dict[str, Any]:
    """Parse and verify one exact canonical lifecycle plan."""
    try:
        decoded = data.decode("utf-8", errors="strict")
        plan = json.loads(decoded)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PlanError("Plan is not valid UTF-8 JSON") from exc
    if not isinstance(plan, dict):
        raise PlanError("Plan root must be an object")
    if canonical_plan(plan) != data:
        raise PlanError("Plan bytes are not canonical")
    if plan.get("schema") != PLAN_SCHEMA or plan.get(
        "schema_version"
    ) != PLAN_SCHEMA_VERSION:
        raise PlanError("Plan schema is unsupported")
    if plan.get("operation") not in PLAN_OPERATIONS:
        raise PlanError("Plan operation is invalid")
    for key in ("target", "target_fingerprint", "source_payload_version"):
        if not isinstance(plan.get(key), str) or not plan[key]:
            raise PlanError(f"Plan field is invalid: {key}")
    if not str(plan["target_fingerprint"]).startswith("sha256:"):
        raise PlanError("Plan target fingerprint is invalid")
    actions = plan.get("actions")
    if not isinstance(actions, list):
        raise PlanError("Plan actions must be a list")
    for action in actions:
        _verify_action(action)
    for key in ("prerequisites", "warnings"):
        values = plan.get(key, [])
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            raise PlanError(f"Plan field is invalid: {key}")
    return plan


def _verify_action(action: Any) -> None:
    """Verify one action without exposing its encoded content."""
    if not isinstance(action, dict):
        raise PlanError("Plan action must be an object")
    kind = action.get("kind")
    if kind not in ACTION_KINDS:
        raise PlanError("Plan action kind is invalid")
    if not isinstance(action.get("path"), str):
        raise PlanError("Plan action path is invalid")
    safe_relative(action["path"])
    if not isinstance(action.get("ownership"), str) or not action["ownership"]:
        raise PlanError("Plan action ownership is invalid")
    encoded = action.get("content_base64")
    declared = action.get("sha256")
    if kind == "write":
        if not isinstance(encoded, str) or not isinstance(declared, str):
            raise PlanError("Plan write action has no verified content")
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise PlanError("Plan write action content is invalid") from exc
        if hashlib.sha256(content).hexdigest() != declared:
            raise PlanError("Plan write action content digest is invalid")
    elif encoded is not None or declared is not None:
        raise PlanError("Plan non-write action contains unexpected content")
