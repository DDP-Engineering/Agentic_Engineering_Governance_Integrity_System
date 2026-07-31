#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repowise.py
@brief Contract tests for optional offline RepoWise configuration and indexing.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import waegis.repowise as repowise_module
from waegis.cli import build_parser
from waegis.commands.repair import run_repair
from waegis.commands.repowise import run_repowise_sync
from waegis.io.envelope import EXIT_OPERATIONAL
from waegis.payload.copier import copy_payload
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import hash_file, read_manifest
from waegis.probes.runner import SubprocessCommandRunner
from waegis.repowise import (
    ARTIFACT_PATH,
    INTEGRATION_RELATIVE_PATH,
    RECEIPT_PATH,
    RUNTIME_PATH,
    STATE_PATH,
    RepoWiseError,
    RepoWiseSettings,
    commit_repowise_configuration,
    configure_repowise,
    lifecycle_repowise,
    repowise_status,
    settings_from_answers,
    sync_repowise,
)


# LOCAL HELPERS


def _write_fake_repowise(
    path: Path,
    *,
    version: str = "0.37.0",
    failure_status: int = 0,
) -> None:
    """
    @brief Write a deterministic fake with Click-compatible Windows expansion.
    @details The fake expands matching standalone wildcard tokens on Windows,
             matching Click's pre-parser, and writes the project-local setup
             files that managed WAEGIS execution must restore.
    """
    path.write_text(
        (
            "import glob, json, os, pathlib, sys\n"
            f"VERSION = {version!r}\n"
            f"FAILURE_STATUS = {failure_status!r}\n"
            "if os.name == 'nt':\n"
            "    expanded = []\n"
            "    for argument in sys.argv[1:]:\n"
            "        matches = (\n"
            "            glob.glob(argument, recursive=True)\n"
            "            if '*' in argument or '?' in argument\n"
            "            else []\n"
            "        )\n"
            "        expanded.extend(matches or [argument])\n"
            "    sys.argv[1:] = expanded\n"
            "if '--version' in sys.argv:\n"
            "    print('repowise ' + VERSION)\n"
            "    raise SystemExit(0)\n"
            "if '--help' in sys.argv:\n"
            "    if 'init' in sys.argv:\n"
            "        print('--resume --no-prose --embedder --progress "
            "--no-editor-setup --no-claude-md --no-agents --no-codex "
            "--no-distill-hook')\n"
            "    else:\n"
            "        print('--progress --index-only --no-agents')\n"
            "    raise SystemExit(0)\n"
            "repo = pathlib.Path(sys.argv[2]).resolve()\n"
            "(repo / '.repowise-invocation.json').write_text(\n"
            "    json.dumps(sys.argv[1:]), encoding='utf-8'\n"
            ")\n"
            "(repo / '.mcp.json').write_text('repowise setup', encoding='utf-8')\n"
            "vscode = repo / '.vscode'\n"
            "vscode.mkdir(parents=True, exist_ok=True)\n"
            "(vscode / 'mcp.json').write_text('repowise setup', encoding='utf-8')\n"
            "(vscode / 'extensions.json').write_text(\n"
            "    'repowise setup', encoding='utf-8'\n"
            ")\n"
            "if FAILURE_STATUS:\n"
            "    print('intentional RepoWise failure')\n"
            "    raise SystemExit(FAILURE_STATUS)\n"
            "root = repo / '.repowise'\n"
            "root.mkdir(parents=True, exist_ok=True)\n"
            "(root / 'knowledge-graph.json').write_text(json.dumps({\n"
            "    'version': '1.0.0',\n"
            "    'schema_version': 1,\n"
            "    'project': {'name': repo.name},\n"
            "    'nodes': [{'id': 'file:src/app.py', "
            "'filePath': 'src/app.py', 'tags': ['entry_point']}],\n"
            "    'edges': [],\n"
            "    'layers': [],\n"
            "}), encoding='utf-8')\n"
            "head = __import__('subprocess').check_output("
            "['git', '-C', str(repo), 'rev-parse', 'HEAD'], "
            "text=True).strip()\n"
            "(root / 'state.json').write_text("
            "json.dumps({'last_sync_commit': head}), encoding='utf-8')\n"
            "print(json.dumps({'event': 'done', 'files': 1, 'nodes': 1}))\n"
        ),
        encoding="utf-8",
    )


