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
@brief Pytest bootstrap for the AEGIS dev project.
@details The test suite imports the CLI from the single-source template tree
         under ``template/.agentic/cli/src``. Disabling bytecode writes keeps
         that shipped tree free of ``__pycache__`` artifacts during testing.
"""

# IMPORTS

from __future__ import annotations

import sys

# CONSTANTS

# @brief Prevent ``.pyc`` files from being written next to the template source
#        so the shipped template stays clean and reproducible.
sys.dont_write_bytecode = True

# END OF FILE
