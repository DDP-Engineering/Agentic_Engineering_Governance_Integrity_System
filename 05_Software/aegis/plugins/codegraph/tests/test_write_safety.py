#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_write_safety.py
@brief Write preconditions, locking, recovery, rebuild, liveness and confinement.
@details Covers REQ-SEC-57e210bb (Git precondition), REQ-SEC-135c0df0
         (ownership), REQ-REL-6f924213 (one writer), REQ-REL-b96977c7
         (reader states from SQLite), REQ-REL-4277bfc7 (recovery only while
         indexing), REQ-REL-bd1529a5 (rebuild), REQ-REL-0858819d (parent
         liveness), REQ-REL-10dc6424 (plugin changed mid-run) and
         REQ-SEC-db558433 (writes confined to the storage folder). Process-level
         behavior runs the real entry point the way AEGIS does.
"""

# IMPORTS

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from conftest import (
    DISPATCH_FLAGS,
    copy_plugin,
    git,
    make_repo,
    run_entry,
    run_json,
    tree_state,
)

from codegraph import config, indexer, python_extract, store

# CONSTANTS

SOURCE = {"src/app.py": "def main():\n    return helper()\n\n\ndef helper():\n    return 1\n"}

# HELPER FUNCTIONS


def database(root: Path) -> Path:
    """@brief The configured database path of a repository."""
    return config.load(root).database


def start_paused_index(root: Path, pause: Path, entry=None, extra_args=(), stdin=None,
                       env=None) -> subprocess.Popen:
    """@brief Start an index run that waits at the publication hook."""
    from conftest import ENTRY
    environment = dict(os.environ, CODEGRAPH_TEST_PAUSE_FILE=str(pause), **(env or {}))
    return subprocess.Popen(
        [sys.executable, *DISPATCH_FLAGS, str(entry or ENTRY), "index", "--root", str(root),
         "--json", *extra_args],
        stdin=stdin if stdin is not None else subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, env=environment)


def wait_for(path: Path, seconds: float = 60) -> None:
    """@brief Wait until a file exists."""
    end = time.monotonic() + seconds
    while not path.exists():
        assert time.monotonic() < end, f"timed out waiting for {path}"
        time.sleep(0.05)


def interrupted_write(root: Path) -> None:
    """@brief Leave a genuine hot journal by killing a run inside its transaction."""
    path = root / "src" / "late.py"
    path.write_text("def late():\n    pass\n" * 200, encoding="utf-8")
    done = run_entry(["index", "--root", str(root), "--json"],
                     env={"CODEGRAPH_TEST_KILL_AT": "after_insert"})
    assert done.returncode != 0
    assert Path(str(database(root)) + "-journal").exists()


def foreign_database(path: Path) -> bytes:
    """@brief Create an ordinary SQLite file at path and return its bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE notes(text TEXT)")
    conn.execute("INSERT INTO notes VALUES ('keep me')")
    conn.commit()
    conn.close()
    return path.read_bytes()


def alive(pid: int) -> bool:
    """@brief Whether a process ID is still running."""
    if sys.platform == "win32":
        done = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                              capture_output=True, text=True, check=False)
        return str(pid) in done.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True

# TESTS - Git precondition (REQ-SEC-57e210bb)


def test_storage_git_would_record_is_refused_before_any_write(tmp_path: Path):
    """REQ-SEC-57e210bb: not ignored -> refused; nothing is created."""
    root = make_repo(tmp_path / "repo", SOURCE, use_git=True, ignore_storage=False)
    code, env = run_json(["index", "--root", str(root)])
    assert (code, env["status"], env["reason"]) == (1, "error", "destination_not_ignored")
    assert "codegraph install" in env["message"] or ".gitignore" in env["message"]
    assert not (root / ".agentic" / "knowledge" / "codegraph").exists()


def test_tracked_storage_is_refused(tmp_path: Path):
    """REQ-SEC-57e210bb: a tracked file in storage blocks indexing."""
    root = make_repo(tmp_path / "repo", SOURCE, use_git=True)
    stray = root / ".agentic" / "knowledge" / "codegraph" / "notes.txt"
    stray.parent.mkdir(parents=True)
    stray.write_text("tracked by mistake\n", encoding="utf-8")
    git(root, "add", "-f", str(stray))
    code, env = run_json(["index", "--root", str(root)])
    assert (code, env["reason"]) == (1, "destination_tracked")
    assert "git rm --cached" in env["message"]
    assert not (stray.parent / "codegraph.lock").exists()


