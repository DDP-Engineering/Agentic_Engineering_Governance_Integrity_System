#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file interview.py
@brief Conditional WAEGIS-owned policy interview and answer normalization.
@details Repository evidence is displayed as proposal provenance. Restrictive
         features default off, and dependent rules are collected only when the
         controlling feature is enabled.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Callable

from .analyze import RepositoryAnalysis
from .prompts import Asker, FieldSpec, parse_list
from .workflow_toml import ALL_STAGES, LANGUAGE_PRESETS, WorkflowError, normalize_roots


# CONSTANTS

GATES = ("build", "typecheck", "lint", "test", "security")
COMPLETION_LEVELS = ("unknown", "discovered", "characterized", "baseline-usable", "baseline-strict")

SAFE_POLICY_DEFAULTS: dict[str, object] = {
    "alignment_enabled": True,
    "alignment_protected_scope_mode": "disabled",
    "alignment_protected_scope_patterns": [],
    "stage_form_retention": "latest",
    "check_execution": "external",
    **{f"gate_{gate}_mode": "disabled" for gate in GATES},
    **{f"gate_{gate}_commands": [] for gate in GATES},
    "secrets_mode": "disabled",
    "secrets_patterns": [],
    "protected_paths_mode": "disabled",
    "protected_paths_patterns": [],
    "protected_paths_operations": [],
    "working_tree_mode": "unrestricted",
    "working_tree_blocked_patterns": [],
    "write_access_mode": "unrestricted",
    "write_access_stages": {},
    "scope_mode": "unrestricted",
    "scope_allowed_roots": [],
    "delivery_mode": "disabled",
    "delivery_command_patterns": [],
    "coverage_mode": "disabled",
    "coverage_roots": [],
    "coverage_exclude": [],
    "baseline_guard_mode": "disabled",
    "minimum_completion_level": "baseline-usable",
    "adoption_source_changes_mode": "unrestricted",
    "quick_changed_paths_mode": "disabled",
    "quick_max_paths": 10,
}


# DATA MODELS / TYPEDEFINITIONS


class InterviewError(ValueError):
    """@brief Raised when supplied/interactively collected answers are invalid."""


# HELPER FUNCTIONS


def _ask_missing(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    asker: Asker | None,
    key: str,
    field: FieldSpec,
    convert: Callable[[str], object] = str,
) -> bool:
    """@brief Ask one absent key; return false when no live asker is available."""
    if key in supplied:
        return True
    if asker is None:
        return False
    try:
        answers[key] = convert(asker.ask(field))
    except (TypeError, ValueError) as exc:
        raise InterviewError(f"invalid answer for {key}: {exc}") from exc
    return True


def _yes_no(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    asker: Asker | None,
    key: str,
    question: str,
    description: str,
    *,
    default: bool,
    enabled: str,
    disabled: str,
) -> bool:
    if key in supplied:
        return True
    if asker is None:
        return False
    value = asker.ask(FieldSpec(key, question, description, "yes" if default else "no", ("yes", "no")))
    answers[key] = enabled if value == "yes" else disabled
    return True


