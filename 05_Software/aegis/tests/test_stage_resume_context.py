#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_stage_resume_context.py
@brief   Verify bounded self-contained Stage resume-context reads.
@details Covers PR-WORKFLOW-008, PR-SNAPSHOT, PR-MODEL, PR-CONFIG,
         PR-REQ, PR-COMP, PR-TRACE, PR-HOST, and AC-STAGE-001.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.test_project_knowledge_trace import requirement_data
from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def _project_bytes(repo: Path) -> dict[str, bytes]:
    """@return Exact project-owned and payload bytes below `.agentic`."""
    root = repo / ".agentic"
    return {
        path.relative_to(repo).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _collection(items: list[Any]) -> list[Any]:
    """@return One expected complete compact collection shape."""
    return items


def _create_linked_graph(repo: Path) -> tuple[str, str, str]:
    """@return Publicly create one Requirement, Specification, and Component."""
    source = repo / "src" / "retry.py"
    source.parent.mkdir()
    source.write_text("def retry():\n    return True\n", encoding="utf-8")
    test = repo / ".agentic" / "tests" / "test_retry.py"
    test.write_text("def test_retry_history():\n    assert True\n", encoding="utf-8")
    exit_code, requirement = invoke(repo, "requirement-create", requirement_data())
    assert exit_code == 0, requirement
    requirement_id = requirement["data"]["id"]
    specification_data = {
        "title": "Retry history format",
        "status": "active",
        "purpose": "Define the retained attempt list.",
        "contract": "Attempts remain append ordered.",
        "inputs_outputs": "Attempt input; durable history output.",
        "rules": ["Never replace an earlier attempt."],
        "error_behavior": "Malformed history remains visible.",
        "examples": "failed, then passed",
        "open_details": "None",
    }
    exit_code, specified = invoke(
        repo,
        "specification-set",
        specification_data,
        "--requirement",
        requirement_id,
    )
    assert exit_code == 0, specified
    component_data = {
        "name": "Retry recorder",
        "status": "active",
        "files": ["src/retry.py"],
        "file_roles": [{"path": "src/retry.py", "role": "Persist retry outcomes."}],
        "requirement_links": [
            {
                "requirement_id": requirement_id,
                "behavior": "Retains ordered attempts.",
            }
        ],
        "test_links": [
            {
                "path": ".agentic/tests/test_retry.py",
                "selector": "test_retry_history",
                "description": "Verifies durable retry history.",
            }
        ],
        "purpose_boundary": "Own retry evidence; not process execution.",
        "interfaces": "retry()",
        "dependencies": [],
        "known_gaps": [],
        "drift_review": {
            "behavior": "yes",
            "interfaces": "yes",
            "dependencies": "yes",
            "files": "yes",
        },
    }
    exit_code, component = invoke(repo, "component-create", component_data)
    assert exit_code == 0, component
    specification_path = f".agentic/requirements/SPEC-{requirement_id[4:]}.md"
    return requirement_id, component["data"]["id"], specification_path


def test_selected_stage_show_assembles_relevant_resume_graph_and_absent_rules(
    tmp_path: Path,
) -> None:
    """@brief Selected Stage read contains the durable Run and relevant graph."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    requirement_id, component_id, specification_path = _create_linked_graph(repo)

    exit_code, response = invoke(repo, "stage-show")

    assert exit_code == 0, response
    assert response["operation"] == "stage.show"
    assert response["stage"] == "intake"
    assert response["revision"].startswith("sha256:")
    data = response["data"]
    assert data["schema"] == "aegis.stage.resume_context"
    assert data["schema_version"] == 1
    assert data["target"] == {
        "run_id": created["run_id"],
        "stage": "intake",
        "current_stage": "intake",
        "selected_run": True,
        "current_stage_target": True,
    }
    assert data["run_summary"]["scope"] == "Pending Alignment."
    assert data["stage_state"]["revision"] == response["revision"]
    assert data["instruction"]
    assert data["sections"]
    knowledge = data["project_knowledge"]
    assert [item["id"] for item in knowledge["requirements"]] == [requirement_id]
    assert knowledge["requirements"][0]["specification"]["path"] == (
        specification_path
    )
    assert [item["id"] for item in knowledge["components"]] == [component_id]
    assert knowledge["affected_files"] == _collection(["src/retry.py"])
    assert knowledge["tests"][0]["path"] == (".agentic/tests/test_retry.py")
    assert data["project_rules"]["state"] == "absent"
    assert data["project_rules"]["content"] == ""
    assert data["tool_context"]["test_roots"] == [".agentic/tests"]
    assert data["tool_context"]["risk"]["attention_threshold"] == "medium"
    assert data["tool_context"]["risk"]["protected_scope_patterns"] == (_collection([]))
    assert response["truncated"] is False


def test_stage_resume_context_returns_direct_structured_rows(tmp_path: Path) -> None:
    """@brief PR-PROTO-005 rows remain inspectable without a second JSON decode."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    assert invoke(
        repo,
        "evidence-add",
        {
            "kind": "manual",
            "actor": "agent",
            "procedure": "inspect structured resume rows",
            "expected": "direct objects",
            "actual": "direct objects",
        },
    )[0] == 0
    assert invoke(
        repo,
        "scope-revise",
        {
            "before": "Inspect encoded resume rows.",
            "after": "Inspect direct structured resume rows.",
            "actor": "agent",
            "reason": "Keep machine values directly invokable.",
            "affected_work": [],
        },
    )[0] == 0
    config_path = repo / ".agentic" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "\n[validation.audits.rows]\n"
        + 'command = ["audit-tool", "--mode", "inspect"]\n'
        + 'working_directory = "."\n'
        + "timeout_seconds = 5\n",
        encoding="utf-8",
    )

    intake_exit, intake = invoke(repo, "stage-show")
    validation_exit, validation = invoke(
        repo, "stage-show", None, "--stage", "validation"
    )

    assert intake_exit == validation_exit == 0
    data = intake["data"]
    assert data["run_summary"]["stages"][0]["name"] == "intake"
    assert data["run_summary"]["scope_changes"][0]["actor"] == "agent"
    assert data["evidence"][0]["procedure"] == "inspect structured resume rows"
    assert data["stage_state"]["events"][0]["event"] == "stage_started"
    attribution = data["run_summary"]["change_attribution"]
    assert all(isinstance(rows, list) for rows in attribution.values())
    command = validation["data"]["tool_context"]["commands"][0]
    assert command["name"] == "rows"
    assert command["command"][0].startswith("audit-")


