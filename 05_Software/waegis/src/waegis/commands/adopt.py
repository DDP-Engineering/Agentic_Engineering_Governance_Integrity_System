#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file adopt.py
@brief ``waegis adopt TARGET``: the Wizard E catalog and command (plan §8.2, T5.2).
@details Registers every plan §8.2 step as a real :class:`waegis.engine.StepSpec`
         over the shared engine and wires the plan §5 CLI contract
         (``--answers``, ``--dry-run``, ``--non-interactive``, ``--json``,
         ``--payload``). Wizard E deploys the AEGIS payload into an *existing*
         repository, resolving payload/local conflicts file by file.
@details **Shared with Wizard N (no fork).** The P0-P2 machine/prereq/network
         prefix and the three ``verify.*`` smoke steps are reused as the *same*
         StepSpec objects imported from :mod:`waegis.commands.new`
         (``COMMON_PREFIX_STEPS``, ``VERIFY_STEPS``, ``GATES_STEP``), as are the
         mode-agnostic helpers (``get_target``/``get_runner``/``ask_field``/…), the
         shared ``deploy.workflow-toml`` detect/verify/on_fail, the
         manifest-amendment helper, and the console/journal command
         infrastructure. Only the repo-analysis, conflict-copy, and
         adoption-branch steps are new here.
@details **Proposals are never auto-applied.** ``analyze.repo`` renders T5.1's
         :func:`waegis.repo.analyze.analyze_repo` output and walks the operator
         through confirming (or overriding) *each* proposed field via
         ``ctx.asker``/FieldSpec; the confirmed answers (not the proposals) are
         what ``deploy.workflow-toml`` consumes. A scripted answer that differs
         from a proposal wins — the analysis only ever proposes.
@details **Four-way prior-install routing (plan §8.2/§6).**
         :class:`waegis.payload.manifest.ManifestState` has only three values
         and collapses "no ``.agentic`` at all" and "``.agentic`` present but no
         manifest" both into ``ABSENT``; ``repo.prior-install`` therefore adds an
         explicit ``.agentic`` directory check to route none / current / older /
         legacy distinctly (see :func:`_act_prior_install`).
@details **Conflict resolution (plan §6, T3.2).** ``deploy.adoption-copy`` is the
         first real caller of the copier's ADOPTION mode: it drives
         :data:`waegis.payload.copier.ConflictDecisionHook` from ``ctx.asker``
         (interactive per-file keep-local/take-payload/write-new) or from a
         pre-supplied ``adoption_conflicts`` table (``--answers``/non-interactive),
         journaling every decision, and verifies each was applied as chosen.
@details **``repo.adoption-commit`` is optional (added 0.2.0).** Its
         ``automation`` changed from ``ASSISTED`` to ``AUTO``: the generic
         per-step "Proceed with '<title>'?" gate a decline of which halts the
         whole run does not apply here. Instead ``_act_adoption_commit`` asks
         its own confirmation; declining sets the cross-step
         :data:`SHARED_ADOPTION_COMMIT_SKIPPED` flag, which
         ``_verify_adoption_commit`` treats as a valid verified outcome and
         ``_act_handoff_adoption`` reflects in its notes — the payload is
         already fully on disk regardless of whether the operator commits it
         themselves or lets this step do it.
@details **``prereq.node`` (added 0.3.0, architecture-review follow-up).**
         Reused verbatim from Wizard N via the (now 8-step)
         :data:`waegis.commands.new.COMMON_PREFIX_STEPS`, so ``ADOPT_STEP_IDS``
         gains it automatically between ``prereq.git`` and
         ``prereq.git-identity`` with no new code here.
"""

# IMPORTS

from __future__ import annotations

import io
import json
from types import MappingProxyType
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import IO, Any, Mapping

from ..engine import (
    Automation,
    Catalog,
    EngineContext,
    EngineError,
    Phase,
    Remediation,
    StepSpec,
    run as engine_run,
)
from ..io.envelope import EXIT_NEEDS_INPUT, EXIT_VALIDATION
from ..io.prompts import FieldSpec, PromptsError, ScriptedAnswerError, ValidationError
from ..payload.copier import (
    SIDECAR_SUFFIX,
    ConflictDecision,
    PayloadConflict,
    copy_payload,
    normalize_conflict_decision_value,
)
from ..payload.locate import read_payload_version
from ..payload.manifest import ManifestState, compute_drift, hash_file, load_manifest
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo.analyze import (
    ADAPTER_DIR_NAMES,
    RepoAnalysis,
    analyze_repo,
    render_repo_analysis,
)
from ..repo.gitops import (
    add_all,
    commit,
    create_branch,
    current_branch,
    head_commit,
    is_work_tree,
    status_porcelain,
    validate_branch_name,
)
from ..repo.workflow_toml import (
    GATE_ORDER,
    WORKFLOW_FIELD_SPECS,
    generate_workflow_toml,
    normalize_stored_answers,
)
from ..transaction import payload_transaction
from ..version import WIZARD_VERSION
from ._shared import (
    CommandOptions,
    AGENTIC_DIR_RELATIVE_PATH,
    PAYLOAD_VALIDATION_ERRORS,
    WORKFLOW_TOML_RELATIVE_PATH,
    ConsoleRunSink,
    JsonRunSink,
    load_wizard_answers,
    locate_validated_payload,
    repowise_additional_mutations,
    select_wizard_askers,
    warn_unknown_wizard_keys,
    wizard_fail,
    wizard_journal_factory,
    wizard_note,
    wizard_postrun_and_emit,
    wizard_recovery_preamble,
    wizard_resume_setup,
)
from .new import (
    COMMON_PREFIX_STEPS,
    GATES_STEP,
    GATE_ACCEPTANCE_FIELD_SPEC,
    OTHER_LANGUAGE_FIELD_SPECS,
    SHARED_ANSWERS,
    SHARED_CLONE_URL,
    SHARED_HOME,
    SHARED_PAYLOAD_OVERRIDE,
    SHARED_REGISTRY_READER,
    SHARED_RUNNER,
    SHARED_TARGET,
    SHARED_TRANSPORT,
    SHARED_WORKFLOW_ROOTS,
    VERIFY_STEPS,
    amend_manifest_generated,
    ask_field,
    detect_workflow_toml,
    get_answers,
    get_payload_root,
    get_runner,
    get_target,
    on_fail_workflow_toml,
    verify_workflow_toml,
)

# CONSTANTS

# @brief Frozen EngineContext.shared keys new to Wizard E (the plan-approved
#        cross-step contract; the SHARED_* keys reused from Wizard N are
#        imported above).
SHARED_ANALYSIS = "analysis"
SHARED_ANALYSIS_ANSWERS = "analysis_answers"
SHARED_ANALYSIS_HEAD = "analysis_head"
SHARED_PRIOR_INSTALL_ROUTE = "prior_install_route"
SHARED_CONFLICT_DECISIONS = "adoption_conflicts"
SHARED_ADOPTION_COPY_RESULT = "adoption_copy_result"

# @brief Cross-step flag set when the operator chooses to skip the adoption
#        commit (repo.adoption-commit act) so its own verify can pass without
#        re-checking git state (plan §8.2: the commit is a courtesy, not a
#        requirement — the payload is already on disk either way).
SHARED_ADOPTION_COMMIT_SKIPPED = "adoption_commit_skipped"

# @brief Default adoption branch (plan §8.2; override via the adoption_branch
#        answer).
DEFAULT_ADOPTION_BRANCH = "chore/aegis-adoption"

# @brief Templated adoption-commit message (plan §8.2 repo.adoption-commit).
ADOPTION_COMMIT_MESSAGE = f"Adopt AEGIS via WAEGIS {WIZARD_VERSION}"

# @brief The four distinct routes repo.prior-install can take (plan §8.2).
PRIOR_INSTALL_ROUTES: frozenset[str] = frozenset({"none", "current", "older", "legacy"})

# @brief Extracts the adoption-mode operator prompt: the first ```text block
#        under the "## Adopt An Existing Project" heading of PROMPT_CHEATSHEET.md
#        (so the handoff text is sourced from the shipped payload, never
#        invented). Non-greedy so it stops at that section's first block.
_ADOPTION_PROMPT_RE = re.compile(
    r"##\s+Adopt An Existing Project.*?```text\s*\n(?P<prompt>.*?)\n```", re.DOTALL
)

# @brief The ordered Wizard E step ids, mirroring plan §8.2 row for row (the
#        reused P0-P2 prefix and the shared verify.* trio included).
ADOPT_STEP_IDS: tuple[str, ...] = (
    "home.init",
    "machine.os",
    "machine.disk",
    "prereq.python",
    "prereq.git",
    "prereq.node",
    "prereq.git-identity",
    "net.proxy",
    "repo.validate-existing",
    "repo.prior-install",
    "analyze.repo",
    "deploy.adoption-copy",
    "deploy.workflow-toml",
    "deploy.gates",
    "verify.cli-smoke",
    "verify.workflow-smoke",
    "verify.hooks-present",
    "repo.adoption-commit",
    "handoff.adoption",
)


# DATA MODELS / TYPEDEFINITIONS


def _normalize_conflict_table(raw: Any) -> dict[str, str]:
    """
    @brief      Validate/normalize the ``adoption_conflicts`` answer: a mapping
                of repo-relative payload path to a conflict decision.
    @param[in]  raw A mapping (answers file), or a JSON string of one.
    @return     ``{path: decision}`` with every decision a valid
                :class:`ConflictDecision` value (``keep-local``/``take-payload``/
                ``write-new``).
    @exception  ValueError If the value is not a mapping or holds an unknown
                decision (the message names the offending path).
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("adoption_conflicts must be a mapping of path -> decision") from exc
    if not isinstance(raw, Mapping):
        raise ValueError("adoption_conflicts must be a mapping of repo-relative path -> decision")
    table: dict[str, str] = {}
    for path, decision in raw.items():
        try:
            text = normalize_conflict_decision_value(decision)
        except ValueError as exc:
            raise ValueError(
                f"invalid conflict decision {decision!r} for {path!r}; "
                "use keep-local, take-payload, or write-new"
            ) from exc
        table[str(path)] = text
    return table


