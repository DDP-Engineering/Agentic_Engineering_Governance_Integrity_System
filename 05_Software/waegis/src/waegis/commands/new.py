#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file new.py
@brief ``waegis new TARGET``: the Wizard N catalog and command (plan §8.1, T4.3).
@details Registers every plan §8.1 step as a real :class:`waegis.engine.StepSpec`
         over the shared engine and wires the plan §5 CLI contract
         (``--answers``, ``--dry-run``, ``--non-interactive``, ``--json``,
         ``--payload``). Preconditions form a linear chain in table order, which
         realizes the P0→P5 phase order exactly and stays correct when
         ``net.proxy`` is ``applies()``-filtered out (the runner counts absent
         preconditions as satisfied-by-absence).
@details **Cross-step data** travels through ``EngineContext.shared`` under the
         ``SHARED_*`` key constants below (target path, injected
         CommandRunner/Transport, loaded answers, pending repo-local git
         identity, gate outcomes). Anything a *resumed* run needs (gates,
         roots) is re-derived from disk (``workflow.toml``, the install
         manifest) — ``shared`` is never assumed to survive a run.
@details **Manifest amendment (plan §6).** ``deploy.payload-copy`` writes the
         manifest via ``copy_payload`` with an empty ``generated`` list; only
         after ``deploy.workflow-toml`` actually rewrites the file from answers
         is the manifest re-read, ``.agentic/workflow.toml`` moved from
         ``files`` into ``generated``, and re-written. Amending at generation
         time (not at copy time via the threaded parameter) keeps the manifest
         truthful at every checkpoint: a run aborted between the two steps has
         a verbatim template copy, not a generated file. Removing the path
         from ``files`` also keeps drift reports clean and keeps
         ``deploy.payload-copy``'s detect green on re-runs.
