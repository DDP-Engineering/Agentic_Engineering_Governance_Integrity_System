#!/usr/bin/env python3
"""
Evaluate AEGIS prompts against disposable repositories and a local model.

Uses the standard library and an explicitly selected Chat Completions
endpoint. Scores observed tool execution and artifacts, never a model's
self-assessment. The core profile runs ten cases; the capabilities
profile runs eighteen more, with fresh local reviewer sessions and a
chained four-session adoption; the hold-out profile runs a second domain,
including a chained five-session lifecycle. Results record prompt growth per
read and configured semantic
checks beside the strict ones. The constrained host is not a
native-host benchmark.
"""

from __future__ import annotations

import argparse
import datetime as dt
import functools
import hashlib
import importlib.util
import json
import os
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
import uuid
import zipfile
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = ROOT / "05_Software/aegis/template/.agentic"
SUITE = ROOT / "05_Software/aegis/evaluations/scenarios.json"
PROFILE = ROOT / "05_Software/aegis/evaluations/profiles/installed-entry.json"
CAPABILITIES = ROOT / "02_Tools/evaluate_aegis_capabilities.py"
HOLDOUT = ROOT / "02_Tools/evaluate_aegis_holdout.py"
SEMANTIC = ROOT / "05_Software/aegis/evaluations/semantic-checks.json"
CODEX_SKILL = ROOT / "05_Software/aegis/integrations/codex/plugins/aegis/skills/aegis/SKILL.md"
TASK = ".agentic/tasks/TASK-aaaaaaaa.md"
REQUIREMENT = "REQ-FUNC-11111111"
DATE = "2026-10-20"
IGNORED = {".git", "__pycache__", ".pytest_cache"}
HARNESS_VERSION = 14
#: the most text one read_file result returns, in whole lines where they fit
READ_CHARS = 40000
#: stands for the evaluated payload's root digest in the payload-independent host contract
ENTRY_PLACEHOLDER = "<root digest installed by the evaluated payload>"
#: identical consecutive tool calls, or alternating pairs, that end a session as a loop
LOOP_CALLS = 6
#: fractions of the loaded context window that a run's peak prompt is flagged above
WINDOW_THRESHOLDS = (0.5, 0.75)
#: one unit of 1-40 characters repeated at least 50 times over this many characters
#: marks degenerate generated text
REPETITION_CHARS = 1000
REPEATED_TEXT = re.compile(r"(.{1,40}?)\1{49,}", re.DOTALL)
#: optional sampling fields sent only when configured
SAMPLING = ("top_p", "top_k", "presence_penalty", "reasoning_effort")
#: Frame card fields; any other `Name:` line continues the current field
FRAME_FIELDS = {"problem", "desired outcome", "actors", "primary scenario", "examples",
                "counterexamples", "in scope", "out of scope", "constraints",
                "success signals", "evidence", "assumptions", "unknowns",
                "decision-blocking questions", "proposed behaviors", "path and reason"}
FIELD_LINE = re.compile(r"^[ \t]*(?:[-*#]+[ \t]*)?\**([A-Za-z][A-Za-z -]{1,40}?)\**:\**[ \t]*(.*)$")
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
    "aegis": "the subcommands of .agentic/aegis.py that its CLI.md documents and --help lists",
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
for discovery and write_file/edit_file for records. The aegis commands write task
records through the installed CLI as well; a read-only native sandbox does not
limit these tools. Tool results are observations.
When user input is needed, present the question in your final response and stop.
Use English for this evaluation. Do not modify the managed payload or verifier."""
REVIEW_TRANSPORT = """
Evaluation transport: use only the provided read-only tools. candidate_digest
replaces the bridge candidate operation and aegis_candidate; it returns the
supplied evaluation digest. No bridge executable is needed. The full snapshot
and actual Git diff are available; no coordinator conversation or other review
result is supplied. Do not infer that a draft or test name alone proves
behavior. Finish with one JSON object and nothing else, with the keys task,
candidate, verdict (approved or changes_required), findings, inspected_paths
and limitations."""


def tool(name: str, description: str, properties: dict, required: list) -> dict:
    """Build one provider-neutral function definition."""
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": properties,
                       "required": required, "additionalProperties": False}}}


def tools_for(commands: tuple[str, ...] | None = None) -> list:
    """The tool schema, with run_command naming a payload's aegis commands.

    commands: The payload's allowed CLI commands; None keeps the generic
             description that the compared host contract uses.
    """
    capabilities = dict(COMMAND_CAPABILITIES)
    if commands:
        capabilities["aegis"] = ", ".join(commands)
    return [
        tool("list_files", "List repository files under a relative directory.",
             {"path": {"type": "string"}}, ["path"]),
        tool("read_file", "Read a UTF-8 text file in whole lines; without offset and "
             "limit it reads the whole file. The result gives total_lines, eof and the "
             "next_offset to continue from.",
             {"path": {"type": "string"},
              "offset": {"type": "integer", "description": "first line to read, 1-based"},
              "limit": {"type": "integer", "description": "number of lines to read"}},
             ["path"]),
        tool("write_file", "Create or replace a project-owned Markdown/TOML record.",
             {"path": {"type": "string"}, "content": {"type": "string"}},
             ["path", "content"]),
        tool("edit_file", "Replace exactly one matching text fragment in a record.",
             {"path": {"type": "string"}, "old": {"type": "string"},
              "new": {"type": "string"}}, ["path", "old", "new"]),
        tool("run_command", "Run a documented capability; no shell. "
             + json.dumps(capabilities, sort_keys=True),
             {"program": {"type": "string", "enum": ["aegis", "git", "verify"]},
              "args": {"type": "array", "items": {"type": "string"}}},
             ["program", "args"]),
    ]


TOOLS = tools_for()
#: tool names a model may mistake for a run_command program
TOOL_NAMES = frozenset(t["function"]["name"] for t in TOOLS) - {"run_command"}
#: CLI commands a session may run; each fixture offers those its own payload defines
AEGIS_COMMANDS = ("status", "brief", "summary", "components", "task", "req", "check",
                  "test", "anchor", "evolution", "explain", "report", "advance", "pause",
                  "log", "ruling", "verdict")
#: commands that print the recorded summary block after their work
SUMMARY_COMMANDS = {"summary", "advance", "pause", "verdict"}


class CapabilityUnavailable(ValueError):
    """A read request outside the documented host capabilities."""


def read_slice(text: str, offset: int | float | str | None,
               limit: int | float | str | None) -> dict:
    """One read_file result: whole lines from a 1-based line offset.

    An offset below 1 reads from the top, and a missing or non-positive
    limit reads to the end. The slice stops before the line that would
    pass READ_CHARS; one longer line is cut at that size. `eof` says
    the file's last line is included, and `next_offset` names the line
    to continue from.

    Raises ValueError: An offset or limit that is not a number.
    """
    lines = text.splitlines(keepends=True)
    first = max(1, int(offset)) if offset is not None else 1
    count = int(limit) if limit is not None else 0
    chosen: list[str] = []
    size = 0
    for line in lines[first - 1:first - 1 + count if count > 0 else None]:
        if chosen and size + len(line) > READ_CHARS:
            break
        chosen.append(line[:READ_CHARS])
        size += len(chosen[-1])
    last = first - 1 + len(chosen)
    eof = last >= len(lines)
    return {"text": "".join(chosen), "total_lines": len(lines), "eof": eof,
            "next_offset": None if eof else last + 1}


def git_revision(value: str) -> bool:
    """Recognize fixture-local revision syntax without accepting Git options."""
    atom = r"(?:HEAD|master|evaluation|[0-9a-fA-F]{7,40})(?:[~^][0-9]*)?"
    return re.fullmatch(rf"{atom}(?:\.{{2,3}}{atom})?", value) is not None


def unavailable_evidence(value: str) -> bool:
    """Recognize explicit non-execution reports, not authored test results.

    Conservative English clauses cover missing evidence and pending
    verification. Other prose remains for semantic review; an execution
    event is checked separately and cannot be negated by this text.
    """
    text = " ".join(value.lower().replace("`", "").split()).strip()
    if not text:
        return True
    # a label such as "unavailable:" or "not recorded -" introduces a clause of its own
    clauses = re.split(r"\s*(?:;|:|—|–|\.\s+)\s*|\s+-\s+", text)
    subject = r"(?:tests?(?: or checks?)?|checks?(?: or tests?)?|verification)"
    auxiliaries = r"(?:(?:have|has|been|were|was|are|is|yet)\s+)*"
    suffix = r"(?: (?:for (?:this|the) candidate|in this session))?(?: yet)?"
    patterns = (
        r"(?:not recorded|none(?: recorded)?|not run|not executed|unavailable|unknown|unrecorded)(?: yet)?",
        rf"no {subject} {auxiliaries}(?:run|executed|performed|recorded){suffix}",
        rf"{subject} {auxiliaries}not (?:run|executed|performed|recorded){suffix}",
        r"(?:focused )?(?:verification|tests?|checks?) (?:is |are |remains? )?(?:still )?pending",
        r"(?:unavailable |missing )?(?:verification |test )?evidence (?:is |remains |stays )?"
        r"(?:still )?(?:unavailable|missing|not recorded|not available)",
        r"no (?:verification |test )?evidence(?: is)?(?: available| recorded)?(?: yet)?",
    )
    return all(any(re.fullmatch(pattern, clause.strip(" .")) for pattern in patterns)
               for clause in clauses)


def dump(path: Path, value: object) -> None:
    """Save a UTF-8 JSON artifact with a trailing newline."""
    write(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write(path: Path, text: str) -> None:
    """Write LF text, creating its parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def files(root: Path) -> dict[str, str]:
    """Hash all ordinary files, excluding Git and bytecode caches."""
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in sorted(root.rglob("*"))
            if p.is_file() and not (IGNORED & set(p.relative_to(root).parts))
            and not p.is_symlink()}


