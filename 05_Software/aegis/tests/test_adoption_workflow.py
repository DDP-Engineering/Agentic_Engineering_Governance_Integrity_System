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
from typing import Any

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


def test_scope_check_separates_disabled_from_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Distinguish mapped, unmapped, and missing paths when disabled."""
    _write_billing_manifest(tmp_path, "baseline-usable")
    _write_source(tmp_path, "src/billing/invoice.py")
    _write_source(tmp_path, "tools/package_runtime.py")
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    capsys.readouterr()

    mapped = _scope_check(capsys, "src/billing/invoice.py")
    unmapped = _scope_check(capsys, "tools/package_runtime.py")
    missing = _scope_check(capsys, "does/not/exist.py")

    assert mapped["enforcement"] == "not-enforced"
    assert mapped["minimum_completion_level"] is None
    assert _codes(mapped) == ["COMPONENT-GUARD-NOT-ENFORCED"]
    assert _codes(unmapped) == [
        "COMPONENT-GUARD-NOT-ENFORCED",
        "COMPONENT-PATH-UNMAPPED",
    ]
    assert _codes(missing) == [
        "COMPONENT-GUARD-NOT-ENFORCED",
        "COMPONENT-PATH-NOT-FOUND",
    ]
    assert all(
        not issue["blocking"] and issue["severity"] == "advisory"
        for payload in (mapped, unmapped, missing)
        for issue in payload["issues"]
    )


def test_scope_check_separates_unmapped_from_clean_when_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Distinguish mapped, unmapped, and missing paths when enforced."""
    replace_workflow_toml(
        '[components.baseline_guard]\nmode = "disabled"',
        '[components.baseline_guard]\nmode = "enforce"\n'
        'minimum_completion_level = "baseline-usable"',
    )
    _write_billing_manifest(tmp_path, "baseline-usable")
    _write_source(tmp_path, "src/billing/invoice.py")
    _write_source(tmp_path, "tools/package_runtime.py")
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    capsys.readouterr()

    mapped = _scope_check(capsys, "src/billing/invoice.py")
    unmapped = _scope_check(capsys, "tools/package_runtime.py")
    missing = _scope_check(capsys, "does/not/exist.py")

    assert mapped["enforcement"] == "enforced"
    assert mapped["minimum_completion_level"] == "baseline-usable"
    assert _codes(mapped) == []
    assert _codes(unmapped) == ["COMPONENT-PATH-UNMAPPED"]
    assert _codes(missing) == ["COMPONENT-PATH-NOT-FOUND"]


def test_verify_coverage_reports_disabled_policy_as_not_enforced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Report a disabled coverage policy instead of an empty audit."""
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    capsys.readouterr()

    main(["verify", "coverage", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert payload["audit_status"] == "not-enforced"
    assert payload["issues"] == [
        {
            "status": "not-enforced",
            "message": "Not enforced - traceability.coverage.mode is disabled.",
        }
    ]


def test_coverage_waiver_seed_is_offered_before_it_is_written(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief List legacy uncovered modules and write them only on request."""
    replace_workflow_toml(
        '[traceability.coverage]\nmode = "disabled"\ncoverable_roots = []',
        '[traceability.coverage]\nmode = "enforce"\ncoverable_roots = ["src"]',
    )
    _write_source(tmp_path, "src/legacy.py")
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "adoption", "--json"])
    run_id = json.loads(capsys.readouterr().out)["run_id"]
    waiver_file = tmp_path / ".agentic" / "requirements" / "coverage_waivers.txt"

    main(["adoption", "coverage-waivers", "--json"])
    offered = json.loads(capsys.readouterr().out)["coverage_waivers"]
    assert offered == {
        "coverage_mode": "enforce",
        "uncovered": ["src/legacy.py"],
        "written": False,
    }
    assert not waiver_file.exists()

    main(["adoption", "coverage-waivers", "--write", "--json"])
    written = json.loads(capsys.readouterr().out)["coverage_waivers"]
    assert written["written"] is True
    assert written["waiver_file"] == ".agentic/requirements/coverage_waivers.txt"

    text = waiver_file.read_text(encoding="utf-8")
    assert "src/legacy.py" in text
    assert f"# Seeded from run {run_id}" in text

    main(["adoption", "coverage-waivers", "--json"])
    after = json.loads(capsys.readouterr().out)["coverage_waivers"]
    assert after["uncovered"] == []

    main(["verify", "coverage", "--json"])
    assert json.loads(capsys.readouterr().out)["issues"] == []


def test_coverage_waiver_seed_names_the_disabled_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@brief Say why a disabled coverage policy has nothing to seed."""
    _write_source(tmp_path, "src/legacy.py")
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "adoption", "--json"])
    capsys.readouterr()

    main(["adoption", "coverage-waivers", "--json"])
    offered = json.loads(capsys.readouterr().out)["coverage_waivers"]

    assert offered["coverage_mode"] == "disabled"
    assert offered["uncovered"] == []
    assert "after enabling coverage" in offered["note"]


def test_coverage_waiver_seed_appends_below_hand_written_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """@brief Preserve an existing waiver file when seeding below it."""
    replace_workflow_toml(
        '[traceability.coverage]\nmode = "disabled"\ncoverable_roots = []',
        '[traceability.coverage]\nmode = "enforce"\ncoverable_roots = ["src"]',
    )
    _write_source(tmp_path, "src/legacy.py")
    _write_source(tmp_path, "src/kept.py")
    waiver_file = tmp_path / ".agentic" / "requirements" / "coverage_waivers.txt"
    waiver_file.parent.mkdir(parents=True, exist_ok=True)
    waiver_file.write_text("# hand written\nsrc/kept.py\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "adoption", "--json"])
    capsys.readouterr()

    main(["adoption", "coverage-waivers", "--write", "--json"])
    capsys.readouterr()

    lines = waiver_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# hand written"
    assert lines[1] == "src/kept.py"
    assert lines[-1] == "src/legacy.py"
    assert lines.count("src/kept.py") == 1


def _scope_check(capsys: pytest.CaptureFixture[str], path: str) -> dict[str, Any]:
    """@brief Run one grouped scope check and return its parsed payload."""
    try:
        main(["adoption", "scope-check", path, "--json"])
    except SystemExit:
        pass
    return json.loads(capsys.readouterr().out)


def _codes(payload: dict[str, Any]) -> list[str]:
    """@brief Return the issue codes of one scope-check payload in order."""
    return [issue["code"] for issue in payload["issues"]]


def _write_source(repo_root: Path, relative_path: str) -> None:
    """@brief Create one placeholder source file for scope-check tests."""
    path = repo_root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("value = 1\n", encoding="utf-8")


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
