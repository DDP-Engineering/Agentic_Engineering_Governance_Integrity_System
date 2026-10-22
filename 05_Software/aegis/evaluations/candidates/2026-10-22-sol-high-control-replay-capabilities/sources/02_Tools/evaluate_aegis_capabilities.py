#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    evaluate_aegis_capabilities.py
@brief   Fixtures and observed checks for live review delegation and design diagrams.
@details Adds a separate capability profile without changing the ten-case core.
         Reviewer processes are supplied by the subscription runner, never scripted.
"""

# IMPORTS
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import tomllib

# CONSTANTS
ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("aegis_eval_core", ROOT / "02_Tools/evaluate_aegis_prompts.py")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)
STAGE_SPEC = importlib.util.spec_from_file_location("aegis_eval_stages", ROOT / "02_Tools/evaluate_aegis_stages.py")
stages = importlib.util.module_from_spec(STAGE_SPEC)
STAGE_SPEC.loader.exec_module(stages)
SUITE = ROOT / "05_Software/aegis/evaluations/capability-scenarios.json"
ROLES = {"aegis-spec-review": "spec_compliance", "aegis-quality-review": "implementation_quality"}
ROLE_DIR = ROOT / "05_Software/aegis/integrations/codex/plugins/aegis/agents"
PROFILE = ROOT / "05_Software/aegis/evaluations/profiles/installed-entry.json"
DIGEST_TOOL = core.tool("candidate_digest", "Read the current evaluation candidate digest; excludes task records.", {}, [])
REVIEW_TOOL = core.tool("delegate_review", "Launch one fresh read-only Codex reviewer session using the named existing AEGIS role. Returns its actual verdict and execution evidence; never edits the coordinator checkout.",
    {"role": {"type": "string", "enum": list(ROLES)}, "task": {"type": "string"},
     "candidate": {"type": "string"}}, ["role", "task", "candidate"])
TOOLS = core.TOOLS + [DIGEST_TOOL, REVIEW_TOOL]
READ_COMMANDS = {"status", "brief", "summary", "components", "explain"}
REVIEW_TOOLS = [t for t in core.TOOLS if t["function"]["name"] in {"list_files", "read_file"}] + [
    core.tool("run_command", "Read-only Git inspection or aegis status, brief, summary, components, explain. No tests, anchors or mutations.",
        {"program": {"type": "string", "enum": ["git", "aegis"]},
         "args": {"type": "array", "items": {"type": "string"}}}, ["program", "args"]), DIGEST_TOOL]

# HELPER FUNCTIONS
def role_prompt(role: str) -> str:
    """@brief Read an existing native role without changing its review criteria."""
    return tomllib.loads((ROLE_DIR / (role + ".toml")).read_text("utf-8"))["developer_instructions"]


def instructions() -> str:
    """@brief Map the native adapter's fresh-agent fallback to bounded test tools."""
    base = core.SYSTEM.replace("network tools, publication and reviewer spawning are unavailable.",
        "network tools and publication are unavailable. Fresh read-only reviewers are available only through delegate_review when configuration enables review.")
    digest = json.loads(PROFILE.read_text("utf-8"))["bootstrap"]["text"]
    skill = ROOT / "05_Software/aegis/integrations/codex/plugins/aegis/skills/aegis/SKILL.md"
    delegation = next(line for line in skill.read_text("utf-8").splitlines() if line.startswith("4. Read `[review]`"))
    return base + ("\nAdditional bounded capabilities: run_command aegis req is available for requirement scaffolds. "
        "Only Build fixtures permit write_file/edit_file on src/normalize.py; this accepts only the original pure "
        "lowercase function or its strip().lower() correction. Existing tests already reproduce the regression; "
        "run_command verify executes them. All other source and tests remain immutable. No publication capability exists.\n") + "\n\nProject instructions:\n" + digest + "\n\nNative adapter review rule:\n" + delegation + (
        "\nThe evaluation exposes the adapter's fresh-agent fallback as delegate_review, one role per call. "
        "candidate_digest replaces the bridge candidate operation. Both roles read the same immutable snapshot, "
        "in independent fresh CLI sessions; their prompts are loaded unchanged from the named role definitions. "
        "Use only the documented MCP tools for repository access and delegation; no native shell, file, web or agent tools. "
        "Supplied historical review fixtures are not fresh reviews. Diagrams use the installed design/diagram instructions.")


def replace_field(text: str, name: str, value: str) -> str:
    return re.sub(rf"(?m)^{re.escape(name)}:.*$", name + ": " + value, text, count=1)


