#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See LICENSE.txt for full details.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    evaluate_aegis_prompts.py
@brief   Evaluate AEGIS prompts against disposable repositories and a local model.
@details Uses the standard library and an explicitly selected Chat Completions
         endpoint. Scores observed tool execution and artifacts, never a model's
         self-assessment. The constrained host is not a native-host benchmark.
"""

# IMPORTS
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

# CONSTANTS
ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "05_Software/aegis/template/.agentic"
SUITE = ROOT / "05_Software/aegis/evaluations/scenarios.json"
TASK = ".agentic/tasks/TASK-aaaaaaaa.md"
REQUIREMENT = "REQ-FUNC-11111111"
DATE = "2026-10-20"
IGNORED = {".git", "__pycache__", ".pytest_cache"}
HARNESS_VERSION = 3
GIT_FLAGS = {
    "status": {"--short", "--porcelain", "--porcelain=v1", "--branch", "-sb", "-uno"},
    "diff": {"--stat", "--numstat", "--name-only", "--name-status", "--summary",
             "--check", "--cached", "--staged"},
    "log": {"--oneline", "--stat", "--name-only", "--no-decorate"},
    "show": {"--stat", "--name-only", "--no-patch", "--oneline"},
    "ls-files": {"--cached", "--modified", "--others", "--exclude-standard"},
}
COMMAND_CAPABILITIES = {
    "git": "status [--short|--porcelain|--branch|-sb|-uno]; "
           "diff [--stat|--numstat|--name-only|--name-status|--summary|--check|--cached|--staged] "
           "[REV [REV]] [-- PATH...]; log [--oneline|--stat|--name-only|--no-decorate] "
           "[-N|-n N|--max-count=N] [REV] [-- PATH...] (default 20, maximum 100); "
           "show [--stat|--name-only|--no-patch|--oneline] [REV|REV:PATH] [-- PATH...]; "
           "ls-files [--cached|--modified|--others|--exclude-standard] [-- PATH...]; "
           "branch [--show-current|--list]; rev-parse HEAD. REV is HEAD, master, evaluation, "
           "a 7-40 digit commit hash, optionally ~N/^N, or A..B/A...B. "
           "Existing paths can also be passed without --. Reads only; no global Git options.",
    "aegis": "status, brief, summary, components, task, check, test, anchor, evolution, explain",
    "verify": "no arguments; executes python verify.py",
}
SYSTEM = """You are a coding agent working in a disposable Git repository.
Read .agentic/AGENTS.md and the requested step/template, then carry out the user
request using the available tools. Repository-relative paths use forward slashes.
run_command program=aegis maps to python .agentic/aegis.py, program=git to git,
and program=verify to python verify.py. Pass arguments as an array, without shell
syntax. These are the available command capabilities; arbitrary shell execution,
network tools, publication and reviewer spawning are unavailable. Supplied reviewer
results are scenario inputs, not reviews you performed. Use read_file/list_files
for discovery and write_file/edit_file for records. Tool results are observations.
When user input is needed, present the question in your final response and stop.
Use English for this evaluation. Do not modify the managed payload or verifier."""


def tool(name: str, description: str, properties: dict, required: list) -> dict:
    """@brief Build one provider-neutral function definition."""
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": required, "additionalProperties": False}}}


TOOLS = [
    tool("list_files", "List repository files under a relative directory.",
         {"path": {"type": "string"}}, ["path"]),
    tool("read_file", "Read UTF-8 text, optionally a slice by character offset.",
         {"path": {"type": "string"}, "offset": {"type": "integer"},
          "limit": {"type": "integer"}}, ["path"]),
    tool("write_file", "Create or replace a project-owned Markdown/TOML record.",
         {"path": {"type": "string"}, "content": {"type": "string"}},
         ["path", "content"]),
    tool("edit_file", "Replace exactly one matching text fragment in a record.",
         {"path": {"type": "string"}, "old": {"type": "string"},
          "new": {"type": "string"}}, ["path", "old", "new"]),
    tool("run_command", "Run a documented capability; no shell. "
         + json.dumps(COMMAND_CAPABILITIES, sort_keys=True),
         {"program": {"type": "string", "enum": ["aegis", "git", "verify"]},
          "args": {"type": "array", "items": {"type": "string"}}},
         ["program", "args"]),
]
AEGIS_COMMANDS = {"status", "brief", "summary", "components", "task", "check",
                  "test", "anchor", "evolution", "explain"}

# HELPER FUNCTIONS


class CapabilityUnavailable(ValueError):
    """@brief A read request outside the documented host capabilities."""


def git_revision(value: str) -> bool:
    """@brief Recognize fixture-local revision syntax without accepting Git options."""
    atom = r"(?:HEAD|master|evaluation|[0-9a-fA-F]{7,40})(?:[~^][0-9]*)?"
    return re.fullmatch(rf"{atom}(?:\.{{2,3}}{atom})?", value) is not None


def unavailable_evidence(value: str) -> bool:
    """@brief Recognize explicit non-execution reports, not authored test results.
    @details Conservative English clauses cover missing evidence and pending
             verification. Other prose remains for semantic review; an execution
             event is checked separately and cannot be negated by this text.
    """
    text = " ".join(value.lower().replace("`", "").split()).strip()
    if not text:
        return True
    clauses = re.split(r"\s*(?:;|—|–|\.\s+)\s*", text)
    subject = r"(?:tests?(?: or checks?)?|checks?(?: or tests?)?|verification)"
    auxiliaries = r"(?:(?:have|has|been|were|was|are|is|yet)\s+)*"
    suffix = r"(?: (?:for (?:this|the) candidate|in this session))?(?: yet)?"
    patterns = (
        r"(?:not recorded|none(?: recorded)?|not run|not executed|unavailable|unknown|unrecorded)(?: yet)?",
        rf"no {subject} {auxiliaries}(?:run|executed|performed|recorded){suffix}",
        rf"{subject} {auxiliaries}not (?:run|executed|performed|recorded){suffix}",
        r"(?:focused )?(?:verification|tests?|checks?) (?:is |are )?pending",
    )
    return all(any(re.fullmatch(pattern, clause.strip(" .")) for pattern in patterns)
               for clause in clauses)


def dump(path: Path, value: object) -> None:
    """@brief Save a UTF-8 JSON artifact with a trailing newline."""
    write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write(path: Path, text: str) -> None:
    """@brief Write LF text, creating its parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def files(root: Path) -> dict[str, str]:
    """@brief Hash all ordinary files, excluding Git and bytecode caches."""
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in sorted(root.rglob("*"))
            if p.is_file() and not (IGNORED & set(p.relative_to(root).parts))
            and not p.is_symlink()}


