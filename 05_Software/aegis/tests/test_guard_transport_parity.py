#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_guard_transport_parity.py
@brief Fail-closed and resolution parity checks across the three hook transports.
@details The shared Python guards are spawned by three different transports:
         `.agentic/tools/run_hook.mjs` (Claude Code, Codex, Qwen Code),
         `.opencode/plugins/agentic-guard.mjs`, and
         `.pi/extensions/agentic-guard/hook-bridge.ts`. They must offer the same
         interpreter candidates in the same order and must all treat a guard
         that could not run as a block, never as an allow. These tests fail if
         one transport drifts from the others.
@details The launcher behavior tests execute `run_hook.mjs` through Node and are
         skipped when no Node runtime is available.
"""

# IMPORTS

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = PACKAGE_ROOT / "template"
RUN_HOOK = TEMPLATE / ".agentic" / "tools" / "run_hook.mjs"
OPENCODE_PLUGIN = TEMPLATE / ".opencode" / "plugins" / "agentic-guard.mjs"
PI_BRIDGE = TEMPLATE / ".pi" / "extensions" / "agentic-guard" / "hook-bridge.ts"

TRANSPORTS = (RUN_HOOK, OPENCODE_PLUGIN, PI_BRIDGE)

#: The CLI wrappers. They resolve Python by the same rules as the transports
#: above but in bash and PowerShell, because neither can import the other's
#: code. Five independent implementations of one rule is not duplication that
#: can be refactored away — a bash script cannot call a TypeScript module — so
#: it is duplication that has to be tested for agreement instead.
RUN_SH = TEMPLATE / ".agentic" / "tools" / "run.sh"
RUN_PS1 = TEMPLATE / ".agentic" / "tools" / "run.ps1"

CLI_WRAPPERS = (RUN_SH, RUN_PS1)

#: Blocking hook status shared by the Claude Code, Codex, and Qwen Code
#: protocols. Any other non-zero status is only a non-blocking hook error, so
#: the launcher must normalize every guard failure onto this value.
BLOCKING_EXIT_CODE = 2

NODE = shutil.which("node")
requires_node = pytest.mark.skipif(NODE is None, reason="Node runtime is not available")


# LOCAL HELPERS


def collapse(text: str) -> str:
    """
    @brief      Collapse all runs of whitespace so source comparisons ignore
                per-language formatting.
    @param[in]  text Source text to normalize.
    @return     Text with every whitespace run reduced to one space.
    @exception  None
    """
    return re.sub(r"\s+", " ", text)


def isolated_env(home: Path, **overrides: str) -> dict[str, str]:
    """
    @brief      Build a launcher environment free of the developer's own runtime.
    @param[in]  home Temporary directory used as `WAEGIS_HOME`, with no
                registered `runtime-python` pointer inside it.
    @param[in]  overrides Extra environment entries; an empty value removes the
                variable entirely.
    @return     Environment mapping for `subprocess.run`.
    @details    `AEGIS_PYTHON` and any registered WAEGIS runtime are cleared so a
                test observes the launcher's own resolution rather than whatever
                the host machine happens to have configured.
    @exception  None
    """
    env = dict(os.environ)
    env.pop("AEGIS_PYTHON", None)
    env["WAEGIS_HOME"] = str(home)
    for key, value in overrides.items():
        if value:
            env[key] = value
        else:
            env.pop(key, None)
    return env


def run_launcher(hook: Path, home: Path, **overrides: str) -> subprocess.CompletedProcess[str]:
    """
    @brief      Execute one hook through the shared Node launcher.
    @param[in]  hook Hook script the launcher should spawn.
    @param[in]  home Temporary `WAEGIS_HOME` with no registered runtime.
    @param[in]  overrides Extra environment entries for `isolated_env`.
    @return     Completed launcher process.
    @exception  None
    """
    assert NODE is not None
    return subprocess.run(
        [NODE, str(RUN_HOOK), str(hook)],
        input="{}",
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=isolated_env(home, **overrides),
        check=False,
    )


def powershell_code(path: Path) -> str:
    """
    @brief      Read a PowerShell script with its comments removed.
    @param[in]  path Script to read.
    @return     Source text containing only executable lines.
    @details    Assertions about what a script *does* must not match prose that
                merely names a construct. A comment explaining why `Write-Error`
                is avoided otherwise reads as `Write-Error` being used.
    @exception  None
    """
    text = re.sub(r"<#.*?#>", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def write_hook(directory: Path, name: str, body: str) -> Path:
    """
    @brief      Write one throwaway Python hook used to drive the launcher.
    @param[in]  directory Directory that receives the script.
    @param[in]  name File name for the script.
    @param[in]  body Python source body.
    @return     Path of the written script.
    @exception  None
    """
    path = directory / name
    path.write_text(body, encoding="utf-8", newline="\n")
    return path


# TESTS


def test_every_transport_offers_the_same_interpreter_candidates() -> None:
    """
    @brief      Verify all three transports declare one ordered candidate list.
    @return     None.
    @details    A transport that resolves a different interpreter can reach a
                different decision for identical repository policy. Bare
                `python` on Windows resolves to the Microsoft Store alias stub,
                which exits non-zero with empty stdout, so the ordered list and
                its PATH probe are part of the guard contract.
    @exception  None
    """
    windows_candidates = collapse('[{ command: "py", args: ["-3"] }, { command: "python", args: [] }]')
    posix_candidates = collapse('[{ command: "python3", args: [] }, { command: "python", args: [] }]')

    for transport in TRANSPORTS:
        source = collapse(transport.read_text(encoding="utf-8"))
        assert windows_candidates in source, f"{transport.name} lost the Windows candidate order"
        assert posix_candidates in source, f"{transport.name} lost the POSIX candidate order"
        assert "pathCommandExists" in source, f"{transport.name} does not probe PATH before spawning"


def test_every_transport_treats_an_unavailable_guard_as_a_block() -> None:
    """
    @brief      Verify no transport reports an unrunnable guard as an allow.
    @return     None.
    @details    The guards always exit 0 and answer on stdout, so a non-zero
                exit is always an abnormal failure. Each transport must name
                that case explicitly rather than falling through to its
                allow path.
    @exception  None
    """
    for transport in TRANSPORTS:
        source = transport.read_text(encoding="utf-8")
        assert "AEGIS guard could not run" in source, f"{transport.name} lost the guard-failure reason"
        assert "without a decision" in source, f"{transport.name} lost the non-zero-exit block"
        assert "fail open" not in source.lower(), f"{transport.name} still documents fail-open behavior"


def test_cli_wrappers_resolve_python_in_the_same_order() -> None:
    """
    @brief      Verify both CLI wrappers keep the shared resolution order.
    @return     None.
    @details    `AEGIS_PYTHON`, then the registered WAEGIS runtime, then the
                system launchers — the same order as the three guard
                transports. Asserted by source position rather than mere
                presence, because the order *is* the contract: an explicit
                operator choice must beat a remembered one, and a remembered
                one must beat guessing.
    @exception  None
    """
    for wrapper in CLI_WRAPPERS:
        source = wrapper.read_text(encoding="utf-8")
        explicit = source.index("AEGIS_PYTHON")
        registered = source.index("runtime-python")
        assert explicit < registered, f"{wrapper.name} consults the pointer before AEGIS_PYTHON"
        assert "WAEGIS_HOME" in source, f"{wrapper.name} ignores an explicit WAEGIS_HOME"


def test_cli_wrappers_use_the_windows_runtime_pointer_location() -> None:
    """
    @brief      Verify both CLI wrappers look for the pointer under APPDATA on
                Windows.
    @return     None.
    @details    `run.sh` is a bash script, which on Windows means Git Bash — a
                real and supported way to use this repository. Packaged WAEGIS
                registers its interpreter under `APPDATA` there, so resolving
                only the POSIX `~/.config/waegis` path silently missed it and
                fell through to the system candidates. Bare `python` on a stock
                Windows host is the Microsoft Store alias stub, so that
                fall-through lands on an interpreter that launches, exits
                non-zero and writes nothing.
    @exception  None
    """
    for wrapper in CLI_WRAPPERS:
        source = wrapper.read_text(encoding="utf-8")
        assert "APPDATA" in source, f"{wrapper.name} cannot find the Windows runtime pointer"


def test_cli_wrappers_offer_the_shared_candidate_order() -> None:
    """
    @brief      Verify the wrappers offer the same ordered launchers as the
                guard transports.
    @return     None.
    @details    `py -3` must precede bare `python` on Windows for the Store-stub
                reason above. `run.sh` carries both platform lists because it
                runs on Linux and under Git Bash; `run.ps1` is Windows-only and
                carries only that one.
    @exception  None
    """
    shell = RUN_SH.read_text(encoding="utf-8")
    assert '"py -3" "python"' in shell, "run.sh lost the Windows candidate order"
    assert '"python3" "python"' in shell, "run.sh lost the POSIX candidate order"

    powershell = collapse(RUN_PS1.read_text(encoding="utf-8"))
    assert collapse('@{ Command = "py"; Args = @("-3") },') in powershell
    assert powershell.index('Command = "py"') < powershell.index('Command = "python"')


def test_cli_wrappers_agree_on_the_no_interpreter_exit_code() -> None:
    """
    @brief      Verify both wrappers exit with the same status when no
                interpreter is available.
    @return     None.
    @details    `run.ps1` previously reported this through a plain
                `Write-Error`, which under `$ErrorActionPreference = "Stop"`
                raises a terminating error and ends the script with status 1 —
                never reaching its own `exit`. `run.sh` used an explicit 2. Two
                scripts meant to be equivalent reported the identical condition
                with different statuses.
    @exception  None
    """
    for wrapper in CLI_WRAPPERS:
        source = wrapper.read_text(encoding="utf-8")
        assert f"exit {BLOCKING_EXIT_CODE}" in source, f"{wrapper.name} lost the shared exit status"

    code = powershell_code(RUN_PS1)
    for line in code.splitlines():
        if "Write-Error" in line:
            assert "-ErrorAction Continue" in line, (
                "Write-Error under $ErrorActionPreference = 'Stop' terminates with status 1 "
                "before the explicit exit can run"
            )


def test_run_ps1_avoids_constrained_language_constructs() -> None:
    """
    @brief      Verify `run.ps1` uses no .NET method invocation.
    @return     None.
    @details    A locked-down corporate Windows host commonly runs PowerShell in
                Constrained Language Mode, where a static .NET call such as
                `[Console]::Error.WriteLine(...)` fails with
                `MethodInvocationNotSupportedInConstrainedLanguage`. That is the
                environment where this wrapper is most likely to be reporting a
                missing interpreter in the first place, so the failure path must
                not itself depend on a construct that mode forbids. Cmdlets are
                unrestricted; method invocation is not.
    @exception  None
    """
    code = powershell_code(RUN_PS1)

    assert "[Console]::" not in code, "static .NET calls fail under Constrained Language Mode"
    assert ".WriteLine(" not in code, "method invocation fails under Constrained Language Mode"


@requires_node
def test_launcher_allows_when_the_hook_exits_clean(tmp_path: Path) -> None:
    """
    @brief      Verify a silent, successful hook still allows the tool call.
    @param[in]  tmp_path Temporary directory for the hook and WAEGIS home.
    @return     None.
    @exception  None
    """
    hook = write_hook(tmp_path, "allow_hook.py", "import sys\nsys.stdin.read()\n")

    result = run_launcher(hook, tmp_path, AEGIS_PYTHON=sys.executable)

    assert result.returncode == 0, result.stderr


@requires_node
def test_launcher_forwards_a_deny_decision_unchanged(tmp_path: Path) -> None:
    """
    @brief      Verify the launcher does not rewrite an explicit deny decision.
    @param[in]  tmp_path Temporary directory for the hook and WAEGIS home.
    @return     None.
    @details    A denial is carried on stdout with exit status 0; the host reads
                the JSON, so the launcher must pass both through untouched.
    @exception  None
    """
    hook = write_hook(
        tmp_path,
        "deny_hook.py",
        "import json, sys\n"
        "sys.stdin.read()\n"
        'print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",'
        ' "permissionDecision": "deny", "permissionDecisionReason": "blocked by policy"}}))\n',
    )

    result = run_launcher(hook, tmp_path, AEGIS_PYTHON=sys.executable)

    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout.strip())
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert decision["hookSpecificOutput"]["permissionDecisionReason"] == "blocked by policy"


@requires_node
def test_launcher_blocks_when_the_hook_crashes(tmp_path: Path) -> None:
    """
    @brief      Verify a crashed guard becomes a blocking hook status.
    @param[in]  tmp_path Temporary directory for the hook and WAEGIS home.
    @return     None.
    @details    Exit status 1 is only a *non-blocking* hook error for Claude
                Code, Codex, and Qwen Code, so passing the child's status
                through would let the tool call proceed unchecked. The launcher
                must normalize it to the blocking status instead.
    @exception  None
    """
    hook = write_hook(
        tmp_path,
        "crashing_hook.py",
        "import sys\nsys.stdin.read()\nraise ValueError('broken policy')\n",
    )

    result = run_launcher(hook, tmp_path, AEGIS_PYTHON=sys.executable)

    assert result.returncode == BLOCKING_EXIT_CODE
    assert "broken policy" in result.stderr
    assert "without a decision" in result.stderr


@requires_node
def test_launcher_blocks_when_the_interpreter_cannot_be_launched(tmp_path: Path) -> None:
    """
    @brief      Verify an unlaunchable configured interpreter blocks.
    @param[in]  tmp_path Temporary directory for the hook and WAEGIS home.
    @return     None.
    @exception  None
    """
    hook = write_hook(tmp_path, "unused_hook.py", "import sys\nsys.stdin.read()\n")

    result = run_launcher(
        hook,
        tmp_path,
        AEGIS_PYTHON=str(tmp_path / "no-such-python"),
    )

    assert result.returncode == BLOCKING_EXIT_CODE
    assert "AEGIS guard could not run" in result.stderr


@requires_node
def test_launcher_blocks_when_no_interpreter_is_available(tmp_path: Path) -> None:
    """
    @brief      Verify an empty PATH with no registered runtime blocks.
    @param[in]  tmp_path Temporary directory for the hook and WAEGIS home.
    @return     None.
    @details    This is the case that previously diverged the hardest: the
                launcher blocked while the OpenCode transport allowed.
    @exception  None
    """
    hook = write_hook(tmp_path, "unused_hook.py", "import sys\nsys.stdin.read()\n")

    result = run_launcher(hook, tmp_path, PATH=str(tmp_path / "empty"))

    assert result.returncode == BLOCKING_EXIT_CODE
    assert "no Python runtime was found" in result.stderr


@requires_node
def test_launcher_module_is_importable_without_running(tmp_path: Path) -> None:
    """
    @brief      Verify importing the launcher does not execute or exit.
    @param[in]  tmp_path Temporary directory used as an isolated WAEGIS home.
    @return     None.
    @details    The launcher is the single source of truth for the resolution
                order, so it has to stay importable. Before the entry-point
                guard, importing it exited the host process with the usage
                error because no hook argument was present.
    @exception  None
    """
    assert NODE is not None
    module_url = RUN_HOOK.resolve().as_uri()

    result = subprocess.run(
        [
            NODE,
            "--input-type=module",
            "-e",
            f'const m = await import("{module_url}");'
            ' console.log([typeof m.resolveInterpreter, typeof m.interpreterCandidates].join(","));',
        ],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=isolated_env(tmp_path),
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "function,function"


# END OF FILE