# @brief The answer key that explicitly continues adoption over a repository
#        that already carries a valid AEGIS install manifest.
ADOPT_OVER_EXISTING_INSTALL_KEY = "adopt_over_existing_install"

# @brief Answer fields new to Wizard E (defaults keep them non-required): the
#        adoption branch name and the per-file conflict decision table, plus
#        the gate-acceptance decision shared with Wizard N (same
#        ``deploy.gates`` step, same answer key) and the prior-install
#        override. The last two are never prompted for as fields: they exist so
#        a non-interactive run can state the decisions that the two
#        default-refuse confirmations otherwise have no operator to make.
ADOPT_EXTRA_FIELD_SPECS: tuple[FieldSpec, ...] = (
    GATE_ACCEPTANCE_FIELD_SPEC,
    FieldSpec(
        key=ADOPT_OVER_EXISTING_INSTALL_KEY,
        question="Adopt into a repository that already has an AEGIS install?",
        description=(
            "Only read when a valid install manifest is already present. "
            "'waegis doctor' (same version) or 'waegis upgrade' (different "
            "version) is normally the right command; when absent or false, "
            "adoption stops there instead of running over the existing "
            "install."
        ),
        example="false",
        default=False,
    ),
    FieldSpec(
        key="adoption_branch",
        question="Which branch should the adoption changes be committed on?",
        description="The AEGIS payload and generated config are committed on this branch, kept separable from your own work.",
        example=DEFAULT_ADOPTION_BRANCH,
        default=DEFAULT_ADOPTION_BRANCH,
        validator=validate_branch_name,
    ),
    FieldSpec(
        key="adoption_conflicts",
        question="Per-file conflict decisions for payload files that already exist and differ?",
        description=(
            "Nothing you own is ever silently overwritten: supply keep-local "
            "(keep yours), take-payload (overwrite with the payload), or "
            "write-new (keep yours and write the payload beside it as a .new "
            "file) per repo-relative path; unlisted conflicts are still asked "
            "interactively."
        ),
        example='{"CLAUDE.md": "keep-local"}',
        # Immutable so the shared spec's default can never be mutated in place;
        # the validator returns a fresh dict on every normalize.
        default=MappingProxyType({}),
        validator=_normalize_conflict_table,
    ),
)

# @brief Every FieldSpec the adopt-mode command can consume (unknown-key check):
#        the six workflow fields (confirmed in analyze.repo), the two
#        "other"-language fields, and the adopt-extra fields.
ADOPT_FIELD_SPECS: tuple[FieldSpec, ...] = (
    *WORKFLOW_FIELD_SPECS,
    *OTHER_LANGUAGE_FIELD_SPECS,
    *ADOPT_EXTRA_FIELD_SPECS,
)


# HELPER FUNCTIONS


def _analysis(ctx: EngineContext) -> RepoAnalysis:
    """
    @brief      The repo analysis for this run (pre-computed by ``run_adopt``,
                or computed on demand and cached).
    @details    ``run_adopt`` seeds ``SHARED_ANALYSIS`` once so validate-existing
                (risk flags), the non-interactive required-key seeding, and
                analyze.repo all share a single read-only analysis; a step-level
                caller without that seed computes and caches it here.
    @param[in]  ctx Active engine context.
    @return     The :class:`RepoAnalysis`.
    @exception  None
    """
    cached = ctx.shared.get(SHARED_ANALYSIS)
    if cached is not None:
        return cached
    analysis = analyze_repo(get_target(ctx), runner=get_runner(ctx))
    ctx.shared[SHARED_ANALYSIS] = analysis
    return analysis


def _current_head(ctx: EngineContext) -> str:
    """
    @brief      The current HEAD commit hash, or ``""`` when none exists.
    @param[in]  ctx Active engine context.
    @return     The HEAD hash, or ``""`` (no commits / not a work tree) — used as
                the analysis cache key.
    @exception  None
    """
    return head_commit(get_runner(ctx), get_target(ctx)) or ""


def _proposed_gate_cmds(candidates: Any) -> list[list[str]]:
    """
    @brief      Extract runnable argv commands from a GateCandidate tuple.
    @param[in]  candidates The analysis' ``gate_test_cmds``/``gate_lint_cmds``.
    @return     ``[list(c.argv) …]`` for every candidate with a usable argv;
                manual-review candidates (``argv is None``) are dropped (their
                provenance is still surfaced in the seeded field description).
    @exception  None
    """
    return [list(candidate.argv) for candidate in candidates if candidate.argv is not None]


def _gate_provenance(candidates: Any) -> str:
    """
    @brief      Render one-line provenance for a gate's candidates.
    @param[in]  candidates The analysis' gate candidate tuple.
    @return     A ``"file (detail); …"`` string (with a manual-review marker
                where applicable), or ``""`` when there are no candidates.
    @exception  None
    """
    parts: list[str] = []
    for candidate in candidates:
        marker = " [manual review]" if candidate.needs_review else ""
        parts.append(f"{candidate.source_file} ({candidate.source_detail}){marker}")
    return "; ".join(parts)


