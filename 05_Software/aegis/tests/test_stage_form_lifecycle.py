#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_stage_form_lifecycle.py
@brief Regression tests for the 2.1.0 stage-form corrections.
@details Covers durable requirement lifecycle survival across a re-apply,
         backward routing that defers only evidence blockers, delivery closure
         re-checking blocking invariants, closed-vocabulary validation at
         `stage apply`, and the rendered field guidance in generated forms.
"""

# IMPORTS

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tomllib

import pytest

from aegis.cli import main
from aegis.config import WorkflowConfig, load_config
from aegis.invariants import evaluate
from aegis.models import ALL_STAGES, Check, Evidence, Graph, SolutionDesign, StageRecord
from aegis.requirement_store import find_requirement_record
from aegis.requirements import RequirementPatch, update_requirement
from aegis.stage_forms import (
    _q,
    apply_stage,
    close_stage,
    next_command,
    prepare_stage,
    stage_blockers,
    stage_directory,
)
from aegis.stage_schema import (
    STAGE_DONE_WHEN,
    StageChecklistItem,
    StageOperationError,
    validate_stage_done_when,
)
from aegis.store import init_graph, save_graph

# LOCAL HELPERS


def _replace(path: Path, edits: dict[str, str]) -> None:
    """
    @brief      Apply literal substitutions to one generated form.
    @param[in]  path Form path.
    @param[in]  edits Mapping of exact source text to replacement text.
    @return     None.
    @exception  AssertionError If any source text is absent.
    """
    text = path.read_text(encoding="utf-8")
    for source, replacement in edits.items():
        assert source in text, f"{source!r} not found in {path}"
        text = text.replace(source, replacement)
    path.write_text(text, encoding="utf-8")


def _journal(repo_root: Path, run_id: str) -> list[dict]:
    """
    @brief      Read one run's journal as parsed records.
    @param[in]  repo_root Repository root.
    @param[in]  run_id Run identifier.
    @return     Every complete journal record in order.
    @exception  None
    """
    path = repo_root / ".agentic" / "runs" / run_id / "journal.jsonl"
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _publish_one_requirement(
    repo_root: Path,
    config: WorkflowConfig,
    statement: str,
) -> tuple[Graph, str]:
    """
    @brief      Drive one run's requirement stage through production code.
    @param[in]  repo_root Temporary repository root.
    @param[in]  config Validated workflow configuration.
    @param[in]  statement Intent statement for the new run.
    @return     The run's graph, closed out of `requirement`, and the ID it
                published.
    @details    The run is created and moved straight to `requirement`; the
                earlier stages contribute nothing to what these tests exercise,
                and everything from `stage prepare` onward is the real path, so
                the published record and the stage payload have their
                production shapes.
    @exception  None
    """
    graph = init_graph(repo_root, "feature", statement)
    graph.stage = "requirement"
    save_graph(repo_root, graph)
    prepare_stage(repo_root, graph, config)

    directory = stage_directory(repo_root, graph)
    form = next(directory.glob("requirement-*.toml"))
    text = form.read_text(encoding="utf-8")
    requirement_id = next(
        line.split("=", 1)[1].strip().strip('"')
        for line in text.splitlines()
        if line.startswith("id = ")
    )
    _replace(
        form,
        {
            'requirement = ""': 'requirement = "The system clears stale state."',
            'rationale = ""': 'rationale = "Stale state is observable."',
            'verification = ""': 'verification = "Manual: inspect the linked check."',
        },
    )
    apply_stage(repo_root, graph, config)
    graph, _ = close_stage(repo_root, graph, config)
    return graph, requirement_id


def _place_at_implementation(
    repo_root: Path,
    graph: Graph,
    config: WorkflowConfig,
    requirement_id: str,
) -> Path:
    """
    @brief      Move a run to `implementation` with one uncovered check.
    @param[in]  repo_root Repository root.
    @param[in,out] graph Active workflow graph.
    @param[in]  config Validated workflow configuration.
    @param[in]  requirement_id Requirement the check cites.
    @return     Prepared implementation form path.
    @details    The check carries no evidence at all, which is the state a
                developer is in when they realise at implementation that the
                contract itself is wrong.
    @exception  None
    """
    graph.stage = "implementation"
    graph.checks = [
        Check(
            id="CHK-001",
            level="unit",
            cites_spec=[],
            cites_requirement=[requirement_id],
            command="pytest -q",
        )
    ]
    graph.stage_records["check"] = StageRecord(
        stage="check",
        revision=1,
        status="closed",
        retention="discard",
        check_execution="external",
    )
    save_graph(repo_root, graph)
    form = prepare_stage(repo_root, graph, config)
    _replace(form, {"changed_paths = []": 'changed_paths = ["src/state.py"]'})
    return form


# TESTS


def test_stage_done_when_covers_every_stage_with_classified_items() -> None:
    """@brief WP1 keeps the canonical checklist complete and classified."""
    validate_stage_done_when()

    assert tuple(STAGE_DONE_WHEN) == tuple(ALL_STAGES)
    assert all(STAGE_DONE_WHEN[stage] for stage in ALL_STAGES)
    assert all(
        item.human != bool(item.command)
        for items in STAGE_DONE_WHEN.values()
        for item in items
    )


def test_stage_done_when_rejects_empty_or_unclassified_items() -> None:
    """@brief WP1 rejects incomplete declarative completion contracts."""
    empty = dict(STAGE_DONE_WHEN)
    empty["intake"] = ()
    with pytest.raises(StageOperationError, match="intake checklist must not be empty"):
        validate_stage_done_when(empty)

    unclassified = dict(STAGE_DONE_WHEN)
    unclassified["intake"] = (StageChecklistItem("Missing classification."),)
    with pytest.raises(StageOperationError, match="must be either machine or human"):
        validate_stage_done_when(unclassified)


def test_generated_primary_forms_render_stable_completion_comments(
    tmp_path: Path,
) -> None:
    """@brief WP1 renders validation checklist comments in canonical order."""
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Render stage completion guidance")
    graph.stage = "validation"
    save_graph(tmp_path, graph)

    form = prepare_stage(tmp_path, graph, config)
    lines = form.read_text(encoding="utf-8").splitlines()
    expected = [
        "# Completion checklist:",
        *[
            "# [human] " + item.text
            if item.human
            else f"# [machine: {item.command}] {item.text}"
            for item in STAGE_DONE_WHEN["validation"]
        ],
        "",
    ]

    assert lines[: len(expected)] == expected
    assert "Completion checklist" not in tomllib.loads(form.read_text(encoding="utf-8"))


def test_collection_forms_render_completion_comments_only_in_stage_control(
    tmp_path: Path,
) -> None:
    """@brief WP1 keeps collection guidance out of every check item form."""
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Render collection completion guidance")
    graph.stage = "check"
    save_graph(tmp_path, graph)

    prepare_stage(tmp_path, graph, config)
    control = stage_directory(tmp_path, graph) / "stage.toml"
    item = next(stage_directory(tmp_path, graph).glob("check-*.toml"))

    assert control.read_text(encoding="utf-8").count("# Completion checklist:") == 1
    assert "Completion checklist" not in item.read_text(encoding="utf-8")


def test_reprepared_forms_retain_completion_comments_and_payload_shape(
    tmp_path: Path,
) -> None:
    """@brief WP1 preserves comment guidance across form rehydration."""
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Rehydrate completion guidance")
    graph.stage = "intake"
    save_graph(tmp_path, graph)
    form = prepare_stage(tmp_path, graph, config)
    initial_payload = tomllib.loads(form.read_text(encoding="utf-8"))

    record = graph.stage_records["intake"]
    record.status = "applied"
    record.payload = initial_payload
    save_graph(tmp_path, graph)

    rehydrated = prepare_stage(tmp_path, graph, config)
    rehydrated_text = rehydrated.read_text(encoding="utf-8")
    rehydrated_payload = tomllib.loads(rehydrated_text)

    assert "# Completion checklist:" in rehydrated_text
    assert "Completion checklist" not in rehydrated_payload
    assert rehydrated_payload["statement"] == initial_payload["statement"]
    assert rehydrated_payload["control"] == initial_payload["control"]


def test_routing_back_from_implementation_preserves_requirement_lifecycle(
    tmp_path: Path,
) -> None:
    """
    @brief      Correcting a wrong contract is possible and costs no history.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    The two halves of this are one workflow, so they are asserted
                together. Routing backwards used to be gated on producing red
                *and* green evidence for the very checks the route is about to
                discard, which made the honest correction cost more than
                pressing forward dishonestly; and once you paid that cost, the
                re-apply at `requirement` republished every record as brand new
                - resetting an already-Active requirement to `Planned` and
                overwriting `created_on`, which exists nowhere but that TOML.
                Either defect alone makes backward routing unusable.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id = _publish_one_requirement(
        tmp_path,
        config,
        "Clear stale state",
    )
    update_requirement(
        tmp_path,
        requirement_id,
        config=config,
        patch=RequirementPatch(status="Active"),
    )
    before = find_requirement_record(tmp_path, requirement_id, config)
    assert before.status == "Active"

    form = _place_at_implementation(tmp_path, graph, config, requirement_id)
    _replace(
        form,
        {
            'summary = ""': 'summary = "The requirement text is wrong"',
            'route_to = ""': 'route_to = "requirement"',
            'route_rationale = ""': (
                'route_rationale = "The observable contract must be restated"'
            ),
        },
    )
    apply_stage(tmp_path, graph, config)

    # The evidence blockers this route defers really do stand right now.
    assert stage_blockers(tmp_path, graph) == [
        "CHK-001 has no active green evidence",
        "CHK-001 is missing prior red evidence",
    ]

    graph, _ = close_stage(tmp_path, graph, config)

    assert graph.stage == "requirement"
    routed = next(
        entry
        for entry in _journal(tmp_path, graph.run_id)
        if entry["event"] == "stage.routed"
    )
    assert routed["data"]["to"] == "requirement"
    assert sorted(routed["data"]["blockers_deferred"]) == [
        "CHK-001 has no active green evidence",
        "CHK-001 is missing prior red evidence",
    ]

    prepare_stage(tmp_path, graph, config)
    apply_stage(tmp_path, graph, config)

    after = find_requirement_record(tmp_path, requirement_id, config)
    assert after.status == "Active"
    assert after.created_on == before.created_on


