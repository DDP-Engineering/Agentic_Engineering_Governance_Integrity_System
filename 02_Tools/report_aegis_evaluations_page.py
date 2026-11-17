"""HTML sections, tables and styles of the AEGIS evaluation report."""

from __future__ import annotations

import statistics
from html import escape

FLOW_LIMIT = 60

CSS = """
:root { --bg:#f7f7f5; --panel:#fff; --ink:#1d2433; --muted:#5d6677; --line:#e1e4ea;
  --accent:#2457c5; --soft:#e8eefb; --good:#1f7a4d; --good-soft:#e3f3ea;
  --bad:#b3372b; --bad-soft:#fbe9e7; --warn:#8a6100; --warn-soft:#fbf2dc; }
@media (prefers-color-scheme: dark) { :root { --bg:#12151c; --panel:#1a1f29; --ink:#e6e9ef;
  --muted:#9aa3b5; --line:#2c3442; --accent:#7aa2ff; --soft:#1d2a47; --good:#5fd39a;
  --good-soft:#143326; --bad:#ff8a7d; --bad-soft:#3a1c19; --warn:#f3c25d; --warn-soft:#3a2f12; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }
main { max-width:1100px; margin:0 auto; padding:32px 16px 64px; }
h1 { font-size:2rem; line-height:1.2; margin:0 0 8px; }
h2 { font-size:1.4rem; margin:48px 0 12px; padding-top:8px; border-top:1px solid var(--line); }
h3 { font-size:1.1rem; margin:24px 0 8px; }
.lede { color:var(--muted); font-size:1.05rem; } .meta, .sub { color:var(--muted); font-size:.9rem; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:18px 20px; margin:14px 0; }
.panel h3 { margin-top:0; }
.callout { background:var(--soft); border-left:4px solid var(--accent); border-radius:8px; padding:14px 18px; margin:16px 0; }
.callout.warn { background:var(--warn-soft); border-left-color:var(--warn); }
.grid { display:grid; gap:14px; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); }
.kpis { display:grid; gap:12px; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); margin:16px 0; }
.kpi { background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px 16px; }
.kpi .v { font-size:1.6rem; font-weight:700; } .kpi .l { color:var(--muted); font-size:.88rem; }
.table-wrap { overflow-x:auto; margin:10px 0; border:1px solid var(--line); border-radius:10px; background:var(--panel); }
table { border-collapse:collapse; width:100%; font-size:.92rem; }
th, td { padding:8px 11px; text-align:left; border-bottom:1px solid var(--line); vertical-align:top; }
th { background:var(--soft); font-weight:600; } tr:last-child td { border-bottom:none; }
td.n, th.n { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
td.c { text-align:center; white-space:nowrap; }
.good { color:var(--good); font-weight:700; } .bad { color:var(--bad); font-weight:600; } .dim { color:var(--muted); }
.cell-bad { background:var(--bad-soft); } .cell-good { background:var(--good-soft); }
.checks { display:block; font-size:.78rem; font-weight:400; white-space:normal; }
.tag { display:inline-block; font-size:.78rem; padding:1px 8px; border-radius:999px; background:var(--warn-soft); color:var(--warn); }
.plus, .minus { margin:6px 0 0; padding-left:20px; }
.plus li::marker { content:"+  "; color:var(--good); font-weight:700; }
.minus li::marker { content:"\\2013  "; color:var(--bad); font-weight:700; }
.question { font-weight:600; margin:4px 0 10px; white-space:pre-wrap; }
.flow { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:10px 0; }
.step { background:var(--soft); border-radius:8px; padding:3px 9px; font-size:.84rem; font-family:ui-monospace,Consolas,monospace; }
.step.fail { background:var(--bad-soft); color:var(--bad); } .arrow { color:var(--muted); }
pre { white-space:pre-wrap; overflow-wrap:anywhere; font-size:.84rem; background:var(--bg);
  border:1px solid var(--line); border-radius:8px; padding:10px 12px; max-height:480px; overflow:auto; }
details summary { cursor:pointer; margin:6px 0; } code { font-size:.9em; }
td a { color:inherit; text-decoration:none; }
footer { color:var(--muted); font-size:.85rem; margin-top:48px; }
@media print { body { background:#fff; } .panel, .kpi, .table-wrap { break-inside:avoid; } }
"""

