#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file gitops.py
@brief Git operations over an injectable CommandRunner (task T4.2).
@details Small, typed primitives over :class:`waegis.probes.runner.CommandRunner`
         for the git plumbing steps described in plan §8.1
         (``repo.target-path``, ``repo.init-or-clone``, ``repo.initial-commit``)
         and reused by the adoption branch (T5.2). This module builds the
         steps' primitives; it does not implement the wizard steps themselves.
@details **No CommandRunner extension needed.** Every git subcommand here is
         invoked as ``git -C <path> <subcommand> ...`` -- git's own ``-C``
         flag changes the working directory *for the git process*, so the
         path is just another argv element. The T2.1
         :class:`waegis.probes.runner.CommandRunner` Protocol (``run(argv,
         *, timeout)``) already supports this without any change to its
         signature or to :class:`waegis.probes.runner.SubprocessCommandRunner`;
         no second command-running seam is introduced and no existing
         consumer (``probes/tools.py``, ``probes/machine.py``) is touched.
@details Every function takes the path argument as ``str | os.PathLike[str]``
         and passes it through via ``str(path)`` only -- never split,
         normalized, or reassembled. This keeps argument-list construction
         OS-agnostic: a Windows-style path string (backslashes) built on a
         POSIX test host is not a ``PurePosixPath`` separator and survives
         ``str(Path(...))`` unchanged, so the resulting argv is identical
         regardless of the host OS running the test.
@details Every function returns a small typed result (:class:`GitOpResult` /
         :class:`GitIdentity`) rather than a raw
         :class:`waegis.probes.runner.CommandResult`, so callers never parse
         exit codes themselves. No function raises for an *expected* git
         failure (bad clone URL, commit with nothing staged, unset identity,
         and so on) -- those come back as ``GitOpResult(ok=False, ...)``.
         Raised exceptions are reserved for programmer errors (e.g.
         :func:`create_branch` with an empty branch name). This module never
         prints.
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
@version 0.5.0
"""

# IMPORTS

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from waegis.probes.runner import CommandResult, CommandRunner

# CONSTANTS

# @brief Substrings identifying an older-git "-b not supported" failure on
#        `git init -b <branch>`, matched against the real (lower-cased)
#        stderr rather than a probed git version string.
_INIT_B_UNSUPPORTED_MARKERS: tuple[str, ...] = (
    "unknown option",
    "unknown switch",
    "unrecognized option",
    "error: unknown option `b'",
)

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class GitOpResult:
    """
    @brief Outcome of one git operation performed through a
           :class:`CommandRunner`.
    @details ``detail`` is a short, human-readable explanation: on success it
             may be empty or a confirmation string; on failure it carries
             git's own stderr (or a pre-check message for failures detected
             before git was even invoked, e.g. a non-empty clone target).
             ``raw`` is the underlying :class:`CommandResult` for callers
             that need the exit code or full output.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    ok: bool
    detail: str
    raw: CommandResult


@dataclass(frozen=True)
class GitIdentity:
    """
    @brief Repo-effective git identity (``user.name`` / ``user.email``).
    @details Each field is ``None`` when unset, which lets callers (notably
             ``prereq.git-identity``'s ``detect()``) distinguish three
             states -- both set, one set, neither set -- rather than
             collapsing "identity missing" into a single boolean.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    name: str | None
    email: str | None


# HELPER FUNCTIONS


def _git_c(path: str | os.PathLike[str], *args: str) -> tuple[str, ...]:
    """
    @brief      Build a ``git -C <path> <args...>`` argv tuple.
    @param[in]  path Repository path, passed through as ``str(path)`` only.
    @param[in]  args Remaining git subcommand arguments, in order.
    @return     The full argv tuple starting with ``"git"``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return ("git", "-C", str(path), *args)


