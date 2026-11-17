#!/usr/bin/env python3
"""
Adoption fixtures and checks: survey, close and the chained adoption.

Each case gets a small existing order-totals library with two components
and their tests, installed but not yet adopted. Source and tests stay
immutable: adoption describes a repository, it never rewrites it.
"""

import fnmatch
import json
import re
import shutil
import subprocess
import sys

KINDS = {"adopt_survey", "adopt_close", "adopt_chain"}
SOURCES = ("src/orders/parse.py", "src/orders/totals.py")
TESTS = ("tests/test_parse.py", "tests/test_totals.py")
TASK = ".agentic/tasks/TASK-aaaaaaaa.md"
STALE_FACT = "Totals are computed in floating-point euros."
FILES = {
    "README.md": "# Order totals\n\nParses order lines `SKU,quantity,unit price in cents` and "
                 "computes order totals in integer cents, with an optional voucher.\n"
                 "Verification: `python verify.py` (Python standard-library unittest).\n",
    "src/__init__.py": "",
    "src/orders/__init__.py": "",
    SOURCES[0]: ('def parse_line(line):\n'
                 '    sku, quantity, price = [part.strip() for part in line.split(",")]\n'
                 '    if not sku:\n'
                 '        raise ValueError("missing SKU")\n'
                 '    return sku.upper(), int(quantity), int(price)\n'),
    SOURCES[1]: ('def order_total(lines):\n'
                 '    return sum(quantity * price for _sku, quantity, price in lines)\n\n\n'
                 'def apply_voucher(total, voucher):\n'
                 '    return max(0, total - voucher)\n'),
    TESTS[0]: ('import unittest\nfrom src.orders.parse import parse_line\n\n\n'
               'class ParseTests(unittest.TestCase):\n'
               '    def test_fields_are_trimmed_and_sku_uppercased(self):\n'
               '        self.assertEqual(parse_line(" ab-1 , 2 , 150 "), ("AB-1", 2, 150))\n\n'
               '    def test_missing_sku_is_rejected(self):\n'
               '        with self.assertRaises(ValueError):\n'
               '            parse_line(" ,1,100")\n'),
    TESTS[1]: ('import unittest\nfrom src.orders.totals import apply_voucher, order_total\n\n\n'
               'class TotalsTests(unittest.TestCase):\n'
               '    def test_total_sums_quantity_times_price(self):\n'
               '        self.assertEqual(order_total([("A", 2, 150), ("B", 1, 99)]), 399)\n\n'
               '    def test_voucher_never_makes_a_total_negative(self):\n'
               '        self.assertEqual(apply_voucher(300, 500), 0)\n'
               '        self.assertEqual(apply_voucher(300, 100), 200)\n'),
    "verify.py": ("import unittest\nprint('FIXTURE_VERIFICATION: unittest', flush=True)\n"
                  "suite = unittest.defaultTestLoader.discover('tests')\n"
                  "result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
                  "raise SystemExit(0 if result.wasSuccessful() else 1)\n"),
}
CONFIG = """schema = 1
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
"""
PARSING_PAGE = """# Order line parsing

## Routing
Parsing one order line: src/orders/parse.py, tests/test_parse.py.

## Purpose and boundaries
Turn one `SKU,quantity,unit price in cents` line into a typed tuple.

## Public interface
parse_line(line: str) -> tuple[str, int, int]

## Key behaviors
- `REQ-FUNC-aaaa0001` - Fields are trimmed and the SKU is uppercased.

## Files
- src/orders/parse.py - the parser.
- tests/test_parse.py - trimming and missing-SKU cases.
"""
TOTALS_PAGE = """# Order totals

## Routing
Order sums and vouchers: src/orders/totals.py, tests/test_totals.py.

## Purpose and boundaries
Sum parsed order lines in integer cents and apply a voucher.

## Public interface
order_total(lines) -> int; apply_voucher(total: int, voucher: int) -> int

## Key behaviors
- `REQ-FUNC-aaaa0002` - The total sums quantity times unit price.
- `REQ-FUNC-aaaa0003` - A voucher never makes a total negative.

## Files
- src/orders/totals.py - totals and voucher.
- tests/test_totals.py - sum and voucher floor cases.
"""
REQUIREMENTS = {
    "REQ-FUNC-aaaa0001": ("Parse order lines", "Parsing shall trim every field and uppercase the SKU.",
                          SOURCES[0], TESTS[0] + "::test_fields_are_trimmed_and_sku_uppercased", ""),
    "REQ-FUNC-aaaa0002": ("Sum order lines", "The order total shall be the sum of quantity times unit price in cents.",
                          SOURCES[1], TESTS[1] + "::test_total_sums_quantity_times_price", ""),
    # The missing spec is the planted error close must fix forward.
    "REQ-FUNC-aaaa0003": ("Voucher floor", "Applying a voucher shall never produce a negative total.",
                          SOURCES[1], TESTS[1] + "::test_voucher_never_makes_a_total_negative",
                          "specs/voucher-rounding.md"),
}