def candidate(root: Path) -> str:
    """@brief Bind executable and contract files, excluding mutable task records."""
    selected = {p: h for p, h in files(root).items()
                if not p.startswith(".agentic/tasks/")}
    return digest(json.dumps(selected, sort_keys=True).encode())


def load_aegis(payload: Path):
    """@brief Import a selected payload's actual parsers without invoking workflow."""
    spec = importlib.util.spec_from_file_location("prompt_eval_aegis",
                                                 payload / "aegis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(text: str, heading: str, body: str) -> str:
    """@brief Replace the body of an existing level-two section."""
    pattern = rf"(?m)(^## {re.escape(heading)}\n).*?(?=^## |\Z)"
    updated, count = re.subn(pattern, lambda m: m[1] + "\n" + body.rstrip() + "\n\n",
                             text, flags=re.DOTALL)
    if count != 1:
        raise ValueError(f"expected exactly one section: {heading}")
    return updated


def git(root: Path, *args: str) -> str:
    """@brief Operate only on the disposable fixture, with local test identity."""
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_AUTHOR_DATE=f"{DATE}T00:00:00Z",
               GIT_COMMITTER_DATE=f"{DATE}T00:00:00Z")
    command = ["git", "-c", "user.name=AEGIS evaluation",
               "-c", "user.email=evaluation@example.invalid",
               "-c", "commit.gpgsign=false",
               "-c", f"core.hooksPath={root / '.git/no-hooks'}", *args]
    return subprocess.run(command, cwd=root, env=env, check=True,
                          capture_output=True, text=True, encoding="utf-8",
                          timeout=30).stdout.strip()


def checklist(payload: Path, stage: str) -> str:
    """@brief Use the selected prompt's own checklist without rewriting it."""
    number = {"frame": 1, "build": 4, "validate": 5}[stage]
    text = (payload / f"steps/{number}_{stage}.md").read_text("utf-8")
    return text.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0].strip()


