#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file prompts.py
@brief FieldSpec prompt primitives and Askers (Console/Scripted) (plan §4, T1.2).
@details Ports the proven ador-init prompt design: ``FieldSpec`` (description,
         example, detected default, validator, secret flag) plus two
         implementations of the engine's ``Asker`` protocol
         (``waegis.engine.step.Asker``) — ``ConsoleAsker`` (interactive,
         stdin/stdout injected for offline tests) and ``ScriptedAsker`` (answers
         supplied from a mapping, as loaded by ``io/answers.py``).
@details The engine's ``Asker`` protocol (frozen by T1.1) only declares
         ``confirm``/``ask``, which is too narrow to carry ``FieldSpec``
         metadata (description, example, validator, secret). Both classes below
         still satisfy that protocol exactly as declared, so no T1.1 contract or
         test changes are required; they additionally expose ``ask_field``, a
         ``FieldSpec``-aware entry point layered on top that command code calls
         directly on the concrete Asker it constructs. This keeps the engine
         free of prompt-shape knowledge while giving step/command authors the
         full novice-mode prompting behaviour plan §4 requires.
@details ``FieldSpec.choices`` (added 0.2.0) is an optional small closed set of
         valid raw values: ``ConsoleAsker.ask_field`` renders it as a numbered
         menu and accepts either the number or the literal value, so console
         operators are not required to type a full word (e.g. a conflict
         decision) by hand. ``ConsoleAsker._write`` also now flushes after
         every prompt write, so the prompt text is guaranteed to render before
         the following blocking read under a fully-buffered stream (observed
         under Windows ``cmd.exe``, unlike a real TTY or PowerShell).
@details **Per-default confirmation policy.** ``confirm`` takes an optional
         ``decision`` keyword naming the answer key that decides the question
         when there is no operator. It exists because a blanket
         ``--non-interactive`` "yes to everything" used to invert the meaning of
         a *default-refuse* safety question: general mutation consent approves
         the rendered mutation plan, which is a materially different decision
         from waiving a safety outcome. :class:`ScriptedAsker` therefore never
         auto-answers ``True`` to a confirmation whose ``default`` is ``False``
         — such a question needs an explicit scripted answer (the ``decision``
         key in the answers mapping, or a scripted confirmation queue) and
         otherwise raises :class:`MissingAnswerError` naming the decision. The
         rule is per-default rather than per-question, so every future
         default-refuse confirmation inherits it. Answering ``False`` is always
         allowed: it agrees with the refusing default and is the conservative
         outcome. ``ConsoleAsker`` accepts ``decision`` and ignores it (a real
         operator is the explicit answer); the consequence of a yes belongs in
         the prompt text itself.
