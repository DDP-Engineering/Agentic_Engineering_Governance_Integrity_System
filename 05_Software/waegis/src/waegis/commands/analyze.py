#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file analyze.py
@brief ``waegis analyze --repo PATH [--json]``: the read-only manifest/drift/
       workflow-inventory report (T3.3).
@details Per plan §10.1, ``analyze`` is deliberately the **read-only subset**
         of ``doctor``: manifest inventory + drift + "which workflows are
         installed" — it renders **no health verdicts** (no pass/fail, no
         exit-code-encoded severity). That is ``doctor``'s job (T6.1). This
         module is a thin reporting layer over :mod:`waegis.payload.manifest`
         (``load_manifest``/``compute_drift``) — it never reimplements
         manifest parsing or drift computation.
@details **Exit code contract.** ``run_analyze`` returns 0 whenever the report
         was produced at all — a repo with no manifest, an invalid manifest,
         or drifted files is still a *successful* analyze run: those are
         informational findings, not command failures. Only a genuine
         operational failure (``--repo`` does not exist or is not a
         directory) returns non-zero.
@details **``--json`` seam (new, frozen per plan §5/§15 D13).** Field names
         below are a public, WADORE-relevant integration contract; changing
         them is a wizard MAJOR version bump.

         ``{"repo": str, "manifest": {"state": "absent"|"invalid"|"valid",
         "error": str|null, "product": str|null, "payload_version": str|null,
         "installed_at": str|null, "installed_by": str|null, "mode": str|null,
         "file_count": int|null, "generated_count": int|null,
         "skipped_count": int|null}, "drift": {"modified": [str, ...],
         "missing": [str, ...]} | null, "inventory": {"agentic_present": bool,
         "adapters": {<adapter-name>: bool, ...}}}``

         ``drift`` is ``null`` unless ``manifest.state == "valid"`` (drift is
         only computable against a valid manifest). ``inventory.adapters`` is
         keyed by adapter directory name with the leading dot stripped (e.g.
         ``"claude"`` for ``.claude/``).
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import json
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import IO, Any

from ..io.envelope import EXIT_OPERATIONAL, write_envelope
from ..payload.manifest import DriftResult, ManifestState, compute_drift, load_manifest
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..repo.analyze import ADAPTER_DIR_NAMES, analyze_repo

# CONSTANTS

# @brief Repo-relative path whose presence marks a legacy/current AEGIS
#        install, independent of whether an install manifest exists.
AGENTIC_DIR_RELATIVE_PATH = ".agentic"

# @brief Known agent adapter directory names shipped by the template payload
#        (plan §2 grounding list). Re-exported from :mod:`waegis.repo.analyze`,
#        the single source of truth (task T5.1), so this command and
#        ``commands/new.py`` (which imports it from here) stay in lockstep with
#        the analysis engine; ``tests/test_commands_analyze.py`` asserts the
#        value still matches the real ``05_Software/aegis/template/`` directory
#        so drift is caught rather than silently guessed at.

# @brief Exit code returned when ``--repo`` does not exist or is not a
#        directory — the one genuine operational failure this command has.
EXIT_REPO_NOT_FOUND = EXIT_OPERATIONAL

# @brief Exit code returned whenever the report was produced, regardless of
#        manifest state or drift findings (plan §10.1: those are
#        informational, not failures, at this command's level).
EXIT_OK = 0

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class ManifestSummary:
    """
    @brief One of the three manifest states (plan §6) plus the fields worth
           reporting for a present-and-valid manifest.
    @details Every field other than ``state`` is ``None`` unless
             ``state == "valid"``, except ``error`` which is set only for
             ``state == "invalid"``.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    state: str
    error: str | None = None
    product: str | None = None
    payload_version: str | None = None
    installed_at: str | None = None
    installed_by: str | None = None
    mode: str | None = None
    file_count: int | None = None
    generated_count: int | None = None
    skipped_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen ``manifest`` JSON-safe mapping.
        @return     Mapping keyed ``state, error, product, payload_version,
                    installed_at, installed_by, mode, file_count,
                    generated_count, skipped_count``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-13
        @version    0.1.0
        """
        return {
            "state": self.state,
            "error": self.error,
            "product": self.product,
            "payload_version": self.payload_version,
            "installed_at": self.installed_at,
            "installed_by": self.installed_by,
            "mode": self.mode,
            "file_count": self.file_count,
            "generated_count": self.generated_count,
            "skipped_count": self.skipped_count,
        }


@dataclass(frozen=True)
class AdapterInventory:
    """
    @brief "Which workflows installed" inventory: ``.agentic/`` presence plus
           per-adapter presence.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    agentic_present: bool
    adapters: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize to the frozen ``inventory`` JSON-safe mapping.
        @return     Mapping keyed ``agentic_present, adapters``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-13
        @version    0.1.0
        """
        return {"agentic_present": self.agentic_present, "adapters": dict(self.adapters)}


