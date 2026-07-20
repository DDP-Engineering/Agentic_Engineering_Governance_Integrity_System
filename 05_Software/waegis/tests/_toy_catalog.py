#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file _toy_catalog.py
@brief Test-only toy catalog and engine fakes for the WAEGIS engine suite (T1.1).
@details Not collected by pytest (underscore prefix). Provides a deterministic
         three-step catalog (``toy.a`` auto, ``toy.b`` assisted depending on
         ``toy.a``, ``toy.c`` auto depending on ``toy.b``), plus a
         ``ScriptAsker`` and a ``RecordingSink``, so the runner/catalog/journal
         behaviours can be exercised entirely offline. All step state lives in
         ``EngineContext.shared`` so one catalog can be re-run against fresh
         contexts (the resume scenario).
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from typing import Any

from waegis.engine import (
    Asker,
    Automation,
    Catalog,
    EngineContext,
    EngineEvent,
    Phase,
    Remediation,
    StepSpec,
)

# DATA MODELS / TYPEDEFINITIONS


class ScriptAsker:
    """
    @brief Deterministic :class:`Asker` for tests.
    @details ``confirm`` returns queued answers in order, falling back to
             ``default_confirm`` when the queue is empty, and records every
             prompt seen. ``ask`` returns a value from a preset mapping (or the
             field default). No console interaction.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(
        self,
        confirms: list[bool] | None = None,
        answers: dict[str, str] | None = None,
        default_confirm: bool = True,
    ) -> None:
        self._confirms = list(confirms) if confirms else []
        self._answers = dict(answers) if answers else {}
        self.default_confirm = default_confirm
        self.confirm_prompts: list[str] = []
        self.ask_keys: list[str] = []

    def confirm(self, prompt: str, *, default: bool = True) -> bool:
        self.confirm_prompts.append(prompt)
        if self._confirms:
            return self._confirms.pop(0)
        return self.default_confirm

    def ask(self, key: str, prompt: str, *, default: str | None = None) -> str:
        self.ask_keys.append(key)
        if key in self._answers:
            return self._answers[key]
        return default if default is not None else ""


class RecordingSink:
    """
    @brief :class:`EventSink` that stores every emitted event for assertions.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """

    def __init__(self) -> None:
        self.events: list[EngineEvent] = []

    def emit(self, event: EngineEvent) -> None:
        self.events.append(event)

    def of_type(self, event_type: type) -> list[EngineEvent]:
        """
        @brief      Events of a given concrete type, in emission order.
        @param[in]  event_type Event class to filter by.
        @return     List of matching events.
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return [e for e in self.events if type(e) is event_type]


# HELPER FUNCTIONS


def _state(ctx: EngineContext) -> dict[str, Any]:
    """
    @brief      Fetch (creating if needed) the toy state on the context.
    @param[in]  ctx Engine context whose ``shared`` holds the toy state.
    @return     Mutable state dict with ``order``, ``flags``, and ``acts``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return ctx.shared.setdefault("toy", {"order": [], "flags": {}, "acts": {}})


def _detect(step_id: str):
    def fn(ctx: EngineContext) -> bool:
        st = _state(ctx)
        st["order"].append((step_id, "detect"))
        return bool(st["flags"].get(step_id, False))

    return fn


def _act(step_id: str, *, raise_exc: bool = False):
    def fn(ctx: EngineContext) -> None:
        st = _state(ctx)
        st["order"].append((step_id, "act"))
        st["acts"][step_id] = st["acts"].get(step_id, 0) + 1
        if raise_exc:
            raise RuntimeError(f"{step_id} act boom")
        st["flags"][step_id] = True
        ctx.record_artifact(f"{step_id}.artifact")
        ctx.record_answer(f"{step_id}_key", "value")

    return fn


def _verify(step_id: str, *, ok: bool = True):
    def fn(ctx: EngineContext) -> bool:
        st = _state(ctx)
        st["order"].append((step_id, "verify"))
        return ok and bool(st["flags"].get(step_id, False))

    return fn


def _on_fail(step_id: str):
    def fn(ctx: EngineContext) -> Remediation:
        return Remediation(
            diagnosis=f"{step_id} failed",
            remediation="retry the wizard",
            it_request=None,
        )

    return fn


def _toy_step(
    step_id: str,
    automation: Automation,
    preconditions: tuple[str, ...],
    *,
    fail_step: str | None,
    fail_mode: str,
) -> StepSpec:
    """
    @brief      Build one toy step, optionally wired to fail.
    @param[in]  step_id Step id.
    @param[in]  automation Automation level.
    @param[in]  preconditions Precondition ids.
    @param[in]  fail_step Which step should fail (or ``None``).
    @param[in]  fail_mode ``"act"`` (act raises) or ``"verify"`` (verify false).
    @return     The configured :class:`StepSpec`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    act_raises = fail_step == step_id and fail_mode == "act"
    verify_ok = not (fail_step == step_id and fail_mode == "verify")
    return StepSpec(
        id=step_id,
        title=f"Toy {step_id[-1].upper()}",
        why=f"Toy step {step_id} exists only to exercise the engine.",
        phase=Phase.P0_MACHINE,
        automation=automation,
        preconditions=preconditions,
        detect=_detect(step_id),
        act=_act(step_id, raise_exc=act_raises),
        verify=_verify(step_id, ok=verify_ok),
        on_fail=_on_fail(step_id),
        change_summary=lambda ctx, sid=step_id: f"would run {sid}",
    )


