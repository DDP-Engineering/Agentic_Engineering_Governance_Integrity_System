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
import json
import os
import sys
from pathlib import Path
from typing import Callable, Sequence, TextIO

from .analyze import analyze_repository
from .answers import AnswersError, load_answers
from .check import check_repository
from .configure import ConfigureError, plan_configure
from .envelope import ResultEnvelope
from .gitsafety import SafetyError, require_clean, require_repository
from .install import InstallError, NeedsInput, apply_install, plan_install
from .interview import InterviewError, collect_install_answers
from .locate import PayloadError, resolve_payload
from .manifest import MANIFEST_PATH, ManifestError, detect_manifest_version
from .prompts import ConsoleAsker, FieldSpec
from .publication import PublicationError, PublicationPlan, apply_publication
from .repair import RepairError, plan_repair
from .runner import CommandRunner
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


def _emit_needs_input(command: str, keys: Sequence[str], plan: object, as_json: bool, out: TextIO) -> int:
    message = "more operator input is required: " + ", ".join(keys)
    if as_json:
        result = {"missing": list(keys)}
        if plan is not None:
            result["plan"] = plan
        out.write(ResultEnvelope(command, "needs-input", EXIT_NEEDS_INPUT, result=result, messages=(message,)).render())
    else:
        out.write(f"{message}\n")
    return EXIT_NEEDS_INPUT


def _render_install_plan(plan: object, out: TextIO, *, as_json: bool) -> None:
    value = plan.to_dict()  # type: ignore[attr-defined]
    if as_json:
        return
    out.write(f"Plan: {value['mode']} AEGIS {value['payload_version']} at {value['target']}\n")
    out.write("Answers:\n")
    for key, answer in value["answers"].items():
        source = value["provenance"].get(key, "resolved policy")
        out.write(f"  {key}: {answer!r} ({source})\n")
    for operation in value["operations"]:
        if operation["action"] != "unchanged":
            out.write(f"  {operation['action']}: {operation['path']} ({operation['disposition']})\n")
    out.write("Recovery:\n")
    recovery = value["recovery"]
    for command in recovery.get("commands", []):
        out.write(f"  {command}\n")
    if recovery["kind"] == "delete-created-target":
        out.write(f"  delete created target: {recovery['path']}\n")


def _run_install_command(
    args: argparse.Namespace,
    out: TextIO,
    err: TextIO,
    input_fn: Callable[[str], str],
) -> int:
    command = args.command
    runner = CommandRunner()
    try:
        payload_root, payload_version, inventory = resolve_payload(args.payload)
        supplied = load_answers(args.answers)
        analysis = None
        if command == "adopt":
            repository = require_repository(runner, args.target)
            require_clean(runner, repository)
            analysis = analyze_repository(repository, runner)
            version = detect_manifest_version(repository.joinpath(*MANIFEST_PATH.split("/")))
            if version is not None and version != 2 and "migration_v1" not in supplied:
                if args.json or args.non_interactive:
                    return _emit_needs_input(command, ("migration_v1",), None, args.json, out)
                migration = ConsoleAsker(out, input_fn).ask(
                    FieldSpec(
                        "migration_v1",
                        "A prior WAEGIS manifest was detected. Re-adopt without trusting its ownership data?",
                        "Every differing path still requires an ordinary conflict decision.",
                        "no",
                        ("yes", "no"),
                    )
                )
                if migration != "yes":
                    return _emit_needs_input(command, ("migration_v1",), None, False, out)
                supplied["migration_v1"] = True
        asker = None if args.json or args.non_interactive else ConsoleAsker(out, input_fn)
        answers, missing = collect_install_answers(
            supplied,
            analysis,
            asker,
            non_interactive=args.json or args.non_interactive,
        )
        if missing:
            return _emit_needs_input(command, missing, None, args.json, out)
        provenance: dict[str, str] = {}
        for key in answers:
            if key in supplied:
                provenance[key] = "answers file"
            elif analysis and key == "language":
                provenance[key] = analysis.language.reason
            elif analysis and key == "source_roots":
                provenance[key] = analysis.source_roots.reason
            elif analysis and key == "test_roots":
                provenance[key] = analysis.test_roots.reason
            elif asker is not None:
                provenance[key] = "interactive operator/default"
            else:
                provenance[key] = "payload safe default"

        def resolve_conflict(path: str) -> str:
            assert asker is not None
            return asker.ask(
                FieldSpec(
                    f"conflicts.{path}",
                    f"Payload destination differs: {path}",
                    "Keep local preserves it; take payload overwrites after recovery evidence; sidecar writes a review copy.",
                    "keep-local",
                    ("keep-local", "take-payload", "sidecar"),
                )
            )

        try:
            plan = plan_install(
                command,
                args.target,
                payload_root,
                payload_version,
                inventory,
                answers,
                runner,
                provenance=provenance,
                conflict_resolver=resolve_conflict if asker else None,
            )
        except NeedsInput as exc:
            return _emit_needs_input(command, exc.keys, None, args.json, out)
        _render_install_plan(plan, out, as_json=args.json)
        if args.dry_run:
            result = {"dry_run": True, "plan": plan.to_dict()}
            if args.json:
                out.write(ResultEnvelope(command, "ok", EXIT_OK, result=result).render())
            else:
                out.write("Dry run complete; no files were changed.\n")
            return EXIT_OK
        if not args.yes:
            if asker is None:
                return _emit_needs_input(command, ("consent",), plan.to_dict(), args.json, out)
            consent = asker.ask(
                FieldSpec("consent", "Apply this complete plan?", "Writes only the paths shown above.", "no", ("yes", "no"))
            )
            if consent != "yes":
                return _emit_needs_input(command, ("consent",), plan.to_dict(), False, out)
        manifest = apply_install(
            plan,
            runner,
            err if args.json else out,
            as_json=args.json,
            break_lock=args.break_lock,
        )
        result = {
            "target": str(plan.target),
            "payload_version": manifest.payload_version,
            "payload_digest": manifest.payload_digest,
            "manifest_version": 2,
            "changed": [operation.path for operation in plan.write_operations],
            "kept": [operation.path for operation in plan.operations if operation.action == "keep-local"],
        }
        if args.json:
            out.write(ResultEnvelope(command, "ok", EXIT_OK, result=result).render())
        else:
            out.write(f"AEGIS {manifest.payload_version} installed successfully at {plan.target}.\n")
            out.write("Review with 'git status', then stage and commit the approved files.\n")
        return EXIT_OK
    except (AnswersError, InterviewError, InstallError, PayloadError, SafetyError, OSError, ValueError) as exc:
        return _emit_error(command, str(exc), args.json, out, err)


