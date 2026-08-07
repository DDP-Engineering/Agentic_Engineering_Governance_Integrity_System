#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repo_analyze.py
@brief Tests for the Wizard E repo analysis heuristics (task T5.1, plan §9).
@details Strictly offline. Git-based inventory tests script a
         :class:`FakeCommandRunner` with realistic ``git ls-files -z`` output
         (the fake-only pattern ``test_repo_gitops.py`` establishes); the walk
         fallback is exercised with a runner reporting git absent. Fixtures are
         small synthetic repos under ``tmp_path``; the very-large-repo case
         injects a synthetic :class:`Inventory` into :func:`analyze_inventory`
         rather than materializing 10k files. Every fixture with a clear
         language asserts the proposed ``language`` is an exact
         ``LANGUAGE_PRESETS`` key (the T5.2 handoff guarantee).
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Sequence

from waegis.repo import analyze
from waegis.repo.analyze import FileRecord, Inventory
from waegis.repo.workflow_toml import LANGUAGE_PRESETS, normalize_roots
from waegis.probes.runner import CommandResult

# LOCAL HELPERS


class _FakeGitRunner:
    """
    @brief Fake :class:`CommandRunner` scripting ``git ls-files -z`` for one
           repo path (the T5.1 git inventory path).
    @details Any other argv (or a different repo path) reports "not found",
             matching :class:`waegis.probes.runner.SubprocessCommandRunner`.
    """

    def __init__(self, repo: Path, files: Sequence[str]) -> None:
        """
        @brief      Build a runner returning ``files`` for ``repo``'s ls-files.
        @param[in]  repo Repository path the ls-files argv targets.
        @param[in]  files Repo-relative tracked paths to return, NUL-joined.
        """
        self._key = ("git", "-C", str(repo), "ls-files", "-z")
        self._stdout = "\0".join(files)

    def run(self, argv, *, timeout: float = 5.0, cwd=None) -> CommandResult:
        """
        @brief      Return the scripted ls-files output, else "not found".
        @param[in]  argv Argument vector.
        @param[in]  timeout Ignored.
        @param[in]  cwd Ignored.
        @return     The scripted :class:`CommandResult`.
        @exception  None
        """
        if tuple(argv) == self._key:
            return CommandResult(found=True, exit_code=0, stdout=self._stdout, stderr="")
        return CommandResult(found=False, exit_code=None, stdout="", stderr="")


class _NoGitRunner:
    """
    @brief Fake :class:`CommandRunner` reporting git absent for every argv,
           forcing the filesystem-walk inventory fallback.
    """

    def run(self, argv, *, timeout: float = 5.0, cwd=None) -> CommandResult:
        """
        @brief      Always report "not found".
        @param[in]  argv Ignored argument vector.
        @param[in]  timeout Ignored.
        @param[in]  cwd Ignored.
        @return     A not-found :class:`CommandResult`.
        @exception  None
        """
        return CommandResult(found=False, exit_code=None, stdout="", stderr="")


def _write(repo: Path, rel_path: str, content: str = "x\n") -> None:
    """
    @brief      Write a fixture file, creating parent directories.
    @param[in]  repo Repository root.
    @param[in]  rel_path Repo-relative path.
    @param[in]  content File content.
    @return     None
    """
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _flag_names(result: analyze.RepoAnalysis) -> set[str]:
    """
    @brief      Collect the risk-flag names raised on a result.
    @param[in]  result The analysis result.
    @return     Set of ``flag.name`` values.
    """
    return {flag.name for flag in result.risk_flags}


# TESTS

# --- python-src ---------------------------------------------------------------


def test_python_src_fixture_via_git_inventory(tmp_path: Path) -> None:
    """
    @brief      python-src (pyproject + src/ + tests/): language=python,
                source_roots=["src"], test_roots=["tests"], pyproject gate
                candidates present; inventory came from git.
    @return     None
    @exception  AssertionError If any proposal is wrong.
    """
    _write(tmp_path, "pyproject.toml", "[tool.pytest.ini_options]\n[tool.ruff]\n")
    _write(tmp_path, "src/pkg/__init__.py", "")
    _write(tmp_path, "src/pkg/core.py", "x = 1\n" * 40)
    _write(tmp_path, "tests/test_core.py", "def test_x():\n    pass\n")
    files = ["pyproject.toml", "src/pkg/__init__.py", "src/pkg/core.py", "tests/test_core.py"]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert result.inventory_source == "git"
    assert result.language == "python"
    assert [p.path for p in result.source_roots] == ["src"]
    assert [p.path for p in result.test_roots] == ["tests"]
    assert result.colocated_tests.detected is False
    test_argvs = [c.argv for c in result.gate_test_cmds]
    lint_argvs = [c.argv for c in result.gate_lint_cmds]
    assert ("pytest", "-q") in test_argvs
    assert ("ruff", "check", ".") in lint_argvs
    assert all(c.source_file == "pyproject.toml" for c in result.gate_test_cmds + result.gate_lint_cmds)