# PUBLIC API


def build_toy_catalog(
    *,
    fail_step: str | None = None,
    fail_mode: str = "verify",
    include_optional: bool = False,
) -> Catalog:
    """
    @brief      Build the deterministic three-step toy catalog (optionally with a
                fourth ``applies``-gated step, or a step wired to fail).
    @param[in]  fail_step Step id that should fail, or ``None`` for all-green.
    @param[in]  fail_mode ``"act"`` (act raises) or ``"verify"`` (verify false).
    @param[in]  include_optional Add ``toy.opt`` gated on ``shared['include_opt']``.
    @return     A validated :class:`Catalog`.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    steps = [
        _toy_step("toy.a", Automation.AUTO, (), fail_step=fail_step, fail_mode=fail_mode),
        _toy_step("toy.b", Automation.ASSISTED, ("toy.a",), fail_step=fail_step, fail_mode=fail_mode),
        _toy_step("toy.c", Automation.AUTO, ("toy.b",), fail_step=fail_step, fail_mode=fail_mode),
    ]
    if include_optional:
        steps.append(
            StepSpec(
                id="toy.opt",
                title="Toy optional",
                why="Only applies when the optional branch is enabled.",
                phase=Phase.P0_MACHINE,
                automation=Automation.AUTO,
                applies=lambda ctx: bool(ctx.shared.get("include_opt", False)),
                detect=_detect("toy.opt"),
                act=_act("toy.opt"),
                verify=_verify("toy.opt"),
                on_fail=_on_fail("toy.opt"),
            )
        )
    return Catalog(steps)


def make_ctx(
    *,
    asker: Asker | None = None,
    sink: Any | None = None,
    shared: dict[str, Any] | None = None,
    mode: str = "test",
) -> EngineContext:
    """
    @brief      Build an :class:`EngineContext` for tests.
    @param[in]  asker Asker to use (defaults to an all-yes :class:`ScriptAsker`).
    @param[in]  sink Event sink (defaults to a :class:`RecordingSink`).
    @param[in]  shared Initial shared state.
    @param[in]  mode Wizard mode label.
    @return     A ready :class:`EngineContext`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return EngineContext(
        mode=mode,
        asker=asker if asker is not None else ScriptAsker(),
        events=sink if sink is not None else RecordingSink(),
        shared=shared if shared is not None else {},
    )


def act_counts(ctx: EngineContext) -> dict[str, int]:
    """
    @brief      How many times each toy step's ``act`` ran on this context.
    @param[in]  ctx Engine context holding the toy state.
    @return     Mapping of step id to act invocation count.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return dict(_state(ctx)["acts"])


def call_order(ctx: EngineContext) -> list[tuple[str, str]]:
    """
    @brief      Ordered (step_id, phase) record of detect/act/verify calls.
    @param[in]  ctx Engine context holding the toy state.
    @return     List of ``(step_id, phase)`` tuples in call order.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return list(_state(ctx)["order"])


# END OF FILE
