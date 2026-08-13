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

import re
from hashlib import sha256
from pathlib import Path

import pytest
from aegis.infrastructure.codecs import (
    parse_markdown_document,
    render_markdown_document,
)

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


def component_data(files: list[str]) -> dict[str, object]:
    """@brief Return one complete Component input for declared member files."""
    return {
        "name": "Retry recorder",
        "status": "active",
        "files": files,
        "file_roles": [
            {"path": path, "role": f"Own the declared member {path}."}
            for path in files
        ],
        "requirement_links": [],
        "test_links": [],
        "purpose_boundary": "Own retry evidence; not process execution.",
        "interfaces": "record_attempt(result)",
        "dependencies": [],
        "known_gaps": [],
        "drift_review": {
            "behavior": "yes",
            "interfaces": "yes",
            "dependencies": "yes",
            "files": "yes",
        },
    }


def _start_requirement_stage(repo: Path) -> dict[str, object]:
    """@brief Create a Run and advance it to its active Requirement Stage."""
    created_run = create_run(repo)
    for stage in ("alignment", "requirement"):
        assert invoke(repo, "stage-complete")[0] == 0
        assert invoke(repo, "stage-start", None, stage)[0] == 0
    return created_run


def test_toml_datetime_in_a_requirement_is_read(tmp_path: Path) -> None:
    """@brief Valid temporal TOML remains readable without rewriting the artifact."""
    repo = installed_repository(tmp_path)
    _start_requirement_stage(repo)
    created = invoke(repo, "requirement-create", requirement_data())[1]
    requirement_id = created["data"]["id"]
    requirement_path = repo / ".agentic/requirements" / f"{requirement_id}.toml"
    text = requirement_path.read_text(encoding="utf-8")
    temporal_text = re.sub(
        r'^updated_at = ".*"$',
        "updated_at = 2026-01-01T00:00:00Z",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    assert temporal_text != text
    requirement_path.write_text(temporal_text, encoding="utf-8", newline="\n")
    original_bytes = requirement_path.read_bytes()

    show_exit, shown = invoke(
        repo, "requirement-show", None, "--requirement", requirement_id
    )
    list_exit, listed = invoke(repo, "requirement-list")
    trace_exit, traced = invoke(repo, "trace-validate")

    assert show_exit == list_exit == trace_exit == 0
    assert shown["data"]["updated_at"] == "2026-01-01T00:00:00+00:00"
    assert requirement_id in {item["id"] for item in listed["data"]["items"]}
    assert traced["operation_status"] == "completed"
    assert requirement_path.read_bytes() == original_bytes


def test_malformed_requirement_toml_reports_its_path(tmp_path: Path) -> None:
    """@brief Genuinely malformed TOML retains a useful artifact path."""
    repo = installed_repository(tmp_path)
    requirement_id = "REQ-0123456789abcdef0123456789abcdef"
    requirement_path = repo / ".agentic/requirements" / f"{requirement_id}.toml"
    requirement_path.parent.mkdir(parents=True, exist_ok=True)
    requirement_path.write_text("updated_at = [\n", encoding="utf-8")

    exit_code, response = invoke(
        repo, "requirement-show", None, "--requirement", requirement_id
    )

    assert exit_code == 4
    assert response["error"]["code"] == "malformed_state"
    assert response["error"]["path"] == (
        f".agentic/requirements/{requirement_id}.toml"
    )


def test_automated_requirement_without_happy_path_is_created_with_a_finding(
    tmp_path: Path,
) -> None:
    """@brief Incomplete automated trace links guide creation without blocking it.

    @details Covers PR-DEFAULT-003/004, PR-POSTURE-002,
             PR-TRACE-006/007/011, FS-FINDING-004, and FS-TRACE-002/004.
    """
    repo = installed_repository(tmp_path)
    created_run = _start_requirement_stage(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    data = requirement_data()
    data["tests"] = []

    exit_code, created = invoke(repo, "requirement-create", data)

    assert exit_code == 0, created
    assert created["operation_status"] == "completed"
    assert created["run_id"] == created_run["run_id"]
    assert created["stage"] == "requirement"
    requirement_id = created["data"]["id"]
    requirement_artifact = next(
        artifact
        for artifact in created["artifacts"]
        if artifact["type"] == "requirement"
    )
    requirement_path = requirement_artifact["path"]
    assert requirement_path == (
        f".agentic/requirements/{requirement_id}.toml"
    )
    findings = [
        finding
        for finding in created["findings"]
        if finding["code"] == "missing_happy_path"
    ]
    assert len(findings) == 1
    assert findings[0]["artifact"] == requirement_path

    requirement_text = (repo / requirement_path).read_text(encoding="utf-8")
    assert data["title"] in requirement_text
    assert 'verification_kind = "automated"' in requirement_text
    assert "[[tests]]" not in requirement_text
    assert "state_json" not in requirement_text

    show_exit, shown = invoke(
        repo, "requirement-show", None, "--requirement", requirement_id
    )
    assert show_exit == 0, shown
    assert shown["data"]["verification_kind"] == "automated"
    assert shown["data"].get("tests", []) == []
    validate_exit, validated = invoke(
        repo, "requirement-validate", None, "--requirement", requirement_id
    )
    assert validate_exit == 0, validated
    assert any(
        finding["code"] == "missing_happy_path"
        and finding["artifact"] == requirement_path
        for finding in validated["findings"]
    )

    run = invoke(repo, "run-show")[1]["data"]
    assert requirement_id in run["metadata"]["requirement_ids"]
    stage = invoke(repo, "stage-show")[1]["data"]
    events = stage["stage_state"]["events"]
    assert any(
        event["event"] == "requirement_created" and event["result"] == requirement_id
        for event in events
    )


def test_requirement_provenance_identifiers_remain_advisory_across_operations(
    tmp_path: Path,
) -> None:
    """@brief Forbidden provenance is named without rejecting current knowledge.

    @details Covers PR-REQ-003, PR-TRACE-011, and AM-REQ-001.
    """
    repo = installed_repository(tmp_path)
    _start_requirement_stage(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic/tests/test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    run_identifier = "RUN-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    requirement_identifier = "REQ-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    data = requirement_data()
    data.update(
        {
            "title": "Apply AEGIS-4711 retry policy",
            "behavior": f"When {run_identifier} retries, preserve each attempt.",
            "confirmation": (
                f"Verify the durable history described by {requirement_identifier}."
            ),
        }
    )

    create_exit, created = invoke(repo, "requirement-create", data)
    requirement_id = created["data"]["id"]
    update_exit, updated = invoke(
        repo,
        "requirement-update",
        data,
        "--requirement",
        requirement_id,
    )
    validate_exit, validated = invoke(
        repo, "requirement-validate", None, "--requirement", requirement_id
    )
    trace_exit, traced = invoke(repo, "trace-validate")

    assert create_exit == update_exit == validate_exit == trace_exit == 0
    for response in (created, updated, validated, traced):
        provenance = [
            finding
            for finding in response["findings"]
            if finding["code"] == "forbidden_requirement_identifier"
        ]
        assert len(provenance) == 3
        summaries = [finding["summary"] for finding in provenance]
        assert any(
            "title" in summary and "AEGIS-4711" in summary
            for summary in summaries
        )
        assert any(
            "behavior" in summary and run_identifier in summary
            for summary in summaries
        )
        assert any(
            "confirmation" in summary and requirement_identifier in summary
            for summary in summaries
        )
        assert all(finding["severity"] == "warning" for finding in provenance)


def test_trace_validate_reports_only_recognizable_unlinked_test_files(
    tmp_path: Path,
) -> None:
    """@brief Configured test roots expose orphan tests without support noise.

    @details Covers PR-TRACE-008/011 and AM-TEST-004/006.
    """
    repo = installed_repository(tmp_path)
    config = repo / ".agentic/config.toml"
    config.write_text(
        config.read_text(encoding="utf-8").replace(
            'tests = [".agentic/tests"]',
            'tests = ["tests", ".agentic/tests", "missing-tests"]',
        ),
        encoding="utf-8",
        newline="\n",
    )
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic/tests/test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    assert invoke(repo, "requirement-create", requirement_data())[0] == 0
    files = {
        "tests/test_orphan.py": "def test_orphan(): pass\n",
        "tests/service_test.py": "def test_service(): pass\n",
        ".agentic/tests/widget.test.js": "export const ok = true;\n",
        ".agentic/tests/card.spec.ts": "export const ok = true;\n",
        "tests/__init__.py": "",
        "tests/conftest.py": "VALUE = 1\n",
        "tests/.cache/test_hidden.py": "def test_hidden(): pass\n",
        "tests/__pycache__/test_cached.pyc": "cache\n",
        "tests/generated/test_generated.py": "def test_generated(): pass\n",
    }
    for relative, content in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    exit_code, traced = invoke(repo, "trace-validate")

    assert exit_code == 0, traced
    orphan_paths = {
        finding["artifact"]
        for finding in traced["findings"]
        if finding["code"] == "unlinked_test"
    }
    assert orphan_paths == {
        "tests/test_orphan.py",
        "tests/service_test.py",
        ".agentic/tests/widget.test.js",
        ".agentic/tests/card.spec.ts",
    }
    incomplete = [
        finding
        for finding in traced["findings"]
        if finding["code"] == "test_enumeration_incomplete"
    ]
    assert [finding["artifact"] for finding in incomplete] == ["missing-tests"]
    assert "incomplete" in incomplete[0]["summary"]


def test_project_requirement_component_and_trace_events_use_run_actor(
    tmp_path: Path,
) -> None:
    """@brief Project mutations without actor input inherit the durable Run actor."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    source = repo / "src" / "retry.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    test = repo / ".agentic" / "tests" / "test_retry.py"
    test.write_text("def test_retry_history(): pass\n", encoding="utf-8")
    assert invoke(repo, "requirement-create", requirement_data())[0] == 0
    assert invoke(repo, "component-create", component_data(["src/retry.py"]))[0] == 0
    assert (
        invoke(
            repo,
            "trace-impacted",
            {"changed_files": ["src/retry.py"], "changed_tests": []},
        )[0]
        == 0
    )

    stage = invoke(repo, "stage-show")[1]["data"]
    events = stage["stage_state"]["events"]
    mutation_events = {
        event["event"]: event["actor"]
        for event in events
        if event["event"]
        in {"requirement_created", "component_created", "trace_impacted"}
    }
    assert mutation_events == {
        "component_created": "agent",
        "requirement_created": "agent",
        "trace_impacted": "agent",
    }


def test_automated_requirement_update_without_happy_path_returns_findings(
    tmp_path: Path,
) -> None:
    """@brief Incomplete updated trace links return immediate advisory findings."""
    repo = installed_repository(tmp_path)
    _start_requirement_stage(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic" / "tests" / "test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    created = invoke(repo, "requirement-create", requirement_data())[1]
    requirement_id = created["data"]["id"]
    requirement_path = f".agentic/requirements/{requirement_id}.toml"
    update_data = requirement_data()
    update_data["behavior"] = "Every updated retry preserves its earlier outcomes."
    update_data["tests"] = []

    exit_code, updated = invoke(
        repo,
        "requirement-update",
        update_data,
        "--requirement",
        requirement_id,
    )

    assert exit_code == 0, updated
    assert updated["operation_status"] == "completed"
    assert {
        finding["code"] for finding in updated["findings"]
    } == {"missing_happy_path", "incomplete_coverage"}
    assert all(
        finding["artifact"] == requirement_path for finding in updated["findings"]
    )
    assert updated["artifacts"] == [
        {
            "type": "requirement",
            "id": None,
            "path": requirement_path,
            "action": "updated",
            "revision": updated["revision"],
        }
    ]

    shown = invoke(
        repo, "requirement-show", None, "--requirement", requirement_id
    )[1]
    assert shown["data"]["behavior"] == update_data["behavior"]
    assert shown["data"].get("tests", []) == []
    validated = invoke(
        repo, "requirement-validate", None, "--requirement", requirement_id
    )[1]
    assert {finding["code"] for finding in validated["findings"]} == {
        "missing_happy_path",
        "incomplete_coverage",
    }


def test_requirement_update_retains_unsafe_test_path_validation(
    tmp_path: Path,
) -> None:
    """@brief Non-blocking trace gaps do not admit unsafe update paths."""
    repo = installed_repository(tmp_path)
    _start_requirement_stage(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / ".agentic" / "tests" / "test_retry.py").write_text(
        "def test_retry_history(): pass\n", encoding="utf-8"
    )
    created = invoke(repo, "requirement-create", requirement_data())[1]
    requirement_id = created["data"]["id"]
    unsafe = requirement_data()
    unsafe["behavior"] = "This unsafe replacement must not persist."
    unsafe["tests"][0]["path"] = "../tests/test_retry.py"

    exit_code, response = invoke(
        repo, "requirement-update", unsafe, "--requirement", requirement_id
    )

    assert exit_code == 2
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "invalid_input"
    assert response["error"]["field"] == "tests.path"
    shown = invoke(
        repo, "requirement-show", None, "--requirement", requirement_id
    )[1]
    assert shown["data"]["behavior"] == requirement_data()["behavior"]


@pytest.mark.parametrize(
    ("case", "field", "details"),
    (
        ("tests_list", "tests", {}),
        ("test_object", "tests", {}),
        ("covered_files", "tests", {}),
        ("unsafe_test_path", "tests.path", {}),
        ("unsafe_covered_file", "tests.covered_files", {}),
        ("status", "status", {"allowed": ["active", "draft"]}),
        ("priority", "priority", {"allowed": ["Could", "Must", "Should"]}),
        (
            "verification_kind",
            "verification_kind",
            {"allowed": ["automated", "manual"]},
        ),
        ("manual_method", "manual_method", {}),
    ),
)
def test_requirement_create_retains_input_validation(
    tmp_path: Path, case: str, field: str, details: dict[str, list[str]]
) -> None:
    """@brief Incomplete trace guidance does not weaken malformed input checks."""
    repo = installed_repository(tmp_path)
    _start_requirement_stage(repo)
    data = requirement_data()
    if case == "tests_list":
        data["tests"] = "not a list"
    elif case == "test_object":
        data["tests"] = ["not an object"]
    elif case == "covered_files":
        data["tests"][0]["covered_files"] = []
    elif case == "unsafe_test_path":
        data["tests"][0]["path"] = "../tests/test_retry.py"
    elif case == "unsafe_covered_file":
        data["tests"][0]["covered_files"] = ["../src/retry.py"]
    elif case == "status":
        data["status"] = "unknown"
    elif case == "priority":
        data["priority"] = "Urgent"
    elif case == "verification_kind":
        data["verification_kind"] = "inspection"
    else:
        data["verification_kind"] = "manual"
        data["manual_method"] = ""
        data["tests"] = []

    exit_code, response = invoke(repo, "requirement-create", data)

    assert exit_code == 2
    assert response["operation_status"] == "error"
    assert response["error"]["code"] == "invalid_input"
    assert response["error"]["field"] == field
    assert response["error"]["details"] == details


@pytest.mark.parametrize(
    ("purposes", "expected_codes"),
    (
        (["happy_path"], {"missing_test"}),
        (["failure_path"], {"missing_happy_path", "missing_test"}),
    ),
)
def test_requirement_create_reports_nonexistent_test_trace_findings(
    tmp_path: Path, purposes: list[str], expected_codes: set[str]
) -> None:
    """@brief Missing supplied tests remain advisory with truthful trace gaps."""
    repo = installed_repository(tmp_path)
    _start_requirement_stage(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("VALUE = 1\n", encoding="utf-8")
    data = requirement_data(".agentic/tests/test_missing.py")
    data["tests"][0]["purposes"] = purposes

    exit_code, created = invoke(repo, "requirement-create", data)

    assert exit_code == 0, created
    assert created["operation_status"] == "completed"
    assert {finding["code"] for finding in created["findings"]} == expected_codes


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
        "contract": (
            "Attempts are append ordered and immutable.\n\n"
            "## Nested protocol detail\n\nThe attempt number increases monotonically."
        ),
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
    specification = spec_path.read_text(encoding="utf-8")
    assert "state_json" not in specification
    assert f"# Specification - {spec_data['title']}" in specification
    for heading in (
        "## Purpose",
        "## Contract",
        "## Inputs and outputs",
        "## Rules and invariants",
        "## Error behavior",
        "## Examples",
        "## Open details",
    ):
        assert heading in specification
    _, specification_state, _ = parse_markdown_document(
        spec_path.read_bytes(), path=spec_path.as_posix()
    )
    assert specification_state["contract"] == spec_data["contract"]

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
        "file_roles": [
            {"path": "src/retry.py", "role": "Persist ordered retry outcomes."}
        ],
        "requirement_links": [
            {
                "requirement_id": requirement,
                "behavior": "Retains ordered attempts.",
            }
        ],
        "test_links": [
            {
                "path": ".agentic/tests/test_retry.py",
                "selector": "test_retry_history",
                "description": "Verifies ordered retry evidence persistence.",
            }
        ],
        "purpose_boundary": "Own retry evidence; not process execution.",
        "interfaces": "record_attempt(result)",
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
    run_id = component["run_id"]
    run_text = (
        repo / ".agentic" / "runs" / run_id / "run.md"
    ).read_text(encoding="utf-8")
    assert f'requirement_ids = ["{requirement}"]' in run_text
    assert f'component_ids = ["{component_id}"]' in run_text
    component_path = repo / ".agentic" / "components" / f"{component_id}.md"
    component_text = component_path.read_text(encoding="utf-8")
    assert "state_json" not in component_text
    assert "# Retry recorder" in component_text
    for heading in (
        "## Purpose and boundary",
        "## Interfaces",
        "## Behaviors and requirements",
        "## File roles",
        "## Tests",
        "## Dependencies",
        "## Known gaps",
        "## Drift review",
    ):
        assert heading in component_text
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
    component_text = component_path.read_text(encoding="utf-8")
    assert requirement not in component_text
    assert not (repo / ".agentic" / "requirements" / f"{requirement}.toml").exists()


def test_component_requirement_links_round_trip_atomically(tmp_path: Path) -> None:
    """@brief PR-COMP-001: Requirement behaviors remain one atomic relationship."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    first = invoke(repo, "requirement-create", requirement_data())[1]["data"]["id"]
    second_data = requirement_data()
    second_data["title"] = "Retry order remains visible"
    second_data["behavior"] = "Retry order remains visible to reviewers."
    second = invoke(repo, "requirement-create", second_data)[1]["data"]["id"]
    data = component_data(["src/retry.py"])
    data["requirement_links"] = [
        {"requirement_id": first, "behavior": "Retains every retry attempt."},
        {"requirement_id": second, "behavior": "Exposes retry ordering."},
    ]

    exit_code, created = invoke(repo, "component-create", data)

    assert exit_code == 0, created
    component_id = created["data"]["id"]
    component_path = repo / ".agentic/components" / f"{component_id}.md"
    rendered = component_path.read_text(encoding="utf-8")
    assert "requirement_ids =" not in rendered
    assert f"- `{first}` - Retains every retry attempt." in rendered
    assert f"- `{second}` - Exposes retry ordering." in rendered

    data["requirement_links"] = list(reversed(data["requirement_links"]))
    updated_exit, updated = invoke(
        repo, "component-update", data, "--component", component_id
    )
    assert updated_exit == 0, updated
    shown = invoke(repo, "component-show", None, "--component", component_id)[1]
    assert shown["data"]["metadata"]["requirement_ids"] == [second, first]
    assert shown["data"]["state"]["requirement_links"] == data[
        "requirement_links"
    ]
    canonical = component_path.read_text(encoding="utf-8")
    legacy = canonical.replace(
        "\n+++\n\n# ",
        f'\nrequirement_ids = ["{second}", "{first}"]\n+++\n\n# ',
        1,
    )
    component_path.write_text(legacy, encoding="utf-8", newline="\n")
    legacy_exit, legacy_shown = invoke(
        repo, "component-show", None, "--component", component_id
    )
    assert legacy_exit == 0, legacy_shown
    assert legacy_shown["data"]["state"]["requirement_links"] == data[
        "requirement_links"
    ]
    component_path.write_text(
        legacy.replace(
            f'requirement_ids = ["{second}", "{first}"]',
            f'requirement_ids = ["{first}", "{second}"]',
        ),
        encoding="utf-8",
        newline="\n",
    )
    mismatch_exit, mismatch = invoke(
        repo, "component-show", None, "--component", component_id
    )
    assert mismatch_exit == 4
    assert mismatch["error"]["code"] == "malformed_state"


def test_component_drift_review_rejects_unknown_keys_without_mutation(
    tmp_path: Path,
) -> None:
    """@brief PR-COMP-004: Unknown drift axes cannot be normalized away."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    created = invoke(
        repo, "component-create", component_data(["src/retry.py"])
    )[1]
    component_id = created["data"]["id"]
    component_path = repo / ".agentic/components" / f"{component_id}.md"
    original = component_path.read_bytes()
    update = component_data(["src/retry.py"])
    update["drift_review"] = {
        "behavior": "yes",
        "interfaces": "yes",
        "dependencies": "yes",
        "files": "yes",
        "state": "current",
    }

    exit_code, refused = invoke(
        repo, "component-update", update, "--component", component_id
    )

    assert exit_code == 2
    assert refused["error"]["code"] == "invalid_input"
    assert refused["error"]["field"] == "drift_review.state"
    assert component_path.read_bytes() == original
    legacy_input = component_data(["src/retry.py"])
    legacy_input.pop("requirement_links")
    legacy_input["requirement_ids"] = []
    legacy_input["behaviors"] = []
    legacy_exit, legacy_refused = invoke(
        repo, "component-update", legacy_input, "--component", component_id
    )
    assert legacy_exit == 2
    assert legacy_refused["error"]["field"] == "requirement_links"
    assert component_path.read_bytes() == original
    for axis in ("behavior", "interfaces", "dependencies", "files"):
        invalid_axis = component_data(["src/retry.py"])
        invalid_axis["drift_review"][axis] = "current"
        axis_exit, axis_refused = invoke(
            repo, "component-update", invalid_axis, "--component", component_id
        )
        assert axis_exit == 2
        assert axis_refused["error"]["field"] == f"drift_review.{axis}"
        assert component_path.read_bytes() == original


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


@pytest.mark.parametrize(
    ("test_path", "selector", "create_test", "reason_fragment"),
    (
        (
            ".agentic/tests/test_missing.py",
            "test_retry_history",
            False,
            "does not exist",
        ),
        (
            "tests/test_retry.py",
            "test_retry_history",
            True,
            "outside configured test roots",
        ),
        (
            ".agentic/tests/test_retry.py",
            "--collect-only",
            True,
            "unsafe selector",
        ),
    ),
)
def test_trace_impacted_invalid_link_uses_explicit_full_suite_fallback(
    tmp_path: Path,
    test_path: str,
    selector: str,
    create_test: bool,
    reason_fragment: str,
) -> None:
    """@brief Unsafe linked tests never become executable impacted selectors."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "retry.py").write_text("pass\n", encoding="utf-8")
    if create_test:
        target = repo / test_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_retry_history(): pass\n", encoding="utf-8")
    data = requirement_data(test_path)
    tests = data["tests"]
    assert isinstance(tests, list)
    tests[0]["selector"] = selector
    assert invoke(repo, "requirement-create", data)[0] == 0

    exit_code, impacted = invoke(
        repo, "trace-impacted", {"changed_files": ["src/retry.py"], "changed_tests": []}
    )

    assert exit_code == 0, impacted
    assert impacted["data"]["mode"] == "full"
    assert impacted["data"]["tests"] == []
    assert any(
        reason_fragment in reason.lower()
        for reason in impacted["data"]["fallback_reasons"]
    )
    assert impacted["data"]["full_suite_commands"] == ["tests.project"]


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


def test_component_drift_is_reported_after_a_member_file_changes(
    tmp_path: Path,
) -> None:
    """@brief Changed declared bytes re-arm Component drift review advisories.

    @details Covers PR-COMP-003/004, AM-COMP-004/005, and FS-COMP-003/004.
    """
    repo = installed_repository(tmp_path)
    create_run(repo)
    member = repo / "src" / "retry.py"
    member.parent.mkdir()
    original_bytes = b"def retry():\n    return 'original'\n"
    changed_bytes = b"def retry():\n    return 'changed'\n"
    member.write_bytes(original_bytes)

    created_exit, created = invoke(
        repo, "component-create", component_data(["src/retry.py"])
    )

    assert created_exit == 0, created
    component_id = created["data"]["id"]
    component_path = (
        repo / ".agentic" / "components" / f"{component_id}.md"
    )
    created_artifact = component_path.read_bytes()
    shown = invoke(
        repo, "component-show", None, "--component", component_id
    )[1]
    assert shown["data"]["state"]["file_digests"] == {
        "src/retry.py": sha256(original_bytes).hexdigest()
    }
    initial_component = invoke(
        repo, "component-validate", None, "--component", component_id
    )[1]
    assert "component_drift" not in {
        finding["code"] for finding in initial_component["findings"]
    }
    initial_trace = invoke(repo, "trace-validate")[1]
    assert "component_drift" not in {
        finding["code"] for finding in initial_trace["findings"]
    }
    assert component_path.read_bytes() == created_artifact

    member.write_bytes(changed_bytes)
    component_validation = invoke(
        repo, "component-validate", None, "--component", component_id
    )[1]
    trace_validation = invoke(repo, "trace-validate")[1]
    for response in (component_validation, trace_validation):
        drift = [
            finding
            for finding in response["findings"]
            if finding["code"] == "component_drift"
        ]
        assert len(drift) == 1
        assert "src/retry.py" in drift[0]["summary"]
    assert component_path.read_bytes() == created_artifact

    resumed = invoke(repo, "stage-show")[1]
    stale = [
        finding
        for finding in resumed["findings"]
        if finding["code"] == "resume_reference_stale"
    ]
    assert len(stale) == 1
    assert "src/retry.py" in stale[0]["observation"]
    component_context = resumed["data"]["project_knowledge"]["components"]
    assert [item["id"] for item in component_context] == [component_id]
    assert component_context[0]["state"] == "available"
    assert component_path.read_bytes() == created_artifact

    update_data = component_data(["src/retry.py"])
    update_data["purpose_boundary"] = "Own reviewed retry evidence."
    updated_exit, updated = invoke(
        repo,
        "component-update",
        update_data,
        "--component",
        component_id,
    )
    assert updated_exit == 0, updated
    refreshed_artifact = component_path.read_bytes()
    assert refreshed_artifact != created_artifact
    refreshed = invoke(
        repo, "component-show", None, "--component", component_id
    )[1]
    assert refreshed["data"]["state"]["file_digests"] == {
        "src/retry.py": sha256(changed_bytes).hexdigest()
    }
    for response in (
        invoke(repo, "component-validate", None, "--component", component_id)[1],
        invoke(repo, "trace-validate")[1],
    ):
        assert "component_drift" not in {
            finding["code"] for finding in response["findings"]
        }
    refreshed_resume = invoke(repo, "stage-show")[1]
    assert "resume_reference_stale" not in {
        finding["code"] for finding in refreshed_resume["findings"]
    }
    assert component_path.read_bytes() == refreshed_artifact


def test_component_digest_baseline_is_deterministic_and_hashes_binary_bytes(
    tmp_path: Path,
) -> None:
    """@brief Multiple exact-byte digests are ordered and remain green unchanged."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    source = repo / "src"
    source.mkdir()
    members = {
        "src/zeta.bin": b"\x00\xff\x10binary\r\n",
        "src/alpha.py": b"VALUE = 1\n",
    }
    for path, content in members.items():
        (repo / path).write_bytes(content)

    created = invoke(repo, "component-create", component_data(list(members)))[1]
    component_id = created["data"]["id"]
    shown = invoke(
        repo, "component-show", None, "--component", component_id
    )[1]
    digests = shown["data"]["state"]["file_digests"]

    assert list(digests) == sorted(members)
    assert digests == {
        path: sha256(content).hexdigest()
        for path, content in sorted(members.items())
    }
    validated = invoke(
        repo, "component-validate", None, "--component", component_id
    )[1]
    assert "component_drift" not in {
        finding["code"] for finding in validated["findings"]
    }


def test_missing_component_member_is_not_redundantly_reported_as_drift(
    tmp_path: Path,
) -> None:
    """@brief A missing member retains its specific finding without false change."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    (repo / "src").mkdir()
    (repo / "src" / "present.py").write_bytes(b"PRESENT = True\n")
    created = invoke(
        repo,
        "component-create",
        component_data(["src/present.py", "src/missing.py"]),
    )[1]
    component_id = created["data"]["id"]

    validated = invoke(
        repo, "component-validate", None, "--component", component_id
    )[1]
    codes = [finding["code"] for finding in validated["findings"]]

    assert codes.count("missing_component_file") == 1
    assert "component_drift" not in codes


def test_legacy_component_without_digest_baselines_degrades_to_advisory(
    tmp_path: Path,
) -> None:
    """@brief A readable legacy Component loads and reports an unreviewed baseline."""
    repo = installed_repository(tmp_path)
    create_run(repo)
    member = repo / "src" / "retry.py"
    member.parent.mkdir()
    member.write_bytes(b"VALUE = 1\n")
    created = invoke(
        repo, "component-create", component_data(["src/retry.py"])
    )[1]
    component_id = created["data"]["id"]
    component_path = (
        repo / ".agentic" / "components" / f"{component_id}.md"
    )
    metadata, state, _ = parse_markdown_document(
        component_path.read_bytes(), path=component_path.as_posix()
    )
    state.pop("file_digests", None)
    component_path.write_bytes(
        render_markdown_document(metadata, state, kind="component")
    )
    legacy_bytes = component_path.read_bytes()

    exit_code, validated = invoke(
        repo, "component-validate", None, "--component", component_id
    )

    assert exit_code == 0, validated
    drift = [
        finding
        for finding in validated["findings"]
        if finding["code"] == "component_drift"
    ]
    assert len(drift) == 1
    assert "src/retry.py" in drift[0]["summary"]
    assert component_path.read_bytes() == legacy_bytes
