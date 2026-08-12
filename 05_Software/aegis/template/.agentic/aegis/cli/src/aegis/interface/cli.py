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
@file    cli.py
@brief   Parse flat AEGIS commands and enforce the outer protocol boundary.
@details Generates argparse subparsers from the central operation registry.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import Any, TextIO

from aegis import PRODUCT_NAME, PROTOCOL_VERSION
from aegis.application.dispatcher import Dispatcher
from aegis.application.operation_registry import find_command, operations_for
from aegis.domain.results import OperationResult
from aegis.interface.human_presenter import render_human
from aegis.interface.input import MachineInputError, load_machine_input
from aegis.interface.json_presenter import render_json

# -----------------------------------------------------------------------------
# CONSTANTS
# -----------------------------------------------------------------------------

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


# -----------------------------------------------------------------------------
# DATA MODELS / TYPEDEFINITIONS
# -----------------------------------------------------------------------------


class _CliInputError(Exception):
    """@brief Carry an argparse failure into the structured outer boundary."""


class _ProtocolArgumentParser(argparse.ArgumentParser):
    """@brief Raise instead of writing usage and exiting."""

    def error(self, message: str) -> None:
        """@exception _CliInputError Always, with the bounded parser message."""
        raise _CliInputError(message)


# -----------------------------------------------------------------------------
# LOCAL HELPERS
# -----------------------------------------------------------------------------


def _build_parser() -> _ProtocolArgumentParser:
    parser = _ProtocolArgumentParser(
        prog="aegis",
        add_help=False,
        description="AEGIS version 1 repository governance protocol.",
    )
    parser.add_argument("--repo")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    parser.add_argument("--protocol-version", type=int, default=PROTOCOL_VERSION)
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--expected-revision")
    parser.add_argument("--help", action="store_true", dest="root_help")
    subparsers = parser.add_subparsers(dest="command")
    for entry in operations_for(PRODUCT_NAME):
        command_parser = subparsers.add_parser(
            entry.command,
            add_help=False,
            help=entry.purpose,
            description=entry.purpose,
        )
        command_parser.add_argument("--help", action="store_true", dest="command_help")
        for argument in entry.arguments:
            settings: dict[str, Any] = {"help": argument.description}
            if argument.metavar is not None:
                settings["metavar"] = argument.metavar
            if argument.choices:
                settings["choices"] = argument.choices
            if argument.positional:
                settings["nargs"] = "?"
                command_parser.add_argument(argument.name, **settings)
            else:
                command_parser.add_argument(
                    *argument.flags,
                    dest=argument.name,
                    **settings,
                )
    return parser


def _requested_format(arguments: Sequence[str]) -> str:
    for index, argument in enumerate(arguments):
        if argument == "--format" and index + 1 < len(arguments):
            return "json" if arguments[index + 1] == "json" else "human"
        if argument == "--format=json":
            return "json"
    return "human"


def _operation_hint(arguments: Sequence[str]) -> str:
    for argument in arguments:
        entry = find_command(argument, PRODUCT_NAME)
        if entry is not None:
            return entry.operation
    return "unknown"


def _safe_error_result(
    dispatcher: Any,
    *,
    operation: str,
    code: str,
    summary: str,
    field: str | None = None,
    details: dict[str, Any] | None = None,
) -> OperationResult:
    return dispatcher.error_result(
        operation=operation,
        code=code,
        summary=summary,
        field=field,
        details=details,
    )


def _exit_code(result: OperationResult) -> int:
    if result.operation_status == "completed":
        return 0
    if result.error is None:
        return 70
    return _EXIT_CODES.get(result.error.code, 70)


def _present(result: OperationResult, output_format: str, stdout: TextIO) -> None:
    if output_format == "json":
        stdout.write(render_json(result, PROTOCOL_VERSION))
    else:
        stdout.write(render_human(result))
    stdout.write("\n")


