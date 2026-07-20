#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file step.py
@brief Step contract surface for the WAEGIS engine.
@details Defines the whole engine contract that both wizard journeys share
         (plan §4): the ``StepSpec`` (a data description of one detect/act/verify
         step), the ``StepResult`` record, the ``Automation``/``Phase``/
         ``StepStatus`` enumerations, the ``Remediation`` payload, the minimal
         ``Asker`` prompting protocol, the ``EngineContext`` passed to every step
         callable, and the event types (``EngineEvent`` subclasses + ``EventSink``
         protocol) through which the runner reports progress without printing.
         The engine imports only the standard library and itself; frontends
         (T1.3 console, M8 GUI) implement ``Asker`` and ``EventSink``.
@details ``verify`` is a required part of the contract: a ``StepSpec`` built
         without one is rejected at construction, so a verify-less step is
         unrepresentable (plan §4 R5). Step ids are a frozen public contract and
         are never renamed once released.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable

# DATA MODELS / TYPEDEFINITIONS


class EngineError(Exception):
    """
    @brief Base class for every error raised by the WAEGIS step engine.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class StepContractError(EngineError):
    """
    @brief Raised when a ``StepSpec`` violates the step contract (e.g. no
           ``verify``).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class CatalogError(EngineError):
    """
    @brief Raised when a catalog is inconsistent (duplicate ids, unknown
           preconditions, or precondition cycles).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class Automation(Enum):
    """
    @brief How much autonomy the wizard has for a step (plan §4).
    @details ``AUTO`` acts with no confirmation; ``ASSISTED`` acts only after the
             operator confirms; ``MANUAL`` means the human acts while the wizard
             guides and then verifies.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    AUTO = "auto"
    ASSISTED = "assisted"
    MANUAL = "manual"


class Phase(Enum):
    """
    @brief Coarse ordering band a step belongs to (plan §4).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    P0_MACHINE = "P0-machine"
    P1_PREREQ = "P1-prereq"
    P2_NETWORK = "P2-network"
    P3_REPO = "P3-repo"
    P4_DEPLOY = "P4-deploy"
    P5_HANDOFF = "P5-handoff"


class StepStatus(Enum):
    """
    @brief Terminal (or pending) state of a step within one run.
    @details ``SKIPPED`` and ``DONE`` are the two "green" outcomes: ``SKIPPED``
             when ``detect`` already found the step satisfied (or it was seeded
             green on resume), ``DONE`` when ``act`` ran and ``verify`` passed.
             ``FAILED`` covers an ``act`` exception or a false ``verify``;
             ``DECLINED`` is a refused assisted-step confirmation; ``BLOCKED`` is
             an unmet precondition; ``NOT_APPLICABLE`` is a step ``applies``
             filtered out.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    PENDING = "pending"
    SKIPPED = "skipped"
    DONE = "done"
    FAILED = "failed"
    DECLINED = "declined"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"


# @brief The two step statuses that count as "green" (satisfied) for
#        precondition resolution and resume seeding.
GREEN_STATUSES: frozenset[StepStatus] = frozenset({StepStatus.SKIPPED, StepStatus.DONE})


@dataclass(frozen=True)
class Remediation:
    """
    @brief Novice-readable failure guidance returned by ``StepSpec.on_fail``.
    @details ``it_request`` is optional copyable text the operator can forward to
             IT for restrictions they cannot resolve themselves (plan §4).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    diagnosis: str
    remediation: str
    it_request: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the remediation to a JSON-safe mapping.
        @return     Mapping with ``diagnosis``, ``remediation``, ``it_request``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return {
            "diagnosis": self.diagnosis,
            "remediation": self.remediation,
            "it_request": self.it_request,
        }


@dataclass
class StepResult:
    """
    @brief Mutable per-step record accumulated as a step runs.
    @details Carries the detect/act/verify outcomes, ISO-8601 timestamps, the
             non-secret answers and artifacts the step recorded, any human notes,
             and the remediation/error captured on failure. One ``StepResult`` is
             produced per step per run and is the unit the journal persists.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str
    status: StepStatus = StepStatus.PENDING
    detected: bool | None = None
    acted: bool = False
    verified: bool | None = None
    started_at: str | None = None
    finished_at: str | None = None
    answers: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    failure: Remediation | None = None
    error: str | None = None

    def is_green(self) -> bool:
        """
        @brief      Report whether this result is a satisfied ("green") outcome.
        @return     ``True`` when the status is ``SKIPPED`` or ``DONE``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return self.status in GREEN_STATUSES

    def to_dict(self) -> dict[str, Any]:
        """
        @brief      Serialize the result to a JSON-safe mapping (journal schema).
        @return     Mapping keyed ``id, status, detected, acted, verified,
                    started_at, finished_at, answers, artifacts, messages,
                    failure, error``.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        return {
            "id": self.step_id,
            "status": self.status.value,
            "detected": self.detected,
            "acted": self.acted,
            "verified": self.verified,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "answers": dict(self.answers),
            "artifacts": list(self.artifacts),
            "messages": list(self.messages),
            "failure": self.failure.to_dict() if self.failure is not None else None,
            "error": self.error,
        }