def test_forward_close_still_demands_its_evidence(tmp_path: Path) -> None:
    """
    @brief      The route fast-path does not weaken an ordinary close.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    The complement of the regression above: deferral is keyed on
                `control.route_to`, so the same stage with the same missing
                evidence and no route must still refuse to close.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id = _publish_one_requirement(
        tmp_path,
        config,
        "Clear stale state",
    )
    form = _place_at_implementation(tmp_path, graph, config, requirement_id)
    _replace(form, {'summary = ""': 'summary = "Implementation complete"'})
    apply_stage(tmp_path, graph, config)

    with pytest.raises(StageOperationError, match="missing prior red evidence"):
        close_stage(tmp_path, graph, config)


def test_routing_back_still_enforces_control_validity(tmp_path: Path) -> None:
    """
    @brief      A route to a later stage is rejected, deferral notwithstanding.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    Only evidence blockers are deferred. Structural and control
                validity are enforced at `stage apply`, ahead of any close, so
                the fast-path can never become a way to route anywhere.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id = _publish_one_requirement(
        tmp_path,
        config,
        "Clear stale state",
    )
    form = _place_at_implementation(tmp_path, graph, config, requirement_id)
    _replace(
        form,
        {
            'summary = ""': 'summary = "Jump ahead"',
            'route_to = ""': 'route_to = "delivery"',
            'route_rationale = ""': 'route_rationale = "Skip the rest"',
        },
    )

    with pytest.raises(StageOperationError, match="must name an earlier stage"):
        apply_stage(tmp_path, graph, config)


