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
         planned subcommand of the CLI contract (plan §5). Most subcommands are
         still stubs that report "not implemented" and exit with code 2; later
         tasks replace them with real command handlers one at a time.
         ``analyze`` (T3.3) was the first real handler; ``new`` (T4.3) the
         second, ``adopt`` (T5.2) the third, ``doctor`` (T6.1) the fourth, and
         ``upgrade`` (T6.2) the fifth, all wiring the plan §5 contract.
         ``doctor`` and ``upgrade`` use their own ``--repo``/``--json`` shape
         (matching ``analyze``, not ``new``/``adopt``'s ``TARGET``-based shape)
         since they operate on an existing install rather than deploying one.
         Only ``version``, ``self-update``, and ``gui`` remain generic
         not-implemented stubs after this task. The exit codes are part of the
         public contract from 0.1.0 onward (AD-9/D13).
@author Eng. Dan Dumitru Pasare
@date 2026-07-15
@version 0.6.0
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

# @brief Exit code returned by not-yet-implemented subcommand stubs.
EXIT_NOT_IMPLEMENTED = 2

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
    @brief      Register the real ``new`` subparser with the plan §5 arguments
                (T4.3), in place of the generic not-implemented stub.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
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
    @brief      Register the real ``adopt`` subparser with the plan §5 arguments
                (T5.2), in place of the generic not-implemented stub.
    @details    The flag shape is identical to ``new`` (frozen cross-command CLI
                contract per plan §15/D13).
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
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
    @brief      Register the real ``analyze`` subparser with its own
                ``--repo``/``--json`` arguments (plan §5 CLI contract), in
                place of the generic not-implemented stub.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
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
    @brief      Register the real ``doctor`` subparser with its own
                ``--repo``/``--json`` arguments (plan §5 CLI contract), in
                place of the generic not-implemented stub.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    parser = sub.add_parser("doctor", help=dict(SUBCOMMANDS)["doctor"])
    parser.add_argument("--repo", required=True, help="Repository root to diagnose")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a human report")
    parser.set_defaults(handler=_handle_doctor)


def _handle_upgrade(args: argparse.Namespace) -> int:
    """
    @brief      Adapt parsed ``waegis upgrade`` arguments to :func:`run_upgrade`.
    @details    The frozen §5 contract exposes only ``--repo``/``--dry-run``/
                ``--json``/``--payload`` (no answers file). The interactive
                (non-``--json``) path drives per-file conflict decisions with a
                :class:`ConsoleAsker`; the ``--json`` path supplies no asker, so
                :func:`run_upgrade` stops-and-reports on any conflict rather than
                guessing (a conflict is never auto-resolved).
    @param[in]  args Parsed namespace with ``repo``, ``dry_run``, ``json``, and
                ``payload``.
    @return     The exit code from :func:`run_upgrade` (0 ok / 1 conflicts /
                2 smoke-failed / 3 operational).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
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
    @brief      Register the real ``upgrade`` subparser with the plan §5
                arguments (T6.2), in place of the generic not-implemented stub.
    @details    Uses the ``--repo``/``--json`` shape shared with ``analyze`` and
                ``doctor`` (an existing-install command), plus ``--dry-run`` and
                ``--payload`` from the §5 contract.
    @param[in]  sub The top-level subparsers action to register under.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
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
    @brief      Build the top-level ``waegis`` argument parser: ``new`` (T4.3),
                ``adopt`` (T5.2), ``analyze`` (T3.3), ``doctor`` (T6.1), and
                ``upgrade`` (T6.2) get their real handlers and arguments; only
                ``version``, ``self-update``, and ``gui`` remain
                not-implemented stubs.
    @return     Configured :class:`argparse.ArgumentParser`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.6.0
    """
    parser = _WaegisArgumentParser(
        prog="waegis",
        description=(
            "WAEGIS - guided configuration and deployment wizard for AEGIS "
            f"(wizard {WIZARD_VERSION})."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in SUBCOMMANDS:
        if name == "new":
            _add_new_parser(sub)
            continue
        if name == "adopt":
            _add_adopt_parser(sub)
            continue
        if name == "analyze":
            _add_analyze_parser(sub)
            continue
        if name == "configure":
            _add_configure_parser(sub)
            continue
        if name == "doctor":
            _add_doctor_parser(sub)
            continue
        if name == "repair":
            _add_repair_parser(sub)
            continue
        if name == "upgrade":
            _add_upgrade_parser(sub)
            continue
        if name == "version":
            _add_version_parser(sub)
            continue
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
