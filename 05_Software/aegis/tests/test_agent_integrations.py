#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: UP009
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""@file test_agent_integrations.py
@brief Execute portable plugin behavior tests through the existing pytest suite.
@details Uses temporary package outputs and actual managed AEGIS fixtures;
         no model requests, personal installations or repository Git writes.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
TESTS = REPO / "05_Software/aegis/integrations/tests"


@pytest.fixture(scope="module")
def integration_env(tmp_path_factory):
    """@brief Build isolated packages with the installed Node runtime."""
    node = shutil.which("node")
    assert node, "Node.js 22+ is required for the plugin verification suite"
    output = tmp_path_factory.mktemp("agent-plugins")
    result = subprocess.run(
        [node, str(REPO / "02_Tools/build_agent_plugins.mjs"), "--output", str(output)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    env = {**os.environ, "AEGIS_PYTHON": sys.executable,
           "AEGIS_TEST_PAYLOAD": str(REPO / "05_Software/aegis/template/.agentic"),
           "AEGIS_TEST_PACKAGES": str(output)}
    return node, env


def run_group(integration_env, filename, pattern=None):
    """@brief Run one behavioral group and surface its real exit status."""
    node, env = integration_env
    command = [node, "--test"]
    if pattern:
        command.append("--test-name-pattern=" + pattern)
    command.append(str(TESTS / filename))
    result = subprocess.run(command, env=env, capture_output=True, text=True,
                            timeout=120, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_opencode_behavior(integration_env):
    """@brief REQ-FUNC-ffc5802a, REQ-FUNC-1ca0ff21: native registration."""
    run_group(integration_env, "interfaces.test.mjs", "opencode:")


def test_codex_behavior(integration_env):
    """@brief REQ-FUNC-92f78e33: packaged bridge resolves installed governance."""
    run_group(integration_env, "interfaces.test.mjs", "codex:")


def test_review_behavior(integration_env):
    """@brief REQ-SEC-16e8890a: reviewers cannot request adapter mutations."""
    run_group(integration_env, "interfaces.test.mjs", "review:")


def test_adapter_behavior(integration_env):
    """@brief REQ-DATA-5e4bf048, REQ-REL-0ef6add6: actual CLI and job lifecycle."""
    run_group(integration_env, "adapter.test.mjs")


def test_install_behavior(integration_env):
    """@brief REQ-PLAT-a3ae118a, REQ-REL-7a97428b: owned-file lifecycle."""
    run_group(integration_env, "lifecycle.test.mjs")


def test_runtime_behavior(integration_env):
    """@brief REQ-PLAT-af657d59: executable discovery without models."""
    run_group(integration_env, "interfaces.test.mjs", "runtime:")