def _failure_detail(result: CommandResult, *, not_found_message: str) -> str:
    """
    @brief      Extract a human-readable failure detail from a
                :class:`CommandResult` that did not succeed.
    @param[in]  result The non-ok :class:`CommandResult`.
    @param[in]  not_found_message Detail to use when ``result.found`` is
                ``False`` (git executable itself missing).
    @return     ``not_found_message`` when git was not found; the timeout
                note when the process timed out; otherwise git's own
                combined stdout/stderr, stripped (falling back to a generic
                exit-code note when git produced no output at all).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    if not result.found:
        return not_found_message
    if result.timed_out:
        return "git command timed out"
    output = result.combined_output().strip()
    if output:
        return output
    return f"git exited with code {result.exit_code}"


# PUBLIC API


def is_work_tree(runner: CommandRunner, path: str | os.PathLike[str]) -> bool:
    """
    @brief      Report whether ``path`` is inside a git work tree.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Directory to check.
    @return     ``True`` only when ``git -C <path> rev-parse
                --is-inside-work-tree`` is found, exits zero, and prints
                ``"true"``. Any other outcome (not found, non-zero exit,
                unexpected output) is reported as ``False``, never raised.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "rev-parse", "--is-inside-work-tree"))
    if not result.ok():
        return False
    return result.stdout.strip() == "true"


def init_repo(
    runner: CommandRunner,
    path: str | os.PathLike[str],
    *,
    initial_branch: str = "main",
) -> GitOpResult:
    """
    @brief      Initialize a new git repository at ``path`` with a chosen
                initial branch name (plan §8.1 ``repo.init-or-clone``).
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Directory to initialize (created by git if it does not
                exist).
    @param[in]  initial_branch Branch name for the initial checkout.
    @return     A :class:`GitOpResult`. Tries ``git init -b <initial_branch>
                <path>`` first; when that specific invocation fails with a
                git error naming ``-b``/the option itself as unrecognized
                (older git predating ``-b`` support -- detected from the
                real stderr text, not a probed version), falls back to
                ``git init <path>`` followed by ``git -C <path>
                symbolic-ref HEAD refs/heads/<initial_branch>``. Any other
                failure (permissions, path issues) is surfaced as
                ``ok=False`` with git's stderr in ``detail``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = runner.run(("git", "init", "-b", initial_branch, str(path)))
    if result.ok():
        return GitOpResult(ok=True, detail=result.combined_output().strip(), raw=result)

    stderr_lower = result.stderr.lower()
    b_unsupported = result.found and any(marker in stderr_lower for marker in _INIT_B_UNSUPPORTED_MARKERS)
    if not b_unsupported:
        return GitOpResult(
            ok=False,
            detail=_failure_detail(result, not_found_message="git was not found"),
            raw=result,
        )

    plain_init = runner.run(("git", "init", str(path)))
    if not plain_init.ok():
        return GitOpResult(
            ok=False,
            detail=_failure_detail(plain_init, not_found_message="git was not found"),
            raw=plain_init,
        )
    symbolic_ref = runner.run(_git_c(path, "symbolic-ref", "HEAD", f"refs/heads/{initial_branch}"))
    if not symbolic_ref.ok():
        return GitOpResult(
            ok=False,
            detail=_failure_detail(symbolic_ref, not_found_message="git was not found"),
            raw=symbolic_ref,
        )
    return GitOpResult(
        ok=True,
        detail=f"initialized with fallback branch rename to {initial_branch!r} (git predates 'init -b')",
        raw=symbolic_ref,
    )


def clone_repo(runner: CommandRunner, url: str, path: str | os.PathLike[str]) -> GitOpResult:
    """
    @brief      Clone ``url`` into ``path`` (plan §8.1 ``repo.init-or-clone``).
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  url Remote URL to clone.
    @param[in]  path Target directory.
    @return     A :class:`GitOpResult`. When ``path`` already exists and is a
                non-empty directory, this is detected *before* invoking
                ``runner`` at all (git itself refuses this but with
                inconsistent messages across versions) and reported as
                ``ok=False`` with a uniform detail message. Otherwise runs
                ``git clone <url> <path>``; a clone failure (network, auth,
                bad URL) is reported as ``ok=False`` with git's own stderr
                passed through in ``detail``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    target = Path(path)
    if target.exists() and target.is_dir() and any(target.iterdir()):
        placeholder = CommandResult(found=False, exit_code=None, stdout="", stderr="")
        return GitOpResult(
            ok=False,
            detail=f"target already exists and is not empty: {path}",
            raw=placeholder,
        )

    result = runner.run(("git", "clone", url, str(path)))
    if result.ok():
        return GitOpResult(ok=True, detail=result.combined_output().strip(), raw=result)
    return GitOpResult(
        ok=False,
        detail=_failure_detail(result, not_found_message="git was not found"),
        raw=result,
    )


