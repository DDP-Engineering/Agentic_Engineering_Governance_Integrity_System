#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_upgrade.py
@brief Offline tests for ``waegis upgrade`` — the plan §10.2 three-way,
       manifest-driven upgrade (T6.2).
@details Strictly offline: every filesystem effect is under ``tmp_path`` and
         every subprocess (the post-apply smoke re-verify) goes through the
         test-only :class:`FakeCommandRunner`, never a real process. Fixtures
         build OLD-manifest + OLD-disk + NEW-payload triples with full control
         over the three hashes ``O``/``L``/``N`` (the manifest's original hash
         is written directly, decoupled from disk, so every row of the O/L/N
         table can be reproduced independently), plus one test that drives the
         REAL ``05_Software/aegis/template/`` tree as the "new" payload against
         an aged/edited install.
@author Eng. Dan Dumitru Pasare
@date 2026-07-20
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import io
import re
from pathlib import Path

import pytest

from waegis.cli import main
from waegis.version import WIZARD_VERSION
from waegis.commands.new import NO_ACTIVE_RUN_MARKER, _amend_manifest_generated, _wrapper_invocation
from waegis.commands.upgrade import (
    EXIT_CONFLICTS,
    EXIT_ERROR,
    EXIT_OK,
    EXIT_SMOKE_FAILED,
    FileAction,
    UpgradeConflict,
    apply_upgrade,
    build_upgrade_plan,
    make_resolution_hook,
    render_upgrade_report,
    run_upgrade,
    UpgradeError,
)
from waegis.payload.copier import SIDECAR_SUFFIX, ConflictDecision, copy_payload
from waegis.payload.locate import locate_payload
from waegis.payload.manifest import (
    FileEntry,
    Manifest,
    load_manifest,
    read_manifest,
    write_manifest,
)

from _fake_command_runner import FakeCommandRunner, failing_result, ok_result

# TEST HELPERS


def _write(path: Path, content: str) -> None:
    """
    @brief      Write ``content`` to ``path`` as verbatim UTF-8 bytes.
    @param[in]  path File to write (parents created).
    @param[in]  content Text content (no newline translation).
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")


def _entry(content: str) -> FileEntry:
    """
    @brief      Build the :class:`FileEntry` a verbatim copy of ``content`` hashes to.
    @param[in]  content Text content.
    @return     A :class:`FileEntry` with the sha256/size of ``content``'s bytes.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    raw = content.encode("utf-8")
    return FileEntry(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))


def _upgrade_answers(path: Path, conflicts: dict[str, str] | None = None) -> Path:
    """@brief Write a complete non-interactive upgrade answers file."""
    data: dict[str, object] = {"git_mode": "require-clean"}
    if conflicts is not None:
        data["upgrade_conflicts"] = conflicts
    _write(path, json.dumps(data))
    return path


def _make_manifest(
    repo: Path,
    files: dict[str, str],
    *,
    generated: tuple[str, ...] = (),
    skipped: tuple[str, ...] = (),
    payload_version: str = "2.0.0",
    installed_at: str = "2026-01-01T00:00:00Z",
    mode: str = "new",
    product: str = "aegis",
) -> Manifest:
    """
    @brief      Construct and write an OLD install manifest with fully-controlled
                original hashes (``O`` decoupled from what is on disk).
    @param[in]  repo Repository root to write the manifest under.
    @param[in]  files ``{path: original-content}`` — ``O`` is the hash of the
                content, independent of the file's current on-disk bytes.
    @param[in]  generated Paths recorded under ``generated``.
    @param[in]  skipped Paths recorded under ``skipped``.
    @param[in]  payload_version Recorded installed payload version.
    @param[in]  installed_at Recorded install timestamp (deterministic).
    @param[in]  mode Recorded install mode.
    @param[in]  product Recorded product name.
    @return     The written :class:`Manifest`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    manifest = Manifest(
        manifest_version=1,
        product=product,
        payload_version=payload_version,
        installed_at=installed_at,
        installed_by="waegis test",
        mode=mode,
        files={path: _entry(content) for path, content in files.items()},
        generated=generated,
        skipped=skipped,
    )
    write_manifest(repo, manifest)
    return manifest


def _make_payload(root: Path, files: dict[str, str], *, marker: bool = False, version: str | None = None) -> Path:
    """
    @brief      Materialize a synthetic new-payload tree.
    @param[in]  root Payload root directory.
    @param[in]  files ``{path: content}`` files the new payload ships.
    @param[in]  marker When true, also write the ``.agentic/workflow.toml`` marker
                so :func:`locate_payload` accepts the directory (run_upgrade path).
    @param[in]  version When set, write a ``.agentic/cli/pyproject.toml`` so
                ``read_payload_version`` returns it.
    @return     ``root``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    root.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        _write(root / path, content)
    if marker and ".agentic/workflow.toml" not in files:
        _write(root / ".agentic/workflow.toml", "# marker\n")
    if version is not None:
        _write(root / ".agentic/cli/pyproject.toml", f'[project]\nname = "aegis"\nversion = "{version}"\n')
    return root