def test_ignored_storage_and_plain_folders_proceed(tmp_path: Path):
    """REQ-SEC-57e210bb: ignored storage indexes; outside Git the check is skipped."""
    for name, use_git in (("git", True), ("plain", False)):
        root = make_repo(tmp_path / name, SOURCE, use_git=use_git)
        code, env = run_json(["index", "--root", str(root)])
        assert (code, env["status"]) == (0, "ok"), name

# TESTS - ownership (REQ-SEC-135c0df0)


def test_foreign_files_are_never_opened_for_writing(tmp_path: Path):
    """REQ-SEC-135c0df0: foreign SQLite (with or without journal) and text stay intact."""
    root = make_repo(tmp_path / "repo", SOURCE)
    target = database(root)
    cases = {"sqlite": foreign_database(target)}
    journal = Path(str(target) + "-journal")
    for case in ("sqlite", "sqlite+journal", "text"):
        if case == "text":
            target.write_bytes(b"plain text, not a database\n")
            journal.unlink(missing_ok=True)
        elif case == "sqlite+journal":
            target.write_bytes(cases["sqlite"])
            journal.write_bytes(b"\xd9\xd5\x05\xf9\x20\xa1\x63\xd7" + b"\0" * 504)
        before = target.read_bytes()
        for args in (["index"], ["index", "--rebuild"]):
            code, env = run_json([*args, "--root", str(root)])
            assert (code, env["reason"]) == (1, "foreign_database"), (case, args)
            assert target.read_bytes() == before, (case, args)


def test_missing_database_is_created_with_the_codegraph_marker(tmp_path: Path):
    """REQ-SEC-135c0df0: only CodeGraph's own files carry the application ID."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    raw = database(root).read_bytes()
    assert raw[:16] == b"SQLite format 3\x00"
    assert int.from_bytes(raw[68:72], "big") == store.APPLICATION_ID

# TESTS - one writer (REQ-REL-6f924213)


def test_second_writer_is_busy_and_a_killed_holder_frees_the_lock(tmp_path: Path):
    """REQ-REL-6f924213: OS lock, released on death, lock file never replaced."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    lock = database(root).parent / "codegraph.lock"
    identity = lock.stat().st_ino
    pause = tmp_path / "pause"
    pids = tmp_path / "workers.txt"
    holder = start_paused_index(root, pause, env={"CODEGRAPH_TEST_WORKER_PIDS": str(pids)})
    (root / "src" / "more.py").write_text("x = 1\n", encoding="utf-8")
    try:
        wait_for(Path(str(pause) + ".waiting"))
        code, env = run_json(["index", "--root", str(root)])
        assert (code, env["status"], env["index"]) == (1, "error", "busy")
    finally:
        holder.kill()
        holder.wait(30)
    code, env = run_json(["index", "--root", str(root)])
    assert (code, env["status"]) == (0, "ok")
    assert lock.exists() and lock.stat().st_ino == identity

# TESTS - reader states (REQ-REL-b96977c7)


def test_reader_states_come_from_sqlite(tmp_path: Path):
    """REQ-REL-b96977c7: busy, needs_recovery, incompatible and harmless journals."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    target = database(root)
    journal = Path(str(target) + "-journal")
    journal.write_bytes(b"")
    conn, state = store.open_reader(target)
    assert state == "ready"
    conn.close()
    journal.unlink()
    writer = sqlite3.connect(target, isolation_level=None)
    writer.execute("BEGIN IMMEDIATE")
    conn, state = store.open_reader(target)
    assert state == "ready"
    assert conn.execute("SELECT count(*) FROM symbols").fetchone()[0] > 0
    conn.close()
    writer.execute("COMMIT")
    writer.execute("BEGIN EXCLUSIVE")
    _conn, state = store.open_reader(target)
    assert state == "busy"
    writer.execute("ROLLBACK")
    writer.close()
    interrupted_write(root)
    _conn, state = store.open_reader(target)
    assert state == "needs_recovery"
    other = tmp_path / "other" / ".agentic" / "knowledge" / "codegraph" / "codegraph.sqlite"
    foreign_database(other)
    _conn, state = store.open_reader(other)
    assert state == "incompatible"


def test_reads_continue_while_an_indexer_extracts(tmp_path: Path):
    """REQ-REL-b96977c7: a running indexer does not block the last generation."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    pause = tmp_path / "pause"
    (root / "src" / "more.py").write_text("x = 1\n", encoding="utf-8")
    holder = start_paused_index(root, pause)
    try:
        wait_for(Path(str(pause) + ".waiting"))
        conn, state = store.open_reader(database(root))
        assert state == "ready"
        conn.close()
    finally:
        pause.write_text("go", encoding="utf-8")
        holder.wait(60)

