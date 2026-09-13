#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_structure.py
@brief P5 structural guards: the philosophy is enforced, size is not.
@details Anti-regrowth tests. Deliberately no size policing - there is
         no line-count test, by product decision. Guarded invariants:
         no hook/waiver/transaction machinery ever grows back into the
         payload, the CLI stays standard-library-only, `check` stays
         advisory without --strict, and every payload file carries the
         license header. The guard predicates are plain functions over
         source text, self-tested here against deliberately bad input -
         the "verify by mutation" of the P5 acceptance, without touching
         the real file.
"""

# IMPORTS

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

import pytest
from test_check import make_repo, write

# CONSTANTS

TREE = Path(__file__).resolve().parents[1]
PAYLOAD = TREE / "template" / ".agentic"
AEGIS_PY = PAYLOAD / "aegis.py"

#: identifiers of the heavy-AEGIS machinery that must never grow back.
FORBIDDEN_IDENTIFIERS = (
    "hook",
    "waiver",
    "evidence_form",
    "transaction",
    "journal_store",
    "permissionDecision",
)

#: file names that would mean adapter/hook wiring returned to the payload.
FORBIDDEN_FILE_NAMES = (
    "hooks.json",
    "settings.json",
    "run_hook.mjs",
    "workflow.toml",
    "components.toml",
)

#: every text file the payload ships must carry the license marker.
LICENSE_MARK = "PolyForm Noncommercial License 1.0.0"

#: the complete expected payload inventory (relative to .agentic/).
EXPECTED_FILES = (
    "AGENTS.md",
    "CLI.md",
    "LICENSE.txt",
    "aegis.py",
    "steps/1_frame.md",
    "steps/2_specify.md",
    "steps/3_design.md",
    "steps/4_build.md",
    "steps/5_validate.md",
    "steps/6_deliver.md",
    "steps/adopt.md",
    "templates/component.md",
    "templates/environment.md",
    "templates/project.md",
    "templates/requirement.toml",
    "templates/spec.md",
    "templates/task.md",
)

IGNORED_DIR_PARTS = {"__pycache__", ".pytest_cache"}


# GUARD PREDICATES (plain functions so they can be self-tested on bad input)


def forbidden_identifier_hits(source: str) -> list[str]:
    """@brief The forbidden identifiers present in `source`, case-insensitive."""
    return [word for word in FORBIDDEN_IDENTIFIERS
            if re.search(word, source, re.IGNORECASE)]


def non_stdlib_imports(source: str) -> list[str]:
    """@brief Top-level module names imported by `source` outside the stdlib."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return sorted(modules - set(sys.stdlib_module_names))


def payload_files() -> list[Path]:
    """@brief Every real payload file, ignoring caches."""
    return [
        path for path in sorted(PAYLOAD.rglob("*"))
        if path.is_file() and not (IGNORED_DIR_PARTS & set(path.parts))
    ]


# TESTS - the machinery must not grow back


def test_aegis_py_contains_no_forbidden_identifier():
    assert forbidden_identifier_hits(AEGIS_PY.read_text(encoding="utf-8")) == []


def test_the_forbidden_identifier_guard_actually_fires():
    bad = "def install_hook():\n    return Transaction()\n"
    assert forbidden_identifier_hits(bad) == ["hook", "transaction"]


def test_payload_ships_no_adapter_or_policy_files():
    names = {path.name for path in payload_files()}
    assert not names.intersection(FORBIDDEN_FILE_NAMES)
    assert not [p for p in payload_files() if p.suffix in (".mjs", ".json")]


def test_payload_inventory_is_exactly_the_documented_set():
    found = {path.relative_to(PAYLOAD).as_posix() for path in payload_files()}
    assert found == set(EXPECTED_FILES)


def test_payload_ships_a_complete_cli_reference(tmp_path):
    """REQ-UX-62a24243: every parser command has its own CLI reference section."""
    _agentic, aegis = make_repo(tmp_path)
    text = (PAYLOAD / "CLI.md").read_text(encoding="utf-8")
    commands = next(action.choices for action in aegis.build_parser()._actions
                    if isinstance(action, argparse._SubParsersAction))
    sections = set(re.findall(r"^## `([^`]+)`", text, re.MULTILINE))
    assert set(commands) <= sections
    assert "When to use" in text
    assert "Examples" in text
    assert "--version" in text


