#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_requirements_traceability.py
@brief Focused tests for UUID-backed current requirement snapshots.
@details Covers deterministic TOML persistence, replacement semantics, live
         reverse indexes, audits, coverage, impact, and INV-8 integration.
@author Eng. Dan Dumitru Pasare
@date 2026-07-22
@version 0.10.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

import pytest

from aegis.cli import main
from aegis.config import WorkflowConfig, load_config
from aegis.invariants import evaluate
from aegis.models import Check, Graph, Intent
from aegis.requirement_store import (
    RequirementRecord,
    RequirementValidationError,
    create_requirement_record,
    load_requirement_file,
    render_requirement_toml,
)
from aegis.requirements import (
    activate_requirement,
    audit_coverage,
    audit_traceability,
    build_requirement_index,
    create_requirement,
    impact,
    list_requirements,
    load_all_requirements,
    load_requirement_index,
    resolve_test,
    show_requirement,
    update_requirement,
)

# CONSTANTS

UUID_ONE = uuid.UUID("6f3a61e8-84fc-438a-9b0b-53554cd04789")
UUID_TWO = uuid.UUID("12345678-1234-4abc-8def-1234567890ab")
REQ_ONE = f"REQ-FUNC-{UUID_ONE}"
REQ_TWO = f"REQ-FUNC-{UUID_TWO}"
CREATED = "2026-07-22T10:20:00Z"
UPDATED = "2026-07-22T14:45:00Z"

# LOCAL HELPERS


def configure_repository(
    repo_root: Path,
    *,
    coverage: bool = False,
    requirement_roots: tuple[str, ...] = (".agentic/requirements",),
) -> WorkflowConfig:
    """
    @brief Configure one temporary repository for requirement tests.
    @param[in] repo_root Temporary repository root.
    @param[in] coverage Enable an enforced ``src`` coverage policy.
    @param[in] requirement_roots Canonical requirement roots to configure.
    @return Parsed strict workflow configuration.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    path = repo_root / ".agentic" / "workflow.toml"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        'roots = [".agentic/requirements"]',
        "roots = [" + ", ".join(f'\"{root}\"' for root in requirement_roots) + "]",
    )
    if coverage:
        text = text.replace(
            '[traceability.coverage]\nmode = "disabled"\ncoverable_roots = []\nexclude = []',
            '[traceability.coverage]\nmode = "enforce"\n'
            'coverable_roots = ["src"]\nexclude = ["__init__.py"]',
        )
    path.write_text(text, encoding="utf-8", newline="\n")
    for root in requirement_roots:
        (repo_root / root).mkdir(parents=True, exist_ok=True)
    return load_config(repo_root)


def write_tested_module(repo_root: Path) -> None:
    """
    @brief Create a current source file and exact Python test selector.
    @param[in] repo_root Temporary repository root.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.2.0
    """
    (repo_root / "src").mkdir(exist_ok=True)
    (repo_root / "src" / "calculator.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8", newline="\n"
    )
    (repo_root / "tests").mkdir(exist_ok=True)
    (repo_root / "tests" / "test_calculator.py").write_text(
        f'def test_add():\n    """{REQ_ONE}"""\n    assert True\n',
        encoding="utf-8",
        newline="\n",
    )


def create_fixed_record(
    repo_root: Path,
    config: WorkflowConfig,
    *,
    identifier: uuid.UUID = UUID_ONE,
    affected_paths: tuple[str, ...] = ("src/calculator.py",),
    linked_tests: tuple[str, ...] = ("tests/test_calculator.py::test_add",),
) -> RequirementRecord:
    """
    @brief Create one deterministic Planned fixture through production storage.
    @return Persisted current snapshot.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    return create_requirement_record(
        repo_root,
        config,
        category="functional",
        priority="Must",
        requirement="Addition returns a sum.",
        rationale="Required calculator behavior.",
        verification="Automated test",
        affected_paths=affected_paths,
        linked_tests=linked_tests,
        timestamp=CREATED,
        uuid_factory=lambda: identifier,
    )


