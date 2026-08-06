#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file _form_io.py
@brief Shared TOML transient-evidence-form I/O helpers.
@details Extracted from evidence_forms.py and check_execution.py, which each
         reimplemented the same "load one strict TOML evidence form", "read
         one trimmed string field", "quote one TOML string", and "retire one
         imported form under its captured retention policy" logic.
"""

# IMPORTS

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import tomllib
from typing import Any

from .stage_schema import StageOperationError

# CONSTANTS

_TOML_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}

# PUBLIC API


def load_evidence_form(path: Path) -> dict[str, Any]:
    """
    @brief      Load one strict TOML evidence form.
    @param[in]  path Form path.
    @return     Parsed top-level TOML table.
    @exception  StageOperationError If the file is unreadable or malformed.
    """
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise StageOperationError(f"{path}: cannot load evidence form: {exc}") from exc


def read_string_field(data: dict[str, Any], key: str, path: Path) -> str:
    """
    @brief      Read one trimmed, strictly-typed string field.
    @param[in]  data Parsed form table.
    @param[in]  key Field name.
    @param[in]  path Form path, used only for the error message.
    @return     Trimmed field value.
    @exception  StageOperationError If the field is missing or not a string.
    """
    value = data.get(key)
    if not isinstance(value, str):
        raise StageOperationError(f"{path}: {key} must be a string")
    return value.strip()


def quote_toml_string(value: str) -> str:
    """
    @brief      Quote one TOML basic string.
    @details    JSON's escape set is not TOML's. `json.dumps` escapes the whole
                C0 range but emits U+007F raw, and TOML's `ASCII_CTRL` includes
                U+007F - so a single DEL byte produced a form that `tomllib`
                could no longer parse. `requirement_store._toml_string` carries
                the same body for the same reason; the two are deliberately not
                merged (see `stage_forms._q`, whose `str()` coercion is
                load-bearing).
    """
    encoded = []
    for character in value:
        if character in _TOML_ESCAPES:
            encoded.append(_TOML_ESCAPES[character])
        elif character < " " or character == "\x7f":
            encoded.append(f"\\u{ord(character):04X}")
        else:
            encoded.append(character)
    return '"' + "".join(encoded) + '"'


def retire_form(path: Path, retention: str, revision_name: str) -> None:
    """
    @brief      Apply the captured retention policy to one imported form.
    @param[in]  path Imported form path.
    @param[in]  retention `versioned` or `discard`; any other value is a no-op.
    @param[in]  revision_name Destination directory name under `revisions/`
                when retention is `versioned`.
    @return     None.
    """
    if retention == "versioned":
        destination = path.parent / "revisions" / revision_name
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination / path.name)
        (destination / "digest.json").write_text(
            json.dumps({"sha256": sha256(path.read_bytes()).hexdigest()}, indent=2)
            + "\n",
            encoding="utf-8",
        )
    elif retention == "discard":
        path.unlink()


# END OF FILE
