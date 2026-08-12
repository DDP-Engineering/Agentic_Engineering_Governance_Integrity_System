#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Test WAEGIS plan/apply lifecycle and exact ownership boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from waegis.composition import create_application


def make_payload(root: Path, marker: str = "one") -> Path:
    """Create one exact manifest-owned synthetic AEGIS payload."""
    payload = root / "payload"
    (payload / "cli").mkdir(parents=True)
    data = f"payload-{marker}\n".encode()
    (payload / "cli" / "marker.txt").write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (payload / "manifest.toml").write_text(
        "schema = 1\n"
        'artifact_type = "payload_manifest"\n'
        'payload_id = "PAYLOAD-0123456789abcdef0123456789abcdef"\n'
        'product = "AEGIS"\n'
        f'product_version = "{marker}"\n'
        'platform = "source"\n'
        'architecture = "x86_64"\n\n'
        "[[files]]\n"
        'path = "cli/marker.txt"\n'
        f"size = {len(data)}\n"
        f'sha256 = "{digest}"\n',
        encoding="utf-8",
    )
    return payload


def execute(app, operation: str, **inputs):
    """Invoke one application operation and require a structured result."""
    return app.execute(operation, inputs).to_envelope(1)


def snapshot(root: Path) -> dict[str, bytes]:
    """Capture every regular target file for read-only-plan assertions."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_install_plan_is_read_only_and_apply_requires_exact_current_plan(
    tmp_path: Path,
) -> None:
    """Cover IP-15 dry-run, byte digest approval, defaults, and staleness."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    output = tmp_path / "plans" / "install.json"
    app = create_application(payload)

    before = snapshot(target)
    planned = execute(app, "install.plan", target=str(target), output=str(output))
    assert planned["operation_status"] == "completed"
    assert snapshot(target) == before
    assert output.is_file() and not output.is_relative_to(target)
    digest = planned["data"]["plan_digest"]

    rejected = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(output),
        confirm_digest="sha256:" + "0" * 64,
    )
    assert rejected["error"]["code"] == "state_conflict"
    assert not (target / ".agentic").exists()

    (target / "late.txt").write_text("changed", encoding="utf-8")
    stale = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(output),
        confirm_digest=digest,
    )
    assert stale["error"]["code"] == "state_conflict"
    assert not (target / ".agentic").exists()

    planned = execute(app, "install.plan", target=str(target), output=str(output))
    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(output),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert applied["operation_status"] == "completed"
    assert (target / ".agentic/aegis/cli/marker.txt").read_text() == "payload-one\n"

    removal_output = tmp_path / "remove.json"
    removal = execute(
        app, "remove.plan", target=str(target), output=str(removal_output)
    )
    removed = execute(
        app,
        "remove.apply",
        target=str(target),
        plan=str(removal_output),
        confirm_digest=removal["data"]["plan_digest"],
    )

    assert removed["operation_status"] == "completed"
    assert not (target / ".agentic/aegis").exists()
    assert (target / ".agentic/config.toml").is_file()
    config = (target / ".agentic/config.toml").read_text(encoding="utf-8")
    assert 'tests = [".agentic/tests"]' in config
    assert 'command = ["python", "-m", "unittest", "discover"' in config
    assert ".agentic/runs/context.toml" in (target / ".git/info/exclude").read_text()
    assert not (target / ".git/index").exists()