def test_delivery_close_refuses_while_a_blocking_invariant_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      A hand-placed delivery stage cannot complete an empty run.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Editing `graph.json`'s `stage` to `delivery` is a developer's
                prerogative, and this is not tamper-proofing. The defect is
                that delivery closed a run to `complete: true` while the report
                it had just generated said `INV-6 FAIL (blocking)` - an
                internal inconsistency no other stage permits.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "change", "--quick", "--json"])
    started = json.loads(capsys.readouterr().out)

    graph_file = (
        tmp_path / ".agentic" / "runs" / started["run_id"] / "graph.json"
    )
    data = json.loads(graph_file.read_text(encoding="utf-8"))
    data["stage"] = "delivery"
    graph_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    main(["stage", "prepare", "--json"])
    form = tmp_path / json.loads(capsys.readouterr().out)["artifact"]
    _replace(
        form,
        {
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "Nothing was actually done"',
        },
    )
    main(["stage", "apply", "--json"])
    capsys.readouterr()

    with pytest.raises(SystemExit):
        main(["stage", "close", "--json"])
    response = json.loads(capsys.readouterr().out)

    assert response["status"] == "blocked"
    assert "invariant INV-6 does not hold" in response["error"]
    assert json.loads(graph_file.read_text(encoding="utf-8"))["complete"] is False


