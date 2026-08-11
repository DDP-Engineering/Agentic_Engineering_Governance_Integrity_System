#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Provide the one explicitly authorized local Git initialization adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from waegis.domain.plans import PlanError


class LocalGitInitializer:
    """Run only `git init`; expose no other Git mutation capability."""

    def initialize(self, target: Path) -> None:
        """Initialize the target through an argument-vector subprocess."""
        try:
            completed = subprocess.run(
                ["git", "init", "--quiet"],
                cwd=target,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                check=False,
                timeout=60,
                shell=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise PlanError(f"Local Git initialization could not start: {exc}") from exc
        if completed.returncode != 0:
            message = completed.stderr.decode("utf-8", errors="replace").strip()
            raise PlanError(f"Local Git initialization failed: {message}")