# TESTS - recovery (REQ-REL-4277bfc7)


def test_only_indexing_recovers_an_interrupted_write(tmp_path: Path):
    """REQ-REL-4277bfc7: readers leave the journal; the next index recovers."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    interrupted_write(root)
    journal = Path(str(database(root)) + "-journal")
    _conn, state = store.open_reader(database(root))
    assert state == "needs_recovery" and journal.exists()
    code, env = run_json(["index", "--root", str(root)])
    assert (code, env["status"]) == (0, "ok")
    conn, state = store.open_reader(database(root))
    assert state == "ready"
    assert conn.execute("SELECT count(*) FROM symbols WHERE name='late' "
                        "AND kind='function'").fetchone()[0] == 200
    conn.close()

# TESTS - rebuild (REQ-REL-bd1529a5)


def test_rebuild_replaces_healthy_interrupted_and_damaged_databases(tmp_path: Path):
    """REQ-REL-bd1529a5: validated replacement and no journal from the old file."""
    root = make_repo(tmp_path / "repo", SOURCE)
    target = database(root)
    journal = Path(str(target) + "-journal")
    for case in ("healthy", "interrupted", "damaged"):
        run_json(["index", "--root", str(root)])
        if case == "interrupted":
            interrupted_write(root)
        elif case == "damaged":
            raw = bytearray(target.read_bytes())
            raw[100:] = b"\xff" * (len(raw) - 100)
            target.write_bytes(bytes(raw))
        code, env = run_json(["index", "--rebuild", "--root", str(root)])
        assert (code, env["status"]) == (0, "ok"), case
        assert not journal.exists(), case
        conn = sqlite3.connect(target)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", case
        conn.close()
        assert not list(target.parent.glob(".codegraph-rebuild-*")), case


def test_failed_rebuild_keeps_the_previous_database(tmp_path: Path):
    """REQ-REL-bd1529a5: a failure during the build leaves the old file readable."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    before = database(root).read_bytes()
    done = run_entry(["index", "--rebuild", "--root", str(root), "--json"],
                     env={"CODEGRAPH_TEST_FAIL_REBUILD": "1"})
    assert done.returncode == 1
    env = json.loads(done.stdout)
    assert (env["status"], env["reason"], env["index"]) == ("error", "internal", "ready")
    assert database(root).read_bytes() == before
    assert not list(database(root).parent.glob(".codegraph-rebuild-*"))