def prepare(root: Path, payload: Path, case: dict) -> dict:
    """@brief Prepare a real, bounded fixture and retain actual preparation proof."""
    if case["kind"] in stages.KINDS:
        initial = stages.prepare(core, replace_field, root, payload, case, prepare)
        core.write(root / "AGENTS.md", json.loads(PROFILE.read_text("utf-8"))["bootstrap"]["text"])
        initial["files"] = core.files(root)
        initial["candidate"] = core.candidate(root)
        return initial
    seed = {"stage": "validate", "setup": "broken" if case["kind"] in {"review", "context"} else "validation"}
    initial = core.prepare(root, payload, seed)
    core.write(root / "AGENTS.md", json.loads(PROFILE.read_text("utf-8"))["bootstrap"]["text"])
    config = root / ".agentic/aegis.toml"
    text = config.read_text("utf-8").replace("max_fix_cycles = 2", "max_fix_cycles = 0")
    if case["kind"] == "review" and case["enabled"]:
        text = text.replace("enabled = false", "enabled = true")
    if case["kind"] == "diagram":
        text += "\n[diagrams]\nenabled = " + str(case["enabled"]).lower() + "\ntypes = " + json.dumps(case["types"]) + "\n"
    if case.get("autopilot"):
        text = text.replace("autopilot = false", "autopilot = true")
    core.write(config, text)
    journal = root / core.TASK
    text = journal.read_text("utf-8")
    if case.get("autopilot"):
        text = replace_field(text, "interaction", "autopilot")
    if case["kind"] in {"review", "context"}:
        # Preparation evidence is executed here, before the fixture's implementation.
        core.write(root / "src/normalize.py", "def normalize_name(value):\n    return value.lower()\n")
        red = subprocess.run([sys.executable, "verify.py"], cwd=root, capture_output=True, text=True, timeout=30)
        assert red.returncode != 0
        text = core.section(text, "Log", f"- {core.DATE} frame: accepted restoration of {core.REQUIREMENT}.\n"
            f"- Fixture preparation red: python verify.py; exit={red.returncode}; surrounding-whitespace assertion fails before fixture implementation.")
        core.write(journal, text)
        anchor = subprocess.run([sys.executable, ".agentic/aegis.py", "anchor", "--task", "TASK-aaaaaaaa"],
            cwd=root, capture_output=True, text=True, timeout=30)
        assert anchor.returncode == 0, anchor.stderr
        core.write(root / "src/normalize.py", "def normalize_name(value):\n    return value.strip().lower()\n")
        green = subprocess.run([sys.executable, "verify.py"], cwd=root, capture_output=True, text=True, timeout=30)
        assert green.returncode == 0
        core.dump(root.parent / "preparation-proof.json", {
            "red": {"exit": red.returncode, "stdout": red.stdout, "stderr": red.stderr},
            "anchor": {"exit": anchor.returncode, "stdout": anchor.stdout},
            "green": {"exit": green.returncode, "stdout": green.stdout, "stderr": green.stderr}})
        text = journal.read_text("utf-8")
        text = core.section(text, "Log", text.split("## Log\n", 1)[1].split("\n## ", 1)[0].strip()
            + f"\n- Fixture preparation green: python verify.py; exit={green.returncode}; existing case, trim and whitespace-only assertions passed after fixture implementation.")
        page = root / ".agentic/knowledge/normalization.md"
        core.write(page, re.sub(r"(?ms)^## Architecture\n.*?(?=^## |\Z)", "", page.read_text("utf-8")))
        if case.get("missing_behavior"):
            text = text.replace("In scope: trim fix and focused tests.", "In scope: trim fix, reject None with ValueError, and focused tests.")
            text = replace_field(text, "requirements", core.REQUIREMENT + ", REQ-FUNC-22222222")
            core.write(root / ".agentic/requirements/functional/REQ-FUNC-22222222.toml",
                f'schema = 1\nid = "REQ-FUNC-22222222"\ntitle = "Reject missing names"\nstatus = "active"\n'
                f'requirement = "None input shall raise ValueError."\nverification = "Run a None-input test expecting ValueError."\n'
                f'affected_paths = ["src/normalize.py"]\nlinked_tests = []\ncreated = "{core.DATE}"\nupdated = "{core.DATE}"\n')
    else:
        text = replace_field(text, "stage", "design")
        text = replace_field(text, "type", "feature")
        text = replace_field(text, "path", "quick" if case.get("skip") else "full")
        design = (payload / "steps/3_design.md").read_text("utf-8")
        done = design.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0].strip()
        text = core.section(text, "Done checklist (current stage)", done)
        if not case.get("skip"):
            requirement = "REQ-FUNC-33333333"
            text = replace_field(text, "requirements", core.REQUIREMENT + ", " + requirement)
            outcome = ("Add asynchronous queued name normalization in one Python process. "
                "src/api.py submit_name accepts a string, creates a job and returns its ID. "
                "src/worker.py consumes queued jobs and calls existing normalize_name. "
                "src/jobs.py owns in-memory states queued, running, done and failed. "
                "A successful job stores the normalized result; a failed job stores its error. "
                "No persistence, network interface or external dependency is requested.")
            text = core.section(text, "Frame", "Problem: callers need asynchronous normalization jobs.\nDesired outcome: " + outcome
                + "\nIn scope: " + outcome + "\nOut of scope: persistence, networking and external dependencies.\nPath and reason: full; new job interface and lifecycle.")
            core.write(root / f".agentic/requirements/functional/{requirement}.toml",
                f'schema = 1\nid = "{requirement}"\ntitle = "Queued normalization"\nstatus = "draft"\n'
                f'requirement = {json.dumps(outcome)}\nverification = "Inspect design coverage for submit, worker, result, failure and lifecycle."\n'
                f'affected_paths = ["src/api.py", "src/worker.py", "src/jobs.py"]\nlinked_tests = []\ncreated = "{core.DATE}"\nupdated = "{core.DATE}"\n')
            text = core.section(text, "Log", f"- {core.DATE} frame: user accepted the queued normalization scope.\n- {core.DATE} specify: requirement prose records the agreed behavior; design is next.")
        text = core.section(text, "Design", "")
        text = core.section(text, "Handoff", f"current: design\nstatus: ready\nnext: Complete design\nmust_read: {core.TASK}\nblockers:")
        text = core.section(text, "Stage report", "stage: design\nresult: in_progress\ncurrent: design\nchanged:\nevidence:\nissues:\nnext: Complete design\nneeds_user: no\nspec_compliance: disabled\nimplementation_quality: disabled\nreview_round:")
    if case["kind"] == "context":
        notes = "## Operator notes\n\nUse the evaluation branch for experiments.\n"
        core.write(root / ".agentic/context/project.md", "# Project\n\nPurpose: normalize supplied names.\nCurrent behavior: input is returned unchanged, including case and surrounding whitespace.\n\n" + notes)
        core.write(root / ".agentic/context/environment.md", "# Environment\n\nVerification: python legacy_verify.py.\nThe legacy verifier is the authoritative verification route.\n\n" + notes)
        initial["context_notes"] = notes.strip()
    core.write(journal, text)
    initial.update(files=core.files(root), candidate=core.candidate(root),
        initial_log=text.split("## Log\n", 1)[1].split("\n## ", 1)[0].strip())
    return initial