def _seeded_workflow_specs(analysis: RepoAnalysis | None) -> list[FieldSpec]:
    """
    @brief      The six workflow FieldSpecs with their defaults seeded from the
                analysis proposals (plan §8.2 "seeded from analysis proposals
                instead of blank defaults").
    @details    ``source_roots``/``test_roots`` seed to the proposed paths, or
                ``None`` (genuinely required) when the analysis proposed none.
                ``language`` seeds to the ranked language (``"other"`` fallback).
                Gate specs seed to the runnable proposed commands (possibly the
                empty list — empty gates are permitted) and carry the candidate
                *provenance* in their description so the operator can judge
                trustworthiness. ``alignment_enabled`` keeps its recommended
                default. A ``None`` analysis (analysis failed) yields empty
                proposals.
    @param[in]  analysis The repo analysis, or ``None``.
    @return     The seeded FieldSpec list, in ``WORKFLOW_FIELD_SPECS`` order.
    @exception  None
    """
    if analysis is not None:
        source = [proposal.path for proposal in analysis.source_roots]
        tests = [proposal.path for proposal in analysis.test_roots]
        gate_proposals = {
            name: _proposed_gate_cmds(
                getattr(analysis, f"gate_{name}_cmds")
            )
            for name in GATE_ORDER
        }
        language = analysis.language
        provenance = {
            name: _gate_provenance(
                getattr(analysis, f"gate_{name}_cmds")
            )
            for name in GATE_ORDER
        }
    else:
        source, tests = [], []
        gate_proposals = {
            name: [] for name in GATE_ORDER
        }
        provenance = {
            name: "" for name in GATE_ORDER
        }
        language = "other"

    proposals: dict[str, Any] = {
        "source_roots": source or None,
        "test_roots": tests or None,
        "language": language,
        **{
            f"gate_{name}_cmds": gate_proposals[name]
            for name in GATE_ORDER
        },
        **{
            f"gate_{name}_mode": (
                "enforce" if gate_proposals[name] else "disabled"
            )
            for name in GATE_ORDER
        },
        "stage_form_retention": "discard",
        "check_execution": "external",
        "alignment_enabled": True,
    }
    seeded: list[FieldSpec] = []
    for spec in WORKFLOW_FIELD_SPECS:
        proposed = proposals.get(spec.key, spec.default)
        description = spec.description
        for name in GATE_ORDER:
            if spec.key == f"gate_{name}_cmds" and provenance[name]:
                description = f"{description}\nProposed from: {provenance[name]}"
        seeded.append(replace(spec, description=description, default=proposed))
    return seeded


def _missing_required_adopt_keys(analysis: RepoAnalysis | None, answers: Mapping[str, Any]) -> list[str]:
    """
    @brief      Required workflow keys a ``--non-interactive`` adopt run must
                supply, given the analysis proposals (plan §5 AD-9 mechanism).
    @details    A field is required only when the analysis proposed no usable
                default for it (``source_roots``/``test_roots`` with no
                proposal), plus the two ``other``-language fields when the
                effective language is ``other``. Every other field defaults to
                its proposal, so a machine-driven run may pin only what the
                analysis could not.
    @param[in]  analysis The repo analysis, or ``None``.
    @param[in]  answers Supplied answers (drives the ``other`` branch).
    @return     Missing required keys, in FieldSpec order.
    @exception  None
    """
    missing = [
        spec.key
        for spec in _seeded_workflow_specs(analysis)
        if spec.default is None and spec.key not in answers
    ]
    default_language = analysis.language if analysis is not None else "other"
    language = str(answers.get("language", default_language)).strip().lower()
    if language == "other":
        missing.extend(spec.key for spec in OTHER_LANGUAGE_FIELD_SPECS if spec.key not in answers)
    return missing


def _validate_supplied_adopt_answers(answers: Mapping[str, Any]) -> None:
    """
    @brief      Validate every supplied adopt answer up front (mirrors Wizard N's
                non-interactive contract), collecting all failures at once.
    @param[in]  answers Supplied answers mapping.
    @return     None
    @exception  ScriptedAnswerError If one or more supplied values fail their
                FieldSpec validator; the message names every offending key.
    """
    errors: dict[str, str] = {}
    for spec in ADOPT_FIELD_SPECS:
        if spec.key in answers:
            try:
                spec.normalize(answers[spec.key])
            except ValidationError as exc:
                errors[spec.key] = str(exc)
    if errors:
        detail = "; ".join(f"{key}: {message}" for key, message in errors.items())
        raise ScriptedAnswerError(next(iter(errors)), detail)


def _resolved_analysis_answers(ctx: EngineContext) -> dict[str, Any]:
    """
    @brief      The confirmed workflow answers for ``deploy.workflow-toml``.
    @details    Normally the operator-confirmed answers ``analyze.repo`` stored
                in ``SHARED_ANALYSIS_ANSWERS``. On a partial resume where that
                shared state is gone but the step still needs to run, the
                proposals are re-derived from a fresh analysis (proposal defaults
                accepted); a genuinely required field with no proposal then
                raises, since it can only come from an interview.
    @param[in]  ctx Active engine context.
    @return     The workflow answers keyed by FieldSpec key (plus the two
                ``other`` extras, ``None`` when unused).
    @exception  EngineError If a required field has neither a confirmed answer
                nor a proposal.
    """
    answers = ctx.shared.get(SHARED_ANALYSIS_ANSWERS)
    if answers:
        return answers
    derived: dict[str, Any] = {}
    for spec in _seeded_workflow_specs(_analysis(ctx)):
        if spec.default is None:
            raise EngineError(
                f"analyze.repo must confirm {spec.key!r} before deploy.workflow-toml can run"
            )
        derived[spec.key] = spec.normalize(spec.default)
    derived.setdefault("source_extensions", None)
    derived.setdefault("test_file_patterns", None)
    return derived


def _adoption_branch(ctx: EngineContext) -> str:
    """
    @brief      The adoption branch name for this run.
    @param[in]  ctx Active engine context.
    @return     The ``adoption_branch`` answer, or :data:`DEFAULT_ADOPTION_BRANCH`.
    @exception  None
    """
    return str(get_answers(ctx).get("adoption_branch") or "").strip() or DEFAULT_ADOPTION_BRANCH


def _adoption_operator_prompt(target: Path) -> str | None:
    """
    @brief      Extract the adoption-mode operator prompt from the *copied* cheat
                sheet, so the handoff text cannot drift from the payload.
    @details    Reads ``TARGET/.agentic/documents/PROMPT_CHEATSHEET.md`` and
                returns the first ```` ```text ```` block under the "## Adopt An
                Existing Project" heading (the ``Use $agentic-adoption. …
                adoption-intake and adoption-alignment …`` prompt).
    @param[in]  target Target repository root.
    @return     The prompt text, or ``None`` when the file or block is absent.
    @exception  None
    """
    cheatsheet = target / ".agentic" / "documents" / "PROMPT_CHEATSHEET.md"
    try:
        text = cheatsheet.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _ADOPTION_PROMPT_RE.search(text)
    return match.group("prompt").strip() if match else None


# --- step: repo.validate-existing ----------------------------------------------


def _act_validate_existing(ctx: EngineContext) -> None:
    """
    @brief      repo.validate-existing act: report the work tree summary (branch,
                dirty files, submodule/LFS risk flags) and confirm adoption.
    @details    Submodule/LFS presence is read from the pre-computed analysis'
                risk flags (T5.1), never re-detected. A dirty tree warns but does
                not block (plan §8.2). The operator confirms the summary before
                the run proceeds.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If the operator declines to adopt.
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    if not is_work_tree(runner, target):
        ctx.note(f"{target} is not a git work tree")
        return
    branch = current_branch(runner, target)
    dirty = status_porcelain(runner, target)
    ctx.note(f"existing git work tree at {target}; branch: {branch or 'unknown'}")
    if dirty:
        ctx.note(f"warning: working tree has {len(dirty)} uncommitted change(s) (not a blocker)")
    else:
        ctx.note("working tree is clean")
    for flag in _analysis(ctx).risk_flags:
        if flag.name in ("risk.submodules", "risk.lfs"):
            ctx.note(f"[{flag.status}] {flag.name}: {flag.detail}")
    ctx.record_answer("adopt_branch", branch or "")
    ctx.record_answer("adopt_dirty_files", len(dirty))
    if not ctx.asker.confirm("Adopt AEGIS into this existing repository?", default=True):
        raise RuntimeError("operator declined to adopt this repository")


def _verify_validate_existing(ctx: EngineContext) -> bool:
    """
    @brief      repo.validate-existing verify: TARGET is a git work tree.
    @param[in]  ctx Active engine context.
    @return     ``True`` when ``git rev-parse --is-inside-work-tree`` confirms it.
    @exception  None
    """
    return is_work_tree(get_runner(ctx), get_target(ctx))


def _on_fail_validate_existing(ctx: EngineContext) -> Remediation:
    """
    @brief      repo.validate-existing remediation.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="TARGET is not an existing git repository (or the operator declined to adopt it).",
        remediation="'waegis adopt' targets an existing git repository: run 'git init' in TARGET "
        "first, or use 'waegis new' to create a brand-new project.",
        it_request=None,
    )


