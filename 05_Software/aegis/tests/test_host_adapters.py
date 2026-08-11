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
from pathlib import Path

from aegis.application.operation_registry import operations_for

TEMPLATE = Path(__file__).parents[1] / "template"
ADAPTERS = TEMPLATE / ".agentic" / "aegis" / "adapters"
HOSTS = ("claude-code", "codex", "qwen-code", "opencode", "pi")


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
    """@brief Each supported host reads the same bounded selected-Stage state."""
    native = {
        "claude-code": TEMPLATE / ".claude" / "skills" / "aegis" / "SKILL.md",
        "codex": TEMPLATE / ".codex" / "skills" / "aegis" / "SKILL.md",
        "qwen-code": TEMPLATE / ".qwen" / "commands" / "aegis.md",
        "opencode": TEMPLATE / ".opencode" / "agents" / "aegis.md",
        "pi": TEMPLATE / ".pi" / "agents" / "aegis.md",
    }
    for host, path in native.items():
        guidance = path.read_text(encoding="utf-8")
        assert "stage.show" in guidance, host
        assert "aegis.machine.response" in guidance, host
        assert "Do not infer approval" in guidance, host
        assert "commit" in guidance and "outside AEGIS" in guidance, host
