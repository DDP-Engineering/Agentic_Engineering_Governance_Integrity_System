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
@brief   Evaluate Stage-completion expectations from recorded state only.
@details Defines the explicit full/short Stage matrix and returns advisory
         finding facts without performing I/O, execution, or publication.
"""

from __future__ import annotations

from typing import Any

STAGE_SECTION_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "intake": (
        "inputs",
        "configured_project_paths",
        "relevant_project_knowledge",
        "restated_ask",
        "initially_affected_repository_area",
        "facts_and_uncertainties",
        "outputs_and_handoff",
    ),
    "alignment": (
        "inputs_from_intake",
        "proposed_scope",
        "developer_corrections",
        "agreed_scope",
        "outputs_and_handoff",
    ),
    "requirement": (
        "inputs_from_alignment",
        "requirement_artifact_changes",
        "traceability",
        "risk_based_test_depth_decision",
        "gaps_and_uncertainties",
        "outputs_and_handoff",
    ),
    "design": (
        "inputs",
        "proposed_solution",
        "requirement_coverage",
        "interfaces_data_and_failure_behavior",
        "alternatives_and_risks",
        "outputs_and_handoff",
    ),
    "check": (
        "inputs",
        "test_work",
        "recorded_red_evidence",
        "test_fingerprints_at_red",
        "red_before_green_decision",
        "outputs_and_handoff",
    ),
    "implementation": (
        "inputs",
        "implementation_changes",
        "test_integrity_comparison",
        "implementation_evidence",
        "component_documentation_review",
        "outputs_and_handoff",
    ),
    "validation": (
        "inputs",
        "impacted_test_selection",
        "automated_validation_evidence",
        "manual_validation_evidence",
        "test_integrity_conclusion",
        "outputs_and_handoff",
    ),
    "delivery": (
        "requested_and_delivered_outcome",
        "project_artifact_changes",
        "implementation_changes",
        "evidence_summary",
        "test_integrity",
        "findings_and_residual_risk",
        "skips_waivers_and_omitted_stages",
        "component_drift_review",
        "delivery_decision",
        "terminal_result",
    ),
}

PROFILE_STAGES = {
    "full": tuple(STAGE_SECTION_EXPECTATIONS),
    "short": tuple(stage for stage in STAGE_SECTION_EXPECTATIONS if stage != "design"),
}

_UNRECORDED_VALUES = {"", "none", "unknown", "not recorded", "pending"}
_APPROVAL_STAGES = {"alignment", "requirement", "design"}


def _finding(
    code: str,
    observation: str,
    consequence: str,
    *,
    expectation: str,
    severity: str = "warning",
    disposition: str = "open",
) -> dict[str, str]:
    """@return One label-free finding fact for application publication."""
    return {
        "code": code,
        "severity": severity,
        "observation": observation,
        "consequence": consequence,
        "disposition": disposition,
        "expectation": expectation,
    }


def _is_recorded(value: Any) -> bool:
    """@return Whether one mandatory section contains an actual record."""
    return isinstance(value, str) and value.strip().lower() not in _UNRECORDED_VALUES


def _automated_test_evidence(
    evidence: list[dict[str, Any]], outcome: str
) -> list[tuple[int, dict[str, Any]]]:
    """@return Ordered automated test evidence with one exact outcome."""
    return [
        (index, item)
        for index, item in enumerate(evidence)
        if item.get("kind") == "automated"
        and item.get("category") == "tests"
        and item.get("outcome") == outcome
    ]


def _valid_red_witness(item: dict[str, Any], *, implementation_started_at: str) -> bool:
    """@return Whether evidence is complete red captured before implementation."""
    fingerprints = item.get("fingerprints")
    time = item.get("time")
    return (
        item.get("red_witness") is True
        and isinstance(fingerprints, dict)
        and bool(fingerprints)
        and isinstance(time, str)
        and bool(time)
        and (not implementation_started_at or time < implementation_started_at)
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
    """@return Truthful flags for the two valid red-before-green alternatives."""
    evidence = [item for item in state.get("evidence", []) if isinstance(item, dict)]
    decisions = [
        item for item in state.get("decisions", []) if isinstance(item, dict)
    ]
    return {
        "valid_witness": any(
            _valid_red_witness(
                item, implementation_started_at=implementation_started_at
            )
            for item in evidence
        ),
        "approved_exception": _valid_red_exception(decisions) is not None,
    }


def _check_expectations(
    state: dict[str, Any], *, implementation_started_at: str
) -> list[dict[str, str]]:
    """@return Findings for the actual-failure-before-implementation contract."""
    evidence = [item for item in state.get("evidence", []) if isinstance(item, dict)]
    failed = _automated_test_evidence(evidence, "failed")
    passed = _automated_test_evidence(evidence, "passed")
    valid_red = [
        (index, item)
        for index, item in failed
        if _valid_red_witness(item, implementation_started_at=implementation_started_at)
    ]
    approved_exception = _valid_red_exception(
        [item for item in state.get("decisions", []) if isinstance(item, dict)]
    )
    if valid_red:
        first_red_index = valid_red[0][0]
        if any(index < first_red_index for index, _ in passed):
            return [
                _finding(
                    "check_red_witness_unexpected_pass",
                    "A relevant Check test passed before any valid red witness.",
                    "The pass does not demonstrate failure before implementation.",
                    expectation="check.red_before_green",
                )
            ]
        return []
    if approved_exception is not None:
        return [
            _finding(
                "check_red_exception_approved",
                "Red-before-green is recorded as exception_approved with a reason "
                "and alternative confirmation.",
                "The expectation is not applicable for this Run and is not passed.",
                expectation="check.red_before_green",
                severity="info",
                disposition="not_applicable",
            )
        ]
    if failed:
        code = (
            "check_red_witness_not_prior"
            if implementation_started_at
            and any(
                isinstance(item.get("time"), str)
                and item.get("time") >= implementation_started_at
                for _, item in failed
            )
            else "check_red_witness_incomplete"
        )
        observation = (
            "The recorded failing test evidence was not captured before Implementation."
            if code == "check_red_witness_not_prior"
            else "Failing Check test evidence lacks a complete immutable red witness."
        )
        return [
            _finding(
                code,
                observation,
                "Complete red-before-green evidence is not established.",
                expectation="check.red_before_green",
            )
        ]
    if passed:
        return [
            _finding(
                "check_red_witness_unexpected_pass",
                "A relevant Check test passed without a prior valid red witness.",
                "The pass does not demonstrate failure before implementation.",
                expectation="check.red_before_green",
            )
        ]
    return [
        _finding(
            "check_red_witness_missing",
            "Check contains no actual failing test witness before implementation. "
            "Use execution-run to establish one, or use decision-add with target "
            "red_before_green, value exception_approved, reason, and "
            "alternative_confirmation when red-before-green genuinely does not apply.",
            "Red-before-green evidence remains missing.",
            expectation="check.red_before_green",
        )
    ]


def evaluate_stage_expectations(
    *,
    stage: str,
    profile: str,
    state: dict[str, Any],
    check_state: dict[str, Any] | None = None,
    implementation_started_at: str = "",
    configured_commands: tuple[str, ...] = (),
) -> tuple[dict[str, str], ...]:
    """
    @brief Evaluate one included Stage entirely from supplied durable state.
    @param[in] stage Canonical Stage name.
    @param[in] profile Full or short Run profile.
    @param[in] state Current Stage state.
    @param[in] check_state Durable Check state used by Implementation.
    @param[in] implementation_started_at Durable Implementation start time.
    @param[in] configured_commands Applicable configured command identities.
    @return Ordered label-free advisory finding facts.
    """
    if stage not in PROFILE_STAGES.get(profile, ()):
        return ()
    findings: list[dict[str, str]] = []
    sections = state.get("sections", {})
    if not isinstance(sections, dict):
        sections = {}
    for section in STAGE_SECTION_EXPECTATIONS[stage]:
        if not _is_recorded(sections.get(section)):
            findings.append(
                _finding(
                    f"{stage}_{section}_unrecorded",
                    f"{stage.title()} section '{section}' has no recorded result.",
                    "The mandatory Stage category remains visibly incomplete.",
                    expectation=f"{stage}.section.{section}",
                )
            )
    if stage in _APPROVAL_STAGES:
        latest_by_target: dict[str, dict[str, Any]] = {}
        for decision in state.get("decisions", []):
            if isinstance(decision, dict) and isinstance(decision.get("target"), str):
                latest_by_target[decision["target"]] = decision
        if not any(
            decision.get("value") == "approved"
            for decision in latest_by_target.values()
        ):
            findings.append(
                _finding(
                    f"{stage}_approval_unrecorded",
                    f"{stage.title()} contains no current approved decision.",
                    "The Stage output has no recorded approval; closure remains "
                    "advisory.",
                    expectation=f"{stage}.approval",
                )
            )
    if stage == "check":
        findings.extend(
            _check_expectations(
                state, implementation_started_at=implementation_started_at
            )
        )
    elif stage == "implementation":
        check_exception = _valid_red_exception(
            [
                item
                for item in (check_state or {}).get("decisions", [])
                if isinstance(item, dict)
            ]
        )
        green = _automated_test_evidence(
            [item for item in state.get("evidence", []) if isinstance(item, dict)],
            "passed",
        )
        if not green and check_exception is None:
            findings.append(
                _finding(
                    "implementation_green_evidence_missing",
                    "Implementation contains no passing automated test evidence.",
                    "The red-to-green result remains incomplete.",
                    expectation="implementation.green_evidence",
                )
            )
    elif stage == "validation":
        recorded = {
            f"{item.get('category')}.{item.get('name')}"
            for item in state.get("evidence", [])
            if isinstance(item, dict)
            and item.get("kind") == "automated"
            and item.get("category") in {"tests", "lints", "audits"}
            and isinstance(item.get("name"), str)
        }
        for command in configured_commands:
            if command not in recorded:
                findings.append(
                    _finding(
                        "validation_command_evidence_missing",
                        f"{command} has no recorded Validation execution outcome.",
                        "The applicable configured command remains unverified.",
                        expectation=f"validation.command.{command}",
                    )
                )
    return tuple(findings)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