def test_rebuild_waits_for_an_open_reader_instead_of_corrupting(tmp_path: Path):
    """REQ-REL-bd1529a5: replacement retries while a reader holds the file."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    opened = threading.Event()

    def hold_reader() -> None:
        conn, state = store.open_reader(database(root))
        assert state == "ready"
        opened.set()
        time.sleep(0.5)
        conn.close()
    reader = threading.Thread(target=hold_reader)
    reader.start()
    opened.wait(10)
    try:
        result = indexer.run_index(config.load(root), rebuild=True)
    finally:
        reader.join()
    assert result["meta"]["generation"] >= 1
    check = sqlite3.connect(database(root))
    assert check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    check.close()

# TESTS - parent liveness (REQ-REL-0858819d)


def test_closing_standard_input_stops_a_watched_run(tmp_path: Path):
    """REQ-REL-0858819d: end-of-file cancels, publishes nothing, leaves no worker."""
    root = make_repo(tmp_path / "repo", SOURCE)
    _code, first = run_json(["index", "--root", str(root)])
    (root / "src" / "slow.py").write_text("x = 1\n", encoding="utf-8")
    pids = tmp_path / "workers.txt"
    from conftest import ENTRY
    run = subprocess.Popen(
        [sys.executable, *DISPATCH_FLAGS, str(ENTRY), "index", "--root", str(root), "--json",
         "--watch-stdin"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=dict(os.environ, CODEGRAPH_TEST_SLOW_FILE="src/slow.py",
                 CODEGRAPH_TEST_WORKER_PIDS=str(pids)))
    wait_for(pids)
    time.sleep(0.5)
    started = time.monotonic()
    run.stdin.close()
    run.wait(30)
    assert time.monotonic() - started < 15
    assert run.returncode == 1
    assert json.loads(run.stdout.read())["reason"] == "cancelled"
    run.stdout.close()
    run.stderr.close()
    conn, _state = store.open_reader(database(root))
    assert store.read_meta(conn)["snapshot"] == first["snapshot"]
    conn.close()
    time.sleep(1)
    for pid in pids.read_text(encoding="utf-8").split():
        assert not alive(int(pid)), pid


def test_a_watched_run_with_open_input_completes(tmp_path: Path):
    """REQ-REL-0858819d: an input held open never stalls Git or the extraction workers."""
    root = make_repo(tmp_path / "repo", SOURCE, use_git=True)
    entry = copy_plugin(tmp_path / "plugin")   # edits to the source folder cannot interfere
    with (tmp_path / "stderr.txt").open("w+", encoding="utf-8") as errors:
        run = subprocess.Popen(
            [sys.executable, *DISPATCH_FLAGS, str(entry), "index", "--root", str(root),
             "--json", "--watch-stdin"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors)
        try:
            run.wait(60)
        except subprocess.TimeoutExpired:
            run.kill()
            run.wait()
        finally:
            run.stdin.close()
        output = run.stdout.read()
        run.stdout.close()
        errors.seek(0)
        assert run.returncode == 0, (output, errors.read()[-2000:])
    assert json.loads(output)["status"] == "ok"


def test_without_the_flag_a_closed_input_does_not_stop_the_run(tmp_path: Path):
    """REQ-REL-0858819d: terminal runs ignore standard input."""
    root = make_repo(tmp_path / "repo", SOURCE)
    done = run_entry(["index", "--root", str(root), "--json"], stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stderr

# TESTS - plugin changed mid-run (REQ-REL-10dc6424)


def test_changed_plugin_content_discards_the_run(tmp_path: Path):
    """REQ-REL-10dc6424: content identity, not the manifest version, decides."""
    root = make_repo(tmp_path / "repo", SOURCE)
    entry = copy_plugin(tmp_path / "plugin")
    first = run_entry(["index", "--root", str(root), "--json"], entry=entry)
    assert first.returncode == 0, first.stderr
    (root / "src" / "more.py").write_text("x = 1\n", encoding="utf-8")
    pause = tmp_path / "pause"
    run = start_paused_index(root, pause, entry=entry)
    wait_for(Path(str(pause) + ".waiting"))
    engine = entry.parent / "codegraph" / "scope.py"
    engine.write_text(engine.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8")
    pause.write_text("go", encoding="utf-8")
    out, _err = run.communicate(timeout=60)
    assert run.returncode == 1
    assert json.loads(out)["reason"] == "plugin_changed"
    conn, _state = store.open_reader(database(root))
    assert store.read_meta(conn)["snapshot"] == json.loads(first.stdout)["snapshot"]
    conn.close()
    shutil.rmtree(entry.parent)
    entry = copy_plugin(tmp_path / "plugin")
    pause.unlink()
    Path(str(pause) + ".waiting").unlink()
    unchanged = start_paused_index(root, pause, entry=entry)
    wait_for(Path(str(pause) + ".waiting"))
    pause.write_text("go", encoding="utf-8")
    unchanged.communicate(timeout=60)
    assert unchanged.returncode == 0

# TESTS - first build, failures and reported state (REQ-REL-1eeb1914, REQ-FUNC-8cb1a3b7)


def test_an_interrupted_first_run_leaves_no_database(tmp_path: Path):
    """REQ-REL-1eeb1914: the first generation is built aside, so a killed run leaves nothing."""
    root = make_repo(tmp_path / "repo", SOURCE)
    done = run_entry(["index", "--root", str(root), "--json"],
                     env={"CODEGRAPH_TEST_KILL_AT": "before_publish"})
    assert done.returncode != 0
    assert not database(root).exists()
    _code, env = run_json(["status", "--root", str(root)])
    assert (env["status"], env["index"]) == ("unavailable", "missing")
    _code, env = run_json(["index", "--root", str(root)])
    assert env["status"] == "ok"
    assert not list(database(root).parent.glob(".codegraph-rebuild-*"))


def test_a_journal_without_its_database_never_meets_the_rebuilt_file(tmp_path: Path):
    """REQ-REL-bd1529a5: a journal whose database is gone is discarded, not replayed."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    interrupted_write(root)
    database(root).unlink()
    _code, env = run_json(["index", "--rebuild", "--root", str(root)])
    assert env["status"] == "ok"
    assert not Path(str(database(root)) + "-journal").exists()
    _code, env = run_json(["status", "--root", str(root)])
    assert env["index"] == "ready"


