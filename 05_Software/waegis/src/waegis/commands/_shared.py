#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file _shared.py
@brief Shared command-lifecycle plumbing for every WAEGIS command.
@details One home for the lifecycle blocks the five mutating commands
         (``new``/``adopt``/``upgrade``/``repair``/``configure``) previously
         each hand-rolled with copy-paste drift (2026-07-31 review, findings
         H5/H7/H8/H18): interrupted-transaction recovery with operator consent,
         payload locate/inspect/version-compatibility validation, wizard asker
         selection, the RepoWise post-run block, the frozen ``--json``-or-human
         envelope emission, and the exit-code/status mapping.
@details Every helper preserves the frozen output contracts byte for byte: the
         ``--json`` envelope shapes, the ``waegis <command>: <message>`` human
         lines, the exit codes, and the journal answer keys are exactly the
         ones the per-command copies produced before consolidation.
@details Two envelope-emission dialects existed and both are kept deliberately:
         the wizards (``new``/``adopt``) write ``waegis <command>:``-prefixed
         lines directly (:func:`wizard_fail`/:func:`wizard_note`), while the
         maintenance commands (``repair``/``configure``) route everything
         through one ``_emit`` per command; those keep their command-specific
         human plan/result rendering locally and share only the identical
         JSON/message core here (:func:`emit_command_output`).