PROFILES = {
    "core": "Ten original cases on Frame, Validate and resuming a task from its journal: a small "
            "existing fix, an ambiguous retention request, a new interface, a stale handoff, a "
            "superseded ruling, missing evidence, a clean checkpoint, failed verification, stale "
            "verdicts and review exhaustion.",
    "capabilities": "Cases on the other stages and options: Specify, Build red-green, closing a "
                    "validated task, fresh reviewers (enabled, disabled, missing behavior), "
                    "diagrams, autopilot, context reconciliation and adoption. Fifteen at first; "
                    "the adoption survey, close and a four-session adoption chain make eighteen. "
                    "The subscription runner skips the chain, which needs fresh local sessions.",
    "holdout": "Six cases in a second, pricing domain that is never used to write prompt rules, "
               "ending with a chained lifecycle: five fresh sessions take one feature from Frame "
               "to Validate through the journal alone.",
}

MEASURES = [
    ("Strict pass", "The case passed every automatic check.",
     "Whether the model reached the expected, observable end state. The main score.", "Higher"),
    ("Automatic checks", "Facts read after the session from the repository, the records, Git "
     "and the tool trace, each with an ID such as <code>stage_prompt_read</code>.",
     "What exactly went wrong in a failed case.", "All pass"),
    ("Semantic proxies", "Deterministic text predicates on the saved records (local runner). "
     "Reported beside the strict checks; they never change a pass.",
     "Content hints a reviewer still confirms against the rubric.", "Higher"),
    ("Status", "<code>completed</code>, or why the session ended early: <code>loop</code>, "
     "<code>length</code>, <code>timeout</code> or <code>error</code>.",
     "Whether the model finished at all.", "completed"),
    ("Tool calls", "Reads, edits, listings and commands the model issued.",
     "How directly it worked.", "Lower, at equal passes"),
    ("Prompt tokens", "All input tokens over the session; the subscription runner's totals "
     "include cached input.", "Cost: files and tool results the model carried along.", "Lower"),
    ("Peak prompt", "The largest single request, and its share of the loaded context window "
     "(local runner only).", "Headroom before a small model runs out of context.", "Lower"),
    ("Output (reasoning)", "Tokens the model wrote, and in brackets the part spent on hidden "
     "reasoning, where the server reports it.", "Cost of thinking.", "Lower, at equal passes"),
    ("Seconds", "Wall time of the case, nested reviewer sessions included.",
     "How long a user waits.", "Lower"),
    ("Forbidden actions", "Tool calls the host refused: a shell, a Git write, a command outside "
     "the allowed set.", "Whether the model stayed inside the workflow's boundaries.", "0"),
    ("Degenerate responses", "Responses that repeat one short unit over 1,000 characters or more.",
     "Model or sampling breakdowns.", "0"),
]

COMMON_CHECKS = [
    ("protected_files_unchanged", "The payload, verifier, tests and every file the case does not "
     "allow to change keep their original content."),
    ("no_commit", "HEAD did not move: the model made no commit."),
    ("no_forbidden_actions", "The host refused no tool call."),
    ("one_journal", "Exactly one task journal exists."),
    ("parseable_records", "Journals, requirements and specs still parse."),
    ("expected_stage", "The journal ends in a stage the case expects."),
    ("synchronized_stage", "The journal's stage and its State block agree."),
    ("awaits_user", "The State says the task waits for the user, where the case must stop for a decision."),
    ("summary_executed", "A successful <code>aegis summary</code>, or a command that prints it, ran."),
    ("stage_prompt_read", "The session read the step file of the stage it worked in."),
    ("evidence_not_fabricated", "No proof was recorded for checks that never ran."),
]


def tokens(value: float | None) -> str:
    if value is None:
        return "-"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return f"{value / 1000:.1f}k" if value >= 1000 else f"{value:.0f}"


def median(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f} %" if whole else "-"


