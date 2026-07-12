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
@brief Command-line entry point for the WAEGIS guided wizard.
@details Defines the top-level ``waegis`` argument parser and registers every
         planned subcommand of the CLI contract (plan §5). In this scaffold each
         subcommand is a stub that reports "not implemented" and exits with code
         2; later tasks replace the stubs with real command handlers. The exit
         codes are part of the public contract from 0.1.0 onward (AD-9/D13).
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import argparse
import sys

from .version import WIZARD_VERSION

# CONSTANTS

# @brief Exit code returned by not-yet-implemented subcommand stubs.
EXIT_NOT_IMPLEMENTED = 2

# @brief Planned subcommands (plan §5) as ``(name, help)`` pairs. Registered in
#        order so ``waegis --help`` lists the full CLI surface from 0.1.0.
SUBCOMMANDS: tuple[tuple[str, str], ...] = (
    ("new", "Configure and deploy AEGIS into a brand-new project"),
    ("adopt", "Configure and deploy AEGIS into an existing repository"),
    ("analyze", "Report install manifest, drift, and installed workflows"),
    ("doctor", "Diagnose an AEGIS install and report health (exit 0/1/2)"),
    ("upgrade", "Move a repository to a newer AEGIS payload"),
    ("version", "Print the wizard version and bundled payload version"),
    ("self-update", "Update the wizard itself (opt-in, staged side-by-side)"),
    ("gui", "Serve the local-web wizard frontend on 127.0.0.1"),
)


# LOCAL HELPERS


def _make_stub(name: str):
    """
    @brief      Build a subcommand handler that reports a not-implemented stub.
    @param[in]  name Subcommand name used in the diagnostic message.
    @return     Callable taking parsed arguments and returning the
                not-implemented exit code (:data:`EXIT_NOT_IMPLEMENTED`).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """

    def _handler(_args: argparse.Namespace) -> int:
        print(f"waegis {name}: not implemented", file=sys.stderr)
        return EXIT_NOT_IMPLEMENTED

    return _handler


def build_parser() -> argparse.ArgumentParser:
    """
    @brief      Build the top-level ``waegis`` argument parser with every planned
                subcommand registered as a stub.
    @return     Configured :class:`argparse.ArgumentParser`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    parser = argparse.ArgumentParser(
        prog="waegis",
        description=(
            "WAEGIS - guided configuration and deployment wizard for AEGIS "
            f"(wizard {WIZARD_VERSION})."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in SUBCOMMANDS:
        stub = sub.add_parser(name, help=help_text)
        stub.set_defaults(handler=_make_stub(name))
    return parser


# EXPORTED FUNCTIONS / PUBLIC API


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Parse arguments and dispatch to the selected subcommand handler.
    @param[in]  argv Optional argument vector; defaults to ``sys.argv[1:]``.
    @return     Integer process exit code produced by the subcommand handler.
    @exception  SystemExit Raised by argparse for ``--help`` (code 0) or for a
                           missing/invalid subcommand (code 2).
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


# END OF FILE