def _write_bundle(root: Path) -> dict[str, object]:
    """@brief Write one minimal valid native Complete sidecar fixture."""
    root.mkdir(parents=True, exist_ok=True)
    launcher_name = (
        "repowise.cmd"
        if repowise_module.runtime_platform() == "windows-x64"
        else "repowise"
    )
    (root / launcher_name).write_text("launcher\n", encoding="utf-8")
    source = root / "repowise-0.37.0-source.zip"
    source.write_bytes(b"exact-source")
    files = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
        }
        for path in sorted(root.iterdir())
        if path.is_file() and path.name != repowise_module.BUNDLE_MANIFEST
    ]
    tree, unpacked = repowise_module._tree_digest(root)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "edition": "complete",
        "repowise_version": "0.37.0",
        "platform": repowise_module.runtime_platform(),
        "launcher": launcher_name,
        "source": {
            "tag": "v0.37.0",
            "commit": "a" * 40,
            "archive": source.name,
        },
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "tree_sha256": tree,
        "packaged_size": max(1, unpacked // 2),
        "unpacked_size": unpacked,
        "files": files,
    }
    (root / repowise_module.BUNDLE_MANIFEST).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    return manifest


def _external_settings(script: Path) -> RepoWiseSettings:
    """@brief Build deterministic external settings for one fake command."""
    return RepoWiseSettings(
        source="external",
        external_command=(sys.executable, str(script)),
        profile="deterministic",
        enforcement="advisory",
    )


def _git_init(repo: Path) -> None:
    """@brief Create a local Git repository with deterministic identity and HEAD."""
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)


# TESTS


def test_settings_reject_remote_ollama_and_unconfigured_external() -> None:
    """@brief Remote model endpoints and incomplete external sources fail closed."""
    with pytest.raises(RepoWiseError, match="loopback"):
        settings_from_answers(
            {
                "repowise_source": "bundled",
                "repowise_profile": "ollama",
                "repowise_ollama_url": "https://models.example.com",
            }
        )
    with pytest.raises(RepoWiseError, match="external_command"):
        settings_from_answers({"repowise_source": "external"})


def test_external_sync_writes_current_receipt_and_detects_worktree_staleness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A successful external sync is fresh until repository inputs change."""
    repo = tmp_path / "project"
    repo.mkdir()
    _git_init(repo)
    tools = repo / ".agentic" / "tools"
    runs = repo / ".agentic" / "runs" / "adoption-fixture"
    tools.mkdir(parents=True)
    runs.mkdir(parents=True)
    (tools / "install.ps1").write_text("fixture\n", encoding="utf-8")
    (runs / "journal.jsonl").write_text("{}\n", encoding="utf-8")
    existing_setup = {
        Path(".mcp.json"): b'{"existing": true}\n',
        Path(".vscode/mcp.json"): b'{"servers": {}}\n',
        Path(".vscode/extensions.json"): b'{"recommendations": []}\n',
    }
    for relative, content in existing_setup.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    script = tmp_path / "fake_repowise.py"
    _write_fake_repowise(script)
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))

    configured = configure_repowise(repo, _external_settings(script))
    assert configured["source"] == "external"
    assert repowise_status(repo)["index"] == "missing"

    result = sync_repowise(repo)
    assert result.ok is True
    assert result.action == "init"
    receipt = json.loads((repo / RECEIPT_PATH).read_text(encoding="utf-8"))
    invocation = json.loads(
        (repo / ".repowise-invocation.json").read_text(encoding="utf-8")
    )
    assert invocation.count("--exclude=.agentic/tools/**") == 1
    assert invocation.count("--exclude=.agentic/runs/**") == 1
    assert not any("install.ps1" in argument for argument in invocation)
    assert not any("adoption-fixture" in argument for argument in invocation)
    assert (repo / ARTIFACT_PATH).is_file()
    assert (repo / STATE_PATH).is_file()
    assert receipt["repowise_version"] == "0.37.0"
    assert receipt["source"] == "external"
    assert receipt["profile"] == "deterministic"
    head, worktree = repowise_module._repository_fingerprints(repo)
    assert receipt["head"] == head
    assert receipt["worktree_fingerprint"] == worktree
    assert receipt["artifact_sha256"] == hashlib.sha256(
        (repo / ARTIFACT_PATH).read_bytes()
    ).hexdigest()
    assert receipt["state_sha256"] == hashlib.sha256(
        (repo / STATE_PATH).read_bytes()
    ).hexdigest()
    for relative, content in existing_setup.items():
        assert (repo / relative).read_bytes() == content
    assert repowise_status(repo)["current"] is True

    (repo / "new-input.py").write_text("print('changed')\n", encoding="utf-8")
    stale = repowise_status(repo)
    assert stale["current"] is False
    assert stale["index"] == "stale"
    assert stale["next"].startswith("waegis repowise sync")


def test_failed_sync_keeps_configuration_and_reports_exact_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief A genuine index failure stays resumable and cannot mint a receipt."""
    repo = tmp_path / "failed project"
    repo.mkdir()
    _git_init(repo)
    script = tmp_path / "failing repowise.py"
    _write_fake_repowise(script, failure_status=9)
    home = tmp_path / "waegis home"
    monkeypatch.setenv("WAEGIS_HOME", str(home))
    configure_repowise(repo, _external_settings(script))
    stream = io.StringIO()

    code = run_repowise_sync(
        repo,
        as_json=False,
        stream=stream,
        yes=True,
    )

    output = stream.getvalue()
    status = repowise_status(repo)
    assert code == EXIT_OPERATIONAL
    assert status["configured"] is True
    assert status["source"] == "external"
    assert status["mode"] == "advisory"
    assert status["index"] == "missing"
    assert (repo / INTEGRATION_RELATIVE_PATH).is_file()
    assert (repo / RUNTIME_PATH).is_file()
    assert not (repo / RECEIPT_PATH).exists()
    assert not (repo / ".mcp.json").exists()
    assert not (repo / ".vscode").exists()
    log_line = next(line for line in output.splitlines() if line.startswith("log: "))
    log_path = Path(log_line.removeprefix("log: "))
    assert log_path.is_file()
    assert "intentional RepoWise failure" in log_path.read_text(encoding="utf-8")
    assert (
        f'resume: waegis repowise sync --repo "{repo.resolve()}"'
        in output
    )


