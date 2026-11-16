#!/usr/bin/env python3
"""
P5 structural guards: the philosophy is enforced, size is not.

Anti-regrowth tests. Deliberately no size policing - there is
no line-count test, by product decision. Guarded invariants:
no hook/waiver/transaction machinery ever grows back into the
payload, the CLI stays standard-library-only, `check` stays
advisory without --strict, and every payload file carries the
SPDX tag. The guard predicates are plain functions over
source text, self-tested here against deliberately bad input -
the "verify by mutation" of the P5 acceptance, without touching
the real file.
"""


from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

import pytest
from test_check import make_repo, write

TREE = Path(__file__).resolve().parents[1]
PAYLOAD = TREE / "template" / ".agentic"
AEGIS_PY = PAYLOAD / "aegis.py"
INTEGRATIONS = TREE / "integrations"

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

#: every text file the payload ships carries this SPDX tag, because the payload
#: is copied into repositories whose own licensing declarations do not cover it.
LICENSE_MARK = "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0"

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
    "steps/adopt.md",
    "steps/diagrams.md",
    "steps/review.md",
    "templates/component.md",
    "templates/environment.md",
    "templates/project.md",
    "templates/requirement.toml",
    "templates/spec.md",
    "templates/task.md",
)

IGNORED_DIR_PARTS = {"__pycache__", ".pytest_cache"}


def stage_step_files() -> list[Path]:
    """
    The step files that run a stage or the adoption procedure.

    The optional diagram and review guides run inside design and
    validate and finish nothing of their own.
    """
    return [path for path in sorted((PAYLOAD / "steps").glob("*.md"))
            if path.name not in {"diagrams.md", "review.md"}]


def forbidden_identifier_hits(source: str) -> list[str]:
    """The forbidden identifiers present in `source`, case-insensitive."""
    return [word for word in FORBIDDEN_IDENTIFIERS
            if re.search(word, source, re.IGNORECASE)]


def non_stdlib_imports(source: str) -> list[str]:
    """Top-level module names imported by `source` outside the stdlib."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return sorted(modules - set(sys.stdlib_module_names))


def payload_files() -> list[Path]:
    """Every real payload file, ignoring caches."""
    return [
        path for path in sorted(PAYLOAD.rglob("*"))
        if path.is_file() and not (IGNORED_DIR_PARTS & set(path.parts))
    ]


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
    text = " ".join((PAYLOAD / "steps" / "4_build.md").read_text(encoding="utf-8").split())
    assert ('log TASK-<id> "red: <command> exit <code> - <expected missing behavior> '
            '(<REQ-ids>)"') in text
    assert "fails for the expected reason" in text
    assert "log the method, the action and the observed result" in text
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

    # the notice sits beside the two interaction modes, being neither of them
    assert "## Deviations" in agents
    assert "DEVIATION <stage>:" in agents
    assert "it never waits for a reply" in agents
    assert "autopilot never suppresses it" in agents
    assert "departs from plan" in agents
    assert ("Corrected tool errors, expected red tests and unrelated findings "
            "are not deviations") in agents
    assert "when a command exits non-zero" not in agents

    # every stage that records an anomaly states it at the same moment
    assert "limits the candidate or its verification is a deviation" in build
    assert "say it as a deviation" in validate
    # the closing checkpoint repeats them with the evidence
    assert "accepted warnings, deviations" in validate


def test_stage_report_instructions_define_stage_choice_boundaries():
    """REQ-UX-84868466: checkpoint reports end with explicit next choices."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    scaffold = (PAYLOAD / "templates" / "task.md").read_text(encoding="utf-8")
    assert "## Checkpoint or autopilot" in agents
    assert ("start your reply with that printed block in a text fence, then explain; "
            "never write the block yourself") in agents
    assert "continue, revise, go back, or stop" in agents
    assert "DEVIATION <stage>:" in agents
    assert "## State" in scaffold and "## Stage report" not in scaffold
    for key in ("status", "reported", "next", "must_read", "changed", "evidence",
                "issues"):
        assert re.search(rf"^{key}:\s*$", scaffold, re.MULTILINE)
    for step in stage_step_files():
        text = " ".join(step.read_text(encoding="utf-8").split())
        if step.name == "adopt.md":
            assert "pause TASK-<id>" in text and "advance TASK-<id>" in text
            continue
        finish = text.split("**Finish:**", 1)[1].split("**Done when:**", 1)[0]
        assert "Checkpoint:" in finish and "Autopilot:" in finish, step.name
        assert "pause TASK-<id>" in finish and "advance TASK-<id>" in finish, step.name
        assert "the choices" in finish, step.name


