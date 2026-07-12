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
@brief Package marker for the WAEGIS guided wizard.
@details WAEGIS configures and deploys the AEGIS template payload into target
         repositories. It is a separate, stdlib-only package (AD-1/AD-3) and is
         never copied into the payload itself.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from .version import WIZARD_VERSION

# CONSTANTS

__version__ = WIZARD_VERSION

# END OF FILE
