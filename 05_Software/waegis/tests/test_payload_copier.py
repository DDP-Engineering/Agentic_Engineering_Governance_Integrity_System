#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_payload_copier.py
@brief Manifest-aware copier tests (T3.2): new-project copy, byte-verbatim
       proof, dry-run, overwrite refusal with the no-partial-write guarantee,
       adoption conflict classification and the per-file decision hook,
       exclusion rules, force semantics, and a real-payload end-to-end run.
@details Strictly offline. Most cases use synthetic ``tmp_path`` payload
         trees; one end-to-end test copies the real
         ``05_Software/aegis/template/`` (read-only as a source) to catch
         real-world surprises the fixtures might miss.
@details ``ensure_executable`` tests (added 0.2.0, architecture-review
         follow-up) cover the POSIX execute-bit backstop applied to every
         copied ``.sh`` file; the mocked-``chmod`` tests are meaningful on
         any host OS, plus one real-filesystem proof skipped on Windows.
@author Eng. Dan Dumitru Pasare
@date 2026-07-18
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

import waegis.payload.copier as copier_module
from waegis.payload.copier import (
    ConflictDecision,
    CopierError,
    OverwriteRefusedError,
    PayloadConflict,
    PayloadMissingError,
    TargetDirectoryMissingError,
    copy_payload,
    ensure_executable,
    should_exclude,
)
from waegis.payload.locate import read_payload_version
from waegis.payload.manifest import MANIFEST_RELATIVE_PATH, hash_file, manifest_path, read_manifest
from waegis.version import WIZARD_VERSION

# CONSTANTS

# @brief The real repo-checkout template payload (used read-only as a source).
REAL_TEMPLATE = Path(__file__).resolve().parents[2] / "aegis" / "template"

# @brief The synthetic payload's file set, as repo-relative POSIX paths.
PAYLOAD_FILES = (
    ".agentic/workflow.toml",
    "AGENTS.md",
    "assets/blob.bin",
    "src/app.py",
)

# LOCAL HELPERS


def _make_payload(root: Path) -> Path:
    """
    @brief      Build the standard synthetic payload tree: a text file, a
                CRLF-bytes file, a binary file, a nested file, and an empty
                directory.
    @param[in]  root Directory to populate.
    @return     ``root``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    (root / ".agentic").mkdir(parents=True)
    (root / ".agentic" / "workflow.toml").write_bytes(b"[workflow]\nname = 'toy'\n")
    (root / "AGENTS.md").write_bytes(b"# AGENTS\r\nCRLF body kept verbatim\r\n")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_bytes(b"print('payload')\n")
    (root / "assets").mkdir()
    (root / "assets" / "blob.bin").write_bytes(bytes(range(256)))
    (root / "empty_dir").mkdir()
    return root


class _RecordingHook:
    """
    @brief Decision hook that records every conflict it is asked about and
           answers with a fixed decision.
    @author Eng. Dan Dumitru Pasare
    @version 0.1.0
    """

    def __init__(self, decision: ConflictDecision) -> None:
        """
        @brief      Store the fixed decision to answer with.
        @param[in]  decision Decision returned for every conflict.
        @return     None
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self.decision = decision
        self.seen: list[PayloadConflict] = []

    def __call__(self, conflict: PayloadConflict) -> ConflictDecision:
        """
        @brief      Record the conflict and return the fixed decision.
        @param[in]  conflict The conflict presented by the copier.
        @return     The fixed decision.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        self.seen.append(conflict)
        return self.decision


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    """
    @brief      Snapshot every file under a root as {posix relpath: bytes}.
    @param[in]  root Directory to snapshot.
    @return     Mapping of relative POSIX path to file content.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# TESTS

# --- new-project mode ---------------------------------------------------------


