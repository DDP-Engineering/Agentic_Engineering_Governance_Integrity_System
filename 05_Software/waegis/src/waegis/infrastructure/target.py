#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Inspect target identity/state and generate complete project configuration."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterator
from pathlib import Path

from waegis.domain.plans import PlanError

MAX_TEST_FILES_TO_INSPECT = 32
MAX_TEST_FILE_BYTES_TO_INSPECT = 64 * 1024
BARE_PYTEST_TEST_PATTERN = re.compile(
    rb"^(?:async[ \t]+)?def[ \t]+test_[A-Za-z0-9_]*[ \t]*\(", re.MULTILINE
)


def resolve_target(value: str) -> Path:
    """Resolve one existing target directory without following later inputs."""
    target = Path(value).resolve()
    if not target.is_dir():
        raise PlanError("Target must be an existing directory")
    return target


def git_directory(target: Path) -> Path | None:
    """Resolve a normal Git directory or one standard linked-worktree pointer."""
    marker = target / ".git"
    if marker.is_dir():
        return marker.resolve()
    if not marker.is_file():
        return None
    try:
        text = marker.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    prefix = "gitdir:"
    if len(text.splitlines()) != 1 or not text.lower().startswith(prefix):
        return None
    value = text[len(prefix) :].strip()
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = marker.parent / candidate
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError):
        return None
    if not resolved.is_dir() or not (resolved / "HEAD").is_file():
        return None
    return resolved


def target_fingerprint(target: Path) -> str:
    """Hash target identity and relevant bytes, excluding transient recovery."""
    digest = hashlib.sha256()
    digest.update(os.fsencode(str(target)))
    for path in sorted(target.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(target).as_posix()
        if relative.startswith(".agentic/.runtime/"):
            continue
        if relative.startswith(".git/") and relative != ".git/info/exclude":
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            raise PlanError(f"Cannot inspect target path: {relative}") from exc
        digest.update(b"\0")
    digest.update(b"git=1" if git_directory(target) is not None else b"git=0")
    return f"sha256:{digest.hexdigest()}"


def ensure_output_outside(target: Path, output: str) -> Path:
    """Require the operator-owned plan output to remain outside the target."""
    path = Path(output).resolve()
    if path == target or path.is_relative_to(target):
        raise PlanError("Plan output must be outside the target repository")
    return path


def detected_test_roots(target: Path) -> list[str]:
    """Return confidently recognized conventional test roots."""
    candidates = ("tests", "test")
    return [candidate for candidate in candidates if (target / candidate).is_dir()]


def _matching_test_files(target: Path, roots: list[str]) -> Iterator[Path]:
    """Yield conventional Python test files without following directory links."""
    for root in roots:
        root_path = target / root
        for directory, directories, filenames in os.walk(root_path, followlinks=False):
            directories.sort()
            for filename in sorted(filenames):
                if not (
                    filename.endswith(".py")
                    and (
                        filename.startswith("test_") or filename.endswith("_test.py")
                    )
                ):
                    continue
                path = Path(directory) / filename
                if path.is_file() and not path.is_symlink():
                    yield path


def _detect_test_framework(
    target: Path, roots: list[str], project_text: str
) -> tuple[str, str]:
    """Choose a framework from configuration or a bounded source-text scan."""
    if (target / "pytest.ini").is_file():
        return "pytest", "pytest.ini is present"
    if (target / "conftest.py").is_file():
        return "pytest", "conftest.py is present"
    if "[tool.pytest" in project_text:
        return "pytest", "pyproject.toml contains a [tool.pytest] section"

    unittest_basis: str | None = None
    for index, path in enumerate(_matching_test_files(target, roots)):
        if index >= MAX_TEST_FILES_TO_INSPECT:
            break
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_TEST_FILE_BYTES_TO_INSPECT)
        except OSError:
            continue
        relative = path.relative_to(target).as_posix()
        if b"unittest.TestCase" in content:
            if unittest_basis is None:
                unittest_basis = f"unittest.TestCase usage detected in {relative}"
            continue
        if BARE_PYTEST_TEST_PATTERN.search(content):
            return "pytest", f"bare pytest-style test function detected in {relative}"

    if unittest_basis is not None:
        return "unittest", unittest_basis
    if not roots:
        return "unittest", "no existing test root was detected"
    return (
        "unittest",
        "no pytest configuration or bare pytest-style test function was detected "
        "in the bounded test scan",
    )


def render_config(target: Path) -> tuple[bytes, list[str]]:
    """Generate immediately usable test paths and a shipped command default."""
    roots = detected_test_roots(target)
    warnings: list[str] = []
    pyproject = target / "pyproject.toml"
    try:
        project_text = (
            pyproject.read_text(encoding="utf-8") if pyproject.is_file() else ""
        )
    except (OSError, UnicodeError):
        project_text = ""
        warnings.append("pyproject.toml could not be inspected confidently.")
    test_framework, detection_basis = _detect_test_framework(
        target, roots, project_text
    )
    warnings.append(
        f"Selected {test_framework} test framework: {detection_basis}."
    )
    ruff_detected = (
        (target / "ruff.toml").is_file()
        or (target / ".ruff.toml").is_file()
        or "[tool.ruff" in project_text
    )
    if roots:
        tests = ", ".join(f'"{root}"' for root in roots)
    else:
        roots = [".agentic/tests"]
        tests = '".agentic/tests"'
        warnings.append("No existing test root was detected; using .agentic/tests.")
    validation: list[str] = []
    if test_framework == "pytest":
        validation.extend(
            [
                "[validation.tests.project]",
                'command = ["python", "-m", "pytest"]',
                'working_directory = "."',
                "timeout_seconds = 0",
                "",
            ]
        )
    else:
        for index, root in enumerate(roots, start=1):
            name = "project" if len(roots) == 1 else f"project_{index}"
            validation.extend(
                [
                    f"[validation.tests.{name}]",
                    'command = ["python", "-m", "unittest", '
                    f'"discover", "-s", "{root}"]',
                    'working_directory = "."',
                    "timeout_seconds = 0",
                    "",
                ]
            )
    if ruff_detected:
        validation.extend(
            [
                "[validation.lints.ruff]",
                'command = ["python", "-m", "ruff", "check", "."]',
                'working_directory = "."',
                "timeout_seconds = 0",
                "",
            ]
        )
    text = f"""schema = 1
artifact_type = "project_config"

[paths]
requirements = ".agentic/requirements"
components = ".agentic/components"
tests = [{tests}]
adoptions = ".agentic/adoptions"
runs = ".agentic/runs"

{chr(10).join(validation)}
[policy]
risk_attention_threshold = "medium"
protected_scope_patterns = []
"""
    return text.encode("utf-8"), warnings