def get_identity(runner: CommandRunner, path: str | os.PathLike[str]) -> GitIdentity:
    """
    @brief      Read the effective ``user.name``/``user.email`` for ``path``.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @return     A :class:`GitIdentity` whose ``name``/``email`` are each the
                configured value, or ``None`` when that key is unset --
                three distinct outcomes (both set, one set, neither set) are
                representable, which ``prereq.git-identity``'s ``detect()``
                needs. Reads via plain ``git config`` (repo-local falling
                through to global, git's own default resolution), never
                forcing ``--local``. Never raises: an unset key simply
                yields ``None`` for that field.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    name_result = runner.run(_git_c(path, "config", "user.name"))
    email_result = runner.run(_git_c(path, "config", "user.email"))
    name = name_result.stdout.strip() if name_result.ok() and name_result.stdout.strip() else None
    email = email_result.stdout.strip() if email_result.ok() and email_result.stdout.strip() else None
    return GitIdentity(name=name, email=email)


def set_identity(
    runner: CommandRunner,
    path: str | os.PathLike[str],
    name: str,
    email: str,
    *,
    local: bool = True,
) -> GitOpResult:
    """
    @brief      Set ``user.name``/``user.email`` for ``path`` (plan §8.1's
                "repo-local offer" for a fresh new-project repo).
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @param[in]  name Value for ``user.name``.
    @param[in]  email Value for ``user.email``.
    @param[in]  local When ``True`` (the default), writes ``--local`` config
                (this repo only); when ``False``, writes ``--global`` config
                explicitly (never the implicit default -- callers must opt
                in to a global write).
    @return     A :class:`GitOpResult`; ``ok=False`` with git's stderr in
                ``detail`` if either write fails.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    scope_flag = "--local" if local else "--global"
    name_result = runner.run(_git_c(path, "config", scope_flag, "user.name", name))
    if not name_result.ok():
        return GitOpResult(
            ok=False,
            detail=_failure_detail(name_result, not_found_message="git was not found"),
            raw=name_result,
        )
    email_result = runner.run(_git_c(path, "config", scope_flag, "user.email", email))
    if not email_result.ok():
        return GitOpResult(
            ok=False,
            detail=_failure_detail(email_result, not_found_message="git was not found"),
            raw=email_result,
        )
    return GitOpResult(ok=True, detail="", raw=email_result)


def head_commit(runner: CommandRunner, path: str | os.PathLike[str]) -> str | None:
    """
    @brief      Read the commit hash HEAD points at in ``path``, if any.
    @details    Added for T4.3's ``repo.initial-commit`` verify: proving "a
                commit now exists" cannot reuse :func:`status_porcelain`, which
                returns ``[]`` both for a clean tree *and* for a failed git
                invocation, so emptiness alone is not evidence of a commit.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @return     The full hash printed by ``git -C <path> rev-parse HEAD``, or
                ``None`` for any failure (no repository, no commits yet, git
                missing) — never raised, matching this module's convention for
                expected git failures.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "rev-parse", "HEAD"))
    if not result.ok():
        return None
    text = result.stdout.strip()
    return text or None


def status_porcelain(runner: CommandRunner, path: str | os.PathLike[str]) -> list[str]:
    """
    @brief      Read ``git status --porcelain`` for ``path``.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @return     Non-empty output lines exactly as git printed them (including
                rename lines in git's own ``R  old -> new`` shape); an empty
                list means a clean tree. Lines are returned verbatim rather
                than parsed into per-field records: every current caller
                (``repo.initial-commit``'s ``verify()``) only needs
                emptiness or a raw line to report, so a per-status-code
                parser would be speculative machinery this task does not
                need -- documented here rather than silently assumed.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "status", "--porcelain"))
    if not result.ok():
        return []
    return [line for line in result.stdout.split("\n") if line]


