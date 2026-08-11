#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Expose the registry-derived flat WAEGIS CLI without interactive mutation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from waegis.application.lifecycle import Application
from waegis.application.registry import OPERATIONS
from waegis.version import PROTOCOL_VERSION

_EXIT_CODES = {
    "invalid_input": 2,
    "state_conflict": 4,
    "malformed_state": 4,
    "invalid_transition": 4,
    "repository_error": 5,
    "missing_prerequisite": 5,
    "publication_failed": 6,
    "internal_error": 70,
}


class CliInputError(ValueError):
    """Carry an argparse failure into the structured protocol boundary."""


class ProtocolArgumentParser(argparse.ArgumentParser):
    """Raise on malformed input instead of printing and terminating."""

    def error(self, message: str) -> None:
        """Raise one bounded parse error."""
        raise CliInputError(message)


def run_cli(app: Application, argv: Sequence[str] | None = None) -> int:
    """Parse, execute, and present one WAEGIS operation."""
    arguments = list(argv or ())
    parser = ProtocolArgumentParser(prog="waegis")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for definition in OPERATIONS:
        child = subparsers.add_parser(definition.command, help=definition.purpose)
        for name in definition.arguments:
            child.add_argument(f"--{name.replace('_', '-')}", dest=name, required=True)
    output_format = "json" if "json" in arguments else "human"
    operation = next(
        (
            entry.operation
            for entry in OPERATIONS
            if entry.command in arguments or entry.operation in arguments
        ),
        "unknown",
    )
    try:
        if "--help" in arguments or "-h" in arguments:
            result = app.execute("help-show", {})
        else:
            namespace = parser.parse_args(arguments)
            values = vars(namespace)
            command = values.pop("command")
            output_format = values.pop("format")
            result = app.execute(command, values)
    except KeyboardInterrupt:
        result = app.error_result(
            operation,
            "internal_error",
            "The WAEGIS invocation was interrupted before completion.",
        )
    except CliInputError:
        result = app.error_result(
            operation,
            "invalid_input",
            "The command arguments are invalid.",
            field="arguments",
        )
    if output_format == "json":
        print(
            json.dumps(
                result.to_envelope(PROTOCOL_VERSION),
                ensure_ascii=False,
                allow_nan=False,
            )
        )
    else:
        envelope = result.to_envelope(PROTOCOL_VERSION)
        print(envelope["message"])
        print(f"Operation: {envelope['operation']}")
        print(f"Status: {envelope['operation_status']}")
        print(f"Product: {envelope['product']} {envelope['product_version']}")
        for key, value in envelope["data"].items():
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        if envelope["error"]:
            print(f"Error: {envelope['error']['code']}: {envelope['error']['summary']}")
    if result.operation_status == "completed":
        return 0
    return _EXIT_CODES.get(result.error.code if result.error else "", 70)