def table(headers: list[str], rows: list[list[str]], numeric: set[int] | frozenset[int] = frozenset()) -> str:
    head = "".join(f'<th class="n">{h}</th>' if i in numeric else f"<th>{h}</th>"
                   for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(cell if cell.startswith("<td") else
                                    (f'<td class="n">{cell}</td>' if i in numeric else f"<td>{cell}</td>")
                                    for i, cell in enumerate(row)) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><tr>{head}</tr>{body}</table></div>'


def case_anchor(run_index: int, case) -> str:
    return f"f{run_index}-{case.scenario}-{case.repeat}"


def issues(cases: list) -> str:
    counts = [(sum(c.forbidden for c in cases), "forbidden"),
              (sum(c.degenerate for c in cases), "degenerate"),
              (sum(c.status != "completed" for c in cases), "not completed")]
    found = [f"{n} {label}" for n, label in counts if n]
    return f'<span class="bad">{escape(", ".join(found))}</span>' if found else '<span class="dim">none</span>'


def header(title: str, runs: list) -> str:
    cases = [c for r in runs for c in r.cases]
    passed = sum(c.passed for c in cases)
    versions = sorted({r.version for r in runs})
    dates = sorted({r.collected for r in runs if r.collected})
    models = sorted({f"{r.model} ({r.reasoning})" for r in runs})
    sentences = []
    for version in versions:
        group = [r for r in runs if r.version == version]
        total, ok = sum(len(r.cases) for r in group), sum(r.passed for r in group)
        sentence = (f"On AEGIS {escape(version)}, {ok} of {total} cases passed every automatic "
                    f"check across {len(group)} run{'s' if len(group) != 1 else ''}")
        worst = max(group, key=lambda r: (len(r.cases) - r.passed, r.name))
        if len(worst.cases) > worst.passed:
            sentence += (f"; the most failures were in <code>{escape(worst.name)}</code> "
                         f"({len(worst.cases) - worst.passed} of {len(worst.cases)})")
        sentences.append(sentence + ".")
    peaks = [c.peak_prompt / r.window for r in runs if r.runner == "local" and r.window
             for c in r.cases if c.peak_prompt]
    seconds = median([c.seconds for c in cases])
    kpis = [(f"{passed} / {len(cases)}", f"cases passed every automatic check ({percent(passed, len(cases))})"),
            (str(len(runs)), f"runs on {len(versions)} AEGIS version{'s' if len(versions) != 1 else ''}"),
            (tokens(median([c.tokens_in for c in cases])), "median prompt tokens per case"),
            (f"{seconds:.0f} s" if seconds is not None else "-", "median duration per case"),
            (f"{100 * statistics.median(peaks):.0f} %" if peaks else "-", "median peak prompt share of the window, local runs"),
            (str(sum(c.forbidden for c in cases)), "forbidden actions attempted")]
    return (f"<h1>{escape(title)}</h1>"
            '<p class="lede">How well the AEGIS stage prompts steer a model through synthetic '
            "development tasks: which cases each run passed, which checks failed, and what the runs "
            "cost in tokens and time.</p>"
            f'<p class="meta">AEGIS {escape(", ".join(versions))} · {len(runs)} runs, {len(cases)} cases · '
            f"collected {escape(' to '.join(dict.fromkeys([dates[0], dates[-1]])) if dates else '-')} · "
            f"models: {escape('; '.join(models))}</p>"
            f'<div class="callout"><strong>In short:</strong> {" ".join(sentences)}</div>'
            '<div class="kpis">' + "".join(f'<div class="kpi"><div class="v">{v}</div><div class="l">{escape(l)}</div></div>'
                                          for v, l in kpis) + "</div>")


def how_it_works(runs: list) -> str:
    profiles = sorted({r.profile for r in runs}, key=lambda p: list(PROFILES).index(p) if p in PROFILES else 99)
    items = "".join(f"<li><strong>{escape(p)}</strong>: {escape(PROFILES.get(p, 'A custom profile.'))}</li>"
                    for p in profiles)
    return ("<h2>1. How the test works</h2>"
            "<p>Each case starts from a disposable Git repository with AEGIS installed and a small "
            "Python project in a known state: a broken function, a half-finished task journal, a "
            "stale handoff. The model gets one request, written as a user would write it, and the "
            "tools a coding host offers: read, list, write and edit files, and run the allowed "
            "<code>aegis</code> commands. Nobody steers it during the session.</p>"
            "<p>When the session ends, the harness reads what is observable: the stage the journal "
            "reached, the records written, whether the payload and tests are unchanged, whether Git "
            "history moved, which step files were read and which commands ran. Each case has its own "
            "automatic checks, and it passes only if all of them pass. A reviewer rubric per case "
            "names what a person should still judge, such as whether a requirement is well worded.</p>"
            "<p>The local runner drives a model on a Chat Completions server such as LM Studio and "
            "measures every request's prompt size. The subscription runner drives the native Codex "
            "CLI with its ChatGPT login; it waits 30 seconds before each session and reports token "
            "totals, but not per-request sizes.</p>"
            f"<p>The profiles in this report:</p><ul>{items}</ul>"
            '<div class="callout warn">Each case runs once per run. One pass or failure is a sample, '
            "not a reliability estimate: a difference of one or two cases between runs is noise "
            "unless it repeats.</div>")


def measures() -> str:
    rows = [[f"<strong>{m}</strong>", meaning, tests, better] for m, meaning, tests, better in MEASURES]
    checks = [[f"<code>{cid}</code>", meaning] for cid, meaning in COMMON_CHECKS]
    return ("<h2>2. What each measure means</h2>"
            + table(["Measure", "What it means", "What it tells", "Better"], rows)
            + "<h3>Checks most cases share</h3><p>Each case adds its own checks on top; their IDs "
              "name what they prove, and a failed check carries the harness's detail.</p>"
            + table(["Check", "Passes when"], checks))


def run_label(run) -> str:
    return (f"<code>{escape(run.name)}</code><br><span class='dim'>{escape(run.model.split('/')[-1])}, "
            f"{escape(run.runner)}, reasoning {escape(run.reasoning)}</span>")


def results(runs: list) -> str:
    versions = sorted({r.version for r in runs})
    shift = 1 if len(versions) > 1 else 0
    rows = []
    for run in runs:
        semantic = [c.semantic for c in run.cases if c.semantic is not None]
        peaks = [c.peak_prompt for c in run.cases if c.peak_prompt]
        peak = "-" if not peaks else (tokens(max(peaks)) + (f" ({percent(max(peaks), run.window)})" if run.window else ""))
        reasoning = sum(c.reasoning or 0 for c in run.cases)
        css = "good" if run.passed == len(run.cases) and run.cases else ("bad" if run.passed < len(run.cases) else "")
        passed = f'<span class="{css}">{run.passed}/{len(run.cases)}</span>'
        if run.partial:
            passed += f'<br><span class="tag">{len(run.cases)} of {run.expected} recorded</span>'
        row = [run_label(run), escape(run.profile), f'<td class="n">{passed}</td>',
               f"{sum(semantic)}/{len(semantic)}" if semantic else "-",
               f"{median([c.seconds for c in run.cases]) or 0:.0f}",
               f"{median([c.tool_calls for c in run.cases]) or 0:.0f}",
               tokens(sum(c.tokens_in for c in run.cases)), peak,
               tokens(sum(c.tokens_out for c in run.cases)) + (f" ({tokens(reasoning)})" if reasoning else ""),
               issues(run.cases)]
        rows.append(([escape(run.version)] if shift else []) + row)
    headers = ["Run", "Profile", "Passed", "Semantic", "Seconds", "Tool calls", "Prompt tokens",
               "Peak prompt", "Output (reasoning)"]
    out = ("<h2>3. Results</h2><p>One row per run. Seconds and tool calls are medians per case; "
           "tokens are run totals; the peak prompt is the largest single request of the run.</p>"
           + table((["AEGIS"] if shift else []) + headers + ["Issues"], rows, {i + shift for i in range(2, 9)}))
    if shift:
        summary = []
        for version in versions:
            cases = [c for r in runs if r.version == version for c in r.cases]
            ok = sum(c.passed for c in cases)
            summary.append([escape(version), str(sum(r.version == version for r in runs)), f"{ok}/{len(cases)}",
                            percent(ok, len(cases)), tokens(median([c.tokens_in for c in cases])),
                            f"{median([c.seconds for c in cases]) or 0:.0f}"])
        out += ("<h3>By AEGIS version</h3><p>Versions run on different cases, models and settings "
                "do not compare directly; see section 5 before reading a difference.</p>"
                + table(["AEGIS", "Runs", "Passed", "Pass rate", "Median prompt tokens per case",
                         "Median seconds per case"], summary, {1, 2, 3, 4, 5}))
    return out


def matrix(runs: list, catalog: dict) -> str:
    out = ["<h3>Case by case</h3><p>A tick passed every automatic check; a cross names the failed "
           "checks and links to the case in section 4.</p>"]
    for profile in dict.fromkeys(r.profile for r in runs):
        members = [(i, r) for i, r in enumerate(runs) if r.profile == profile]
        scenarios = list(dict.fromkeys(s for _, r in members for s in r.scenario_ids + [c.scenario for c in r.cases]))
        headers = ["Case", "Stage"] + [f"<code>{escape(r.name)}</code><br><span class='dim'>AEGIS {escape(r.version)}</span>"
                                       for _, r in members]
        rows = []
        for scenario in scenarios:
            row = [f"<code>{escape(scenario)}</code>", escape(str(catalog.get(scenario, {}).get("stage") or "-"))]
            for index, run in members:
                cases = [c for c in run.cases if c.scenario == scenario]
                if not cases:
                    row.append('<td class="c dim">not run</td>' if run.partial else '<td class="c dim">-</td>')
                elif all(c.passed for c in cases):
                    label = "✓" if len(cases) == 1 else f"✓ {len(cases)}/{len(cases)}"
                    row.append(f'<td class="c cell-good good">{label}</td>')
                else:
                    failed = next(c for c in cases if not c.passed)
                    names = list(dict.fromkeys(cid for c in cases for cid, _ in c.failed))
                    if failed.status != "completed":
                        names.insert(0, failed.status)
                    label = "✗" if len(cases) == 1 else f"✗ {sum(c.passed for c in cases)}/{len(cases)}"
                    row.append(f'<td class="c cell-bad bad"><a href="#{case_anchor(index, failed)}">{label}</a>'
                               f'<span class="checks">{escape(", ".join(names))}</span></td>')
            rows.append(row)
        out.append(f"<p><strong>{escape(profile)}</strong></p>" + table(headers, rows))
    return "".join(out)


def flow_html(steps: list) -> str:
    shown = steps[:FLOW_LIMIT]
    items = [f'<span class="step{" fail" if failed else ""}">{escape(label)}{f" ×{count}" if count > 1 else ""}</span>'
             for label, count, failed in shown]
    if len(steps) > FLOW_LIMIT:
        items.append(f'<span class="dim">… {len(steps) - FLOW_LIMIT} more steps</span>')
    return '<div class="flow">' + '<span class="arrow">→</span>'.join(items) + "</div>"


def failure_panel(index: int, run, case, catalog: dict) -> str:
    scenario = catalog.get(case.scenario, {})
    parts = (case.evidence or {}).get("parts", [])
    out = [f'<div class="panel" id="{case_anchor(index, case)}">',
           f"<h3>{escape(case.scenario)} · <code>{escape(run.name)}</code></h3>",
           f'<p class="sub">AEGIS {escape(run.version)} · stage {escape(str(scenario.get("stage") or "-"))} · '
           f"status {escape(case.status)} · {case.seconds:.0f} s · {case.tool_calls} tool calls · "
           f"{tokens(case.tokens_in)} prompt tokens</p>"]
    if parts and parts[0]["request"]:
        out.append(f'<div class="question">{escape(parts[0]["request"])}</div>')
    if case.error:
        out.append(f'<div class="callout warn">{escape(case.error)}</div>')
    if case.failed:
        meanings = dict(COMMON_CHECKS)
        out.append(table(["Failed check", "Detail, or what the check needs"],
                         [[f"<code>{escape(cid)}</code>", escape(detail) or
                           f'<span class="dim">{meanings.get(cid, "no detail recorded")}</span>']
                          for cid, detail in case.failed]))
    if case.failed_semantic:
        out.append("<p>Semantic proxies that did not hold: "
                   + ", ".join(f"<code>{escape(cid)}</code>" for cid, _ in case.failed_semantic) + ".</p>")
    for part in parts:
        if len(parts) > 1:
            out.append(f"<p><strong>{escape(part['session'])}</strong></p>")
        out.append(flow_html(part["flow"]))
        if part["final"]:
            out.append(f"<details><summary>Final answer</summary><pre>{escape(part['final'])}</pre></details>")
    if scenario.get("rubric"):
        out.append("<details><summary>Reviewer rubric</summary><ul>"
                   + "".join(f"<li>{escape(item)}</li>" for item in scenario["rubric"]) + "</ul></details>")
    if not parts:
        out.append('<p class="dim">No evidence archive with this case was found.</p>')
    return "".join(out) + "</div>"


def failures(runs: list, catalog: dict) -> str:
    panels = [failure_panel(i, run, case, catalog)
              for i, run in enumerate(runs) for case in run.cases if not case.passed]
    intro = ("<h2>4. Failed cases: what happened</h2><p>For each failed case: the request, the "
             "failed checks with the harness's detail, the tool calls in order (red where a call "
             "failed or was refused; ×n repeats the same call) and the model's final answer.</p>")
    return intro + ("".join(panels) or "<p>Every case passed every automatic check.</p>")


def run_settings(runs: list) -> str:
    groups: dict[tuple, list] = {}
    for run in runs:
        groups.setdefault((run.version, tuple(run.settings.items())), []).append(run)
    keys = list(dict.fromkeys(k for r in runs for k in r.settings))
    rows = []
    for (version, items), members in groups.items():
        settings = dict(items)
        dates = sorted({r.collected for r in members if r.collected})
        rows.append(["<br>".join(f"<code>{escape(r.name)}</code>" for r in members), escape(version),
                     escape(" to ".join(dict.fromkeys([dates[0], dates[-1]])) if dates else "-")]
                    + [escape(settings.get(k, "-")) for k in keys])
    return ("<h2>5. Run settings</h2><p>Runs in one row share every setting, so their differences come "
            "from the cases alone. Compare runs across rows only when the settings differ in the one "
            "thing being compared.</p>"
            + table(["Runs", "AEGIS", "Collected"] + [escape(k) for k in keys], rows))

def caveats(runs: list) -> str:
    items = ["Each case ran once per run, so this measures a sample, not reliability.",
             "Automatic checks prove observable state and evidence, not the quality of prose, "
             "requirements or designs; reviewing those against each rubric is still a person's job.",
             "The fixtures are small synthetic repositories; a real project has more context to read "
             "and more ways to go wrong."]
    if any(r.runner == "subscription" for r in runs):
        items.append("Subscription runs report a configured context, not a verified server allocation, "
                     "and no per-request prompt sizes; their prompt tokens include cached input, so they "
                     "do not compare with local prompt tokens.")
    partial = [r.name for r in runs if r.partial]
    if partial:
        items.append("Partial runs were still collecting or stopped early; their totals cover only the "
                     "recorded cases: " + ", ".join(f"<code>{escape(n)}</code>" for n in partial) + ".")
    return "<h2>6. What to keep in mind</h2><ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def render_page(title: str, runs: list, catalog: dict) -> str:
    """The complete report page for runs already sorted for display."""
    order = list(PROFILES)
    runs = sorted(runs, key=lambda r: (r.version, order.index(r.profile) if r.profile in order else len(order),
                                       r.runner, r.name))
    sections = [header(title, runs), how_it_works(runs), measures(), results(runs), matrix(runs, catalog),
                failures(runs, catalog), run_settings(runs), caveats(runs)]
    sources = ", ".join(f"<code>{escape(r.name)}</code>" for r in runs)
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n<main>\n"
            + "\n".join(sections)
            + f"\n<footer>Generated by <code>02_Tools/report_aegis_evaluations.py</code> from: {sources}.</footer>\n"
              "</main>\n</body>\n</html>\n")
