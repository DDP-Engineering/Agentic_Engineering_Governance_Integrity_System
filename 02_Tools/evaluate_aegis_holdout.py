#!/usr/bin/env python3
"""
Hold-out pricing fixtures, a bounded code host and scorers for prompt evaluations.

A second domain that never motivates prompt rules. Its frame, specify and
design cases mirror the core intents with different vocabulary, and one
chained case runs five fresh stage sessions on one repository. Model code
is limited to two files and a restricted Python subset before anything
executes; this bounds accidental damage and is not a security sandbox.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("aegis_eval_core_for_holdout",
                                              ROOT / "02_Tools/evaluate_aegis_prompts.py")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)
SUITE = ROOT / "05_Software/aegis/evaluations/holdout-scenarios.json"
SOURCE = "src/pricing.py"
TESTS = "tests/test_pricing.py"
CODE = (SOURCE, TESTS)
REQUIREMENT = "REQ-FUNC-22222222"
RECALCULATION_REQUIREMENT = "REQ-FUNC-44444444"
CORRECT = "def apply_discount(price_cents, percent):\n    return price_cents * (100 - percent) // 100\n"
BROKEN = ("def apply_discount(price_cents, percent):\n"
          "    return round(price_cents * (100 - percent) / 100)\n")
TEST_TEXT = """import unittest
from src.pricing import apply_discount


class PricingTests(unittest.TestCase):
    def test_rounds_down(self):
        self.assertEqual(apply_discount(995, 10), 895)

    def test_zero_percent(self):
        self.assertEqual(apply_discount(1000, 0), 1000)

    def test_full_discount(self):
        self.assertEqual(apply_discount(1000, 100), 0)
"""
VERIFY = ("import unittest\n"
          "print('FIXTURE_VERIFICATION: unittest', flush=True)\n"
          "suite = unittest.defaultTestLoader.discover('tests')\n"
          "result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
          "raise SystemExit(0 if result.wasSuccessful() else 1)\n")
KNOWLEDGE = f"""# Pricing

## Routing
Discount arithmetic on integer cents: src/pricing.py, tests/test_pricing.py.

## Purpose and boundaries
Compute discounted prices in integer cents. No storage, currency formatting or user interface is implemented.

## Public interface
apply_discount(price_cents: int, percent: int) -> int

## Invariants
Prices are integer cents; a discount rounds down to whole cents.

## Key behaviors
- `{REQUIREMENT}` - Apply percentage discounts.

## Files
- src/pricing.py - discount arithmetic.
- tests/test_pricing.py - rounding, zero and full discounts.
"""
RECALCULATION = ("Recalculate discounted prices once per night in one Python process. "
                 "src/scheduler.py starts one recalculation run per night. src/recalc.py "
                 "applies the existing apply_discount to every stored item and records each "
                 "item's new price or its error. src/store.py owns the in-memory items and the "
                 "run results. A failure for one item does not stop the run. No persistence, "
                 "network interface or external dependency is requested.")
FRAMES = {
    "specify": ("Problem: price labels need an exact text form.\n"
                "Desired outcome: add format_price(cents). For a non-negative integer, return "
                "the text EUR, one space and the amount in euros with exactly two decimals, "
                "followed by one LF; 895 gives 'EUR 8.95' and one LF. For a negative integer, "
                "raise ValueError. Existing apply_discount behavior stays unchanged.\n"
                "In scope: these two responses and the exact text format; record requirements "
                "and a format spec.\n"
                "Out of scope: currency conversion, localization, storage and new dependencies.\n"
                "Evidence: STATED accepted owner request above; source and existing tests are "
                "available for comparison."),
    "design": ("Problem: discounted prices are recalculated by hand.\n"
               f"Desired outcome: {RECALCULATION}\n"
               f"In scope: {RECALCULATION}\n"
               "Out of scope: persistence, networking and external dependencies."),
}
ACCEPTANCE = """from src.pricing import apply_discount
assert apply_discount(995, 10) == 895
assert apply_discount(1000, 0) == 1000
assert apply_discount(1000, 100) == 0
for percent in (-1, 101):
    try:
        apply_discount(1000, percent)
    except ValueError:
        continue
    raise SystemExit(f"accepted percent {percent}")