@pytest.mark.parametrize(
    ("stage", "edit", "expected"),
    [
        (
            "validation",
            {'diff_review = "pending"': 'diff_review = "approved"'},
            'validation diff_review must be "pending", "pass" or '
            '"not-applicable" (got "approved")',
        ),
        (
            "delivery",
            {'decision = "pending"': 'decision = "accept"'},
            'delivery decision must be "pending" or "approved" (got "accept")',
        ),
    ],
)
def test_stage_apply_rejects_an_unknown_token_and_names_the_accepted_set(
    tmp_path: Path,
    stage: str,
    edit: dict[str, str],
    expected: str,
) -> None:
    """
    @brief      Closed-vocabulary fields fail at apply, naming the real tokens.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  stage Stage whose form carries the field.
    @param[in]  edit Substitution introducing the wrong token.
    @param[in]  expected Exact expected error text.
    @return     None.
    @details    These were accepted silently by `stage apply` and rejected only
                at `stage close`, by a message that named neither the offending
                value nor a token that would have worked. `baseline-review`
                already validated its decision at import; this brings the rest
                into line with it.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Exercise the stage vocabulary")
    graph.stage = stage  # type: ignore[assignment]
    save_graph(tmp_path, graph)
    form = prepare_stage(tmp_path, graph, config)
    _replace(form, {'summary = ""': 'summary = "Ready"', **edit})

    with pytest.raises(StageOperationError) as error:
        apply_stage(tmp_path, graph, config)

    assert str(error.value) == expected


def test_generated_forms_carry_their_field_help_and_accepted_tokens(
    tmp_path: Path,
) -> None:
    """
    @brief      Schema help reaches the agent instead of staying metadata.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    `StageFieldSpec.help` existed and was explicitly not rendered,
                so a bare `diff_review = "pending"` gave no way to learn which
                tokens clear the blocker. Comments are not part of the parsed
                table, so the imported payload is unaffected.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Read the generated guidance")
    graph.stage = "validation"
    save_graph(tmp_path, graph)

    text = prepare_stage(tmp_path, graph, config).read_text(encoding="utf-8")

    assert (
        "# Diff review. Accepted: pending | pass | not-applicable" in text
    )
    assert '\ndiff_review = "pending"' in text
    # Fields with an open vocabulary carry their help and nothing more.
    assert "# Manual evidence.\nmanual_evidence = []" in text


# --- W22 / B18: adoption-delivery closes under the same invariant re-check ------


def _place_adoption_at_delivery(
    repo_root: Path,
    config: WorkflowConfig,
    *,
    bad_citation: bool,
) -> Graph:
    """
    @brief      Build an adoption run applied at `adoption-delivery`.
    @param[in]  repo_root Configured temporary repository.
    @param[in]  config Validated workflow configuration.
    @param[in]  bad_citation Whether to add a check citing a missing record.
    @return     Graph whose adoption-delivery record is applied and approved.
    @exception  None
    """
    graph = init_graph(repo_root, "adoption", "Adopt this repository")
    graph.stage = "adoption-delivery"
    if bad_citation:
        graph.checks = [
            Check(
                id="CHK-001",
                level="unit",
                cites_spec=[],
                cites_requirement=["REQ-FUNC-00000000-0000-0000-0000-000000000000"],
                command="pytest -q",
            )
        ]
    save_graph(repo_root, graph)
    form = prepare_stage(repo_root, graph, config)
    _replace(
        form,
        {
            'decision = "pending"': 'decision = "approved"',
            'summary = ""': 'summary = "The repository is adopted."',
        },
    )
    apply_stage(repo_root, graph, config)
    return graph


