#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_aegis_v2_policy.py
@brief Policy and deterministic-execution tests for AEGIS 2.0.
@details Covers strict schema rejection, versioned form retention, captured
         check modes, managed red/green evidence, five-group gate ordering,
         execute-all failure behavior, and launch/timeout evidence semantics.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

from aegis.check_execution import prepare_check_evidence, run_checks
from aegis.cli import main
from aegis.config import ConfigurationError, GATE_ORDER, load_config
from aegis.gates import _run_command, run_gates
from aegis.invariants import evaluate
from aegis.models import Check, Graph, Intent, SolutionDesign, StageRecord
from aegis.requirement_store import RequirementRecord, publish_requirement_records
from aegis.stage_forms import StageOperationError, close_stage, stage_blockers
from aegis.store import init_graph, load_graph, save_graph

# TESTS


def test_schema_two_configuration_is_rejected_before_use(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Confirm there is no schema-2 configuration reader."""
    replace_workflow_toml("schema_version = 3", "schema_version = 2")
    with pytest.raises(ConfigurationError, match="schema_version = 3"):
        load_config(tmp_path)


def test_versioned_retention_preserves_applied_revision_and_digest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Preserve a complete applied form revision under versioned policy."""
    replace_workflow_toml(
        'stage_form_retention = "discard"',
        'stage_form_retention = "versioned"',
    )
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    started = json.loads(capsys.readouterr().out)
    form = tmp_path / started["artifact"]
    text = form.read_text(encoding="utf-8")
    text = text.replace('statement = ""', 'statement = "Version forms"')
    text = text.replace('summary = ""', 'summary = "Intent imported"')
    form.write_text(text, encoding="utf-8")
    main(["stage", "apply", "--json"])
    capsys.readouterr()

    revision = form.parent / "revisions" / "0001"
    assert (revision / "intake.toml").is_file()
    digest = json.loads((revision / "digest.json").read_text(encoding="utf-8"))
    graph = load_graph(tmp_path, started["run_id"])
    assert digest["sha256"] == graph.stage_records["intake"].digest


def test_managed_mode_records_red_then_green_and_rejects_external_path(
    tmp_path: Path,
) -> None:
    """@brief Enforce one captured check mode and retain red-before-green state."""
    marker = tmp_path / "implemented.flag"
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from pathlib import Path\n"
        "raise SystemExit(0 if Path('implemented.flag').exists() else 1)\n",
        encoding="utf-8",
    )
    command = f'"{sys.executable}" probe.py'
    check = Check(
        id="CHK-e06de81b-5ef9-4720-bc75-bcefb63ea793",
        level="test",
        cites_spec=[],
        cites_requirement=["REQ-FUNC-8b11c230-cab4-4e33-b357-7f95bf8c5571"],
        command=command,
    )
    graph = Graph(
        run_id="fix-20260729T120000Z-fedcba98",
        stage="check",
        intent=Intent(id="I-2", kind="fix", statement="Managed evidence"),
        checks=[check],
        stage_records={
            "check": StageRecord(
                stage="check",
                revision=1,
                status="applied",
                retention="discard",
                check_execution="managed",
            )
        },
    )
    save_graph(tmp_path, graph)
    with pytest.raises(StageOperationError, match="mode is managed.*check run"):
        prepare_check_evidence(tmp_path, graph)

    red = run_checks(tmp_path, graph)
    assert [(item.result, item.exit_status) for item in red] == [("fail", 1)]
    assert graph.checks[0].state == "red"
    marker.write_text("ready\n", encoding="utf-8")
    graph.stage = "implementation"
    graph.stage_records["implementation"] = StageRecord(
        stage="implementation",
        revision=1,
        status="applied",
        retention="discard",
        check_execution="managed",
    )
    green = run_checks(tmp_path, graph)
    assert [(item.result, item.exit_status) for item in green] == [("pass", 0)]
    assert graph.checks[0].red_evidence == "E-0001"
    assert graph.checks[0].green_evidence == "E-0002"

    graph.stage_records["implementation"].check_execution = "external"
    with pytest.raises(StageOperationError, match="mode is external.*check prepare"):
        run_checks(tmp_path, graph)


