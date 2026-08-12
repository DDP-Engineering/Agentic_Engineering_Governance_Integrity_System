#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_release_launchers.py
@brief Focused regressions for relocatable release launchers.
@details Confirms that launching an archive does not modify product-owned code.
"""

import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

TOOLS = pathlib.Path(__file__).parents[1]
REPOSITORY = TOOLS.parent
sys.path.insert(0, str(TOOLS))

import build_aegis_release as release  # noqa: E402


class ReleaseLauncherTests(unittest.TestCase):
    """@brief Tests extracted package launch behavior."""

    def test_launchers_do_not_write_bytecode_into_product_files(self) -> None:
        """@brief Keeps package execution from creating removal residue."""
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            for product in ("aegis", "waegis"):
                archive = release.build_archive(
                    REPOSITORY,
                    root / "archives",
                    product=product,
                    platform="windows-x86_64",
                    with_dependencies=False,
                    runtime_lock=TOOLS / "runtime_inputs.toml",
                )
                extracted = root / product
                with zipfile.ZipFile(archive) as bundle:
                    bundle.extractall(extracted)
                if product == "aegis":
                    subprocess.run(
                        ["git", "init", "--quiet", str(extracted)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    launcher = extracted / ".agentic/aegis/bin/launcher.py"
                    product_root = extracted / ".agentic/aegis"
                    arguments = [
                        "--repo",
                        str(extracted),
                        "--format",
                        "json",
                        "version-show",
                    ]
                else:
                    launcher = extracted / "bin/launcher.py"
                    product_root = extracted / "lib/waegis"
                    arguments = ["--format", "json", "version-show"]
                completed = subprocess.run(
                    [sys.executable, str(launcher), *arguments],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertEqual([], list(product_root.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
