#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file configure.py
@brief Post-install, owned-field-only workflow configuration lifecycle.
@details Uses stored manifest answers first and repository-analysis proposals as
         fallbacks. The current workflow file is the rewrite base, so comments
         and every non-owned field remain byte-for-byte unchanged. Writes are
         atomic, smoke/gate failures restore the prior file, and configuration
         metadata is written to the install manifest last.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.3.1
"""

# IMPORTS

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path
from typing import IO, Any, Mapping

from ..io.answers import AnswersFileError, load_answers_file
from ..io.envelope import (
    EXIT_NEEDS_INPUT,
    EXIT_OK,
    EXIT_OPERATIONAL,
    EXIT_VALIDATION,
    write_envelope,
)
from ..io.prompts import ConsoleAsker, PromptsError
from ..payload.copier import CopierError, inspect_payload
from ..payload.locate import PayloadLocateError, locate_payload, read_payload_version
from ..payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    ManifestState,
    hash_file,
    load_manifest,
    resolve_managed_path,
    write_manifest,
)
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo.analyze import RepoAnalysis, analyze_repo
from ..repo.workflow_toml import (
    WORKFLOW_FIELD_SPECS,
    WorkflowTomlError,
    generate_workflow_toml,
)
from ..repowise import REPOWISE_ANSWER_KEYS, RepoWiseError, lifecycle_repowise
from ..verification import smoke_reverify
from ..version import PAYLOAD_COMPAT_SPEC, WIZARD_VERSION, is_payload_compatible
from ..transaction import FileTransaction, recover_incomplete_transactions
from .new import OTHER_LANGUAGE_FIELD_SPECS, WORKFLOW_TOML_RELATIVE_PATH

# CONSTANTS

_CONTROL_KEYS = frozenset({"run_gates", "run_smoke"})
_CONFIG_KEYS = frozenset(spec.key for spec in (*WORKFLOW_FIELD_SPECS, *OTHER_LANGUAGE_FIELD_SPECS))


# HELPER FUNCTIONS


def _emit(
    stream: IO[str],
    *,
    as_json: bool,
    status: str,
    exit_code: int,
    plan: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    messages: tuple[str, ...] = (),
) -> int:
    """
    @brief      Emit configure output through the human or JSON surface.
    @return     ``exit_code``.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if as_json:
        return write_envelope(
            stream,
            "configure",
            status=status,
            exit_code=exit_code,
            plan=plan,
            result=result,
            messages=messages,
        )
    for message in messages:
        stream.write(message + "\n")
    if plan is not None:
        changes = plan.get("changes", [])
        stream.write(f"Configuration plan: {len(changes)} field change(s).\n")
        for change in changes:
            stream.write(f"  {change['field']}: {change['before']!r} -> {change['after']!r}\n")
    if result is not None and result.get("configured"):
        stream.write("Configuration updated and verified.\n")
    return exit_code


def _analysis_defaults(analysis: RepoAnalysis | None) -> dict[str, Any]:
    """
    @brief      Convert read-only repository proposals into field defaults.
    @return     Proposed configuration mapping.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if analysis is None:
        return {}
    return {
        "source_roots": [item.path for item in analysis.source_roots],
        "test_roots": [item.path for item in analysis.test_roots],
        "language": analysis.language or "python",
        **{
            f"gate_{name}_cmds": [
                list(item.argv)
                for item in getattr(analysis, f"gate_{name}_cmds")
                if item.argv and not item.needs_review
            ]
            for name in ("build", "typecheck", "lint", "test", "security")
        },
    }


def _stored_answers(configuration: Mapping[str, Any]) -> dict[str, Any]:
    """
    @brief      Extract allowlisted generator answers from manifest metadata.
    @return     Stored answer mapping, possibly empty.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.2.0
    """
    raw = configuration.get("answers")
    if not isinstance(raw, Mapping):
        return {}
    return {str(key): value for key, value in raw.items() if str(key) in _CONFIG_KEYS}


def _resolve_answers(
    supplied: Mapping[str, Any],
    stored: Mapping[str, Any],
    proposals: Mapping[str, Any],
    *,
    non_interactive: bool,
    asker: ConsoleAsker | None,
) -> dict[str, Any]:
    """
    @brief      Resolve and normalize configuration answers by precedence.
    @return     Complete normalized generator answer mapping.
    @exception  PromptsError If a required/invalid value is encountered.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    resolved: dict[str, Any] = {}
    for spec in WORKFLOW_FIELD_SPECS:
        default = stored.get(spec.key, proposals.get(spec.key, spec.default))
        dynamic = replace(spec, default=default)
        if spec.key in supplied:
            resolved[spec.key] = dynamic.normalize(supplied[spec.key])
        elif non_interactive:
            resolved[spec.key] = dynamic.normalize(default)
        else:
            assert asker is not None
            resolved[spec.key] = asker.ask_field(dynamic)
    if resolved["language"] == "other":
        for spec in OTHER_LANGUAGE_FIELD_SPECS:
            default = stored.get(spec.key)
            dynamic = replace(spec, default=default)
            if spec.key in supplied:
                resolved[spec.key] = dynamic.normalize(supplied[spec.key])
            elif non_interactive:
                if default is None:
                    raise PromptsError(f"missing required answer: {spec.key}")
                resolved[spec.key] = dynamic.normalize(default)
            else:
                assert asker is not None
                resolved[spec.key] = asker.ask_field(dynamic)
    return resolved


