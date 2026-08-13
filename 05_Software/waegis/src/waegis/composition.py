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
    requested_operation,
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
    operation = requested_operation(arguments)
    configure_utf8(sys.stdout)
    try:
        app = create_application(bundled_payload_root())
    except PlanError as exc:
        result = Application.error_result(
            operation,
            "malformed_state",
            f"WAEGIS cannot start: {exc}",
        )
        return present_result(result, output_format)
    except KeyboardInterrupt:
        result = Application.error_result(
            operation,
            "internal_error",
            "WAEGIS startup was interrupted; no target success is claimed.",
        )
        return present_result(result, output_format)
    except Exception:
        result = Application.error_result(
            operation,
            "internal_error",
            "WAEGIS could not compose the application; no target success is claimed.",
        )
        return present_result(result, output_format)
    try:
        return run_cli(app, arguments, git_available=git_available)
    except (KeyboardInterrupt, SystemExit):
        result = Application.error_result(
            operation,
            "internal_error",
            "WAEGIS stopped before dispatch; no target success is claimed.",
        )
        return present_result(result, output_format)
    except Exception:
        result = Application.error_result(
            operation,
            "internal_error",
            "WAEGIS failed before dispatch; no target success is claimed.",
        )
        return present_result(result, output_format)


if __name__ == "__main__":
    raise SystemExit(main())