def test_component_catalogue_command_guides_every_useful_stage(tmp_path):
    """REQ-FUNC-8ec7a0c7: one flat command exposes title-and-path discovery."""
    _agentic, aegis = make_repo(tmp_path)
    commands = next(action.choices for action in aegis.build_parser()._actions
                    if isinstance(action, argparse._SubParsersAction))
    assert "components" in commands

    agents = (PAYLOAD / "AGENTS.md").read_text(encoding="utf-8")
    cli = (PAYLOAD / "CLI.md").read_text(encoding="utf-8")
    assert "python .agentic/aegis.py components" in agents
    assert "## `components`" in cli

    for step in ("1_frame.md", "2_specify.md", "3_design.md", "adopt.md"):
        text = (PAYLOAD / "steps" / step).read_text(encoding="utf-8")
        assert "aegis.py components" in text, step
    for step in ("4_build.md", "5_validate.md"):
        text = (PAYLOAD / "steps" / step).read_text(encoding="utf-8")
        assert "aegis.py components" in text and "additional" in text, step
    deliver = (PAYLOAD / "steps" / "6_deliver.md").read_text(encoding="utf-8")
    assert "aegis.py components" not in deliver


@pytest.mark.parametrize("name", ["aegis.py", "CLI.md"])
def test_installed_cli_matches_template(name):
    """REQ-TEST-e38913a7: the installed CLI matches the managed payload."""
    installed = TREE.parents[1] / ".agentic" / name
    assert installed.read_bytes() == (PAYLOAD / name).read_bytes()


@pytest.mark.parametrize("command", ["anchor", "evolution", "summary", "brief", "trace"])
def test_cli_reference_guard_detects_a_missing_command_section(tmp_path, monkeypatch,
                                                             command):
    """REQ-UX-62a24243: a summary mention cannot replace a command's own guide."""
    text = (PAYLOAD / "CLI.md").read_text(encoding="utf-8")
    incomplete = re.sub(rf"^## `{command}`\n.*?(?=^## |\Z)", "", text,
                        flags=re.MULTILINE | re.DOTALL)
    assert incomplete != text
    reference = tmp_path / "reference"
    write(reference / "CLI.md", incomplete)
    monkeypatch.setitem(globals(), "PAYLOAD", reference)
    with pytest.raises(AssertionError):
        test_payload_ships_a_complete_cli_reference(tmp_path / "repo")


def test_build_stage_records_reproducible_red_evidence_without_git_witness():
    """REQ-TEST-a67ee43e: red evidence is precise prose, not Git ceremony."""
    text = (PAYLOAD / "steps" / "4_build.md").read_text(encoding="utf-8")
    assert "exact test selector or command" in text
    assert "non-zero exit code" in text
    assert "expected missing-behavior failure reason" in text
    assert "manual observation" in text
    assert "test-only commit" not in text
    assert "red-witness" not in text


def test_deviation_notices_are_stated_when_recorded_not_only_at_delivery():
    """REQ-UX-ccb4ca06: material departures are spoken without tool noise."""
    # normalized: these are wrapped prose, and a rewrap must not fail the guard
    def flat(*parts: str) -> str:
        return " ".join((PAYLOAD.joinpath(*parts)
                         .read_text(encoding="utf-8")).split())

    agents = flat("AGENTS.md")
    build = flat("steps", "4_build.md")
    validate = flat("steps", "5_validate.md")
    deliver = flat("steps", "6_deliver.md")

    # the notice sits beside the two interaction modes, being neither of them
    assert "Deviation notices" in agents
    assert "DEVIATION <stage>:" in agents
    assert "never pauses the work" in agents
    assert "Autopilot does not suppress" in agents
    assert "materially differs" in agents
    assert "recoverable internal tool-use errors" in agents
    assert "expected failing test" in agents
    assert "when a command exits non-zero" not in agents

    # every stage that records an anomaly states it at the same moment
    assert "state it as a deviation notice" in build
    assert "state it as a deviation notice" in validate
    assert "materially limits" in build
    assert "operational detail, not a deviation" in validate

    # delivery still presents the aggregate; notices never stand in for it
    assert "notices supplement this presentation" in deliver


