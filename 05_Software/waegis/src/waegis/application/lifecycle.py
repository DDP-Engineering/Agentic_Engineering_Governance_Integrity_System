#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Plan and apply repository initialization and payload lifecycle operations."""

from __future__ import annotations

import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from waegis.application.registry import OPERATIONS, operation_by_name
from waegis.domain.plans import (
    Action,
    PlanError,
    canonical_plan,
    parse_canonical_plan,
    plan_digest,
)
from waegis.domain.results import OperationResult, ProtocolError
from waegis.infrastructure.payload import PayloadManifest
from waegis.infrastructure.target import (
    configured_project_roots,
    configured_run_pointer,
    ensure_output_outside,
    git_directory,
    render_config,
    resolve_target,
    target_fingerprint,
)
from waegis.infrastructure.transactions import (
    PublicationInterrupted,
    TransactionPublisher,
)
from waegis.ports.services import GitInitializer
from waegis.version import WIZARD_VERSION

PLAN_SHOW_DEFAULT_LIMIT = 50
PLAN_SHOW_MAX_LIMIT = 100
PLAN_SHOW_MAX_PREREQUISITES = 20
PLAN_SHOW_MAX_WARNINGS = 20
PLAN_SHOW_MAX_TEXT = 500
HOST_GUIDANCE_STARTERS = (
    (
        "adapters/starters/claude-code/SKILL.md",
        ".claude/skills/aegis/SKILL.md",
    ),
    ("adapters/starters/codex/SKILL.md", ".codex/skills/aegis/SKILL.md"),
    ("adapters/starters/opencode/aegis.md", ".opencode/agents/aegis.md"),
    ("adapters/starters/pi/SKILL.md", ".pi/skills/aegis/SKILL.md"),
    ("adapters/starters/qwen-code/aegis.md", ".qwen/commands/aegis.md"),
)
ROOT_AGENTS_BEGIN = b"<!-- AEGIS:BEGIN (managed by WAEGIS) -->"
ROOT_AGENTS_END = b"<!-- AEGIS:END -->"
ROOT_AGENTS_BRIDGE = b"""<!-- AEGIS:BEGIN (managed by WAEGIS) -->
## AEGIS development workflow

For development tasks in this repository:

- use the repository-installed AEGIS workflow;
- read and follow `.agentic/rules.md`;
- treat AEGIS as guidance and a development record, not as a blocker to
  ordinary work; and
- keep commits, pushes, merges, and other outward Git actions under explicit
  developer direction.

<!-- AEGIS:END -->
"""