# --- step: repo.prior-install --------------------------------------------------


def _record_route(ctx: EngineContext, route: str) -> None:
    """
    @brief      Record the prior-install route on the shared contract and journal.
    @param[in]  ctx Active engine context.
    @param[in]  route One of :data:`PRIOR_INSTALL_ROUTES`.
    @return     None
    @exception  None
    """
    ctx.shared[SHARED_PRIOR_INSTALL_ROUTE] = route
    ctx.record_answer("prior_install_route", route)


def _act_prior_install(ctx: EngineContext) -> None:
    """
    @brief      repo.prior-install act: four-way routing on the prior install.
    @details    ``ManifestState`` alone cannot tell "no ``.agentic``" from
                "``.agentic`` present but no manifest" (both are ``ABSENT``), so
                an explicit ``.agentic`` directory check supplies the fourth
                branch: valid manifest matching the bundled payload -> suggest
                ``waegis doctor`` (confirm continue/stop); valid manifest with a
                different version -> suggest ``waegis upgrade`` (confirm
                continue/stop); no ``.agentic`` -> continue; ``.agentic`` present
                without a usable manifest -> the conservative path (the
                fast-path skip in deploy.adoption-copy is unavailable, so every
                payload file is re-evaluated). Declining "continue" stops the run
                before deploy.adoption-copy (the precondition chain).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If the operator chooses to stop.
    """
    target = get_target(ctx)
    agentic_present = (target / AGENTIC_DIR_RELATIVE_PATH).is_dir()
    load = load_manifest(target)
    current_version = read_payload_version(get_payload_root(ctx))

    if load.state is ManifestState.VALID and load.manifest is not None:
        installed = load.manifest.payload_version
        if current_version is not None and installed == current_version:
            _record_route(ctx, "current")
            ctx.note(
                f"AEGIS payload {installed} is already installed and matches the bundled payload; "
                f"consider 'waegis doctor --repo {target}'."
            )
            if not ctx.asker.confirm(
                "This repository already has the current AEGIS payload. Continue adoption anyway? "
                "'waegis doctor' is the command for an already-installed repository.",
                default=False,
                decision=ADOPT_OVER_EXISTING_INSTALL_KEY,
            ):
                raise RuntimeError(
                    "operator chose to stop; run 'waegis doctor' on the already-installed repository"
                )
            return
        _record_route(ctx, "older")
        ctx.note(
            f"AEGIS payload {installed} is installed; the bundled payload is {current_version}. "
            f"Consider 'waegis upgrade --repo {target}'."
        )
        if not ctx.asker.confirm(
            "This repository has a different AEGIS payload version. Continue adoption anyway "
            "(instead of 'waegis upgrade')?",
            default=False,
            decision=ADOPT_OVER_EXISTING_INSTALL_KEY,
        ):
            raise RuntimeError("operator chose to stop; run 'waegis upgrade' to move the existing install")
        return

    if not agentic_present:
        _record_route(ctx, "none")
        ctx.note("no prior AEGIS install detected (.agentic absent); proceeding with a fresh adoption")
        return

    _record_route(ctx, "legacy")
    manifest_state = "an invalid" if load.state is ManifestState.INVALID else "no"
    ctx.note(
        f".agentic is present but {manifest_state} install manifest was found (legacy install); "
        "using the conservative adoption path - every payload file is re-evaluated, nothing is "
        "silently skipped."
    )


def _verify_prior_install(ctx: EngineContext) -> bool:
    """
    @brief      repo.prior-install verify: a valid route was recorded.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the recorded route is one of the four known values.
    @exception  None
    """
    return ctx.shared.get(SHARED_PRIOR_INSTALL_ROUTE) in PRIOR_INSTALL_ROUTES


def _on_fail_prior_install(ctx: EngineContext) -> Remediation:
    """
    @brief      repo.prior-install remediation (operator chose to stop).
    @param[in]  ctx Active engine context.
    @return     The remediation text, pointing at doctor/upgrade per the route.
    @exception  None
    """
    route = ctx.shared.get(SHARED_PRIOR_INSTALL_ROUTE)
    if route == "current":
        remediation = "Run 'waegis doctor --repo TARGET' to check the existing install instead of re-adopting."
    elif route == "older":
        remediation = "Run 'waegis upgrade --repo TARGET' to move the existing install to the bundled payload."
    else:
        remediation = "Re-run 'waegis adopt' and choose to continue when prompted."
    return Remediation(
        diagnosis="Adoption was stopped because this repository already has an AEGIS install.",
        remediation=remediation,
        it_request=None,
    )


# --- step: analyze.repo --------------------------------------------------------


def _detect_analyze_repo(ctx: EngineContext) -> bool:
    """
    @brief      analyze.repo detect: confirmed answers already cached for the
                current HEAD this session.
    @param[in]  ctx Active engine context.
    @return     ``True`` when confirmed answers exist for the current HEAD.
    @exception  None
    """
    if not ctx.shared.get(SHARED_ANALYSIS_ANSWERS):
        return False
    return ctx.shared.get(SHARED_ANALYSIS_HEAD) == _current_head(ctx)


def _act_analyze_repo(ctx: EngineContext) -> None:
    """
    @brief      analyze.repo act: render the analysis and confirm each proposed
                field (never auto-applied).
    @details    Runs T5.1's heuristics (read-only), renders them via
                :func:`render_repo_analysis` into the step notes, then walks the
                operator through each workflow field via ``ctx.asker``/FieldSpec
                seeded from the proposal (gate provenance surfaced in the
                description). A scripted answer overrides its proposal; an absent
                one accepts it. The confirmed answers are stored for
                deploy.workflow-toml to consume.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  waegis.io.prompts.PromptsError On a missing/invalid scripted answer.
    """
    analysis = _analysis(ctx)
    buffer = io.StringIO()
    render_repo_analysis(analysis, buffer)
    for line in buffer.getvalue().splitlines():
        if line.strip():
            ctx.note(line)

    collected: dict[str, Any] = {}
    for spec in _seeded_workflow_specs(analysis):
        collected[spec.key] = ask_field(ctx, spec)
        ctx.record_answer(spec.key, collected[spec.key])
    collected["source_extensions"] = None
    collected["test_file_patterns"] = None
    if collected["language"] == "other":
        for spec in OTHER_LANGUAGE_FIELD_SPECS:
            collected[spec.key] = ask_field(ctx, spec)
            ctx.record_answer(spec.key, collected[spec.key])

    ctx.shared[SHARED_ANALYSIS_ANSWERS] = collected
    ctx.shared[SHARED_ANALYSIS_HEAD] = _current_head(ctx)
    ctx.note("analysis proposals confirmed field by field; nothing was auto-applied")


def _verify_analyze_repo(ctx: EngineContext) -> bool:
    """
    @brief      analyze.repo verify: confirmed answers were recorded.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the confirmed answers include a language.
    @exception  None
    """
    answers = ctx.shared.get(SHARED_ANALYSIS_ANSWERS)
    return bool(answers) and "language" in answers


# --- step: deploy.adoption-copy ------------------------------------------------


def _detect_adoption_copy(ctx: EngineContext) -> bool:
    """
    @brief      deploy.adoption-copy detect: an existing valid manifest whose
                files all hash-match (already adopted).
    @details    In the "legacy" route no valid manifest exists, so this returns
                ``False`` and the full conflict-resolving copy runs (the
                conservative path).
    @param[in]  ctx Active engine context.
    @return     ``True`` when a valid manifest is present with clean drift.
    @exception  OSError If a recorded file cannot be hashed.
    """
    load = load_manifest(get_target(ctx))
    if load.state is not ManifestState.VALID or load.manifest is None:
        return False
    drift = compute_drift(get_target(ctx), load.manifest)
    if drift.modified or drift.missing:
        ctx.note(f"manifest present but drifted: {len(drift.modified)} modified, {len(drift.missing)} missing")
        return False
    ctx.note("install manifest present and every recorded file hash-matches (already adopted)")
    return True


