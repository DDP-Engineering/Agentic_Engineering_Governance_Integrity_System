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
@brief Deterministic, read-only repo analysis heuristics with ranked,
       provenance-tagged proposals (plan §9, task T5.1).
@details The Wizard E (``waegis adopt``) analysis engine the ``analyze.repo``
         step (T5.2) calls. Everything this module emits is a **proposal with
         provenance** for the operator to confirm field by field — this module
         never decides anything, never executes a candidate command, and never
         writes a file to the target repository (read-only by construction).
@details **T5.2 handoff mapping (plan §7 answer table).** Field names map 1:1
         onto the ``workflow.toml`` answers:

         - ``source_roots`` answer = ``[p.path for p in analysis.source_roots]``
           (each path passes :func:`waegis.repo.workflow_toml.normalize_roots`);
         - ``test_roots`` answer = same extraction;
         - ``language`` answer = ``analysis.language`` — always an exact
           :data:`waegis.repo.workflow_toml.LANGUAGE_PRESETS` key, or
           ``"other"`` when no known code extension was found;
         - ``gate_test_cmds`` / ``gate_lint_cmds`` answers =
           ``[list(c.argv) for c in ... if c.argv is not None]``;
           ``needs_review`` candidates are surfaced to the operator instead of
           auto-converted.
@details **Frozen ``--json`` shape (plan §15 D13 convention).** Field names are
         a public integration contract; changing them is a wizard MAJOR bump:

         ``{"repo": str, "inventory_source": "git"|"walk", "file_count": int,
         "language": str, "languages": [{language, file_count, total_bytes,
         score}], "build_systems": [{name, path, language_hint}],
         "source_roots": [{path, confidence, reason}], "test_roots": [{path,
         confidence, reason}], "colocated_tests": {detected, patterns, note},
         "gate_test_cmds": [{gate, argv, raw, source_file, source_detail,
         needs_review}], "gate_lint_cmds": [same], "risk_flags": [{name,
         status, detail, guidance}]}``

         Risk flags reuse the :class:`waegis.io.reports.ProbeFindingRecord`
         shape. Statuses: ``"warn"`` for heuristic risks and ``"conflict"``
         for the plan §9 guaranteed conflicts (pre-existing ``AGENTS.md`` /
         ``CLAUDE.md``) — a guaranteed conflict is categorically different
         from a heuristic warning, so it gets its own token beside the probe
         layer's ``ok``/``warn``/``fail``.
@details **Deliberate scope limits (documented, not accidental):**

         - The non-git inventory fallback honors only the **top-level**
           ``.gitignore``, with plain ``fnmatchcase`` glob matching against the
           relative path, its basename, and each path segment. Negations
           (``!pattern``) and nested ``.gitignore`` files are ignored. This is
           not full git-ignore semantics and is not meant to be.
         - CI files are **line-scanned, not YAML-parsed** (stdlib has no YAML
           parser): GitHub workflow ``run:`` values and GitLab ``script:`` /
           ``before_script:`` list items. Block scalars (``run: |``) are
           skipped. Extracted lines are classified into test/lint gates by a
           keyword scan; lines matching neither keyword set (installs,
           checkouts, deploys) are dropped — they are not gates.
         - Makefile detection is a line-scan for ``test:``/``lint:`` targets;
           the proposed command is ``make <target>`` (invoking make IS the
           gate) — recipe lines are never parsed.
         - A shell-syntax candidate line that cannot be safely split into an
           argv list (shell metacharacters, ``shlex`` errors) is emitted with
           ``argv=None`` and ``needs_review=True`` ("manual review required")
           instead of a wrong argv split.
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
import re
import shlex
import tomllib
from collections import Counter
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import IO, Any, Sequence

from ..io.reports import ProbeFindingRecord
from ..payload.manifest import MANIFEST_RELATIVE_PATH
from ..probes.runner import CommandRunner
from .gitops import ls_files
from .workflow_toml import LANGUAGE_PRESETS

# CONSTANTS

# @brief Known agent adapter directory names shipped by the template payload
#        (plan §2 grounding list). Sourced from ``05_Software/aegis/template/``;
#        ``tests/test_commands_analyze.py`` asserts this constant still matches
#        the real template directory so drift is caught rather than silently
#        guessed at. Single source of truth — ``commands/analyze.py`` and
#        ``commands/new.py`` re-import it from here.
ADAPTER_DIR_NAMES: tuple[str, ...] = (".claude", ".codex", ".opencode", ".pi", ".qwen")

# @brief Directory whose presence marks a prior/partial AEGIS install.
AGENTIC_DIR_NAME = ".agentic"

# @brief WAEGIS-managed workflow infrastructure that must never influence the
#        host project's language ranking or source-root proposals.
_WORKFLOW_INFRASTRUCTURE_DIRS = frozenset((AGENTIC_DIR_NAME, *ADAPTER_DIR_NAMES))

# @brief Root files that are also shipped by the payload: their pre-existence
#        is a plan §9 GUARANTEED conflict ("never overwrite") — detection-only
#        here; the per-file keep/replace decision belongs to T3.2's copier
#        driven by T5.2.
GUARANTEED_CONFLICT_FILES: tuple[str, ...] = ("AGENTS.md", "CLAUDE.md")

# @brief Inventory size above which the analysis flags itself heuristic-only
#        (plan §9: warn, never refuse to run).
LARGE_REPO_FILE_THRESHOLD = 10_000

# @brief Node package-manager lockfiles (monorepo signal when several coexist;
#        also selects the package manager for package.json gate candidates).
LOCKFILE_NAMES: tuple[str, ...] = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml")

# @brief Extension -> LANGUAGE_PRESETS key map derived from the preset table at
#        import time (first preset wins on a future collision; currently none).
_EXTENSION_LANGUAGE: dict[str, str] = {}
for _key, _preset in LANGUAGE_PRESETS.items():
    for _ext in _preset.source_extensions:
        _EXTENSION_LANGUAGE.setdefault(_ext, _key)

# @brief Root-level build-system marker files: (family name, filename,
#        language hint). The hint boosts that language's ranking score once
#        per family (plan §9: markers contribute to the language ranking).
_ROOT_MARKERS: tuple[tuple[str, str, str | None], ...] = (
    ("pyproject", "pyproject.toml", "python"),
    ("setuptools", "setup.py", "python"),
    ("setuptools", "setup.cfg", "python"),
    ("npm", "package.json", "javascript"),
    ("npm-lock", "package-lock.json", None),
    ("yarn-lock", "yarn.lock", None),
    ("pnpm-lock", "pnpm-lock.yaml", None),
    ("maven", "pom.xml", "java"),
    ("gradle", "build.gradle", "java"),
    ("gradle", "build.gradle.kts", "java"),
    ("cmake", "CMakeLists.txt", "cpp"),
    ("cargo", "Cargo.toml", "rust"),
    ("go", "go.mod", "go"),
    ("make", "Makefile", None),
    ("docker", "Dockerfile", None),
)

