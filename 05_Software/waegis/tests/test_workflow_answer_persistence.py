#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_workflow_answer_persistence.py
@brief Durable workflow-answer persistence, reconstruction, and manifest
       compatibility.
@details Covers the deployment finding that an adopted repository stored an
         empty ``configuration``, which left a later RepoWise-only
         configuration with nothing to resolve source roots from. The fixtures
         are synthetic: a payload copy plus a generated workflow.toml, with
         deliberately unconventional roots and no code files, so the repository
         analysis can propose nothing and the stored/reconstructed answers are
         the only thing that can carry the configuration.
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

from waegis.commands.configure import CONFIG_KEYS, run_configure, stored_answers
from waegis.commands.doctor import run_doctor
from waegis.commands.new import (
    NO_ACTIVE_RUN_MARKER,
    WORKFLOW_TOML_RELATIVE_PATH,
    amend_manifest_generated,
    _wrapper_invocation,
)
from waegis.commands.repair import run_repair
from waegis.commands.upgrade import (
    _build_new_manifest,
    build_upgrade_plan,
    resolve_upgrade_decisions,
)
from waegis.payload.copier import ConflictDecision, copy_payload
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    load_manifest,
    read_manifest,
    write_manifest,
)
from waegis.repo.workflow_toml import (
    ALL_STAGES,
    CONDITIONAL_ANSWER_KEYS,
    GENERATOR_ANSWER_KEYS,
    OTHER_LANGUAGE_FIELD_SPECS,
    OWNED_ANSWER_LOCATIONS,
    WORKFLOW_FIELD_SPECS,
    derive_answers_from_workflow,
    generate_workflow_toml,
    normalize_stored_answers,
)

from _fake_command_runner import FakeCommandRunner, failing_result, ok_result

# CONSTANTS

# @brief A configuration no repository analysis could ever propose: roots named
#        outside every convention, and policy switched away from every default.
#        Anything that survives a round trip therefore came from the stored or
#        reconstructed answers, never from a lucky proposal.
_DISTINCTIVE_ANSWERS: dict[str, object] = {
    "source_roots": ["engine"],
    "test_roots": ["checks"],
    "language": "python",
    "gate_build_cmds": [],
    "gate_typecheck_cmds": [],
    "gate_lint_cmds": [],
    "gate_test_cmds": [["harness", "--all"]],
    "gate_security_cmds": [],
    "alignment_enabled": False,
    "coverage_mode": "enforce",
    "coverage_roots": ["engine"],
    "coverage_exclude": ["engine/generated/**"],
    "stage_form_retention": "versioned",
    "check_execution": "managed",
    "gate_test_mode": "enforce",
    "secrets_mode": "enforce",
    "secret_patterns": ["token-[0-9]+"],
    "scope_mode": "advisory",
    "scope_allowed_roots": ["engine"],
    "source_changes_mode": "blocked",
}

# @brief The three keys the manifest's configuration block is made of.
_CONFIGURATION_KEYS = {"answers", "generator_version", "generated_files"}


# LOCAL HELPERS


def _smoke_ok_runner(repo: Path) -> FakeCommandRunner:
    """@brief A fake runner whose scripted wrapper calls make smoke pass."""
    return FakeCommandRunner(
        {
            _wrapper_invocation(repo, "--help"): ok_result(),
            _wrapper_invocation(repo, "run", "status", "--json"): failing_result(
                exit_code=2, stderr=NO_ACTIVE_RUN_MARKER
            ),
        }
    )


