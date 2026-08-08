#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli_surface.py
@brief Regression tests for the 2.1.0 CLI-surface corrections.
@details Covers run abandonment and enumeration, the requirement category
         flag, run-aware `config validate`, attributable approvals, read-only
         tolerance of an unresolvable run, and the two output-contract fixes.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis.cli import main
from aegis.models import Graph
from aegis.store import (
    current_run_path,
    graph_path,
    init_graph,
    load_graph,
    save_graph,
)


# LOCAL HELPERS


def _invoke(capsys: pytest.CaptureFixture[str], argv: list[str]) -> dict:
    """
    @brief      Run one CLI command and return its parsed JSON response.
    @param[in]  capsys Pytest capture fixture.
    @param[in]  argv Command arguments without the `--json` flag.
    @return     Parsed response payload.
    @exception  None
    """
    main([*argv, "--json"])
    return json.loads(capsys.readouterr().out)


def _start_feature(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> str:
    """
    @brief      Start one full feature run and return its ID.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  capsys Pytest capture fixture.
    @return     New run ID.
    @exception  None
    """
    return str(_invoke(capsys, ["run", "start", "feature"])["run_id"])


# TESTS - W2: a run can be abandoned


def test_run_abandon_ends_the_run_and_releases_the_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `run abandon` gives an unwanted run an exit.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Until 2.1.0 the only ways out of a run were driving it to
                delivery or leaving it incomplete forever, while the stop menu
                offered "abort" and the merge documentation forbade deleting
                the run directory.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)

    payload = _invoke(
        capsys,
        ["run", "abandon", "--reason", "The requirement was withdrawn."],
    )

    assert payload["outcome"] == "abandoned"
    assert payload["complete"] is True
    graph = load_graph(tmp_path, run_id)
    assert graph.complete is True
    assert graph.outcome == "abandoned"
    # The run directory is durable; only this worktree's selection is released.
    assert graph_path(tmp_path, run_id).is_file()
    assert not current_run_path(tmp_path).exists()
    journal = (
        tmp_path / ".agentic" / "runs" / run_id / "journal.jsonl"
    ).read_text(encoding="utf-8")
    abandoned = [
        json.loads(line)
        for line in journal.splitlines()
        if json.loads(line)["event"] == "run.abandoned"
    ]
    assert len(abandoned) == 1
    assert abandoned[0]["data"]["reason"] == "The requirement was withdrawn."