"""

# IMPORTS

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, Any, Callable, Mapping, Sequence

from ..consent import ConsentDecision, mutation_consent
from ..engine import (
    EngineEvent,
    Journal,
    Note,
    PlanReady,
    RunSummary,
    StepFinished,
    waegis_home,
)
from ..io.answers import AnswersFileError, load_answers_file, unknown_keys
from ..io.console import (
    LiveStatusRenderer,
    plan_preview_json,
    render_plan_preview,
    run_summary_json,
)
from ..io.envelope import (
    EXIT_NEEDS_INPUT,
    EXIT_OK,
    EXIT_OPERATIONAL,
    EXIT_VALIDATION,
    write_envelope,
)
from ..io.prompts import (
    ConsoleAsker,
    FieldSpec,
    ScriptedAnswerError,
    ScriptedAsker,
    ValidationError,
)
from ..lifecycle import build_journal_fingerprints, find_resume_journal, replay_answers
from ..payload.copier import CopierError, SIDECAR_SUFFIX, inspect_payload
from ..payload.locate import PayloadLocateError, locate_payload, read_payload_version
from ..probes.runner import CommandRunner
from ..repowise import (
    REPOWISE_ANSWER_KEYS,
    RepoWiseError,
    commit_repowise_configuration,
    lifecycle_repowise,
)
from ..transaction import (
    TransactionError,
    pending_transaction_ids,
    recover_incomplete_transactions,
)
from ..version import PAYLOAD_COMPAT_SPEC, WIZARD_VERSION, is_payload_compatible

# CONSTANTS


@dataclass(frozen=True)
class CommandOptions:
    """
    @brief      Shared injectable command boundary options.
    @details    Keeps the recurring command seam explicit without changing the
                public ``run_*`` call signatures owned by ``cli.py``.
    """
    stream: IO[str]
    stdin: IO[str] | None
    runner: CommandRunner | None
    home: Path | None
    yes: bool
    dry_run: bool
    non_interactive: bool
    as_json: bool
    answers_path: str | Path | None
    payload: str | Path | None

# @brief Repo-relative path of the generated configuration surface (single
#        definition; previously re-declared in new.py and doctor.py — H7).
WORKFLOW_TOML_RELATIVE_PATH = ".agentic/workflow.toml"

# @brief Repo-relative directory whose presence marks a prior/legacy install
#        (single definition; previously re-declared in adopt/doctor/analyze).
AGENTIC_DIR_RELATIVE_PATH = ".agentic"

# @brief Templated RepoWise-configuration commit message (single definition;
#        previously duplicated in new.py and adopt.py).
REPOWISE_COMMIT_MESSAGE = f"Configure RepoWise via WAEGIS {WIZARD_VERSION}"

# @brief The exception tuple every payload locate/inspect/compat block catches.
PAYLOAD_VALIDATION_ERRORS = (PayloadLocateError, CopierError, ValueError, OSError)


# HELPER FUNCTIONS


def sidecar_relative_path(relative: str) -> str:
    """
    @brief      Return the canonical ``<name>.new`` sidecar repo-relative path.
    @param[in]  relative Repo-relative POSIX path of the conflicting file.
    @return     The sidecar's repo-relative POSIX path.
    @exception  None
    """
    path = PurePosixPath(relative)
    return path.with_name(path.name + SIDECAR_SUFFIX).as_posix()


def locate_validated_payload(
    payload: Any,
) -> tuple[Path, Any, str]:
    """
    @brief      Locate, inspect, and version-validate the payload in one step.
    @details    The shared "payload validated and fingerprinted up front" block
                every command duplicated (H5). The incompatible-version message
                is the frozen one all five commands already emitted.
    @param[in]  payload Optional ``--payload`` root override.
    @return     ``(payload_root, inventory, payload_version)``.
    @exception  waegis.payload.locate.PayloadLocateError If no payload resolves
                or its version is incompatible.
    @exception  waegis.payload.copier.CopierError Propagated from
                ``inspect_payload`` (including its ``PayloadMissingError``
                subclass) when the payload root is missing or an included
                source is unsafe or not a regular file.
    @exception  OSError Propagated from ``inspect_payload`` if an included
                file cannot be opened or read while hashing (callers catch
                :data:`PAYLOAD_VALIDATION_ERRORS`, which covers all of the
                above, exactly as before).
    """
    payload_root = locate_payload(payload)
    inventory = inspect_payload(payload_root)
    payload_version = read_payload_version(payload_root)
    if payload_version is None or not is_payload_compatible(payload_version):
        raise PayloadLocateError(
            f"payload version {payload_version or 'unknown'!r} is incompatible; expected {PAYLOAD_COMPAT_SPEC}"
        )
    return payload_root, inventory, payload_version


def wizard_fail(
    stream: IO[str],
    command: str,
    *,
    as_json: bool,
    status: str,
    exit_code: int,
    message: str,
) -> int:
    """
    @brief      Emit one wizard failure through the JSON or human surface.
    @details    The ``write_envelope``-or-``waegis <command>: <message>`` early
                -return pattern repeated at every validation site in
                ``run_new``/``run_adopt``.
    @param[in]  stream Output stream.
    @param[in]  command Envelope command name (``new``/``adopt``).
    @param[in]  as_json ``--json`` mode flag.
    @param[in]  status Frozen envelope status.
    @param[in]  exit_code Standardized exit code.
    @param[in]  message The single message to emit.
    @return     ``exit_code``.
    @exception  None
    """
    if as_json:
        return write_envelope(stream, command, status=status, exit_code=exit_code, messages=(message,))
    stream.write(f"waegis {command}: {message}\n")
    return exit_code


def wizard_note(
    stream: IO[str],
    command: str,
    *,
    as_json: bool,
    json_messages: list[str],
    message: str,
    warning: bool = False,
) -> None:
    """
    @brief      Route one informational wizard message to the active surface.
    @details    ``--json`` collects messages for the final envelope; human mode
                writes the ``waegis <command>:`` (optionally ``warning:``)
                prefixed line immediately.
    @param[in]  stream Output stream.
    @param[in]  command Command name for the human prefix.
    @param[in]  as_json ``--json`` mode flag.
    @param[in,out] json_messages Envelope message accumulator (``--json``).
    @param[in]  message The message text (unprefixed).
    @param[in]  warning Prefix the human line with ``warning:``.
    @return     None
    @exception  None
    """
    if as_json:
        json_messages.append(message)
    elif warning:
        stream.write(f"waegis {command}: warning: {message}\n")
    else:
        stream.write(f"waegis {command}: {message}\n")


def wizard_recovery_preamble(
    target_path: Path,
    *,
    command: str,
    stream: IO[str],
    as_json: bool,
    dry_run: bool,
    non_interactive: bool,
    yes: bool,
    stdin: IO[str] | None,
    json_messages: list[str],
) -> int | None:
    """
    @brief      Roll back an interrupted prior run before touching TARGET.
    @details    The transaction inspect + recovery-consent preamble previously
                copy-pasted between ``run_new`` and ``run_adopt`` (H5). A dry
                run writes nothing, so it must not mutate the target either:
                it only reports pending recoveries.
    @param[in]  target_path Resolved TARGET path.
    @param[in]  command Command name (``new``/``adopt``).
    @param[in]  stream Output stream.
    @param[in]  as_json ``--json`` mode flag.
    @param[in]  dry_run Inspect-only mode.
    @param[in]  non_interactive Never prompt.
    @param[in]  yes Blanket approval flag.
    @param[in]  stdin Interactive input stream (``None`` when unavailable).
    @param[in,out] json_messages Envelope message accumulator (``--json``).
    @return     An exit code on early termination, else ``None`` to continue.
    @exception  None
    """
    if dry_run:
        try:
            pending = pending_transaction_ids(target_path)
        except (OSError, ValueError, TransactionError) as exc:
            return wizard_fail(
                stream,
                command,
                as_json=as_json,
                status="error",
                exit_code=EXIT_OPERATIONAL,
                message=f"could not inspect interrupted transaction state: {exc}",
            )
        for item in pending:
            wizard_note(
                stream,
                command,
                as_json=as_json,
                json_messages=json_messages,
                message=f"pending transaction recovery not applied in dry-run: {item}",
            )
        return None
    try:
        pending = pending_transaction_ids(target_path)
        recovery_asker = (
            ConsoleAsker(stdin=stdin, stdout=stream)
            if not non_interactive and stdin is not None
            else None
        )
        recovery_consent = mutation_consent(
            mutation_planned=bool(pending),
            yes=yes,
            asker=recovery_asker,
            prompt=f"Roll back {len(pending)} interrupted transaction(s) before continuing?",
        )
        if recovery_consent is not ConsentDecision.APPROVED:
            return wizard_fail(
                stream,
                command,
                as_json=as_json,
                status="needs-input",
                exit_code=EXIT_NEEDS_INPUT,
                message="transaction recovery requires explicit approval",
            )
        recovered = recover_incomplete_transactions(target_path)
    except (OSError, ValueError, TransactionError) as exc:
        return wizard_fail(
            stream,
            command,
            as_json=as_json,
            status="error",
            exit_code=EXIT_OPERATIONAL,
            message=f"could not recover an interrupted transaction: {exc}",
        )
    if recovered:
        wizard_note(
            stream,
            command,
            as_json=as_json,
            json_messages=json_messages,
            message=f"rolled back {len(recovered)} interrupted transaction(s): {', '.join(recovered)}",
        )
    return None


def load_wizard_answers(
    answers_path: Any,
    *,
    command: str,
    stream: IO[str],
    as_json: bool,
) -> dict[str, Any] | int:
    """
    @brief      Load the ``--answers`` file for a wizard, or fail its way.
    @param[in]  answers_path Optional answers file path.
    @param[in]  command Command name (``new``/``adopt``).
    @param[in]  stream Output stream.
    @param[in]  as_json ``--json`` mode flag.
    @return     The loaded answers dict (empty when no file was given), or an
                exit code (``int``) on a load failure.
    @exception  None
    """
    if answers_path is None:
        return {}
    try:
        return load_answers_file(answers_path)
    except AnswersFileError as exc:
        return wizard_fail(
            stream, command, as_json=as_json, status="failed", exit_code=EXIT_VALIDATION, message=str(exc)
        )


def warn_unknown_wizard_keys(
    answers: Mapping[str, Any],
    specs: Sequence[FieldSpec],
    *,
    command: str,
    stream: IO[str],
    as_json: bool,
    json_messages: list[str],
) -> None:
    """
    @brief      Warn (never fail) about unrecognized wizard answer keys.
    @details    RepoWise answer keys are excluded: they are consumed by the
                post-run lifecycle, not the wizard FieldSpecs.
    @param[in]  answers Loaded answers mapping.
    @param[in]  specs The command's complete FieldSpec set.
    @param[in]  command Command name (``new``/``adopt``).
    @param[in]  stream Output stream.
    @param[in]  as_json ``--json`` mode flag.
    @param[in,out] json_messages Envelope message accumulator (``--json``).
    @return     None
    @exception  None
    """
    unknown = sorted(set(unknown_keys(answers, specs)) - REPOWISE_ANSWER_KEYS)
    if unknown:
        wizard_note(
            stream,
            command,
            as_json=as_json,
            json_messages=json_messages,
            message=f"unrecognized answer key(s): {', '.join(unknown)}",
            warning=True,
        )


def wizard_resume_setup(
    *,
    command: str,
    catalog: Any,
    target_path: Path,
    answers: dict[str, Any],
    payload_digest: str,
    home: Path | None,
    dry_run: bool,
    field_specs: Sequence[FieldSpec],
) -> tuple[dict[str, str], Path, Any, dict[str, Any]]:
    """
    @brief      Build journal fingerprints and merge auto-discovered resume
                answers (shared verbatim between the two wizards).
    @param[in]  command Command name (``new``/``adopt``).
    @param[in]  catalog The wizard's step catalog.
    @param[in]  target_path Resolved TARGET path.
    @param[in]  answers Loaded answers mapping.
    @param[in]  payload_digest The inspected payload digest.
    @param[in]  home WAEGIS home override.
    @param[in]  dry_run Dry runs never resume.
    @param[in]  field_specs The command's FieldSpecs (resume answer allowlist).
    @return     ``(fingerprints, state_home, resume, answers)`` with resume
                answers merged under the freshly supplied ones.
    @exception  None
    """
    fingerprints = build_journal_fingerprints(
        command=command,
        catalog=catalog,
        target=target_path,
        answers=answers,
        payload_digest=payload_digest,
    )
    state_home = home if home is not None else waegis_home()
    resume = (
        None
        if dry_run
        else find_resume_journal(
            state_home,
            expected_fingerprints=fingerprints,
            current_answers=answers,
        )
    )
    if resume is not None:
        prior_answers = replay_answers(
            resume,
            allowed_keys=(*(spec.key for spec in field_specs), *REPOWISE_ANSWER_KEYS),
        )
        answers = {**prior_answers, **answers}
    return fingerprints, state_home, resume, answers


def wizard_journal_factory(
    *,
    command: str,
    target_path: Path,
    home: Path | None,
    fingerprints: Mapping[str, str],
    answers: Mapping[str, Any] | None = None,
) -> Callable[[], Journal]:
    """
    @brief      Build the deferred journal factory the engine calls only after
                plan approval.
    @param[in]  command Journal mode (``new``/``adopt``).
    @param[in]  target_path Resolved TARGET path.
    @param[in]  home WAEGIS home override.
    @param[in]  fingerprints Journal fingerprints for resume compatibility.
    @param[in]  answers Answers this run started with, recorded so a later
                resume can tell an added answer from a changed one.
    @return     A zero-argument factory creating the mutation journal.
    @exception  None
    """

    def begin_journal() -> Journal:
        """@brief Create the mutation journal only after plan approval."""
        return Journal.begin(
            mode=command,
            wizard_version=WIZARD_VERSION,
            target=str(target_path),
            dry_run=False,
            home=home,
            fingerprints=fingerprints,
            initial_answers=dict(answers or {}),
        )

    return begin_journal


def repowise_additional_mutations(answers: Mapping[str, Any]) -> tuple[str, ...]:
    """
    @brief      The extra plan-approval mutation line for a requested RepoWise
                configuration (shared verbatim between the two wizards).
    @param[in]  answers Loaded answers mapping.
    @return     A one-element tuple when RepoWise work is requested, else empty.
    @exception  None
    """
    if REPOWISE_ANSWER_KEYS.intersection(answers) and (
        answers.get("repowise_source") != "disabled"
        or bool(answers.get("repowise_sync", False))
    ):
        return (
            (
                "configure RepoWise "
                f"source={answers.get('repowise_source')}; "
                f"sync={bool(answers.get('repowise_sync', False))}"
            ),
        )
    return ()


def select_wizard_askers(
    answers: Mapping[str, Any],
    *,
    non_interactive: bool,
    stdin: IO[str] | None,
    stream: IO[str],
) -> tuple[Any, ConsoleAsker | None]:
    """
    @brief      Select the step asker and the plan-approval asker (plan §4
                item 6; previously copy-pasted between the wizards — H5/H18).
    @details    ``--non-interactive`` scripts everything (confirms=True) and
                never approves interactively. Otherwise a console asker is
                layered under pre-supplied answers (:class:`HybridAsker`) when
                both exist, and a confirmation-refusing scripted asker is the
                last resort when no console is available.
    @details    ``confirms=True`` is *blanket consent to the rendered mutation
                plan*, not to every question a step can ask: the scripted
                asker's per-default policy (see :mod:`waegis.io.prompts`) still
                refuses to auto-answer ``True`` to a default-refuse safety
                question, which needs its own named answer key. The
                ``confirms=False`` asker is unaffected — refusing is the
                conservative answer either way.
    @param[in]  answers Loaded answers mapping.
    @param[in]  non_interactive Never prompt.
    @param[in]  stdin Interactive input stream (``None`` when unavailable).
    @param[in]  stream Output stream for console prompts.
    @return     ``(asker, approval_asker)``.
    @exception  None
    """
    if non_interactive:
        return ScriptedAsker(answers, confirms=True), None
    console = ConsoleAsker(stdin=stdin, stdout=stream) if stdin is not None else None
    if console is None:
        return ScriptedAsker(answers, confirms=False), None
    if answers:
        return HybridAsker(answers, console), console
    return console, console


def wizard_exit_and_status(
    summary: RunSummary,
    *,
    repowise_result: Mapping[str, Any] | None,
    repowise_error: str | None,
) -> tuple[int, str]:
    """
    @brief      Map a wizard run outcome to its exit code and envelope status.
    @details    The named replacement for the identical triple-nested
                conditional-expression chains in ``run_new``/``run_adopt``
                (H18): a RepoWise failure after a green AEGIS run is
                operational (``error``); otherwise the engine summary decides
                between ``ok``, ``needs-input`` (plan not approved), and
                ``failed`` (a step stopped the run).
    @param[in]  summary The engine's run summary.
    @param[in]  repowise_result The RepoWise lifecycle result, if it ran.
    @param[in]  repowise_error The RepoWise lifecycle error, if it raised.
    @return     ``(exit_code, status)``.
    @exception  None
    """
    if repowise_error or (repowise_result and not repowise_result["sync"]["ok"]):
        exit_code = EXIT_OPERATIONAL
    elif summary.ok:
        exit_code = EXIT_OK
    elif not summary.results:
        exit_code = EXIT_NEEDS_INPUT
    else:
        exit_code = EXIT_VALIDATION
    if exit_code == EXIT_OPERATIONAL:
        status = "error"
    elif summary.ok:
        status = "ok"
    elif exit_code == EXIT_NEEDS_INPUT:
        status = "needs-input"
    else:
        status = "failed"
    return exit_code, status


def wizard_postrun_and_emit(
    summary: RunSummary,
    *,
    command: str,
    target_path: Path,
    answers: Mapping[str, Any],
    non_interactive: bool,
    dry_run: bool,
    yes: bool,
    as_json: bool,
    stream: IO[str],
    sink: Any,
    json_messages: list[str],
    repowise_asker: Any,
    runner: CommandRunner,
    state_home: Path,
    commit_step_id: str,
    handoff_step_id: str,
    commit_skipped: bool = False,
) -> int:
    """
    @brief      The shared wizard epilogue: RepoWise post-run, JSON/human
                emission, and exit-code mapping (previously near-verbatim in
                ``run_new`` and ``run_adopt`` — H5/H18).
    @details    After a green non-dry run, the RepoWise lifecycle runs and its
                configuration is committed only when the wizard's own commit
                step actually acted (and, for adopt, was not operator-skipped
                via ``commit_skipped``). ``--json`` emits exactly one frozen
                envelope; human mode renders the end-of-run outcome plus any
                RepoWise failure guidance.
    @param[in]  summary The engine's run summary.
    @param[in]  command Command and RepoWise lifecycle name (``new``/``adopt``).
    @param[in]  target_path Resolved TARGET path.
    @param[in]  answers Final merged answers mapping.
    @param[in]  non_interactive Never prompt.
    @param[in]  dry_run Plan-preview-only mode.
    @param[in]  yes Blanket approval flag.
    @param[in]  as_json ``--json`` mode flag.
    @param[in]  stream Output stream.
    @param[in]  sink The run's event sink (plan capture in ``--json`` mode).
    @param[in]  json_messages Collected envelope messages (``--json``).
    @param[in]  repowise_asker Asker for the RepoWise lifecycle prompts.
    @param[in]  runner CommandRunner for the RepoWise configuration commit.
    @param[in]  state_home Resolved WAEGIS home.
    @param[in]  commit_step_id The wizard's commit step
                (``repo.initial-commit``/``repo.adoption-commit``).
    @param[in]  handoff_step_id The wizard's P5 handoff step id.
    @param[in]  commit_skipped Operator chose to skip the wizard commit
                (adopt only), so the RepoWise commit is skipped too.
    @return     The standardized exit code.
    @exception  None
    """
    repowise_result: dict[str, Any] | None = None
    repowise_error: str | None = None
    if summary.ok and not dry_run:
        try:
            repowise_result = lifecycle_repowise(
                target_path,
                answers,
                lifecycle=command,
                interactive=not non_interactive,
                asker=repowise_asker,
                stream=None if as_json else stream,
                home=state_home,
                yes=yes,
            )
            commit_result = next(
                (result for result in summary.results if result.step_id == commit_step_id),
                None,
            )
            if commit_result is not None and commit_result.acted and not commit_skipped:
                commit_repowise_configuration(
                    target_path,
                    runner,
                    message=REPOWISE_COMMIT_MESSAGE,
                )
        except (OSError, RepoWiseError) as exc:
            repowise_error = str(exc)

    if as_json:
        plan_data = None
        if isinstance(sink, JsonRunSink) and sink.plan is not None:
            plan_data = json.loads(plan_preview_json(sink.plan))
        if dry_run:
            return write_envelope(
                stream,
                command,
                status="ok",
                exit_code=EXIT_OK,
                plan=plan_data,
                messages=json_messages,
            )
        exit_code, status = wizard_exit_and_status(
            summary, repowise_result=repowise_result, repowise_error=repowise_error
        )
        result_data = json.loads(run_summary_json(summary))
        result_data["aegis"] = {"ok": summary.ok}
        result_data["repowise"] = repowise_result or {
            "aegis": "ok" if summary.ok else "failed",
            "sync": {"ok": False, "error": repowise_error},
        }
        return write_envelope(
            stream,
            command,
            status=status,
            exit_code=exit_code,
            plan=plan_data,
            result=result_data,
            messages=(*json_messages, *((repowise_error,) if repowise_error else ())),
        )
    render_human_outcome(summary, target_path, stream, handoff_step_id=handoff_step_id)
    if repowise_error:
        stream.write(f"RepoWise integration failed after AEGIS deployment: {repowise_error}\n")
    elif repowise_result and not repowise_result["sync"]["ok"]:
        stream.write(
            "RepoWise indexing failed after AEGIS deployment; "
            f"resume with: {repowise_result['sync']['resume_command']}\n"
        )
    exit_code, _ = wizard_exit_and_status(
        summary, repowise_result=repowise_result, repowise_error=repowise_error
    )
    return exit_code


def emit_command_output(
    stream: IO[str],
    command: str,
    *,
    as_json: bool,
    status: str,
    exit_code: int,
    plan: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    messages: tuple[str, ...] = (),
    render_human: Callable[[IO[str], Mapping[str, Any] | None, Mapping[str, Any] | None], None] | None = None,
) -> int:
    """
    @brief      Emit one maintenance-command result (``repair``/``configure``)
                through the JSON or human surface.
    @details    The identical JSON-envelope + bare-message-lines core the two
                per-command ``_emit`` helpers shared; the intentionally
                command-specific human plan/result rendering stays in each
                command and is injected via ``render_human``.
    @param[in]  stream Output stream.
    @param[in]  command Envelope command name.
    @param[in]  as_json ``--json`` mode flag.
    @param[in]  status Frozen envelope status.
    @param[in]  exit_code Standardized exit code.
    @param[in]  plan Optional frozen plan payload.
    @param[in]  result Optional frozen result payload.
    @param[in]  messages Messages for both surfaces.
    @param[in]  render_human Optional human renderer for ``plan``/``result``.
    @return     ``exit_code``.
    @exception  None
    """
    if as_json:
        return write_envelope(
            stream,
            command,
            status=status,
            exit_code=exit_code,
            plan=plan,
            result=result,
            messages=messages,
        )
    for message in messages:
        stream.write(message + "\n")
    if render_human is not None:
        render_human(stream, plan, result)
    return exit_code


def render_pending_recovery(stream: IO[str], plan: Mapping[str, Any] | None) -> None:
    """
    @brief      Render the dry-run pending-transaction-recovery notice lines
                (shared human output of ``repair`` and ``configure``).
    @param[in]  stream Output stream.
    @param[in]  plan The plan payload (``pending_recovery`` list honored).
    @return     None
    @exception  None
    """
    if plan is None:
        return
    for transaction_id in plan.get("pending_recovery", []):
        stream.write(
            "Pending transaction recovery not applied in dry-run: "
            f"{transaction_id}\n"
        )


def recover_transactions_or_emit(
    repo_path: Path,
    *,
    dry_run: bool,
    yes: bool,
    recovery_asker: ConsoleAsker | None,
    emit: Callable[..., int],
) -> tuple[Any, Any] | int:
    """
    @brief      The maintenance-command recovery preamble: inspect pending
                transactions, ask consent, and recover (shared verbatim by
                ``repair``/``configure``/``upgrade`` — H5).
    @param[in]  repo_path Resolved repository path.
    @param[in]  dry_run Inspect-only mode (consent and recovery are skipped).
    @param[in]  yes Blanket approval flag.
    @param[in]  recovery_asker Optional interactive asker for the consent.
    @param[in]  emit The command's emitter, called with keyword arguments
                ``status``/``exit_code``/``plan``/``messages`` on early exit.
    @return     ``(pending, recovered)`` on success, or the emitter's exit
                code (``int``) on refusal or an operational failure.
    @exception  None
    """
    try:
        pending = pending_transaction_ids(repo_path)
        if not dry_run:
            recovery_consent = mutation_consent(
                mutation_planned=bool(pending),
                yes=yes,
                asker=recovery_asker,
                prompt=f"Roll back {len(pending)} interrupted transaction(s) before continuing?",
            )
            if recovery_consent is not ConsentDecision.APPROVED:
                return emit(
                    status="needs-input",
                    exit_code=EXIT_NEEDS_INPUT,
                    plan={"recovery": list(pending)},
                    messages=("transaction recovery requires explicit approval",),
                )
        recovered = () if dry_run else recover_incomplete_transactions(repo_path)
    except (OSError, ValueError, TransactionError) as exc:
        return emit(
            status="error",
            exit_code=EXIT_OPERATIONAL,
            messages=(f"could not recover an interrupted transaction: {exc}",),
        )
    return pending, recovered


# COMMAND SUPPORT


class HybridAsker:
    """
    @brief Asker layering an answers mapping over an interactive ConsoleAsker.
    @details Implements plan §4 item 6 for ``--answers`` without
             ``--non-interactive``: a pre-supplied answer is used (validated,
             scripted-style), everything else prompts on the console. Shared by
             both wizards (previously ``new._HybridAsker``, imported privately
             by adopt — H8).
    """

    def __init__(self, answers: Mapping[str, Any], console: ConsoleAsker) -> None:
        """
        @brief      Construct the hybrid asker.
        @param[in]  answers Pre-supplied answers mapping.
        @param[in]  console Interactive fallback asker.
        @return     None
        @exception  None
        """
        self._answers = dict(answers)
        self._console = console

    def confirm(self, prompt: str, *, default: bool = True, decision: str | None = None) -> bool:
        """
        @brief      Delegate confirmations to the console.
        @details    Confirmations always reach the operator here even when the
                    answers mapping names the decision: this asker exists
                    precisely because a console is available, and a live
                    operator is the most explicit answer there is.
        @param[in]  prompt Question text.
        @param[in]  default Value assumed on empty input.
        @param[in]  decision Answer key that would decide this question without
                    an operator; passed through and ignored by the console.
        @return     The operator's choice.
        @exception  None
        """
        return self._console.confirm(prompt, default=default, decision=decision)

    def ask(self, key: str, prompt: str, *, default: str | None = None) -> str:
        """
        @brief      Answer from the mapping when present, else prompt.
        @param[in]  key Stable answer key.
        @param[in]  prompt Question text.
        @param[in]  default Fallback default.
        @return     The answer.
        @exception  None
        """
        if key in self._answers:
            return str(self._answers[key])
        return self._console.ask(key, prompt, default=default)

    def ask_field(self, spec: FieldSpec) -> Any:
        """
        @brief      Resolve a FieldSpec from the mapping when present (validated,
                    scripted-style), else prompt interactively.
        @param[in]  spec The field to resolve.
        @return     The normalized answer.
        @exception  waegis.io.prompts.ScriptedAnswerError If the pre-supplied
                    value fails validation (no silent fallback to prompting).
        """
        if spec.key in self._answers:
            try:
                return spec.normalize(self._answers[spec.key])
            except ValidationError as exc:
                raise ScriptedAnswerError(spec.key, str(exc)) from exc
        return self._console.ask_field(spec)


class ConsoleRunSink:
    """
    @brief Human-mode event sink: plan preview + live step status + step notes.
    @details Thin composition over the T1.3 renderers (no second renderer):
             ``PlanReady`` goes to :func:`render_plan_preview`, step transitions
             to :class:`LiveStatusRenderer`, and each finished step's messages
             are echoed indented so warnings (empty gates, guidance) are loud on
             the console, not only in the journal.
    @details Notes are indented to align under the padded marker column (added
             0.2.0, see ``io/console.py`` 0.2.0), and a blank line follows each
             finished step's notes so the log reads as distinct step blocks.
    """

    def __init__(self, stream: IO[str]) -> None:
        """
        @brief      Construct the sink over an output stream.
        @param[in]  stream Output stream.
        @return     None
        @exception  None
        """
        self._stream = stream
        self._live = LiveStatusRenderer(stream)

    def emit(self, event: EngineEvent) -> None:
        """
        @brief      Render one engine event.
        @param[in]  event The emitted event.
        @return     None
        @exception  None
        """
        if isinstance(event, PlanReady):
            render_plan_preview(event.plan, self._stream)
            return
        if isinstance(event, Note):
            self._stream.write(f"note: {event.message}\n")
            return
        if isinstance(event, StepFinished):
            self._live.emit(event)
            for message in event.result.messages:
                self._stream.write(f"       - {message}\n")
            self._stream.write("\n")
            return
        self._live.emit(event)


class JsonRunSink:
    """
    @brief ``--json`` event sink: captures the plan, renders nothing live.
    @details The command emits exactly one JSON document on stdout: the frozen
             plan-preview shape for ``--dry-run``, the frozen run-summary shape
             otherwise (plan §5, io/console.py field-name contract).
    """

    def __init__(self) -> None:
        """
        @brief      Construct the sink with no captured plan yet.
        @return     None
        @exception  None
        """
        self.plan: Any | None = None

    def emit(self, event: EngineEvent) -> None:
        """
        @brief      Capture the plan; ignore every other event.
        @param[in]  event The emitted event.
        @return     None
        @exception  None
        """
        if isinstance(event, PlanReady):
            self.plan = event.plan


def render_human_outcome(
    summary: RunSummary,
    target: Path,
    stream: IO[str],
    *,
    handoff_step_id: str = "handoff.summary",
) -> None:
    """
    @brief      Render the human end-of-run outcome: handoff notes on success,
                the stopping step's remediation on failure.
    @param[in]  summary The engine's run summary.
    @param[in]  target Resolved TARGET path (for the completed-resume message).
    @param[in]  stream Output stream.
    @param[in]  handoff_step_id Id of the P5 handoff step whose notes are echoed
                on success; defaults to Wizard N's ``"handoff.summary"``, Wizard
                E passes ``"handoff.adoption"``.
    @details    The success recap is prefixed with a ``=== Summary ... ===``
                header (0.3.0) marking it as a deliberate, unprefixed re-print
                of the handoff step's own notes (already shown, bullet-prefixed,
                in the live step log) rather than an accidental duplicate.
    @return     None
    @exception  None
    """
    if summary.dry_run:
        stream.write("dry run: no changes were made.\n")
        return
    if summary.ok:
        handoff = next((r for r in summary.results if r.step_id == handoff_step_id), None)
        if handoff is not None and handoff.acted:
            # Deliberately re-prints the handoff step's own notes (already
            # shown, prefixed, during the live step log): this is the final,
            # unprefixed recap the operator copies from, not an accidental
            # repeat, so a header marks the boundary between "what happened"
            # (the log above) and "what to do next" (this recap).
            stream.write("\n=== Summary (recap of the handoff notes above) ===\n")
            for message in handoff.messages:
                stream.write(message + "\n")
        else:
            stream.write(f"\nAll steps are already complete for {target}.\n")
        return
    if not summary.results:
        stream.write("plan not approved; nothing was changed.\n")
        return
    stopped = summary.results[-1]
    stream.write(f"\nstopped at step: {stopped.step_id} ({stopped.status.value})\n")
    if stopped.error:
        stream.write(f"error: {stopped.error}\n")
    if stopped.failure is not None:
        stream.write(f"diagnosis:   {stopped.failure.diagnosis}\n")
        stream.write(f"remediation: {stopped.failure.remediation}\n")
        if stopped.failure.it_request:
            stream.write("ask IT (copy the text below):\n")
            stream.write(f"  {stopped.failure.it_request}\n")


# END OF FILE
