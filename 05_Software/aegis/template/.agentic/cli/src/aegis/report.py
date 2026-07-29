#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file report.py
@brief Markdown report rendering for workflow runs.
@details Renders schema-3 stage state, durable requirements, solution design,
         checks, evidence, verification records, and adoption baseline data.
@author Eng. Dan Dumitru Pasare
@date 2026-07-22
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

from collections import Counter
from pathlib import Path

from .components import audit_local_scope, load_components
from .config import WorkflowConfig
from .invariants import evaluate
from .models import Graph
from .requirement_store import load_all_requirement_records
from .requirements import audit_coverage, audit_traceability
from .stage_forms import next_command
from .verification import validation_summary_path

# PUBLIC API


def render_report(
    repo_root: Path, graph: Graph, config: WorkflowConfig
) -> str:
    """
    @brief      Render a complete Markdown report for the active workflow graph.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  graph Input value used by the workflow helper.
    @param[in]  config Validated workflow configuration.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    1.0.0
    """
    results = evaluate(repo_root, graph, config)
    traceability_issues = audit_traceability(repo_root, config)
    coverage_issues = audit_coverage(repo_root, config)
    lines = [
        f"# AEGIS Report: {graph.run_id}",
        "",
        f"- Stage: `{graph.stage}`",
        f"- Access mode: `{graph.access_mode}`",
        f"- Intent: `{graph.intent.id}` {graph.intent.kind} - {graph.intent.statement}",
        "",
        "## Intent Alignment",
    ]
    if graph.alignment:
        alignment = graph.alignment
        lines.append(f"- Source: {alignment.source}")
        lines.append(f"- Understanding: {alignment.understanding}")
        lines.append(f"- Risk: `{alignment.risk}`")
        lines.append(f"- Decision: `{alignment.decision}` - {alignment.reason}")
        lines.append(f"- Scope: {'; '.join(alignment.scope)}")
        lines.append(f"- Acceptance: {'; '.join(alignment.acceptance)}")
        lines.append(f"- Assumptions: {'; '.join(alignment.assumptions) if alignment.assumptions else 'none'}")
        lines.append(f"- Open questions: {'; '.join(alignment.open_questions) if alignment.open_questions else 'none'}")
        lines.append(
            "- Recommended responses: "
            f"{'; '.join(alignment.recommended_responses) if alignment.recommended_responses else 'none'}"
        )
        if alignment.planned_paths:
            lines.append(f"- Planned paths: {', '.join(alignment.planned_paths)}")
    else:
        lines.append("- None recorded.")

    lines.extend([
        "",
        "## Stage Lifecycle",
    ])
    if graph.stage_records:
        for stage, record in graph.stage_records.items():
            lines.append(
                f"- `{stage}` revision {record.revision}: `{record.status}`; "
                f"retention `{record.retention}`; check execution "
                f"`{record.check_execution}`"
            )
    else:
        lines.append("- No stage records.")

    lines.extend(["", "## Requirements"])
    requirements = load_all_requirement_records(repo_root, config)
    if requirements:
        for requirement in requirements:
            lines.append(
                f"- `{requirement.id}` {requirement.status}: "
                f"{requirement.requirement}"
            )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Solution Design"])
    if graph.design:
        design = graph.design
        lines.extend(
            [
                f"- Revision: {design.revision}",
                f"- Status: `{design.status}`",
                f"- Approval: `{design.approval}`",
                f"- Document: `{design.document_path}`",
                f"- Selected option: {design.selected_option or 'none'}",
                "- Cited requirements: "
                + (", ".join(f"`{item}`" for item in design.requirement_digests) or "none"),
                "- Open questions: "
                + ("; ".join(design.open_questions) or "none"),
            ]
        )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Checks"])
    if graph.checks:
        for check in graph.checks:
            cites = ", ".join(check.cites_requirement)
            lines.append(
                f"- `{check.id}` {check.state}; requirements {cites}; "
                f"command `{check.command}`"
            )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Evidence"])
    if graph.evidence:
        for item in graph.evidence:
            failure_kind = f" ({item.failure_kind})" if item.failure_kind else ""
            lines.append(
                f"- `{item.id}` {item.kind}/{item.result}{failure_kind}: {item.summary}"
            )
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Invariants"])
    for item in results:
        marker = "PASS" if item.holds else "FAIL"
        lines.append(f"- `{item.id}` {marker} ({item.policy}): {item.message}")

    lines.extend(["", "## Traceability Audits"])
    if not traceability_issues and not coverage_issues:
        lines.append("- PASS: live traceability and coverage audits have no findings.")
    for issue in traceability_issues:
        lines.append(f"- `{issue.code}` {issue.message}")
    for issue in coverage_issues:
        lines.append(f"- `{issue.code}` {issue.message}")

    validation_path = validation_summary_path(repo_root, graph)
    lines.extend(["", "## Deterministic Verification"])
    if validation_path.is_file():
        lines.append(
            f"- Validation summary: "
            f"`{validation_path.relative_to(repo_root).as_posix()}`"
        )
    else:
        lines.append("- Not yet run. Use `aegis verify run` during validation.")

    adoption_lines = _render_adoption_baseline(repo_root, graph, config)
    if adoption_lines:
        lines.extend(["", *adoption_lines])

    lines.extend(["", "## Handoff"])
    lines.append(f"- Next command: `{next_command(graph)}`")
    lines.append(
        "- Delivery closure records the human handoff decision only; it does "
        "not push, publish, merge, or create a pull request."
    )
    lines.append("")
    return "\n".join(lines)