def test_adoption_delivery_close_is_not_blocked_by_inv6(tmp_path: Path) -> None:
    """
    @brief      Extending the delivery invariant re-check does not wedge adoption.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    B18 was deliberately scoped to `delivery` in Batch 4 because an
                adoption run has no evidence-producing stage, so INV-6 would
                have failed on every one of them and demanded a standing waiver
                for a condition the workflow itself creates. W22 settled that by
                making INV-6 report `not-applicable` for adoption runs, which is
                what makes this close reachable.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = _place_adoption_at_delivery(tmp_path, config, bad_citation=False)

    assert stage_blockers(tmp_path, graph) == []

    graph, artifact = close_stage(tmp_path, graph, config)

    assert graph.complete is True
    assert artifact is None


def test_adoption_delivery_close_refuses_a_failing_blocking_invariant(
    tmp_path: Path,
) -> None:
    """
    @brief      The re-check really does run on the adoption close path.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    The complement of the test above: leaving B18 delivery-only
                would have been an undocumented asymmetry where adoption gets a
                weaker close gate than every other run.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = _place_adoption_at_delivery(tmp_path, config, bad_citation=True)

    with pytest.raises(StageOperationError) as raised:
        close_stage(tmp_path, graph, config)

    assert "invariant INV-2 does not hold" in str(raised.value)
    assert graph.complete is False


# --- W21: guidance must agree with what `stage close` will accept ---------------


def test_next_command_says_close_when_a_route_defers_the_evidence(
    tmp_path: Path,
) -> None:
    """
    @brief      A routing implementation stage is told to close, not to gather.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    Regression test (W21, 2026-08-04): W3 made a routing close defer
                the evidence blockers, but `next_command` still returned
                `aegis check run`. That is the single most trusted output in the
                protocol - the agent follows it literally - so the friction W3
                removed came straight back through the guidance channel, telling
                the agent to produce evidence for checks it is about to delete.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id = _publish_one_requirement(
        tmp_path,
        config,
        "Clear stale state",
    )
    form = _place_at_implementation(tmp_path, graph, config, requirement_id)
    _replace(
        form,
        {
            'summary = ""': 'summary = "The requirement text is wrong"',
            'route_to = ""': 'route_to = "requirement"',
            'route_rationale = ""': (
                'route_rationale = "The observable contract must be restated"'
            ),
        },
    )
    apply_stage(tmp_path, graph, config)

    assert stage_blockers(tmp_path, graph) == [
        "CHK-001 has no active green evidence",
        "CHK-001 is missing prior red evidence",
    ]
    assert next_command(graph, tmp_path) == "aegis stage close"


def test_next_command_still_asks_for_evidence_without_a_route(
    tmp_path: Path,
) -> None:
    """
    @brief      The guidance fast-path is keyed on `route_to`, like the close.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    The complement of the regression above: the same stage with the
                same missing evidence and no route must still be told to gather
                it.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id = _publish_one_requirement(
        tmp_path,
        config,
        "Clear stale state",
    )
    form = _place_at_implementation(tmp_path, graph, config, requirement_id)
    _replace(form, {'summary = ""': 'summary = "Work in progress"'})
    apply_stage(tmp_path, graph, config)

    assert next_command(graph, tmp_path) == "aegis check prepare"


# --- B27: the B26 re-pin must not absorb a concurrent human edit ----------------