print("HOLDOUT_ACCEPTANCE: ok")
"""
#: builtins that could reach files, processes, introspection or dynamic code
FORBIDDEN_NAMES = {"eval", "exec", "compile", "open", "input", "__import__", "globals",
                   "locals", "vars", "getattr", "setattr", "delattr", "breakpoint", "exit",
                   "quit", "help", "memoryview", "type", "object", "super", "dir"}
#: syntax a small pure module and its unittest cases need; anything else is refused
ALLOWED_NODES = (
    ast.Module, ast.Expr, ast.Constant, ast.FunctionDef, ast.arguments, ast.arg,
    ast.Return, ast.If, ast.IfExp, ast.Compare, ast.BoolOp, ast.BinOp, ast.UnaryOp,
    ast.Name, ast.Load, ast.Store, ast.Call, ast.keyword, ast.Starred, ast.Raise,
    ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr, ast.Attribute, ast.For,
    ast.While, ast.Break, ast.Continue, ast.Pass, ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.Subscript, ast.Slice, ast.JoinedStr, ast.FormattedValue, ast.ListComp,
    ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.comprehension, ast.Assert,
    ast.Try, ast.ExceptHandler, ast.With, ast.withitem, ast.ClassDef, ast.Import,
    ast.ImportFrom, ast.alias, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv,
    ast.Mod, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq, ast.Lt,
    ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn)
RAISES = {"self.assertRaises", "self.assertRaisesRegex"}


def safe_code(text: str, path: str) -> bool:
    """Accept only the restricted Python subset allowed for model-written code.

    text: Proposed file content.
    path: SOURCE or TESTS; only tests may import unittest and the pricing module.

    Refuses other imports, names or attributes starting with an underscore
    (except `__name__`), dangerous builtins, exponentiation, decorators,
    classes other than unittest cases, and context managers other than
    assertRaises. It bounds accidents in a synthetic repository; it is not
    a security sandbox.
    """
    if not isinstance(text, str) or len(text) > 20000:
        return False
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    tests = path == TESTS
    modules = {"__future__", "src.pricing"} if tests else {"__future__"}
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            return False
        if isinstance(node, ast.Import) and (
                not tests or [alias.name for alias in node.names] != ["unittest"]):
            return False
        if isinstance(node, ast.ImportFrom) and (node.level or node.module not in modules):
            return False
        if isinstance(node, ast.alias) and (node.name.startswith("_")
                                            or (node.asname or "").startswith("_")):
            return False
        if isinstance(node, ast.ClassDef) and (
                not tests or node.decorator_list or node.keywords or len(node.bases) != 1
                or ast.unparse(node.bases[0]) != "unittest.TestCase"):
            return False
        if isinstance(node, ast.FunctionDef) and node.decorator_list:
            return False
        if isinstance(node, ast.With) and (not tests or any(
                not isinstance(item.context_expr, ast.Call)
                or ast.unparse(item.context_expr.func) not in RAISES for item in node.items)):
            return False
        if isinstance(node, ast.Name) and (
                node.id in FORBIDDEN_NAMES or (node.id.startswith("_") and node.id != "__name__")):
            return False
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return False
    return True


def instructions(entry: str | None = None) -> str:
    """Shared core instructions plus this profile's two bounded capabilities.

    entry: The installed root digest; the current payload's by default."""
    return core.instructions(entry) + (
        "\n\nAdditional bounded capabilities: run_command aegis req is available for "
        f"requirement scaffolds. In a Build session, write_file and edit_file may also change "
        f"{SOURCE} and {TESTS}; the host accepts only a restricted Python subset (imports of "
        "unittest and the pricing module, no names or attributes starting with an underscore, "
        "no file, process or dynamic-code builtins). All other source and tests stay immutable.")


