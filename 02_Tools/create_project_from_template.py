#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file create_project_from_template.py
@brief Copy the bundled AEGIS payload into a target repository.
@details Supports both new-project bootstrap and safe existing-repository
         adoption. Existing files are never overwritten unless ``--force`` is
         supplied, and ``--dry-run`` can preview copied files without writing.
         Since T3.2 this script is a thin wrapper over the WAEGIS
         manifest-aware copier (``waegis.payload.copier``): the public flags
         and messages are unchanged, but every real (non-dry-run) copy now
         also writes ``<target>/.agentic/install-manifest.json`` recording the
         payload version and the sha256 of every copied file (plan §6, AD-6)
         so `waegis analyze`/`doctor`/`upgrade` can manage the install later.
         ``--dry-run`` writes nothing, including no manifest. An overwrite
         refusal now happens before any file is written, so a refused run
         leaves the target untouched (previously files earlier in the walk
         were already copied).
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.3.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The WAEGIS package (stdlib-only) lives in this repository; make it importable
# when this script runs straight from a checkout without an install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "05_Software" / "waegis" / "src"))

from waegis.payload.copier import (  # noqa: E402
    EXCLUDED_PARTS,
    EXCLUDED_PATTERNS,
    EXCLUDED_SUFFIXES,
    CopierError,
    copy_payload,
)
from waegis.payload.copier import should_exclude as _should_exclude  # noqa: E402

__all__ = [
    "TEMPLATE_ROOT",
    "EXCLUDED_PARTS",
    "EXCLUDED_SUFFIXES",
    "EXCLUDED_PATTERNS",
    "should_exclude",
    "copy_template",
    "main",
]

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "05_Software" / "aegis" / "template"


def should_exclude(path: Path) -> bool:
    """
    @brief      Return whether a template path is generated or dependency state.
    @details    Delegates to ``waegis.payload.copier.should_exclude`` — the
                single source of truth for the exclusion rules since T3.2.
    @param[in]  path Path relative to the template root.
    @return     True when the path must not be copied into a target project.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.3.0
    """
    return _should_exclude(path)


def copy_template(
    target: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    require_existing_target: bool = False,
) -> list[Path]:
    """
    @brief      Copy or preview the bundled template files into a target root.
    @details    Thin wrapper over ``waegis.payload.copier.copy_payload``. The
                observable contract is unchanged (never-overwrite default,
                dry-run preview, ``SystemExit`` messages) with one documented
                addition: a real copy also writes
                ``<target>/.agentic/install-manifest.json`` (mode ``"new"``,
                or ``"adopt"`` when ``require_existing_target`` is set). The
                manifest is a side-effect file and is not included in the
                returned list.
    @param[in]  target Target project or existing repository root.
    @param[in]  force Overwrite existing files when true.
    @param[in]  dry_run Preview copied file paths without writing.
    @param[in]  require_existing_target Require target to already be a directory.
    @return     Destination files that were copied or would be copied.
    @exception  SystemExit Raised for a missing template, missing existing repo,
                or an overwrite refusal.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.3.0
    """
    try:
        result = copy_payload(
            TEMPLATE_ROOT,
            target,
            mode="adopt" if require_existing_target else "new",
            force=force,
            dry_run=dry_run,
            require_existing_target=require_existing_target,
        )
    except CopierError as exc:
        raise SystemExit(str(exc)) from exc
    return [result.target / relative for relative in result.copied]


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Parse command-line arguments and run the template copier.
    @param[in]  argv Optional argument list for tests.
    @return     Process exit code.
    @exception  SystemExit Raised by argparse or copy validation failures.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.3.0
    """
    parser = argparse.ArgumentParser(
        description="Copy the AEGIS payload into a new project or existing repository."
    )
    parser.add_argument("target", help="Target project or existing repository directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files in the target directory.")
    parser.add_argument("--dry-run", action="store_true", help="Show files that would be copied without writing.")
    parser.add_argument(
        "--existing-repo",
        action="store_true",
        help="Require the target directory to already exist; useful for adoption of an existing repository.",
    )
    args = parser.parse_args(argv)

    copied = copy_template(
        Path(args.target),
        force=args.force,
        dry_run=args.dry_run,
        require_existing_target=args.existing_repo,
    )
    action = "Would copy" if args.dry_run else "Copied"
    print(f"{action} {len(copied)} template files to {Path(args.target).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