# --- node-monorepo ------------------------------------------------------------


def test_node_monorepo_fixture(tmp_path: Path) -> None:
    """
    @brief      node-monorepo: javascript ranked, monorepo risk flag raised,
                gate candidates from package.json scripts with that provenance.
    @return     None
    @exception  AssertionError If the language, flag, or provenance is wrong.
    """
    _write(tmp_path, "package.json", '{"scripts": {"test": "jest", "lint": "eslint ."}}')
    _write(tmp_path, "package-lock.json", "{}")
    _write(tmp_path, "packages/a/package.json", "{}")
    _write(tmp_path, "packages/a/index.js", "console.log(1)\n" * 10)
    _write(tmp_path, "packages/b/package.json", "{}")
    _write(tmp_path, "packages/b/index.js", "console.log(2)\n" * 10)
    files = [
        "package.json",
        "package-lock.json",
        "packages/a/package.json",
        "packages/a/index.js",
        "packages/b/package.json",
        "packages/b/index.js",
    ]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert result.language == "javascript"
    assert "risk.monorepo" in _flag_names(result)
    test_candidate = result.gate_test_cmds[0]
    lint_candidate = result.gate_lint_cmds[0]
    assert test_candidate.source_file == "package.json"
    assert test_candidate.source_detail == "scripts.test"
    assert test_candidate.argv == ("npm", "test")
    assert lint_candidate.source_detail == "scripts.lint"
    assert lint_candidate.argv == ("npm", "run", "lint")


def test_node_monorepo_lockfile_selects_package_manager(tmp_path: Path) -> None:
    """
    @brief      A yarn.lock steers package.json gate candidates to yarn.
    @return     None
    @exception  AssertionError If the package manager was not yarn.
    """
    _write(tmp_path, "package.json", '{"scripts": {"test": "jest"}}')
    _write(tmp_path, "yarn.lock", "")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())

    assert result.gate_test_cmds[0].argv == ("yarn", "run", "test")


# --- java-maven ---------------------------------------------------------------


def test_java_maven_fixture(tmp_path: Path) -> None:
    """
    @brief      java-maven: language=java, source_roots detects the Maven
                layout, test_roots detects src/test/java specifically.
    @return     None
    @exception  AssertionError If a proposal is wrong.
    """
    _write(tmp_path, "pom.xml", "<project/>")
    _write(tmp_path, "src/main/java/com/x/App.java", "class App {}\n" * 20)
    _write(tmp_path, "src/test/java/com/x/AppTest.java", "class AppTest {}\n")
    files = ["pom.xml", "src/main/java/com/x/App.java", "src/test/java/com/x/AppTest.java"]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert result.language == "java"
    assert [p.path for p in result.source_roots] == ["src/main/java"]
    assert [p.path for p in result.test_roots] == ["src/test/java"]


# --- go-colocated-tests -------------------------------------------------------


def test_go_colocated_tests_fixture(tmp_path: Path) -> None:
    """
    @brief      go-colocated: language=go, colocated-tests flag raised, and
                test_roots reflects the file-pattern reality (empty — no test
                directory) rather than a fictional directory.
    @return     None
    @exception  AssertionError If the flag or proposals are wrong.
    """
    _write(tmp_path, "go.mod", "module example.com/x\n")
    _write(tmp_path, "pkg/foo.go", "package pkg\n" * 10)
    _write(tmp_path, "pkg/foo_test.go", "package pkg\n")
    _write(tmp_path, "cmd/main.go", "package main\n" * 5)
    files = ["go.mod", "pkg/foo.go", "pkg/foo_test.go", "cmd/main.go"]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert result.language == "go"
    assert result.test_roots == ()
    assert result.colocated_tests.detected is True
    assert result.colocated_tests.patterns == ("*_test.go",)
    assert "*_test.go" in result.colocated_tests.note
    source_paths = {p.path for p in result.source_roots}
    assert "pkg" in source_paths and "cmd" in source_paths


# --- guaranteed conflict vs prior install -------------------------------------