def journal(root: Path, payload: Path, aegis, stage: str) -> str:
    """Write TASK-aaaaaaaa at `stage` with its accepted Frame; return its Log."""
    text = aegis.scaffold_template("task.md")
    requirements = (REQUIREMENT if stage == "specify"
                    else f"{REQUIREMENT}, {RECALCULATION_REQUIREMENT}")
    header = {"stage": stage, "type": "feature", "path": "full", "branch": "evaluation",
              "base": core.git(root, "rev-parse", "HEAD"), "requirements": requirements,
              "opened": core.DATE}
    for key, value in header.items():
        text = re.sub(rf"(?m)^{key}:.*$", f"{key}: {value}", text, count=1)
    text = text.replace("# TASK-0000", "# TASK-aaaaaaaa")
    step = (payload / "steps" / aegis.STAGE_STEP_FILES[stage]).read_text("utf-8")
    done = step.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0].strip()
    text = core.section(text, "Done checklist (current stage)", done)
    text = core.section(text, "Frame", FRAMES[stage])
    log = f"- {core.DATE} frame: user accepted the scope; full path for a new interface."
    if stage == "design":
        core.write(root / f".agentic/requirements/functional/{RECALCULATION_REQUIREMENT}.toml",
                   f'schema = 1\nid = "{RECALCULATION_REQUIREMENT}"\n'
                   'title = "Nightly price recalculation"\nstatus = "draft"\n'
                   f"requirement = {json.dumps(RECALCULATION)}\n"
                   'verification = "Inspect design coverage for scheduling, recalculation, '
                   'per-item results and failures."\n'
                   'affected_paths = ["src/scheduler.py", "src/recalc.py", "src/store.py"]\n'
                   f'linked_tests = []\ncreated = "{core.DATE}"\nupdated = "{core.DATE}"\n')
        log += f"\n- {core.DATE} specify: requirement prose records the agreed behavior; design is next."
    text = core.section(text, "Log", log)
    text = core.resume_state(text, payload, stage, f"Complete {stage}")
    core.write(root / core.TASK, text)
    return log


