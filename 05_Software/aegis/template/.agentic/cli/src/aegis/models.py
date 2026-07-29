#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file models.py
@brief Data models used by the schema-version-3 workflow state graph.
@details Defines the authoritative eight-stage run graph. Schema-version-2
         graphs and legacy fields are rejected rather than migrated.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

# DATA MODELS / TYPEDEFINITIONS

RunKind = Literal["feature", "fix", "change", "adoption"]

Stage = Literal[
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
    "delivery",
    "adoption-intake",
    "adoption-alignment",
    "repo-discovery",
    "component-map",
    "component-adoption",
    "baseline-review",
    "adoption-delivery",
]

AccessMode = Literal["standard", "repo-wide"]
AlignmentRisk = Literal["low", "medium", "high"]
AlignmentDecision = Literal["proceed", "pause"]

# CONSTANTS

STAGES: list[Stage] = [
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
    "delivery",
]

ADOPTION_STAGES: list[Stage] = [
    "adoption-intake",
    "adoption-alignment",
    "repo-discovery",
    "component-map",
    "component-adoption",
    "baseline-review",
    "adoption-delivery",
]

ALL_STAGES: list[Stage] = [*STAGES, *ADOPTION_STAGES]

# HELPER FUNCTIONS


def now_iso() -> str:
    """
    @brief      Handle now iso workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# DATA MODELS / TYPEDEFINITIONS


@dataclass
class Intent:
    """
    @brief      Represent Intent data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    id: str
    kind: RunKind
    statement: str
    scope_hint: list[str] = field(default_factory=list)
    status: str = "draft"
    created_at: str = field(default_factory=now_iso)


@dataclass
class IntentAlignment:
    """
    @brief      Represent an intent-alignment record for a workflow run.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    source: str
    understanding: str
    scope: list[str]
    assumptions: list[str]
    acceptance: list[str]
    open_questions: list[str]
    recommended_responses: list[str]
    risk: AlignmentRisk
    decision: AlignmentDecision
    reason: str
    planned_paths: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)


@dataclass
class SpecItem:
    """
    @brief      Represent SpecItem data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    id: str
    tag: Literal["behavior", "property"]
    statement: str
    status: Literal["proposed", "accepted", "realized", "retired"] = "proposed"
    examples: list[str] = field(default_factory=list)
    threshold: str | None = None


@dataclass
class Check:
    """
    @brief      Represent Check data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    id: str
    level: str
    cites_spec: list[str]
    cites_requirement: list[str] = field(default_factory=list)
    command: str | None = None
    path: str | None = None
    state: Literal["red", "green", "unknown"] = "unknown"
    red_evidence: str | None = None
    green_evidence: str | None = None
    contract_variants: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    parity_targets: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    """
    @brief      Represent Evidence data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    id: str
    kind: Literal["test-run", "diff", "scan", "gate", "decision", "note"]
    result: Literal["pass", "fail", "info"]
    summary: str
    status: Literal["active", "superseded"] = "active"
    failure_kind: str | None = None
    superseded_by: str | None = None
    supersede_reason: str | None = None
    command: str | None = None
    path: str | None = None
    stage: str | None = None
    check_id: str | None = None
    gate_name: str | None = None
    exit_status: int | None = None
    output_log: str | None = None
    created_at: str = field(default_factory=now_iso)


@dataclass
class ChangeUnit:
    """
    @brief      Represent ChangeUnit data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    id: str
    touched_paths: list[str]


@dataclass
class Decision:
    """
    @brief      Represent Decision data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    id: str
    question: str
    chosen: str
    rationale: str
    approver: str = "human"
    created_at: str = field(default_factory=now_iso)


@dataclass
class StageRecord:
    """
    @brief      Represent the authoritative imported state for one stage.
    @details    The captured interface policy applies to this prepared revision
                even when workspace configuration changes before import.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """

    stage: Stage
    revision: int
    status: Literal["prepared", "applied", "closed"]
    retention: Literal["versioned", "latest", "discard"]
    check_execution: Literal["external", "managed"]
    digest: str = ""
    artifact: str = ""
    summary: str = ""
    unresolved_questions: list[str] = field(default_factory=list)
    requested_access_mode: str = ""
    access_rationale: str = ""
    route_to: str = ""
    route_rationale: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    prepared_at: str = field(default_factory=now_iso)
    applied_at: str | None = None
    closed_at: str | None = None


@dataclass
class SolutionDesign:
    """
    @brief      Represent one authoritative solution-design proposal.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-29
    @version    0.1.0
    """

    revision: int
    status: Literal["proposed", "approved", "stale"]
    document_path: str
    document_digest: str
    requirement_digests: dict[str, str]
    selected_option: str
    open_questions: list[str] = field(default_factory=list)
    approval: Literal["none", "human", "stale"] = "none"
    proposed_at: str = field(default_factory=now_iso)
    approved_at: str | None = None


@dataclass
class Graph:
    """
    @brief      Represent Graph data used by the workflow.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    1.0.0
    """
    run_id: str
    stage: Stage
    intent: Intent
    schema_version: int = 3
    access_mode: AccessMode = "standard"
    complete: bool = False
    alignment: IntentAlignment | None = None
    design: SolutionDesign | None = None
    spec_items: list[SpecItem] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    change_units: list[ChangeUnit] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    stage_records: dict[str, StageRecord] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Handle to dict workflow behavior.
        @return     Result produced by the workflow helper.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-06-20
        @version    0.4.0
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Graph":
        """
        @brief      Load one strict schema-version-3 graph mapping.
        @param[in]  data Input value used by the workflow helper.
        @return     Parsed graph using only the current persisted contract.
        @exception  ValueError If the graph is not an exact schema-3 document.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-29
        @version    1.0.0
        """
        expected = {
            "run_id",
            "stage",
            "intent",
            "schema_version",
            "access_mode",
            "complete",
            "alignment",
            "design",
            "spec_items",
            "checks",
            "evidence",
            "change_units",
            "decisions",
            "stage_records",
        }
        if data.get("schema_version") != 3:
            raise ValueError(
                "unsupported run graph schema; AEGIS 2.0 requires schema_version 3"
            )
        unknown = sorted(set(data) - expected)
        missing = sorted(expected - set(data))
        if unknown or missing:
            detail = (
                f"unknown keys: {', '.join(unknown)}"
                if unknown
                else f"missing keys: {', '.join(missing)}"
            )
            raise ValueError(f"invalid schema-3 run graph: {detail}")
        alignment = data["alignment"]
        design = data["design"]
        return cls(
            run_id=data["run_id"],
            stage=data["stage"],
            intent=Intent(**data["intent"]),
            schema_version=3,
            access_mode=data["access_mode"],
            complete=data["complete"],
            alignment=IntentAlignment(**alignment) if alignment else None,
            design=SolutionDesign(**design) if design else None,
            spec_items=[SpecItem(**item) for item in data["spec_items"]],
            checks=[Check(**item) for item in data["checks"]],
            evidence=[Evidence(**item) for item in data["evidence"]],
            change_units=[ChangeUnit(**item) for item in data["change_units"]],
            decisions=[Decision(**item) for item in data["decisions"]],
            stage_records={
                name: StageRecord(**record)
                for name, record in data["stage_records"].items()
            },
        )


# END OF FILE