def test_existing_claude_md_raises_guaranteed_conflict(tmp_path: Path) -> None:
    """
    @brief      A plain root CLAUDE.md (no .agentic/) raises a
                guaranteed-conflict flag naming that file, with the
                ``"conflict"`` status, and no prior-install flag.
    @return     None
    @exception  AssertionError If the flag is missing or misclassified.
    """
    _write(tmp_path, "CLAUDE.md", "# project\n")
    _write(tmp_path, "main.py", "print(1)\n")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())

    conflicts = [f for f in result.risk_flags if f.name == "risk.guaranteed-conflict"]
    assert len(conflicts) == 1
    assert conflicts[0].status == "conflict"
    assert "CLAUDE.md" in conflicts[0].detail
    assert "risk.prior-install" not in _flag_names(result)


def test_partial_agentic_raises_prior_install_distinctly(tmp_path: Path) -> None:
    """
    @brief      A bare .agentic/ (no manifest, no adapter dirs, no AGENTS.md/
                CLAUDE.md) raises prior-install, distinct from
                guaranteed-conflict, and notes the manifest is absent.
    @return     None
    @exception  AssertionError If the flag is missing or the two are conflated.
    """
    (tmp_path / ".agentic").mkdir()
    _write(tmp_path, "main.py", "print(1)\n")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())

    prior = [f for f in result.risk_flags if f.name == "risk.prior-install"]
    assert len(prior) == 1
    assert prior[0].status == "warn"
    assert "without install manifest" in prior[0].detail
    assert "risk.guaranteed-conflict" not in _flag_names(result)


# --- submodules + LFS ---------------------------------------------------------


def test_submodules_and_lfs_flags_raised_independently(tmp_path: Path) -> None:
    """
    @brief      .gitmodules and .gitattributes(filter=lfs) raise their two
                flags independently.
    @return     None
    @exception  AssertionError If either flag is missing.
    """
    _write(tmp_path, ".gitmodules", '[submodule "vendor"]\n\tpath = vendor\n')
    _write(tmp_path, ".gitattributes", "*.psd filter=lfs diff=lfs merge=lfs -text\n")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())

    names = _flag_names(result)
    assert "risk.submodules" in names
    assert "risk.lfs" in names


def test_gitattributes_without_lfs_does_not_flag(tmp_path: Path) -> None:
    """
    @brief      A .gitattributes without ``filter=lfs`` raises no LFS flag.
    @return     None
    @exception  AssertionError If an LFS flag is spuriously raised.
    """
    _write(tmp_path, ".gitattributes", "* text=auto\n")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())

    assert "risk.lfs" not in _flag_names(result)


# --- very-large repo (injected inventory) -------------------------------------


def test_very_large_repo_raises_heuristic_only_flag(tmp_path: Path) -> None:
    """
    @brief      An inventory over 10,000 files raises the large-repo flag while
                still producing a full analysis — injected, not materialized.
    @return     None
    @exception  AssertionError If the flag is missing or the count is wrong.
    """
    inventory = Inventory(
        source="git",
        files=tuple(FileRecord(path=f"src/mod{i}.py", size=100) for i in range(10_001)),
    )

    result = analyze.analyze_inventory(tmp_path, inventory)

    assert result.file_count == 10_001
    assert "risk.large-repo" in _flag_names(result)
    assert result.language == "python"


def test_exactly_threshold_files_does_not_raise_large_repo(tmp_path: Path) -> None:
    """
    @brief      Exactly 10,000 files does not trip the strictly-greater-than
                large-repo threshold.
    @return     None
    @exception  AssertionError If the flag is spuriously raised.
    """
    inventory = Inventory(
        source="git",
        files=tuple(FileRecord(path=f"src/mod{i}.py", size=100) for i in range(10_000)),
    )

    result = analyze.analyze_inventory(tmp_path, inventory)

    assert "risk.large-repo" not in _flag_names(result)


# --- walk fallback + .gitignore -----------------------------------------------


def test_walk_fallback_honors_top_level_gitignore(tmp_path: Path) -> None:
    """
    @brief      When git is absent the inventory comes from a filesystem walk
                that honors the top-level .gitignore and always skips .git/.
    @return     None
    @exception  AssertionError If an ignored path leaks into the inventory.
    """
    _write(tmp_path, ".gitignore", "build/\n*.log\nnode_modules\n")
    _write(tmp_path, "src/app.py", "x = 1\n")
    _write(tmp_path, "build/artifact.py", "generated\n")
    _write(tmp_path, "debug.log", "noise\n")
    _write(tmp_path, "node_modules/dep/index.js", "1\n")
    _write(tmp_path, ".git/config", "[core]\n")

    inventory = analyze.collect_inventory(tmp_path, runner=_NoGitRunner())
    paths = {record.path for record in inventory.files}

    assert inventory.source == "walk"
    assert "src/app.py" in paths
    assert "build/artifact.py" not in paths
    assert "debug.log" not in paths
    assert "node_modules/dep/index.js" not in paths
    assert not any(p.startswith(".git/") for p in paths)