def acceptance(root: Path) -> bool:
    """Run the harness-owned acceptance check on the final pricing source."""
    source = root / SOURCE
    if not source.is_file() or not safe_code(source.read_text("utf-8"), SOURCE):
        return False
    done = subprocess.run([sys.executable, "-c", ACCEPTANCE], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=30,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return done.returncode == 0 and "HOLDOUT_ACCEPTANCE: ok" in done.stdout


def prepare(root: Path, payload: Path, case: dict) -> dict:
    """Create one pricing repository for a hold-out case; never reuse a checkout.

    Returns: Initial file hashes, journal log, immutable Git head and candidate digest.
    """
    root.mkdir(parents=True, exist_ok=False)
    shutil.copytree(payload, root / ".agentic",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    aegis = core.load_aegis(root / ".agentic")
    core.write(root / ".gitignore", "__pycache__/\n*.pyc\n.agentic/tasks/*.json\n")
    core.write(root / ".agentic/aegis.toml", """schema = 1
[commands]
test = "python verify.py"
timeout = 30
[layout]
source = ["src/", "verify.py"]
tests = ["tests/"]
docs = ["README.md"]
default_branch = "master"
[interaction]
autopilot = false
[review]
enabled = false
max_fix_cycles = 2
""")
    core.write(root / "AGENTS.md", core.bootstrap_text(payload))
    core.write(root / "README.md", "# Pricing\n\napply_discount reduces a price in integer "
               "cents by a percentage, rounding down to whole cents.\nVerification: "
               "`python verify.py` (Python standard-library unittest).\n")
    core.write(root / ".agentic/context/project.md",
               "# Project profile\n\n## Purpose and users\n\nCompute discounted prices for a "
               "small shop back office.\n## Implementation orientation\n\n"
               "src/pricing.py; tests/test_pricing.py.\n")
    core.write(root / ".agentic/context/environment.md",
               "# Environment guide\n\n## Verification\n\nPython 3.11+ and Git are ready.\n"
               "Run `python verify.py`; it uses unittest without external dependencies.\n")
    core.write(root / ".agentic/knowledge/pricing.md", KNOWLEDGE)
    core.write(root / f".agentic/requirements/functional/{REQUIREMENT}.toml", f"""schema = 1
id = "{REQUIREMENT}"
title = "Apply percentage discounts"
status = "active"
requirement = "The pricing module shall return the price in cents reduced by the discount percentage, rounded down to whole cents."
verification = "Run python verify.py: apply_discount(995, 10) returns 895, 0 percent keeps the price and 100 percent returns 0."
affected_paths = ["src/pricing.py"]
linked_tests = ["tests/test_pricing.py"]
created = "{core.DATE}"
updated = "{core.DATE}"
""")
    core.write(root / SOURCE, BROKEN if case.get("setup") == "broken" else CORRECT)
    core.write(root / TESTS, TEST_TEXT)
    core.write(root / "verify.py", VERIFY)
    core.git(root, "init", "--initial-branch=master")
    core.git(root, "add", "-A")
    core.git(root, "commit", "-m", "Pricing fixture starting contract")
    core.git(root, "switch", "-c", "evaluation")
    head = core.git(root, "rev-parse", "HEAD")
    log = journal(root, payload, aegis, case["kind"]) if case["kind"] in FRAMES else ""
    return {"files": core.files(root), "head": head, "initial_log": log,
            "candidate": core.candidate(root), "kind": case["kind"]}


class HoldoutHost(core.Host):
    """Core host plus requirement scaffolds and AST-bounded Build code writes."""

    def __init__(self, root: Path, initial: dict, payload: dict, phase: str | None = None):
        super().__init__(root, initial, payload)
        self.phase = phase

    def path(self, name: object, writable: bool = False) -> Path:
        """Allow the two code files to be written only during a Build session."""
        target = super().path(name)
        if writable and self.phase == "build" and target.relative_to(self.root).as_posix() in CODE:
            return target
        return super().path(name, writable)

    def call(self, name: str, arguments: dict) -> dict:
        """Refuse a Build code write outside the restricted subset before writing."""
        if self.phase == "build" and name in {"write_file", "edit_file"}:
            try:
                target = super().path(arguments["path"])
                relative = target.relative_to(self.root).as_posix()
                if relative in CODE:
                    proposed = (arguments.get("content", "") if name == "write_file" else
                                target.read_text("utf-8").replace(
                                    str(arguments.get("old", "")), str(arguments.get("new", "")), 1))
                    if not safe_code(proposed, relative):
                        result = {"error": f"{relative} is outside the restricted Python subset",
                                  "denied": True}
                        self.events.append({"tool": name, "arguments": arguments,
                                            "result": result, "seconds": 0.0})
                        return result
            except (KeyError, ValueError, TypeError, OSError):
                pass  # the base host reports malformed or refused paths itself
        return super().call(name, arguments)

    def command(self, program: str, args: list[str]) -> dict:
        """Check model-written code before anything executes; add requirement scaffolds."""
        trusted = dict(self.initial["files"])
        for relative in CODE:
            target = self.root / relative
            if target.is_file():
                text = target.read_text("utf-8")
                if not safe_code(text, relative):
                    raise PermissionError(f"{relative} is outside the restricted Python subset")
                trusted[relative] = core.digest(text.encode())
        self.initial = {**self.initial, "files": trusted}
        if program == "aegis" and isinstance(args, list) and args[:1] == ["req"]:
            if args[1:] in (["--help"], ["-h"]):
                return super().command(program, args)
            if len(args) > 1 and any(mark in str(args[1]) for mark in ("/", "\\", "..")):
                raise PermissionError("req categories are plain names")
            if len(args) != 3 or not isinstance(args[2], str):
                # a malformed scaffold is a wrong call, not a forbidden one; the
                # evaluated CLI decides which category names, aliases included, exist
                raise core.CapabilityUnavailable(
                    "req takes one category and one literal title; see req --help")
            before = super().command("git", ["rev-parse", "HEAD"])
            done = subprocess.run([sys.executable, ".agentic/aegis.py", *args], cwd=self.root,
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=45,
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            return {"exit_code": done.returncode, "stdout": done.stdout, "stderr": done.stderr,
                    "candidate_before": before["candidate_after"],
                    "candidate_after": core.candidate(self.root)}
        return super().command(program, args)


def score(root: Path, case: dict, initial: dict, events: list, payload: Path,
          reviews: list, final: str) -> dict:
    """Grade one hold-out frame, specify or design case from events and files."""
    result = core.score(root, case, initial, events, payload)
    if result.get("rubric") is None:
        return {**result, "rubric": case["rubric"]}
    checks = result["checks"]

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"id": name, "passed": bool(passed), "detail": detail})

    reads = {e["arguments"].get("path") for e in events
             if e["tool"] == "read_file" and "text" in e["result"]}
    text = core.journal_text(root)
    if case["kind"] == "specify":
        new = core.new_requirements(root, initial)
        add("stage_prompt_read", ".agentic/steps/2_specify.md" in reads)
        add("new_draft_requirements", bool(new) and all(
            r.get("status") == "draft" and not r.get("linked_tests") for r in new))
        add("requirements_linked_in_journal",
            bool(new) and all(str(r.get("id", "missing")) in text for r in new))
        specs = [p.read_text("utf-8") for p in (root / ".agentic/specs").glob("*.md")]
        add("exact_format_spec_saved", any(
            "EUR" in s and ("LF" in s or "newline" in s.lower() or "\\n" in s) for s in specs))
        contract = f".agentic/requirements/functional/{REQUIREMENT}.toml"
        add("existing_contract_unchanged",
            core.files(root).get(contract) == initial["files"].get(contract))
        add("check_executed", any(e["tool"] == "run_command" and "exit_code" in e["result"]
                                  and e["arguments"].get("args", [])[:1] == ["check"]
                                  for e in events))
    elif case["kind"] == "design":
        add("stage_prompt_read", ".agentic/steps/3_design.md" in reads)
        add("design_saved", bool(core.section_text(text, "Design")))
        add("component_knowledge_unchanged", all(
            core.files(root).get(p) == value for p, value in initial["files"].items()
            if p.startswith(".agentic/knowledge/")))
        add("no_unrequested_diagrams", not any((root / ".agentic/tasks").glob("diagram_*.md")))
    result["passed"] = all(c["passed"] for c in checks)
    return result


def score_chain(root: Path, case: dict, initial: dict, events: list, payload: Path,
                sessions: list, final: str) -> dict:
    """Grade a chained case on the integrated result that all sessions left.

    Build may change the two code files, so they leave the protected set;
    everything else follows the core checks across every session's events.
    """
    bounded = {**initial, "files": {p: h for p, h in initial["files"].items() if p not in CODE}}
    result = core.score(root, case, bounded, events, payload)
    checks = result["checks"]

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"id": name, "passed": bool(passed), "detail": detail})

    add("all_sessions_completed",
        len(sessions) == len(case["chain"]) and all(s["status"] == "completed" for s in sessions),
        "; ".join(f"{s['stage']}={s['status']}" for s in sessions))
    new = core.new_requirements(root, initial)

    def linked(test: str) -> bool:
        return (root / str(test).split("::", 1)[0]).is_file()

    add("error_requirement_active_and_linked", any(
        "ValueError" in r.get("requirement", "") and r.get("status") == "active"
        and r.get("linked_tests") and all(linked(t) for t in r["linked_tests"]) for r in new))
    try:
        existing = tomllib.loads((root / f".agentic/requirements/functional/{REQUIREMENT}.toml")
                                 .read_text("utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        existing = {}
    add("existing_contract_active", existing.get("status") == "active")
    add("hidden_acceptance", acceptance(root))
    commands = [(i, e) for i, e in enumerate(events)
                if e["tool"] == "run_command" and "exit_code" in e["result"]]
    edits = [i for i, e in enumerate(events) if e["tool"] in {"write_file", "edit_file"}
             and e["arguments"].get("path") == SOURCE and "written_chars" in e["result"]]
    runs = [(i, e) for i, e in commands if e["arguments"].get("program") == "verify"
            or (e["arguments"].get("program") == "aegis"
                and e["arguments"].get("args", [])[:1] == ["test"])]
    red = [i for i, e in runs if e["result"]["exit_code"] != 0]
    green = [i for i, e in runs if e["result"]["exit_code"] == 0]
    anchors = [i for i, e in commands if e["arguments"].get("args", [])[:1] == ["anchor"]
               and e["result"]["exit_code"] == 0]
    evolutions = [i for i, e in commands if e["arguments"].get("args", [])[:1] == ["evolution"]
                  and e["result"]["exit_code"] == 0]
    add("red_anchor_edit_green_evolution", bool(edits) and any(
        r < a < edits[0] < g < v for r in red for a in anchors for g in green for v in evolutions))
    proofs = [e for _, e in commands if e["arguments"].get("program") == "aegis"
              and {"--strict", "--run"} <= set(e["arguments"].get("args", []))
              and e["result"]["exit_code"] == 0]
    add("final_proof_current",
        bool(proofs) and proofs[-1]["result"].get("candidate_after") == core.candidate(root))
    result.update(passed=all(c["passed"] for c in checks), rubric=case["rubric"])
    return result
