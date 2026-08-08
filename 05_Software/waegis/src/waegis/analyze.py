#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file analyze.py
@brief Deterministic read-only repository proposals with provenance.
@details Uses tracked/untracked repository evidence only. Proposals are never
         applied without answers or interactive confirmation.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import tomllib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .gitops import run_git
from .runner import Runner
from .workflow_toml import LANGUAGE_PRESETS


# CONSTANTS

_INFRASTRUCTURE = frozenset({".agentic", ".claude", ".codex", ".opencode", ".pi", ".qwen"})
_EXTENSIONS = {extension: language for language, preset in LANGUAGE_PRESETS.items() for extension in preset.extensions}
_SOURCE_NAMES = ("src", "app", "lib", "cmd", "pkg", "internal", "Sources")
_TEST_NAMES = ("tests", "test", "spec", "__tests__")


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True, slots=True)
class Proposal:
    """@brief One answer proposal and the evidence that produced it."""

    value: object
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {"value": self.value, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class RepositoryAnalysis:
    """@brief Read-only proposal set for the interview."""

    repository: Path
    inventory_source: str
    file_count: int
    language: Proposal
    source_roots: Proposal
    test_roots: Proposal
    gates: Mapping[str, tuple[Proposal, ...]]

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": str(self.repository),
            "inventory_source": self.inventory_source,
            "file_count": self.file_count,
            "language": self.language.to_dict(),
            "source_roots": self.source_roots.to_dict(),
            "test_roots": self.test_roots.to_dict(),
            "gates": {name: [item.to_dict() for item in values] for name, values in self.gates.items()},
        }


# HELPER FUNCTIONS


def _files(repository: Path, runner: Runner) -> tuple[str, tuple[str, ...]]:
    result = run_git(runner, repository, ("ls-files", "-co", "--exclude-standard", "-z"))
    if result.returncode == 0:
        return "git", tuple(sorted((item.replace("\\", "/") for item in result.stdout.split("\0") if item)))
    paths: list[str] = []
    for directory, names, files in os.walk(repository):
        names[:] = sorted(name for name in names if name not in {".git", ".venv", "node_modules", "__pycache__"})
        root = Path(directory)
        paths.extend((root / name).relative_to(repository).as_posix() for name in sorted(files))
    return "walk", tuple(sorted(paths))


def _gate_proposals(repository: Path) -> dict[str, tuple[Proposal, ...]]:
    found: dict[str, list[Proposal]] = {name: [] for name in ("build", "typecheck", "lint", "test", "security")}
    package = repository / "package.json"
    if package.is_file():
        try:
            scripts = json.loads(package.read_text(encoding="utf-8")).get("scripts", {})
        except (OSError, UnicodeError, json.JSONDecodeError):
            scripts = {}
        if isinstance(scripts, dict):
            for gate in found:
                if isinstance(scripts.get(gate), str):
                    found[gate].append(Proposal(["npm", "run", gate], f"package.json scripts.{gate}"))
    pyproject = repository / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError):
            data = {}
        tool = data.get("tool", {}) if isinstance(data, dict) else {}
        if isinstance(tool, dict):
            if "pytest" in tool:
                found["test"].append(Proposal(["python", "-m", "pytest"], "pyproject.toml [tool.pytest]"))
            if "ruff" in tool:
                found["lint"].append(Proposal(["python", "-m", "ruff", "check", "."], "pyproject.toml [tool.ruff]"))
            if "mypy" in tool:
                found["typecheck"].append(Proposal(["python", "-m", "mypy", "."], "pyproject.toml [tool.mypy]"))
    makefile = repository / "Makefile"
    if makefile.is_file():
        try:
            lines = makefile.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            lines = []
        for gate in found:
            if any(line.startswith(f"{gate}:") for line in lines):
                found[gate].append(Proposal(["make", gate], f"Makefile target {gate}"))
    return {gate: tuple(values) for gate, values in found.items()}


# EXPORTED FUNCTIONS / PUBLIC API


def analyze_repository(repository: Path, runner: Runner) -> RepositoryAnalysis:
    """
    @brief Analyze project evidence without reading WAEGIS-managed infrastructure.
    @param[in] repository Existing repository root.
    @param[in] runner Injectable Git runner.
    @return Provenance-tagged proposals.
    """
    root = repository.resolve(strict=True)
    source, paths = _files(root, runner)
    project_paths = tuple(path for path in paths if path.split("/", 1)[0] not in _INFRASTRUCTURE)
    counts = Counter(_EXTENSIONS.get(Path(path).suffix.casefold()) for path in project_paths)
    counts.pop(None, None)
    language = counts.most_common(1)[0][0] if counts else "python"
    language_reason = f"{counts[language]} matching source files" if counts else "no recognized source extension; safe default"
    source_roots = [name for name in _SOURCE_NAMES if any(path == name or path.startswith(f"{name}/") for path in project_paths)]
    test_roots = [name for name in _TEST_NAMES if any(path == name or path.startswith(f"{name}/") for path in project_paths)]
    if not source_roots:
        source_roots = ["src"]
    if not test_roots:
        test_roots = ["tests"]
    return RepositoryAnalysis(
        root,
        source,
        len(project_paths),
        Proposal(language, language_reason),
        Proposal(source_roots, "conventional roots containing repository files"),
        Proposal(test_roots, "conventional test roots containing repository files"),
        _gate_proposals(root),
    )


# END OF FILE