# HELPER FUNCTIONS


# @brief Sentinel marking an unset ``verify`` so a verify-less step is rejected
#        at construction rather than silently defaulting to a permissive check.
_VERIFY_UNSET: Callable[[Any], bool] = lambda ctx: False  # noqa: E731


def _default_on_fail(ctx: "EngineContext") -> Remediation:
    """
    @brief      Generic remediation used when a ``StepSpec`` supplies no
                ``on_fail`` of its own.
    @param[in]  ctx Engine context for the failed step (unused by the default).
    @return     A neutral :class:`Remediation` pointing the operator at the run
                journal.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    return Remediation(
        diagnosis="The step could not be verified as complete.",
        remediation="Review the run journal for details and re-run the wizard; "
        "steps already green will be detected and skipped.",
        it_request=None,
    )


# @brief Default ``applies`` predicate: every step applies unless it opts out.
_DEFAULT_APPLIES: Callable[["EngineContext"], bool] = lambda ctx: True  # noqa: E731

# @brief Default ``detect`` predicate: assume not already satisfied.
_DEFAULT_DETECT: Callable[["EngineContext"], bool] = lambda ctx: False  # noqa: E731

# @brief Default ``act``: a no-op, for pure-check steps that only verify.
_DEFAULT_ACT: Callable[["EngineContext"], None] = lambda ctx: None  # noqa: E731

# @brief Default ``change_summary``: no preview text.
_DEFAULT_SUMMARY: Callable[["EngineContext"], str] = lambda ctx: ""  # noqa: E731


# PUBLIC API


@dataclass(frozen=True)
class StepSpec:
    """
    @brief Immutable description of one wizard step (plan §4).
    @details A step is data: a set of small callables invoked with an
             :class:`EngineContext`. ``verify`` is required and machine-checkable;
             the other callables carry sensible defaults so a pure-check step need
             only supply ``verify``. ``preconditions`` names step ids that must be
             green first. ``applies`` lets one catalog serve both wizard modes.
             ``id`` is a stable public key and is never renamed once released.
    @note    ``verify`` defaults to a rejecting sentinel; ``__post_init__`` raises
             :class:`StepContractError` if it is left unset or is not callable, so
             a verify-less step cannot be constructed.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    id: str
    title: str
    why: str
    phase: Phase
    automation: Automation
    verify: Callable[["EngineContext"], bool] = _VERIFY_UNSET
    preconditions: tuple[str, ...] = ()
    applies: Callable[["EngineContext"], bool] = _DEFAULT_APPLIES
    detect: Callable[["EngineContext"], bool] = _DEFAULT_DETECT
    act: Callable[["EngineContext"], None] = _DEFAULT_ACT
    on_fail: Callable[["EngineContext"], Remediation] = _default_on_fail
    change_summary: Callable[["EngineContext"], str] = _DEFAULT_SUMMARY

    def __post_init__(self) -> None:
        """
        @brief      Enforce the step contract at construction time.
        @return     None
        @exception  StepContractError If ``id`` is empty, ``verify`` was left
                    unset, or any of the contract callables is not callable.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        if not self.id:
            raise StepContractError("StepSpec requires a non-empty id")
        if self.verify is _VERIFY_UNSET:
            raise StepContractError(
                f"step {self.id!r} must supply a verify() callable (verify is required)"
            )
        for name in ("verify", "applies", "detect", "act", "on_fail", "change_summary"):
            if not callable(getattr(self, name)):
                raise StepContractError(f"step {self.id!r}: {name} must be callable")


@runtime_checkable
class Asker(Protocol):
    """
    @brief Minimal prompting protocol the engine depends on (plan §4).
    @details Keeps the engine free of any console/GUI code: the runner uses
             ``confirm`` for the plan-approval gate and assisted-step
             confirmations, and steps use ``ask`` to gather answers. T1.2 supplies
             the ``ConsoleAsker``/``ScriptedAsker`` implementations.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def confirm(self, prompt: str, *, default: bool = True) -> bool:
        """
        @brief      Ask a yes/no question.
        @param[in]  prompt Question text.
        @param[in]  default Value assumed when the operator gives no answer.
        @return     The operator's boolean choice.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        ...

    def ask(self, key: str, prompt: str, *, default: str | None = None) -> str:
        """
        @brief      Ask for a free-text answer.
        @param[in]  key Stable answer key (used by answers files / journaling).
        @param[in]  prompt Question text.
        @param[in]  default Suggested default answer, if any.
        @return     The operator's answer.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        ...


@runtime_checkable
class EventSink(Protocol):
    """
    @brief Sink the runner emits progress events to (plan §4: the engine never
           prints).
    @details A single ``emit`` keeps frontends simple and lets the M8 GUI
             serialize each event. The engine defaults to :class:`NullSink`.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def emit(self, event: "EngineEvent") -> None:
        """
        @brief      Receive one engine event.
        @param[in]  event The emitted :class:`EngineEvent`.
        @return     None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        ...