def _prompt_conflict(ctx: EngineContext, conflict: PayloadConflict) -> ConflictDecision:
    """
    @brief      Interactively resolve one conflict (fallback when no answer-table
                decision was supplied).
    @param[in]  ctx Active engine context.
    @param[in]  conflict The exists-and-different conflict to resolve.
    @return     The chosen :class:`ConflictDecision`.
    @exception  waegis.io.prompts.PromptsError On a missing/invalid scripted answer.
    """
    ctx.note(
        f"conflict on {conflict.relative_path}: local {conflict.target_entry.size} bytes / "
        f"{conflict.target_entry.sha256[:12]} vs payload {conflict.source_entry.size} bytes / "
        f"{conflict.source_entry.sha256[:12]}"
    )
    spec = FieldSpec(
        key=f"conflict:{conflict.relative_path}",
        question=f"{conflict.relative_path} already exists and differs from the payload — keep yours, take payload, or write payload beside yours?",
        description=(
            "Nothing you own is ever silently overwritten: keep-local keeps "
            "yours untouched, take-payload overwrites it with the payload, "
            "write-new keeps yours and writes the payload as a .new file "
            "beside it."
        ),
        example="keep-local",
        default="keep-local",
        validator=normalize_conflict_decision_value,
        choices=("keep-local", "take-payload", "write-new"),
    )
    return ConflictDecision(ask_field(ctx, spec))


def _make_conflict_hook(ctx: EngineContext):
    """
    @brief      Build the per-conflict decision hook driven by the answer table
                first, then the asker.
    @details    A decision supplied in the ``adoption_conflicts`` table
                (``--answers``/non-interactive) is used; otherwise the operator
                is prompted. Every decision is journaled via ``ctx.record_answer``.
    @param[in]  ctx Active engine context.
    @return     A :data:`waegis.payload.copier.ConflictDecisionHook`.
    @exception  None
    """
    table: Mapping[str, str] = ctx.shared.get(SHARED_CONFLICT_DECISIONS) or {}

    def hook(conflict: PayloadConflict) -> ConflictDecision:
        """
        @brief      Resolve one conflict via the table or the asker.
        @param[in]  conflict The conflict to resolve.
        @return     The chosen :class:`ConflictDecision`.
        @exception  EngineError If the table holds an invalid decision.
        """
        path = conflict.relative_path
        raw = table.get(path)
        if raw is not None:
            try:
                decision = ConflictDecision(normalize_conflict_decision_value(raw))
            except ValueError as exc:
                raise EngineError(f"invalid conflict decision {raw!r} for {path!r}") from exc
        else:
            decision = _prompt_conflict(ctx, conflict)
        ctx.record_answer(f"conflict_decision:{path}", decision.value)
        ctx.note(f"conflict {path}: {decision.value}")
        return decision

    return hook


def _act_adoption_copy(ctx: EngineContext) -> None:
    """
    @brief      deploy.adoption-copy act: locate the payload and copy it in
                ADOPTION mode, resolving conflicts through the hook (T3.2).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  waegis.payload.locate.PayloadLocateError If no payload resolves.
    @exception  waegis.payload.copier.CopierError On a copy failure.
    """
    payload = get_payload_root(ctx)
    target = get_target(ctx)
    result = copy_payload(
        payload,
        target,
        mode="adopt",
        on_conflict=_make_conflict_hook(ctx),
        require_existing_target=True,
        # Crash safety, and the case that matters most: adoption writes into a
        # repository that already holds the operator's own work. The journal is
        # staged over exactly the destinations the apply phase will touch —
        # including every take-payload overwrite — so an interruption is rolled
        # back on the next WAEGIS command instead of leaving the repository
        # half-converted with no manifest.
        on_apply=lambda paths: payload_transaction(target, command="adopt", paths=paths),
    )
    assert (
        result.manifest is not None and result.manifest_file is not None
    ), "copy_payload must produce a manifest on a non-dry-run apply"
    ctx.shared[SHARED_ADOPTION_COPY_RESULT] = result
    ctx.record_answer("payload_version", result.manifest.payload_version)
    ctx.record_answer("copied_count", len(result.copied))
    ctx.record_answer("skipped_count", len(result.skipped))
    ctx.record_artifact(str(result.manifest_file))
    ctx.note(
        f"copied {len(result.copied)} payload file(s); {len(result.conflicts)} conflict(s); "
        f"{len(result.skipped)} kept local from {payload}"
    )


def _verify_adoption_copy(ctx: EngineContext) -> bool:
    """
    @brief      deploy.adoption-copy verify: manifest re-hashes clean and every
                conflict decision was applied on disk exactly as chosen.
    @param[in]  ctx Active engine context.
    @return     ``True`` when drift is clean and every resolution matches.
    @exception  OSError If a file cannot be hashed.
    """
    target = get_target(ctx)
    load = load_manifest(target)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return False
    drift = compute_drift(target, load.manifest)
    if drift.modified or drift.missing:
        return False
    result = ctx.shared.get(SHARED_ADOPTION_COPY_RESULT)
    if result is None:
        return True
    for resolution in result.resolutions:
        conflict = resolution.conflict
        path = conflict.relative_path
        destination = target / path
        if resolution.decision is ConflictDecision.TAKE_PAYLOAD:
            if not destination.is_file() or hash_file(destination).sha256 != conflict.source_entry.sha256:
                return False
            if path not in load.manifest.files:
                return False
        elif resolution.decision is ConflictDecision.KEEP_LOCAL:
            if not destination.is_file() or hash_file(destination).sha256 != conflict.target_entry.sha256:
                return False
            if path not in load.manifest.skipped:
                return False
        else:  # ConflictDecision.WRITE_NEW
            sidecar = destination.with_name(destination.name + SIDECAR_SUFFIX)
            if not sidecar.is_file() or hash_file(sidecar).sha256 != conflict.source_entry.sha256:
                return False
            if not destination.is_file() or hash_file(destination).sha256 != conflict.target_entry.sha256:
                return False
            if path not in load.manifest.skipped:
                return False
    return True