def test_stage_resume_context_compacts_complete_values_and_accounts_truncation(
    tmp_path: Path,
) -> None:
    """@brief PR-MODEL-003/005 accounting appears only for actual omission."""
    repo = installed_repository(tmp_path)
    create_run(repo, profile="short")

    complete_exit, complete = invoke(repo, "stage-show")

    assert complete_exit == 0, complete
    data = complete["data"]
    assert complete["truncated"] is False
    assert isinstance(data["instruction"], str)
    assert isinstance(data["sections"], list)
    assert isinstance(data["run_summary"]["scope"], str)
    assert isinstance(data["run_summary"]["stages"], list)
    assert isinstance(data["project_knowledge"]["requirements"], list)
    assert isinstance(data["tool_context"]["commands"], list)
    assert len(json.dumps(data, separators=(",", ":"), ensure_ascii=False)) < 9000

    rules_text = "Keep evidence locally reviewable.\n" * 300
    rules_path = repo / ".agentic" / "rules.md"
    rules_path.write_text(rules_text, encoding="utf-8")
    for index in range(10):
        requirement = requirement_data()
        requirement["title"] = f"Bounded context {index:02d}"
        requirement["behavior"] = f"Context item {index:02d} remains deterministic."
        assert invoke(repo, "requirement-create", requirement)[0] == 0

    truncated_exit, truncated = invoke(repo, "stage-show")

    assert truncated_exit == 0, truncated
    truncated_data = truncated["data"]
    rules = truncated_data["project_rules"]["content"]
    assert rules["truncated"] is True
    assert rules["total_characters"] == len(rules_text)
    assert rules["returned_characters"] == len(rules["content"])
    assert rules["omitted_characters"] == (
        rules["total_characters"] - rules["returned_characters"]
    )
    requirements = truncated_data["project_knowledge"]["requirements"]
    assert requirements["truncated"] is True
    assert requirements["total_count"] == 10
    assert requirements["returned_count"] == 8
    assert requirements["omitted_count"] == 2
    assert len(requirements["items"]) == requirements["returned_count"]
    assert truncated["truncated"] is True
    assert truncated["details_ref"].endswith("/01-intake.md")


