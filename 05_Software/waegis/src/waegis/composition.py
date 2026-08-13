#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Wire WAEGIS ports to independent standard-library infrastructure."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from waegis.application.lifecycle import Application
from waegis.domain.plans import PlanError
from waegis.infrastructure.git import LocalGitInitializer
from waegis.infrastructure.payload import PayloadManifest
from waegis.interface.cli import (
    configure_utf8,
    present_result,
    requested_output_format,
    run_cli,
)


def create_application(
    payload_root: Path, *, fault_after: int | None = None
) -> Application:
    """Construct an application from an already assembled payload directory."""
    return Application(
        PayloadManifest.load(payload_root.resolve()),
        LocalGitInitializer(),
        fault_after=fault_after,
    )


def bundled_payload_root() -> Path:
    """Locate payload data embedded beside the installed WAEGIS package."""
    package = Path(__file__).resolve().parent
    embedded = package / "payload" / ".agentic" / "aegis"
    if embedded.is_dir():
        return embedded
    development = package.parents[2] / "aegis" / "template" / ".agentic" / "aegis"
    return development


def main(
    argv: Sequence[str] | None = None,
    *,
    git_available: bool = True,
) -> int:
    """Run WAEGIS and ensure absent runtime data never produces a traceback."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    output_format = requested_output_format(arguments)
    configure_utf8(sys.stdout)
    try:
        app = create_application(bundled_payload_root())
    except PlanError as exc:
        if output_format == "json":
            result = Application.error_result(
                "unknown",
                "malformed_state",
                f"WAEGIS cannot start: {exc}",
            )
            return present_result(result, output_format)
        print(f"WAEGIS cannot start: {exc}", file=sys.stderr)
        return 4
    try:
        return run_cli(app, arguments, git_available=git_available)
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception:
        if output_format == "json":
            result = Application.error_result(
                "unknown",
                "internal_error",
                "WAEGIS failed before dispatch; no target success is claimed.",
            )
            return present_result(result, output_format)
        print(
            "WAEGIS failed before dispatch; no target success is claimed.",
            file=sys.stderr,
        )
        return 70


if __name__ == "__main__":
    raise SystemExit(main())
