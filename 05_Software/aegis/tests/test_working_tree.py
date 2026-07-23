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
@brief Workflow support module for test_working_tree.
@details Covers expected workflow behavior through focused pytest checks.
@author Eng. Dan Dumitru Pasare
@date 2026-06-20
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess

import pytest

from aegis.cli import main


# LOCAL HELPERS


def run_cli(tmp_path: Path, *args: str) -> None:
    """
    @brief      Run CLI workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  args Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        main(list(args))
    finally:
        os.chdir(cwd)


def init_repo(tmp_path: Path) -> None:
    """
    @brief      Handle init repo workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "add", ".agentic/workflow.toml"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "workflow config"],
        cwd=tmp_path,
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


# TESTS


def test_working_tree_audit_reports_arbitrary_untracked_files_without_failing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Handle test working tree audit reports arbitrary untracked files without failing workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
    """
    init_repo(tmp_path)
    (tmp_path / "meeting-notes.md").write_text("Local human notes.\n", encoding="utf-8")

    run_cli(tmp_path, "working-tree", "audit")
    report = json.loads(capsys.readouterr().out)

    assert report["blocking_findings"] == []
    assert report["untracked"] == [{"status": "??", "path": "meeting-notes.md"}]


def test_working_tree_audit_fails_for_configured_blocked_patterns(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Handle test working tree audit fails for configured blocked patterns workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    replace_workflow_toml(
        '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
        '[guardrails.working_tree]\nmode = "restricted"\nblocked_patterns = ["generated/**"]',
    )
    init_repo(tmp_path)
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "artifact.txt").write_text("Generated delivery blocker.\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        run_cli(tmp_path, "working-tree", "audit")

    assert exc.value.code == 1


def test_working_tree_audit_matches_blocked_pattern_for_non_ascii_filename(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      A blocked-pattern path with a non-ASCII name is still matched.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @details    Regression test (code-review follow-up, 2026-07-18): Git's
                default `core.quotePath=true` reports a non-ASCII filename such
                as `café.txt` as the C-style-quoted, octal-escaped string
                `"caf\303\251.txt"` in `git status --porcelain` output. Before
                the `-c core.quotepath=false` fix plus `_unquote_git_path`,
                `_git_status` passed that literal quoted string through
                unchanged, so no blocked-pattern glob (like `generated/**`)
                could ever match it.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.2.0
    """
    replace_workflow_toml(
        '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
        '[guardrails.working_tree]\nmode = "restricted"\nblocked_patterns = ["generated/**"]',
    )
    init_repo(tmp_path)
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "café.txt").write_text("Generated delivery blocker.\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        run_cli(tmp_path, "working-tree", "audit")

    assert exc.value.code == 1


def test_delivery_preflight_allows_arbitrary_untracked_files(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Handle test delivery preflight allows arbitrary untracked files workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    init_repo(tmp_path)
    run_cli(tmp_path, "start", "--kind", "feature", "--statement", "demo")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")
    (tmp_path / "saved-mail.txt").write_text("Local user artifact.\n", encoding="utf-8")

    run_cli(tmp_path, "delivery-preflight")

    assert "Delivery preflight passed" in capsys.readouterr().out


def test_delivery_preflight_blocks_adoption_source_changes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify adoption delivery blocks application source changes.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @param[in]  replace_workflow_toml Strict configuration editor fixture.
    @version    0.3.0
    """
    replace_workflow_toml(
        '[adoption.source_changes]\nmode = "unrestricted"',
        '[adoption.source_changes]\nmode = "blocked"',
    )
    init_repo(tmp_path)
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")
    source = tmp_path / "src" / "billing"
    source.mkdir(parents=True)
    (source / "invoice.py").write_text("def total():\n    return 1\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        run_cli(tmp_path, "delivery-preflight")

    output = capsys.readouterr().out
    assert exc.value.code == 1
    assert "ADOPTION-SOURCE-CHANGE" in output
    assert "src/billing/invoice.py" in output


def test_delivery_preflight_blocks_untracked_file_under_nested_source_root(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify adoption delivery blocks nested untracked source roots.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @param[in]  replace_workflow_toml Strict configuration editor fixture.
    @version    0.3.0
    """
    replace_workflow_toml('roots = ["src", "app", "lib"]', 'roots = ["src/billing"]')
    replace_workflow_toml(
        '[adoption.source_changes]\nmode = "unrestricted"',
        '[adoption.source_changes]\nmode = "blocked"',
    )
    init_repo(tmp_path)
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")
    source = tmp_path / "src" / "billing"
    source.mkdir(parents=True)
    (source / "invoice.py").write_text("def total():\n    return 1\n", encoding="utf-8")
    waivers = tmp_path / ".agentic" / "requirements" / "coverage_waivers.txt"
    waivers.parent.mkdir(parents=True, exist_ok=True)
    waivers.write_text("src/billing/invoice.py\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        run_cli(tmp_path, "delivery-preflight")

    output = capsys.readouterr().out
    assert exc.value.code == 1
    assert "ADOPTION-SOURCE-CHANGE" in output
    assert "src/billing/invoice.py" in output


def test_delivery_preflight_allows_adoption_artifacts_and_characterization_tests(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify adoption delivery allows non-runtime adoption artifacts.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    init_repo(tmp_path)
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")
    adoption_paths = [
        ".agentic/components.toml",
        ".agentic/knowledge/components/billing.md",
        ".agentic/reports/adoption/components/billing-baseline.md",
        "tests/billing/test_invoice_characterization.py",
    ]
    for relative_path in adoption_paths:
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# adoption artifact\n", encoding="utf-8")

    run_cli(tmp_path, "delivery-preflight")

    output = capsys.readouterr().out
    assert "ADOPTION-SOURCE-CHANGE" not in output
    assert "Delivery preflight passed" in output


def test_delivery_preflight_blocks_adoption_source_rename_to_non_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify adoption delivery blocks source paths hidden by renames.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @param[in]  replace_workflow_toml Strict configuration editor fixture.
    @version    0.3.0
    """
    replace_workflow_toml(
        '[adoption.source_changes]\nmode = "unrestricted"',
        '[adoption.source_changes]\nmode = "blocked"',
    )
    init_repo(tmp_path)
    source = tmp_path / "src" / "billing"
    source.mkdir(parents=True)
    invoice = source / "invoice.py"
    invoice.write_text("def total():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/billing/invoice.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "baseline"],
        cwd=tmp_path,
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
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")
    docs = tmp_path / "docs"
    docs.mkdir()
    invoice.rename(docs / "invoice.py")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, capture_output=True)

    with pytest.raises(SystemExit) as exc:
        run_cli(tmp_path, "delivery-preflight")

    output = capsys.readouterr().out
    assert exc.value.code == 1
    assert "ADOPTION-SOURCE-CHANGE" in output
    assert "src/billing/invoice.py" in output


def test_delivery_preflight_allows_adoption_source_changes_when_config_enabled(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief      Verify configured adoption behavior changes bypass the guardrail.
    @param[in]  tmp_path Input value used by the workflow helper.
    @param[in]  capsys Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.2.0
    """
    init_repo(tmp_path)
    run_cli(tmp_path, "start", "--kind", "adoption", "--statement", "Adopt billing")
    run_cli(tmp_path, "record-evidence", "--kind", "note", "--result", "info", "--summary", "ready")
    source = tmp_path / "src" / "billing"
    source.mkdir(parents=True)
    (source / "invoice.py").write_text("def total():\n    return 1\n", encoding="utf-8")
    run_cli(tmp_path, "delivery-preflight")

    output = capsys.readouterr().out
    assert "ADOPTION-SOURCE-CHANGE" not in output
    assert "Delivery preflight passed" in output


def test_working_tree_blocks_when_directory_is_not_a_repository(tmp_path: Path) -> None:
    """
    @brief      Verify a non-repository working tree blocks instead of passing.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @return     None.
    @details    Regression guard. `git status` exits 128 outside a repository
                and writes its diagnosis to stderr, leaving stdout empty —
                byte-identical to a genuinely clean tree. The audit read only
                stdout, so it concluded there was nothing to block on and
                delivery preflight passed without ever having inspected
                anything.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    with pytest.raises(SystemExit):
        run_cli(tmp_path, "working-tree")


def test_working_tree_blocks_when_git_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief      Verify a missing git executable blocks instead of raising.
    @param[in]  tmp_path Temporary repository root used by the workflow helper.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None.
    @details    The second failure mode, and the one that behaved differently:
                a missing git raised `FileNotFoundError` straight out of the
                audit, so the delivery hook surfaced a raw traceback as its deny
                reason instead of an actionable message. It now blocks the same
                way an unreadable status does.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-23
    @version    0.1.0
    """
    init_repo(tmp_path)

    def _no_git(*args: object, **kwargs: object) -> None:
        """@brief Stand in for an absent git executable."""
        raise FileNotFoundError(2, "The system cannot find the file specified", "git")

    monkeypatch.setattr("aegis.working_tree.subprocess.run", _no_git)
    with pytest.raises(SystemExit):
        run_cli(tmp_path, "working-tree")


# END OF FILE