def _list_value(value: object, key: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise InterviewError(f"{key} must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise InterviewError(f"{key} entries must be non-empty strings")
        normalized = item.strip()
        if normalized not in result:
            result.append(normalized)
    if not result and not allow_empty:
        raise InterviewError(f"{key} must not be empty")
    return result


def _choice(answers: Mapping[str, object], key: str, choices: Sequence[str]) -> str:
    value = answers.get(key)
    if not isinstance(value, str) or value not in choices:
        raise InterviewError(f"{key} must be one of: {', '.join(choices)}")
    return value


def _conditional_list(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    asker: Asker | None,
    missing: list[str],
    key: str,
    question: str,
    description: str,
    *,
    default: Sequence[str] = (),
    example: str | None = None,
    allow_empty: bool = False,
) -> None:
    while True:
        try:
            if key not in supplied:
                rendered = ", ".join(default)
                if not _ask_missing(
                    answers,
                    supplied,
                    asker,
                    key,
                    FieldSpec(key, question, description, rendered, example=example),
                    lambda value: parse_list(value) if value.strip() else [],
                ):
                    missing.append(key)
                    return
            answers[key] = _list_value(answers[key], key, allow_empty=allow_empty)
        except InterviewError:
            if key in supplied or asker is None:
                raise
            continue
        return


def _collect_basics(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    analysis: RepositoryAnalysis | None,
    asker: Asker | None,
    missing: list[str],
) -> None:
    defaults = {
        "language": analysis.language.value if analysis else "python",
        "source_roots": analysis.source_roots.value if analysis else ["src"],
        "test_roots": analysis.test_roots.value if analysis else ["tests"],
    }
    basics = (
        (
            "language",
            FieldSpec(
                "language",
                "Which language is this project mainly written in?",
                "Selects source extensions and linked-test conventions; installs no language tooling. "
                + (f"Proposal evidence: {analysis.language.reason}." if analysis else "Payload default."),
                str(defaults["language"]),
                (*LANGUAGE_PRESETS, "other"),
            ),
            str,
        ),
        (
            "source_roots",
            FieldSpec(
                "source_roots",
                "Where does your source code live?",
                "Defines production code for coverage, scope, and write policy."
                + (f" Proposal evidence: {analysis.source_roots.reason}." if analysis else ""),
                ", ".join(defaults["source_roots"]),
                example="src, app",
            ),
            parse_list,
        ),
        (
            "test_roots",
            FieldSpec(
                "test_roots",
                "Where do your tests live?",
                "Defines where requirement-linked tests resolve."
                + (f" Proposal evidence: {analysis.test_roots.reason}." if analysis else ""),
                ", ".join(defaults["test_roots"]),
                example="tests",
            ),
            parse_list,
        ),
    )
    for key, field, convert in basics:
        if not _ask_missing(answers, supplied, asker, key, field, convert):
            missing.append(key)
    language = answers.get("language")
    if "language" in missing:
        return
    if language not in {*LANGUAGE_PRESETS, "other"}:
        raise InterviewError(f"unsupported language: {language!r}")
    if language == "other":
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "source_extensions",
            "Which source-file extensions should AEGIS recognize?",
            "Supplies traceability extensions absent from the built-in presets.",
            example=".zig, .zon",
        )
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "test_file_patterns",
            "Which file-name patterns identify tests?",
            "Lets requirement links resolve tests for the custom language.",
            example="*_test.zig",
        )


def _collect_alignment_and_gates(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    analysis: RepositoryAnalysis | None,
    asker: Asker | None,
    missing: list[str],
) -> None:
    if "alignment_enabled" not in supplied and asker is not None:
        value = asker.ask(
            FieldSpec(
                "alignment_enabled",
                "Record intent alignment before requirement and design work?",
                "When enabled, each run records approved intent before downstream engineering proceeds.",
                "yes",
                ("yes", "no"),
            )
        )
        answers["alignment_enabled"] = value == "yes"
    elif not isinstance(answers.get("alignment_enabled"), bool):
        raise InterviewError("alignment_enabled must be boolean")
    _yes_no(
        answers,
        supplied,
        asker,
        "alignment_protected_scope_mode",
        "Require protected-scope patterns in alignment?",
        "Records and validates the scope; the current payload does not enforce those patterns at runtime.",
        default=False,
        enabled="enforce",
        disabled="disabled",
    )
    if _choice(answers, "alignment_protected_scope_mode", ("disabled", "enforce")) == "enforce":
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "alignment_protected_scope_patterns",
            "Which path globs form the protected alignment scope?",
            "The alignment record validates these protected-scope declarations.",
            example="infra/**",
        )
    _ask_missing(
        answers,
        supplied,
        asker,
        "stage_form_retention",
        FieldSpec(
            "stage_form_retention",
            "Keep, version, or discard stage forms after import?",
            "Latest retains the final handoff; versioned retains all revisions; discard removes imported forms.",
            "latest",
            ("versioned", "latest", "discard"),
        ),
    )
    _choice(answers, "stage_form_retention", ("versioned", "latest", "discard"))
    _ask_missing(
        answers,
        supplied,
        asker,
        "check_execution",
        FieldSpec(
            "check_execution",
            "Who executes check commands?",
            "External imports evidence from any environment; managed lets AEGIS execute commands.",
            "external",
            ("external", "managed"),
        ),
    )
    _choice(answers, "check_execution", ("external", "managed"))
    for gate in GATES:
        mode_key = f"gate_{gate}_mode"
        _yes_no(
            answers,
            supplied,
            asker,
            mode_key,
            f"Enable the {gate} gate?",
            "When enforced, command failure blocks validation until fixed or explicitly waived.",
            default=False,
            enabled="enforce",
            disabled="disabled",
        )
        if _choice(answers, mode_key, ("disabled", "enforce")) == "enforce":
            proposals = analysis.gates.get(gate, ()) if analysis else ()
            proposed = [" ".join(str(part) for part in item.value) for item in proposals]
            reason = "; ".join(item.reason for item in proposals)
            _conditional_list(
                answers,
                supplied,
                asker,
                missing,
                f"gate_{gate}_commands",
                f"Which command(s) run the {gate} gate?",
                "Commands run from the repository root in order; the first failure fails the gate."
                + (f" Proposal evidence: {reason}." if reason else ""),
                default=proposed,
                example="python -m pytest",
            )


