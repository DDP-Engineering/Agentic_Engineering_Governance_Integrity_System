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
import tomllib
from pathlib import Path

from waegis.composition import create_application
from waegis.infrastructure.payload import PayloadManifest
from waegis.infrastructure.target import detected_test_roots

HOST_STARTERS = {
    "adapters/starters/claude-code/SKILL.md": (
        ".claude/skills/aegis/SKILL.md",
        b"claude starter\n",
    ),
    "adapters/starters/codex/SKILL.md": (
        ".codex/skills/aegis/SKILL.md",
        b"codex starter\n",
    ),
    "adapters/starters/opencode/aegis.md": (
        ".opencode/agents/aegis.md",
        b"opencode starter\n",
    ),
    "adapters/starters/pi/SKILL.md": (
        ".pi/skills/aegis/SKILL.md",
        b"pi starter\n",
    ),
    "adapters/starters/qwen-code/aegis.md": (
        ".qwen/commands/aegis.md",
        b"qwen starter\n",
    ),
}


def make_payload(root: Path, marker: str = "one") -> Path:
    """Create one exact manifest-owned synthetic AEGIS payload."""
    payload = root / "payload"
    (payload / "cli").mkdir(parents=True)
    data = f"payload-{marker}\n".encode()
    (payload / "cli" / "marker.txt").write_bytes(data)
    files = {"cli/marker.txt": data}
    for source, (_destination, starter) in HOST_STARTERS.items():
        content = starter.replace(b"starter", f"starter {marker}".encode())
        path = payload / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        files[source] = content
    entries = "".join(
        "\n[[files]]\n"
        f'path = "{path}"\n'
        f"size = {len(content)}\n"
        f'sha256 = "{hashlib.sha256(content).hexdigest()}"\n'
        for path, content in sorted(files.items())
    )
    (payload / "manifest.toml").write_text(
        "schema = 1\n"
        'artifact_type = "payload_manifest"\n'
        'payload_id = "PAYLOAD-0123456789abcdef0123456789abcdef"\n'
        'product = "AEGIS"\n'
        f'product_version = "{marker}"\n'
        'platform = "source"\n'
        'architecture = "x86_64"\n\n'
        + entries,
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
    assert (target / ".agentic/.gitignore").read_text(encoding="utf-8") == (
        ".runtime/\nruns/context.toml\n"
    )

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


def test_fresh_install_creates_and_preserves_every_configured_root(
    tmp_path: Path,
) -> None:
    """PR-CONFIG-001/002: installed project-owned roots match relocations."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    (target / ".agentic").mkdir(parents=True)
    config = (
        "schema = 1\n"
        'artifact_type = "project_config"\n\n'
        "[paths]\n"
        'requirements = "project-state/requirements"\n'
        'components = "project-state/components"\n'
        'tests = ["quality/unit", "quality/integration"]\n'
        'adoptions = "project-state/adoptions"\n'
        'runs = "project-state/runs"\n'
    )
    (target / ".agentic/config.toml").write_text(config, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)

    before = snapshot(target)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    assert planned["operation_status"] == "completed"
    assert snapshot(target) == before
    configured = tomllib.loads(config)["paths"]
    roots = {
        configured["requirements"],
        configured["components"],
        *configured["tests"],
        configured["adoptions"],
        configured["runs"],
    }
    assert all(not (target / root).exists() for root in roots)
    actions = json.loads(plan.read_text(encoding="utf-8"))["actions"]
    root_placeholders = {
        action["path"]: action["ownership"]
        for action in actions
        if action["path"].endswith("/.gitkeep")
    }
    assert root_placeholders == {f"{root}/.gitkeep": "project" for root in roots}

    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert applied["operation_status"] == "completed"
    assert all((target / root).is_dir() for root in roots)

    remove_plan = tmp_path / "remove.json"
    removal = execute(
        app, "remove.plan", target=str(target), output=str(remove_plan)
    )
    removed = execute(
        app,
        "remove.apply",
        target=str(target),
        plan=str(remove_plan),
        confirm_digest=removal["data"]["plan_digest"],
    )
    assert removed["operation_status"] == "completed"
    assert all((target / root / ".gitkeep").is_file() for root in roots)


def test_new_gitignored_disposable_files_do_not_stale_plan(tmp_path: Path) -> None:
    """PR-WAEGIS-002: New ignored cache, swap, and log files are disposable."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    (target / ".gitignore").write_text(
        "__pycache__/\n*.pyc\n*.swp\n*.log\n", encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))

    cache = target / "tests/__pycache__"
    cache.mkdir(parents=True)
    (cache / "test_a.cpython-312.pyc").write_bytes(b"disposable-bytecode")
    (target / "notes.swp").write_text("disposable swap", encoding="utf-8")
    (target / "test-run.log").write_text("disposable log", encoding="utf-8")
    for ignored in (
        cache / "test_a.cpython-312.pyc",
        target / "notes.swp",
        target / "test-run.log",
    ):
        assert subprocess.run(
            ["git", "-C", str(target), "check-ignore", "--quiet", str(ignored)],
            check=False,
        ).returncode == 0
    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert applied["operation_status"] == "completed"
    assert (target / ".agentic/aegis/cli/marker.txt").is_file()