class Application:
    """Coordinate WAEGIS use cases through one bounded operation surface."""

    def __init__(
        self,
        payload: PayloadManifest,
        git: GitInitializer,
        *,
        fault_after: int | None = None,
    ) -> None:
        self.payload = payload
        self.git = git
        self.fault_after = fault_after

    def execute(self, operation: str, inputs: dict[str, Any]) -> OperationResult:
        """Dispatch one operation and convert all failures into protocol output."""
        operation_id = f"OP-{uuid.uuid4().hex}"
        definition = operation_by_name(operation)
        if definition is None:
            return self._error(
                operation, operation_id, "invalid_input", "Unknown operation"
            )
        missing = [name for name in definition.arguments if not inputs.get(name)]
        if missing:
            return self._error(
                definition.operation,
                operation_id,
                "invalid_input",
                f"Missing required input: {missing[0]}",
                field=missing[0],
            )
        try:
            if definition.operation == "help.show":
                return self._help(operation_id)
            if definition.operation == "version.show":
                return self._success(
                    definition.operation,
                    operation_id,
                    "WAEGIS version.",
                    {"version": WIZARD_VERSION},
                )
            if definition.operation == "plan.show":
                return self._show_plan(operation_id, inputs)
            if definition.operation.endswith(".plan"):
                return self._plan(definition.operation, operation_id, inputs)
            return self._apply(definition.operation, operation_id, inputs)
        except PublicationInterrupted as exc:
            return self._error(
                definition.operation,
                operation_id,
                "publication_failed",
                str(exc),
                retryable=True,
                details={"recovery_available": True},
            )
        except PlanError as exc:
            summary = str(exc)
            lowered = summary.lower()
            if any(
                word in lowered for word in ("digest", "changed", "different", "stale")
            ):
                code = "state_conflict"
            elif "manifest" in lowered or "recovery journal" in lowered:
                code = "malformed_state"
            elif "resolves outside" in lowered or "target must" in lowered:
                code = "repository_error"
            elif "already" in lowered:
                code = "invalid_transition"
            elif (
                "git" in lowered
                or "unavailable" in lowered
                or "not supplied" in lowered
            ):
                code = "missing_prerequisite"
            else:
                code = "invalid_input"
            return self._error(definition.operation, operation_id, code, summary)
        except Exception:
            return self._error(
                definition.operation,
                operation_id,
                "internal_error",
                "Unexpected WAEGIS failure; no target state was claimed successful.",
            )

    @staticmethod
    def error_result(
        operation: str, code: str, summary: str, *, field: str | None = None
    ) -> OperationResult:
        """Construct one outer-boundary error through the common result model."""
        return Application._error(
            operation,
            f"OP-{uuid.uuid4().hex}",
            code,
            summary,
            field=field,
        )

    def _plan(
        self, operation: str, operation_id: str, inputs: dict[str, Any]
    ) -> OperationResult:
        target = resolve_target(str(inputs["target"]))
        output = ensure_output_outside(target, str(inputs["output"]))
        if operation != "repository_init.plan" and git_directory(target) is None:
            raise PlanError(
                "Target is not a Git repository; authorize repository-init first"
            )
        if operation == "repository_init.plan":
            if (target / ".git").exists():
                raise PlanError("Target is already a Git repository")
            actions = [
                {"kind": "git_init", "path": ".git", "ownership": "repository_metadata"}
            ]
            warnings: list[str] = []
            modified: list[str] = []
        elif operation == "install.plan":
            actions, warnings = self._install_actions(target)
            modified = []
        elif operation == "upgrade.plan":
            installed = self._installed_manifest(target)
            actions, warnings = self._upgrade_actions(target, installed)
            modified = installed.modified_installed_paths(target)
        else:
            installed = self._installed_manifest(target)
            actions = [
                Action("delete", f".agentic/aegis/{path}", "payload").to_dict()
                for path in sorted(installed.files, reverse=True)
            ]
            warnings = []
            modified = installed.modified_installed_paths(target)
        plan = {
            "schema": "waegis.lifecycle.plan",
            "schema_version": 1,
            "operation": operation,
            "target": str(target),
            "target_fingerprint": target_fingerprint(target),
            "source_payload_version": self.payload.version,
            "actions": actions,
            "prerequisites": ["operator authorization by exact plan digest"],
            "warnings": warnings,
        }
        content = canonical_plan(plan)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(content)
        digest = plan_digest(content)
        return self._success(
            operation,
            operation_id,
            "Lifecycle plan written without modifying the target.",
            {
                "plan_digest": digest,
                "action_count": len(actions),
                "warnings": warnings,
                "modified_payload_paths": modified,
            },
            artifacts=(
                {"path": str(output), "sha256": digest.removeprefix("sha256:")},
            ),
        )

    def _apply(
        self, operation: str, operation_id: str, inputs: dict[str, Any]
    ) -> OperationResult:
        target = resolve_target(str(inputs["target"]))
        plan_path = Path(str(inputs["plan"])).resolve()
        try:
            plan_bytes = plan_path.read_bytes()
        except OSError as exc:
            raise PlanError("Plan is unavailable or invalid") from exc
        plan = parse_canonical_plan(plan_bytes)
        supplied = str(inputs["confirm_digest"])
        actual = plan_digest(plan_bytes)
        if supplied != actual:
            raise PlanError("Plan digest confirmation does not match exact plan bytes")
        expected_plan_operation = operation.removesuffix(".apply") + ".plan"
        if plan.get("operation") != expected_plan_operation or plan.get(
            "target"
        ) != str(target):
            raise PlanError(
                "Plan operation or target is different from this apply request"
            )
        publisher = TransactionPublisher(target, self.fault_after)
        if publisher.pending_digest() is not None:
            publisher.recover(actual)
            return self._success(
                operation,
                operation_id,
                "Interrupted publication recovered.",
                {"recovered": True},
            )
        if target_fingerprint(target) != plan.get("target_fingerprint"):
            raise PlanError("Target changed after planning; create a new plan")
        if operation == "repository_init.apply":
            self.git.initialize(target)
        else:
            publisher.apply(list(plan.get("actions", [])), actual)
        return self._success(
            operation,
            operation_id,
            "Authorized lifecycle plan applied.",
            {"action_count": len(plan.get("actions", [])), "plan_digest": actual},
        )

    def _show_plan(
        self, operation_id: str, inputs: dict[str, Any]
    ) -> OperationResult:
        """Return one bounded body-free page from an exact canonical plan."""
        plan_path = Path(str(inputs["plan"])).resolve()
        try:
            plan_bytes = plan_path.read_bytes()
        except OSError as exc:
            raise PlanError("Plan file cannot be read") from exc
        plan = parse_canonical_plan(plan_bytes)
        offset = self._page_value(inputs.get("offset"), "offset", default=0)
        limit = self._page_value(
            inputs.get("limit"), "limit", default=PLAN_SHOW_DEFAULT_LIMIT
        )
        if limit < 1 or limit > PLAN_SHOW_MAX_LIMIT:
            raise PlanError(
                f"Plan review limit must be between 1 and {PLAN_SHOW_MAX_LIMIT}"
            )
        actions = list(plan["actions"])
        if offset < 0 or offset > len(actions):
            raise PlanError("Plan review offset is outside the action list")
        page = actions[offset : offset + limit]
        summaries = [
            {
                "index": offset + index,
                "path": action["path"],
                "kind": action["kind"],
                "ownership": action["ownership"],
                "sha256": action.get("sha256"),
            }
            for index, action in enumerate(page)
        ]
        kind_counts = Counter(str(action["kind"]) for action in actions)
        ownership_counts = Counter(str(action["ownership"]) for action in actions)
        prerequisites = list(plan.get("prerequisites", []))
        warnings = list(plan.get("warnings", []))
        returned_prerequisites, prerequisites_truncated = self._bounded_texts(
            prerequisites, PLAN_SHOW_MAX_PREREQUISITES
        )
        returned_warnings, warnings_truncated = self._bounded_texts(
            warnings, PLAN_SHOW_MAX_WARNINGS
        )
        remaining = len(actions) - offset - len(summaries)
        omitted = len(actions) - len(summaries)
        truncated = (
            offset > 0
            or remaining > 0
            or prerequisites_truncated
            or warnings_truncated
        )
        digest = plan_digest(plan_bytes)
        return self._success(
            "plan.show",
            operation_id,
            "Canonical lifecycle plan summary.",
            {
                "plan_digest": digest,
                "plan_byte_count": len(plan_bytes),
                "planned_operation": plan["operation"],
                "target": plan["target"],
                "target_fingerprint": plan["target_fingerprint"],
                "source_payload_version": plan["source_payload_version"],
                "action_count": len(actions),
                "action_counts_by_kind": dict(sorted(kind_counts.items())),
                "action_counts_by_ownership": dict(
                    sorted(ownership_counts.items())
                ),
                "offset": offset,
                "limit": limit,
                "returned_count": len(summaries),
                "omitted_count": omitted,
                "next_offset": offset + len(summaries) if remaining > 0 else None,
                "actions": summaries,
                "prerequisite_count": len(prerequisites),
                "prerequisites": returned_prerequisites,
                "warning_count": len(warnings),
                "warnings": returned_warnings,
            },
            artifacts=(
                {"path": str(plan_path), "sha256": digest.removeprefix("sha256:")},
            ),
            truncated=truncated,
            details_ref=str(plan_path),
        )

    @staticmethod
    def _page_value(value: Any, field: str, *, default: int) -> int:
        """Parse one bounded plan-review page value."""
        if value in {None, ""}:
            return default
        try:
            return int(str(value), 10)
        except ValueError as exc:
            raise PlanError(f"Plan review {field} must be an integer") from exc

    @staticmethod
    def _bounded_texts(values: list[str], limit: int) -> tuple[list[str], bool]:
        """Bound plan metadata arrays and each returned text value."""
        returned = [value[:PLAN_SHOW_MAX_TEXT] for value in values[:limit]]
        truncated = len(values) > limit or any(
            len(value) > PLAN_SHOW_MAX_TEXT for value in values[:limit]
        )
        return returned, truncated

    def _install_actions(self, target: Path) -> tuple[list[dict[str, Any]], list[str]]:
        if (target / ".agentic/aegis/manifest.toml").exists():
            raise PlanError("AEGIS is already installed; use upgrade-plan")
        actions = [
            Action("write", f".agentic/aegis/{path}", "payload", content).to_dict()
            for path, content in sorted(self.payload.files.items())
        ]
        config, warnings = render_config(target)
        config_path = target / ".agentic/config.toml"
        if not config_path.exists():
            actions.append(
                Action("write", ".agentic/config.toml", "project", config).to_dict()
            )
        elif config_path.is_file():
            config = config_path.read_bytes()
        else:
            raise PlanError("Existing .agentic/config.toml is not a regular file")
        if not (target / ".agentic/rules.md").exists():
            rules = b"# Project-specific AEGIS rules\n\nAdd repository guidance here.\n"
            actions.append(
                Action("write", ".agentic/rules.md", "project", rules).to_dict()
            )
        host_actions, host_warnings = self._host_guidance_actions(target)
        actions.extend(host_actions)
        warnings.extend(host_warnings)
        root_agents_actions, root_agents_warnings = self._root_agents_actions(target)
        actions.extend(root_agents_actions)
        warnings.extend(root_agents_warnings)
        for root in configured_project_roots(config):
            root_path = target / root
            probe = root_path
            while not probe.exists() and probe != target:
                probe = probe.parent
            if root_path.is_dir():
                continue
            if probe.exists() and not probe.is_dir():
                warnings.append(
                    f"Configured project root is obstructed and was preserved: {root}."
                )
                continue
            actions.append(
                Action("write", f"{root}/.gitkeep", "project", b"").to_dict()
            )
        exclusion_actions, exclusion_warnings = self._exclusion_actions(target, config)
        actions.extend(exclusion_actions)
        warnings.extend(exclusion_warnings)
        return actions, warnings

    def _host_guidance_actions(
        self, target: Path
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Create missing project-owned native host starters from payload data."""
        actions: list[dict[str, Any]] = []
        warnings: list[str] = []
        for source, destination in HOST_GUIDANCE_STARTERS:
            try:
                content = self.payload.files[source]
            except KeyError as exc:
                raise PlanError(
                    f"Payload host guidance starter is unavailable: {source}"
                ) from exc
            path = target / destination
            if path.exists() or path.is_symlink():
                continue
            probe = path.parent
            while probe != target and not probe.exists() and not probe.is_symlink():
                probe = probe.parent
            if probe != target and (probe.is_symlink() or not probe.is_dir()):
                warnings.append(
                    "Host guidance destination is obstructed and was preserved: "
                    f"{destination}."
                )
                continue
            actions.append(Action("write", destination, "project", content).to_dict())
        return actions, warnings

    @staticmethod
    def _root_agents_actions(
        target: Path,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Prefix one discoverable AEGIS bridge without losing project guidance."""
        relative = "AGENTS.md"
        path = target / relative
        if path.is_symlink():
            return [], [
                "Root AGENTS.md is a symlink and was preserved without an AEGIS bridge."
            ]
        if not path.exists():
            return [
                Action("write", relative, "project", ROOT_AGENTS_BRIDGE).to_dict()
            ], []
        if not path.is_file():
            return [], [
                "Root AGENTS.md is not a regular file and was preserved without an "
                "AEGIS bridge."
            ]
        try:
            before = path.read_bytes()
        except OSError:
            return [], [
                "Root AGENTS.md could not be read and was preserved without an AEGIS "
                "bridge."
            ]
        if ROOT_AGENTS_BEGIN in before:
            if ROOT_AGENTS_END not in before:
                return [], [
                    "Root AGENTS.md contains an incomplete WAEGIS-managed AEGIS "
                    "bridge and was preserved for manual review."
                ]
            return [], []
        try:
            before.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            return [], [
                "Root AGENTS.md is not UTF-8 and was preserved without an AEGIS bridge."
            ]
        utf8_bom = b"\xef\xbb\xbf"
        continuation = (
            before[len(utf8_bom) :] if before.startswith(utf8_bom) else before
        )
        separator = b"\n" if continuation else b""
        after = ROOT_AGENTS_BRIDGE + separator + continuation
        return [Action("write", relative, "project", after).to_dict()], [
            "Existing root AGENTS.md guidance will continue after the added AEGIS "
            "bridge."
        ]

    @staticmethod
    def _append_exclusion_rules(
        before: bytes, additions: tuple[str, ...], *, path: str
    ) -> bytes:
        """Append missing rules without replacing any existing project content."""
        try:
            text = before.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise PlanError(f"Existing {path} is not UTF-8; it was preserved") from exc
        lines = text.splitlines()
        for addition in additions:
            if addition in lines:
                continue
            if text and not text.endswith(("\n", "\r")):
                text += "\n"
            text += addition + "\n"
            lines.append(addition)
        return text.encode("utf-8")

    def _exclusion_actions(
        self, target: Path, config: bytes
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Plan versioned and transitional repository-local exclusion updates."""
        repository_pointer, versioned_pointer = configured_run_pointer(config)
        actions: list[dict[str, Any]] = []
        warnings: list[str] = []
        versioned_path = target / ".agentic/.gitignore"
        versioned_before = (
            versioned_path.read_bytes() if versioned_path.is_file() else b""
        )
        versioned_rules = [".runtime/"]
        if versioned_pointer is None:
            warnings.append(
                "Configured Run pointer is outside .agentic; the versioned "
                ".agentic/.gitignore cannot cover it."
            )
        else:
            versioned_rules.append(versioned_pointer)
        versioned_after = self._append_exclusion_rules(
            versioned_before,
            tuple(versioned_rules),
            path=".agentic/.gitignore",
        )
        if versioned_after != versioned_before:
            actions.append(
                Action(
                    "write", ".agentic/.gitignore", "project", versioned_after
                ).to_dict()
            )

        if (target / ".git").is_file():
            warnings.append(
                "Linked Git worktree detected; shared info/exclude was not modified."
            )
            return actions, warnings
        exclude_path = target / ".git/info/exclude"
        before = exclude_path.read_bytes() if exclude_path.is_file() else b""
        after = self._append_exclusion_rules(
            before,
            (repository_pointer, ".agentic/.runtime/"),
            path=".git/info/exclude",
        )
        if after != before:
            actions.append(
                Action(
                    "write",
                    ".git/info/exclude",
                    "repository_local_exclusion",
                    after,
                ).to_dict()
            )
        return actions, warnings

    def _installed_manifest(self, target: Path) -> PayloadManifest:
        root = target / ".agentic/aegis"
        if not (root / "manifest.toml").is_file():
            raise PlanError("No installed manifest-owned AEGIS payload was found")
        return PayloadManifest.load(root, verify=False)

    def _upgrade_actions(
        self, target: Path, installed: PayloadManifest
    ) -> tuple[list[dict[str, Any]], list[str]]:
        actions = [
            Action("delete", f".agentic/aegis/{path}", "payload").to_dict()
            for path in sorted(
                set(installed.files) - set(self.payload.files), reverse=True
            )
        ]
        actions.extend(
            Action("write", f".agentic/aegis/{path}", "payload", content).to_dict()
            for path, content in sorted(self.payload.files.items())
        )
        config_path = target / ".agentic/config.toml"
        if config_path.is_file():
            config = config_path.read_bytes()
        elif config_path.exists():
            raise PlanError("Existing .agentic/config.toml is not a regular file")
        else:
            config, _ = render_config(target)
        exclusion_actions, warnings = self._exclusion_actions(target, config)
        host_actions, host_warnings = self._host_guidance_actions(target)
        actions.extend(host_actions)
        warnings.extend(host_warnings)
        root_agents_actions, root_agents_warnings = self._root_agents_actions(target)
        actions.extend(root_agents_actions)
        warnings.extend(root_agents_warnings)
        actions.extend(exclusion_actions)
        return actions, warnings

    def _help(self, operation_id: str) -> OperationResult:
        operations = [
            {
                "operation": entry.operation,
                "command": entry.command,
                "purpose": entry.purpose,
                "required_arguments": list(entry.arguments),
                "optional_arguments": list(entry.optional_arguments),
                "implemented": True,
            }
            for entry in OPERATIONS
        ]
        return self._success(
            "help.show", operation_id, "WAEGIS operations.", {"operations": operations}
        )

    @staticmethod
    def _success(
        operation: str,
        operation_id: str,
        message: str,
        data: dict[str, Any],
        *,
        artifacts: tuple[dict[str, Any], ...] = (),
        truncated: bool = False,
        details_ref: str | None = None,
    ) -> OperationResult:
        return OperationResult(
            operation,
            operation_id,
            "completed",
            message,
            data,
            artifacts=artifacts,
            truncated=truncated,
            details_ref=details_ref,
        )

    @staticmethod
    def _error(
        operation: str,
        operation_id: str,
        code: str,
        summary: str,
        *,
        field: str | None = None,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> OperationResult:
        return OperationResult(
            operation,
            operation_id,
            "error",
            summary,
            error=ProtocolError(
                code, summary, field=field, retryable=retryable, details=details or {}
            ),
        )