def write_report(repo_root: Path, graph: Graph, rendered: str) -> Path:
    """
    @brief      Write report workflow behavior.
    @param[in]  repo_root Input value used by the workflow helper.
    @param[in]  graph Input value used by the workflow helper.
    @param[in]  rendered Complete report text rendered with the operation config.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    path = repo_root / ".agentic" / "runs" / graph.run_id / "report.md"
    path.write_text(rendered, encoding="utf-8")
    return path


# HELPER FUNCTIONS


def _render_adoption_baseline(
    repo_root: Path, graph: Graph, config: WorkflowConfig
) -> list[str]:
    """
    @brief      Render adoption baseline details when relevant to a run.
    @param[in]  repo_root Repository root.
    @param[in]  graph Workflow graph.
    @param[in]  config Validated workflow configuration.
    @return     Markdown lines for the adoption section, or an empty list.
    @exception  tomllib.TOMLDecodeError Raised when component TOML is invalid.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.2.0
    """
    manifest = load_components(repo_root, config.component_manifest)
    if graph.intent.kind != "adoption" and not manifest.components:
        return []

    lines = [
        "## Adoption Baseline",
        f"- Component manifest: `{config.component_manifest}`",
        "- Minimum baseline: "
        f"`{config.component_baseline_guard.minimum_completion_level}`",
        f"- Adoption report root: `{config.adoption_report_root}`",
        "",
        "### Component Status Counts",
    ]
    if manifest.components:
        counts = Counter(component.adoption_status for component in manifest.components.values())
        for status, count in sorted(counts.items()):
            lines.append(f"- `{status}`: {count}")
    else:
        lines.append("- No components configured.")

    lines.extend(["", "### Components"])
    if manifest.components:
        for name, component in sorted(manifest.components.items()):
            tests = ", ".join(component.tests) if component.tests else "no tests mapped"
            lines.append(f"- `{name}`: {component.adoption_status}; paths {', '.join(component.paths) or 'none'}; tests {tests}")
    else:
        lines.append("- No components configured.")

    touched_paths = _touched_paths(graph)
    if touched_paths:
        lines.extend(["", "### Local Scope Findings"])
        issues = audit_local_scope(
            repo_root,
            touched_paths,
            config,
            config.component_baseline_guard.minimum_completion_level,
        )
        if issues:
            for issue in issues:
                location = f" [{issue.path}]" if issue.path else ""
                subject = f" ({issue.name})" if issue.name else ""
                lines.append(f"- `{issue.code}`{subject}{location}: {issue.message}")
        else:
            lines.append("- No local-scope findings for touched paths.")
    return lines


def _touched_paths(graph: Graph) -> list[str]:
    """
    @brief      Collect touched paths from change units.
    @param[in]  graph Workflow graph.
    @return     Sorted unique repository-relative paths.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-22
    @version    0.1.0
    """
    return sorted({path for unit in graph.change_units for path in unit.touched_paths})


# END OF FILE
