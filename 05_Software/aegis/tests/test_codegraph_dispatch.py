#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_codegraph_dispatch.py
@brief The AEGIS core's knowledge-graph commands, against a stub plugin.
@details Every test copies `template/.agentic` into a tmp_path repository and
         installs a tiny standard-library stub as
         `.agentic/plugins/codegraph/codegraph.py`. The stub records how it was
         launched (interpreter, flags, arguments) and answers with whatever
         `stub.json` beside it asks for, so the core's dispatch, limits,
         validation and exit codes are tested without any parser.
"""

# IMPORTS

from __future__ import annotations

import importlib.util
import itertools
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# CONSTANTS

PAYLOAD = Path(__file__).resolve().parents[1] / "template" / ".agentic"
_COUNTER = itertools.count()
READ_COMMANDS = {"know_graph": ("status", None), "know_graph_check": ("check", None),
                 "know_graph_find": ("find", "Order"), "know_graph_file": ("file", "src/a.py"),
                 "know_graph_symbol": ("symbol", "0123456789"),
                 "know_graph_callers": ("callers", "0123456789"),
                 "know_graph_refs": ("refs", "0123456789")}
ALL_COMMANDS = {**READ_COMMANDS, "know_graph_index": ("index", None)}
ENABLED = "[codegraph]\nenabled = true\n"

STUB = r'''
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(here, "stub.json")
settings = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
record = {"argv": sys.argv[1:], "executable": sys.executable, "isolated": sys.flags.isolated,
          "no_bytecode": sys.flags.dont_write_bytecode, "utf8": sys.flags.utf8_mode,
          "pid": os.getpid()}
if settings.get("child"):
    record["child"] = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"]).pid
if settings.get("orphan"):
    record["orphan"] = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(%d)" % settings["orphan"]],
        stdout=sys.stdout).pid
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as handle:
    handle.write(json.dumps(record) + "\n")
if settings.get("stderr"):
    sys.stderr.write(settings["stderr"])
    sys.stderr.flush()
if settings.get("wait_eof"):
    sys.stdin.buffer.read()
    open(os.path.join(here, "eof.txt"), "w").write("eof")
time.sleep(settings.get("sleep", 0))
if settings.get("flood"):
    sys.stdout.buffer.write(b"x" * settings["flood"])
    sys.stdout.flush()
out = settings.get("raw")
if out is None:
    env = {"schema": 1, "provider": "codegraph", "protocol": 1, "plugin_version": "0.1.0",
           "action": sys.argv[1], "status": settings.get("status", "ok"), "reason": None,
           "message": None, "index": "ready", "freshness": "not_fully_checked",
           "indexing_supported": True, "python_support": "tested", "snapshot": None,
           "generation": None, "indexed_at": None, "has_more": False, "next_page": None}
    if "--json" in sys.argv:
        env.update(results=[], details=settings.get("details", {}))
    else:
        env["text"] = settings.get("text", "STUB TEXT")
    out = json.dumps(env)
sys.stdout.write(out)
sys.stdout.flush()
sys.exit(settings.get("exit", 0))
'''

# HELPER FUNCTIONS


def make_repo(tmp_path: Path, config: str = ENABLED, stub: dict | None = None,
              install: bool = True) -> tuple[Path, object]:
    """@brief Payload copy with config and (optionally) a stub plugin; returns (agentic, module)."""
    agentic = tmp_path / ".agentic"
    shutil.copytree(PAYLOAD, agentic)
    (agentic / "aegis.toml").write_text(config, encoding="utf-8")
    (agentic / "knowledge").mkdir(exist_ok=True)
    if install:
        plugin = agentic / "plugins" / "codegraph"
        plugin.mkdir(parents=True)
        (plugin / "codegraph.py").write_text(STUB, encoding="utf-8")
        (plugin / "stub.json").write_text(json.dumps(stub or {}), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"aegis_codegraph_{next(_COUNTER)}",
                                                  agentic / "aegis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return agentic, module


def set_stub(agentic: Path, **settings) -> None:
    """@brief Replace the stub's behavior settings."""
    (agentic / "plugins" / "codegraph" / "stub.json").write_text(json.dumps(settings),
                                                                  encoding="utf-8")


def calls(agentic: Path) -> list[dict]:
    """@brief Launch records written by the stub."""
    path = agentic / "plugins" / "codegraph" / "calls.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def command_args(command: str) -> list[str]:
    """@brief A complete invocation of one knowledge-graph command."""
    target = ALL_COMMANDS[command][1]
    return [command] if target is None else [command, target]


