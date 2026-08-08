#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file envelope.py
@brief Deterministic V2 JSON result envelope.
@details Keeps one JSON document on stdout and separates stable result fields
         from human diagnostics and pre-mutation recovery records.
"""

# IMPORTS

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True, slots=True)
class ResultEnvelope:
    """@brief Closed command result emitted by JSON mode."""

    command: str
    status: str
    exit_code: int
    result: Mapping[str, object] = field(default_factory=dict)
    messages: Sequence[str] = field(default_factory=tuple)
    schema_version: int = 2

    def to_dict(self) -> dict[str, object]:
        """@brief Convert the envelope to a deterministic mapping."""
        return {
            "schema_version": self.schema_version,
            "command": self.command,
            "status": self.status,
            "exit_code": self.exit_code,
            "result": dict(self.result),
            "messages": list(self.messages),
        }

    def render(self) -> str:
        """@brief Serialize one JSON document with a final newline."""
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


# END OF FILE