def _write_answers(path: Path, data: dict[str, object]) -> Path:
    """@brief Write one JSON answers file and return its path."""
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _install_generated(repo: Path, *, persist: bool) -> Path:
    """
    @brief      Install the payload and generate workflow.toml from
                :data:`_DISTINCTIVE_ANSWERS`.
    @param[in]  repo Repository root to create.
    @param[in]  persist When false, amend the manifest the way adoption used to
                — moving the generated file across without recording a single
                answer, which is the historical state under repair.
    @return     The payload root used.
    @exception  OSError If the fixture cannot be written.
    """
    payload = locate_payload()
    copy_payload(payload, repo, mode="adopt")
    # Deliberately not code files: with nothing to rank, the analysis proposes
    # no roots at all, exactly as it did on the repository that surfaced this.
    for root in ("engine", "checks"):
        (repo / root).mkdir(parents=True, exist_ok=True)
        (repo / root / "notes.txt").write_text("fixture\n", encoding="utf-8")
    base = (payload / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    generated = generate_workflow_toml(base, **_DISTINCTIVE_ANSWERS)  # type: ignore[arg-type]
    workflow = repo / WORKFLOW_TOML_RELATIVE_PATH
    workflow.write_text(generated.text, encoding="utf-8", newline="")
    amend_manifest_generated(
        repo,
        answers=normalize_stored_answers(_DISTINCTIVE_ANSWERS) if persist else None,
    )
    return payload


def _configure_repowise_only(repo: Path, payload: Path, tmp_path: Path) -> dict[str, object]:
    """
    @brief      Run a non-interactive configure whose answers file names only
                RepoWise keys — no workflow field restated.
    @param[in]  repo Repository root.
    @param[in]  payload Validated payload root.
    @param[in]  tmp_path Directory for the answers file.
    @return     The parsed command envelope.
    @exception  AssertionError Never raised here; callers assert on the result.
    """
    answers = _write_answers(tmp_path / "repowise-only.json", {"repowise_source": "disabled"})
    stream = io.StringIO()
    run_configure(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
        runner=_smoke_ok_runner(repo),
    )
    return json.loads(stream.getvalue())


# TESTS


def test_every_generator_answer_owns_exactly_one_workflow_location() -> None:
    """
    @brief      The allowlist, the spec tables, and the file-location table are
                one source: a field added to the generator cannot be silently
                left out of what gets persisted or reconstructed.
    @return     None
    @exception  AssertionError If the three tables disagree.
    """
    spec_keys = {spec.key for spec in (*WORKFLOW_FIELD_SPECS, *OTHER_LANGUAGE_FIELD_SPECS)}
    assert spec_keys == GENERATOR_ANSWER_KEYS == CONFIG_KEYS
    assert set(OWNED_ANSWER_LOCATIONS) == GENERATOR_ANSWER_KEYS
    locations = list(OWNED_ANSWER_LOCATIONS.values())
    assert len(set(locations)) == len(locations)  # no two answers own one key
    assert CONDITIONAL_ANSWER_KEYS <= GENERATOR_ANSWER_KEYS


def test_reconstructed_answers_regenerate_the_same_workflow_bytes() -> None:
    """
    @brief      A generated workflow.toml is a complete record of its answers:
                reading it back and regenerating reproduces it byte for byte,
                including the two conditional policy targets.
    @return     None
    @exception  AssertionError If a value or a byte differs.
    """
    payload = locate_payload()
    base = (payload / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    answers = {
        **_DISTINCTIVE_ANSWERS,
        "baseline_guard_mode": "enforce",
        "baseline_minimum_completion_level": "characterized",
        "write_access_mode": "stage_restricted",
        "write_access_stages": {
            stage: (["engine/**"] if stage == "implementation" else []) for stage in ALL_STAGES
        },
    }
    generated = generate_workflow_toml(base, **answers)  # type: ignore[arg-type]

    derived = derive_answers_from_workflow(generated.text)
    assert derived["source_roots"] == ["engine"]
    assert derived["secret_patterns"] == ["token-[0-9]+"]
    assert derived["alignment_enabled"] is False
    assert derived["baseline_minimum_completion_level"] == "characterized"
    assert derived["write_access_stages"]["implementation"] == ["engine/**"]
    # Preset languages derive their extensions, so the "other" answers are not
    # part of what an interview would have collected.
    assert "source_extensions" not in derived
    assert derived.keys() <= GENERATOR_ANSWER_KEYS

    assert generate_workflow_toml(generated.text, **derived).text == generated.text


def test_reconstruction_ignores_a_file_that_is_not_a_valid_workflow() -> None:
    """
    @brief      Reconstruction is a recovery, not a parser: anything that is not
                a valid schema-version-3 workflow yields no answers rather than
                a partial guess.
    @return     None
    @exception  AssertionError If invalid input produced answers.
    """
    assert derive_answers_from_workflow("this is not toml =") == {}
    assert derive_answers_from_workflow('[source]\nroots = ["src"]\n') == {}


def test_both_wizards_normalize_to_one_stored_shape() -> None:
    """
    @brief      New and adopt reduce their own answer sets to an identical
                durable shape: wizard-only answers (branch, conflicts, git
                identity), RepoWise runtime data, and unasked ``None``
                placeholders never become configuration.
    @return     None
    @exception  AssertionError If the two shapes differ or a stray key survived.
    """
    workflow_answers = {
        **_DISTINCTIVE_ANSWERS,
        "source_extensions": None,
        "test_file_patterns": None,
    }
    from_new = normalize_stored_answers(
        {**workflow_answers, "clone_url": "", "git_user_name": "Fixture", "git_user_email": "f@e"}
    )
    from_adopt = normalize_stored_answers(
        {
            **workflow_answers,
            "adoption_branch": "agentic-adoption",
            "adoption_conflicts": {"CLAUDE.md": "keep-local"},
            "repowise_source": "external",
            "repowise_external_command": ["repowise"],
        }
    )
    assert from_new == from_adopt
    assert list(from_new) == sorted(from_new)
    assert set(from_new) <= GENERATOR_ANSWER_KEYS
    assert "source_extensions" not in from_new  # unasked placeholder dropped
    assert from_new["source_roots"] == ["engine"]


def test_repowise_only_configure_needs_no_stored_answers_after_adoption(tmp_path: Path) -> None:
    """
    @brief      With the answers persisted, a RepoWise-only configuration
                changes no workflow field and rewrites no workflow byte.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If a field was restated or the file was rewritten.
    """
    repo = tmp_path / "repo"
    payload = _install_generated(repo, persist=True)
    before = (repo / WORKFLOW_TOML_RELATIVE_PATH).read_bytes()

    document = _configure_repowise_only(repo, payload, tmp_path)

    assert document["status"] == "ok"
    assert document["exit_code"] == 0
    assert document["plan"]["changes"] == []
    assert document["plan"]["workflow_content_changed"] is False
    assert document["result"]["configured"] is True
    assert (repo / WORKFLOW_TOML_RELATIVE_PATH).read_bytes() == before


def test_repowise_only_configure_reconstructs_an_empty_configuration(tmp_path: Path) -> None:
    """
    @brief      The reported field failure: an install whose manifest records no
                answers is configured from the workflow file it already has —
                the run succeeds, restates nothing, leaves the workflow bytes
                untouched, and heals the manifest on the way out.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the run failed, drifted, or did not self-heal.
    """
    repo = tmp_path / "repo"
    payload = _install_generated(repo, persist=False)
    before = (repo / WORKFLOW_TOML_RELATIVE_PATH).read_bytes()
    assert read_manifest(repo).configuration == {}  # the historical state

    document = _configure_repowise_only(repo, payload, tmp_path)

    assert document["status"] == "ok", document["messages"]
    assert document["exit_code"] == 0
    assert document["plan"]["changes"] == []
    assert document["plan"]["workflow_content_changed"] is False
    assert (repo / WORKFLOW_TOML_RELATIVE_PATH).read_bytes() == before

    configuration = read_manifest(repo).configuration
    assert set(configuration) == _CONFIGURATION_KEYS
    answers = configuration["answers"]
    assert set(answers) == {spec.key for spec in WORKFLOW_FIELD_SPECS}
    for key, expected in normalize_stored_answers(_DISTINCTIVE_ANSWERS).items():
        assert answers[key] == expected, key
    assert stored_answers(configuration) == answers


def test_historical_and_repaired_manifests_stay_interchangeable(tmp_path: Path) -> None:
    """
    @brief      Manifest compatibility: a manifest written by the previous
                WAEGIS — same schema, populated configuration, an older
                generator version — round-trips byte-identically and is accepted
                by doctor and repair, as is a manifest repaired by this one.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If either manifest was rejected or rewritten.
    """
    repo = tmp_path / "repo"
    payload = _install_generated(repo, persist=True)
    manifest_path = repo / MANIFEST_RELATIVE_PATH

    # Restate the stored block the way WAEGIS 1.0.0 wrote it, then prove a
    # read/write cycle does not touch a byte of it.
    historical = json.loads(manifest_path.read_text(encoding="utf-8"))
    historical["configuration"]["generator_version"] = "1.0.0"
    manifest_path.write_text(
        json.dumps(historical, indent=2) + "\n", encoding="utf-8", newline=""
    )
    historical_bytes = manifest_path.read_bytes()

    write_manifest(repo, read_manifest(repo))
    assert manifest_path.read_bytes() == historical_bytes
    assert stored_answers(read_manifest(repo).configuration)["source_roots"] == ["engine"]

    for label, expected_repair in (("historical", 0), ("repaired", 0)):
        stream = io.StringIO()
        run_doctor(
            repo,
            stream=stream,
            as_json=True,
            runner=_smoke_ok_runner(repo),
            home=tmp_path / f"home-{label}",
        )
        report = json.loads(stream.getvalue())["result"]
        assert all(
            finding["status"] != "fail" for finding in report["groups"]["manifest"]
        ), f"{label}: doctor rejected the manifest\n{stream.getvalue()}"

        stream = io.StringIO()
        assert (
            run_repair(
                repo,
                stream=stream,
                answers_path=_write_answers(tmp_path / f"repair-{label}.json", {"run_smoke": False}),
                non_interactive=True,
                yes=True,
                as_json=True,
                payload=payload,
                runner=_smoke_ok_runner(repo),
            )
            == expected_repair
        ), f"{label}: {stream.getvalue()}"
        assert stored_answers(read_manifest(repo).configuration)["source_roots"] == ["engine"]

        # Upgrade carries the stored configuration across unchanged, so neither
        # manifest loses its answers by being upgraded.
        plan = build_upgrade_plan(
            repo, new_payload_root=payload, load_result=load_manifest(repo)
        )
        assert plan.configuration == read_manifest(repo).configuration, label
        decisions, _outcomes = resolve_upgrade_decisions(
            plan, lambda _conflict: ConflictDecision.KEEP_LOCAL
        )
        upgraded = _build_new_manifest(plan, decisions)
        assert upgraded.configuration == read_manifest(repo).configuration, label

        # Second pass runs against the manifest this WAEGIS just wrote.
        _configure_repowise_only(repo, payload, tmp_path)


# END OF FILE