def test_stage_show_does_not_duplicate_collections(tmp_path: Path) -> None:
    """@brief Stage collections occur once without losing bounded accounting."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    attachment = repo / "resume-context.log"
    attachment.write_text("bounded context evidence\n", encoding="utf-8")
    operations = (
        (
            "evidence-add",
            {
                "kind": "manual",
                "actor": "agent",
                "procedure": "inspect stage context",
                "expected": "one bounded collection",
                "actual": "one bounded collection",
            },
            (),
        ),
        (
            "finding-add",
            {
                "severity": "warning",
                "observation": "Resume context was duplicated.",
                "consequence": "Model context was wasted.",
            },
            (),
        ),
        (
            "finding-waive",
            {"actor": "agent", "reason": "Regression coverage added."},
            ("--finding", "F1"),
        ),
        (
            "decision-add",
            {
                "value": "approved",
                "actor": "agent",
                "target": "resume_context_shape",
                "reason": "Keep each Stage collection once.",
            },
            (),
        ),
        (
            "attachment-add",
            {
                "source": str(attachment),
                "purpose": "resume context evidence",
                "content_type": "text/plain",
            },
            (),
        ),
    )
    for operation, data, arguments in operations:
        exit_code, response = invoke(repo, operation, data, *arguments)
        assert exit_code == 0, response

    exit_code, response = invoke(repo, "stage-show")

    assert exit_code == 0, response
    data = response["data"]
    stage_state = data["stage_state"]
    collection_names = {"sections", "evidence", "findings", "decisions", "escapes"}
    assert collection_names.isdisjoint(stage_state)
    assert set(stage_state) == {
        "status",
        "revision",
        "started_at",
        "updated_at",
        "completed_at",
        "attachments",
        "events",
        "work_applied",
    }
    for name in collection_names:
        collection = data[name]
        assert isinstance(collection, list)
        assert collection
        assert all(isinstance(item, dict) for item in collection)
    for name in ("attachments", "events"):
        collection = stage_state[name]
        assert isinstance(collection, list)
        assert collection
        assert all(isinstance(item, dict) for item in collection)
    assert "guidance" in data
    assert "guidance" not in stage_state


def test_explicit_historical_stage_show_preserves_selection_and_all_bytes(
    tmp_path: Path,
) -> None:
    """@brief Explicit nonselected Run/Stage inspection is strictly read-only."""
    repo = installed_repository(tmp_path)
    historical = create_run(repo)
    selected = create_run(repo, profile="short")
    pointer = repo / ".agentic" / "runs" / "context.toml"
    before = _project_bytes(repo)

    exit_code, response = invoke(
        repo,
        "stage-show",
        None,
        "--run",
        historical["run_id"],
        "--stage",
        "requirement",
    )

    assert exit_code == 0, response
    assert response["run_id"] == historical["run_id"]
    assert response["stage"] == "requirement"
    assert response["data"]["target"] == {
        "run_id": historical["run_id"],
        "stage": "requirement",
        "current_stage": "intake",
        "selected_run": False,
        "current_stage_target": False,
    }
    assert selected["run_id"] in pointer.read_text(encoding="utf-8")
    assert _project_bytes(repo) == before


def test_historical_run_expands_component_linked_by_current_requirement(
    tmp_path: Path,
) -> None:
    """@brief Relevant graph expansion is not limited to Run-owned Components."""
    repo = installed_repository(tmp_path)
    historical = create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    (repo / ".agentic" / "tests" / "test_retry.py").write_text(
        "pass\n", encoding="utf-8"
    )
    requirement = invoke(repo, "requirement-create", requirement_data())[1]["data"][
        "id"
    ]
    selected = create_run(repo)
    component_data = {
        "name": "Existing retry recorder",
        "status": "active",
        "files": ["src/retry.py"],
        "file_roles": [{"path": "src/retry.py", "role": "Persist retries."}],
        "requirement_links": [
            {"requirement_id": requirement, "behavior": "Retains retries."}
        ],
        "test_links": [
            {
                "path": ".agentic/tests/test_retry.py",
                "selector": "test_retry_history",
                "description": "Covers retry history.",
            }
        ],
        "purpose_boundary": "Own retry state.",
        "interfaces": "retry()",
        "dependencies": [],
        "known_gaps": [],
        "drift_review": {
            "behavior": "yes",
            "interfaces": "yes",
            "dependencies": "yes",
            "files": "yes",
        },
    }
    component = invoke(repo, "component-create", component_data)[1]["data"]["id"]

    exit_code, response = invoke(
        repo, "stage-show", None, "--run", historical["run_id"]
    )

    assert exit_code == 0, response
    items = response["data"]["project_knowledge"]["components"]
    assert [item["id"] for item in items] == [component]
    assert response["data"]["target"]["selected_run"] is False
    assert selected["run_id"] in (
        repo / ".agentic" / "runs" / "context.toml"
    ).read_text(encoding="utf-8")


def test_present_rules_are_bounded_and_invalid_rules_become_findings(
    tmp_path: Path,
) -> None:
    """@brief Optional rules are explicit, bounded, and never silently decoded."""
    repo = installed_repository(tmp_path)
    create_run(repo, profile="short")
    rules_path = repo / ".agentic" / "rules.md"
    rules_path.write_text("Keep evidence local.\n" * 500, encoding="utf-8")

    exit_code, present = invoke(repo, "stage-show")

    assert exit_code == 0, present
    rules = present["data"]["project_rules"]
    assert rules["state"] == "present"
    assert rules["content"]["truncated"] is True
    assert rules["content"]["omitted_characters"] > 0
    assert present["truncated"] is True
    assert present["details_ref"].endswith("/01-intake.md")

    rules_path.write_bytes("Règle locale.\r\n".encode("cp1252"))
    exit_code, legacy = invoke(repo, "stage-show")
    assert exit_code == 0, legacy
    assert legacy["data"]["project_rules"]["content"] == ("Règle locale.\n")

    rules_path.write_bytes(b"\xff\xfe\x00")
    exit_code, unreadable = invoke(repo, "stage-show")

    assert exit_code == 0, unreadable
    assert unreadable["data"]["project_rules"]["state"] == "unreadable"
    assert "resume_reference_unreadable" in {
        finding["code"] for finding in unreadable["findings"]
    }


def test_stage_tool_context_filters_commands_and_redacts_secret_arguments(
    tmp_path: Path,
) -> None:
    """@brief Stage context exposes applicable commands without secret values."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    config_path = repo / ".agentic" / "config.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + "\n[validation.audits.private]\n"
        + 'command = ["audit-tool", "--token", "secret-value", "--mode", "check"]\n'
        + 'working_directory = "."\n'
        + "timeout_seconds = 5\n",
        encoding="utf-8",
    )

    intake_exit, intake = invoke(repo, "stage-show")
    validation_exit, validation = invoke(
        repo, "stage-show", None, "--stage", "validation"
    )

    assert intake_exit == validation_exit == 0
    assert intake["data"]["tool_context"]["commands"] == []
    commands = validation["data"]["tool_context"]["commands"]
    assert commands[0]["name"] == "private"
    assert commands[0]["command"] == [
        "audit-tool",
        "--token",
        "<redacted>",
        "--mode",
        "check",
    ]
    assert "secret-value" not in json.dumps(validation)


