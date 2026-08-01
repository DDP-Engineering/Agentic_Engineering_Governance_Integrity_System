#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_engine_journal.py
@brief Journal round-trip, resume, and home-resolution tests (T1.1).
@details Covers requirement R6 (safe to abort/re-run): a journal survives a
         write/read round-trip, a loaded journal never bypasses current-state
         detection, and the ``WAEGIS_HOME`` override is honoured. Strictly offline; all
         writes go under a pytest ``tmp_path``.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from waegis.engine import (
    STATUS_COMPLETED,
    Journal,
    StepStatus,
    run,
    waegis_home,
)
from waegis.version import WIZARD_VERSION
from waegis.lifecycle import FINGERPRINT_KEYS, find_resume_journal, stable_fingerprint

from _toy_catalog import act_counts, build_toy_catalog, make_ctx

# TESTS


def test_journal_round_trip(tmp_path: Path) -> None:
    """
    @brief      A journal written by a run reloads to an equal document.
    @param[in]  tmp_path Pytest-provided temporary directory (WAEGIS home).
    @return     None
    @exception  AssertionError If the reloaded journal differs.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    journal = Journal.begin(
        mode="test",
        wizard_version=WIZARD_VERSION,
        target=str(tmp_path / "repo"),
        home=tmp_path,
    )
    ctx = make_ctx()
    summary = run(build_toy_catalog(), ctx, journal=journal)
    assert summary.ok is True

    reloaded = Journal.load(journal.path)
    assert reloaded.to_dict() == journal.to_dict()
    assert reloaded.status == STATUS_COMPLETED
    assert reloaded.green_step_ids() == {"toy.a", "toy.b", "toy.c"}


def test_secrets_never_journaled_by_construction(tmp_path: Path) -> None:
    """
    @brief      Only values recorded via ``record_answer`` appear in the journal;
                the toy steps record no secret, so answers hold only their keys.
    @param[in]  tmp_path Temporary WAEGIS home.
    @return     None
    @exception  AssertionError If unexpected answer keys are journaled.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    journal = Journal.begin(mode="test", wizard_version=WIZARD_VERSION, home=tmp_path)
    run(build_toy_catalog(), make_ctx(), journal=journal)

    reloaded = Journal.load(journal.path)
    for step in reloaded.to_dict()["steps"]:
        assert set(step["answers"]).issubset({"toy.a_key", "toy.b_key", "toy.c_key"})


def test_resume_redetects_previously_green_steps(tmp_path: Path) -> None:
    """
    @brief      Loading a prior journal does not hide damage: a fresh context
                fails detection and the steps act again (R6).
    @param[in]  tmp_path Temporary WAEGIS home.
    @return     None
    @exception  AssertionError If a resumed step acts or is not skipped.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    catalog = build_toy_catalog()

    first = Journal.begin(mode="test", wizard_version=WIZARD_VERSION, home=tmp_path)
    run(catalog, make_ctx(), journal=first)

    # Fresh context: in-memory detected state is gone, so every checkpoint must
    # be re-detected and repaired rather than blindly skipped.
    prior = Journal.load(first.path)
    ctx2 = make_ctx()
    second = Journal.begin(mode="test", wizard_version=WIZARD_VERSION, home=tmp_path)
    summary = run(catalog, ctx2, journal=second, resume=prior)

    assert summary.ok is True
    assert {r.status for r in summary.results} == {StepStatus.DONE}
    assert act_counts(ctx2) == {"toy.a": 1, "toy.b": 1, "toy.c": 1}


def test_resume_iterable_is_only_a_redetection_hint(tmp_path: Path) -> None:
    """
    @brief      A bare iterable resume seed cannot bypass current detection.
    @param[in]  tmp_path Temporary WAEGIS home.
    @return     None
    @exception  AssertionError If a seeded id is not skipped.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ctx = make_ctx()
    summary = run(build_toy_catalog(), ctx, resume={"toy.a"})

    statuses = {r.step_id: r.status for r in summary.results}
    assert statuses["toy.a"] is StepStatus.DONE
    assert act_counts(ctx)["toy.a"] == 1
    assert statuses["toy.b"] is StepStatus.DONE