def test_new_copy_into_empty_dir_copies_exact_file_set(tmp_path: Path) -> None:
    """
    @brief      A new-project copy into a creatable target copies exactly the
                payload file set (minus exclusions), creates empty payload
                directories, and writes a manifest recording every file.
    @return     None
    @exception  AssertionError If the copied set or manifest is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"

    result = copy_payload(payload, target, mode="new")

    assert result.copied == PAYLOAD_FILES
    assert result.identical == ()
    assert result.conflicts == ()
    assert result.skipped == ()
    assert not result.dry_run
    assert (target / "empty_dir").is_dir()

    assert result.manifest_file == manifest_path(target)
    manifest = read_manifest(target)
    assert manifest == result.manifest
    assert manifest.mode == "new"
    assert manifest.product == "aegis"
    assert manifest.payload_version == "unknown"  # synthetic payload ships no version declaration
    assert manifest.installed_by == f"waegis {WIZARD_VERSION}"
    assert set(manifest.files) == set(PAYLOAD_FILES)
    assert manifest.generated == ()
    assert manifest.skipped == ()


def test_copied_files_are_byte_verbatim_by_direct_hash_equality(tmp_path: Path) -> None:
    """
    @brief      Byte-verbatim proof: for every copied file — including the
                CRLF-bytes file and the binary file — the destination's
                sha256 computed directly with hash_file equals the source's,
                and the manifest records that same source hash.
    @return     None
    @exception  AssertionError If any copy translated or altered bytes.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"

    result = copy_payload(payload, target, mode="new")

    for relative in PAYLOAD_FILES:
        source_entry = hash_file(payload / relative)
        target_entry = hash_file(target / relative)
        assert target_entry == source_entry, f"bytes differ after copy: {relative}"
        assert result.manifest is not None
        assert result.manifest.files[relative] == source_entry
    # The CRLF file specifically must still contain CRLF bytes.
    assert b"\r\n" in (target / "AGENTS.md").read_bytes()


def test_dry_run_reports_same_files_and_writes_nothing(tmp_path: Path) -> None:
    """
    @brief      Dry-run returns the same copied list as a real run but writes
                nothing: no target directory, no files, no manifest.
    @return     None
    @exception  AssertionError If dry-run wrote anything or diverged.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"

    preview = copy_payload(payload, target, mode="new", dry_run=True)

    assert preview.dry_run
    assert preview.copied == PAYLOAD_FILES
    assert preview.manifest is None
    assert preview.manifest_file is None
    assert not target.exists()

    real = copy_payload(payload, target, mode="new")
    assert real.copied == preview.copied


def test_missing_payload_and_missing_existing_target_raise_typed_errors(tmp_path: Path) -> None:
    """
    @brief      A missing payload root and a missing required-existing target
                raise their typed errors with the legacy message text.
    @return     None
    @exception  AssertionError If the errors or messages are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    with pytest.raises(PayloadMissingError, match="Template directory not found"):
        copy_payload(tmp_path / "no-payload", tmp_path / "target", mode="new")

    payload = _make_payload(tmp_path / "payload")
    with pytest.raises(TargetDirectoryMissingError, match="Existing repository directory not found"):
        copy_payload(payload, tmp_path / "no-target", mode="adopt", require_existing_target=True)


# --- overwrite refusal (strict mode) ------------------------------------------


def test_strict_mode_refuses_differing_file_and_leaves_target_untouched(tmp_path: Path) -> None:
    """
    @brief      Without force or a hook, a pre-existing differing file raises
                OverwriteRefusedError naming the path — and the refusal
                happens before any write, so the target is completely
                untouched (the documented no-partial-copy decision).
    @return     None
    @exception  AssertionError If anything was written or the error is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    target.mkdir()
    (target / "AGENTS.md").write_bytes(b"local content\n")
    before = _tree_snapshot(target)

    with pytest.raises(OverwriteRefusedError, match="Refusing to overwrite existing file:") as excinfo:
        copy_payload(payload, target, mode="new")

    assert excinfo.value.conflicting_paths == (target.resolve() / "AGENTS.md",)
    assert "AGENTS.md" in str(excinfo.value)
    assert _tree_snapshot(target) == before
    assert not manifest_path(target).exists()


def test_strict_mode_refuses_even_identical_files(tmp_path: Path) -> None:
    """
    @brief      Legacy parity: strict mode refuses on any pre-existing
                destination file, even one byte-identical to the payload.
    @return     None
    @exception  AssertionError If an identical file is silently accepted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    target.mkdir()
    (target / "AGENTS.md").write_bytes((payload / "AGENTS.md").read_bytes())

    with pytest.raises(OverwriteRefusedError):
        copy_payload(payload, target, mode="new")


