#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_payload_manifest.py
@brief Install manifest schema-v1 tests: round-trip, golden JSON, hash
       stability, path normalization, validation failures, drift, and the
       absent/invalid/valid load states (T3.1).
@details Strictly offline, uses only synthetic ``tmp_path`` fixture trees —
         never touches ``05_Software/aegis/template/`` directly.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from waegis.payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    DriftResult,
    FileEntry,
    ManifestError,
    ManifestState,
    build_manifest,
    compute_drift,
    hash_file,
    load_manifest,
    manifest_from_dict,
    manifest_path,
    resolve_managed_path,
    read_manifest,
    write_manifest,
)
from waegis.version import WIZARD_VERSION

# LOCAL HELPERS


def _make_tree(root: Path) -> None:
    """
    @brief      Build a small synthetic payload-shaped file tree under ``root``.
    @param[in]  root Directory to populate.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic" / "cli").mkdir()
    (root / ".agentic" / "cli" / "cli.py").write_text("print('hello')\n", encoding="utf-8", newline="\n")
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8", newline="\n")


# TESTS

# --- round-trip --------------------------------------------------------------


def test_build_write_read_round_trip(tmp_path: Path) -> None:
    """
    @brief      Building, writing, and reading back a manifest for a small
                synthetic tree preserves fields and file hashes exactly.
    @return     None
    @exception  AssertionError If any field or hash mismatches after round-trip.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _make_tree(tmp_path)
    manifest = build_manifest(
        tmp_path,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=[".agentic/cli/cli.py", "AGENTS.md"],
        generated=[".agentic/workflow.toml"],
        skipped=["CLAUDE.md"],
        installed_at="2026-07-12T12:00:00Z",
        installed_by="waegis 0.1.0",
    )
    write_manifest(tmp_path, manifest)

    loaded = read_manifest(tmp_path)

    assert loaded == manifest
    assert loaded.files[".agentic/cli/cli.py"].sha256 == hash_file(tmp_path / ".agentic" / "cli" / "cli.py").sha256
    assert loaded.files["AGENTS.md"].size == (tmp_path / "AGENTS.md").stat().st_size


def test_build_manifest_installed_by_defaults_to_current_wizard_version(tmp_path: Path) -> None:
    """
    @brief      ``installed_by`` defaults to ``"waegis {WIZARD_VERSION}"`` read
                from ``waegis.version`` at call time, not a hardcoded string.
    @return     None
    @exception  AssertionError If the default does not reflect the live version.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _make_tree(tmp_path)
    manifest = build_manifest(
        tmp_path,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=["AGENTS.md"],
    )
    assert manifest.installed_by == f"waegis {WIZARD_VERSION}"


def test_manifest_never_lists_itself(tmp_path: Path) -> None:
    """
    @brief      The manifest file itself never appears as a key in its own
                ``files`` map, even if the caller's file list includes it.
    @return     None
    @exception  AssertionError If the manifest path key is present in ``files``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _make_tree(tmp_path)
    manifest_dir = tmp_path / ".agentic"
    (manifest_dir / "install-manifest.json").write_text("{}\n", encoding="utf-8")

    manifest = build_manifest(
        tmp_path,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=["AGENTS.md", MANIFEST_RELATIVE_PATH],
    )

    assert MANIFEST_RELATIVE_PATH not in manifest.files
    assert manifest_path(tmp_path) == tmp_path / ".agentic" / "install-manifest.json"


# --- golden-file contract -----------------------------------------------------


