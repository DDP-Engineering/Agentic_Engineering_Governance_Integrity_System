#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file doctor.py
@brief ``waegis doctor --repo PATH [--json]``: the plan §10.1 health-verdict
       check catalog (T6.1). Opens milestone M6.
@details **Doctor vs analyze (read this first).** ``waegis analyze``
         (T3.3) is the read-only subset — manifest/drift/inventory with no
         pass/fail verdicts, exit code reflects only whether the report could
         be produced. ``waegis doctor`` is the opposite: every check gets an
         attached health verdict (``ok``/``warn``/``fail``) and the exit code
         *is* the worst verdict found (0 healthy / 1 warnings / 2 failures),
         per plan §10.1. Do not conflate the two commands: doctor re-derives
         everything from the same building blocks analyze uses
         (:mod:`waegis.payload.manifest`), it does not reimplement manifest or
         drift computation.
@details **Check groups (plan §10.1 table), each a list of findings:**

         - **Machine** — re-runs :func:`waegis.probes.machine.probe_os_support`,
           :func:`waegis.probes.machine.probe_disk_space` (at ``--repo``'s
           path), :func:`waegis.probes.tools.probe_python`,
           :func:`waegis.probes.tools.probe_git`,
           :func:`waegis.probes.tools.probe_uv`. Network probes
           (``probes/network.py``) are deliberately **not** part of any doctor
           group — plan §10.1's table lists only python/git versions under
           "Machine", and no other group names a network check; inventing a
           place for one would be scope creep beyond the frozen table.
         - **Manifest** — a four-way state (mirrors T5.2's
           ``repo.prior-install`` routing, since
           :class:`waegis.payload.manifest.ManifestState` alone cannot tell
           "never installed" from "legacy pre-manifest install" — both are
           ``ABSENT``): valid (``ok``), invalid/corrupt (``fail`` — a real,
           actionable break), legacy (``.agentic`` present, no manifest file;
           ``warn``), none (no ``.agentic`` at all; ``warn``). Unlike
           ``repo.prior-install``'s single "legacy" routing bucket, doctor
           assigns *distinct* severities to invalid vs. legacy because a
           health report, not a routing decision, is the point. Also computes
           an ``update available`` finding (installed ``payload_version`` vs.
           the currently bundled payload's version via
           :func:`waegis.payload.locate.read_payload_version`): ``warn`` when
           the bundled payload is strictly newer, ``ok`` otherwise (including
           "cannot determine").
         - **Drift** — :func:`waegis.payload.manifest.compute_drift`; any
           modified/missing file is ``warn`` (drift alone does not mean
           broken). The full modified/missing lists travel on
           :attr:`DoctorReport.drift_detail` and appear in ``--json`` only
           (human view: counts), mirroring ``analyze``'s verbosity split.
         - **workflow.toml** — parses via ``tomllib`` (``fail`` if it cannot);
           every ``[source].roots``/``[tests].roots`` entry exists on disk
           (``warn`` per missing root — legitimately absent mid-adoption);
           write-zone alignment via
           :func:`waegis.repo.workflow_toml.verify_workflow_invariants`
           (``fail`` if it raises — re-used exactly, not reimplemented, per
           that function's own docstring inviting this reuse; an invariant
           break on an *installed* repo is a real foreign/manual edit, unlike
           T4.1's generation-time guard which prevents this at the source);
           ``[gates].test``/``[gates].lint`` non-empty (``warn`` each if
           empty); ``[components].manifest`` path exists (``warn`` if
           configured but missing).
         - **Runnability** — wrapper scripts present (``fail`` if either
           ``run.ps1``/``run.sh`` is missing) and the platform-appropriate one
           answers ``--help`` with exit 0 through the injected
           :class:`waegis.probes.runner.CommandRunner` (``fail`` otherwise);
           hook files present (``fail`` if any of the four core hooks is
           missing — a functional break); known agent adapter directories
           present (``warn`` per missing one — informational, not every repo
           uses every adapter). ``_wrapper_invocation``/``HOOK_FILES`` are
           imported from :mod:`waegis.commands.new` rather than re-derived,
           since T5.2 already factored them out generically for reuse by both
           wizard journeys; severities (fail for hooks, warn for adapters) are
           doctor-specific and computed locally rather than reusing
           ``new.py``'s single boolean ``_hooks_and_adapters_missing``
           predicate, which collapses both into one undifferentiated check.
         - **Journal** — the most recent
           :class:`waegis.engine.journal.Journal` recorded for this
           ``--repo`` path (scanned the same way T4.3's
           ``_find_prior_journal`` does, without the mode filter doctor has no
           reason to apply): completed (``ok``), stopped mid-run (``warn``,
           names the step), no prior journal at all (``ok`` — informational
           absence, not a failure).
@details **Exit codes.** Every finding's verdict maps to a severity
         (``ok``=0, ``warn``=1, ``fail``=2); the report's ``exit_code`` is the
         *worst* severity across every group (plan §10.1: 0 healthy / 1
         warnings-only / 2 at least one failure). A ``--repo`` that does not
         exist or is not a directory is a distinct, genuine operational
         failure and returns :data:`EXIT_REPO_NOT_FOUND` (3) — deliberately
         outside ``{0, 1, 2}`` so it can never be misread as a health verdict.
@details **``--json`` seam (new, frozen, WADORE-relevant per plan §5/§15
         D13).** ``{"repo": str, "overall_status": "ok"|"warn"|"fail",
         "exit_code": int, "groups": {"machine": [Finding, ...], "manifest":
         [Finding, ...], "drift": {"findings": [Finding, ...], "modified":
         [str, ...], "missing": [str, ...]}, "workflow_toml": [Finding, ...],
         "runnability": [Finding, ...], "journal": [Finding, ...]}}`` where
         ``Finding`` is ``{"name": str, "status": "ok"|"warn"|"fail",
         "detail": str, "guidance": str|null}`` — the same shape as
         :class:`waegis.io.reports.ProbeFindingRecord`, reused directly rather
         than inventing a parallel type. ``drift`` is the one group whose
         JSON carries structured data beyond a finding list (the full
         modified/missing file lists), a deliberate, documented exception.
         These field names are a public, frozen integration contract;
         changing them is a wizard MAJOR version bump.
@author Eng. Dan Dumitru Pasare
@date 2026-07-15
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import IO, Any, Mapping

from ..engine import STATUS_COMPLETED, Journal, waegis_home
from ..io.envelope import EXIT_OPERATIONAL, write_envelope
from ..io.reports import ProbeFindingRecord
from ..payload.locate import PayloadLocateError, locate_payload, read_payload_version
from ..payload.manifest import (
    DriftResult,
    Manifest,
    ManifestLoadResult,
    ManifestState,
    compute_drift,
    load_manifest,
)
from ..probes.machine import probe_disk_space, probe_os_support
from ..probes.runner import CommandRunner, SubprocessCommandRunner
from ..probes.tools import probe_git, probe_python, probe_uv
from ..repo.workflow_toml import InvariantViolationError, verify_workflow_invariants
from ..version import _parse_version
from ..verification import HOOK_FILES, SMOKE_TIMEOUT_SECONDS, wrapper_invocation
from .analyze import ADAPTER_DIR_NAMES
from .new import MIN_FREE_DISK_BYTES

# CONSTANTS

# @brief Repo-relative path of the generated configuration surface.
WORKFLOW_TOML_RELATIVE_PATH = ".agentic/workflow.toml"

# @brief Repo-relative directory whose presence marks a prior/legacy install.
AGENTIC_DIR_RELATIVE_PATH = ".agentic"

# @brief Severity rank for aggregating findings into one worst-case verdict;
#        doubles as the exit code for that severity (plan §10.1: 0/1/2).
_SEVERITY_RANK: dict[str, int] = {"ok": 0, "warn": 1, "fail": 2}

# @brief Exit codes: the three health-verdict codes plus the operational one.
EXIT_OK = 0
EXIT_WARN = 1
EXIT_FAIL = 2
EXIT_REPO_NOT_FOUND = 3

# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True)
class DoctorReport:
    """
    @brief Full ``waegis doctor`` report: every plan §10.1 group's findings
           plus the aggregated exit code.
    @details ``drift_detail`` carries the full modified/missing lists
             (``--json``-only, per the human-counts/json-lists split); it is
             ``None`` exactly when drift was not computed (no valid manifest).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-15
    @version 0.1.0
    """

    repo: str
    machine: tuple[ProbeFindingRecord, ...]
    manifest: tuple[ProbeFindingRecord, ...]
    drift: tuple[ProbeFindingRecord, ...]
    drift_detail: DriftResult | None
    workflow_toml: tuple[ProbeFindingRecord, ...]
    runnability: tuple[ProbeFindingRecord, ...]
    journal: tuple[ProbeFindingRecord, ...]
    exit_code: int
    overall_status: str

    def all_findings(self) -> tuple[ProbeFindingRecord, ...]:
        """
        @brief      Every finding across every group, in group order.
        @return     Flattened tuple of every :class:`ProbeFindingRecord`.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-15
        @version    0.1.0
        """
        return (
            self.machine
            + self.manifest
            + self.drift
            + self.workflow_toml
            + self.runnability
            + self.journal
        )

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the whole report to the frozen ``--json`` shape.
        @return     Mapping keyed ``repo, overall_status, exit_code, groups``
                    (see module docstring for the full field-name contract).
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-15
        @version    0.1.0
        """
        drift_json: dict[str, Any] = {"findings": _findings_to_dicts(self.drift)}
        if self.drift_detail is not None:
            drift_json["modified"] = list(self.drift_detail.modified)
            drift_json["missing"] = list(self.drift_detail.missing)
        else:
            drift_json["modified"] = []
            drift_json["missing"] = []
        return {
            "repo": self.repo,
            "overall_status": self.overall_status,
            "exit_code": self.exit_code,
            "groups": {
                "machine": _findings_to_dicts(self.machine),
                "manifest": _findings_to_dicts(self.manifest),
                "drift": drift_json,
                "workflow_toml": _findings_to_dicts(self.workflow_toml),
                "runnability": _findings_to_dicts(self.runnability),
                "journal": _findings_to_dicts(self.journal),
            },
        }


# HELPER FUNCTIONS


def _findings_to_dicts(findings: tuple[ProbeFindingRecord, ...]) -> list[dict[str, Any]]:
    """
    @brief      Serialize a tuple of findings to the frozen JSON-safe list shape.
    @param[in]  findings Findings to serialize, in order.
    @return     List of ``{name, status, detail, guidance}`` mappings.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    return [
        {
            "name": f.name,
            "status": f.status,
            "detail": f.detail,
            "guidance": f.guidance,
            "repair_action": _repair_action(f),
        }
        for f in findings
    ]


def _repair_action(finding: ProbeFindingRecord) -> dict[str, Any] | None:
    """
    @brief      Map one unhealthy finding to a typed lifecycle action.
    @return     Action mapping or ``None`` when no mutation is appropriate.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    if finding.status == "ok":
        return None
    if finding.name == "drift.files":
        return {"type": "repair-managed-drift", "command": "repair"}
    if finding.name.startswith("workflow."):
        return {"type": "regenerate-configuration", "command": "configure"}
    if finding.name.startswith("runnability."):
        return {"type": "restore-runtime-files", "command": "repair"}
    if finding.name == "manifest.update-available":
        return {"type": "upgrade-payload", "command": "upgrade"}
    if finding.name == "manifest.state":
        return {"type": "reinstall-current-manifest", "command": "adopt"}
    return None


def _finding(name: str, status: str, detail: str, guidance: str | None = None) -> ProbeFindingRecord:
    """
    @brief      Build one doctor finding, normalizing a probe's ``"info"``
                status to ``"ok"`` (doctor's verdict vocabulary is exactly
                ``ok``/``warn``/``fail``).
    @param[in]  name Finding name (dotted, matches the underlying probe's name
                where one exists).
    @param[in]  status Raw status; ``"info"`` is folded into ``"ok"``.
    @param[in]  detail One-line human summary.
    @param[in]  guidance Optional fix-it text.
    @return     The built :class:`ProbeFindingRecord`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    normalized = "ok" if status == "info" else status
    return ProbeFindingRecord(name=name, status=normalized, detail=detail, guidance=guidance)


def _from_probe(finding: ProbeFindingRecord) -> ProbeFindingRecord:
    """
    @brief      Re-wrap a probe's own finding through :func:`_finding` so its
                status is normalized into doctor's verdict vocabulary.
    @param[in]  finding A finding returned directly by a ``probes/*`` function.
    @return     The normalized :class:`ProbeFindingRecord`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    return _finding(finding.name, finding.status, finding.detail, finding.guidance)


def _table(document: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    """
    @brief      Fetch ``document[key]`` as a mapping, degrading to ``{}``.
    @details    Guards against a hand-edited workflow.toml where a section
                that should be a table is some other TOML type.
    @param[in]  document Parsed TOML document.
    @param[in]  key Top-level section name.
    @return     ``document[key]`` when it is a mapping, else ``{}``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    value = document.get(key)
    return value if isinstance(value, Mapping) else {}


def _aggregate(*groups: tuple[ProbeFindingRecord, ...]) -> tuple[int, str]:
    """
    @brief      Aggregate every finding across every group into one worst-case
                verdict (plan §10.1: 0 healthy / 1 warnings / 2 failures).
    @param[in]  groups Every check group's finding tuple.
    @return     ``(exit_code, overall_status)``; ``(0, "ok")`` when no findings
                were produced at all.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    worst = 0
    for group in groups:
        for finding in group:
            worst = max(worst, _SEVERITY_RANK[finding.status])
    status_by_rank = {0: "ok", 1: "warn", 2: "fail"}
    return worst, status_by_rank[worst]


# --- group: Machine -----------------------------------------------------------


def _build_machine_findings(repo: Path, runner: CommandRunner) -> tuple[ProbeFindingRecord, ...]:
    """
    @brief      Machine group: re-run the P0/P1 machine and tool probes
                (plan §10.1: "P0/P1 probes re-run").
    @param[in]  repo Repository root (disk-space probe target).
    @param[in]  runner Injectable :class:`CommandRunner` for the tool probes.
    @return     Findings for ``machine.os``, ``machine.disk``,
                ``prereq.python``, ``prereq.git``, ``prereq.uv``.
    @exception  OSError If no ancestor of ``repo`` is accessible for the
                disk-space probe.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    return (
        _from_probe(probe_os_support()),
        _from_probe(probe_disk_space(repo, minimum_bytes=MIN_FREE_DISK_BYTES)),
        _from_probe(probe_python(runner)),
        _from_probe(probe_git(runner)),
        _from_probe(probe_uv(runner)),
    )


# --- group: Manifest ------------------------------------------------------------


def _build_update_available_finding(repo: Path, manifest: Manifest, payload_root: Path | None) -> ProbeFindingRecord:
    """
    @brief      ``manifest.update-available``: compare the installed
                ``payload_version`` against the currently bundled payload's
                version.
    @param[in]  repo Repository root (used only in the guidance text).
    @param[in]  manifest The loaded, valid install manifest.
    @param[in]  payload_root The resolved bundled payload root, or ``None``
                when no payload could be located.
    @return     ``"warn"`` when the bundled payload is strictly newer,
                ``"ok"`` otherwise (including "cannot determine").
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    if payload_root is None:
        return _finding("manifest.update-available", "ok", "bundled payload location unknown; update check skipped")
    bundled_version = read_payload_version(payload_root)
    if not bundled_version:
        return _finding("manifest.update-available", "ok", "bundled payload version unknown; update check skipped")
    try:
        is_newer = _parse_version(bundled_version) > _parse_version(manifest.payload_version)
    except ValueError:
        return _finding(
            "manifest.update-available",
            "ok",
            f"cannot compare versions (installed {manifest.payload_version!r}, bundled {bundled_version!r})",
        )
    if is_newer:
        return _finding(
            "manifest.update-available",
            "warn",
            f"update available: installed {manifest.payload_version}, bundled payload is {bundled_version}",
            guidance=f"run 'waegis upgrade --repo {repo}' to move to the newer payload",
        )
    return _finding(
        "manifest.update-available",
        "ok",
        f"up to date (installed {manifest.payload_version}, bundled {bundled_version})",
    )


def _build_manifest_findings(
    repo: Path, load_result: ManifestLoadResult, payload_root: Path | None
) -> tuple[ProbeFindingRecord, ...]:
    """
    @brief      Manifest group: the four-way state (plan §6, mirrors T5.2's
                ``repo.prior-install`` routing) plus ``update-available`` when
                a valid manifest is present.
    @param[in]  repo Repository root.
    @param[in]  load_result Result of :func:`waegis.payload.manifest.load_manifest`.
    @param[in]  payload_root The resolved bundled payload root, or ``None``.
    @return     One ``manifest.state`` finding, plus ``manifest.update-available``
                only when the manifest is valid.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    if load_result.state is ManifestState.VALID and load_result.manifest is not None:
        manifest = load_result.manifest
        state_finding = _finding(
            "manifest.state",
            "ok",
            f"install manifest present and valid (payload_version={manifest.payload_version}, "
            f"mode={manifest.mode}, files={len(manifest.files)})",
        )
        return (state_finding, _build_update_available_finding(repo, manifest, payload_root))

    if load_result.state is ManifestState.INVALID:
        return (
            _finding(
                "manifest.state",
                "fail",
                f"install manifest present but invalid: {load_result.error}",
                guidance="repair or remove the manifest, or re-run the wizard's payload-copy step "
                "to regenerate it",
            ),
        )

    agentic_present = (repo / AGENTIC_DIR_RELATIVE_PATH).is_dir()
    if agentic_present:
        return (
            _finding(
                "manifest.state",
                "warn",
                "no install manifest found; .agentic is present (legacy pre-manifest install)",
                guidance="drift/update checks are unavailable without a manifest; consider "
                "re-adopting with a current WAEGIS build to generate one",
            ),
        )
    return (
        _finding(
            "manifest.state",
            "warn",
            "no install manifest found and no .agentic directory (AEGIS does not appear to be "
            "installed here)",
            guidance="run 'waegis new' or 'waegis adopt' to install AEGIS",
        ),
    )


# --- group: Drift ----------------------------------------------------------------


def _build_drift_findings(
    repo: Path, load_result: ManifestLoadResult
) -> tuple[tuple[ProbeFindingRecord, ...], DriftResult | None]:
    """
    @brief      Drift group: local-vs-manifest-original drift (plan §10.1);
                any modified/missing file is ``warn``, never ``fail``.
    @param[in]  repo Repository root.
    @param[in]  load_result Result of :func:`waegis.payload.manifest.load_manifest`.
    @return     ``(findings, drift_detail)``; ``drift_detail`` is ``None``
                when no valid manifest exists to compare against.
    @exception  OSError If a manifest-recorded file cannot be hashed.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    if load_result.state is not ManifestState.VALID or load_result.manifest is None:
        return (
            (_finding("drift.files", "ok", "drift not computed (no valid manifest to compare against)"),),
            None,
        )
    drift = compute_drift(repo, load_result.manifest)
    if not drift.modified and not drift.missing:
        return ((_finding("drift.files", "ok", "no drift detected"),), drift)
    detail = f"{len(drift.modified)} modified, {len(drift.missing)} missing (vs. install manifest)"
    return (
        (
            _finding(
                "drift.files",
                "warn",
                detail,
                guidance="review with 'waegis analyze --repo PATH', then re-adopt or accept the drift",
            ),
        ),
        drift,
    )


# --- group: workflow.toml ---------------------------------------------------------


def _build_workflow_toml_findings(repo: Path) -> tuple[ProbeFindingRecord, ...]:
    """
    @brief      workflow.toml group: parse, root existence, write-zone
                invariants, gate emptiness, and the components manifest path
                (plan §10.1).
    @details    Re-uses :func:`waegis.repo.workflow_toml.verify_workflow_invariants`
                exactly (that function is public specifically for this reuse)
                rather than reimplementing invariant checking. If the file
                does not exist or does not parse, only ``workflow.parse`` is
                returned — the remaining checks are not applicable without a
                parsed document.
    @param[in]  repo Repository root.
    @return     Findings for ``workflow.parse``, and (when parsing succeeded)
                ``workflow.roots.source``, ``workflow.roots.test``,
                ``workflow.invariants``, ``workflow.gates.test``,
                ``workflow.gates.lint``, ``workflow.components-manifest``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    path = repo / WORKFLOW_TOML_RELATIVE_PATH
    if not path.is_file():
        return (
            _finding(
                "workflow.parse",
                "fail",
                f"{WORKFLOW_TOML_RELATIVE_PATH} not found",
                guidance="run 'waegis new' or 'waegis adopt' to install it",
            ),
        )
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return (_finding("workflow.parse", "fail", f"{WORKFLOW_TOML_RELATIVE_PATH} could not be parsed: {exc}"),)

    findings: list[ProbeFindingRecord] = [
        _finding("workflow.parse", "ok", f"{WORKFLOW_TOML_RELATIVE_PATH} parses as valid TOML")
    ]

    source_roots = [str(root) for root in _table(document, "source").get("roots", [])]
    test_roots = [str(root) for root in _table(document, "tests").get("roots", [])]

    missing_source = [root for root in source_roots if not (repo / root).is_dir()]
    if missing_source:
        findings.append(
            _finding(
                "workflow.roots.source",
                "warn",
                f"missing source root(s): {', '.join(missing_source)}",
                guidance="create the missing directories or update [source].roots",
            )
        )
    else:
        findings.append(_finding("workflow.roots.source", "ok", f"all {len(source_roots)} source root(s) exist"))

    missing_test = [root for root in test_roots if not (repo / root).is_dir()]
    if missing_test:
        findings.append(
            _finding(
                "workflow.roots.test",
                "warn",
                f"missing test root(s): {', '.join(missing_test)}",
                guidance="create the missing directories or update [tests].roots",
            )
        )
    else:
        findings.append(_finding("workflow.roots.test", "ok", f"all {len(test_roots)} test root(s) exist"))

    try:
        verify_workflow_invariants(document, source_roots=source_roots, test_roots=test_roots)
        findings.append(_finding("workflow.invariants", "ok", "write-zone invariants hold"))
    except InvariantViolationError as exc:
        findings.append(
            _finding(
                "workflow.invariants",
                "fail",
                str(exc),
                guidance="fix write_zones/traceability to match [source].roots/[tests].roots, or "
                "re-generate workflow.toml",
            )
        )

    gates = _table(document, "gates")
    test_cmds = gates.get("test", [])
    lint_cmds = gates.get("lint", [])
    findings.append(
        _finding(
            "workflow.gates.test",
            "ok" if test_cmds else "warn",
            f"gate 'test' has {len(test_cmds)} command(s)" if test_cmds else "gate 'test' is configured empty",
            guidance=None if test_cmds else "configure [gates].test",
        )
    )
    findings.append(
        _finding(
            "workflow.gates.lint",
            "ok" if lint_cmds else "warn",
            f"gate 'lint' has {len(lint_cmds)} command(s)" if lint_cmds else "gate 'lint' is configured empty",
            guidance=None if lint_cmds else "configure [gates].lint",
        )
    )

    components_path = _table(document, "components").get("manifest")
    if components_path:
        exists = (repo / str(components_path)).is_file()
        findings.append(
            _finding(
                "workflow.components-manifest",
                "ok" if exists else "warn",
                f"[components].manifest = {components_path!r} {'exists' if exists else 'is missing'}",
                guidance=None if exists else "restore the component manifest file or update [components].manifest",
            )
        )
    else:
        findings.append(_finding("workflow.components-manifest", "warn", "[components].manifest is not configured"))

    return tuple(findings)


# --- group: Runnability -----------------------------------------------------------


def _build_runnability_findings(repo: Path, runner: CommandRunner) -> tuple[ProbeFindingRecord, ...]:
    """
    @brief      Runnability group: wrapper scripts present and answer
                ``--help``, hook files present, known adapter directories
                present (plan §10.1).
    @param[in]  repo Repository root.
    @param[in]  runner Injectable :class:`CommandRunner` for the wrapper smoke
                invocation.
    @return     Findings for ``runnability.wrapper-files``,
                ``runnability.cli-smoke``, ``runnability.hooks``,
                ``runnability.adapters``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    findings: list[ProbeFindingRecord] = []

    wrapper_names = ("run.ps1", "run.sh")
    missing_wrappers = [name for name in wrapper_names if not (repo / ".agentic" / "tools" / name).is_file()]
    if missing_wrappers:
        findings.append(
            _finding(
                "runnability.wrapper-files",
                "fail",
                f"missing wrapper script(s): {', '.join(missing_wrappers)}",
                guidance="re-run the wizard's payload-copy step or restore the missing wrapper script(s)",
            )
        )
    else:
        findings.append(_finding("runnability.wrapper-files", "ok", "run.ps1 and run.sh are both present"))

    argv = wrapper_invocation(repo, "--help")
    result = runner.run(argv, timeout=SMOKE_TIMEOUT_SECONDS, cwd=repo)
    if result.ok():
        findings.append(_finding("runnability.cli-smoke", "ok", f"'{' '.join(argv)}' exited 0"))
    else:
        detail = result.combined_output().strip() if result.found else "the wrapper executable was not found"
        findings.append(
            _finding(
                "runnability.cli-smoke",
                "fail",
                f"'{' '.join(argv)}' failed: {detail or 'no output'}",
                guidance="confirm Python 3.11+ is on PATH for the wrapper, then re-run 'waegis doctor'",
            )
        )

    missing_hooks = [hook for hook in HOOK_FILES if not (repo / ".agentic" / "hooks" / hook).is_file()]
    if missing_hooks:
        findings.append(
            _finding(
                "runnability.hooks",
                "fail",
                f"missing hook file(s): {', '.join(missing_hooks)}",
                guidance="re-run the wizard's payload-copy step or restore the missing hook file(s)",
            )
        )
    else:
        findings.append(_finding("runnability.hooks", "ok", f"all {len(HOOK_FILES)} hook files present"))

    missing_adapters = [adapter for adapter in ADAPTER_DIR_NAMES if not (repo / adapter).is_dir()]
    if missing_adapters:
        findings.append(
            _finding(
                "runnability.adapters",
                "warn",
                f"missing adapter directory(ies): {', '.join(missing_adapters)}",
                guidance="restore the missing adapter directory(ies) if that agent client is in use",
            )
        )
    else:
        findings.append(
            _finding("runnability.adapters", "ok", f"all {len(ADAPTER_DIR_NAMES)} known adapter directories present")
        )

    return tuple(findings)


# --- group: Journal ----------------------------------------------------------------


def _latest_journal_for_repo(home: Path, repo: Path) -> Journal | None:
    """
    @brief      Find the latest recorded (non-dry-run) journal for this repo.
    @details    Scans ``<home>/journals/*.json`` newest-first (run ids are
                lexicographically sortable timestamps), mirroring
                ``commands/new.py``'s ``_find_prior_journal`` but without its
                mode filter — doctor reports the last run regardless of
                whether it was ``new`` or ``adopt``. Unreadable or corrupt
                journals are skipped, never fatal.
    @param[in]  home WAEGIS home directory.
    @param[in]  repo Resolved repository path.
    @return     The loaded latest :class:`Journal`, or ``None``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    journals_dir = home / "journals"
    if not journals_dir.is_dir():
        return None
    target = str(repo)
    for path in sorted(journals_dir.glob("*.json"), reverse=True):
        try:
            journal = Journal.load(path)
        except Exception:  # noqa: BLE001 - a corrupt journal must never block doctor
            continue
        if not journal.dry_run and journal.target == target:
            return journal
    return None


def _build_journal_findings(repo: Path, home: Path) -> tuple[ProbeFindingRecord, ...]:
    """
    @brief      Journal group: whether the last wizard run for this repo
                completed, or names the step it stopped at (plan §10.1).
    @param[in]  repo Resolved repository path.
    @param[in]  home WAEGIS home directory.
    @return     One ``journal.last-run`` finding.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    journal = _latest_journal_for_repo(home, repo)
    if journal is None:
        return (_finding("journal.last-run", "ok", "no prior wizard run journal found for this repository"),)
    if journal.status == STATUS_COMPLETED:
        return (_finding("journal.last-run", "ok", f"last run ({journal.run_id}, mode={journal.mode}) completed"),)
    stopped = f", stopped at step '{journal.stopped_at_step}'" if journal.stopped_at_step else ""
    return (
        _finding(
            "journal.last-run",
            "warn",
            f"last run ({journal.run_id}, mode={journal.mode}) did not complete (status={journal.status}{stopped})",
            guidance="re-run the wizard to finish the interrupted install",
        ),
    )


# --- rendering -----------------------------------------------------------------


def _render_group(stream: IO[str], title: str, findings: tuple[ProbeFindingRecord, ...]) -> None:
    """
    @brief      Render one group's findings as an indented, plain-ASCII-safe
                block (mirrors ``analyze``'s human-report style).
    @param[in]  stream Output stream.
    @param[in]  title Human-readable group title.
    @param[in]  findings The group's findings, in order.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    stream.write(f"{title}:\n")
    for finding in findings:
        stream.write(f"  [{finding.status}] {finding.name}: {finding.detail}\n")
        if finding.guidance:
            stream.write(f"      guidance: {finding.guidance}\n")
    stream.write("\n")


# PUBLIC API


def build_doctor_report(
    repo: str | PathLike[str],
    *,
    runner: CommandRunner | None = None,
    home: Path | None = None,
) -> DoctorReport:
    """
    @brief      Compute the full ``waegis doctor`` report for a repo root.
    @details    Pure data computation, separable from rendering/exit-code
                emission (same split ``commands/analyze.py`` uses). Assumes
                ``repo`` already exists and is a directory — callers
                (:func:`run_doctor`) validate that first.
    @param[in]  repo Repository root directory to diagnose.
    @param[in]  runner Injectable :class:`CommandRunner` for the tool probes
                and the wrapper smoke check; defaults to the real subprocess
                runner.
    @param[in]  home Override WAEGIS home directory (tests); defaults to
                :func:`waegis.engine.waegis_home`.
    @return     The computed :class:`DoctorReport`, exit code included.
    @exception  OSError If a manifest-recorded file cannot be hashed during
                drift computation, or no ancestor of ``repo`` is accessible
                for the disk-space probe.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    repo_path = Path(repo).resolve()
    active_runner = runner if runner is not None else SubprocessCommandRunner()
    active_home = home if home is not None else waegis_home()

    machine = _build_machine_findings(repo_path, active_runner)

    load_result = load_manifest(repo_path)
    try:
        payload_root = locate_payload()
    except PayloadLocateError:
        payload_root = None
    manifest = _build_manifest_findings(repo_path, load_result, payload_root)

    drift, drift_detail = _build_drift_findings(repo_path, load_result)
    workflow_toml = _build_workflow_toml_findings(repo_path)
    runnability = _build_runnability_findings(repo_path, active_runner)
    journal = _build_journal_findings(repo_path, active_home)

    exit_code, overall_status = _aggregate(machine, manifest, drift, workflow_toml, runnability, journal)

    return DoctorReport(
        repo=str(repo_path),
        machine=machine,
        manifest=manifest,
        drift=drift,
        drift_detail=drift_detail,
        workflow_toml=workflow_toml,
        runnability=runnability,
        journal=journal,
        exit_code=exit_code,
        overall_status=overall_status,
    )


def render_doctor_report(report: DoctorReport, stream: IO[str]) -> None:
    """
    @brief      Render a :class:`DoctorReport` as a plain-ASCII-safe human
                report, grouped in plan §10.1 table order.
    @details    Drift shows counts only; the full modified/missing lists are
                ``--json``-only (:func:`doctor_report_json`).
    @param[in]  report The report to render.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    stream.write(f"WAEGIS doctor - {report.repo}\n\n")
    _render_group(stream, "Machine", report.machine)
    _render_group(stream, "Manifest", report.manifest)
    _render_group(stream, "Drift", report.drift)
    if report.drift_detail is not None:
        stream.write(f"  modified: {len(report.drift_detail.modified)} file(s)\n")
        stream.write(f"  missing:  {len(report.drift_detail.missing)} file(s)\n\n")
    _render_group(stream, "workflow.toml", report.workflow_toml)
    _render_group(stream, "Runnability", report.runnability)
    _render_group(stream, "Journal", report.journal)
    stream.write(f"Overall: {report.overall_status} (exit {report.exit_code})\n")


def doctor_report_json(report: DoctorReport) -> str:
    """
    @brief      Serialize a :class:`DoctorReport` to the frozen ``--json``
                shape (see module docstring for the full field-name contract).
    @param[in]  report The report to serialize.
    @return     JSON text, 2-space indent.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)


def run_doctor(
    repo: str | PathLike[str],
    *,
    as_json: bool,
    stream: IO[str],
    runner: CommandRunner | None = None,
    home: Path | None = None,
) -> int:
    """
    @brief      Entry point for ``waegis doctor --repo PATH [--json]``.
    @details    Unlike ``run_analyze``, the returned exit code reflects the
                worst health verdict found (0/1/2), not merely whether the
                report could be produced — see module docstring.
    @param[in]  repo Repository root directory to diagnose.
    @param[in]  as_json When true, render the frozen ``--json`` shape instead
                of the human report.
    @param[in]  stream Output stream (real console or injected buffer for tests).
    @param[in]  runner Injectable :class:`CommandRunner`; defaults to the real
                subprocess runner.
    @param[in]  home Override WAEGIS home directory (tests).
    @return     :data:`EXIT_REPO_NOT_FOUND` (3) when ``repo`` does not exist or
                is not a directory; otherwise the report's aggregated exit
                code (0/1/2).
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-15
    @version    0.1.0
    """
    repo_path = Path(repo)
    if not repo_path.is_dir():
        message = f"--repo path does not exist or is not a directory: {repo_path}"
        if as_json:
            return write_envelope(stream, "doctor", status="error", exit_code=EXIT_OPERATIONAL, messages=(message,))
        stream.write(f"waegis doctor: {message}\n")
        return EXIT_OPERATIONAL

    report = build_doctor_report(repo_path, runner=runner, home=home)
    if as_json:
        status = {0: "ok", 1: "warning", 2: "failed"}[report.exit_code]
        return write_envelope(
            stream,
            "doctor",
            status=status,
            exit_code=report.exit_code,
            result=report.to_dict(),
        )
    else:
        render_doctor_report(report, stream)
    return report.exit_code


# END OF FILE