# TESTS


def test_uuid_identity_and_deterministic_toml_round_trip(tmp_path: Path) -> None:
    """
    @brief Verify the canonical UUIDv4 identity and deterministic schema order.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    record = create_fixed_record(
        tmp_path,
        config,
        affected_paths=("src/z.py", "./src/calculator.py"),
        linked_tests=("tests/test_calculator.py::test_add",),
    )
    path = tmp_path / record.source_file
    text = path.read_text(encoding="utf-8")

    assert record.id == REQ_ONE
    assert record.affected_paths == ("src/calculator.py", "src/z.py")
    assert text == render_requirement_toml(record)
    assert text.index("affected_paths") < text.index("linked_tests")
    assert text.endswith("\n")
    assert load_requirement_file(path, tmp_path, ".agentic/requirements", config) == record
    assert "source_file" not in record.to_dict()


def test_independent_creates_use_different_ids_and_files(tmp_path: Path) -> None:
    """
    @brief Verify independent requirement creation never edits a shared register.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.2.0
    """
    config = configure_repository(tmp_path)
    first = create_requirement(
        tmp_path,
        category="functional",
        priority="Must",
        requirement="First behavior.",
        rationale="First rationale.",
        verification="Inspection: inspect the first behavior",
        config=config,
        timestamp=CREATED,
    )
    second = create_requirement(
        tmp_path,
        category="functional",
        priority="Should",
        requirement="Second behavior.",
        rationale="Second rationale.",
        verification="Manual: verify the second behavior",
        config=config,
        timestamp=CREATED,
    )

    assert first.id != second.id
    assert first.source_file != second.source_file
    assert (tmp_path / first.source_file).is_file()
    assert (tmp_path / second.source_file).is_file()


def test_uuid_collision_retries_without_overwrite(tmp_path: Path) -> None:
    """
    @brief Verify an exclusive-create collision retries with a fresh UUID.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    first = create_fixed_record(tmp_path, config, linked_tests=())
    original = (tmp_path / first.source_file).read_text(encoding="utf-8")
    identifiers: Iterator[uuid.UUID] = iter((UUID_ONE, UUID_TWO))

    second = create_requirement_record(
        tmp_path,
        config=config,
        category="functional",
        priority="Could",
        requirement="A distinct behavior.",
        rationale="Collision retry coverage.",
        verification="Manual: inspect collision behavior",
        timestamp=CREATED,
        uuid_factory=lambda: next(identifiers),
    )

    assert second.id == REQ_TWO
    assert (tmp_path / first.source_file).read_text(encoding="utf-8") == original
    assert len(load_all_requirements(tmp_path, config)) == 2


@pytest.mark.parametrize(
    ("mutation", "key"),
    [
        (lambda text: text.replace("schema_version = 1\n", ""), "schema_version"),
        (lambda text: text.replace("schema_version = 1", 'schema_version = "1"'), "schema_version"),
        (lambda text: text.replace("schema_version = 1", "schema_version = 2"), "schema_version"),
        (lambda text: text.replace('category = "functional"', 'category = "security"'), "category"),
        (lambda text: text + 'unexpected = "value"\n', "unexpected"),
    ],
)
def test_malformed_records_report_file_and_key(
    tmp_path: Path, mutation: Callable[[str], str], key: str
) -> None:
    """
    @brief Verify malformed snapshots identify their source file and offending key.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    record = create_fixed_record(tmp_path, config, linked_tests=())
    path = tmp_path / record.source_file
    path.write_text(mutation(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")

    with pytest.raises(RequirementValidationError) as exc_info:
        load_all_requirements(tmp_path, config)

    assert record.source_file in str(exc_info.value)
    assert exc_info.value.key == key


def test_scalar_update_preserves_immutable_identity(tmp_path: Path) -> None:
    """
    @brief Verify current-contract scalar revisions retain ID and creation time.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    original = create_fixed_record(tmp_path, config, linked_tests=())

    updated = update_requirement(
        tmp_path,
        original.id,
        priority="Should",
        requirement="Addition returns a precise sum.",
        config=config,
        timestamp=UPDATED,
    )

    assert updated.id == original.id
    assert updated.category == original.category
    assert updated.created_on == CREATED
    assert updated.last_updated == UPDATED
    assert updated.priority == "Should"
    assert show_requirement(tmp_path, original.id, config).requirement.endswith("precise sum.")