def _golden_json() -> str:
    """
    @brief      A fixed schema-v1 manifest JSON document, per plan §6.
    @return     JSON text, 2-space indent, stable key order.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return (
        "{\n"
        '  "manifest_version": 1,\n'
        '  "product": "aegis",\n'
        '  "payload_version": "0.4.0",\n'
        '  "installed_at": "2026-07-11T12:00:00Z",\n'
        '  "installed_by": "waegis 0.1.0",\n'
        '  "mode": "new",\n'
        '  "files": {\n'
        '    ".agentic/cli/src/aegis/cli.py": {\n'
        '      "sha256": "aaaa",\n'
        '      "size": 12345\n'
        "    },\n"
        '    "AGENTS.md": {\n'
        '      "sha256": "bbbb",\n'
        '      "size": 2345\n'
        "    }\n"
        "  },\n"
        '  "generated": [\n'
        '    ".agentic/workflow.toml"\n'
        "  ],\n"
        '  "skipped": [\n'
        '    "CLAUDE.md"\n'
        "  ],\n"
        '  "payload_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",\n'
        '  "configuration": {}\n'
        "}"
    )


def test_golden_manifest_parses_to_expected_fields() -> None:
    """
    @brief      The fixed golden manifest JSON parses into a ``Manifest`` with
                exactly the expected field values (frozen contract, plan §15).
    @return     None
    @exception  AssertionError If any field differs from the golden document.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    data = json.loads(_golden_json())
    manifest = manifest_from_dict(data)

    assert manifest.manifest_version == 1
    assert manifest.product == "aegis"
    assert manifest.payload_version == "0.4.0"
    assert manifest.installed_at == "2026-07-11T12:00:00Z"
    assert manifest.installed_by == "waegis 0.1.0"
    assert manifest.mode == "new"
    assert manifest.files == {
        ".agentic/cli/src/aegis/cli.py": FileEntry(sha256="aaaa", size=12345),
        "AGENTS.md": FileEntry(sha256="bbbb", size=2345),
    }
    assert manifest.generated == (".agentic/workflow.toml",)
    assert manifest.skipped == ("CLAUDE.md",)


def test_golden_manifest_serializes_back_to_the_same_json() -> None:
    """
    @brief      Re-serializing the parsed golden manifest reproduces the exact
                same JSON text — catches accidental field reordering/renaming.
    @return     None
    @exception  AssertionError If the round-tripped JSON differs at all.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    golden = _golden_json()
    manifest = manifest_from_dict(json.loads(golden))
    assert json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False) == golden


# --- hash stability -----------------------------------------------------------


def test_hash_stable_across_copy_mechanisms(tmp_path: Path) -> None:
    """
    @brief      The same logical content copied via ``shutil.copy2`` vs. a
                manual byte read/write yields the identical hash.
    @return     None
    @exception  AssertionError If the two copies hash differently.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    original = tmp_path / "original.txt"
    original.write_bytes(b"line one\nline two\nline three\n")

    via_copy2 = tmp_path / "via_copy2.txt"
    shutil.copy2(original, via_copy2)

    via_manual = tmp_path / "via_manual.txt"
    with open(original, "rb") as src, open(via_manual, "wb") as dst:
        shutil.copyfileobj(src, dst)

    original_hash = hash_file(original)
    assert hash_file(via_copy2) == original_hash
    assert hash_file(via_manual) == original_hash


def test_hash_differs_for_actually_different_bytes(tmp_path: Path) -> None:
    """
    @brief      A CRLF version and an LF version of the same logical content
                are genuinely different byte streams and must hash differently
                — proving this module performs no newline normalization.
    @return     None
    @exception  AssertionError If the two variants hash identically.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    lf_path = tmp_path / "lf.txt"
    crlf_path = tmp_path / "crlf.txt"
    lf_path.write_bytes(b"line one\nline two\nline three\n")
    crlf_path.write_bytes(b"line one\r\nline two\r\nline three\r\n")

    assert hash_file(lf_path) != hash_file(crlf_path)


# --- POSIX path normalization --------------------------------------------------


def test_build_manifest_normalizes_windows_style_input_paths(tmp_path: Path) -> None:
    """
    @brief      A manifest built from Windows-style backslash input paths
                stores forward-slash POSIX keys, on any host OS.
    @return     None
    @exception  AssertionError If a backslash survives into a manifest key.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b.txt").write_text("x", encoding="utf-8")

    manifest = build_manifest(
        tmp_path,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=["a\\b.txt"],
        generated=["a\\generated.toml"],
    )

    assert "a/b.txt" in manifest.files
    assert all("\\" not in key for key in manifest.files)
    assert manifest.generated == ("a/generated.toml",)