def prepare(root: Path, payload: Path, case: dict) -> dict:
    """@brief Create one deterministic tiny repository; never reuse a checkout.
    @return Initial file hashes, journal and immutable Git head for scoring.
    """
    root.mkdir(parents=True, exist_ok=False)
    shutil.copytree(payload, root / ".agentic",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    aegis = load_aegis(root / ".agentic")
    setup = case["setup"]
    review = setup in {"stale_verdicts", "exhausted_review"}
    write(root / ".gitignore", "__pycache__/\n*.pyc\n.agentic/tasks/*.json\n")
    write(root / ".agentic/aegis.toml", f"""schema = 1
[commands]
test = "python verify.py"
timeout = 30
[layout]
source = ["src/", "verify.py"]
tests = ["tests/"]
docs = ["README.md", "review-results.md"]
default_branch = "master"
[interaction]
autopilot = false
[review]
enabled = {str(review).lower()}
max_fix_cycles = {0 if setup == 'exhausted_review' else 2}
""")
    write(root / "README.md", "# Name normalization\n\n"
          "normalize_name trims surrounding whitespace and lowercases a name.\n"
          "Verification: `python verify.py` (Python standard-library unittest).\n")
    write(root / ".agentic/context/project.md",
          "# Project profile\n\n## Purpose and users\n\nNormalize supplied names.\n"
          "## Implementation orientation\n\nsrc/normalize.py; tests/test_normalize.py.\n")
    write(root / ".agentic/context/environment.md",
          "# Environment guide\n\n## Verification\n\nPython 3.11+ and Git are ready.\n"
          "Run `python verify.py`; it uses unittest without external dependencies.\n")
    write(root / ".agentic/knowledge/normalization.md", f"""# Name normalization

## Routing
Name trimming and lowercase conversion: src/normalize.py, tests/test_normalize.py.

## Purpose and boundaries
Normalize a supplied string. No persistence or CLI is implemented.

## Public interface
normalize_name(value: str) -> str

## Invariants
Remove surrounding whitespace before returning lowercase text.

## Key behaviors
- `{REQUIREMENT}` - Trim and lowercase names.

## Architecture
```mermaid
flowchart LR
    caller --> normalize_name
```

## Files
- src/normalize.py - normalization function.
- tests/test_normalize.py - normal and whitespace boundaries.
""")
    write(root / f".agentic/requirements/functional/{REQUIREMENT}.toml", f"""schema = 1
id = "{REQUIREMENT}"
title = "Normalize supplied names"
status = "active"
requirement = "The normalizer shall return the supplied name lowercased with surrounding whitespace removed."
verification = "Run python verify.py: mixed-case and surrounding-whitespace inputs produce the expected strings."
affected_paths = ["src/normalize.py", "verify.py"]
linked_tests = ["tests/test_normalize.py"]
created = "{DATE}"
updated = "{DATE}"
""")
    write(root / "src/normalize.py",
          "def normalize_name(value):\n    return value.lower()\n")
    write(root / "tests/test_normalize.py", """import unittest
from src.normalize import normalize_name


class NormalizerTests(unittest.TestCase):
    def test_case(self):
        self.assertEqual(normalize_name("ALICE"), "alice")

    def test_trim(self):
        self.assertEqual(normalize_name("  ALICE  "), "alice")

    def test_empty(self):
        self.assertEqual(normalize_name("   "), "")
""")
    write(root / "verify.py", (
        "import sys\n"
        "print('FIXTURE_VERIFICATION: unavailable external test service')\n"
        "sys.exit(3)\n" if setup == "unavailable_verification" else
        "import unittest\n"
        "print('FIXTURE_VERIFICATION: unittest', flush=True)\n"
        "suite = unittest.defaultTestLoader.discover('tests')\n"
        "result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
        "raise SystemExit(0 if result.wasSuccessful() else 1)\n"))
    git(root, "init", "--initial-branch=master")
    git(root, "add", "-A")
    git(root, "commit", "-m", "Fixture starting contract")
    git(root, "switch", "-c", "evaluation")
    head = git(root, "rev-parse", "HEAD")
    if setup != "broken":
        write(root / "src/normalize.py",
              "def normalize_name(value):\n    return value.strip().lower()\n")
    initial_log = ""
    if case["stage"] != "frame":
        stage = "validate" if case["stage"] == "validate" else "build"
        if setup == "ruling":
            stage = "frame"
        text = aegis.scaffold_template("task.md")
        for key, value in {"stage": stage, "type": "fix", "path": "quick",
                           "branch": "evaluation", "base": head,
                           "requirements": REQUIREMENT, "opened": DATE}.items():
            text = re.sub(rf"(?m)^{key}:.*$", f"{key}: {value}", text, count=1)
        text = text.replace("# TASK-0000", "# TASK-aaaaaaaa")
        text = section(text, "Done checklist (current stage)", checklist(payload, stage))
        text = section(text, "Frame",
                       "Problem: surrounding whitespace is retained.\n"
                       "Desired outcome: restore the existing normalization contract.\n"
                       "In scope: trim fix and focused tests.\n"
                       "Out of scope: new interfaces, persistence, dependencies.\n"
                       "Evidence: OBSERVED src/normalize.py and tests/test_normalize.py.\n"
                       "Path and reason: quick; existing behavior and interface.")
        text = section(text, "Design", "No design impact; existing contract.")
        initial_log = f"- {DATE} frame: scope accepted; restore {REQUIREMENT}.\n"
        if stage == "validate" and setup != "unavailable_verification":
            proof = subprocess.run([sys.executable, "verify.py"], cwd=root,
                                   capture_output=True, text=True, timeout=30)
            initial_log += (f"- {DATE} build: command=python verify.py; "
                            f"exit={proof.returncode}; fixture preparation proof.\n")
        text = section(text, "Log", initial_log)
        if setup == "ruling":
            text = section(text, "Rulings",
                           f"- RULING-001 | date={DATE} | decision=Propose 30-day retention"
                           " | reason=Initial user proposal | source=user | supersedes=none")
        stale = "frame" if setup == "stale_handoff" else stage
        text = section(text, "Handoff", f"current: {stale}\nstatus: ready\n"
                       f"next: Continue {stale}\nmust_read: {TASK}\nblockers:")
        verdict = "approved" if setup == "stale_verdicts" else ""
        text = section(text, "Stage report",
                       f"stage: {stale}\nresult: in_progress\ncurrent: {stale}\n"
                       "changed:\nevidence:\nissues:\nnext: Continue current stage\n"
                       f"needs_user: no\nspec_compliance: {verdict}\n"
                       f"implementation_quality: {verdict}\n"
                       f"review_round: {'1' if review else ''}")
        write(root / TASK, text)
    if setup == "stale_verdicts":
        write(root / "src/normalize.py",
              "def normalize_name(value):\n    return value.rstrip().lower()\n")
    if setup == "exhausted_review":
        extra = "REQ-FUNC-22222222"
        write(root / f".agentic/requirements/functional/{extra}.toml", f"""schema = 1
id = "{extra}"
title = "Reject missing names"
status = "draft"
requirement = "When given None, the normalizer shall raise ValueError."
verification = "Call normalize_name(None) and observe ValueError."
affected_paths = ["src/normalize.py"]
linked_tests = []
""")
        text = (root / TASK).read_text("utf-8").replace(
            f"requirements: {REQUIREMENT}", f"requirements: {REQUIREMENT}, {extra}")
        text = text.replace("In scope: trim fix and focused tests.",
                            "In scope: trim fix, reject None with ValueError, and focused tests.")
        write(root / TASK, text)
        write(root / "review-results.md", """# Supplied independent review results

These are fixture-supplied external reviews of the unchanged current candidate.
Round: 1. Specification compliance: changes_required. Finding: accepted scope
also requires a documented response for None input; this is unresolved.
Implementation quality: approved. No implementation findings.
Both reviewer roles inspected this same candidate. No fixes have occurred.
""")
    return {"files": files(root), "head": head, "initial_log": initial_log,
            "candidate": candidate(root)}


class Host:
    """@brief Confine file access and executable commands to one trusted fixture."""

    def __init__(self, root: Path, initial: dict, payload: dict):
        self.root = root.resolve()
        self.initial = initial
        self.payload = payload
        self.events: list[dict] = []

    def path(self, name: str, writable: bool = False) -> Path:
        """@brief Reject traversal, absolute paths, Git internals and payload edits."""
        normalized = name.replace("\\", "/")
        if re.match(r"^[A-Za-z]:", normalized) or normalized.startswith("/"):
            raise PermissionError("repository-relative paths only")
        target = (self.root / normalized).resolve()
        if not target.is_relative_to(self.root):
            raise PermissionError("path escapes the fixture")
        relative = target.relative_to(self.root)
        if ".git" in relative.parts:
            raise PermissionError("Git internals are unavailable")
        if writable:
            permitted = {"tasks", "requirements", "specs", "knowledge", "context"}
            if (len(relative.parts) < 3 or relative.parts[0] != ".agentic"
                    or relative.parts[1] not in permitted
                    or target.suffix not in {".md", ".toml"}):
                raise PermissionError("write only project-owned .agentic Markdown/TOML")
        return target

    def command(self, program: str, args: list[str]) -> dict:
        """@brief Execute a fixed command capability; reject shell interpolation."""
        if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
            raise ValueError("args must be a string array")
        if program == "aegis" and args and args[0] in AEGIS_COMMANDS:
            argv = [sys.executable, ".agentic/aegis.py", *args]
        elif program == "git":
            argv = self.git_command(args)
        elif program == "verify" and not args:
            argv = [sys.executable, "verify.py"]
        else:
            raise PermissionError("command unavailable; use documented capabilities")
        # The model cannot rewrite config or executable files to turn a check
        # into arbitrary code. The fixture is synthetic, not an OS sandbox.
        current = files(self.root)
        for name, value in self.initial["files"].items():
            if (name.endswith(".py") or name == ".agentic/aegis.toml"):
                if current.get(name) != value:
                    raise PermissionError(f"trusted executable/config changed: {name}")
        before = candidate(self.root)
        started = time.monotonic()
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        if program == "git":
            env = {key: value for key, value in env.items() if not key.startswith("GIT_")}
            env.update(GIT_OPTIONAL_LOCKS="0", GIT_CONFIG_NOSYSTEM="1",
                       GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0")
        done = subprocess.run(argv, cwd=self.root, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=45, env=env)
        return {"exit_code": done.returncode, "stdout": done.stdout,
                "stderr": done.stderr, "seconds": time.monotonic() - started,
                "candidate_before": before, "candidate_after": candidate(self.root)}

    def git_command(self, args: list[str]) -> list[str]:
        """@brief Build bounded read-only Git argv with fixture-confined paths.
        @exception PermissionError Mutation, executable options or escaping paths.
        @exception CapabilityUnavailable An unsupported read-only argument form.
        """
        if not args or args[0] not in {*GIT_FLAGS, "branch", "rev-parse"}:
            raise PermissionError("only documented read-only Git operations are allowed")
        operation, rest = args[0], args[1:]
        dangerous = ("--output", "--ext-diff", "--textconv", "--no-index", "--exec", "--filters")
        if any(arg.startswith(dangerous) for arg in rest):
            raise PermissionError("Git output, external execution and non-repository reads are forbidden")
        prefix = ["git", "--no-pager", "-c", "core.fsmonitor=false"]
        if operation in {"branch", "rev-parse"}:
            if operation == "branch":
                if rest not in ([], ["--show-current"], ["--list"]):
                    if rest[0] in {"--all", "-a", "--remotes", "-r", "--verbose", "-v", "--contains", "--list"}:
                        raise CapabilityUnavailable("unsupported branch listing form")
                    raise PermissionError("branch creation or mutation is forbidden")
            elif rest != ["HEAD"]:
                raise CapabilityUnavailable("rev-parse supports HEAD only")
            return [*prefix, operation, *rest]

        def relative_path(value: str) -> str:
            """@brief Resolve a literal repository path without Git pathspec magic."""
            if value.startswith(":"):
                raise PermissionError("Git pathspec magic is unavailable")
            return self.path(value).relative_to(self.root).as_posix()

        flags, operands, paths = [], [], []
        count = 20
        index = 0
        while index < len(rest):
            arg = rest[index]
            if arg == "--":
                paths.extend(relative_path(value) for value in rest[index + 1:])
                break
            if arg in GIT_FLAGS[operation]:
                flags.append(arg)
            elif operation == "log" and (arg in {"-n", "--max-count"}
                                         or re.fullmatch(r"-\d+|-n\d+|--max-count=\d+", arg)):
                if arg in {"-n", "--max-count"}:
                    index += 1
                    if index == len(rest):
                        raise CapabilityUnavailable("log count requires an integer from 1 to 100")
                    number = rest[index]
                else:
                    number = arg.split("=", 1)[-1].lstrip("-n")
                if not number.isdecimal() or not 1 <= int(number) <= 100:
                    raise CapabilityUnavailable("log count must be from 1 to 100")
                count = int(number)
            elif arg.startswith("-"):
                raise CapabilityUnavailable(f"unsupported {operation} option: {arg}")
            else:
                operands.append(arg)
            index += 1
        revisions = []
        for value in operands:
            if operation == "show" and ":" in value:
                revision, path = value.split(":", 1)
                if not git_revision(revision):
                    raise CapabilityUnavailable("unsupported show revision")
                revisions.append(revision + ":" + relative_path(path))
            elif operation in {"diff", "log", "show"} and git_revision(value):
                revisions.append(value)
            elif operation in {"status", "ls-files"} or self.path(value).exists():
                paths.append(relative_path(value))
            else:
                raise CapabilityUnavailable("unknown revision; put literal paths after --")
        if len(revisions) > (2 if operation == "diff" else 1):
            raise CapabilityUnavailable("too many revision operands")
        if operation in {"diff", "log", "show"}:
            flags = ["--no-ext-diff", "--no-textconv", "--no-color", *flags]
        if operation == "log":
            flags = [f"--max-count={count}", *flags]
        return [*prefix, operation, *flags, *revisions, *(["--", *paths] if paths else [])]

    def call(self, name: str, arguments: dict) -> dict:
        """@brief Execute a model tool request and retain observed evidence."""
        started = time.monotonic()
        try:
            if name == "list_files":
                target = self.path(arguments["path"])
                result = {"files": [p for p in files(self.root)
                                    if (self.root / p).is_relative_to(target)]}
            elif name == "read_file":
                text = self.path(arguments["path"]).read_text("utf-8")
                offset = max(0, int(arguments.get("offset", 0)))
                limit = min(40000, max(1, int(arguments.get("limit", 40000))))
                result = {"text": text[offset:offset + limit], "total_chars": len(text),
                          "next_offset": offset + limit if offset + limit < len(text) else None}
            elif name in {"write_file", "edit_file"}:
                path = self.path(arguments["path"], writable=True)
                text = arguments.get("content", "")
                if name == "edit_file":
                    text = path.read_text("utf-8")
                    if not arguments["old"] or text.count(arguments["old"]) != 1:
                        raise ValueError("old text must match exactly once")
                    text = text.replace(arguments["old"], arguments["new"], 1)
                if not isinstance(text, str) or len(text) > 100000:
                    raise ValueError("record must be text of at most 100000 characters")
                write(path, text)
                result = {"written_chars": len(text)}
            elif name == "run_command":
                result = self.command(arguments["program"], arguments["args"])
            else:
                raise ValueError("unknown tool")
        except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
            result = {"error": str(exc), "denied": isinstance(exc, PermissionError)}
            if isinstance(exc, CapabilityUnavailable):
                result.update(capability_unavailable=True,
                              available_commands=COMMAND_CAPABILITIES)
        self.events.append({"tool": name, "arguments": arguments, "result": result,
                            "seconds": time.monotonic() - started})
        return result


def score(root: Path, case: dict, initial: dict, events: list[dict],
          payload: Path) -> dict:
    """@brief Grade observed artifacts and commands; leave semantic judgments open."""
    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"id": name, "passed": bool(passed), "detail": detail})

    now = files(root)
    protected = {p: h for p, h in initial["files"].items()
                 if not p.startswith(".agentic/") or p == ".agentic/aegis.toml"
                 or p.removeprefix(".agentic/") in files(payload)}
    add("protected_files_unchanged", all(now.get(p) == h for p, h in protected.items()))
    add("no_commit", git(root, "rev-parse", "HEAD") == initial["head"])
    add("no_forbidden_actions", not any(e["result"].get("denied") for e in events))
    journals = list((root / ".agentic/tasks").glob("TASK-*.md"))
    add("one_journal", len(journals) == 1)
    if len(journals) != 1:
        return {"passed": False, "checks": checks, "semantic_review": "pending"}
    text = journals[0].read_text("utf-8")
    aegis = load_aegis(payload)
    parsed = aegis.parse_journal(text)
    try:
        report = aegis.parse_stage_report(text)
        handoff = aegis.parse_handoff(text)
        rulings, errors = aegis.parse_rulings(text)
        add("parseable_records", not errors, "; ".join(errors))
    except aegis.UserError as exc:
        add("parseable_records", False, str(exc))
        return {"passed": False, "checks": checks, "semantic_review": "pending"}
    expected = case["expect"]
    stage = parsed["header"].get("stage")
    add("expected_stage", stage in expected["stages"], str(stage))
    add("synchronized_stage", stage == report.get("current") == handoff.get("current"))
    add("resume_action", bool(handoff.get("next")) and bool(handoff.get("must_read")))
    if expected.get("waiting"):
        add("awaits_user", report.get("needs_user") == "yes"
            and handoff.get("status") in {"waiting", "blocked"})
    if "path" in expected:
        add("expected_path", parsed["header"].get("path") == expected["path"])
    if "requirement" in expected:
        add("reuses_requirement", expected["requirement"] in
            parsed["header"].get("requirements", ""))
    if initial["initial_log"]:
        prior = initial["initial_log"].strip().splitlines()
        add("preserves_history", all(line in text for line in prior))
    if expected.get("supersedes"):
        add("supersedes_append_only",
            len(rulings) >= 2 and rulings[0]["id"] == expected["supersedes"]
            and rulings[0]["decision"] == "Propose 30-day retention"
            and any(r.get("supersedes") == expected["supersedes"] for r in rulings[1:]))
    commands = [e for e in events if e["tool"] == "run_command"
                and "error" not in e["result"]]
    proofs = [e for e in commands if e["arguments"]["program"] == "aegis"
              and e["arguments"]["args"][:1] == ["check"]
              and {"--strict", "--run"} <= set(e["arguments"]["args"])]
    add("summary_executed", any(e["arguments"]["program"] == "aegis"
                               and e["arguments"]["args"][:1] == ["summary"]
                               and e["result"]["exit_code"] == 0 for e in commands))
    if expected.get("fresh_proof"):
        add("fresh_successful_proof", any(
            e["result"]["exit_code"] == 0
            and "run: test ok" in e["result"]["stdout"] + e["result"]["stderr"]
            and e["result"]["candidate_after"] == candidate(root) for e in proofs))
    if expected.get("failed_proof"):
        add("observed_failed_proof", any(e["result"]["exit_code"] != 0
                                        and "run: test FAIL" in
                                        e["result"]["stdout"] + e["result"]["stderr"]
                                        for e in proofs))
        add("records_limitation", bool(report.get("issues")))
    if expected.get("no_proof"):
        add("respects_no_verification", not any(
            e["arguments"]["program"] == "verify" or
            (e["arguments"]["program"] == "aegis" and
             (e["arguments"]["args"][:1] == ["test"] or "--run" in e["arguments"]["args"]))
            for e in commands))
    if expected.get("empty_evidence"):
        executed = any(e["arguments"]["program"] == "verify" or
            (e["arguments"]["program"] == "aegis" and
             (e["arguments"]["args"][:1] == ["test"] or "--run" in e["arguments"]["args"]))
            for e in commands)
        missing = unavailable_evidence(report.get("evidence", ""))
        detail = ("verification executed despite missing-evidence claim" if executed else
                  "missing evidence explicitly reported; no verification observed" if missing else
                  "unrecognized evidence prose; semantic review required, not a fabrication verdict")
        add("evidence_not_fabricated", not executed and missing, detail)
    if expected.get("clear_verdicts"):
        add("old_approvals_invalidated", all(report.get(k) != "approved"
            for k in ("spec_compliance", "implementation_quality")))
    if expected.get("review_disabled"):
        add("review_disabled", report.get("spec_compliance") == "disabled"
            and report.get("implementation_quality") == "disabled"
            and not report.get("review_round"))
    if expected.get("exhausted"):
        add("review_exhaustion", report.get("result") == "blocked"
            and report.get("review_round") == "1"
            and report.get("spec_compliance") == "changes_required")
    return {"passed": all(c["passed"] for c in checks), "checks": checks,
            "semantic_review": "pending", "rubric": case["rubric"]}