def test_preexisting_untracked_ignored_file_remains_disposable(tmp_path: Path) -> None:
    """PR-WAEGIS-002: Existing ignored cache bytes are not authorization state."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    cache = target / "tests/__pycache__"
    cache.mkdir(parents=True)
    (target / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    bytecode = cache / "test_a.cpython-312.pyc"
    bytecode.write_bytes(b"before planning")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))

    bytecode.write_bytes(b"rewritten after planning")
    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert applied["operation_status"] == "completed"


def test_modified_preexisting_ignored_staged_file_stales_plan(tmp_path: Path) -> None:
    """PR-WAEGIS-002/006: Meaningful staged bytes remain fingerprinted."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    (target / ".gitignore").write_text("*.log\n", encoding="utf-8")
    tracked = target / "audit.log"
    tracked.write_text("planned bytes\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    subprocess.run(
        ["git", "-C", str(target), "add", "-f", ".gitignore", "audit.log"],
        check=True,
    )
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))

    tracked.write_text("meaningfully changed bytes\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(target), "add", "-f", "audit.log"], check=True
    )
    rejected = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert rejected["error"]["code"] == "state_conflict"
    assert not (target / ".agentic").exists()


def test_new_force_added_ignored_file_stales_plan(tmp_path: Path) -> None:
    """PR-WAEGIS-002/006: A newly tracked ignored path is meaningful state."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    (target / ".gitignore").write_text("*.log\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))

    tracked = target / "important.log"
    tracked.write_text("meaningful staged addition\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(target), "add", "-f", "important.log"], check=True
    )
    subprocess.run(
        ["git", "-C", str(target), "update-index", "--index-version=4"], check=True
    )
    rejected = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert rejected["error"]["code"] == "state_conflict"
    assert not (target / ".agentic").exists()


def test_plan_show_is_paginated_and_omits_action_bodies(tmp_path: Path) -> None:
    """PR-WAEGIS-002: Exact lifecycle plans have a bounded review operation."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)
    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    plan_before = plan.read_bytes()
    target_before = snapshot(target)

    shown = execute(app, "plan.show", plan=str(plan), offset="1", limit="2")

    assert shown["operation_status"] == "completed"
    assert shown["operation"] == "plan.show"
    assert shown["data"]["plan_digest"] == planned["data"]["plan_digest"]
    assert shown["data"]["action_count"] > shown["data"]["returned_count"] == 2
    assert shown["data"]["offset"] == 1
    assert set(shown["data"]["action_counts_by_kind"]) == {"write"}
    assert all(
        set(action) == {"index", "path", "kind", "ownership", "sha256"}
        for action in shown["data"]["actions"]
    )
    assert shown["truncated"] is True
    assert shown["details_ref"] == str(plan.resolve())
    assert "content_base64" not in json.dumps(shown)
    assert plan.read_bytes() == plan_before
    assert snapshot(target) == target_before

    refused_page = execute(app, "plan.show", plan=str(plan), limit="101")
    assert refused_page["error"]["code"] == "invalid_input"
    assert plan.read_bytes() == plan_before
    assert snapshot(target) == target_before


