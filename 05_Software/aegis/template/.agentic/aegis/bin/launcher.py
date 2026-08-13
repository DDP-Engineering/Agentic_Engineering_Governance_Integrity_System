#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Launch the repository-local AEGIS package from a relocatable payload."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main() -> int:
    """Resolve only payload-relative runtime paths and enter AEGIS."""
    payload = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(payload / "cli" / "src"))
    from aegis.composition import main as aegis_main

    return aegis_main(
        sys.argv[1:],
        git_available=shutil.which("git") is not None,
    )


if __name__ == "__main__":
    raise SystemExit(main())
