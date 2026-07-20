#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repo_gitops.py
@brief Tests for the git primitives over CommandRunner (T4.2).
@details Strictly offline: every test uses :class:`FakeCommandRunner` from
         ``_fake_command_runner.py`` and asserts on scripted responses and
         recorded argv tuples. No test invokes a real ``git`` process.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from waegis.repo import gitops

from _fake_command_runner import FakeCommandRunner, failing_result, ok_result

# TESTS

# --- is_work_tree -------------------------------------------------------------


def test_is_work_tree_true_when_inside_work_tree() -> None:
    """
    @brief      ``rev-parse --is-inside-work-tree`` printing ``true`` reports
                ``True``.
    @return     None
    @exception  AssertionError If the result is not ``True``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {("git", "-C", "/repo", "rev-parse", "--is-inside-work-tree"): ok_result(stdout="true\n")}
    )

    assert gitops.is_work_tree(runner, "/repo") is True


def test_is_work_tree_false_when_not_a_repo() -> None:
    """
    @brief      A non-zero exit (not a git repo) reports ``False``.
    @return     None
    @exception  AssertionError If the result is not ``False``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/plain-dir", "rev-parse", "--is-inside-work-tree"): failing_result(
                exit_code=128, stderr="fatal: not a git repository"
            )
        }
    )

    assert gitops.is_work_tree(runner, "/plain-dir") is False


def test_is_work_tree_false_when_git_not_found() -> None:
    """
    @brief      A missing git executable reports ``False``, never raises.
    @return     None
    @exception  AssertionError If the call raises or returns other than
                ``False``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({})

    assert gitops.is_work_tree(runner, "/anywhere") is False


# --- init_repo ------------------------------------------------------------


def test_init_repo_success_with_dash_b_supported() -> None:
    """
    @brief      A modern git accepts ``init -b main`` directly; no fallback
                commands are issued.
    @return     None
    @exception  AssertionError If ``ok`` is not ``True`` or extra calls made.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {("git", "init", "-b", "main", "/new-repo"): ok_result(stdout="Initialized empty Git repository")}
    )

    result = gitops.init_repo(runner, "/new-repo")

    assert result.ok is True
    assert runner.calls == [("git", "init", "-b", "main", "/new-repo")]


def test_init_repo_falls_back_on_older_git_without_dash_b() -> None:
    """
    @brief      When ``-b`` is unrecognized (older git), falls back to plain
                ``init`` then ``symbolic-ref HEAD`` to rename the branch.
    @return     None
    @exception  AssertionError If the fallback commands are not issued in
                order or ``ok`` is not ``True``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "init", "-b", "main", "/new-repo"): failing_result(
                exit_code=129, stderr="error: unknown option `b'"
            ),
            ("git", "init", "/new-repo"): ok_result(stdout="Initialized empty Git repository"),
            ("git", "-C", "/new-repo", "symbolic-ref", "HEAD", "refs/heads/main"): ok_result(),
        }
    )

    result = gitops.init_repo(runner, "/new-repo")

    assert result.ok is True
    assert runner.calls == [
        ("git", "init", "-b", "main", "/new-repo"),
        ("git", "init", "/new-repo"),
        ("git", "-C", "/new-repo", "symbolic-ref", "HEAD", "refs/heads/main"),
    ]


def test_init_repo_failure_surfaces_ok_false_with_detail() -> None:
    """
    @brief      A genuine init failure (not the ``-b``-unsupported shape)
                surfaces ``ok=False`` with git's stderr, no fallback attempted.
    @return     None
    @exception  AssertionError If ``ok`` is not ``False`` or a fallback ran.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "init", "-b", "main", "/no-perms"): failing_result(
                exit_code=128, stderr="fatal: permission denied"
            )
        }
    )

    result = gitops.init_repo(runner, "/no-perms")

    assert result.ok is False
    assert "permission denied" in result.detail
    assert runner.calls == [("git", "init", "-b", "main", "/no-perms")]


# --- clone_repo -------------------------------------------------------------