def candidate(root: Path) -> str:
    """Bind executable and contract files, excluding mutable task records."""
    selected = {p: h for p, h in files(root).items()
                if not p.startswith(".agentic/tasks/")}
    return digest(json.dumps(selected, sort_keys=True).encode())


def load_aegis(payload: Path):
    """Import a selected payload's actual parsers without invoking workflow."""
    spec = importlib.util.spec_from_file_location("prompt_eval_aegis",
                                                 payload / "aegis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bootstrap_text(payload: Path | None = None) -> str:
    """The root digest an installed project supplies at startup.

    `init` installs the digest of the payload it comes from, so each
    evaluated payload supplies its own; the default is the current payload.
    """
    return load_aegis(payload or PAYLOAD).POINTER_DIGEST


def instructions(entry: str | None = None) -> str:
    """Core-profile system text shared by the local and subscription transports.

    entry: The installed root digest; the current payload's by default.

    The subscription transport appends only its MCP tool-routing note, so
    local and native core observations start from the same instructions.
    """
    return (SYSTEM + "\n\nProject instructions supplied at session startup:\n\n"
            + (bootstrap_text() if entry is None else entry))


def parser_commands(agentic: Path) -> tuple[str, ...]:
    """Every subcommand that a payload's own parser defines."""
    parser = load_aegis(agentic).build_parser()
    return tuple(next(action.choices for action in parser._actions
                      if isinstance(action, argparse._SubParsersAction)))


def aegis_commands(agentic: Path) -> tuple[str, ...]:
    """The allowed CLI commands that a payload's own parser defines."""
    defined = parser_commands(agentic)
    return tuple(command for command in AEGIS_COMMANDS if command in defined)


def state_block(payload: Path) -> bool:
    """Whether a payload keeps journal state in one CLI-written `## State` block."""
    return "\n## State\n" in (payload / "templates/task.md").read_text("utf-8")


def resume_state(text: str, payload: Path, stage: str, next_action: str,
                 verdict: str = "disabled", review_round: str = "",
                 report_next: str | None = None, waiting: bool = False,
                 changed: str = "", evidence: str = "") -> str:
    """Record a fixture's resume state in the payload's own format.

    A payload with a `## State` block reads that block; an older payload
    reads Handoff and Stage report. Both receive the same facts in the
    format their own instructions describe, so paired fixtures stay
    equivalent.

    report_next: The older Stage report's next action, where it differs.
    waiting: A pause for the user instead of work in progress.
    """
    result = "paused" if waiting else "in_progress"
    if state_block(payload):
        return section(text, "State",
                       f"status: {'waiting' if waiting else 'working'}\n"
                       f"reported: {stage} - {result}\nnext: {next_action}\n"
                       f"must_read: {TASK}\nchanged: {changed}\nevidence: {evidence}\n"
                       f"issues:\nspec_compliance: {verdict}\n"
                       f"implementation_quality: {verdict}\nreview_round: {review_round}")
    text = section(text, "Handoff", f"current: {stage}\n"
                   f"status: {'waiting' if waiting else 'ready'}\n"
                   f"next: {next_action}\nmust_read: {TASK}\nblockers:")
    return section(text, "Stage report",
                   f"stage: {stage}\nresult: {result}\ncurrent: {stage}\n"
                   f"changed: {changed}\nevidence: {evidence}\nissues:\n"
                   f"next: {report_next or next_action}\n"
                   f"needs_user: {'yes' if waiting else 'no'}\nspec_compliance: {verdict}\n"
                   f"implementation_quality: {verdict}\nreview_round: {review_round}")


def summary_block(stdout: str) -> str:
    """The summary lines a command printed, through its Details line."""
    lines = stdout.strip().splitlines()
    end = next((index for index, line in enumerate(lines) if line.startswith("Details:")),
               len(lines) - 1)
    return "\n".join(lines[:end + 1])


def recorded_state(aegis, text: str, stage: str) -> dict:
    """A journal's recorded resume state in one shape, from either format.

    Keys follow the older Stage report (`result`, `needs_user`, the review
    fields, `changed`, `evidence`, `issues`) plus `status`, `next`,
    `must_read` and `synchronized`, which says whether the record is bound
    to the header stage `stage`.

    Raises aegis.UserError: A malformed record.
    """
    if "\n## State\n" in text and hasattr(aegis, "parse_state"):
        state = aegis.parse_state(text)
        reported, _separator, result = state.get("reported", "").partition(" - ")
        status = state.get("status", "")
        return {**state, "result": result, "stage": reported,
                "needs_user": ("yes" if status in {"waiting", "blocked"} else
                               "no" if status else ""),
                "synchronized": bool(reported) and (
                    reported == stage or status in {"ready", "done"})}
    report, handoff = aegis.parse_stage_report(text), aegis.parse_handoff(text)
    return {**report, "status": handoff.get("status", ""), "next": handoff.get("next", ""),
            "must_read": handoff.get("must_read", ""),
            "synchronized": stage == report.get("current") == handoff.get("current")}


@functools.lru_cache(maxsize=1)
def load_capabilities():
    """Import the capability fixtures, hosts and scorer on first use.

    That module imports this file under its own name; importing it lazily
    avoids a cycle. Both copies share only pure helpers, while the model
    transport and its `request_json` stay in this module.
    """
    spec = importlib.util.spec_from_file_location("aegis_eval_capabilities", CAPABILITIES)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_signature(call: dict) -> str:
    """Canonical name-and-arguments identity of one requested tool call."""
    function = call.get("function", {}) if isinstance(call, dict) else {}
    try:
        arguments = json.loads(function.get("arguments", ""))
    except (TypeError, ValueError):
        arguments = function.get("arguments")
    return json.dumps([function.get("name"), arguments], sort_keys=True, ensure_ascii=False)


def repetition_loop(signatures: list[str], calls: int = LOOP_CALLS) -> bool:
    """Recognize one call repeated, or two calls alternating, `calls` times in a row."""
    tail = signatures[-calls:]
    return len(tail) == calls and all(tail[i] == tail[i % 2] for i in range(calls))


def repetition_run(text: str) -> int:
    """Length of the longest run of one short unit repeated at least 50 times.

    Returns: Characters in that run, or 0 below REPETITION_CHARS.
    """
    if not isinstance(text, str) or len(text) < REPETITION_CHARS:
        return 0
    longest = max((len(m.group(0)) for m in REPEATED_TEXT.finditer(text)), default=0)
    return longest if longest >= REPETITION_CHARS else 0


def context_metrics(usage: list, turns: list, events: list, window: int | None) -> dict:
    """Summarize prompt growth and attribute it to the file reads that caused it.

    usage: Reported usage per request; entries may be missing.
    turns: Per request, the tool events and result sizes appended after it.
    events: Tool events of the session, indexed by `turns`.
    window: Loaded context window in tokens, when known.

    The prompt of request n+1 minus the prompt and completion of request n
    is the cost of the tool results appended between them. That growth is
    shared among those results by character length. Reads without a
    following measured request keep their characters and are marked
    unmeasured.

    Returns: First, peak and total prompt tokens, completion tokens, window use and
    per-path read costs, most expensive first.
    """
    def count(record, key):
        value = record.get(key) if isinstance(record, dict) else None
        return value if isinstance(value, int) else None

    prompts = [count(u, "prompt_tokens") for u in usage]
    reads: dict[str, dict] = {}
    for index, turn in enumerate(turns):
        results = turn.get("tool_results", [])
        total = sum(item["chars"] for item in results)
        before = prompts[index] if index < len(prompts) else None
        after = prompts[index + 1] if index + 1 < len(prompts) else None
        growth = None
        if before is not None and after is not None:
            growth = max(after - before - (count(usage[index], "completion_tokens") or 0), 0)
        for item in results:
            event = events[item["event"]] if 0 <= item["event"] < len(events) else {}
            if event.get("tool") != "read_file" or "text" not in event.get("result", {}):
                continue
            path = str(event.get("arguments", {}).get("path", ""))
            entry = reads.setdefault(path, {"path": path, "reads": 0, "chars": 0,
                                            "tokens": 0, "measured": True})
            entry["reads"] += 1
            entry["chars"] += item["chars"]
            if growth is not None and total:
                entry["tokens"] += round(growth * item["chars"] / total)
            else:
                entry["measured"] = False
    known = [p for p in prompts if p is not None]
    return with_window({"first_prompt_tokens": known[0] if known else None,
                        "peak_prompt_tokens": max(known) if known else None,
                        "total_prompt_tokens": sum(known) if known else None,
                        "completion_tokens": sum(count(u, "completion_tokens") or 0
                                                 for u in usage),
                        "reads": sorted(reads.values(),
                                        key=lambda r: (-r["tokens"], -r["chars"], r["path"]))},
                       window)


def with_window(context: dict, window: int | None) -> dict:
    """Add the loaded window and the peak prompt's share of it to a summary."""
    peak = context.get("peak_prompt_tokens")
    fraction = round(peak / window, 3) if peak and window else None
    return {**context, "context_window": window, "peak_window_fraction": fraction,
            "above_window_thresholds": [t for t in WINDOW_THRESHOLDS
                                        if fraction is not None and fraction > t]}


def server_model(base_url: str, model: str) -> dict | None:
    """The requested model's record from the LM Studio REST API, when available."""
    parsed = urllib.parse.urlparse(base_url)
    try:
        server = request_json(f"{parsed.scheme}://{parsed.netloc}/api/v0/models", None, 15)
    except (OSError, ValueError):
        return None
    return next((m for m in server.get("data", []) if m.get("id") == model), None)


def loaded_window(record: dict | None) -> int | None:
    """Loaded context length of a server model record; absent while unloaded."""
    value = (record or {}).get("loaded_context_length")
    return value if isinstance(value, int) and value > 0 else None


def server_identity(record):
    """Comparable server model fields, without load state or loaded length.

    A just-in-time server can report one model unloaded before a run and
    loaded after it; the loaded length is compared as `context_window`.
    """
    if not isinstance(record, dict):
        return record
    return {k: v for k, v in record.items() if k not in {"state", "loaded_context_length"}}


def review_response(text: str) -> dict:
    """Parse a reviewer's final JSON object, allowing one surrounding fence.

    Raises ValueError: The text holds no single JSON object.
    """
    body = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.DOTALL)
    if fenced:
        body = fenced.group(1)
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end < start:
        raise ValueError("review response contains no JSON object")
    value = json.loads(body[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("review response is not a JSON object")
    return value


@functools.lru_cache(maxsize=1)
def load_holdout():
    """Import the hold-out pricing fixtures, host and scorers on first use."""
    spec = importlib.util.spec_from_file_location("aegis_eval_holdout", HOLDOUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def journal_text(root: Path) -> str:
    """The fixture's single task journal, or empty text when there is not exactly one."""
    journals = sorted((root / ".agentic/tasks").glob("TASK-*.md"))
    return journals[0].read_text("utf-8") if len(journals) == 1 else ""


def section_text(text: str, heading: str) -> str:
    """Body of a level-two section without authoring comments, stripped."""
    match = re.search(rf"(?ms)^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text)
    return re.sub(r"(?s)<!--.*?-->", "", match.group(1)).strip() if match else ""


def frame_fields(text: str) -> dict[str, str]:
    """Split the Frame section into its card fields, keyed in lower case."""
    fields: dict[str, str] = {}
    current = None
    for line in section_text(text, "Frame").splitlines():
        match = FIELD_LINE.match(line)
        if match and match.group(1).strip().lower() in FRAME_FIELDS:
            current = match.group(1).strip().lower()
            fields[current] = match.group(2)
        elif current:
            fields[current] += "\n" + line
    return fields


def new_requirements(root: Path, initial: dict) -> list[dict]:
    """Requirement records created during the run; unparseable files count as empty."""
    records = []
    for path in sorted((root / ".agentic/requirements").rglob("*.toml")):
        if path.relative_to(root).as_posix() in initial["files"]:
            continue
        try:
            records.append(tomllib.loads(path.read_text("utf-8")))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            records.append({})
    return records


def frame_open(record: dict, spec: dict) -> tuple[bool, str]:
    """At least one listed term appears among the Frame's unknowns or questions."""
    fields = record["frame"]
    text = (fields.get("unknowns", "") + "\n"
            + fields.get("decision-blocking questions", "")).lower()
    hits = [term for term in spec["any"] if term.lower() in text]
    return bool(hits), ("matched " + ", ".join(hits)) if hits else "no listed term open"


def frame_mentions(record: dict, spec: dict) -> tuple[bool, str]:
    """Every listed term appears somewhere in the Frame."""
    frame = section_text(record["journal"], "Frame").lower()
    missing = [term for term in spec["all"] if term.lower() not in frame]
    return not missing, ("missing " + ", ".join(missing)) if missing else ""


def frame_no_quantity(record: dict, spec: dict) -> tuple[bool, str]:
    """The named Frame fields state no number with one of the listed units."""
    units = "|".join(re.escape(unit) for unit in spec["units"])
    pattern = re.compile(rf"\b\d+(?:[.,]\d+)?\s*(?:{units})s?\b", re.IGNORECASE)
    found = [f"{name}: {m.group(0)}" for name in spec["fields"]
             for m in pattern.finditer(record["frame"].get(name.lower(), ""))]
    return not found, "; ".join(found)


def requirements_split(record: dict, spec: dict) -> tuple[bool, str]:
    """At least two new requirements, with the error response in some but not all."""
    prose = [str(r.get("requirement", "")) for r in record["new"]]
    errors = sum(spec["error"] in text for text in prose)
    return (len(prose) >= 2 and 0 < errors < len(prose),
            f"{len(prose)} new requirement(s), {errors} naming {spec['error']}")


def requirements_mention(record: dict, spec: dict) -> tuple[bool, str]:
    """Some new requirement's prose contains every listed term."""
    return (any(all(term in str(r.get("requirement", "")) for term in spec["all"])
                for r in record["new"]), f"{len(record['new'])} new requirement(s)")


def design_cites_requirements(record: dict, _spec: dict) -> tuple[bool, str]:
    """The Design section names every requirement on the journal header."""
    ids = [value.strip() for value in record["requirements"].split(",") if value.strip()]
    missing = [value for value in ids if value not in record["design"]]
    return (bool(record["design"]) and bool(ids) and not missing,
            ("missing " + ", ".join(missing)) if missing else "")


def design_mentions(record: dict, spec: dict) -> tuple[bool, str]:
    """Every listed term appears in the Design section."""
    missing = [term for term in spec["all"] if term not in record["design"]]
    return not missing, ("missing " + ", ".join(missing)) if missing else ""


def design_max_lines(record: dict, spec: dict) -> tuple[bool, str]:
    """The Design section exists and has at most the listed number of lines."""
    lines = [line for line in record["design"].splitlines() if line.strip()]
    return 0 < len(lines) <= spec["lines"], f"{len(lines)} lines"


def design_present(record: dict, _spec: dict) -> tuple[bool, str]:
    """The Design section records a note or a skip reason."""
    return bool(record["design"]), ""


PREDICATES = {"frame_open": frame_open, "frame_mentions": frame_mentions,
              "frame_no_quantity": frame_no_quantity, "requirements_split": requirements_split,
              "requirements_mention": requirements_mention,
              "design_cites_requirements": design_cites_requirements,
              "design_mentions": design_mentions, "design_max_lines": design_max_lines,
              "design_present": design_present}


def semantic_checks(root: Path, case: dict, initial: dict) -> list[dict]:
    """Evaluate the scenario's configured semantic predicates on the saved records.

    Predicates come from semantic-checks.json by scenario id. They are reported
    beside the strict checks and never change a strict pass.

    Raises ValueError: A configured predicate type is unknown.
    """
    specs = json.loads(SEMANTIC.read_text("utf-8"))["checks"].get(case["id"], [])
    if not specs:
        return []
    text = journal_text(root)
    header = re.search(r"(?m)^requirements:[ \t]*(.*)$", text)
    record = {"journal": text, "frame": frame_fields(text),
              "design": section_text(text, "Design"),
              "requirements": header.group(1) if header else "",
              "new": new_requirements(root, initial)}
    results = []
    for spec in specs:
        if spec["type"] not in PREDICATES:
            raise ValueError(f"unknown semantic check type: {spec['type']}")
        passed, detail = PREDICATES[spec["type"]](record, spec)
        results.append({"id": spec["id"], "passed": bool(passed), "detail": detail})
    return results


def section(text: str, heading: str, body: str) -> str:
    """Replace the body of an existing level-two section."""
    pattern = rf"(?m)(^## {re.escape(heading)}\n).*?(?=^## |\Z)"
    updated, count = re.subn(pattern, lambda m: m[1] + "\n" + body.rstrip() + "\n\n",
                             text, flags=re.DOTALL)
    if count != 1:
        raise ValueError(f"expected exactly one section: {heading}")
    return updated


def git(root: Path, *args: str) -> str:
    """Operate only on the disposable fixture, with local test identity."""
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
    """Use the selected prompt's own checklist without rewriting it."""
    number = {"frame": 1, "build": 4, "validate": 5}[stage]
    text = (payload / f"steps/{number}_{stage}.md").read_text("utf-8")
    return text.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0].strip()


def prepare(root: Path, payload: Path, case: dict) -> dict:
    """Create one deterministic tiny repository; never reuse a checkout.

    Returns: Initial file hashes, journal and immutable Git head for scoring.
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
        for key, value in {"stage": stage, "type": "fix",
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
                       "Evidence: OBSERVED src/normalize.py and tests/test_normalize.py.")
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
        text = resume_state(text, payload, stale, f"Continue {stale}",
                            verdict="approved" if setup == "stale_verdicts" else "",
                            review_round="1" if review else "",
                            report_next="Continue current stage")
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
    """Confine file access and executable commands to one trusted fixture."""

    def __init__(self, root: Path, initial: dict, payload: dict):
        self.root = root.resolve()
        self.initial = initial
        self.payload = payload
        self.events: list[dict] = []
        #: the fixture's own payload decides which allowed commands exist
        self.cli = parser_commands(self.root / ".agentic")
        self.aegis = tuple(command for command in AEGIS_COMMANDS if command in self.cli)

    def path(self, name: object, writable: bool = False) -> Path:
        """Reject traversal, absolute paths, Git internals and payload edits.

        name: A model-supplied value; anything but a string is rejected.
        """
        if not isinstance(name, str):
            raise ValueError("path must be a repository-relative string")
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
        """Execute a fixed command capability; reject shell interpolation."""
        if not isinstance(args, list) or any(not isinstance(x, str) for x in args):
            raise ValueError("args must be a string array")
        if program == "aegis" and args and (args[0] in self.aegis
                                            or args == ["--help"]):
            argv = [sys.executable, ".agentic/aegis.py", *args]
        elif program == "aegis" and args and args[0] not in self.cli and not args[0].startswith("-"):
            # a command this CLI does not have is a wrong guess; a real command
            # outside the allowed set stays forbidden
            raise CapabilityUnavailable(f"aegis has no '{args[0]}' command; see aegis --help")
        elif program == "aegis" and args[:1] == ["init"] and self.initial.get("initialized"):
            # adopt.md starts with init, which the fixture ran when AEGIS was installed
            raise CapabilityUnavailable("AEGIS was initialized when it was installed; continue")
        elif program == "git" and args[:1] == ["git"]:
            # `git git status` repeats the program: a wrong call, unless what
            # follows is a write, which stays forbidden
            self.git_command(args[1:])
            raise CapabilityUnavailable("git is the program; leave it out of args")
        elif program == "git":
            argv = self.git_command(args)
        elif program == "verify" and not args:
            argv = [sys.executable, "verify.py"]
        elif program in TOOL_NAMES:
            # a tool asked for through run_command is a wrong tool choice, not an
            # attempt to execute something outside the capabilities
            raise CapabilityUnavailable(f"{program} is a tool; call it directly")
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
        """Build bounded read-only Git argv with fixture-confined paths.

        Raises PermissionError: Mutation, executable options or escaping paths.
        Raises CapabilityUnavailable: An unsupported read-only argument form.
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
            """Resolve a literal repository path without Git pathspec magic."""
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
        """Execute a model tool request and retain observed evidence."""
        started = time.monotonic()
        try:
            if name == "list_files":
                target = self.path(arguments["path"])
                result = {"files": [p for p in files(self.root)
                                    if (self.root / p).is_relative_to(target)]}
            elif name == "read_file":
                target = self.path(arguments["path"])
                # Windows raises PermissionError for a directory; it is a wrong
                # tool choice, never a forbidden action
                if target.is_dir():
                    raise CapabilityUnavailable("path is a directory; use list_files")
                result = read_slice(target.read_text("utf-8"), arguments.get("offset"),
                                    arguments.get("limit"))
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
                              available_commands={**COMMAND_CAPABILITIES,
                                                  "aegis": ", ".join(self.aegis)})
        self.events.append({"tool": name, "arguments": arguments, "result": result,
                            "seconds": time.monotonic() - started})
        return result


def score(root: Path, case: dict, initial: dict, events: list[dict],
          payload: Path) -> dict:
    """Grade observed artifacts and commands; leave semantic judgments open."""
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
    stage = parsed["header"].get("stage")
    try:
        report = recorded_state(aegis, text, stage or "")
        rulings, errors = aegis.parse_rulings(text)
        add("parseable_records", not errors, "; ".join(errors))
    except aegis.UserError as exc:
        add("parseable_records", False, str(exc))
        return {"passed": False, "checks": checks, "semantic_review": "pending"}
    expected = case["expect"]
    add("expected_stage", stage in expected["stages"], str(stage))
    add("synchronized_stage", report["synchronized"])
    add("resume_action", bool(report.get("next")) and bool(report.get("must_read")))
    if expected.get("waiting"):
        add("awaits_user", report.get("needs_user") == "yes"
            and report.get("status") in {"waiting", "blocked"})
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
                               and e["arguments"]["args"][:1] in [[c] for c in SUMMARY_COMMANDS]
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
    writers = sum(e["arguments"]["program"] == "aegis" and e["result"]["exit_code"] == 0
                  and e["arguments"]["args"][:1] in [["advance"], ["pause"], ["log"],
                                                     ["ruling"], ["verdict"]]
                  for e in commands)
    return {"passed": all(c["passed"] for c in checks), "checks": checks,
            "semantic_review": "pending", "rubric": case["rubric"],
            "journal_writer_commands": writers}


def request_json(url: str, data: dict | None, timeout: float) -> dict:
    """Perform one explicit endpoint request, without SDKs or retries."""
    body = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def chat_session(host, system: str, prompt: str, tools: list, args, run_dir: Path,
                 run_timeout: float) -> dict:
    """Run one bounded model/tool loop and save its evidence after every request.

    host: Tool host exposing `call` and the shared `events` list.
    run_timeout: Wall-clock bound for this session, in seconds.
    Returns: Status, error, final text, usage, per-request tool results, returned
    model identities, degenerate responses and elapsed seconds.
    Note: A session that repeats one call, or alternates two, LOOP_CALLS times in
    a row ends with status `loop`, as does a response cut at the output
    limit inside repeated text; only `completed` can ever pass. A response
    that repeats text but still finishes is counted, not failed.
    """
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    write(run_dir / "request.txt", prompt)
    write(run_dir / "instructions.txt", system)
    sampling = {key: getattr(args, key, None) for key in SAMPLING}
    started = time.monotonic()
    usage, turns, signatures = [], [], []
    status, error, final = "turn_limit", "", ""
    observed_models = set()
    degenerate = 0
    for turn in range(args.max_turns):
        if time.monotonic() - started >= run_timeout:
            status = "run_timeout"
            break
        try:
            body = {"model": args.model, "messages": messages, "tools": tools,
                    "temperature": args.temperature, "max_tokens": args.max_tokens,
                    "stream": False,
                    **{key: value for key, value in sampling.items() if value is not None}}
            response = request_json(args.base_url.rstrip("/") + "/chat/completions", body,
                                    min(args.request_timeout,
                                        run_timeout - (time.monotonic() - started)))
            if not isinstance(response, dict) or not isinstance(response.get("choices"), list):
                raise ValueError("invalid Chat Completions response")
            observed_models.add(response.get("model", "unreported"))
            usage.append(response.get("usage"))
            turns.append({"turn": turn, "tool_results": []})
            choice = response["choices"][0]
            raw = choice["message"]
            if not isinstance(raw, dict):
                raise ValueError("invalid assistant message")
            message = {"role": "assistant", "content": raw.get("content")}
            if raw.get("tool_calls"):
                message["tool_calls"] = raw["tool_calls"]
            messages.append(message)
            repeated = repetition_run(message.get("content") or "")
            degenerate += bool(repeated)
            with (run_dir / "responses.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"turn": turn, "message": message,
                    "usage": response.get("usage"), "model": response.get("model"),
                    "finish_reason": choice.get("finish_reason"),
                    "repetition_chars": repeated}) + "\n")
            if choice.get("finish_reason") == "length":
                status = "loop" if repeated else "output_limit"
                error = "repeated text until the output limit" if repeated else ""
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
                content = json.dumps(result, ensure_ascii=False)
                turns[-1]["tool_results"].append({"event": len(host.events) - 1,
                                                  "chars": len(content)})
                signatures.append(call_signature(call))
                messages.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": content})
            dump(run_dir / "tools.json", host.events)
            if repetition_loop(signatures):
                status = "loop"
                break
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            status, error = "runner_error", str(exc)
            break
    dump(run_dir / "tools.json", host.events)
    write(run_dir / "final.txt", final)
    return {"status": status, "error": error, "final": final, "usage": usage,
            "turns": turns, "observed_models": observed_models,
            "degenerate_responses": degenerate,
            "seconds": round(time.monotonic() - started, 3)}