def current_branch(runner: CommandRunner, path: str | os.PathLike[str]) -> str | None:
    """
    @brief      Read the name of the branch currently checked out in ``path``
                (task T5.2's ``repo.validate-existing``/``repo.adoption-commit``).
    @details    Runs ``git -C <path> rev-parse --abbrev-ref HEAD``. A normal
                branch checkout prints the branch name; a detached HEAD prints
                the literal ``"HEAD"``, which is returned verbatim so callers
                can tell a real branch from a detached state. Any expected
                failure (git missing, ``path`` not a work tree, a repository
                with no commits yet) yields ``None`` rather than raising,
                matching this module's convention.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @return     The current branch name, ``"HEAD"`` when detached, or ``None``
                for any expected failure.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "rev-parse", "--abbrev-ref", "HEAD"))
    if not result.ok():
        return None
    text = result.stdout.strip()
    return text or None


def ls_files(runner: CommandRunner, path: str | os.PathLike[str]) -> list[str] | None:
    """
    @brief      List the files git tracks in ``path`` (task T5.1's inventory
                primitive, plan §9).
    @details    Runs ``git -C <path> ls-files -z``: NUL-separated output avoids
                git's C-style quoting of non-ASCII path names, so entries are
                usable verbatim. Paths are repo-relative with forward slashes,
                exactly as git prints them.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @return     The tracked file list (possibly empty for a fresh repository
                with nothing added yet), or ``None`` for any expected failure
                (git missing, ``path`` not a work tree) — never raised,
                matching this module's convention. ``None`` versus ``[]``
                distinguishes "could not list" from "listed, nothing tracked",
                which the T5.1 inventory needs to decide whether to fall back
                to a filesystem walk.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-14
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "ls-files", "-z"))
    if not result.ok():
        return None
    return [entry for entry in result.stdout.split("\0") if entry]


def add_all(runner: CommandRunner, path: str | os.PathLike[str]) -> GitOpResult:
    """
    @brief      Stage all changes (including deletions) in ``path``.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @return     A :class:`GitOpResult` for ``git -C <path> add -A``. ``-A``
                (rather than ``add .``) is used because callers beyond a
                fresh payload copy -- notably adoption's conflict flow,
                which may leave ``.new`` sidecar files the caller decides
                whether to stage -- also route through this same function;
                it stages whatever the working tree currently holds and
                makes no policy decision about what "should" be staged.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "add", "-A"))
    if result.ok():
        return GitOpResult(ok=True, detail="", raw=result)
    return GitOpResult(
        ok=False,
        detail=_failure_detail(result, not_found_message="git was not found"),
        raw=result,
    )


def commit(runner: CommandRunner, path: str | os.PathLike[str], message: str) -> GitOpResult:
    """
    @brief      Commit staged changes in ``path``.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @param[in]  message Commit message, passed as a single argv element
                (never string-concatenated into a shell command --
                :class:`waegis.probes.runner.SubprocessCommandRunner` always
                invokes ``subprocess.run`` with an argument list, never
                ``shell=True``, and this function follows that same
                pattern).
    @return     A :class:`GitOpResult`; a failure (e.g. nothing staged)
                comes back as ``ok=False`` with git's own message in
                ``detail``, never as a raised exception.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    result = runner.run(_git_c(path, "commit", "-m", message))
    if result.ok():
        return GitOpResult(ok=True, detail=result.combined_output().strip(), raw=result)
    return GitOpResult(
        ok=False,
        detail=_failure_detail(result, not_found_message="git was not found"),
        raw=result,
    )


def create_branch(
    runner: CommandRunner,
    path: str | os.PathLike[str],
    name: str,
    *,
    checkout: bool = True,
) -> GitOpResult:
    """
    @brief      Create a branch in ``path``.
    @param[in]  runner Injectable :class:`CommandRunner`.
    @param[in]  path Repository path.
    @param[in]  name Branch name; must be non-empty.
    @param[in]  checkout When ``True`` (the default), creates and switches to
                the branch via ``git checkout -b <name>`` (the more
                universally-supported form across this plan's supported git
                versions, preferred over ``switch -c``); when ``False``,
                creates the branch without switching via ``git branch
                <name>``.
    @return     A :class:`GitOpResult`; git failures (e.g. branch already
                exists) come back as ``ok=False`` with git's message in
                ``detail``.
    @exception  ValueError If ``name`` is empty -- a programmer error, not an
                expected git failure.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    if not name:
        raise ValueError("create_branch requires a non-empty branch name")

    if checkout:
        result = runner.run(_git_c(path, "checkout", "-b", name))
    else:
        result = runner.run(_git_c(path, "branch", name))
    if result.ok():
        return GitOpResult(ok=True, detail=result.combined_output().strip(), raw=result)
    return GitOpResult(
        ok=False,
        detail=_failure_detail(result, not_found_message="git was not found"),
        raw=result,
    )


# END OF FILE
