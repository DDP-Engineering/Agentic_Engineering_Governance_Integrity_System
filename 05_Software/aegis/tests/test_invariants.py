#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_invariants.py
@brief Workflow support module for test_invariants.
@details Covers expected workflow behavior through focused pytest checks.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import subprocess

from aegis.check_execution import _update_check_states
from aegis.config import RuleSetPolicy, ScopePolicy, WorkflowConfig, load_config
from aegis.invariants import (
    InvariantResult,
    _clean_secrets,
    _component_baseline_scope,
    _coverage,
    _no_regression,
    _red_before_green,
    evaluate,
)
from aegis.models import ChangeUnit, Check, Evidence, Graph
from aegis.requirements import load_requirement_index
from aegis.stage_forms import (
    apply_stage,
    close_stage,
    prepare_stage,
    stage_directory,
)
from aegis.store import add_waiver, init_graph, save_graph


# LOCAL HELPERS


def init_repo_with_commit(tmp_path: Path) -> None:
    """
    @brief      Initialize a Git repo with one committed file.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True, capture_output=True)


def secret_config(repo_root: Path) -> WorkflowConfig:
    """
    @brief      Build a WorkflowConfig with one secret-like regex configured.
    @param[in]  repo_root Repository containing the complete workflow config.
    @return     Valid workflow configuration with secret enforcement enabled.
    @exception  None
    """
    return replace(
        load_config(repo_root),
        secrets=RuleSetPolicy(mode="enforce", patterns=(r"sk-[A-Za-z0-9_-]{20,}",)),
    )


def complete_requirement_stage(
    repo_root: Path,
    config: WorkflowConfig,
    statement: str,
    requirement_text: str,
) -> tuple[Graph, str]:
    """
    @brief      Drive one full run's requirement stage through production code.
    @param[in]  repo_root Temporary repository root.
    @param[in]  config Validated workflow configuration.
    @param[in]  statement Intent statement for the new run.
    @param[in]  requirement_text Observable requirement prose.
    @return     The run's graph, advanced to design, and its requirement ID.
    @details    The run is created at its declared first stage and moved to
                `requirement` directly; the earlier stages contribute nothing
                to requirement ownership, which is what these tests exercise.
                Everything from `stage prepare` onward is the real code path,
                so the imported stage-record payload has its production shape.
    @exception  None
    """
    graph = init_graph(repo_root, "feature", statement)
    graph.stage = "requirement"
    save_graph(repo_root, graph)
    prepare_stage(repo_root, graph, config)

    directory = stage_directory(repo_root, graph)
    form = directory / "requirement-001.toml"
    text = form.read_text(encoding="utf-8")
    requirement_id = next(
        line.split("=", 1)[1].strip().strip('"')
        for line in text.splitlines()
        if line.startswith("id = ")
    )
    form.write_text(
        text.replace('requirement = ""', f'requirement = "{requirement_text}"')
        .replace('rationale = ""', 'rationale = "The behaviour is contractual."')
        .replace('verification = ""', 'verification = "Run the linked check."'),
        encoding="utf-8",
    )
    apply_stage(repo_root, graph, config)
    graph, _ = close_stage(repo_root, graph, config)
    return graph, requirement_id


def invariant(results: list[InvariantResult], invariant_id: str) -> InvariantResult:
    """
    @brief      Select one invariant result by its stable identifier.
    @param[in]  results Evaluated invariant results.
    @param[in]  invariant_id Stable invariant identifier.
    @return     The single matching result.
    @exception  StopIteration If the identifier is absent.
    """
    return next(item for item in results if item.id == invariant_id)


# TESTS


def test_clean_secrets_detects_staged_file(tmp_path: Path) -> None:
    """
    @brief      A secret in a staged-but-uncommitted file fails INV-7.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): the
                previous `git diff` (unstaged only) never showed a file that
                had already been `git add`-ed, so a secret committed via
                `git add` then left staged would silently pass INV-7.
    @exception  None
    """
    init_repo_with_commit(tmp_path)
    (tmp_path / "config.py").write_text("TOKEN = 'sk-abcdefghijklmnopqrstuvwx'\n", encoding="utf-8")
    subprocess.run(["git", "add", "config.py"], cwd=tmp_path, check=True, capture_output=True)

    result = _clean_secrets(tmp_path, secret_config(tmp_path))

    assert result.holds is False


def test_clean_secrets_detects_untracked_file(tmp_path: Path) -> None:
    """
    @brief      A secret in a brand-new untracked file fails INV-7.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): a
                newly created file has no committed history to diff against,
                so it never appeared in a plain `git diff` at all; the fix
                reads untracked file content directly via `git ls-files
                --others --exclude-standard`.
    @exception  None
    """
    init_repo_with_commit(tmp_path)
    (tmp_path / "new_file.py").write_text("TOKEN = 'sk-abcdefghijklmnopqrstuvwx'\n", encoding="utf-8")

    result = _clean_secrets(tmp_path, secret_config(tmp_path))

    assert result.holds is False


def test_clean_secrets_passes_for_untracked_file_without_secret(tmp_path: Path) -> None:
    """
    @brief      A clean untracked file does not trip INV-7.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    init_repo_with_commit(tmp_path)
    (tmp_path / "notes.md").write_text("Nothing sensitive here.\n", encoding="utf-8")

    result = _clean_secrets(tmp_path, secret_config(tmp_path))

    assert result.holds is True


