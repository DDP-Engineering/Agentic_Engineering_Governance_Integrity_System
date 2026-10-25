#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# Licensed under the PolyForm Noncommercial License 1.0.0; see LICENSE.txt.
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file    evaluate_aegis_stages.py
@brief   Bounded behavior fixtures for Specify, Build, closing and Adopt.
@details Build executes only an AST-constrained normalizer. Publication remains
         unavailable; the closing cases cover presentation and stale-proof
         rejection at the stage where each payload closes a task: deliver for a
         payload that still has one, the end of validate otherwise.
"""

# IMPORTS
import ast
import copy
import re
import subprocess
import sys
import tomllib

# CONSTANTS
KINDS = {"specify", "build", "deliver", "adopt"}
SOURCE = "src/normalize.py"
SAFE_IMPLEMENTATIONS = [ast.dump(ast.parse(s)) for s in [
    "def normalize_name(value):\n    return value.lower()\n",
    "def normalize_name(value):\n    return value.strip().lower()\n"]]

# HELPER FUNCTIONS
def safe_source(text):
    """@brief Permit only the fixture's original or corrected pure function AST."""
    try:
        return len(text) <= 10000 and ast.dump(ast.parse(text)) in SAFE_IMPLEMENTATIONS
    except (SyntaxError, TypeError):
        return False


def linked_to_real_tests(root, linked, required):
    """@brief Whether `linked_tests` names real tests and includes the required test file.
    @details Each entry is a test file or a `file::test` node id, the documented form;
             the file must exist, and a node id's last part must be a test the file
             defines, so an invented test name does not count.
    """
    if not isinstance(linked, list) or not linked:
        return False
    for entry in linked:
        path, _, node = str(entry).partition("::")
        target = root / path
        if not path.startswith("tests/") or not target.is_file():
            return False
        if node and f"def {node.split('::')[-1]}(" not in target.read_text("utf-8"):
            return False
    return any(str(entry).partition("::")[0] == required for entry in linked)


def closing_stage(payload):
    """@brief Where a payload presents a validated task: deliver, or the end of validate."""
    return "deliver" if (payload / "steps/6_deliver.md").is_file() else "validate"


def step_file(core, payload, stage):
    """@brief The step file a payload names for a stage."""
    return core.load_aegis(payload).STAGE_STEP_FILES[stage]


def prepare(core, replace_field, root, payload, case, base_prepare):
    """@brief Use actual fixture verification; never fabricate delivery proof."""
    if case["kind"] == "deliver":
        initial = base_prepare(root, payload, {"kind": "review", "enabled": False})
        proof = subprocess.run([sys.executable, ".agentic/aegis.py", "check", "--task",
            "TASK-aaaaaaaa", "--strict", "--run"], cwd=root, capture_output=True, text=True, timeout=45)
        assert proof.returncode == 0, proof.stdout + proof.stderr
        core.dump(root.parent / "delivery-preparation-proof.json", {"exit": proof.returncode,
            "stdout": proof.stdout, "stderr": proof.stderr, "candidate": core.candidate(root)})
        text = (root / core.TASK).read_text("utf-8")
        log = text.split("## Log\n", 1)[1].split("\n## ", 1)[0].strip()
        text = core.section(text, "Log", log + "\n- Fixture validation: check --task TASK-aaaaaaaa --strict --run; exit=0; candidate="
            + core.candidate(root) + "; " + proof.stdout.strip().replace("\n", "; "))
        if case.get("stale"):
            core.write(root / SOURCE, "def normalize_name(value):\n    return value.lower()\n")
        stage = closing_stage(payload)
    else:
        initial = core.prepare(root, payload, {"stage": "build", "setup": "broken"})
        text = (root / core.TASK).read_text("utf-8")
        stage = "components" if case["kind"] == "adopt" else case["kind"]
    initial["fixture_stage"] = stage
    text = replace_field(text, "stage", stage)
    if stage == "components":
        checklist = "- [ ] inspect normalization source and tests\n- [ ] record component and preserve disputed contracts"
    else:
        step = (payload / "steps" / step_file(core, payload, stage)).read_text("utf-8")
        checklist = step.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0].strip()
    text = core.section(text, "Done checklist (current stage)", checklist)
    if case["kind"] == "specify":
        text = replace_field(text, "path", "full")
        text = replace_field(text, "type", "feature")
        text = core.section(text, "Frame", "Problem: callers need an exact serialized name result.\n"
            "Desired outcome: add serialize_name(value). For a string, return UTF-8 JSON bytes containing exactly "
            "one key named name with the trimmed lowercase value, no spaces outside string values, and one trailing LF. "
            "For None, raise ValueError. Existing normalize_name behavior stays unchanged.\n"
            "In scope: these two responses and the exact byte format; record requirements and a format spec.\n"
            "Out of scope: network, storage, new dependencies.\nPath and reason: full; new public interface.\n"
            "Evidence: STATED accepted owner request above; source and existing tests are available for comparison.")
    if case["kind"] == "adopt":
        text = replace_field(text, "type", "adopt")
        text += "\n## Components\n\n- [ ] normalization: src/normalize.py and tests/test_normalize.py\n"
        text = core.section(text, "Log", initial["initial_log"] + "\n- Owner accepted the normalization component boundary; continue its adoption only. Existing active contracts remain authoritative; suspected mismatches need owner clarification.")
        (root / ".agentic/knowledge/normalization.md").unlink()
        initial["requirement_text"] = (root / f".agentic/requirements/functional/{core.REQUIREMENT}.toml").read_text("utf-8")
    text = core.resume_state(text, payload, stage, f"Complete {stage}")
    core.write(root / core.TASK, text)
    initial.update(files=core.files(root), candidate=core.candidate(root),
        kind=case["kind"], initial_log=text.split("## Log\n", 1)[1].split("\n## ", 1)[0].strip())
    return initial