def _smoke_ok_runner(repo: Path) -> FakeCommandRunner:
    """
    @brief      A fake runner that makes the post-apply smoke re-verify pass.
    @details    ``run.* --help`` exits 0; ``run.* status`` exits non-zero with
                the coherent fresh-install marker (:data:`NO_ACTIVE_RUN_MARKER`),
                which :func:`waegis.commands.upgrade._smoke_reverify` treats as
                healthy.
    @param[in]  repo Repository root (determines the wrapper argv keys).
    @return     A scripted :class:`FakeCommandRunner`.
    @author     Eng. Dan Dumitru Pasare
    @version    0.2.0
    """
    return FakeCommandRunner(
        {
            ("git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"): ok_result(stdout="true\n"),
            ("git", "-C", str(repo), "status", "--porcelain"): ok_result(),
            _wrapper_invocation(repo, "--help"): ok_result(),
            _wrapper_invocation(repo, "run", "status", "--json"): failing_result(
                exit_code=2,
                stderr=NO_ACTIVE_RUN_MARKER,
            ),
        }
    )


def _smoke_fail_runner(repo: Path) -> FakeCommandRunner:
    """
    @brief      A fake runner that makes the post-apply smoke re-verify FAIL.
    @param[in]  repo Repository root (determines the wrapper argv keys).
    @return     A scripted :class:`FakeCommandRunner` whose ``--help`` fails.
    @author     Eng. Dan Dumitru Pasare
    @version    0.2.0
    """
    return FakeCommandRunner(
        {
            ("git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"): ok_result(stdout="true\n"),
            ("git", "-C", str(repo), "status", "--porcelain"): ok_result(),
            _wrapper_invocation(repo, "--help"): failing_result(exit_code=1, stderr="boom"),
            _wrapper_invocation(repo, "run", "status", "--json"): failing_result(
                exit_code=2,
                stderr=NO_ACTIVE_RUN_MARKER,
            ),
        }
    )


def _plan(repo: Path, new_payload: Path):
    """
    @brief      Build the upgrade plan for a repo + new payload.
    @param[in]  repo Repository root.
    @param[in]  new_payload New payload root.
    @return     The computed plan.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return build_upgrade_plan(repo, new_payload_root=new_payload, load_result=load_manifest(repo))


def _action_of(plan, path: str) -> FileAction:
    """
    @brief      The classified action of exactly one path in a plan.
    @param[in]  plan The computed plan.
    @param[in]  path Repo-relative POSIX path.
    @return     The :class:`FileAction`.
    @exception  AssertionError If the path is not present exactly once.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    matches = [item.action for item in plan.items if item.path == path]
    assert len(matches) == 1, f"expected exactly one plan item for {path!r}, got {matches}"
    return matches[0]


# ---------------------------------------------------------------------------
# EXHAUSTIVE O/L/N MATRIX — one independent case per table row (plan §10.2).
# Each asserts the exact resulting ACTION and the exact resulting MANIFEST.
# ---------------------------------------------------------------------------


def test_row1_unchanged(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "X"})

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.UNCHANGED

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert report.manifest_written
    assert (repo / "file.txt").read_text(encoding="utf-8") == "X"
    assert read_manifest(repo).files == {"file.txt": _entry("X")}


def test_row2_auto_apply_new(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"})

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.AUTO_APPLY_NEW

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Y"
    assert report.manifest.files["file.txt"] == _entry("Y")


def test_row3_keep_local(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Z")  # L != O
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "X"})  # N == O

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.KEEP_LOCAL

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Z"  # local kept
    # Original hash (== O == N) recorded; drift will honestly show it modified.
    assert report.manifest.files["file.txt"] == _entry("X")


