#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_protocol.py
@brief The CodeGraph response protocol, its renderings and its budgets.
@details Covers REQ-FUNC-8cb1a3b7 (envelope fields kept separate),
         REQ-UX-461978be (compact text and single JSON views),
         REQ-NFR-17c50caa (record-boundary byte and count budgets) and the
         token format behind REQ-FUNC-ff8000c4 (request-bound paging).
"""

# IMPORTS

from __future__ import annotations

import json

import pytest

from codegraph import protocol

# CONSTANTS

SYMBOL = {"id": "8f31c2a90b" + "0" * 22, "display_id": "8f31c2a90b", "kind": "function",
          "name": "select_files", "qualified_name": "scope.select_files",
          "signature": "def select_files(config, inventory)", "path": "codegraph/scope.py",
          "start": {"line": 41, "column": 1}, "end": {"line": 77, "column": 20},
          "role": "source", "language": "python", "citation": "current"}
META = {"snapshot": "5c0d2e9a41" + "1" * 22, "generation": 3,
        "indexed_at": "2026-10-03T10:00:00.000000Z"}
CAPABLE = {"indexing_supported": True, "python_support": "tested"}

# HELPER FUNCTIONS


def find_envelope(records: list, **extra) -> dict:
    """@brief A served `find` envelope around the given records."""
    return protocol.envelope("find", index="ready", freshness="not_fully_checked",
                             capability=CAPABLE, meta=META, results=records, **extra)

# TESTS - envelope (REQ-FUNC-8cb1a3b7)


def test_envelope_keeps_status_index_freshness_and_capability_separate():
    """REQ-FUNC-8cb1a3b7: an empty search is ok, a missing index unavailable."""
    empty = find_envelope([])
    assert (empty["status"], empty["results"], empty["index"]) == ("ok", [], "ready")
    missing = protocol.envelope("find", status="unavailable", reason="missing",
                                message="No CodeGraph index yet.", index="missing",
                                capability=CAPABLE)
    assert (missing["status"], missing["index"], missing["freshness"]) == \
        ("unavailable", "missing", None)
    for env in (empty, missing):
        protocol.validate(env)
        assert (env["schema"], env["provider"], env["protocol"]) == (1, "codegraph", 1)


@pytest.mark.parametrize("status", protocol.STATUSES)
def test_every_status_value_validates(status: str):
    """REQ-FUNC-8cb1a3b7: one fixture per status value."""
    env = protocol.envelope("status", status=status,
                            reason=None if status == "ok" else "missing",
                            message=None if status == "ok" else "explained",
                            index=None if status == "disabled" else "missing",
                            capability=None if status == "disabled" else CAPABLE)
    protocol.validate(env)


@pytest.mark.parametrize("index", protocol.INDEX_STATES)
@pytest.mark.parametrize("freshness", (*protocol.FRESHNESS, None))
def test_every_index_and_freshness_value_validates(index: str, freshness):
    """REQ-FUNC-8cb1a3b7: the state vocabularies are closed and accepted."""
    protocol.validate(protocol.envelope("check", index=index, freshness=freshness,
                                        capability=CAPABLE, meta=META))


@pytest.mark.parametrize("broken", [
    {"status": "fine"}, {"index": "half"}, {"freshness": "maybe"},
    {"schema": 2}, {"provider": "other"}, {"protocol": 9}, {"action": "drop"},
])
def test_values_outside_the_vocabulary_are_rejected(broken: dict):
    """REQ-FUNC-8cb1a3b7: the validator is strict."""
    env = find_envelope([])
    env.update(broken)
    with pytest.raises(ValueError):
        protocol.validate(env)

# TESTS - renderings (REQ-UX-461978be)


def test_compact_text_matches_the_golden_example():
    """REQ-UX-461978be: header, one line per record, footer."""
    text = protocol.render_text(find_envelope([SYMBOL]))
    assert text == (
        "CodeGraph | find | ok | index=ready | freshness=not_fully_checked"
        " | snapshot=5c0d2e9a41 gen=3\n"
        "scope.select_files(config, inventory) | codegraph/scope.py:41-77 | id=8f31c2a90b\n"
        "shown=1 | more=no")


def test_unavailable_text_carries_the_fallback_message():
    """REQ-UX-461978be: non-ok responses explain what to do instead."""
    env = protocol.envelope("find", status="unavailable", reason="missing",
                            message="No CodeGraph index yet. Run know_graph_index, "
                                    "or use ordinary search.",
                            index="missing", capability=CAPABLE)
    assert protocol.render_text(env) == (
        "CodeGraph | find | unavailable | index=missing | freshness=- | snapshot=- gen=-\n"
        "shown=0 | more=no\n"
        "No CodeGraph index yet. Run know_graph_index, or use ordinary search.")


def test_text_envelope_view_carries_text_instead_of_records():
    """REQ-UX-461978be: AEGIS receives one rendering, never both."""
    env = find_envelope([SYMBOL])
    view = protocol.view(env, "text-envelope")
    assert "results" not in view and "details" not in view
    assert view["text"] == protocol.render_text(env)
    json_view = protocol.view(env, "json")
    assert "text" not in json_view and json_view["results"] == [SYMBOL]
    assert json.loads(protocol.serialize(json_view)) == json_view

# TESTS - budgets (REQ-NFR-17c50caa)


def test_byte_budget_drops_whole_records_and_reports_more():
    """REQ-NFR-17c50caa: output fits, stays valid, and never cuts a record."""
    records = [dict(SYMBOL, name=f"name{index}") for index in range(200)]
    for view_name in ("json", "text-envelope", "text"):
        env = protocol.fit(find_envelope(records), max_bytes=2048, view_name=view_name)
        output = protocol.output(env, view_name)
        assert len(output.encode("utf-8")) <= 2048, view_name
        assert env["has_more"] is True
        assert 0 < len(env["results"]) < 200
        if view_name != "text":
            json.loads(output)


def test_enlarged_budget_is_capped_at_32_kib():
    """REQ-NFR-17c50caa: an explicit enlargement never exceeds 32768 bytes."""
    records = [dict(SYMBOL, name=f"name{index}") for index in range(2000)]
    env = protocol.fit(find_envelope(records), max_bytes=100000, view_name="json")
    assert len(protocol.output(env, "json").encode("utf-8")) <= 32768


def test_small_results_are_untouched():
    """REQ-NFR-17c50caa: nothing is dropped when everything fits."""
    env = protocol.fit(find_envelope([SYMBOL]), max_bytes=8192, view_name="json")
    assert env["has_more"] is False and env["results"] == [SYMBOL]

# TESTS - paging tokens (REQ-FUNC-ff8000c4)


def test_page_tokens_round_trip_and_bind_the_request():
    """REQ-FUNC-ff8000c4: tokens carry snapshot, request digest and offset."""
    digest = protocol.request_digest("find", "save", "rank", 20)
    token = protocol.encode_page(META["snapshot"], digest, 40)
    assert protocol.decode_page(token) == (META["snapshot"], digest, 40)
    assert digest != protocol.request_digest("find", "load", "rank", 20)
    assert digest != protocol.request_digest("find", "save", "rank", 10)
    with pytest.raises(ValueError):
        protocol.decode_page("not-a-token")

# TESTS - exit codes


@pytest.mark.parametrize("status, code", [
    ("ok", 0), ("ambiguous", 0), ("not_found", 0), ("expired", 0),
    ("unavailable", 0), ("disabled", 0), ("error", 1)])
def test_exit_codes_follow_the_status(status: str, code: int):
    """REQ-FUNC-8cb1a3b7: only `error` fails."""
    assert protocol.exit_code(status) == code

# TESTS - review fixes: names, reasons, per-action fixtures (REQ-UX-461978be, REQ-FUNC-8cb1a3b7)

SHORT_SYMBOL = {"id": "a" * 32, "display_id": "aaaaaaaaaa", "kind": "function", "name": "f",
          "qualified_name": "m.f", "signature": "def f(x)", "path": "m.py",
          "start": {"line": 1, "column": 1}, "end": {"line": 2, "column": 5},
          "role": "source", "language": "python", "depth": 1, "citation": "current"}
SHORT_REFERENCE = {"kind": "call", "label": "lexical-binding", "path": "n.py", "line": 7,
             "column": 3, "spelling": "f", "target": "a" * 32, "from": None,
             "from_display": None, "citation": "current"}


@pytest.mark.parametrize("name, signature, expected", [
    ("f", "def f(x)", "m.f(x) |"), ("a", "async def a(d) -> b", "m.a(d) -> b |"),
    ("C", "class C(Base)", "m.C(Base) |"), ("de", "def de()", "m.de() |")])
def test_short_names_render_with_their_parameters(name: str, signature: str, expected: str):
    """REQ-UX-461978be: the name is found after the keyword, never inside it."""
    record = dict(SHORT_SYMBOL, name=name, signature=signature, qualified_name=f"m.{name}",
                  kind="class" if signature.startswith("class") else "function")
    assert protocol._symbol_line(record).startswith(expected)


def test_reasons_come_from_the_vocabulary():
    """REQ-FUNC-8cb1a3b7: every emitted reason is listed; anything else is rejected."""
    for reason in ("not_found", "ambiguous", "expired", "internal", "invalid_request"):
        protocol.validate(protocol.envelope("find", "error", reason=reason))
    with pytest.raises(ValueError):
        protocol.validate(protocol.envelope("find", "error", reason="bogus"))


def fixture(action: str) -> dict:
    """@brief A representative response for one action."""
    if action in ("find", "file"):
        return protocol.envelope(action, results=[SHORT_SYMBOL], index="ready")
    if action == "symbol":
        return protocol.envelope(action, results=[dict(SHORT_REFERENCE, relation="caller")],
                                 details={"symbol": SHORT_SYMBOL}, index="ready")
    if action == "callers":
        return protocol.envelope(action, results=[SHORT_REFERENCE],
                                 details={"candidates": [dict(SHORT_REFERENCE, line=9,
                                                              label="candidate")]},
                                 index="ready")
    if action == "refs":
        return protocol.envelope(action, results=[SHORT_REFERENCE], index="ready")
    return protocol.envelope(action, index="ready", freshness="current",
                             details={"files": {"indexed": 3}, "inventory": "git"})


@pytest.mark.parametrize("action", protocol.ACTIONS)
def test_every_action_has_a_valid_fixture_whose_views_agree(action: str):
    """REQ-FUNC-8cb1a3b7: one fixture per action validates, and text matches JSON."""
    env = fixture(action)
    protocol.validate(env)
    shown = json.loads(protocol.output(env, "json"))
    text = protocol.render_text(env)
    assert f"shown={protocol.record_count(shown)}" in text
    records = shown["results"] + shown["details"].get("candidates", [])
    for record in records:
        assert f"{record['path']}:{record.get('line') or record['start']['line']}" in text
    for key, value in shown["details"].items():
        if isinstance(value, str):
            assert f"{key}: {value}" in text

def test_one_oversized_record_is_shortened_to_fit_the_hard_cap():
    """REQ-NFR-17c50caa: the record a page keeps never pushes it past 32768 bytes."""
    long_path = "src/" + "deep/" * 120 + "m.py"
    huge = dict(SHORT_SYMBOL, signature="def f(x='" + "a" * 70000 + "')", path=long_path)
    for view_name in ("json", "text-envelope"):
        env = protocol.fit(protocol.envelope("find", results=[huge, SHORT_SYMBOL]), 8192,
                           view_name, next_page=lambda kept: f"token-{kept}")
        assert len(protocol.output(env, view_name).encode("utf-8")) <= protocol.HARD_BYTE_CAP
        assert len(env["results"]) == 1 and env["results"][0]["signature"].endswith("\u2026")
        assert env["results"][0]["path"] == long_path   # a citation is never cut
        assert env["results"][0]["id"] == huge["id"]
        assert env["next_page"] == "token-1"
    symbol = protocol.fit(protocol.envelope("symbol", details={"symbol": huge}), 8192, "json")
    assert len(protocol.output(symbol, "json").encode("utf-8")) <= protocol.HARD_BYTE_CAP

# END OF FILE
