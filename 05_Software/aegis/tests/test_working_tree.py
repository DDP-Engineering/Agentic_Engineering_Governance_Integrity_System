#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_working_tree.py
@brief Deterministic working-tree review tests for AEGIS 2.
@details Covers untracked reporting, configured blockers, Unicode paths,
         adoption source protection, and fail-closed Git diagnostics.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import subprocess

import pytest

from aegis.config import load_config
from aegis.models import Graph, Intent
from aegis.working_tree import _git_status, audit_working_tree

# TESTS


def test_audit_reports_untracked_file_without_blocking(tmp_path: Path) -> None:
    """@brief Treat ordinary untracked files as review input, not failure."""
    _init_repo(tmp_path)
    (tmp_path / "meeting-notes.md").write_text("Notes.\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert report["blocking_findings"] == []
    assert report["untracked"] == [{"status": "??", "path": "meeting-notes.md"}]


def test_audit_matches_configured_blocker_and_unicode_path(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Match blocked globs after Git path decoding."""
    replace_workflow_toml(
        '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
        '[guardrails.working_tree]\nmode = "restricted"\n'
        'blocked_patterns = ["generated/**"]',
    )
    _init_repo(tmp_path)
    path = tmp_path / "generated" / "café.txt"
    path.parent.mkdir()
    path.write_text("Generated.\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert report["blocking_findings"][0]["code"] == "blocked-pattern"
    assert report["blocking_findings"][0]["path"] == "generated/café.txt"


def test_adoption_source_change_is_blocked(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Keep adoption delivery from silently changing application code."""
    replace_workflow_toml(
        '[adoption.source_changes]\nmode = "unrestricted"',
        '[adoption.source_changes]\nmode = "blocked"',
    )
    _init_repo(tmp_path)
    source = tmp_path / "src" / "app.py"
    source.parent.mkdir()
    source.write_text("print('changed')\n", encoding="utf-8")
    graph = Graph(
        run_id="adoption-20260729T120000Z-abcdef12",
        stage="adoption-delivery",
        intent=Intent(id="I-1", kind="adoption", statement="Adopt repository"),
    )

    report = audit_working_tree(tmp_path, load_config(tmp_path), graph)

    assert any(
        finding["code"] == "ADOPTION-SOURCE-CHANGE"
        for finding in report["blocking_findings"]
    )


def test_non_repository_fails_closed(tmp_path: Path) -> None:
    """@brief Report unavailable Git state as a blocking finding."""
    report = audit_working_tree(tmp_path, load_config(tmp_path))
    assert report["blocking_findings"][0]["code"] == "git-status-unavailable"


def test_missing_git_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Convert a missing executable into deterministic review failure."""
    def unavailable(*args: object, **kwargs: object) -> None:
        """@brief Simulate a host without Git."""
        raise FileNotFoundError("git missing")

    monkeypatch.setattr(subprocess, "run", unavailable)
    report = audit_working_tree(tmp_path, load_config(tmp_path))
    assert report["blocking_findings"][0]["code"] == "git-status-unavailable"


def test_git_status_uses_bounded_nul_delimited_rename_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Parse arrow-bearing rename paths without ambiguous splitting."""
    observed: dict[str, object] = {}

    def completed(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        """@brief Return one rename and one ordinary arrow-bearing filename."""
        observed["command"] = command
        observed.update(kwargs)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="R  new -> name\0old -> name\0?? literal -> name\0",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", completed)

    entries, error = _git_status(tmp_path)

    assert error is None
    assert entries == [
        {
            "status": "R ",
            "path": "new -> name",
            "previous_path": "old -> name",
        },
        {"status": "??", "path": "literal -> name"},
    ]
    assert "-z" in observed["command"]
    assert observed["timeout"] == 30
    assert observed["errors"] == "strict"


def test_git_status_timeout_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A hung Git process becomes a bounded unavailable-state result."""
    def timeout(*_args: object, **_kwargs: object) -> None:
        """@brief Simulate Git exceeding its audit deadline."""
        raise subprocess.TimeoutExpired("git", 30)

    monkeypatch.setattr(subprocess, "run", timeout)

    entries, error = _git_status(tmp_path)

    assert entries == []
    assert error is not None
    assert "timed out" in error


def test_renaming_a_protected_file_is_still_a_protected_path_finding(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A rename out of a protected location does not evade the guard.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Shared policy-fragment fixture.
    @return     None.
    @details    Regression test (B2, 2026-08-04): the protected-path and
                blocked-pattern checks tested the bare `entry["path"]`, which
                for an `R`/`C` porcelain entry is the *destination*. Three lines
                above, the adoption-source check already used `_entry_paths`,
                which returns Git's `previous_path` too - so the asymmetry was
                an oversight in a function whose docstring says it has to fail
                closed. `git mv config/secrets.yaml …` moved a protected file
                out of its protected location and produced no finding at all.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
        '[guardrails.protected_paths]\nmode = "enforce"\n'
        'patterns = ["config/secrets.yaml"]\noperations = ["write"]',
    )
    _init_repo(tmp_path)
    protected = tmp_path / "config" / "secrets.yaml"
    protected.parent.mkdir()
    protected.write_text("token: value\n", encoding="utf-8")
    _git(tmp_path, "add", "config/secrets.yaml")
    _commit(tmp_path, "add protected file")
    _git(tmp_path, "mv", "config/secrets.yaml", "config/legacy-secrets.yaml")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert [
        finding["path"]
        for finding in report["blocking_findings"]
        if finding["code"] == "protected-path"
    ] == ["config/secrets.yaml"]


def test_blocked_pattern_also_matches_a_rename_source(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      The blocked-pattern check reads both paths of a rename too.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Shared policy-fragment fixture.
    @return     None.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
        '[guardrails.working_tree]\nmode = "restricted"\n'
        'blocked_patterns = ["generated/**"]',
    )
    _init_repo(tmp_path)
    generated = tmp_path / "generated" / "bundle.js"
    generated.parent.mkdir()
    generated.write_text("// bundle\n", encoding="utf-8")
    _git(tmp_path, "add", "generated/bundle.js")
    _commit(tmp_path, "add generated file")
    _git(tmp_path, "mv", "generated/bundle.js", "dist-bundle.js")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert [
        finding["path"]
        for finding in report["blocking_findings"]
        if finding["code"] == "blocked-pattern"
    ] == ["generated/bundle.js"]


@pytest.mark.skipif(
    os.name == "nt",
    reason="A backslash is not a legal filename character on Windows.",
)
def test_backslash_in_a_posix_filename_is_not_translated(tmp_path: Path) -> None:
    """
    @brief      A literal backslash in a filename survives status decoding.
    @param[in]  tmp_path Temporary repository root.
    @return     None.
    @details    NUL-delimited porcelain emits path bytes without C-style quote
                parsing or separator replacement, so a literal backslash stays
                part of the POSIX filename and reaches policy matching intact.
    @exception  None
    """
    _init_repo(tmp_path)
    (tmp_path / "data\\report.csv").write_text("value\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert report["untracked"] == [{"status": "??", "path": "data\\report.csv"}]


def test_secret_scan_skips_generated_run_artifacts(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      AEGIS's own run output is not scanned for secrets.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Exact workflow configuration editor.
    @return     None.
    @details    Regression test (lifecycle field test, 2026-08-06): every file
                `verify run` writes under `.agentic/runs/<run-id>/` embeds the
                secrets invariant's own name and message, so the delivery
                preflight raised a `secret-pattern` finding against AEGIS's own
                `validation-summary.json`. A file beside it that AEGIS did not
                write is still scanned.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
        '[guardrails.secrets]\nmode = "enforce"\npatterns = ["(?i)secret"]',
    )
    _init_repo(tmp_path)
    run_directory = tmp_path / ".agentic" / "runs" / "RUN-20260806-000000"
    run_directory.mkdir(parents=True)
    (run_directory / "validation-summary.json").write_text(
        '{"name": "Clean secrets"}\n', encoding="utf-8"
    )
    (tmp_path / "authored.md").write_text("my secret token\n", encoding="utf-8")

    report = audit_working_tree(tmp_path, load_config(tmp_path))

    assert [
        finding["path"]
        for finding in report["blocking_findings"]
        if finding["code"] == "secret-pattern"
    ] == ["authored.md"]


def test_secret_scan_skips_the_secrets_policy_declaration(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      The table declaring the patterns is not scanned with them.
    @param[in]  tmp_path Temporary repository root.
    @param[in]  replace_workflow_toml Exact workflow configuration editor.
    @return     None.
    @details    Regression test (lifecycle field test, 2026-08-06, batch 2):
                editing `.agentic/workflow.toml` put it in the working tree, and
                `(?i)secret` then matched the `[guardrails.secrets]` header that
                declares it - so every run that touched the configuration raised
                a `secret-pattern` finding against the configuration. A
                credential pasted elsewhere in the same file is still found.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
        '[guardrails.secrets]\nmode = "enforce"\npatterns = ["(?i)secret"]',
    )
    _init_repo(tmp_path)
    config_path = tmp_path / ".agentic" / "workflow.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'patterns = ["(?i)secret"]', 'patterns = ["(?i)secret", "(?i)token"]'
        ),
        encoding="utf-8",
        newline="\n",
    )

    exempt = audit_working_tree(tmp_path, load_config(tmp_path))

    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            '[gates.security]\nmode = "disabled"\ncommands = []',
            '[gates.security]\nmode = "enforce"\ncommands = ["scan --secret abc"]',
        ),
        encoding="utf-8",
        newline="\n",
    )
    elsewhere = audit_working_tree(tmp_path, load_config(tmp_path))

    assert [
        finding["path"]
        for finding in exempt["blocking_findings"]
        if finding["code"] == "secret-pattern"
    ] == []
    assert [
        finding["path"]
        for finding in elsewhere["blocking_findings"]
        if finding["code"] == "secret-pattern"
    ] == [".agentic/workflow.toml"]


def _git(repo_root: Path, *arguments: str) -> None:
    """@brief Run one Git command in the fixture repository."""
    subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )


def _commit(repo_root: Path, message: str) -> None:
    """@brief Commit the index with a deterministic identity."""
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


def _init_repo(repo_root: Path) -> None:
    """@brief Initialize and commit the generated schema-3 policy."""
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "add", ".agentic/workflow.toml"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "workflow config"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        },
    )


# END OF FILE
