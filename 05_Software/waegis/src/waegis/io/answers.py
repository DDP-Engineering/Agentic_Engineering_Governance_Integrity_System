#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file answers.py
@brief Answers-file load/save seam (TOML/JSON) for non-interactive runs (T1.2).
@details Implements the ``--answers FILE`` seam (plan §4 item 6, AD-9): a flat
         ``FieldSpec.key`` to value mapping loaded from TOML (``tomllib``, read
         only) or JSON, chosen by file extension. Unknown keys are collected and
         reported to the caller rather than failing the load. Saving excludes
         every field marked ``secret`` by construction, so a replay file can
         never carry a secret value. ``require_non_interactive_answers``
         implements the ``--non-interactive`` contract: every missing required
         key is reported in one structured error, not just the first.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.1.1
"""

# IMPORTS

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any, Mapping, Sequence

from .prompts import FieldSpec

# DATA MODELS / TYPEDEFINITIONS


class AnswersError(Exception):
    """
    @brief Base class for every error raised by the answers-file seam.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class AnswersFileError(AnswersError):
    """
    @brief Raised when an answers file cannot be read, parsed, or serialized.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class MissingAnswersError(AnswersError):
    """
    @brief Raised when ``--non-interactive`` finds required keys unanswered.
    @details Carries every missing key at once so the operator sees the full
             list in a single error rather than fixing one key at a time.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self, keys: Sequence[str]) -> None:
        """
        @brief      Construct the error from every missing required key.
        @param[in]  keys The missing ``FieldSpec.key`` values, in spec order.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self.keys = list(keys)
        joined = ", ".join(self.keys)
        super().__init__(f"missing required answers: {joined}")


# HELPER FUNCTIONS


def _toml_scalar(value: Any) -> str:
    """
    @brief      Render one Python value as a TOML scalar/array literal.
    @param[in]  value A ``bool``, ``int``, ``float``, ``str``, or list/tuple of
                these (flat answers-file values only).
    @return     The TOML literal text for ``value``.
    @exception  AnswersFileError If ``value`` has an unsupported type.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_toml_scalar(item) for item in value) + "]"
    raise AnswersFileError(f"cannot serialize value of type {type(value).__name__!r} to TOML")


