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
@file    stage_expectations.py
@brief   Evaluate the common structural Stage-completion contract.
@details Reports only missing records, unresolved designated references,
         invalid recorded command outcomes, and applicable approval state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STAGE_SECTION_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "intake": (
        "inputs", "configured_project_paths", "relevant_project_knowledge",
        "restated_ask", "initially_affected_repository_area",
        "facts_and_uncertainties", "outputs_and_handoff",
    ),
    "alignment": (
        "inputs_from_intake", "proposed_scope", "developer_corrections",
        "agreed_scope", "outputs_and_handoff",
    ),
    "requirement": (
        "inputs_from_alignment", "requirement_artifact_changes", "traceability",
        "risk_based_test_depth_decision", "gaps_and_uncertainties",
        "outputs_and_handoff",
    ),
    "design": (
        "inputs", "proposed_solution", "requirement_coverage",
        "interfaces_data_and_failure_behavior", "alternatives_and_risks",
        "outputs_and_handoff",
    ),
    "check": (
        "inputs", "test_work", "recorded_red_evidence",
        "test_fingerprints_at_red", "red_before_green_decision",
        "outputs_and_handoff",
    ),
    "implementation": (
        "inputs", "implementation_changes", "test_integrity_comparison",
        "implementation_evidence", "component_documentation_review",
        "outputs_and_handoff",
    ),
    "validation": (
        "inputs", "impacted_test_selection", "automated_validation_evidence",
        "manual_validation_evidence", "test_integrity_conclusion",
        "outputs_and_handoff",
    ),
    "delivery": (
        "requested_and_delivered_outcome", "project_artifact_changes",
        "implementation_changes", "evidence_summary", "test_integrity",
        "findings_and_residual_risk", "skips_waivers_and_omitted_stages",
        "component_drift_review", "delivery_decision", "terminal_result",
    ),
}

PROFILE_STAGES = {
    "full": tuple(STAGE_SECTION_EXPECTATIONS),
    "short": tuple(stage for stage in STAGE_SECTION_EXPECTATIONS if stage != "design"),
}

_APPROVAL_STAGES = frozenset({"alignment", "requirement", "design", "delivery"})
_OUTCOMES = frozenset({"passed", "failed", "timed_out", "cancelled", "launch_error"})


@dataclass(frozen=True)
class StageExpectationEvaluation:
    """@brief Findings and exact structural-check count for one Stage."""

    findings: tuple[dict[str, str], ...]
    evaluated_expectation_count: int


def _finding(
    code: str,
    observation: str,
    consequence: str,
    *,
    expectation: str,
) -> dict[str, str]:
    """@return One label-free structural finding for application publication."""
    return {
        "code": code,
        "severity": "warning",
        "observation": observation,
        "consequence": consequence,
        "disposition": "open",
        "expectation": expectation,
    }


def _is_recorded(value: Any) -> bool:
    """@return Whether a required section contains a non-blank recorded value."""
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower() != "none"
    )


def _valid_red_witness(item: dict[str, Any], *, implementation_started_at: str) -> bool:
    """@return Whether durable evidence contains a complete prior red witness."""
    fingerprints = item.get("fingerprints")
    timestamp = item.get("time")
    return (
        item.get("red_witness") is True
        and isinstance(fingerprints, dict)
        and bool(fingerprints)
        and isinstance(timestamp, str)
        and bool(timestamp)
        and (not implementation_started_at or timestamp < implementation_started_at)
    )


def _valid_red_exception(decisions: list[dict[str, Any]]) -> dict[str, Any] | None:
    """@return The latest complete approved red non-applicability, if any."""
    latest = next(
        (
            item
            for item in reversed(decisions)
            if item.get("target") == "red_before_green"
        ),
        None,
    )
    if latest is None or latest.get("value") != "exception_approved":
        return None
    if not all(
        isinstance(latest.get(field), str) and latest[field].strip()
        for field in ("reason", "alternative_confirmation")
    ):
        return None
    return latest


def summarize_red_before_green_state(
    state: dict[str, Any], *, implementation_started_at: str
) -> dict[str, bool]:
    """@return Factual flags for Delivery reporting without judging adequacy."""
    evidence = [item for item in state.get("evidence", []) if isinstance(item, dict)]
    decisions = [item for item in state.get("decisions", []) if isinstance(item, dict)]
    return {
        "valid_witness": any(
            _valid_red_witness(
                item, implementation_started_at=implementation_started_at
            )
            for item in evidence
        ),
        "approved_exception": _valid_red_exception(decisions) is not None,
    }


def evaluate_stage_expectations(
    *,
    stage: str,
    profile: str,
    state: dict[str, Any],
    designated_references: tuple[tuple[str, bool], ...] = (),
    continuous_delegation: bool = False,
) -> StageExpectationEvaluation:
    """
    @brief Evaluate one included Stage using only the common structural checks.
    @param[in] stage Canonical Stage name.
    @param[in] profile Full or short Run profile.
    @param[in] state Current durable Stage state.
    @param[in] designated_references Reference paths and their resolved state.
    @param[in] continuous_delegation Whether durable Run authority is continuous.
    @return Ordered structural findings and exact check count.
    """
    if stage not in PROFILE_STAGES.get(profile, ()):
        return StageExpectationEvaluation((), 0)
    findings: list[dict[str, str]] = []
    sections = state.get("sections")
    if not isinstance(sections, dict):
        sections = {}
    evaluated_count = len(STAGE_SECTION_EXPECTATIONS[stage])
    for section in STAGE_SECTION_EXPECTATIONS[stage]:
        if not _is_recorded(sections.get(section)):
            findings.append(
                _finding(
                    f"{stage}_{section}_unrecorded",
                    f"{stage.title()} section '{section}' has no recorded result.",
                    "The minimum Stage record remains structurally incomplete.",
                    expectation=f"{stage}.section.{section}",
                )
            )
    evaluated_count += len(designated_references)
    for path, exists in designated_references:
        if not exists:
            findings.append(
                _finding(
                    "stage_reference_missing",
                    f"Designated existing reference does not resolve safely: {path}",
                    "The recorded reference is unavailable or unsafe.",
                    expectation=f"{stage}.reference.{path}",
                )
            )
    command_evidence = [
        item
        for item in state.get("evidence", [])
        if isinstance(item, dict) and item.get("kind") == "automated"
    ]
    evaluated_count += len(command_evidence)
    for index, evidence in enumerate(command_evidence, start=1):
        if evidence.get("outcome") not in _OUTCOMES:
            findings.append(
                _finding(
                    "recorded_command_outcome_invalid",
                    f"Recorded command evidence {index} has no recognized outcome.",
                    "Its test, lint, or audit conclusion remains unknown.",
                    expectation=f"{stage}.evidence.{index}.outcome",
                )
            )
    if stage in _APPROVAL_STAGES:
        evaluated_count += 1
        latest_by_target: dict[str, dict[str, Any]] = {}
        for decision in state.get("decisions", []):
            if isinstance(decision, dict) and isinstance(decision.get("target"), str):
                latest_by_target[decision["target"]] = decision
        approved = latest_by_target.get(stage, {}).get("value") == "approved"
        if not approved and not continuous_delegation:
            findings.append(
                _finding(
                    f"{stage}_approval_unrecorded",
                    (
                        f"{stage.title()} has no current approval or "
                        "continuous delegation."
                    ),
                    "The applicable authority is not recorded.",
                    expectation=f"{stage}.approval_or_delegation",
                )
            )
    return StageExpectationEvaluation(tuple(findings), evaluated_count)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
