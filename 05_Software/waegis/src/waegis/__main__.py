#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file __main__.py
@brief Module entry point for the WAEGIS wizard (``python -m waegis``).
@details Delegates to :func:`waegis.cli.main` and propagates its integer exit
         code to the process.
"""

# IMPORTS

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