def test_clone_repo_success() -> None:
    """
    @brief      A successful clone reports ``ok=True``.
    @return     None
    @exception  AssertionError If ``ok`` is not ``True``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "clone", "https://example.test/repo.git", "/dest"): ok_result(
                stderr="Cloning into '/dest'..."
            )
        }
    )

    result = gitops.clone_repo(runner, "https://example.test/repo.git", "/dest")

    assert result.ok is True


def test_clone_repo_target_already_exists_non_empty_short_circuits(tmp_path) -> None:
    """
    @brief      A pre-existing non-empty target directory is rejected before
                the runner is ever invoked.
    @return     None
    @exception  AssertionError If the runner recorded any call, or ``ok`` is
                not ``False``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "dest"
    target.mkdir()
    (target / "existing.txt").write_text("hello")
    runner = FakeCommandRunner({})

    result = gitops.clone_repo(runner, "https://example.test/repo.git", target)

    assert result.ok is False
    assert "not empty" in result.detail
    assert runner.calls == []


def test_clone_repo_git_failure_passes_through_stderr() -> None:
    """
    @brief      A network/auth clone failure passes git's own stderr through
                in ``detail``.
    @return     None
    @exception  AssertionError If the failure detail does not contain git's
                stderr, or ``ok`` is not ``False``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "clone", "https://example.test/missing.git", "/dest"): failing_result(
                exit_code=128, stderr="fatal: repository 'https://example.test/missing.git' not found"
            )
        }
    )

    result = gitops.clone_repo(runner, "https://example.test/missing.git", "/dest")

    assert result.ok is False
    assert "not found" in result.detail


# --- get_identity -----------------------------------------------------------


def test_get_identity_both_set() -> None:
    """
    @brief      Both ``user.name`` and ``user.email`` set are both returned.
    @return     None
    @exception  AssertionError If either field is missing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/repo", "config", "user.name"): ok_result(stdout="Jane Doe\n"),
            ("git", "-C", "/repo", "config", "user.email"): ok_result(stdout="jane@example.test\n"),
        }
    )

    identity = gitops.get_identity(runner, "/repo")

    assert identity.name == "Jane Doe"
    assert identity.email == "jane@example.test"


def test_get_identity_only_name_set() -> None:
    """
    @brief      Only ``user.name`` set leaves ``email`` as ``None`` (distinct
                from both-set and neither-set outcomes).
    @return     None
    @exception  AssertionError If ``name`` or ``email`` do not match.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/repo", "config", "user.name"): ok_result(stdout="Jane Doe\n"),
            ("git", "-C", "/repo", "config", "user.email"): failing_result(exit_code=1),
        }
    )

    identity = gitops.get_identity(runner, "/repo")

    assert identity.name == "Jane Doe"
    assert identity.email is None


def test_get_identity_neither_set() -> None:
    """
    @brief      Neither key set returns both fields as ``None`` without
                raising.
    @return     None
    @exception  AssertionError If either field is not ``None``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/repo", "config", "user.name"): failing_result(exit_code=1),
            ("git", "-C", "/repo", "config", "user.email"): failing_result(exit_code=1),
        }
    )

    identity = gitops.get_identity(runner, "/repo")

    assert identity.name is None
    assert identity.email is None


# --- set_identity -----------------------------------------------------------