class StageHost(core.Host):
    """@brief Extend writes only for a statically constrained Build function."""

    def path(self, name, writable=False):
        target = super().path(name)
        if writable and self.initial.get("kind") == "build" and target.relative_to(self.root).as_posix() == stages.SOURCE:
            return target
        return super().path(name, writable)

    def command(self, program, args):
        # The only mutable executable must satisfy the exact safe AST before any execution.
        if self.initial.get("kind") == "build":
            source = (self.root / stages.SOURCE).read_text("utf-8")
            if not stages.safe_source(source):
                raise PermissionError("fixture implementation violates the safe normalizer AST")
            self.initial = {**self.initial, "files": {**self.initial["files"],
                stages.SOURCE: core.digest(source.encode())}}
        if program == "aegis" and args[:1] == ["req"]:
            if len(args) != 3 or args[1] not in {"functional", "ux", "nfr", "security", "data", "platform", "reliability", "test"}:
                raise PermissionError("req requires one category and one literal title")
            # Keep the core executable/config trust checks, including for this extra command.
            before = self.command("git", ["rev-parse", "HEAD"])
            done = subprocess.run([sys.executable, ".agentic/aegis.py", *args], cwd=self.root,
                capture_output=True, text=True, timeout=45)
            return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr,
                "candidate_before": before["candidate_after"], "candidate_after": core.candidate(self.root)}
        return super().command(program, args)