def test_green_rerun_retires_failed_attempts_for_inv4_and_inv3(
    tmp_path: Path,
) -> None:
    """
    @brief      A genuine pass after failed attempts satisfies INV-4 and INV-3.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    End-to-end over the shared state-update rule: a check-stage red
                witness, a failed implementation attempt, then a genuine pass.
                The failed attempt is retired so INV-4 no longer reports a live
                regression, while the check-stage red stays active so INV-3's
                red-before-green link survives.
    """
    graph = init_graph(tmp_path, "fix", "Reconcile check evidence")
    graph.checks = [
        Check(id="CHK-001", level="unit", cites_spec=[], command="pytest -q")
    ]
    graph.evidence = [
        Evidence(
            id="E-0001",
            kind="test-run",
            result="fail",
            summary="red witness",
            stage="check",
            check_id="CHK-001",
            exit_status=1,
        ),
        Evidence(
            id="E-0002",
            kind="test-run",
            result="fail",
            summary="launcher denied",
            stage="implementation",
            check_id="CHK-001",
            exit_status=127,
        ),
    ]
    fresh_pass = Evidence(
        id="E-0003",
        kind="test-run",
        result="pass",
        summary="observed pass",
        stage="implementation",
        check_id="CHK-001",
        exit_status=0,
    )
    graph.evidence.append(fresh_pass)

    _update_check_states(graph, [fresh_pass])

    config = load_config(tmp_path)
    assert _no_regression(graph, config).holds is True
    assert _red_before_green(graph).holds is True
    assert graph.checks[0].red_evidence == "E-0001"
    assert graph.checks[0].green_evidence == "E-0003"


def test_regressed_check_still_fails_inv4(tmp_path: Path) -> None:
    """
    @brief      A rerun failure after a pass keeps INV-4 honestly failing.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    """
    graph = init_graph(tmp_path, "fix", "Expose a genuine regression")
    graph.checks = [
        Check(id="CHK-001", level="unit", cites_spec=[], command="pytest -q")
    ]
    graph.evidence = [
        Evidence(
            id="E-0001",
            kind="test-run",
            result="pass",
            summary="previously green",
            stage="implementation",
            check_id="CHK-001",
            exit_status=0,
        ),
    ]
    regression = Evidence(
        id="E-0002",
        kind="test-run",
        result="fail",
        summary="assertion failed",
        stage="implementation",
        check_id="CHK-001",
        exit_status=1,
    )
    graph.evidence.append(regression)

    _update_check_states(graph, [regression])

    config = load_config(tmp_path)
    assert _no_regression(graph, config).holds is False
    assert graph.checks[0].state == "red"


# --- INV-1 run-owned coverage scope ---------------------------------------------


def test_second_full_run_holds_inv1_for_requirements_it_does_not_own(
    tmp_path: Path,
) -> None:
    """
    @brief      A later full run is not blocked by an earlier run's requirement.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Regression test (2026-08-04): INV-1 compared the durable,
                repository-wide requirement register against one run's
                run-local checks. There is no durable check register, so from
                the second full run onward the rule was unsatisfiable and
                every full run failed listing every requirement it had not
                touched. INV-1 now means "every requirement this run owns is
                covered by a check"; repository-wide coverage stays the job of
                the traceability audit's REQ-LINK-MISSING finding.
    @exception  None
    """
    config = load_config(tmp_path)
    _, first_requirement = complete_requirement_stage(
        tmp_path,
        config,
        "Persist the first behaviour",
        "The system persists the first value.",
    )
    second_graph, second_requirement = complete_requirement_stage(
        tmp_path,
        config,
        "Persist the second behaviour",
        "The system persists the second value.",
    )

    # The durable register really does carry both runs' requirements: this is
    # the accumulation that used to make the second run unpassable.
    register = load_requirement_index(tmp_path, config).by_id
    assert {first_requirement, second_requirement} <= set(register)

    second_graph.checks = [
        Check(
            id="CHK-001",
            level="unit",
            cites_spec=[],
            cites_requirement=[second_requirement],
            command="pytest -q",
        )
    ]

    result = invariant(evaluate(tmp_path, second_graph, config), "INV-1")

    assert result.holds is True
    assert first_requirement not in result.message