# --- source-root coverage fallback --------------------------------------------


def test_source_root_coverage_fallback_when_no_convention(tmp_path: Path) -> None:
    """
    @brief      With no conventional layout, source roots fall back to the
                minimal top-level dir set covering >= 90% of code files, tagged
                low confidence.
    @return     None
    @exception  AssertionError If the fallback proposal is wrong.
    """
    # 9 code files in "core", 1 in "extras" -> "core" alone covers 90%.
    for i in range(9):
        _write(tmp_path, f"core/mod{i}.py", "x = 1\n")
    _write(tmp_path, "extras/util.py", "y = 2\n")
    files = [f"core/mod{i}.py" for i in range(9)] + ["extras/util.py"]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert [p.path for p in result.source_roots] == ["core"]
    assert result.source_roots[0].confidence == "low"


# --- language / handoff guarantees --------------------------------------------


def test_managed_workflow_code_never_becomes_project_source(tmp_path: Path) -> None:
    """
    @brief      Installed AEGIS code and adapter code do not influence host
                language or source-root proposals.
    @return     None
    @exception  AssertionError If managed workflow infrastructure leaks into
                the project proposal.
    """
    inventory = Inventory(
        source="git",
        files=(
            FileRecord(".agentic/cli/src/aegis/cli.py", 100_000),
            FileRecord(".pi/extensions/agentic-guard/index.ts", 100_000),
            FileRecord("src/main.go", 10),
        ),
    )

    result = analyze.analyze_inventory(tmp_path, inventory)

    assert result.language == "go"
    assert [proposal.path for proposal in result.source_roots] == ["src"]


def test_no_code_files_yields_other_language(tmp_path: Path) -> None:
    """
    @brief      A repo with no known code extensions proposes language
                "other" (a valid workflow_toml answer) and no crash.
    @return     None
    @exception  AssertionError If the language is not "other".
    """
    _write(tmp_path, "README.md", "# docs only\n")
    _write(tmp_path, "notes.txt", "text\n")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())

    assert result.language == "other"
    assert result.languages == ()


def test_every_fixture_language_is_a_preset_key_and_roots_normalize(tmp_path: Path) -> None:
    """
    @brief      T5.2 handoff guarantee: a clear-language fixture's proposed
                ``language`` is an exact LANGUAGE_PRESETS key, and every root
                proposal survives ``normalize_roots`` unchanged.
    @return     None
    @exception  AssertionError If a language name or root shape would break
                the generate_workflow_toml handoff.
    """
    _write(tmp_path, "pyproject.toml", "[tool.ruff]\n")
    _write(tmp_path, "src/app.py", "x = 1\n" * 10)
    _write(tmp_path, "tests/test_app.py", "def test():\n    pass\n")
    files = ["pyproject.toml", "src/app.py", "tests/test_app.py"]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert result.language in LANGUAGE_PRESETS
    source_paths = [p.path for p in result.source_roots]
    test_paths = [p.path for p in result.test_roots]
    assert normalize_roots(source_paths) == source_paths
    assert normalize_roots(test_paths) == test_paths


# --- JSON round-trip ----------------------------------------------------------


def test_json_round_trips_with_documented_field_names(tmp_path: Path) -> None:
    """
    @brief      ``repo_analysis_json`` round-trips through ``json.loads`` with
                the documented top-level field names, and a manual-review gate
                candidate serializes ``argv`` as ``null``.
    @return     None
    @exception  AssertionError If a field name or the null argv is wrong.
    """
    _write(tmp_path, "pyproject.toml", "[tool.pytest.ini_options]\n")
    _write(tmp_path, "src/app.py", "x = 1\n")
    _write(tmp_path, "Makefile", "test:\n\tpytest\n")
    _write(tmp_path, ".github/workflows/ci.yml", "jobs:\n  x:\n    steps:\n      - run: pytest && ruff .\n")
    files = ["pyproject.toml", "src/app.py", "Makefile", ".github/workflows/ci.yml"]

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))
    parsed = json.loads(analyze.repo_analysis_json(result))

    for key in (
        "repo",
        "inventory_source",
        "file_count",
        "language",
        "languages",
        "build_systems",
        "source_roots",
        "test_roots",
        "colocated_tests",
        "gate_test_cmds",
        "gate_lint_cmds",
        "risk_flags",
    ):
        assert key in parsed
    manual = [c for group in ("gate_test_cmds", "gate_lint_cmds") for c in parsed[group] if c["needs_review"]]
    assert manual, "expected the shell-syntax CI line to produce a manual-review candidate"
    assert all(c["argv"] is None for c in manual)