def _place_at_validation(
    repo_root: Path,
    config: WorkflowConfig,
) -> tuple[Graph, str, Path]:
    """
    @brief      Build a full run applied at `validation` with one green check.
    @param[in]  repo_root Configured temporary repository.
    @param[in]  config Validated workflow configuration.
    @return     The graph, its requirement ID, and that requirement's file.
    @details    The design is approved and its requirement digest pinned, which
                is the state INV-10 guards from `check` onward and the state
                validation close is about to rewrite.
    @exception  None
    """
    graph, requirement_id = _publish_one_requirement(
        repo_root,
        config,
        "Clear stale state",
    )
    record = find_requirement_record(repo_root, requirement_id, config)
    requirement_path = repo_root / str(record.source_file)
    design_path = repo_root / ".agentic" / "runs" / graph.run_id / "design.md"
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text("# Design\n\nUse a transaction.\n", encoding="utf-8")
    graph.stage = "validation"
    graph.design = SolutionDesign(
        revision=1,
        status="approved",
        approval="human",
        document_path=design_path.relative_to(repo_root).as_posix(),
        document_digest=sha256(design_path.read_bytes()).hexdigest(),
        requirement_digests={
            requirement_id: sha256(requirement_path.read_bytes()).hexdigest()
        },
        selected_option="Transactional update",
    )
    graph.checks = [
        Check(
            id="CHK-001",
            level="unit",
            cites_spec=[],
            cites_requirement=[requirement_id],
            command="pytest -q",
            state="green",
            red_evidence=["EV-001"],
        )
    ]
    graph.evidence = [
        Evidence(
            id="EV-001",
            kind="test-run",
            result="fail",
            summary="Red run",
            stage="check",
            check_id="CHK-001",
        ),
        Evidence(
            id="EV-002",
            kind="test-run",
            result="pass",
            summary="Green run",
            stage="implementation",
            check_id="CHK-001",
        ),
    ]
    graph.stage_records["validation"] = StageRecord(
        stage="validation",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="external",
        payload={
            "deterministic_verification": ["EV-002"],
            "diff_review": "pass",
            "documentation_review": "not-applicable",
            "style_review": "not-applicable",
            "manual_evidence": [],
        },
    )
    save_graph(repo_root, graph)
    return graph, requirement_id, requirement_path


def _invariant_holds(
    repo_root: Path,
    graph: Graph,
    config: WorkflowConfig,
    invariant_id: str,
) -> bool:
    """
    @brief      Report whether one invariant currently holds for a graph.
    @param[in]  repo_root Repository root.
    @param[in]  graph Active workflow graph.
    @param[in]  config Validated workflow configuration.
    @param[in]  invariant_id Stable invariant identifier.
    @return     The invariant's `holds` value as a boolean.
    @exception  StopIteration If the identifier is absent.
    """
    return bool(
        next(
            item
            for item in evaluate(repo_root, graph, config)
            if item.id == invariant_id
        ).holds
    )


def test_validation_close_activates_and_re_pins_its_own_status_flip(
    tmp_path: Path,
) -> None:
    """
    @brief      AEGIS rewriting its own lifecycle field is not INV-10 drift.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    The B26 half of this pair: activation flips `status` from
                `Planned` to `Active` in the very file whose digest the approved
                design pins, so without the re-pin INV-10 reported "snapshot
                changed" for the rest of every full run and the delivery hook
                denied every push.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id, requirement_path = _place_at_validation(tmp_path, config)

    assert stage_blockers(tmp_path, graph) == []

    graph, _ = close_stage(tmp_path, graph, config)

    assert find_requirement_record(tmp_path, requirement_id, config).status == "Active"
    assert graph.design is not None
    assert graph.design.requirement_digests[requirement_id] == sha256(
        requirement_path.read_bytes()
    ).hexdigest()
    assert _invariant_holds(tmp_path, graph, config, "INV-10")


def test_validation_close_refuses_to_absorb_a_post_approval_edit(
    tmp_path: Path,
) -> None:
    """
    @brief      Drift already present is reported, not re-pinned over.
    @param[in]  tmp_path Configured temporary repository.
    @return     None.
    @details    Regression test (B27, 2026-08-04): the B26 re-pin took the
                digest *after* activation wrote the file, so it captured
                whatever the file then contained - including an edit a human had
                made after design approval. INV-10 went back to passing and the
                edit was silently absorbed, which is exactly the case INV-10
                exists to catch. Validation close does not evaluate invariants,
                so nothing intercepted the drift before the re-pin. The blocker
                is an ordinary waivable stage blocker: a deliberate
                post-approval edit is still deliverable, it just has to be
                approved as one.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, requirement_id, requirement_path = _place_at_validation(tmp_path, config)
    requirement_path.write_text(
        requirement_path.read_text(encoding="utf-8").replace(
            "The system clears stale state.",
            "The system clears stale state, eventually.",
        ),
        encoding="utf-8",
        newline="\n",
    )
    pinned = graph.design.requirement_digests[requirement_id] if graph.design else ""

    blockers = stage_blockers(tmp_path, graph)

    assert blockers == [
        f"{requirement_id} changed after design approval; activating it "
        "would pin that edit over the approved snapshot"
    ]
    with pytest.raises(StageOperationError):
        close_stage(tmp_path, graph, config)
    # Nothing was written: the requirement is untouched and the pin still names
    # the approved snapshot, so INV-10 keeps reporting the drift.
    assert find_requirement_record(tmp_path, requirement_id, config).status == "Planned"
    assert graph.design is not None
    assert graph.design.requirement_digests[requirement_id] == pinned
    assert not _invariant_holds(tmp_path, graph, config, "INV-10")


