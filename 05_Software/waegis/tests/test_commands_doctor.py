#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_doctor.py
@brief Tests for ``waegis doctor`` (T6.1): every plan §10.1 check group, the
       ok/warn/fail verdict-to-exit-code aggregation, and the ``--json``
       shape.
@details Strictly offline: the "healthy repo" fixture uses the real
         :func:`waegis.payload.copier.copy_payload` and
         :func:`waegis.repo.workflow_toml.generate_workflow_toml` (pure
         filesystem operations, no subprocess/network), while every tool
         probe and the wrapper smoke check go through a scripted
         :class:`FakeCommandRunner` — never a real subprocess. Journals are
         constructed directly via :class:`waegis.engine.Journal` with
         explicit sortable run ids so "latest journal" tests are never
         timing-flaky.
@author Eng. Dan Dumitru Pasare
@date 2026-07-15
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
from dataclasses import replace
from pathlib import Path

from waegis.commands.doctor import (
    EXIT_FAIL,
    EXIT_OK,
    EXIT_REPO_NOT_FOUND,
    EXIT_WARN,
    WORKFLOW_TOML_RELATIVE_PATH,
    _aggregate,
    build_doctor_report,
    render_doctor_report,
    run_doctor,
)
from waegis.commands.new import _amend_manifest_generated, _wrapper_invocation
from waegis.engine import STATUS_COMPLETED, STATUS_FAILED, Journal
from waegis.io.reports import ProbeFindingRecord
from waegis.payload.copier import copy_payload
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import read_manifest, write_manifest
from waegis.repo.workflow_toml import generate_workflow_toml

from _fake_command_runner import FakeCommandRunner, ok_result

# LOCAL HELPERS


def _install_healthy_repo(repo: Path, *, gates_configured: bool = True) -> None:
    """
    @brief      Build a fully healthy AEGIS install under ``repo`` using the
                real payload copier and workflow.toml generator.
    @param[in]  repo Empty, already-created target directory.
    @param[in]  gates_configured When ``True`` (default), configure non-empty
                ``[gates].test``/``[gates].lint`` so a healthy fixture is
                truly all-``ok``; ``False`` reproduces the "empty gates"
                scenario on an otherwise valid install.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = locate_payload()
    copy_payload(payload, repo, mode="new")
    base_text = (payload / WORKFLOW_TOML_RELATIVE_PATH).read_text(encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    gate_cmds = [["python", "-c", "pass"]] if gates_configured else []
    generated = generate_workflow_toml(
        base_text,
        source_roots=["src"],
        test_roots=["tests"],
        language="python",
        gate_test_cmds=gate_cmds,
        gate_lint_cmds=gate_cmds,
        alignment_enabled=True,
    )
    (repo / WORKFLOW_TOML_RELATIVE_PATH).write_text(generated.text, encoding="utf-8", newline="")
    _amend_manifest_generated(repo)


def _healthy_runner(repo: Path) -> FakeCommandRunner:
    """
    @brief      Build a :class:`FakeCommandRunner` scripted to answer every
                probe/smoke command a healthy repo needs as healthy.
    @param[in]  repo Target repository (determines the platform-appropriate
                wrapper invocation key via :func:`_wrapper_invocation`).
    @return     A scripted :class:`FakeCommandRunner`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return FakeCommandRunner(
        {
            ("py", "-3", "--version"): ok_result("Python 3.11.9"),
            ("git", "--version"): ok_result("git version 2.40.0"),
            _wrapper_invocation(repo, "--help"): ok_result(),
        }
    )


def _make_journal(
    home: Path,
    repo: Path,
    run_id: str,
    *,
    status: str,
    stopped_at_step: str | None = None,
) -> Journal:
    """
    @brief      Construct and finalize a journal directly with an explicit,
                sortable ``run_id`` so "latest journal" tests are deterministic.
    @param[in]  home WAEGIS home directory.
    @param[in]  repo Repository the journal targets.
    @param[in]  run_id Explicit run id (lexicographically sortable by caller).
    @param[in]  status Terminal run status.
    @param[in]  stopped_at_step Step id a stop occurred at, if any.
    @return     The finalized :class:`Journal`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = home / "journals" / f"{run_id}.json"
    journal = Journal(
        run_id=run_id,
        wizard_version="0.1.0",
        mode="new",
        target=str(Path(repo).resolve()),
        dry_run=False,
        started_at="2026-07-15T00:00:00Z",
        path=path,
    )
    journal.finalize(status=status, stopped_at_step=stopped_at_step)
    return journal


def _finding(report_findings, name: str) -> ProbeFindingRecord:
    """
    @brief      Fetch a specific named finding out of a group's finding tuple.
    @param[in]  report_findings A ``DoctorReport`` group's finding tuple.
    @param[in]  name The finding name to locate.
    @return     The matching :class:`ProbeFindingRecord`.
    @exception  StopIteration If no finding with that name exists.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return next(f for f in report_findings if f.name == name)