def test_read_manifest_normalizes_keys_from_disk(tmp_path: Path) -> None:
    """
    @brief      A manifest document whose JSON keys use backslashes still reads
                back as forward-slash keys.
    @return     None
    @exception  AssertionError If a backslash key survives parsing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    data = {
        "manifest_version": 1,
        "product": "aegis",
        "payload_version": "0.4.0",
        "installed_at": "2026-07-12T00:00:00Z",
        "installed_by": "waegis 0.1.0",
        "mode": "new",
        "files": {"a\\b.txt": {"sha256": "aaaa", "size": 1}},
        "generated": [],
        "skipped": [],
        "payload_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        "configuration": {},
    }
    manifest = manifest_from_dict(data)
    assert "a/b.txt" in manifest.files
    assert "a\\b.txt" not in manifest.files


# --- validation failures --------------------------------------------------


def test_missing_manifest_version_raises_clear_error() -> None:
    """
    @brief      A document missing ``manifest_version`` fails with a message
                naming it.
    @return     None
    @exception  AssertionError If ``ManifestError`` is not raised, or the
                message omits the missing key.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    data = json.loads(_golden_json())
    del data["manifest_version"]
    with pytest.raises(ManifestError, match="manifest_version"):
        manifest_from_dict(data)


def test_unknown_manifest_version_raises_clear_error() -> None:
    """
    @brief      A document with an unsupported ``manifest_version`` fails with
                a message naming the unexpected value.
    @return     None
    @exception  AssertionError If ``ManifestError`` is not raised, or the
                message omits the offending version.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    data = json.loads(_golden_json())
    data["manifest_version"] = 99
    with pytest.raises(ManifestError, match="99"):
        manifest_from_dict(data)


@pytest.mark.parametrize("field", ["payload_digest", "configuration"])
def test_previous_manifest_layout_is_not_accepted(field: str) -> None:
    """@brief Current schema fields are mandatory without a compatibility reader."""
    data = json.loads(_golden_json())
    del data[field]
    with pytest.raises(ManifestError, match=field):
        manifest_from_dict(data)


def test_malformed_file_entry_raises_error_naming_the_key() -> None:
    """
    @brief      A ``files`` entry missing ``sha256`` or ``size`` fails with a
                message naming the offending file key.
    @return     None
    @exception  AssertionError If ``ManifestError`` is not raised, or the
                message omits the offending key.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    data = json.loads(_golden_json())
    data["files"]["AGENTS.md"] = {"sha256": "bbbb"}  # missing "size"
    with pytest.raises(ManifestError, match="AGENTS.md"):
        manifest_from_dict(data)

    data2 = json.loads(_golden_json())
    data2["files"]["AGENTS.md"] = {"size": 2345}  # missing "sha256"
    with pytest.raises(ManifestError, match="AGENTS.md"):
        manifest_from_dict(data2)


@pytest.mark.parametrize(
    "unsafe",
    ["../escape.txt", "/absolute.txt", "C:/drive.txt", "//server/share.txt", "a//b.txt", "a/./b.txt"],
)
def test_manifest_rejects_unsafe_or_noncanonical_managed_paths(unsafe: str) -> None:
    """@brief Current manifests reject traversal, roots, drives, and ambiguous forms."""
    data = json.loads(_golden_json())
    entry = data["files"].pop("AGENTS.md")
    data["files"][unsafe] = entry
    with pytest.raises(ManifestError, match="path|absolute|drive|canonical|separator"):
        manifest_from_dict(data)