def test_stage_report_instructions_define_stage_choice_boundaries():
    """REQ-UX-84868466: checkpoint reports end with explicit next choices."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    scaffold = (PAYLOAD / "templates" / "task.md").read_text(encoding="utf-8")
    assert "## Stage reporting" in agents
    assert "before any detailed explanation" in agents
    assert "stop after every completed stage" in agents
    assert "Stage-boundary choices" in agents
    assert "DEVIATION <stage>:" in agents
    assert "## Stage report" in scaffold
    for key in ("stage", "result", "current", "changed", "evidence", "issues",
                "next", "needs_user"):
        assert re.search(rf"^{key}:\s*$", scaffold, re.MULTILINE)
    for step in (PAYLOAD / "steps").glob("*.md"):
        text = " ".join(step.read_text(encoding="utf-8").split())
        assert "**Reporting and resume:**" in text, step.name
        assert "summary TASK-<id>" in text, step.name
        assert "completed stage" in agents and "current" in agents
        assert "pause" in text and "Stage reporting" in text, step.name


def test_resume_guidance_is_local_and_preserves_required_evidence():
    """REQ-UX-94a33d75: small-context resume is explicit without skipping proof."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "summary TASK-<id>" in agents
    assert "relevant log entries" in agents
    assert "unresolved issues" in agents
    assert "Full journal reads required by validate and deliver still apply" in agents
    prompts = agents.split("For a small local model", 1)[1]
    assert prompts.count("Stop after this stage.") == 6
    for step in (PAYLOAD / "steps").glob("*.md"):
        text = " ".join(step.read_text(encoding="utf-8").split())
        assert "Resume a task" in text, step.name
        assert "Read required durable evidence" in text, step.name
        assert "context requires review" in text, step.name


def test_workflow_defines_append_only_rulings_and_supersession():
    """REQ-FUNC-7ea14fe4: durable decisions retain history and provenance."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "## Rulings and handoffs" in agents
    assert "Rulings are append-only" in agents
    assert "Never edit or delete" in agents
    assert "supersedes" in agents and "RULING-" in agents


def test_workflow_defines_replaceable_handoff_and_freshness():
    """REQ-FUNC-7ea14fe4: one current resume snapshot is stage-bound."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "Handoff is one replaceable" in agents
    assert "current must match" in agents
    for trigger in ("stage transition", "pause", "blocker", "session end"):
        assert trigger in agents


def test_every_stage_refreshes_handoff_on_pause_or_transition():
    """REQ-FUNC-7ea14fe4: every stage boundary leaves a usable handoff."""
    for step in (PAYLOAD / "steps").glob("*.md"):
        text = " ".join(step.read_text(encoding="utf-8").split())
        assert "minimal Handoff" in text, step.name
        assert "transition" in text and "pause" in text, step.name


def test_rulings_cannot_expand_user_or_git_authority():
    """REQ-FUNC-7ea14fe4: recorded decisions cannot grant new authority."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "cannot grant authority" in agents
    assert "newer user instructions" in agents
    assert "repository rules" in agents and "Git authority" in agents


def test_small_model_prompts_start_with_brief_then_required_files():
    """REQ-UX-94a33d75: limited-context workers start from durable resume state."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    prompts = agents.split("For a small local model", 1)[1]
    assert "brief TASK-<id>" in prompts
    assert "current step file" in prompts and "must_read" in prompts
    assert prompts.index("brief TASK-<id>") < prompts.index("current step file")


def test_validate_defines_two_independent_review_questions():
    """REQ-FUNC-9514e017: validation asks both explicit questions separately."""
    text = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "Specification compliance" in text
    assert "Implementation quality" in text
    assert "independent verdicts" in text


def test_validate_repeats_both_verdicts_after_any_candidate_change():
    """REQ-FUNC-9514e017: approvals never survive a changed candidate."""
    text = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "Any candidate change invalidates both verdicts" in text
    assert "perform both reviews again" in text


def test_fix_loop_uses_one_plus_max_fix_cycles_total_rounds():
    """REQ-FUNC-cbff6478: the initial review plus fixes has a finite bound."""
    text = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "1 + max_fix_cycles" in text
    assert "two fix cycles means three total review rounds" in text


def test_fix_loop_routes_findings_without_expanding_scope():
    """REQ-FUNC-cbff6478: autonomous fixes consume only recorded findings."""
    build = " ".join((PAYLOAD / "steps" / "4_build.md").read_text("utf-8").split())
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "Fix only recorded review findings" in build
    assert "Do not expand scope" in build
    assert "route to the appropriate existing stage" in validate


