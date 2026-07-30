#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file verification.py
@brief Consolidated deterministic verification orchestration.
@details Runs impact selection, every enabled gate group, invariants,
         traceability, coverage, and working-tree review before producing the
         human diff-review input summary.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .config import GATE_ORDER, WorkflowConfig
from .errors import CommandInputError
from .gates import run_gates
from .invariants import blocking_failures, evaluate
from .models import Graph, now_iso
from .requirements import audit_coverage, audit_traceability, impact
from .store import append_journal, load_graph, run_dir
from .working_tree import audit_working_tree

# PUBLIC API


def run_verification(
    repo_root: Path,
    graph: Graph,
    config: WorkflowConfig,
    timeout: int = 300,
) -> tuple[dict[str, Any], int]:
    """
    @brief      Execute the complete deterministic verification sequence.
    @param[in]  repo_root Repository root.
    @param[in]  graph Active workflow graph.
    @param[in]  config Validated workspace configuration.
    @param[in]  timeout Per-command gate timeout.
    @return     Validation summary and aggregate exit code.
    @version    0.1.0
    """
    impact_report = impact(repo_root, None, config=config)
    selection = _regression_selection(impact_report)
    gate_code = run_gates(
        repo_root,
        graph.run_id,
        config,
        list(GATE_ORDER),
        timeout,
    )
    graph = load_graph(repo_root, graph.run_id)
    invariant_results = evaluate(repo_root, graph, config)
    traceability = audit_traceability(repo_root, config)
    coverage = audit_coverage(repo_root, config)
    working_tree = audit_working_tree(repo_root, config, graph)
    gate_status = {
        name: {
            "status": (
                "disabled"
                if getattr(config.gates, name).mode == "disabled"
                else _gate_result(graph, name)
            ),
            "commands": list(getattr(config.gates, name).commands),
        }
        for name in GATE_ORDER
    }
    summary = {
        "schema_version": 3,
        "run_id": graph.run_id,
        "generated_at": now_iso(),
        "sequence": [
            "impact",
            "gates",
            "invariants",
            "traceability",
            "coverage",
            "working-tree",
        ],
        "regression_selection": selection,
        "impact": impact_report,
        "gates": gate_status,
        "security_note": (
            "The security gate reports only explicitly configured deterministic "
            "tooling and is not an authoritative security-assurance claim."
        ),
        "invariants": [asdict(item) for item in invariant_results],
        "traceability": [asdict(item) for item in traceability],
        "coverage": [asdict(item) for item in coverage],
        "working_tree": working_tree,
        "human_diff_review": "pending",
    }
    path = validation_summary_path(repo_root, graph)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    failed = bool(
        gate_code
        or blocking_failures(invariant_results)
        or traceability
        or coverage
        or working_tree["blocking_findings"]
    )
    append_journal(
        repo_root,
        graph.run_id,
        "verification.completed",
        {
            "summary": path.relative_to(repo_root).as_posix(),
            "status": "failed" if failed else "ok",
        },
    )
    return summary, 1 if failed else 0


def validation_summary_path(repo_root: Path, graph: Graph) -> Path:
    """
    @brief      Return the durable validation summary path.
    @return     Run-local JSON summary path.
    @version    0.1.0
    """
    return run_dir(repo_root, graph.run_id) / "validation-summary.json"


def read_validation_summary(repo_root: Path, graph: Graph) -> dict[str, Any]:
    """
    @brief      Read the most recent validation summary.
    @exception  CommandInputError If the summary is missing or malformed.
    @version    0.2.0
    """
    path = validation_summary_path(repo_root, graph)
    if not path.is_file():
        raise CommandInputError("no validation summary; run `aegis verify run`")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandInputError(
            f"cannot load validation summary {path}: {exc}"
        ) from exc


# LOCAL HELPERS


def _regression_selection(report: list[dict[str, Any]]) -> dict[str, Any]:
    """@brief Select focused or full regression from traceability impact."""
    linked = sorted(
        {
            test
            for item in report
            for test in item.get("linked_tests", [])
        }
    )
    untraced = sorted(
        item["file"]
        for item in report
        if not item.get("requirements")
    )
    full = bool(
        untraced
        or any(item.get("full_regression_recommended") for item in report)
        or len(report) > 10
    )
    reasons: list[str] = []
    if untraced:
        reasons.append("untraced changed paths")
    if len(report) > 10:
        reasons.append("cross-cutting change set")
    if any(item.get("full_regression_recommended") for item in report):
        reasons.append("coverage policy recommends full regression")
    return {
        "mode": "full" if full else "focused",
        "linked_tests_first": linked,
        "full_regression_reasons": reasons,
        "untraced_paths": untraced,
    }


def _gate_result(graph: Graph, name: str) -> str:
    """@brief Summarize active evidence for one enforced gate group."""
    evidence = [
        item
        for item in graph.evidence
        if item.kind == "gate"
        and item.gate_name == name
        and item.status == "active"
    ]
    if not evidence:
        return "not-run"
    return "failed" if any(item.result == "fail" for item in evidence) else "passed"


# END OF FILE