def test_collection_update_replaces_and_clears_complete_sets(tmp_path: Path) -> None:
    """
    @brief Verify renamed tests and affected paths replace complete stale sets.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.2.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    original = create_fixed_record(tmp_path, config)
    (tmp_path / "tests" / "test_calculator_renamed.py").write_text(
        "def test_sum():\n    assert True\n",
        encoding="utf-8",
        newline="\n",
    )

    replaced = update_requirement(
        tmp_path,
        original.id,
        linked_tests=["tests/test_calculator_renamed.py::test_sum"],
        affected_paths=["src/new.py", "src/**/nested.py"],
        config=config,
        timestamp=UPDATED,
    )
    cleared = update_requirement(
        tmp_path,
        original.id,
        clear_linked_tests=True,
        clear_affected_paths=True,
        verification="Manual: inspect current behavior",
        config=config,
        timestamp=UPDATED,
    )

    assert replaced.affected_paths == ("src/**/nested.py", "src/new.py")
    assert replaced.linked_tests == ("tests/test_calculator_renamed.py::test_sum",)
    assert cleared.affected_paths == ()
    assert cleared.linked_tests == ()


def test_activation_replaces_tests_and_does_not_write_on_failure(tmp_path: Path) -> None:
    """
    @brief Verify Active transition validates the complete selector set atomically.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    record = create_fixed_record(tmp_path, config, linked_tests=())
    path = tmp_path / record.source_file
    before = path.read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="do not resolve"):
        activate_requirement(
            tmp_path,
            record.id,
            ["tests/test_missing.py::test_missing"],
            "Automated test",
            config,
            timestamp=UPDATED,
        )
    assert path.read_text(encoding="utf-8") == before

    active = activate_requirement(
        tmp_path,
        record.id,
        ["tests/test_calculator.py::test_add"],
        "Automated test",
        config,
        timestamp=UPDATED,
    )
    assert active.status == "Active"
    assert active.linked_tests == ("tests/test_calculator.py::test_add",)
    assert audit_traceability(tmp_path, config) == []


def test_manual_activation_requires_explicit_method_prefix(tmp_path: Path) -> None:
    """
    @brief Verify manual-only activation uses the ratified explicit prefix contract.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    record = create_fixed_record(tmp_path, config, linked_tests=())

    with pytest.raises(ValueError, match="Manual"):
        activate_requirement(tmp_path, record.id, [], "Manual inspection", config)

    active = activate_requirement(
        tmp_path,
        record.id,
        [],
        "Inspection: review the generated result",
        config,
        timestamp=UPDATED,
    )
    assert active.status == "Active"


def test_duplicate_ids_across_roots_are_rejected_by_index(tmp_path: Path) -> None:
    """
    @brief Verify duplicate IDs in distinct canonical files are semantic errors.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(
        tmp_path,
        requirement_roots=(".agentic/requirements", ".agentic/imported_requirements"),
    )
    record = create_fixed_record(tmp_path, config, linked_tests=())
    source = tmp_path / record.source_file
    duplicate = tmp_path / ".agentic" / "imported_requirements" / "functional" / source.name
    duplicate.parent.mkdir(parents=True)
    shutil.copyfile(source, duplicate)

    records = load_all_requirements(tmp_path, config)
    with pytest.raises(RequirementValidationError, match="duplicate requirement ID"):
        build_requirement_index(records)