def test_row4_already_converged(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Y")  # L != O
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"})  # N != O, L == N

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.ALREADY_CONVERGED

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Y"
    assert report.manifest.files["file.txt"] == _entry("Y")


def test_row5_conflict_takes_hook(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Z")  # L
    _make_manifest(repo, {"file.txt": "X"})  # O
    _make_payload(new, {"file.txt": "Y"})  # N; X, Y, Z all distinct

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.CONFLICT
    assert [c.relative_path for c in plan.conflicts()] == ["file.txt"]

    hook = make_resolution_hook({"file.txt": "take-payload"}, None)
    report = apply_upgrade(plan, hook=hook, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Y"
    assert report.manifest.files["file.txt"] == _entry("Y")


def test_row6_add_new(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _make_manifest(repo, {})  # valid, empty: O absent for file.txt
    _make_payload(new, {"file.txt": "Y"})  # no local file

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.ADD_NEW

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Y"
    assert report.manifest.files["file.txt"] == _entry("Y")


def test_row7_new_converged(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Y")  # untracked local equal to new
    _make_manifest(repo, {})
    _make_payload(new, {"file.txt": "Y"})

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.NEW_CONVERGED

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Y"
    assert report.manifest.files["file.txt"] == _entry("Y")


def test_row8_new_upstream_collision_is_conflict(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Z")  # untracked local, differs from new
    _make_manifest(repo, {})
    _make_payload(new, {"file.txt": "Y"})

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.CONFLICT

    # keep-local: the untracked local file is NOT silently overwritten.
    hook = make_resolution_hook({"file.txt": "keep-local"}, None)
    report = apply_upgrade(plan, hook=hook, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Z"
    assert "file.txt" not in report.manifest.files
    assert "file.txt" in report.manifest.skipped


def test_row9_removed_upstream_unmodified_deleted(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "X")  # L == O
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {})  # new payload no longer ships file.txt

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.DELETE_REMOVED

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert not (repo / "file.txt").exists()
    assert "file.txt" not in report.manifest.files


def test_row10_removed_upstream_modified_kept(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Z")  # L != O
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {})

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.KEEP_MODIFIED_REMOVED
    # It is NOT in the delete list.
    assert "file.txt" not in plan.by_action(FileAction.DELETE_REMOVED)

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Z"  # local edit survives
    assert "file.txt" not in report.manifest.files  # payload no longer ships it
    assert report.preserved_local_edits() == ("file.txt",)


def test_row11_removed_upstream_already_gone(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _make_manifest(repo, {"file.txt": "X"})  # tracked, but not on disk
    _make_payload(new, {})

    plan = _plan(repo, new)
    assert _action_of(plan, "file.txt") is FileAction.DELETE_REMOVED  # no-op delete

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert report.manifest_written
    assert "file.txt" not in report.manifest.files


def test_row12_degenerate_path_in_neither(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "unrelated.txt", "local")  # in neither manifest nor new payload
    _make_manifest(repo, {})
    _make_payload(new, {})

    plan = _plan(repo, new)
    assert plan.items == ()  # nothing to classify

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    assert report.manifest_written
    assert report.manifest.files == {}
    assert (repo / "unrelated.txt").read_text(encoding="utf-8") == "local"  # untouched


# ---------------------------------------------------------------------------
# generated-file exclusion
# ---------------------------------------------------------------------------


def test_generated_file_never_touched(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "keep.txt", "X")
    _write(repo / ".agentic/workflow.toml", "LOCAL CONFIG")
    _make_manifest(repo, {"keep.txt": "X"}, generated=(".agentic/workflow.toml",))
    # The new payload ships a wildly different workflow.toml — must be ignored.
    _make_payload(new, {"keep.txt": "X", ".agentic/workflow.toml": "TOTALLY DIFFERENT UPSTREAM CONFIG"})

    plan = _plan(repo, new)
    # Never classified, never in any action list.
    assert all(item.path != ".agentic/workflow.toml" for item in plan.items)
    for action in FileAction:
        assert ".agentic/workflow.toml" not in plan.by_action(action)

    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))
    # Survives untouched; still recorded as generated; never in files.
    assert (repo / ".agentic/workflow.toml").read_text(encoding="utf-8") == "LOCAL CONFIG"
    assert ".agentic/workflow.toml" in report.manifest.generated
    assert ".agentic/workflow.toml" not in report.manifest.files


# ---------------------------------------------------------------------------
# conflict hook cardinality + each decision's on-disk + manifest result
# ---------------------------------------------------------------------------


class _RecordingHook:
    """
    @brief Test hook recording every conflict path it is asked to resolve.
    @author Eng. Dan Dumitru Pasare
    @version 0.1.0
    """

    def __init__(self, decision: ConflictDecision) -> None:
        self.decision = decision
        self.calls: list[str] = []

    def __call__(self, conflict: UpgradeConflict) -> ConflictDecision:
        self.calls.append(conflict.relative_path)
        return self.decision


def _mixed_scenario(tmp_path: Path) -> tuple[Path, Path]:
    """
    @brief      One repo/new pair with an unchanged, an auto-apply, and a
                conflict file (for cardinality assertions).
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "a.txt", "X")  # unchanged
    _write(repo / "b.txt", "X")  # auto-apply (L==O, N!=O)
    _write(repo / "c.txt", "Z")  # conflict (L!=O, N!=O, L!=N)
    _make_manifest(repo, {"a.txt": "X", "b.txt": "X", "c.txt": "X"})
    _make_payload(new, {"a.txt": "X", "b.txt": "Y", "c.txt": "Y"})
    return repo, new


def test_conflict_hook_called_once_only_for_conflicts(tmp_path: Path) -> None:
    repo, new = _mixed_scenario(tmp_path)
    plan = _plan(repo, new)
    hook = _RecordingHook(ConflictDecision.KEEP_LOCAL)
    apply_upgrade(plan, hook=hook, runner=_smoke_ok_runner(repo))
    assert hook.calls == ["c.txt"]  # exactly once, only the true conflict


def test_rewritten_hook_config_is_reported_for_retrust(tmp_path: Path) -> None:
    """
    @brief      Rewriting `.codex/hooks.json` reports it as needing re-trust,
                and the human report says so in the action-required block.
    @details    Codex binds hook trust to the file's content hash, so a
                byte-correct upgrade of this file stops every hook in it from
                running until it is re-reviewed. The upgrade still succeeds and
                the smoke re-verify still passes, so this notice is the only
                signal the operator gets that enforcement is now off.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-28
    @version    0.1.0
    """
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / ".codex/hooks.json", '{"hooks": {}}')
    _make_manifest(repo, {".codex/hooks.json": '{"hooks": {}}'})
    _make_payload(new, {".codex/hooks.json": '{"description": "x", "hooks": {}}'})

    plan = _plan(repo, new)
    assert _action_of(plan, ".codex/hooks.json") is FileAction.AUTO_APPLY_NEW
    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))

    assert report.manifest_written
    assert report.hook_configs_needing_retrust() == (".codex/hooks.json",)
    assert report.to_dict()["hook_configs_needing_retrust"] == [".codex/hooks.json"]

    buffer = io.StringIO()
    render_upgrade_report(report, buffer)
    rendered = buffer.getvalue()
    assert "ACTION REQUIRED" in rendered
    assert ".codex/hooks.json" in rendered


def test_untouched_hook_config_needs_no_retrust(tmp_path: Path) -> None:
    """
    @brief      An upgrade that does not rewrite the hook config reports no
                re-trust, and stays silent about it in the human report.
    @details    Guards against a notice that fires on every upgrade: one the
                operator learns to skip is worth no more than none at all.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-28
    @version    0.1.0
    """
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / ".codex/hooks.json", '{"hooks": {}}')
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {".codex/hooks.json": '{"hooks": {}}', "file.txt": "X"})
    _make_payload(new, {".codex/hooks.json": '{"hooks": {}}', "file.txt": "Y"})

    plan = _plan(repo, new)
    assert _action_of(plan, ".codex/hooks.json") is FileAction.UNCHANGED
    report = apply_upgrade(plan, runner=_smoke_ok_runner(repo))

    assert report.hook_configs_needing_retrust() == ()
    buffer = io.StringIO()
    render_upgrade_report(report, buffer)
    assert "ACTION REQUIRED" not in buffer.getvalue()


def test_keep_local_hook_config_needs_no_retrust(tmp_path: Path) -> None:
    """
    @brief      A conflict resolved ``keep-local`` writes nothing, so the
                existing hook trust survives and no re-review is demanded.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-28
    @version    0.1.0
    """
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / ".codex/hooks.json", '{"hooks": {"local": 1}}')  # L != O
    _make_manifest(repo, {".codex/hooks.json": '{"hooks": {}}'})
    _make_payload(new, {".codex/hooks.json": '{"hooks": {"new": 1}}'})  # N != O, N != L

    plan = _plan(repo, new)
    assert _action_of(plan, ".codex/hooks.json") is FileAction.CONFLICT
    report = apply_upgrade(plan, hook=_RecordingHook(ConflictDecision.KEEP_LOCAL), runner=_smoke_ok_runner(repo))

    assert report.hook_configs_needing_retrust() == ()


def test_take_payload_hook_config_needs_retrust(tmp_path: Path) -> None:
    """
    @brief      A conflict resolved ``take-payload`` does rewrite the file, so
                it is reported for re-trust like any other write.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-28
    @version    0.1.0
    """
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / ".codex/hooks.json", '{"hooks": {"local": 1}}')
    _make_manifest(repo, {".codex/hooks.json": '{"hooks": {}}'})
    _make_payload(new, {".codex/hooks.json": '{"hooks": {"new": 1}}'})

    plan = _plan(repo, new)
    report = apply_upgrade(plan, hook=_RecordingHook(ConflictDecision.TAKE_PAYLOAD), runner=_smoke_ok_runner(repo))

    assert report.hook_configs_needing_retrust() == (".codex/hooks.json",)


def test_conflict_keep_local(tmp_path: Path) -> None:
    repo, new = _mixed_scenario(tmp_path)
    plan = _plan(repo, new)
    report = apply_upgrade(plan, hook=_RecordingHook(ConflictDecision.KEEP_LOCAL), runner=_smoke_ok_runner(repo))
    assert (repo / "c.txt").read_text(encoding="utf-8") == "Z"  # local kept
    assert "c.txt" not in report.manifest.files
    assert "c.txt" in report.manifest.skipped


def test_conflict_take_payload(tmp_path: Path) -> None:
    repo, new = _mixed_scenario(tmp_path)
    plan = _plan(repo, new)
    report = apply_upgrade(plan, hook=_RecordingHook(ConflictDecision.TAKE_PAYLOAD), runner=_smoke_ok_runner(repo))
    assert (repo / "c.txt").read_text(encoding="utf-8") == "Y"  # payload taken
    assert report.manifest.files["c.txt"] == _entry("Y")
    assert "c.txt" not in report.manifest.skipped


def test_conflict_write_new_sidecar(tmp_path: Path) -> None:
    repo, new = _mixed_scenario(tmp_path)
    plan = _plan(repo, new)
    report = apply_upgrade(plan, hook=_RecordingHook(ConflictDecision.WRITE_NEW), runner=_smoke_ok_runner(repo))
    assert (repo / "c.txt").read_text(encoding="utf-8") == "Z"  # local kept
    assert (repo / ("c.txt" + SIDECAR_SUFFIX)).read_text(encoding="utf-8") == "Y"  # payload beside it
    assert "c.txt" not in report.manifest.files
    assert "c.txt" in report.manifest.skipped


# ---------------------------------------------------------------------------
# --dry-run: full plan, zero writes, manifest byte-identical
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"}, marker=True, version="2.0.1")  # would auto-apply

    manifest_path = repo / ".agentic" / "install-manifest.json"
    before = manifest_path.read_bytes()

    stream = io.StringIO()
    code = run_upgrade(
        repo,
        as_json=False,
        dry_run=True,
        stream=stream,
        payload=str(new),
        runner=_smoke_ok_runner(repo),
        home=tmp_path / "home",
    )

    assert code == EXIT_OK
    assert "Dry run" in stream.getvalue()
    assert "auto-apply-new" in stream.getvalue()
    assert (repo / "file.txt").read_text(encoding="utf-8") == "X"  # not applied
    assert manifest_path.read_bytes() == before  # byte-identical


# ---------------------------------------------------------------------------
# post-apply smoke failure + manifest-rewrite-last ordering
# ---------------------------------------------------------------------------


def test_smoke_failure_leaves_manifest_untouched(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"}, payload_version="2.0.0")
    _make_payload(new, {"file.txt": "Y"})

    manifest_before = (repo / ".agentic" / "install-manifest.json").read_bytes()

    plan = _plan(repo, new)
    report = apply_upgrade(plan, runner=_smoke_fail_runner(repo))

    assert report.applied is False
    assert report.rolled_back is True
    assert report.smoke_ok is False
    assert report.manifest_written is False
    assert report.exit_code == EXIT_SMOKE_FAILED
    # Files and manifest are both restored by the transaction rollback.
    assert (repo / "file.txt").read_text(encoding="utf-8") == "X"
    assert (repo / ".agentic" / "install-manifest.json").read_bytes() == manifest_before
    assert read_manifest(repo).payload_version == "2.0.0"
    assert read_manifest(repo).files["file.txt"] == _entry("X")


# ---------------------------------------------------------------------------
# resume-after-partial-apply: a run that stops before step 3, then re-runs
# ---------------------------------------------------------------------------


def test_smoke_failure_rolls_back_and_clean_rerun_applies(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "auto.txt", "X")  # -> AUTO_APPLY_NEW
    _write(repo / "removed.txt", "X")  # -> DELETE_REMOVED
    _write(repo / "conflict.txt", "Z")  # -> CONFLICT (take-payload)
    _make_manifest(repo, {"auto.txt": "X", "removed.txt": "X", "conflict.txt": "X"}, payload_version="2.0.0")
    _make_payload(new, {"auto.txt": "Y", "conflict.txt": "Y"}, version="2.0.1")  # removed.txt dropped upstream

    # First run "stops before step 3": apply happens, but the smoke re-verify
    # fails so the manifest is NOT rewritten (simulating an abort after step 1).
    plan1 = _plan(repo, new)
    hook = make_resolution_hook({"conflict.txt": "take-payload"}, None)
    report1 = apply_upgrade(plan1, hook=hook, runner=_smoke_fail_runner(repo))
    assert report1.manifest_written is False
    assert read_manifest(repo).payload_version == "2.0.0"  # old manifest intact
    # Disk is restored completely.
    assert report1.rolled_back is True
    assert (repo / "auto.txt").read_text(encoding="utf-8") == "X"
    assert (repo / "removed.txt").read_text(encoding="utf-8") == "X"
    assert (repo / "conflict.txt").read_text(encoding="utf-8") == "Z"

    # Second run from scratch against the still-old manifest + updated disk.
    plan2 = _plan(repo, new)
    assert _action_of(plan2, "auto.txt") is FileAction.AUTO_APPLY_NEW
    assert _action_of(plan2, "conflict.txt") is FileAction.CONFLICT
    assert _action_of(plan2, "removed.txt") is FileAction.DELETE_REMOVED

    report2 = apply_upgrade(plan2, hook=hook, runner=_smoke_ok_runner(repo))
    assert report2.manifest_written is True
    final = read_manifest(repo)
    assert final.payload_version == "2.0.1"
    assert final.files["auto.txt"] == _entry("Y")
    assert final.files["conflict.txt"] == _entry("Y")
    assert "removed.txt" not in final.files
    # Disk unchanged by the second run (no double-apply corruption).
    assert (repo / "auto.txt").read_text(encoding="utf-8") == "Y"
    assert (repo / "conflict.txt").read_text(encoding="utf-8") == "Y"


# ---------------------------------------------------------------------------
# no-manifest conservative path
# ---------------------------------------------------------------------------


def test_no_manifest_is_rejected(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    # A plain .agentic/ install with NO manifest.
    _write(repo / ".agentic/collide.txt", "LOCAL")  # exists in both -> conflict
    _write(repo / ".agentic/workflow.toml", "MY CONFIG")  # protected as generated
    _write(repo / "unrelated.txt", "MINE")  # local-only -> left untouched
    _make_payload(
        new,
        {".agentic/collide.txt": "UPSTREAM", ".agentic/new-only.txt": "NEW", ".agentic/workflow.toml": "UP CONFIG"},
        version="2.0.1",
    )

    with pytest.raises(UpgradeError, match="valid current install manifest"):
        _plan(repo, new)


def test_invalid_manifest_is_rejected(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / ".agentic/install-manifest.json", "{ this is not valid json")
    _write(repo / "file.txt", "LOCAL")
    _make_payload(new, {"file.txt": "UPSTREAM"})

    with pytest.raises(UpgradeError, match="valid current install manifest"):
        _plan(repo, new)


# ---------------------------------------------------------------------------
# --json output (healthy + conflict-present)
# ---------------------------------------------------------------------------


def test_json_healthy_upgrade(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"}, marker=True, version="2.0.1")

    stream = io.StringIO()
    answers = _upgrade_answers(tmp_path / "answers.json")
    code = run_upgrade(
        repo,
        as_json=True,
        dry_run=False,
        stream=stream,
        payload=str(new),
        answers_path=answers,
        yes=True,
        runner=_smoke_ok_runner(repo),
        home=tmp_path / "home",
    )
    assert code == EXIT_OK
    data = json.loads(stream.getvalue())
    assert data["command"] == "upgrade"
    assert data["exit_code"] == EXIT_OK
    assert data["plan"]["repo"] == str(repo.resolve())
    assert data["plan"]["new_payload_version"] == "2.0.1"
    assert "file.txt" in data["plan"]["actions"]["auto-apply-new"]
    report = data["result"]
    assert report["applied"] is True
    assert report["smoke_ok"] is True
    assert report["manifest_written"] is True
    assert report["conflicts_unresolved"] is False
    assert report["conflicts"] == []


def test_branch_commit_upgrade_uses_git_operation_status_properties(tmp_path: Path) -> None:
    """
    @brief      Complete a branch-and-commit upgrade through ``GitOpResult.ok``.
    @details    Regression for T6.2: Git operation results expose ``ok`` as a
                boolean field, so branch creation, staging, and commit must not
                call it as a method.
    @param[in]  tmp_path Isolated repository, payload, answers, and journal root.
    @return     None
    @exception  AssertionError If the upgrade fails or omits a Git operation.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.2.0
    """
    repo, new = (tmp_path / "repo").resolve(), tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"}, marker=True, version="2.0.1")
    branch = "waegis/upgrade-2.0.1"
    answers = tmp_path / "answers.json"
    _write(answers, json.dumps({"git_mode": "branch-commit", "git_branch": branch}))
    runner = FakeCommandRunner(
        {
            ("git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"): ok_result(stdout="true\n"),
            ("git", "-C", str(repo), "status", "--porcelain"): ok_result(),
            ("git", "-C", str(repo), "checkout", "-b", branch): ok_result(),
            _wrapper_invocation(repo, "--help"): ok_result(),
                _wrapper_invocation(repo, "run", "status", "--json"): failing_result(
                    exit_code=2,
                    stderr=NO_ACTIVE_RUN_MARKER,
                ),
            ("git", "-C", str(repo), "add", "-A"): ok_result(),
            ("git", "-C", str(repo), "commit", "-m", "Upgrade AEGIS to 2.0.1"): ok_result(),
        }
    )

    code = run_upgrade(
        repo,
        as_json=True,
        dry_run=False,
        stream=io.StringIO(),
        payload=str(new),
        answers_path=answers,
        non_interactive=True,
        yes=True,
        runner=runner,
        home=tmp_path / "home",
    )

    assert code == EXIT_OK
    assert ("git", "-C", str(repo), "checkout", "-b", branch) in runner.calls
    assert ("git", "-C", str(repo), "add", "-A") in runner.calls
    assert ("git", "-C", str(repo), "commit", "-m", "Upgrade AEGIS to 2.0.1") in runner.calls


def test_branch_commit_upgrade_reports_branch_creation_failure(tmp_path: Path) -> None:
    """
    @brief      Return an operational envelope when the upgrade branch fails.
    @details    Regression for T6.2: failure reporting reads ``GitOpResult.detail``
                rather than calling a ``CommandResult``-only output method.
    @param[in]  tmp_path Isolated repository, payload, answers, and journal root.
    @return     None
    @exception  AssertionError If the failure escapes or loses Git's detail.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-20
    @version    0.1.0
    """
    repo, new = (tmp_path / "repo").resolve(), tmp_path / "new"
    _write(repo / "file.txt", "X")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"}, marker=True, version="2.0.1")
    branch = "waegis/upgrade-2.0.1"
    answers = tmp_path / "answers.json"
    _write(answers, json.dumps({"git_mode": "branch-commit", "git_branch": branch}))
    runner = FakeCommandRunner(
        {
            ("git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"): ok_result(stdout="true\n"),
            ("git", "-C", str(repo), "status", "--porcelain"): ok_result(),
            ("git", "-C", str(repo), "checkout", "-b", branch): failing_result(stderr="branch already exists"),
        }
    )
    stream = io.StringIO()

    code = run_upgrade(
        repo,
        as_json=True,
        dry_run=False,
        stream=stream,
        payload=str(new),
        answers_path=answers,
        non_interactive=True,
        yes=True,
        runner=runner,
        home=tmp_path / "home",
    )

    assert code == EXIT_ERROR
    assert "branch already exists" in json.loads(stream.getvalue())["messages"][0]
    assert (repo / "file.txt").read_text(encoding="utf-8") == "X"


def test_json_conflict_stop_and_report(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Z")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"}, marker=True, version="2.0.1")

    manifest_before = (repo / ".agentic" / "install-manifest.json").read_bytes()

    stream = io.StringIO()
    answers = _upgrade_answers(tmp_path / "answers.json")
    # --json path supplies no asker/resolutions -> stop-and-report.
    code = run_upgrade(
        repo,
        as_json=True,
        dry_run=False,
        stream=stream,
        payload=str(new),
        answers_path=answers,
        yes=True,
        runner=_smoke_ok_runner(repo),
        home=tmp_path / "home",
    )
    assert code == EXIT_CONFLICTS
    data = json.loads(stream.getvalue())
    assert data["status"] == "needs-input"
    assert data["result"] == {}
    assert "file.txt" in data["plan"]["actions"]["conflict"]
    # Nothing was written.
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Z"
    assert (repo / ".agentic" / "install-manifest.json").read_bytes() == manifest_before


def test_run_upgrade_resolutions_seam_applies(tmp_path: Path) -> None:
    repo, new = tmp_path / "repo", tmp_path / "new"
    _write(repo / "file.txt", "Z")
    _make_manifest(repo, {"file.txt": "X"})
    _make_payload(new, {"file.txt": "Y"}, marker=True, version="2.0.1")

    stream = io.StringIO()
    answers = _upgrade_answers(tmp_path / "answers.json")
    code = run_upgrade(
        repo,
        as_json=True,
        dry_run=False,
        stream=stream,
        payload=str(new),
        answers_path=answers,
        yes=True,
        resolutions={"file.txt": "take-payload"},
        runner=_smoke_ok_runner(repo),
        home=tmp_path / "home",
    )
    assert code == EXIT_OK
    assert (repo / "file.txt").read_text(encoding="utf-8") == "Y"


def test_run_upgrade_missing_repo_is_operational_error(tmp_path: Path) -> None:
    stream = io.StringIO()
    code = run_upgrade(tmp_path / "nope", as_json=False, dry_run=False, stream=stream)
    assert code == EXIT_ERROR


# ---------------------------------------------------------------------------
# realism: drive the REAL template as the "new" payload against an aged install
# ---------------------------------------------------------------------------


def test_real_template_as_new_payload(tmp_path: Path) -> None:
    """
    @brief      Verify upgrade actions against the current shipped AEGIS payload.
    @param[in]  tmp_path Temporary repository and payload workspace.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.1
    """
    real = locate_payload()  # the repo-checkout template
    repo = tmp_path / "repo"
    copy_payload(real, repo, mode="new")  # manifest O == real template hashes
    _amend_manifest_generated(repo)  # move workflow.toml -> generated (as new.py does)

    # Build a NEW payload = a copy of the real template with realistic edits.
    new = tmp_path / "new"
    copy_payload(real, new, mode="new")
    (new / ".agentic" / "install-manifest.json").unlink()  # not part of the payload

    # (a) upstream changed AGENTS.md (repo copy unmodified -> AUTO_APPLY_NEW)
    _write(new / "AGENTS.md", (new / "AGENTS.md").read_text(encoding="utf-8") + "\n# upstream change\n")
    # (b) upstream removed a category placeholder (repo copy unmodified -> DELETE_REMOVED)
    removed_rel = ".agentic/requirements/security/.gitkeep"
    (new / removed_rel).unlink()
    # (c) upstream version bump
    ver_file = new / ".agentic" / "cli" / "pyproject.toml"
    _pyproject = ver_file.read_text(encoding="utf-8")
    _current = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', _pyproject)
    bumped_payload_version = f"{_current.group(1)}.{_current.group(2)}.{int(_current.group(3)) + 1}"
    ver_file.write_text(
        _pyproject.replace(_current.group(0), f'version = "{bumped_payload_version}"'),
        encoding="utf-8",
    )

    # Operator locally edited CLAUDE.md (upstream unchanged there -> KEEP_LOCAL).
    _write(repo / "CLAUDE.md", (repo / "CLAUDE.md").read_text(encoding="utf-8") + "\n# my local note\n")

    plan = _plan(repo, new)
    assert "AGENTS.md" in plan.by_action(FileAction.AUTO_APPLY_NEW)
    assert removed_rel in plan.by_action(FileAction.DELETE_REMOVED)
    assert "CLAUDE.md" in plan.by_action(FileAction.KEEP_LOCAL)
    assert plan.conflicts() == ()  # only L==O or N==O changes were made
    # workflow.toml stayed generated (never classified).
    assert all(item.path != ".agentic/workflow.toml" for item in plan.items)

    report = apply_upgrade(plan, hook=None, runner=_smoke_ok_runner(repo))
    assert report.manifest_written is True
    assert report.manifest.payload_version == bumped_payload_version
    assert not (repo / removed_rel).exists()  # removed upstream, unmodified -> deleted
    assert "# upstream change" in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "# my local note" in (repo / "CLAUDE.md").read_text(encoding="utf-8")  # local edit preserved
    assert removed_rel not in report.manifest.files
    assert ".agentic/workflow.toml" in report.manifest.generated


# ---------------------------------------------------------------------------
# CLI wiring regression: only version/self-update/gui remain generic stubs
# ---------------------------------------------------------------------------


def test_version_command_is_released(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert f"WAEGIS {WIZARD_VERSION}" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["self-update", "gui"])
def test_unimplemented_commands_are_hidden(name: str) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([name])
    assert excinfo.value.code == 2


def test_upgrade_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["upgrade", "--help"])
    assert excinfo.value.code == 0


def test_upgrade_missing_repo_via_cli(tmp_path: Path) -> None:
    assert main(["upgrade", "--repo", str(tmp_path / "nope")]) == EXIT_ERROR


# END OF FILE
