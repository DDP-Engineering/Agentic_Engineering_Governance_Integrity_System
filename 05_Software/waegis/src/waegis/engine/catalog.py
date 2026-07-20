#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file catalog.py
@brief Step registration, ordering, and precondition resolution (plan §4).
@details A ``Catalog`` is an ordered set of ``StepSpec`` objects that serves both
         wizard journeys. It validates itself at construction ("registration
         time"): duplicate ids, unknown precondition ids, and precondition cycles
         all raise ``CatalogError``. The canonical order is a stable topological
         sort that honours both registration order and preconditions, so a step
         never runs before a step it depends on. ``plan_for`` filters the ordered
         steps through ``applies(ctx)`` so one catalog drives both modes and
         optional branches.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from .step import CatalogError, EngineContext, StepSpec

# PUBLIC API


class Catalog:
    """
    @brief Validated, ordered collection of wizard steps.
    @details Construction is the single validation point: the constructor rejects
             duplicate ids, preconditions that name an unknown step, and any
             precondition cycle. The stored order is a deterministic topological
             sort (Kahn's algorithm, breaking ties by registration order) so the
             runner can execute steps in a single forward pass.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self, steps: list[StepSpec] | tuple[StepSpec, ...]) -> None:
        """
        @brief      Register and validate a catalog of steps.
        @param[in]  steps Step specs in registration order.
        @return     None
        @exception  CatalogError If an id is duplicated, a precondition names an
                    unknown step, or the preconditions contain a cycle.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        registration = list(steps)
        by_id: dict[str, StepSpec] = {}
        for spec in registration:
            if spec.id in by_id:
                raise CatalogError(f"duplicate step id: {spec.id!r}")
            by_id[spec.id] = spec
        self._by_id: dict[str, StepSpec] = by_id
        self._registration: tuple[StepSpec, ...] = tuple(registration)
        self._validate_preconditions()
        self._ordered: tuple[StepSpec, ...] = self._topological_order()

    def _validate_preconditions(self) -> None:
        """
        @brief      Reject preconditions that name a step not in the catalog.
        @return     None
        @exception  CatalogError If any precondition id is unknown or self-referential.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        for spec in self._registration:
            for pre in spec.preconditions:
                if pre == spec.id:
                    raise CatalogError(f"step {spec.id!r} lists itself as a precondition")
                if pre not in self._by_id:
                    raise CatalogError(
                        f"step {spec.id!r} has unknown precondition {pre!r}"
                    )

    def _topological_order(self) -> tuple[StepSpec, ...]:
        """
        @brief      Order steps so preconditions precede dependents, breaking ties
                    by registration order (Kahn's algorithm).
        @return     Steps in stable topological order.
        @exception  CatalogError If the preconditions contain a cycle.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        index = {spec.id: position for position, spec in enumerate(self._registration)}
        remaining = {spec.id: set(spec.preconditions) for spec in self._registration}
        ordered: list[StepSpec] = []
        while remaining:
            ready = [sid for sid, pres in remaining.items() if not pres]
            if not ready:
                cyclic = ", ".join(sorted(remaining))
                raise CatalogError(f"precondition cycle among steps: {cyclic}")
            nxt = min(ready, key=lambda sid: index[sid])
            ordered.append(self._by_id[nxt])
            del remaining[nxt]
            for pres in remaining.values():
                pres.discard(nxt)
        return tuple(ordered)

    def get(self, step_id: str) -> StepSpec:
        """
        @brief      Look up a step by id.
        @param[in]  step_id Step id to resolve.
        @return     The matching :class:`StepSpec`.
        @exception  CatalogError If no step has that id.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        try:
            return self._by_id[step_id]
        except KeyError:
            raise CatalogError(f"unknown step id: {step_id!r}") from None

    def ordered(self) -> tuple[StepSpec, ...]:
        """
        @brief      Return every step in canonical (topological) order.
        @return     Ordered tuple of all registered steps.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return self._ordered

    def plan_for(self, ctx: EngineContext) -> list[StepSpec]:
        """
        @brief      Return the ordered steps that apply to the given context.
        @param[in]  ctx Engine context whose mode/branch selects steps.
        @return     Ordered list of steps for which ``applies(ctx)`` is true.
        @exception  Exception Propagates any error raised by a step's ``applies``.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return [spec for spec in self._ordered if spec.applies(ctx)]

    def __len__(self) -> int:
        """
        @brief      Number of registered steps.
        @return     Step count.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return len(self._registration)

    def __iter__(self):
        """
        @brief      Iterate steps in canonical order.
        @return     Iterator over the ordered steps.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return iter(self._ordered)


# END OF FILE
