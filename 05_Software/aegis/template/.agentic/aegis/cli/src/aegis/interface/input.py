#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file input.py @brief Decode one versioned structured machine input object."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TextIO


class MachineInputError(ValueError):
    """@brief Report invalid structured input before application dispatch."""

    def __init__(self, summary: str, *, path: str | None = None) -> None:
        super().__init__(summary)
        self.path = path


def load_machine_input(source: str, *, stdin: TextIO, operation: str) -> dict[str, Any]:
    """@brief Load and validate one operation-matched JSON input object."""
    path = None if source == "-" else source
    try:
        text = (
            stdin.read()
            if source == "-"
            else Path(source).read_text(encoding="utf-8-sig")
        )
        envelope = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MachineInputError(
            "Structured input is not readable UTF-8 JSON.", path=path
        ) from error
    if not isinstance(envelope, dict):
        raise MachineInputError("Structured input must be one JSON object.")
    if (
        envelope.get("schema") != "aegis.machine.input"
        or envelope.get("schema_version") != 1
    ):
        raise MachineInputError("Structured input schema is unsupported.")
    if envelope.get("operation") != operation:
        raise MachineInputError(
            "Structured input operation does not match the command."
        )
    data = envelope.get("data")
    if not isinstance(data, dict):
        raise MachineInputError("Structured input data must be one object.")
    return data


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