# @brief Anywhere-in-tree build-system markers matched against file basenames.
_GLOB_MARKERS: tuple[tuple[str, str, str | None], ...] = (
    ("dotnet", "*.csproj", "csharp"),
    ("dotnet", "*.sln", "csharp"),
)

# @brief Ranking boost one detected marker family adds to its hinted language.
_MARKER_LANGUAGE_BOOST = 0.25

# @brief Maven/Gradle standard layout roots (checked before the generic
#        conventions so `src` is not proposed whole when tests live inside it).
_MAVEN_SOURCE_ROOT = "src/main/java"
_MAVEN_TEST_ROOT = "src/test/java"

# @brief Conventional top-level source/test directory names (plan §9).
_CONVENTIONAL_SOURCE_DIRS: tuple[str, ...] = ("src", "app", "lib")
_GO_SOURCE_DIRS: tuple[str, ...] = ("cmd", "pkg", "internal")
_SWIFT_SOURCE_DIR = "Sources"
_CONVENTIONAL_TEST_DIRS: tuple[str, ...] = ("tests", "test", "spec")
_COLOCATED_TEST_DIR_NAME = "__tests__"

# @brief Fallback source-root coverage target: minimal set of top-level dirs
#        covering at least this share of code files (plan §9).
_COVERAGE_TARGET = 0.90

# @brief Keyword sets classifying an extracted CI/script line into a gate.
#        Lint is checked FIRST: lint invocations routinely name test
#        directories ("ruff check tests/"), while test invocations rarely name
#        lint tools — checking test first would misclassify those.
_LINT_KEYWORDS = frozenset(
    {"lint", "ruff", "flake8", "pylint", "eslint", "golangci-lint", "clang-tidy", "mypy"}
)
_TEST_KEYWORDS = frozenset(
    {"pytest", "test", "tests", "unittest", "tox", "nox", "jest", "vitest", "mocha", "ctest", "rspec"}
)

# @brief Splitter producing lowercase tokens for the keyword classification.
_TOKEN_SPLIT_RE = re.compile(r"[^a-z0-9_-]+")

# @brief Substrings marking a shell-syntax line as unsafe to argv-split:
#        chaining, redirection, substitution, and expansion all change meaning
#        when naively tokenized, so such candidates become "manual review
#        required" instead of a wrong argv (``$`` also covers ``$(``).
_SHELL_UNSAFE_MARKERS: tuple[str, ...] = ("&&", "||", ";", "|", ">", "<", "`", "$", "&", "\n")

# @brief npm's default placeholder test script is not a real gate candidate.
_NPM_PLACEHOLDER_MARKER = "no test specified"

# @brief Matches a Makefile `test:`/`lint:` target line (not a `:=` assignment).
_MAKE_TARGET_RE = re.compile(r"^(test|lint)\s*:(?!=)")

# @brief Matches a GitHub-workflow `run:` line (optionally a `- run:` step).
_RUN_LINE_RE = re.compile(r"^\s*(?:-\s+)?run:\s*(?P<value>.+?)\s*$")

# @brief Matches a GitLab `script:`/`before_script:` key on a stripped line.
_SCRIPT_KEY_RE = re.compile(r"^(?P<key>script|before_script):\s*(?P<value>.*)$")

# @brief YAML block-scalar indicators: a `run:`/`script:` value that is only
#        one of these carries no command text on the line (scope limit).
_BLOCK_SCALAR_MARKERS = frozenset({"|", ">", "|-", ">-", "|+", ">+"})


def _is_workflow_infrastructure(path: str) -> bool:
    """@brief Report whether a relative path belongs to WAEGIS infrastructure."""
    return path.split("/", 1)[0] in _WORKFLOW_INFRASTRUCTURE_DIRS

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class FileRecord:
    """
    @brief One inventoried file: repo-relative forward-slash path plus size.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    path: str
    size: int


@dataclass(frozen=True)
class Inventory:
    """
    @brief The file inventory the heuristics run over.
    @details ``source`` records how it was obtained: ``"git"`` (``git
             ls-files``) or ``"walk"`` (filesystem fallback honoring the
             top-level ``.gitignore``). Injectable into
             :func:`analyze_inventory` so tests can synthesize very large
             inventories without materializing files.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    source: str
    files: tuple[FileRecord, ...]


@dataclass(frozen=True)
class LanguageScore:
    """
    @brief One ranked language guess.
    @details ``language`` is always an exact
             :data:`waegis.repo.workflow_toml.LANGUAGE_PRESETS` key (the T5.2
             handoff guarantee). ``score`` blends file-count share and
             byte share over code files (0.5 each) plus
             :data:`_MARKER_LANGUAGE_BOOST` per detected marker family
             hinting at this language, rounded to 4 decimals.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    language: str
    file_count: int
    total_bytes: int
    score: float

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe mapping.
        @return     Mapping keyed ``language, file_count, total_bytes, score``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return {
            "language": self.language,
            "file_count": self.file_count,
            "total_bytes": self.total_bytes,
            "score": self.score,
        }


@dataclass(frozen=True)
class BuildSystemMarker:
    """
    @brief One detected build-system marker file.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    name: str
    path: str
    language_hint: str | None

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe mapping.
        @return     Mapping keyed ``name, path, language_hint``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return {"name": self.name, "path": self.path, "language_hint": self.language_hint}


@dataclass(frozen=True)
class RootProposal:
    """
    @brief One proposed source/test root, tagged with confidence + provenance.
    @details ``path`` is repo-relative with forward slashes and passes
             :func:`waegis.repo.workflow_toml.normalize_roots` (no glob
             characters, no ``.``/``..`` segments, never absolute).
             ``confidence`` is ``"high"`` (named convention), ``"medium"``
             (structural evidence), or ``"low"`` (coverage fallback).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    path: str
    confidence: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe mapping.
        @return     Mapping keyed ``path, confidence, reason``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return {"path": self.path, "confidence": self.confidence, "reason": self.reason}


@dataclass(frozen=True)
class ColocatedTests:
    """
    @brief The colocated-tests flag (plan §9 / D12).
    @details ``detected`` means test-pattern files sit outside every detected
             test root (e.g. ``*_test.go`` beside sources), so write-zone
             patterns would have to be file-pattern-based rather than
             directory-based. Detection only: acting on it is a T5.2/operator
             decision.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    detected: bool
    patterns: tuple[str, ...]
    note: str

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe mapping.
        @return     Mapping keyed ``detected, patterns, note``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return {"detected": self.detected, "patterns": list(self.patterns), "note": self.note}


