#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_io_answers.py
@brief Answers-file (TOML/JSON) load/save tests for the WAEGIS io layer (T1.2).
@details Strictly offline: all files live under pytest's ``tmp_path``. Covers
         TOML/JSON round-trip, unknown-key warnings, secret exclusion on save,
         all-missing-keys-at-once reporting for ``--non-interactive``,
         malformed-file error clarity, and BOM tolerance for JSON files
         written by Windows PowerShell.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest
from waegis.io.answers import (
    AnswersFileError,
    MissingAnswersError,
    load_answers_file,
    missing_required_keys,
    require_non_interactive_answers,
    save_answers_file,
    unknown_keys,
)
from waegis.io.prompts import FieldSpec

# LOCAL HELPERS


def _specs() -> list[FieldSpec]:
    """
    @brief      A small representative FieldSpec set for the round-trip tests.
    @return     Three fields: a required text field, a defaulted field, and a
                secret field that must never be saved.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return [
        FieldSpec(key="project_name", description="Project name."),
        FieldSpec(key="source_root", description="Source root.", default="src"),
        FieldSpec(key="api_token", description="API token.", secret=True),
    ]


# TESTS


def test_toml_round_trip(tmp_path: Path) -> None:
    """
    @brief      Saving then loading a TOML answers file round-trips the values.
    @return     None
    @exception  AssertionError If the loaded mapping does not match the saved one.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "answers.toml"
    specs = _specs()
    answers = {"project_name": "acme", "source_root": "src", "api_token": "should-not-be-saved"}
    save_answers_file(path, specs, answers)
    loaded = load_answers_file(path)
    assert loaded == {"project_name": "acme", "source_root": "src"}


def test_json_with_utf8_bom_loads(tmp_path: Path) -> None:
    """
    @brief      A JSON answers file with a UTF-8 BOM (as written by Windows
                PowerShell's ``Out-File -Encoding utf8``) loads normally.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the BOM breaks loading.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "answers.json"
    path.write_bytes(b'\xef\xbb\xbf{"project_name": "acme"}')
    assert load_answers_file(path) == {"project_name": "acme"}


def test_json_round_trip(tmp_path: Path) -> None:
    """
    @brief      Saving then loading a JSON answers file round-trips the values.
    @return     None
    @exception  AssertionError If the loaded mapping does not match the saved one.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "answers.json"
    specs = _specs()
    answers = {"project_name": "acme", "source_root": "lib"}
    save_answers_file(path, specs, answers)
    loaded = load_answers_file(path)
    assert loaded == {"project_name": "acme", "source_root": "lib"}


def test_save_excludes_secret_fields(tmp_path: Path) -> None:
    """
    @brief      A secret field is excluded from the saved file by construction,
                regardless of the file format.
    @return     None
    @exception  AssertionError If the secret value is present in either file.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    specs = _specs()
    answers = {"project_name": "acme", "source_root": "src", "api_token": "top-secret"}

    toml_path = tmp_path / "answers.toml"
    save_answers_file(toml_path, specs, answers)
    assert "top-secret" not in toml_path.read_text(encoding="utf-8")
    assert "api_token" not in toml_path.read_text(encoding="utf-8")

    json_path = tmp_path / "answers.json"
    save_answers_file(json_path, specs, answers)
    assert "top-secret" not in json_path.read_text(encoding="utf-8")


def test_unknown_keys_are_collected_not_raised(tmp_path: Path) -> None:
    """
    @brief      An answers file key that no FieldSpec expects is reported to the
                caller as a warning, not a load failure.
    @return     None
    @exception  AssertionError If the load raises or the unknown key is missed.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "answers.json"
    path.write_text('{"project_name": "acme", "typo_field": "oops"}', encoding="utf-8")
    loaded = load_answers_file(path)
    assert loaded == {"project_name": "acme", "typo_field": "oops"}
    assert unknown_keys(loaded, _specs()) == ["typo_field"]


def test_missing_required_keys_reports_all_at_once() -> None:
    """
    @brief      ``require_non_interactive_answers`` reports every missing
                required key in one structured error, not just the first.
    @return     None
    @exception  AssertionError If not all missing keys are present in the error.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    specs = [
        FieldSpec(key="project_name", description="Name."),
        FieldSpec(key="target_path", description="Target."),
        FieldSpec(key="source_root", description="Source root.", default="src"),
    ]
    with pytest.raises(MissingAnswersError) as excinfo:
        require_non_interactive_answers(specs, {})
    assert set(excinfo.value.keys) == {"project_name", "target_path"}
    assert missing_required_keys(specs, {}) == ["project_name", "target_path"]


def test_require_non_interactive_answers_resolves_defaults_and_validates() -> None:
    """
    @brief      A complete answer set resolves defaults and validates supplied
                values.
    @return     None
    @exception  AssertionError If resolution is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    specs = [
        FieldSpec(key="project_name", description="Name."),
        FieldSpec(key="source_root", description="Source root.", default="src"),
    ]
    resolved = require_non_interactive_answers(specs, {"project_name": "acme"})
    assert resolved == {"project_name": "acme", "source_root": "src"}


def test_malformed_toml_file_raises_clear_error(tmp_path: Path) -> None:
    """
    @brief      A malformed TOML file raises ``AnswersFileError`` with a clear
                message rather than an uncaught parser exception.
    @return     None
    @exception  AssertionError If the wrong exception type is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "broken.toml"
    path.write_text("this = = not valid toml", encoding="utf-8")
    with pytest.raises(AnswersFileError):
        load_answers_file(path)


def test_malformed_json_file_raises_clear_error(tmp_path: Path) -> None:
    """
    @brief      A malformed JSON file raises ``AnswersFileError`` with a clear
                message rather than an uncaught parser exception.
    @return     None
    @exception  AssertionError If the wrong exception type is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "broken.json"
    path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(AnswersFileError):
        load_answers_file(path)


def test_unsupported_extension_raises_clear_error(tmp_path: Path) -> None:
    """
    @brief      An answers file with an unsupported extension raises a clear
                error rather than being silently misparsed.
    @return     None
    @exception  AssertionError If the wrong exception type is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = tmp_path / "answers.yaml"
    path.write_text("project_name: acme", encoding="utf-8")
    with pytest.raises(AnswersFileError):
        load_answers_file(path)


# END OF FILE