def test_inv1_fails_when_the_second_run_leaves_its_own_requirement_uncovered(
    tmp_path: Path,
) -> None:
    """
    @brief      Narrowing INV-1 to run-owned requirements still catches a gap.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    The complement of the regression above: the rule must keep
                failing for a requirement the run does own and did not cover,
                and must name only that requirement.
    @exception  None
    """
    config = load_config(tmp_path)
    _, first_requirement = complete_requirement_stage(
        tmp_path,
        config,
        "Persist the first behaviour",
        "The system persists the first value.",
    )
    second_graph, second_requirement = complete_requirement_stage(
        tmp_path,
        config,
        "Persist the second behaviour",
        "The system persists the second value.",
    )

    result = invariant(evaluate(tmp_path, second_graph, config), "INV-1")

    assert result.holds is False
    assert second_requirement in result.message
    assert first_requirement not in result.message


def test_inv1_holds_before_a_run_imports_any_requirement(tmp_path: Path) -> None:
    """
    @brief      A run that owns nothing yet passes INV-1 rather than failing.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    A first run always passed vacuously here because the register
                was empty. A second run reaches its intake and alignment
                stages with the register already populated, so scoping must
                not fall back to the register when the run has imported no
                requirement stage record - that fallback would reinstate the
                original defect for the first third of every later run.
    @exception  None
    """
    config = load_config(tmp_path)
    complete_requirement_stage(
        tmp_path,
        config,
        "Persist the first behaviour",
        "The system persists the first value.",
    )
    later = init_graph(tmp_path, "feature", "Start a second run")

    result = invariant(evaluate(tmp_path, later, config), "INV-1")

    assert result.holds is True
    assert "owns no requirements yet" in result.message


def test_inv1_message_is_stable_across_two_loads_of_the_same_offenders(
    tmp_path: Path,
) -> None:
    """
    @brief      An unchanged offender set always renders the same message.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    The message is part of this result's waiver digest, so it has
                to be a function of the offender *set* alone. `missing` was
                built from `requirements.values()` - register-walk order - so
                the same three uncovered requirements could render in two
                different orders and stale an accepted waiver on ordering
                alone, with nothing about the run actually changed. Feeding the
                same register in two orders is the direct test of that: it
                fails for any unsorted implementation and cannot pass by luck.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = None
    requirement_ids = []
    for subject in ("first", "second", "third"):
        graph, requirement_id = complete_requirement_stage(
            tmp_path,
            config,
            f"Persist the {subject} behaviour",
            f"The system persists the {subject} value.",
        )
        requirement_ids.append(requirement_id)
    register = load_requirement_index(tmp_path, config).by_id
    owned = set(requirement_ids)
    assert graph is not None and not graph.checks

    forward = _coverage(register, owned, graph)
    reversed_register = dict(reversed(list(register.items())))
    backward = _coverage(reversed_register, owned, graph)

    assert forward.message == backward.message
    assert forward.message.endswith(", ".join(sorted(requirement_ids)))


def test_inv1_reports_an_emptied_requirement_record_as_that_defect(
    tmp_path: Path,
) -> None:
    """
    @brief      A malformed ownership record fails loudly, not silently.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    An imported requirement stage record always names at least one
                requirement, so a record that names none is corrupt. Reporting
                that specific defect keeps the two indistinguishable meanings
                of "this run owns nothing" apart: not-imported-yet passes,
                imported-but-empty fails with an actionable message.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, _ = complete_requirement_stage(
        tmp_path,
        config,
        "Persist a behaviour",
        "The system persists the value.",
    )
    graph.stage_records["requirement"].payload["requirements"] = []
    graph.design = None

    result = invariant(evaluate(tmp_path, graph, config), "INV-1")

    assert result.holds is False
    assert "names no requirement" in result.message
    assert result.can_waive is True


# --- INV-9 component baseline guard ---------------------------------------------


