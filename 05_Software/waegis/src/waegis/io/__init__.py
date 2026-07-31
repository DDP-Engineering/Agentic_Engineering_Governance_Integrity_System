#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __init__.py
@brief Public surface of the WAEGIS input/output layer (plan §4/§12).
@details Re-exports the ``FieldSpec``/``Asker`` prompt primitives (T1.2), the
         answers-file seam (T1.2), and the console/report renderers plus their
         ``--json`` twins (T1.3). As a sub-package of ``waegis`` this does not
         shadow the stdlib ``io`` module.
"""

# IMPORTS

from __future__ import annotations

from .answers import (
    AnswersError,
    AnswersFileError,
    MissingAnswersError,
    load_answers_file,
    missing_required_keys,
    require_non_interactive_answers,
    save_answers_file,
    unknown_keys,
)
from .console import (
    ASCII_MARKERS,
    GLYPH_MARKERS,
    LiveStatusRenderer,
    plan_preview_json,
    render_plan_preview,
    run_summary_json,
    run_summary_to_dict,
    step_result_json,
)
from .prompts import (
    ConsoleAsker,
    FieldSpec,
    InvalidAnswersError,
    MissingAnswerError,
    PromptsError,
    ScriptedAnswerError,
    ScriptedAsker,
    ValidationError,
    guard_answers,
)
from .reports import (
    BlockingPointReport,
    ProbeFinding,
    ProbeFindingRecord,
    blocking_point_report_json,
    environment_report_json,
    environment_report_to_dict,
    render_blocking_point_report,
    render_environment_report,
)

# CONSTANTS

# @brief Public io-layer names.
__all__ = [
    # prompts
    "ConsoleAsker",
    "FieldSpec",
    "InvalidAnswersError",
    "MissingAnswerError",
    "PromptsError",
    "ScriptedAnswerError",
    "ScriptedAsker",
    "ValidationError",
    "guard_answers",
    # answers file
    "AnswersError",
    "AnswersFileError",
    "MissingAnswersError",
    "load_answers_file",
    "missing_required_keys",
    "require_non_interactive_answers",
    "save_answers_file",
    "unknown_keys",
    # console
    "ASCII_MARKERS",
    "GLYPH_MARKERS",
    "LiveStatusRenderer",
    "plan_preview_json",
    "render_plan_preview",
    "run_summary_json",
    "run_summary_to_dict",
    "step_result_json",
    # reports
    "BlockingPointReport",
    "ProbeFinding",
    "ProbeFindingRecord",
    "blocking_point_report_json",
    "environment_report_json",
    "environment_report_to_dict",
    "render_blocking_point_report",
    "render_environment_report",
]

# END OF FILE
