#!/usr/bin/env python3
"""
Verify native Pi and Qwen integration behavior without model requests.

Build isolated packages and exercise host APIs, protocol and lifecycle.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def native_env(tmp_path_factory):
    """Build a fresh four-host package set for the native behavior groups."""
    node = shutil.which("node")
    assert node, "Node.js 22+ is required for integration verification"
    output = tmp_path_factory.mktemp("additional-integrations")
    result = subprocess.run(
        [node, str(REPO / "02_Tools/build_agent_plugins.mjs"), "--output", str(output)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return node, {**os.environ, "AEGIS_PYTHON": sys.executable,
                  "AEGIS_TEST_PACKAGES": str(output),
                  "AEGIS_TEST_PAYLOAD": str(REPO / "05_Software/aegis/template/.agentic")}


def run_group(native_env, selector):
    """Surface an actual model-free Node behavior group's exit status."""
    node, env = native_env
    result = subprocess.run(
        [node, "--test", "--test-name-pattern=" + selector + ":",
         str(REPO / "05_Software/aegis/integrations/tests/additional.test.mjs")],
        env=env, capture_output=True, text=True, timeout=120, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_pi_behavior(native_env):
    """Verify Pi command and tool execution against the native API shape."""
    run_group(native_env, "pi")


def test_pi_review_behavior(native_env):
    """Verify independent Pi launch isolation and review inputs."""
    run_group(native_env, "pi_review")


def test_qwen_behavior(native_env):
    """Verify native Qwen extension resources and review restrictions."""
    run_group(native_env, "qwen")


def test_protocol_behavior(native_env):
    """Verify standard-input protocol discovery, validation and real calls."""
    run_group(native_env, "protocol")


def test_install_behavior(native_env):
    """Verify configuration preservation and installation ownership."""
    run_group(native_env, "install")


def test_build_behavior(native_env):
    """Verify four-host assembly and self-contained runtime placement."""
    run_group(native_env, "build")