def test_in_memory_reverse_indexes_are_sorted_and_not_persisted(tmp_path: Path) -> None:
    """
    @brief Verify live reverse mappings contain IDs only and create no cache.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    create_fixed_record(tmp_path, config, identifier=UUID_TWO)
    create_fixed_record(tmp_path, config, identifier=UUID_ONE)

    index = load_requirement_index(tmp_path, config)

    assert list(index.by_id) == [REQ_TWO, REQ_ONE]
    assert index.by_test["tests/test_calculator.py::test_add"] == (REQ_TWO, REQ_ONE)
    assert index.by_path["src/calculator.py"] == (REQ_TWO, REQ_ONE)
    assert not (tmp_path / ".agentic" / "registry").exists()
    assert not (tmp_path / ".agentic" / ".workspace" / "cache").exists()


def test_impact_matches_exact_directory_glob_and_current_tests(tmp_path: Path) -> None:
    """
    @brief Verify impact uses shared matching over exact paths, roots, and globs.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.2.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    create_fixed_record(
        tmp_path,
        config,
        affected_paths=("src/calculator.py", "lib", "app/**/*.py"),
    )

    report = impact(
        tmp_path,
        ["src/calculator.py", "lib/math/core.py", "app/ui/view.py", "docs/readme.md"],
        config=config,
    )

    assert [item["file"] for item in report] == [
        "src/calculator.py",
        "lib/math/core.py",
        "app/ui/view.py",
        "docs/readme.md",
    ]
    assert [item["requirements"][0]["id"] for item in report[:3]] == [REQ_ONE] * 3
    assert report[0]["linked_tests"] == ["tests/test_calculator.py::test_add"]
    assert report[3]["requirements"] == []


def test_impact_includes_current_and_previous_git_rename_paths(tmp_path: Path) -> None:
    """
    @brief Verify Git renames expose both names while current snapshots map the new path.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    record = create_fixed_record(tmp_path, config)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )
    (tmp_path / "src" / "calculator.py").rename(
        tmp_path / "src" / "calculator_renamed.py"
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)
    update_requirement(
        tmp_path,
        record.id,
        affected_paths=["src/calculator_renamed.py"],
        config=config,
        timestamp=UPDATED,
    )

    by_path = {entry["file"]: entry for entry in impact(tmp_path, config=config)}

    assert "src/calculator.py" in by_path
    assert "src/calculator_renamed.py" in by_path
    assert by_path["src/calculator.py"]["requirements"] == []
    assert by_path["src/calculator_renamed.py"]["requirements"][0]["id"] == record.id


def test_coverage_uses_active_live_records_and_current_waivers(tmp_path: Path) -> None:
    """
    @brief Verify coverage requires a matching Active record with resolvable tests.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path, coverage=True)
    write_tested_module(tmp_path)
    record = create_fixed_record(tmp_path, config)

    missing = audit_coverage(tmp_path, config)
    assert [issue.code for issue in missing] == ["REQ-COVERAGE-MISSING"]

    activate_requirement(
        tmp_path,
        record.id,
        ["tests/test_calculator.py::test_add"],
        "Automated test",
        config,
        timestamp=UPDATED,
    )
    assert audit_coverage(tmp_path, config) == []

    waiver = tmp_path / ".agentic" / "requirements" / "coverage_waivers.txt"
    waiver.write_text("src/calculator.py\n", encoding="utf-8", newline="\n")
    assert [issue.code for issue in audit_coverage(tmp_path, config)] == [
        "REQ-COVERAGE-STALE-WAIVER"
    ]