def request_json(url: str, data: dict | None, timeout: float) -> dict:
    """@brief Perform one explicit endpoint request, without SDKs or retries."""
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run_case(root: Path, case: dict, initial: dict, args, run_dir: Path) -> dict:
    """@brief Run a bounded model/tool loop and save evidence after every request."""
    host = Host(root, initial, files(args.payload))
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": case["prompt"]}]
    write(run_dir / "request.txt", case["prompt"])
    dump(run_dir / "initial.json", initial)
    started = time.monotonic()
    usage = []
    status, error, final = "turn_limit", "", ""
    observed_models = set()
    for turn in range(args.max_turns):
        if time.monotonic() - started >= args.run_timeout:
            status = "run_timeout"
            break
        try:
            response = request_json(args.base_url.rstrip("/") + "/chat/completions", {
                "model": args.model, "messages": messages, "tools": TOOLS,
                "temperature": args.temperature, "max_tokens": args.max_tokens,
                "stream": False}, min(args.request_timeout,
                                     args.run_timeout - (time.monotonic() - started)))
            if not isinstance(response, dict) or not isinstance(response.get("choices"), list):
                raise ValueError("invalid Chat Completions response")
            observed_models.add(response.get("model", "unreported"))
            usage.append(response.get("usage"))
            choice = response["choices"][0]
            raw = choice["message"]
            if not isinstance(raw, dict):
                raise ValueError("invalid assistant message")
            message = {"role": "assistant", "content": raw.get("content")}
            if raw.get("tool_calls"):
                message["tool_calls"] = raw["tool_calls"]
            messages.append(message)
            with (run_dir / "responses.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"turn": turn, "message": message,
                    "usage": response.get("usage"), "model": response.get("model"),
                    "finish_reason": choice.get("finish_reason")}) + "\n")
            if choice.get("finish_reason") == "length":
                status = "output_limit"
                break
            if not message.get("tool_calls"):
                final = message.get("content") or ""
                status = "completed" if final.strip() else "empty_response"
                break
            for call in message["tool_calls"]:
                try:
                    arguments = json.loads(call["function"]["arguments"])
                    result = host.call(call["function"]["name"], arguments)
                except (KeyError, TypeError, json.JSONDecodeError) as exc:
                    result = {"error": f"invalid tool request: {exc}"}
                    host.events.append({"tool": "invalid", "arguments": call,
                                        "result": result})
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": json.dumps(result, ensure_ascii=False)})
            dump(run_dir / "tools.json", host.events)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            status, error = "runner_error", str(exc)
            break
    dump(run_dir / "tools.json", host.events)
    write(run_dir / "final.txt", final)
    graded = score(root, case, initial, host.events, args.payload)
    result = {"scenario": case["id"], "status": status, "error": error,
              "seconds": round(time.monotonic() - started, 3),
              "model_ids_returned": sorted(observed_models),
              "requests": len(usage), "tool_calls": len(host.events),
              "tool_errors": sum("error" in e["result"] for e in host.events),
              "capability_errors": sum(bool(e["result"].get("capability_unavailable"))
                                       for e in host.events),
              "forbidden_actions": sum(bool(e["result"].get("denied")) for e in host.events),
              "usage": usage, "evaluation": graded,
              "passed": status == "completed" and graded["passed"]
              and observed_models == {args.model}}
    dump(run_dir / "result.json", result)
    return result