def resume_section() -> str:
    """The flattened `## Start or resume` section of the agent contract."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    return agents.split("## Start or resume", 1)[1].split("## The task journal", 1)[0]


def test_resume_guidance_is_local_and_preserves_required_evidence():
    """REQ-UX-94a33d75: small-context resume is explicit without skipping proof."""
    resume = resume_section()
    assert resume.index("aegis.py status") < resume.index("1_frame.md")
    assert resume.index("brief TASK-<id>") < resume.index("Read next")
    assert "git branch --show-current" in resume and "stop and say so" in resume
    assert "not the whole repository" in resume
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "The whole task journal" in validate
    assert "This step file again" in validate


def test_workflow_defines_append_only_rulings_and_supersession():
    """REQ-FUNC-7ea14fe4: durable decisions retain history and provenance."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    template = " ".join((PAYLOAD / "templates" / "task.md").read_text("utf-8").split())
    assert "Rulings are append-only" in agents
    assert "that link is what marks the old one superseded" in agents
    assert "never edit or annotate an earlier line" in agents
    assert "earlier lines are never edited" in template
    assert "--supersedes RULING-<old-id>" in template


def test_state_is_written_by_the_cli_through_named_writers():
    """REQ-FUNC-7ea14fe4: one current resume snapshot, written by commands."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "The CLI writes the rest" in agents
    for command in ("advance TASK-<id>", "pause TASK-<id>", "log TASK-<id>",
                    "ruling TASK-<id>", "verdict TASK-<id>"):
        assert command in agents, command


def test_every_stage_finishes_through_the_journal_writers():
    """REQ-FUNC-7ea14fe4: every stage boundary leaves a usable resume state."""
    for step in stage_step_files():
        text = " ".join(step.read_text(encoding="utf-8").split())
        assert "pause TASK-<id>" in text and "advance TASK-<id>" in text, step.name


def test_rulings_cannot_expand_user_or_git_authority():
    """REQ-FUNC-7ea14fe4: recorded decisions cannot grant new authority."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    assert "cannot grant authority" in agents
    assert "newer user instructions" in agents
    assert "repository rules" in agents and "Git permissions" in agents


def test_small_context_entry_starts_with_brief_then_read_next():
    """REQ-UX-94a33d75: limited-context workers start from durable resume state."""
    source = AEGIS_PY.read_text(encoding="utf-8")
    digest = " ".join(source.split('POINTER_DIGEST = """\\\n', 1)[1].split('"""', 1)[0].split())
    for text in (resume_section(), digest):
        assert text.index("brief TASK-<id>") < text.index("Read next")


def review_flat() -> str:
    """The optional explicit-review guide, whitespace collapsed."""
    return " ".join((PAYLOAD / "steps" / "review.md").read_text("utf-8").split())


def test_validate_defines_two_independent_review_questions():
    """REQ-FUNC-9514e017: validation asks both explicit questions separately."""
    text = review_flat()
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "Specification compliance" in text and "Implementation quality" in text
    assert "two independent reviewers" in text
    assert "Review: policy=enabled" in validate and "`.agentic/steps/review.md`" in validate


def test_validate_repeats_both_verdicts_after_any_candidate_change():
    """REQ-FUNC-9514e017: approvals never survive a changed candidate."""
    text = review_flat()
    assert "Any candidate edit invalidates both verdicts" in text
    assert "review both roles again" in text


def test_fix_loop_uses_one_plus_max_fix_cycles_total_rounds():
    """REQ-FUNC-cbff6478: the initial review plus fixes has a finite bound."""
    text = review_flat()
    assert "1 + max_fix_cycles" in text
    assert "two fix cycles allow three rounds" in text


def test_fix_loop_routes_findings_without_expanding_scope():
    """REQ-FUNC-cbff6478: autonomous fixes consume only recorded findings."""
    build = " ".join((PAYLOAD / "steps" / "4_build.md").read_text("utf-8").split())
    assert "fix only the recorded findings, without expanding scope" in build
    assert "advance TASK-<id> --to build" in review_flat()
    assert "fix only those findings" in review_flat()


