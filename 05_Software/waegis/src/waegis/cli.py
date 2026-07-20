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
@details Defines the top-level ``waegis`` argument parser and registers each
         supported command through its dedicated subparser and real handler.
         New-project and adoption commands use a positional target, while
         existing-install commands use their documented ``--repo`` contracts.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.7.0
"""

# IMPORTS

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .commands.adopt import run_adopt
from .commands.analyze import run_analyze
from .commands.configure import run_configure
from .commands.doctor import run_doctor
from .commands.new import run_new
from .commands.repair import run_repair
from .commands.upgrade import run_upgrade
from .commands.version import run_version
from .io.envelope import EXIT_OPERATIONAL, EXIT_VALIDATION, command_envelope, write_envelope
from .io.prompts import ConsoleAsker
from .runtime import RuntimeRegistrationError, register_packaged_runtime
from .version import WIZARD_VERSION

# CONSTANTS

# @brief Planned subcommands (plan §5) as ``(name, help)`` pairs. Registered in
#        order so ``waegis --help`` lists the full CLI surface from 0.1.0.
SUBCOMMANDS: tuple[tuple[str, str], ...] = (
    ("new", "Configure and deploy AEGIS into a brand-new project"),
    ("adopt", "Configure and deploy AEGIS into an existing repository"),
    ("analyze", "Report install manifest, drift, and installed workflows"),
    ("configure", "Regenerate owned workflow configuration fields"),
    ("doctor", "Diagnose an AEGIS install and report health (exit 0/1/2)"),
    ("repair", "Repair missing or damaged managed AEGIS files"),
    ("upgrade", "Move a repository to a newer AEGIS payload"),
    ("version", "Print the wizard version and bundled payload version"),
)

# @brief Parse context used only to preserve the one-envelope ``--json`` rule
#        for errors raised before a command handler exists.
_PARSE_ARGV: tuple[str, ...] = ()


class _WaegisArgumentParser(argparse.ArgumentParser):
    """
    @brief Argument parser that renders syntax failures as JSON when requested.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-16
    @version 0.1.0
    """

    def error(self, message: str) -> None:
        """@brief Emit one JSON envelope or delegate to argparse's human error."""
        if "--json" in _PARSE_ARGV:
            command = next((item for item in _PARSE_ARGV if item in dict(SUBCOMMANDS)), "waegis")
            payload = command_envelope(
                command,
                status="failed",
                exit_code=EXIT_VALIDATION,
                messages=(message,),
            )
            sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
            raise SystemExit(EXIT_VALIDATION)
        super().error(message)


# LOCAL HELPERS


def _handle_new(args: argparse.Namespace) -> int:
    """
    @brief      Adapt parsed ``waegis new`` arguments to :func:`run_new`.
    @param[in]  args Parsed namespace with ``target``, ``answers``, ``dry_run``,
                ``non_interactive``, ``json``, and ``payload``.
    @return     The exit code from :func:`run_new`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    return run_new(
        Path(args.target),
        stream=sys.stdout,
        answers_path=args.answers,
        dry_run=args.dry_run,
        non_interactive=args.non_interactive,
        yes=args.yes,
        as_json=args.json,
        payload=args.payload,
    )


def _add_new_parser(sub: argparse._SubParsersAction) -> None:
    """
    @brief      Register the ``new`` subparser with its deployment arguments.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.2.0
    """
    parser = sub.add_parser("new", help=dict(SUBCOMMANDS)["new"])
    parser.add_argument("target", metavar="TARGET", help="Directory to create the new AEGIS project in")
    parser.add_argument("--answers", help="TOML or JSON answers file pre-supplying interview answers")
    parser.add_argument("--dry-run", action="store_true", help="Show the plan preview and stop; change nothing")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Never prompt; fail loudly listing every missing required answer",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of human output")
    parser.add_argument("--yes", action="store_true", help="Approve the rendered plan without prompting")
    parser.add_argument("--payload", help="Override payload resolution with an explicit payload root")
    parser.set_defaults(handler=_handle_new)


def _handle_adopt(args: argparse.Namespace) -> int:
    """
    @brief      Adapt parsed ``waegis adopt`` arguments to :func:`run_adopt`.
    @param[in]  args Parsed namespace with ``target``, ``answers``, ``dry_run``,
                ``non_interactive``, ``json``, and ``payload``.
    @return     The exit code from :func:`run_adopt`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    return run_adopt(
        Path(args.target),
        stream=sys.stdout,
        answers_path=args.answers,
        dry_run=args.dry_run,
        non_interactive=args.non_interactive,
        yes=args.yes,
        as_json=args.json,
        payload=args.payload,
    )