"""

# IMPORTS

from __future__ import annotations

import getpass
from dataclasses import dataclass
from typing import IO, Any, Callable, Mapping, Sequence

# DATA MODELS / TYPEDEFINITIONS


class PromptsError(Exception):
    """
    @brief Base class for every error raised by the prompt primitives.
    """


class ValidationError(PromptsError):
    """
    @brief Raised by a ``FieldSpec`` validator to reject a candidate value.
    @details The exception message is the novice-readable re-prompt text. A
             validator may also raise a plain ``ValueError``; ``FieldSpec``
             normalizes it to this type so callers only ever catch one class.
    """


class MissingAnswerError(PromptsError):
    """
    @brief Raised when a required answer is absent and no default applies.
    @details This is what ``--non-interactive`` surfaces (plan §4/§5): the
             ``key`` attribute names the missing field so the operator's error
             message is actionable. A refused default-refuse confirmation
             raises this too, with ``detail`` carrying the longer "which
             decision, and how to supply it" text.
    """

    def __init__(self, key: str, *, detail: str | None = None) -> None:
        """
        @brief      Construct the error for one missing field or decision.
        @param[in]  key The ``FieldSpec.key`` (or decision key) that had no
                    answer.
        @param[in]  detail Full message to use in place of the default
                    missing-field wording.
        @return     None
        """
        super().__init__(detail or f"missing answer for required field {key!r}")
        self.key = key


class ScriptedAnswerError(PromptsError):
    """
    @brief Raised when a scripted (answers-file) value fails validation.
    @details ``ScriptedAsker`` never re-prompts (there is no operator to ask),
             so an invalid scripted answer fails loudly with this error instead
             of looping.
    """

    def __init__(self, key: str, message: str) -> None:
        """
        @brief      Construct the error for one invalid scripted field.
        @param[in]  key The ``FieldSpec.key`` whose scripted value was invalid.
        @param[in]  message The validator's rejection message.
        @return     None
        """
        super().__init__(f"scripted answer for {key!r} is invalid: {message}")
        self.key = key
        self.message = message


class InvalidAnswersError(PromptsError):
    """
    @brief Raised by :func:`guard_answers` when one or more values are invalid.
    @details This is the "never-save-invalid" guard: it carries every failing
             key and message so a caller can report all of them at once, never
             persisting a partially-invalid answer set.
    """

    def __init__(self, errors: Mapping[str, str]) -> None:
        """
        @brief      Construct the error from every failing key/message pair.
        @param[in]  errors Mapping of ``FieldSpec.key`` to rejection message.
        @return     None
        """
        detail = "; ".join(f"{key}: {message}" for key, message in errors.items())
        super().__init__(f"refusing to proceed: invalid answers ({detail})")
        self.errors = dict(errors)


@dataclass(frozen=True)
class FieldSpec:
    """
    @brief One prompt-shape question (plan §4 item 5, ported from ador-init).
    @details ``description`` is the novice-readable "why", shown unless terse
             mode suppresses it. ``example`` and ``default`` (the detected
             default) are rendered alongside the prompt. ``validator`` takes the
             candidate raw value and either returns the normalized value or
             raises :class:`ValidationError` (or a plain ``ValueError``, which
             is normalized to it) carrying the re-prompt message. ``secret``
             marks a field that must never be echoed, journaled, or written to
             a saved answers file. ``choices``, when set, is a small closed set
             of valid raw values (e.g. conflict-resolution decisions);
             ``ConsoleAsker.ask_field`` renders it as a numbered menu and
             accepts either the number or the literal value, while
             ``ScriptedAsker``/``--answers`` files are unaffected (they always
             take the literal value). ``question``, when set, is a
             plain-language question rendered as the prompt line in place of
             the ``key``-based line (``ConsoleAsker`` only); it never affects
             ``ScriptedAsker`` or answers-file compatibility.
    """

    key: str
    description: str
    example: str | None = None
    default: Any | None = None
    validator: Callable[[Any], Any] | None = None
    secret: bool = False
    choices: tuple[str, ...] | None = None
    question: str | None = None

    def default_value(self) -> Any:
        """
        @brief      Return the default in a caller-safe, serializable form.
        @details    Immutable mapping defaults (e.g. ``MappingProxyType``) are
                    returned as a fresh ``dict`` copy so every consumer —
                    including journal JSON serialization — receives a plain,
                    mutable-by-them value.
        @return     The default, copied when it is a non-``dict`` mapping.
        @exception  None
        """
        if isinstance(self.default, Mapping) and not isinstance(self.default, dict):
            return dict(self.default)
        return self.default

    def normalize(self, raw: Any) -> Any:
        """
        @brief      Apply the empty-accepts-default rule and the validator.
        @details    An empty string or ``None`` is treated as "no input given":
                    it resolves to :attr:`default` verbatim, without running the
                    validator (the detected default is trusted as-is). Any other
                    value is passed to :attr:`validator`, if set.
        @param[in]  raw Candidate value (a string for console/scripted text
                    input; answers-file values may already be typed).
        @return     The normalized value.
        @exception  ValidationError If no default applies and the value is
                    empty, or if the validator rejects a non-empty value.
        """
        if raw is None or raw == "":
            if self.default is not None:
                return self.default_value()
            raise ValidationError(f"{self.key} has no default; a value is required")
        if self.validator is None:
            return raw
        try:
            return self.validator(raw)
        except ValidationError:
            raise
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def hint(self) -> str:
        """
        @brief      Build the inline "(e.g. ...; default: ...)" prompt suffix.
        @return     The parenthesized hint, or ``""`` when neither an example
                    nor a default is set.
        @exception  None
        """
        bits: list[str] = []
        if self.example is not None:
            bits.append(f"e.g. {self.example}")
        if self.default is not None:
            bits.append(f"default: {self.default}")
        return f" ({'; '.join(bits)})" if bits else ""


# HELPER FUNCTIONS


def _as_bool(key: str, raw: Any) -> bool:
    """
    @brief      Interpret a scripted decision answer as a boolean.
    @details    Answers files are typed (TOML/JSON booleans survive the load),
                but a hand-written file may still spell the value out, so the
                usual literals are accepted. Anything else is rejected rather
                than coerced: a decision that silently reads as ``True`` is the
                exact failure mode the per-default policy exists to prevent.
    @param[in]  key The decision key, for the rejection message.
    @param[in]  raw The scripted value.
    @return     The boolean the answer denotes.
    @exception  ScriptedAnswerError If the value is not a recognizable boolean.
    """
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in ("true", "yes", "y", "1"):
        return True
    if text in ("false", "no", "n", "0"):
        return False
    raise ScriptedAnswerError(key, f"expected a boolean, got {raw!r}")


def _default_secret_reader(prompt: str) -> str:
    """
    @brief      Default no-echo reader used by :class:`ConsoleAsker` for secrets.
    @param[in]  prompt Prompt text ``getpass`` displays before reading.
    @return     The line the operator typed, without echoing it to the console.
    @exception  EOFError If stdin is closed.
    """
    return getpass.getpass(prompt)


# PUBLIC API


class ConsoleAsker:
    """
    @brief Interactive :class:`~waegis.engine.step.Asker` over injected streams.
    @details Satisfies the engine ``Asker`` protocol (``confirm``/``ask``) and
             additionally implements ``ask_field`` for full ``FieldSpec``
             prompting: prints the description ("why") unless terse, shows the
             example and detected default, applies the validator, and
             re-prompts on invalid input with the validator's message. Empty
             input accepts the default. Secret fields are read through an
             injectable no-echo reader (``getpass.getpass`` by default) and
             their raw value is never written to ``stdout`` or otherwise
             returned except as the normalized answer. ``stdin``/``stdout`` are
             injected so tests never touch a real terminal.
    """

    def __init__(
        self,
        *,
        stdin: IO[str],
        stdout: IO[str],
        terse: bool = False,
        secret_reader: Callable[[str], str] | None = None,
    ) -> None:
        """
        @brief      Construct a console asker over injected streams.
        @param[in]  stdin Readable stream lines are read from (``readline``).
        @param[in]  stdout Writable stream prompts and messages are written to.
        @param[in]  terse When true, suppress ``FieldSpec.description`` text.
        @param[in]  secret_reader No-echo reader taking a prompt and returning
                    the typed line; defaults to ``getpass.getpass``.
        @return     None
        """
        self._stdin = stdin
        self._stdout = stdout
        self._terse = terse
        self._secret_reader = secret_reader if secret_reader is not None else _default_secret_reader

    def _write(self, text: str) -> None:
        """
        @brief      Write text to the injected stdout stream and flush it.
        @details    A prompt is always followed by a blocking ``readline()``,
                    so the write must be flushed here rather than relying on
                    the stream's own buffering policy: a fully-buffered
                    stream (e.g. ``cmd.exe`` piping stdout, unlike a real TTY
                    or PowerShell) would otherwise hold the prompt text back
                    until an unrelated later flush, making the wizard look
                    hung with no visible question to answer.
        @param[in]  text Text to write (no trailing newline is added).
        @return     None
        """
        self._stdout.write(text)
        flush = getattr(self._stdout, "flush", None)
        if flush is not None:
            flush()

    def confirm(self, prompt: str, *, default: bool = True, decision: str | None = None) -> bool:
        """
        @brief      Ask a yes/no question (engine ``Asker`` protocol member).
        @param[in]  prompt Question text.
        @param[in]  default Value assumed when the operator presses enter.
        @param[in]  decision Answer key that would decide this question without
                    an operator; accepted and ignored here, since a live
                    operator *is* the explicit answer.
        @return     The operator's boolean choice.
        @exception  None
        """
        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            self._write(f"{prompt} {suffix}: ")
            line = self._stdin.readline()
            if line == "":
                return False
            raw = line.strip().lower()
            if raw == "":
                return default
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            self._write("Please answer 'y' or 'n'.\n")

    def ask(self, key: str, prompt: str, *, default: str | None = None) -> str:
        """
        @brief      Ask for a free-text answer (engine ``Asker`` protocol member).
        @details    Unvalidated, single-line variant used directly by the
                    engine/steps; ``ask_field`` is the ``FieldSpec``-aware entry
                    point for the full prompt shape.
        @param[in]  key Stable answer key (unused here beyond the protocol
                    signature; ``ask_field`` is what journals answers).
        @param[in]  prompt Question text.
        @param[in]  default Suggested default answer, if any.
        @return     The operator's answer, or ``default`` on empty input.
        @exception  None
        """
        hint = f" [{default}]" if default is not None else ""
        self._write(f"{prompt}{hint}: ")
        raw = self._stdin.readline().rstrip("\n")
        return raw if raw != "" else (default if default is not None else "")

    def ask_field(self, spec: FieldSpec) -> Any:
        """
        @brief      Prompt for one ``FieldSpec``, re-prompting until valid.
        @details    Prints ``spec.description`` unless terse, then — when
                    ``spec.choices`` is set — a numbered menu of the valid
                    values (the one matching ``spec.default`` marked), then
                    the prompt line: ``spec.question`` when set, else the
                    ``key``-based line, followed by the
                    ``(e.g. ...; default: ...)`` hint. Secret fields are read
                    with the injected no-echo
                    reader; other fields are read from ``stdin``. When
                    ``spec.choices`` is set and the operator types a bare
                    number in range, it is resolved to the corresponding
                    choice before validation; typing the literal value still
                    works unchanged. Invalid input prints the validator's
                    message and loops; empty input accepts the default
                    without validation.
        @param[in]  spec The field to prompt for.
        @return     The normalized answer.
        @exception  MissingAnswerError If ``stdin`` reaches EOF before a valid
                    answer is provided.
        """
        if not self._terse and spec.description:
            self._write(f"{spec.description}\n")
        if spec.choices:
            for index, choice in enumerate(spec.choices, start=1):
                marker = " (default)" if choice == spec.default else ""
                self._write(f"  {index}) {choice}{marker}\n")
        if spec.question is not None:
            prompt_text = f"{spec.question}{spec.hint()}: "
        else:
            prompt_text = f"{spec.key}{spec.hint()}: "
        while True:
            if spec.secret:
                raw = self._secret_reader(prompt_text)
            else:
                self._write(prompt_text)
                line = self._stdin.readline()
                if line == "":
                    raise MissingAnswerError(spec.key)
                raw = line.rstrip("\n")
            candidate = raw
            if spec.choices and raw.strip().isdigit():
                index = int(raw.strip())
                if 1 <= index <= len(spec.choices):
                    candidate = spec.choices[index - 1]
            try:
                return spec.normalize(candidate)
            except ValidationError as exc:
                self._write(f"{exc}\n")
                continue


class ScriptedAsker:
    """
    @brief Non-interactive :class:`~waegis.engine.step.Asker` over a mapping.
    @details Satisfies the engine ``Asker`` protocol and additionally
             implements ``ask_field``: the validator still runs, but there is
             no operator to re-prompt, so a missing answer raises
             :class:`MissingAnswerError` naming the key (what
             ``--non-interactive`` surfaces) and an invalid scripted answer
             raises :class:`ScriptedAnswerError` instead of looping.
    """

    def __init__(
        self,
        answers: Mapping[str, Any] | None = None,
        *,
        confirms: bool | Sequence[bool] = True,
    ) -> None:
        """
        @brief      Construct a scripted asker from a preloaded answers mapping.
        @param[in]  answers Flat ``FieldSpec.key`` to value mapping (as produced
                    by ``io/answers.py``).
        @param[in]  confirms A fixed boolean used for every ``confirm`` call, or
                    a finite queue of booleans consumed in order.
        @return     None
        """
        self._answers: dict[str, Any] = dict(answers) if answers else {}
        if isinstance(confirms, bool):
            self._confirm_queue: list[bool] | None = None
            self._fixed_confirm = confirms
        else:
            self._confirm_queue = list(confirms)
            self._fixed_confirm = True

    def confirm(self, prompt: str, *, default: bool = True, decision: str | None = None) -> bool:
        """
        @brief      Answer a yes/no question from the scripted answers, queue,
                    or fixed value, honoring the per-default policy.
        @details    Resolution order: the named ``decision`` key in the answers
                    mapping (the most explicit statement of intent), then a
                    finite confirmation queue, then the fixed value. The fixed
                    value may only auto-answer ``True`` to a question whose
                    ``default`` is ``True``: a default-refuse question answered
                    ``True`` by blanket consent would waive a safety outcome
                    nobody decided, so it raises instead (module docstring).
        @param[in]  prompt Question text (used only in the refusal message).
        @param[in]  default The interactive default, which selects the policy.
        @param[in]  decision Answer key that decides this question explicitly.
        @return     The scripted boolean.
        @exception  MissingAnswerError If a finite confirmation queue is empty,
                    or a default-refuse question has no explicit answer.
        @exception  ScriptedAnswerError If the ``decision`` answer is not a
                    recognizable boolean.
        """
        if decision is not None and decision in self._answers:
            return _as_bool(decision, self._answers[decision])
        if self._confirm_queue is not None:
            if self._confirm_queue:
                return self._confirm_queue.pop(0)
            raise MissingAnswerError("confirmation")
        if self._fixed_confirm and not default:
            key = decision or "confirmation"
            raise MissingAnswerError(
                key,
                detail=(
                    "refusing to answer a default-refuse question without an explicit "
                    f"decision: {prompt} — general consent (--yes/--non-interactive) "
                    "approves the rendered mutation plan only; set "
                    f"{key!r} in the answers file to make this choice explicitly"
                ),
            )
        return self._fixed_confirm

    def ask(self, key: str, prompt: str, *, default: str | None = None) -> str:
        """
        @brief      Answer a free-text question from the scripted mapping.
        @param[in]  key Stable answer key looked up in the scripted mapping.
        @param[in]  prompt Question text (unused; scripted answers ignore it).
        @param[in]  default Fallback returned when ``key`` is absent.
        @return     The scripted answer, or ``default`` when absent.
        @exception  MissingAnswerError If ``key`` is absent and ``default`` is
                    ``None``.
        """
        if key in self._answers:
            return str(self._answers[key])
        if default is not None:
            return default
        raise MissingAnswerError(key)

    def ask_field(self, spec: FieldSpec) -> Any:
        """
        @brief      Resolve one ``FieldSpec`` from the scripted mapping.
        @param[in]  spec The field to resolve.
        @return     The normalized answer.
        @exception  MissingAnswerError If ``spec.key`` has no scripted answer
                    and ``spec.default`` is ``None``.
        @exception  ScriptedAnswerError If the scripted value fails validation.
        """
        if spec.key not in self._answers:
            if spec.default is not None:
                return spec.default_value()
            raise MissingAnswerError(spec.key)
        raw = self._answers[spec.key]
        try:
            return spec.normalize(raw)
        except ValidationError as exc:
            raise ScriptedAnswerError(spec.key, str(exc)) from exc


def guard_answers(specs: Sequence[FieldSpec], answers: Mapping[str, Any]) -> dict[str, Any]:
    """
    @brief      Never-save-invalid guard: validate a complete answer set.
    @details    Validates every field in ``specs`` against ``answers``,
                collecting *every* failing key (missing-with-no-default, or
                validator rejection) rather than stopping at the first. Callers
                (a completed wizard run about to persist an answers file, or a
                command about to proceed) must call this and refuse to
                continue/persist when it raises.
    @param[in]  specs Every ``FieldSpec`` the answer set must satisfy.
    @param[in]  answers Candidate ``FieldSpec.key`` to value mapping.
    @return     The normalized answer mapping, keyed by ``FieldSpec.key``, when
                every field is valid.
    @exception  InvalidAnswersError If one or more fields are missing (with no
                default) or fail validation; carries every offending key.
    """
    errors: dict[str, str] = {}
    normalized: dict[str, Any] = {}
    for spec in specs:
        if spec.key not in answers:
            if spec.default is not None:
                normalized[spec.key] = spec.default_value()
                continue
            errors[spec.key] = "missing and no default is set"
            continue
        try:
            normalized[spec.key] = spec.normalize(answers[spec.key])
        except ValidationError as exc:
            errors[spec.key] = str(exc)
    if errors:
        raise InvalidAnswersError(errors)
    return normalized


# END OF FILE