def test_fix_loop_exhaustion_blocks_and_needs_user():
    """REQ-FUNC-cbff6478: a failed last round cannot enter delivery."""
    text = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "result: blocked" in text and "needs_user: yes" in text
    assert "do not advance to deliver" in text


def test_scope_ambiguity_uses_existing_human_checkpoint():
    """REQ-FUNC-cbff6478: the loop cannot guess a changed contract."""
    text = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "specification ambiguity or scope change" in text
    assert "existing human checkpoint" in text


def test_disabled_review_keeps_existing_validation_and_has_no_fix_loop():
    """REQ-FUNC-9514e017: the opt-in switch controls no mandatory proof."""
    text = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "When review is disabled" in text
    assert "skip only explicit verdicts and their fix loop" in text
    for proof in ("semantic review", "full suite", "strict check", "evidence"):
        assert proof in text


def test_deliver_requires_current_approved_verdicts_only_when_enabled():
    """REQ-FUNC-9514e017: delivery respects policy and current bound evidence."""
    text = " ".join((PAYLOAD / "steps" / "6_deliver.md").read_text("utf-8").split())
    assert "When explicit review is enabled" in text
    assert "both current bound verdicts are `approved`" in text
    assert "When explicit review is disabled" in text
    assert "existing validation evidence" in text


def test_large_work_may_split_only_into_optional_one_level_children():
    """REQ-FUNC-3bc8597c: decomposition is explicit, optional, and shallow."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text("utf-8").split())
    frame = " ".join((PAYLOAD / "steps" / "1_frame.md").read_text("utf-8").split())
    design = " ".join((PAYLOAD / "steps" / "3_design.md").read_text("utf-8").split())
    assert "## Optional child tasks" in agents
    assert "opt-in" in agents and "one level" in agents
    assert "large enough for optional children" in frame
    assert "non-overlapping child scopes" in design and "requirement links" in design


def test_parent_validates_integrated_visible_child_work():
    """REQ-FUNC-3bc8597c: the parent owns proof of the combined candidate."""
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "Parent validation" in validate
    assert "integrated candidate" in validate
    assert "children visible in this checkout" in validate
    assert "independently validated" in validate


def test_resume_starts_with_brief_but_requires_current_stage_sources():
    """REQ-UX-94a33d75: compact re-entry preserves authoritative source reads."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text("utf-8").split())
    resume = agents.split("## Resume a task", 1)[1].split("## Interaction modes", 1)[0]
    assert resume.index("brief TASK-<id>") < resume.index("current step file")
    assert "must_read" in resume
    assert "Full journal reads required by validate and deliver still apply" in resume


def test_every_pause_refreshes_stage_report_and_handoff():
    """REQ-FUNC-7ea14fe4: user reporting and worker resume state move together."""
    for step in (PAYLOAD / "steps").glob("*.md"):
        text = " ".join(step.read_text("utf-8").split())
        assert "Stage reporting" in text and "pauses" in text, step.name
        assert "minimal Handoff" in text, step.name


