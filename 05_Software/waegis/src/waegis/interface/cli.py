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
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from waegis.application.lifecycle import Application
from waegis.application.registry import OPERATIONS
from waegis.domain.results import OperationResult
from waegis.infrastructure.target import git_directory
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


def requested_operation(arguments: Sequence[str]) -> str:
    """Resolve the requested operation before application composition."""
    return next(
        (
            entry.operation
            for entry in OPERATIONS
            if entry.command in arguments or entry.operation in arguments
        ),
        "unknown",
    )


def configure_utf8(stream: TextIO) -> None:
    """Configure a process text stream for canonical UTF-8 and LF output."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="strict", newline="\n")


def _help_option(name: str, *, optional: bool) -> str:
    """Render one registry argument as readable command-line help."""
    token = name.replace("_", "-")
    rendered = f"--{token} <{token.upper()}>"
    return f"[{rendered}]" if optional else rendered


def _present_human_help(envelope: dict[str, object], stream: TextIO) -> None:
    """Render the structured help catalog as a concise operator reference."""
    print(
        f"WAEGIS {envelope['product_version']} - AEGIS lifecycle utility",
        file=stream,
    )
    print(file=stream)
    print("Usage:", file=stream)
    print("  waegis", file=stream)
    print("  waegis <command> [options]", file=stream)
    print("", file=stream)
    print("Run waegis without a command to start the guided setup.", file=stream)
    print(file=stream)
    print("Commands:", file=stream)
    data = envelope.get("data", {})
    operations = data.get("operations", []) if isinstance(data, dict) else []
    for operation in operations:
        if not isinstance(operation, dict):
            continue
        usage = [str(operation.get("command", ""))]
        usage.extend(
            _help_option(str(name), optional=False)
            for name in operation.get("required_arguments", [])
        )
        usage.extend(
            _help_option(str(name), optional=True)
            for name in operation.get("optional_arguments", [])
        )
        print(f"  {' '.join(usage)}", file=stream)
        print(f"      {operation.get('purpose', '')}", file=stream)
    print(file=stream)
    print("Lifecycle workflow:", file=stream)
    print(
        "  Create a plan, review it with plan-show, then apply the exact",
        file=stream,
    )
    print("  reviewed plan by confirming its sha256 digest.", file=stream)


def _result_exit_code(result: OperationResult) -> int:
    """Map one result to its documented process exit class."""
    if result.operation_status == "completed":
        return 0
    return _EXIT_CODES.get(result.error.code if result.error else "", 70)


def _wizard_prompt(stdin: TextIO, stdout: TextIO, prompt: str) -> str | None:
    """Read one interactive answer, returning None on end-of-input."""
    stdout.write(prompt)
    stdout.flush()
    answer = stdin.readline()
    if answer == "":
        return None
    return answer.strip()


def _wizard_confirm(
    stdin: TextIO,
    stdout: TextIO,
    prompt: str,
    *,
    default: bool,
) -> bool | None:
    """Read a bounded yes/no answer with an explicit default."""
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        answer = _wizard_prompt(stdin, stdout, prompt + suffix)
        if answer is None:
            return None
        if not answer:
            return default
        if answer.casefold() in {"y", "yes"}:
            return True
        if answer.casefold() in {"n", "no"}:
            return False
        print("Please answer Y or N.", file=stdout)


def _wizard_show_plan(
    app: Application,
    plan_path: Path,
    stdin: TextIO,
    stdout: TextIO,
) -> int:
    """Offer a readable, paged review of one exact lifecycle plan."""
    detailed = _wizard_confirm(
        stdin,
        stdout,
        "Review the individual planned actions now?",
        default=False,
    )
    if not detailed:
        return 0
    offset = 0
    while True:
        reviewed = app.execute(
            "plan-show",
            {"plan": str(plan_path), "offset": str(offset), "limit": "25"},
        )
        if reviewed.operation_status != "completed":
            return present_result(reviewed, "human", stdout)
        if offset == 0:
            print("", file=stdout)
            print("Plan action totals:", file=stdout)
            for kind, count in reviewed.data["action_counts_by_kind"].items():
                print(f"  {kind}: {count}", file=stdout)
        actions = reviewed.data["actions"]
        total = int(reviewed.data["action_count"])
        first = offset + 1
        last = offset + len(actions)
        print("", file=stdout)
        print(f"Actions {first}-{last} of {total}:", file=stdout)
        for action in actions:
            print(
                f"  {action['index'] + 1}. {action['kind']} {action['path']} "
                f"({action['ownership']})",
                file=stdout,
            )
        next_offset = reviewed.data["next_offset"]
        if next_offset is None:
            print("", file=stdout)
            print(
                f"Review complete: displayed all {total} actions (1-{total}).",
                file=stdout,
            )
            return 0
        continued = _wizard_confirm(
            stdin,
            stdout,
            "Show the next planned actions?",
            default=True,
        )
        if not continued:
            print(
                f"Review stopped after action {last} of {total}; "
                "remaining actions were not displayed.",
                file=stdout,
            )
            return 0
        offset = int(next_offset)


def _wizard_plan_and_apply(
    app: Application,
    *,
    operation: str,
    label: str,
    target: Path,
    plan_path: Path,
    stdin: TextIO,
    stdout: TextIO,
) -> tuple[int, bool]:
    """Create, summarize, review, and optionally apply one lifecycle plan."""
    create = _wizard_confirm(
        stdin,
        stdout,
        f"Create the {label.lower()} plan at {plan_path}?",
        default=True,
    )
    if not create:
        print(f"{label} canceled. The target repository was not changed.", file=stdout)
        return 0, False
    planned = app.execute(
        f"{operation}-plan",
        {"target": str(target), "output": str(plan_path)},
    )
    if planned.operation_status != "completed":
        return present_result(planned, "human", stdout), False
    print("", file=stdout)
    print("Plan created:", file=stdout)
    print(f"  File: {plan_path}", file=stdout)
    print(f"  Actions: {planned.data['action_count']}", file=stdout)
    warnings = list(planned.data.get("warnings", []))
    if warnings:
        print("  Findings:", file=stdout)
        for warning in warnings:
            print(f"    - {warning}", file=stdout)
    else:
        print("  Findings: none", file=stdout)
    digest = str(planned.data["plan_digest"])
    print(f"  Digest: {digest}", file=stdout)
    review_exit = _wizard_show_plan(app, plan_path, stdin, stdout)
    if review_exit != 0:
        return review_exit, False
    apply_plan = _wizard_confirm(
        stdin,
        stdout,
        "Apply this exact plan?",
        default=False,
    )
    if not apply_plan:
        print(
            f"{label} canceled. The target repository was not changed. "
            f"The reviewed plan remains at {plan_path}.",
            file=stdout,
        )
        return 0, False
    applied = app.execute(
        f"{operation}-apply",
        {
            "target": str(target),
            "plan": str(plan_path),
            "confirm_digest": digest,
        },
    )
    if applied.operation_status != "completed":
        return present_result(applied, "human", stdout), False
    return 0, True


def run_wizard(
    app: Application,
    *,
    git_available: bool,
    stdin: TextIO,
    stdout: TextIO,
) -> int:
    """Guide an unfamiliar developer through safe AEGIS adoption or upgrade."""
    print("Welcome to WAEGIS", file=stdout)
    print("", file=stdout)
    print(
        "This wizard installs or upgrades AEGIS in a software repository.",
        file=stdout,
    )
    print("You can cancel safely at any prompt before applying a plan.", file=stdout)
    print("", file=stdout)
    raw_target = _wizard_prompt(stdin, stdout, "Repository path: ")
    if not raw_target:
        print("Canceled. No target repository was changed.", file=stdout)
        return 0
    try:
        target = Path(raw_target.strip('"')).expanduser().resolve()
    except (OSError, RuntimeError):
        print("The repository path could not be resolved.", file=stdout)
        return 5
    if not target.is_dir():
        print("The repository path is not an existing directory.", file=stdout)
        return 5
    check = _wizard_confirm(
        stdin,
        stdout,
        "Check runtime and repository prerequisites?",
        default=True,
    )
    if not check:
        print("Canceled. No target repository was changed.", file=stdout)
        return 0
    python_compatible = sys.version_info[:2] == (3, 12)
    repository = git_directory(target) is not None
    installed = (target / ".agentic/aegis/manifest.toml").is_file()
    print("", file=stdout)
    print(
        f"Python 3.12: {'available' if python_compatible else 'not available'} "
        f"(running {sys.version_info.major}.{sys.version_info.minor}."
        f"{sys.version_info.micro})",
        file=stdout,
    )
    print(
        f"Git executable: {'available' if git_available else 'not available'}",
        file=stdout,
    )
    print(f"Target repository: accessible ({target})", file=stdout)
    print(f"Git repository: {'yes' if repository else 'no'}", file=stdout)
    print(f"AEGIS installed: {'yes' if installed else 'no'}", file=stdout)
    if not python_compatible:
        print("A compatible Python runtime is required before continuing.", file=stdout)
        return 5
    if not repository:
        if not git_available:
            print("Git is required to initialize this repository.", file=stdout)
            return 5
        initialize = _wizard_confirm(
            stdin,
            stdout,
            "Initialize this directory as a local Git repository?",
            default=False,
        )
        if not initialize:
            print("Canceled. No target repository was changed.", file=stdout)
            return 0
        init_path = target.parent / f"{target.name}-git-init.json"
        exit_code, initialized = _wizard_plan_and_apply(
            app,
            operation="repository-init",
            label="Repository initialization",
            target=target,
            plan_path=init_path,
            stdin=stdin,
            stdout=stdout,
        )
        if exit_code != 0 or not initialized:
            return exit_code
        print("Local Git repository initialized successfully.", file=stdout)
    operation = "upgrade" if installed else "install"
    label = "AEGIS upgrade" if installed else "Installation"
    plan_path = target.parent / f"{target.name}-aegis-{operation}.json"
    print("", file=stdout)
    exit_code, applied = _wizard_plan_and_apply(
        app,
        operation=operation,
        label=label,
        target=target,
        plan_path=plan_path,
        stdin=stdin,
        stdout=stdout,
    )
    if exit_code != 0 or not applied:
        return exit_code
    print("", file=stdout)
    success_message = (
        "AEGIS upgraded successfully."
        if installed
        else "AEGIS installed successfully."
    )
    print(
        success_message,
        file=stdout,
    )
    print("", file=stdout)
    print("Verify the installation:", file=stdout)
    if os.name == "nt":
        print(f'  cd /d "{target}"', file=stdout)
        launcher = ".agentic\\aegis\\bin\\aegis.cmd"
    else:
        print(f'  cd "{target}"', file=stdout)
        launcher = "./.agentic/aegis/bin/aegis"
    print(f"  {launcher} payload-verify", file=stdout)
    print(f"  {launcher} config-validate", file=stdout)
    return 0


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
    elif (
        envelope["operation"] == "help.show"
        and envelope["operation_status"] == "completed"
    ):
        _present_human_help(envelope, stream)
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
    return _result_exit_code(result)


def run_cli(
    app: Application,
    argv: Sequence[str] | None = None,
    *,
    git_available: bool = True,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Parse, execute, and present one WAEGIS operation."""
    arguments = list(argv or ())
    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    if not arguments:
        return run_wizard(
            app,
            git_available=git_available,
            stdin=input_stream,
            stdout=output_stream,
        )
    parser = ProtocolArgumentParser(prog="waegis")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for definition in OPERATIONS:
        child = subparsers.add_parser(definition.command, help=definition.purpose)
        for name in definition.arguments:
            child.add_argument(f"--{name.replace('_', '-')}", dest=name, required=True)
        for name in definition.optional_arguments:
            child.add_argument(f"--{name.replace('_', '-')}", dest=name)
    output_format = requested_output_format(arguments)
    operation = requested_operation(arguments)
    try:
        if "--help" in arguments or "-h" in arguments:
            result = app.execute("help-show", {})
        else:
            namespace = parser.parse_args(arguments)
            values = vars(namespace)
            command = values.pop("command")
            output_format = values.pop("format")
            if not git_available and operation == "repository_init.apply":
                result = app.error_result(
                    operation,
                    "missing_prerequisite",
                    "repository-init-apply requires Git on PATH.",
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
    return present_result(result, output_format, output_stream)