def test_fix_loop_exhaustion_blocks_and_needs_user():
    """REQ-FUNC-cbff6478: a failed last round cannot close the task."""
    text = review_flat()
    assert "pause TASK-<id> --blocked" in text
    assert "Do not repair, prove or close from here" in text


def test_scope_ambiguity_uses_existing_human_checkpoint():
    """REQ-FUNC-cbff6478: the loop cannot guess a changed contract."""
    assert ("specification ambiguity a reviewer finds is a question for the user"
            in review_flat())


def test_disabled_review_keeps_existing_validation_and_has_no_fix_loop():
    """REQ-FUNC-9514e017: the opt-in switch controls no mandatory proof."""
    assert ("with review disabled, validate skips only these verdicts and keeps every "
            "other step") in review_flat()
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    for proof in ("Review the diff", "**Prove last:**", "--strict --run",
                  "Log the result once"):
        assert proof in validate


def test_closing_records_review_approval_only_when_enabled():
    """REQ-FUNC-9514e017: closing respects the policy and current verdicts."""
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "explicit review approved, when enabled" in validate
    assert "Both approved: continue with validate's next step" in review_flat()


def test_large_work_may_split_only_into_optional_one_level_children():
    """REQ-FUNC-3bc8597c: decomposition is explicit, optional, and shallow."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text("utf-8").split())
    frame = " ".join((PAYLOAD / "steps" / "1_frame.md").read_text("utf-8").split())
    design = " ".join((PAYLOAD / "steps" / "3_design.md").read_text("utf-8").split())
    assert "child tasks, one level deep" in agents and "--parent TASK-<id>" in agents
    assert "Decide whether the work needs child tasks" in frame
    assert "non-overlapping scope and its requirements" in design


def test_parent_validates_integrated_visible_child_work():
    """REQ-FUNC-3bc8597c: the parent owns proof of the combined candidate."""
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert "A parent task validates the integrated candidate" in validate
    assert "child tasks visible in this checkout" in validate
    assert "independently validated" in validate


def test_resume_starts_with_brief_but_requires_current_stage_sources():
    """REQ-UX-94a33d75: compact re-entry preserves authoritative source reads."""
    resume = resume_section()
    assert resume.index("brief TASK-<id>") < resume.index("Read next")
    assert "relevant sections of `.agentic/context/environment.md`" in resume


def test_five_stage_workflow_stops_at_each_stage_when_autopilot_is_off():
    """REQ-FUNC-d60b322b: stage order is unchanged while control is explicit."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text("utf-8").split())
    rows = [f"| {stage} | `.agentic/steps/{number}_{stage}.md` |" for number, stage in
            enumerate(("frame", "specify", "design", "build", "validate"), 1)]
    positions = [agents.index(row) for row in rows]
    assert positions == sorted(positions)
    assert "| deliver |" not in agents
    assert "(default `false`)" in agents and "**checkpoint** (default)" in agents
    assert "An explicit user instruction" in agents and "always wins" in agents


def test_pointer_digest_routes_to_the_contract_without_replacing_it():
    """REQ-PLAT-e675406e: generated pointers carry the entry routes, not the contract."""
    source = AEGIS_PY.read_text(encoding="utf-8")
    digest = " ".join(source.split('POINTER_DIGEST = """\\\n', 1)[1].split('"""', 1)[0].split())
    for phrase in ("read `.agentic/AGENTS.md`", "aegis.py status", "steps/1_frame.md",
                   "brief TASK-<id>", "Read next",
                   "frame -> specify -> design -> build -> validate -> done",
                   "specify and design have skip rules", "`advance`", "`pause`",
                   "never blocks", "follow the repository's own procedures",
                   "DEVIATION <stage>:"):
        assert phrase in digest, phrase
    assert "enough to act on" not in digest
    assert "quick" not in digest


