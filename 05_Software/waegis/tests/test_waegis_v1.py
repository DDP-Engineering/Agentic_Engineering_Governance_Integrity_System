#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_waegis_v1.py
@brief WAEGIS 1.x and AEGIS schema-3 integration tests.
@details Covers version compatibility, all five independently configured gates,
         interface defaults, and explicit security-script analysis.
@author Eng. Dan Dumitru Pasare
@date 2026-07-29
@version 1.0.0
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import tomllib

from waegis.probes.runner import CommandRunner
from waegis.repo.analyze import analyze_repo
from waegis.repo.workflow_toml import (
    GATE_ORDER,
    WORKFLOW_FIELD_SPECS,
    generate_workflow_toml,
    verify_workflow_schema,
)
from waegis.version import (
    PAYLOAD_COMPAT_SPEC,
    WIZARD_VERSION,
    is_payload_compatible,
)

# TESTS


def test_version_boundary_is_aegis_two_only() -> None:
    """@brief Verify the unsupported cross-major compatibility boundary."""
    assert WIZARD_VERSION == "1.2.0"
    assert PAYLOAD_COMPAT_SPEC == ">=2.0.0,<3.0.0"
    assert is_payload_compatible("2.0.0")
    assert not is_payload_compatible("1.9.9")
    assert not is_payload_compatible("3.0.0")


def test_generator_emits_schema_three_interface_and_five_gates() -> None:
    """@brief Verify the policy-neutral generator owns the complete new schema."""
    template = (
        Path(__file__).parents[2]
        / "aegis"
        / "template"
        / ".agentic"
        / "workflow.toml"
    )
    answers = {spec.key: spec.default for spec in WORKFLOW_FIELD_SPECS}
    generated = generate_workflow_toml(
        template.read_text(encoding="utf-8"),
        **answers,
    )
    document = tomllib.loads(generated.text)
    verify_workflow_schema(document)
    assert document["schema_version"] == 3
    assert document["interface"] == {
        "stage_form_retention": "discard",
        "check_execution": "external",
    }
    assert tuple(document["gates"]) == GATE_ORDER
    assert all(document["gates"][name]["mode"] == "disabled" for name in GATE_ORDER)


def test_analysis_proposes_security_only_from_explicit_script(
    tmp_path: Path,
) -> None:
    """@brief Ensure repository analysis does not invent a security command."""
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "scripts": {
                    "build": "tsc",
                    "security": "semgrep --config policy.yml",
                }
            }
        ),
        encoding="utf-8",
    )
    analysis = analyze_repo(tmp_path, runner=_NoGitRunner())
    assert analysis.gate_build_cmds[0].source_detail == "scripts.build"
    assert analysis.gate_security_cmds[0].source_detail == "scripts.security"
    assert analysis.gate_security_cmds[0].argv == ("npm", "run", "security")


class _NoGitRunner(CommandRunner):
    """@brief Minimal runner forcing read-only filesystem inventory fallback."""

    def run(self, argv, *, timeout=5.0, cwd=None):  # type: ignore[no-untyped-def]
        """@brief Return a non-zero Git result without executing anything."""
        from waegis.probes.runner import CommandResult

        return CommandResult(
            found=True,
            exit_code=1,
            stdout="",
            stderr="not a git repository",
            timed_out=False,
        )


# END OF FILE