def _dump_toml(mapping: Mapping[str, Any]) -> str:
    """
    @brief      Serialize a flat mapping to minimal TOML text.
    @details    The stdlib ``tomllib`` module is read-only, so this hand-rolled
                writer covers exactly the flat-key scalar/array shape the
                answers-file schema needs; it is not a general TOML writer.
    @param[in]  mapping Flat key to value mapping to serialize.
    @return     TOML document text (one ``key = value`` line per entry).
    @exception  AnswersFileError If a value has an unsupported type.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    lines = [f"{key} = {_toml_scalar(value)}" for key, value in mapping.items()]
    return "\n".join(lines) + ("\n" if lines else "")


# PUBLIC API


def load_answers_file(path: str | Path) -> dict[str, Any]:
    """
    @brief      Load a flat answers mapping from a TOML or JSON file.
    @details    Format is chosen by file extension (``.toml`` or ``.json``).
                The result is the raw mapping; use :func:`unknown_keys` against
                a ``FieldSpec`` list to find keys the catalog does not expect.
                JSON is decoded as ``utf-8-sig`` so an answers file written by
                Windows PowerShell (whose ``utf8`` encoding prepends a BOM)
                loads the same as a BOM-less one.
    @param[in]  path Path to the answers file.
    @return     The flat ``key`` to value mapping.
    @exception  AnswersFileError If the extension is unsupported, the file
                cannot be read, the content is not valid TOML/JSON, or the
                parsed document is not a flat mapping.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-13
    @version    0.2.0
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in (".toml", ".json"):
        raise AnswersFileError(f"unsupported answers file extension: {file_path.suffix!r}")
    try:
        if suffix == ".toml":
            with file_path.open("rb") as handle:
                data = tomllib.load(handle)
        else:
            # utf-8-sig: identical to utf-8 for BOM-less files, and tolerates
            # the BOM Windows PowerShell's `Out-File -Encoding utf8` prepends.
            data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise AnswersFileError(f"cannot read answers file {file_path}: {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise AnswersFileError(f"malformed TOML answers file {file_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise AnswersFileError(f"malformed JSON answers file {file_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise AnswersFileError(f"answers file {file_path} must contain a flat mapping")
    return dict(data)


def unknown_keys(answers: Mapping[str, Any], specs: Sequence[FieldSpec]) -> list[str]:
    """
    @brief      Find answer keys that no ``FieldSpec`` in the catalog expects.
    @details    Collected, not raised: an unrecognized key is a warning the
                caller reports to the operator, never a load failure (a newer
                answers file replayed against an older catalog should still
                work for the keys it recognizes).
    @param[in]  answers Loaded answers mapping.
    @param[in]  specs Every ``FieldSpec`` the current catalog defines.
    @return     Sorted list of keys present in ``answers`` but not in ``specs``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    known = {spec.key for spec in specs}
    return sorted(key for key in answers if key not in known)


def missing_required_keys(specs: Sequence[FieldSpec], answers: Mapping[str, Any]) -> list[str]:
    """
    @brief      Find required keys that ``answers`` does not supply.
    @details    A field is required when it has no detected default; a field
                with a default is never "missing" (the default applies).
    @param[in]  specs Every ``FieldSpec`` the current catalog defines.
    @param[in]  answers Loaded (or partially built) answers mapping.
    @return     Missing required keys, in ``specs`` order.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return [spec.key for spec in specs if spec.key not in answers and spec.default is None]


def require_non_interactive_answers(
    specs: Sequence[FieldSpec], answers: Mapping[str, Any]
) -> dict[str, Any]:
    """
    @brief      Resolve a full answer set for ``--non-interactive`` (AD-9).
    @details    Reports every missing required key at once via
                :class:`MissingAnswersError` rather than failing on the first.
                Present values are validated through their ``FieldSpec``;
                absent-but-defaulted fields resolve to the default verbatim.
    @param[in]  specs Every ``FieldSpec`` the running catalog defines.
    @param[in]  answers Loaded answers mapping (e.g. from :func:`load_answers_file`).
    @return     The normalized answer mapping, keyed by ``FieldSpec.key``.
    @exception  MissingAnswersError If any required key has no answer.
    @exception  waegis.io.prompts.ValidationError If a present value fails its
                validator.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    missing = missing_required_keys(specs, answers)
    if missing:
        raise MissingAnswersError(missing)
    resolved: dict[str, Any] = {}
    for spec in specs:
        if spec.key in answers:
            resolved[spec.key] = spec.normalize(answers[spec.key])
        else:
            resolved[spec.key] = spec.default
    return resolved


def save_answers_file(
    path: str | Path, specs: Sequence[FieldSpec], answers: Mapping[str, Any]
) -> None:
    """
    @brief      Save a completed run's answers for replay via ``--answers``.
    @details    Every field marked ``secret`` is excluded by construction: the
                loop below only ever considers non-secret specs, so a secret
                value can never reach the written file regardless of what
                ``answers`` contains.
    @param[in]  path Destination path; format is chosen by extension (``.toml``
                or ``.json``).
    @param[in]  specs Every ``FieldSpec`` the running catalog defines.
    @param[in]  answers Completed answer mapping to save from.
    @return     None
    @exception  AnswersFileError If the extension is unsupported or a value
                cannot be serialized (TOML only).
    @exception  OSError If the file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix not in (".toml", ".json"):
        raise AnswersFileError(f"unsupported answers file extension: {file_path.suffix!r}")
    saveable = {spec.key: answers[spec.key] for spec in specs if not spec.secret and spec.key in answers}
    if suffix == ".json":
        file_path.write_text(json.dumps(saveable, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    else:
        file_path.write_text(_dump_toml(saveable), encoding="utf-8")


# END OF FILE