def test_waegis_home_override_respected(tmp_path: Path, monkeypatch) -> None:
    """
    @brief      ``WAEGIS_HOME`` overrides the default home, and journals land
                under it.
    @param[in]  tmp_path Temporary directory used as the override home.
    @param[in]  monkeypatch Pytest environment patcher.
    @return     None
    @exception  AssertionError If the override is not honoured.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    monkeypatch.setenv("WAEGIS_HOME", str(tmp_path))
    assert waegis_home() == tmp_path

    journal = Journal.begin(mode="test", wizard_version=WIZARD_VERSION)
    assert journal.path.parent == tmp_path / "journals"
    assert journal.path.exists()


def test_resume_lookup_requires_every_fingerprint(tmp_path: Path) -> None:
    """@brief An incomplete journal is reusable only when all five dimensions match."""
    fingerprints = {key: stable_fingerprint(key) for key in FINGERPRINT_KEYS}
    journal = Journal.begin(
        mode="new",
        wizard_version=WIZARD_VERSION,
        home=tmp_path,
        fingerprints=fingerprints,
    )
    assert find_resume_journal(tmp_path, expected_fingerprints=fingerprints).path == journal.path
    incompatible = dict(fingerprints)
    incompatible["payload"] = stable_fingerprint("different-payload")
    assert find_resume_journal(tmp_path, expected_fingerprints=incompatible) is None


def test_completed_journal_is_never_a_resume_candidate(tmp_path: Path) -> None:
    """@brief Completed checkpoints cannot suppress fresh lifecycle detection."""
    fingerprints = {key: stable_fingerprint(key) for key in FINGERPRINT_KEYS}
    journal = Journal.begin(
        mode="new",
        wizard_version=WIZARD_VERSION,
        home=tmp_path,
        fingerprints=fingerprints,
    )
    journal.finalize(status=STATUS_COMPLETED)
    assert find_resume_journal(tmp_path, expected_fingerprints=fingerprints) is None


def test_previous_layout_without_fingerprints_is_rejected(tmp_path: Path) -> None:
    """@brief The unreleased current schema has no compatibility reader."""
    journal = Journal.begin(mode="test", wizard_version=WIZARD_VERSION, home=tmp_path)
    document = journal.to_dict()
    del document["fingerprints"]
    journal.path.write_text(json.dumps(document), encoding="utf-8")
    try:
        Journal.load(journal.path)
    except ValueError as exc:
        assert "fingerprints" in str(exc)
    else:
        raise AssertionError("a previous journal layout must not be accepted")


def test_two_interleaved_journal_flushes_never_publish_a_mixed_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief      A second flush of the same journal that completes while the
                first is between its temp write and its publish must not
                corrupt or destroy either document.
    @details    A fixed ``<run-id>.json.tmp`` sibling is shared by every writer
                of that journal, so a second flush overwrote and then consumed
                the first flush's staged bytes and the first flush's own rename
                operated on a file that no longer held its content. Per-call
                unique temp names keep the two flushes independent.
    @param[in]  tmp_path Pytest-provided WAEGIS home.
    @param[in]  monkeypatch Used to suspend the first flush at its publish.
    @return     None
    @exception  AssertionError If the published journal is not valid, or a temp
                file is left behind.
    """
    journal = Journal.begin(mode="test", wizard_version=WIZARD_VERSION, home=tmp_path)
    real_replace = os.replace
    interleaved: list[bool] = []

    def interleaving_replace(source: object, destination: object) -> None:
        """@brief Let a whole second flush run inside the first one's publish."""
        if not interleaved:
            interleaved.append(True)
            journal.flush()
        return real_replace(source, destination)  # type: ignore[arg-type]

    monkeypatch.setattr(os, "replace", interleaving_replace)
    journal.flush()
    monkeypatch.undo()

    assert interleaved == [True]
    reloaded = Journal.load(journal.path)
    assert reloaded.run_id == journal.run_id
    leftovers = sorted(path.name for path in journal.path.parent.glob("*.tmp"))
    assert leftovers == []


# END OF FILE