def test_a_commit_blocked_by_a_reader_reports_busy(tmp_path: Path):
    """REQ-REL-6f924213: SQLite busy at publication is busy, not a damaged database."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    (root / "src" / "app.py").write_text(SOURCE["src/app.py"] + "\n\ndef extra():\n    pass\n",
                                         encoding="utf-8")
    reader = sqlite3.connect(database(root), isolation_level=None)
    reader.execute("BEGIN")
    reader.execute("SELECT count(*) FROM symbols").fetchone()
    try:
        code, env = run_json(["index", "--root", str(root)])
    finally:
        reader.execute("ROLLBACK")
        reader.close()
    assert (code, env["status"], env["reason"], env["index"]) == (1, "error", "busy", "busy")


def test_index_refusals_report_the_database_state(tmp_path: Path):
    """REQ-FUNC-8cb1a3b7: an index error still says what state the database is in."""
    root = make_repo(tmp_path / "repo", SOURCE, use_git=True, ignore_storage=False)
    _code, env = run_json(["index", "--root", str(root)])
    assert (env["reason"], env["index"]) == ("destination_not_ignored", "missing")


def test_cancellation_during_resolution_publishes_nothing(tmp_path: Path):
    """REQ-REL-0858819d: a stop request after extraction still prevents publication."""
    root = make_repo(tmp_path / "repo", SOURCE)
    first = indexer.run_index(config.load(root))
    (root / "src" / "app.py").write_text(SOURCE["src/app.py"] + "\n\ndef extra():\n    pass\n",
                                         encoding="utf-8")
    phases: list[str] = []
    with pytest.raises(python_extract.Cancelled):
        indexer.run_index(config.load(root), should_stop=lambda: "resolve" in phases,
                          progress=lambda phase, *_rest: phases.append(phase))
    conn, _state = store.open_reader(database(root))
    assert store.read_meta(conn)["snapshot"] == first["meta"]["snapshot"]
    conn.close()


def test_generation_keeps_counting_across_a_rebuild(tmp_path: Path):
    """REQ-REL-1eeb1914: generations increase across updates and rebuilds."""
    root = make_repo(tmp_path / "repo", SOURCE)
    run_json(["index", "--root", str(root)])
    run_json(["index", "--root", str(root)])
    _code, env = run_json(["index", "--rebuild", "--root", str(root)])
    assert env["generation"] == 3

# TESTS - write confinement (REQ-SEC-db558433)


def test_indexing_writes_only_the_storage_folder(tmp_path: Path):
    """REQ-SEC-db558433: index, rebuild and recovery change nothing else."""
    root = make_repo(tmp_path / "repo", SOURCE)
    entry = copy_plugin(root / ".agentic" / "plugins" / "codegraph")
    storage = ".agentic/knowledge/codegraph"
    before = {k: v for k, v in tree_state(root).items() if not k.startswith(storage)}
    for args, env in ((["index"], {}), (["index", "--rebuild"], {}),
                      (["index"], {"CODEGRAPH_TEST_KILL_AT": "after_insert"}), (["index"], {})):
        if env:
            (root / "src" / "app.py").write_text(SOURCE["src/app.py"] + "\n# changed\n",
                                                 encoding="utf-8")
            before = {k: v for k, v in tree_state(root).items() if not k.startswith(storage)}
        done = run_entry([*args, "--root", str(root), "--json"], entry=entry, env=env)
        assert (done.returncode != 0) == bool(env), (args, done.stderr)
        after = {k: v for k, v in tree_state(root).items() if not k.startswith(storage)}
        assert after == before, args
    (root / "src" / "app.py").write_text(SOURCE["src/app.py"] + "\n# again\n", encoding="utf-8")
    before = {k: v for k, v in tree_state(root).items() if not k.startswith(storage)}
    standalone = run_entry(["index", "--root", str(root), "--json"], entry=entry, flags=(),
                           env={"PYTHONDONTWRITEBYTECODE": ""})
    assert standalone.returncode == 0, standalone.stderr
    after = {k: v for k, v in tree_state(root).items() if not k.startswith(storage)}
    assert after == before
    assert not list(root.rglob("__pycache__"))

# END OF FILE
