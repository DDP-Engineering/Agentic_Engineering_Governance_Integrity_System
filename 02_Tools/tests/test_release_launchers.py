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

import json
import os
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

    def test_external_editions_check_python_312_and_git(self) -> None:
        """@brief AC-RUNTIME-001 external launchers check exact prerequisites."""
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary)
            for platform in ("windows-x86_64", "ubuntu-22.04-x86_64"):
                for product in ("aegis", "waegis"):
                    archive = release.build_archive(
                        REPOSITORY,
                        output,
                        product=product,
                        platform=platform,
                        with_dependencies=False,
                        runtime_lock=TOOLS / "runtime_inputs.toml",
                    )
                    with zipfile.ZipFile(archive) as bundle:
                        prerequisites = bundle.read("PREREQUISITES.md").decode()
                        inventory = json.loads(
                            bundle.read("ARCHIVE_INVENTORY.json")
                        )
                        if product == "aegis":
                            launcher = (
                                ".agentic/aegis/bin/aegis.cmd"
                                if platform == "windows-x86_64"
                                else ".agentic/aegis/bin/aegis"
                            )
                        else:
                            launcher = (
                                "bin/waegis.cmd"
                                if platform == "windows-x86_64"
                                else "bin/waegis"
                            )
                        wrapper = bundle.read(launcher).decode()

                    self.assertIn("Python 3.12", prerequisites)
                    self.assertIn("Git", prerequisites)
                    self.assertEqual("external 3.12", inventory["python_version"])
                    if platform == "windows-x86_64":
                        self.assertIn("py -3.12", wrapper)
                        self.assertIn("where git", wrapper)
                    else:
                        self.assertIn("python3.12", wrapper)
                        self.assertIn("command -v git", wrapper)

    @unittest.skipUnless(sys.platform == "win32", "Windows launcher smoke test")
    def test_windows_external_archives_launch_through_cmd(self) -> None:
        """@brief AC-PKG-001 extracted Windows entry points execute cleanly."""
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
                launcher = (
                    extracted / ".agentic/aegis/bin/aegis.cmd"
                    if product == "aegis"
                    else extracted / "bin/waegis.cmd"
                )
                completed = subprocess.run(
                    [
                        os.environ.get("COMSPEC", "cmd.exe"),
                        "/d",
                        "/c",
                        str(launcher),
                        "--format",
                        "json",
                        "version-show",
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertEqual([], list(extracted.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