def run_aegis(root, *args):
    """Run the fixture's own installed CLI; preparation must succeed."""
    done = subprocess.run([sys.executable, ".agentic/aegis.py", *args], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", timeout=60, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def requirement_text(core, rid):
    title, prose, path, test, spec = REQUIREMENTS[rid]
    return (f'schema = 1\nid = "{rid}"\ntitle = "{title}"\nstatus = "active"\n'
            f"requirement = {json.dumps(prose)}\nverification = \"Run python verify.py.\"\n"
            f'affected_paths = ["{path}"]\nlinked_tests = ["{test}"]\n'
            + (f'spec = "{spec}"\n' if spec else "")
            + f'created = "{core.DATE}"\nupdated = "{core.DATE}"\n')


def prepare(core, root, payload, case):
    """Install the payload in an existing, unadopted repository at the case's phase."""
    root.mkdir(parents=True, exist_ok=False)
    shutil.copytree(payload, root / ".agentic", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    core.write(root / ".gitignore", "__pycache__/\n*.pyc\n")
    core.write(root / ".agentic/aegis.toml", CONFIG)
    for name, text in FILES.items():
        core.write(root / name, text)
    run_aegis(root, "init")  # what the developer did when installing AEGIS
    if case["kind"] == "adopt_survey":
        core.write(root / ".agentic/knowledge/parsing.md", PARSING_PAGE.replace(
            "- `REQ-FUNC-aaaa0001` - Fields are trimmed and the SKU is uppercased.\n",
            "- Fields are trimmed and the SKU is uppercased.\n"))
    core.git(root, "init", "--initial-branch=master")
    core.git(root, "add", "-A")
    core.git(root, "commit", "-m", "Order totals before adoption")
    core.git(root, "switch", "-c", "evaluation")
    head = core.git(root, "rev-parse", "HEAD")
    log = ""
    if case["kind"] == "adopt_close":
        log = close_fixture(core, root, payload, head)
    return {"files": core.files(root), "head": head, "initial_log": log,
            "candidate": core.candidate(root), "kind": case["kind"], "initialized": True}


def close_fixture(core, root, payload, head):
    """Every component adopted; one requirement error and one stale context fact remain."""
    aegis = core.load_aegis(payload)
    core.write(root / ".agentic/knowledge/parsing.md", PARSING_PAGE)
    core.write(root / ".agentic/knowledge/totals.md", TOTALS_PAGE)
    for rid in REQUIREMENTS:
        core.write(root / f".agentic/requirements/functional/{rid}.toml", requirement_text(core, rid))
    project = root / ".agentic/context/project.md"
    core.write(project, project.read_text("utf-8").rstrip() + "\n\n" + STALE_FACT + "\n")
    text = aegis.scaffold_template("task.md")
    for key, value in {"stage": "components", "type": "adopt", "branch": "evaluation",
                       "base": head, "opened": core.DATE}.items():
        text = re.sub(rf"(?m)^{key}:.*$", f"{key}: {value}", text, count=1)
    text = text.replace("# TASK-0000 — <one-line title>", "# TASK-aaaaaaaa - Adopt order totals")
    done = (root / ".agentic/steps/adopt.md").read_text("utf-8")
    done = done.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0].strip()
    lines = done.splitlines()
    items = [i for i, line in enumerate(lines) if line.startswith("- [ ]")]
    for i in items[:-2]:  # an item may wrap over lines; the last two belong to close
        lines[i] = lines[i].replace("- [ ]", "- [x]", 1)
    text = core.section(text, "Done checklist (current stage)", "\n".join(lines))
    log = (f"- {core.DATE} survey: owner agreed the component list: parsing, totals.\n"
           f"- {core.DATE} components: parsing adopted; REQ-FUNC-aaaa0001 linked to its test.\n"
           f"- {core.DATE} components: totals adopted; REQ-FUNC-aaaa0002 and REQ-FUNC-aaaa0003 linked.")
    text = core.section(text, "Log", log)
    text = text.rstrip("\n") + ("\n\n## Components\n\n"
                                "- [x] parsing: src/orders/parse.py, tests/test_parse.py\n"
                                "- [x] totals: src/orders/totals.py, tests/test_totals.py\n")
    text = core.resume_state(text, payload, "components", "Close the adoption", waiting=True)
    core.write(root / TASK, text)
    return log


def component_items(core, text):
    """The `## Components` checklist as (ticked, item) pairs; indented lines belong to the item above."""
    items = []
    for line in core.section_text(text, "Components").splitlines():
        match = re.match(r"\s*-\s*\[([ xX])\]\s*(.+)$", line)
        if match:
            items.append((match.group(1).lower() == "x", match.group(2)))
        elif items and line[:1] in (" ", "\t") and line.strip():
            items[-1] = (items[-1][0], items[-1][1] + " " + line.strip())
    return items


def covers(item, path):
    """Whether one checklist item names `path` literally, by its folder or by a glob."""
    for token in re.findall(r"[\w.*-]+(?:/[\w.*-]*)+", item):
        if path == token or fnmatch.fnmatchcase(path, token):
            return True
        if not any(c in token for c in "*?") and token.endswith("/") and path.startswith(token):
            return True
    return False


def findings(root):
    """`check --json` over the whole tree, read from the fixture's own CLI."""
    done = subprocess.run([sys.executable, ".agentic/aegis.py", "check", "--json"], cwd=root,
                          capture_output=True, text=True, encoding="utf-8", timeout=60, check=False)
    try:
        return json.loads(done.stdout)["findings"]
    except (ValueError, KeyError):
        return [{"level": "ERROR", "check": "unreadable", "message": done.stderr}]


def new_requirements_ok(core, root, initial):
    """New requirements: all active, linked to tests that exist, covering both components."""
    new = core.new_requirements(root, initial)

    def real(entry):
        path, _, node = str(entry).partition("::")
        target = root / path
        return (path.startswith("tests/") and target.is_file()
                and (not node or f"def {node.split('::')[-1]}(" in target.read_text("utf-8")))

    linked = bool(new) and all(r.get("status") == "active" and r.get("linked_tests")
                               and all(real(t) for t in r["linked_tests"]) for r in new)
    paths = [p for r in new for p in r.get("affected_paths", [])]
    return linked, all(any(p == s or s.startswith(p.rstrip("/") + "/") for p in paths) for s in SOURCES)


def page_mentions(root, initial, path, new_only=False):
    """Whether a component knowledge page names `path`."""
    pages = sorted((root / ".agentic/knowledge").glob("*.md"))
    return any(path in p.read_text("utf-8") for p in pages
               if not new_only or p.relative_to(root).as_posix() not in initial["files"])


def score(core, root, case, initial, events, payload):
    """Grade one survey or close session from its files and observed commands."""
    stage = "survey" if case["kind"] == "adopt_survey" else "close"
    result = core.score(root, {**case, "expect": {"stages": [stage], "waiting": True}},
                        initial, events, payload)
    checks = result["checks"]

    def add(name, value, detail=""):
        checks.append({"id": name, "passed": bool(value), "detail": detail})

    text = core.journal_text(root)
    reads = {e["arguments"].get("path") for e in events if e["tool"] == "read_file" and "text" in e["result"]}
    commands = [e for e in events if e["tool"] == "run_command" and "exit_code" in e["result"]]

    def ran(*prefix):
        return any(e["arguments"].get("program") == "aegis" and e["result"]["exit_code"] == 0
                   and e["arguments"].get("args", [])[:len(prefix)] == list(prefix) for e in commands)

    add("stage_prompt_read", ".agentic/steps/adopt.md" in reads)
    items = component_items(core, text)
    if stage == "survey":
        header = re.search(r"(?m)^type:\s*(\S+)", text)
        add("adoption_journal", bool(header) and header.group(1) == "adopt")
        add("components_inventory_read", ran("components"))
        add("components_proposed", len(items) >= 2 and not any(t for t, _ in items))
        owners = [next((i for i, (_t, item) in enumerate(items) if covers(item, s)), None) for s in SOURCES]
        add("components_cover_sources_separately", None not in owners and len(set(owners)) == len(owners),
            json.dumps(owners))
        now = core.files(root)
        knowledge = {p: h for p, h in now.items() if p.startswith(".agentic/knowledge/")}
        add("no_component_work_before_agreement",
            knowledge == {p: h for p, h in initial["files"].items() if p.startswith(".agentic/knowledge/")}
            and not core.new_requirements(root, initial))
        project = ".agentic/context/project.md"
        add("context_populated", now.get(project) != initial["files"].get(project)
            and "order" in (root / project).read_text("utf-8").lower())
    else:
        add("whole_tree_check_run", any(e["arguments"].get("program") == "aegis"
                                        and e["arguments"].get("args", [])[:1] == ["check"]
                                        and "--task" not in e["arguments"].get("args", []) for e in commands))
        errors = [f for f in findings(root) if f.get("level") == "ERROR"]
        add("check_errors_fixed", not errors, "; ".join(f"{f['check']}: {f.get('message', '')}" for f in errors))
        project = (root / ".agentic/context/project.md").read_text("utf-8")
        add("context_reconciled", STALE_FACT not in project and "floating" not in project.lower())
        add("report_appended", "## Delivery report" in text)
        add("components_kept_ticked", len(items) == 2 and all(t for t, _ in items))
    result.update(passed=all(c["passed"] for c in checks), rubric=case["rubric"])
    return result


def score_chain(core, root, case, initial, events, payload, sessions, final):
    """Grade the chained adoption on the repository all four sessions left."""
    result = core.score(root, case, initial, events, payload)
    checks = result["checks"]

    def add(name, value, detail=""):
        checks.append({"id": name, "passed": bool(value), "detail": detail})

    add("all_sessions_completed",
        len(sessions) == len(case["chain"]) and all(s["status"] == "completed" for s in sessions),
        "; ".join(f"{s['stage']}={s['status']}" for s in sessions))
    text = core.journal_text(root)
    items = component_items(core, text)
    add("every_component_ticked", len(items) >= 2 and all(t for t, _ in items))
    add("knowledge_routes_every_component", all(page_mentions(root, initial, s, new_only=True) for s in SOURCES))
    linked, covered = new_requirements_ok(core, root, initial)
    add("requirements_active_and_linked_to_real_tests", linked)
    add("requirements_cover_every_component", covered)
    pages = {}
    for e in events:
        target = str(e["arguments"].get("path", ""))
        if (e["tool"] in {"write_file", "edit_file"} and "written_chars" in e["result"]
                and target.startswith(".agentic/knowledge/")):
            pages.setdefault(e.get("session"), set()).add(target)
    first, second = pages.get("components", set()), pages.get("components-next", set())
    add("one_component_per_session", len(first) == 1 and len(second) == 1 and first != second,
        json.dumps({k: sorted(v) for k, v in pages.items()}))
    add("survey_waited_for_owner", not any(e.get("session") == "survey" and target_page(e) for e in events))
    errors = [f for f in findings(root) if f.get("level") == "ERROR"]
    add("check_errors_fixed", not errors, "; ".join(f"{f['check']}: {f.get('message', '')}" for f in errors))
    add("report_appended", "## Delivery report" in text)
    result.update(passed=all(c["passed"] for c in checks), rubric=case["rubric"])
    return result


def target_page(event):
    """Whether one event wrote a knowledge page or a requirement."""
    path = str(event["arguments"].get("path", ""))
    return (event["tool"] in {"write_file", "edit_file"} and "written_chars" in event["result"]
            and path.startswith((".agentic/knowledge/", ".agentic/requirements/"))) or (
        event["tool"] == "run_command" and event["arguments"].get("args", [])[:1] == ["req"]
        and event["result"].get("exit_code") == 0)