def test_strict_dry_run_also_refuses_on_existing_files(tmp_path: Path) -> None:
    """
    @brief      Legacy parity: dry-run in strict mode still refuses on a
                pre-existing file (the legacy script's existence check
                preceded its dry-run guard).
    @return     None
    @exception  AssertionError If dry-run bypasses the refusal.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    target.mkdir()
    (target / "AGENTS.md").write_bytes(b"local content\n")

    with pytest.raises(OverwriteRefusedError):
        copy_payload(payload, target, mode="new", dry_run=True)


# --- adoption mode: classification and the decision hook ----------------------


def _make_adoption_target(payload: Path, target: Path) -> None:
    """
    @brief      Build a target with all three classification cases against the
                synthetic payload: AGENTS.md identical, src/app.py different,
                everything else missing.
    @param[in]  payload The synthetic payload root.
    @param[in]  target Target directory to populate.
    @return     None
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    target.mkdir()
    (target / "AGENTS.md").write_bytes((payload / "AGENTS.md").read_bytes())
    (target / "src").mkdir()
    (target / "src" / "app.py").write_bytes(b"print('local edit')\n")


def test_adoption_classifies_missing_identical_different(tmp_path: Path) -> None:
    """
    @brief      One payload tree with all three cases classifies correctly:
                missing files are copied, the identical file is skipped
                silently yet recorded in the manifest as if freshly copied,
                and the differing file is the only conflict — the hook is
                called exactly once, never for identical or missing files.
    @return     None
    @exception  AssertionError If classification or hook cardinality is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)
    hook = _RecordingHook(ConflictDecision.KEEP_LOCAL)

    result = copy_payload(payload, target, mode="adopt", on_conflict=hook)

    assert [conflict.relative_path for conflict in hook.seen] == ["src/app.py"]
    assert result.copied == (".agentic/workflow.toml", "assets/blob.bin")
    assert result.identical == ("AGENTS.md",)
    assert [conflict.relative_path for conflict in result.conflicts] == ["src/app.py"]
    conflict = result.conflicts[0]
    assert conflict.source_entry == hash_file(payload / "src" / "app.py")
    assert conflict.target_entry.sha256 != conflict.source_entry.sha256
    assert conflict.target_entry.size == len(b"print('local edit')\n")

    manifest = read_manifest(target)
    assert manifest.files["AGENTS.md"] == hash_file(payload / "AGENTS.md")  # identical: recorded as freshly copied


def test_keep_local_preserves_file_and_records_skip(tmp_path: Path) -> None:
    """
    @brief      keep-local leaves the local bytes in place, omits the file
                from manifest files, and records it under skipped.
    @return     None
    @exception  AssertionError If the local file was replaced or not skipped.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)

    result = copy_payload(payload, target, mode="adopt", on_conflict=_RecordingHook(ConflictDecision.KEEP_LOCAL))

    assert (target / "src" / "app.py").read_bytes() == b"print('local edit')\n"
    assert result.skipped == ("src/app.py",)
    assert result.resolutions[0].decision is ConflictDecision.KEEP_LOCAL
    assert result.resolutions[0].written_path is None
    manifest = read_manifest(target)
    assert manifest.skipped == ("src/app.py",)
    assert "src/app.py" not in manifest.files
    assert manifest.mode == "adopt"


def test_take_payload_replaces_file_and_records_it(tmp_path: Path) -> None:
    """
    @brief      take-payload overwrites the local file with payload bytes and
                records it in manifest files with the source hash.
    @return     None
    @exception  AssertionError If the payload bytes did not replace the local.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)

    result = copy_payload(payload, target, mode="adopt", on_conflict=_RecordingHook(ConflictDecision.TAKE_PAYLOAD))

    assert (target / "src" / "app.py").read_bytes() == b"print('payload')\n"
    assert "src/app.py" in result.copied
    assert result.skipped == ()
    assert result.resolutions[0].decision is ConflictDecision.TAKE_PAYLOAD
    assert result.resolutions[0].written_path == "src/app.py"
    manifest = read_manifest(target)
    assert manifest.files["src/app.py"] == hash_file(payload / "src" / "app.py")
    assert manifest.skipped == ()


def test_write_new_keeps_local_and_writes_sidecar(tmp_path: Path) -> None:
    """
    @brief      write-new keeps the local file, writes the payload bytes
                verbatim as "<name>.new" beside it, records the payload path
                under skipped, and never lists the sidecar in manifest files.
    @return     None
    @exception  AssertionError If either side of the decision is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)

    result = copy_payload(payload, target, mode="adopt", on_conflict=_RecordingHook(ConflictDecision.WRITE_NEW))

    assert (target / "src" / "app.py").read_bytes() == b"print('local edit')\n"
    sidecar = target / "src" / "app.py.new"
    assert hash_file(sidecar) == hash_file(payload / "src" / "app.py")
    assert result.skipped == ("src/app.py",)
    assert result.resolutions[0].decision is ConflictDecision.WRITE_NEW
    assert result.resolutions[0].written_path == "src/app.py.new"
    manifest = read_manifest(target)
    assert manifest.skipped == ("src/app.py",)
    assert "src/app.py" not in manifest.files
    assert "src/app.py.new" not in manifest.files