def test_component_baseline_scope_returns_result_when_guard_enforces(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      An enforcing component baseline guard evaluates, not crashes.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Exact workflow configuration editor.
    @return     None.
    @details    Regression test (2026-08-04): INV-9 passed a fourth argument
                read from `cfg.adoption_default_completion_level`, an
                attribute `WorkflowConfig` does not have. The resulting
                `AttributeError` is outside the CLI error boundary, so every
                command that evaluates invariants - including `waive list`,
                the escape hatch itself - died with a raw traceback the moment
                a repository opted into the guard.
    @exception  None
    """
    replace_workflow_toml(
        '[components.baseline_guard]\nmode = "disabled"',
        '[components.baseline_guard]\nmode = "enforce"\n'
        'minimum_completion_level = "characterized"',
    )
    manifest = tmp_path / ".agentic" / "components.toml"
    manifest.write_text(
        '[components.core]\npaths = ["src/core"]\nadoption_status = "discovered"\n',
        encoding="utf-8",
    )
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Change mapped component behaviour")
    graph.change_units = [
        ChangeUnit(id="CU-001", touched_paths=["src/core/engine.py"])
    ]

    result = _component_baseline_scope(tmp_path, graph, config)

    assert isinstance(result, InvariantResult)
    assert result.holds is False
    assert "COMPONENT-BASELINE-MISSING" in result.message


# --- Malformed requirement storage ----------------------------------------------


def test_malformed_requirement_file_becomes_a_waivable_blocker(
    tmp_path: Path,
) -> None:
    """
    @brief      An unloadable requirement register does not abort evaluation.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Regression test (2026-08-04): `evaluate` let
                `RequirementValidationError` escape, so a single malformed
                requirement file killed `waive list` and `verify run` alike.
                The blocker could not even be enumerated, let alone waived.
                The four requirement-reading rules now report the parse error
                as an ordinary waivable blocking failure, and the message
                still names the offending file.
    @exception  None
    """
    config = load_config(tmp_path)
    graph, _ = complete_requirement_stage(
        tmp_path,
        config,
        "Persist a behaviour",
        "The system persists the value.",
    )
    record = next(
        (tmp_path / ".agentic" / "requirements").rglob("*.toml")
    )
    record.write_text("schema_version = 1\nid = 42\n", encoding="utf-8")

    results = evaluate(tmp_path, graph, config)

    for invariant_id in ("INV-1", "INV-2", "INV-8", "INV-10"):
        result = invariant(results, invariant_id)
        assert result.holds is False
        assert result.can_waive is True
        assert record.name in result.message
    assert invariant(results, "INV-6").holds is not None


# --- Waiver digest stability ----------------------------------------------------


def test_message_fallback_waiver_is_staled_by_a_new_offender(
    tmp_path: Path,
) -> None:
    """
    @brief      A fallback-digest waiver does not extend to a later offender.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Regression test (2026-08-04): a proposal to digest only
                `{"id"}` on the message fallback was withdrawn. The message is
                derived from the offender list, so it cannot churn unless that
                set changes - and when it changes, the approval a human gave
                no longer covers what is failing. INV-2 is the same fallback
                path, checked here alongside the INV-5 case below.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Cite a requirement that is absent")
    graph.checks = [
        Check(
            id="CHK-001",
            level="unit",
            cites_spec=[],
            cites_requirement=["REQ-FUNC-00000000-0000-4000-8000-000000000001"],
            command="pytest -q",
        )
    ]
    save_graph(tmp_path, graph)
    first = invariant(evaluate(tmp_path, graph, config), "INV-2")
    assert first.holds is False
    add_waiver(
        tmp_path,
        graph,
        first.id,
        "The absent snapshot is accepted for this run.",
        first.state_digests,
    )

    graph.checks.append(
        Check(
            id="CHK-002",
            level="unit",
            cites_spec=[],
            cites_requirement=["REQ-FUNC-00000000-0000-4000-8000-000000000002"],
            command="pytest -q",
        )
    )
    save_graph(tmp_path, graph)
    second = invariant(evaluate(tmp_path, graph, config), "INV-2")

    assert second.message != first.message
    assert second.state_digests != first.state_digests
    assert second.waived is not True


def test_in_scope_waiver_does_not_cover_a_second_out_of_scope_path(
    tmp_path: Path,
) -> None:
    """
    @brief      An INV-5 waiver approves the paths it named, and no others.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    INV-5 takes the message fallback, and for it the offender's
                identity is the entire substance of the approval: a human who
                accepted out-of-scope path A never saw path B. The withdrawn
                digest narrowing would have carried the waiver silently onto
                B. The waiver must stale instead.
    @exception  None
    """
    config = replace(
        load_config(tmp_path),
        scope=ScopePolicy(mode="enforce", allowed_roots=("src",)),
    )
    graph = init_graph(tmp_path, "feature", "Touch a path outside scope")
    graph.change_units = [
        ChangeUnit(id="CU-001", touched_paths=["tools/a.py"])
    ]
    save_graph(tmp_path, graph)
    first = invariant(evaluate(tmp_path, graph, config), "INV-5")
    assert first.holds is False
    assert "tools/a.py" in first.message
    add_waiver(
        tmp_path,
        graph,
        first.id,
        "Editing the tool directory is accepted for this run.",
        first.state_digests,
    )
    assert invariant(evaluate(tmp_path, graph, config), "INV-5").waived is True

    graph.change_units[0].touched_paths.append("vendor/b.py")
    save_graph(tmp_path, graph)
    second = invariant(evaluate(tmp_path, graph, config), "INV-5")

    assert "vendor/b.py" in second.message
    assert second.state_digests != first.state_digests
    assert second.waived is not True


def test_pinned_invariants_keep_digesting_their_own_offending_state(
    tmp_path: Path,
) -> None:
    """
    @brief      INV-3's waiver tracks exact state, not just the invariant ID.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    INV-3, INV-4, INV-7 and INV-10 pin structured state rather than
                taking the message fallback, so a new offender stales their
                waivers through a different code path than the one above.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "fix", "Declare a check green without red")
    graph.checks = [
        Check(
            id="CHK-001",
            level="unit",
            cites_spec=[],
            command="pytest -q",
            state="green",
        )
    ]
    first = invariant(evaluate(tmp_path, graph, config), "INV-3")

    graph.checks.append(
        Check(
            id="CHK-002",
            level="unit",
            cites_spec=[],
            command="pytest -q",
            state="green",
        )
    )
    second = invariant(evaluate(tmp_path, graph, config), "INV-3")

    assert first.holds is False
    assert second.holds is False
    assert second.state_digests != first.state_digests


def test_inv3_offender_ordering_alone_does_not_stale_a_waiver(
    tmp_path: Path,
) -> None:
    """
    @brief      An INV-3 waiver survives a reordering of the same offender set.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Regression test (W20, 2026-08-04): INV-3 pins its own structured
                state via `state_digests({"missing": missing})` rather than
                falling back to the message, so the sorting sweep that closed
                W18 did not reach it. `missing` is built in `graph.checks`
                order, so moving a check changed the digest although the
                offender *set* was unchanged, staling a human's approval for
                nothing.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "fix", "Two green checks with no red evidence")

    def green(check_id: str) -> Check:
        """@brief Build one green check with no red evidence."""
        return Check(
            id=check_id,
            level="unit",
            cites_spec=[],
            command="pytest -q",
            state="green",
        )

    graph.checks = [green("CHK-001"), green("CHK-002")]
    first = invariant(evaluate(tmp_path, graph, config), "INV-3")

    graph.checks = [green("CHK-002"), green("CHK-001")]
    reordered = invariant(evaluate(tmp_path, graph, config), "INV-3")

    assert first.holds is False
    assert reordered.state_digests == first.state_digests
    assert reordered.message == first.message


