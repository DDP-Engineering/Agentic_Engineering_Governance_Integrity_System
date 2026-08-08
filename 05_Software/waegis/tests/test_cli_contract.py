#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_cli_contract.py
@brief Tests the WAEGIS 3 command vocabulary and version envelope.
@details Pins removal of RepoWise and addition of check while preserving doctor
         as a documented alias.
"""

import io
import json

from waegis.cli import EXIT_ERROR, EXIT_OK, build_parser, main


def test_parser_exposes_only_the_v3_command_groups() -> None:
    """@brief D1 removes RepoWise and V2 makes check the primary health command."""
    parser = build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")  # type: ignore[attr-defined]
    assert set(subparsers.choices) == {
        "new",
        "adopt",
        "analyze",
        "configure",
        "check",
        "doctor",
        "repair",
        "upgrade",
        "version",
    }


def test_version_json_is_one_v2_document() -> None:
    """@brief D4/D6 and schema identity are visible without mutation."""
    out = io.StringIO()
    err = io.StringIO()
    assert main(["version", "--json"], stdout=out, stderr=err) == EXIT_OK
    value = json.loads(out.getvalue())
    assert err.getvalue() == ""
    assert value["schema_version"] == 2
    assert value["command"] == "version"
    assert value["result"]["waegis_version"] == "3.0.0"
    assert value["result"]["bundled_payload_version"] == "3.0.0"
    assert value["result"]["compatible_payload_range"] == ">=3.0.0,<4.0.0"
    assert value["result"]["manifest_schema"] == 2


def test_pending_scaffold_command_fails_without_mutation() -> None:
    """@brief Phase 1 does not claim command success before implementation."""
    out = io.StringIO()
    err = io.StringIO()
    assert main(["analyze", "--repo", ".", "--json"], stdout=out, stderr=err) == EXIT_ERROR
    value = json.loads(out.getvalue())
    assert value["status"] == "failed"
    assert "Phase 1 scaffold" in value["messages"][0]
    assert err.getvalue() == ""


# END OF FILE