@pytest.mark.parametrize(
    "paths",
    [
        ("folder\\file.txt", "folder/file.txt"),
        ("Folder/file.txt", "folder/file.txt"),
    ],
)
def test_manifest_rejects_normalization_and_case_collisions(paths: tuple[str, str]) -> None:
    """@brief Two textual paths may not normalize or case-fold to one target."""
    data = json.loads(_golden_json())
    entry = data["files"].pop("AGENTS.md")
    data["files"][paths[0]] = entry
    data["files"][paths[1]] = entry
    with pytest.raises(ManifestError, match="collision|duplicate"):
        manifest_from_dict(data)


def test_managed_path_rejects_symlink_escape(tmp_path: Path) -> None:
    """@brief An existing symlink component cannot redirect a managed path outside the repo."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repo / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")
    with pytest.raises(ManifestError, match="symlink|escapes"):
        resolve_managed_path(repo, "linked/file.txt")


# --- drift ---------------------------------------------------------------------


def test_drift_unmodified_edited_deleted_and_extra(tmp_path: Path) -> None:
    """
    @brief      Drift computation: unmodified file is in neither list; edited
                file is in ``modified``; deleted file is in ``missing``; a new
                file on disk untracked by the manifest is ignored entirely (the
                "extra" case is out of this function's scope — computing it
                needs a *new* payload's file list, T3.2/T6.2's job).
    @return     None
    @exception  AssertionError If any file lands in the wrong bucket.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    (tmp_path / "unchanged.txt").write_text("same\n", encoding="utf-8", newline="\n")
    (tmp_path / "edited.txt").write_text("original\n", encoding="utf-8", newline="\n")
    (tmp_path / "deleted.txt").write_text("gone soon\n", encoding="utf-8", newline="\n")

    manifest = build_manifest(
        tmp_path,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=["unchanged.txt", "edited.txt", "deleted.txt"],
    )

    (tmp_path / "edited.txt").write_text("changed!\n", encoding="utf-8", newline="\n")
    (tmp_path / "deleted.txt").unlink()
    (tmp_path / "untracked_new_file.txt").write_text("new\n", encoding="utf-8")

    drift = compute_drift(tmp_path, manifest)

    assert drift == DriftResult(modified=("edited.txt",), missing=("deleted.txt",))
    assert "unchanged.txt" not in drift.modified
    assert "unchanged.txt" not in drift.missing
    # Explicit boundary: a file on disk that the manifest never recorded is
    # neither modified nor missing — "extra" needs a new payload's file list.
    assert "untracked_new_file.txt" not in drift.modified
    assert "untracked_new_file.txt" not in drift.missing


# --- absent / invalid / valid ---------------------------------------------------


def test_load_manifest_reports_absent_when_no_manifest_file(tmp_path: Path) -> None:
    """
    @brief      ``load_manifest`` reports ``ABSENT`` for a repo with no manifest.
    @return     None
    @exception  AssertionError If the state or payload fields are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = load_manifest(tmp_path)
    assert result.state == ManifestState.ABSENT
    assert result.manifest is None
    assert result.error is None


def test_load_manifest_reports_invalid_for_malformed_json(tmp_path: Path) -> None:
    """
    @brief      ``load_manifest`` reports ``INVALID`` (with an error message)
                for a manifest file present but not parseable/valid — distinct
                from ``ABSENT``.
    @return     None
    @exception  AssertionError If the state, manifest, or error fields are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path = manifest_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not valid json", encoding="utf-8")

    result = load_manifest(tmp_path)
    assert result.state == ManifestState.INVALID
    assert result.manifest is None
    assert result.error is not None


def test_load_manifest_reports_valid_for_a_well_formed_manifest(tmp_path: Path) -> None:
    """
    @brief      ``load_manifest`` reports ``VALID`` with the parsed manifest for
                a well-formed document — distinct from both other states.
    @return     None
    @exception  AssertionError If the state or manifest fields are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _make_tree(tmp_path)
    manifest = build_manifest(
        tmp_path,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=["AGENTS.md"],
    )
    write_manifest(tmp_path, manifest)

    result = load_manifest(tmp_path)
    assert result.state == ManifestState.VALID
    assert result.manifest == manifest
    assert result.error is None


# END OF FILE