def test_six_stage_workflow_stops_at_each_stage_when_autopilot_is_off():
    """REQ-FUNC-d60b322b: stage order is unchanged while control is explicit."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text("utf-8").split())
    assert all(f"| {number} | {stage} |" in agents for number, stage in enumerate(
        ("frame", "specify", "design", "build", "validate", "deliver"), 1))
    assert "autopilot = false" in agents
    assert "Missing table or key means `false`" in agents
    assert "pre-publication approval" in agents


def test_pointer_digest_is_sufficient_for_offline_resume():
    """REQ-PLAT-e675406e: generated pointers carry the survival contract."""
    source = AEGIS_PY.read_text(encoding="utf-8")
    digest = source.split('POINTER_DIGEST = """\\\n', 1)[1].split('"""', 1)[0]
    for phrase in ("brief TASK-<id>", "one-level child", "Rulings are append-only",
                   "Handoff is replaceable", "optional explicit review",
                   "bounded fix", "cannot grant authority",
                   "autopilot = false", "stops after every stage",
                   "publication approval"):
        assert phrase in digest


def test_six_stage_workflow_separates_validation_from_publication():
    """REQ-FUNC-24ea4f73: proof may mutate; publication may not."""
    agents = (PAYLOAD / "AGENTS.md").read_text(encoding="utf-8")
    build = (PAYLOAD / "steps" / "4_build.md").read_text(encoding="utf-8")
    validate = (PAYLOAD / "steps" / "5_validate.md").read_text(encoding="utf-8")
    deliver = (PAYLOAD / "steps" / "6_deliver.md").read_text(encoding="utf-8")

    assert "| 5 | validate |" in agents
    assert "| 6 | deliver |" in agents
    assert "set `stage: validate`" in build
    assert "Prove the final candidate only after" in validate
    assert "does not edit the validated candidate" in deliver
    assert "return to `validate`" in deliver


def test_deliver_has_no_default_write_zone(tmp_path):
    """REQ-FUNC-24ea4f73: merge-base diffs cannot enforce stage-local edits."""
    _agentic, aegis = make_repo(tmp_path)
    assert "validate" not in aegis.DEFAULT_ZONES
    assert "deliver" not in aegis.DEFAULT_ZONES


def test_deliver_folds_close_out_into_a_local_only_delivery():
    """REQ-FUNC-dcb42072: a second commit only where publication can fail."""
    deliver = " ".join(
        (PAYLOAD / "steps" / "6_deliver.md").read_text(encoding="utf-8").split())
    assert "nothing can fail after it" in deliver
    assert "let the same commit carry them" in deliver
    # the separate close-out survives wherever the outcome can still fail
    assert "can still fail after the delivery commit" in deliver
    assert "close-out commit pushed to the same PR" in deliver


def test_check_help_makes_no_unconditional_zero_exit_promise(tmp_path, capsys):
    """REQ-UX-e9952f0f: a usage error has always exited non-zero."""
    _agentic, aegis = make_repo(tmp_path)
    source = AEGIS_PY.read_text(encoding="utf-8")
    assert "always exits 0" not in source
    assert "exits 0 always" not in source

    aegis.main(["init"])
    capsys.readouterr()
    with pytest.raises(SystemExit):
        aegis.main(["check", "--help"])
    assert "always exits 0" not in capsys.readouterr().out

    # the exit the help must not deny
    assert aegis.main(["check", "--task", "TASK-nope"]) == 1


# TESTS - the payload is self-contained prose


def test_payload_never_references_external_documents():
    """The payload must stand alone: no plan docs, no sibling products."""
    banned = re.compile(r"plan doc|doc[ -]0\d|00_Planning", re.IGNORECASE)
    for path in payload_files():
        if path.suffix in (".md", ".py", ".toml"):
            hit = banned.search(path.read_text(encoding="utf-8"))
            assert hit is None, f"{path.name} references '{hit.group(0)}'"


def test_frame_captures_evidence_intent_and_ambiguity_before_mechanics():
    """REQ-UX-81840102: framing preserves understanding before administration."""
    agents = (PAYLOAD / "AGENTS.md").read_text(encoding="utf-8")
    frame = (PAYLOAD / "steps" / "1_frame.md").read_text(encoding="utf-8")
    task = (PAYLOAD / "templates" / "task.md").read_text(encoding="utf-8")

    for phrase in ("## Semantic analysis protocol", "STATED", "OBSERVED",
                   "INFERRED", "UNKNOWN", "decision-blocking"):
        assert phrase in agents
    for phrase in ("## Frame card", "Problem:", "Desired outcome:",
                   "Primary scenario:", "Success signals:", "Counterexamples:",
                   "Assumptions:", "Unknowns:", "yes | no | evidence"):
        assert phrase in frame
    assert frame.index("semantic analysis protocol") < frame.index("Establish the branch")
    assert "scope acceptance, not implementation" in frame
    assert "## Frame" in task
    assert "Evidence:" in task


def test_specify_proves_behavior_coverage_and_verification_quality():
    """REQ-FUNC-aa60c372: specification demonstrates semantic completeness."""
    specify = (PAYLOAD / "steps" / "2_specify.md").read_text(encoding="utf-8")
    requirement = (PAYLOAD / "templates" / "requirement.toml").read_text(
        encoding="utf-8")
    spec = (PAYLOAD / "templates" / "spec.md").read_text(encoding="utf-8")
    task = (PAYLOAD / "templates" / "task.md").read_text(encoding="utf-8")
    specify = " ".join(specify.split())

    for phrase in ("Behavior inventory", "Frame outcome", "Atomic behavior",
                   "broad Frame outcome", "Boundary or failure",
                   "vary, fail, change, or be verified independently",
                   "Setup", "Observable oracle", "semantic conflict",
                   "state machine", "migration"):
        assert phrase in specify
    assert "every atomic behavior maps to exactly one requirement" in specify
    assert "independently verifiable responses" in requirement
    assert "## Assumptions and open decisions" in spec
    assert "## Requirement coverage" in task


def test_design_scales_depth_and_keeps_proposals_distinct_from_current_architecture():
    """REQ-FUNC-3e0263e7: design depth follows risk and proposals stay explicit."""
    design = (PAYLOAD / "steps" / "3_design.md").read_text(encoding="utf-8")
    component = (PAYLOAD / "templates" / "component.md").read_text(
        encoding="utf-8")
    validate = (PAYLOAD / "steps" / "5_validate.md").read_text(encoding="utf-8")
    design = " ".join(design.split())
    component = " ".join(component.split())

    for phrase in ("30 lines is the default", "Requirements coverage",
                   "sufficiently constrained implementation path",
                   "Component responsibilities", "Interfaces and contracts",
                   "Data ownership and state transitions", "Failure recovery",
                   "Security and trust boundaries", "Compatibility and migration",
                   "Observability", "Open decisions"):
        assert phrase in design
    assert "Proposed architecture" in design
    assert "decision-free" not in design
    assert "do not replace the current diagram" in design
    assert "Keep this drawn as the code is now" in component
    for phrase in ("task's Design", "built code", "current-state",
                   "historical design evidence", "never delete it"):
        assert phrase in validate


# TESTS - Python 3.11 compatibility


#: an f-string whose braces contain a double-quoted string needs the
#: flexible f-string grammar of Python 3.12 (PEP 701) - the promise is 3.11.
NESTED_FSTRING_RE = re.compile(r'f"[^"\n]*\{[^{}\n]*"')


def test_no_nested_quote_fstrings_python_311_promise():
    hits = [line for line in AEGIS_PY.read_text(encoding="utf-8").splitlines()
            if NESTED_FSTRING_RE.search(line)]
    assert hits == [], f"3.12-only f-string syntax: {hits[0]}"


def test_the_nested_fstring_guard_actually_fires():
    assert NESTED_FSTRING_RE.search('x = f"TASK-{new_id(taken("a", "b"))}"')


# TESTS - the CLI stays standard-library-only


def test_aegis_py_imports_only_the_standard_library():
    assert non_stdlib_imports(AEGIS_PY.read_text(encoding="utf-8")) == []


def test_the_stdlib_import_guard_actually_fires():
    bad = "import requests\nfrom yaml import safe_load\nimport os\n"
    assert non_stdlib_imports(bad) == ["requests", "yaml"]


# TESTS - check stays advisory without --strict


def test_check_exits_zero_without_strict_even_on_errors(tmp_path, monkeypatch,
                                                        capsys):
    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write(agentic / "requirements" / "functional" / "REQ-FUNC-1111.toml",
          "not [ toml\n")
    capsys.readouterr()
    assert aegis.main(["check"]) == 0
    out = capsys.readouterr().out
    assert "result: ERROR" in out  # the failure is visible, never blocking


def test_json_stdout_stays_one_parseable_document(tmp_path, monkeypatch,
                                                  capsys):
    """Every --json invocation must print exactly one JSON document."""
    import json as _json

    agentic, aegis = make_repo(tmp_path)
    aegis.main(["init"])
    monkeypatch.setattr(aegis, "run_git", lambda *_a: None)
    write(agentic / "requirements" / "functional" / "REQ-FUNC-11111111.toml",
          "not [ toml\n")
    write(agentic / "tasks" / "TASK-aaaa.md",
          "# TASK-aaaa — t\n\nstage: build\ntype: fix\npath: quick\n"
          "requirements:\nbranch: b\nopened: 2026-08-02\n\n## Log\n\n- x\n")

    for argv in (["check", "--json"],
                 ["check", "--json", "--run"],
                 ["check", "--json", "--strict"],
                 ["check", "--json", "--full", "--task", "TASK-aaaa"],
                 ["status", "--json"],
                 ["status", "--json", "--all"],
                 ["status", "TASK-aaaa", "--json"]):
        capsys.readouterr()
        aegis.main(argv)
        document = _json.loads(capsys.readouterr().out)  # raises if impure
        assert document["schema"] == aegis.JSON_SCHEMA


def test_strict_is_an_explicit_opt_in_flag_not_a_default():
    source = AEGIS_PY.read_text(encoding="utf-8")
    match = re.search(r'add_argument\("--strict",\s*action="store_true"', source)
    assert match, "--strict must be a store_true opt-in flag"


# TESTS - license headers everywhere


def test_every_payload_file_carries_the_license_header():
    for path in payload_files():
        head = path.read_text(encoding="utf-8")[:600]
        assert LICENSE_MARK in head, f"missing license header: {path.name}"


def test_every_test_file_carries_the_license_header():
    for path in sorted(TREE.glob("tests/test_*.py")):
        head = path.read_text(encoding="utf-8")[:600]
        assert LICENSE_MARK in head, f"missing license header: {path.name}"


def test_component_pages_carry_an_architecture_diagram():
    """REQ-FUNC-500cfb8b: the page template defines where the drawing lives."""
    text = (PAYLOAD / "templates" / "component.md").read_text(encoding="utf-8")
    assert "## Architecture" in text
    assert "```mermaid" in text
    # the drawing is of this component's own logic, not of the whole system
    assert "flowchart" in text


def test_adopt_and_validate_keep_the_architecture_diagram_current():
    """REQ-FUNC-500cfb8b: adoption creates the diagram; validation reconciles it."""
    adopt = (PAYLOAD / "steps" / "adopt.md").read_text(encoding="utf-8")
    design = (PAYLOAD / "steps" / "3_design.md").read_text(encoding="utf-8")
    validate = (PAYLOAD / "steps" / "5_validate.md").read_text(encoding="utf-8")
    assert "## Architecture" in adopt
    # adoption draws what is there; design records a proposal; validation
    # reconciles the canonical knowledge page only after implementation.
    assert "architecture" in adopt.lower()
    assert "Proposed architecture" in design
    assert "do not replace the current diagram" in design
    assert "built code" in validate
    assert "current-state" in validate
    assert "historical design evidence" in validate


def test_component_knowledge_routes_implementation_work():
    """REQ-FUNC-9db20045: component pages route work to exact code and tests."""
    component = (PAYLOAD / "templates" / "component.md").read_text(
        encoding="utf-8")
    adopt = (PAYLOAD / "steps" / "adopt.md").read_text(encoding="utf-8")
    frame = (PAYLOAD / "steps" / "1_frame.md").read_text(encoding="utf-8")
    specify = (PAYLOAD / "steps" / "2_specify.md").read_text(encoding="utf-8")
    design = (PAYLOAD / "steps" / "3_design.md").read_text(encoding="utf-8")
    build = (PAYLOAD / "steps" / "4_build.md").read_text(encoding="utf-8")
    validate = (PAYLOAD / "steps" / "5_validate.md").read_text(
        encoding="utf-8")
    component_flat = " ".join(component.split())
    adopt_flat = " ".join(adopt.split())
    frame_flat = " ".join(frame.split())
    specify_flat = " ".join(specify.split())
    design_flat = " ".join(design.split())
    build_flat = " ".join(build.split())
    validate_flat = " ".join(validate.split())

    for heading in ("## Routing", "## Purpose and boundaries",
                    "## Public interface", "## Invariants",
                    "## Change map", "## Key behaviors",
                    "## Architecture", "## Files"):
        assert heading in component
    assert "exact source and tests remain authoritative" in component_flat
    assert "multiple independent edit-and-test seams" in component_flat

    assert "## Routing" in adopt_flat
    assert "exact source and tests" in adopt_flat
    assert "## Routing" in frame_flat
    assert "selection signals" in frame_flat
    assert "legacy page" in frame_flat
    assert "available sections" in frame_flat
    assert "exact source and tests" in frame_flat
    assert "## Purpose and boundaries" in specify_flat
    assert "## Invariants" in specify_flat
    assert "## Change map" in design_flat
    assert "aegis.py components" in build_flat
    for heading in ("Routing", "Purpose and boundaries", "Invariants",
                    "Change map"):
        assert heading in validate_flat
    assert "touched legacy page" in validate_flat
    assert "migrate it to the current template" in validate_flat