def test_adoption_dry_run_lists_conflicts_without_calling_hook(tmp_path: Path) -> None:
    """
    @brief      Dry-run classifies and reports conflicts but never calls the
                hook and writes nothing.
    @return     None
    @exception  AssertionError If the hook was consulted or anything written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)
    before = _tree_snapshot(target)
    hook = _RecordingHook(ConflictDecision.TAKE_PAYLOAD)

    result = copy_payload(payload, target, mode="adopt", on_conflict=hook, dry_run=True)

    assert hook.seen == []
    assert [conflict.relative_path for conflict in result.conflicts] == ["src/app.py"]
    assert result.resolutions == ()
    assert result.copied == (".agentic/workflow.toml", "assets/blob.bin")
    assert _tree_snapshot(target) == before
    assert not manifest_path(target).exists()


def test_invalid_hook_return_raises_and_leaves_target_untouched(tmp_path: Path) -> None:
    """
    @brief      A hook returning a non-ConflictDecision raises CopierError
                before any write; a hook raising propagates the same way. In
                both cases the target is untouched.
    @return     None
    @exception  AssertionError If a write happened despite the failing hook.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)
    before = _tree_snapshot(target)

    with pytest.raises(CopierError, match="conflict decision hook returned"):
        copy_payload(payload, target, mode="adopt", on_conflict=lambda conflict: "keep-local")  # type: ignore[arg-type,return-value]
    assert _tree_snapshot(target) == before

    def _exploding_hook(conflict: PayloadConflict) -> ConflictDecision:
        raise RuntimeError("operator aborted")

    with pytest.raises(RuntimeError, match="operator aborted"):
        copy_payload(payload, target, mode="adopt", on_conflict=_exploding_hook)
    assert _tree_snapshot(target) == before
    assert not manifest_path(target).exists()


def test_write_new_refuses_existing_differing_sidecar(tmp_path: Path) -> None:
    """
    @brief      write-new refuses (pre-write) when "<name>.new" already exists
                with different content, leaving the target untouched.
    @return     None
    @exception  AssertionError If the sidecar was clobbered.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)
    (target / "src" / "app.py.new").write_bytes(b"someone else's sidecar\n")
    before = _tree_snapshot(target)

    with pytest.raises(CopierError, match="refusing to overwrite existing sidecar"):
        copy_payload(payload, target, mode="adopt", on_conflict=_RecordingHook(ConflictDecision.WRITE_NEW))
    assert _tree_snapshot(target) == before


# --- force (legacy override) ---------------------------------------------------


def test_force_overwrites_everything_via_internal_take_payload_hook(tmp_path: Path) -> None:
    """
    @brief      force=True resolves every conflict as take-payload (recorded
                in resolutions) and rewrites pre-existing identical files,
                preserving the legacy copied-count semantics.
    @return     None
    @exception  AssertionError If force diverges from legacy overwrite
                behavior.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    target = tmp_path / "target"
    _make_adoption_target(payload, target)

    result = copy_payload(payload, target, mode="new", force=True)

    assert (target / "src" / "app.py").read_bytes() == b"print('payload')\n"
    assert result.copied == PAYLOAD_FILES  # identical AGENTS.md rewritten: legacy count parity
    assert result.identical == ()
    assert [resolution.decision for resolution in result.resolutions] == [ConflictDecision.TAKE_PAYLOAD]
    assert result.resolutions[0].conflict.relative_path == "src/app.py"
    manifest = read_manifest(target)
    assert set(manifest.files) == set(PAYLOAD_FILES)
    assert manifest.skipped == ()


