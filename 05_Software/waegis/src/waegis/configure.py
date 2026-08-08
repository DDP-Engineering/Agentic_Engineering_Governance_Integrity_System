#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file configure.py
@brief WAEGIS-owned workflow reconfiguration planner.
@details Uses current valid values as interactive defaults, preserves advanced
         TOML bytes, and publishes configuration metadata only after the real
         installed AEGIS validator accepts the result.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path

from .analyze import RepositoryAnalysis, analyze_repository
from .answers import configuration_answers
from .gitsafety import build_recovery_plan, require_clean, require_repository
from .interview import collect_install_answers
from .locate import resolve_payload
from .manifest import MANIFEST_PATH, InstallManifest, file_record, load_manifest
from .ownership import Disposition
from .prompts import Asker, FieldSpec
from .publication import PublicationPlan
from .runner import Runner
from .version import WIZARD_VERSION
from .workflow_toml import WorkflowError, generate_workflow, workflow_answers


# DATA MODELS / TYPEDEFINITIONS


class ConfigureError(RuntimeError):
    """@brief Raised when configuration cannot be safely planned."""


class _CurrentDefaultAsker:
    """@brief Decorate prompts with current configuration as displayed defaults."""

    def __init__(self, current: Mapping[str, object], delegate: Asker) -> None:
        self.current = current
        self.delegate = delegate

    def ask(self, field: FieldSpec) -> str:
        value: object = self.current.get(field.key, field.default)
        if field.key.startswith("write_access_stages."):
            stages = self.current.get("write_access_stages", {})
            stage = field.key.split(".", 1)[1]
            value = stages.get(stage, []) if isinstance(stages, Mapping) else []
        if field.choices == ("yes", "no"):
            if isinstance(value, bool):
                rendered = "yes" if value else "no"
            else:
                rendered = "no" if value in {"disabled", "unrestricted"} else "yes"
        elif field.key == "protected_paths_operations":
            rendered = "both" if value == ["read", "write"] else ", ".join(value) if isinstance(value, list) else str(value)
        elif isinstance(value, list):
            rendered = ", ".join(str(item) for item in value)
        else:
            rendered = str(value)
        return self.delegate.ask(replace(field, default=rendered))


# HELPER FUNCTIONS


def _read_workflow(path: Path) -> tuple[str | None, dict[str, object] | None]:
    try:
        text = path.read_text(encoding="utf-8")
        return text, workflow_answers(text)
    except (OSError, UnicodeError, WorkflowError):
        return None, None


def _merge_current(current: Mapping[str, object], supplied: Mapping[str, object]) -> dict[str, object]:
    merged = dict(current)
    merged.update(supplied)
    if "language" in supplied and supplied["language"] != current.get("language"):
        for dependent in ("source_extensions", "test_file_patterns"):
            if dependent not in supplied:
                merged.pop(dependent, None)
    cleared = {
        "alignment_protected_scope_mode": ("disabled", ("alignment_protected_scope_patterns",)),
        "secrets_mode": ("disabled", ("secrets_patterns",)),
        "protected_paths_mode": ("disabled", ("protected_paths_patterns", "protected_paths_operations")),
        "working_tree_mode": ("unrestricted", ("working_tree_blocked_patterns",)),
        "write_access_mode": ("unrestricted", ("write_access_stages",)),
        "scope_mode": ("unrestricted", ("scope_allowed_roots",)),
        "delivery_mode": ("disabled", ("delivery_command_patterns",)),
        "coverage_mode": ("disabled", ("coverage_roots", "coverage_exclude")),
    }
    for mode_key, (off, dependents) in cleared.items():
        if mode_key in supplied and merged.get(mode_key) == off:
            for dependent in dependents:
                if dependent not in supplied:
                    merged[dependent] = {} if dependent == "write_access_stages" else []
    return merged


# EXPORTED FUNCTIONS / PUBLIC API


def plan_configure(
    repository: Path,
    supplied: Mapping[str, object],
    runner: Runner,
    *,
    payload: Path | None,
    asker: Asker | None,
    non_interactive: bool,
) -> tuple[PublicationPlan | None, dict[str, object], tuple[str, ...], bool, RepositoryAnalysis]:
    """@brief Plan a comment-preserving owned-field configuration update."""
    root = require_repository(runner, repository)
    require_clean(runner, root)
    manifest = load_manifest(root.joinpath(*MANIFEST_PATH.split("/")))
    workflow_path = root / ".agentic" / "workflow.toml"
    current_text, current = _read_workflow(workflow_path)
    payload_root, _, _ = resolve_payload(payload)
    template = (payload_root / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    reconstructs = current_text is None or current is None
    base_text = template if reconstructs else current_text
    analysis = analyze_repository(root, runner)
    if non_interactive or asker is None:
        resolved_supplied = _merge_current(current or {}, supplied)
        answers, missing = collect_install_answers(
            resolved_supplied,
            analysis,
            None,
            non_interactive=True,
        )
    else:
        decorated = _CurrentDefaultAsker(current, asker) if current else asker
        answers, missing = collect_install_answers(supplied, analysis, decorated, non_interactive=False)
    if missing:
        return None, answers, missing, reconstructs, analysis
    if current and answers.get("language") == current.get("language"):
        for dependent in ("source_extensions", "test_file_patterns"):
            if dependent not in supplied and dependent in current:
                answers[dependent] = current[dependent]
    elif current:
        for dependent in ("source_extensions", "test_file_patterns"):
            if dependent not in supplied:
                answers.pop(dependent, None)
    try:
        generated = generate_workflow(base_text, answers).encode("utf-8")
    except WorkflowError as exc:
        raise ConfigureError(str(exc)) from exc
    existing_record = manifest.files.get(".agentic/workflow.toml")
    if existing_record is None or existing_record.disposition is not Disposition.GENERATED:
        raise ConfigureError("manifest does not grant configure authority for .agentic/workflow.toml")
    updated_files = dict(manifest.files)
    updated_files[".agentic/workflow.toml"] = file_record(generated, Disposition.GENERATED)
    configuration = {
        "answers": configuration_answers(answers),
        "generator_version": WIZARD_VERSION,
        "workflow_sha256": updated_files[".agentic/workflow.toml"].sha256,
    }
    updated_manifest = InstallManifest(
        manifest.payload_version,
        manifest.payload_digest,
        manifest.installed_at,
        manifest.installed_by,
        manifest.mode,
        updated_files,
        configuration,
    )
    current_bytes = workflow_path.read_bytes() if workflow_path.is_file() else None
    writes = {".agentic/workflow.toml": generated} if current_bytes != generated else {}
    manifest_changed = updated_manifest.to_dict() != manifest.to_dict()
    if not writes and not manifest_changed:
        return None, answers, (), reconstructs, analysis
    recovery = build_recovery_plan(runner, root, (*writes, MANIFEST_PATH))
    return (
        PublicationPlan("configure", root, writes, (), recovery, updated_manifest),
        answers,
        (),
        reconstructs,
        analysis,
    )


# END OF FILE
