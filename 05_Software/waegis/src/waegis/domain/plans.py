#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Model exact lifecycle plans and safe repository-relative paths."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any


class PlanError(ValueError):
    """Report invalid plan or payload data without leaking a traceback."""


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