@pytest.mark.parametrize(
    "value",
    ["\x7f", "before\x7fafter", "\x00", "\n", "\t", '"', "\\", "café \U0001f600"],
    ids=[
        "del",
        "embedded-del",
        "nul",
        "newline",
        "tab",
        "quote",
        "backslash",
        "non-ascii",
    ],
)
def test_q_round_trips_every_control_character(value: str) -> None:
    """
    @brief      `stage_forms._q` produces something `tomllib` can read back.
    @param[in]  value Prose that has to survive a write/read round trip.
    @return     None.
    @details    Regression test (B25, 2026-08-04): `_q` carried the same
                `json.dumps` defect as B3 - it escapes the C0 range but emits
                U+007F (DEL) raw, which TOML's `ASCII_CTRL` rejects. A DEL byte
                in a stage-form field therefore produced a form `stage apply`
                could not parse. The fix keeps `_q`'s load-bearing `str()`
                coercion and routes the result through a TOML-legal escaper.
    @exception  None
    """
    assert tomllib.loads("k = " + _q(value))["k"] == value


def test_q_still_coerces_non_string_scalars() -> None:
    """
    @brief      `_q` still stringifies bools/ints rather than emitting bare TOML literals.
    @return     None.
    @exception  None
    @details    The `str()` coercion is what H1 protects: routing through the
                escaper must not regress it back to emitting `true`/`1` as bare
                TOML literals.
    """
    assert tomllib.loads("k = " + _q(True))["k"] == "True"
    assert tomllib.loads("k = " + _q(1))["k"] == "1"


def test_close_error_names_the_blocker_id_and_ends_one_sentence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      A close refused by an unresolved question names its blocker ID.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Working-directory fixture.
    @param[in]  capsys Captured CLI output.
    @return     None.
    @details    The blocker ID for an unresolved question is a slugified
                60-character prefix of the question plus a hash, so the error
                that tells the operator to look it up has to carry it. The
                question's own full stop was also doubled by the sentence the
                error appends.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "adoption", "--json"])
    artifact = json.loads(capsys.readouterr().out)["artifact"]
    question = "The test suite cannot run in full: the venv has no pip to install it."
    _replace(
        tmp_path / artifact,
        {
            'statement = ""': 'statement = "Adopt the billing component"',
            'adoption_slice = ""': 'adoption_slice = "billing"',
            'summary = ""': 'summary = "Adoption intake approved"',
            "unresolved_questions = []": (
                f"unresolved_questions = [{json.dumps(question)}]"
            ),
        },
    )
    main(["stage", "apply", "--json"])
    capsys.readouterr()
    main(["waive", "list", "--json"])
    blocker_id = json.loads(capsys.readouterr().out)["eligible_blockers"][0]["id"]

    with pytest.raises(SystemExit):
        main(["stage", "close", "--json"])
    error = json.loads(capsys.readouterr().out)["error"]

    assert blocker_id.startswith("stage:adoption-intake:")
    assert f"[{blocker_id}]" in error
    assert ".." not in error


# END OF FILE
