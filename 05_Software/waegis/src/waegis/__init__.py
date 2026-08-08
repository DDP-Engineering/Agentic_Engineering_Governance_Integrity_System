#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __init__.py
@brief Public WAEGIS package identity.
@details Exposes the project version without importing command or payload code.
"""

from .version import WIZARD_VERSION

__version__ = WIZARD_VERSION

__all__ = ["WIZARD_VERSION", "__version__"]

# END OF FILE