class NullSink:
    """
    @brief Event sink that discards every event (engine default).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def emit(self, event: "EngineEvent") -> None:
        """
        @brief      Discard the event.
        @param[in]  event Ignored.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return None


@dataclass
class EngineContext:
    """
    @brief Shared state handed to every step callable during a run.
    @details Carries the wizard ``mode``, the injected ``asker`` and event
             ``events`` sink, and a free ``shared`` scratch mapping for steps and
             commands (e.g. the target path or probe results). While a step runs
             the runner activates that step's :class:`StepResult`; the
             ``record_answer``/``record_artifact``/``note`` helpers append to it.
             Only ``record_answer`` writes into the journalled ``answers`` map, so
             secret values (never passed here) cannot reach the journal.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    mode: str
    asker: Asker
    events: EventSink = field(default_factory=NullSink)
    shared: dict[str, Any] = field(default_factory=dict)
    _current: StepResult | None = field(default=None, repr=False, compare=False)

    def _begin(self, result: StepResult) -> None:
        """
        @brief      Activate the result the recording helpers append to.
        @param[in]  result The step result now being produced.
        @return     None
        @exception  None
        @note       Called by the runner; not part of the step-facing API.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        self._current = result

    def _end(self) -> None:
        """
        @brief      Deactivate the current result once a step finishes.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        self._current = None

    def _require_current(self) -> StepResult:
        """
        @brief      Return the active result or fail if called outside a step.
        @return     The active :class:`StepResult`.
        @exception  EngineError If no step is currently running.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        if self._current is None:
            raise EngineError("recording helpers may only be used while a step runs")
        return self._current

    def record_answer(self, key: str, value: Any) -> None:
        """
        @brief      Record a non-secret answer for the running step's journal.
        @param[in]  key Stable answer key.
        @param[in]  value JSON-serializable answer value. Never pass secrets.
        @return     None
        @exception  EngineError If called outside a running step.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        self._require_current().answers[key] = value

    def record_artifact(self, path: str) -> None:
        """
        @brief      Record an artifact (created path, commit ref, ...) the step
                    produced.
        @param[in]  path Human-readable artifact identifier.
        @return     None
        @exception  EngineError If called outside a running step.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        self._require_current().artifacts.append(path)

    def note(self, message: str) -> None:
        """
        @brief      Attach a human-readable note to the running step's result.
        @param[in]  message Note text.
        @return     None
        @exception  EngineError If called outside a running step.
        @author     Eng. Dan Dumitru Pasare
        @date       2026-07-12
        @version    0.1.0
        """
        self._require_current().messages.append(message)


# @brief Engine progress events. ``EngineEvent`` is the frozen base; the runner
#        emits the concrete subclasses below and frontends dispatch on type.


@dataclass(frozen=True)
class EngineEvent:
    """
    @brief Base type for every event the runner emits through an ``EventSink``.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


@dataclass(frozen=True)
class RunStarted(EngineEvent):
    """
    @brief Emitted once when a run begins.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    mode: str
    dry_run: bool
    step_ids: tuple[str, ...]


@dataclass(frozen=True)
class PlanReady(EngineEvent):
    """
    @brief Emitted with the ordered plan preview before any mutation.
    @note ``plan`` holds a :class:`waegis.engine.plan.Plan`; it is typed loosely
          here so the contract module stays free of a plan-module import.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    plan: Any


@dataclass(frozen=True)
class PlanApproved(EngineEvent):
    """
    @brief Emitted when the operator approves the plan at the preview gate.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


@dataclass(frozen=True)
class PlanRejected(EngineEvent):
    """
    @brief Emitted when the operator declines the plan at the preview gate.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


@dataclass(frozen=True)
class StepStarted(EngineEvent):
    """
    @brief Emitted when a step begins its detect/act/verify cycle.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str
    title: str
    phase: Phase
    automation: Automation


@dataclass(frozen=True)
class StepDetected(EngineEvent):
    """
    @brief Emitted after a step's ``detect`` runs.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str
    satisfied: bool


@dataclass(frozen=True)
class StepActed(EngineEvent):
    """
    @brief Emitted after a step's ``act`` returns.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str


@dataclass(frozen=True)
class StepVerified(EngineEvent):
    """
    @brief Emitted after a step's ``verify`` runs.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str
    ok: bool


@dataclass(frozen=True)
class StepFinished(EngineEvent):
    """
    @brief Emitted once per step with its terminal result (any status).
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    result: StepResult


@dataclass(frozen=True)
class Note(EngineEvent):
    """
    @brief Emitted for an informational message not tied to a lifecycle point.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    step_id: str | None
    message: str


@dataclass(frozen=True)
class RunFinished(EngineEvent):
    """
    @brief Emitted once when a run ends (completed, stopped, or dry-run).
    @note ``summary`` holds a :class:`waegis.engine.runner.RunSummary`; typed
          loosely so the contract module stays free of a runner-module import.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    summary: Any


# END OF FILE
