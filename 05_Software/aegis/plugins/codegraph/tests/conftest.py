#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file conftest.py
@brief Shared helpers for the CodeGraph plugin test suite.
@details Puts the plugin folder first on `sys.path` so `import codegraph`
         resolves to the package under test, and offers helpers that run the
         real entry point in a subprocess with the same interpreter flags
         AEGIS uses. Tests that assert "nothing was written" run against a
         fresh copy of the plugin folder so no earlier import can have left
         bytecode behind.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# CONSTANTS

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
ENTRY = PLUGIN_ROOT / "codegraph.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
#: interpreter flags AEGIS passes when it launches the plugin
DISPATCH_FLAGS = ("-I", "-B", "-X", "utf8")

sys.dont_write_bytecode = True
#: spawned extraction workers do not inherit the runtime flag; the variable reaches them
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

# HELPER FUNCTIONS


def copy_plugin(target: Path) -> Path:
    """
    @brief Copy the plugin folder without tests or bytecode caches.
    @param[in] target Destination folder; created by this call.
    @return Path of the copied entry point.
    """
    shutil.copytree(PLUGIN_ROOT, target, ignore=shutil.ignore_patterns(
        "tests", "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache"))
    return target / "codegraph.py"


def run_entry(args: list[str], entry: Path = ENTRY, flags=DISPATCH_FLAGS,
              env: dict | None = None, stdin=subprocess.DEVNULL,
              timeout: float = 120) -> subprocess.CompletedProcess:
    """
    @brief Run the plugin entry point the way AEGIS does and capture output.
    @param[in] args Operation and options after the script path.
    @param[in] entry Entry script to run, normally the canonical one.
    @param[in] flags Interpreter flags placed before the script path.
    @param[in] env Extra environment variables merged over the current ones.
    @return The completed process with text stdout and stderr.
    """
    environment = dict(os.environ)
    environment.update(env or {})
    return subprocess.run([sys.executable, *flags, str(entry), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          stdin=stdin, env=environment, timeout=timeout,
                          check=False)


def run_json(args: list[str], **kwargs) -> tuple[int, dict]:
    """@brief Run the entry with `--json` (before any `--` marker) and parse its output."""
    split = args.index("--") if "--" in args else len(args)
    done = run_entry([*args[:split], "--json", *args[split:]], **kwargs)
    assert done.stdout.strip(), done.stderr
    return done.returncode, json.loads(done.stdout)


def tree_state(root: Path) -> dict[str, tuple[int, bytes]]:
    """@brief Every file and folder under root with its size and content."""
    state: dict[str, tuple[int, bytes]] = {}
    for path in sorted(root.rglob("*")):
        key = path.relative_to(root).as_posix()
        if path.is_dir():
            state[key + "/"] = (0, b"")
        else:
            data = path.read_bytes()
            state[key] = (len(data), data)
    return state


def git(root: Path, *args: str) -> str:
    """@brief Run git in root and return stdout; failures raise."""
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout


def make_repo(root: Path, files: dict[str, str], source=("src/",), tests=(),
              extra: str = "", use_git: bool = False, ignore_storage: bool = True) -> Path:
    """
    @brief Build a small repository with CodeGraph enabled.
    @param[in] files Repository-relative path to text content.
    @param[in] source `[layout] source` patterns.
    @param[in] tests `[layout] tests` patterns.
    @param[in] extra Extra lines appended to the `[codegraph]` table.
    @param[in] use_git Initialise Git and commit the files.
    @param[in] ignore_storage With Git, ignore `.agentic/knowledge/codegraph/`.
    @return The repository root.
    """
    root.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    config = root / ".agentic" / "aegis.toml"
    (root / ".agentic" / "knowledge").mkdir(parents=True, exist_ok=True)  # as AEGIS init creates it
    config.write_text(
        "[layout]\n"
        f"source = {json.dumps(list(source))}\n"
        f"tests = {json.dumps(list(tests))}\n"
        "[codegraph]\nenabled = true\n" + extra + "\n", encoding="utf-8")
    if use_git:
        git(root, "init", "-q")
        git(root, "config", "user.email", "test@example.invalid")
        git(root, "config", "user.name", "Test")
        git(root, "config", "core.autocrlf", "false")
        if ignore_storage:
            (root / ".gitignore").write_text(".agentic/knowledge/codegraph/\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "fixture")
    return root


# FIXTURES


@pytest.fixture()
def plugin_copy(tmp_path: Path) -> Path:
    """@brief A fresh plugin folder copy; returns its entry point."""
    return copy_plugin(tmp_path / "plugin")

# END OF FILE
