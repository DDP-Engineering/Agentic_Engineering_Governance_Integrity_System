#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_install_flow.py
@brief Real-payload acceptance tests for shared new/adopt flow.
@details Exercises actual Git repositories and copied AEGIS wrappers offline,
         including dry-run, conflicts, V1 entry, and handled-failure rollback.
"""

import io
import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from waegis.cli import EXIT_ERROR, EXIT_NEEDS_INPUT, EXIT_OK, main
from waegis.install import InstallError, apply_install, plan_install
from waegis.interview import collect_install_answers
from waegis.locate import resolve_payload, source_checkout_payload
from waegis.manifest import load_manifest
from waegis.ownership import Disposition
from waegis.runner import CommandRunner
from waegis.workflow_toml import ALL_STAGES


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", "-C", str(repo), *args), text=True, capture_output=True, check=check)


def _repository(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests" / "test_app.py").write_text("def test_value(): assert True\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "WAEGIS Tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _answers(path: Path, extra: dict[str, object] | None = None) -> Path:
    values: dict[str, object] = {
        "language": "python",
        "source_roots": ["src"],
        "test_roots": ["tests"],
    }
    if extra:
        values.update(extra)
    path.write_text(json.dumps({"answers_version": 2, "answers": values}), encoding="utf-8")
    return path


def _run(arguments: list[str]) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(arguments, stdout=stdout, stderr=stderr)
    return code, json.loads(stdout.getvalue()), stderr.getvalue()


def test_new_real_payload_initializes_without_history_mutation(tmp_path: Path) -> None:
    """@brief R2/D7 new installs AEGIS 3, validates, and leaves commit work to the operator."""
    target = tmp_path / "new-repo"
    answers = _answers(tmp_path / "answers.json")
    code, result, recovery = _run(["new", str(target), "--answers", str(answers), "--non-interactive", "--yes", "--json"])
    assert code == EXIT_OK, result
    assert result["status"] == "ok"
    assert json.loads(recovery)["waegis_recovery"]["kind"] == "delete-created-target"
    manifest = load_manifest(target / ".agentic" / "install-manifest.json")
    assert manifest.payload_version == "3.0.0"
    assert manifest.mode == "new"
    workflow = tomllib.loads((target / ".agentic" / "workflow.toml").read_text(encoding="utf-8"))
    assert workflow["source"]["roots"] == ["src"]
    assert _git(target, "rev-parse", "--verify", "HEAD", check=False).returncode != 0
    assert _git(target, "diff", "--cached").stdout == ""


def test_new_dry_run_and_missing_answers_are_read_only(tmp_path: Path) -> None:
    """@brief R3/R6 dry-run writes nothing and non-interactive missing keys aggregate."""
    target = tmp_path / "new-repo"
    code, result, recovery = _run(["new", str(target), "--non-interactive", "--json"])
    assert code == EXIT_NEEDS_INPUT
    assert set(result["result"]["missing"]) == {"language", "source_roots", "test_roots"}
    assert recovery == ""
    answers = _answers(tmp_path / "answers.json")
    code, result, recovery = _run(["new", str(target), "--answers", str(answers), "--non-interactive", "--dry-run", "--json"])
    assert code == EXIT_OK
    assert result["result"]["dry_run"] is True
    assert result["result"]["plan"]["answers"]["language"] == "python"
    assert result["result"]["plan"]["provenance"]["language"] == "answers file"
    assert recovery == ""
    assert not target.exists()


def test_new_restrictive_policy_validates_through_real_aegis(tmp_path: Path) -> None:
    """@brief R2/R6 every conditional policy maps to AEGIS-valid schema-3 TOML."""
    target = tmp_path / "restricted"
    values: dict[str, object] = {
        "alignment_protected_scope_mode": "enforce",
        "alignment_protected_scope_patterns": ["infra/**"],
        "gate_test_mode": "enforce",
        "gate_test_commands": ["python -m pytest"],
        "secrets_mode": "enforce",
        "secrets_patterns": ["token-[0-9]+"],
        "protected_paths_mode": "enforce",
        "protected_paths_patterns": ["private/**"],
        "protected_paths_operations": ["read", "write"],
        "working_tree_mode": "restricted",
        "working_tree_blocked_patterns": ["dist/**"],
        "write_access_mode": "stage_restricted",
        "write_access_stages": {
            stage: ["src/**"] if stage == "implementation" else [] for stage in ALL_STAGES
        },
        "scope_mode": "enforce",
        "scope_allowed_roots": ["src"],
        "delivery_mode": "enforce",
        "delivery_command_patterns": ["git push"],
        "coverage_mode": "enforce",
        "coverage_roots": ["src"],
        "coverage_exclude": [],
        "baseline_guard_mode": "enforce",
        "minimum_completion_level": "baseline-usable",
        "adoption_source_changes_mode": "blocked",
        "quick_changed_paths_mode": "advise",
        "quick_max_paths": 8,
    }
    answers = _answers(tmp_path / "restricted.json", values)
    code, result, _ = _run(
        ["new", str(target), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    workflow = tomllib.loads((target / ".agentic" / "workflow.toml").read_text(encoding="utf-8"))
    assert workflow["quick"]["changed_paths"]["max_paths"] == 8
    assert workflow["guardrails"]["write_access"]["stages"]["implementation"] == ["src/**"]


def test_adopt_javascript_fixture_uses_evidence_and_real_payload(tmp_path: Path) -> None:
    """@brief R2 adoption succeeds for the second required language fixture."""
    repo = tmp_path / "javascript"
    (repo / "src").mkdir(parents=True)
    (repo / "test").mkdir()
    (repo / "src" / "app.js").write_text("export const value = 1;\n", encoding="utf-8")
    (repo / "test" / "app.test.js").write_text("// test\n", encoding="utf-8")
    (repo / "package.json").write_text(
        '{"scripts":{"test":"node --test","lint":"eslint ."}}\n',
        encoding="utf-8",
    )
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.invalid")
    _git(repo, "config", "user.name", "WAEGIS Tests")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "javascript baseline")
    answers = _answers(
        tmp_path / "javascript.json",
        {"language": "javascript", "source_roots": ["src"], "test_roots": ["test"]},
    )
    code, result, _ = _run(
        ["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    workflow = tomllib.loads((repo / ".agentic" / "workflow.toml").read_text(encoding="utf-8"))
    assert workflow["traceability"]["language"] == "javascript"


def test_adopt_preserves_path_specific_local_conflict_and_git_history(tmp_path: Path) -> None:
    """@brief R1/R4 adoption keeps local bytes and creates no branch, index, or commit change."""
    repo = _repository(tmp_path)
    agents = repo / "AGENTS.md"
    agents.write_text("local instructions\n", encoding="utf-8")
    _git(repo, "add", "AGENTS.md")
    _git(repo, "commit", "-m", "local adapter")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    answers = _answers(tmp_path / "answers.json", {"conflicts": {"AGENTS.md": "keep-local"}})
    code, result, recovery = _run(["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"])
    assert code == EXIT_OK, result
    assert "git-path-recovery" in recovery
    assert agents.read_text(encoding="utf-8") == "local instructions\n"
    manifest = load_manifest(repo / ".agentic" / "install-manifest.json")
    assert manifest.files["AGENTS.md"].disposition is Disposition.KEPT_LOCAL
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == head
    assert _git(repo, "diff", "--cached").stdout == ""


def test_adopt_missing_conflict_and_dirty_tree_refuse_before_writes(tmp_path: Path) -> None:
    """@brief R3/R6 missing path decisions and dirt cannot enter mutation."""
    repo = _repository(tmp_path)
    (repo / "AGENTS.md").write_text("local\n", encoding="utf-8")
    _git(repo, "add", "AGENTS.md")
    _git(repo, "commit", "-m", "local")
    answers = _answers(tmp_path / "answers.json")
    code, result, recovery = _run(["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"])
    assert code == EXIT_NEEDS_INPUT
    assert "conflicts.AGENTS.md" in result["result"]["missing"]
    assert recovery == ""


def test_adopt_rejects_stale_conflict_and_identical_ignored_managed_path(tmp_path: Path) -> None:
    """@brief R3/R6 stale decisions and unmanaged baselines fail before consent."""
    repo = _repository(tmp_path)
    answers = _answers(tmp_path / "stale.json", {"conflicts": {"obsolete.txt": "keep-local"}})
    code, result, recovery = _run(
        ["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--dry-run", "--json"]
    )
    assert code == EXIT_NEEDS_INPUT
    assert result["result"]["missing"] == ["conflicts.obsolete.txt"]
    assert recovery == ""

    (repo / ".gitignore").write_text("AGENTS.md\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore managed destination")
    payload, _, _ = resolve_payload()
    (repo / "AGENTS.md").write_bytes((payload / "AGENTS.md").read_bytes())
    answers = _answers(tmp_path / "clean.json", {"conflicts": {".gitignore": "keep-local"}})
    code, result, recovery = _run(
        ["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--dry-run", "--json"]
    )
    assert code == EXIT_ERROR
    assert "outside the committed baseline" in result["messages"][0]
    assert recovery == ""
    assert not (repo / ".agentic").exists()
    (repo / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    code, result, recovery = _run(["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"])
    assert code == EXIT_ERROR
    assert "not clean" in result["messages"][0]
    assert recovery == ""


def test_v1_entry_requires_explicit_migration_consent(tmp_path: Path) -> None:
    """@brief R1 minimally detects V1 and never trusts its file ownership."""
    repo = _repository(tmp_path)
    manifest = repo / ".agentic" / "install-manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"schema_version": 1, "files": "untrusted"}\n', encoding="utf-8")
    _git(repo, "add", ".agentic/install-manifest.json")
    _git(repo, "commit", "-m", "v1 receipt")
    answers = _answers(tmp_path / "answers.json")
    code, result, _ = _run(["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"])
    assert code == EXIT_NEEDS_INPUT
    assert result["result"]["missing"] == ["migration_v1"]
    answers = _answers(tmp_path / "migration.json", {"migration_v1": True})
    code, result, _ = _run(["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"])
    assert code == EXIT_OK, result
    assert load_manifest(manifest).mode == "adopt"


def test_validation_failure_restores_original_repository(tmp_path: Path) -> None:
    """@brief R3 handled smoke failure executes the exact recovery plan automatically."""
    repo = _repository(tmp_path)
    payload = tmp_path / "payload"
    shutil.copytree(source_checkout_payload(), payload)
    if os.name == "nt":
        (payload / ".agentic" / "tools" / "run.ps1").write_text("exit 19\n", encoding="utf-8")
    else:
        (payload / ".agentic" / "tools" / "run.sh").write_text("#!/bin/sh\nexit 19\n", encoding="utf-8")
    answers = _answers(tmp_path / "answers.json")
    code, result, recovery = _run(
        ["adopt", str(repo), "--payload", str(payload), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_ERROR
    assert "wrapper --help failed" in result["messages"][0]
    assert "git-path-recovery" in recovery
    assert _git(repo, "status", "--porcelain", "--untracked-files=all").stdout == ""
    assert (repo / "src" / "app.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not (repo / ".agentic").exists() or not (repo / ".agentic" / "install-manifest.json").exists()


def test_apply_refuses_changed_head_and_never_deletes_foreign_new_target(tmp_path: Path) -> None:
    """@brief R3 apply pins HEAD and only deletes a directory it actually created."""
    runner = CommandRunner()
    payload, version, inventory = resolve_payload()
    answers, missing = collect_install_answers(
        {"language": "python", "source_roots": ["src"], "test_roots": ["tests"]},
        None,
        None,
        non_interactive=True,
    )
    assert missing == ()

    target = tmp_path / "raced-new"
    new_plan = plan_install("new", target, payload, version, inventory, answers, runner)
    target.mkdir()
    marker = target / "foreign.txt"
    marker.write_text("foreign\n", encoding="utf-8")
    with pytest.raises(InstallError, match="already exists"):
        apply_install(new_plan, runner, io.StringIO(), as_json=False)
    assert marker.read_text(encoding="utf-8") == "foreign\n"

    head_root = tmp_path / "head"
    head_root.mkdir()
    repo = _repository(head_root)
    adopt_plan = plan_install("adopt", repo, payload, version, inventory, answers, runner)
    (repo / "later.txt").write_text("later\n", encoding="utf-8")
    _git(repo, "add", "later.txt")
    _git(repo, "commit", "-m", "changed after planning")
    recovery = io.StringIO()
    with pytest.raises(InstallError, match="HEAD changed after planning"):
        apply_install(adopt_plan, runner, recovery, as_json=False)
    assert recovery.getvalue() == ""
    assert not (repo / ".agentic").exists()


# END OF FILE
