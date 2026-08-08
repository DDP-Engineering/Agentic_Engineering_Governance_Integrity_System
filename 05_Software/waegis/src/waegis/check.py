#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file check.py
@brief Deterministic read-only WAEGIS/AEGIS installation health inspection.
@details Uses the installed AEGIS wrapper as the configuration/status oracle
         and limits strict adapter parsing to the documented Codex format.
"""

# IMPORTS

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .drift import inspect_drift, ownership_counts
from .gitsafety import require_repository
from .locate import PAYLOAD_VERSION_FILE, resolve_payload
from .manifest import MANIFEST_PATH, ManifestError, detect_manifest_version, load_manifest
from .ownership import Disposition
from .publication import NO_ACTIVE_RUN_MARKER, SMOKE_TIMEOUT, STATUS_KEYS, wrapper_invocation
from .runner import Runner
from .runtime import pointer_health
from .version import is_payload_compatible, parse_semver


# CONSTANTS

REQUIRED_HOOKS = (
    "delivery_preflight.py",
    "guard_read_path.py",
    "guard_shell_write.py",
    "guard_write_zone.py",
    "post_tool_evidence.py",
    "secret_scan.py",
)


# DATA MODELS / TYPEDEFINITIONS


@dataclass(frozen=True, slots=True)
class Finding:
    """@brief One stable warning/failure with exact operator guidance."""

    code: str
    severity: str
    message: str
    path: str | None = None
    action: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "action": self.action,
        }


@dataclass(frozen=True, slots=True)
class CheckResult:
    """@brief Complete V2-owned health result and exit behavior."""

    repository: Path
    manifest_status: str
    payload_version: str | None
    bundled_payload_version: str | None
    ownership: Mapping[str, int]
    findings: tuple[Finding, ...]

    @property
    def exit_code(self) -> int:
        if any(finding.severity == "failure" for finding in self.findings):
            return 2
        if self.findings:
            return 1
        return 0

    def to_dict(self) -> dict[str, object]:
        return {
            "repository": str(self.repository),
            "manifest_status": self.manifest_status,
            "payload_version": self.payload_version,
            "bundled_payload_version": self.bundled_payload_version,
            "ownership": dict(self.ownership),
            "findings": [finding.to_dict() for finding in self.findings],
            "summary": {
                "warnings": sum(item.severity == "warning" for item in self.findings),
                "failures": sum(item.severity == "failure" for item in self.findings),
            },
        }


# HELPER FUNCTIONS


def _finding(code: str, severity: str, message: str, path: str | None = None, action: str | None = None) -> Finding:
    return Finding(code, severity, message, path, action)


def _valid_envelope(text: str) -> bool:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return False
    return isinstance(value, dict) and STATUS_KEYS.issubset(value)


def _wrapper_findings(repository: Path, runner: Runner) -> list[Finding]:
    findings: list[Finding] = []
    environment = {"AEGIS_PYTHON": sys.executable}
    commands = (
        ("WRAPPER-HELP", ("--help",)),
        ("CONFIG-INVALID", ("config", "validate", "--json")),
        ("STATUS-INCOHERENT", ("run", "status", "--json")),
    )
    for code, arguments in commands:
        try:
            result = runner.run(
                wrapper_invocation(repository, *arguments),
                cwd=repository,
                timeout=SMOKE_TIMEOUT,
                env=environment,
            )
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            findings.append(_finding(code, "failure", f"installed AEGIS wrapper could not run: {exc}", action="repair managed launch files"))
            continue
        if code == "WRAPPER-HELP":
            if result.returncode != 0:
                findings.append(_finding(code, "failure", "installed AEGIS wrapper --help failed", action="run waegis repair"))
        elif code == "CONFIG-INVALID":
            if result.returncode != 0 or not _valid_envelope(result.stdout):
                detail = result.stderr.strip() or result.stdout.strip()
                findings.append(_finding(code, "failure", f"AEGIS rejected workflow configuration: {detail}", ".agentic/workflow.toml", "run waegis configure"))
        else:
            coherent = (result.returncode == 0 and _valid_envelope(result.stdout)) or (
                result.returncode != 0 and NO_ACTIVE_RUN_MARKER in f"{result.stdout}\n{result.stderr}"
            )
            if not coherent:
                findings.append(_finding(code, "failure", "AEGIS run status was neither an active envelope nor RUN-POINTER-MISSING", action="inspect the installed runtime and run state"))
    return findings


def _adapter_findings(repository: Path, runner: Runner) -> list[Finding]:
    findings: list[Finding] = []
    codex = repository / ".codex" / "hooks.json"
    node_bridge = codex.is_file() or (repository / ".agentic" / "tools" / "run_hook.mjs").is_file()
    if codex.exists():
        try:
            value = json.loads(codex.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            findings.append(_finding("CODEX-HOOKS-INVALID", "failure", f"Codex hooks JSON is invalid: {exc}", ".codex/hooks.json", "restore or correct the adapter"))
        else:
            if (
                not isinstance(value, dict)
                or set(value) != {"description", "hooks"}
                or not isinstance(value.get("description"), str)
                or not isinstance(value.get("hooks"), dict)
            ):
                findings.append(_finding("CODEX-HOOKS-INVALID", "failure", "Codex hooks must contain only description and hooks at top level", ".codex/hooks.json", "restore or correct the adapter"))
    if node_bridge:
        try:
            node = runner.run(("node", "--version"), cwd=repository, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            node = None
        if node is None or node.returncode != 0:
            findings.append(_finding("NODE-MISSING", "warning", "installed adapters use the Node bridge but Node is not resolvable", action="install Node or use an adapter that does not require the bridge"))
    return findings


def _root_findings(repository: Path) -> list[Finding]:
    path = repository / ".agentic" / "workflow.toml"
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
        roots = [*value["source"]["roots"], *value["tests"]["roots"]]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError):
        return []
    return [
        _finding("ROOT-MISSING", "warning", "configured source/test root does not exist", str(root), "create it or run waegis configure")
        for root in roots
        if not (repository / root).exists()
    ]


# EXPORTED FUNCTIONS / PUBLIC API


def check_repository(repository: Path, runner: Runner) -> CheckResult:
    """@brief Inspect one installation without changing repository or lock state."""
    root = require_repository(runner, repository)
    manifest_path = root.joinpath(*MANIFEST_PATH.split("/"))
    version = detect_manifest_version(manifest_path)
    if not manifest_path.exists():
        finding = _finding("MANIFEST-MISSING", "failure", "WAEGIS 3 install manifest is absent", MANIFEST_PATH, "run waegis adopt")
        return CheckResult(root, "absent", None, None, {}, (finding,))
    if version != 2:
        status = "v1" if version is not None else "invalid"
        action = "run waegis adopt with explicit V1 migration consent" if status == "v1" else "preserve and inspect the invalid manifest"
        finding = _finding("MANIFEST-UNSUPPORTED", "failure", f"install manifest is {status}, not schema 2", MANIFEST_PATH, action)
        return CheckResult(root, status, None, None, {}, (finding,))
    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        finding = _finding("MANIFEST-INVALID", "failure", str(exc), MANIFEST_PATH, "preserve and inspect the manifest")
        return CheckResult(root, "invalid", None, None, {}, (finding,))
    findings: list[Finding] = []
    for record in inspect_drift(root, manifest):
        if record.state == "clean":
            continue
        if record.disposition is Disposition.MANAGED:
            severity, code, action = "failure", "MANAGED-DRIFT", "run waegis repair"
        elif record.disposition is Disposition.GENERATED:
            severity, code, action = "failure", "CONFIG-DRIFT", "run waegis configure"
        else:
            severity, code, action = "warning", "PROJECT-OWNED-DRIFT", "review the project-owned path"
        findings.append(_finding(code, severity, f"{record.disposition.value} file is {record.state}", record.path, action))
    for hook in REQUIRED_HOOKS:
        path = f".agentic/hooks/{hook}"
        if not (root / ".agentic" / "hooks" / hook).is_file():
            findings.append(_finding("HOOK-MISSING", "failure", "required shared hook is missing", path, "run waegis repair"))
    findings.extend(_wrapper_findings(root, runner))
    findings.extend(_adapter_findings(root, runner))
    findings.extend(_root_findings(root))
    pointer_status, pointer_value = pointer_health()
    if pointer_status == "invalid":
        findings.append(_finding("RUNTIME-POINTER-INVALID", "warning", f"registered AEGIS runtime is unavailable: {pointer_value}", action="rerun a mutating command through the native WAEGIS launcher"))
    installed_path = root.joinpath(*PAYLOAD_VERSION_FILE.split("/"))
    installed_version: str | None = None
    try:
        installed_version = tomllib.loads(installed_path.read_text(encoding="utf-8"))["project"]["version"]
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, KeyError, TypeError):
        findings.append(_finding("VERSION-UNREADABLE", "failure", "installed payload version cannot be read", PAYLOAD_VERSION_FILE, "run waegis repair"))
    if installed_version != manifest.payload_version:
        findings.append(_finding("VERSION-MISMATCH", "failure", "installed payload version differs from the manifest", PAYLOAD_VERSION_FILE, "run waegis repair or upgrade"))
    elif installed_version is not None:
        try:
            compatible = is_payload_compatible(installed_version)
        except ValueError:
            compatible = False
        if not compatible:
            findings.append(_finding("VERSION-INCOMPATIBLE", "failure", "installed payload is outside the WAEGIS 3 compatibility range", PAYLOAD_VERSION_FILE, "use a compatible WAEGIS release"))
    bundled_version: str | None = None
    try:
        _, bundled_version, _ = resolve_payload()
    except ValueError:
        pass
    if installed_version and bundled_version:
        try:
            update_available = parse_semver(bundled_version)[:3] > parse_semver(installed_version)[:3]
        except ValueError:
            update_available = False
        if update_available:
            findings.append(_finding("UPDATE-AVAILABLE", "warning", f"compatible bundled payload {bundled_version} is newer than installed {installed_version}", action="review waegis upgrade --dry-run"))
    findings.sort(key=lambda item: (item.severity, item.code, item.path or ""))
    return CheckResult(root, "valid", manifest.payload_version, bundled_version, ownership_counts(manifest), tuple(findings))


# END OF FILE