def test_the_admission_rule_sits_at_every_gate():
    """Only durable product rules enter AEGIS; bug fixes and local UI edits go direct."""
    source = AEGIS_PY.read_text(encoding="utf-8")
    digest = " ".join(source.split('POINTER_DIGEST = """\\\n', 1)[1].split('"""', 1)[0].split())
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    for text in (digest, agents):
        for phrase in ("durable product rule", "product-wide UI rule",
                       "a bug fix that restores intended behavior",
                       "a local UI adjustment (one element's position, spacing, wording or style)",
                       "contradicts an active requirement", "security or data handling",
                       "The user's explicit choice wins", "`LANE: direct|aegis - <why>`"):
            assert phrase in text, phrase
    assert "add a regression test for a logic bug" in agents
    gates = [INTEGRATIONS / "claude" / "plugins" / "aegis" / "hooks.mjs",
             INTEGRATIONS / "qwen" / "AEGIS.md",
             INTEGRATIONS / "opencode" / "prompts" / "aegis.md",
             INTEGRATIONS / "claude" / "plugins" / "aegis" / "skills" / "workflow" / "SKILL.md",
             INTEGRATIONS / "codex" / "plugins" / "aegis" / "skills" / "aegis" / "SKILL.md",
             INTEGRATIONS / "pi" / "skills" / "aegis" / "SKILL.md",
             INTEGRATIONS / "qwen" / "skills" / "aegis" / "SKILL.md"]
    for gate in gates:
        text = " ".join(gate.read_text(encoding="utf-8").split())
        assert "durable product rule" in text, gate
        assert "bug fixes that restore intended behavior" in text, gate


def test_validation_closes_the_task_and_publication_stays_outside(tmp_path):
    """REQ-FUNC-24ea4f73: proof may mutate; publication is the developer's."""
    agents = " ".join((PAYLOAD / "AGENTS.md").read_text(encoding="utf-8").split())
    validate = " ".join((PAYLOAD / "steps" / "5_validate.md").read_text("utf-8").split())
    assert ("Commits, pushes, pull requests, merges, tickets, releases and packaging "
            "are outside it") in agents
    assert "**Prove last:**" in validate and "they are not AEGIS steps" in validate
    assert "A legacy journal at `deliver`" in validate
    _agentic, aegis = make_repo(tmp_path)
    assert aegis.WORK_STAGES[-2:] == ("validate", "done")
    assert aegis.STAGE_STEP_FILES["deliver"] == "5_validate.md"


def test_deliver_has_no_default_write_zone(tmp_path):
    """REQ-FUNC-24ea4f73: merge-base diffs cannot enforce stage-local edits."""
    _agentic, aegis = make_repo(tmp_path)
    assert "validate" not in aegis.DEFAULT_ZONES
    assert "deliver" not in aegis.DEFAULT_ZONES


def test_no_step_commits_pushes_or_publishes():
    """REQ-FUNC-dcb42072: Git publication follows the repository's procedures."""
    for path in sorted((PAYLOAD / "steps").glob("*.md")):
        text = " ".join(path.read_text(encoding="utf-8").split())
        for action in ("git commit", "git push", "open the PR", "close-out commit"):
            assert action not in text, (path.name, action)


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


def test_payload_never_references_external_documents():
    """The payload must stand alone: no plan docs, no sibling products."""
    banned = re.compile(r"plan doc|doc[ -]0\d|00_Planning", re.IGNORECASE)
    for path in payload_files():
        if path.suffix in (".md", ".py", ".toml"):
            hit = banned.search(path.read_text(encoding="utf-8"))
            assert hit is None, f"{path.name} references '{hit.group(0)}'"


def test_frame_captures_evidence_intent_and_ambiguity_before_mechanics():
    """REQ-UX-81840102: framing preserves understanding before scope is accepted.

    The journal's skeleton holds the Frame fields, so creating it comes
    first; analysis, challenge and the path all precede any acceptance.
    """
    agents = (PAYLOAD / "AGENTS.md").read_text(encoding="utf-8")
    frame = " ".join((PAYLOAD / "steps" / "1_frame.md").read_text(encoding="utf-8").split())
    task = (PAYLOAD / "templates" / "task.md").read_text(encoding="utf-8")

    for phrase in ("## Evidence", "STATED", "OBSERVED", "INFERRED", "UNKNOWN"):
        assert phrase in agents
    for phrase in ("**Analyze.**", "**Challenge.**", "**Audit.**", "decision-blocking",
                   "`Decision-blocking questions`", "`Proposed behaviors`",
                   "Do not settle open behavior by convention",
                   "an example that needs a value the user has not given names it, such "
                   "as `N days`, instead of choosing a number"):
        assert phrase in frame, phrase
    assert (frame.index("Create the journal") < frame.index("**Analyze.**")
            < frame.index("**Challenge.**") < frame.index("When existing requirements")
            < frame.index("**Audit.**") < frame.index("**Finish:**"))
    assert "quick" not in frame.lower() and "path:" not in task
    assert "the first decision-blocking question" in frame
    for field in ("Problem:", "Desired outcome:", "Primary scenario:", "Success signals:",
                  "Counterexamples:", "Assumptions:", "Unknowns:", "Evidence:"):
        assert field in task, field


