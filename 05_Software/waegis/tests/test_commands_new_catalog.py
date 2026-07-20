#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_new_catalog.py
@brief Wizard N catalog registration tests (T4.3): plan §8.1 parity.
@details Strictly offline. Proves the real catalog registers cleanly through
         ``Catalog``'s own validation (no duplicate ids, unknown
         preconditions, or cycles), mirrors plan §8.1 row for row (ids, order,
         automation kinds), chains preconditions linearly in table order, and
         ``applies()``-filters ``net.proxy`` exactly when no clone URL was
         answered.
@details ``deploy.gates`` deliberately deviates from plan §8.1 as of 0.1.1:
         ``AUTO`` rather than ``ASSISTED``, so a decline defers instead of
         halting the run (see ``_EXPECTED_AUTOMATION``'s inline comment).
@details ``prereq.node`` (0.1.2) is not in plan §8.1 at all — an
         architecture-review follow-up step, also ``AUTO``/warn-not-block.
@author Eng. Dan Dumitru Pasare
@date 2026-07-18
@version 0.1.2
"""

# IMPORTS

from __future__ import annotations

from waegis.commands.new import NEW_STEP_IDS, SHARED_CLONE_URL, build_new_catalog
from waegis.engine import Automation, EngineContext

from _toy_catalog import ScriptAsker

# CONSTANTS

# @brief Plan §8.1 automation column, keyed by step id.
_EXPECTED_AUTOMATION: dict[str, Automation] = {
    "home.init": Automation.AUTO,
    "machine.os": Automation.AUTO,
    "machine.disk": Automation.AUTO,
    "prereq.python": Automation.ASSISTED,
    "prereq.git": Automation.ASSISTED,
    # Not in plan §8.1 (architecture-review follow-up, 0.1.1): warn-not-block,
    # like machine.os, not ASSISTED like prereq.python/prereq.git.
    "prereq.node": Automation.AUTO,
    "prereq.git-identity": Automation.MANUAL,
    "net.proxy": Automation.AUTO,
    "repo.target-path": Automation.ASSISTED,
    "repo.init-or-clone": Automation.ASSISTED,
    "deploy.payload-copy": Automation.ASSISTED,
    "deploy.workflow-toml": Automation.ASSISTED,
    # Deliberately AUTO, not plan §8.1's ASSISTED: declining the generic
    # ASSISTED gate halts the whole run, but gate commands can be slow and an
    # operator should be able to defer them cleanly instead. _act_gates asks
    # its own "proceed?" confirmation and records a "deferred" outcome on
    # decline, so verify still passes.
    "deploy.gates": Automation.AUTO,
    "verify.cli-smoke": Automation.AUTO,
    "verify.workflow-smoke": Automation.AUTO,
    "verify.hooks-present": Automation.AUTO,
    "repo.initial-commit": Automation.ASSISTED,
    "handoff.summary": Automation.AUTO,
}


# LOCAL HELPERS


def _ctx(shared: dict | None = None) -> EngineContext:
    """
    @brief      Build a minimal context for applies()/plan_for checks.
    @param[in]  shared Initial shared mapping.
    @return     A ready :class:`EngineContext`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return EngineContext(mode="new", asker=ScriptAsker(), shared=shared if shared is not None else {})


# TESTS


def test_catalog_registers_and_matches_plan_order() -> None:
    """
    @brief      The real catalog constructs (Catalog validation: no duplicate
                ids, unknown preconditions, or cycles) and its canonical order
                mirrors plan §8.1 row for row.
    @return     None
    @exception  AssertionError If the ordered ids differ from plan §8.1.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.1
    """
    catalog = build_new_catalog()

    assert [spec.id for spec in catalog.ordered()] == list(NEW_STEP_IDS)
    assert len(catalog) == 18


def test_catalog_matches_plan_automation_kinds() -> None:
    """
    @brief      Every step's automation kind matches the plan §8.1 column
                (with the deliberate ``deploy.gates`` deviation, see
                ``_EXPECTED_AUTOMATION``).
    @return     None
    @exception  AssertionError On any automation mismatch.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.2
    """
    catalog = build_new_catalog()

    for spec in catalog.ordered():
        assert spec.automation is _EXPECTED_AUTOMATION[spec.id], spec.id


def test_catalog_preconditions_form_linear_chain() -> None:
    """
    @brief      Preconditions chain linearly in table order (each step requires
                exactly the previous one), realizing the P0->P5 phase order.
    @return     None
    @exception  AssertionError If any step's preconditions deviate.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    catalog = build_new_catalog()

    for index, spec in enumerate(catalog.ordered()):
        expected = () if index == 0 else (NEW_STEP_IDS[index - 1],)
        assert spec.preconditions == expected, spec.id


def test_net_proxy_applies_only_with_clone_url() -> None:
    """
    @brief      ``net.proxy.applies`` is False without a clone URL and True
                with one (plan §8.1: applies only when a remote clone is
                requested).
    @return     None
    @exception  AssertionError If the applies predicate misbehaves.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = build_new_catalog().get("net.proxy")

    assert spec.applies(_ctx({SHARED_CLONE_URL: ""})) is False
    assert spec.applies(_ctx({})) is False
    assert spec.applies(_ctx({SHARED_CLONE_URL: "https://forge.example.com/org/repo.git"})) is True


def test_plan_for_skips_net_proxy_without_clone_url() -> None:
    """
    @brief      The applies-filtered plan omits ``net.proxy`` for a local-only
                'git init' flow and includes it when a clone URL is answered,
                without disturbing any other step.
    @return     None
    @exception  AssertionError If the planned id lists are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    catalog = build_new_catalog()

    local_ids = [spec.id for spec in catalog.plan_for(_ctx({SHARED_CLONE_URL: ""}))]
    clone_ids = [
        spec.id for spec in catalog.plan_for(_ctx({SHARED_CLONE_URL: "https://forge.example.com/r.git"}))
    ]

    assert local_ids == [step_id for step_id in NEW_STEP_IDS if step_id != "net.proxy"]
    assert clone_ids == list(NEW_STEP_IDS)


# END OF FILE