@details **Documented step decisions** (each also stated in the step's ``why``):
         ``machine.os`` is report-only (verify always true — warn-not-block per
         §8.1) while ``machine.disk`` fails verify only below the 1 GiB
         minimum, a true blocker; ``prereq.python``/``prereq.git`` never run
         privileged installs — the wizard guides with the probe's OS-keyed
         command and re-probes (§8.1's "run on confirm" read safely);
         ``prereq.git-identity`` accepts a pending repo-local identity from the
         answers (§8.1's "or will be set repo-local"), applied by
         ``repo.init-or-clone`` after init; ``verify.workflow-smoke`` accepts
         the embedded CLI's coherent ``RUN-POINTER-MISSING`` response as the
         healthy fresh-install outcome (the real CLI exits with status 2 on
         ``status`` before any run is started).
@details **Non-interactive contract (AD-9).** ``--non-interactive`` validates
         the answers against the complete workflow FieldSpecs with their interactive
         defaults *stripped*: a machine-driven (WADORE) run must pin the full
         configuration explicitly, and every missing key is reported at once
         before the engine (or journal) starts. ``git_user_name``/
         ``git_user_email``/``clone_url`` stay optional (empty default).
@details **Shared with Wizard E (T5.2).** ``commands/adopt.py`` reuses the P0-P2
         prefix and the three ``verify.*`` smoke steps as the *same* StepSpec
         objects (:data:`COMMON_PREFIX_STEPS`, :data:`VERIFY_STEPS`,
         :data:`GATES_STEP`, all sliced from :func:`_build_new_steps`), plus the
         mode-agnostic helpers and the shared ``deploy.workflow-toml``
         detect/verify/on_fail — so the two catalogs share objects rather than
         forking the logic. Journal discovery is shared through
         :func:`waegis.lifecycle.find_resume_journal`; rendering helpers carry
         mode/handoff parameters so Wizard E reuses them too.
@details **``deploy.gates`` is optional (added 0.4.0).** Its ``automation``
         changed from ``ASSISTED`` to ``AUTO`` (shared with Wizard E via
         :data:`GATES_STEP`, so this applies to both catalogs): declining the
         old generic "Proceed with '<title>'?" gate halted the whole run,
         which is wrong for potentially slow gate commands. ``_act_gates`` now
         asks its own top-level confirmation and defers every configured gate
         command (a valid, already-supported ``_verify_gates`` outcome)
         instead of raising when declined.
@details **Console output layout (added 0.4.0).** ``ConsoleRunSink`` (now in
         ``commands/_shared.py``) indents step notes to align under the (now
         padded, see ``io/console.py`` 0.2.0) marker column and writes a blank
         line after each finished step, so the live log reads as distinct
         blocks. ``render_human_outcome`` (also in ``commands/_shared.py``)
         prints a ``=== Summary ... ===`` header before its end-of-run recap so
         it no longer looks like an accidental repeat of the live log above it.
@details **Failed-gate evidence and gate consent.** A failing gate command used
         to be recorded as an outcome string and a one-line note, with its
         output discarded — enough to know a gate failed, never enough to tell
         a real product failure from a wrong working directory. ``_act_gates``
         now records, per failed command, the argv, resolved cwd, exit code,
         duration, timeout, and bounded stdout/stderr tails, and writes the
         full output to one log file per failure under
         ``<home>/logs/gates``; the journal and ``--json`` result carry the
         bounded tails plus the log path and the exact reproduction command,
         so the envelope stays bounded while the evidence stays complete.
         Everything persisted is redacted with the repository's *own*
         configured secret patterns (``guardrails.secrets.patterns``, the
         persisted form of the ``secret_patterns`` answer) — this deliberately
         does not invent a second pattern list. A passing gate still records
         its outcome and nothing else. Accepting a failing enforced gate is a
         decision of its own, separate from the mutation-plan consent that
         ``--yes``/``--non-interactive`` grants: it needs the explicit
         ``accept_failing_gates`` answer or an interactive confirmation that
         states the consequence (see :mod:`waegis.io.prompts` for the
         per-default policy that enforces this for every default-refuse
         question).
@details **``prereq.node`` (added 0.5.0, architecture-review follow-up).** New
         warn-not-block step in ``P1_PREREQ``, between ``prereq.git`` and
         ``prereq.git-identity`` (also inserted into ``_COMMON_PREFIX_IDS``,
         so Wizard E gets it automatically): every AEGIS hook is dispatched
         through Node, which nothing checked for before this step existed.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import re
import shlex
import time
import tomllib
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Mapping, Sequence
from urllib.parse import urlsplit

from ..engine import (
    Automation,
    Catalog,
    EngineContext,
    EngineError,
    Phase,
    Remediation,
    StepSpec,
    run as engine_run,
    waegis_home,
)
from ..io.answers import MissingAnswersError, require_non_interactive_answers
from ..io.envelope import EXIT_NEEDS_INPUT, EXIT_VALIDATION
from ..io.prompts import FieldSpec, PromptsError
from ..payload.copier import copy_payload, should_exclude
from ..payload.locate import locate_payload
from ..payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    ManifestState,
    compute_drift,
    hash_file,
    load_manifest,
    read_manifest,
    write_manifest,
)
from ..probes.machine import probe_disk_space, probe_os_support
from ..probes.network import (
    SocketTransport,
    WinInetRegistryReader,
    probe_proxy_configuration,
    to_blocking_point_report,
)
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..probes.tools import probe_git, probe_node, probe_python
from ..repo import gitops
from ..repo.workflow_toml import (
    GATE_ORDER,
    OTHER_LANGUAGE_FIELD_SPECS,
    WORKFLOW_FIELD_SPECS,
    WorkflowTomlError,
    generate_workflow_toml,
    normalize_stored_answers,
    verify_workflow_invariants,
)
from ..transaction import payload_transaction
from ..verification import (
    HOOK_FILES,
    NO_ACTIVE_RUN_MARKER,
    SMOKE_TIMEOUT_SECONDS,
    wrapper_invocation as _wrapper_invocation,
)
from ..version import WIZARD_VERSION
from ._shared import (
    CommandOptions,
    WORKFLOW_TOML_RELATIVE_PATH,
    ConsoleRunSink,
    JsonRunSink,
    PAYLOAD_VALIDATION_ERRORS,
    load_wizard_answers,
    locate_validated_payload,
    repowise_additional_mutations,
    select_wizard_askers,
    warn_unknown_wizard_keys,
    wizard_fail,
    wizard_journal_factory,
    wizard_postrun_and_emit,
    wizard_recovery_preamble,
    wizard_resume_setup,
)
from .analyze import ADAPTER_DIR_NAMES

# CONSTANTS

# @brief Frozen EngineContext.shared keys (the plan-approved cross-step contract).
SHARED_TARGET = "target"
SHARED_PAYLOAD_OVERRIDE = "payload_override"
SHARED_PAYLOAD_ROOT = "payload_root"
SHARED_RUNNER = "runner"
SHARED_TRANSPORT = "transport"
SHARED_REGISTRY_READER = "registry_reader"
SHARED_ANSWERS = "answers"
SHARED_CLONE_URL = "clone_url"
SHARED_PENDING_IDENTITY = "pending_identity"
SHARED_WORKFLOW_ROOTS = "workflow_roots"
SHARED_GATE_OUTCOMES = "gate_outcomes"
SHARED_HOME = "home"
SHARED_NET_PROXY_FINDING = "net_proxy_finding"
SHARED_CLI_SMOKE_RESULT = "cli_smoke_result"
SHARED_WORKFLOW_SMOKE_STATUS = "workflow_smoke_status"
SHARED_WORKFLOW_SMOKE_GATES = "workflow_smoke_gates"

# @brief Minimum free disk space at the TARGET drive (plan §8.1 machine.disk).
MIN_FREE_DISK_BYTES = 1024**3

# @brief Timeout for operator gate commands (a real test suite may be slow).
GATE_TIMEOUT_SECONDS = 600.0

# @brief Characters of a failed gate's stdout (and, separately, stderr) kept
#        inline in the journal and the ``--json`` result. A failing test suite
#        prints its verdict last, so the *tail* is the diagnostic part; the
#        full text always survives in the durable log file, which is why this
#        can stay small enough to keep the envelope bounded.
GATE_OUTPUT_TAIL_LIMIT = 4000

# @brief Subdirectory of ``<home>/logs`` holding one log file per failed gate
#        command (sibling of the RepoWise log directory).
GATE_LOG_DIRNAME = "gates"

# @brief The answer key that explicitly accepts failing enforced gates.
ACCEPT_FAILING_GATES_KEY = "accept_failing_gates"

# @brief The answer key that explicitly accepts creating TARGET nested inside
#        another git work tree.
ACCEPT_NESTED_REPOSITORY_KEY = "accept_nested_repository"

# @brief Templated initial-commit message (plan §8.1 repo.initial-commit).
INITIAL_COMMIT_MESSAGE = f"Bootstrap AEGIS via WAEGIS {WIZARD_VERSION}"

# @brief Exit codes (frozen per plan §5/§15 D13; matches analyze's 0/1 shape).
EXIT_OK = 0
EXIT_FAILURE = EXIT_NEEDS_INPUT

# @brief Matches the first fenced ```text block of PROMPT_CHEATSHEET.md — the
#        first operator prompt the handoff step surfaces.
_FIRST_PROMPT_RE = re.compile(r"```text\s*\n(.*?)\n```", re.DOTALL)

# @brief The ordered Wizard N step ids, mirroring plan §8.1 row for row.
#        ``prereq.node`` (added 0.4.0, architecture-review follow-up) is the
#        one deliberate deviation from plan §8.1: every AEGIS hook is
#        dispatched through Node (``run_hook.mjs``) but nothing checked for it
#        before this addition. Warn-not-block, so it sits alongside
#        ``machine.os`` in spirit rather than blocking like
#        ``prereq.python``/``prereq.git``.
NEW_STEP_IDS: tuple[str, ...] = (
    "home.init",
    "machine.os",
    "machine.disk",
    "prereq.python",
    "prereq.git",
    "prereq.node",
    "prereq.git-identity",
    "net.proxy",
    "repo.target-path",
    "repo.init-or-clone",
    "deploy.payload-copy",
    "deploy.workflow-toml",
    "deploy.gates",
    "verify.cli-smoke",
    "verify.workflow-smoke",
    "verify.hooks-present",
    "repo.initial-commit",
    "handoff.summary",
)


# DATA MODELS / TYPEDEFINITIONS


# @brief The gate-acceptance decision, shared verbatim by both wizards (Wizard
#        E splices it into its own spec tuple) because both run the same
#        ``deploy.gates`` step. It is never prompted for as a field: it exists
#        so a non-interactive run can state the decision that
#        ``_act_gates``'s default-refuse confirmation otherwise has no operator
#        to make. The ``False`` default keeps it optional *and* keeps the
#        refusing behaviour when it is absent.
GATE_ACCEPTANCE_FIELD_SPEC = FieldSpec(
    key=ACCEPT_FAILING_GATES_KEY,
    question="Accept enforced quality gates that fail, and continue anyway?",
    description=(
        "Only read when a configured gate command actually fails. When true, a "
        "failing enforced gate is recorded as accepted-failing and the "
        "deployment reports success with an accepted failure; when absent or "
        "false, a failing gate stops the run. General mutation consent "
        "(--yes / --non-interactive) deliberately does not decide this."
    ),
    example="false",
    default=False,
)

# @brief Optional wizard-level answers (defaults keep them non-required):
#        clone_url selects clone-over-init; the git identity pair feeds
#        prereq.git-identity's pending repo-local path; accept_failing_gates
#        decides deploy.gates' default-refuse acceptance question.
NEW_EXTRA_FIELD_SPECS: tuple[FieldSpec, ...] = (
    GATE_ACCEPTANCE_FIELD_SPEC,
    FieldSpec(
        key=ACCEPT_NESTED_REPOSITORY_KEY,
        question="Create TARGET inside another git repository anyway?",
        description=(
            "Only read when TARGET turns out to lie inside an existing git "
            "work tree. When true, the nested repository is created anyway; "
            "when absent or false, the run stops rather than nesting silently."
        ),
        example="false",
        default=False,
    ),
    FieldSpec(
        key="clone_url",
        question="Clone from a remote instead of running a local 'git init'?",
        description="When set, the repository is cloned from this URL; leave empty for a new local repository.",
        example="https://forge.example.com/org/repo.git",
        default="",
        validator=lambda value: gitops.validate_clone_url(value, allow_empty=True),
    ),
    FieldSpec(
        key="git_user_name",
        question="Git identity name to record, if no global Git identity exists?",
        description="Set repo-locally only when Git has no usable global identity already; leave empty to skip.",
        example="Ada Lovelace",
        default="",
    ),
    FieldSpec(
        key="git_user_email",
        question="Git identity e-mail to record, if no global Git identity exists?",
        description="Set repo-locally only when Git has no usable global identity already; leave empty to skip.",
        example="ada@example.com",
        default="",
    ),
)

# @brief Every FieldSpec the new-mode catalog can consume (unknown-key check).
NEW_FIELD_SPECS: tuple[FieldSpec, ...] = (
    *WORKFLOW_FIELD_SPECS,
    *NEW_EXTRA_FIELD_SPECS,
    *OTHER_LANGUAGE_FIELD_SPECS,
)


# HELPER FUNCTIONS


def get_target(ctx: EngineContext) -> Path:
    """
    @brief      The resolved TARGET path from the shared contract.
    @param[in]  ctx Active engine context.
    @return     The target directory path.
    @exception  KeyError If the command did not seed the shared contract.
    """
    return ctx.shared[SHARED_TARGET]


def get_runner(ctx: EngineContext) -> CommandRunner:
    """
    @brief      The injected CommandRunner from the shared contract.
    @param[in]  ctx Active engine context.
    @return     The CommandRunner every subprocess-backed step must use.
    @exception  KeyError If the command did not seed the shared contract.
    """
    return ctx.shared[SHARED_RUNNER]


def get_answers(ctx: EngineContext) -> Mapping[str, Any]:
    """
    @brief      The loaded answers mapping from the shared contract.
    @param[in]  ctx Active engine context.
    @return     The (possibly empty) answers mapping.
    @exception  None
    """
    return ctx.shared.get(SHARED_ANSWERS, {})


def _nearest_existing(path: Path) -> Path:
    """
    @brief      Walk up from ``path`` to the closest existing ancestor.
    @details    Used where a probe or git needs a real directory while TARGET
                may not exist yet (disk-space probe, global-identity read,
                nested-work-tree check).
    @param[in]  path Candidate path (may not exist).
    @return     ``path`` itself when it exists, else the first existing
                ancestor, else the current working directory.
    @exception  None
    """
    candidate = path
    while not candidate.exists():
        if candidate.parent == candidate:
            return Path.cwd()
        candidate = candidate.parent
    return candidate


def get_payload_root(ctx: EngineContext) -> Path:
    """
    @brief      Resolve (and memoize) the payload root for this run.
    @details    Honors the ``--payload`` override from the shared contract and
                recomputes when absent, so a resumed run that skipped
                ``deploy.payload-copy`` can still locate the base template.
    @param[in]  ctx Active engine context.
    @return     The payload root directory.
    @exception  waegis.payload.locate.PayloadLocateError If no payload resolves.
    """
    cached = ctx.shared.get(SHARED_PAYLOAD_ROOT)
    if cached is not None:
        return cached
    root = locate_payload(ctx.shared.get(SHARED_PAYLOAD_OVERRIDE))
    ctx.shared[SHARED_PAYLOAD_ROOT] = root
    return root


def _note_finding(ctx: EngineContext, finding: Any) -> None:
    """
    @brief      Record a probe finding (and its guidance) on the running step.
    @param[in]  ctx Active engine context.
    @param[in]  finding Any ``ProbeFinding``-shaped record.
    @return     None
    @exception  EngineError If called outside a running step.
    """
    ctx.note(f"[{finding.status}] {finding.name}: {finding.detail}")
    if finding.guidance:
        ctx.note(f"guidance: {finding.guidance}")


def _probe_write_read(directory: Path) -> bool:
    """
    @brief      Write-read-delete probe proving a directory is truly writable.
    @param[in]  directory Directory to probe.
    @return     ``True`` when the round trip succeeds.
    @exception  None All failures report ``False``.
    """
    probe = directory / ".waegis-write-probe"
    try:
        probe.write_text("probe", encoding="utf-8")
        content = probe.read_text(encoding="utf-8")
        probe.unlink()
    except OSError:
        return False
    return content == "probe"


def ask_field(ctx: EngineContext, spec: FieldSpec) -> Any:
    """
    @brief      Prompt for one FieldSpec through the active asker.
    @details    The engine ``Asker`` protocol only declares ``confirm``/``ask``;
                every asker this command constructs additionally implements
                ``ask_field`` (T1.2's layered entry point).
    @param[in]  ctx Active engine context.
    @param[in]  spec The field to prompt for.
    @return     The normalized answer.
    @exception  EngineError If the active asker has no ``ask_field``.
    @exception  waegis.io.prompts.PromptsError On a missing/invalid scripted answer.
    """
    ask_field = getattr(ctx.asker, "ask_field", None)
    if ask_field is None:
        raise EngineError(f"the active asker cannot prompt for field {spec.key!r}")
    return ask_field(spec)


def split_gate_command(command: str) -> list[str]:
    """
    @brief      Split one configured gate command string into argv, honoring the
                host's path syntax (DPT-F07).
    @details    ``shlex.split`` defaults to POSIX mode, where a backslash is an
                escape character. On Windows that silently destroys every native
                path an operator writes unquoted: the configured gate
                ``uv run --directory 05_Software\\pkg python -m pytest`` was
                handed to the child as ``--directory 05_Softwarepkg``, so the
                command failed to locate the package and exited nonzero while
                the very same suite passed when run by hand from the package
                root. That is the exact shape of DPT-F07, and it contradicts
                this field's own documented contract ("Run exactly as given").
    @details    The fix disables *escape* processing on Windows while keeping
                POSIX *quote* processing, so a quoted path keeps working and its
                surrounding quotes are still removed. Plain ``posix=False``
                would not do: it returns the quote characters inside the token,
                which ``subprocess`` would then pass to the child literally.
                :mod:`waegis.repowise` solves the same problem for the RepoWise
                external command; this is the gate-command counterpart.
    @details    On every non-Windows host the lexer is configured exactly as
                ``shlex.split`` configures it, so POSIX behavior is unchanged
                byte for byte.
    @param[in]  command Configured gate command string.
    @return     The argv list to execute.
    @exception  ValueError If the string has an unbalanced quote.
    """
    lexer = shlex.shlex(command, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    if os.name == "nt":
        lexer.escape = ""
    return list(lexer)


def _read_gates(target: Path) -> dict[str, tuple[str, list[list[str]]]]:
    """
    @brief      Read the configured gate commands from the written workflow.toml.
    @details    Disk is the source of truth (resume-safe): a resumed run whose
                ``deploy.workflow-toml`` was skipped still sees the real gates.
    @param[in]  target Target repository root.
    @return     Gate names mapped to captured mode and argv lists.
    @exception  OSError If the file cannot be read.
    @exception  tomllib.TOMLDecodeError If the file is not valid TOML.
    """
    document = tomllib.loads((target / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8"))
    gates = document.get("gates", {})
    result: dict[str, tuple[str, list[list[str]]]] = {}
    for name in GATE_ORDER:
        group = gates.get(name, {})
        mode = str(group.get("mode", "disabled"))
        commands = [
            split_gate_command(str(command))
            for command in group.get("commands", [])
        ]
        result[name] = (mode, commands)
    return result


def _payload_file_count(payload_root: Path) -> int:
    """
    @brief      Count the payload files a copy would install (exclusions applied,
                manifest excluded), for deploy.payload-copy's file-count verify.
    @param[in]  payload_root Payload (template) root directory.
    @return     Number of non-excluded payload files.
    @exception  OSError If the payload tree cannot be walked.
    """
    count = 0
    for source in payload_root.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(payload_root)
        if should_exclude(relative):
            continue
        if relative.as_posix() == MANIFEST_RELATIVE_PATH:
            continue
        count += 1
    return count


def _sanitize_url(url: str) -> str:
    """
    @brief      Strip any embedded password from a URL before journaling (AD-10).
    @param[in]  url Candidate remote URL.
    @return     The URL with a ``user:secret@`` credential reduced to ``user@``;
                unparseable values pass through unchanged.
    @exception  None
    """
    return gitops.sanitize_clone_url(url)


def _clone_host_port(url: str) -> tuple[str, int] | None:
    """
    @brief      Extract the ``(host, port)`` connectivity target from a clone URL.
    @param[in]  url The answered clone URL.
    @return     ``(host, port)`` (port defaults to 443) for a scheme-qualified
                URL, or ``None`` for scp-like or unparseable forms — the proxy
                probe then reports configuration only, without a connect test.
    @exception  None
    """
    if "://" not in url:
        return None
    parsed = urlsplit(url)
    if not parsed.hostname:
        return None
    return parsed.hostname, parsed.port or 443


def _first_operator_prompt(target: Path) -> str | None:
    """
    @brief      Extract the first operator prompt from the *copied* cheat sheet.
    @details    Reads ``TARGET/.agentic/documents/PROMPT_CHEATSHEET.md`` (the
                shipped file, so the handoff text cannot drift from the payload)
                and returns its first fenced ```` ```text ```` block.
    @param[in]  target Target repository root.
    @return     The prompt text, or ``None`` when the file or block is absent.
    @exception  None
    """
    cheatsheet = target / ".agentic" / "documents" / "PROMPT_CHEATSHEET.md"
    try:
        text = cheatsheet.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FIRST_PROMPT_RE.search(text)
    return match.group(1).strip() if match else None


def _workflow_document(target: Path) -> Mapping[str, Any] | None:
    """
    @brief      Parse the target's workflow.toml, degrading to ``None``.
    @param[in]  target Target repository root.
    @return     The parsed document, or ``None`` when absent/unparseable.
    @exception  None
    """
    path = target / WORKFLOW_TOML_RELATIVE_PATH
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _hooks_and_adapters_missing(target: Path) -> list[str]:
    """
    @brief      List every required hook file and adapter directory absent from
                TARGET (verify.hooks-present's shared predicate).
    @param[in]  target Target repository root.
    @return     Sorted repo-relative names of missing items (empty = all present).
    @exception  None
    """
    missing: list[str] = []
    for hook in HOOK_FILES:
        if not (target / ".agentic" / "hooks" / hook).is_file():
            missing.append(f".agentic/hooks/{hook}")
    for adapter in ADAPTER_DIR_NAMES:
        if not (target / adapter).is_dir():
            missing.append(adapter)
    return sorted(missing)


# --- step: home.init ---------------------------------------------------------


def _home_dir(ctx: EngineContext) -> Path:
    """
    @brief      The WAEGIS home directory for this run.
    @param[in]  ctx Active engine context.
    @return     The shared home override, or :func:`waegis_home`.
    @exception  None
    """
    return ctx.shared.get(SHARED_HOME) or waegis_home()


def _detect_home_init(ctx: EngineContext) -> bool:
    """
    @brief      home.init detect: home and journals directories already exist.
    @param[in]  ctx Active engine context.
    @return     ``True`` when both directories exist.
    @exception  None
    """
    home = _home_dir(ctx)
    return home.is_dir() and (home / "journals").is_dir()


def _act_home_init(ctx: EngineContext) -> None:
    """
    @brief      home.init act: create the home and journals directories.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  OSError If the directories cannot be created.
    """
    home = _home_dir(ctx)
    (home / "journals").mkdir(parents=True, exist_ok=True)
    ctx.record_artifact(str(home))


def _verify_home_init(ctx: EngineContext) -> bool:
    """
    @brief      home.init verify: write-read probe inside the home directory.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the home exists and the round trip succeeds.
    @exception  None
    """
    home = _home_dir(ctx)
    return home.is_dir() and _probe_write_read(home)


# --- steps: machine.os / machine.disk ----------------------------------------


def _detect_machine_os(ctx: EngineContext) -> bool:
    """
    @brief      machine.os detect: run the OS-support probe and record it.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the OS is inside the support matrix.
    @exception  None
    """
    finding = probe_os_support()
    _note_finding(ctx, finding)
    return finding.status == "ok"


def _detect_machine_disk(ctx: EngineContext) -> bool:
    """
    @brief      machine.disk detect: probe free space at the TARGET drive.
    @param[in]  ctx Active engine context.
    @return     ``True`` when free space meets the minimum.
    @exception  OSError If no ancestor of TARGET is accessible.
    """
    finding = probe_disk_space(_nearest_existing(get_target(ctx)), minimum_bytes=MIN_FREE_DISK_BYTES)
    _note_finding(ctx, finding)
    return finding.status == "ok"


def _verify_machine_disk(ctx: EngineContext) -> bool:
    """
    @brief      machine.disk verify: fail only on a genuine sub-minimum blocker.
    @param[in]  ctx Active engine context.
    @return     ``True`` unless the re-probe reports ``fail``.
    @exception  OSError If no ancestor of TARGET is accessible.
    """
    finding = probe_disk_space(_nearest_existing(get_target(ctx)), minimum_bytes=MIN_FREE_DISK_BYTES)
    return finding.status != "fail"


def _on_fail_machine_disk(ctx: EngineContext) -> Remediation:
    """
    @brief      machine.disk remediation: free space before continuing.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="The drive holding TARGET has less than 1 GiB of free space.",
        remediation="Free at least 1 GiB on that drive (delete files or empty the recycle bin), "
        "or choose a TARGET on another drive, then re-run the wizard.",
        it_request=None,
    )


# --- steps: prereq.python / prereq.git ----------------------------------------


def _detect_prereq_python(ctx: EngineContext) -> bool:
    """
    @brief      prereq.python detect: probe for a usable Python 3.11+.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the probe reports ``ok``.
    @exception  None
    """
    finding = probe_python(get_runner(ctx))
    _note_finding(ctx, finding)
    return finding.status == "ok"


def _act_prereq_python(ctx: EngineContext) -> None:
    """
    @brief      prereq.python act: guide the install; never install privileged
                software itself (documented interpretation of §8.1).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  None
    """
    finding = probe_python(get_runner(ctx))
    _note_finding(ctx, finding)
    ctx.note(
        "WAEGIS does not perform privileged installs: run the command above in a separate "
        "terminal, then let the wizard continue - this step re-probes to verify."
    )


def _verify_prereq_python(ctx: EngineContext) -> bool:
    """
    @brief      prereq.python verify: re-probe reports a version >= 3.11.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the re-probe reports ``ok``.
    @exception  None
    """
    return probe_python(get_runner(ctx)).status == "ok"


def _on_fail_prereq_python(ctx: EngineContext) -> Remediation:
    """
    @brief      prereq.python remediation with the probe's OS-keyed guidance.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    finding = probe_python(get_runner(ctx))
    return Remediation(
        diagnosis=finding.detail,
        remediation=finding.guidance or "Install Python 3.11 or newer and ensure it is on PATH.",
        it_request=finding.guidance,
    )


def _detect_prereq_git(ctx: EngineContext) -> bool:
    """
    @brief      prereq.git detect: probe for git >= 2.30.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the probe reports ``ok``.
    @exception  None
    """
    finding = probe_git(get_runner(ctx))
    _note_finding(ctx, finding)
    return finding.status == "ok"


def _act_prereq_git(ctx: EngineContext) -> None:
    """
    @brief      prereq.git act: guide the install (no privileged installs).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  None
    """
    finding = probe_git(get_runner(ctx))
    _note_finding(ctx, finding)
    ctx.note(
        "WAEGIS does not perform privileged installs: run the command above in a separate "
        "terminal, then let the wizard continue - this step re-probes to verify."
    )


def _verify_prereq_git(ctx: EngineContext) -> bool:
    """
    @brief      prereq.git verify: re-probe reports git >= 2.30.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the re-probe reports ``ok``.
    @exception  None
    """
    return probe_git(get_runner(ctx)).status == "ok"


def _on_fail_prereq_git(ctx: EngineContext) -> Remediation:
    """
    @brief      prereq.git remediation with the probe's OS-keyed guidance.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    finding = probe_git(get_runner(ctx))
    return Remediation(
        diagnosis=finding.detail,
        remediation=finding.guidance or "Install Git 2.30 or newer and ensure it is on PATH.",
        it_request=finding.guidance,
    )


# --- step: prereq.node ----------------------------------------------------------


def _detect_prereq_node(ctx: EngineContext) -> bool:
    """
    @brief      prereq.node detect: probe for Node.js and record the finding.
    @details    Report-only, like ``machine.os``: this step's ``verify`` always
                passes (see its ``StepSpec`` below), so a missing Node never
                stops the run — it only means every AEGIS hook will not run
                until Node is installed, which the recorded note/guidance
                makes explicit.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the probe reports ``ok`` (found and parseable).
    @exception  None
    """
    finding = probe_node(get_runner(ctx))
    _note_finding(ctx, finding)
    return finding.status == "ok"


# --- step: prereq.git-identity -------------------------------------------------


def _identity_probe_path(ctx: EngineContext) -> Path:
    """
    @brief      Path to read the effective git identity against.
    @details    TARGET may not exist yet at P1; the nearest existing ancestor
                lets ``git config`` fall through to the global configuration.
    @param[in]  ctx Active engine context.
    @return     An existing directory path.
    @exception  None
    """
    return _nearest_existing(get_target(ctx))


def _detect_git_identity(ctx: EngineContext) -> bool:
    """
    @brief      prereq.git-identity detect: user.name and user.email both set.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the effective identity is complete.
    @exception  None
    """
    identity = gitops.get_identity(get_runner(ctx), _identity_probe_path(ctx))
    if identity.name and identity.email:
        ctx.note(f"git identity: {identity.name} <{identity.email}>")
        return True
    ctx.note("git identity incomplete: user.name and/or user.email is not configured")
    return False


def _act_git_identity(ctx: EngineContext) -> None:
    """
    @brief      prereq.git-identity act: record a pending repo-local identity
                from the answers, or guide the exact global commands.
    @details    Plan §8.1's detect text — "set (global or will be set
                repo-local)" — is realized here: when the answers supply
                ``git_user_name``/``git_user_email``, the pair is recorded and
                ``repo.init-or-clone`` applies it with ``git config --local``
                once the repository exists.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  None
    """
    answers = get_answers(ctx)
    name = str(answers.get("git_user_name") or "").strip()
    email = str(answers.get("git_user_email") or "").strip()
    if name and email:
        ctx.shared[SHARED_PENDING_IDENTITY] = (name, email)
        ctx.record_answer("git_user_name", name)
        ctx.record_answer("git_user_email", email)
        ctx.note(f"identity will be set repo-locally after init: {name} <{email}>")
        return
    ctx.note("Set your git identity by running these two commands, then continue:")
    ctx.note('  git config --global user.name "Your Name"')
    ctx.note('  git config --global user.email "you@example.com"')
    ctx.note(
        "(In a non-interactive run, supply the git_user_name and git_user_email answers "
        "instead - the wizard then sets a repo-local identity after 'git init'.)"
    )


def _verify_git_identity(ctx: EngineContext) -> bool:
    """
    @brief      prereq.git-identity verify: identity is set, or a valid pending
                repo-local pair is recorded.
    @param[in]  ctx Active engine context.
    @return     ``True`` when either condition holds.
    @exception  None
    """
    identity = gitops.get_identity(get_runner(ctx), _identity_probe_path(ctx))
    if identity.name and identity.email:
        return True
    pending = ctx.shared.get(SHARED_PENDING_IDENTITY)
    return bool(pending and pending[0] and pending[1])


def _on_fail_git_identity(ctx: EngineContext) -> Remediation:
    """
    @brief      prereq.git-identity remediation naming the exact commands.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="Git does not know who you are, so it cannot record commits.",
        remediation='Run: git config --global user.name "Your Name" and '
        'git config --global user.email "you@example.com", then re-run the wizard. '
        "Non-interactive runs may supply git_user_name/git_user_email answers instead.",
        it_request=None,
    )


# --- step: net.proxy ------------------------------------------------------------


def _applies_net_proxy(ctx: EngineContext) -> bool:
    """
    @brief      net.proxy applies only when a remote clone was requested.
    @param[in]  ctx Active engine context.
    @return     ``True`` when a clone URL was answered.
    @exception  None
    """
    return bool(ctx.shared.get(SHARED_CLONE_URL))


def _act_net_proxy(ctx: EngineContext) -> None:
    """
    @brief      net.proxy act: run the T2.2 proxy probe against the clone host.
    @details    Env vars and (on Windows) the system proxy are inspected; a
                direct-vs-proxied connect test runs only when the command
                injected a transport and the clone URL yields a host. A
                ``fail`` finding is rendered as an IT-forwardable blocking
                point in the step notes.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  OSError Propagated from :func:`probe_proxy_configuration` (in
                turn from the injected transport's ``connect``) for a failure
                kind it does not map to a :data:`ConnectOutcome`.
    """
    clone_url = str(ctx.shared.get(SHARED_CLONE_URL) or "")
    target_pair = _clone_host_port(clone_url)
    finding = probe_proxy_configuration(
        os.environ,
        registry=ctx.shared.get(SHARED_REGISTRY_READER),
        transport=ctx.shared.get(SHARED_TRANSPORT),
        target=target_pair,
    )
    ctx.shared[SHARED_NET_PROXY_FINDING] = finding
    _note_finding(ctx, finding)
    if finding.status == "fail":
        host = target_pair[0] if target_pair else clone_url
        report = to_blocking_point_report(
            finding,
            step_id="net.proxy",
            title="Network path to the clone host is blocked",
            attempted=f"connectivity check for {host} (direct, then via the configured proxy)",
            why="a remote clone URL was requested, so the wizard verified the host is reachable "
            "before attempting 'git clone'",
        )
        ctx.note("BLOCKING POINT (copy this to IT): " + json.dumps(report.to_dict(), ensure_ascii=False))


def _verify_net_proxy(ctx: EngineContext) -> bool:
    """
    @brief      net.proxy verify: the recorded finding is not a hard failure.
    @param[in]  ctx Active engine context.
    @return     ``True`` for ``ok``/``info`` findings.
    @exception  None
    """
    finding = ctx.shared.get(SHARED_NET_PROXY_FINDING)
    return finding is not None and finding.status != "fail"


def _on_fail_net_proxy(ctx: EngineContext) -> Remediation:
    """
    @brief      net.proxy remediation from the probe's own guidance.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    finding = ctx.shared.get(SHARED_NET_PROXY_FINDING)
    detail = finding.detail if finding is not None else "the network check did not run"
    guidance = finding.guidance if finding is not None else None
    return Remediation(
        diagnosis=detail,
        remediation="Forward the blocking-point report from the step notes to IT, or re-run "
        "without a clone URL to create a local-only repository.",
        it_request=guidance,
    )


# --- step: repo.target-path -----------------------------------------------------


def _nested_in_foreign_work_tree(ctx: EngineContext) -> bool:
    """
    @brief      Whether TARGET's parent lies inside an existing git work tree.
    @details    Checks the parent (not TARGET itself) so a re-run against the
                repository this wizard created is not misreported as nesting.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the parent is inside a work tree.
    @exception  None
    """
    parent = _nearest_existing(get_target(ctx).parent)
    return gitops.is_work_tree(get_runner(ctx), parent)


def _detect_target_path(ctx: EngineContext) -> bool:
    """
    @brief      repo.target-path detect: TARGET is an existing directory not
                nested inside a foreign work tree.
    @param[in]  ctx Active engine context.
    @return     ``True`` when both conditions hold.
    @exception  None
    """
    return get_target(ctx).is_dir() and not _nested_in_foreign_work_tree(ctx)


def _act_target_path(ctx: EngineContext) -> None:
    """
    @brief      repo.target-path act: confirm nesting (if any) and create TARGET.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If the operator declines to nest inside another
                work tree.
    @exception  OSError If the directory cannot be created.
    """
    target = get_target(ctx)
    if _nested_in_foreign_work_tree(ctx):
        ctx.note(f"warning: {target} lies inside an existing git work tree")
        if not ctx.asker.confirm(
            "TARGET is inside another git repository. Create a nested repository anyway? "
            "The outer repository will see the whole nested tree as untracked content.",
            default=False,
            decision=ACCEPT_NESTED_REPOSITORY_KEY,
        ):
            raise RuntimeError("operator declined to create TARGET inside another git work tree")
    target.mkdir(parents=True, exist_ok=True)
    ctx.record_artifact(str(target))


def _verify_target_path(ctx: EngineContext) -> bool:
    """
    @brief      repo.target-path verify: TARGET exists and is writable.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the write-read probe succeeds.
    @exception  None
    """
    target = get_target(ctx)
    return target.is_dir() and _probe_write_read(target)


# --- step: repo.init-or-clone ----------------------------------------------------


def _detect_init_or_clone(ctx: EngineContext) -> bool:
    """
    @brief      repo.init-or-clone detect: TARGET is already a git work tree.
    @param[in]  ctx Active engine context.
    @return     ``True`` when ``git rev-parse --is-inside-work-tree`` says so.
    @exception  None
    """
    return gitops.is_work_tree(get_runner(ctx), get_target(ctx))


def _act_init_or_clone(ctx: EngineContext) -> None:
    """
    @brief      repo.init-or-clone act: ``git init -b main`` (default) or
                ``git clone`` per the answered URL, then apply any pending
                repo-local identity.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If the git operation or identity write fails
                (surfaced as a step failure with git's own message).
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    clone_url = str(ctx.shared.get(SHARED_CLONE_URL) or "")
    if clone_url:
        result = gitops.clone_repo(runner, clone_url, target)
        ctx.record_answer("clone_url", _sanitize_url(clone_url))
    else:
        result = gitops.init_repo(runner, target, initial_branch="main")
        ctx.record_answer("initial_branch", "main")
    if not result.ok:
        raise RuntimeError(f"git {'clone' if clone_url else 'init'} failed: {result.detail}")
    pending = ctx.shared.get(SHARED_PENDING_IDENTITY)
    if pending:
        identity_result = gitops.set_identity(runner, target, pending[0], pending[1], local=True)
        if not identity_result.ok:
            raise RuntimeError(f"setting the repo-local git identity failed: {identity_result.detail}")
        ctx.note(f"repo-local git identity set: {pending[0]} <{pending[1]}>")
    ctx.record_artifact(str(target / ".git"))


def _verify_init_or_clone(ctx: EngineContext) -> bool:
    """
    @brief      repo.init-or-clone verify: TARGET is now a git work tree.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the re-check passes.
    @exception  None
    """
    return gitops.is_work_tree(get_runner(ctx), get_target(ctx))


# --- step: deploy.payload-copy ----------------------------------------------------


def _detect_payload_copy(ctx: EngineContext) -> bool:
    """
    @brief      deploy.payload-copy detect: a valid manifest exists and every
                recorded file still hash-matches (already copied).
    @param[in]  ctx Active engine context.
    @return     ``True`` when the manifest is valid with clean drift.
    @exception  OSError If a recorded file cannot be hashed.
    """
    load = load_manifest(get_target(ctx))
    if load.state is not ManifestState.VALID or load.manifest is None:
        return False
    drift = compute_drift(get_target(ctx), load.manifest)
    if drift.modified or drift.missing:
        ctx.note(
            f"manifest present but drifted: {len(drift.modified)} modified, {len(drift.missing)} missing"
        )
        return False
    ctx.note("install manifest present and every recorded file hash-matches")
    return True


def _act_payload_copy(ctx: EngineContext) -> None:
    """
    @brief      deploy.payload-copy act: locate the payload and copy it in
                strict new-project mode (never overwrites — T3.2).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  waegis.payload.locate.PayloadLocateError If no payload resolves.
    @exception  waegis.payload.copier.CopierError On a strict-mode refusal
                (pre-existing files) or copy failure.
    """
    payload = get_payload_root(ctx)
    target = get_target(ctx)
    result = copy_payload(
        payload,
        target,
        mode="new",
        # Crash safety: the copy writes hundreds of files one at a time, so an
        # interruption partway through would otherwise leave a half-scaffolded
        # directory and no manifest. The journal is staged over exactly the
        # destinations the apply phase will touch and rolls back on the next
        # WAEGIS command if this process never finishes.
        on_apply=lambda paths: payload_transaction(target, command="new", paths=paths),
    )
    assert (
        result.manifest is not None and result.manifest_file is not None
    ), "copy_payload must produce a manifest on a non-dry-run apply"
    ctx.record_answer("payload_version", result.manifest.payload_version)
    ctx.record_artifact(str(result.manifest_file))
    ctx.note(f"copied {len(result.copied)} payload files from {payload}")


def _verify_payload_copy(ctx: EngineContext) -> bool:
    """
    @brief      deploy.payload-copy verify: re-hash every copied file against
                the manifest and match the source payload's file count.
    @param[in]  ctx Active engine context.
    @return     ``True`` when drift is clean and the counts agree.
    @exception  OSError If hashing or the payload walk fails.
    """
    load = load_manifest(get_target(ctx))
    if load.state is not ManifestState.VALID or load.manifest is None:
        return False
    drift = compute_drift(get_target(ctx), load.manifest)
    if drift.modified or drift.missing:
        return False
    expected = _payload_file_count(get_payload_root(ctx))
    if len(load.manifest.files) != expected:
        ctx.note(f"file count mismatch: manifest records {len(load.manifest.files)}, payload ships {expected}")
        return False
    return True


def _on_fail_payload_copy(ctx: EngineContext) -> Remediation:
    """
    @brief      deploy.payload-copy remediation for the strict-refusal case.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="The payload could not be copied - most commonly because TARGET already "
        "contains files the strict new-project mode refuses to overwrite.",
        remediation="Use an empty directory for a new project, or run 'waegis adopt' for an "
        "existing repository (adopt resolves conflicts file by file).",
        it_request=None,
    )


# --- step: deploy.workflow-toml -----------------------------------------------------


def detect_workflow_toml(ctx: EngineContext) -> bool:
    """
    @brief      deploy.workflow-toml detect: an answers-generated workflow.toml
                is already in place.
    @details    The verbatim template copy also parses and satisfies the
                invariants, so the decisive signal is the manifest listing the
                file under ``generated``.
    @param[in]  ctx Active engine context.
    @return     ``True`` when generated, parseable, and invariant-clean.
    @exception  None
    """
    target = get_target(ctx)
    load = load_manifest(target)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return False
    if WORKFLOW_TOML_RELATIVE_PATH not in load.manifest.generated:
        return False
    document = _workflow_document(target)
    if document is None:
        return False
    source_roots = document.get("source", {}).get("roots", [])
    test_roots = document.get("tests", {}).get("roots", [])
    try:
        verify_workflow_invariants(
            document,
            source_roots=source_roots,
            test_roots=test_roots,
            repo_root=target,
        )
    except WorkflowTomlError:
        return False
    return True


def _act_workflow_toml(ctx: EngineContext) -> None:
    """
    @brief      deploy.workflow-toml act: interview, generate, write, create
                missing roots, and amend the install manifest.
    @details    The interview drives :data:`WORKFLOW_FIELD_SPECS` through the
                active asker (ConsoleAsker interactively, ScriptedAsker under
                ``--answers``/``--non-interactive``); language ``other``
                additionally asks :data:`OTHER_LANGUAGE_FIELD_SPECS`. The base
                text is the payload's own workflow.toml (T4.1 contract). Every
                ``GateWarning`` is recorded loudly via ``ctx.note`` (plan §7).
                The manifest amendment moves ``.agentic/workflow.toml`` from
                ``files`` to ``generated`` (module docstring rationale).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  waegis.io.prompts.PromptsError On a missing/invalid scripted answer.
    @exception  waegis.repo.workflow_toml.WorkflowTomlError If generation or an
                invariant fails (never-save-invalid guard).
    @exception  OSError If the file or roots cannot be written.
    @exception  FileNotFoundError If the amendment step finds no install
                manifest under ``target``.
    @exception  waegis.payload.manifest.ManifestError If the existing install
                manifest is invalid.
    """
    target = get_target(ctx)
    collected: dict[str, Any] = {}
    for spec in WORKFLOW_FIELD_SPECS:
        collected[spec.key] = ask_field(ctx, spec)
        ctx.record_answer(spec.key, collected[spec.key])
    extras: dict[str, Any] = {"source_extensions": None, "test_file_patterns": None}
    if collected["language"] == "other":
        for spec in OTHER_LANGUAGE_FIELD_SPECS:
            extras[spec.key] = ask_field(ctx, spec)
            ctx.record_answer(spec.key, extras[spec.key])

    base_text = (get_payload_root(ctx) / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    generated = generate_workflow_toml(base_text, **collected, **extras)
    for warning in generated.warnings:
        ctx.note(f"WARNING: {warning.message}")

    workflow_path = target / WORKFLOW_TOML_RELATIVE_PATH
    workflow_path.parent.mkdir(parents=True, exist_ok=True)
    workflow_path.write_text(generated.text, encoding="utf-8", newline="")
    ctx.record_artifact(str(workflow_path))

    # Roots are stored normalized for this step's verify; a resumed run
    # re-derives them from the written file instead.
    source_roots = [str(root) for root in collected["source_roots"]]
    test_roots = [str(root) for root in collected["test_roots"]]
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

    amend_manifest_generated(target, answers=normalize_stored_answers({**collected, **extras}))
    ctx.note("install manifest amended: .agentic/workflow.toml moved from files to generated")


def amend_manifest_generated(target: Path, *, answers: Mapping[str, Any] | None = None) -> None:
    """
    @brief      Move ``.agentic/workflow.toml`` from the manifest's ``files``
                map into its ``generated`` list (idempotent).
    @details    Done at generation time — not at copy time via ``copy_payload``'s
                ``generated`` parameter — so the manifest is truthful at every
                checkpoint (plan §6: ``generated`` means *rewritten from
                answers*, which only becomes true here). Dropping the entry
                from ``files`` keeps drift reports clean and keeps
                ``deploy.payload-copy``'s detect green on re-runs.
    @param[in]  target Target repository root holding the manifest.
    @param[in]  answers The durable generator answers to record, already
                reduced through
                :func:`waegis.repo.workflow_toml.normalize_stored_answers` by
                the calling wizard. ``None`` leaves the existing configuration
                untouched (the file-move-only amendment). Every wizard that
                generates the workflow passes them: a manifest without them
                cannot answer "what was this configured with", and a later
                ``configure`` would have to ask for settings the repository
                already holds.
    @return     None
    @exception  FileNotFoundError If no manifest exists.
    @exception  waegis.payload.manifest.ManifestError If the manifest is invalid.
    @exception  OSError If the manifest cannot be re-written.
    """
    manifest = read_manifest(target)
    files = {key: entry for key, entry in manifest.files.items() if key != WORKFLOW_TOML_RELATIVE_PATH}
    generated = manifest.generated
    if WORKFLOW_TOML_RELATIVE_PATH not in generated:
        generated = (*generated, WORKFLOW_TOML_RELATIVE_PATH)
    configuration = dict(manifest.configuration)
    if answers is not None:
        workflow_hash = hash_file(target / WORKFLOW_TOML_RELATIVE_PATH).sha256
        configuration = {
            "answers": {key: answers[key] for key in sorted(answers)},
            "generator_version": WIZARD_VERSION,
            "generated_files": {WORKFLOW_TOML_RELATIVE_PATH: {"sha256": workflow_hash}},
        }
    write_manifest(
        target,
        replace(manifest, files=files, generated=generated, configuration=configuration),
    )


def verify_workflow_toml(ctx: EngineContext) -> bool:
    """
    @brief      deploy.workflow-toml verify: re-parse, re-run the invariants
                against the answered roots, require the roots to exist, and
                require the manifest amendment.
    @param[in]  ctx Active engine context.
    @return     ``True`` when every check passes.
    @exception  None
    """
    target = get_target(ctx)
    document = _workflow_document(target)
    if document is None:
        return False
    roots = ctx.shared.get(SHARED_WORKFLOW_ROOTS)
    if roots is None:
        source_roots = document.get("source", {}).get("roots", [])
        test_roots = document.get("tests", {}).get("roots", [])
    else:
        source_roots, test_roots = roots
    try:
        verify_workflow_invariants(
            document,
            source_roots=source_roots,
            test_roots=test_roots,
            repo_root=target,
        )
    except WorkflowTomlError as exc:
        ctx.note(f"invariant check failed: {exc}")
        return False
    for root in (*source_roots, *test_roots):
        if not (target / root).is_dir():
            ctx.note(f"configured root does not exist: {root}")
            return False
    load = load_manifest(target)
    if load.state is not ManifestState.VALID or load.manifest is None:
        return False
    return (
        WORKFLOW_TOML_RELATIVE_PATH in load.manifest.generated
        and WORKFLOW_TOML_RELATIVE_PATH not in load.manifest.files
    )


def on_fail_workflow_toml(ctx: EngineContext) -> Remediation:
    """
    @brief      deploy.workflow-toml remediation.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="The workflow configuration could not be generated or verified.",
        remediation="Check the step notes for the failed invariant or missing root, correct the "
        "answers (source_roots/test_roots/language/gates), and re-run - completed steps are skipped.",
        it_request=None,
    )


# --- step: deploy.gates ----------------------------------------------------------


def _gate_secret_patterns(ctx: EngineContext, target: Path) -> tuple[re.Pattern[str], ...]:
    """
    @brief      The repository's own configured secret patterns, compiled.
    @details    Single source, deliberately: ``guardrails.secrets.patterns`` in
                the written workflow.toml *is* the persisted ``secret_patterns``
                answer, and reading it from disk keeps this consistent with
                :func:`_read_gates` on a resumed run whose interview step was
                skipped. The in-memory answer is only consulted when the file
                cannot be read at all. No second pattern list is invented here:
                a repository that configured no patterns gets no redaction,
                which is the same contract its own guardrails run under.
                A pattern that does not compile is skipped rather than fatal —
                the gate has already failed and losing the evidence entirely
                would be the worse outcome.
    @param[in]  ctx Active engine context.
    @param[in]  target Target repository root.
    @return     The compiled patterns, possibly empty.
    @exception  None
    """
    document = _workflow_document(target)
    if document is not None:
        raw = document.get("guardrails", {}).get("secrets", {}).get("patterns", [])
    else:
        raw = get_answers(ctx).get("secret_patterns", [])
    compiled: list[re.Pattern[str]] = []
    for pattern in raw if isinstance(raw, (list, tuple)) else ():
        try:
            compiled.append(re.compile(str(pattern)))
        except re.error:
            continue
    return tuple(compiled)


def _redact(text: str, patterns: Sequence[re.Pattern[str]]) -> str:
    """
    @brief      Replace every configured-secret match with a fixed marker.
    @param[in]  text Raw captured output.
    @param[in]  patterns Compiled secret patterns.
    @return     The redacted text (unchanged when no pattern matches).
    @exception  None
    """
    for pattern in patterns:
        text = pattern.sub("[REDACTED]", text)
    return text


def _bounded_tail(text: str) -> tuple[str, bool]:
    """
    @brief      Keep the last :data:`GATE_OUTPUT_TAIL_LIMIT` characters of a
                captured stream.
    @param[in]  text Redacted stream text.
    @return     ``(tail, truncated)``.
    @exception  None
    """
    if len(text) <= GATE_OUTPUT_TAIL_LIMIT:
        return text, False
    return text[-GATE_OUTPUT_TAIL_LIMIT:], True


def _gate_reproduction(argv: Sequence[str], cwd: Path) -> str:
    """
    @brief      The exact command that re-runs one failed gate by hand.
    @details    ``shlex.join`` quotes each argument of the argv
                :func:`_read_gates` built, so what is printed re-runs what was
                run. On Windows a native path is emitted single-quoted, which
                PowerShell takes literally — the same shell the deployment
                tooling uses there.
    @param[in]  argv The gate command's argument vector.
    @param[in]  cwd The working directory it ran in.
    @return     A single copyable shell line.
    @exception  None
    """
    return f"cd {shlex.quote(str(cwd))} && {shlex.join(argv)}"


def _write_gate_log(
    ctx: EngineContext,
    *,
    gate_name: str,
    argv: Sequence[str],
    cwd: Path,
    result: Any,
    duration: float,
    patterns: Sequence[re.Pattern[str]],
) -> str | None:
    """
    @brief      Write one failed gate command's full, redacted output to a
                durable log file under the WAEGIS home.
    @details    Large output belongs in an isolated file rather than the
                journal or the ``--json`` envelope, which both stay bounded.
                Redaction is applied here as well as to the inline tails: the
                log is the copy an operator is most likely to paste elsewhere.
                A log that cannot be written is not fatal — the bounded tails
                still carry a diagnosis — so this returns ``None`` instead of
                raising and taking the gate's evidence down with it.
    @param[in]  ctx Active engine context.
    @param[in]  gate_name The gate group (``test``, ``lint``, ...).
    @param[in]  argv The gate command's argument vector.
    @param[in]  cwd The working directory it ran in.
    @param[in]  result The command result being recorded.
    @param[in]  duration Wall-clock seconds the command took.
    @param[in]  patterns Compiled secret patterns.
    @return     The log file path as text, or ``None`` when it could not be
                written.
    @exception  None
    """
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    directory = _home_dir(ctx) / "logs" / GATE_LOG_DIRNAME
    path = directory / f"{stamp}-{uuid.uuid4().hex[:6]}.log"
    # The whole body is redacted — including the argv/reproduce header lines,
    # so a credential embedded in the gate command itself never persists.
    body = _redact(
        (
            f"gate: {gate_name}\n"
            f"argv: {json.dumps(list(argv))}\n"
            f"cwd: {cwd}\n"
            f"exit_code: {result.exit_code}\n"
            f"found: {result.found}\n"
            f"timed_out: {result.timed_out}\n"
            f"timeout_seconds: {GATE_TIMEOUT_SECONDS}\n"
            f"duration_seconds: {duration:.3f}\n"
            f"reproduce: {_gate_reproduction(argv, cwd)}\n"
            "--- stdout ---\n"
            f"{result.stdout}\n"
            "--- stderr ---\n"
            f"{result.stderr}\n"
        ),
        patterns,
    )
    try:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    except OSError:
        return None
    return str(path)


def _gate_failure_record(
    ctx: EngineContext,
    *,
    gate_name: str,
    argv: Sequence[str],
    cwd: Path,
    result: Any,
    duration: float,
    patterns: Sequence[re.Pattern[str]],
) -> dict[str, Any]:
    """
    @brief      Build the journalled evidence record for one failed gate command.
    @details    Everything a post-mortem needs without re-running the gate:
                what ran, where, how it ended, how long it took, the bounded
                redacted tails of both streams, whether those tails were cut,
                where the full log is, and the one-line reproduction. The
                ``decision`` field is filled in by the caller once the operator
                (or the answers file) has decided; it is not a gate *outcome*
                and never enters the ``gate_outcomes`` vocabulary.
    @param[in]  ctx Active engine context.
    @param[in]  gate_name The gate group the command belongs to.
    @param[in]  argv The gate command's argument vector.
    @param[in]  cwd The working directory it ran in.
    @param[in]  result The failing command result.
    @param[in]  duration Wall-clock seconds the command took.
    @param[in]  patterns Compiled secret patterns.
    @return     A JSON-safe evidence mapping.
    @exception  None
    """
    stdout_tail, stdout_truncated = _bounded_tail(_redact(result.stdout, patterns))
    stderr_tail, stderr_truncated = _bounded_tail(_redact(result.stderr, patterns))
    # The command/argv/reproduce fields are redacted too: a gate command that
    # itself embeds a credential must not survive into any evidence sink.
    return {
        "gate": gate_name,
        "command": _redact(" ".join(argv), patterns),
        "argv": [_redact(argument, patterns) for argument in argv],
        "cwd": str(cwd),
        "exit_code": result.exit_code,
        "found": result.found,
        "timed_out": result.timed_out,
        "timeout_seconds": GATE_TIMEOUT_SECONDS,
        "duration_seconds": round(duration, 3),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "truncated": stdout_truncated or stderr_truncated,
        "log_path": _write_gate_log(
            ctx,
            gate_name=gate_name,
            argv=argv,
            cwd=cwd,
            result=result,
            duration=duration,
            patterns=patterns,
        ),
        "reproduce": _redact(_gate_reproduction(argv, cwd), patterns),
        "decision": None,
    }


def _note_gate_failure(ctx: EngineContext, record: Mapping[str, Any]) -> None:
    """
    @brief      Surface one failed gate's evidence pointers on the human stream.
    @details    Notes are journalled *and* printed by the console sink, so this
                is what keeps human and ``--json`` output telling the same
                story: the one-line failure, where the full log is, and the
                exact command that reproduces it.
    @param[in]  ctx Active engine context.
    @param[in]  record The evidence record built for the failure.
    @return     None
    @exception  EngineError If called outside a running step.
    """
    if record["timed_out"]:
        ending = f"timed out after {record['timeout_seconds']}s"
    elif not record["found"]:
        ending = "could not be launched (command not found)"
    else:
        ending = f"exited {record['exit_code']}"
    ctx.note(
        f"gate '{record['gate']}' FAILED: {record['command']} {ending} "
        f"in {record['duration_seconds']}s (cwd: {record['cwd']})"
    )
    if record["log_path"] is not None:
        ctx.note(f"  full output log: {record['log_path']}")
    else:
        ctx.note("  full output log could not be written; the recorded tails are all there is")
    ctx.note(f"  reproduce with: {record['reproduce']}")


def _act_gates(ctx: EngineContext) -> None:
    """
    @brief      deploy.gates act: offer to run each configured gate command once
                in TARGET, recording every outcome; a failing or empty gate must
                be explicitly accepted (recorded, never silent).
    @details    This step is ``AUTO`` automation (not ``ASSISTED``): it asks its
                own top-level "proceed?" confirmation here rather than relying
                on the generic per-step gate, because gate commands (e.g. a
                full test suite) can be slow, and an operator declining to run
                them right now should defer them cleanly (recorded outcome
                ``deferred``, verify still passes) instead of halting the
                whole run the way an ``ASSISTED`` decline would.
    @details    A failing command's evidence is recorded *before* the
                acceptance question is asked, so a refusal — which fails the
                step by raising — still leaves the journal holding everything
                needed to diagnose it. Acceptance itself is a separate decision
                from the run's mutation consent: the confirmation defaults to
                refuse and names :data:`ACCEPT_FAILING_GATES_KEY`, so a
                non-interactive run without that answer is refused loudly
                rather than waived silently.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If the operator refuses to accept a failing or
                empty gate (the step then fails, by their decision).
    @exception  waegis.io.prompts.MissingAnswerError If a non-interactive run
                hits a failing gate without stating the acceptance decision.
    @exception  OSError / tomllib.TOMLDecodeError If workflow.toml is unreadable.
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    gates = _read_gates(target)
    outcomes: dict[str, str] = {}
    failures: list[dict[str, Any]] = []
    if all(mode == "disabled" for mode, _commands in gates.values()):
        for gate_name in gates:
            outcomes[gate_name] = "disabled"
        ctx.note("gate execution is disabled explicitly by workflow.toml")
        ctx.shared[SHARED_GATE_OUTCOMES] = outcomes
        ctx.record_answer("gate_outcomes", outcomes)
        ctx.record_answer("gate_accepted_failing", [])
        return
    if not ctx.asker.confirm("Proceed with 'Try the quality gates once'?", default=True):
        for gate_name, (mode, commands) in gates.items():
            if mode == "disabled":
                outcomes[gate_name] = "disabled"
                continue
            for command in commands:
                outcomes[" ".join(command)] = "deferred"
        ctx.note("gate run deferred entirely by operator (recorded)")
        ctx.shared[SHARED_GATE_OUTCOMES] = outcomes
        ctx.record_answer("gate_outcomes", outcomes)
        ctx.record_answer("gate_accepted_failing", [])
        return
    for gate_name, (mode, commands) in gates.items():
        if mode == "disabled":
            outcomes[gate_name] = "disabled"
            continue
        if not ctx.asker.confirm(
            f"Run the {len(commands)} '{gate_name}' gate command(s) once now inside TARGET?",
            default=True,
        ):
            for command in commands:
                outcomes[" ".join(command)] = "deferred"
            ctx.note(f"gate '{gate_name}': execution deferred by operator (recorded)")
            continue
        for command in commands:
            label = " ".join(command)
            started = time.monotonic()
            result = runner.run(tuple(command), timeout=GATE_TIMEOUT_SECONDS, cwd=target)
            duration = time.monotonic() - started
            if result.ok():
                # A passing gate stays cheap: outcome only, no captured volume.
                ctx.note(f"gate '{gate_name}' PASS: {label}")
                outcomes[label] = "pass"
                continue
            record = _gate_failure_record(
                ctx,
                gate_name=gate_name,
                argv=tuple(command),
                cwd=target,
                result=result,
                duration=duration,
                patterns=_gate_secret_patterns(ctx, target),
            )
            failures.append(record)
            _note_gate_failure(ctx, record)
            # Recorded before the decision so a refusal still journals the
            # evidence on its way out through the raise below.
            ctx.record_answer("gate_failures", failures)
            accepted = ctx.asker.confirm(
                f"Gate command failed: {label}. Accept the failing gate and continue? "
                "It will be recorded as accepted-failing, and the deployment will "
                "report success with an accepted failure.",
                default=False,
                decision=ACCEPT_FAILING_GATES_KEY,
            )
            record["decision"] = "accepted" if accepted else "rejected"
            ctx.record_answer("gate_failures", failures)
            if not accepted:
                ctx.record_answer("gate_outcomes", outcomes)
                raise RuntimeError(f"operator rejected the failing gate command: {label}")
            outcomes[label] = "accepted-failing"
    ctx.shared[SHARED_GATE_OUTCOMES] = outcomes
    ctx.record_answer("gate_outcomes", outcomes)
    ctx.record_answer(
        "gate_accepted_failing",
        [label for label, outcome in outcomes.items() if outcome == "accepted-failing"],
    )
    if failures:
        ctx.record_answer("gate_failures", failures)


def _verify_gates(ctx: EngineContext) -> bool:
    """
    @brief      deploy.gates verify: every gate outcome is recorded.
    @details    Deliberately does NOT require every command to have passed: a
                deliberately accepted failing/deferred/empty gate is a valid,
                recorded outcome (plan §7).
    @param[in]  ctx Active engine context.
    @return     ``True`` when outcomes were recorded with known values.
    @exception  None
    """
    outcomes = ctx.shared.get(SHARED_GATE_OUTCOMES)
    if outcomes is None:
        return False
    allowed = {"pass", "accepted-failing", "deferred", "accepted-empty", "disabled"}
    return all(value in allowed for value in outcomes.values())


# --- steps: verify.cli-smoke / verify.workflow-smoke -------------------------------


def _act_cli_smoke(ctx: EngineContext) -> None:
    """
    @brief      verify.cli-smoke act: run the real wrapper with ``--help``
                inside TARGET.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  None
    """
    target = get_target(ctx)
    argv = _wrapper_invocation(target, "--help")
    result = get_runner(ctx).run(argv, timeout=SMOKE_TIMEOUT_SECONDS, cwd=target)
    ctx.shared[SHARED_CLI_SMOKE_RESULT] = result
    ctx.note(f"ran: {' '.join(argv)} -> exit {result.exit_code}")


def _verify_cli_smoke(ctx: EngineContext) -> bool:
    """
    @brief      verify.cli-smoke verify: the wrapper exited 0.
    @param[in]  ctx Active engine context.
    @return     ``True`` on a found, zero-exit run.
    @exception  None
    """
    result = ctx.shared.get(SHARED_CLI_SMOKE_RESULT)
    return result is not None and result.ok()


def _on_fail_cli_smoke(ctx: EngineContext) -> Remediation:
    """
    @brief      verify.cli-smoke remediation.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    result = ctx.shared.get(SHARED_CLI_SMOKE_RESULT)
    detail = result.combined_output().strip() if result is not None else "the wrapper did not run"
    return Remediation(
        diagnosis=f"The copied workflow wrapper failed its --help smoke test: {detail or 'no output'}",
        remediation="Confirm Python 3.11+ is on PATH for the wrapper (run.ps1 tries 'python' then "
        "'py'; run.sh tries 'python3' then 'python'), then re-run the wizard.",
        it_request="please install Python 3.11+ and, on Windows, allow running local PowerShell "
        "scripts (the wizard invokes run.ps1 with -ExecutionPolicy Bypass for its own check)",
    )


def _act_workflow_smoke(ctx: EngineContext) -> None:
    """
    @brief      Run grouped ``run status --json`` and, when applicable,
                ``verify gates`` through the installed wrapper.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  OSError / tomllib.TOMLDecodeError If workflow.toml is unreadable.
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    status_argv = _wrapper_invocation(target, "run", "status", "--json")
    status_result = runner.run(status_argv, timeout=SMOKE_TIMEOUT_SECONDS, cwd=target)
    ctx.shared[SHARED_WORKFLOW_SMOKE_STATUS] = status_result
    ctx.note(f"ran: {' '.join(status_argv)} -> exit {status_result.exit_code}")

    gates = _read_gates(target)
    outcomes = ctx.shared.get(SHARED_GATE_OUTCOMES) or {}
    all_passed = bool(outcomes) and all(
        value in {"pass", "disabled"} for value in outcomes.values()
    )
    enabled_commands = [
        command
        for mode, commands in gates.values()
        if mode == "enforce"
        for command in commands
    ]
    if enabled_commands and all_passed:
        gates_argv = _wrapper_invocation(target, "verify", "gates")
        gates_result = runner.run(gates_argv, timeout=GATE_TIMEOUT_SECONDS, cwd=target)
        ctx.shared[SHARED_WORKFLOW_SMOKE_GATES] = gates_result
        ctx.note(f"ran: {' '.join(gates_argv)} -> exit {gates_result.exit_code}")


def _verify_workflow_smoke(ctx: EngineContext) -> bool:
    """
    @brief      Verify grouped run status and optional gate responses.
    @details    A fresh install has no active workflow run, and the embedded
                CLI's ``status`` then exits non-zero with "No active agentic
                run" (confirmed against the real template CLI) — that coherent
                response *is* the healthy fresh-install outcome. A zero exit
                must additionally produce JSON-parseable output.
    @param[in]  ctx Active engine context.
    @return     ``True`` when the responses are healthy.
    @exception  None
    """
    status_result = ctx.shared.get(SHARED_WORKFLOW_SMOKE_STATUS)
    if status_result is None:
        return False
    if status_result.ok():
        try:
            json.loads(status_result.stdout)
        except json.JSONDecodeError:
            return False
    elif NO_ACTIVE_RUN_MARKER not in status_result.combined_output():
        return False
    gates_result = ctx.shared.get(SHARED_WORKFLOW_SMOKE_GATES)
    return gates_result is None or gates_result.ok()


def _on_fail_workflow_smoke(ctx: EngineContext) -> Remediation:
    """
    @brief      verify.workflow-smoke remediation.
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    status_result = ctx.shared.get(SHARED_WORKFLOW_SMOKE_STATUS)
    detail = status_result.combined_output().strip() if status_result is not None else "status did not run"
    return Remediation(
        diagnosis=f"The workflow CLI did not respond as expected to 'status': {detail or 'no output'}",
        remediation="Run the wrapper manually inside TARGET (.agentic/tools/run.ps1 status or "
        "bash .agentic/tools/run.sh status) and check the printed error, then re-run the wizard.",
        it_request=None,
    )


# --- step: verify.hooks-present ------------------------------------------------------


def _detect_hooks_present(ctx: EngineContext) -> bool:
    """
    @brief      verify.hooks-present detect: every hook and adapter is present.
    @param[in]  ctx Active engine context.
    @return     ``True`` when nothing is missing.
    @exception  None
    """
    missing = _hooks_and_adapters_missing(get_target(ctx))
    if missing:
        ctx.note("missing: " + ", ".join(missing))
        return False
    ctx.note(f"all {len(HOOK_FILES)} hook files and {len(ADAPTER_DIR_NAMES)} adapter dirs present")
    return True


def _verify_hooks_present(ctx: EngineContext) -> bool:
    """
    @brief      verify.hooks-present verify: same predicate as detect.
    @param[in]  ctx Active engine context.
    @return     ``True`` when nothing is missing.
    @exception  None
    """
    return not _hooks_and_adapters_missing(get_target(ctx))


# --- step: repo.initial-commit --------------------------------------------------------


def _detect_initial_commit(ctx: EngineContext) -> bool:
    """
    @brief      repo.initial-commit detect: clean tree and an existing commit.
    @details    ``status_porcelain`` alone is insufficient — it returns ``[]``
                for a failed git invocation too — so an actual HEAD commit is
                required as well (the reason ``gitops.head_commit`` exists).
    @param[in]  ctx Active engine context.
    @return     ``True`` when committed and clean.
    @exception  None
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    if gitops.status_porcelain(runner, target):
        return False
    return gitops.head_commit(runner, target) is not None


def _act_initial_commit(ctx: EngineContext) -> None:
    """
    @brief      repo.initial-commit act: stage everything and commit with the
                templated bootstrap message.
    @param[in]  ctx Active engine context.
    @return     None
    @exception  RuntimeError If staging or committing fails (git's message is
                surfaced in the step failure).
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    add_result = gitops.add_all(runner, target)
    if not add_result.ok:
        raise RuntimeError(f"git add failed: {add_result.detail}")
    commit_result = gitops.commit(runner, target, INITIAL_COMMIT_MESSAGE)
    if not commit_result.ok:
        raise RuntimeError(f"git commit failed: {commit_result.detail}")
    ctx.record_answer("commit_message", INITIAL_COMMIT_MESSAGE)
    head = gitops.head_commit(runner, target)
    if head:
        ctx.record_artifact(f"commit {head}")


def _verify_initial_commit(ctx: EngineContext) -> bool:
    """
    @brief      repo.initial-commit verify: clean tree and a HEAD commit exist.
    @param[in]  ctx Active engine context.
    @return     ``True`` when both re-checks pass.
    @exception  None
    """
    runner = get_runner(ctx)
    target = get_target(ctx)
    if gitops.status_porcelain(runner, target):
        return False
    return gitops.head_commit(runner, target) is not None


def _on_fail_initial_commit(ctx: EngineContext) -> Remediation:
    """
    @brief      repo.initial-commit remediation (identity is the common cause).
    @param[in]  ctx Active engine context.
    @return     The remediation text.
    @exception  None
    """
    return Remediation(
        diagnosis="The bootstrap commit could not be created.",
        remediation="The most common cause is a missing git identity: run "
        'git config --global user.name "Your Name" and git config --global user.email '
        '"you@example.com" (or supply git_user_name/git_user_email answers), then re-run.',
        it_request=None,
    )


# --- step: handoff.summary -------------------------------------------------------------


def _act_handoff_summary(ctx: EngineContext) -> None:
    """
    @brief      handoff.summary act: journal what was installed, where, the
                first operator prompt, and how to continue.
    @details    The prompt is extracted from the *copied* PROMPT_CHEATSHEET.md
                so it cannot drift from the shipped payload. The ``waegis
                doctor`` pointer points the operator at the real health check
                (T6.1 shipped ``doctor``, so it is no longer a stub).
    @param[in]  ctx Active engine context.
    @return     None
    @exception  None
    """
    target = get_target(ctx)
    load = load_manifest(target)
    payload_version = (
        load.manifest.payload_version if load.state is ManifestState.VALID and load.manifest else "unknown"
    )
    ctx.note(f"AEGIS payload {payload_version} installed at {target} by WAEGIS {WIZARD_VERSION}.")
    prompt = _first_operator_prompt(target)
    if prompt:
        ctx.note("First prompt to try in your agent tool (from .agentic/documents/PROMPT_CHEATSHEET.md):")
        ctx.note(prompt)
    else:
        ctx.note("See .agentic/documents/PROMPT_CHEATSHEET.md in the new project for the first operator prompt.")
    ctx.note(f"Health checks: run 'waegis doctor --repo {target}' any time to validate this install.")
    ctx.note(
        "Orchestrator (WADORE) onboarding is a separate product; this wizard's job ends with a "
        "verified, committed AEGIS repository."
    )
    ctx.record_answer("payload_version", payload_version)


# STEP CATALOG


# @brief The P0-P2 machine/prereq/network prefix step ids Wizard E reuses
#        verbatim (plan §8.2 "Reuses home.init through net.proxy unchanged").
_COMMON_PREFIX_IDS: tuple[str, ...] = (
    "home.init",
    "machine.os",
    "machine.disk",
    "prereq.python",
    "prereq.git",
    "prereq.node",
    "prereq.git-identity",
    "net.proxy",
)

# @brief The three smoke-verify step ids Wizard E reuses verbatim (plan §8.2:
#        "verify.cli-smoke / verify.workflow-smoke / verify.hooks-present ...
#        identical to Wizard N").
_VERIFY_IDS: tuple[str, ...] = (
    "verify.cli-smoke",
    "verify.workflow-smoke",
    "verify.hooks-present",
)


def _build_new_steps() -> list[StepSpec]:
    """
    @brief      Construct every plan §8.1 Wizard N step, in order.
    @details    Kept as one ordered list so the shared prefix/verify/gates
                objects (:data:`COMMON_PREFIX_STEPS`, :data:`VERIFY_STEPS`,
                :data:`GATES_STEP`) are sliced from the very instances the
                Wizard N catalog runs; Wizard E (``commands/adopt.py``) then
                splices those same instances, so the two catalogs share objects
                rather than forking the logic.
    @return     The ordered list of Wizard N :class:`StepSpec` objects.
    @exception  waegis.engine.StepContractError If a step were ever malformed.
    """
    steps = [
        StepSpec(
            id="home.init",
            title="Prepare the WAEGIS home folder",
            why="WAEGIS keeps a journal of every run in a small home folder so an aborted run "
            "can be resumed and later commands (doctor) can see what happened. This step makes "
            "sure that folder exists and is writable.",
            phase=Phase.P0_MACHINE,
            automation=Automation.AUTO,
            detect=_detect_home_init,
            act=_act_home_init,
            verify=_verify_home_init,
            change_summary=lambda ctx: "create the WAEGIS home and journals folder if missing",
        ),
        StepSpec(
            id="machine.os",
            title="Check the operating system",
            why="WAEGIS is verified on Windows 11 and Ubuntu 22.04+. Another OS is reported as a "
            "warning, never a blocker (warn-not-block): this step's verification always passes "
            "and only records what it found.",
            phase=Phase.P0_MACHINE,
            automation=Automation.AUTO,
            preconditions=("home.init",),
            detect=_detect_machine_os,
            verify=lambda ctx: True,
            change_summary=lambda ctx: "report the OS against the support matrix (no changes)",
        ),
        StepSpec(
            id="machine.disk",
            title="Check free disk space",
            why="Deploying the AEGIS payload needs room on the TARGET drive. Unlike the OS check "
            "this one can genuinely block: verification fails only when less than 1 GiB is free.",
            phase=Phase.P0_MACHINE,
            automation=Automation.AUTO,
            preconditions=("machine.os",),
            detect=_detect_machine_disk,
            verify=_verify_machine_disk,
            on_fail=_on_fail_machine_disk,
            change_summary=lambda ctx: "report free space at the TARGET drive (no changes)",
        ),
        StepSpec(
            id="prereq.python",
            title="Check for Python 3.11+",
            why="The copied workflow runs on Python. The wizard never installs privileged "
            "software itself: if Python is missing it shows the exact install command for your "
            "OS, waits for you, and re-checks.",
            phase=Phase.P1_PREREQ,
            automation=Automation.ASSISTED,
            preconditions=("machine.disk",),
            detect=_detect_prereq_python,
            act=_act_prereq_python,
            verify=_verify_prereq_python,
            on_fail=_on_fail_prereq_python,
            change_summary=lambda ctx: "probe python launchers; guide an install if missing",
        ),
        StepSpec(
            id="prereq.git",
            title="Check for Git 2.30+",
            why="The new project is a git repository and the wizard commits the installed "
            "workflow. As with Python, the wizard guides the install and re-checks; it never "
            "installs software itself.",
            phase=Phase.P1_PREREQ,
            automation=Automation.ASSISTED,
            preconditions=("prereq.python",),
            detect=_detect_prereq_git,
            act=_act_prereq_git,
            verify=_verify_prereq_git,
            on_fail=_on_fail_prereq_git,
            change_summary=lambda ctx: "probe git; guide an install if missing",
        ),
        StepSpec(
            id="prereq.node",
            title="Check for Node.js",
            why="The Claude Code, Codex, and Qwen Code adapters dispatch every AEGIS guard "
            "(write-zone, secret scan, protected read, delivery preflight) through Node "
            "(.agentic/tools/run_hook.mjs). Without Node those guards cannot launch, and a "
            "guard that cannot launch does not block - their tool calls run unchecked. Unlike "
            "Python/git this still never stops setup: OpenCode runs the guard in its own "
            "runtime and needs no system Node, and installing Node later makes every hook work "
            "with no repair or re-run.",
            phase=Phase.P1_PREREQ,
            automation=Automation.AUTO,
            preconditions=("prereq.git",),
            detect=_detect_prereq_node,
            verify=lambda ctx: True,
            change_summary=lambda ctx: "probe Node.js, used by every AEGIS hook (no changes, never blocks)",
        ),
        StepSpec(
            id="prereq.git-identity",
            title="Check your git identity",
            why="Git refuses to commit without a user.name and user.email. If they are not set "
            "globally, this step shows the exact commands - or, when the answers supply them, "
            "records an identity the wizard sets repo-locally right after 'git init'.",
            phase=Phase.P1_PREREQ,
            automation=Automation.MANUAL,
            preconditions=("prereq.node",),
            detect=_detect_git_identity,
            act=_act_git_identity,
            verify=_verify_git_identity,
            on_fail=_on_fail_git_identity,
            change_summary=lambda ctx: "read git identity; guide or record a repo-local identity",
        ),
        StepSpec(
            id="net.proxy",
            title="Check the network path to the clone host",
            why="This step only runs when a remote clone URL was requested. It detects a "
            "configured proxy (environment variables, and the Windows system proxy) and tests "
            "reachability, producing an IT-forwardable report when blocked.",
            phase=Phase.P2_NETWORK,
            automation=Automation.AUTO,
            preconditions=("prereq.git-identity",),
            applies=_applies_net_proxy,
            act=_act_net_proxy,
            verify=_verify_net_proxy,
            on_fail=_on_fail_net_proxy,
            change_summary=lambda ctx: "probe proxy configuration and clone-host reachability (no changes)",
        ),
        StepSpec(
            id="repo.target-path",
            title="Prepare the project folder",
            why="The wizard creates TARGET if needed and checks it is writable. If TARGET lies "
            "inside another git repository you are asked to confirm, because nested repositories "
            "are usually a mistake.",
            phase=Phase.P3_REPO,
            automation=Automation.ASSISTED,
            preconditions=("net.proxy",),
            detect=_detect_target_path,
            act=_act_target_path,
            verify=_verify_target_path,
            change_summary=lambda ctx: f"create {get_target(ctx)} if missing and confirm it is writable",
        ),
        StepSpec(
            id="repo.init-or-clone",
            title="Create the git repository",
            why="A brand-new project gets 'git init -b main'; when a clone URL was answered the "
            "wizard clones it instead. A pending repo-local identity from the earlier step is "
            "applied here, right after the repository exists.",
            phase=Phase.P3_REPO,
            automation=Automation.ASSISTED,
            preconditions=("repo.target-path",),
            detect=_detect_init_or_clone,
            act=_act_init_or_clone,
            verify=_verify_init_or_clone,
            change_summary=lambda ctx: (
                "git clone into TARGET" if ctx.shared.get(SHARED_CLONE_URL) else "git init -b main in TARGET"
            ),
        ),
        StepSpec(
            id="deploy.payload-copy",
            title="Copy the AEGIS payload",
            why="Copies the versioned AEGIS template into TARGET byte-for-byte and writes the "
            "install manifest that makes later analyze/doctor/upgrade possible. New-project mode "
            "never overwrites an existing file - it stops instead.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.ASSISTED,
            preconditions=("repo.init-or-clone",),
            detect=_detect_payload_copy,
            act=_act_payload_copy,
            verify=_verify_payload_copy,
            on_fail=_on_fail_payload_copy,
            change_summary=lambda ctx: "copy the payload into TARGET and write .agentic/install-manifest.json",
        ),
        StepSpec(
            id="deploy.workflow-toml",
            title="Configure the workflow (workflow.toml)",
            why="A short interview (source folders, test folders, language, gate commands) "
            "generates .agentic/workflow.toml with the write-zone invariants guaranteed. Empty "
            "gates are allowed but recorded as loud warnings.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.ASSISTED,
            preconditions=("deploy.payload-copy",),
            detect=detect_workflow_toml,
            act=_act_workflow_toml,
            verify=verify_workflow_toml,
            on_fail=on_fail_workflow_toml,
            change_summary=lambda ctx: "interview, generate .agentic/workflow.toml, create missing roots",
        ),
        StepSpec(
            id="deploy.gates",
            title="Try the quality gates once",
            why="Runs each configured gate command once inside TARGET so you know immediately "
            "whether they work. You may explicitly accept a failing or deferred gate - the "
            "decision is recorded, never silent. Optional: declining defers every gate "
            "(recorded, not a failure) instead of stopping the run.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.AUTO,
            preconditions=("deploy.workflow-toml",),
            act=_act_gates,
            verify=_verify_gates,
            change_summary=lambda ctx: (
                "offer to run each configured gate command once in TARGET "
                "(optional; declining defers every gate instead of stopping)"
            ),
        ),
        StepSpec(
            id="verify.cli-smoke",
            title="Smoke-test the workflow wrapper",
            why="Runs the real copied wrapper (run.ps1 on Windows, run.sh elsewhere) with "
            "--help inside TARGET, proving the workflow CLI starts on this machine.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.AUTO,
            preconditions=("deploy.gates",),
            act=_act_cli_smoke,
            verify=_verify_cli_smoke,
            on_fail=_on_fail_cli_smoke,
            change_summary=lambda ctx: "run the wrapper --help in TARGET (no changes)",
        ),
        StepSpec(
            id="verify.workflow-smoke",
            title="Smoke-test the workflow status",
            why="Runs the wrapper's 'status' inside TARGET (and 'gates run' when gates are "
            "configured and passed). On a fresh install the CLI answers 'RUN-POINTER-MISSING' "
            "- that coherent response is the expected healthy outcome here.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.AUTO,
            preconditions=("verify.cli-smoke",),
            act=_act_workflow_smoke,
            verify=_verify_workflow_smoke,
            on_fail=_on_fail_workflow_smoke,
            change_summary=lambda ctx: "run the wrapper status (and gates run when configured) in TARGET",
        ),
        StepSpec(
            id="verify.hooks-present",
            title="Verify hooks and agent adapters",
            why="Confirms every workflow hook file and agent adapter folder shipped by the "
            "payload is present in TARGET, so agent tools find their configuration. A hook that "
            "did not copy is a guard that never runs, and nothing else would report it.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.AUTO,
            preconditions=("verify.workflow-smoke",),
            detect=_detect_hooks_present,
            verify=_verify_hooks_present,
            change_summary=lambda ctx: "check hook files and adapter folders exist (no changes)",
        ),
        StepSpec(
            id="repo.initial-commit",
            title="Commit the installed workflow",
            why="Records the whole installed payload and generated configuration as the "
            "repository's bootstrap commit, so the project starts from a clean, versioned state.",
            phase=Phase.P4_DEPLOY,
            automation=Automation.ASSISTED,
            preconditions=("verify.hooks-present",),
            detect=_detect_initial_commit,
            act=_act_initial_commit,
            verify=_verify_initial_commit,
            on_fail=_on_fail_initial_commit,
            change_summary=lambda ctx: f'git add -A && git commit -m "{INITIAL_COMMIT_MESSAGE}"',
        ),
        StepSpec(
            id="handoff.summary",
            title="Summary and next steps",
            why="Prints and journals what was installed, where, the first operator prompt from "
            "the shipped cheat sheet, and how to check the install later. Reporting only - "
            "nothing changes.",
            phase=Phase.P5_HANDOFF,
            automation=Automation.AUTO,
            preconditions=("repo.initial-commit",),
            act=_act_handoff_summary,
            verify=lambda ctx: True,
            change_summary=lambda ctx: "print and journal the handoff summary (no changes)",
        ),
    ]
    return steps


# @brief The ordered Wizard N step instances, built once so the shared subsets
#        below are the exact objects Wizard E reuses (object identity, not a
#        re-created lookalike).
_NEW_STEPS: tuple[StepSpec, ...] = tuple(_build_new_steps())

# @brief Wizard N step lookup by id, for slicing the shared subsets.
_NEW_STEP_BY_ID: dict[str, StepSpec] = {step.id: step for step in _NEW_STEPS}

# @brief SHARED with Wizard E: the P0-P2 prefix StepSpec objects, unchanged.
COMMON_PREFIX_STEPS: tuple[StepSpec, ...] = tuple(
    _NEW_STEP_BY_ID[step_id] for step_id in _COMMON_PREFIX_IDS
)

# @brief SHARED with Wizard E: the deploy.gates StepSpec object, unchanged.
GATES_STEP: StepSpec = _NEW_STEP_BY_ID["deploy.gates"]

# @brief SHARED with Wizard E: the three smoke-verify StepSpec objects, unchanged.
VERIFY_STEPS: tuple[StepSpec, ...] = tuple(_NEW_STEP_BY_ID[step_id] for step_id in _VERIFY_IDS)


def build_new_catalog() -> Catalog:
    """
    @brief      Build the Wizard N catalog: every plan §8.1 step, in order, with
                a linear precondition chain realizing the P0→P5 phase order.
    @details    The steps come from :func:`_build_new_steps`; Wizard E reuses the
                shared prefix/verify/gates objects sliced from that same list.
    @return     The validated :class:`Catalog`.
    @exception  waegis.engine.CatalogError If the catalog were ever inconsistent
                (duplicate ids, unknown preconditions, cycles).
    """
    return Catalog(list(_NEW_STEPS))


# COMMAND SUPPORT


def _non_interactive_required_specs(answers: Mapping[str, Any]) -> list[FieldSpec]:
    """
    @brief      The FieldSpecs a ``--non-interactive`` run must answer.
    @details    The six workflow specs with their interactive defaults stripped
                (a machine-driven run must pin the configuration explicitly —
                silently applying interactive defaults would hide
                misconfiguration), plus the two ``other``-language specs when
                that language was chosen.
    @param[in]  answers Loaded answers mapping (drives the ``other`` branch).
    @return     The required spec list.
    @exception  None
    """
    required = [replace(spec, default=None) for spec in WORKFLOW_FIELD_SPECS]
    if str(answers.get("language", "")).strip().lower() == "other":
        required.extend(OTHER_LANGUAGE_FIELD_SPECS)
    return required


# EXPORTED FUNCTIONS / PUBLIC API


@dataclass(frozen=True)
class NewContext:
    """@brief Resolved public boundary for the new command phases."""
    target_path: Path
    options: CommandOptions
    transport: Any | None
    registry_reader: Any | None
    json_messages: list[str]


@dataclass(frozen=True)
class NewResolved:
    """@brief Validated new inputs before engine planning."""
    context: NewContext
    answers: dict[str, Any]
    payload_root: Path
    catalog: Catalog
    fingerprints: Mapping[str, str]
    state_home: Path
    resume: Any


@dataclass(frozen=True)
class NewPlan:
    """@brief New-command plan and engine dependencies."""
    resolved: NewResolved
    runner: CommandRunner
    asker: Any
    approval_asker: Any
    sink: ConsoleRunSink | JsonRunSink
    engine_context: EngineContext


@dataclass(frozen=True)
class NewOutcome:
    """@brief Completed engine run awaiting command-level reporting."""
    plan: NewPlan
    summary: Any


def _validate_new(context: NewContext) -> int | NewResolved:
    """@brief Validate and resolve every read-only new-command input."""
    options = context.options
    early_exit = wizard_recovery_preamble(
        context.target_path,
        command="new",
        stream=options.stream,
        as_json=options.as_json,
        dry_run=options.dry_run,
        non_interactive=options.non_interactive,
        yes=options.yes,
        stdin=options.stdin,
        json_messages=context.json_messages,
    )
    if early_exit is not None:
        return early_exit
    loaded = load_wizard_answers(
        options.answers_path, command="new", stream=options.stream, as_json=options.as_json
    )
    if isinstance(loaded, int):
        return loaded
    answers: dict[str, Any] = loaded
    warn_unknown_wizard_keys(
        answers, NEW_FIELD_SPECS, command="new", stream=options.stream,
        as_json=options.as_json, json_messages=context.json_messages,
    )
    if "clone_url" in answers:
        try:
            answers["clone_url"] = gitops.validate_clone_url(answers["clone_url"], allow_empty=True)
        except ValueError as exc:
            return wizard_fail(
                options.stream, "new", as_json=options.as_json, status="failed",
                exit_code=EXIT_VALIDATION, message=f"invalid clone_url: {exc}",
            )
    try:
        payload_root, inventory, _payload_version = locate_validated_payload(options.payload)
    except PAYLOAD_VALIDATION_ERRORS as exc:
        return wizard_fail(
            options.stream, "new", as_json=options.as_json, status="failed",
            exit_code=EXIT_VALIDATION, message=str(exc),
        )
    catalog = build_new_catalog()
    fingerprints, state_home, resume, answers = wizard_resume_setup(
        command="new", catalog=catalog, target_path=context.target_path,
        answers=answers, payload_digest=inventory.digest, home=options.home,
        dry_run=options.dry_run, field_specs=NEW_FIELD_SPECS,
    )
    return NewResolved(
        context, answers, payload_root, catalog, fingerprints, state_home, resume
    )


def _plan_new(resolved: NewResolved) -> int | NewPlan:
    """@brief Build the new-command engine plan without mutating the target."""
    context = resolved.context
    answers = resolved.answers
    options = context.options
    if options.non_interactive:
        try:
            require_non_interactive_answers(_non_interactive_required_specs(answers), answers)
        except MissingAnswersError as exc:
            return wizard_fail(
                options.stream, "new", as_json=options.as_json, status="needs-input",
                exit_code=EXIT_NEEDS_INPUT,
                message="--non-interactive requires a complete answer set; missing: " + ", ".join(exc.keys),
            )
        except PromptsError as exc:
            return wizard_fail(
                options.stream, "new", as_json=options.as_json, status="failed",
                exit_code=EXIT_VALIDATION, message=f"invalid answer: {exc}",
            )
    asker, approval_asker = select_wizard_askers(
        answers, non_interactive=options.non_interactive,
        stdin=options.stdin, stream=options.stream,
    )
    clone_url = str(answers.get("clone_url") or "")
    runner = options.runner or SubprocessCommandRunner()
    transport = context.transport or (SocketTransport() if clone_url else None)
    registry_reader = context.registry_reader
    if registry_reader is None and os.name == "nt":
        registry_reader = WinInetRegistryReader()
    shared: dict[str, Any] = {
        SHARED_TARGET: context.target_path,
        SHARED_PAYLOAD_OVERRIDE: resolved.payload_root,
        SHARED_RUNNER: runner, SHARED_TRANSPORT: transport,
        SHARED_REGISTRY_READER: registry_reader, SHARED_ANSWERS: answers,
        SHARED_CLONE_URL: clone_url, SHARED_HOME: options.home,
    }
    sink: ConsoleRunSink | JsonRunSink = (
        JsonRunSink() if options.as_json else ConsoleRunSink(options.stream)
    )
    engine_context = EngineContext(mode="new", asker=asker, events=sink, shared=shared)
    return NewPlan(
        resolved, runner, asker, approval_asker, sink, engine_context,
    )


def _consent_new(plan: NewPlan) -> NewPlan:
    """@brief Preserve the engine-owned approval seam for the new plan."""
    options = plan.resolved.context.options
    if not options.dry_run and plan.resolved.resume is not None and not options.as_json:
        options.stream.write(
            f"resuming compatible incomplete run {plan.resolved.resume.run_id}; "
            "green steps will be re-detected\n"
        )
    return plan


def _apply_new(plan: NewPlan) -> NewOutcome:
    """@brief Run the new plan through the engine's consent and apply phases."""
    resolved = plan.resolved
    options = resolved.context.options
    summary = engine_run(
        resolved.catalog, plan.engine_context, dry_run=options.dry_run,
        resume=resolved.resume, yes=options.yes,
        approval_asker=plan.approval_asker,
        journal_factory=None if options.dry_run else wizard_journal_factory(
            command="new", target_path=resolved.context.target_path,
            home=options.home, fingerprints=resolved.fingerprints,
            answers=resolved.answers,
        ),
        additional_mutations=repowise_additional_mutations(resolved.answers),
    )
    return NewOutcome(plan, summary)


def _report_new(outcome: NewOutcome) -> int:
    """@brief Emit the byte-compatible new-command report and exit code."""
    plan = outcome.plan
    resolved = plan.resolved
    options = resolved.context.options
    return wizard_postrun_and_emit(
        outcome.summary, command="new", target_path=resolved.context.target_path,
        answers=resolved.answers, non_interactive=options.non_interactive,
        dry_run=options.dry_run, yes=options.yes, as_json=options.as_json,
        stream=options.stream, sink=plan.sink,
        json_messages=resolved.context.json_messages, repowise_asker=plan.asker,
        runner=plan.runner, state_home=resolved.state_home,
        commit_step_id="repo.initial-commit", handoff_step_id="handoff.summary",
    )


def _run_new_phases(
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
    context = NewContext(
        Path(target).resolve(), normalized, transport, registry_reader, []
    )
    resolved = _validate_new(context)
    if isinstance(resolved, int):
        return resolved
    plan = _plan_new(resolved)
    if isinstance(plan, int):
        return plan
    return _report_new(_apply_new(_consent_new(plan)))


def run_new(
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
    @brief      Run the new-project wizard through its five lifecycle phases.
    @details    Preserves the public CLI/test injection seam while packaging
                recurring arguments in :class:`CommandOptions`.
    @return     Standardized command exit code 0/1/2/3.
    """
    return _run_new_phases(
        target,
        options=CommandOptions(
            stream, stdin, runner, home, yes, dry_run, non_interactive,
            as_json, answers_path, payload,
        ),
        transport=transport,
        registry_reader=registry_reader,
    )


# END OF FILE
