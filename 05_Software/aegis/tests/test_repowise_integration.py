#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repowise_integration.py
@brief Verify the optional RepoWise discovery-provider boundary.
@details Covers strict configuration, receipt/artifact validation, normalized
         adoption proposals, advisory behavior, and required freshness.
"""

# IMPORTS

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

import aegis.repowise as repowise_module
from aegis.config import load_config
from aegis.models import Graph, Intent, StageRecord
from aegis.repowise import (
    RepoWiseIntegrationError,
    inspect_repowise,
    load_repowise_integration,
)
from aegis.stage_forms import prepare_stage, stage_blockers

# CONSTANTS

_POLICY = """\
schema_version = 1
provider = "repowise"
mode = "{mode}"
source = "external"
version_spec = ">=0.37.0,<0.38.0"
artifact = ".repowise/knowledge-graph.json"
state = ".repowise/state.json"
require_head_match = true
require_worktree_match = true
"""

# TESTS


def test_absent_policy_is_disabled_and_strict_policy_rejects_unknown_keys(
    tmp_path: Path,
) -> None:
    """@brief Preserve absence-as-disabled while rejecting schema extensions."""
    assert load_repowise_integration(tmp_path).mode == "disabled"
    path = tmp_path / ".agentic" / "integrations" / "repowise.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _POLICY.format(mode="advisory") + 'unexpected = "value"\n',
        encoding="utf-8",
    )
    with pytest.raises(RepoWiseIntegrationError, match="unsupported key"):
        load_repowise_integration(tmp_path)


def test_current_artifacts_prepopulate_repo_discovery_and_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Import validated RepoWise proposals without executing RepoWise."""
    _write_integration_fixture(tmp_path, mode="advisory")
    monkeypatch.setattr(repowise_module, "repository_head", lambda root: "abc123")
    monkeypatch.setattr(
        repowise_module,
        "worktree_fingerprint",
        lambda root: "worktree-1",
    )
    graph = Graph(
        run_id="adoption-20260729T120000Z-1234abcd",
        stage="repo-discovery",
        intent=Intent(id="I-1", kind="adoption", statement="Adopt repository"),
    )

    form = prepare_stage(tmp_path, graph, load_config(tmp_path))
    text = form.read_text(encoding="utf-8")

    assert 'repowise_status = "current"' in text
    assert '"src/api.py"' in text
    assert '"src/api.py"' in text
    assert '"API"' in text
    assert '"FastAPI"' in text
    assert graph.stage_records["repo-discovery"].payload["candidate_components"] == [
        "API"
    ]
    snapshot = (
        tmp_path
        / ".agentic"
        / "runs"
        / graph.run_id
        / "discovery"
        / "repowise.json"
    )
    assert snapshot.is_file()
    assert json.loads(snapshot.read_text(encoding="utf-8"))["status"] == "current"


def test_required_stale_receipt_blocks_repo_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Block adoption closure only when RepoWise is explicitly required."""
    _write_integration_fixture(tmp_path, mode="required", receipt_head="old")
    monkeypatch.setattr(repowise_module, "repository_head", lambda root: "abc123")
    monkeypatch.setattr(
        repowise_module,
        "worktree_fingerprint",
        lambda root: "worktree-1",
    )
    graph = Graph(
        run_id="adoption-20260729T120000Z-1234abcd",
        stage="repo-discovery",
        intent=Intent(id="I-1", kind="adoption", statement="Adopt repository"),
        stage_records={
            "repo-discovery": StageRecord(
                stage="repo-discovery",
                revision=1,
                status="applied",
                retention="discard",
                check_execution="external",
                payload={"candidate_components": ["API"]},
            )
        },
    )

    blockers = stage_blockers(tmp_path, graph)

    assert any("required RepoWise discovery is not current" in item for item in blockers)
    assert inspect_repowise(tmp_path).status == "stale"


def test_stale_advisory_artifacts_do_not_prepopulate_or_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """@brief Stale advisory evidence warns without becoming discovery input."""
    _write_integration_fixture(tmp_path, mode="advisory", receipt_head="old")
    monkeypatch.setattr(repowise_module, "repository_head", lambda root: "abc123")
    monkeypatch.setattr(
        repowise_module,
        "worktree_fingerprint",
        lambda root: "worktree-1",
    )
    graph = Graph(
        run_id="adoption-20260729T120000Z-1234abcd",
        stage="repo-discovery",
        intent=Intent(id="I-1", kind="adoption", statement="Adopt repository"),
    )

    prepare_stage(tmp_path, graph, load_config(tmp_path))

    payload = graph.stage_records["repo-discovery"].payload
    assert payload["candidate_components"] == []
    assert payload["repowise_status"] == "stale"
    assert payload["repowise_warnings"]
    assert not (
        tmp_path
        / ".agentic"
        / "runs"
        / graph.run_id
        / "discovery"
        / "repowise.json"
    ).exists()


# LOCAL HELPERS


def _write_integration_fixture(
    repo_root: Path,
    *,
    mode: str,
    receipt_head: str = "abc123",
) -> None:
    """@brief Write matching policy, graph, state, and WAEGIS receipt fixtures."""
    integration = repo_root / ".agentic" / "integrations"
    provider = repo_root / ".repowise"
    integration.mkdir(parents=True, exist_ok=True)
    provider.mkdir(parents=True, exist_ok=True)
    (integration / "repowise.toml").write_text(
        _POLICY.format(mode=mode),
        encoding="utf-8",
    )
    graph = {
        "version": "1.0.0",
        "schema_version": 1,
        "project": {
            "name": "sample",
            "entry_points": ["src/api.py"],
            "tech_stack": [{"name": "FastAPI"}],
        },
        "nodes": [
            {
                "id": "file:src/api.py",
                "filePath": "src/api.py",
                "tags": ["entry_point"],
            },
            {
                "id": "file:tests/test_api.py",
                "filePath": "tests/test_api.py",
                "tags": ["test"],
            },
        ],
        "edges": [],
        "layers": [{"id": "layer:api", "name": "API", "nodeIds": ["file:src/api.py"]}],
        "tour": [],
    }
    state = {"last_sync_commit": "abc123"}
    graph_path = provider / "knowledge-graph.json"
    state_path = provider / "state.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    receipt = {
        "schema_version": 1,
        "provider": "repowise",
        "repowise_version": "0.37.0",
        "source": "external",
        "profile": "deterministic",
        "completed": True,
        "head": receipt_head,
        "worktree_fingerprint": "worktree-1",
        "artifact": ".repowise/knowledge-graph.json",
        "artifact_sha256": _digest(graph_path),
        "state": ".repowise/state.json",
        "state_sha256": _digest(state_path),
        "synced_at": "2026-07-29T12:00:00Z",
    }
    (integration / "repowise-receipt.json").write_text(
        json.dumps(receipt),
        encoding="utf-8",
    )


def _digest(path: Path) -> str:
    """@brief Hash one small test fixture."""
    return sha256(path.read_bytes()).hexdigest()


# END OF FILE