def local_reviewer(cap, args, run_dir: Path, repo: Path, initial: dict,
                   payload_files: dict, ledger: list):
    """Build the delegate that runs each review role once in a fresh local session.

    cap: The capability module: role prompts, reviewer host and tools.
    ledger: Completed review observations, in launch order.

    Both roles inspect one immutable snapshot copied at the first request,
    through the read-only reviewer tool set and their unchanged native role
    prompts. Neither receives the coordinator conversation or the other
    verdict. A repeated role returns its recorded observation while the
    candidate is unchanged; a changed candidate has consumed the round, as
    in the subscription transport.

    Returns: Callable taking `delegate_review` arguments and returning the observation.
    """
    snapshot = run_dir / "review-snapshot"
    baseline: dict[str, str] = {}

    def delegate(arguments: dict) -> dict:
        role, bound = arguments["role"], arguments["candidate"]
        for previous in ledger:
            if previous["role"] == role:
                if previous["candidate"] != bound:
                    raise ValueError("review round consumed; candidate changed without "
                                     "a new policy decision")
                return {**previous, "reused_observation": True}
        if not snapshot.exists():
            shutil.copytree(repo, snapshot,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            baseline.update(files(snapshot))
        if candidate(snapshot) != bound or candidate(repo) != bound:
            raise ValueError("candidate changed between reviews; no second verdict reused")
        folder = run_dir / "reviewers" / role
        folder.mkdir(parents=True)
        host = cap.CapabilityHost(snapshot, {**initial, "files": files(snapshot),
                                             "candidate": candidate(snapshot)},
                                  payload_files, reviewer=True)
        prompt = (f"Independently review {arguments['task']}, candidate {bound}. Read the "
                  "complete task, accepted scope and current source/tests. Verify the "
                  "digest before and after inspection.")
        session = chat_session(host, cap.role_prompt(role) + REVIEW_TRANSPORT, prompt,
                               cap.REVIEW_TOOLS, args, folder,
                               getattr(args, "review_timeout", 900))
        status, error, response = session["status"], session["error"], None
        if status == "completed":
            try:
                response = review_response(session["final"])
                if (response.get("task") != arguments["task"]
                        or response.get("candidate") != bound
                        or response.get("verdict") not in {"approved", "changes_required"}):
                    raise ValueError("review response identity or verdict mismatch")
            except ValueError as exc:
                status, error, response = "invalid_review_response", str(exc), None
        events = host.events
        result = {"role": role, "candidate": bound, "status": status, "error": error,
                  "thread_id": f"local-{role}-{uuid.uuid4().hex[:12]}",
                  "response": response,
                  "verdict": response.get("verdict") if response else None,
                  "observed_reads": sorted({str(e["arguments"].get("path")) for e in events
                                            if e["tool"] == "read_file"
                                            and "text" in e["result"]}),
                  "digest_reads": sum(e["tool"] == "candidate_digest"
                                      and e["result"].get("candidate") == bound
                                      for e in events),
                  "denied_actions": sum(bool(e["result"].get("denied")) for e in events),
                  "native_violations": 0,
                  "snapshot_unchanged": files(snapshot) == baseline,
                  "seconds": session["seconds"],
                  "degenerate_responses": session["degenerate_responses"],
                  "model_ids_returned": sorted(session["observed_models"]),
                  "output_tokens": sum(u.get("completion_tokens", 0)
                                       for u in session["usage"] if isinstance(u, dict)),
                  "run_directory": folder.relative_to(run_dir).as_posix()}
        ledger.append(result)
        dump(run_dir / "reviews.json", ledger)
        return result

    return delegate


def core_profile(payload: Path = PAYLOAD) -> dict:
    """The ten-case core profile: its fixtures, host, tools, system text and scorer.

    `system` carries the payload's own root digest; `contract` replaces it with a
    placeholder, so the host contract compared across payloads stays fixed.
    """
    return {
        "name": "core", "suite": SUITE, "system": instructions(bootstrap_text(payload)),
        "contract": instructions(ENTRY_PLACEHOLDER),
        "tools": tools_for(aegis_commands(payload)), "contract_tools": TOOLS,
        "prepare": prepare,
        "host": lambda root, initial, payload_files, _run_dir, _args, _phase=None:
            (Host(root, initial, payload_files), []),
        "score": lambda root, case, initial, events, payload, _reviews, _final:
            score(root, case, initial, events, payload),
        "sources": [Path(__file__).resolve(), SUITE, PROFILE, SEMANTIC]}


def capability_profile(payload: Path = PAYLOAD) -> dict:
    """The capability profile, with fresh local reviewer sessions and the chained adoption."""
    cap = load_capabilities()

    def host(root, initial, payload_files, run_dir, args, _phase=None):
        reviews: list[dict] = []
        delegate = local_reviewer(cap, args, run_dir, root, initial, payload_files, reviews)
        return cap.CapabilityHost(root, initial, payload_files, delegate=delegate), reviews

    return {
        "name": "capabilities", "suite": cap.SUITE,
        "system": cap.instructions(bootstrap_text(payload)),
        "contract": cap.instructions(ENTRY_PLACEHOLDER),
        "tools": cap.tools_for(aegis_commands(payload)), "contract_tools": cap.TOOLS,
        "prepare": cap.prepare, "host": host, "score": cap.score, "score_chain": cap.score_chain,
        "sources": [Path(__file__).resolve(), CAPABILITIES, Path(cap.stages.__file__),
                    Path(cap.adoption.__file__),
                    cap.SUITE, PROFILE, SEMANTIC, cap.ROLE_DIR / "aegis-spec-review.toml",
                    cap.ROLE_DIR / "aegis-quality-review.toml", CODEX_SKILL]}


def holdout_profile(payload: Path = PAYLOAD) -> dict:
    """The hold-out pricing profile, including the chained lifecycle case."""
    holdout = load_holdout()
    return {
        "name": "holdout", "suite": holdout.SUITE,
        "system": holdout.instructions(bootstrap_text(payload)),
        "contract": holdout.instructions(ENTRY_PLACEHOLDER),
        "tools": tools_for(aegis_commands(payload)), "contract_tools": TOOLS,
        "prepare": holdout.prepare,
        "host": lambda root, initial, payload_files, _run_dir, _args, phase=None:
            (holdout.HoldoutHost(root, initial, payload_files, phase), []),
        "score": holdout.score, "score_chain": holdout.score_chain,
        "sources": [Path(__file__).resolve(), HOLDOUT, holdout.SUITE, PROFILE, SEMANTIC]}


PROFILES = {"core": core_profile, "capabilities": capability_profile,
            "holdout": holdout_profile}


def run_case(root: Path, case: dict, initial: dict, args, run_dir: Path,
             profile: dict | None = None, window: int | None = None) -> dict:
    """Run one scenario session and grade it from observed events and files.

    profile: Fixtures, host, tools, system text and scorer; core by default.
    window: Loaded context window in tokens, when known.
    Returns: The saved run result, including context metrics, reviewer sessions and
    semantic checks; a chained case delegates to run_chain.
    """
    profile = profile or core_profile(args.payload)
    if case.get("chain"):
        return run_chain(root, case, initial, args, run_dir, profile, window)
    host, reviews = profile["host"](root, initial, files(args.payload), run_dir, args)
    dump(run_dir / "initial.json", initial)
    session = chat_session(host, profile["system"], case["prompt"], profile["tools"],
                           args, run_dir, args.run_timeout)
    graded = profile["score"](root, case, initial, host.events, args.payload, reviews,
                              session["final"])
    events = host.events
    semantic = semantic_checks(root, case, initial)
    result = {"scenario": case["id"], "profile": profile["name"],
              "status": session["status"], "error": session["error"],
              "seconds": session["seconds"],
              "model_ids_returned": sorted(session["observed_models"]),
              "requests": len(session["usage"]), "tool_calls": len(events),
              "tool_errors": sum("error" in e["result"] for e in events),
              "capability_errors": sum(bool(e["result"].get("capability_unavailable"))
                                       for e in events),
              "forbidden_actions": sum(bool(e["result"].get("denied")) for e in events),
              "reviewer_sessions": len(reviews),
              "degenerate_responses": session["degenerate_responses"],
              "reviewer_degenerate_responses": sum(r.get("degenerate_responses", 0)
                                                   for r in reviews),
              "usage": session["usage"],
              "context": context_metrics(session["usage"], session["turns"], events, window),
              "evaluation": graded,
              "semantic_checks": semantic,
              "semantic_passed": all(c["passed"] for c in semantic) if semantic else None,
              "passed": session["status"] == "completed" and graded["passed"]
              and session["observed_models"] == {args.model}}
    dump(run_dir / "result.json", result)
    return result


def merged_context(contexts: list[dict], window: int | None) -> dict:
    """Combine per-session context summaries of one chained case."""
    peaks = [c["peak_prompt_tokens"] for c in contexts if c.get("peak_prompt_tokens")]
    totals = [c["total_prompt_tokens"] for c in contexts if c.get("total_prompt_tokens")]
    reads: dict[str, dict] = {}
    for context in contexts:
        for item in context.get("reads", []):
            entry = reads.setdefault(item["path"], {"path": item["path"], "reads": 0,
                                                    "chars": 0, "tokens": 0, "measured": True})
            for key in ("reads", "chars", "tokens"):
                entry[key] += item[key]
            entry["measured"] = entry["measured"] and item["measured"]
    return with_window({
        "first_prompt_tokens": contexts[0].get("first_prompt_tokens") if contexts else None,
        "peak_prompt_tokens": max(peaks) if peaks else None,
        "total_prompt_tokens": sum(totals) if totals else None,
        "completion_tokens": sum(c.get("completion_tokens", 0) for c in contexts),
        "reads": sorted(reads.values(), key=lambda r: (-r["tokens"], -r["chars"], r["path"]))},
        window)


def run_chain(root: Path, case: dict, initial: dict, args, run_dir: Path, profile: dict,
              window: int | None = None) -> dict:
    """Run each stage of a chained case as a fresh session on one repository.

    Every session starts a new conversation with only its stage request; the
    files and journal earlier sessions left are the whole handoff. The first
    session must leave exactly one journal, whose ID replaces `{task}` in later
    requests. A session that does not complete ends the chain.

    Raises ValueError: The profile cannot grade chained cases.
    """
    if "score_chain" not in profile:
        raise ValueError(f"profile {profile['name']} has no chained-case scorer")
    dump(run_dir / "initial.json", initial)
    payload_files = files(args.payload)
    events, sessions, usage, contexts = [], [], [], []
    observed_models: set = set()
    task, final, status, error = "", "", "completed", ""
    for index, step in enumerate(case["chain"], 1):
        session_dir = run_dir / f"session-{index}-{step['stage']}"
        session_dir.mkdir()
        host, _reviews = profile["host"](root, initial, payload_files, session_dir, args,
                                         step["stage"])
        session = chat_session(host, profile["system"], step["prompt"].replace("{task}", task),
                               profile["tools"], args, session_dir, args.run_timeout)
        for event in host.events:
            event["session"] = step["stage"]
        events.extend(host.events)
        usage.extend(session["usage"])
        observed_models |= session["observed_models"]
        context = context_metrics(session["usage"], session["turns"], host.events, window)
        contexts.append(context)
        final = session["final"]
        journals = sorted((root / ".agentic/tasks").glob("TASK-*.md"))
        if not task and len(journals) == 1:
            task = journals[0].stem
        sessions.append({"stage": step["stage"], "status": session["status"],
                         "error": session["error"], "seconds": session["seconds"],
                         "requests": len(session["usage"]), "tool_calls": len(host.events),
                         "degenerate_responses": session["degenerate_responses"],
                         "task": task, "context": context})
        if session["status"] != "completed" or not task:
            status = f"{step['stage']}:{session['status'] if task else 'no_journal'}"
            error = session["error"]
            break
    dump(run_dir / "tools.json", events)
    graded = profile["score_chain"](root, case, initial, events, args.payload, sessions, final)
    semantic = semantic_checks(root, case, initial)
    result = {"scenario": case["id"], "profile": profile["name"], "status": status,
              "error": error, "seconds": round(sum(s["seconds"] for s in sessions), 3),
              "model_ids_returned": sorted(observed_models), "requests": len(usage),
              "tool_calls": len(events),
              "tool_errors": sum("error" in e["result"] for e in events),
              "capability_errors": sum(bool(e["result"].get("capability_unavailable"))
                                       for e in events),
              "forbidden_actions": sum(bool(e["result"].get("denied")) for e in events),
              "reviewer_sessions": 0,
              "degenerate_responses": sum(s["degenerate_responses"] for s in sessions),
              "reviewer_degenerate_responses": 0, "sessions": sessions, "usage": usage,
              "context": merged_context(contexts, window), "evaluation": graded,
              "semantic_checks": semantic,
              "semantic_passed": all(c["passed"] for c in semantic) if semantic else None,
              "passed": status == "completed" and graded["passed"]
              and observed_models == {args.model}}
    dump(run_dir / "result.json", result)
    return result


def pass_rates(results: list[dict]) -> dict[str, dict[str, str]]:
    """Strict and semantic passes per scenario across repeats, in first-seen order."""
    rates: dict[str, dict[str, list[int]]] = {}
    for result in results:
        entry = rates.setdefault(result["scenario"], {"strict": [0, 0], "semantic": [0, 0]})
        entry["strict"][0] += bool(result["passed"])
        entry["strict"][1] += 1
        if result.get("semantic_passed") is not None:
            entry["semantic"][0] += bool(result["semantic_passed"])
            entry["semantic"][1] += 1
    return {scenario: {kind: f"{passed}/{runs}" if runs else "-"
                       for kind, (passed, runs) in entry.items()}
            for scenario, entry in rates.items()}


def report(results: list[dict], metadata: dict) -> str:
    """Render a measured pilot summary, keeping semantic review separate."""
    def cell(value, pattern="{:,}"):
        return "-" if value is None else pattern.format(value)

    contexts = [r.get("context", {}) for r in results]
    peaks = [c.get("peak_prompt_tokens") for c in contexts if c.get("peak_prompt_tokens")]
    window = metadata.get("context_window")
    lines = ["# AEGIS prompt baseline", "",
             f"Model: `{metadata['model']}`. Profile: `{metadata.get('profile', 'core')}`. "
             f"Runs: {len(results)}.",
             f"Automated scenario passes: {sum(r['passed'] for r in results)}/{len(results)}.",
             "Semantic rubric: pending human review; automated passes are not overall acceptance.",
             f"Median duration: {statistics.median(r['seconds'] for r in results):.1f} seconds.",
             f"Total model requests: {sum(r['requests'] for r in results)}; "
             f"tool calls: {sum(r['tool_calls'] for r in results)}; "
             f"reviewer sessions: {sum(r.get('reviewer_sessions', 0) for r in results)}.",
             f"Unavailable read requests: {sum(r.get('capability_errors', 0) for r in results)}; "
             f"forbidden-action attempts: {sum(r.get('forbidden_actions', 0) for r in results)}. "
             "Unavailable reads are diagnostics; forbidden actions fail the scope check.",
             "Degenerate responses (one short unit repeated over "
             f"{REPETITION_CHARS:,}+ characters): "
             f"{sum(r.get('degenerate_responses', 0) for r in results)} coordinator, "
             f"{sum(r.get('reviewer_degenerate_responses', 0) for r in results)} reviewer.",
             f"Context window: {cell(window)} tokens; median peak prompt: "
             f"{cell(statistics.median(peaks) if peaks else None, '{:,.0f}')}; "
             + "; ".join(f"runs above {threshold:.0%}: "
                         f"{sum(threshold in c.get('above_window_thresholds', []) for c in contexts)}"
                         for threshold in WINDOW_THRESHOLDS) + ".",
             "", "| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | "
                 "Tools | Peak prompt | Window | Prompt total | Output |",
             "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for result, context in zip(results, contexts):
        checks = result["evaluation"]["checks"]
        semantic = result.get("semantic_checks") or []
        lines.append(f"| {result['scenario']} | {result['repeat']} | {result['status']} | "
                     f"{sum(c['passed'] for c in checks)}/{len(checks)} | "
                     + (f"{sum(c['passed'] for c in semantic)}/{len(semantic)}" if semantic
                        else "-")
                     + f" | {result['seconds']:.1f} | {result['tool_calls']} | "
                     f"{cell(context.get('peak_prompt_tokens'))} | "
                     f"{cell(context.get('peak_window_fraction'), '{:.0%}')} | "
                     f"{cell(context.get('total_prompt_tokens'))} | "
                     f"{cell(context.get('completion_tokens'))} |")
    lines.extend(["", "## Failed automatic checks", ""])
    for result in results:
        failed = [c["id"] for c in result["evaluation"]["checks"] if not c["passed"]]
        if failed or result["status"] != "completed":
            lines.append(f"- {result['scenario']} / {result['repeat']}: "
                         + ", ".join(failed or [result["status"]]))
    lines.extend(["", "## Failed semantic checks", "",
                  "Semantic checks are deterministic proxies reported beside the strict "
                  "checks; they never change a strict pass.", ""])
    for result in results:
        failed = [f"{c['id']} ({c['detail']})" if c["detail"] else c["id"]
                  for c in result.get("semantic_checks") or [] if not c["passed"]]
        if failed:
            lines.append(f"- {result['scenario']} / {result['repeat']}: " + "; ".join(failed))
    lines.extend(["", "## Pass rate by case", "",
                  "| Scenario | Strict passes | Semantic passes |", "|---|---:|---:|"])
    for scenario, rate in pass_rates(results).items():
        lines.append(f"| {scenario} | {rate['strict']} | {rate['semantic']} |")
    reads: dict[str, dict] = {}
    for context in contexts:
        for item in context.get("reads", []):
            entry = reads.setdefault(item["path"], {"reads": 0, "tokens": 0, "chars": 0})
            for key in ("reads", "tokens", "chars"):
                entry[key] += item[key]
    lines.extend(["", "## Most expensive reads", "",
                  "| Path | Reads | Tokens | Tokens per read | Characters |",
                  "|---|---:|---:|---:|---:|"])
    for path, entry in sorted(reads.items(), key=lambda item: -item[1]["tokens"])[:12]:
        lines.append(f"| `{path}` | {entry['reads']} | {entry['tokens']:,} | "
                     f"{entry['tokens'] // max(entry['reads'], 1):,} | {entry['chars']:,} |")
    reviewers = ("Reviewer sessions are fresh local sessions with the same model and endpoint."
                 if metadata.get("profile") == "capabilities" else
                 "Reviewer findings are scripted inputs; independent reviewer quality is not measured.")
    lines.extend(["", "## Limits", "",
        "This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.",
        reviewers,
        "One-stage sessions do not establish full-workflow completion or statistical reliability.",
        "Missing token usage remains unknown. Repeated input tokens include conversation replay.",
        "Read costs share each request's prompt growth among its tool results by length.",
        "Server sampling defaults, hardware and load can affect results even at temperature zero.",
        "No prompt changes are made by the harness.", ""])
    return "\n".join(lines)


def archive(output: Path, work: Path, payload: Path,
            sources: list[Path] | None = None) -> None:
    """Preserve replayable evidence, omitting Git internals and caches.

    sources: Harness, scenario, profile and role files the run depended on,
            stored under their repository paths. Without them the archive
            keeps the original two-file harness layout used by the
            subscription transport.
    """
    with zipfile.ZipFile(output / "evidence.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for base, prefix in ((work, "runs"), (payload, "payload")):
            for name in files(base):
                bundle.write(base / name, f"{prefix}/{name}")
        if sources is None:
            bundle.write(Path(__file__), "harness/evaluate_aegis_prompts.py")
            bundle.write(SUITE, "harness/scenarios.json")
            return
        for source in sources:
            bundle.write(source, "harness/" + source.relative_to(ROOT).as_posix())


def execute(args) -> int:
    """Establish a live baseline only after verifying the requested model."""
    profile = PROFILES[getattr(args, "profile", "core")](args.payload)
    cases = json.loads(profile["suite"].read_text("utf-8"))["scenarios"]
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
    sources = {source.relative_to(ROOT).as_posix(): digest(source.read_bytes())
               for source in profile["sources"]}
    metadata = {"schema": 1, "harness_version": HARNESS_VERSION,
                "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "profile": profile["name"],
                "model": args.model, "base_url": args.base_url,
                "temperature": args.temperature,
                **{key: getattr(args, key, None) for key in SAMPLING},
                "max_tokens": args.max_tokens,
                "max_turns": args.max_turns, "request_timeout": args.request_timeout,
                "run_timeout": args.run_timeout,
                "review_timeout": (getattr(args, "review_timeout", None)
                                   if profile["name"] == "capabilities" else None),
                "repeats": args.repeats,
                "python": platform.python_version(), "platform": platform.platform(),
                "source_commit": git(ROOT, "rev-parse", "HEAD"),
                "payload_files": payload_hashes,
                "suite_sha256": digest(profile["suite"].read_bytes()),
                "harness_sha256": digest(Path(__file__).read_bytes()),
                "sources": sources,
                "system_sha256": digest(profile["system"].encode()),
                "host_contract_sha256": digest(json.dumps(
                    [profile["contract"], profile["contract_tools"]], sort_keys=True).encode()),
                # payload properties, recorded rather than compared
                "entry_sha256": digest(bootstrap_text(args.payload).encode()),
                "aegis_commands": list(aegis_commands(args.payload)),
                "scenario_ids": [c["id"] for c in cases]}
    metadata["server_model"] = server_model(args.base_url, args.model)
    configured = getattr(args, "context_window", None)
    metadata["context_window"] = configured or loaded_window(metadata["server_model"])
    dump(args.output / "manifest.json", metadata)
    results = []
    for repeat in range(1, args.repeats + 1):
        for case in cases:
            name = f"{case['id']}-{repeat}"
            run_dir = args.work_dir / name
            run_dir.mkdir()
            root = run_dir / "repo"
            print(f"START {name}", flush=True)
            initial = profile["prepare"](root, args.payload, case)
            result = run_case(root, case, initial, args, run_dir, profile,
                              metadata["context_window"])
            if configured is None:
                # a just-in-time server reports the loaded length only once the
                # model serves requests; observe it after every case
                observed = loaded_window(server_model(args.base_url, args.model))
                if observed:
                    result["context"] = with_window(result["context"], observed)
                    dump(run_dir / "result.json", result)
                    if metadata["context_window"] is None:
                        metadata["context_window"] = observed
                    elif observed != metadata["context_window"]:
                        metadata["context_window_varied"] = True
                    dump(args.output / "manifest.json", metadata)
            result["repeat"] = repeat
            results.append(result)
            dump(args.output / "results.json", results)
            write(args.output / "report.md", report(results, metadata))
            print(f"DONE {name} {result['status']} pass={result['passed']} "
                  f"seconds={result['seconds']} "
                  f"peak_prompt={result['context']['peak_prompt_tokens']}", flush=True)
    if files(args.payload) != payload_hashes:
        raise ValueError("source payload changed during evaluation; baseline is invalid")
    if any(digest((ROOT / name).read_bytes()) != value for name, value in sources.items()):
        raise ValueError("harness or scenarios changed during evaluation; baseline is invalid")
    archive(args.output, args.work_dir, args.payload, profile["sources"])
    dump(args.output / "evidence.sha256.json",
         {"evidence.zip": digest((args.output / "evidence.zip").read_bytes())})
    return 0 if all(r["passed"] for r in results) else 1


def compare(left: Path, right: Path) -> dict:
    """Refuse unlike experiments before comparing automated outcomes."""
    old = json.loads((left / "manifest.json").read_text("utf-8"))
    new = json.loads((right / "manifest.json").read_text("utf-8"))
    controls = ("harness_version", "profile", "model", "temperature", *SAMPLING,
                "max_tokens", "max_turns", "repeats",
                "request_timeout", "run_timeout", "review_timeout", "server_model",
                "context_window", "suite_sha256", "harness_sha256", "sources",
                "host_contract_sha256", "scenario_ids")
    def control(manifest: dict, key: str):
        value = manifest.get(key)
        return server_identity(value) if key == "server_model" else value

    differences = [key for key in controls if control(old, key) != control(new, key)]
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

    def median_context(runs: list[dict], key: str):
        values = [r.get("context", {}).get(key) for r in runs]
        known = [v for v in values if isinstance(v, (int, float))]
        return statistics.median(known) if known else None

    def semantic_total(runs: list[dict]) -> str:
        graded = [r["semantic_passed"] for r in runs if r.get("semantic_passed") is not None]
        return f"{sum(graded)}/{len(graded)}" if graded else "-"

    rates_before, rates_after = pass_rates(before), pass_rates(after)

    return {"automated_regressions": [
        {"scenario": r["scenario"], "repeat": r["repeat"]} for r in after
        if indexed[(r["scenario"], r["repeat"])]["passed"] and not r["passed"]],
        "passes_before": sum(r["passed"] for r in before),
        "passes_after": sum(r["passed"] for r in after),
        "median_seconds_before": statistics.median(r["seconds"] for r in before),
        "median_seconds_after": statistics.median(r["seconds"] for r in after),
        "median_peak_prompt_before": median_context(before, "peak_prompt_tokens"),
        "median_peak_prompt_after": median_context(after, "peak_prompt_tokens"),
        "median_total_prompt_before": median_context(before, "total_prompt_tokens"),
        "median_total_prompt_after": median_context(after, "total_prompt_tokens"),
        "case_pass_rates": {scenario: {"before": rates_before[scenario],
                                       "after": rates_after.get(scenario)}
                            for scenario in rates_before},
        "semantic_passes_before": semantic_total(before),
        "semantic_passes_after": semantic_total(after),
        "semantic_acceptance": "requires reviewed rubric; not inferred"}


def main(argv: list[str] | None = None) -> int:
    """Run/list scenarios or compare two compatible saved experiments."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list")
    listing.add_argument("--profile", choices=sorted(PROFILES), default="core")
    run = sub.add_parser("run")
    run.add_argument("--base-url", required=True, help="For example http://localhost:1234/v1")
    run.add_argument("--model", required=True)
    run.add_argument("--profile", choices=sorted(PROFILES), default="core",
                     help="core: ten frame/task/validate cases; capabilities: eighteen "
                          "specify/design/build/deliver/adopt/review/context cases, including "
                          "a chained four-session adoption; holdout: "
                          "the pricing domain, including a chained five-session lifecycle")
    run.add_argument("--payload", type=Path, default=PAYLOAD)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--work-dir", type=Path, required=True)
    run.add_argument("--cases", default="")
    run.add_argument("--repeats", type=int, default=2)
    run.add_argument("--max-turns", type=int, default=40)
    run.add_argument("--max-tokens", type=int, default=16384,
                     help="Generated tokens per reply, including reasoning (default: %(default)s)")
    run.add_argument("--temperature", type=float, default=0.0)
    run.add_argument("--top-p", type=float, default=None,
                     help="Sent only when set; use the model's recommended sampling")
    run.add_argument("--top-k", type=int, default=None, help="Sent only when set")
    run.add_argument("--presence-penalty", type=float, default=None,
                     help="Sent only when set; -2 to 2, positive values discourage repetition")
    run.add_argument("--reasoning-effort", choices=["low", "medium", "high", "xhigh"], default=None,
                     help="Sent only when set; turns on the model's thinking where the server "
                          "supports it. The reasoning is never sent back with the history")
    run.add_argument("--context-window", type=int, default=None,
                     help="Loaded context in tokens when the server does not report it")
    run.add_argument("--request-timeout", type=float, default=900)
    run.add_argument("--run-timeout", type=float, default=2400)
    run.add_argument("--review-timeout", type=float, default=900,
                     help="Bound for each local reviewer session (capabilities profile)")
    diff = sub.add_parser("compare")
    diff.add_argument("baseline", type=Path)
    diff.add_argument("candidate", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            suite = PROFILES[args.profile]()["suite"]
            for case in json.loads(suite.read_text("utf-8"))["scenarios"]:
                print(f"{case['id']}\t{case['stage']}")
            return 0
        if args.command == "compare":
            print(json.dumps(compare(args.baseline, args.candidate), indent=2))
            return 0
        if min(args.repeats, args.max_turns, args.max_tokens,
               args.request_timeout, args.run_timeout, args.review_timeout) <= 0:
            raise ValueError("run limits must be positive")
        if args.top_p is not None and not 0 < args.top_p <= 1:
            raise ValueError("top-p must be in (0, 1]")
        if args.top_k is not None and args.top_k < 1:
            raise ValueError("top-k must be positive")
        if args.presence_penalty is not None and not -2 <= args.presence_penalty <= 2:
            raise ValueError("presence penalty must be in [-2, 2]")
        if args.context_window is not None and args.context_window <= 0:
            raise ValueError("context window must be positive")
        args.payload = args.payload.resolve()
        args.output = args.output.resolve()
        args.work_dir = args.work_dir.resolve()
        return execute(args)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"evaluation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