@dataclass(frozen=True)
class AnalyzeReport:
    """
    @brief Full ``waegis analyze`` report: manifest inventory, drift, and
           workflow inventory for one repo root.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-13
    @version 0.1.0
    """

    repo: str
    manifest: ManifestSummary
    drift: DriftResult | None
    inventory: AdapterInventory
    configuration_proposals: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the whole report to the frozen ``--json`` shape.
        @return     Mapping keyed ``repo, manifest, drift, inventory`` (see
                    module docstring for the full field-name contract).
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-13
        @version    0.1.0
        """
        drift_dict = None
        if self.drift is not None:
            drift_dict = {"modified": list(self.drift.modified), "missing": list(self.drift.missing)}
        return {
            "repo": self.repo,
            "manifest": self.manifest.to_dict(),
            "drift": drift_dict,
            "inventory": self.inventory.to_dict(),
            "configuration_proposals": dict(self.configuration_proposals),
        }


# LOCAL HELPERS


def _build_adapter_inventory(repo: Path) -> AdapterInventory:
    """
    @brief      Inspect ``repo`` for ``.agentic/`` and each known agent
                adapter directory.
    @param[in]  repo Repository root directory.
    @return     The built :class:`AdapterInventory`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    agentic_present = (repo / AGENTIC_DIR_RELATIVE_PATH).is_dir()
    adapters = {name.lstrip("."): (repo / name).is_dir() for name in ADAPTER_DIR_NAMES}
    return AdapterInventory(agentic_present=agentic_present, adapters=adapters)


def _manifest_summary_for_absent() -> ManifestSummary:
    """
    @brief      Build the manifest summary for the "no manifest found" state.
    @return     A :class:`ManifestSummary` with ``state="absent"``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    return ManifestSummary(state=ManifestState.ABSENT.value)


def _manifest_summary_for_invalid(error: str | None) -> ManifestSummary:
    """
    @brief      Build the manifest summary for the "present but invalid" state.
    @param[in]  error The validation error surfaced by ``load_manifest``.
    @return     A :class:`ManifestSummary` with ``state="invalid"`` and the
                error message preserved verbatim.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    return ManifestSummary(state=ManifestState.INVALID.value, error=error)


def _manifest_summary_for_valid(manifest) -> ManifestSummary:  # noqa: ANN001 - Manifest, avoid re-import churn
    """
    @brief      Build the manifest summary for the "present and valid" state.
    @param[in]  manifest The loaded :class:`~waegis.payload.manifest.Manifest`.
    @return     A :class:`ManifestSummary` with ``state="valid"`` and every
                reportable field populated.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    return ManifestSummary(
        state=ManifestState.VALID.value,
        product=manifest.product,
        payload_version=manifest.payload_version,
        installed_at=manifest.installed_at,
        installed_by=manifest.installed_by,
        mode=manifest.mode,
        file_count=len(manifest.files),
        generated_count=len(manifest.generated),
        skipped_count=len(manifest.skipped),
    )


# PUBLIC API


def build_analyze_report(
    repo: str | PathLike[str],
    *,
    runner: CommandRunner | None = None,
) -> AnalyzeReport:
    """
    @brief      Compute the ``waegis analyze`` report for a repo root.
    @details    Pure data computation, separable from rendering: calls
                ``load_manifest`` to distinguish absent/invalid/valid, calls
                ``compute_drift`` only when the manifest is valid, and
                inspects ``.agentic/`` plus each known adapter directory.
                Assumes ``repo`` already exists and is a directory — callers
                (``run_analyze``) validate that first.
    @param[in]  repo Repository root directory to analyze.
    @return     The computed :class:`AnalyzeReport`.
    @exception  OSError If a manifest-recorded file cannot be hashed during
                drift computation.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    repo_path = Path(repo)
    load_result = load_manifest(repo_path)

    manifest_summary: ManifestSummary
    drift: DriftResult | None = None
    if load_result.state is ManifestState.ABSENT:
        manifest_summary = _manifest_summary_for_absent()
    elif load_result.state is ManifestState.INVALID:
        manifest_summary = _manifest_summary_for_invalid(load_result.error)
    else:
        assert load_result.manifest is not None
        manifest_summary = _manifest_summary_for_valid(load_result.manifest)
        drift = compute_drift(repo_path, load_result.manifest)

    inventory = _build_adapter_inventory(repo_path)
    proposals: dict[str, Any] = {}
    try:
        analysis = analyze_repo(repo_path, runner=runner or SubprocessCommandRunner())
        proposals = {
            "source_roots": [item.to_dict() for item in analysis.source_roots],
            "test_roots": [item.to_dict() for item in analysis.test_roots],
            "language": analysis.language,
            **{
                f"gate_{name}_cmds": [
                    item.to_dict()
                    for item in getattr(analysis, f"gate_{name}_cmds")
                ]
                for name in ("build", "typecheck", "lint", "test", "security")
            },
        }
    except Exception as exc:  # noqa: BLE001 - proposals are best-effort, report remains useful
        proposals = {"error": str(exc)}
    return AnalyzeReport(
        repo=str(repo_path),
        manifest=manifest_summary,
        drift=drift,
        inventory=inventory,
        configuration_proposals=proposals,
    )


