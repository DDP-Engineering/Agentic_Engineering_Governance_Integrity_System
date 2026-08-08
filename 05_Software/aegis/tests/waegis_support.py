#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file waegis_support.py
@brief Materialize a verified WAEGIS payload inventory for adapter tests.
@details Keeps adapter fixture setup separate from WAEGIS mutation orchestration;
         WAEGIS integration tests own Git, consent, recovery, and manifest behavior.
"""

# IMPORTS

from pathlib import Path
from typing import Iterable, Protocol


# DATA MODELS / TYPEDEFINITIONS


class InventoryRecordLike(Protocol):
    """@brief Structural path contract needed by the fixture materializer."""

    path: str


# EXPORTED FUNCTIONS / PUBLIC API


def materialize_inventory(source: Path, target: Path, records: Iterable[InventoryRecordLike]) -> tuple[str, ...]:
    """
    @brief Copy the already verified inventory bytes into an isolated fixture.
    @param[in] source Payload source root.
    @param[in] target Absent fixture destination.
    @param[in] records Verified WAEGIS inventory records.
    @return Canonical copied paths in inventory order.
    """
    target.mkdir()
    copied: list[str] = []
    for record in records:
        destination = target.joinpath(*record.path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.joinpath(*record.path.split("/")).read_bytes())
        copied.append(record.path)
    return tuple(copied)


# END OF FILE