def test_abandoned_run_cannot_be_selected_or_resumed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      An abandoned run never returns to being the active run.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Abandonment is terminal. `run select` refuses it outright and
                names the read-only route, and the run being complete is what
                makes every mutating stage command decline it.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    _invoke(capsys, ["run", "abandon", "--reason", "Changed direction."])

    with pytest.raises(SystemExit) as selected:
        main(["run", "select", run_id, "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert selected.value.code == 1
    assert payload["status"] == "blocked"
    assert "abandoned" in payload["error"]
    assert not current_run_path(tmp_path).exists()

    # Read-only inspection still works through explicit --run, and reports the
    # run as complete with its outcome named.
    status = _invoke(capsys, ["--run", run_id, "run", "status"])
    assert status["complete"] is True
    assert status["outcome"] == "abandoned"
    assert status["next"] == "none"

    with pytest.raises(SystemExit) as prepared:
        main(["--run", run_id, "stage", "prepare", "--json"])
    assert prepared.value.code == 1
    assert "complete" in json.loads(capsys.readouterr().out)["error"]


def test_abandoning_an_ended_run_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      A run can only be abandoned once.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    _invoke(capsys, ["run", "abandon", "--reason", "Once."])

    with pytest.raises(SystemExit) as raised:
        main(["--run", run_id, "run", "abandon", "--reason", "Twice.", "--json"])

    assert raised.value.code == 1
    assert "already ended" in json.loads(capsys.readouterr().out)["error"]


def test_run_list_enumerates_runs_without_resolving_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `run list` works with no pointer and reports every outcome.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    This is the command an operator reaches for exactly when they
                do not know which run they have, so requiring a resolvable run
                would defeat it.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    first = _start_feature(tmp_path, capsys)
    _invoke(capsys, ["run", "abandon", "--reason", "Wrong scope."])
    second = _start_feature(tmp_path, capsys)

    payload = _invoke(capsys, ["run", "list"])

    rows = {item["run_id"]: item for item in payload["runs"]}
    assert set(rows) == {first, second}
    assert rows[first]["outcome"] == "abandoned"
    assert rows[first]["complete"] is True
    assert rows[first]["selected"] is False
    assert rows[second]["outcome"] == ""
    assert rows[second]["selected"] is True
    assert rows[second]["kind"] == "feature"
    assert rows[second]["profile"] == "full"


def test_run_list_reports_an_unreadable_graph_instead_of_hiding_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      A pre-schema-3 or corrupt run is still enumerated.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph_path(tmp_path, run_id).write_text(
        json.dumps({"schema_version": 2}),
        encoding="utf-8",
    )

    payload = _invoke(capsys, ["run", "list"])

    assert [item["run_id"] for item in payload["runs"]] == [run_id]
    assert payload["runs"][0]["stage"] == "unreadable"


# TESTS - W19: recovery must survive the state it reads being what is broken


def test_run_list_row_carries_the_parse_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      An unreadable run reports *why* it is unreadable.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Regression test (W19, 2026-08-04): the row already existed, but
                carried only the `unreadable` marker. This listing is what an
                operator reads when they do not know what is wrong, and it was
                the only place the cause could appear before the run is
                abandoned.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph_path(tmp_path, run_id).write_text("{ not json", encoding="utf-8")

    payload = _invoke(capsys, ["run", "list"])

    row = payload["runs"][0]
    assert row["stage"] == "unreadable"
    assert "JSONDecodeError" in row["error"]


def test_a_run_with_a_corrupt_graph_can_still_be_abandoned(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `run abandon` operates on the run ID, not on a loaded graph.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Regression test (W19, 2026-08-04): `run abandon` required a
                resolvable run, so the escape hatch did not work in the case
                that most needs it. The only exit left was `run start`, which
                orphans the run in `.agentic/runs/` forever. The abandonment is
                journalled, the pointer released, the run directory kept, and
                the parse error reported rather than the command refused.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph_path(tmp_path, run_id).write_text("{ not json", encoding="utf-8")

    payload = _invoke(
        capsys,
        ["run", "abandon", "--reason", "Graph is unrecoverable."],
    )

    assert payload["status"] == "ok"
    assert payload["run_id"] == run_id
    assert payload["outcome"] == "abandoned"
    assert "does not resolve to a valid graph" in payload["graph_error"]
    assert not current_run_path(tmp_path).exists()
    assert graph_path(tmp_path, run_id).is_file()
    journal = (
        tmp_path / ".agentic" / "runs" / run_id / "journal.jsonl"
    ).read_text(encoding="utf-8")
    abandoned = [
        json.loads(line)
        for line in journal.splitlines()
        if json.loads(line)["event"] == "run.abandoned"
    ]
    assert len(abandoned) == 1
    assert abandoned[0]["data"]["reason"] == "Graph is unrecoverable."


def test_abandoning_an_unknown_run_is_still_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Skipping the graph load does not accept a run that is not there.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    _start_feature(tmp_path, capsys)

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "--run",
                "feature-20260804T120000Z-deadbeef",
                "run",
                "abandon",
                "--reason",
                "No such run.",
                "--json",
            ]
        )

    assert raised.value.code == 1
    assert "RUN-ID-NOT-FOUND" in json.loads(capsys.readouterr().out)["error"]


# TESTS - W16: run start must not silently orphan a live run


def test_run_start_warns_that_an_incomplete_run_is_left_behind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Starting a second run names the run it displaced.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Nothing wedges - `run select` recovers full state - but only
                if the operator still has the ID, which is exactly what they
                lose by not being told.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    first = _start_feature(tmp_path, capsys)

    payload = _invoke(capsys, ["run", "start", "fix"])

    assert "warnings" in payload
    warning = payload["warnings"][0]
    assert first in warning
    assert f"aegis run select {first}" in warning
    assert "run abandon" in warning


def test_run_start_does_not_warn_when_no_live_run_is_displaced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      The warning fires only when real work is being orphaned.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    assert "warnings" not in _invoke(capsys, ["run", "start", "feature"])
    _invoke(capsys, ["run", "abandon", "--reason", "Not needed."])

    assert "warnings" not in _invoke(capsys, ["run", "start", "feature"])


# TESTS - W1: requirements can be created in every category


@pytest.mark.parametrize(
    ("category", "code"),
    [
        ("security", "SEC"),
        ("ux", "UX"),
        ("non_functional", "NFR"),
        ("data_privacy", "DATA"),
    ],
)
def test_stage_add_category_mints_a_matching_id_and_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    category: str,
    code: str,
) -> None:
    """
    @brief      `stage add --category` files a requirement outside functional.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @param[in]  category Requested requirement category.
    @param[in]  code Category code expected in the minted ID.
    @return     None.
    @details    The ID prefix and the `category` field must agree or the
                validator rejects the record, and the CLI owns every durable
                ID - so before this flag there was no legal way to file the
                seven non-functional categories the documentation asks for.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph = load_graph(tmp_path, run_id)
    graph.stage = "requirement"
    _save(tmp_path, graph)
    _invoke(capsys, ["stage", "prepare"])

    payload = _invoke(capsys, ["stage", "add", "--category", category])

    form = (tmp_path / payload["artifact"]).read_text(encoding="utf-8")
    assert f'category = "{category}"' in form
    identifier = _toml_value(form, "id")
    assert identifier.startswith(f"REQ-{code}-")


def test_stage_add_defaults_to_functional(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Omitting the flag preserves the pre-2.1.0 behaviour exactly.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph = load_graph(tmp_path, run_id)
    graph.stage = "requirement"
    _save(tmp_path, graph)
    _invoke(capsys, ["stage", "prepare"])

    payload = _invoke(capsys, ["stage", "add"])

    form = (tmp_path / payload["artifact"]).read_text(encoding="utf-8")
    assert 'category = "functional"' in form
    assert _toml_value(form, "id").startswith("REQ-FUNC-")


def test_unknown_category_is_rejected_by_the_parser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      An invented category never reaches the ID minter.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as raised:
        main(["stage", "add", "--category", "invented"])
    assert raised.value.code == 2


# TESTS - W4: config validate must not misdirect to a new run


def test_config_validate_points_at_the_selected_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `config validate` continues the live run instead of a new one.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Five documents order the agent to run `config validate` at the
                start of every skill, and the protocol trains it to obey `next`
                literally - so a hardcoded `aegis run start feature` told the
                agent to start a second run mid-run.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    _start_feature(tmp_path, capsys)

    payload = _invoke(capsys, ["config", "validate"])

    assert payload["stage"] == "intake"
    assert payload["next"] == "aegis stage apply"
    assert payload["schema_version"] == 3


def test_config_validate_falls_back_when_no_run_is_live(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      With no live run the bootstrap advice is unchanged.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    fresh = _invoke(capsys, ["config", "validate"])
    assert fresh["stage"] == "none"
    assert fresh["next"] == "aegis run start feature"

    _start_feature(tmp_path, capsys)
    _invoke(capsys, ["run", "abandon", "--reason", "Not needed."])
    after = _invoke(capsys, ["config", "show"])

    assert after["stage"] == "none"
    assert after["next"] == "aegis run start feature"


def test_config_validate_survives_an_unresolvable_run_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Config inspection never depends on run resolution succeeding.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph_path(tmp_path, run_id).write_text(
        json.dumps({"schema_version": 2}),
        encoding="utf-8",
    )

    payload = _invoke(capsys, ["config", "validate"])

    assert payload["status"] == "ok"
    assert payload["next"] == "aegis run start feature"


# TESTS - B19: approvals are attributable


def test_waive_add_records_the_given_approver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `--approver` reaches the durable waiver record.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    graph = init_graph(tmp_path, "feature", "Attribute one approval")

    payload = _invoke(
        capsys,
        [
            "waive",
            "add",
            "INV-6",
            "--reason",
            "Evidence arrives with the next step.",
            "--approver",
            "Grace Hopper <grace@example.invalid>",
        ],
    )

    assert payload["waiver"]["approver"] == "Grace Hopper <grace@example.invalid>"
    persisted = load_graph(tmp_path, graph.run_id)
    assert persisted.waivers[0].approver == "Grace Hopper <grace@example.invalid>"


def test_approver_defaults_to_the_git_identity_and_falls_back_to_human(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      Git supplies the default; "human" survives as the fallback.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @return     None.
    @details    A repository where git reports no identity must behave exactly
                as every pre-2.1.0 repository did, which is what keeps existing
                graphs and waivers loading unchanged.
    @exception  None
    """
    from aegis import cli

    values = {"user.name": "Ada Lovelace", "user.email": "ada@example.invalid"}
    monkeypatch.setattr(
        cli,
        "_git_config_value",
        lambda root, key: values.get(key, ""),
    )
    assert cli._resolve_approver(tmp_path, None) == (
        "Ada Lovelace <ada@example.invalid>"
    )
    assert cli._resolve_approver(tmp_path, "  Explicit  ") == "Explicit"

    values.clear()
    assert cli._resolve_approver(tmp_path, None) == "human"


