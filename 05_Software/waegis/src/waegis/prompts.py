#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file prompts.py
@brief Small injectable consequence-style prompt seam.
@details Keeps input/output testable without an event system and makes Enter
         select exactly the displayed default.
"""

# IMPORTS

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, Sequence, TextIO


# DATA MODELS / TYPEDEFINITIONS


class Asker(Protocol):
    """@brief Structural contract for one prompt source."""

    def ask(self, field: FieldSpec) -> str:
        """@brief Return one validated raw answer or the displayed default."""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """@brief One plain question, consequence, choices, and default."""

    key: str
    question: str
    description: str
    default: str
    choices: Sequence[str] = ()
    example: str | None = None


class ConsoleAsker:
    """@brief Live console implementation of the prompt seam."""

    def __init__(self, stream: TextIO, input_fn: Callable[[str], str] = input) -> None:
        self._stream = stream
        self._input = input_fn

    def ask(self, field: FieldSpec) -> str:
        """@brief Render consequences and retry choices until one is valid."""
        while True:
            choices = f" [{' / '.join(field.choices)}]" if field.choices else ""
            self._stream.write(f"{field.question}{choices} (default: {field.default})\n")
            self._stream.write(f"  -> {field.description}\n")
            if field.example:
                self._stream.write(f"  e.g. {field.example}\n")
            self._stream.flush()
            value = self._input("> ").strip() or field.default
            if not field.choices or value in field.choices:
                return value
            self._stream.write(f"Choose one of: {', '.join(field.choices)}\n")


def parse_list(value: str) -> list[str]:
    """@brief Parse a comma-separated prompt answer into non-empty values."""
    result = [item.strip() for item in value.split(",") if item.strip()]
    if not result:
        raise ValueError("at least one value is required")
    return result


# END OF FILE
