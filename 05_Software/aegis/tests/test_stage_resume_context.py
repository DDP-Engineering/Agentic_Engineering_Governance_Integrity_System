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


def _collection(items: list[Any]) -> dict[str, Any]:
    """@return One expected complete bounded-collection shape."""
    return {
        "items": items,
        "total_count": len(items),
        "returned_count": len(items),
        "omitted_count": 0,
        "truncated": False,
    }


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
        "requirement_ids": [requirement_id],
        "test_links": [
            {
                "path": ".agentic/tests/test_retry.py",
                "selector": "test_retry_history",
                "description": "Verifies durable retry history.",
            }
        ],
        "purpose_boundary": "Own retry evidence; not process execution.",
        "interfaces": "retry()",
        "behaviors": ["Retains ordered attempts."],
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
    assert data["run_summary"]["scope"]["content"] == "Pending Alignment."
    assert data["stage_state"]["revision"] == response["revision"]
    assert data["instruction"]["content"]
    assert data["sections"]["items"]
    knowledge = data["project_knowledge"]
    assert [item["id"] for item in knowledge["requirements"]["items"]] == [
        requirement_id
    ]
    assert knowledge["requirements"]["items"][0]["specification"]["path"] == (
        specification_path
    )
    assert [item["id"] for item in knowledge["components"]["items"]] == [component_id]
    assert knowledge["affected_files"] == _collection(["src/retry.py"])
    assert knowledge["tests"]["items"][0]["path"] == (".agentic/tests/test_retry.py")
    assert data["project_rules"]["state"] == "absent"
    assert data["project_rules"]["content"]["content"] == ""
    assert data["tool_context"]["test_roots"]["items"] == [".agentic/tests"]
    assert data["tool_context"]["risk"]["attention_threshold"] == "medium"
    assert data["tool_context"]["risk"]["protected_scope_patterns"] == (_collection([]))
    assert response["truncated"] is False


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
        "requirement_ids": [requirement],
        "test_links": [
            {
                "path": ".agentic/tests/test_retry.py",
                "selector": "test_retry_history",
                "description": "Covers retry history.",
            }
        ],
        "purpose_boundary": "Own retry state.",
        "interfaces": "retry()",
        "behaviors": ["Retains retries."],
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
    items = response["data"]["project_knowledge"]["components"]["items"]
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
    assert legacy["data"]["project_rules"]["content"]["content"] == ("Règle locale.\n")

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
    assert intake["data"]["tool_context"]["commands"]["items"] == []
    commands = validation["data"]["tool_context"]["commands"]["items"]
    assert commands[0]["name"] == "private"
    assert [item["content"] for item in commands[0]["command"]["items"]] == [
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
    requirements = response["data"]["project_knowledge"]["requirements"]["items"]
    components = response["data"]["project_knowledge"]["components"]["items"]
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
    assert omitted_ids["items"] == sorted(ids)[expected_limit:]
    assert omitted_ids["omitted_count"] == 0
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