def test_specify_proves_behavior_coverage_and_verification_quality():
    """REQ-FUNC-aa60c372: specification demonstrates semantic completeness."""
    specify = (PAYLOAD / "steps" / "2_specify.md").read_text(encoding="utf-8")
    requirement = (PAYLOAD / "templates" / "requirement.toml").read_text(
        encoding="utf-8")
    spec = (PAYLOAD / "templates" / "spec.md").read_text(encoding="utf-8")
    task = (PAYLOAD / "templates" / "task.md").read_text(encoding="utf-8")
    specify = " ".join(specify.split())

    for phrase in ("## Requirement coverage", "one trigger or state and one observable response",
                   "every error response included", "its own requirement", "EARS",
                   'one "shall"', "setup, trigger, observable oracle", "boundary",
                   "**Challenge.**", "conflicts with existing requirements",
                   "state machines", "migrations"):
        assert phrase in specify, phrase
    assert "Each atomic behavior maps to exactly one requirement" in " ".join(task.split())
    assert "| Frame outcome | Atomic behavior | Requirement | Verification |" in task
    assert "independently verifiable responses" in requirement
    assert "## Assumptions and open decisions" in spec
    assert "## Requirement coverage" in task


def test_design_scales_depth_and_keeps_proposals_out_of_current_knowledge():
    """REQ-FUNC-3e0263e7: design depth follows risk and proposals stay explicit."""
    design = (PAYLOAD / "steps" / "3_design.md").read_text(encoding="utf-8")
    validate = (PAYLOAD / "steps" / "5_validate.md").read_text(encoding="utf-8")
    design = " ".join(design.split())
    validate = " ".join(validate.split())

    for phrase in ("about 30 lines", "**Approach**", "**Interfaces and data**",
                   "**Files and test seams**", "**Risks and open decisions**",
                   "**Requirement map**", "primary flow", "failure recovery",
                   "security, concurrency, compatibility or migration",
                   "An open product decision stays open", "one skip rule"):
        assert phrase in design, phrase
    assert "decision-free" not in design
    # the proposal lives in the task; current pages change only after build
    assert "Leave knowledge pages unchanged" in design
    assert "reviewed code and tests" in validate


#: an f-string whose braces contain a double-quoted string needs the
#: flexible f-string grammar of Python 3.12 (PEP 701) - the promise is 3.11.
NESTED_FSTRING_RE = re.compile(r'f"[^"\n]*\{[^{}\n]*"')


def test_no_nested_quote_fstrings_python_311_promise():
    hits = [line for line in AEGIS_PY.read_text(encoding="utf-8").splitlines()
            if NESTED_FSTRING_RE.search(line)]
    assert hits == [], f"3.12-only f-string syntax: {hits[0]}"


def test_the_nested_fstring_guard_actually_fires():
    assert NESTED_FSTRING_RE.search('x = f"TASK-{new_id(taken("a", "b"))}"')


def test_aegis_py_imports_only_the_standard_library():
    assert non_stdlib_imports(AEGIS_PY.read_text(encoding="utf-8")) == []


def test_the_stdlib_import_guard_actually_fires():
    bad = "import requests\nfrom yaml import safe_load\nimport os\n"
    assert non_stdlib_imports(bad) == ["requests", "yaml"]


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


def test_every_payload_file_carries_the_spdx_tag():
    for path in payload_files():
        if path.name == "LICENSE.txt":
            continue  # the license text itself
        head = path.read_text(encoding="utf-8")[:300]
        assert LICENSE_MARK in head, f"missing SPDX tag: {path.name}"


