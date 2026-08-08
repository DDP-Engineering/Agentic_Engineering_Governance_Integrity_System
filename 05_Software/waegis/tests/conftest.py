#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file conftest.py @brief Isolate per-user runtime/cache state in every test."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_waegis_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """@brief Prevent integration tests from changing the operator's WAEGIS home."""
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    monkeypatch.delenv("AEGIS_PYTHON", raising=False)
    monkeypatch.delenv("WAEGIS_PACKAGED_RUNTIME", raising=False)
    monkeypatch.delenv("WAEGIS_PACKAGING_TYPE", raising=False)


# END OF FILE