def test_set_identity_repo_local_by_default() -> None:
    """
    @brief      Default ``local=True`` writes ``--local`` config.
    @return     None
    @exception  AssertionError If ``--local`` is absent from the recorded
                commands.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/repo", "config", "--local", "user.name", "Jane Doe"): ok_result(),
            ("git", "-C", "/repo", "config", "--local", "user.email", "jane@example.test"): ok_result(),
        }
    )

    result = gitops.set_identity(runner, "/repo", "Jane Doe", "jane@example.test")

    assert result.ok is True
    assert runner.calls == [
        ("git", "-C", "/repo", "config", "--local", "user.name", "Jane Doe"),
        ("git", "-C", "/repo", "config", "--local", "user.email", "jane@example.test"),
    ]


def test_set_identity_global_when_requested() -> None:
    """
    @brief      ``local=False`` writes explicit ``--global`` config.
    @return     None
    @exception  AssertionError If ``--global`` is absent from the recorded
                commands.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/repo", "config", "--global", "user.name", "Jane Doe"): ok_result(),
            ("git", "-C", "/repo", "config", "--global", "user.email", "jane@example.test"): ok_result(),
        }
    )

    result = gitops.set_identity(runner, "/repo", "Jane Doe", "jane@example.test", local=False)

    assert result.ok is True
    assert runner.calls == [
        ("git", "-C", "/repo", "config", "--global", "user.name", "Jane Doe"),
        ("git", "-C", "/repo", "config", "--global", "user.email", "jane@example.test"),
    ]


# --- status_porcelain --------------------------------------------------------


def test_status_porcelain_empty_tree() -> None:
    """
    @brief      An empty porcelain output means a clean tree -> ``[]``.
    @return     None
    @exception  AssertionError If the result is not an empty list.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({("git", "-C", "/repo", "status", "--porcelain"): ok_result(stdout="")})

    assert gitops.status_porcelain(runner, "/repo") == []


def test_status_porcelain_dirty_tree_with_rename_line() -> None:
    """
    @brief      A multi-line porcelain output (including a rename-format
                line) is returned verbatim, proving the parser does not
                naively split every line's first two characters -- it does
                not touch the status-code prefix at all.
    @return     None
    @exception  AssertionError If any line is altered or dropped.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    porcelain_output = " M modified.txt\n?? untracked.txt\nR  old_name.txt -> new_name.txt\n"
    runner = FakeCommandRunner(
        {("git", "-C", "/repo", "status", "--porcelain"): ok_result(stdout=porcelain_output)}
    )

    lines = gitops.status_porcelain(runner, "/repo")

    assert lines == [
        " M modified.txt",
        "?? untracked.txt",
        "R  old_name.txt -> new_name.txt",
    ]


# --- add_all / commit / create_branch: exact argv regression guards --------


def test_add_all_records_exact_argument_list() -> None:
    """
    @brief      ``add_all`` issues exactly ``git -C <path> add -A``.
    @return     None
    @exception  AssertionError If the recorded argv differs.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({("git", "-C", "/repo", "add", "-A"): ok_result()})

    result = gitops.add_all(runner, "/repo")

    assert result.ok is True
    assert runner.calls == [("git", "-C", "/repo", "add", "-A")]


def test_commit_records_exact_argument_list_with_message_as_single_arg() -> None:
    """
    @brief      ``commit`` issues exactly ``git -C <path> commit -m
                <message>`` with the message as one argv element, never
                shell-concatenated (regression guard against injection).
    @return     None
    @exception  AssertionError If the recorded argv differs or the message
                is split across elements.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    message = "Initial commit; rm -rf / && echo pwned"
    runner = FakeCommandRunner({("git", "-C", "/repo", "commit", "-m", message): ok_result()})

    result = gitops.commit(runner, "/repo", message)

    assert result.ok is True
    assert runner.calls == [("git", "-C", "/repo", "commit", "-m", message)]


def test_commit_failure_returns_ok_false_not_an_exception() -> None:
    """
    @brief      A "nothing to commit" failure returns ``ok=False`` with
                git's message, never raises.
    @return     None
    @exception  AssertionError If ``ok`` is not ``False`` or the call raises.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/repo", "commit", "-m", "empty"): failing_result(
                exit_code=1, stdout="nothing to commit, working tree clean"
            )
        }
    )

    result = gitops.commit(runner, "/repo", "empty")

    assert result.ok is False
    assert "nothing to commit" in result.detail


def test_create_branch_records_exact_argument_list() -> None:
    """
    @brief      ``create_branch`` (default ``checkout=True``) issues exactly
                ``git -C <path> checkout -b <name>``.
    @return     None
    @exception  AssertionError If the recorded argv differs.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({("git", "-C", "/repo", "checkout", "-b", "feature/x"): ok_result()})

    result = gitops.create_branch(runner, "/repo", "feature/x")

    assert result.ok is True
    assert runner.calls == [("git", "-C", "/repo", "checkout", "-b", "feature/x")]