def test_missing_references_remain_visible_as_nonfabricated_context_findings(
    tmp_path: Path,
) -> None:
    """@brief Missing Run graph references remain explicit unavailable entries."""
    repo = installed_repository(tmp_path)
    created = create_run(repo)
    requirement_id, _, _ = _create_linked_graph(repo)
    requirement_path = repo / ".agentic" / "requirements" / f"{requirement_id}.toml"
    requirement_text = requirement_path.read_text(encoding="utf-8")
    requirement_path.write_text(
        requirement_text.replace(
            f'specification = ".agentic/requirements/SPEC-{requirement_id[4:]}.md"',
            'specification = ".agentic/requirements/SPEC-'
            '00000000000000000000000000000000.md"',
        ),
        encoding="utf-8",
    )
    run_path = repo / ".agentic" / "runs" / created["run_id"] / "run.md"
    run_text = run_path.read_text(encoding="utf-8")
    missing_requirement = "REQ-ffffffffffffffffffffffffffffffff"
    missing_component = "COMP-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
    run_text = run_text.replace(
        f'requirement_ids = ["{requirement_id}"]',
        f'requirement_ids = ["{missing_requirement}", "{requirement_id}"]',
    ).replace(
        "component_ids = [",
        f'component_ids = ["{missing_component}", ',
        1,
    )
    run_path.write_text(run_text, encoding="utf-8")

    exit_code, response = invoke(repo, "stage-show")

    assert exit_code == 0, response
    requirements = response["data"]["project_knowledge"]["requirements"]
    components = response["data"]["project_knowledge"]["components"]
    assert (
        next(item for item in requirements if item["id"] == missing_requirement)[
            "state"
        ]
        == "unavailable"
    )
    assert (
        next(item for item in components if item["id"] == missing_component)["state"]
        == "unavailable"
    )
    missing = [
        finding
        for finding in response["findings"]
        if finding["code"] == "resume_reference_missing"
    ]
    assert {finding["path"] for finding in missing} >= {
        f".agentic/requirements/{missing_requirement}.toml",
        f".agentic/components/{missing_component}.md",
        ".agentic/requirements/SPEC-00000000000000000000000000000000.md",
    }


