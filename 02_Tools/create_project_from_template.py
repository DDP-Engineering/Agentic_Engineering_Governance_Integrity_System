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
@author Eng. Dan Dumitru Pasare
@date 2026-06-23
@version 0.2.0
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "05_Software" / "aegis" / "template"
# `node_modules`/`.vitest` belong to the `.pi/` adapter's isolated vitest setup and
# must never be carried into a scaffolded project.
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".vitest"}
EXCLUDED_SUFFIXES = {".pyc"}
EXCLUDED_PATTERNS = ("*.egg-info", ".uv-cache*")


def should_exclude(path: Path) -> bool:
    """
    @brief      Return whether a template path is generated or dependency state.
    @param[in]  path Path relative to the template root.
    @return     True when the path must not be copied into a target project.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.2.0
    """
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return True
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    return any(path.match(pattern) for pattern in EXCLUDED_PATTERNS)


def copy_template(
    target: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    require_existing_target: bool = False,
) -> list[Path]:
    """
    @brief      Copy or preview the bundled template files into a target root.
    @param[in]  target Target project or existing repository root.
    @param[in]  force Overwrite existing files when true.
    @param[in]  dry_run Preview copied file paths without writing.
    @param[in]  require_existing_target Require target to already be a directory.
    @return     Destination files that were copied or would be copied.
    @exception  SystemExit Raised for a missing template, missing existing repo,
                or an overwrite refusal.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.2.0
    """
    if not TEMPLATE_ROOT.exists():
        raise SystemExit(f"Template directory not found: {TEMPLATE_ROOT}")

    target = target.resolve()
    if require_existing_target and not target.is_dir():
        raise SystemExit(f"Existing repository directory not found: {target}")

    copied: list[Path] = []
    for source in sorted(TEMPLATE_ROOT.rglob("*")):
        relative = source.relative_to(TEMPLATE_ROOT)
        if should_exclude(relative):
            continue
        destination = target / relative
        if source.is_dir():
            if not dry_run:
                destination.mkdir(parents=True, exist_ok=True)
            continue
        if destination.exists() and not force:
            raise SystemExit(f"Refusing to overwrite existing file: {destination}")
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        copied.append(destination)
    return copied


def main(argv: list[str] | None = None) -> int:
    """
    @brief      Parse command-line arguments and run the template copier.
    @param[in]  argv Optional argument list for tests.
    @return     Process exit code.
    @exception  SystemExit Raised by argparse or copy validation failures.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-23
    @version    0.2.0
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
