#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_io_prompts.py
@brief FieldSpec/Asker prompt-primitive tests for the WAEGIS io layer (T1.2).
@details Strictly offline: ``ConsoleAsker`` is driven through injected
         ``io.StringIO`` streams and a fake secret reader, never real stdin.
         Covers FieldSpec validation/re-prompt/default behaviour, ScriptedAsker
         missing/invalid-answer errors, secret-field no-echo handling, and the
         never-save-invalid guard.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io

import pytest
from waegis.engine import Asker
from waegis.io.prompts import (
    ConsoleAsker,
    FieldSpec,
    InvalidAnswersError,
    MissingAnswerError,
    ScriptedAnswerError,
    ScriptedAsker,
    ValidationError,
    guard_answers,
)

# LOCAL HELPERS


def _port_validator(raw: str) -> int:
    """
    @brief      Example validator: normalize to ``int`` and reject out-of-range.
    @param[in]  raw Candidate raw value.
    @return     The validated port number.
    @exception  ValueError If ``raw`` is not an integer or out of TCP range.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    value = int(raw)
    if not (1 <= value <= 65535):
        raise ValueError(f"port must be between 1 and 65535, got {value}")
    return value


def _console(input_text: str, *, terse: bool = False, secret_reader=None) -> tuple[ConsoleAsker, io.StringIO]:
    """
    @brief      Build a :class:`ConsoleAsker` over injected string streams.
    @param[in]  input_text Text fed to stdin, one answer per line.
    @param[in]  terse Passed through to ``ConsoleAsker``.
    @param[in]  secret_reader Optional fake no-echo reader.
    @return     The asker and its stdout buffer (for assertions).
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    stdin = io.StringIO(input_text)
    stdout = io.StringIO()
    asker = ConsoleAsker(stdin=stdin, stdout=stdout, terse=terse, secret_reader=secret_reader)
    return asker, stdout


# TESTS


def test_console_asker_and_scripted_asker_satisfy_engine_protocol() -> None:
    """
    @brief      Both askers satisfy the frozen engine ``Asker`` protocol.
    @return     None
    @exception  AssertionError If either class fails the ``isinstance`` check.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    console, _ = _console("\n")
    scripted = ScriptedAsker({})
    assert isinstance(console, Asker)
    assert isinstance(scripted, Asker)


def test_valid_value_passes_and_is_normalized() -> None:
    """
    @brief      A valid raw value is normalized through the validator.
    @return     None
    @exception  AssertionError If the returned value is not the validated int.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port to bind.", validator=_port_validator)
    asker, _ = _console("8080\n")
    assert asker.ask_field(spec) == 8080


def test_invalid_value_reprompts_with_validator_message() -> None:
    """
    @brief      An invalid value re-prompts, printing the validator's message,
                and the eventual valid retry is returned.
    @return     None
    @exception  AssertionError If no re-prompt occurs or the message is missing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port to bind.", validator=_port_validator)
    asker, stdout = _console("not-a-number\n99999\n8080\n")
    result = asker.ask_field(spec)
    assert result == 8080
    output = stdout.getvalue()
    assert "invalid literal" in output
    assert "port must be between 1 and 65535" in output


def test_empty_input_accepts_default_without_validation() -> None:
    """
    @brief      Empty input accepts the detected default, bypassing the
                validator (a default that would fail validation is still
                accepted verbatim).
    @return     None
    @exception  AssertionError If the default is not returned unchanged.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port to bind.", default=99999, validator=_port_validator)
    asker, _ = _console("\n")
    assert asker.ask_field(spec) == 99999


def test_detected_default_rendered_in_prompt_text() -> None:
    """
    @brief      The rendered prompt shows both the example and the default.
    @return     None
    @exception  AssertionError If either hint is absent from stdout.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port to bind.", example="8080", default="8000")
    asker, stdout = _console("\n")
    asker.ask_field(spec)
    output = stdout.getvalue()
    assert "e.g. 8080" in output
    assert "default: 8000" in output


def test_terse_mode_suppresses_description() -> None:
    """
    @brief      Terse mode omits the novice ``why`` description text.
    @return     None
    @exception  AssertionError If the description leaks into stdout.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="EXPLAIN WHY THIS MATTERS", default="8000")
    asker, stdout = _console("\n", terse=True)
    asker.ask_field(spec)
    assert "EXPLAIN WHY THIS MATTERS" not in stdout.getvalue()


