#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file working_tree.py
@brief Working-tree audit helpers for delivery preflight checks.
@details Provides reusable implementation behavior for the standalone AEGIS system.
@details `_git_status` (0.3.0, code-review follow-up) now runs with
         `-c core.quotepath=false` and unquotes any remaining C-style-quoted
         path, so a protected/blocked/secret path pattern can no longer be
         dodged by a non-ASCII filename that Git would otherwise report as an
         escaped, quoted string.
@details `_git_status` (0.5.0, code-review follow-up) only splits an entry on
         `" -> "` when the status code marks a rename or copy (`R`/`C`), so a
         file whose own name contains that sequence is no longer misparsed.
@details The secret scan (2.1.0, lifecycle field test) skips AEGIS's own
         generated run artifacts. `verify run` writes `validation-summary.json`,
         `report.md`, and `graph.json` under `.agentic/runs/<run-id>/`, and each
         one embeds the secrets invariant's name and message verbatim, so a
         configured pattern as ordinary as `(?i)secret` matched the tool's own
         output. AEGIS is the only writer of that tree; it is tool output, not
         authored content.
@details The secret scan (2.1.0, lifecycle field test) also skips the
         `[guardrails.secrets]` table of `.agentic/workflow.toml`. That table
         *is* the pattern list, so `(?i)secret` matches its own table header and
         every configured pattern matches its own declaration: any run that
         edited the config failed the scan, and a freshly deployed repository
         failed it before the first commit, when the whole untracked file is
         read. Only that one table is skipped - the rest of the config, where a
         credential could plausibly be pasted into a gate command, is scanned
         exactly as before.