def test_existing_graphs_recording_the_human_literal_still_load() -> None:
    """
    @brief      Widening the approver to a string keeps old graphs loadable.
    @return     None.
    @details    `approver` was a closed `Literal["human"]`, so every waiver
                written before 2.1.0 carries that exact value. Rejecting it
                would make the whole graph unloadable.
    @exception  None
    """
    document = _minimal_graph_document()
    document["waivers"] = [
        {
            "id": "WVR-1",
            "blocker_id": "INV-6",
            "reason": "Accepted.",
            "state_digests": {"invariant:INV-6": "abc"},
            "approver": "human",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]

    graph = Graph.from_dict(document)

    assert graph.waivers[0].approver == "human"


def test_an_empty_approver_is_still_rejected_on_load() -> None:
    """
    @brief      Widening the type does not make the field optional.
    @return     None.
    @exception  None
    """
    document = _minimal_graph_document()
    document["waivers"] = [
        {
            "id": "WVR-1",
            "blocker_id": "INV-6",
            "reason": "Accepted.",
            "state_digests": {},
            "approver": "   ",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]

    with pytest.raises(ValueError, match="approver must be a non-empty string"):
        Graph.from_dict(document)


def test_graphs_without_an_outcome_key_still_load() -> None:
    """
    @brief      The new `outcome` field is optional by absence.
    @return     None.
    @details    The graph schema is strict and closed, so a run written before
                2.1.0 - which has no `outcome` key at all - must still parse.
    @exception  None
    """
    graph = Graph.from_dict(_minimal_graph_document())

    assert graph.outcome == ""
    assert "outcome" not in graph.to_dict()


def test_an_unknown_outcome_is_rejected() -> None:
    """
    @brief      The closed schema stays closed over the new field's values.
    @return     None.
    @exception  None
    """
    document = _minimal_graph_document()
    document["outcome"] = "cancelled"

    with pytest.raises(ValueError, match="outcome must be empty or abandoned"):
        Graph.from_dict(document)


# TESTS - W17: a malformed requirement file must not disable its own escape hatch


def _write_malformed_requirement(tmp_path: Path) -> Path:
    """
    @brief      Drop one unloadable record into the requirement register.
    @param[in]  tmp_path Configured temporary repository.
    @return     Path of the malformed file.
    @exception  None
    """
    path = tmp_path / ".agentic" / "requirements" / "functional" / "bad.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("schema_version = 1\nid = 42\n", encoding="utf-8")
    return path


def test_waive_list_offers_a_blocker_for_an_unloadable_register(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `waive list` enumerates the parse failure instead of raising.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Regression test (W17, 2026-08-04): the tolerance added for this
                in Batch 2 covered `invariants.evaluate` only, while
                `collect_waiver_targets` reaches `audit_traceability` and
                `audit_coverage`, which load the register independently. One
                malformed file therefore still took down the single command
                that could produce the waiver for it - the same amplification
                as B3, where the fault disables the mechanism for recovering
                from it.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    _start_feature(tmp_path, capsys)
    bad = _write_malformed_requirement(tmp_path)

    payload = _invoke(capsys, ["waive", "list"])

    register = [
        blocker
        for blocker in payload["eligible_blockers"]
        if blocker["id"] == "requirement-register"
    ]
    assert len(register) == 1
    assert bad.name in register[0]["description"]


def test_verify_run_reports_an_unloadable_register_as_a_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      `verify run` degrades to a named finding instead of aborting.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    Impact and both requirement audits read the same register, so
                the parse error is carried through all three and surfaces once.
                Neither audit may look like it passed, which is why the finding
                appears in both lists.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    _start_feature(tmp_path, capsys)
    bad = _write_malformed_requirement(tmp_path)

    with pytest.raises(SystemExit) as raised:
        main(["verify", "run", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert raised.value.code == 1
    for audit in ("traceability", "coverage"):
        assert payload["verification"][audit][0]["code"] == "REQ-REGISTER-UNREADABLE"
        assert bad.name in payload["verification"][audit][0]["message"]


# TESTS - B20: a stale pointer must not block read-only commands


def test_requirement_list_survives_an_unresolvable_run_pointer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Reading the durable register does not depend on a run.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    A schema-2 run left behind by 1.4.1 wedged `requirement list`,
                a pure read of a store that has nothing to do with runs.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph_path(tmp_path, run_id).write_text(
        json.dumps({"schema_version": 2}),
        encoding="utf-8",
    )

    payload = _invoke(capsys, ["requirement", "list"])

    assert payload["status"] == "ok"
    assert payload["stage"] == "none"
    assert payload["requirements"] == []
    assert payload["next"] == "aegis run list"


def test_mutating_commands_still_require_a_resolvable_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Read-only tolerance is not extended to state mutation.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    graph_path(tmp_path, run_id).write_text(
        json.dumps({"schema_version": 2}),
        encoding="utf-8",
    )

    for argv in (["stage", "prepare"], ["stage", "apply"], ["stage", "close"]):
        with pytest.raises(SystemExit) as raised:
            main([*argv, "--json"])
        assert raised.value.code == 1
        assert "RUN-POINTER-STALE" in json.loads(capsys.readouterr().out)["error"]


def test_stale_pointer_names_the_cause_and_offers_a_working_next_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      The stale-pointer message stops being a dead end.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    It used to say the graph was "missing or invalid" when the file
                plainly existed, and to suggest `--run <existing-run-id>` when
                the stale ID *was* the existing ID.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    stale = _start_feature(tmp_path, capsys)
    healthy = _start_feature(tmp_path, capsys)
    current_run_path(tmp_path).write_text(
        f"{stale}\n",
        encoding="utf-8",
        newline="\n",
    )
    graph_path(tmp_path, stale).write_text(
        json.dumps({"schema_version": 2}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit):
        main(["stage", "prepare", "--json"])
    error = json.loads(capsys.readouterr().out)["error"]

    assert "schema_version 3" in error
    assert f"aegis run select {healthy}" in error
    # The unloadable run is never offered back as its own remedy.
    assert f"aegis run select {stale}" not in error


# TESTS - B21/B22: the verification output contract


def test_verify_status_exit_code_matches_the_summary_it_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      A failed verification is never reported as `status: ok`.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    An agent polling `verify status` to decide whether it may
                proceed used to get exit 0 while the summary it printed said a
                gate had failed.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)

    with pytest.raises(SystemExit) as ran:
        main(["verify", "run", "--json"])
    run_payload = json.loads(capsys.readouterr().out)
    assert ran.value.code == 1
    assert run_payload["verification"]["status"] == "failed"

    with pytest.raises(SystemExit) as reported:
        main(["verify", "status", "--json"])
    status_payload = json.loads(capsys.readouterr().out)

    assert reported.value.code == 1
    assert status_payload["status"] == "failed"
    assert status_payload["verification"]["status"] == "failed"
    summary = json.loads(
        (
            tmp_path / ".agentic" / "runs" / run_id / "validation-summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["status"] == "failed"


def test_verify_status_on_a_pre_2_1_0_summary_is_reported_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      A summary with no recorded verdict is not guessed at.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    run_id = _start_feature(tmp_path, capsys)
    with pytest.raises(SystemExit):
        main(["verify", "run", "--json"])
    capsys.readouterr()
    path = tmp_path / ".agentic" / "runs" / run_id / "validation-summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    del summary["status"]
    path.write_text(json.dumps(summary), encoding="utf-8")

    main(["verify", "status", "--json"])

    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_non_json_output_indents_nested_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      The human surface stops emitting one unwrapped JSON line.
    @param[in]  tmp_path Configured temporary repository.
    @param[in]  monkeypatch Pytest environment fixture.
    @param[in]  capsys Pytest capture fixture.
    @return     None.
    @details    `verify run` without `--json` printed a single ~4 KB line,
                which made the human surface strictly worse than `--json`.
                Scalars keep their exact one-line shape.
    @exception  None
    """
    monkeypatch.chdir(tmp_path)
    _start_feature(tmp_path, capsys)
    with pytest.raises(SystemExit):
        main(["verify", "run"])
    lines = capsys.readouterr().out.splitlines()

    assert lines[0] == "status: failed"
    assert any(line == "verification:" for line in lines)
    assert all(len(line) < 400 for line in lines)
    # Nested content is indented under its key rather than inlined after it.
    assert any(line.startswith('    "run_id"') for line in lines)


# LOCAL HELPERS


def _save(repo_root: Path, graph: Graph) -> None:
    """
    @brief      Persist a directly manipulated graph.
    @param[in]  repo_root Repository root.
    @param[in]  graph Graph to publish.
    @return     None.
    @exception  None
    """
    save_graph(repo_root, graph)


def _toml_value(text: str, key: str) -> str:
    """
    @brief      Read one simple quoted TOML value from a generated form.
    @param[in]  text Complete form text.
    @param[in]  key Key whose value is wanted.
    @return     Decoded string value.
    @exception  StopIteration If the key is absent.
    """
    prefix = f"{key} = "
    line = next(
        item for item in text.splitlines() if item.startswith(prefix)
    )
    return json.loads(line[len(prefix):])


def _minimal_graph_document() -> dict:
    """
    @brief      Build the smallest valid schema-3 graph mapping.
    @return     Mapping accepted by :meth:`Graph.from_dict`.
    @exception  None
    """
    return {
        "run_id": "feature-2026-01-01T000000Z-0a1b2c3d",
        "stage": "intake",
        "intent": {
            "id": "I-1",
            "kind": "feature",
            "statement": "Do the thing",
            "scope_hint": [],
            "status": "draft",
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        "schema_version": 3,
        "access_mode": "standard",
        "complete": False,
        "alignment": None,
        "design": None,
        "spec_items": [],
        "checks": [],
        "evidence": [],
        "change_units": [],
        "decisions": [],
        "stage_records": {},
    }


# END OF FILE