class CapabilityHost:
    """@brief Preserve core access rules and add role-bound read-only delegation."""

    def __init__(self, root: Path, initial: dict, payload: dict, reviewer=False, delegate=None):
        self.base = StageHost(root, initial, payload)
        self.reviewer, self.delegate = reviewer, delegate
        self.events = self.base.events

    def call(self, name: str, arguments: dict) -> dict:
        """@brief Enforce role limits before executing or dispatching any operation."""
        started = time.monotonic()
        try:
            if name in {"write_file", "edit_file"} and self.base.initial.get("kind") == "build":
                path = self.base.path(arguments["path"])
                if path.relative_to(self.base.root).as_posix() == stages.SOURCE:
                    proposed = arguments.get("content", "") if name == "write_file" else path.read_text("utf-8").replace(arguments.get("old", ""), arguments.get("new", ""), 1)
                    if not stages.safe_source(proposed):
                        raise PermissionError("fixture implementation violates the safe normalizer AST")
            command_ok = (arguments.get("program") == "git" or
                (arguments.get("program") == "aegis" and arguments.get("args", [])[:1] in
                 [[operation] for operation in READ_COMMANDS] and "--run" not in arguments.get("args", [])))
            if self.reviewer and (name in {"write_file", "edit_file", "delegate_review"}
                    or (name == "run_command" and not command_ok)):
                raise PermissionError("reviewer may only read files, inspect Git and read candidate digest")
            if name == "candidate_digest":
                result = {"candidate": core.candidate(self.base.root)}
            elif name == "delegate_review":
                config = tomllib.loads((self.base.root / ".agentic/aegis.toml").read_text("utf-8"))
                if config.get("review", {}).get("enabled") is not True:
                    raise PermissionError("review disabled; no reviewer process launched")
                if arguments.get("role") not in ROLES:
                    raise ValueError("unknown reviewer role")
                reference = arguments.get("task", "")
                match = re.fullmatch(r"(TASK-[0-9a-f]{8})(?:\s*:[\s\S]*)?", reference.strip())
                if (not match or match[1] != "TASK-aaaaaaaa"
                        or set(re.findall(r"TASK-[0-9a-f]{8}", reference)) != {"TASK-aaaaaaaa"}):
                    raise ValueError("task reference must name TASK-aaaaaaaa, optionally followed by a colon and brief")
                if arguments.get("candidate") != core.candidate(self.base.root):
                    raise ValueError("candidate digest does not match the current tree; read candidate_digest again")
                if self.delegate is None:
                    raise ValueError("live review backend unavailable")
                result = self.delegate({**arguments, "task": match[1]})
            else:
                return self.base.call(name, arguments)
        except (ValueError, OSError, KeyError, TypeError) as exc:
            result = {"error": str(exc), "denied": isinstance(exc, PermissionError)}
        self.events.append({"tool": name, "arguments": arguments, "result": result,
                            "seconds": time.monotonic() - started})
        return result


