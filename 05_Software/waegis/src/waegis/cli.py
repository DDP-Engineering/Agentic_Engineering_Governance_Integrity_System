#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file cli.py
@brief WAEGIS 3 command-line surface and exit mapping.
@details Defines the complete V2 command vocabulary while Phase 1 exposes only
         the read-only version implementation. Later phases attach command
         orchestrators without changing this package boundary.
"""

# IMPORTS

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence, TextIO

from .envelope import ResultEnvelope
from .locate import PayloadError, resolve_payload
from .version import MANIFEST_VERSION, PAYLOAD_COMPAT_SPEC, WIZARD_VERSION


# CONSTANTS

EXIT_OK = 0
EXIT_WARNING = 1
EXIT_ERROR = 2
EXIT_NEEDS_INPUT = 3


# HELPER FUNCTIONS


def _add_repo(parser: argparse.ArgumentParser, *, include_json: bool = True) -> None:
    parser.add_argument("--repo", type=Path, required=True, help="target Git repository")
    if include_json:
        parser.add_argument("--json", action="store_true", help="emit one JSON result")


def _add_mutation_options(parser: argparse.ArgumentParser, *, payload: bool = False) -> None:
    if payload:
        parser.add_argument("--payload", type=Path, help="explicit AEGIS payload directory")
    parser.add_argument("--answers", type=Path, help="V2 JSON or TOML answers file")
    parser.add_argument("--non-interactive", action="store_true", help="never prompt")
    parser.add_argument("--yes", action="store_true", help="approve a complete rendered plan")
    parser.add_argument("--dry-run", action="store_true", help="render the plan without mutation")
    parser.add_argument("--break-lock", action="store_true", help="break a confirmed dead-owner lock")
    parser.add_argument("--json", action="store_true", help="emit one JSON result")


def _emit_error(command: str, message: str, as_json: bool, out: TextIO, err: TextIO) -> int:
    if as_json:
        out.write(ResultEnvelope(command, "failed", EXIT_ERROR, messages=(message,)).render())
    else:
        err.write(f"waegis {command}: {message}\n")
    return EXIT_ERROR


def _run_version(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    try:
        _, payload_version, inventory = resolve_payload(args.payload)
    except PayloadError as exc:
        return _emit_error("version", str(exc), args.json, out, err)
    result = {
        "waegis_version": WIZARD_VERSION,
        "bundled_payload_version": payload_version,
        "compatible_payload_range": PAYLOAD_COMPAT_SPEC,
        "payload_digest": inventory.digest,
        "manifest_schema": MANIFEST_VERSION,
        "packaging_type": os.environ.get("WAEGIS_PACKAGING_TYPE", "source-checkout"),
    }
    if args.json:
        out.write(ResultEnvelope("version", "ok", EXIT_OK, result=result).render())
    else:
        out.write(
            f"WAEGIS {WIZARD_VERSION}\n"
            f"AEGIS payload {payload_version} ({PAYLOAD_COMPAT_SPEC})\n"
            f"manifest schema {MANIFEST_VERSION}\n"
            f"packaging {result['packaging_type']}\n"
        )
    return EXIT_OK


def _run_pending(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    return _emit_error(args.command, "command implementation is not available in the Phase 1 scaffold", args.json, out, err)


# EXPORTED FUNCTIONS / PUBLIC API


def build_parser() -> argparse.ArgumentParser:
    """@brief Build the stable WAEGIS 3 command parser."""
    parser = argparse.ArgumentParser(
        prog="waegis",
        description=f"WAEGIS {WIZARD_VERSION} - guided AEGIS 3 deployment",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    new = commands.add_parser("new", help="install AEGIS into an absent target")
    new.add_argument("target", type=Path)
    _add_mutation_options(new, payload=True)

    adopt = commands.add_parser("adopt", help="install AEGIS into a clean existing repository")
    adopt.add_argument("target", type=Path)
    _add_mutation_options(adopt, payload=True)

    analyze = commands.add_parser("analyze", help="analyze repository evidence without mutation")
    _add_repo(analyze)

    configure = commands.add_parser("configure", help="edit WAEGIS-owned workflow policy")
    _add_repo(configure, include_json=False)
    _add_mutation_options(configure, payload=True)

    check = commands.add_parser("check", help="inspect AEGIS installation health")
    _add_repo(check)

    doctor = commands.add_parser("doctor", help="alias for check")
    _add_repo(doctor)

    repair = commands.add_parser("repair", help="restore approved managed payload files")
    _add_repo(repair, include_json=False)
    _add_mutation_options(repair, payload=True)

    upgrade = commands.add_parser("upgrade", help="apply an ownership-aware AEGIS 3 upgrade")
    _add_repo(upgrade, include_json=False)
    _add_mutation_options(upgrade, payload=True)

    version = commands.add_parser("version", help="report WAEGIS and bundled AEGIS versions")
    version.add_argument("--payload", type=Path, help="explicit AEGIS payload directory")
    version.add_argument("--json", action="store_true", help="emit one JSON result")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """
    @brief Parse and run one WAEGIS command.
    @param[in] argv Optional argument sequence excluding executable name.
    @param[in] stdout Injectable output stream.
    @param[in] stderr Injectable diagnostics stream.
    @return Stable process exit code.
    """
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    args = build_parser().parse_args(argv)
    if args.command == "version":
        return _run_version(args, out, err)
    return _run_pending(args, out, err)


# END OF FILE