def test_gate_groups_run_in_fixed_order_and_continue_after_failure(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Run all five enforced groups even when an earlier group fails."""
    probe = tmp_path / "gate_probe.py"
    probe.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "with Path('gate-order.txt').open('a', encoding='utf-8') as stream:\n"
        "    stream.write(sys.argv[1] + '\\n')\n"
        "raise SystemExit(1 if sys.argv[1] == 'typecheck' else 0)\n",
        encoding="utf-8",
    )
    for name in GATE_ORDER:
        old = f'[gates.{name}]\nmode = "disabled"\ncommands = []'
        command = f'"{sys.executable}" gate_probe.py {name}'
        new = f'[gates.{name}]\nmode = "enforce"\ncommands = [{json.dumps(command)}]'
        replace_workflow_toml(old, new)
    config = load_config(tmp_path)
    graph = init_graph(tmp_path, "feature", "Gate ordering")

    exit_code = run_gates(tmp_path, graph.run_id, config)
    assert exit_code == 1
    assert (tmp_path / "gate-order.txt").read_text(encoding="utf-8").splitlines() == list(
        GATE_ORDER
    )
    reloaded = load_graph(tmp_path, graph.run_id)
    assert [item.gate_name for item in reloaded.evidence] == list(GATE_ORDER)
    assert [item.result for item in reloaded.evidence] == [
        "pass",
        "fail",
        "pass",
        "pass",
        "pass",
    ]


def test_command_launch_and_timeout_become_deterministic_failures(
    tmp_path: Path,
) -> None:
    """@brief Convert missing executables and timeouts into exit evidence values."""
    missing = _run_command(tmp_path, "aegis-executable-that-does-not-exist", 5)
    assert missing.returncode == 127
    timed_out = _run_command(
        tmp_path,
        f'"{sys.executable}" -c "import time; time.sleep(2)"',
        1,
    )
    assert timed_out.returncode == 124


def test_design_approval_becomes_invalid_when_authoritative_document_changes(
    tmp_path: Path,
) -> None:
    """@brief Enforce design approval and document digest integrity from check."""
    config = load_config(tmp_path)
    run_id = "feature-20260729T130000Z-abcdef12"
    requirement_id = "REQ-FUNC-448e988e-4f3a-4ec6-9d37-a56f05893174"
    spec = tmp_path / ".agentic" / "runs" / run_id / "requirements" / f"{requirement_id}.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# Observable contract\n", encoding="utf-8")
    linked_test = tmp_path / "tests" / "test_state.py"
    linked_test.parent.mkdir(parents=True, exist_ok=True)
    linked_test.write_text(
        "def test_state_is_stable():\n    assert True\n",
        encoding="utf-8",
    )
    published = publish_requirement_records(
        tmp_path,
        [
            RequirementRecord(
                schema_version=1,
                id=requirement_id,
                category="functional",
                status="Planned",
                priority="Must",
                requirement="The result is stable.",
                rationale="Users depend on stable state.",
                verification="Run the linked deterministic check.",
                spec_ref=spec.relative_to(tmp_path).as_posix(),
                affected_paths=("src/state.py",),
                linked_tests=("tests/test_state.py::test_state_is_stable",),
                created_on="2026-07-29T13:00:00Z",
                last_updated="2026-07-29T13:00:00Z",
            )
        ],
        config,
    )[0]
    design_path = tmp_path / ".agentic" / "runs" / run_id / "design.md"
    design_path.parent.mkdir(parents=True, exist_ok=True)
    design_path.write_text("# Design\n\nUse a transaction.\n", encoding="utf-8")
    requirement_path = tmp_path / str(published.source_file)
    graph = Graph(
        run_id=run_id,
        stage="design",
        intent=Intent(id="I-3", kind="feature", statement="Stable results"),
        design=SolutionDesign(
            revision=1,
            status="proposed",
            document_path=design_path.relative_to(tmp_path).as_posix(),
            document_digest=sha256(design_path.read_bytes()).hexdigest(),
            requirement_digests={
                requirement_id: sha256(requirement_path.read_bytes()).hexdigest()
            },
            selected_option="Transactional update",
        ),
        stage_records={
            "design": StageRecord(
                stage="design",
                revision=1,
                status="applied",
                retention="discard",
                check_execution="external",
            )
        },
    )
    save_graph(tmp_path, graph)
    assert stage_blockers(tmp_path, graph) == []
    graph, _ = close_stage(tmp_path, graph, config)
    assert graph.stage == "check"
    assert graph.design is not None
    assert graph.design.status == "approved"
    assert graph.design.approval == "human"
    assert next(item for item in evaluate(tmp_path, graph, config) if item.id == "INV-10").holds

    design_path.write_text("# Design\n\nChanged after approval.\n", encoding="utf-8")
    inv_10 = next(item for item in evaluate(tmp_path, graph, config) if item.id == "INV-10")
    assert not inv_10.holds
    assert "design.md digest changed" in inv_10.message


# END OF FILE