"""

# IMPORTS

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .config import CONFIG_RELATIVE_PATH, WorkflowConfig
from .paths import matches_pattern

# CONSTANTS

MAX_SECRET_SCAN_BYTES = 1_000_000
GENERATED_RUN_ARTIFACT_ROOT = ".agentic/runs"

# @brief The one configuration table whose content is the secret patterns
#        themselves, and so cannot be scanned with them.
SECRETS_POLICY_TABLE = "guardrails.secrets"
WORKFLOW_CONFIG_PATH = CONFIG_RELATIVE_PATH.as_posix()

# PUBLIC API


def is_generated_run_artifact(path: str) -> bool:
    """
    @brief      Report whether a repository path is AEGIS-generated run output.
    @param[in]  path Repository-relative path in either slash style.
    @return     True when the path lies inside the generated run-artifact tree.
    @details    Shared by the working-tree secret scan and INV-7 so both agree
                on which files are the tool's own output rather than content
                anybody authored.
    @exception  None
    """
    normalized = path.replace("\\", "/").strip("/")
    return (
        normalized == GENERATED_RUN_ARTIFACT_ROOT
        or normalized.startswith(f"{GENERATED_RUN_ARTIFACT_ROOT}/")
    )


def without_secret_policy(path: str, text: str) -> str:
    """
    @brief      Drop the lines that declare the secret patterns themselves.
    @param[in]  path Repository-relative path the text belongs to, in either
                slash style.
    @param[in]  text File content, or unified diff text for that one file.
    @return     `text` unchanged for every path but `.agentic/workflow.toml`,
                and for that file the same text without its
                `[guardrails.secrets]` table.
    @details    Shared by the working-tree secret scan and INV-7 so both agree
                on the scan surface. Only the one table is removed: a
                credential pasted anywhere else in the configuration - into a
                gate command, a delivery command pattern, a protected-path glob
                - is still scanned, and this is the only table whose declared
                content cannot be told apart from what it declares.
    @details    Accepts diff text as well as whole-file text because INV-7
                scans the former and the working-tree audit the latter. A
                leading `+`/`-`/space column is stripped before a line is read
                as a TOML table header, and a hunk or file header resets the
                table to unknown, since the next line may come from anywhere in
                the file. Unknown means scanned: a hunk this cannot place stays
                on the scan surface rather than dropping off it.
    @exception  None
    """
    if path.replace("\\", "/").strip("/") != WORKFLOW_CONFIG_PATH:
        return text
    kept: list[str] = []
    inside = False
    for line in text.splitlines(keepends=True):
        if line.startswith(("@@", "diff --git ")):
            inside = False
            kept.append(line)
            continue
        content = line[1:] if line[:1] in ("+", "-", " ") else line
        stripped = content.strip()
        if stripped.startswith("["):
            inside = stripped.strip("[]").strip() == SECRETS_POLICY_TABLE
        if not inside:
            kept.append(line)
    return "".join(kept)


def audit_working_tree(
    repo_root: Path,
    config: WorkflowConfig,
    graph: Any | None = None,
) -> dict[str, Any]:
    """
    @brief      Audit the working tree against protected/blocked/secret path
                policy and adoption source-change restrictions.
    @param[in]  repo_root Repository root whose Git working tree is audited.
    @param[in]  config Validated workflow configuration providing protected-
                path, working-tree, secrets, and adoption-source policy.
    @param[in]  graph Active workflow graph when delivery preflight needs
                run-kind-specific checks.
    @return     Dict with `entries` (raw Git status entries), `untracked`
                (entries with `??` status), and `blocking_findings` (list of
                code/path/message records).
    @details    An unreadable working tree is a blocking finding, not a pass
                (0.4.0). The audit's whole job is to prove nothing blocking is
                present, and it cannot prove that from a status it never got —
                so a Git that failed or is missing has to fail closed, the same
                way an unavailable guard hook blocks rather than allows.
    @exception  None
    """
    entries, status_error = _git_status(repo_root)
    findings = []
    if status_error:
        findings.append(_finding("git-status-unavailable", "", status_error))
    for entry in entries:
        path = entry["path"]
        entry_paths = _entry_paths(entry)
        blocked_adoption_path = next(
            (
                candidate
                for candidate in entry_paths
                if _is_blocked_adoption_source_change(candidate, config, graph)
            ),
            None,
        )
        if blocked_adoption_path:
            findings.append(
                _finding(
                    "ADOPTION-SOURCE-CHANGE",
                    blocked_adoption_path,
                    "Adoption delivery cannot include application source changes.",
                )
            )
        # Both of these test every path the entry names, not only
        # `entry["path"]`: for a rename or copy that field is the
        # *destination*, so `git mv config/secrets.yaml config/legacy.yaml`
        # moved a protected file out of its protected location without
        # producing a finding. The secret scan below stays on the destination -
        # the source path no longer exists on disk after a rename.
        protected_hit = next(
            (
                candidate
                for candidate in entry_paths
                if _matches_any(candidate, config.protected_paths.patterns)
            ),
            None,
        )
        if (
            config.protected_paths.mode == "enforce"
            and "write" in config.protected_paths.operations
            and protected_hit
        ):
            findings.append(_finding("protected-path", protected_hit, "Protected path is present in the working tree."))
        blocked_hit = next(
            (
                candidate
                for candidate in entry_paths
                if _matches_any(candidate, config.working_tree.blocked_patterns)
            ),
            None,
        )
        if config.working_tree.mode == "restricted" and blocked_hit:
            findings.append(_finding("blocked-pattern", blocked_hit, "Path matches a configured working-tree blocker."))
        secret = (
            None
            if config.secrets.mode == "disabled" or is_generated_run_artifact(path)
            else _secret_match(repo_root / path, path, config.secrets.patterns)
        )
        if secret:
            findings.append(_finding("secret-pattern", path, f"Configured secret pattern matched: {secret}"))
    return {
        "entries": entries,
        "untracked": [entry for entry in entries if entry["status"] == "??"],
        "blocking_findings": findings,
    }


# HELPER FUNCTIONS


def _git_status(repo_root: Path) -> tuple[list[dict[str, str]], str | None]:
    """
    @brief      Read the porcelain working-tree status.
    @param[in]  repo_root Repository root the status is read for.
    @return     Parsed entries, and an error message when the status could not
                be read at all (``None`` on success).
    @details    Both failure modes are reported rather than mistaken for a
                clean tree (0.2.0). Git exiting non-zero — not a repository,
                a broken index, an unreadable object store — writes its
                diagnosis to stderr and leaves stdout empty, which is
                byte-identical to a genuinely clean tree, so the audit used to
                conclude there was nothing to block on. Git being absent
                entirely raised ``FileNotFoundError`` out of the audit, which
                the delivery hook then surfaced as a raw traceback. Neither is
                an answer, so both come back as an error for the caller to turn
                into a blocking finding.
    @exception  None
    """
    try:
        result = subprocess.run(
            # `-c core.quotepath=false` stops Git from C-style-quoting and
            # octal-escaping paths containing non-ASCII bytes (its default
            # `core.quotePath=true` behavior); without it, a file such as
            # `café.txt` is reported as the literal string `"caf\303\251.txt"`,
            # which none of the protected/blocked/secret path patterns below
            # would ever match.
            [
                "git",
                "-c",
                "core.quotepath=false",
                "status",
                "--porcelain=v1",
                "-z",
                "-uall",
            ],
            cwd=repo_root,
            text=True,
            encoding="utf-8",
            errors="strict",
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, UnicodeDecodeError, subprocess.TimeoutExpired) as exc:
        return [], f"Git could not be run to audit the working tree: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else "no diagnostic output"
        return [], f"Git status failed with exit code {result.returncode}: {reason}"
    entries: list[dict[str, str]] = []
    fields = result.stdout.split("\0")
    index = 0
    while index < len(fields):
        field = fields[index]
        index += 1
        if len(field) < 4:
            continue
        status = field[:2]
        entry = {"status": status, "path": field[3:]}
        # In porcelain `-z` mode Git emits a rename/copy destination followed
        # by its source as a second NUL-delimited field. No quoting or ` -> `
        # separator is involved, so either path may contain that literal text.
        if "R" in status or "C" in status:
            if index >= len(fields) or not fields[index]:
                return [], "Git status returned an incomplete rename record"
            entry["previous_path"] = fields[index]
            index += 1
        entries.append(entry)
    return entries, None


def _secret_match(path: Path, relative_path: str, patterns: list[str]) -> str | None:
    """
    @brief      Scan a file's content for a configured secret pattern.
    @param[in]  path Filesystem path of the changed file to scan.
    @param[in]  relative_path Repository-relative form of the same file, used to
                recognize the configuration file that declares the patterns.
    @param[in]  patterns Configured secret-detection regex patterns.
    @return     The first pattern that matched the file's content, or `None`
                when the file is unreadable, too large, or has no match.
    @exception  None
    """
    if not patterns or not path.exists() or not path.is_file():
        return None
    try:
        if path.stat().st_size > MAX_SECRET_SCAN_BYTES:
            return None
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    text = without_secret_policy(relative_path, text)
    for pattern in patterns:
        if re.search(pattern, text):
            return pattern
    return None


def _finding(code: str, path: str, message: str) -> dict[str, str]:
    """
    @brief      Build one blocking-finding record.
    @param[in]  code Short machine-readable finding identifier.
    @param[in]  path Repository-relative path the finding applies to.
    @param[in]  message Human-readable explanation of the finding.
    @return     The `code`/`path`/`message` finding record.
    @exception  None
    """
    return {"code": code, "path": path, "message": message}


def _matches_any(path: str, patterns: list[str]) -> bool:
    """
    @brief      Check whether a path matches any of the given glob patterns.
    @param[in]  path Repo-relative path to test.
    @param[in]  patterns Glob patterns to test against.
    @return     True when at least one pattern matches the path.
    @exception  None
    """
    return any(matches_pattern(path, pattern) for pattern in patterns)


def _is_blocked_adoption_source_change(path: str, config: WorkflowConfig, graph: Any | None) -> bool:
    """
    @brief      Detect source changes that are not allowed during adoption.
    @param[in]  path Repository-relative Git status path.
    @param[in]  config Workflow configuration.
    @param[in]  graph Active workflow graph when available.
    @return     True when an adoption run touches application source.
    @exception  None
    """
    if graph is None or getattr(getattr(graph, "intent", None), "kind", None) != "adoption":
        return False
    if config.adoption_source_changes.mode == "unrestricted":
        return False
    normalized = path.replace("\\", "/").strip("/")
    return any(_path_is_under_root(normalized, root) for root in config.source_roots)


def _entry_paths(entry: dict[str, str]) -> list[str]:
    """
    @brief      Return current and previous Git paths for a status entry.
    @param[in]  entry Git status entry.
    @return     Paths that should be checked for policy findings.
    @exception  None
    """
    paths = [entry["path"]]
    previous_path = entry.get("previous_path")
    if previous_path:
        paths.append(previous_path)
    return paths


def _path_is_under_root(path: str, root: str) -> bool:
    """
    @brief      Check whether a Git status path is at or below a root path.
    @param[in]  path Repository-relative path.
    @param[in]  root Repository-relative root.
    @return     True when the path belongs to the root tree.
    @exception  None
    """
    normalized_root = root.replace("\\", "/").strip("/")
    return path == normalized_root or path.startswith(f"{normalized_root}/")


# END OF FILE
