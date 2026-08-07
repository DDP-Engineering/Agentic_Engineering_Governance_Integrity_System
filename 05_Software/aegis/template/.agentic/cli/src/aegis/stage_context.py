#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file stage_context.py
@brief Build the bounded bootstrap surface for one fresh AEGIS stage session.
@details Resolves only payload-owned workflow guidance and the current plus
         immediately previous primary form. It never reads evidence, journals,
         requirement indexes, reports, or the complete configuration surface.
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Graph, Stage
from .stage_forms import stage_directory
from .stage_schema import STAGE_REFERENCE_PATHS, run_stage_spec

# CONSTANTS

CONTEXT_SCHEMA_VERSION = 1
_AGENTS_PATH = "AGENTS.md"
_DEVELOPMENT_SKILL = ".agentic/skills/agentic-development/SKILL.md"
_ADOPTION_SKILL = ".agentic/skills/agentic-adoption/SKILL.md"
_DELIVERY_SKILL = ".agentic/skills/agentic-delivery/SKILL.md"
_COLLECTION_STAGES = frozenset({"requirement", "check", "component-adoption"})


# PUBLIC API


def build_stage_context(repo_root: Path, graph: Graph) -> dict[str, Any]:
    """
    @brief Build a fixed-shape, read-only fresh-session bootstrap response.
    @param[in] repo_root Repository root.
    @param[in] graph Authoritative selected run graph.
    @return Versioned context response containing bounded repository paths.
    @exception StageOperationError If the run does not match its lifecycle schema.
    @details Paths are repository-relative POSIX paths. The response names a
             missing retained predecessor explicitly rather than silently
             omitting it, so an agent has a deterministic recovery route.
    """
    spec = run_stage_spec(graph)
    current_form = _primary_form_path(repo_root, graph, graph.stage)
    artifact = _relative(repo_root, current_form)
    skill = _skill_path(graph.stage)
    reference = STAGE_REFERENCE_PATHS[graph.stage]
    previous, unavailable = _previous_stage_forms(repo_root, graph, spec.stages)
    required_reads = _unique_existing_paths(
        repo_root,
        [_AGENTS_PATH, skill, reference, artifact, *previous],
    )
    return {
        "context_schema_version": CONTEXT_SCHEMA_VERSION,
        "run_id": graph.run_id,
        "kind": graph.intent.kind,
        "profile": graph.profile,
        "stage": graph.stage,
        "reference": reference,
        "skill": skill,
        "artifact": artifact,
        "previous_stage_artifacts": previous,
        "unavailable_previous_stage_artifacts": unavailable,
        "required_reads": required_reads,
        "next_commands": [
            "aegis stage prepare",
            "aegis stage apply",
            "aegis stage close",
        ],
        "human_gate": "stage close",
    }


# LOCAL HELPERS


def _skill_path(stage: Stage) -> str:
    """@brief Return the router that owns one stage's procedure."""
    if stage in {"delivery", "adoption-delivery"}:
        return _DELIVERY_SKILL
    if stage.startswith("adoption-") or stage in {
        "repo-discovery",
        "component-map",
        "component-adoption",
        "baseline-review",
    }:
        return _ADOPTION_SKILL
    return _DEVELOPMENT_SKILL


def _previous_stage_forms(
    repo_root: Path,
    graph: Graph,
    stages: tuple[Stage, ...],
) -> tuple[list[str], list[dict[str, str]]]:
    """
    @brief Locate the immediately preceding retained primary form, if available.
    @return Available paths and explicit unavailable-form records.
    """
    stage_index = stages.index(graph.stage)
    if stage_index == 0:
        return [], []
    previous_stage = stages[stage_index - 1]
    record = graph.stage_records.get(previous_stage)
    if record is None:
        return [], [_unavailable(previous_stage, "the previous stage has no record")]
    if record.retention == "discard":
        return [], [_unavailable(previous_stage, "the captured retention policy discarded the form")]
    source = _primary_form_path(repo_root, graph, previous_stage)
    if record.retention == "versioned":
        source = source.parent / "revisions" / f"{record.revision:04d}" / source.name
    if source.is_file():
        return [_relative(repo_root, source)], []
    return [], [_unavailable(previous_stage, "the retained primary form is unavailable")]


def _unavailable(stage: Stage, reason: str) -> dict[str, str]:
    """@brief Return the stable recovery description for one absent form."""
    return {
        "stage": stage,
        "reason": reason,
        "recovery_command": "aegis stage show",
    }


def _primary_form_path(repo_root: Path, graph: Graph, stage: Stage) -> Path:
    """@brief Resolve the bounded primary form path for a current or prior stage."""
    directory = stage_directory(repo_root, graph) if stage == graph.stage else (
        repo_root / ".agentic" / "runs" / graph.run_id / "stages" / stage
    )
    name = "stage.toml" if stage in _COLLECTION_STAGES else f"{stage}.toml"
    return directory / name


def _relative(repo_root: Path, path: Path) -> str:
    """@brief Convert one repository-local path to the CLI's POSIX form."""
    return path.relative_to(repo_root).as_posix()


def _unique_existing_paths(repo_root: Path, paths: list[str]) -> list[str]:
    """@brief Preserve path order while keeping the expected bootstrap contract."""
    unique: list[str] = []
    for path in paths:
        if path not in unique:
            unique.append(path)
    return unique


# END OF FILE