@dataclass(frozen=True)
class GateCandidate:
    """
    @brief One gate-command candidate with structured provenance — never
           auto-trusted, never executed by this module.
    @details ``source_file`` (repo-relative provenance file) and
             ``source_detail`` (locator inside it, e.g. ``scripts.test``,
             ``target 'lint'``, ``run: line 12``) tag where the candidate came
             from. ``raw`` is the string exactly as extracted (or the derived
             command text for presence-based candidates such as a pytest
             config section). ``argv`` is the plan §7
             ``gate_test_cmds``/``gate_lint_cmds`` element shape; it is
             ``None`` with ``needs_review=True`` when a safe split was
             impossible (manual review required).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    gate: str
    argv: tuple[str, ...] | None
    raw: str
    source_file: str
    source_detail: str
    needs_review: bool

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen JSON-safe mapping.
        @return     Mapping keyed ``gate, argv, raw, source_file,
                    source_detail, needs_review`` (``argv`` is ``null`` for a
                    manual-review candidate).
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return {
            "gate": self.gate,
            "argv": list(self.argv) if self.argv is not None else None,
            "raw": self.raw,
            "source_file": self.source_file,
            "source_detail": self.source_detail,
            "needs_review": self.needs_review,
        }


@dataclass(frozen=True)
class RepoAnalysis:
    """
    @brief Full plan §9 analysis result: ranked languages, build systems,
           root proposals, colocated-tests flag, gate candidates, risk flags.
    @details Every field is a proposal for the operator; nothing here is ever
             auto-applied. ``source_roots``/``test_roots``/``language``/
             ``gate_test_cmds``/``gate_lint_cmds`` are named after the plan §7
             answers they feed (see module docstring for the extraction
             mapping T5.2 uses).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-14
    @version 0.1.0
    """

    repo: str
    inventory_source: str
    file_count: int
    language: str
    languages: tuple[LanguageScore, ...]
    build_systems: tuple[BuildSystemMarker, ...]
    source_roots: tuple[RootProposal, ...]
    test_roots: tuple[RootProposal, ...]
    colocated_tests: ColocatedTests
    gate_test_cmds: tuple[GateCandidate, ...]
    gate_lint_cmds: tuple[GateCandidate, ...]
    risk_flags: tuple[ProbeFindingRecord, ...]

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the whole analysis to the frozen ``--json``
                    shape (see module docstring for the field-name contract).
        @return     JSON-safe mapping keyed ``repo, inventory_source,
                    file_count, language, languages, build_systems,
                    source_roots, test_roots, colocated_tests, gate_test_cmds,
                    gate_lint_cmds, risk_flags``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return {
            "repo": self.repo,
            "inventory_source": self.inventory_source,
            "file_count": self.file_count,
            "language": self.language,
            "languages": [entry.to_dict() for entry in self.languages],
            "build_systems": [marker.to_dict() for marker in self.build_systems],
            "source_roots": [proposal.to_dict() for proposal in self.source_roots],
            "test_roots": [proposal.to_dict() for proposal in self.test_roots],
            "colocated_tests": self.colocated_tests.to_dict(),
            "gate_test_cmds": [candidate.to_dict() for candidate in self.gate_test_cmds],
            "gate_lint_cmds": [candidate.to_dict() for candidate in self.gate_lint_cmds],
            "risk_flags": [_flag_to_dict(flag) for flag in self.risk_flags],
        }


# LOCAL HELPERS


def _flag_to_dict(flag: ProbeFindingRecord) -> dict[str, Any]:
    """
    @brief      Serialize one risk flag to the probe-finding JSON shape.
    @param[in]  flag The :class:`ProbeFindingRecord` to serialize.
    @return     Mapping keyed ``name, status, detail, guidance`` (the same
                field names ``io/reports.py`` uses for probe findings).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return {"name": flag.name, "status": flag.status, "detail": flag.detail, "guidance": flag.guidance}


def _read_text(path: Path) -> str | None:
    """
    @brief      Read a marker file's text, tolerating absence and bad bytes.
    @param[in]  path File to read.
    @return     The decoded text (undecodable bytes replaced), or ``None``
                when the file does not exist or cannot be read — analysis
                heuristics always degrade gracefully instead of raising.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _gitignore_patterns(repo: Path) -> list[str]:
    """
    @brief      Load the top-level ``.gitignore`` patterns for the walk
                fallback (deliberately simplified — see module docstring).
    @param[in]  repo Repository root.
    @return     Cleaned pattern list: blank lines, comments, and negations
                (``!pattern``, unsupported by design) removed; leading and
                trailing slashes stripped.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    text = _read_text(repo / ".gitignore")
    if text is None:
        return []
    patterns: list[str] = []
    for line in text.splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#") or entry.startswith("!"):
            continue
        entry = entry.strip("/")
        if entry:
            patterns.append(entry)
    return patterns


def _is_ignored(rel_path: str, patterns: Sequence[str]) -> bool:
    """
    @brief      Report whether a relative path matches a ``.gitignore``
                pattern under the simplified fallback semantics.
    @details    A pattern matches when it glob-matches the whole relative
                path, the path's basename, any single path segment, or a
                leading directory portion (``pattern/*``). Case-sensitive
                (``fnmatchcase``) so results are identical on every host OS.
    @param[in]  rel_path Repo-relative forward-slash path.
    @param[in]  patterns Cleaned patterns from :func:`_gitignore_patterns`.
    @return     ``True`` when any pattern matches.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    segments = rel_path.split("/")
    for pattern in patterns:
        if fnmatchcase(rel_path, pattern) or fnmatchcase(rel_path, pattern + "/*"):
            return True
        if any(fnmatchcase(segment, pattern) for segment in segments):
            return True
    return False


def _walk_paths(repo: Path) -> list[str]:
    """
    @brief      Filesystem-walk inventory fallback for a non-git target.
    @details    Always excludes ``.git/``; honors the top-level ``.gitignore``
                via :func:`_is_ignored` (simplified semantics, module
                docstring). Directories and files are visited in sorted order
                so the inventory is deterministic.
    @param[in]  repo Repository root.
    @return     Sorted repo-relative forward-slash file paths.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    patterns = _gitignore_patterns(repo)
    collected: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        rel_dir = Path(dirpath).relative_to(repo).as_posix()
        prefix = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = sorted(
            name for name in dirnames if name != ".git" and not _is_ignored(prefix + name, patterns)
        )
        for name in sorted(filenames):
            rel_path = prefix + name
            if not _is_ignored(rel_path, patterns):
                collected.append(rel_path)
    return collected