def test_plan_show_and_apply_reject_noncanonical_plan_bytes(tmp_path: Path) -> None:
    """PR-WAEGIS-002: Review and apply accept only canonical plan bytes."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)
    execute(app, "install.plan", target=str(target), output=str(plan))
    parsed = json.loads(plan.read_text(encoding="utf-8"))
    altered = json.dumps(parsed, indent=2).encode("utf-8")
    plan.write_bytes(altered)
    altered_digest = f"sha256:{hashlib.sha256(altered).hexdigest()}"

    shown = execute(app, "plan.show", plan=str(plan))
    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=altered_digest,
    )

    assert shown["operation_status"] == "error"
    assert applied["operation_status"] == "error"
    assert not (target / ".agentic").exists()


def test_install_writes_a_versioned_exclusion(tmp_path: Path) -> None:
    """Project-owned local-state exclusions propagate through an ordinary clone."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    target.mkdir()
    root_ignore = target / ".gitignore"
    root_ignore.write_bytes(b"operator-owned-root-rule\n")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)

    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    plan_data = json.loads(plan.read_text(encoding="utf-8"))
    exclusion_action = next(
        action
        for action in plan_data["actions"]
        if action["path"] == ".agentic/.gitignore"
    )
    assert exclusion_action["ownership"] == "project"
    applied = execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert applied["operation_status"] == "completed"
    assert (target / ".agentic/.gitignore").read_text(encoding="utf-8") == (
        ".runtime/\nruns/context.toml\n"
    )
    assert root_ignore.read_bytes() == b"operator-owned-root-rule\n"

    subprocess.run(["git", "-C", str(target), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(target), "-c", "user.name=WAEGIS Test", "-c",
         "user.email=waegis@example.invalid", "commit", "-qm", "install"],
        check=True,
    )
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(target), str(clone)], check=True)
    (clone / ".agentic/.runtime").mkdir()
    (clone / ".agentic/.runtime/local.txt").write_text("local\n", encoding="utf-8")
    (clone / ".agentic/runs").mkdir(exist_ok=True)
    (clone / ".agentic/runs/context.toml").write_text(
        'selected_run = "RUN-local"\n', encoding="utf-8"
    )

    assert subprocess.run(
        ["git", "-C", str(clone), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout == ""


def test_relocated_runs_pointer_is_excluded(tmp_path: Path) -> None:
    """Configured Run roots drive both preserved versioned and local exclusions."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    (target / ".agentic").mkdir(parents=True)
    (target / ".agentic/config.toml").write_text(
        "schema = 1\n"
        'artifact_type = "project_config"\n\n'
        "[paths]\n"
        'requirements = ".agentic/requirements"\n'
        'components = ".agentic/components"\n'
        'tests = [".agentic/tests"]\n'
        'adoptions = ".agentic/adoptions"\n'
        'runs = ".agentic/team-runs"\n',
        encoding="utf-8",
    )
    (target / ".agentic/.gitignore").write_bytes(b"operator-cache/\n")
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    plan = tmp_path / "install.json"
    app = create_application(payload)

    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    actions = json.loads(plan.read_text(encoding="utf-8"))["actions"]
    ownership = {
        action["path"]: action["ownership"]
        for action in actions
        if action["path"] in {item[0] for item in HOST_STARTERS.values()}
    }
    assert ownership == {
        destination: "project"
        for destination, _content in HOST_STARTERS.values()
    }
    execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    assert (target / ".agentic/.gitignore").read_text(encoding="utf-8") == (
        "operator-cache/\n.runtime/\nteam-runs/context.toml\n"
    )
    local_exclude = (target / ".git/info/exclude").read_text(encoding="utf-8")
    assert ".agentic/team-runs/context.toml" in local_exclude.splitlines()
    assert ".agentic/runs/context.toml" not in local_exclude.splitlines()
    pointer = target / ".agentic/team-runs/context.toml"
    pointer.parent.mkdir(exist_ok=True)
    pointer.write_text('selected_run = "RUN-local"\n', encoding="utf-8")
    ignored = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "-q", str(pointer)],
        check=False,
    )
    assert ignored.returncode == 0


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
    assert "timeout_seconds" not in config
    assert "[validation.lints.ruff]" in config
    assert 'command = ["python", "-m", "ruff", "check", "."]' in config
    assert (target / "notes.txt").read_text() == "keep me\n"


def test_bare_function_tests_are_detected_as_pytest(tmp_path: Path) -> None:
    """PR-DEFAULT-001: Bare pytest functions select a usable test command."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    (target / "tests").mkdir(parents=True)
    (target / "tests/test_calc.py").write_text(
        "def test_addition():\n    assert 1 + 1 == 2\n",
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
    assert 'command = ["python", "-m", "pytest"]' in config
    assert (
        "Selected pytest test framework: pytest-style test function or method detected "
        "in tests/test_calc.py."
        in planned["data"]["warnings"]
    )


def test_class_style_pytest_is_detected(tmp_path: Path) -> None:
    """PR-SCOPE-009: Indented pytest methods select a usable pytest command."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    (target / "tests").mkdir(parents=True)
    (target / "tests/test_calc.py").write_text(
        "class TestCalc:\n"
        "    def test_add(self):\n"
        "        assert 1 + 1 == 2\n",
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
    assert 'command = ["python", "-m", "pytest"]' in config
    assert (
        "Selected pytest test framework: pytest-style test function or method "
        "detected in tests/test_calc.py."
        in planned["data"]["warnings"]
    )
    selected = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=target,
        check=False,
        capture_output=True,
    )
    assert selected.returncode == 0, selected.stdout.decode(errors="replace")


def test_nested_test_root_is_detected(tmp_path: Path) -> None:
    """PR-CONFIG-004: A nested software project's pytest root is configured."""
    payload = make_payload(tmp_path / "source")
    target = tmp_path / "project"
    project = target / "04_Software/VoiceApplication"
    (project / "tests").mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\naddopts = '-q'\n",
        encoding="utf-8",
    )
    (project / "tests/test_a.py").write_text(
        "def test_nested():\n    assert True\n",
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
    assert 'tests = ["04_Software/VoiceApplication/tests"]' in config
    assert 'command = ["python", "-m", "pytest"]' in config
    assert (
        "Selected pytest test framework: "
        "04_Software/VoiceApplication/pyproject.toml contains a "
        "[tool.pytest] section."
        in planned["data"]["warnings"]
    )
    selected = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=target,
        check=False,
        capture_output=True,
    )
    assert selected.returncode == 0, selected.stdout.decode(errors="replace")


def test_test_root_discovery_is_bounded_and_deterministic(tmp_path: Path) -> None:
    """PR-CONFIG-004/005: Find nested roots while pruning generated trees."""
    target = tmp_path / "project"
    for relative in (
        "tests",
        "test",
        "alpha/tests",
        "beta/test",
        "three/deep/tests",
        "four/levels/deep/tests",
        "five/levels/are/too/deep/tests",
        "node_modules/package/tests",
        ".venv/package/tests",
    ):
        (target / relative).mkdir(parents=True)
    outside = tmp_path / "outside"
    (outside / "tests").mkdir(parents=True)
    try:
        os.symlink(outside, target / "linked", target_is_directory=True)
    except OSError as exc:
        if os.name != "nt":
            raise AssertionError("Directory symlink creation failed") from exc
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "& { param($link, $destination) New-Item -ItemType Junction "
                "-Path $link -Target $destination | Out-Null }",
                str(target / "linked"),
                str(outside),
            ],
            check=False,
            capture_output=True,
        )
        assert completed.returncode == 0, completed.stderr.decode(errors="replace")

    assert detected_test_roots(target) == [
        "tests",
        "test",
        "alpha/tests",
        "beta/test",
        "three/deep/tests",
        "four/levels/deep/tests",
    ]