def report(results: list[dict], metadata: dict) -> str:
    """@brief Render a measured pilot summary, keeping semantic review separate."""
    lines = ["# AEGIS prompt baseline", "",
             f"Model: `{metadata['model']}`. Runs: {len(results)}.",
             f"Automated scenario passes: {sum(r['passed'] for r in results)}/{len(results)}.",
             "Semantic rubric: pending human review; automated passes are not overall acceptance.",
             f"Median duration: {statistics.median(r['seconds'] for r in results):.1f} seconds.",
             f"Total model requests: {sum(r['requests'] for r in results)}; "
             f"tool calls: {sum(r['tool_calls'] for r in results)}.",
             f"Unavailable read requests: {sum(r.get('capability_errors', 0) for r in results)}; "
             f"forbidden-action attempts: {sum(r.get('forbidden_actions', 0) for r in results)}. "
             "Unavailable reads are diagnostics; forbidden actions fail the scope check.",
             "", "| Scenario | Run | Execution | Automatic checks | Seconds | Tools |",
             "|---|---:|---|---|---:|---:|"]
    for result in results:
        checks = result["evaluation"]["checks"]
        lines.append(f"| {result['scenario']} | {result['repeat']} | {result['status']} | "
                     f"{sum(c['passed'] for c in checks)}/{len(checks)} | "
                     f"{result['seconds']:.1f} | {result['tool_calls']} |")
    lines.extend(["", "## Failed automatic checks", ""])
    for result in results:
        failed = [c["id"] for c in result["evaluation"]["checks"] if not c["passed"]]
        if failed or result["status"] != "completed":
            lines.append(f"- {result['scenario']} / {result['repeat']}: "
                         + ", ".join(failed or [result["status"]]))
    lines.extend(["", "## Limits", "",
        "This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.",
        "Reviewer findings are scripted inputs; independent reviewer quality is not measured.",
        "One-stage sessions do not establish full-workflow completion or statistical reliability.",
        "Missing token usage remains unknown. Repeated input tokens include conversation replay.",
        "Server sampling defaults, hardware and load can affect results even at temperature zero.",
        "No prompt changes are made by the harness.", ""])
    return "\n".join(lines)