def test_click_option_serialization_is_literal_on_windows_and_stable_on_posix() -> None:
    """@brief Windows binds glob values while POSIX retains the prior argv shape."""
    patterns = repowise_module.REPOWISE_EXCLUDE_PATTERNS
    assert repowise_module._click_option_arguments(
        "--exclude",
        patterns,
        os_name="nt",
    ) == [
        "--exclude=.agentic/tools/**",
        "--exclude=.agentic/runs/**",
    ]
    assert repowise_module._click_option_arguments(
        "--exclude",
        patterns,
        os_name="posix",
    ) == [
        "--exclude",
        ".agentic/tools/**",
        "--exclude",
        ".agentic/runs/**",
    ]
    special_model = 'model (zăpadă) "quoted" *?'
    assert repowise_module._click_option_arguments(
        "--model",
        (special_model,),
        os_name="nt",
    ) == [f"--model={special_model}"]


@pytest.mark.skipif(os.name != "nt", reason="Windows subprocess contract")
def test_windows_external_command_script_in_space_path_passes_capability_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief External array commands preserve spaced, Unicode repository paths."""
    repo = tmp_path / "project (zăpadă)"
    repo.mkdir()
    _git_init(repo)
    command_directory = tmp_path / "external command with spaces"
    command_directory.mkdir()
    script = command_directory / "repowise command.py"
    _write_fake_repowise(script)
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis home"))

    configured = configure_repowise(repo, _external_settings(script))
    result = sync_repowise(repo)

    assert configured["source"] == "external"
    assert result.ok is True
    assert repowise_status(repo)["current"] is True
    invocation = json.loads(
        (repo / ".repowise-invocation.json").read_text(encoding="utf-8")
    )
    assert invocation[1] == str(repo.resolve())


@pytest.mark.skipif(os.name != "nt", reason="Windows Complete launcher contract")
def test_windows_bundled_runtime_bypasses_cmd_launcher_with_real_subprocess(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    @brief Managed Complete execution bypasses ``cmd`` and preserves glob values.
    @details A real child process runs from a sidecar and repository path that
             contain spaces. The bootstrap emulates Click's Windows expansion,
             so the regression fails if exclusions return to standalone tokens.
    """
    repo = tmp_path / "bundled project with spaces"
    repo.mkdir()
    _git_init(repo)
    (repo / ".agentic" / "tools" / "fixture").mkdir(parents=True)
    (repo / ".agentic" / "tools" / "fixture" / "install.ps1").write_text(
        "fixture\n",
        encoding="utf-8",
    )
    (repo / ".agentic" / "runs" / "fixture").mkdir(parents=True)
    (repo / ".agentic" / "runs" / "fixture" / "journal.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )
    sidecar = repo / ".agentic" / "tools" / "repowise" / "0.37.0" / "windows-x64"
    site_packages = sidecar / "site-packages"
    site_packages.mkdir(parents=True)
    launcher = sidecar / "repowise.cmd"
    launcher.write_text("@echo off\r\nexit /b 99\r\n", encoding="ascii")
    _write_fake_repowise(site_packages / "waegis_repowise_bootstrap.py")
    (site_packages / "sitecustomize.py").write_text(
        '"""Test socket-guard placeholder."""\n',
        encoding="utf-8",
    )
    test_interpreter = Path(sys.executable)
    monkeypatch.setattr(
        repowise_module,
        "_BUNDLED_WINDOWS_INTERPRETER",
        test_interpreter,
    )
    settings = RepoWiseSettings(
        source="bundled",
        profile="deterministic",
        enforcement="advisory",
    )
    repowise_module._write_text(
        repo / INTEGRATION_RELATIVE_PATH,
        repowise_module._integration_text(settings),
    )
    repowise_module._write_json(
        repo / RUNTIME_PATH,
        {
            "schema_version": 1,
            "source": "bundled",
            "command": [launcher.relative_to(repo).as_posix()],
            "profile": "deterministic",
            "ollama_url": "http://127.0.0.1:11434",
            "model": "",
            "embedding_model": "",
        },
    )
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis home"))

    command = repowise_module._runtime_command(
        repo,
        repowise_module._load_json(repo / RUNTIME_PATH),
    )
    result = sync_repowise(repo)

    assert command[0] == str(test_interpreter)
    assert "cmd.exe" not in command
    assert result.ok is True
    invocation = json.loads(
        (repo / ".repowise-invocation.json").read_text(encoding="utf-8")
    )
    assert invocation.count("--exclude=.agentic/tools/**") == 1
    assert invocation.count("--exclude=.agentic/runs/**") == 1
    assert not any("install.ps1" in argument for argument in invocation)
    assert not any("journal.jsonl" in argument for argument in invocation)
    assert not (repo / ".mcp.json").exists()
    assert not (repo / ".vscode").exists()


def test_external_version_outside_supported_minor_is_rejected(tmp_path: Path) -> None:
    """@brief The external bridge accepts only the explicitly supported 0.37.x line."""
    repo = tmp_path / "project"
    repo.mkdir()
    script = tmp_path / "future_repowise.py"
    _write_fake_repowise(script, version="0.38.0")
    with pytest.raises(RepoWiseError, match="outside"):
        configure_repowise(repo, _external_settings(script))


def test_configuration_transfers_policy_ownership_and_repair_reconstructs_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief The mutable policy leaves payload ownership and remains repairable."""
    repo = tmp_path / "project"
    payload = locate_payload()
    copy_payload(payload, repo, mode="new")
    script = tmp_path / "fake_repowise.py"
    _write_fake_repowise(script)
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))

    configure_repowise(repo, _external_settings(script))

    manifest = read_manifest(repo)
    policy = repo / INTEGRATION_RELATIVE_PATH
    assert INTEGRATION_RELATIVE_PATH not in manifest.files
    assert INTEGRATION_RELATIVE_PATH in manifest.generated
    assert manifest.configuration["repowise"]["source"] == "external"
    assert (
        manifest.configuration["generated_files"][INTEGRATION_RELATIVE_PATH][
            "sha256"
        ]
        == hash_file(policy).sha256
    )

    policy.unlink()
    answers = tmp_path / "repair.json"
    answers.write_text(json.dumps({"run_smoke": False}), encoding="utf-8")
    stream = io.StringIO()
    code = run_repair(
        repo,
        stream=stream,
        answers_path=answers,
        non_interactive=True,
        yes=True,
        as_json=True,
        payload=payload,
    )

    assert code == 0
    assert policy.is_file()
    assert 'source = "external"' in policy.read_text(encoding="utf-8")
    repaired = read_manifest(repo)
    assert (
        repaired.configuration["generated_files"][INTEGRATION_RELATIVE_PATH][
            "sha256"
        ]
        == hash_file(policy).sha256
    )


def test_disabled_default_is_noop_and_selected_configuration_commits_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Core default stays in the deployment commit; opt-in gets its own."""
    repo = tmp_path / "project"
    payload = locate_payload()
    copy_payload(payload, repo, mode="new")
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path / "waegis-home"))
    manifest_path = repo / ".agentic" / "install-manifest.json"
    manifest_before = manifest_path.read_bytes()

    result = lifecycle_repowise(
        repo,
        {},
        lifecycle="new",
        interactive=False,
        asker=None,
        stream=None,
    )

    assert result["configuration"]["changed"] is False
    assert manifest_path.read_bytes() == manifest_before
    assert not (repo / repowise_module.RUNTIME_PATH).exists()

    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "AEGIS"], check=True)
    script = tmp_path / "fake_repowise.py"
    _write_fake_repowise(script)
    configure_repowise(repo, _external_settings(script))

    committed = commit_repowise_configuration(
        repo,
        SubprocessCommandRunner(),
        message="Configure RepoWise",
    )

    assert committed is True
    assert commit_repowise_configuration(
        repo,
        SubprocessCommandRunner(),
        message="Configure RepoWise",
    ) is False
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert status.stdout == ""
    subject = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert subject.stdout.strip() == "Configure RepoWise"


