#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file version.py
@brief ``waegis version`` reporting from the single version source.
@author Eng. Dan Dumitru Pasare
@date 2026-07-16
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import os
import sys
import zipimport
from typing import IO, Any

from ..io.envelope import EXIT_OK, write_envelope
from ..payload.copier import CopierError, inspect_payload
from ..payload.locate import PayloadLocateError, locate_payload, read_payload_version
from ..version import PAYLOAD_COMPAT_SPEC, WIZARD_VERSION


def _packaging_type() -> str:
    """@brief Detect source, zipapp, or application-archive execution."""
    explicit = os.environ.get("WAEGIS_PACKAGING_TYPE")
    if explicit:
        return explicit
    if isinstance(globals().get("__loader__"), zipimport.zipimporter) or str(sys.argv[0]).endswith(".pyz"):
        return "zipapp"
    if getattr(sys, "frozen", False):
        return "application-archive"
    return "source-checkout"


def build_version_info() -> dict[str, Any]:
    """
    @brief      Build the version and bundled-payload report.
    @return     JSON-safe result mapping.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    payload_version: str | None = None
    payload_digest: str | None = None
    try:
        payload = locate_payload()
        payload_version = read_payload_version(payload)
        payload_digest = inspect_payload(payload).digest
    except (PayloadLocateError, CopierError, OSError, ValueError):
        pass
    return {
        "waegis_version": WIZARD_VERSION,
        "compatible_payload_range": PAYLOAD_COMPAT_SPEC,
        "bundled_payload_version": payload_version,
        "bundled_payload_digest": payload_digest,
        "packaging_type": _packaging_type(),
    }


def run_version(*, as_json: bool, stream: IO[str]) -> int:
    """
    @brief      Render ``waegis version [--json]``.
    @return     Zero.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-16
    @version    0.1.0
    """
    info = build_version_info()
    if as_json:
        return write_envelope(stream, "version", status="ok", exit_code=EXIT_OK, result=info)
    stream.write(f"WAEGIS {info['waegis_version']}\n")
    stream.write(f"Compatible AEGIS payloads: {info['compatible_payload_range']}\n")
    stream.write(f"Bundled payload: {info['bundled_payload_version'] or 'unavailable'}\n")
    stream.write(f"Payload digest: {info['bundled_payload_digest'] or 'unavailable'}\n")
    stream.write(f"Packaging: {info['packaging_type']}\n")
    return EXIT_OK


# END OF FILE