def test_create_branch_without_checkout_uses_branch_command() -> None:
    """
    @brief      ``checkout=False`` issues ``git -C <path> branch <name>``
                instead, without switching.
    @return     None
    @exception  AssertionError If the recorded argv differs.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({("git", "-C", "/repo", "branch", "feature/x"): ok_result()})

    result = gitops.create_branch(runner, "/repo", "feature/x", checkout=False)

    assert result.ok is True
    assert runner.calls == [("git", "-C", "/repo", "branch", "feature/x")]


def test_create_branch_empty_name_raises_value_error() -> None:
    """
    @brief      An empty branch name is a programmer error and raises
                immediately, without invoking the runner.
    @return     None
    @exception  AssertionError If no exception is raised or the runner was
                invoked.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({})

    try:
        gitops.create_branch(runner, "/repo", "")
        raised = False
    except ValueError:
        raised = True

    assert raised is True
    assert runner.calls == []


# --- Windows/POSIX path safety -----------------------------------------------


def test_windows_style_path_argument_construction_is_os_agnostic() -> None:
    """
    @brief      A Windows-style path string (backslashes) is passed through
                to the argv unchanged regardless of the host OS running this
                test -- the module never splits or re-joins path components,
                it only calls ``str(path)``.
    @return     None
    @exception  AssertionError If the recorded argv does not contain the
                Windows-style path verbatim.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    windows_path = r"C:\Users\test\projects\my-repo"
    runner = FakeCommandRunner(
        {
            (
                "git",
                "-C",
                windows_path,
                "rev-parse",
                "--is-inside-work-tree",
            ): ok_result(stdout="true\n")
        }
    )

    assert gitops.is_work_tree(runner, windows_path) is True
    assert runner.calls == [("git", "-C", windows_path, "rev-parse", "--is-inside-work-tree")]


# --- ls_files (T5.1 inventory primitive) --------------------------------------


def test_ls_files_returns_nul_split_tracked_paths() -> None:
    """
    @brief      A successful ``git ls-files -z`` yields the NUL-separated
                tracked paths as a list, trailing NUL dropped.
    @return     None
    @exception  AssertionError If the parsed path list is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {("git", "-C", "/repo", "ls-files", "-z"): ok_result(stdout="src/a.py\0src/b.py\0tests/t.py\0")}
    )

    assert gitops.ls_files(runner, "/repo") == ["src/a.py", "src/b.py", "tests/t.py"]


def test_ls_files_empty_repo_returns_empty_list_not_none() -> None:
    """
    @brief      A tracked-nothing repository returns ``[]`` (distinct from the
                ``None`` "could not list" signal the walk fallback keys on).
    @return     None
    @exception  AssertionError If the result is not an empty list.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({("git", "-C", "/repo", "ls-files", "-z"): ok_result(stdout="")})

    assert gitops.ls_files(runner, "/repo") == []


def test_ls_files_not_a_work_tree_returns_none() -> None:
    """
    @brief      A non-zero exit (not a git work tree) returns ``None``, never
                raises.
    @return     None
    @exception  AssertionError If the result is not ``None``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner(
        {
            ("git", "-C", "/plain", "ls-files", "-z"): failing_result(
                exit_code=128, stderr="fatal: not a git repository"
            )
        }
    )

    assert gitops.ls_files(runner, "/plain") is None


def test_ls_files_git_missing_returns_none() -> None:
    """
    @brief      A missing git executable returns ``None``, never raises.
    @return     None
    @exception  AssertionError If the call raises or returns other than ``None``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    runner = FakeCommandRunner({})

    assert gitops.ls_files(runner, "/anywhere") is None


# END OF FILE