def _stat_size(repo: Path, rel_path: str) -> int:
    """
    @brief      Read one inventoried file's size in bytes.
    @param[in]  repo Repository root.
    @param[in]  rel_path Repo-relative forward-slash path.
    @return     ``st_size``, or ``0`` when the file cannot be stat'ed (e.g. a
                tracked-but-deleted file in a dirty work tree).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    try:
        return (repo / rel_path).stat().st_size
    except OSError:
        return 0


def _detect_build_systems(inventory: Inventory) -> tuple[BuildSystemMarker, ...]:
    """
    @brief      Detect build-system marker files from the inventory (plan §9).
    @details    Root markers match exact top-level filenames; ``*.csproj`` /
                ``*.sln`` match basenames anywhere in the tree. Inventory-based
                (not disk-based) so injected inventories are honored.
    @param[in]  inventory The file inventory.
    @return     Detected markers in stable spec-then-path order.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    paths = {record.path for record in inventory.files}
    markers: list[BuildSystemMarker] = []
    for name, filename, hint in _ROOT_MARKERS:
        if filename in paths:
            markers.append(BuildSystemMarker(name=name, path=filename, language_hint=hint))
    for name, pattern, hint in _GLOB_MARKERS:
        for path in sorted(p for p in paths if fnmatchcase(p.rsplit("/", 1)[-1], pattern)):
            markers.append(BuildSystemMarker(name=name, path=path, language_hint=hint))
    return tuple(markers)


def _rank_languages(
    inventory: Inventory, markers: Sequence[BuildSystemMarker]
) -> tuple[LanguageScore, ...]:
    """
    @brief      Rank languages from the extension histogram weighted by both
                file count and total bytes, plus build-marker boosts (plan §9).
    @details    Score = 0.5 * count-share + 0.5 * byte-share over code files
                (files whose lowercased extension maps to a preset), plus
                :data:`_MARKER_LANGUAGE_BOOST` once per detected marker
                *family* hinting at the language (so fifty ``.csproj`` files
                boost csharp once, not fifty times). Ties break on the
                language name so the ranking is deterministic.
    @param[in]  inventory The file inventory.
    @param[in]  markers Detected build-system markers.
    @return     Ranked :class:`LanguageScore` tuple (descending score); empty
                when no code extension and no hinting marker was found.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    counts: Counter[str] = Counter()
    sizes: Counter[str] = Counter()
    for record in inventory.files:
        if _is_workflow_infrastructure(record.path):
            continue
        language = _EXTENSION_LANGUAGE.get(PurePosixPath(record.path).suffix.lower())
        if language is not None:
            counts[language] += 1
            sizes[language] += record.size
    total_count = sum(counts.values())
    total_bytes = sum(sizes.values())

    boosts: dict[str, float] = {}
    seen_families: set[str] = set()
    for marker in markers:
        if marker.language_hint is not None and marker.name not in seen_families:
            seen_families.add(marker.name)
            boosts[marker.language_hint] = boosts.get(marker.language_hint, 0.0) + _MARKER_LANGUAGE_BOOST

    scores: dict[str, float] = {}
    for language in set(counts) | set(boosts):
        count_share = counts[language] / total_count if total_count else 0.0
        byte_share = sizes[language] / total_bytes if total_bytes else 0.0
        scores[language] = 0.5 * count_share + 0.5 * byte_share + boosts.get(language, 0.0)

    ranked = sorted(scores, key=lambda language: (-scores[language], language))
    return tuple(
        LanguageScore(
            language=language,
            file_count=counts[language],
            total_bytes=sizes[language],
            score=round(scores[language], 4),
        )
        for language in ranked
    )


def _propose_test_roots(inventory: Inventory) -> tuple[RootProposal, ...]:
    """
    @brief      Propose test roots from conventional names (plan §9).
    @details    ``src/test/java`` (Maven/Gradle) is checked before the generic
                top-level names; every directory named ``__tests__`` at any
                depth is proposed individually (path-sorted).
    @param[in]  inventory The file inventory.
    @return     Test-root proposals, each tagged with confidence + reason.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    paths = [record.path for record in inventory.files]
    proposals: list[RootProposal] = []
    seen: set[str] = set()

    def _add(path: str, confidence: str, reason: str) -> None:
        """
        @brief      Append one deduplicated proposal.
        @param[in]  path Repo-relative directory.
        @param[in]  confidence Confidence tag.
        @param[in]  reason Provenance note.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        if path not in seen:
            seen.add(path)
            proposals.append(RootProposal(path=path, confidence=confidence, reason=reason))

    if any(path.startswith(_MAVEN_TEST_ROOT + "/") for path in paths):
        _add(_MAVEN_TEST_ROOT, "high", "Maven/Gradle standard test layout (src/test/java)")
    for name in _CONVENTIONAL_TEST_DIRS:
        if any(path.startswith(name + "/") for path in paths):
            _add(name, "high", f"conventional top-level '{name}' directory")
    colocated_dirs: set[str] = set()
    for path in paths:
        parts = path.split("/")[:-1]
        for index, segment in enumerate(parts):
            if segment == _COLOCATED_TEST_DIR_NAME:
                colocated_dirs.add("/".join(parts[: index + 1]))
    for directory in sorted(colocated_dirs):
        _add(directory, "medium", "'__tests__' directory convention")
    return tuple(proposals)


def _propose_source_roots(
    inventory: Inventory,
    language: str,
    markers: Sequence[BuildSystemMarker],
    test_root_paths: set[str],
) -> tuple[RootProposal, ...]:
    """
    @brief      Propose source roots: named conventions first, coverage
                fallback second (plan §9).
    @details    Convention order: ``src/main/java`` (suppresses the generic
                ``src``, which would engulf ``src/test/java``), top-level
                ``src``/``app``/``lib`` with code files, Go ``cmd``/``pkg``/
                ``internal`` (when ``go.mod`` is present or the ranked language
                is go), Swift ``Sources`` (any files — ``.swift`` has no
                preset), and top-level Python packages (a direct
                ``__init__.py``). When nothing matches, falls back to the
                minimal set of top-level directories covering >=
                :data:`_COVERAGE_TARGET` of code files by count (largest
                first). Detected test roots are never proposed as source
                roots; root-level loose code files are never proposed as
                ``"."`` (``normalize_roots`` rejects it).
    @param[in]  inventory The file inventory.
    @param[in]  language Top-ranked language key (or ``"other"``).
    @param[in]  markers Detected build-system markers.
    @param[in]  test_root_paths Paths already proposed as test roots.
    @return     Source-root proposals, each tagged with confidence + reason.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    all_paths = [
        record.path
        for record in inventory.files
        if not _is_workflow_infrastructure(record.path)
    ]
    path_set = set(all_paths)
    code_files = [
        path for path in all_paths if PurePosixPath(path).suffix.lower() in _EXTENSION_LANGUAGE
    ]
    proposals: list[RootProposal] = []
    seen: set[str] = set()

    def _add(path: str, confidence: str, reason: str) -> None:
        """
        @brief      Append one proposal unless duplicated or a test root.
        @param[in]  path Repo-relative directory.
        @param[in]  confidence Confidence tag.
        @param[in]  reason Provenance note.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        if path not in seen and path not in test_root_paths:
            seen.add(path)
            proposals.append(RootProposal(path=path, confidence=confidence, reason=reason))

    maven_layout = any(path.startswith(_MAVEN_SOURCE_ROOT + "/") for path in code_files)
    if maven_layout:
        _add(_MAVEN_SOURCE_ROOT, "high", "Maven/Gradle standard layout (src/main/java)")
    for name in _CONVENTIONAL_SOURCE_DIRS:
        if name == "src" and maven_layout:
            continue
        if any(path.startswith(name + "/") for path in code_files):
            _add(name, "high", f"conventional top-level '{name}' directory with code files")
    if language == "go" or any(marker.name == "go" for marker in markers):
        for name in _GO_SOURCE_DIRS:
            if any(path.startswith(name + "/") and path.endswith(".go") for path in code_files):
                _add(name, "high", f"Go convention: top-level '{name}' directory with .go files")
    if any(path.startswith(_SWIFT_SOURCE_DIR + "/") for path in all_paths):
        _add(_SWIFT_SOURCE_DIR, "high", "Swift convention: top-level 'Sources' directory")
    for directory in sorted({path.split("/", 1)[0] for path in all_paths if "/" in path}):
        if f"{directory}/__init__.py" in path_set:
            _add(directory, "medium", f"top-level Python package ('{directory}/__init__.py' present)")

    if not proposals and code_files:
        dir_counts: Counter[str] = Counter(
            path.split("/", 1)[0] for path in code_files if "/" in path
        )
        total_in_dirs = sum(dir_counts.values())
        covered = 0
        for directory, count in sorted(dir_counts.items(), key=lambda item: (-item[1], item[0])):
            if directory in test_root_paths:
                continue
            covered += count
            _add(
                directory,
                "low",
                f"fallback: top-level directory holding {count} of {total_in_dirs} "
                "code files (no conventional layout found)",
            )
            if covered / total_in_dirs >= _COVERAGE_TARGET:
                break
    return tuple(proposals)


def _detect_colocated_tests(
    inventory: Inventory, language: str, test_root_paths: Sequence[str]
) -> ColocatedTests:
    """
    @brief      Detect test-pattern files living outside every detected test
                root (plan §9 / D12) for the top-ranked language.
    @param[in]  inventory The file inventory.
    @param[in]  language Top-ranked language key; ``"other"`` (no preset, no
                patterns) never detects.
    @param[in]  test_root_paths Detected test-root paths.
    @return     The :class:`ColocatedTests` flag; ``note`` explains the
                write-zone implication when detected, empty otherwise.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    preset = LANGUAGE_PRESETS.get(language)
    if preset is None:
        return ColocatedTests(detected=False, patterns=(), note="")
    matched: set[str] = set()
    for record in inventory.files:
        if _is_workflow_infrastructure(record.path):
            continue
        if any(record.path.startswith(root + "/") for root in test_root_paths):
            continue
        basename = record.path.rsplit("/", 1)[-1]
        for pattern in preset.test_file_patterns:
            if fnmatchcase(basename, pattern):
                matched.add(pattern)
    if not matched:
        return ColocatedTests(detected=False, patterns=(), note="")
    patterns = tuple(sorted(matched))
    note = (
        "test files matching " + ", ".join(patterns) + " sit beside sources outside any "
        "detected test root; write-zone patterns must become file-pattern-based rather "
        "than directory-based (plan D12) — operator/T5.2 decision required, nothing is "
        "decided here"
    )
    return ColocatedTests(detected=True, patterns=patterns, note=note)