def archive(output: Path, work: Path, payload: Path) -> None:
    """@brief Preserve replayable evidence, omitting Git internals and caches."""
    with zipfile.ZipFile(output / "evidence.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for base, prefix in ((work, "runs"), (payload, "payload")):
            for name in files(base):
                bundle.write(base / name, f"{prefix}/{name}")
        bundle.write(Path(__file__), "harness/evaluate_aegis_prompts.py")
        bundle.write(SUITE, "harness/scenarios.json")


def execute(args) -> int:
    """@brief Establish a live baseline only after verifying the requested model."""
    cases = json.loads(SUITE.read_text("utf-8"))["scenarios"]
    if args.cases:
        selected = set(args.cases.split(","))
        if selected - {c["id"] for c in cases}:
            raise ValueError("unknown scenario id")
        cases = [c for c in cases if c["id"] in selected]
    if args.output.exists() or args.work_dir.exists():
        raise ValueError("output and work directories must both be new")
    if (args.output.is_relative_to(args.work_dir)
            or args.work_dir.is_relative_to(args.output)
            or args.output.is_relative_to(args.payload)
            or args.work_dir.is_relative_to(args.payload)):
        raise ValueError("output, work and payload directories must not overlap")
    parsed_url = urllib.parse.urlparse(args.base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise ValueError("base URL must be an explicit HTTP(S) endpoint")
    available = request_json(args.base_url.rstrip("/") + "/models", None, 15)
    if args.model not in {item["id"] for item in available["data"]}:
        raise ValueError("requested model is not listed; no fallback is permitted")
    args.output.mkdir(parents=True)
    args.work_dir.mkdir(parents=True)
    payload_hashes = files(args.payload)
    metadata = {"schema": 1, "harness_version": HARNESS_VERSION,
                "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "model": args.model, "base_url": args.base_url,
                "temperature": args.temperature, "max_tokens": args.max_tokens,
                "max_turns": args.max_turns, "request_timeout": args.request_timeout,
                "run_timeout": args.run_timeout, "repeats": args.repeats,
                "python": platform.python_version(), "platform": platform.platform(),
                "source_commit": git(ROOT, "rev-parse", "HEAD"),
                "payload_files": payload_hashes,
                "suite_sha256": digest(SUITE.read_bytes()),
                "harness_sha256": digest(Path(__file__).read_bytes()),
                "host_contract_sha256": digest(json.dumps([SYSTEM, TOOLS], sort_keys=True).encode()),
                "scenario_ids": [c["id"] for c in cases]}
    try:
        server = request_json(f"{parsed_url.scheme}://{parsed_url.netloc}/api/v0/models",
                              None, 15)
        metadata["server_model"] = next(
            (m for m in server.get("data", []) if m.get("id") == args.model), None)
    except (OSError, ValueError):
        metadata["server_model"] = None
    dump(args.output / "manifest.json", metadata)
    results = []
    for repeat in range(1, args.repeats + 1):
        for case in cases:
            name = f"{case['id']}-{repeat}"
            run_dir = args.work_dir / name
            run_dir.mkdir()
            root = run_dir / "repo"
            print(f"START {name}", flush=True)
            initial = prepare(root, args.payload, case)
            result = run_case(root, case, initial, args, run_dir)
            result["repeat"] = repeat
            results.append(result)
            dump(args.output / "results.json", results)
            write(args.output / "report.md", report(results, metadata))
            print(f"DONE {name} {result['status']} pass={result['passed']} "
                  f"seconds={result['seconds']}", flush=True)
    if files(args.payload) != payload_hashes:
        raise ValueError("source payload changed during evaluation; baseline is invalid")
    if (digest(Path(__file__).read_bytes()) != metadata["harness_sha256"]
            or digest(SUITE.read_bytes()) != metadata["suite_sha256"]):
        raise ValueError("harness or scenarios changed during evaluation; baseline is invalid")
    archive(args.output, args.work_dir, args.payload)
    dump(args.output / "evidence.sha256.json",
         {"evidence.zip": digest((args.output / "evidence.zip").read_bytes())})
    return 0 if all(r["passed"] for r in results) else 1


def compare(left: Path, right: Path) -> dict:
    """@brief Refuse unlike experiments before comparing automated outcomes."""
    old = json.loads((left / "manifest.json").read_text("utf-8"))
    new = json.loads((right / "manifest.json").read_text("utf-8"))
    controls = ("harness_version", "model", "temperature", "max_tokens", "max_turns", "repeats",
                "request_timeout", "run_timeout", "server_model",
                "suite_sha256", "harness_sha256", "host_contract_sha256", "scenario_ids")
    differences = [key for key in controls if old.get(key) != new.get(key)]
    if differences:
        raise ValueError("incomparable controls: " + ", ".join(differences))
    before = json.loads((left / "results.json").read_text("utf-8"))
    after = json.loads((right / "results.json").read_text("utf-8"))
    expected = {(case, n) for case in old["scenario_ids"]
                for n in range(1, old["repeats"] + 1)}
    for runs in (before, after):
        keys = [(r["scenario"], r["repeat"]) for r in runs]
        if len(keys) != len(expected) or set(keys) != expected:
            raise ValueError("incomplete or duplicate run set")
    indexed = {(r["scenario"], r["repeat"]): r for r in before}
    return {"automated_regressions": [
        {"scenario": r["scenario"], "repeat": r["repeat"]} for r in after
        if indexed[(r["scenario"], r["repeat"])]["passed"] and not r["passed"]],
        "passes_before": sum(r["passed"] for r in before),
        "passes_after": sum(r["passed"] for r in after),
        "median_seconds_before": statistics.median(r["seconds"] for r in before),
        "median_seconds_after": statistics.median(r["seconds"] for r in after),
        "semantic_acceptance": "requires reviewed rubric; not inferred"}


# PUBLIC API
def main(argv: list[str] | None = None) -> int:
    """@brief Run/list scenarios or compare two compatible saved experiments."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    run = sub.add_parser("run")
    run.add_argument("--base-url", required=True, help="For example http://localhost:1234/v1")
    run.add_argument("--model", required=True)
    run.add_argument("--payload", type=Path, default=PAYLOAD)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--work-dir", type=Path, required=True)
    run.add_argument("--cases", default="")
    run.add_argument("--repeats", type=int, default=2)
    run.add_argument("--max-turns", type=int, default=40)
    run.add_argument("--max-tokens", type=int, default=16384,
                     help="Generated tokens per reply, including reasoning (default: %(default)s)")
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--request-timeout", type=float, default=180)
    run.add_argument("--run-timeout", type=float, default=600)
    diff = sub.add_parser("compare")
    diff.add_argument("baseline", type=Path)
    diff.add_argument("candidate", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for case in json.loads(SUITE.read_text("utf-8"))["scenarios"]:
                print(f"{case['id']}\t{case['stage']}")
            return 0
        if args.command == "compare":
            print(json.dumps(compare(args.baseline, args.candidate), indent=2))
            return 0
        if min(args.repeats, args.max_turns, args.max_tokens,
               args.request_timeout, args.run_timeout) <= 0:
            raise ValueError("run limits must be positive")
        args.payload = args.payload.resolve()
        args.output = args.output.resolve()
        args.work_dir = args.work_dir.resolve()
        return execute(args)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"evaluation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

# END OF FILE
