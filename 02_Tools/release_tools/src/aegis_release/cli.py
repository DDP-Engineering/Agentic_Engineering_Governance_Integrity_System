#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Expose bounded build and inspection commands for local offline inputs."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from aegis_release.archives import BuildError, build_archive
from aegis_release.inspection import InspectionError, inspect_archive


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch the local archive build and inspection tools."""
    parser = argparse.ArgumentParser(prog="python -m aegis_release")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Build one offline release archive.")
    subparsers.add_parser("inspect", help="Inspect one release archive.")
    args, remainder = parser.parse_known_args(argv)
    if args.command == "build":
        return build_main(remainder)
    return inspect_main(remainder)


def build_main(argv: Sequence[str] | None = None) -> int:
    """Build one requested archive without downloading or guessing inputs."""
    parser = argparse.ArgumentParser(prog="aegis-build-archive")
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--product", choices=("aegis", "waegis"), required=True)
    parser.add_argument(
        "--platform",
        choices=("windows-x86_64", "ubuntu-22.04-x86_64"),
        required=True,
    )
    parser.add_argument("--with-dependencies", action="store_true")
    parser.add_argument("--runtime-lock", required=True)
    args = parser.parse_args(argv)
    try:
        archive = build_archive(
            Path(args.repository),
            Path(args.output),
            product=args.product,
            platform=args.platform,
            with_dependencies=args.with_dependencies,
            runtime_lock=Path(args.runtime_lock),
        )
    except BuildError as exc:
        print(f"Build refused: {exc}", file=sys.stderr)
        return 2
    print(archive)
    return 0


def inspect_main(argv: Sequence[str] | None = None) -> int:
    """Inspect one archive without extracting it."""
    parser = argparse.ArgumentParser(prog="aegis-inspect-archive")
    parser.add_argument("archive")
    args = parser.parse_args(argv)
    try:
        report = inspect_archive(Path(args.archive))
    except (InspectionError, OSError) as exc:
        print(f"Inspection failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0