def _strip_quotes(text: str) -> str:
    """
    @brief      Strip one pair of matching surrounding quotes from a scanned
                YAML value.
    @param[in]  text The raw value text.
    @return     The unquoted text when it was wrapped in matching single or
                double quotes, otherwise the input unchanged.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _classify_gate(text: str) -> str | None:
    """
    @brief      Classify an extracted CI/script line into a gate by keywords.
    @details    Lint keywords are checked before test keywords (see the
                constant's rationale). Tokens are lowercase alphanumeric runs
                (plus ``_``/``-``), so ``go test ./...`` and ``npm run lint``
                both classify by whole words, not substrings.
    @param[in]  text The extracted command string.
    @return     ``"lint"``, ``"test"``, or ``None`` when the line names
                neither (installs/checkouts/deploys are not gates — dropped
                by design, module docstring).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    tokens = set(_TOKEN_SPLIT_RE.split(text.lower()))
    if tokens & _LINT_KEYWORDS:
        return "lint"
    if tokens & _TEST_KEYWORDS:
        return "test"
    return None


def _string_candidate(gate: str, text: str, source_file: str, source_detail: str) -> GateCandidate | None:
    """
    @brief      Build a gate candidate from a shell-syntax string, argv-split
                only when the split is safe.
    @details    A string containing any :data:`_SHELL_UNSAFE_MARKERS`
                substring (chaining, redirection, substitution, expansion), or
                one ``shlex.split`` rejects, becomes a manual-review candidate
                (``argv=None``, ``needs_review=True``) — never a wrong argv
                like ``["pytest", "-q", "&&", "ruff"]``.
    @param[in]  gate ``"test"`` or ``"lint"``.
    @param[in]  text The extracted command string (kept verbatim in ``raw``).
    @param[in]  source_file Repo-relative provenance file.
    @param[in]  source_detail Locator inside the provenance file.
    @return     The candidate, or ``None`` for an empty/whitespace string.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    if not text.strip():
        return None
    if any(marker in text for marker in _SHELL_UNSAFE_MARKERS):
        return GateCandidate(
            gate=gate, argv=None, raw=text, source_file=source_file,
            source_detail=source_detail, needs_review=True,
        )
    try:
        parts = shlex.split(text)
    except ValueError:
        return GateCandidate(
            gate=gate, argv=None, raw=text, source_file=source_file,
            source_detail=source_detail, needs_review=True,
        )
    if not parts:
        return None
    return GateCandidate(
        gate=gate, argv=tuple(parts), raw=text, source_file=source_file,
        source_detail=source_detail, needs_review=False,
    )


def _package_json_candidates(repo: Path) -> list[GateCandidate]:
    """
    @brief      Extract gate candidates from the root ``package.json``
                ``scripts.test``/``scripts.lint``.
    @details    The proposed argv is the package-manager invocation
                (``npm test`` / ``npm run lint``; ``npm`` becomes ``pnpm`` or
                ``yarn`` when the matching lockfile is present) — running the
                script through its package manager preserves pre/post scripts
                and ``node_modules/.bin`` resolution. The raw script string is
                kept verbatim in ``raw``. npm's default "no test specified"
                placeholder is skipped. Root ``package.json`` only (workspace
                packages are a monorepo risk flag, not a gate source).
    @param[in]  repo Repository root.
    @return     Zero, one, or two candidates.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    text = _read_text(repo / "package.json")
    if text is None:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return []
    manager = "npm"
    if (repo / "pnpm-lock.yaml").is_file():
        manager = "pnpm"
    elif (repo / "yarn.lock").is_file():
        manager = "yarn"
    candidates: list[GateCandidate] = []
    test_script = scripts.get("test")
    if isinstance(test_script, str) and test_script.strip() and _NPM_PLACEHOLDER_MARKER not in test_script:
        candidates.append(
            GateCandidate(
                gate="test", argv=(manager, "test"), raw=test_script,
                source_file="package.json", source_detail="scripts.test", needs_review=False,
            )
        )
    lint_script = scripts.get("lint")
    if isinstance(lint_script, str) and lint_script.strip():
        candidates.append(
            GateCandidate(
                gate="lint", argv=(manager, "run", "lint"), raw=lint_script,
                source_file="package.json", source_detail="scripts.lint", needs_review=False,
            )
        )
    return candidates


def _pyproject_candidates(repo: Path) -> list[GateCandidate]:
    """
    @brief      Extract gate candidates from ``pyproject.toml`` tool sections.
    @details    Presence-based: a ``[tool.pytest]``/``[tool.pytest.ini_options]``
                table proposes ``pytest -q``; a ``[tool.ruff]`` table proposes
                ``ruff check .``. These are derived commands (nothing literal
                to extract), so ``raw`` carries the derived command text and
                ``source_detail`` names the config section that justified it.
    @param[in]  repo Repository root.
    @return     Zero, one, or two candidates.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    text = _read_text(repo / "pyproject.toml")
    if text is None:
        return []
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return []
    tool = data.get("tool")
    if not isinstance(tool, dict):
        return []
    candidates: list[GateCandidate] = []
    pytest_table = tool.get("pytest")
    if isinstance(pytest_table, dict):
        section = "[tool.pytest.ini_options]" if "ini_options" in pytest_table else "[tool.pytest]"
        candidates.append(
            GateCandidate(
                gate="test", argv=("pytest", "-q"), raw="pytest -q",
                source_file="pyproject.toml", source_detail=section, needs_review=False,
            )
        )
    if isinstance(tool.get("ruff"), dict):
        candidates.append(
            GateCandidate(
                gate="lint", argv=("ruff", "check", "."), raw="ruff check .",
                source_file="pyproject.toml", source_detail="[tool.ruff]", needs_review=False,
            )
        )
    return candidates


def _makefile_candidates(repo: Path) -> list[GateCandidate]:
    """
    @brief      Extract gate candidates from ``Makefile`` ``test:``/``lint:``
                targets (simple line-scan, plan §9 — no Makefile parser).
    @details    The proposed command is ``make <target>`` — invoking make IS
                the gate; recipe lines are never parsed. ``:=`` assignments do
                not match. First occurrence of each target wins.
    @param[in]  repo Repository root.
    @return     Zero, one, or two candidates.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    text = _read_text(repo / "Makefile")
    if text is None:
        return []
    candidates: list[GateCandidate] = []
    seen: set[str] = set()
    for line in text.splitlines():
        match = _MAKE_TARGET_RE.match(line)
        if match is None:
            continue
        target = match.group(1)
        if target in seen:
            continue
        seen.add(target)
        candidates.append(
            GateCandidate(
                gate=target, argv=("make", target), raw=line.strip(),
                source_file="Makefile", source_detail=f"target '{target}'", needs_review=False,
            )
        )
    return candidates


def _github_workflow_candidates(repo: Path) -> list[GateCandidate]:
    """
    @brief      Extract gate candidates from ``.github/workflows/*.yml|yaml``
                ``run:`` lines (line-scan, no YAML parser — module docstring).
    @details    Each ``run:`` value is keyword-classified
                (:func:`_classify_gate`; unmatched lines dropped) and
                argv-split via :func:`_string_candidate` (manual-review
                fallback for shell syntax). Block scalars (``run: |``) are
                skipped. Files are visited name-sorted for determinism.
    @param[in]  repo Repository root.
    @return     Extracted candidates with per-line provenance.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    workflows_dir = repo / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []
    candidates: list[GateCandidate] = []
    workflow_files = sorted(
        (entry for entry in workflows_dir.iterdir() if entry.is_file() and entry.suffix in (".yml", ".yaml")),
        key=lambda entry: entry.name,
    )
    for workflow in workflow_files:
        text = _read_text(workflow)
        if text is None:
            continue
        source_file = f".github/workflows/{workflow.name}"
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = _RUN_LINE_RE.match(line)
            if match is None:
                continue
            value = _strip_quotes(match.group("value"))
            if value in _BLOCK_SCALAR_MARKERS:
                continue
            gate = _classify_gate(value)
            if gate is None:
                continue
            candidate = _string_candidate(gate, value, source_file, f"run: line {lineno}")
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _gitlab_ci_candidates(repo: Path) -> list[GateCandidate]:
    """
    @brief      Extract gate candidates from ``.gitlab-ci.yml`` ``script:`` /
                ``before_script:`` list items (indent-tracking line-scan, no
                YAML parser — module docstring).
    @details    Handles both the inline form (``script: pytest -q``) and the
                list form (``- pytest -q`` items indented deeper than the
                key). Items are keyword-classified (unmatched lines dropped)
                and argv-split with the manual-review fallback.
    @param[in]  repo Repository root.
    @return     Extracted candidates with per-line provenance.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    text = _read_text(repo / ".gitlab-ci.yml")
    if text is None:
        return []
    candidates: list[GateCandidate] = []
    in_script = False
    script_indent = 0
    script_key = ""

    def _append(value: str, lineno: int) -> None:
        """
        @brief      Classify and append one extracted script item.
        @param[in]  value The extracted command string.
        @param[in]  lineno 1-based line number for provenance.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        gate = _classify_gate(value)
        if gate is None:
            return
        candidate = _string_candidate(gate, value, ".gitlab-ci.yml", f"{script_key}: line {lineno}")
        if candidate is not None:
            candidates.append(candidate)

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        key_match = _SCRIPT_KEY_RE.match(stripped)
        if key_match is not None:
            script_key = key_match.group("key")
            inline_value = _strip_quotes(key_match.group("value").strip())
            if inline_value and inline_value not in _BLOCK_SCALAR_MARKERS:
                _append(inline_value, lineno)
                in_script = False
            else:
                in_script = True
                script_indent = indent
            continue
        if in_script:
            if indent > script_indent and stripped.startswith("- "):
                _append(_strip_quotes(stripped[2:].strip()), lineno)
            elif indent <= script_indent:
                in_script = False
    return candidates


def _extract_gate_candidates(repo: Path) -> tuple[tuple[GateCandidate, ...], tuple[GateCandidate, ...]]:
    """
    @brief      Gather gate candidates from every supported source, in a
                stable order, deduplicated.
    @details    Order: package.json, pyproject.toml, Makefile, GitHub
                workflows (name-sorted), .gitlab-ci.yml. Duplicates of the
                same ``(gate, raw, source_file)`` (e.g. a matrix job repeating
                one command) keep only their first occurrence — distinct
                source files always stay distinct provenance.
    @param[in]  repo Repository root.
    @return     ``(test candidates, lint candidates)`` tuples.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    collected: list[GateCandidate] = []
    collected.extend(_package_json_candidates(repo))
    collected.extend(_pyproject_candidates(repo))
    collected.extend(_makefile_candidates(repo))
    collected.extend(_github_workflow_candidates(repo))
    collected.extend(_gitlab_ci_candidates(repo))

    deduped: list[GateCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in collected:
        key = (candidate.gate, candidate.raw, candidate.source_file)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    tests = tuple(candidate for candidate in deduped if candidate.gate == "test")
    lints = tuple(candidate for candidate in deduped if candidate.gate == "lint")
    return tests, lints


def _collect_risk_flags(repo: Path, inventory: Inventory) -> tuple[ProbeFindingRecord, ...]:
    """
    @brief      Collect the plan §9 adoption risk flags.
    @details    Stable order: submodules, LFS, monorepo, large repo,
                prior install, guaranteed conflicts (one flag per conflicting
                file). Directory/file presence is checked on disk (an empty
                ``.agentic/`` holds no inventoried files); the large-repo
                check uses the inventory so injected inventories are honored.
                Detection only — nothing is resolved or decided here.
    @param[in]  repo Repository root.
    @param[in]  inventory The file inventory.
    @return     Raised flags as :class:`ProbeFindingRecord` tuples (possibly
                empty). Statuses: ``"warn"``, or ``"conflict"`` for the
                guaranteed conflicts.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    flags: list[ProbeFindingRecord] = []

    if (repo / ".gitmodules").is_file():
        flags.append(
            ProbeFindingRecord(
                name="risk.submodules",
                status="warn",
                detail=".gitmodules present: the repository uses git submodules",
                guidance="submodule contents are not analyzed; adoption covers only the top-level repository",
            )
        )

    gitattributes = _read_text(repo / ".gitattributes")
    if gitattributes is not None and "filter=lfs" in gitattributes:
        flags.append(
            ProbeFindingRecord(
                name="risk.lfs",
                status="warn",
                detail=".gitattributes contains filter=lfs: the repository uses Git LFS",
                guidance="LFS-tracked content may be represented by pointer files; size-based heuristics can be misleading",
            )
        )

    lockfiles_present = [name for name in LOCKFILE_NAMES if (repo / name).is_file()]
    packages_dir = repo / "packages"
    workspace_package_count = 0
    if packages_dir.is_dir():
        try:
            workspace_package_count = sum(
                1 for entry in packages_dir.iterdir() if entry.is_dir() and (entry / "package.json").is_file()
            )
        except OSError:
            workspace_package_count = 0
    monorepo_signals: list[str] = []
    if len(lockfiles_present) >= 2:
        monorepo_signals.append("multiple lockfiles: " + ", ".join(lockfiles_present))
    if workspace_package_count >= 2:
        monorepo_signals.append(f"packages/ holds {workspace_package_count} package.json packages")
    if monorepo_signals:
        flags.append(
            ProbeFindingRecord(
                name="risk.monorepo",
                status="warn",
                detail="monorepo signals detected: " + "; ".join(monorepo_signals),
                guidance="a monorepo may need per-package roots and gates; review every proposal carefully",
            )
        )

    if len(inventory.files) > LARGE_REPO_FILE_THRESHOLD:
        flags.append(
            ProbeFindingRecord(
                name="risk.large-repo",
                status="warn",
                detail=(
                    f"inventory holds {len(inventory.files)} files "
                    f"(> {LARGE_REPO_FILE_THRESHOLD}): this analysis is heuristic-only at this size"
                ),
                guidance="treat every proposal as approximate; expect manual adjustment",
            )
        )

    agentic_present = (repo / AGENTIC_DIR_NAME).is_dir()
    adapters_present = [name for name in ADAPTER_DIR_NAMES if (repo / name).is_dir()]
    if agentic_present or adapters_present:
        present_dirs = ([AGENTIC_DIR_NAME] if agentic_present else []) + adapters_present
        manifest_note = ""
        if agentic_present:
            has_manifest = (repo / MANIFEST_RELATIVE_PATH).is_file()
            manifest_note = " (with install manifest)" if has_manifest else " (without install manifest)"
        flags.append(
            ProbeFindingRecord(
                name="risk.prior-install",
                status="warn",
                detail="prior/partial install directories present: " + ", ".join(present_dirs) + manifest_note,
                guidance=(
                    "conflict preview only, nothing is resolved here; the adoption wizard's "
                    "prior-install step routes this (waegis analyze --repo reports manifest/drift detail)"
                ),
            )
        )

    for filename in GUARANTEED_CONFLICT_FILES:
        if (repo / filename).is_file():
            flags.append(
                ProbeFindingRecord(
                    name="risk.guaranteed-conflict",
                    status="conflict",
                    detail=f"{filename} already exists at the target root and is also shipped by the payload",
                    guidance=(
                        "guaranteed conflict (plan section 9): never overwritten; the adoption copy "
                        "will require a per-file keep/replace decision with a merge hint"
                    ),
                )
            )

    return tuple(flags)


# PUBLIC API


def collect_inventory(repo: str | os.PathLike[str], *, runner: CommandRunner) -> Inventory:
    """
    @brief      Build the file inventory for ``repo`` (plan §9).
    @details    Primary path: ``git ls-files`` via
                :func:`waegis.repo.gitops.ls_files`. When that returns
                ``None`` (git missing, not a work tree), falls back to the
                filesystem walk honoring the top-level ``.gitignore``
                (simplified semantics — module docstring). File sizes come
                from ``stat`` (0 when unreadable, e.g. tracked-but-deleted).
    @param[in]  repo Repository root directory.
    @param[in]  runner Injectable :class:`CommandRunner` for the git path.
    @return     The :class:`Inventory` with ``source`` recording which path
                produced it (``"git"`` or ``"walk"``).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    repo_path = Path(repo)
    tracked = ls_files(runner, repo_path)
    if tracked is not None:
        source = "git"
        paths = tracked
    else:
        source = "walk"
        paths = _walk_paths(repo_path)
    files = tuple(FileRecord(path=path, size=_stat_size(repo_path, path)) for path in paths)
    return Inventory(source=source, files=files)


def analyze_inventory(repo: str | os.PathLike[str], inventory: Inventory) -> RepoAnalysis:
    """
    @brief      Run every plan §9 heuristic over an already-collected
                inventory and assemble the :class:`RepoAnalysis`.
    @details    The injectable seam for very-large-repo tests (synthesize an
                :class:`Inventory` without materializing files). Path-based
                heuristics (languages, build systems, roots, colocated tests)
                use only the inventory; content-based extraction (gate
                candidates, risk-flag file checks) reads marker files from
                disk and degrades gracefully when they are absent. Read-only:
                nothing in the target repository is created or modified, and
                no candidate command is ever executed.
    @param[in]  repo Repository root directory (for content reads and the
                report's ``repo`` field).
    @param[in]  inventory The file inventory to analyze.
    @return     The assembled :class:`RepoAnalysis` — proposals only, nothing
                auto-applied.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    repo_path = Path(repo)
    markers = _detect_build_systems(inventory)
    languages = _rank_languages(inventory, markers)
    language = languages[0].language if languages else "other"
    test_roots = _propose_test_roots(inventory)
    test_root_paths = {proposal.path for proposal in test_roots}
    source_roots = _propose_source_roots(inventory, language, markers, test_root_paths)
    colocated = _detect_colocated_tests(inventory, language, sorted(test_root_paths))
    gate_test_cmds, gate_lint_cmds = _extract_gate_candidates(repo_path)
    risk_flags = _collect_risk_flags(repo_path, inventory)
    return RepoAnalysis(
        repo=str(repo_path),
        inventory_source=inventory.source,
        file_count=len(inventory.files),
        language=language,
        languages=languages,
        build_systems=markers,
        source_roots=source_roots,
        test_roots=test_roots,
        colocated_tests=colocated,
        gate_test_cmds=gate_test_cmds,
        gate_lint_cmds=gate_lint_cmds,
        risk_flags=risk_flags,
    )


def analyze_repo(repo: str | os.PathLike[str], *, runner: CommandRunner) -> RepoAnalysis:
    """
    @brief      Full plan §9 analysis entry point: collect the inventory,
                then run every heuristic.
    @param[in]  repo Repository root directory.
    @param[in]  runner Injectable :class:`CommandRunner` for the git
                inventory path.
    @return     The assembled :class:`RepoAnalysis`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    return analyze_inventory(repo, collect_inventory(repo, runner=runner))


def render_repo_analysis(analysis: RepoAnalysis, stream: IO[str]) -> None:
    """
    @brief      Render the human-readable analysis summary (plain-ASCII-safe,
                mirroring ``io/console.py``'s encoding convention).
    @details    Every section states its proposals with confidence and
                provenance; the closing line restates the module's contract:
                proposals only, nothing applied without operator confirmation.
    @param[in]  analysis The analysis to render.
    @param[in]  stream Output stream (real console or injected buffer for
                tests).
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    stream.write(f"WAEGIS repo analysis - {analysis.repo}\n")
    stream.write("\n")
    stream.write(f"Inventory: {analysis.file_count} file(s), source: {analysis.inventory_source}\n")
    stream.write("\n")

    stream.write("Languages (ranked):\n")
    if analysis.languages:
        for rank, entry in enumerate(analysis.languages, start=1):
            stream.write(
                f"  {rank}. {entry.language}: {entry.file_count} file(s), "
                f"{entry.total_bytes} byte(s), score {entry.score:.4f}\n"
            )
    else:
        stream.write("  no known code extensions found\n")
    stream.write(f"  proposed language: {analysis.language}\n")
    stream.write("\n")

    stream.write("Build systems:\n")
    if analysis.build_systems:
        for marker in analysis.build_systems:
            hint = f" (language hint: {marker.language_hint})" if marker.language_hint else ""
            stream.write(f"  {marker.name}: {marker.path}{hint}\n")
    else:
        stream.write("  none detected\n")
    stream.write("\n")

    stream.write("Proposed source roots:\n")
    if analysis.source_roots:
        for proposal in analysis.source_roots:
            stream.write(f"  {proposal.path} [{proposal.confidence}] - {proposal.reason}\n")
    else:
        stream.write("  none proposed (operator input required)\n")
    stream.write("\n")

    stream.write("Proposed test roots:\n")
    if analysis.test_roots:
        for proposal in analysis.test_roots:
            stream.write(f"  {proposal.path} [{proposal.confidence}] - {proposal.reason}\n")
    else:
        stream.write("  none proposed (operator input required)\n")
    stream.write("\n")

    stream.write("Colocated tests:\n")
    if analysis.colocated_tests.detected:
        stream.write(f"  detected (patterns: {', '.join(analysis.colocated_tests.patterns)})\n")
        stream.write(f"  note: {analysis.colocated_tests.note}\n")
    else:
        stream.write("  none detected\n")
    stream.write("\n")

    for label, candidates in (("test", analysis.gate_test_cmds), ("lint", analysis.gate_lint_cmds)):
        stream.write(f"Gate command candidates ({label}):\n")
        if candidates:
            for candidate in candidates:
                origin = f"{candidate.source_file} ({candidate.source_detail})"
                if candidate.argv is not None:
                    stream.write(f"  {' '.join(candidate.argv)}  <- {origin}\n")
                else:
                    stream.write(f"  [manual review required] {candidate.raw}  <- {origin}\n")
        else:
            stream.write("  none found\n")
        stream.write("\n")

    stream.write("Adoption risk flags:\n")
    if analysis.risk_flags:
        for flag in analysis.risk_flags:
            stream.write(f"  [{flag.status}] {flag.name}: {flag.detail}\n")
            if flag.guidance:
                stream.write(f"      guidance: {flag.guidance}\n")
    else:
        stream.write("  none raised\n")
    stream.write("\n")

    stream.write(
        "All values above are proposals with provenance; nothing is applied without "
        "operator confirmation.\n"
    )


def repo_analysis_json(analysis: RepoAnalysis) -> str:
    """
    @brief      Serialize a :class:`RepoAnalysis` to the frozen ``--json``
                shape (see module docstring for the field-name contract).
    @param[in]  analysis The analysis to serialize.
    @return     JSON text, 2-space indent.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    return json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False)


# END OF FILE