def _run_selected_gates(runner: CommandRunner, repo: Path, answers: Mapping[str, Any]) -> list[str]:
    """
    @brief      Run configured gate commands when ``run_gates`` was selected.
    @return     Failure messages; empty means all selected gates passed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if not answers.get("run_gates", False):
        return []
    failures: list[str] = []
    for gate in (
        "gate_build_cmds",
        "gate_typecheck_cmds",
        "gate_lint_cmds",
        "gate_test_cmds",
        "gate_security_cmds",
    ):
        for command in answers.get(gate, []):
            result = runner.run(tuple(command), timeout=600.0, cwd=repo)
            if not result.ok():
                failures.append(f"{gate}: {' '.join(command)} -> exit {result.exit_code}")
    return failures


# EXPORTED FUNCTIONS / PUBLIC API


def run_configure(
    repo: str | os.PathLike[str],
    *,
    stream: IO[str],
    answers_path: str | os.PathLike[str] | None = None,
    dry_run: bool = False,
    non_interactive: bool = False,
    yes: bool = False,
    as_json: bool = False,
    payload: str | os.PathLike[str] | None = None,
    stdin: IO[str] | None = None,
    runner: CommandRunner | None = None,
) -> int:
    """
    @brief      Configure an installed repository transactionally.
    @return     Standardized exit code 0/1/2/3.
    @exception  None All failures are rendered through the selected surface.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.3.1
    """
    repo_path = Path(repo).resolve()
    if as_json:
        non_interactive = True
    if not repo_path.is_dir():
        return _emit(
            stream,
            as_json=as_json,
            status="error",
            exit_code=EXIT_OPERATIONAL,
            messages=(f"--repo path does not exist or is not a directory: {repo_path}",),
        )
    try:
        recovered = recover_incomplete_transactions(repo_path)
    except (OSError, ValueError) as exc:
        return _emit(
            stream,
            as_json=as_json,
            status="error",
            exit_code=EXIT_OPERATIONAL,
            messages=(f"could not recover an interrupted transaction: {exc}",),
        )
    load = load_manifest(repo_path)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=("a valid current install manifest is required before configuration",),
        )
    manifest = load.manifest
    supplied: dict[str, Any] = {}
    if answers_path is not None:
        try:
            supplied = load_answers_file(answers_path)
        except AnswersFileError as exc:
            return _emit(
                stream,
                as_json=as_json,
                status="failed",
                exit_code=EXIT_VALIDATION,
                messages=(str(exc),),
            )
    unknown = sorted(set(supplied) - _CONFIG_KEYS - _CONTROL_KEYS - REPOWISE_ANSWER_KEYS)
    if unknown:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=("unrecognized answer key(s): " + ", ".join(unknown),),
        )
    try:
        payload_root = locate_payload(payload)
        inspect_payload(payload_root)
        payload_version = read_payload_version(payload_root)
        if payload_version is None or not is_payload_compatible(payload_version):
            raise ValueError(
                f"payload version {payload_version or 'unknown'!r} is incompatible; expected {PAYLOAD_COMPAT_SPEC}"
            )
    except (PayloadLocateError, CopierError, ValueError, OSError) as exc:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )

    active_runner = runner or SubprocessCommandRunner()
    try:
        analysis = analyze_repo(repo_path, runner=active_runner)
    except Exception:  # noqa: BLE001 - proposals are optional
        analysis = None
    asker = None if non_interactive else ConsoleAsker(stdin=stdin or sys.stdin, stdout=stream)
    stored = _stored_answers(manifest.configuration)
    try:
        resolved = _resolve_answers(
            supplied,
            stored,
            _analysis_defaults(analysis),
            non_interactive=non_interactive,
            asker=asker,
        )
        controls = {
            "run_gates": bool(supplied.get("run_gates", False)),
            "run_smoke": bool(supplied.get("run_smoke", True)),
        }
        workflow_path = resolve_managed_path(repo_path, WORKFLOW_TOML_RELATIVE_PATH)
        if workflow_path.is_file():
            base_text = workflow_path.read_text(encoding="utf-8")
        else:
            base_text = resolve_managed_path(payload_root, WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
        generated = generate_workflow_toml(base_text, **resolved)
    except (PromptsError, WorkflowTomlError, ValueError, OSError) as exc:
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            messages=(str(exc),),
        )

    changes = [
        {"field": key, "before": stored.get(key), "after": resolved[key]}
        for key in sorted(resolved)
        if stored.get(key) != resolved[key]
    ]
    content_changed = not workflow_path.is_file() or workflow_path.read_text(encoding="utf-8") != generated.text
    plan = {
        "repo": str(repo_path),
        "changes": changes,
        "workflow_content_changed": content_changed,
        "warnings": [warning.message for warning in generated.warnings],
        "recovered_transactions": list(recovered),
        **controls,
        "repowise_requested": bool(REPOWISE_ANSWER_KEYS.intersection(supplied)) or not non_interactive,
    }
    if dry_run:
        return _emit(stream, as_json=as_json, status="ok", exit_code=EXIT_OK, plan=plan)
    repowise_requested = bool(plan["repowise_requested"])
    if not content_changed and not changes and not repowise_requested:
        return _emit(
            stream,
            as_json=as_json,
            status="ok",
            exit_code=EXIT_OK,
            plan=plan,
            result={"configured": False, "no_op": True},
        )
    if non_interactive and not yes:
        return _emit(
            stream,
            as_json=as_json,
            status="needs-input",
            exit_code=EXIT_NEEDS_INPUT,
            plan=plan,
            messages=("non-interactive mutation requires --yes",),
        )
    if not yes and asker is not None and not asker.confirm("Apply this configuration plan?", default=True):
        return _emit(
            stream,
            as_json=as_json,
            status="needs-input",
            exit_code=EXIT_NEEDS_INPUT,
            plan=plan,
            messages=("configuration plan was not approved",),
        )

    temporary = workflow_path.with_name(workflow_path.name + ".waegis-tmp")
    transaction: FileTransaction | None = None
    try:
        transaction = FileTransaction.begin(
            repo_path,
            command="configure",
            paths=(WORKFLOW_TOML_RELATIVE_PATH, MANIFEST_RELATIVE_PATH),
        )
        transaction.mark("applying")
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(generated.text, encoding="utf-8", newline="")
        os.replace(temporary, workflow_path)
        failures = _run_selected_gates(active_runner, repo_path, {**resolved, **controls})
        smoke: tuple[Any, ...] = ()
        smoke_ok = True
        if controls["run_smoke"]:
            smoke, smoke_ok = smoke_reverify(active_runner, repo_path)
            failures.extend(f"{item.name}: {item.detail}" for item in smoke if item.status == "fail")
        if not smoke_ok or failures:
            raise RuntimeError("; ".join(failures))
        configuration = dict(manifest.configuration)
        raw_generated = configuration.get("generated_files")
        generated_files = dict(raw_generated) if isinstance(raw_generated, Mapping) else {}
        generated_files[WORKFLOW_TOML_RELATIVE_PATH] = {
            "sha256": hash_file(workflow_path).sha256
        }
        configuration["answers"] = {
            key: resolved[key] for key in sorted(resolved)
        }
        configuration["generator_version"] = WIZARD_VERSION
        configuration["generated_files"] = generated_files
        generated_paths = tuple(sorted(set(manifest.generated) | {WORKFLOW_TOML_RELATIVE_PATH}))
        transaction.mark("verified")
        write_manifest(
            repo_path,
            replace(manifest, generated=generated_paths, configuration=configuration),
        )
        transaction.commit()
    except BaseException as exc:  # transaction must roll back every failure/interruption
        if temporary.exists():
            temporary.unlink()
        if transaction is not None and transaction.directory.exists():
            transaction.rollback()
        return _emit(
            stream,
            as_json=as_json,
            status="failed",
            exit_code=EXIT_VALIDATION,
            plan=plan,
            result={"configured": False, "rolled_back": True},
            messages=(f"configuration verification failed; rolled back: {exc}",),
        )

    repowise_result: dict[str, Any] | None = None
    repowise_error: str | None = None
    if repowise_requested:
        try:
            repowise_result = lifecycle_repowise(
                repo_path,
                supplied,
                lifecycle="configure",
                interactive=not non_interactive,
                asker=asker,
                stream=None if as_json else stream,
            )
        except (OSError, RepoWiseError) as exc:
            repowise_error = str(exc)
    if repowise_error or (repowise_result and not repowise_result["sync"]["ok"]):
        return _emit(
            stream,
            as_json=as_json,
            status="error",
            exit_code=EXIT_OPERATIONAL,
            plan=plan,
            result={
                "configured": True,
                "no_op": False,
                "rolled_back": False,
                "aegis": {"ok": True},
                "repowise": repowise_result
                or {"aegis": "ok", "sync": {"ok": False, "error": repowise_error}},
            },
            messages=((repowise_error,) if repowise_error else ()),
        )

    warning_messages = tuple(warning.message for warning in generated.warnings)
    exit_code = EXIT_NEEDS_INPUT if warning_messages else EXIT_OK
    status = "warning" if warning_messages else "ok"
    return _emit(
        stream,
        as_json=as_json,
        status=status,
        exit_code=exit_code,
        plan=plan,
        result={
            "configured": True,
            "no_op": False,
            "rolled_back": False,
            "aegis": {"ok": True},
            "repowise": repowise_result,
        },
        messages=warning_messages,
    )


# END OF FILE
