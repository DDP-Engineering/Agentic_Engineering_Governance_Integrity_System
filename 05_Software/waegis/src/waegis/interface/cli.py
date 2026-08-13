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
import sys
from collections.abc import Sequence
from typing import TextIO

from waegis.application.lifecycle import Application
from waegis.application.registry import OPERATIONS
from waegis.domain.results import OperationResult
from waegis.version import PROTOCOL_VERSION

_EXIT_CODES = {
    "invalid_input": 2,
    "not_found": 3,
    "ambiguous_run": 3,
    "invalid_transition": 4,
    "state_conflict": 4,
    "malformed_state": 4,
    "unsupported_schema": 4,
    "capability_unavailable": 4,
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


def requested_output_format(arguments: Sequence[str]) -> str:
    """Parse the requested presentation mode independently of command errors."""
    parser = ProtocolArgumentParser(prog="waegis", add_help=False)
    parser.add_argument("--format", choices=("human", "json"), default="human")
    try:
        namespace, _unknown = parser.parse_known_args(arguments)
    except CliInputError:
        return "human"
    return str(namespace.format)


def configure_utf8(stream: TextIO) -> None:
    """Configure a process text stream for canonical UTF-8 and LF output."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="strict", newline="\n")


def present_result(
    result: OperationResult,
    output_format: str,
    stdout: TextIO | None = None,
) -> int:
    """Write one result through the selected protocol presenter."""
    stream = sys.stdout if stdout is None else stdout
    envelope = result.to_envelope(PROTOCOL_VERSION)
    if output_format == "json":
        stream.write(
            json.dumps(
                envelope,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )
        stream.write("\n")
    else:
        print(envelope["message"], file=stream)
        print(f"Operation: {envelope['operation']}", file=stream)
        print(f"Status: {envelope['operation_status']}", file=stream)
        print(
            f"Product: {envelope['product']} {envelope['product_version']}",
            file=stream,
        )
        for key, value in envelope["data"].items():
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}", file=stream)
        if envelope["error"]:
            print(
                f"Error: {envelope['error']['code']}: {envelope['error']['summary']}",
                file=stream,
            )
    if result.operation_status == "completed":
        return 0
    return _EXIT_CODES.get(result.error.code if result.error else "", 70)


def run_cli(
    app: Application,
    argv: Sequence[str] | None = None,
    *,
    git_available: bool = True,
) -> int:
    """Parse, execute, and present one WAEGIS operation."""
    arguments = list(argv or ())
    parser = ProtocolArgumentParser(prog="waegis")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for definition in OPERATIONS:
        child = subparsers.add_parser(definition.command, help=definition.purpose)
        for name in definition.arguments:
            child.add_argument(f"--{name.replace('_', '-')}", dest=name, required=True)
    output_format = requested_output_format(arguments)
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
            if not git_available and operation not in {"help.show", "version.show"}:
                result = app.error_result(
                    operation,
                    "missing_prerequisite",
                    "WAEGIS requires Git on PATH.",
                )
            else:
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
    return present_result(result, output_format)