@pytest.mark.parametrize(
    ("profile", "created_count", "expected_limit"),
    (("full", 18, 16), ("short", 10, 8)),
)
def test_large_resume_graph_has_profile_budget_and_deterministic_omission_counts(
    tmp_path: Path,
    profile: str,
    created_count: int,
    expected_limit: int,
) -> None:
    """@brief Large full/short graphs use stable ordered explicit omissions."""
    repo = installed_repository(tmp_path)
    create_run(repo, profile=profile)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    (repo / ".agentic" / "tests" / "test_retry.py").write_text(
        "pass\n", encoding="utf-8"
    )
    ids = []
    for index in range(created_count):
        data = requirement_data()
        data["title"] = f"Requirement {index:02d}"
        data["behavior"] = f"Behavior {index:02d} remains deterministic."
        exit_code, created = invoke(repo, "requirement-create", data)
        assert exit_code == 0, created
        ids.append(created["data"]["id"])

    first_exit, first = invoke(repo, "stage-show")
    second_exit, second = invoke(repo, "stage-show")

    assert first_exit == second_exit == 0
    assert first["data"] == second["data"]
    requirements = first["data"]["project_knowledge"]["requirements"]
    assert first["data"]["budget"]["requirements"] == expected_limit
    assert [item["id"] for item in requirements["items"]] == sorted(ids)[
        :expected_limit
    ]
    assert requirements["total_count"] == created_count
    assert requirements["returned_count"] == expected_limit
    assert requirements["omitted_count"] == created_count - expected_limit
    assert requirements["truncated"] is True
    omitted_ids = first["data"]["project_knowledge"]["omitted_requirement_ids"]
    assert omitted_ids == sorted(ids)[expected_limit:]
    assert first["truncated"] is True


def test_stage_show_cli_and_host_operation_identity_remain_canonical(
    tmp_path: Path,
) -> None:
    """@brief Host/CLI control stays `stage.show` with `stage-show` spelling."""
    repo = installed_repository(tmp_path)
    create_run(repo)

    exit_code, response = invoke(repo, "stage-show")

    assert exit_code == 0
    assert response["operation"] == "stage.show"
    assert response["data"]["schema"] == "aegis.stage.resume_context"
    assert json.dumps(response["data"], sort_keys=False)