def test_install_supports_linked_git_worktree_without_shared_metadata_write(
    tmp_path: Path,
) -> None:
    """A linked worktree is a repository without a target-local Git directory."""
    payload = make_payload(tmp_path / "source")
    primary = tmp_path / "primary"
    primary.mkdir()
    subprocess.run(["git", "init", "-q", str(primary)], check=True)
    subprocess.run(
        ["git", "-C", str(primary), "config", "user.name", "WAEGIS Test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(primary), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    (primary / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(primary), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(primary), "commit", "-q", "-m", "baseline"],
        check=True,
    )
    target = tmp_path / "linked"
    subprocess.run(
        ["git", "-C", str(primary), "worktree", "add", "-q", "--detach", str(target)],
        check=True,
    )
    assert (target / ".git").is_file()
    output = tmp_path / "install.json"
    app = create_application(payload)

    planned = execute(app, "install.plan", target=str(target), output=str(output))

    assert planned["operation_status"] == "completed"
    assert (
        "Linked Git worktree detected; shared info/exclude was not modified."
        in planned["data"]["warnings"]
    )
    plan = json.loads(output.read_text(encoding="utf-8"))
    assert ".git/info/exclude" not in {action["path"] for action in plan["actions"]}

    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(output),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert applied["operation_status"] == "completed"
    assert (target / ".agentic/aegis/cli/marker.txt").read_text() == "payload-one\n"


def test_install_detects_existing_pytest_root_and_preserves_dirty_files(
    tmp_path: Path,
) -> None:
    """Cover detected integration configuration and a dirty target fixture."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    (target / "tests").mkdir(parents=True)
    (target / "tests/test_existing.py").write_text("assert True\n", encoding="utf-8")
    (target / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\naddopts = "-q"\n\n[tool.ruff]\nline-length = 88\n',
        encoding="utf-8",
    )
    (target / "notes.txt").write_text("keep me\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    output = tmp_path / "install.json"
    app = create_application(payload)

    planned = execute(app, "install.plan", target=str(target), output=str(output))
    execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(output),
        confirm_digest=planned["data"]["plan_digest"],
    )
    config = (target / ".agentic/config.toml").read_text(encoding="utf-8")
    assert 'tests = ["tests"]' in config
    assert 'command = ["python", "-m", "pytest"]' in config
    assert "[validation.lints.ruff]" in config
    assert 'command = ["python", "-m", "ruff", "check", "."]' in config
    assert (target / "notes.txt").read_text() == "keep me\n"


def test_install_uses_unittest_for_existing_tests_without_pytest_signal(
    tmp_path: Path,
) -> None:
    """Existing tests are not falsely classified as pytest without evidence."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    (target / "tests").mkdir(parents=True)
    (target / "tests/test_existing.py").write_text(
        "import unittest\n\nclass Existing(unittest.TestCase):\n    pass\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    config = (target / ".agentic/config.toml").read_text(encoding="utf-8")
    assert 'tests = ["tests"]' in config
    assert 'command = ["python", "-m", "unittest", "discover", "-s", "tests"]' in (
        config
    )


def test_repository_init_is_separately_planned_and_only_apply_runs_git(
    tmp_path: Path,
) -> None:
    """Cover the sole authorized local Git mutation and no implicit init."""
    target = tmp_path / "plain"
    target.mkdir()
    payload = make_payload(tmp_path / "source")
    app = create_application(payload)
    install_output = tmp_path / "install.json"

    refused = execute(
        app, "install.plan", target=str(target), output=str(install_output)
    )
    assert refused["error"]["code"] == "missing_prerequisite"
    assert not (target / ".git").exists()

    output = tmp_path / "init.json"
    planned = execute(
        app, "repository_init.plan", target=str(target), output=str(output)
    )
    assert not (target / ".git").exists()
    applied = execute(
        app,
        "repository_init.apply",
        target=str(target),
        plan=str(output),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert applied["operation_status"] == "completed"
    assert (target / ".git").is_dir()


def test_upgrade_and_remove_use_manifest_ownership_and_preserve_project_data(
    tmp_path: Path,
) -> None:
    """Cover IP-16 replacement, modified reporting, removal, and preservation."""
    first = make_payload(tmp_path / "first", "one")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    app = create_application(first)
    plan = tmp_path / "install.json"
    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    (target / ".agentic/aegis/cli/marker.txt").write_text("operator edit\n")
    project_paths = [
        ".agentic/config.toml",
        ".agentic/rules.md",
        ".agentic/requirements/REQ-a.toml",
        ".agentic/components/COMP-a.md",
        ".agentic/tests/test_a.py",
        ".agentic/adoptions/ADOPT-a.md",
        ".agentic/runs/RUN-a/run.md",
        "application.txt",
    ]
    for relative in project_paths[2:]:
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "import unittest\n\n"
            "class Preserved(unittest.TestCase):\n"
            "    def test_application(self):\n"
            "        self.assertTrue(True)\n"
            if relative == ".agentic/tests/test_a.py"
            else f"preserve {relative}\n"
        )
        path.write_text(content, encoding="utf-8")
    preserved = {
        relative: (target / relative).read_bytes() for relative in project_paths
    }

    second = make_payload(tmp_path / "second", "two")
    upgraded_app = create_application(second)
    plan = tmp_path / "upgrade.json"
    planned = execute(
        upgraded_app, "upgrade.plan", target=str(target), output=str(plan)
    )
    assert planned["data"]["modified_payload_paths"] == ["cli/marker.txt"]
    applied = execute(
        upgraded_app,
        "upgrade.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert applied["operation_status"] == "completed"
    assert (target / ".agentic/aegis/cli/marker.txt").read_text() == "payload-two\n"
    assert all((target / key).read_bytes() == value for key, value in preserved.items())

    plan = tmp_path / "remove.json"
    planned = execute(upgraded_app, "remove.plan", target=str(target), output=str(plan))
    removed = execute(
        upgraded_app,
        "remove.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert removed["operation_status"] == "completed"
    assert not (target / ".agentic/aegis").exists()
    assert all((target / key).read_bytes() == value for key, value in preserved.items())
    project_tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            ".agentic/tests",
        ],
        cwd=target,
        check=False,
        capture_output=True,
    )
    assert project_tests.returncode == 0, project_tests.stderr.decode(errors="replace")


def test_catalog_and_envelope_are_bounded_and_have_no_outward_git_action(
    tmp_path: Path,
) -> None:
    """Cover independent protocol parity and the exact WAEGIS operation surface."""
    app = create_application(make_payload(tmp_path))
    result = execute(app, "help.show")
    assert list(result) == [
        "schema",
        "schema_version",
        "product",
        "product_version",
        "operation",
        "operation_id",
        "operation_status",
        "run_id",
        "stage",
        "revision",
        "outcome",
        "message",
        "data",
        "findings",
        "artifacts",
        "next_actions",
        "error",
        "truncated",
        "details_ref",
    ]
    operations = result["data"]["operations"]
    assert [entry["operation"] for entry in operations] == [
        "help.show",
        "version.show",
        "repository_init.plan",
        "repository_init.apply",
        "install.plan",
        "install.apply",
        "upgrade.plan",
        "upgrade.apply",
        "remove.plan",
        "remove.apply",
    ]
    forbidden = {"stage", "commit", "branch", "tag", "merge", "push", "pull_request"}
    assert not any(
        word in entry["operation"] for entry in operations for word in forbidden
    )
    assert result["product"] == "WAEGIS"
    assert result["operation_status"] == "completed"
    assert json.dumps(result, allow_nan=False)


def test_interrupted_install_rolls_forward_only_the_same_authorized_plan(
    tmp_path: Path,
) -> None:
    """Cover WAEGIS-local durable publication and exact-plan recovery."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    planner = create_application(payload)
    planned = execute(planner, "install.plan", target=str(target), output=str(plan))

    interrupted = execute(
        create_application(payload, fault_after=2),
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert interrupted["error"]["code"] == "publication_failed"
    assert interrupted["error"]["details"]["recovery_available"] is True

    recovered = execute(
        create_application(payload),
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert recovered["operation_status"] == "completed"
    assert recovered["data"]["recovered"] is True
    assert (target / ".agentic/aegis/cli/marker.txt").is_file()
    assert not (target / ".agentic/.runtime/waegis/transaction.json").exists()


def test_install_refuses_repository_symlink_escape(tmp_path: Path) -> None:
    """A repository-owned symlink cannot redirect WAEGIS writes outside target."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    outside = tmp_path / "outside"
    target.mkdir()
    outside.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    try:
        os.symlink(outside, target / ".agentic", target_is_directory=True)
    except OSError as exc:
        if os.name != "nt":
            import pytest

            pytest.skip(f"Directory symlink unavailable: {exc}")
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "& { param($link, $destination) New-Item -ItemType Junction "
                "-Path $link -Target $destination | Out-Null }",
                str(target / ".agentic"),
                str(outside),
            ],
            check=False,
            capture_output=True,
        )
        assert completed.returncode == 0, completed.stderr.decode(errors="replace")
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert applied["operation_status"] == "error"
    assert not list(outside.rglob("*"))