def _collect_guardrails(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    asker: Asker | None,
    missing: list[str],
) -> None:
    rules = (
        (
            "secrets",
            "Scan for secrets before validation?",
            "Matching tool input is blocked live and the working tree is scanned at validation.",
            "secrets_patterns",
            "Which Python regular expressions identify secrets?",
            "token-[0-9]+",
        ),
        (
            "working_tree",
            "Block suspicious working-tree patterns?",
            "Matching files in the working tree block validation until reviewed.",
            "working_tree_blocked_patterns",
            "Which path globs are blocked?",
            "dist/**",
        ),
        (
            "delivery",
            "Guard outward delivery commands?",
            "Matching commands are denied until verification and delivery preflight succeed.",
            "delivery_command_patterns",
            "Which lowercase command fragments count as delivery?",
            "git push, gh pr merge",
        ),
    )
    mode_values = {"secrets": ("disabled", "enforce"), "working_tree": ("unrestricted", "restricted"), "delivery": ("disabled", "enforce")}
    for name, question, consequence, list_key, list_question, example in rules:
        disabled, enabled = mode_values[name]
        _yes_no(
            answers,
            supplied,
            asker,
            f"{name}_mode",
            question,
            consequence,
            default=False,
            enabled=enabled,
            disabled=disabled,
        )
        if _choice(answers, f"{name}_mode", (disabled, enabled)) == enabled:
            _conditional_list(
                answers,
                supplied,
                asker,
                missing,
                list_key,
                list_question,
                consequence,
                example=example,
            )
    _yes_no(
        answers,
        supplied,
        asker,
        "protected_paths_mode",
        "Protect specific paths from reads or writes?",
        "Matching hook operations are denied and matching changes block validation.",
        default=False,
        enabled="enforce",
        disabled="disabled",
    )
    if _choice(answers, "protected_paths_mode", ("disabled", "enforce")) == "enforce":
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "protected_paths_patterns",
            "Which path globs are protected?",
            "Hooks and validation apply protection to these paths.",
            example="private/**",
        )
        if "protected_paths_operations" not in supplied:
            if asker is None:
                missing.append("protected_paths_operations")
            else:
                selected = asker.ask(
                    FieldSpec(
                        "protected_paths_operations",
                        "Protect reads, writes, or both?",
                        "Selected operations are denied for protected paths.",
                        "both",
                        ("read", "write", "both"),
                    )
                )
                answers["protected_paths_operations"] = ["read", "write"] if selected == "both" else [selected]
        if "protected_paths_operations" not in missing:
            operations = _list_value(answers["protected_paths_operations"], "protected_paths_operations")
            if not set(operations) <= {"read", "write"}:
                raise InterviewError("protected_paths_operations accepts only read and write")
            answers["protected_paths_operations"] = operations
    _yes_no(
        answers,
        supplied,
        asker,
        "write_access_mode",
        "Restrict writes by workflow stage?",
        "Hooks deny writes outside each stage's explicitly allowed folders.",
        default=False,
        enabled="stage_restricted",
        disabled="unrestricted",
    )
    if _choice(answers, "write_access_mode", ("unrestricted", "stage_restricted")) == "stage_restricted":
        raw_stages = answers.get("write_access_stages") if "write_access_stages" in supplied else None
        if raw_stages is None:
            if asker is None:
                missing.append("write_access_stages")
            else:
                raw_stages = {}
                for stage in ALL_STAGES:
                    value = asker.ask(
                        FieldSpec(
                            f"write_access_stages.{stage}",
                            f"Which globs may the {stage} stage write?",
                            "An empty list makes this stage read-only.",
                            "",
                            example="src/**, tests/**",
                        )
                    )
                    raw_stages[stage] = parse_list(value) if value.strip() else []
                answers["write_access_stages"] = raw_stages
        if raw_stages is not None:
            if not isinstance(raw_stages, Mapping) or set(raw_stages) != set(ALL_STAGES):
                raise InterviewError("write_access_stages must contain every supported stage exactly once")
            answers["write_access_stages"] = {
                stage: _list_value(raw_stages[stage], f"write_access_stages.{stage}", allow_empty=True)
                for stage in ALL_STAGES
            }
    _ask_missing(
        answers,
        supplied,
        asker,
        "scope_mode",
        FieldSpec(
            "scope_mode",
            "Check paths against the run's declared scope?",
            "Advisory reports scope creep; enforce blocks it.",
            "unrestricted",
            ("unrestricted", "advisory", "enforce"),
        ),
    )
    if _choice(answers, "scope_mode", ("unrestricted", "advisory", "enforce")) != "unrestricted":
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "scope_allowed_roots",
            "Which roots are allowed by declared scope?",
            "Scope checking compares changed paths with these repository roots.",
            example="src, tests",
        )