# --- W22: INV-6 cannot hold for a run shape with no evidence stage ---------------


def test_inv6_is_not_applicable_for_an_adoption_run(tmp_path: Path) -> None:
    """
    @brief      An adoption run reports INV-6 as not-applicable, not failed.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    Decision on record (W22, 2026-08-04): an adoption run has no
                evidence-producing stage, so INV-6 can never hold for one.
                Reporting a blocking failure would demand a standing waiver for
                a condition the workflow itself creates - the same
                unsatisfiable-invariant shape as the original INV-1 scoping
                defect. `holds` is `None`, preserving the honest three-way
                distinction between not-applicable, waived, and disabled.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "adoption", "Adopt this repository")

    result = invariant(evaluate(tmp_path, graph, config), "INV-6")

    assert result.holds is None
    assert result.status == "not-applicable"
    assert result.policy == "not-applicable"
    assert "adoption run" in result.message


def test_inv6_still_fails_a_full_run_with_no_evidence(tmp_path: Path) -> None:
    """
    @brief      The not-applicable answer is scoped to adoption runs alone.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @exception  None
    """
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Add a behaviour")

    result = invariant(evaluate(tmp_path, graph, config), "INV-6")

    assert result.holds is False
    assert result.status != "not-applicable"


# END OF FILE