def test_force_and_hook_are_mutually_exclusive(tmp_path: Path) -> None:
    """
    @brief      force=True together with a caller hook is ambiguous and raises
                ValueError.
    @return     None
    @exception  AssertionError If the ambiguous combination is accepted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    with pytest.raises(ValueError, match="mutually exclusive"):
        copy_payload(
            payload,
            tmp_path / "target",
            mode="new",
            force=True,
            on_conflict=_RecordingHook(ConflictDecision.KEEP_LOCAL),
        )


# --- exclusion rules ------------------------------------------------------------


def test_exclusion_rules_never_copy_generated_or_dependency_state(tmp_path: Path) -> None:
    """
    @brief      Every exclusion rule is honored against a payload containing
                all of them: __pycache__, .pytest_cache, .ruff_cache,
                node_modules, .vitest, *.pyc, *.egg-info, .uv-cache*.
    @return     None
    @exception  AssertionError If any excluded artifact reaches the target or
                the manifest.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    for part in ("__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".vitest"):
        (payload / part).mkdir()
        (payload / part / "artifact.txt").write_bytes(b"generated\n")
    (payload / "src" / "app.pyc").write_bytes(b"bytecode")
    (payload / "pkg.egg-info").mkdir()
    (payload / "pkg.egg-info" / "PKG-INFO").write_bytes(b"meta\n")
    (payload / ".uv-cache-abc").mkdir()
    (payload / ".uv-cache-abc" / "entry").write_bytes(b"cache\n")
    target = tmp_path / "target"

    result = copy_payload(payload, target, mode="new")

    assert result.copied == PAYLOAD_FILES
    for excluded in ("__pycache__", ".pytest_cache", ".ruff_cache", "node_modules", ".vitest", "pkg.egg-info", ".uv-cache-abc"):
        assert not (target / excluded).exists()
    assert not (target / "src" / "app.pyc").exists()
    manifest = read_manifest(target)
    assert set(manifest.files) == set(PAYLOAD_FILES)


def test_should_exclude_predicate_matches_ported_rules(tmp_path: Path) -> None:
    """
    @brief      The shared should_exclude predicate matches the rules ported
                from create_project_from_template.py.
    @return     None
    @exception  AssertionError If any rule diverges from the legacy set.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    excluded = [
        Path("pkg/__pycache__/module.pyc"),
        Path(".pytest_cache/README.md"),
        Path(".ruff_cache/x"),
        Path(".pi/node_modules/dep/index.js"),
        Path(".pi/.vitest/state.json"),
        Path("src/app.pyc"),
        Path("pkg.egg-info"),
        Path(".uv-cache-abc"),
    ]
    included = [Path("src/app.py"), Path("AGENTS.md"), Path(".agentic/workflow.toml")]
    for path in excluded:
        assert should_exclude(path), f"should be excluded: {path}"
    for path in included:
        assert not should_exclude(path), f"should be included: {path}"


def test_payload_shipped_manifest_is_never_copied(tmp_path: Path) -> None:
    """
    @brief      A .agentic/install-manifest.json inside the payload source is
                defensively skipped: the target's manifest is freshly emitted,
                not the payload's copy.
    @return     None
    @exception  AssertionError If the payload's stale manifest leaks through.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    payload = _make_payload(tmp_path / "payload")
    (payload / MANIFEST_RELATIVE_PATH).write_bytes(b'{"stale": true}')
    target = tmp_path / "target"

    result = copy_payload(payload, target, mode="new")

    assert MANIFEST_RELATIVE_PATH not in result.copied
    manifest = read_manifest(target)  # parses: the stale payload copy would fail validation
    assert MANIFEST_RELATIVE_PATH not in manifest.files


# --- execute-bit backstop (ensure_executable, architecture-review follow-up) ---


def test_ensure_executable_grants_exec_bits_on_posix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      On a POSIX-reported OS, a ``.sh`` destination gets
                owner/group/other execute bits added to its existing mode.
    @details    Asserts on the exact ``chmod`` call (mocked, not a real
                filesystem mode change) so the test is meaningful on any host
                OS, including this suite's own Windows dev machine where a
                real chmod would not reflect POSIX semantics.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  monkeypatch Pytest fixture.
    @return     None
    @exception  AssertionError If ``chmod`` is not called with the OR'd mode.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    monkeypatch.setattr(copier_module.os, "name", "posix")
    destination = tmp_path / "run.sh"
    destination.write_bytes(b"#!/bin/sh\necho hi\n")
    original_mode = destination.stat().st_mode

    with patch.object(Path, "chmod", autospec=True) as mock_chmod:
        ensure_executable(destination)

    mock_chmod.assert_called_once_with(
        destination, original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    )


def test_ensure_executable_is_a_noop_on_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      On Windows, ``ensure_executable`` never calls ``chmod`` — the
                POSIX execute bit concept does not apply there.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  monkeypatch Pytest fixture.
    @return     None
    @exception  AssertionError If ``chmod`` is called.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    monkeypatch.setattr(copier_module.os, "name", "nt")
    destination = tmp_path / "run.sh"
    destination.write_bytes(b"#!/bin/sh\necho hi\n")

    with patch.object(Path, "chmod", autospec=True) as mock_chmod:
        ensure_executable(destination)

    mock_chmod.assert_not_called()


def test_ensure_executable_ignores_non_script_suffixes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    @brief      A destination whose suffix is not in ``EXECUTABLE_SUFFIXES``
                (e.g. ``.txt``) is left untouched even on POSIX.
    @param[in]  tmp_path Pytest tmp fixture.
    @param[in]  monkeypatch Pytest fixture.
    @return     None
    @exception  AssertionError If ``chmod`` is called.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    monkeypatch.setattr(copier_module.os, "name", "posix")
    destination = tmp_path / "notes.txt"
    destination.write_text("hi", encoding="utf-8")

    with patch.object(Path, "chmod", autospec=True) as mock_chmod:
        ensure_executable(destination)

    mock_chmod.assert_not_called()


@pytest.mark.skipif(os.name == "nt", reason="POSIX execute bits are not meaningful on Windows")
def test_real_template_shell_scripts_are_executable_after_copy_on_posix(tmp_path: Path) -> None:
    """
    @brief      Copying the real template onto a POSIX host leaves
                ``run.sh``/``install.sh`` genuinely executable on disk, not
                just mocked — the end-to-end proof, run only where it is
                meaningful.
    @param[in]  tmp_path Pytest tmp fixture (TARGET).
    @return     None
    @exception  AssertionError If either script lacks the owner execute bit.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-18
    @version    0.1.0
    """
    assert REAL_TEMPLATE.is_dir()
    target = tmp_path / "target"

    copy_payload(REAL_TEMPLATE, target, mode="new")

    for relative in (".agentic/tools/run.sh", ".agentic/tools/install.sh"):
        mode = (target / relative).stat().st_mode
        assert mode & stat.S_IXUSR, f"{relative} is not owner-executable after copy"


# --- real-payload end-to-end -----------------------------------------------------


def test_real_template_end_to_end_copy_and_manifest(tmp_path: Path) -> None:
    """
    @brief      Copying the real 05_Software/aegis/template/ payload yields a
                manifest whose file count equals the independently computed
                non-excluded file count and whose every hash equals
                hash_file() of the corresponding source template file; the
                payload_version matches the template's own declaration.
    @return     None
    @exception  AssertionError If the real payload surprises the copier.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    assert REAL_TEMPLATE.is_dir()
    target = tmp_path / "target"

    result = copy_payload(REAL_TEMPLATE, target, mode="new")

    expected_files = {
        source.relative_to(REAL_TEMPLATE).as_posix()
        for source in REAL_TEMPLATE.rglob("*")
        if source.is_file()
        and not should_exclude(source.relative_to(REAL_TEMPLATE))
        and source.relative_to(REAL_TEMPLATE).as_posix() != MANIFEST_RELATIVE_PATH
    }
    manifest = read_manifest(target)
    assert set(manifest.files) == expected_files
    assert len(manifest.files) == len(expected_files)
    for key, entry in manifest.files.items():
        assert entry == hash_file(REAL_TEMPLATE / key), f"hash mismatch against source template: {key}"
    assert manifest.payload_version == read_payload_version(REAL_TEMPLATE)
    assert manifest.payload_version not in (None, "unknown")
    assert result.copied == tuple(sorted(expected_files))
    assert manifest_path(target).is_file()


# END OF FILE