def alive(pid: int) -> bool:
    """@brief Whether a process is still running."""
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


def wait_dead(pid: int, seconds: float = 10) -> bool:
    """@brief Poll until a process has gone."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if not alive(pid):
            return True
        time.sleep(0.2)
    return False

# TESTS - disabled and missing plugin (REQ-FUNC-b303507f, REQ-FUNC-f5d5ee3d)


@pytest.mark.parametrize("config", ["schema = 1\n", "[codegraph]\nenabled = false\n"])
def test_disabled_codegraph_starts_nothing(tmp_path: Path, capsys, config: str):
    """REQ-FUNC-b303507f: every command reports disabled and exits 0."""
    agentic, aegis = make_repo(tmp_path, config=config)
    for command in ALL_COMMANDS:
        assert aegis.main([*command_args(command), "--json"]) == 0, command
        env = json.loads(capsys.readouterr().out)
        assert (env["status"], env["reason"], env["action"]) == \
            ("disabled", "not_enabled", ALL_COMMANDS[command][0])
    assert aegis.main(["know_graph"]) == 0
    assert "disabled" in capsys.readouterr().out
    assert calls(agentic) == []
    assert not (agentic / "knowledge" / "codegraph").exists()
    (agentic / "aegis.toml").write_text(ENABLED, encoding="utf-8")
    assert aegis.main(["know_graph"]) == 0
    assert len(calls(agentic)) == 1


def test_missing_plugin_is_unavailable(tmp_path: Path, capsys):
    """REQ-FUNC-f5d5ee3d: enabled without a plugin folder starts nothing."""
    agentic, aegis = make_repo(tmp_path, install=False)
    for command in ALL_COMMANDS:
        assert aegis.main([*command_args(command), "--json"]) == 0, command
        env = json.loads(capsys.readouterr().out)
        assert (env["status"], env["reason"]) == ("unavailable", "plugin_missing")
    assert not (agentic / "plugins").exists()
    assert not (agentic / "knowledge" / "codegraph").exists()

# TESTS - governance commands stay independent (REQ-FUNC-8b15c62d)


def test_governance_commands_never_start_the_plugin(tmp_path: Path, capsys, monkeypatch):
    """REQ-FUNC-8b15c62d: only know_graph commands launch the plugin."""
    config = ENABLED + '[commands]\ntest = "python -c pass"\n'
    agentic, aegis = make_repo(tmp_path, config=config)
    monkeypatch.setattr(aegis, "git_branch", lambda: "main")
    assert aegis.main(["task", "Probe CodeGraph isolation"]) == 0
    task = capsys.readouterr().out.strip().rsplit("/", 1)[-1].removesuffix(".md")
    for argv in (["init"], ["status"], ["brief", task], ["summary", task], ["check"],
                 ["check", "--run"], ["components"], ["explain", ".agentic/aegis.toml"],
                 ["trace"], ["diagram"]):
        aegis.main(argv)
        capsys.readouterr()
    assert calls(agentic) == []
    aegis.main(["know_graph"])
    assert len(calls(agentic)) == 1

# TESTS - dispatch (REQ-FUNC-b383069e)


def test_read_commands_run_the_entry_point_isolated_with_their_arguments(tmp_path: Path,
                                                                         capsys):
    """REQ-FUNC-b383069e: same interpreter, -I -B -X utf8, paths, protocol, target."""
    agentic, aegis = make_repo(tmp_path)
    for command, (operation, target) in READ_COMMANDS.items():
        assert aegis.main(command_args(command)) == 0, command
        assert capsys.readouterr().out == "STUB TEXT\n"
        record = calls(agentic)[-1]
        assert (record["isolated"], record["no_bytecode"], record["utf8"]) == (1, 1, 1)
        assert os.path.samefile(record["executable"], sys.executable)
        argv = record["argv"]
        assert argv[0] == operation
        root = aegis.ROOT
        assert argv[argv.index("--root") + 1] == str(root)
        assert argv[argv.index("--config") + 1] == str(agentic / "aegis.toml")
        assert argv[argv.index("--database") + 1] == str(
            root / ".agentic" / "knowledge" / "codegraph" / "codegraph.sqlite")
        assert argv[argv.index("--protocol") + 1] == "1"
        assert "--text-envelope" in argv
        if target:
            assert argv[-2:] == ["--", target]
    aegis.main(["know_graph_find", "--json", "--limit", "5", "--max-bytes", "2048",
                "--", "-dash"])
    argv = calls(agentic)[-1]["argv"]
    assert argv[-2:] == ["--", "-dash"] and "--json" in argv
    assert argv[argv.index("--limit") + 1] == "5"
    assert argv[argv.index("--max-bytes") + 1] == "2048"
    aegis.main(["know_graph_symbol", "0123456789", "--limit", "5"])
    argv = calls(agentic)[-1]["argv"]
    assert argv[argv.index("--limit") + 1] == "5"
    aegis.main(["know_graph_file", "./src\\a.py"])
    assert calls(agentic)[-1]["argv"][-1] == "src/a.py"
    with pytest.raises(SystemExit) as caught:
        aegis.main(["know_graph_find"])
    assert caught.value.code == 2


def test_id_commands_pass_every_id_in_order(tmp_path: Path, capsys):
    """REQ-FUNC-b383069e: several IDs arrive after `--` in order; find and file keep one."""
    agentic, aegis = make_repo(tmp_path)
    ids = ["0123456789", "abcdef0123", "fedcba9876"]
    for command in ("know_graph_symbol", "know_graph_callers", "know_graph_refs"):
        assert aegis.main([command, *ids]) == 0, command
        assert calls(agentic)[-1]["argv"][-4:] == ["--", *ids]
    launched = len(calls(agentic))
    for command in ("know_graph_find", "know_graph_file"):
        with pytest.raises(SystemExit) as caught:
            aegis.main([command, "one", "two"])
        assert caught.value.code == 2
    assert len(calls(agentic)) == launched
    capsys.readouterr()


@pytest.mark.parametrize("argv", [
    ["know_graph", "--limit", "5"], ["know_graph_check", "--max-bytes", "2048"],
    ["know_graph", "--page", "x"], ["know_graph_symbol", "0123456789", "--page", "x"],
    ["know_graph_index", "--limit", "5"]])
def test_options_a_command_does_not_use_are_usage_errors(tmp_path: Path, argv: list[str]):
    """REQ-FUNC-b383069e: only paged queries take --page; status and check take neither bound."""
    agentic, aegis = make_repo(tmp_path)
    with pytest.raises(SystemExit) as caught:
        aegis.main(argv)
    assert caught.value.code == 2
    assert calls(agentic) == []

# TESTS - database path (REQ-SEC-c7e64a0e)


@pytest.mark.parametrize("value", [
    "src/index.sqlite", "../outside.sqlite",
    ".agentic/knowledge/codegraph/codegraph.sqlite-journal",
    ".agentic/knowledge/codegraph/codegraph.lock",
    ".agentic/knowledge/codegraph/sub/x.sqlite"])
def test_invalid_database_path_starts_nothing(tmp_path: Path, capsys, value: str):
    """REQ-SEC-c7e64a0e: one-line error, exit 1, no launch."""
    agentic, aegis = make_repo(tmp_path, config=ENABLED + f'database = "{value}"\n')
    assert aegis.main(["know_graph"]) == 1
    assert capsys.readouterr().err.startswith("error: [codegraph] database")
    assert calls(agentic) == []


def test_linked_storage_folder_is_rejected(tmp_path: Path, capsys):
    """REQ-SEC-c7e64a0e: a link may not move the storage folder out of the repository."""
    agentic, aegis = make_repo(tmp_path / "repo")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, agentic / "knowledge" / "codegraph", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available on this machine")
    assert aegis.main(["know_graph"]) == 1
    assert calls(agentic) == []


def test_alternative_database_name_is_accepted(tmp_path: Path):
    """REQ-SEC-c7e64a0e: NAME.sqlite inside the storage folder launches."""
    agentic, aegis = make_repo(
        tmp_path, config=ENABLED + 'database = ".agentic/knowledge/codegraph/alt-1.sqlite"\n')
    assert aegis.main(["know_graph"]) == 0
    argv = calls(agentic)[-1]["argv"]
    assert argv[argv.index("--database") + 1].endswith("alt-1.sqlite")

# TESTS - limits (REQ-REL-53d13fb2, REQ-REL-0e1c6d89)


@pytest.mark.parametrize("command, key", [("know_graph", "timeout_seconds"),
                                          ("know_graph_check", "check_timeout_seconds"),
                                          ("know_graph_index", "index_timeout_seconds")])
def test_time_limit_kills_the_plugin_tree(tmp_path: Path, capsys, command: str, key: str):
    """REQ-REL-53d13fb2: exit 1 near the limit; plugin and its child are gone."""
    agentic, aegis = make_repo(tmp_path, config=ENABLED + f"{key} = 1\n",
                               stub={"sleep": 30, "child": True})
    storage = agentic / "knowledge"
    before = sorted(p.name for p in storage.rglob("*"))
    started = time.monotonic()
    assert aegis.main([command]) == 1
    assert time.monotonic() - started < 15
    assert "time limit" in capsys.readouterr().err
    record = calls(agentic)[-1]
    assert wait_dead(record["pid"]) and wait_dead(record["child"])
    assert sorted(p.name for p in storage.rglob("*")) == before


def test_a_refused_tree_kill_returns_and_says_so(tmp_path: Path, capsys, monkeypatch):
    """REQ-REL-53d13fb2: survivors holding the output pipe neither hang AEGIS nor go unmentioned."""
    agentic, aegis = make_repo(tmp_path, config=ENABLED + "timeout_seconds = 1\n",
                               stub={"sleep": 30, "orphan": 20})

    def refused(proc) -> bool:   # what kill_tree returns when taskkill is denied
        proc.kill()
        return False
    monkeypatch.setattr(aegis, "kill_tree", refused)
    started = time.monotonic()
    try:
        assert aegis.main(["know_graph"]) == 1
        assert time.monotonic() - started < 15
        assert "may have survived" in capsys.readouterr().err
    finally:
        orphan = calls(agentic)[-1].get("orphan")
        if orphan and alive(orphan):
            os.kill(orphan, signal.SIGTERM)


def test_no_survivors_are_claimed_for_a_plugin_that_already_exited(tmp_path: Path, capsys,
                                                                   monkeypatch):
    """REQ-REL-0e1c6d89: a refused kill of a finished plugin is not reported as survivors."""
    _agentic, aegis = make_repo(tmp_path, stub={"flood": 66000})

    def refused(proc) -> bool:   # taskkill refuses a process that has already exited
        proc.wait(10)
        return False
    monkeypatch.setattr(aegis, "kill_tree", refused)
    assert aegis.main(["know_graph"]) == 1
    error = capsys.readouterr().err
    assert "output exceeded" in error and "may have survived" not in error


def test_a_child_still_holding_the_output_is_reported(tmp_path: Path, capsys):
    """REQ-REL-53d13fb2: a finished plugin whose child keeps its output open is a survivor case."""
    agentic, aegis = make_repo(tmp_path, config=ENABLED + "timeout_seconds = 1\n",
                               stub={"orphan": 8})
    try:
        assert aegis.main(["know_graph"]) == 1
        error = capsys.readouterr().err
        assert "time limit" in error
        if sys.platform == "win32":
            # taskkill cannot reach a child whose parent has already exited
            assert "may have survived" in error
        else:
            # the plugin's process group still reaches the child
            assert wait_dead(calls(agentic)[-1]["orphan"], 5)
            assert "may have survived" not in error
    finally:
        orphan = calls(agentic)[-1].get("orphan")
        if orphan and alive(orphan):
            os.kill(orphan, signal.SIGTERM)


def test_index_without_a_limit_outlasts_the_read_limit(tmp_path: Path):
    """REQ-REL-53d13fb2: index_timeout_seconds = 0 applies no limit."""
    _agentic, aegis = make_repo(tmp_path, config=ENABLED + "timeout_seconds = 1\n",
                                stub={"sleep": 3})
    assert aegis.main(["know_graph_index"]) == 0


def test_output_cap_stops_a_flooding_plugin(tmp_path: Path, capsys):
    """REQ-REL-0e1c6d89: reading stops at the cap; the plugin is terminated."""
    agentic, aegis = make_repo(tmp_path, stub={"flood": 10 * 1024 * 1024, "sleep": 0})
    started = time.monotonic()
    assert aegis.main(["know_graph"]) == 1
    assert time.monotonic() - started < 15
    assert "output exceeded" in capsys.readouterr().err
    assert wait_dead(calls(agentic)[-1]["pid"])
    padding = {"pad": "y" * 60000}
    set_stub(agentic, details=padding)
    assert aegis.main(["know_graph", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["details"] == padding

# TESTS - protocol validation and exit codes (REQ-FUNC-e780b270, REQ-FUNC-d1994267)


@pytest.mark.parametrize("raw", [
    "not json", '{"schema": 1}{"schema": 1}',
    '{"schema": 1, "provider": "codegraph", "protocol": 1, "action": "find", "status": "ok", "text": "t"}',
    '{"schema": 1, "provider": "codegraph", "protocol": 1, "action": "status", "status": "weird", "text": "t"}',
    '{"schema": 1, "provider": "codegraph", "protocol": 1, "action": "status", "status": "ok"}',
    '{"schema": 2, "provider": "codegraph", "protocol": 1, "action": "status", "status": "ok", "text": "t"}',
    '{"schema": 1, "provider": "other", "protocol": 1, "action": "status", "status": "ok", "text": "t"}',
    '{"schema": 1, "provider": "codegraph", "protocol": 2, "action": "status", "status": "ok", "text": "t"}'])
def test_malformed_plugin_output_is_a_protocol_failure(tmp_path: Path, capsys, raw: str):
    """REQ-FUNC-e780b270: nothing of the plugin's output is printed."""
    _agentic, aegis = make_repo(tmp_path, stub={"raw": raw})
    assert aegis.main(["know_graph"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "protocol failure" in captured.err


def test_an_empty_answer_reports_what_the_plugin_said(tmp_path: Path, capsys):
    """REQ-FUNC-e780b270: no output is a failure without an answer, naming the plugin's error."""
    _agentic, aegis = make_repo(tmp_path, stub={
        "raw": "", "exit": 1, "stderr": "error: [codegraph] include must be a list of strings\n"})
    assert aegis.main(["know_graph"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: CodeGraph failed without an answer: error: "
                                   "[codegraph] include must be a list of strings")


@pytest.mark.parametrize("status, code", [
    ("ok", 0), ("ambiguous", 0), ("not_found", 0), ("expired", 0), ("unavailable", 0),
    ("disabled", 0), ("error", 1)])
def test_status_maps_to_the_exit_code(tmp_path: Path, capsys, status: str, code: int):
    """REQ-FUNC-d1994267: only status error fails."""
    _agentic, aegis = make_repo(tmp_path, stub={"status": status, "exit": code})
    assert aegis.main(["know_graph", "--json"]) == code
    assert json.loads(capsys.readouterr().out)["status"] == status

# TESTS - explicit indexing (REQ-FUNC-48ff6d8e)


def test_index_passes_liveness_rebuild_and_progress(tmp_path: Path, capfd):
    """REQ-FUNC-48ff6d8e: --watch-stdin, --rebuild, stderr progress, exit from status."""
    agentic, aegis = make_repo(tmp_path, stub={"stderr": "codegraph: extract 1/1\n"})
    assert aegis.main(["know_graph_index", "--rebuild"]) == 0
    argv = calls(agentic)[-1]["argv"]
    assert argv[0] == "index" and "--watch-stdin" in argv and "--rebuild" in argv
    assert "codegraph: extract 1/1" in capfd.readouterr().err
    set_stub(agentic, status="error", exit=1)
    assert aegis.main(["know_graph_index"]) == 1


def test_killing_aegis_closes_the_index_input(tmp_path: Path):
    """REQ-FUNC-48ff6d8e: the plugin sees end-of-file when its launcher dies."""
    agentic, _aegis = make_repo(tmp_path, stub={"wait_eof": True})
    run = subprocess.Popen([sys.executable, str(agentic / "aegis.py"), "know_graph_index"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    marker = agentic / "plugins" / "codegraph" / "eof.txt"
    end = time.monotonic() + 30
    while not calls(agentic) and time.monotonic() < end:
        time.sleep(0.1)
    time.sleep(0.5)
    assert not marker.exists()
    run.kill()
    run.wait(10)
    end = time.monotonic() + 15
    while not marker.exists() and time.monotonic() < end:
        time.sleep(0.1)
    assert marker.exists()

# TESTS - static configuration check (REQ-FUNC-871f7c12)


def test_check_reports_malformed_codegraph_settings(tmp_path: Path):
    """REQ-FUNC-871f7c12: wrong types, ranges and paths are config warnings."""
    _agentic, aegis = make_repo(tmp_path, config=(
        '[codegraph]\nenabled = "yes"\nmax_results = 500\ntimeout_seconds = 0\n'
        'database = "src/x.sqlite"\n'), install=False)
    findings = [f for f in aegis.run_checks(aegis.load_config(), None) if f[1] == "config"]
    messages = " | ".join(f[3] for f in findings)
    assert "[codegraph] enabled should be bool" in messages
    assert "[codegraph] max_results should be 1 through 200" in messages
    assert "[codegraph] timeout_seconds should be at least 1" in messages
    assert "[codegraph] database" in messages
    _agentic, aegis = make_repo(tmp_path / "plain", config="schema = 1\n", install=False)
    assert not [f for f in aegis.run_checks(aegis.load_config(), None)
                if f[1] == "config" and "codegraph" in f[3]]

# END OF FILE
