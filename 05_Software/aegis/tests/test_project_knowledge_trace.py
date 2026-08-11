#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_project_knowledge_trace.py
@brief   Verify current Requirements, Components, and computed traceability.
@details Covers IP-07 through IP-09, PR-REQ, PR-COMP, PR-TRACE, and
         AC-REQ-001/003, AC-COMP-001, and AC-TRACE-001/002.
"""

from __future__ import annotations

from pathlib import Path

from tests.test_run_stage_workflow import create_run, installed_repository, invoke


def requirement_data(
    test_path: str = ".agentic/tests/test_retry.py",
) -> dict[str, object]:
    """@brief Return one complete single-behavior Requirement input."""
    return {
        "title": "Retry evidence remains durable",
        "status": "active",
        "priority": "Must",
        "behavior": (
            "When an execution is retried, every earlier attempt remains recorded."
        ),
        "confirmation": (
            "Execute a failure followed by a passing retry and inspect both records."
        ),
        "verification_kind": "automated",
        "manual_method": "",
        "impacted_files": ["src/retry.py"],
        "tests": [
            {
                "path": test_path,
                "selector": "test_retry_history",
                "purposes": ["happy_path", "failure_path"],
                "covered_files": ["src/retry.py"],
            }
        ],
        "rationale": "Retries must not manufacture a clean history.",
    }


def test_requirement_and_specification_replace_current_content_without_provenance(
    tmp_path: Path,
) -> None:
    """@brief Requirement/Specification updates replace project knowledge."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    (repo / ".agentic" / "tests" / "test_retry.py").write_text(
        "pass\n", encoding="utf-8"
    )

    exit_code, created = invoke(repo, "requirement-create", requirement_data())
    assert exit_code == 0, created
    requirement_id = created["data"]["id"]
    requirement_path = repo / ".agentic" / "requirements" / f"{requirement_id}.toml"
    content = requirement_path.read_text(encoding="utf-8")
    assert requirement_id.startswith("REQ-")
    assert "RUN-" not in content
    assert "ticket" not in content.lower()

    spec_data = {
        "title": "Retry history format",
        "status": "active",
        "purpose": "Define the retained attempt list.",
        "contract": "Attempts are append ordered and immutable.",
        "inputs_outputs": "Input attempt; output durable ordered record.",
        "rules": ["Never replace an earlier attempt."],
        "error_behavior": "Malformed state is preserved and reported.",
        "examples": "failed, then passed",
        "open_details": "None",
    }
    exit_code, specified = invoke(
        repo, "specification-set", spec_data, "--requirement", requirement_id
    )
    assert exit_code == 0, specified
    spec_path = repo / ".agentic" / "requirements" / f"SPEC-{requirement_id[4:]}.md"
    assert spec_path.exists()

    updated_data = requirement_data()
    updated_data["behavior"] = (
        "Every command retry preserves all prior attempt outcomes."
    )
    exit_code, updated = invoke(
        repo, "requirement-update", updated_data, "--requirement", requirement_id
    )
    assert exit_code == 0, updated
    assert "Every command retry" in requirement_path.read_text(encoding="utf-8")
    assert "When an execution is retried" not in requirement_path.read_text(
        encoding="utf-8"
    )


def test_component_find_validate_and_requirement_delete_preserve_source_and_tests(
    tmp_path: Path,
) -> None:
    """@brief Current links are removed atomically without deleting project code."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    source = repo / "src" / "retry.py"
    test = repo / ".agentic" / "tests" / "test_retry.py"
    source.write_text("pass\n", encoding="utf-8")
    test.write_text("pass\n", encoding="utf-8")
    requirement = invoke(repo, "requirement-create", requirement_data())[1]["data"][
        "id"
    ]
    component_data = {
        "name": "Retry recorder",
        "status": "active",
        "files": ["src/retry.py"],
        "requirement_ids": [requirement],
        "test_links": [
            {"path": ".agentic/tests/test_retry.py", "selector": "test_retry_history"}
        ],
        "purpose_boundary": "Own retry evidence; not process execution.",
        "interfaces": "record_attempt(result)",
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
    component_id = component["data"]["id"]
    found = invoke(repo, "component-find", None, "--path", "src/retry.py")[1]
    assert found["data"]["items"][0]["id"] == component_id
    assert (
        invoke(repo, "component-validate", None, "--component", component_id)[1][
            "data"
        ]["finding_count"]
        == 0
    )

    exit_code, deleted = invoke(
        repo, "requirement-delete", None, "--requirement", requirement
    )
    assert exit_code == 0, deleted
    assert source.exists() and test.exists()
    component_text = (
        repo / ".agentic" / "components" / f"{component_id}.md"
    ).read_text(encoding="utf-8")
    assert requirement not in component_text
    assert not (repo / ".agentic" / "requirements" / f"{requirement}.toml").exists()


def test_trace_union_and_explicit_full_suite_fallback(tmp_path: Path) -> None:
    """@brief Covered changes select the union; gaps select configured full suite."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    for name in ("test_retry.py", "test_retry_audit.py"):
        (repo / ".agentic" / "tests" / name).write_text("pass\n", encoding="utf-8")
    first = requirement_data()
    second = requirement_data(".agentic/tests/test_retry_audit.py")
    second["title"] = "Retry audit remains reviewable"
    second["behavior"] = "Retry history can be reviewed after execution."
    invoke(repo, "requirement-create", first)
    invoke(repo, "requirement-create", second)

    exit_code, impacted = invoke(
        repo, "trace-impacted", {"changed_files": ["src/retry.py"], "changed_tests": []}
    )
    assert exit_code == 0, impacted
    assert impacted["data"]["mode"] == "impacted"
    assert {item["path"] for item in impacted["data"]["tests"]} == {
        ".agentic/tests/test_retry.py",
        ".agentic/tests/test_retry_audit.py",
    }
    fallback = invoke(
        repo,
        "trace-impacted",
        {"changed_files": ["src/unmapped.py"], "changed_tests": []},
    )[1]
    assert fallback["data"]["mode"] == "full"
    assert fallback["data"]["fallback_reasons"] == [
        "No complete test coverage for src/unmapped.py."
    ]
    validation = invoke(repo, "trace-validate")[1]
    assert validation["operation_status"] == "completed"


def test_trace_validate_reports_incomplete_and_diverged_file_coverage(
    tmp_path: Path,
) -> None:
    """@brief Coverage must neither omit impacted files nor invent unrelated ones."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    for name in ("retry.py", "uncovered.py", "outside.py"):
        (repo / "src" / name).write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic/tests/test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    data = requirement_data()
    data["impacted_files"] = ["src/retry.py", "src/uncovered.py"]
    data["tests"][0]["covered_files"] = ["src/retry.py", "src/outside.py"]
    created = invoke(repo, "requirement-create", data)[1]
    assert created["operation_status"] == "completed"

    validated = invoke(repo, "trace-validate")[1]
    codes = {finding["code"] for finding in validated["findings"]}

    assert "incomplete_coverage" in codes
    assert "diverged_coverage" in codes
