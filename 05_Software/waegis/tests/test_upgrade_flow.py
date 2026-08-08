#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_upgrade_flow.py
@brief Real-payload ownership-aware upgrade acceptance.
@details Covers replacements/removals/additions, all conflict decisions,
         generated/seeded preservation, dry-run identity, and refusal inputs.
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from waegis.cli import EXIT_ERROR, EXIT_NEEDS_INPUT, EXIT_OK, main
from waegis.locate import source_checkout_payload
from waegis.manifest import load_manifest
from waegis.ownership import Disposition
from waegis.publication import apply_publication
from waegis.runner import CommandRunner
from waegis.upgrade import plan_upgrade


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


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def _tree(repo: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(item for item in repo.rglob("*") if item.is_file() and ".git" not in item.parts):
        result[path.relative_to(repo).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _payload(tmp_path: Path, version: str = "3.1.0") -> Path:
    payload = tmp_path / f"payload-{version}"
    shutil.copytree(source_checkout_payload(), payload)
    pyproject = payload / ".agentic" / "cli" / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8").replace('version = "3.0.0"', f'version = "{version}"', 1),
        encoding="utf-8",
    )
    init = payload / ".agentic" / "cli" / "src" / "aegis" / "__init__.py"
    init.write_text(
        init.read_text(encoding="utf-8").replace('__version__ = "3.0.0"', f'__version__ = "{version}"', 1),
        encoding="utf-8",
    )
    return payload


def test_upgrade_three_way_preserves_project_state_and_git_history(tmp_path: Path) -> None:
    """@brief R4/D7 upgrade applies exact managed actions without history automation."""
    repo = _repository(tmp_path)
    install = _answers(tmp_path / "install.json")
    code, result, _ = _run(
        ["adopt", str(repo), "--answers", str(install), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    _commit(repo, "install AEGIS 3.0")
    payload = _payload(tmp_path)

    replace_path = ".agentic/hooks/guard_read_path.py"
    remove_path = ".agentic/hooks/README.md"
    keep_path = ".agentic/hooks/guard_write_zone.py"
    take_path = ".agentic/hooks/secret_scan.py"
    add_path = ".agentic/hooks/new_guard.py"
    (payload / replace_path).write_text((payload / replace_path).read_text(encoding="utf-8") + "# payload replacement\n", encoding="utf-8")
    (payload / remove_path).unlink()
    (payload / keep_path).write_text((payload / keep_path).read_text(encoding="utf-8") + "# payload conflict\n", encoding="utf-8")
    (payload / take_path).write_text((payload / take_path).read_text(encoding="utf-8") + "# payload wins\n", encoding="utf-8")
    (payload / add_path).write_text("# payload addition\n", encoding="utf-8")
    (payload / ".agentic" / "workflow.toml").write_text(
        (payload / ".agentic" / "workflow.toml").read_text(encoding="utf-8") + "# upstream workflow change\n",
        encoding="utf-8",
    )

    (repo / keep_path).write_text((repo / keep_path).read_text(encoding="utf-8") + "# local keep sentinel\n", encoding="utf-8")
    (repo / take_path).write_text((repo / take_path).read_text(encoding="utf-8") + "# local lose sentinel\n", encoding="utf-8")
    (repo / add_path).write_text("# local addition sentinel\n", encoding="utf-8")
    workflow = repo / ".agentic" / "workflow.toml"
    workflow.write_text(workflow.read_text(encoding="utf-8") + "# local generated sentinel\n", encoding="utf-8")
    (repo / "CHANGELOG.md").write_text("project-owned changelog sentinel\n", encoding="utf-8")
    _commit(repo, "committed local upgrade state")
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    answers = _answers(
        tmp_path / "upgrade.json",
        {
            "conflicts": {
                keep_path: "keep-local",
                take_path: "take-payload",
                add_path: "sidecar",
            }
        },
    )

    missing = _answers(tmp_path / "missing.json")
    code, needed, recovery = _run(
        ["upgrade", "--repo", str(repo), "--payload", str(payload), "--answers", str(missing), "--non-interactive", "--dry-run", "--json"]
    )
    assert code == EXIT_NEEDS_INPUT
    assert set(needed["result"]["missing"]) == {
        f"conflicts.{keep_path}",
        f"conflicts.{take_path}",
        f"conflicts.{add_path}",
    }
    assert recovery == ""

    before = _tree(repo)
    code, dry_run, recovery = _run(
        ["upgrade", "--repo", str(repo), "--payload", str(payload), "--answers", str(answers), "--non-interactive", "--dry-run", "--json"]
    )
    assert code == EXIT_OK, dry_run
    assert recovery == ""
    assert _tree(repo) == before
    code, upgraded, recovery = _run(
        ["upgrade", "--repo", str(repo), "--payload", str(payload), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, upgraded
    assert "git-path-recovery" in recovery
    assert "# payload replacement" in (repo / replace_path).read_text(encoding="utf-8")
    assert not (repo / remove_path).exists()
    assert "# local keep sentinel" in (repo / keep_path).read_text(encoding="utf-8")
    assert "# payload wins" in (repo / take_path).read_text(encoding="utf-8")
    assert "# local lose sentinel" not in (repo / take_path).read_text(encoding="utf-8")
    assert (repo / add_path).read_text(encoding="utf-8") == "# local addition sentinel\n"
    sidecar = repo / f"{add_path}.waegis-3.0.0.new"
    assert sidecar.read_text(encoding="utf-8") == "# payload addition\n"
    assert "# local generated sentinel" in workflow.read_text(encoding="utf-8")
    assert "# upstream workflow change" not in workflow.read_text(encoding="utf-8")
    assert (repo / "CHANGELOG.md").read_text(encoding="utf-8") == "project-owned changelog sentinel\n"
    manifest = load_manifest(repo / ".agentic" / "install-manifest.json")
    assert manifest.payload_version == "3.1.0"
    assert manifest.mode == "upgrade"
    assert manifest.files[keep_path].disposition is Disposition.KEPT_LOCAL
    assert manifest.files[add_path].disposition is Disposition.KEPT_LOCAL
    assert manifest.files[sidecar.relative_to(repo).as_posix()].disposition is Disposition.SIDECAR
    assert _git(repo, "rev-parse", "HEAD").stdout.strip() == head
    assert _git(repo, "diff", "--cached").stdout == ""


def test_upgrade_refuses_manifest_and_version_boundaries_before_mutation(tmp_path: Path) -> None:
    """@brief R1/R2 invalid entry states and cross-major payloads fail before recovery output."""
    repo = _repository(tmp_path)
    payload = _payload(tmp_path, "4.0.0")
    answers = _answers(tmp_path / "answers.json")
    code, result, recovery = _run(
        ["upgrade", "--repo", str(repo), "--payload", str(payload), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_ERROR
    assert "manifest" in result["messages"][0]
    assert recovery == ""
    manifest = repo / ".agentic" / "install-manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"schema_version":1}\n', encoding="utf-8")
    _commit(repo, "v1 manifest")
    code, result, recovery = _run(
        ["upgrade", "--repo", str(repo), "--payload", str(payload), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_ERROR
    assert "unsupported" in result["messages"][0]
    assert recovery == ""

    other_root = tmp_path / "other"
    other_root.mkdir()
    installed = _repository(other_root)
    install_answers = _answers(other_root / "install.json")
    code, result, _ = _run(
        ["adopt", str(installed), "--answers", str(install_answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    _commit(installed, "install compatible baseline")
    code, result, recovery = _run(
        ["upgrade", "--repo", str(installed), "--payload", str(payload), "--answers", str(answers), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_ERROR
    assert "outside >=3.0.0,<4.0.0" in result["messages"][0]
    assert recovery == ""


def test_hard_kill_uses_preemitted_recovery_and_immediate_rerun(tmp_path: Path) -> None:
    """@brief R3 hard kill before manifest publication restores exactly and reruns."""
    repo = _repository(tmp_path)
    install = _answers(tmp_path / "install.json")
    code, result, _ = _run(
        ["adopt", str(repo), "--answers", str(install), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    _commit(repo, "install AEGIS 3.0")
    payload = _payload(tmp_path)
    signal = tmp_path / "validation-started"
    if os.name == "nt":
        wrapper = payload / ".agentic" / "tools" / "run.ps1"
        text = wrapper.read_text(encoding="utf-8")
        text = text.replace(
            '$ErrorActionPreference = "Stop"',
            '$ErrorActionPreference = "Stop"\n'
            'if (-not [string]::IsNullOrWhiteSpace($env:WAEGIS_TEST_SIGNAL)) {\n'
            '    Set-Content -LiteralPath $env:WAEGIS_TEST_SIGNAL -Value "ready"\n'
            '    Start-Sleep -Seconds 5\n'
            '}',
            1,
        )
    else:
        wrapper = payload / ".agentic" / "tools" / "run.sh"
        text = wrapper.read_text(encoding="utf-8")
        text = text.replace(
            "set -eu",
            'set -eu\nif [ -n "${WAEGIS_TEST_SIGNAL:-}" ]; then\n'
            '  printf ready > "$WAEGIS_TEST_SIGNAL"\n'
            '  sleep 5\n'
            "fi",
            1,
        )
    wrapper.write_text(text, encoding="utf-8")
    before = _tree(repo)
    package_root = Path(__file__).parents[1]
    environment = os.environ.copy()
    environment["WAEGIS_TEST_SIGNAL"] = str(signal)
    environment["PYTHONPATH"] = str(package_root / "src")
    python = str(Path(getattr(sys, "_base_executable", sys.executable)))
    process = subprocess.Popen(
        (
            python,
            "-m",
            "waegis",
            "upgrade",
            "--repo",
            str(repo),
            "--payload",
            str(payload),
            "--answers",
            str(install),
            "--non-interactive",
            "--yes",
            "--json",
        ),
        cwd=package_root,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 20
    while not signal.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.05)
    assert signal.exists(), process.communicate(timeout=10)
    process.kill()
    _, stderr = process.communicate(timeout=15)
    recovery = json.loads(stderr.splitlines()[0])["waegis_recovery"]
    assert recovery["commands"]
    for command in recovery["commands"]:
        completed = subprocess.run(command, cwd=repo, shell=True, text=True, capture_output=True)
        assert completed.returncode == 0, completed.stderr
    assert _tree(repo) == before
    assert _git(repo, "status", "--porcelain", "--untracked-files=all").stdout == ""
    code, result, rerun_recovery = _run(
        [
            "upgrade",
            "--repo",
            str(repo),
            "--payload",
            str(payload),
            "--answers",
            str(install),
            "--non-interactive",
            "--yes",
            "--break-lock",
            "--json",
        ]
    )
    assert code == EXIT_OK, result
    assert "git-path-recovery" in rerun_recovery
    assert load_manifest(repo / ".agentic" / "install-manifest.json").payload_version == "3.1.0"


def test_keyboard_interrupt_rolls_back_automatically(tmp_path: Path) -> None:
    """@brief R3 handled interruption restores the original committed tree."""
    repo = _repository(tmp_path)
    install = _answers(tmp_path / "install.json")
    code, result, _ = _run(
        ["adopt", str(repo), "--answers", str(install), "--non-interactive", "--yes", "--json"]
    )
    assert code == EXIT_OK, result
    _commit(repo, "install AEGIS 3.0")
    payload = _payload(tmp_path)
    runner = CommandRunner()
    plan = plan_upgrade(repo, payload, {}, runner)
    before = _tree(repo)

    class InterruptingRunner:
        def run(self, args, **kwargs):  # type: ignore[no-untyped-def]
            if args[0] != "git" and "--help" in args:
                raise KeyboardInterrupt
            return runner.run(args, **kwargs)

    with pytest.raises(KeyboardInterrupt):
        apply_publication(plan.publication, InterruptingRunner(), io.StringIO(), as_json=False)
    assert _tree(repo) == before
    assert _git(repo, "status", "--porcelain", "--untracked-files=all").stdout == ""
    rerun = plan_upgrade(repo, payload, {}, runner)
    apply_publication(rerun.publication, runner, io.StringIO(), as_json=False)
    assert load_manifest(repo / ".agentic" / "install-manifest.json").payload_version == "3.1.0"


# END OF FILE