def test_repowise_command_group_has_only_status_and_sync() -> None:
    """@brief The public CLI exposes the compact two-command RepoWise group."""
    parser = build_parser()
    status = parser.parse_args(["repowise", "status", "--repo", "."])
    sync = parser.parse_args(["repowise", "sync", "--repo", "."])
    assert status.repowise_action == "status"
    assert sync.repowise_action == "sync"
    with pytest.raises(SystemExit):
        parser.parse_args(["repowise", "install", "--repo", "."])


def test_disabled_policy_needs_no_runtime_metadata(tmp_path: Path) -> None:
    """@brief A generated disabled integration remains valid without sidecars."""
    repo = tmp_path / "project"
    repo.mkdir()
    policy = repo / ".agentic" / "integrations" / "repowise.toml"
    policy.parent.mkdir(parents=True)
    policy.write_text(
        repowise_module._integration_text(RepoWiseSettings()),
        encoding="utf-8",
    )

    status = repowise_status(repo)

    assert status["mode"] == "disabled"
    assert status["installed"] is False


def test_status_rejects_noncanonical_schema_one_policy(tmp_path: Path) -> None:
    """@brief Strict integration fields cannot redirect the supported bridge."""
    repo = tmp_path / "project"
    repo.mkdir()
    policy = repo / ".agentic" / "integrations" / "repowise.toml"
    policy.parent.mkdir(parents=True)
    text = repowise_module._integration_text(RepoWiseSettings())
    policy.write_text(
        text.replace(
            'version_spec = ">=0.37.0,<0.38.0"',
            'version_spec = ">=0.37.0,<0.39.0"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(RepoWiseError, match="version_spec"):
        repowise_status(repo)


def test_bundle_manifest_rejects_traversal_and_source_hash_drift(tmp_path: Path) -> None:
    """@brief Sidecar verification rejects unsafe paths and altered source."""
    bundle = tmp_path / "bundle"
    manifest = _write_bundle(bundle)
    assert repowise_module._load_bundle_manifest(bundle)["tree_sha256"]

    files = manifest["files"]
    assert isinstance(files, list)
    files.append({"path": "../escape", "sha256": "0" * 64, "size": 1})
    (bundle / repowise_module.BUNDLE_MANIFEST).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    with pytest.raises(RepoWiseError, match="unsafe"):
        repowise_module._load_bundle_manifest(bundle)

    manifest = _write_bundle(bundle)
    manifest["source_sha256"] = "0" * 64
    (bundle / repowise_module.BUNDLE_MANIFEST).write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )
    with pytest.raises(RepoWiseError, match="source archive"):
        repowise_module._load_bundle_manifest(bundle)


# END OF FILE
