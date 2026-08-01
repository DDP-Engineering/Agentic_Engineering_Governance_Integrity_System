#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_engine_catalog.py
@brief Catalog validation and ordering tests for the WAEGIS engine (T1.1).
@details Covers requirement R6 (safe, resumable runs rest on a well-formed
         catalog): unknown-precondition and cycle rejection at registration
         time, duplicate-id rejection, ``applies()`` filtering that lets one
         catalog serve both wizard modes, and stable precondition-aware ordering.
         Strictly offline.
"""

# IMPORTS

from __future__ import annotations

import pytest

from waegis.engine import (
    Automation,
    Catalog,
    CatalogError,
    Phase,
    StepContractError,
    StepSpec,
)

from _toy_catalog import build_toy_catalog, make_ctx

# LOCAL HELPERS


def _spec(step_id: str, preconditions: tuple[str, ...] = ()) -> StepSpec:
    """
    @brief      Build a minimal valid step for catalog tests.
    @param[in]  step_id Step id.
    @param[in]  preconditions Precondition ids.
    @return     A :class:`StepSpec` with a trivial passing ``verify``.
    """
    return StepSpec(
        id=step_id,
        title=step_id,
        why="test step",
        phase=Phase.P0_MACHINE,
        automation=Automation.AUTO,
        preconditions=preconditions,
        verify=lambda ctx: True,
    )


# TESTS


def test_verify_is_required_at_construction() -> None:
    """
    @brief      A step built without ``verify`` is rejected (R5: verify required).
    @return     None
    @exception  AssertionError If construction does not raise.
    """
    with pytest.raises(StepContractError):
        StepSpec(
            id="x",
            title="x",
            why="no verify supplied",
            phase=Phase.P0_MACHINE,
            automation=Automation.AUTO,
        )


def test_unknown_precondition_rejected() -> None:
    """
    @brief      A precondition naming an unknown step is rejected at registration.
    @return     None
    @exception  AssertionError If the catalog constructs without error.
    """
    with pytest.raises(CatalogError):
        Catalog([_spec("a", preconditions=("does-not-exist",))])


def test_precondition_cycle_rejected() -> None:
    """
    @brief      A precondition cycle is rejected at registration time.
    @return     None
    @exception  AssertionError If the catalog constructs without error.
    """
    with pytest.raises(CatalogError):
        Catalog([_spec("a", preconditions=("b",)), _spec("b", preconditions=("a",))])


def test_duplicate_id_rejected() -> None:
    """
    @brief      Two steps sharing an id are rejected.
    @return     None
    @exception  AssertionError If the catalog constructs without error.
    """
    with pytest.raises(CatalogError):
        Catalog([_spec("a"), _spec("a")])


def test_stable_precondition_order() -> None:
    """
    @brief      Steps are ordered so preconditions precede dependents.
    @return     None
    @exception  AssertionError If the order violates preconditions.
    """
    catalog = build_toy_catalog()
    order = [spec.id for spec in catalog.ordered()]
    assert order.index("toy.a") < order.index("toy.b") < order.index("toy.c")


def test_topological_reorders_out_of_order_registration() -> None:
    """
    @brief      A dependent registered before its precondition is still ordered
                after it.
    @return     None
    @exception  AssertionError If the precondition is not moved ahead.
    """
    catalog = Catalog([_spec("b", preconditions=("a",)), _spec("a")])
    order = [spec.id for spec in catalog.ordered()]
    assert order == ["a", "b"]


def test_applies_filtering_selects_branch() -> None:
    """
    @brief      ``plan_for`` includes an ``applies``-gated step only when enabled.
    @return     None
    @exception  AssertionError If filtering does not honour the branch flag.
    """
    catalog = build_toy_catalog(include_optional=True)

    ctx_off = make_ctx(shared={"include_opt": False})
    ctx_on = make_ctx(shared={"include_opt": True})

    ids_off = [spec.id for spec in catalog.plan_for(ctx_off)]
    ids_on = [spec.id for spec in catalog.plan_for(ctx_on)]

    assert "toy.opt" not in ids_off
    assert "toy.opt" in ids_on


# END OF FILE