def _on_fail_adoption_copy(ctx: EngineContext) -> Remediation:
    """
    @brief      deploy.adoption-copy remediation.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="The payload could not be copied into the existing repository, or a conflict "
        "decision could not be resolved.",
        remediation="Review the conflict notes in the step output; supply per-file decisions via "
        "the adoption_conflicts answer (keep-local/take-payload/write-new), then re-run.",
        it_request=None,
    )


# --- step: deploy.workflow-toml (adopt act) ------------------------------------


def _act_adopt_workflow_toml(ctx: EngineContext) -> None:
    """
    @brief      deploy.workflow-toml act (adopt): generate workflow.toml from the
                analysis-confirmed answers, create missing roots, amend the
                manifest.
    @details    Unlike Wizard N this step does not interview: the answers were
                already confirmed (or overridden) in analyze.repo and stored in
                ``SHARED_ANALYSIS_ANSWERS``. Generation, root creation, and the
                manifest amendment (``.agentic/workflow.toml`` moved from
                ``files`` to ``generated`` after generation) reuse Wizard N's
                exact machinery (:func:`generate_workflow_toml`,
                :func:`amend_manifest_generated`) — including persisting the
                confirmed answers, so an adopted repository can be reconfigured
                later without restating settings it already holds. The stored
                set is allowlisted to the generator's own answer keys, which
                keeps the adopt-only answers (branch name, conflict decisions)
                and RepoWise runtime data out of the durable configuration.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  waegis.repo.workflow_toml.WorkflowTomlError On generation/invariant failure.
    @exception  OSError If the file or roots cannot be written.
    """
    target = get_target(ctx)
    answers = _resolved_analysis_answers(ctx)
    base_text = (get_payload_root(ctx) / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    generator_answers = {spec.key: answers[spec.key] for spec in WORKFLOW_FIELD_SPECS}
    generated = generate_workflow_toml(
        base_text,
        **generator_answers,
        source_extensions=answers.get("source_extensions"),
        test_file_patterns=answers.get("test_file_patterns"),
    )
    for warning in generated.warnings:
        ctx.note(f"WARNING: {warning.message}")

    workflow_path = target / WORKFLOW_TOML_RELATIVE_PATH
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(generated.text, encoding="utf-8", newline="")
    ctx.record_artifact(str(workflow_path))

    source_roots = [str(root) for root in answers["source_roots"]]
    test_roots = [str(root) for root in answers["test_roots"]]
    ctx.shared[SHARED_WORKFLOW_ROOTS] = (source_roots, test_roots)

    missing_roots = [root for root in (*source_roots, *test_roots) if not (target / root).is_dir()]
    if missing_roots:
        if ctx.asker.confirm(
            f"Create missing root folder(s) with a .gitkeep: {', '.join(missing_roots)}?",
            default=True,
        ):
            for root in missing_roots:
                root_dir = target / root
                root_dir.mkdir(parents=True, exist_ok=True)
                (root_dir / ".gitkeep").write_text("", encoding="utf-8")
                ctx.record_artifact(str(root_dir / ".gitkeep"))
        else:
            ctx.note("operator declined creating missing roots - verification requires them to exist")

    amend_manifest_generated(target, answers=normalize_stored_answers(answers))
    ctx.note("install manifest amended: .agentic/workflow.toml moved from files to generated")


# --- step: repo.adoption-commit ------------------------------------------------


def _detect_adoption_commit(ctx: EngineContext) -> bool:
    """
    @brief      repo.adoption-commit detect: already on the adoption branch with a
                clean tree and a commit.
    @param[in]  ctx Active engine context.
    @return     ``True`` when committed and clean on the adoption branch.
    @exception  None
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    if current_branch(runner, target) != _adoption_branch(ctx):
        return False
    if status_porcelain(runner, target):
        return False
    return head_commit(runner, target) is not None


def _act_adoption_commit(ctx: EngineContext) -> None:
    """
    @brief      repo.adoption-commit act: ask whether to commit now, then (if
                so) create the adoption branch (if needed), stage everything,
                and commit with the templated message.
    @details    This step is deliberately optional (plan §8.2 D-note): the
                payload is already fully on disk by the time this step runs,
                so declining just means the operator will commit it
                themselves, on their own branch/message, whenever they choose
                — it does not undo or block anything already deployed. The
                confirmation therefore lives inside this ``AUTO``-automation
                step's own ``act`` (rather than the generic per-step
                "Proceed with '<title>'?" ``ASSISTED`` gate a decline of which
                halts the whole run) so a "no" here can complete the run
                cleanly through to ``handoff.adoption`` instead of stopping
                it.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If branching, staging, or committing fails.
    """
    ctx.shared.pop(SHARED_ADOPTION_COMMIT_SKIPPED, None)
    if not ctx.asker.confirm(
        "Commit the adoption now on a new branch? (choose 'n' to commit it yourself later)", default=True
    ):
        ctx.shared[SHARED_ADOPTION_COMMIT_SKIPPED] = True
        ctx.note("operator chose to commit the adoption manually later; nothing was committed")
        return
    runner = get_runner(ctx)
    target = get_target(ctx)
    branch = _adoption_branch(ctx)
    if current_branch(runner, target) != branch:
        branch_result = create_branch(runner, target, branch)
        if not branch_result.ok:
            raise RuntimeError(f"creating the adoption branch {branch!r} failed: {branch_result.detail}")
        ctx.record_answer("adoption_branch", branch)
    add_result = add_all(runner, target)
    if not add_result.ok:
        raise RuntimeError(f"git add failed: {add_result.detail}")
    commit_result = commit(runner, target, ADOPTION_COMMIT_MESSAGE)
    if not commit_result.ok:
        raise RuntimeError(f"git commit failed: {commit_result.detail}")
    ctx.record_answer("commit_message", ADOPTION_COMMIT_MESSAGE)
    head = head_commit(runner, target)
    if head:
        ctx.record_artifact(f"commit {head}")


def _verify_adoption_commit(ctx: EngineContext) -> bool:
    """
    @brief      repo.adoption-commit verify: clean tree, a HEAD commit, on the
                adoption branch — or the operator's explicit skip from this
                same act (plan §8.2 D-note: skipping is a valid, verified
                outcome, not a failure).
    @param[in]  ctx Active engine context.
    @return     ``True`` when skipped, or when all three re-checks pass.
    @exception  None
    """
    if ctx.shared.get(SHARED_ADOPTION_COMMIT_SKIPPED):
        return True
    runner = get_runner(ctx)
    target = get_target(ctx)
    if current_branch(runner, target) != _adoption_branch(ctx):
        return False
    if status_porcelain(runner, target):
        return False
    return head_commit(runner, target) is not None


