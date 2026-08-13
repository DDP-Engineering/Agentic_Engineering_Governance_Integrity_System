#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    test_host_adapters.py
@brief   Verify every host resource is a thin versioned protocol transport.
@details Covers IP-14, PR-HOST, PR-ROLE, PR-MODEL, AC-HOST-001, and the
         synthetic contract portion of AC-HOST-002/AC-MODEL-001.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from aegis.application.operation_registry import operations_for

TEMPLATE = Path(__file__).parents[1] / "template"
ADAPTERS = TEMPLATE / ".agentic" / "aegis" / "adapters"
HOSTS = ("claude-code", "codex", "qwen-code", "opencode", "pi")
NATIVE = {
    "claude-code": TEMPLATE / ".claude" / "skills" / "aegis" / "SKILL.md",
    "codex": TEMPLATE / ".codex" / "skills" / "aegis" / "SKILL.md",
    "qwen-code": TEMPLATE / ".qwen" / "commands" / "aegis.md",
    "opencode": TEMPLATE / ".opencode" / "agents" / "aegis.md",
    "pi": TEMPLATE / ".pi" / "skills" / "aegis" / "SKILL.md",
}
STARTERS = {
    host: ADAPTERS / "starters" / host / path.name
    for host, path in NATIVE.items()
}


def front_matter(path: Path) -> dict[str, str]:
    """@brief Parse the scalar YAML metadata used by native host loaders."""
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "---"
    closing = lines.index("---", 1)
    return {
        key.strip(): value.strip()
        for key, value in (line.split(":", 1) for line in lines[1:closing])
    }


def test_host_descriptors_use_one_contract_and_own_no_workflow_policy() -> None:
    """@brief Host resources translate transport without transitions/approval."""
    contract = json.loads((ADAPTERS / "contract.json").read_text(encoding="utf-8"))
    operations = [entry.operation for entry in operations_for("AEGIS")]

    assert contract["schema"] == "aegis.host_adapter.contract"
    assert contract["schema_version"] == 1
    assert contract["machine_response_schema"] == "aegis.machine.response"
    assert contract["operations"] == operations
    assert contract["max_next_actions"] == 3
    for host in HOSTS:
        descriptor = json.loads(
            (ADAPTERS / host / "adapter.json").read_text(encoding="utf-8")
        )
        assert descriptor["contract"] == "../contract.json"
        assert descriptor["dispatcher"] == [
            ".agentic/aegis/bin/aegis",
            "--format",
            "json",
        ]
        assert descriptor["operation_identifiers"] == "contract"
        assert descriptor["owns_transitions"] is False
        assert descriptor["owns_approvals"] is False


def test_native_host_guidance_routes_resume_through_stage_show() -> None:
    """@brief Each supported host reads bounded state and input contracts."""
    for host, path in NATIVE.items():
        guidance = path.read_text(encoding="utf-8")
        assert "stage-show" in guidance, host
        assert "stage.show" not in guidance, host
        assert "Stage instruction" in guidance, host
        assert "common findings" in guidance, host
        assert "recovery actions" in guidance, host
        assert "next actions" in guidance, host
        assert "help-show" in guidance, host
        assert "aegis.machine.input" in guidance, host
        assert "--input" in guidance, host
        assert "Do not infer" in guidance, host
        assert "approvals" in guidance and "skips" in guidance, host
        assert "waivers" in guidance, host
        assert "commit" in guidance and "outside AEGIS" in guidance, host


def test_native_host_guidance_uses_loader_metadata_and_canonical_starters() -> None:
    """@brief PR-HOST-001/002: starter files match each native loader contract."""
    expected = {
        "claude-code": {"name": "aegis"},
        "codex": {"name": "aegis"},
        "pi": {"name": "aegis"},
        "opencode": {"mode": "all"},
        "qwen-code": {},
    }
    for host, required in expected.items():
        metadata = front_matter(NATIVE[host])
        assert metadata.get("description"), host
        assert metadata | required == metadata, host
        assert NATIVE[host].read_bytes() == STARTERS[host].read_bytes(), host
    assert len({path.read_bytes() for path in NATIVE.values()}) == len(HOSTS)
    assert not (TEMPLATE / ".pi" / "agents" / "aegis.md").exists()

    manifest = tomllib.loads(
        (TEMPLATE / ".agentic" / "aegis" / "manifest.toml").read_text(
            encoding="utf-8"
        )
    )
    manifest_paths = {entry["path"] for entry in manifest["files"]}
    assert {
        path.relative_to(TEMPLATE / ".agentic" / "aegis").as_posix()
        for path in STARTERS.values()
    } <= manifest_paths
