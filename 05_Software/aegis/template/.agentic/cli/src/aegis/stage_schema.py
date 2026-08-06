#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file stage_schema.py
@brief Declarative lifecycle and field schemas for AEGIS stage forms.
@details Defines run-profile sequences plus field order, value kind, presence,
         defaults, and maintenance help metadata consumed by stage handling.
"""

# IMPORTS

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
import uuid

from .models import (
    ADOPTION_STAGES,
    QUICK_STAGES,
    STAGES,
    Graph,
    RunKind,
    RunProfile,
    Stage,
)

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class StageFieldSpec:
    """
    @brief Describe one declarative single-stage form field.
    @details The default may be an immutable value or a graph-aware callable.
             Help text is rendered as a TOML comment above the field, together
             with `accepted` when the field takes a closed token set: a bare
             `diff_review = "pending"` gave the agent no way to learn that only
             `pass` and `not-applicable` clear the blocker, which cost a failed
             close and a guess per field.
    """

    name: str
    kind: Literal["string", "array", "bool"]
    default: Any
    help: str
    accepted: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunStageSpec:
    """
    @brief Describe one valid kind/profile lifecycle sequence.
    @details Bypassed stages are explicit audit states, not successful stages.
    """

    stages: tuple[Stage, ...]
    bypassed_stages: tuple[Stage, ...] = ()


class StageOperationError(ValueError):
    """
    @brief Describe an actionable stage-form or lifecycle failure.
    """


# DECLARATIVE RUN SCHEMA

_STANDARD_RUN_SPEC = RunStageSpec(tuple(STAGES))
_ADOPTION_RUN_SPEC = RunStageSpec(tuple(ADOPTION_STAGES))
_QUICK_RUN_SPEC = RunStageSpec(
    tuple(QUICK_STAGES),
    tuple(stage for stage in STAGES if stage not in QUICK_STAGES),
)
RUN_STAGE_SCHEMAS: dict[tuple[RunKind, RunProfile], RunStageSpec] = {
    ("feature", "full"): _STANDARD_RUN_SPEC,
    ("fix", "full"): _STANDARD_RUN_SPEC,
    ("change", "full"): _STANDARD_RUN_SPEC,
    ("adoption", "full"): _ADOPTION_RUN_SPEC,
    ("fix", "quick"): _QUICK_RUN_SPEC,
    ("change", "quick"): _QUICK_RUN_SPEC,
}


def run_stage_spec(graph: Graph) -> RunStageSpec:
    """
    @brief Resolve and validate the declarative lifecycle for one graph.
    @param[in] graph Candidate graph loaded from durable or in-memory state.
    @return Matching run-stage schema.
    @exception StageOperationError If kind, profile, stage, or records conflict.
    """
    try:
        spec = RUN_STAGE_SCHEMAS.get((graph.intent.kind, graph.profile))
    except TypeError:
        spec = None
    if spec is None:
        raise StageOperationError(
            "run kind/profile mismatch: "
            f"kind {graph.intent.kind!r} cannot use profile {graph.profile!r}"
        )
    if graph.stage not in spec.stages:
        raise StageOperationError(
            f"stage {graph.stage!r} is not valid for a "
            f"{graph.intent.kind!r}/{graph.profile!r} run"
        )
    invalid_records = sorted(set(graph.stage_records) - set(spec.stages))
    if invalid_records:
        raise StageOperationError(
            "stage records conflict with the run profile: "
            + ", ".join(invalid_records)
        )
    mismatched_records = sorted(
        name
        for name, record in graph.stage_records.items()
        if record.stage != name
    )
    if mismatched_records:
        raise StageOperationError(
            "stage-record identity mismatch: " + ", ".join(mismatched_records)
        )
    invalid_routes = sorted(
        (
            name,
            record.route_to,
        )
        for name, record in graph.stage_records.items()
        if not isinstance(record.route_to, str)
        or (
            record.route_to
            and (
                record.route_to not in spec.stages
                or spec.stages.index(record.route_to)
                >= spec.stages.index(record.stage)
            )
        )
    )
    if invalid_routes:
        details = ", ".join(
            f"{stage} -> {route!r}" for stage, route in invalid_routes
        )
        raise StageOperationError(
            "stage-record route conflicts with the run profile: " + details
        )
    return spec


# DECLARATIVE STAGE SCHEMA

REQUIRED_STAGE_VALUE = object()
# Accepted token sets, declared once so the form help an agent reads and the
# validation `stage apply` performs cannot drift apart.
ALIGNMENT_RISKS = ("low", "medium", "high")
ALIGNMENT_DECISIONS = ("proceed", "pause")
REVIEW_DECISIONS = ("pending", "pass", "not-applicable")
PENDING_OR_APPROVED = ("pending", "approved")
_ALIGNMENT_FIELDS = (
    StageFieldSpec("understanding", "string", "", "Problem understanding."),
    StageFieldSpec("in_scope", "array", (), "Included scope."),
    StageFieldSpec("out_of_scope", "array", (), "Excluded scope."),
    StageFieldSpec("assumptions", "array", (), "Assumptions."),
    StageFieldSpec("acceptance_criteria", "array", (), "Acceptance criteria."),
    StageFieldSpec("questions", "array", (), "Open questions."),
    StageFieldSpec("recommended_answers", "array", (), "Recommended answers."),
    StageFieldSpec("planned_paths", "array", (), "Planned paths."),
    StageFieldSpec("risk", "string", "low", "Risk level.", ALIGNMENT_RISKS),
    StageFieldSpec(
        "decision", "string", "proceed", "Decision.", ALIGNMENT_DECISIONS
    ),
)
_DELIVERY_FIELDS = (
    # Renamed from `preflight` (D5, 2026-08-04): the word was overloaded three
    # ways across the payload - this form field, the `delivery_preflight.py`
    # hook, and the working-tree audit's own "delivery preflight" concept -
    # with no `aegis delivery preflight` command tying them together. The
    # field itself is just a free-text reference the operator records, so
    # `preflight_reference` names what it actually holds without colliding
    # with the other two meanings.
    StageFieldSpec("preflight_reference", "string", "", "Preflight reference."),
    StageFieldSpec("report", "string", "", "Report reference."),
    StageFieldSpec(
        "decision",
        "string",
        "pending",
        "Handoff decision; the run cannot close until it is approved.",
        PENDING_OR_APPROVED,
    ),
)
STAGE_FIELD_SPECS: dict[Stage, tuple[StageFieldSpec, ...]] = {
    "intake": (
        StageFieldSpec(
            "statement", "string", lambda graph: graph.intent.statement, "Intent."
        ),
        StageFieldSpec(
            "scope_hints", "array", lambda graph: graph.intent.scope_hint, "Scope."
        ),
        StageFieldSpec(
            "access_mode", "string", lambda graph: graph.access_mode, "Access mode."
        ),
    ),
    "alignment": _ALIGNMENT_FIELDS,
    "design": (
        StageFieldSpec(
            "document", "string", REQUIRED_STAGE_VALUE, "Design document."
        ),
        StageFieldSpec("cited_requirement_ids", "array", (), "Cited requirements."),
        StageFieldSpec("selected_option", "string", "", "Selected option."),
    ),
    "implementation": (
        StageFieldSpec(
            "change_unit_id",
            "string",
            lambda _graph: f"CU-{uuid.uuid4()}",
            "Change-unit ID.",
        ),
        StageFieldSpec("changed_paths", "array", (), "Changed paths."),
        StageFieldSpec("documentation_effects", "array", (), "Documentation effects."),
        StageFieldSpec("linked_check_evidence", "array", (), "Check evidence."),
    ),
    "validation": (
        StageFieldSpec(
            "deterministic_verification",
            "array",
            (),
            "References to the verification runs that back this stage, such as"
            " an evidence ID or a validation-summary path; at least one is"
            " required to close.",
        ),
        StageFieldSpec(
            "diff_review", "string", "pending", "Diff review.", REVIEW_DECISIONS
        ),
        StageFieldSpec(
            "documentation_review",
            "string",
            "pending",
            "Docs review.",
            REVIEW_DECISIONS,
        ),
        StageFieldSpec(
            "style_review", "string", "pending", "Style review.", REVIEW_DECISIONS
        ),
        StageFieldSpec("manual_evidence", "array", (), "Manual evidence."),
        StageFieldSpec("approved_supersessions", "array", (), "Supersessions."),
    ),
    "delivery": _DELIVERY_FIELDS,
    "adoption-intake": (
        StageFieldSpec(
            "statement", "string", lambda graph: graph.intent.statement, "Intent."
        ),
        StageFieldSpec("adoption_slice", "string", "", "Adoption slice."),
        StageFieldSpec("bundle_components", "array", (), "Bundle components."),
        StageFieldSpec("bundle_rationale", "string", "", "Bundle rationale."),
        StageFieldSpec(
            "access_mode", "string", lambda graph: graph.access_mode, "Access mode."
        ),
    ),
    "adoption-alignment": _ALIGNMENT_FIELDS,
    "repo-discovery": (
        StageFieldSpec("source_roots", "array", (), "Source roots."),
        StageFieldSpec("test_roots", "array", (), "Test roots."),
        StageFieldSpec("requirement_roots", "array", (), "Requirement roots."),
        StageFieldSpec("documentation_roots", "array", (), "Documentation roots."),
        StageFieldSpec("gate_commands", "array", (), "Gate commands."),
        StageFieldSpec("candidate_components", "array", (), "Candidate components."),
        StageFieldSpec("external_dependencies", "array", (), "Dependencies."),
        StageFieldSpec("entry_points", "array", (), "Entry points."),
        StageFieldSpec("existing_tests", "array", (), "Existing tests."),
        StageFieldSpec("discovery_evidence", "array", (), "Discovery evidence."),
        StageFieldSpec("repowise_warnings", "array", (), "RepoWise warnings."),
        StageFieldSpec("repowise_status", "string", "disabled", "RepoWise status."),
    ),
    "component-map": (
        StageFieldSpec(
            "manifest", "string", ".agentic/components.toml", "Manifest path."
        ),
        StageFieldSpec("components", "array", (), "Mapped components."),
        StageFieldSpec("approved_slice", "array", (), "Approved slice."),
        StageFieldSpec(
            "approval_decision",
            "string",
            "pending",
            "Decision.",
            PENDING_OR_APPROVED,
        ),
    ),
    "component-adoption": (
        StageFieldSpec("adopted_components", "array", (), "Adopted components."),
        StageFieldSpec("changed_paths", "array", (), "Changed paths."),
        StageFieldSpec("documentation", "array", (), "Documentation."),
        StageFieldSpec("requirement_links", "array", (), "Requirement links."),
        StageFieldSpec("remaining_gaps", "array", (), "Remaining gaps."),
        StageFieldSpec("behavior_changed", "bool", False, "Behavior changed."),
    ),
    "baseline-review": (
        StageFieldSpec("reviewed_components", "array", (), "Reviewed components."),
        StageFieldSpec("blocking_gaps", "array", (), "Blocking gaps."),
        StageFieldSpec("follow_up_gaps", "array", (), "Follow-up gaps."),
        StageFieldSpec("accepted_legacy_risks", "array", (), "Accepted risks."),
        StageFieldSpec(
            "decision", "string", "pending", "Decision.", PENDING_OR_APPROVED
        ),
    ),
    "adoption-delivery": _DELIVERY_FIELDS,
}

# END OF FILE
