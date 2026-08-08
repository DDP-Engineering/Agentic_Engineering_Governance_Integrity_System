#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_payload_inventory.py
@brief Tests closed payload membership, identity, and tamper detection.
@details Exercises both a generated fixture and the complete in-tree AEGIS
         payload without importing AEGIS at runtime.
"""

import json
import os
import stat
import zipfile
from pathlib import Path

import pytest

from waegis.copier import (
    InventoryError,
    enumerate_payload,
    parse_inventory,
    serialize_inventory,
    verify_inventory,
)
from waegis.locate import PayloadError, extract_zipapp_payload, resolve_payload
from waegis.ownership import Disposition


INVENTORY_FIXTURE = Path(__file__).parent / "fixtures" / "payload-inventory-v1.json"


def test_golden_payload_inventory_round_trips_byte_identically() -> None:
    """@brief Phase 1 pins deterministic inventory serialization."""
    inventory = parse_inventory(json.loads(INVENTORY_FIXTURE.read_text(encoding="utf-8")))
    assert serialize_inventory(inventory) == INVENTORY_FIXTURE.read_bytes()


def test_real_aegis_payload_is_closed_and_fully_classified() -> None:
    """@brief R4/R9 classify every current AEGIS template member exactly once."""
    _, version, inventory = resolve_payload()
    assert version == "3.0.0"
    assert len(inventory.records) == 155
    assert len(inventory.by_path) == len(inventory.records)
    assert all(record.disposition in Disposition for record in inventory.records)
    assert inventory.by_path[".agentic/workflow.toml"].disposition is Disposition.GENERATED
    assert inventory.by_path[".agentic/components.toml"].disposition is Disposition.SEEDED
    assert inventory.by_path[".agentic/cli/pyproject.toml"].disposition is Disposition.MANAGED


def test_generated_inventory_round_trips_and_detects_one_byte_change(tmp_path: Path) -> None:
    """@brief R9 pins identity and rejects payload tampering."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "alpha.txt").write_bytes(b"alpha\n")
    (payload / "nested").mkdir()
    (payload / "nested" / "beta.txt").write_bytes(b"beta\n")
    inventory = enumerate_payload(payload)
    decoded = json.loads(serialize_inventory(inventory))
    assert parse_inventory(decoded) == inventory
    (payload / "nested" / "beta.txt").write_bytes(b"Beta\n")
    with pytest.raises(InventoryError, match="mismatch"):
        verify_inventory(payload, inventory)


def test_inventory_excludes_local_build_and_coverage_artifacts(tmp_path: Path) -> None:
    """@brief R9 local test/build products never leak into the deployable payload."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "kept.txt").write_text("payload\n", encoding="utf-8")
    for directory in (".hypothesis", ".uv_cache", "htmlcov"):
        artifact = payload / directory
        artifact.mkdir()
        (artifact / "leak.txt").write_text("local\n", encoding="utf-8")
    (payload / ".coverage").write_text("coverage\n", encoding="utf-8")
    (payload / "coverage.xml").write_text("coverage\n", encoding="utf-8")
    inventory = enumerate_payload(payload)
    assert [record.path for record in inventory.records] == ["kept.txt"]


def test_inventory_detects_missing_and_unexpected_entries(tmp_path: Path) -> None:
    """@brief Closed membership rejects both subtraction and addition."""
    payload = tmp_path / "payload"
    payload.mkdir()
    source = payload / "one.txt"
    source.write_text("one", encoding="utf-8")
    inventory = enumerate_payload(payload)
    source.unlink()
    with pytest.raises(InventoryError, match="missing"):
        verify_inventory(payload, inventory)
    source.write_text("one", encoding="utf-8")
    (payload / "two.txt").write_text("two", encoding="utf-8")
    with pytest.raises(InventoryError, match="unexpected"):
        verify_inventory(payload, inventory)


def test_inventory_rejects_case_collisions(tmp_path: Path) -> None:
    """@brief Portable payload membership cannot vary by filesystem case rules."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "File.txt").write_text("one", encoding="utf-8")
    (payload / "file.TXT").write_text("two", encoding="utf-8")
    if len(list(payload.iterdir())) < 2:
        pytest.skip("host filesystem is case-insensitive")
    with pytest.raises(InventoryError, match="case-colliding"):
        enumerate_payload(payload)


