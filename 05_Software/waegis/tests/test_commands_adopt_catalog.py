#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_adopt_catalog.py
@brief Wizard E catalog registration + shared-object reuse tests (T5.2).
@details Offline, no git. Proves the plan §8.2 catalog is consistent (no
         duplicate ids, no unknown preconditions, no cycles - all enforced by
         the Catalog constructor) and, crucially, that the P0-P2 prefix, the
         deploy.gates step, and the three verify.* smoke steps are reused as the
         *same* StepSpec objects Wizard N runs (object identity, not lookalikes),
         while deploy.workflow-toml is an adopt-specific instance.
"""

# IMPORTS

from __future__ import annotations

from waegis.commands.adopt import ADOPT_STEP_IDS, build_adopt_catalog
from waegis.commands.new import NEW_STEP_IDS, build_new_catalog

# CONSTANTS

# @brief The step ids Wizard E reuses verbatim from Wizard N (plan §8.2): the
#        P0-P2 prefix, the gates step, and the three verify.* smoke steps.
_SHARED_IDS: tuple[str, ...] = (
    "home.init",
    "machine.os",
    "machine.disk",
    "prereq.python",
    "prereq.git",
    "prereq.git-identity",
    "net.proxy",
    "deploy.gates",
    "verify.cli-smoke",
    "verify.workflow-smoke",
    "verify.hooks-present",
)


# TESTS


def test_catalog_builds_in_plan_order_without_duplicates() -> None:
    """
    @brief      build_adopt_catalog() constructs cleanly (the Catalog ctor
                rejects duplicate ids / unknown preconditions / cycles) and its
                order matches ADOPT_STEP_IDS row for row (plan §8.2).
    @return     None
    @exception  AssertionError If the order or uniqueness is wrong.
    """
    ids = tuple(step.id for step in build_adopt_catalog().ordered())
    assert ids == ADOPT_STEP_IDS
    assert len(set(ids)) == len(ids)


def test_every_precondition_names_a_catalog_step() -> None:
    """
    @brief      Every precondition references a step id present in the catalog
                (no dangling preconditions).
    @return     None
    @exception  AssertionError If a precondition names an unknown step.
    """
    known = set(ADOPT_STEP_IDS)
    for step in build_adopt_catalog().ordered():
        for precondition in step.preconditions:
            assert precondition in known, f"{step.id} names unknown precondition {precondition}"


def test_shared_steps_are_the_same_objects_as_wizard_n() -> None:
    """
    @brief      The P0-P2 prefix, deploy.gates, and the three verify.* steps are
                the *same* StepSpec instances Wizard N runs (shared, not forked),
                while deploy.workflow-toml is an adopt-specific instance.
    @return     None
    @exception  AssertionError If any shared step is a distinct object, or the
                adopt-specific step is shared.
    """
    adopt_by_id = {step.id: step for step in build_adopt_catalog().ordered()}
    new_by_id = {step.id: step for step in build_new_catalog().ordered()}
    for step_id in _SHARED_IDS:
        assert adopt_by_id[step_id] is new_by_id[step_id], f"{step_id} is not the shared object"
    assert adopt_by_id["deploy.workflow-toml"] is not new_by_id["deploy.workflow-toml"]


def test_adopt_specific_step_ids_are_present() -> None:
    """
    @brief      The six adopt-specific step ids are registered and Wizard N does
                not carry them.
    @return     None
    @exception  AssertionError If an adopt-specific step is missing or leaked
                into Wizard N.
    """
    adopt_only = {
        "repo.validate-existing",
        "repo.prior-install",
        "analyze.repo",
        "deploy.adoption-copy",
        "repo.adoption-commit",
        "handoff.adoption",
    }
    assert adopt_only.issubset(set(ADOPT_STEP_IDS))
    assert adopt_only.isdisjoint(set(NEW_STEP_IDS))


# END OF FILE
