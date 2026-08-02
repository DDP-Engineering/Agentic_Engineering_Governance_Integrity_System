#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_adoption_workflow.py
@brief Grouped adoption inspection and baseline-policy tests.
@details The adoption stage sequence is exercised end to end in test_cli_v2;
         this module covers the retained read-only inspection commands.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path

import pytest

from aegis.cli import main

# TESTS


def test_adoption_component_status_and_baseline_use_stable_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Report component and baseline details inside the 2.0 envelope."""
    monkeypatch.chdir(tmp_path)
    _write_billing_manifest(tmp_path, "baseline-usable")
    main(["run", "start", "adoption", "--json"])
    capsys.readouterr()

    main(["adoption", "component-status", "--json"])
    status = json.loads(capsys.readouterr().out)
    assert tuple(status)[:4] == ("status", "stage", "artifact", "next")
    assert status["components"]["billing"]["adoption_status"] == "baseline-usable"

    main(["adoption", "baseline", "--json"])
    baseline = json.loads(capsys.readouterr().out)
    assert baseline["baseline"]["component_count"] == 1


def test_adoption_scope_check_blocks_unadopted_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Fail the grouped scope check for an unadopted mapped component."""
    replace_workflow_toml(
        '[components.baseline_guard]\nmode = "disabled"',
        '[components.baseline_guard]\nmode = "enforce"\n'
        'minimum_completion_level = "baseline-usable"',
    )
    _write_billing_manifest(tmp_path, "discovered")
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    capsys.readouterr()

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "adoption",
                "scope-check",
                "src/billing/invoice.py",
                "--json",
            ]
        )

    payload = json.loads(capsys.readouterr().out)
    assert raised.value.code == 1
    assert payload["status"] == "failed"
    assert payload["issues"][0]["code"] == "COMPONENT-BASELINE-MISSING"


def _write_billing_manifest(repo_root: Path, status: str) -> None:
    """@brief Write one component record for adoption command tests."""
    path = repo_root / ".agentic" / "components.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[components.billing]\n"
        'paths = ["src/billing"]\n'
        'tests = ["tests/billing/**"]\n'
        f'adoption_status = "{status}"\n'
        'criticality = "high"\n',
        encoding="utf-8",
    )


# END OF FILE