def _collect_traceability(
    answers: dict[str, object],
    supplied: Mapping[str, object],
    asker: Asker | None,
    missing: list[str],
) -> None:
    _yes_no(
        answers,
        supplied,
        asker,
        "coverage_mode",
        "Enforce requirement coverage for source files?",
        "Covered source files need an active requirement, a resolvable test, or a waiver.",
        default=False,
        enabled="enforce",
        disabled="disabled",
    )
    if _choice(answers, "coverage_mode", ("disabled", "enforce")) == "enforce":
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "coverage_roots",
            "Which roots require requirement coverage?",
            "Coverage applies only below these repository roots.",
            default=answers.get("source_roots", []),
            example="src",
        )
        _conditional_list(
            answers,
            supplied,
            asker,
            missing,
            "coverage_exclude",
            "Which globs are excluded from requirement coverage?",
            "Excluded paths do not need requirement links or waivers.",
            allow_empty=True,
            example="src/generated/**",
        )
    _yes_no(
        answers,
        supplied,
        asker,
        "baseline_guard_mode",
        "Enforce a component baseline before behavior changes?",
        "Behavior-changing runs may touch only components documented to the selected level.",
        default=False,
        enabled="enforce",
        disabled="disabled",
    )
    if _choice(answers, "baseline_guard_mode", ("disabled", "enforce")) == "enforce":
        if not _ask_missing(
            answers,
            supplied,
            asker,
            "minimum_completion_level",
            FieldSpec(
                "minimum_completion_level",
                "What minimum component completion level is required?",
                "Components below this documentation level block behavior-changing runs.",
                "baseline-usable",
                COMPLETION_LEVELS,
            ),
        ):
            missing.append("minimum_completion_level")
        _choice(answers, "minimum_completion_level", COMPLETION_LEVELS)
    _ask_missing(
        answers,
        supplied,
        asker,
        "adoption_source_changes_mode",
        FieldSpec(
            "adoption_source_changes_mode",
            "Allow adoption runs to modify application source?",
            "Blocked prevents adoption delivery from changing application source.",
            "unrestricted",
            ("unrestricted", "blocked"),
        ),
    )
    _choice(answers, "adoption_source_changes_mode", ("unrestricted", "blocked"))
    _yes_no(
        answers,
        supplied,
        asker,
        "quick_changed_paths_mode",
        "Advise when a quick run touches too many paths?",
        "Above the threshold AEGIS recommends a full run but does not block work.",
        default=False,
        enabled="advise",
        disabled="disabled",
    )
    if _choice(answers, "quick_changed_paths_mode", ("disabled", "advise")) == "advise":
        while True:
            try:
                if not _ask_missing(
                    answers,
                    supplied,
                    asker,
                    "quick_max_paths",
                    FieldSpec(
                        "quick_max_paths",
                        "How many changed paths trigger quick-run advice?",
                        "Crossing this positive threshold recommends a full run.",
                        "10",
                    ),
                    int,
                ):
                    missing.append("quick_max_paths")
                    break
                if (
                    not isinstance(answers.get("quick_max_paths"), int)
                    or isinstance(answers.get("quick_max_paths"), bool)
                    or answers["quick_max_paths"] <= 0
                ):
                    raise InterviewError("quick_max_paths must be a positive integer")
            except InterviewError:
                if "quick_max_paths" in supplied or asker is None:
                    raise
                continue
            break


# EXPORTED FUNCTIONS / PUBLIC API


def collect_install_answers(
    supplied: Mapping[str, object],
    analysis: RepositoryAnalysis | None,
    asker: Asker | None,
    *,
    non_interactive: bool,
) -> tuple[dict[str, object], tuple[str, ...]]:
    """
    @brief Resolve the complete conditional install interview.
    @return Normalized answers and every conditionally required missing key.
    """
    live_asker = None if non_interactive else asker
    answers = dict(SAFE_POLICY_DEFAULTS)
    answers.update(supplied)
    missing: list[str] = []
    _collect_basics(answers, supplied, analysis, live_asker, missing)
    _collect_alignment_and_gates(answers, supplied, analysis, live_asker, missing)
    _collect_guardrails(answers, supplied, live_asker, missing)
    _collect_traceability(answers, supplied, live_asker, missing)
    if missing:
        return answers, tuple(sorted(set(missing)))
    try:
        answers["source_roots"] = list(normalize_roots(answers["source_roots"], "source_roots"))
        answers["test_roots"] = list(normalize_roots(answers["test_roots"], "test_roots"))
    except WorkflowError as exc:
        raise InterviewError(str(exc)) from exc
    return answers, ()


# END OF FILE