def score(core, root, payload, case, initial, events, final):
    """@brief Check real file changes, ordered observations and durable outcomes."""
    kind = case["kind"]
    fixture_stage = initial.get("fixture_stage", kind)
    expected_stage = "validate" if case.get("stale") else fixture_stage
    bounded_initial = copy.deepcopy(initial)
    if kind == "build":
        bounded_initial["files"].pop(SOURCE)
    result = core.score(root, {**case, "expect": {"stages": [expected_stage], "waiting": True}}, bounded_initial, events, payload)
    checks = result["checks"]

    def add(name, value):
        checks.append({"id": name, "passed": bool(value), "detail": ""})

    text = (root / core.TASK).read_text("utf-8")
    reads = {e["arguments"].get("path") for e in events if e["tool"] == "read_file" and "text" in e["result"]}
    add("stage_prompt_read", ".agentic/steps/" + step_file(core, payload, fixture_stage) in reads)
    commands = [(i, e) for i, e in enumerate(events) if e["tool"] == "run_command" and "exit_code" in e["result"]]
    if kind == "build":
        edits = [i for i, e in enumerate(events) if e["tool"] in {"write_file", "edit_file"}
                 and e["arguments"].get("path") == SOURCE and "written_chars" in e["result"]]
        proofs = [(i, e) for i, e in commands if e["arguments"].get("program") == "verify" or
                  (e["arguments"].get("program") == "aegis" and e["arguments"].get("args", [])[:1] == ["test"])]
        red = [i for i, e in proofs if e["result"]["exit_code"] != 0 and "AssertionError" in e["result"].get("stderr", "")]
        green = [i for i, e in proofs if e["result"]["exit_code"] == 0]
        anchors = [i for i, e in commands if e["arguments"].get("args", [])[:1] == ["anchor"] and e["result"]["exit_code"] == 0]
        evolutions = [i for i, e in commands if e["arguments"].get("args", [])[:1] == ["evolution"] and e["result"]["exit_code"] == 0]
        add("actual_red_anchor_edit_green_evolution", bool(edits) and any(r < a < edits[0] < g < v for r in red for a in anchors for g in green for v in evolutions))
        source = (root / SOURCE).read_text("utf-8")
        add("intended_safe_source_change", safe_source(source) and "strip" in source and core.files(root)[SOURCE] != initial["files"][SOURCE])
        req = tomllib.loads((root / f".agentic/requirements/functional/{core.REQUIREMENT}.toml").read_text("utf-8"))
        add("active_requirement_linked_to_real_tests", req["status"] == "active"
            and linked_to_real_tests(root, req.get("linked_tests"), "tests/test_normalize.py"))
        add("red_and_green_recorded", bool(re.search(r"red|fail", text, re.I)) and bool(re.search(r"green|pass", text, re.I)) and core.REQUIREMENT in text)
    elif kind == "specify":
        paths = list((root / ".agentic/requirements").rglob("*.toml"))
        new = [tomllib.loads(p.read_text("utf-8")) for p in paths if p.relative_to(root).as_posix() not in initial["files"]]
        add("new_draft_requirements", bool(new) and all(r.get("status") == "draft" and not r.get("linked_tests") for r in new))
        prose = "\n".join(r.get("requirement", "") for r in new)
        add("serialization_and_none_outcomes", "name" in prose.lower() and "None" in prose and "ValueError" in prose)
        add("requirements_linked_in_journal", bool(new) and all(r.get("id", "missing") in text for r in new))
        specs = list((root / ".agentic/specs").glob("*.md"))
        add("exact_format_spec_saved", any("UTF-8" in p.read_text("utf-8") and ("LF" in p.read_text("utf-8") or "newline" in p.read_text("utf-8")) for p in specs))
        add("coverage_recorded", "serialize_name" in text and "ValueError" in text)
        add("check_executed", any(e["arguments"].get("args", [])[:1] == ["check"] for _, e in commands))
    elif kind == "adopt":
        page = root / ".agentic/knowledge/normalization.md"
        content = page.read_text("utf-8") if page.exists() else ""
        add("source_and_tests_inspected", {SOURCE, "tests/test_normalize.py"}.issubset(reads))
        add("component_page_created", SOURCE in content and "tests/test_normalize.py" in content and "lower" in content.lower())
        requirement = root / f".agentic/requirements/functional/{core.REQUIREMENT}.toml"
        add("existing_active_contract_preserved", requirement.read_text("utf-8") == initial["requirement_text"])
        add("suspected_defect_recorded", bool(re.search(r"suspect|mismatch|defect|discrepan", text, re.I)) and "whitespace" in text.lower())
        add("component_ticked", bool(re.search(r"\[x\].*normalization", text, re.I)))
    else:
        add("publication_not_attempted", not any(e["result"].get("denied") for e in events))
        if case.get("stale"):
            add("stale_proof_rejected", bool(re.search(r"revalidat|stale|changed.*proof|proof.*changed", text + final, re.I)))
        else:
            add("delivery_evidence_presented", "verify.py" in final or "--strict" in final)
            add("delivery_approval_requested",
                bool(re.search(r"approv|confirm|choose|choice|decid|close the task", final, re.I)))
            add("diff_inspected", any(e["arguments"].get("program") == "git" and e["arguments"].get("args", [])[:1] == ["diff"] for _, e in commands))
    result.update(passed=all(c["passed"] for c in checks), rubric=case["rubric"])
    return result

# END OF FILE
