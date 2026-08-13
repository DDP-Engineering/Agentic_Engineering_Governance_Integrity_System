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
@details Confirms runtime checks preserve the structured product protocol.
"""

import json
import os
import pathlib
import shutil
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

    def test_external_editions_delegate_git_check_to_python(self) -> None:
        """@brief AC-RUNTIME-001 keeps only interpreter checks in wrappers."""
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
                        python_launcher = bundle.read(
                            launcher.rsplit("/", 1)[0] + "/launcher.py"
                        ).decode()

                    self.assertIn("Python 3.12", prerequisites)
                    self.assertIn("Git", prerequisites)
                    self.assertEqual("external 3.12", inventory["python_version"])
                    if platform == "windows-x86_64":
                        self.assertIn("py -3.12", wrapper)
                        self.assertNotIn("where git", wrapper)
                    else:
                        self.assertIn("python3.12", wrapper)
                        self.assertNotIn("command -v git", wrapper)
                    self.assertIn('shutil.which("git")', python_launcher)

    def test_missing_prerequisite_is_reported_as_an_envelope(self) -> None:
        """@brief PR-PROTO-004 reports missing Git through one JSON response."""
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            empty_path = root / "empty-path"
            empty_path.mkdir()
            environment = os.environ.copy()
            py_launcher = shutil.which("py") if sys.platform == "win32" else None
            isolated_path = (
                pathlib.Path(py_launcher).parent if py_launcher else empty_path
            )
            self.assertIsNone(shutil.which("git", path=str(isolated_path)))
            environment["PATH"] = str(isolated_path)

            for product in ("aegis", "waegis"):
                with self.subTest(product=product):
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
                        (extracted / ".git").mkdir()
                        launcher = extracted / ".agentic/aegis/bin/launcher.py"
                        wrapper = extracted / ".agentic/aegis/bin/aegis.cmd"
                        arguments = (
                            "--repo",
                            str(extracted),
                            "--format",
                            "json",
                            "config-show",
                        )
                        operation = "config.show"
                    else:
                        launcher = extracted / "bin/launcher.py"
                        wrapper = extracted / "bin/waegis.cmd"
                        arguments = (
                            "--format",
                            "json",
                            "repository-init-plan",
                            "--target",
                            str(extracted / "target"),
                            "--output",
                            str(extracted / "plan.json"),
                        )
                        operation = "repository_init.plan"

                    invocation = (
                        [
                            os.environ.get("COMSPEC", "cmd.exe"),
                            "/d",
                            "/c",
                            str(wrapper),
                            *arguments,
                        ]
                        if py_launcher
                        else [sys.executable, str(launcher), *arguments]
                    )
                    completed = subprocess.run(
                        invocation,
                        check=False,
                        capture_output=True,
                        text=True,
                        env=environment,
                    )

                    self.assertEqual(5, completed.returncode)
                    self.assertEqual("", completed.stderr)
                    self.assertEqual(1, completed.stdout.count("\n"))
                    response = json.loads(completed.stdout)
                    self.assertEqual("aegis.machine.response", response["schema"])
                    self.assertEqual(operation, response["operation"])
                    self.assertEqual("error", response["operation_status"])
                    self.assertEqual(
                        "missing_prerequisite", response["error"]["code"]
                    )

    def test_repository_free_operations_do_not_require_git(self) -> None:
        """@brief PR-PROTO-004 keeps help and version independent of Git."""
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            archive = release.build_archive(
                REPOSITORY,
                root / "archives",
                product="aegis",
                platform="windows-x86_64",
                with_dependencies=False,
                runtime_lock=TOOLS / "runtime_inputs.toml",
            )
            extracted = root / "aegis"
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(extracted)
            empty_path = root / "empty-path"
            empty_path.mkdir()
            environment = os.environ.copy()
            environment["PATH"] = str(empty_path)
            launcher = extracted / ".agentic/aegis/bin/launcher.py"

            for arguments in (
                ("--format", "json", "version-show"),
                ("--format", "json", "--help"),
            ):
                completed = subprocess.run(
                    [sys.executable, str(launcher), *arguments],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                self.assertEqual("", completed.stderr)
                self.assertEqual(1, completed.stdout.count("\n"))
                response = json.loads(completed.stdout)
                self.assertEqual("aegis.machine.response", response["schema"])
                self.assertEqual("completed", response["operation_status"])

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