def _on_fail_adoption_commit(ctx: EngineContext) -> Remediation:
    """
    @brief      repo.adoption-commit remediation.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="The adoption branch or commit could not be created.",
        remediation="The most common causes are a missing git identity or a pre-existing branch of "
        "the same name: set your git identity (or supply a different adoption_branch), then re-run.",
        it_request=None,
    )


# --- step: handoff.adoption ----------------------------------------------------


def _act_handoff_adoption(ctx: EngineContext) -> None:
    """
    @brief      handoff.adoption act: journal what was adopted, name the present
                agent adapters, and print the real adoption-intake prompt.
    @details    The prompt is extracted from the *copied* PROMPT_CHEATSHEET.md so
                it cannot drift from the payload. WAEGIS's job ends here: the
                in-repo ``agentic-adoption`` workflow (adoption-intake ->
                adoption-alignment -> ...) is driven by the operator's agent tool.
    @details    The committed-vs-uncommitted note and the closing summary
                sentence both branch on :data:`SHARED_ADOPTION_COMMIT_SKIPPED`
                (0.2.0), so the handoff text never claims a commit exists when
                the operator declined ``repo.adoption-commit``.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  None
    """
    target = get_target(ctx)
    load = load_manifest(target)
    payload_version = (
        load.manifest.payload_version if load.state is ManifestState.VALID and load.manifest else "unknown"
    )
    ctx.note(f"AEGIS payload {payload_version} adopted into {target} by WAEGIS {WIZARD_VERSION}.")
    if ctx.shared.get(SHARED_ADOPTION_COMMIT_SKIPPED):
        ctx.note("Changes are on disk but NOT committed - commit them yourself when ready.")
    else:
        ctx.note(f"Changes are committed on branch '{_adoption_branch(ctx)}'.")
    adapters = [name for name in ADAPTER_DIR_NAMES if (target / name).is_dir()]
    if adapters:
        ctx.note("Agent adapters present (use the one your team runs): " + ", ".join(adapters))
    prompt = _adoption_operator_prompt(target)
    if prompt:
        ctx.note(
            "Start the in-repo adoption workflow with this prompt in your agent tool "
            "(from .agentic/documents/PROMPT_CHEATSHEET.md):"
        )
        ctx.note(prompt)
    else:
        ctx.note(
            "See '## Adopt An Existing Project' in .agentic/documents/PROMPT_CHEATSHEET.md for the "
            "adoption-intake prompt."
        )
    branch_state = (
        "a verified adoption, left uncommitted for you to commit yourself"
        if ctx.shared.get(SHARED_ADOPTION_COMMIT_SKIPPED)
        else "a verified, committed adoption branch"
    )
    ctx.note(
        f"That prompt starts the agentic-adoption skill at adoption-intake; WAEGIS's job ends here with {branch_state}."
    )
    ctx.record_answer("payload_version", payload_version)


# STEP CATALOG


def _build_adopt_steps() -> list[StepSpec]:
    """
    @brief      Construct the ordered Wizard E steps (plan §8.2), reusing the
                shared prefix/verify/gates StepSpec objects from Wizard N.
    @details    ``COMMON_PREFIX_STEPS`` (P0-P2), ``GATES_STEP``, and
                ``VERIFY_STEPS`` are the *same* instances Wizard N runs; only the
                repo-analysis, conflict-copy, and adoption-branch steps are new.
                ``deploy.workflow-toml`` here reuses Wizard N's shared
                detect/verify/on_fail with an adopt-specific ``act``.
    @return     The ordered list of Wizard E :class:`StepSpec` objects.
    @exception  waegis.engine.StepContractError If a step were ever malformed.
    """
    return [
        *COMMON_PREFIX_STEPS,
        StepSpec(
            id="repo.validate-existing",
            title="Check the existing repository",
            why="'waegis adopt' works on an existing git repository. This step confirms TARGET is a "
            "git work tree and reports its branch, uncommitted changes (a warning, not a blocker), "
            "and any submodule/LFS risks before anything is changed.",
            phase=Phase.P3_REPO,
            automation=Automation.AUTO,
            preconditions=("net.proxy",),
            detect=lambda ctx: False,
            act=_act_validate_existing,
            verify=_verify_validate_existing,
            on_fail=_on_fail_validate_existing,
            change_summary=lambda ctx: "report the existing repository summary and confirm adoption (no changes)",
        ),
        StepSpec(
            id="repo.prior-install",
            title="Check for a prior AEGIS install",
            why="If AEGIS is already installed here, re-adopting is usually the wrong tool. This step "
            "detects a prior/partial install and points you at 'waegis doctor' or 'waegis upgrade', "
            "or proceeds when there is no prior install.",
            phase=Phase.P3_REPO,
            automation=Automation.AUTO,
            preconditions=("repo.validate-existing",),
            detect=lambda ctx: False,
            act=_act_prior_install,
            verify=_verify_prior_install,
            on_fail=_on_fail_prior_install,
            change_summary=lambda ctx: "detect any prior AEGIS install and route accordingly (no changes)",
        ),
        StepSpec(
            id="analyze.repo",
            title="Analyze the repository",
            why="Reads the repository (read-only) and proposes source folders, test folders, the main "
            "language, and gate commands with their provenance. You confirm or override each proposal "
            "- nothing is applied automatically.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.AUTO,
            preconditions=("repo.prior-install",),
            detect=_detect_analyze_repo,
            act=_act_analyze_repo,
            verify=_verify_analyze_repo,
            change_summary=lambda ctx: "analyze the repository and confirm each proposed setting (no changes)",
        ),
        StepSpec(
            id="deploy.adoption-copy",
            title="Copy the AEGIS payload (adoption)",
            why="Copies the AEGIS template into the existing repository byte-for-byte and writes the "
            "install manifest. Files that already exist and differ are never overwritten silently - "
            "you decide each: keep yours, take the payload, or write the payload as a .new file.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.ASSISTED,
            preconditions=("analyze.repo",),
            detect=_detect_adoption_copy,
            act=_act_adoption_copy,
            verify=_verify_adoption_copy,
            on_fail=_on_fail_adoption_copy,
            change_summary=lambda ctx: "copy the payload into TARGET, resolving conflicts file by file",
        ),
        StepSpec(
            id="deploy.workflow-toml",
            title="Configure the workflow (workflow.toml)",
            why="Generates .agentic/workflow.toml from the settings you confirmed during analysis, "
            "with the write-zone invariants guaranteed. Empty gates are allowed but recorded as loud "
            "warnings.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.ASSISTED,
            preconditions=("deploy.adoption-copy",),
            detect=detect_workflow_toml,
            act=_act_adopt_workflow_toml,
            verify=verify_workflow_toml,
            on_fail=on_fail_workflow_toml,
            change_summary=lambda ctx: "generate .agentic/workflow.toml from the confirmed settings, create missing roots",
        ),
        GATES_STEP,
        *VERIFY_STEPS,
        StepSpec(
            id="repo.adoption-commit",
            title="Commit the adoption on a branch",
            why="Records the installed payload and generated configuration as a commit on a dedicated "
            "adoption branch (default 'chore/aegis-adoption'), so the change is isolated and easy to "
            "review before merging. Optional: the payload is already on disk regardless, so declining "
            "just leaves the commit for the operator to make themselves.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.AUTO,
            preconditions=("verify.hooks-present",),
            detect=_detect_adoption_commit,
            act=_act_adoption_commit,
            verify=_verify_adoption_commit,
            on_fail=_on_fail_adoption_commit,
            change_summary=lambda ctx: (
                f"git checkout -b {_adoption_branch(ctx)} && git add -A && git commit (optional; "
                "asks first, skipping leaves it for you to commit yourself)"
            ),
        ),
        StepSpec(
            id="handoff.adoption",
            title="Hand off to the adoption workflow",
            why="Prints and journals the exact operator prompt that starts the in-repo adoption "
            "workflow (the agentic-adoption skill at adoption-intake), names the agent adapters "
            "present, and states that WAEGIS's job ends here. Reporting only - nothing changes.",
            phase=Phase.P5_HANDOFF,
            automation=Automation.AUTO,
            preconditions=("repo.adoption-commit",),
            act=_act_handoff_adoption,
            verify=lambda ctx: True,
            change_summary=lambda ctx: "print and journal the adoption hand-off (no changes)",
        ),
    ]


def build_adopt_catalog() -> Catalog:
    """
    @brief      Build the Wizard E catalog: every plan §8.2 step, in order, with
                a linear precondition chain realizing the P0->P5 phase order.
    @return     The validated :class:`Catalog`.
    @exception  waegis.engine.CatalogError If the catalog were ever inconsistent
                (duplicate ids, unknown preconditions, cycles).
    """
    return Catalog(_build_adopt_steps())


# EXPORTED FUNCTIONS / PUBLIC API


@dataclass(frozen=True)
class AdoptContext:
    """@brief Resolved public boundary for the adopt command phases."""
    target_path: Path
    options: CommandOptions
    transport: Any | None
    registry_reader: Any | None
    json_messages: list[str]


@dataclass(frozen=True)
class AdoptResolved:
    """@brief Validated adopt inputs before repository analysis."""
    context: AdoptContext
    answers: dict[str, Any]
    payload_root: Path
    catalog: Catalog
    fingerprints: Mapping[str, str]
    state_home: Path
    resume: Any


@dataclass(frozen=True)
class AdoptPlan:
    """@brief Adopt engine plan with explicit command dependencies."""
    resolved: AdoptResolved
    runner: CommandRunner
    analysis: RepoAnalysis | None
    asker: Any
    approval_asker: Any
    sink: ConsoleRunSink | JsonRunSink
    engine_context: EngineContext


@dataclass(frozen=True)
class AdoptOutcome:
    """@brief Completed adopt engine run awaiting reporting."""
    plan: AdoptPlan
    summary: Any


def _validate_adopt(context: AdoptContext) -> int | AdoptResolved:
    """@brief Validate and resolve every read-only adopt-command input."""
    options = context.options
    if not context.target_path.is_dir():
        return wizard_fail(
            options.stream, "adopt", as_json=options.as_json, status="failed",
            exit_code=EXIT_VALIDATION,
            message=f"TARGET does not exist or is not a directory: {context.target_path}",
        )
    early_exit = wizard_recovery_preamble(
        context.target_path, command="adopt", stream=options.stream,
        as_json=options.as_json, dry_run=options.dry_run,
        non_interactive=options.non_interactive, yes=options.yes,
        stdin=options.stdin, json_messages=context.json_messages,
    )
    if early_exit is not None:
        return early_exit
    loaded = load_wizard_answers(
        options.answers_path, command="adopt",
        stream=options.stream, as_json=options.as_json,
    )
    if isinstance(loaded, int):
        return loaded
    answers: dict[str, Any] = loaded
    warn_unknown_wizard_keys(
        answers, ADOPT_FIELD_SPECS, command="adopt", stream=options.stream,
        as_json=options.as_json, json_messages=context.json_messages,
    )
    try:
        _validate_supplied_adopt_answers(answers)
    except PromptsError as exc:
        return wizard_fail(
            options.stream, "adopt", as_json=options.as_json, status="failed",
            exit_code=EXIT_VALIDATION, message=f"invalid answer: {exc}",
        )
    try:
        payload_root, inventory, _payload_version = locate_validated_payload(options.payload)
    except PAYLOAD_VALIDATION_ERRORS as exc:
        return wizard_fail(
            options.stream, "adopt", as_json=options.as_json, status="failed",
            exit_code=EXIT_VALIDATION, message=str(exc),
        )
    catalog = build_adopt_catalog()
    fingerprints, state_home, resume, answers = wizard_resume_setup(
        command="adopt", catalog=catalog, target_path=context.target_path,
        answers=answers, payload_digest=inventory.digest, home=options.home,
        dry_run=options.dry_run, field_specs=ADOPT_FIELD_SPECS,
    )
    return AdoptResolved(
        context, answers, payload_root, catalog, fingerprints, state_home, resume
    )


def _analyze_adopt(resolved: AdoptResolved, runner: CommandRunner) -> RepoAnalysis | None:
    """@brief Run the existing best-effort adopt analysis at its original point."""
    options = resolved.context.options
    try:
        return analyze_repo(resolved.context.target_path, runner=runner)
    except Exception as exc:  # noqa: BLE001 - analysis is best-effort
        wizard_note(
            options.stream, "adopt", as_json=options.as_json,
            json_messages=resolved.context.json_messages,
            message=f"repository analysis failed ({exc}); proposals will be empty",
            warning=True,
        )
        return None


def _plan_adopt(resolved: AdoptResolved) -> int | AdoptPlan:
    """@brief Build the adopt engine plan without mutating the target."""
    options = resolved.context.options
    runner = options.runner or SubprocessCommandRunner()
    analysis = _analyze_adopt(resolved, runner)
    if options.non_interactive:
        missing = _missing_required_adopt_keys(analysis, resolved.answers)
        if missing:
            return wizard_fail(
                options.stream, "adopt", as_json=options.as_json,
                status="needs-input", exit_code=EXIT_NEEDS_INPUT,
                message="--non-interactive requires a complete answer set; missing: " + ", ".join(missing),
            )
        try:
            _validate_supplied_adopt_answers(resolved.answers)
        except PromptsError as exc:
            return wizard_fail(
                options.stream, "adopt", as_json=options.as_json, status="failed",
                exit_code=EXIT_VALIDATION, message=f"invalid answer: {exc}",
            )
    asker, approval_asker = select_wizard_askers(
        resolved.answers, non_interactive=options.non_interactive,
        stdin=options.stdin, stream=options.stream,
    )
    conflict_table: dict[str, str] = {}
    if resolved.answers.get("adoption_conflicts"):
        try:
            conflict_table = _normalize_conflict_table(
                resolved.answers["adoption_conflicts"]
            )
        except ValueError as exc:
            return wizard_fail(
                options.stream, "adopt", as_json=options.as_json, status="failed",
                exit_code=EXIT_VALIDATION,
                message=f"invalid adoption_conflicts answer: {exc}",
            )
    shared = _adopt_shared(resolved, runner, analysis, conflict_table)
    sink: ConsoleRunSink | JsonRunSink = (
        JsonRunSink() if options.as_json else ConsoleRunSink(options.stream)
    )
    engine_context = EngineContext(mode="adopt", asker=asker, events=sink, shared=shared)
    return AdoptPlan(resolved, runner, analysis, asker, approval_asker, sink, engine_context)


def _adopt_shared(
    resolved: AdoptResolved,
    runner: CommandRunner,
    analysis: RepoAnalysis | None,
    conflict_table: Mapping[str, str],
) -> dict[str, Any]:
    """@brief Build the frozen adopt EngineContext shared mapping."""
    context = resolved.context
    shared: dict[str, Any] = {
        SHARED_TARGET: context.target_path,
        SHARED_PAYLOAD_OVERRIDE: resolved.payload_root,
        SHARED_RUNNER: runner, SHARED_TRANSPORT: context.transport,
        SHARED_REGISTRY_READER: context.registry_reader,
        SHARED_ANSWERS: resolved.answers, SHARED_CLONE_URL: "",
        SHARED_HOME: context.options.home,
        SHARED_CONFLICT_DECISIONS: dict(conflict_table),
    }
    if analysis is not None:
        shared[SHARED_ANALYSIS] = analysis
    return shared


def _consent_adopt(plan: AdoptPlan) -> AdoptPlan:
    """@brief Preserve the engine-owned approval seam for the adopt plan."""
    options = plan.resolved.context.options
    if not options.dry_run and plan.resolved.resume is not None and not options.as_json:
        options.stream.write(
            f"resuming compatible incomplete run {plan.resolved.resume.run_id}; "
            "green steps will be re-detected\n"
        )
    return plan


def _apply_adopt(plan: AdoptPlan) -> AdoptOutcome:
    """@brief Run the adopt plan through the engine consent/apply phases."""
    resolved = plan.resolved
    options = resolved.context.options
    summary = engine_run(
        resolved.catalog, plan.engine_context, dry_run=options.dry_run,
        resume=resolved.resume, yes=options.yes,
        approval_asker=plan.approval_asker,
        journal_factory=None if options.dry_run else wizard_journal_factory(
            command="adopt", target_path=resolved.context.target_path,
            home=options.home, fingerprints=resolved.fingerprints,
        ),
        additional_mutations=repowise_additional_mutations(resolved.answers),
    )
    return AdoptOutcome(plan, summary)


def _report_adopt(outcome: AdoptOutcome) -> int:
    """@brief Emit the byte-compatible adopt report and exit code."""
    plan = outcome.plan
    resolved = plan.resolved
    options = resolved.context.options
    return wizard_postrun_and_emit(
        outcome.summary, command="adopt", target_path=resolved.context.target_path,
        answers=resolved.answers, non_interactive=options.non_interactive,
        dry_run=options.dry_run, yes=options.yes, as_json=options.as_json,
        stream=options.stream, sink=plan.sink,
        json_messages=resolved.context.json_messages, repowise_asker=plan.asker,
        runner=plan.runner, state_home=resolved.state_home,
        commit_step_id="repo.adoption-commit", handoff_step_id="handoff.adoption",
        commit_skipped=bool(
            plan.engine_context.shared.get(SHARED_ADOPTION_COMMIT_SKIPPED, False)
        ),
    )


def _run_adopt_phases(
    target: str | os.PathLike[str],
    *,
    options: CommandOptions,
    transport: Any | None = None,
    registry_reader: Any | None = None,
) -> int:
    """@brief Orchestrate validate, plan, consent, apply, and report phases."""
    normalized = replace(
        options, non_interactive=options.non_interactive or options.as_json
    )
    context = AdoptContext(
        Path(target).resolve(), normalized, transport, registry_reader, []
    )
    resolved = _validate_adopt(context)
    if isinstance(resolved, int):
        return resolved
    plan = _plan_adopt(resolved)
    if isinstance(plan, int):
        return plan
    return _report_adopt(_apply_adopt(_consent_adopt(plan)))


def run_adopt(
    target: str | os.PathLike[str],
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
    transport: Any | None = None,
    registry_reader: Any | None = None,
    home: Path | None = None,
) -> int:
    """
    @brief      Run the adoption wizard through its five lifecycle phases.
    @details    Preserves the public CLI/test injection seam while packaging
                recurring arguments in :class:`CommandOptions`.
    @return     Standardized command exit code 0/1/2/3.
    """
    return _run_adopt_phases(
        target,
        options=CommandOptions(
            stream, stdin, runner, home, yes, dry_run, non_interactive,
            as_json, answers_path, payload,
        ),
        transport=transport,
        registry_reader=registry_reader,
    )


# END OF FILE