def test_scripted_asker_applies_validator() -> None:
    """
    @brief      ScriptedAsker validates a supplied answer through the FieldSpec.
    @return     None
    @exception  AssertionError If the normalized value is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port.", validator=_port_validator)
    asker = ScriptedAsker({"port": "9090"})
    assert asker.ask_field(spec) == 9090


def test_scripted_asker_missing_answer_names_the_key() -> None:
    """
    @brief      A missing scripted answer raises ``MissingAnswerError`` naming
                the field key (what ``--non-interactive`` surfaces).
    @return     None
    @exception  AssertionError If the error is not raised or misnames the key.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port.", validator=_port_validator)
    asker = ScriptedAsker({})
    with pytest.raises(MissingAnswerError) as excinfo:
        asker.ask_field(spec)
    assert excinfo.value.key == "port"


def test_scripted_asker_invalid_answer_fails_loudly_without_reprompt() -> None:
    """
    @brief      An invalid scripted answer fails immediately (no re-prompt loop
                exists in scripted mode).
    @return     None
    @exception  AssertionError If the wrong error type is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="port", description="Port.", validator=_port_validator)
    asker = ScriptedAsker({"port": "99999"})
    with pytest.raises(ScriptedAnswerError) as excinfo:
        asker.ask_field(spec)
    assert excinfo.value.key == "port"
    assert "between 1 and 65535" in excinfo.value.message


def test_secret_field_uses_no_echo_reader_and_is_not_written_to_stdout() -> None:
    """
    @brief      A secret field is read via the injected no-echo reader; the raw
                secret value never appears on stdout.
    @return     None
    @exception  AssertionError If stdout leaks the secret or the reader is unused.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    calls: list[str] = []

    def fake_secret_reader(prompt: str) -> str:
        calls.append(prompt)
        return "s3cr3t-value"

    spec = FieldSpec(key="token", description="API token.", secret=True)
    asker, stdout = _console("", secret_reader=fake_secret_reader)
    result = asker.ask_field(spec)

    assert result == "s3cr3t-value"
    assert len(calls) == 1
    assert "s3cr3t-value" not in stdout.getvalue()


def test_guard_answers_rejects_one_invalid_value() -> None:
    """
    @brief      The never-save-invalid guard refuses an answer set carrying one
                invalid value, even when other fields are valid.
    @return     None
    @exception  AssertionError If it does not raise, or the bad key is absent.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    specs = [
        FieldSpec(key="name", description="Name."),
        FieldSpec(key="port", description="Port.", validator=_port_validator),
    ]
    answers = {"name": "acme", "port": "not-a-number"}
    with pytest.raises(InvalidAnswersError) as excinfo:
        guard_answers(specs, answers)
    assert "port" in excinfo.value.errors
    assert "name" not in excinfo.value.errors


def test_guard_answers_accepts_a_fully_valid_set() -> None:
    """
    @brief      A fully valid answer set passes the guard and is normalized.
    @return     None
    @exception  AssertionError If normalization is wrong or it raises.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    specs = [
        FieldSpec(key="name", description="Name."),
        FieldSpec(key="port", description="Port.", validator=_port_validator, default=8000),
    ]
    normalized = guard_answers(specs, {"name": "acme"})
    assert normalized == {"name": "acme", "port": 8000}


def test_field_spec_normalize_raises_without_default() -> None:
    """
    @brief      ``FieldSpec.normalize`` raises ``ValidationError`` on empty input
                when no default is configured.
    @return     None
    @exception  AssertionError If no error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = FieldSpec(key="name", description="Name.")
    with pytest.raises(ValidationError):
        spec.normalize("")


def test_console_confirmation_distinguishes_eof_from_blank_default_yes() -> None:
    """@brief EOF declines while a real blank line may accept the stated default."""
    eof_asker, _ = _console("")
    blank_asker, _ = _console("\n")
    assert eof_asker.confirm("Mutate?", default=True) is False
    assert blank_asker.confirm("Mutate?", default=True) is True


def test_scripted_confirmation_queue_exhaustion_fails_closed() -> None:
    """@brief A finite scripted queue never turns exhaustion into approval."""
    asker = ScriptedAsker(confirms=[False])
    assert asker.confirm("first") is False
    with pytest.raises(MissingAnswerError):
        asker.confirm("second")


# END OF FILE
