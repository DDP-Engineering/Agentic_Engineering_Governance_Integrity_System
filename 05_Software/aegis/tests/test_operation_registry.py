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
@file    test_operation_registry.py
@brief   Verify the version 1 operation catalog and flat command contract.
@details Covers the IP-01 subset of PR-PROTO-006 and AC-PROTO-001.
"""

# -----------------------------------------------------------------------------
# IMPORTS
# -----------------------------------------------------------------------------

import re

from aegis.application.operation_registry import (
    ALL_OPERATIONS,
    command_for,
    operations_for,
)

# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


def test_registry_declares_all_56_unique_protocol_operations() -> None:
    """@brief Verify the complete cross-product catalog is declared once."""
    operation_ids = [entry.operation for entry in ALL_OPERATIONS]
    commands = [entry.command for entry in ALL_OPERATIONS]

    assert len(ALL_OPERATIONS) == 56
    assert len(operation_ids) == len(set(operation_ids))
    assert len(commands) == len(set(commands))


def test_registry_derives_every_command_mechanically() -> None:
    """@brief Verify dotted and underscored identifiers map canonically."""
    for entry in ALL_OPERATIONS:
        expected = entry.operation.replace(".", "-").replace("_", "-")
        assert entry.command == expected
        assert command_for(entry.operation) == expected


def test_product_catalogs_keep_aegis_and_waegis_boundaries_explicit() -> None:
    """@brief Verify common metadata does not expose WAEGIS actions in AEGIS."""
    aegis = operations_for("AEGIS")
    waegis = operations_for("WAEGIS")

    assert len(aegis) == 48
    assert len(waegis) == 10
    assert {entry.operation for entry in aegis if entry.implemented} == {
        "help.show",
        "version.show",
    }
    assert "install.apply" not in {entry.operation for entry in aegis}
    assert "run.create" not in {entry.operation for entry in waegis}


def test_registry_owns_complete_bounded_help_and_execution_metadata() -> None:
    """@brief Verify every catalog declaration can drive help and dispatch."""
    for entry in ALL_OPERATIONS:
        assert entry.purpose
        assert entry.result
        assert entry.example
        assert "\n" not in entry.example
        assert "&&" not in entry.example
        assert ";" not in entry.example
        assert callable(entry.executor)
        assert all(argument.name for argument in entry.arguments)
        assert all(argument.description for argument in entry.arguments)
        assert set(entry.required_arguments).isdisjoint(entry.optional_arguments)


def test_registry_declares_representative_final_cli_input_schemas() -> None:
    """@brief Verify parser-relevant input contracts live in the registry."""
    by_operation = {entry.operation: entry for entry in ALL_OPERATIONS}

    run_create = by_operation["run.create"]
    assert run_create.required_arguments == ("--input <source>",)
    assert run_create.optional_arguments == ()

    run_profile = by_operation["run.set_profile"]
    assert run_profile.arguments[0].choices == ("full", "short")

    stage_show = by_operation["stage.show"]
    assert stage_show.optional_arguments == ("--run <id>", "--stage <name>")


def test_registry_declares_canonical_execution_and_stage_choices() -> None:
    """@brief Verify CP execution categories and Stage names are exact."""
    by_operation = {entry.operation: entry for entry in ALL_OPERATIONS}
    stages = (
        "intake",
        "alignment",
        "requirement",
        "design",
        "check",
        "implementation",
        "validation",
        "delivery",
    )

    execution = by_operation["execution.run"]
    category, _, selection = execution.arguments
    assert category.display_name == "--category <tests|lints|audits>"
    assert category.description == "Select the tests, lints, or audits category."
    assert category.choices == ("tests", "lints", "audits")
    assert execution.example == "aegis execution-run --category tests --name project"
    assert selection.display_name == "--selection <label>"

    assert by_operation["stage.start"].arguments[0].choices == stages
    assert by_operation["stage.show"].arguments[1].choices == stages


def test_registry_examples_use_canonical_version_1_identity_shapes() -> None:
    """@brief Reject known placeholder identities from minimal examples."""
    examples = "\n".join(entry.example for entry in ALL_OPERATIONS)
    by_operation = {entry.operation: entry for entry in ALL_OPERATIONS}
    canonical_hex = "0123456789abcdef0123456789abcdef"
    forbidden = (
        "REQ-001",
        "CMP-001",
        "ADP-001",
        "F-001",
        "stage-revisit review",
        "<32hex>",
        "abc123",
        "--confirm-digest abc",
    )

    assert not any(value in examples for value in forbidden)
    assert f"REQ-{canonical_hex}" in by_operation["requirement.show"].example
    assert f"COMP-{canonical_hex}" in by_operation["component.show"].example
    assert f"ADOPT-{canonical_hex}" in by_operation["adoption.show"].example
    assert "--finding F1" in by_operation["finding.waive"].example

    apply_examples = [
        entry.example for entry in ALL_OPERATIONS if entry.operation.endswith(".apply")
    ]
    for example in apply_examples:
        digest = example.rsplit("--confirm-digest ", 1)[1]
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", digest)


# -----------------------------------------------------------------------------
# END OF FILE
# -----------------------------------------------------------------------------
