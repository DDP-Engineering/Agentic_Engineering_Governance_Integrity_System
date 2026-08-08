#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_check_configure_repair.py
@brief Real-payload Phase 3 health and narrow-maintenance acceptance.
@details Proves read-only 0/1/2 checks, comment-preserving configuration, and
         managed-only repair against committed disposable repositories.
"""

import hashlib
import io
import json
import subprocess
import tomllib
from pathlib import Path

from waegis.cli import EXIT_ERROR, EXIT_OK, EXIT_WARNING, main
from waegis.check import CheckResult, Finding, check_repository
from waegis.envelope import ResultEnvelope
from waegis.manifest import load_manifest
from waegis.runner import CommandResult, CommandRunner


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


def _answers(path: Path, values: dict[str, object]) -> Path:
    path.write_text(json.dumps({"answers_version": 2, "answers": values}), encoding="utf-8")
    return path


def _run(arguments: list[str]) -> tuple[int, dict[str, object], str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(arguments, stdout=stdout, stderr=stderr)
    return code, json.loads(stdout.getvalue()), stderr.getvalue()


def _install(repo: Path, tmp_path: Path) -> None:
    answers = _answers(
        tmp_path / "install.json",
        {"language": "python", "source_roots": ["src"], "test_roots": ["tests"]},
    )
    code, result, _ = _run(
        ["adopt", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def _tree(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in repo.rglob("*") if item.is_file() and ".git" not in item.parts):
        result[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def test_check_json_contract_matches_golden_fixture() -> None:
    """@brief R7 pins the V2-owned health-result schema and stable names."""
    result = CheckResult(
        Path("."),
        "valid",
        "3.0.0",
        "3.1.0",
        {"managed": 2},
        (Finding("UPDATE-AVAILABLE", "warning", "new payload", None, "review upgrade"),),
    ).to_dict()
    result["repository"] = "<repo>"
    rendered = ResultEnvelope("check", "warning", 1, result=result).render()
    fixture = Path(__file__).parent / "fixtures" / "check-result-v2.json"
    assert rendered == fixture.read_text(encoding="utf-8")


def test_check_and_doctor_are_idempotent_with_zero_one_two_results(tmp_path: Path) -> None:
    """@brief R7 check is read-only and maps healthy/warning/failure deterministically."""
    repo = _repository(tmp_path)
    _install(repo, tmp_path)
    before = _tree(repo)
    code, healthy, _ = _run(["check", "--repo", str(repo), "--json"])
    assert code == EXIT_OK, healthy
    assert healthy["result"]["manifest_status"] == "valid"
    code, doctor, _ = _run(["doctor", "--repo", str(repo), "--json"])
    assert code == EXIT_OK
    assert doctor["result"] == healthy["result"]
    assert _tree(repo) == before
    code, analysis, _ = _run(["analyze", "--repo", str(repo), "--json"])
    assert code == EXIT_OK
    assert analysis["result"]["installation"]["status"] == "valid"

    class NoNodeRunner:
        def run(self, args, **kwargs):  # type: ignore[no-untyped-def]
            if args[0] == "node":
                return CommandResult(tuple(args), 1, "", "not found")
            return CommandRunner().run(args, **kwargs)

    no_node = check_repository(repo, NoNodeRunner())
    assert no_node.exit_code == EXIT_WARNING
    assert any(item.code == "NODE-MISSING" for item in no_node.findings)

    changelog = repo / "CHANGELOG.md"
    changelog.write_text("project change\n", encoding="utf-8")
    code, warning, _ = _run(["check", "--repo", str(repo), "--json"])
    assert code == EXIT_WARNING
    assert any(item["code"] == "PROJECT-OWNED-DRIFT" for item in warning["result"]["findings"])

    codex = repo / ".codex" / "hooks.json"
    original_codex = codex.read_text(encoding="utf-8")
    invalid_codex = json.loads(original_codex)
    invalid_codex["unknown"] = True
    codex.write_text(json.dumps(invalid_codex), encoding="utf-8")
    code, invalid, _ = _run(["check", "--repo", str(repo), "--json"])
    assert code == EXIT_ERROR
    assert any(item["code"] == "CODEX-HOOKS-INVALID" for item in invalid["result"]["findings"])
    codex.write_text(original_codex, encoding="utf-8")

    (repo / ".agentic" / "hooks" / "guard_read_path.py").unlink()
    code, failed, _ = _run(["check", "--repo", str(repo), "--json"])
    assert code == EXIT_ERROR
    assert any(item["code"] in {"MANAGED-DRIFT", "HOOK-MISSING"} for item in failed["result"]["findings"])


def test_check_reports_v1_as_unsupported_readoption_input(tmp_path: Path) -> None:
    """@brief R1/R7 V1 detection supplies the exact re-adoption next action."""
    repo = _repository(tmp_path)
    manifest = repo / ".agentic" / "install-manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"schema_version":1}\n', encoding="utf-8")
    code, result, _ = _run(["check", "--repo", str(repo), "--json"])
    assert code == EXIT_ERROR
    assert result["result"]["manifest_status"] == "v1"
    assert "migration consent" in result["result"]["findings"][0]["action"]


def test_configure_preserves_advanced_bytes_and_adds_then_removes_quick_policy(tmp_path: Path) -> None:
    """@brief R2/R5 configure changes owned fields while preserving advanced content."""
    repo = _repository(tmp_path)
    _install(repo, tmp_path)
    workflow = repo / ".agentic" / "workflow.toml"
    text = workflow.read_text(encoding="utf-8")
    text = text.replace(
        '[gates.test]\nmode = "disabled"\ncommands = []',
        '[gates.test]\n# operator advanced comment\nmode = "disabled"\ncommands = []\n'
        'timeout = 2400\nimpacted_command = ["python", "-m", "pytest", "-q"]',
    )
    workflow.write_text(text, encoding="utf-8")
    _commit(repo, "installed with advanced configuration")
    answers = _answers(
        tmp_path / "configure.json",
        {"source_roots": ["src", "lib"], "quick_changed_paths_mode": "advise", "quick_max_paths": 6},
    )
    before = _tree(repo)
    code, dry_run, recovery = _run(
        [
            "configure",
            "--repo",
            str(repo),
            "--answers",
            str(answers),
            "--non-interactive",
            "--dry-run",
            "--json",
        ]
    )
    assert code == EXIT_OK, dry_run
    assert recovery == ""
    assert _tree(repo) == before

    code, result, recovery = _run(
        ["configure", "--repo", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    assert "git-path-recovery" in recovery
    updated = workflow.read_text(encoding="utf-8")
    assert "# operator advanced comment" in updated
    assert "timeout = 2400" in updated
    assert 'impacted_command = ["python", "-m", "pytest", "-q"]' in updated
    parsed = tomllib.loads(updated)
    assert parsed["source"]["roots"] == ["src", "lib"]
    assert parsed["quick"]["changed_paths"]["max_paths"] == 6
    _commit(repo, "configure quick advice")

    disable = _answers(tmp_path / "disable.json", {"quick_changed_paths_mode": "disabled"})
    code, result, _ = _run(
        ["configure", "--repo", str(repo), "--answers", str(disable), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    assert "quick" not in tomllib.loads(workflow.read_text(encoding="utf-8"))


def test_repair_restores_only_managed_files_and_routes_generated_drift(tmp_path: Path) -> None:
    """@brief R4 repair restores managed bytes and leaves seeded project data untouched."""
    repo = _repository(tmp_path)
    _install(repo, tmp_path)
    _commit(repo, "install AEGIS")
    hook = repo / ".agentic" / "hooks" / "guard_read_path.py"
    expected = hook.read_bytes()
    hook.unlink()
    changelog = repo / "CHANGELOG.md"
    changelog.write_text("project-owned sentinel\n", encoding="utf-8")
    _commit(repo, "committed managed and project drift")
    code, result, recovery = _run(
        ["repair", "--repo", str(repo), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_WARNING, result
    assert "git-path-recovery" in recovery
    assert hook.read_bytes() == expected
    assert changelog.read_text(encoding="utf-8") == "project-owned sentinel\n"
    assert all("CHANGELOG.md" != path for path in result["result"]["changed"])
    assert load_manifest(repo / ".agentic" / "install-manifest.json").mode == "repair"
    _commit(repo, "repair managed file")

    (repo / ".agentic" / "workflow.toml").unlink()
    _commit(repo, "remove generated workflow")
    code, result, recovery = _run(
        ["repair", "--repo", str(repo), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_ERROR
    assert "configure" in result["messages"][0]
    assert recovery == ""

    answers = _answers(
        tmp_path / "reconstruct.json",
        {"language": "python", "source_roots": ["src"], "test_roots": ["tests"]},
    )
    code, result, recovery = _run(
        ["configure", "--repo", str(repo), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    assert result["result"]["reconstructed"] is True
    assert "git-path-recovery" in recovery
    assert (repo / ".agentic" / "workflow.toml").is_file()


# END OF FILE