def _add_adopt_parser(sub: argparse._SubParsersAction) -> None:
    """
    @brief      Register the ``adopt`` subparser with its deployment arguments.
    @details    The flag shape is identical to ``new`` (frozen cross-command CLI
                contract per plan §15/D13).
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.2.0
    """
    parser = sub.add_parser("adopt", help=dict(SUBCOMMANDS)["adopt"])
    parser.add_argument("target", metavar="TARGET", help="Existing repository to adopt AEGIS into")
    parser.add_argument("--answers", help="TOML or JSON answers file pre-supplying interview answers")
    parser.add_argument("--dry-run", action="store_true", help="Show the plan preview and stop; change nothing")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Never prompt; fail loudly listing every missing required answer",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of human output")
    parser.add_argument("--yes", action="store_true", help="Approve the rendered plan without prompting")
    parser.add_argument("--payload", help="Override payload resolution with an explicit payload root")
    parser.set_defaults(handler=_handle_adopt)


def _handle_analyze(args: argparse.Namespace) -> int:
    """
    @brief      Adapt parsed ``waegis analyze`` arguments to :func:`run_analyze`.
    @param[in]  args Parsed namespace with ``repo`` (str) and ``json`` (bool).
    @return     The exit code from :func:`run_analyze`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    return run_analyze(Path(args.repo), as_json=args.json, stream=sys.stdout)


def _add_analyze_parser(sub: argparse._SubParsersAction) -> None:
    """
    @brief      Register the ``analyze`` subparser with ``--repo`` and
                ``--json`` arguments.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.2.0
    """
    parser = sub.add_parser("analyze", help=dict(SUBCOMMANDS)["analyze"])
    parser.add_argument("--repo", required=True, help="Repository root to analyze")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a human report")
    parser.set_defaults(handler=_handle_analyze)


def _handle_configure(args: argparse.Namespace) -> int:
    """@brief Adapt parsed ``configure`` arguments to :func:`run_configure`."""
    return run_configure(
        Path(args.repo),
        stream=sys.stdout,
        answers_path=args.answers,
        dry_run=args.dry_run,
        non_interactive=args.non_interactive,
        yes=args.yes,
        as_json=args.json,
        payload=args.payload,
        stdin=sys.stdin,
    )


def _add_configure_parser(sub: argparse._SubParsersAction) -> None:
    """@brief Register the post-install configuration command."""
    parser = sub.add_parser("configure", help=dict(SUBCOMMANDS)["configure"])
    parser.add_argument("--repo", required=True, help="Repository root to configure")
    parser.add_argument("--answers", help="TOML or JSON configuration answers")
    parser.add_argument("--dry-run", action="store_true", help="Render the resolved field changes only")
    parser.add_argument("--non-interactive", action="store_true", help="Never prompt")
    parser.add_argument("--yes", action="store_true", help="Approve the rendered plan without prompting")
    parser.add_argument("--json", action="store_true", help="Emit one machine-readable JSON envelope")
    parser.add_argument("--payload", help="Override payload resolution")
    parser.set_defaults(handler=_handle_configure)


def _handle_repair(args: argparse.Namespace) -> int:
    """@brief Adapt parsed ``repair`` arguments to :func:`run_repair`."""
    return run_repair(
        Path(args.repo),
        stream=sys.stdout,
        answers_path=args.answers,
        dry_run=args.dry_run,
        non_interactive=args.non_interactive,
        yes=args.yes,
        as_json=args.json,
        payload=args.payload,
        stdin=sys.stdin,
    )


def _add_repair_parser(sub: argparse._SubParsersAction) -> None:
    """@brief Register the transactional repair command."""
    parser = sub.add_parser("repair", help=dict(SUBCOMMANDS)["repair"])
    parser.add_argument("--repo", required=True, help="Repository root to repair")
    parser.add_argument("--answers", help="TOML or JSON repair decisions/configuration answers")
    parser.add_argument("--dry-run", action="store_true", help="Render the resolved repair plan only")
    parser.add_argument("--non-interactive", action="store_true", help="Never prompt")
    parser.add_argument("--yes", action="store_true", help="Approve the rendered plan without prompting")
    parser.add_argument("--json", action="store_true", help="Emit one machine-readable JSON envelope")
    parser.add_argument("--payload", help="Override payload resolution")
    parser.set_defaults(handler=_handle_repair)


def _handle_doctor(args: argparse.Namespace) -> int:
    """
    @brief      Adapt parsed ``waegis doctor`` arguments to :func:`run_doctor`.
    @param[in]  args Parsed namespace with ``repo`` (str) and ``json`` (bool).
    @return     The exit code from :func:`run_doctor` (0/1/2 health verdict,
                or 3 for a ``--repo`` operational failure).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    return run_doctor(Path(args.repo), as_json=args.json, stream=sys.stdout)