def test_selector_resolution_requires_configured_root_and_exact_identifier(tmp_path: Path) -> None:
    """
    @brief Verify exact test selectors cannot escape configured test roots.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)

    assert resolve_test(tmp_path, "tests/test_calculator.py::test_add", config) == (
        True,
        "resolved",
    )
    assert not resolve_test(tmp_path, "src/calculator.py::add", config)[0]
    assert not resolve_test(tmp_path, "tests/test_calculator.py::test_missing", config)[0]


def test_list_filters_current_snapshots(tmp_path: Path) -> None:
    """
    @brief Verify list and show return current records in deterministic ID order.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    create_fixed_record(tmp_path, config, identifier=UUID_ONE, linked_tests=())
    second = create_fixed_record(tmp_path, config, identifier=UUID_TWO, linked_tests=())
    update_requirement(
        tmp_path,
        second.id,
        status="Retired",
        config=config,
        timestamp=UPDATED,
    )

    assert [record.id for record in list_requirements(tmp_path, config=config)] == [
        REQ_TWO,
        REQ_ONE,
    ]
    assert [
        record.id for record in list_requirements(tmp_path, status="Retired", config=config)
    ] == [REQ_TWO]
    assert show_requirement(tmp_path, REQ_ONE, config).status == "Planned"