def _run_analyze(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    try:
        analysis = analyze_repository(args.repo, CommandRunner())
    except (OSError, ValueError) as exc:
        return _emit_error("analyze", str(exc), args.json, out, err)
    if args.json:
        out.write(ResultEnvelope("analyze", "ok", EXIT_OK, result=analysis.to_dict()).render())
    else:
        value = analysis.to_dict()
        out.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return EXIT_OK


def _render_publication_plan(plan: PublicationPlan, out: TextIO, *, as_json: bool) -> None:
    if as_json:
        return
    value = plan.to_dict()
    out.write(f"Plan: {plan.command} at {plan.target}\n")
    for path in value["writes"]:
        out.write(f"  write: {path}\n")
    for path in value["removals"]:
        out.write(f"  remove: {path}\n")
    out.write("Recovery:\n")
    for command in value["recovery"]["commands"]:
        out.write(f"  {command}\n")


def _publication_consent(
    command: str,
    plan: PublicationPlan,
    args: argparse.Namespace,
    asker: ConsoleAsker | None,
    out: TextIO,
) -> int | None:
    if args.dry_run:
        if args.json:
            out.write(ResultEnvelope(command, "ok", EXIT_OK, result={"dry_run": True, "plan": plan.to_dict()}).render())
        else:
            out.write("Dry run complete; no files were changed.\n")
        return EXIT_OK
    if args.yes:
        return None
    if asker is None:
        return _emit_needs_input(command, ("consent",), plan.to_dict(), args.json, out)
    consent = asker.ask(
        FieldSpec("consent", "Apply this complete plan?", "Writes only the paths shown above.", "no", ("yes", "no"))
    )
    if consent != "yes":
        return _emit_needs_input(command, ("consent",), plan.to_dict(), False, out)
    return None


def _run_configure(
    args: argparse.Namespace,
    out: TextIO,
    err: TextIO,
    input_fn: Callable[[str], str],
) -> int:
    command = "configure"
    runner = CommandRunner()
    asker = None if args.json or args.non_interactive else ConsoleAsker(out, input_fn)
    try:
        supplied = load_answers(args.answers)
        plan, answers, missing, reconstructs, analysis = plan_configure(
            args.repo,
            supplied,
            runner,
            payload=args.payload,
            asker=asker,
            non_interactive=args.json or args.non_interactive,
        )
        if missing:
            return _emit_needs_input(command, missing, None, args.json, out)
        if plan is None:
            result = {"changed": [], "reconstructed": reconstructs, "answers": answers, "analysis": analysis.to_dict()}
            if args.json:
                out.write(ResultEnvelope(command, "ok", EXIT_OK, result=result).render())
            else:
                out.write("Configuration already matches the resolved answers; no files changed.\n")
            return EXIT_OK
        _render_publication_plan(plan, out, as_json=args.json)
        consent_result = _publication_consent(command, plan, args, asker, out)
        if consent_result is not None:
            return consent_result
        apply_publication(plan, runner, err if args.json else out, as_json=args.json, break_lock=args.break_lock)
        result = {
            "changed": sorted(plan.writes),
            "manifest_updated": True,
            "reconstructed": reconstructs,
            "workflow_sha256": plan.manifest.configuration["workflow_sha256"],
        }
        if args.json:
            out.write(ResultEnvelope(command, "ok", EXIT_OK, result=result).render())
        else:
            out.write("AEGIS workflow configuration validated and published. Review with 'git status'.\n")
        return EXIT_OK
    except (AnswersError, ConfigureError, ManifestError, PayloadError, PublicationError, SafetyError, OSError, ValueError) as exc:
        return _emit_error(command, str(exc), args.json, out, err)


def _run_check(args: argparse.Namespace, out: TextIO, err: TextIO) -> int:
    command = args.command
    try:
        result = check_repository(args.repo, CommandRunner())
    except (ManifestError, SafetyError, OSError, ValueError) as exc:
        return _emit_error(command, str(exc), args.json, out, err)
    code = result.exit_code
    status = "ok" if code == EXIT_OK else "warning" if code == EXIT_WARNING else "failed"
    if args.json:
        out.write(ResultEnvelope(command, status, code, result=result.to_dict()).render())
    else:
        out.write(f"WAEGIS check: {status}\n")
        for finding in result.findings:
            location = f" [{finding.path}]" if finding.path else ""
            out.write(f"  {finding.severity.upper()} {finding.code}{location}: {finding.message}\n")
            if finding.action:
                out.write(f"    Next: {finding.action}\n")
    return code


def _run_repair(args: argparse.Namespace, out: TextIO, err: TextIO, input_fn: Callable[[str], str]) -> int:
    command = "repair"
    runner = CommandRunner()
    asker = None if args.json or args.non_interactive else ConsoleAsker(out, input_fn)
    try:
        plan, drift = plan_repair(args.repo, args.payload, runner)
        if plan is None:
            result = {"changed": [], "unrepaired_drift": list(drift)}
            status = "warning" if drift else "ok"
            code = EXIT_WARNING if drift else EXIT_OK
            if args.json:
                out.write(ResultEnvelope(command, status, code, result=result).render())
            else:
                out.write("No managed files need repair.\n")
                if drift:
                    out.write("Project-owned drift was left untouched.\n")
            return code
        _render_publication_plan(plan, out, as_json=args.json)
        consent_result = _publication_consent(command, plan, args, asker, out)
        if consent_result is not None:
            return consent_result
        apply_publication(plan, runner, err if args.json else out, as_json=args.json, break_lock=args.break_lock)
        unrepaired = [item for item in drift if item["disposition"] != "managed"]
        result = {"changed": sorted(plan.writes), "manifest_updated": True, "unrepaired_drift": unrepaired}
        code = EXIT_WARNING if unrepaired else EXIT_OK
        status = "warning" if unrepaired else "ok"
        if args.json:
            out.write(ResultEnvelope(command, status, code, result=result).render())
        else:
            out.write("Managed AEGIS files repaired and validated. Review with 'git status'.\n")
            if unrepaired:
                out.write("Project-owned drift remains for operator review.\n")
        return code
    except (ManifestError, PayloadError, PublicationError, RepairError, SafetyError, OSError, ValueError) as exc:
        return _emit_error(command, str(exc), args.json, out, err)


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
    input_fn: Callable[[str], str] = input,
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
    if args.command in {"new", "adopt"}:
        return _run_install_command(args, out, err, input_fn)
    if args.command == "analyze":
        return _run_analyze(args, out, err)
    if args.command == "configure":
        return _run_configure(args, out, err, input_fn)
    if args.command in {"check", "doctor"}:
        return _run_check(args, out, err)
    if args.command == "repair":
        return _run_repair(args, out, err, input_fn)
    return _run_pending(args, out, err)


# END OF FILE
