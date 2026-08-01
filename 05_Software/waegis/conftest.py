#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file conftest.py
@brief Pytest bootstrap for the WAEGIS dev project.
@details The test suite imports the wizard package from ``src`` (wired through
         the ``pythonpath`` pytest option). Disabling bytecode writes keeps the
         source tree free of ``__pycache__`` artifacts during testing.
"""

# IMPORTS

from __future__ import annotations

import sys

# @brief Prevent ``.pyc`` files from being written next to the wizard source so
#        the tree stays clean and reproducible during testing.
sys.dont_write_bytecode = True