def score(root: Path, case: dict, initial: dict, events: list, payload: Path,
          reviews: list, final: str) -> dict:
    """@brief Check observed sessions and artifacts, separately from semantic grading."""
    if case["kind"] in stages.KINDS:
        return stages.score(core, root, payload, case, initial, events, final)
    expected = {"stages": ["validate"] if case["kind"] in {"review", "context"} else
                ["build" if case.get("transition") else "design"], "waiting": True}
    if case["kind"] in {"review", "context"} and not case["enabled"]:
        expected.update(review_disabled=True, fresh_proof=True)
    result = core.score(root, {**case, "expect": expected}, initial, events, payload)
    checks = result["checks"]

    def add(name, value, detail=""):
        checks.append({"id": name, "passed": bool(value), "detail": detail})

    text = (root / core.TASK).read_text("utf-8")
    aegis = core.load_aegis(payload)
    try:
        report = aegis.parse_stage_report(text)
    except aegis.UserError as exc:
        add("capability_records_valid", False, str(exc))
        return {**result, "passed": False, "rubric": case["rubric"]}
    if case["kind"] == "review":
        launches = [e for e in events if e["tool"] == "delegate_review"]
        if not case["enabled"]:
            add("no_reviewer_activation", not launches and not reviews)
        else:
            complete = [v for v in reviews if v.get("status") == "completed"]
            add("two_real_review_sessions", len(complete) == 2 and {v["role"] for v in complete} == set(ROLES)
                and len({v.get("thread_id") for v in complete}) == 2 and all(v.get("thread_id") for v in complete))
            add("same_unchanged_candidate", len(complete) == 2 and len({v["candidate"] for v in complete}) == 1
                and all(v["candidate"] == core.candidate(root) and v.get("snapshot_unchanged") for v in complete))
            add("independent_read_evidence", len(complete) == 2 and all(v.get("observed_reads")
                and {"src/normalize.py", "tests/test_normalize.py", core.TASK, "AGENTS.md", ".agentic/AGENTS.md",
                     f".agentic/requirements/functional/{core.REQUIREMENT}.toml"}.issubset(v["observed_reads"])
                and v.get("digest_reads", 0) >= 2 and not v.get("denied_actions") and not v.get("native_violations") for v in complete))
            add("verdicts_from_actual_reviewers", len(complete) == 2 and all(report.get(ROLES[v["role"]]) == v.get("verdict") for v in complete)
                and report.get("review_round") == "1")
            if case.get("missing_behavior"):
                add("missing_behavior_detected", any(v.get("verdict") == "changes_required"
                    and re.search(r"None|ValueError", json.dumps(v.get("response", {}))) for v in complete))
            if len(complete) == 2:
                needs_fix = any(v["verdict"] == "changes_required" for v in complete)
                final_proof = [e for e in events if e["tool"] == "run_command"
                    and e["arguments"].get("program") == "aegis" and "--strict" in e["arguments"].get("args", [])
                    and "--run" in e["arguments"].get("args", []) and e["result"].get("exit_code") == 0]
                add("review_policy_respected", report.get("result") == "blocked" and not final_proof if needs_fix
                    else bool(final_proof) and final_proof[-1]["result"].get("candidate_after") == core.candidate(root))
    elif case["kind"] == "context":
        now = core.files(root)
        for filename in ["project.md", "environment.md"]:
            path = ".agentic/context/" + filename
            content = (root / path).read_text("utf-8")
            add(filename + "_updated", now[path] != initial["files"][path])
            add(filename + "_unrelated_notes_preserved", initial["context_notes"] in content)
        project = (root / ".agentic/context/project.md").read_text("utf-8").lower()
        environment = (root / ".agentic/context/environment.md").read_text("utf-8").lower()
        add("project_current_behavior", ("strip" in project or "trim" in project) and "lower" in project
            and "input is returned unchanged" not in project)
        add("environment_current_command", "python verify.py" in environment and "legacy_verify.py" not in environment)
    else:
        add("component_knowledge_unchanged", all(core.files(root).get(p) == value
            for p, value in initial["files"].items() if p.startswith(".agentic/knowledge/")))
        diagram = root / ".agentic/tasks/diagram_TASK-aaaaaaaa.md"
        needed = case["enabled"] and bool(case["types"]) and not case.get("skip")
        match = re.search(r"(?ms)^## Design\n(.*?)(?=^## |\Z)", text)
        design = match.group(1) if match else ""
        add("design_saved", bool(design.strip()))
        if not needed:
            add("no_unrequested_diagrams", not diagram.exists() and "diagram_TASK-" not in design)
        else:
            content = diagram.read_text("utf-8") if diagram.exists() else ""
            blocks = re.findall(r"```mermaid[ \t]*\n(.*?)```", content, re.S)
            add("diagram_artifact_and_link", bool(content) and "diagram_TASK-aaaaaaaa.md" in design)
            for diagram_type, header in [("structure", r"flowchart (?:LR|TD)"), ("sequence", "sequenceDiagram"), ("state", "stateDiagram-v2")]:
                add("generated_" + diagram_type, any(re.match(header, b.strip()) for b in blocks))
            add("structure_change_markers", all(x in content for x in ["classDef added", "classDef changed", "classDef removed", ":::added"]))
            if not case.get("autopilot"):
                summaries = [e["result"].get("stdout", "").strip() for e in events if e["tool"] == "run_command"
                    and e["arguments"].get("program") == "aegis" and e["arguments"].get("args", [])[:1] == ["summary"]]
                summary = summaries[-1] if summaries else ""
                add("diagrams_shown_after_summary", bool(blocks) and bool(summary) and summary in final
                    and all(b.strip() in final for b in blocks)
                    and final.find("```mermaid") > final.find(summary) + len(summary))
        if case.get("autopilot"):
            add("autopilot_recorded", core.load_aegis(payload).parse_journal(text)["header"].get("interaction") == "autopilot")
            if needed:
                add("autopilot_no_diagram_display", not re.search(r"```mermaid", final))
                add("autopilot_diagram_reported", "diagram_TASK-aaaaaaaa.md" in report.get("changed", ""))
    result["passed"] = all(c["passed"] for c in checks)
    result["rubric"] = case["rubric"]
    result["limitations"] = ["Mermaid syntax/rendering is not certified by fence/header checks; manual semantic inspection required."] if case["kind"] == "diagram" else []
    return result

# END OF FILE
