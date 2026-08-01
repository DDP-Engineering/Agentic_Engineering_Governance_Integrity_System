#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_adopt_prior_install.py
@brief Four-way repo.prior-install routing tests (T5.2, plan §8.2/§6).
@details Offline, no git. Proves the four *distinctly observable* routes, which
         ManifestState (three values) alone cannot produce: it collapses "no
         .agentic at all" and "bare .agentic without a manifest" both into
         ABSENT, so the step adds an explicit .agentic directory check. Cases:
         no .agentic -> "none"; valid manifest at the bundled version ->
         "current" (suggests doctor); valid manifest at an older version ->
         "older" (suggests upgrade); .agentic present without a manifest ->
         "legacy" (conservative path). Also proves declining "continue" stops
         the run while still recording the route.
@author Eng. Dan Dumitru Pasare
@date 2026-07-14
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

from pathlib import Path

import pytest

from waegis.commands.adopt import (
    ADOPT_OVER_EXISTING_INSTALL_KEY,
    SHARED_PRIOR_INSTALL_ROUTE,
    _act_prior_install,
)
from waegis.commands.new import SHARED_PAYLOAD_ROOT, SHARED_RUNNER, SHARED_TARGET
from waegis.engine import EngineContext, StepResult
from waegis.io.prompts import ScriptedAsker
from waegis.payload.manifest import MANIFEST_VERSION, Manifest, write_manifest

from _fake_command_runner import FakeCommandRunner

# CONSTANTS

# @brief The version the fake bundled payload declares (the "current" version).
_CURRENT_VERSION = "0.4.0"


# LOCAL HELPERS


def _fake_payload(tmp_path: Path, version: str = _CURRENT_VERSION) -> Path:
    """
    @brief      Build a minimal payload root declaring ``version`` so
                ``read_payload_version`` resolves the "current" version.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  version Version to declare.
    @return     The payload root path.
    @exception  OSError If the version file cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    root = tmp_path / "payload"
    cli_dir = root / ".agentic" / "cli"
    cli_dir.mkdir(parents=True)
    (cli_dir / "pyproject.toml").write_text(f'[project]\nversion = "{version}"\n', encoding="utf-8")
    return root


def _write_manifest(target: Path, payload_version: str) -> None:
    """
    @brief      Write a minimal *valid* install manifest at ``target``.
    @param[in]  target Target repository root.
    @param[in]  payload_version Version the manifest records.
    @return     None
    @exception  OSError If the manifest cannot be written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    write_manifest(
        target,
        Manifest(
            manifest_version=MANIFEST_VERSION,
            product="aegis",
            payload_version=payload_version,
            installed_at="2026-07-14T00:00:00Z",
            installed_by="test",
            mode="new",
            files={},
            generated=(),
            skipped=(),
        ),
    )


def _ctx(target: Path, payload: Path, *, confirm: bool) -> EngineContext:
    """
    @brief      Build a prior-install step context with an active StepResult so
                the recording helpers work outside the runner.
    @param[in]  target Target repository root.
    @param[in]  payload Fake payload root (for the current-version read).
    @details    The continue/stop confirmation defaults to refuse, so the
                scripted answer is supplied as the named decision rather than a
                blanket confirm value: a blanket "yes to everything" is exactly
                what the asker's per-default policy now refuses to accept for
                that class of question.
    @param[in]  confirm Scripted answer to the continue/stop confirmation.
    @return     A ready :class:`EngineContext`.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.2.0
    """
    ctx = EngineContext(
        mode="adopt",
        asker=ScriptedAsker(
            {ADOPT_OVER_EXISTING_INSTALL_KEY: confirm}, confirms=confirm
        ),
        shared={
            SHARED_TARGET: target,
            SHARED_RUNNER: FakeCommandRunner({}),
            SHARED_PAYLOAD_ROOT: payload,
        },
    )
    ctx._begin(StepResult(step_id="repo.prior-install"))
    return ctx


# TESTS


def test_route_none_when_no_agentic_directory(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A target with no ``.agentic`` routes to "none" and continues.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the route is not "none".
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    target.mkdir()
    ctx = _ctx(target, _fake_payload(tmp_path), confirm=True)
    _act_prior_install(ctx)
    assert ctx.shared[SHARED_PRIOR_INSTALL_ROUTE] == "none"


def test_route_current_when_manifest_matches_bundled_version(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A valid manifest at the bundled version routes to "current"
                (suggests doctor) and, on confirm, continues.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the route is not "current".
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    target.mkdir()
    _write_manifest(target, _CURRENT_VERSION)
    ctx = _ctx(target, _fake_payload(tmp_path, _CURRENT_VERSION), confirm=True)
    _act_prior_install(ctx)
    assert ctx.shared[SHARED_PRIOR_INSTALL_ROUTE] == "current"
    assert "doctor" in " ".join(ctx._require_current().messages)


def test_route_older_when_manifest_version_differs(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A valid manifest at a different version routes to "older"
                (suggests upgrade) and, on confirm, continues.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the route is not "older".
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    target.mkdir()
    _write_manifest(target, "0.0.1")
    ctx = _ctx(target, _fake_payload(tmp_path, _CURRENT_VERSION), confirm=True)
    _act_prior_install(ctx)
    assert ctx.shared[SHARED_PRIOR_INSTALL_ROUTE] == "older"
    assert "upgrade" in " ".join(ctx._require_current().messages)


def test_route_legacy_when_agentic_present_without_manifest(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      A bare ``.agentic`` directory with no manifest routes to "legacy"
                (the conservative path) - the case ManifestState.ABSENT cannot
                distinguish from "no .agentic at all".
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the route is not "legacy".
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    (target / ".agentic").mkdir(parents=True)
    ctx = _ctx(target, _fake_payload(tmp_path), confirm=True)
    _act_prior_install(ctx)
    assert ctx.shared[SHARED_PRIOR_INSTALL_ROUTE] == "legacy"


def test_declining_continue_stops_but_records_route(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """
    @brief      Declining "continue anyway" on an already-installed repo raises
                (stopping the run before deploy.adoption-copy) while still
                recording the route for observability.
    @param[in]  tmp_path Pytest tmp fixture.
    @return     None
    @exception  AssertionError If the stop did not raise or record the route.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target = tmp_path / "repo"
    target.mkdir()
    _write_manifest(target, _CURRENT_VERSION)
    ctx = _ctx(target, _fake_payload(tmp_path, _CURRENT_VERSION), confirm=False)
    with pytest.raises(RuntimeError):
        _act_prior_install(ctx)
    assert ctx.shared[SHARED_PRIOR_INSTALL_ROUTE] == "current"


# END OF FILE