def test_cli_exposes_snapshot_crud_and_no_registry_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Verify the agent-facing CRUD forms and hard removal of registry CLI.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    configure_repository(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(
        [
            "requirement",
            "create",
            "--category",
            "functional",
            "--priority",
            "Must",
            "--requirement",
            "CLI creation persists one snapshot.",
            "--rationale",
            "Agent-facing contract coverage.",
            "--verification",
            "Inspection: inspect the created snapshot",
            "--affected-path",
            "src/cli.py",
        ]
    )
    created = json.loads(capsys.readouterr().out)
    requirement_id = created["id"]
    assert created["path"].endswith(f"/{requirement_id}.toml")
    assert created["record"]["status"] == "Planned"

    main(["requirement", "show", "--id", requirement_id, "--json"])
    assert json.loads(capsys.readouterr().out)["id"] == requirement_id

    main(
        [
            "requirement",
            "update",
            "--id",
            requirement_id,
            "--priority",
            "Should",
            "--clear-affected-paths",
        ]
    )
    assert json.loads(capsys.readouterr().out)["affected_paths"] == []

    main(["requirement", "list", "--status", "Planned", "--json"])
    assert [item["id"] for item in json.loads(capsys.readouterr().out)] == [
        requirement_id
    ]

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    help_text = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert "registry" not in help_text

    with pytest.raises(SystemExit) as exc_info:
        main(["requirement", "--help"])
    help_text = capsys.readouterr().out
    assert exc_info.value.code == 0
    assert all(command in help_text for command in ("create", "show", "list", "update", "activate"))


def test_cli_activation_updates_snapshot_and_selected_run_journal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Verify activation is the only requirement command that journals to a run.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.2.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    record = create_fixed_record(tmp_path, config, linked_tests=())
    monkeypatch.chdir(tmp_path)

    main(["start", "--kind", "feature", "--statement", "Selected run"])
    selected = json.loads(capsys.readouterr().out)
    main(["start", "--kind", "feature", "--statement", "Pointer run"])
    pointer = json.loads(capsys.readouterr().out)
    main(
        [
            "requirement",
            "activate",
            "--run-id",
            selected["run_id"],
            "--id",
            record.id,
            "--linked-test",
            "tests/test_calculator.py::test_add",
            "--verification",
            "Automated test",
        ]
    )
    activated = json.loads(capsys.readouterr().out)
    selected_journal = (
        tmp_path / ".agentic" / "runs" / selected["run_id"] / "journal.jsonl"
    ).read_text(encoding="utf-8")
    pointer_journal = (
        tmp_path / ".agentic" / "runs" / pointer["run_id"] / "journal.jsonl"
    ).read_text(encoding="utf-8")

    assert activated["status"] == "Active"
    assert '"event": "requirement.activated"' in selected_journal
    assert record.id in selected_journal
    assert '"event": "requirement.activated"' not in pointer_journal


def test_report_and_preflight_need_no_registry_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Verify report and preflight operate only on canonical live data.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest monkeypatch fixture.
    @param[in] capsys Pytest output capture fixture.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.2.0
    """
    configure_repository(tmp_path)
    # Delivery preflight audits the working tree, and an unreadable tree is a
    # blocking finding rather than a pass, so the fixture has to be a real
    # repository for this test to exercise what it is actually about.
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    monkeypatch.chdir(tmp_path)
    main(["start", "--kind", "feature", "--statement", "Live preflight"])
    capsys.readouterr()
    main(
        [
            "record-evidence",
            "--kind",
            "note",
            "--result",
            "info",
            "--summary",
            "Canonical data inspected.",
        ]
    )
    capsys.readouterr()

    main(["report"])
    capsys.readouterr()
    main(["delivery-preflight"])

    assert "Delivery preflight passed." in capsys.readouterr().out
    assert not (tmp_path / ".agentic" / "registry").exists()


def test_inv8_reads_active_requirements_from_live_index(tmp_path: Path) -> None:
    """
    @brief Verify INV-8 reads current TOML snapshots without registry state.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-22
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    record = create_fixed_record(tmp_path, config)
    graph = Graph(
        run_id="feature-2026-07-22T102000Z-1234abcd",
        stage="implementation",
        intent=Intent(id="INTENT-1", kind="feature", statement="Test INV-8"),
        checks=[
            Check(
                id="CHECK-1",
                level="test",
                cites_spec=[],
                cites_requirement=[record.id],
                state="green",
            )
        ],
    )

    planned = next(item for item in evaluate(tmp_path, graph, config) if item.id == "INV-8")
    assert not planned.holds

    activate_requirement(
        tmp_path,
        record.id,
        ["tests/test_calculator.py::test_add"],
        "Automated test",
        config,
        timestamp=UPDATED,
    )
    active = next(item for item in evaluate(tmp_path, graph, config) if item.id == "INV-8")
    assert active.holds


def test_planned_requirement_without_a_test_is_flagged(tmp_path: Path) -> None:
    """
    @brief Verify a non-Retired requirement with no resolvable test is flagged.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-24
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    record = create_fixed_record(tmp_path, config, linked_tests=())

    issues = audit_traceability(tmp_path, config)

    assert [(issue.code, issue.req_id) for issue in issues] == [
        ("REQ-NO-VERIFICATION", record.id)
    ]
    assert record.status == "Planned"
    assert "(Planned)" in issues[0].message


def test_planned_requirement_with_a_resolvable_test_is_not_flagged(tmp_path: Path) -> None:
    """
    @brief Verify a Planned requirement backed by a resolvable test passes traceability.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-24
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    write_tested_module(tmp_path)
    record = create_fixed_record(tmp_path, config)

    assert record.status == "Planned"
    assert audit_traceability(tmp_path, config) == []


def test_planned_requirement_with_manual_method_is_not_flagged(tmp_path: Path) -> None:
    """
    @brief Verify manual verification still exempts a testless non-Retired requirement.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-24
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    create_requirement(
        tmp_path,
        category="functional",
        priority="Must",
        requirement="Generated report is inspected.",
        rationale="Some behavior is only verifiable by inspection.",
        verification="Inspection: inspect the generated report",
        config=config,
        timestamp=CREATED,
    )

    assert audit_traceability(tmp_path, config) == []


def test_retired_requirement_without_a_test_is_not_flagged(tmp_path: Path) -> None:
    """
    @brief Verify Retired requirements are exempt from the verification gate.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-24
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    record = create_fixed_record(tmp_path, config, linked_tests=())
    update_requirement(
        tmp_path,
        record.id,
        status="Retired",
        config=config,
        timestamp=UPDATED,
    )

    assert audit_traceability(tmp_path, config) == []


def test_delivery_preflight_blocks_a_planned_requirement_without_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Verify delivery preflight blocks when a non-Retired requirement has no test.
    @return None.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-24
    @version 0.1.0
    """
    config = configure_repository(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    create_fixed_record(tmp_path, config, linked_tests=())
    monkeypatch.chdir(tmp_path)
    main(["start", "--kind", "feature", "--statement", "Preflight blocks untested requirement"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc_info:
        main(["delivery-preflight"])

    assert exc_info.value.code == 1
    assert "REQ-NO-VERIFICATION" in capsys.readouterr().out


# END OF FILE