def test_render_summary_states_proposals_only(tmp_path: Path) -> None:
    """
    @brief      The human summary renders without error and restates the
                proposals-only contract.
    @return     None
    @exception  AssertionError If the closing contract line is absent.
    """
    _write(tmp_path, "src/app.py", "x = 1\n")

    result = analyze.analyze_repo(tmp_path, runner=_NoGitRunner())
    stream = io.StringIO()
    analyze.render_repo_analysis(result, stream)
    text = stream.getvalue()

    assert "WAEGIS repo analysis" in text
    assert "proposals with provenance" in text


# --- below-root project layouts (W1, W2, W4) ----------------------------------


# @brief A project parked two levels down, the numbered-folder convention this
#        estate uses. Before the depth-aware sweep this proposed the whole
#        `04_Software` tree as source and no test root at all.
_NESTED_LAYOUT: tuple[str, ...] = (
    "04_Software/VoiceWeaver/pyproject.toml",
    "04_Software/VoiceWeaver/src/voiceweaver/__init__.py",
    "04_Software/VoiceWeaver/src/voiceweaver/config.py",
    "04_Software/VoiceWeaver/src/voiceweaver/domain/parsing.py",
    "04_Software/VoiceWeaver/tests/test_config.py",
    "04_Software/VoiceWeaver/tests/test_domain.py",
    "01_Documentation/rules.md",
)


def test_below_root_test_directory_is_proposed(tmp_path: Path) -> None:
    """
    @brief      A `tests/` directory below the repository root is proposed.
    @details    The root-only match left `test_roots` empty, which is the one
                field that makes `--non-interactive` adoption impossible.
    @return     None
    @exception  AssertionError If the nested test root is not proposed.
    """
    result = analyze.analyze_repo(
        tmp_path, runner=_FakeGitRunner(tmp_path, _NESTED_LAYOUT)
    )

    assert [p.path for p in result.test_roots] == ["04_Software/VoiceWeaver/tests"]
    assert result.test_roots[0].confidence == "medium"


def test_below_root_source_directory_beats_the_coverage_fallback(tmp_path: Path) -> None:
    """
    @brief      A nested `src/` is proposed instead of the whole numbered tree.
    @details    The coverage fallback previously proposed `04_Software`, which
                also owns build output, models, and virtual environments.
    @return     None
    @exception  AssertionError If the fallback still wins.
    """
    result = analyze.analyze_repo(
        tmp_path, runner=_FakeGitRunner(tmp_path, _NESTED_LAYOUT)
    )

    assert [p.path for p in result.source_roots] == ["04_Software/VoiceWeaver/src"]
    assert "fallback" not in result.source_roots[0].reason


def test_below_root_tests_are_not_reported_as_colocated(tmp_path: Path) -> None:
    """
    @brief      Finding the nested test root clears the colocated-tests flag.
    @details    With no test root detected, every `test_*.py` looked colocated
                and the operator was advised to switch to file-pattern write
                zones for an ordinary `tests/` directory.
    @return     None
    @exception  AssertionError If colocation is still reported.
    """
    result = analyze.analyze_repo(
        tmp_path, runner=_FakeGitRunner(tmp_path, _NESTED_LAYOUT)
    )

    assert result.colocated_tests.detected is False


def test_nested_roots_never_overlap_a_named_convention(tmp_path: Path) -> None:
    """
    @brief      A nested sweep hit never widens an already-proposed root.
    @details    `src/test` matches the `test` convention at depth one and would
                otherwise be proposed alongside the Maven `src/test/java` it
                contains.
    @return     None
    @exception  AssertionError If an overlapping root is proposed.
    """
    files = (
        "src/main/java/com/example/App.java",
        "src/test/java/com/example/AppTest.java",
    )

    result = analyze.analyze_repo(tmp_path, runner=_FakeGitRunner(tmp_path, files))

    assert [p.path for p in result.test_roots] == ["src/test/java"]
    assert [p.path for p in result.source_roots] == ["src/main/java"]


# END OF FILE
