#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Plan and apply repository initialization and payload lifecycle operations."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from waegis.application.registry import OPERATIONS, operation_by_name
from waegis.domain.plans import Action, PlanError, canonical_plan, plan_digest
from waegis.domain.results import OperationResult, ProtocolError
from waegis.infrastructure.payload import PayloadManifest
from waegis.infrastructure.target import (
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
            actions = self._upgrade_actions(installed)
            warnings = []
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
            plan = json.loads(plan_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise PlanError("Plan is unavailable or invalid") from exc
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

    def _install_actions(self, target: Path) -> tuple[list[dict[str, Any]], list[str]]:
        if (target / ".agentic/aegis/manifest.toml").exists():
            raise PlanError("AEGIS is already installed; use upgrade-plan")
        actions = [
            Action("write", f".agentic/aegis/{path}", "payload", content).to_dict()
            for path, content in sorted(self.payload.files.items())
        ]
        config, warnings = render_config(target)
        if not (target / ".agentic/config.toml").exists():
            actions.append(
                Action("write", ".agentic/config.toml", "project", config).to_dict()
            )
        if not (target / ".agentic/rules.md").exists():
            rules = b"# Project-specific AEGIS rules\n\nAdd repository guidance here.\n"
            actions.append(
                Action("write", ".agentic/rules.md", "project", rules).to_dict()
            )
        if not any((target / root).is_dir() for root in ("tests", "test")):
            actions.append(
                Action("write", ".agentic/tests/.gitkeep", "project", b"").to_dict()
            )
        if (target / ".git").is_file():
            warnings.append(
                "Linked Git worktree detected; shared info/exclude was not modified."
            )
            return actions, warnings
        exclude_path = target / ".git/info/exclude"
        before = exclude_path.read_bytes() if exclude_path.is_file() else b""
        text = before.decode("utf-8", errors="strict")
        additions = [".agentic/runs/context.toml", ".agentic/.runtime/"]
        for addition in additions:
            if addition not in text.splitlines():
                if text and not text.endswith("\n"):
                    text += "\n"
                text += addition + "\n"
        if text.encode("utf-8") != before:
            actions.append(
                Action(
                    "write",
                    ".git/info/exclude",
                    "repository_local_exclusion",
                    text.encode("utf-8"),
                ).to_dict()
            )
        return actions, warnings

    def _installed_manifest(self, target: Path) -> PayloadManifest:
        root = target / ".agentic/aegis"
        if not (root / "manifest.toml").is_file():
            raise PlanError("No installed manifest-owned AEGIS payload was found")
        return PayloadManifest.load(root, verify=False)

    def _upgrade_actions(self, installed: PayloadManifest) -> list[dict[str, Any]]:
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
        return actions

    def _help(self, operation_id: str) -> OperationResult:
        operations = [
            {
                "operation": entry.operation,
                "command": entry.command,
                "purpose": entry.purpose,
                "required_arguments": list(entry.arguments),
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
    ) -> OperationResult:
        return OperationResult(
            operation, operation_id, "completed", message, data, artifacts=artifacts
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
