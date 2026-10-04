#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_natives.py
@brief Vendored parser selection and indexing capability (REQ-PLAT-dc7bdd06).
@details The vendored folder holds one binary per supported interpreter; these
         tests check that the running interpreter finds its own, that an
         unmatched or untested interpreter is reported truthfully, that the
         read side never loads a native module, and that an installed
         `tree_sitter` cannot shadow the vendored copy.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import PLUGIN_ROOT

from codegraph import natives

# TESTS


def test_running_interpreter_can_index_and_reports_its_matrix_status():
    """REQ-PLAT-dc7bdd06: this interpreter has a vendored binary."""
    manifest = natives.read_manifest()
    capability = natives.capability()
    assert capability["indexing_supported"] is True
    expected = "tested" if natives.platform_key() in manifest["tested"] else "untested"
    assert capability["python_support"] == expected


def test_interpreter_without_a_matching_binary_cannot_index():
    """REQ-PLAT-dc7bdd06: no matching extension suffix means no indexing."""
    capability = natives.capability(suffixes=[".cpython-399-fake-platform.so"])
    assert capability == {"indexing_supported": False, "python_support": None}


def test_compatible_binary_outside_the_tested_matrix_is_untested():
    """REQ-PLAT-dc7bdd06: a usable but untested interpreter says so."""
    capability = natives.capability(manifest={"tested": []})
    assert capability == {"indexing_supported": True, "python_support": "untested"}


def test_capability_check_loads_no_native_module():
    """REQ-PLAT-dc7bdd06: the read side never imports a parser binary."""
    script = (
        "import sys, json; sys.dont_write_bytecode = True; "
        f"sys.path.insert(0, {str(PLUGIN_ROOT)!r}); "
        "from codegraph import natives; natives.capability(); "
        "print(json.dumps(sorted(m for m in sys.modules if m.startswith('tree_sitter'))))"
    )
    done = subprocess.run([sys.executable, "-I", "-B", "-c", script],
                          capture_output=True, text=True, check=True)
    assert json.loads(done.stdout) == []


def test_vendored_parser_wins_over_an_installed_package(tmp_path: Path):
    """REQ-PLAT-dc7bdd06: a foreign tree_sitter on the path is never loaded."""
    fake = tmp_path / "site" / "tree_sitter"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("raise ImportError('foreign copy')\n",
                                      encoding="utf-8")
    script = (
        "import sys; sys.dont_write_bytecode = True; "
        f"sys.path.insert(0, {str(PLUGIN_ROOT)!r}); "
        "from codegraph import natives; natives.ensure_on_path(); "
        "import tree_sitter; print(tree_sitter.__file__)"
    )
    for flags in (["-I", "-B"], ["-B"]):
        done = subprocess.run(
            [sys.executable, *flags, "-c", script], capture_output=True,
            text=True, env=dict(os.environ, PYTHONPATH=str(fake.parent)),
            check=True)
        loaded = Path(done.stdout.strip()).resolve()
        assert loaded.is_relative_to((PLUGIN_ROOT / "vendor").resolve()), flags


def test_vendored_parser_parses_python_source():
    """REQ-PLAT-dc7bdd06: the vendored binding and grammar work together."""
    parser = natives.new_parser()
    tree = parser.parse(b"def answer():\n    return 42\n")
    assert tree.root_node.type == "module"
    assert not tree.root_node.has_error

# TESTS - committed natives (REQ-PLAT-dc7bdd06)


def test_git_would_commit_every_vendored_file():
    """REQ-PLAT-dc7bdd06: no ignore rule (such as `*.py[cod]`) hides a native binding."""
    probe = subprocess.run(["git", "-C", str(PLUGIN_ROOT), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL,
                           check=False)
    if probe.returncode != 0:
        pytest.skip("the plugin source is not inside a Git work tree")
    top = Path(probe.stdout.strip())
    folders = [PLUGIN_ROOT / "vendor", top / ".agentic" / "plugins" / "codegraph" / "vendor"]
    files = [path.resolve().relative_to(top.resolve()).as_posix() for folder in folders
             if folder.is_dir() for path in folder.rglob("*") if path.is_file()]
    assert files
    # paths go as arguments: text-mode stdin on Windows would end each line with \r
    ignored = subprocess.run(["git", "-C", str(top), "check-ignore", "--no-index", "--", *files],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL,
                             check=False)
    # exit 1 means no path is ignored; 0 lists the ignored paths; anything else is a Git error
    assert (ignored.returncode, ignored.stdout.strip()) == (1, ""), (ignored.stdout,
                                                                    ignored.stderr)

# END OF FILE
