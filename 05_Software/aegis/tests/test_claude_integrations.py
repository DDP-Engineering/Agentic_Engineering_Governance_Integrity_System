#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file test_claude_integrations.py
@brief Verify native Claude Code integration behavior without model requests.
@details Build isolated packages and exercise host APIs, protocol and lifecycle.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def run_group(selector):
    """@brief Exercise actual model-free Claude integration behavior."""
    node = shutil.which("node")
    assert node, "Node.js 22+ is required"
    result = subprocess.run(
        [node, "--test", "--test-name-pattern=" + selector + ":",
         str(REPO / "05_Software/aegis/integrations/tests/claude.test.mjs")],
        env={**os.environ, "AEGIS_PYTHON": sys.executable}, capture_output=True,
        text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_resources_behavior():
    """@brief Verify Claude resources behavior."""
    run_group("resources")


def test_hooks_behavior():
    """@brief Verify Claude hooks behavior."""
    run_group("hooks")


def test_install_behavior():
    """@brief Verify Claude install behavior."""
    run_group("install")


def test_ownership_behavior():
    """@brief Verify Claude ownership behavior."""
    run_group("ownership")


def test_build_behavior():
    """@brief Verify Claude build behavior."""
    run_group("build")