def configure_utf8(stream: TextIO) -> None:
    """@brief Configure a process text stream for canonical UTF-8 and LF."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="strict", newline="\n")


# -----------------------------------------------------------------------------
# EXPORTED FUNCTIONS / PUBLIC API
# -----------------------------------------------------------------------------


def run_cli(
    arguments: Sequence[str],
    *,
    stdin: TextIO | None = None,
    stdout: TextIO,
    stderr: TextIO,
    dispatcher: Dispatcher | Any,
) -> int:
    """
    @brief Execute one CLI request without terminating the host process.
    @param[in] arguments CLI argument tokens excluding executable name.
    @param[out] stdout Selected protocol output stream.
    @param[out] stderr Reserved error stream; kept empty after protocol start.
    @param[in] dispatcher Optional injected dispatcher for deterministic tests.
    @return Protocol exit class.
    """
    del stderr
    application = dispatcher
    input_stream = sys.stdin if stdin is None else stdin
    output_format = _requested_format(arguments)
    operation = _operation_hint(arguments)

    try:
        parser = _build_parser()
        namespace = parser.parse_args(arguments)
        output_format = namespace.format
        repository = None

        if namespace.protocol_version != PROTOCOL_VERSION:
            result = _safe_error_result(
                application,
                operation=operation,
                code="unsupported_schema",
                summary="The requested protocol version is not supported.",
                field="protocol_version",
                details={
                    "requested": namespace.protocol_version,
                    "supported": PROTOCOL_VERSION,
                },
            )
        elif namespace.root_help or namespace.command is None:
            if namespace.command is None and not namespace.root_help:
                result = _safe_error_result(
                    application,
                    operation="unknown",
                    code="invalid_input",
                    summary="One canonical command is required.",
                    field="command",
                )
            else:
                result = application.dispatch("help.show", {"operation": None})
        else:
            entry = find_command(namespace.command, PRODUCT_NAME)
            if entry is None:
                result = _safe_error_result(
                    application,
                    operation="unknown",
                    code="invalid_input",
                    summary="The requested command is not recognized.",
                    field="command",
                )
            elif getattr(namespace, "command_help", False):
                result = application.dispatch(
                    "help.show",
                    {"operation": entry.operation},
                )
            else:
                missing = [
                    argument.display_name
                    for argument in entry.arguments
                    if argument.required
                    and getattr(namespace, argument.name, None) is None
                ]
                if missing:
                    result = _safe_error_result(
                        application,
                        operation=entry.operation,
                        code="invalid_input",
                        summary="The command arguments are invalid.",
                        field="arguments",
                        details={"missing": missing},
                    )
                else:
                    inputs = {
                        argument.name: value
                        for argument in entry.arguments
                        if (value := getattr(namespace, argument.name, None))
                        is not None
                    }
                    source = inputs.pop("input", None)
                    if source is not None:
                        structured = load_machine_input(
                            source,
                            stdin=input_stream,
                            operation=entry.operation,
                        )
                        conflicts = sorted(set(inputs).intersection(structured))
                        if conflicts:
                            raise MachineInputError(
                                "A field was supplied through both CLI and "
                                "structured input."
                            )
                        inputs.update(structured)
                    if namespace.expected_revision is not None:
                        inputs["expected_revision"] = namespace.expected_revision
                    repository_free = entry.operation in {
                        "help.show",
                        "version.show",
                    }
                    if namespace.repo is not None or not repository_free:
                        repository, repository_error = application.resolve_repository(
                            namespace.repo or os.getcwd(),
                            operation=entry.operation,
                        )
                        if repository_error is not None:
                            result = repository_error
                        else:
                            result = application.dispatch(
                                entry.operation,
                                inputs,
                                repository=None if repository_free else repository,
                                machine_mode=output_format == "json",
                            )
                    else:
                        result = application.dispatch(entry.operation, inputs)
    except MachineInputError as error:
        result = _safe_error_result(
            application,
            operation=operation,
            code="invalid_input",
            summary=str(error),
            field="input",
        )
    except _CliInputError as error:
        result = _safe_error_result(
            application,
            operation=operation,
            code="invalid_input",
            summary="The command arguments are invalid.",
            field="arguments",
            details={"reason": str(error)},
        )
    except KeyboardInterrupt:
        result = _safe_error_result(
            application,
            operation=operation,
            code="internal_error",
            summary="The AEGIS invocation was interrupted before completion.",
        )
    except Exception:
        result = _safe_error_result(
            application,
            operation=operation,
            code="internal_error",
            summary="An unexpected AEGIS failure prevented completion.",
        )

    _present(result, output_format, stdout)
    return _exit_code(result)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