def test_detection_basis_is_reported(tmp_path: Path) -> None:
    """PR-CONFIG-007: The selected framework warning identifies its basis."""
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

    assert (
        "Selected unittest test framework: unittest.TestCase usage detected in "
        "tests/test_existing.py."
        in planned["data"]["warnings"]
    )


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
    exclusion_path = target / ".agentic/.gitignore"
    exclusion_path.write_text(
        exclusion_path.read_text(encoding="utf-8") + "operator-cache/\n",
        encoding="utf-8",
    )
    (target / ".agentic/aegis/cli/marker.txt").write_text("operator edit\n")
    project_paths = [
        ".agentic/.gitignore",
        ".agentic/config.toml",
        ".agentic/rules.md",
        ".agentic/requirements/REQ-a.toml",
        ".agentic/components/COMP-a.md",
        ".agentic/tests/test_a.py",
        ".agentic/adoptions/ADOPT-a.md",
        ".agentic/runs/RUN-a/run.md",
        "application.txt",
    ]
    for relative in project_paths[3:]:
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

    plan = tmp_path / "reinstall.json"
    planned = execute(
        upgraded_app, "install.plan", target=str(target), output=str(plan)
    )
    reinstalled = execute(
        upgraded_app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert reinstalled["operation_status"] == "completed"
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


def test_install_delivers_host_guidance(tmp_path: Path) -> None:
    """PR-HOST-002: a fresh install creates every native host starter."""
    payload = make_payload(tmp_path / "source", "one")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    app = create_application(payload)
    plan = tmp_path / "install.json"

    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    for source, (destination, _content) in HOST_STARTERS.items():
        assert (target / destination).read_bytes() == (payload / source).read_bytes()


def test_install_creates_root_agents_bridge_when_missing(tmp_path: Path) -> None:
    """REQ-PLAT-bd3ae391: a fresh target receives discoverable guidance."""
    payload = make_payload(tmp_path / "source", "one")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    app = create_application(payload)
    plan = tmp_path / "install.json"

    planned = execute(app, "install.plan", target=str(target), output=str(plan))
    plan_document = json.loads(plan.read_text(encoding="utf-8"))
    action = next(
        item for item in plan_document["actions"] if item["path"] == "AGENTS.md"
    )
    assert action["kind"] == "write"
    assert action["ownership"] == "project"
    execute(
        app,
        "install.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )

    guidance = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert guidance.count("<!-- AEGIS:BEGIN (managed by WAEGIS) -->") == 1
    assert ".agentic/rules.md" in guidance
    assert "commit" in guidance
    assert "push" in guidance


def test_install_prefixes_existing_root_agents_guidance_once(tmp_path: Path) -> None:
    """REQ-PLAT-bd3ae391: existing guidance continues after one bridge."""
    first = make_payload(tmp_path / "first", "one")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    existing = b"# Project instructions\n\nKeep this exact guidance.\n"
    (target / "AGENTS.md").write_bytes(existing)
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
    merged = (target / "AGENTS.md").read_bytes()
    assert merged.count(b"<!-- AEGIS:BEGIN (managed by WAEGIS) -->") == 1
    assert merged.endswith(existing)

    second = make_payload(tmp_path / "second", "two")
    upgraded = create_application(second)
    upgrade = tmp_path / "upgrade.json"
    upgrade_plan = execute(
        upgraded, "upgrade.plan", target=str(target), output=str(upgrade)
    )
    assert upgrade_plan["operation_status"] == "completed"
    upgrade_document = json.loads(upgrade.read_text(encoding="utf-8"))
    assert all(item["path"] != "AGENTS.md" for item in upgrade_document["actions"])


def test_upgrade_preserves_edited_host_guidance(tmp_path: Path) -> None:
    """PR-HOST-002/PR-PAYLOAD-005: starters are create-only project files."""
    first = make_payload(tmp_path / "first", "one")
    target = tmp_path / "project"
    target.mkdir()
    subprocess.run(["git", "init", "-q", str(target)], check=True)
    edited = b"project-owned edited guidance\n"
    edited_destinations = {
        destination for destination, _content in HOST_STARTERS.values()
    }
    for destination in edited_destinations:
        path = target / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(edited)
    legacy_pi = target / ".pi/agents/aegis.md"
    legacy_pi.parent.mkdir(parents=True, exist_ok=True)
    legacy_pi.write_bytes(b"legacy project-owned pi guidance\n")

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
    assert all((target / path).read_bytes() == edited for path in edited_destinations)

    missing = {
        ".pi/skills/aegis/SKILL.md",
        ".qwen/commands/aegis.md",
    }
    for destination in missing:
        (target / destination).unlink()
    second = make_payload(tmp_path / "second", "two")
    upgraded = create_application(second)
    plan = tmp_path / "upgrade.json"
    planned = execute(upgraded, "upgrade.plan", target=str(target), output=str(plan))
    execute(
        upgraded,
        "upgrade.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    for source, (destination, _content) in HOST_STARTERS.items():
        expected = (
            second / source
        ).read_bytes() if destination in missing else edited
        assert (target / destination).read_bytes() == expected
    assert legacy_pi.read_bytes() == b"legacy project-owned pi guidance\n"

    (target / ".codex/skills/aegis/SKILL.md").write_bytes(b"changed externally\n")
    PayloadManifest.load(target / ".agentic/aegis", verify=True)
    preserved = {
        path: (target / path).read_bytes() for path in edited_destinations
    }

    plan = tmp_path / "remove.json"
    planned = execute(upgraded, "remove.plan", target=str(target), output=str(plan))
    execute(
        upgraded,
        "remove.apply",
        target=str(target),
        plan=str(plan),
        confirm_digest=planned["data"]["plan_digest"],
    )
    assert all(
        (target / path).read_bytes() == content
        for path, content in preserved.items()
    )
    assert legacy_pi.is_file()


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
        "plan.show",
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
    plan_show = next(
        entry for entry in operations if entry["operation"] == "plan.show"
    )
    assert plan_show["required_arguments"] == ["plan"]
    assert plan_show["optional_arguments"] == ["offset", "limit"]


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