def test_inventory_rejects_links_when_supported(tmp_path: Path) -> None:
    """@brief Archive/payload links never become installable members."""
    payload = tmp_path / "payload"
    payload.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("outside", encoding="utf-8")
    link = payload / "link.txt"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("host does not permit test symlinks")
    with pytest.raises(InventoryError, match="link/reparse"):
        enumerate_payload(payload)


def test_inventory_parser_rejects_digest_tampering(tmp_path: Path) -> None:
    """@brief The inventory identity binds every record and disposition."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "a.txt").write_text("a", encoding="utf-8")
    value = json.loads(serialize_inventory(enumerate_payload(payload)))
    value["files"][0]["size"] = 9
    with pytest.raises(InventoryError, match="identity digest"):
        parse_inventory(value)


def _zip_payload(archive: Path, members: list[tuple[str, bytes]], *, link: str | None = None) -> None:
    """@brief Build a small zipapp-like payload fixture."""
    with zipfile.ZipFile(archive, "w") as bundle:
        for name, data in members:
            bundle.writestr(name, data)
        if link is not None:
            info = zipfile.ZipInfo(link)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(info, b"outside")


def test_safe_zipapp_extraction_uses_closed_inventory(tmp_path: Path) -> None:
    """@brief Phase 1 extracts exact bytes into a content-addressed cache."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "a.txt").write_bytes(b"a\n")
    inventory = enumerate_payload(payload)
    archive = tmp_path / "waegis.pyz"
    _zip_payload(archive, [("__main__.py", b"pass\n"), ("payload/a.txt", b"a\n")])
    extracted = extract_zipapp_payload(archive, inventory, tmp_path / "cache")
    assert extracted == tmp_path / "cache" / inventory.digest / "payload"
    assert (extracted / "a.txt").read_bytes() == b"a\n"
    assert extract_zipapp_payload(archive, inventory, tmp_path / "cache") == extracted


@pytest.mark.parametrize(
    ("members", "message"),
    [
        ([("payload/a.txt", b"A\n")], "digest mismatch"),
        ([("payload/a.txt", b"a\n"), ("payload/extra.txt", b"x")], "undeclared"),
        ([], "missing"),
        ([("payload/../escape.txt", b"x")], "unsafe"),
        ([("payload/a.txt", b"a\n"), ("payload/A.TXT", b"a\n")], "case-colliding"),
    ],
)
def test_zipapp_extraction_rejects_invalid_members(
    tmp_path: Path,
    members: list[tuple[str, bytes]],
    message: str,
) -> None:
    """@brief Missing, extra, changed, traversal, and collision cases fail closed."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "a.txt").write_bytes(b"a\n")
    inventory = enumerate_payload(payload)
    archive = tmp_path / "bad.pyz"
    _zip_payload(archive, members)
    with pytest.raises(PayloadError, match=message):
        extract_zipapp_payload(archive, inventory, tmp_path / "cache")


def test_zipapp_extraction_rejects_link_members(tmp_path: Path) -> None:
    """@brief Linked archive members never reach the target cache."""
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "a.txt").write_bytes(b"a\n")
    inventory = enumerate_payload(payload)
    archive = tmp_path / "link.pyz"
    _zip_payload(archive, [("payload/a.txt", b"a\n")], link="payload/link.txt")
    with pytest.raises(PayloadError, match="member type"):
        extract_zipapp_payload(archive, inventory, tmp_path / "cache")


# END OF FILE