def render_analyze_report(report: AnalyzeReport, stream: IO[str]) -> None:
    """
    @brief      Render an :class:`AnalyzeReport` as a plain-ASCII-safe human
                report, mirroring ``io/console.py``'s encoding-safety
                convention (no glyphs, no reliance on non-CP1252 codepoints).
    @details    Counts only in the human view; :func:`analyze_report_json`
                carries the full modified/missing file lists (plan §10.1's
                stated human-vs-json verbosity split, which analyze follows).
    @param[in]  report The report to render.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    stream.write(f"WAEGIS analyze - {report.repo}\n")
    stream.write("\n")

    stream.write("Manifest:\n")
    manifest = report.manifest
    if manifest.state == ManifestState.ABSENT.value:
        stream.write("  no install manifest found (legacy install or never installed)\n")
    elif manifest.state == ManifestState.INVALID.value:
        stream.write("  manifest present but invalid\n")
        stream.write(f"  error: {manifest.error}\n")
    else:
        stream.write("  manifest present\n")
        stream.write(f"  product:         {manifest.product}\n")
        stream.write(f"  payload_version: {manifest.payload_version}\n")
        stream.write(f"  installed_at:    {manifest.installed_at}\n")
        stream.write(f"  installed_by:    {manifest.installed_by}\n")
        stream.write(f"  mode:            {manifest.mode}\n")
        stream.write(f"  files:           {manifest.file_count}\n")
        stream.write(f"  generated:       {manifest.generated_count}\n")
        stream.write(f"  skipped:         {manifest.skipped_count}\n")
    stream.write("\n")

    stream.write("Drift:\n")
    if report.drift is None:
        stream.write("  not computed (no valid manifest to compare against)\n")
    elif not report.drift.modified and not report.drift.missing:
        stream.write("  no drift detected\n")
    else:
        stream.write(f"  modified: {len(report.drift.modified)} file(s)\n")
        stream.write(f"  missing:  {len(report.drift.missing)} file(s)\n")
    stream.write("\n")

    stream.write("Workflow inventory:\n")
    stream.write(f"  .agentic present: {'yes' if report.inventory.agentic_present else 'no'}\n")
    name_width = max((len(name) for name in report.inventory.adapters), default=0)
    for name, present in report.inventory.adapters.items():
        stream.write(f"  .{name.ljust(name_width)} present: {'yes' if present else 'no'}\n")
    stream.write("\nConfiguration proposals:\n")
    if "error" in report.configuration_proposals:
        stream.write(f"  unavailable: {report.configuration_proposals['error']}\n")
    else:
        stream.write(f"  language: {report.configuration_proposals.get('language') or 'unknown'}\n")
        source = [item["path"] for item in report.configuration_proposals.get("source_roots", [])]
        tests = [item["path"] for item in report.configuration_proposals.get("test_roots", [])]
        stream.write(f"  source_roots: {', '.join(source) or '(none)'}\n")
        stream.write(f"  test_roots:   {', '.join(tests) or '(none)'}\n")


def analyze_report_json(report: AnalyzeReport) -> str:
    """
    @brief      Serialize an :class:`AnalyzeReport` to the frozen ``--json``
                shape (see module docstring for the full field-name contract).
    @param[in]  report The report to serialize.
    @return     JSON text, 2-space indent.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def run_analyze(repo: str | PathLike[str], *, as_json: bool, stream: IO[str]) -> int:
    """
    @brief      Entry point for ``waegis analyze --repo PATH [--json]``.
    @details    Per plan §10.1, this command renders no health verdicts: the
                exit code reflects only whether the report could be produced
                at all. A missing manifest, an invalid manifest, or drifted
                files are informational findings and still return 0; only a
                nonexistent/non-directory ``--repo`` is an operational failure.
    @param[in]  repo Repository root directory to analyze.
    @param[in]  as_json When true, render the frozen ``--json`` shape instead
                of the human report.
    @param[in]  stream Output stream (real console or injected buffer for
                tests).
    @return     :data:`EXIT_OK` (0) when the report was produced;
                :data:`EXIT_REPO_NOT_FOUND` (1) when ``repo`` does not exist or
                is not a directory.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.1.0
    """
    repo_path = Path(repo)
    if not repo_path.is_dir():
        message = f"--repo path does not exist or is not a directory: {repo_path}"
        if as_json:
            return write_envelope(stream, "analyze", status="error", exit_code=EXIT_REPO_NOT_FOUND, messages=(message,))
        stream.write(f"waegis analyze: {message}\n")
        return EXIT_REPO_NOT_FOUND

    report = build_analyze_report(repo_path)
    if as_json:
        return write_envelope(stream, "analyze", status="ok", exit_code=EXIT_OK, result=report.to_dict())
    else:
        render_analyze_report(report, stream)
    return EXIT_OK


# END OF FILE