def _add_doctor_parser(sub: argparse._SubParsersAction) -> None:
    """
    @brief      Register the ``doctor`` subparser with ``--repo`` and
                ``--json`` arguments.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.2.0
    """
    parser = sub.add_parser("doctor", help=dict(SUBCOMMANDS)["doctor"])
    parser.add_argument("--repo", required=True, help="Repository root to diagnose")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a human report")
    parser.set_defaults(handler=_handle_doctor)


def _handle_upgrade(args: argparse.Namespace) -> int:
    """
    @brief      Adapt parsed ``waegis upgrade`` arguments to :func:`run_upgrade`.
    @details    The parser accepts ``--repo``, ``--dry-run``, ``--answers``,
                ``--non-interactive``, ``--yes``, ``--json``, and ``--payload``.
                Interactive human output uses :class:`ConsoleAsker`; JSON mode
                supplies no asker and never guesses conflict decisions.
    @param[in]  args Parsed namespace containing the documented upgrade flags.
    @return     The exit code from :func:`run_upgrade` (0 ok / 1 conflicts /
                2 smoke-failed / 3 operational).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.2.0
    """
    asker = None if args.json else ConsoleAsker(stdin=sys.stdin, stdout=sys.stdout)
    return run_upgrade(
        Path(args.repo),
        as_json=args.json,
        dry_run=args.dry_run,
        stream=sys.stdout,
        payload=args.payload,
        answers_path=args.answers,
        non_interactive=args.non_interactive,
        yes=args.yes,
        asker=asker,
    )


def _add_upgrade_parser(sub: argparse._SubParsersAction) -> None:
    """
    @brief      Register the ``upgrade`` subparser for an existing installation.
    @details    Supports dry runs, answers files, non-interactive approval,
                JSON output, and an explicit payload override.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.2.0
    """
    parser = sub.add_parser("upgrade", help=dict(SUBCOMMANDS)["upgrade"])
    parser.add_argument("--repo", required=True, help="Repository root to upgrade to a newer AEGIS payload")
    parser.add_argument("--dry-run", action="store_true", help="Show the upgrade plan and stop; change nothing")
    parser.add_argument("--answers", help="TOML or JSON conflict decisions and Git-mode answers")
    parser.add_argument("--non-interactive", action="store_true", help="Never prompt")
    parser.add_argument("--yes", action="store_true", help="Approve the fully resolved plan without prompting")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a human report")
    parser.add_argument("--payload", help="Override payload resolution with an explicit new payload root")
    parser.set_defaults(handler=_handle_upgrade)


def _handle_version(args: argparse.Namespace) -> int:
    """@brief Adapt parsed ``version`` arguments to :func:`run_version`."""
    return run_version(as_json=args.json, stream=sys.stdout)


def _add_version_parser(sub: argparse._SubParsersAction) -> None:
    """@brief Register the real version command."""
    parser = sub.add_parser("version", help=dict(SUBCOMMANDS)["version"])
    parser.add_argument("--json", action="store_true", help="Emit one machine-readable JSON envelope")
    parser.set_defaults(handler=_handle_version)


def build_parser() -> argparse.ArgumentParser:
    """
    @brief      Build the top-level parser with one dedicated subparser and
                handler for every supported WAEGIS command.
    @return     Configured :class:`argparse.ArgumentParser`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.7.0
    """
    parser = _WaegisArgumentParser(
        prog="waegis",
        description=(
            "WAEGIS - guided configuration and deployment wizard for AEGIS "
            f"(wizard {WIZARD_VERSION})."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_new_parser(sub)
    _add_adopt_parser(sub)
    _add_analyze_parser(sub)
    _add_configure_parser(sub)
    _add_doctor_parser(sub)
    _add_repair_parser(sub)
    _add_upgrade_parser(sub)
    _add_version_parser(sub)
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
    global _PARSE_ARGV  # noqa: PLW0603 - parser error hook needs the active argv
    active_argv = tuple(sys.argv[1:] if argv is None else argv)
    try:
        register_packaged_runtime()
    except RuntimeRegistrationError as exc:
        command = next((item for item in active_argv if item in dict(SUBCOMMANDS)), "waegis")
        if "--json" in active_argv:
            return write_envelope(
                sys.stdout,
                command,
                status="error",
                exit_code=EXIT_OPERATIONAL,
                messages=(str(exc),),
            )
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_OPERATIONAL
    _PARSE_ARGV = active_argv
    parser = build_parser()
    args = parser.parse_args(active_argv)
    return args.handler(args)


# END OF FILE