def payload_flat(*parts: str) -> str:
    """One payload file with its whitespace collapsed to single spaces."""
    return " ".join(PAYLOAD.joinpath(*parts).read_text(encoding="utf-8").split())


def test_design_draws_diagrams_only_through_the_enabled_guide():
    """REQ-FUNC-ee1d2096, REQ-FUNC-f7220cb2: one pointer, one guide, one file."""
    design = payload_flat("steps", "3_design.md")
    guide = payload_flat("steps", "diagrams.md")
    # brief computes the configuration gate once; design reads its line
    assert "The `Diagrams:` line of `python .agentic/aegis.py brief TASK-<id>`" in design
    assert "When `brief` shows `Diagrams: draw ...`" in design
    assert "`.agentic/steps/diagrams.md`" in design
    for phrase in ("`.agentic/tasks/diagram_TASK-<id>.md`",
                   "Diagrams: [diagram_TASK-<id>.md](diagram_TASK-<id>.md)",
                   "`structure`", "`sequence`", "`state`",
                   "flowchart", "sequenceDiagram", "stateDiagram-v2",
                   "Mermaid", "The Design text is authoritative",
                   "Not drawn:", "no design note",
                   "Draw exactly the types the `Diagrams:` line names",
                   "only `enabled = true` draws",
                   "a missing or non-list `types` means `structure`",
                   "an empty or unknown-only list draws nothing, with no file and no link"):
        assert phrase in guide, phrase
    # the worked example shows every edge mark it asks for
    example = guide[guide.index("```mermaid"):guide.index("## Sequence")]
    for mark in ("==>", "-.->", ":::added", ":::changed", ":::removed"):
        assert mark in example, mark


def test_design_checkpoint_shows_diagrams_before_the_choices():
    """REQ-UX-b0bd0225: summary, then the diagrams, then the design choices."""
    design = payload_flat("steps", "3_design.md")
    guide = payload_flat("steps", "diagrams.md")
    finish = design[design.index("**Finish:**"):]
    sentence = finish[finish.index("show the summary"):]
    sentence = sentence[:sentence.index(". ")]
    assert (sentence.index("summary") < sentence.index("diagrams")
            < sentence.index("the choices"))
    presentation = guide[guide.index("**Checkpoint presentation:**"):]
    assert (presentation.index("the summary `pause` printed")
            < presentation.index("Mermaid fence") < presentation.index("the design choices"))
    assert "omit the diagram display and add no stop" in guide


def test_no_stage_obligation_depends_on_diagrams():
    """REQ-FUNC-6343dfb8: a diagram is illustration, never a completion duty."""
    for path in sorted((PAYLOAD / "steps").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "**Done when:**" in text:
            done = text[text.index("**Done when:**"):]
            done = done.split("**Skip when:**")[0]
            assert "diagram" not in done.lower(), path.name
    for name in ("4_build.md", "5_validate.md", "review.md"):
        text = (PAYLOAD / "steps" / name).read_text(encoding="utf-8")
        assert "diagram" not in text.lower(), name
    assert "Nothing checks this file" in payload_flat("steps", "diagrams.md")


def test_only_the_design_guide_directs_drawing_a_diagram():
    """REQ-FUNC-f7220cb2: no other step, template or adoption step draws one."""
    paths = [*sorted((PAYLOAD / "steps").glob("*.md")),
             *sorted((PAYLOAD / "templates").glob("*"))]
    for path in paths:
        if path.name == "diagrams.md":
            continue
        text = path.read_text(encoding="utf-8")
        # Presentation may name Mermaid; drawing syntax belongs to the guide.
        assert not re.search(
            r"```mermaid\b|\bflowchart\s+(?:LR|TD)\b|\bsequenceDiagram\b|\bstateDiagram-v2\b",
            text, re.IGNORECASE,
        ), path.name
        assert "Proposed architecture" not in text, path.name
        if path.name != "5_validate.md":
            assert "## Architecture" not in text, path.name


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
                    "## Change map", "## Key behaviors", "## Files"):
        assert heading in component
    assert "## Architecture" not in component
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
    assert "Migrate a touched legacy page to the current template" in validate_flat
    assert "retired `## Architecture` section" in validate_flat
    assert ("remove a retired `## Architecture` section and keep any still-true "
            "constraint from it in Purpose and boundaries or Invariants") in validate_flat