# TESTS

# --- healthy repo --------------------------------------------------------------


def test_healthy_repo_all_ok_exit_zero(tmp_path: Path) -> None:
    """
    @brief      A fully healthy install (real payload, valid manifest, no
                drift, valid workflow.toml, all hooks/wrappers present)
                reports every finding ``ok`` and exits 0.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert report.exit_code == EXIT_OK
    assert report.overall_status == "ok"
    assert report.all_findings(), "expected a non-empty finding set"
    for finding in report.all_findings():
        assert finding.status == "ok", f"{finding.name}: {finding.detail}"


# --- drift ------------------------------------------------------------------


def test_drift_present_exit_one_warn(tmp_path: Path) -> None:
    """
    @brief      One modified and one missing file vs. the manifest: the drift
                finding lists both (via ``drift_detail``), overall exit is 1
                (warn), and every other group stays ``ok``.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    manifest = read_manifest(repo)
    text_files = sorted(key for key in manifest.files if key.endswith((".md", ".py", ".toml")))
    modified_rel, missing_rel = text_files[0], text_files[1]
    modified_path = repo / modified_rel
    modified_path.write_text(modified_path.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    (repo / missing_rel).unlink()

    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert report.exit_code == EXIT_WARN
    drift_finding = _finding(report.drift, "drift.files")
    assert drift_finding.status == "warn"
    assert report.drift_detail is not None
    assert modified_rel in report.drift_detail.modified
    assert missing_rel in report.drift_detail.missing

    other = [f for f in report.all_findings() if f.name != "drift.files"]
    assert all(f.status == "ok" for f in other), [f for f in other if f.status != "ok"]


# --- update available ---------------------------------------------------------


def test_update_available_distinct_from_drift(tmp_path: Path) -> None:
    """
    @brief      A manifest recording a deliberately old ``payload_version``
                (older than the bundled payload's real version) reports
                ``manifest.update-available`` as ``warn`` while
                ``drift.files`` stays ``ok`` — the two findings are distinct.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    manifest = read_manifest(repo)
    write_manifest(repo, replace(manifest, payload_version="0.1.0"))

    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert report.exit_code == EXIT_WARN

    update_finding = _finding(report.manifest, "manifest.update-available")
    assert update_finding.status == "warn"
    assert "0.1.0" in update_finding.detail

    drift_finding = _finding(report.drift, "drift.files")
    assert drift_finding.status == "ok"


# --- workflow.toml: invariant violation -----------------------------------------


def test_workflow_toml_invariant_violation_exit_two_fail(tmp_path: Path) -> None:
    """
    @brief      A hand-edited installed workflow.toml that breaks write-zone
                alignment (``src/**`` dropped from
                ``[write_zones].implementation``) reports
                ``workflow.invariants`` as ``fail`` with the raised error text
                surfaced, and the overall exit is 2.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    workflow_path = repo / WORKFLOW_TOML_RELATIVE_PATH
    text = workflow_path.read_text(encoding="utf-8")
    broken = text.replace(
        'implementation = ["src/**", ".agentic/knowledge/components/**"]',
        'implementation = [".agentic/knowledge/components/**"]',
    )
    assert broken != text, "the expected implementation line was not found to break"
    workflow_path.write_text(broken, encoding="utf-8", newline="")

    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert report.exit_code == EXIT_FAIL
    invariants_finding = _finding(report.workflow_toml, "workflow.invariants")
    assert invariants_finding.status == "fail"
    assert "invariant 1" in invariants_finding.detail


# --- workflow.toml: empty gates ---------------------------------------------------


def test_missing_gates_warn_not_fail(tmp_path: Path) -> None:
    """
    @brief      Empty ``[gates].test``/``[gates].lint`` on an otherwise valid
                installed workflow.toml produces warn-level findings, not a
                hard failure.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo, gates_configured=False)

    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert _finding(report.workflow_toml, "workflow.gates.test").status == "warn"
    assert _finding(report.workflow_toml, "workflow.gates.lint").status == "warn"
    assert report.exit_code == EXIT_WARN


# --- runnability: missing hook file -----------------------------------------------


def test_missing_hook_file_exit_two_fail(tmp_path: Path) -> None:
    """
    @brief      Deleting one of the four core hook files after install
                reports ``runnability.hooks`` as ``fail`` naming that file,
                and the overall exit is 2.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    (repo / ".agentic" / "hooks" / "secret_scan.py").unlink()

    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert report.exit_code == EXIT_FAIL
    hooks_finding = _finding(report.runnability, "runnability.hooks")
    assert hooks_finding.status == "fail"
    assert "secret_scan.py" in hooks_finding.detail


# --- manifest: four-way state, reported distinctly --------------------------------


def test_manifest_state_none_vs_legacy_vs_invalid_reported_distinctly(tmp_path: Path) -> None:
    """
    @brief      "No manifest, no .agentic at all", "invalid/corrupt
                manifest", and "bare .agentic without manifest (legacy)" are
                three distinct manifest.state findings (mirrors T5.2's
                ``repo.prior-install`` four-way routing, adapted with
                doctor-specific severities: none/legacy warn, invalid fails).
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    none_repo = tmp_path / "none"
    none_repo.mkdir()
    none_report = build_doctor_report(none_repo, runner=_healthy_runner(none_repo), home=tmp_path / "home-none")
    none_finding = _finding(none_report.manifest, "manifest.state")

    legacy_repo = tmp_path / "legacy"
    legacy_repo.mkdir()
    (legacy_repo / ".agentic").mkdir()
    legacy_report = build_doctor_report(
        legacy_repo, runner=_healthy_runner(legacy_repo), home=tmp_path / "home-legacy"
    )
    legacy_finding = _finding(legacy_report.manifest, "manifest.state")

    invalid_repo = tmp_path / "invalid"
    invalid_repo.mkdir()
    (invalid_repo / ".agentic").mkdir()
    (invalid_repo / ".agentic" / "install-manifest.json").write_text("{not valid json", encoding="utf-8")
    invalid_report = build_doctor_report(
        invalid_repo, runner=_healthy_runner(invalid_repo), home=tmp_path / "home-invalid"
    )
    invalid_finding = _finding(invalid_report.manifest, "manifest.state")

    assert none_finding.status == "warn"
    assert "no .agentic directory" in none_finding.detail
    assert legacy_finding.status == "warn"
    assert "legacy pre-manifest install" in legacy_finding.detail
    assert invalid_finding.status == "fail"

    details = {none_finding.detail, legacy_finding.detail, invalid_finding.detail}
    assert len(details) == 3, "expected three distinct manifest-state messages"

    for report in (none_report, legacy_report, invalid_report):
        assert not any(f.name == "manifest.update-available" for f in report.manifest)


# --- journal group -----------------------------------------------------------------


def test_journal_group_absent_completed_and_stopped_reported_distinctly(tmp_path: Path) -> None:
    """
    @brief      No prior journal reports an informational absence (``ok``); a
                completed prior run reports ``ok``; a run that stopped
                mid-way reports ``warn`` naming the stopping step. The three
                are distinct.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    home = tmp_path / "home"

    absent_report = build_doctor_report(repo, runner=_healthy_runner(repo), home=home)
    absent_finding = _finding(absent_report.journal, "journal.last-run")
    assert absent_finding.status == "ok"
    assert "no prior wizard run journal" in absent_finding.detail

    _make_journal(home, repo, "20260101T000000Z-aaaaaa", status=STATUS_COMPLETED)
    completed_report = build_doctor_report(repo, runner=_healthy_runner(repo), home=home)
    completed_finding = _finding(completed_report.journal, "journal.last-run")
    assert completed_finding.status == "ok"
    assert "completed" in completed_finding.detail

    _make_journal(
        home, repo, "20260101T000100Z-bbbbbb", status=STATUS_FAILED, stopped_at_step="deploy.payload-copy"
    )
    stopped_report = build_doctor_report(repo, runner=_healthy_runner(repo), home=home)
    stopped_finding = _finding(stopped_report.journal, "journal.last-run")
    assert stopped_finding.status == "warn"
    assert "deploy.payload-copy" in stopped_finding.detail

    details = {absent_finding.detail, completed_finding.detail, stopped_finding.detail}
    assert len(details) == 3


# --- verdict aggregation (direct, not inferred from scenarios) ---------------------


def test_aggregate_all_ok_exit_zero() -> None:
    """
    @brief      Aggregating only ``ok`` findings across groups yields exit 0.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ok_group = (ProbeFindingRecord(name="a", status="ok", detail="x"),)
    exit_code, status = _aggregate(ok_group, ok_group)
    assert exit_code == EXIT_OK
    assert status == "ok"


def test_aggregate_one_warn_zero_fail_exit_one() -> None:
    """
    @brief      One ``warn`` finding among otherwise-``ok`` groups yields
                exit 1, never escalating to a fail.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ok_group = (ProbeFindingRecord(name="a", status="ok", detail="x"),)
    warn_group = (ProbeFindingRecord(name="b", status="warn", detail="y"),)
    exit_code, status = _aggregate(ok_group, warn_group, ok_group)
    assert exit_code == EXIT_WARN
    assert status == "warn"


def test_aggregate_one_fail_among_ok_warn_exit_two() -> None:
    """
    @brief      One ``fail`` finding among several ``ok``/``warn`` findings
                yields exit 2 — fail always wins the aggregation.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ok_group = (ProbeFindingRecord(name="a", status="ok", detail="x"),)
    warn_group = (ProbeFindingRecord(name="b", status="warn", detail="y"),)
    fail_group = (ProbeFindingRecord(name="c", status="fail", detail="z"),)
    exit_code, status = _aggregate(ok_group, warn_group, fail_group, ok_group)
    assert exit_code == EXIT_FAIL
    assert status == "fail"


# --- --repo not found ---------------------------------------------------------


def test_repo_not_found_is_a_distinct_exit_code(tmp_path: Path) -> None:
    """
    @brief      A ``--repo`` path that does not exist produces a clear error
                and an exit code distinct from every health-verdict code
                (0/1/2).
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    missing = tmp_path / "does-not-exist"
    stream = io.StringIO()
    exit_code = run_doctor(missing, as_json=False, stream=stream)
    assert exit_code == EXIT_REPO_NOT_FOUND
    assert exit_code not in (EXIT_OK, EXIT_WARN, EXIT_FAIL)
    assert stream.getvalue().strip() != ""


def test_repo_path_that_is_a_file_is_also_not_found(tmp_path: Path) -> None:
    """
    @brief      A ``--repo`` path that exists but is a file, not a directory,
                is also reported as the not-found operational failure.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    a_file = tmp_path / "not-a-dir.txt"
    a_file.write_text("x", encoding="utf-8")
    stream = io.StringIO()
    assert run_doctor(a_file, as_json=False, stream=stream) == EXIT_REPO_NOT_FOUND


# --- --json shape --------------------------------------------------------------


def test_json_output_is_valid_and_documented_for_healthy_repo(tmp_path: Path) -> None:
    """
    @brief      ``--json`` output for a healthy repo parses via ``json.loads``
                and carries every documented top-level/group/finding field.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    stream = io.StringIO()
    exit_code = run_doctor(repo, as_json=True, stream=stream, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert exit_code == EXIT_OK

    payload = json.loads(stream.getvalue())
    assert set(payload) == {"schema_version", "command", "status", "exit_code", "plan", "result", "messages"}
    assert payload["command"] == "doctor"
    assert payload["exit_code"] == 0
    report = payload["result"]
    assert report["overall_status"] == "ok"
    assert set(report["groups"]) == {"machine", "manifest", "drift", "workflow_toml", "runnability", "journal"}
    assert isinstance(report["groups"]["machine"], list)
    assert set(report["groups"]["drift"]) == {"findings", "modified", "missing"}
    for finding in report["groups"]["machine"]:
        assert set(finding) == {"name", "status", "detail", "guidance", "repair_action"}


def test_json_output_is_valid_and_documented_for_mixed_verdict(tmp_path: Path) -> None:
    """
    @brief      ``--json`` output for a mixed-verdict repo (empty gates,
                warn-level) parses via ``json.loads`` and reports the warn
                exit code and status consistently.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo, gates_configured=False)
    stream = io.StringIO()
    exit_code = run_doctor(repo, as_json=True, stream=stream, runner=_healthy_runner(repo), home=tmp_path / "home")
    assert exit_code == EXIT_WARN

    payload = json.loads(stream.getvalue())
    report = payload["result"]
    assert report["overall_status"] == "warn"
    assert payload["exit_code"] == 1
    gate_findings = [f for f in report["groups"]["workflow_toml"] if f["name"].startswith("workflow.gates")]
    assert gate_findings
    assert all(f["status"] == "warn" for f in gate_findings)


# --- human rendering does not crash and mentions every group ----------------------


def test_human_render_mentions_every_group_header(tmp_path: Path) -> None:
    """
    @brief      The human report includes every group header and the overall
                verdict line for a healthy repo.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _install_healthy_repo(repo)
    report = build_doctor_report(repo, runner=_healthy_runner(repo), home=tmp_path / "home")
    stream = io.StringIO()
    render_doctor_report(report, stream)
    text = stream.getvalue()
    for header in ("Machine:", "Manifest:", "Drift:", "workflow.toml:", "Runnability:", "Journal:", "Overall:"):
        assert header in text

# END OF FILE
