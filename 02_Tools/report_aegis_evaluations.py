"""Render AEGIS prompt evaluation runs as one self-contained HTML report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from report_aegis_evaluations_page import render_page

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_FILES = ("scenarios.json", "capability-scenarios.json", "holdout-scenarios.json")
VERSION_LINE = re.compile(rb'^VERSION = "([^"]+)"', re.M)
PAYLOAD_CLI = re.compile(r"(^|/)(payload|frozen-payload|\.agentic)/aegis\.py$")
FINAL_TEXT_LIMIT = 6000


class ReportError(Exception):
    """A run folder that cannot be reported faithfully."""


@dataclass
class Case:
    scenario: str
    repeat: int
    status: str
    passed: bool
    semantic: bool | None
    seconds: float
    tool_calls: int
    tokens_in: int
    tokens_out: int
    reasoning: int | None
    peak_prompt: int | None
    forbidden: int
    degenerate: int
    reviewer_sessions: int
    error: str
    failed: list[tuple[str, str]]
    failed_semantic: list[tuple[str, str]]
    evidence: dict | None = None


@dataclass
class Run:
    name: str
    path: Path
    runner: str
    version: str | None
    payload_sha256: str
    profile: str
    model: str
    reasoning: str
    collected: str
    window: int | None
    expected: int
    scenario_ids: list[str]
    settings: dict[str, str]
    cases: list[Case]

    @property
    def passed(self) -> int:
        return sum(case.passed for case in self.cases)

    @property
    def partial(self) -> bool:
        return len(self.cases) < self.expected


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReportError(f"{path}: {exc}") from exc


def payload_version(run_dir: Path) -> str | None:
    """VERSION of the payload CLI kept in evidence.zip, written when a run ends."""
    evidence = run_dir / "evidence.zip"
    if evidence.is_file():
        with zipfile.ZipFile(evidence) as archive:
            for name in archive.namelist():
                if PAYLOAD_CLI.search(name):
                    match = VERSION_LINE.search(archive.read(name))
                    if match:
                        return match.group(1).decode("ascii", "replace")
    return None


def resolve_versions(runs: list[Run]) -> None:
    """Name a run without evidence after another run, or the template, with the same CLI hash."""
    known = {run.payload_sha256: run.version for run in runs if run.version}
    template = ROOT / "05_Software" / "aegis" / "template" / ".agentic" / "aegis.py"
    if template.is_file():
        match = VERSION_LINE.search(template.read_bytes())
        if match:
            known.setdefault(hashlib.sha256(template.read_bytes()).hexdigest(), match.group(1).decode())
    for run in runs:
        if not run.version:
            run.version = known.get(run.payload_sha256) or f"unknown ({run.payload_sha256[:8]})"


def usage_sum(usage: list, key: str) -> int:
    return sum(item.get(key) or 0 for item in usage if isinstance(item, dict))


def failed_checks(checks: list) -> list[tuple[str, str]]:
    return [(str(c.get("id")), str(c.get("detail") or "")) for c in checks
            if isinstance(c, dict) and not c.get("passed")]


def parse_case(result: dict, subscription: bool) -> Case:
    evaluation = result.get("evaluation") or {}
    usage = result.get("usage") or []
    context = result.get("context") or {}
    semantic_checks = result.get("semantic_checks") or []
    if subscription:
        tokens_in, tokens_out = usage_sum(usage, "input_tokens"), result.get("output_tokens") or 0
        reasoning, peak = result.get("reasoning_tokens"), None
        tool_calls = result.get("coordinator_tool_calls") or 0
    else:
        tokens_in = context.get("total_prompt_tokens") or usage_sum(usage, "prompt_tokens")
        tokens_out = context.get("completion_tokens") or usage_sum(usage, "completion_tokens")
        reasoning = sum((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
                        for u in usage if isinstance(u, dict))
        peak, tool_calls = context.get("peak_prompt_tokens"), result.get("tool_calls") or 0
    return Case(
        scenario=str(result.get("scenario")), repeat=int(result.get("repeat") or 1),
        status=str(result.get("status") or "unknown"), passed=bool(result.get("passed")),
        semantic=result.get("semantic_passed") if semantic_checks else None,
        seconds=float(result.get("seconds") or 0), tool_calls=int(tool_calls),
        tokens_in=int(tokens_in), tokens_out=int(tokens_out), reasoning=reasoning,
        peak_prompt=peak, forbidden=int(result.get("forbidden_actions") or 0),
        degenerate=int(result.get("degenerate_responses") or 0),
        reviewer_sessions=int(result.get("reviewer_sessions") or 0),
        error=str(result.get("error") or ""),
        failed=failed_checks(evaluation.get("checks") or []),
        failed_semantic=failed_checks(semantic_checks),
    )


def run_settings(manifest: dict, subscription: bool) -> dict[str, str]:
    payload = (manifest.get("payload_files") or {}).get("aegis.py", "")[:8] or "-"
    if subscription:
        pacing = (manifest.get("pacing") or {}).get("before_each_cli_seconds")
        return {"Runner": "Codex CLI, subscription", "Model": str(manifest.get("model", "-")),
                "Reasoning": str(manifest.get("reasoning", "-")), "Sampling": "service defaults",
                "Context": f"{manifest.get('context') or 0:,} (configured)",
                "Output limit": "not exposed",
                "Tooling": str(manifest.get("cli_version", "-"))
                           + (f", {pacing} s pause per session" if pacing else ""),
                "Payload aegis.py": payload}
    server = manifest.get("server_model") or {}
    sampling = ", ".join(f"{label} {manifest[key]}" for key, label in
                         (("temperature", "temperature"), ("top_p", "top-p"), ("top_k", "top-k"),
                          ("presence_penalty", "presence"))
                         if manifest.get(key) is not None)
    window = manifest.get("context_window")
    return {"Runner": "LM Studio, local",
            "Model": f"{manifest.get('model', '-')} {server.get('quantization', '')}".strip(),
            "Reasoning": str(manifest.get("reasoning_effort") or "off"),
            "Sampling": sampling or "server defaults",
            "Context": f"{window:,} (loaded)" if window else "not reported",
            "Output limit": f"{manifest.get('max_tokens') or 0:,}",
            "Tooling": f"harness {manifest.get('harness_version', '-')}, {manifest.get('max_turns', '-')} turns, "
                       f"{manifest.get('run_timeout', '-')} s",
            "Payload aegis.py": payload}


def load_run(run_dir: Path) -> Run:
    manifest = read_json(run_dir / "manifest.json")
    results = read_json(run_dir / "results.json")
    if not isinstance(manifest, dict) or not isinstance(results, list):
        raise ReportError(f"{run_dir}: manifest.json must be an object and results.json a list")
    subscription = "cli" in manifest
    scenario_ids = [str(s) for s in manifest.get("scenario_ids") or []]
    reasoning = manifest.get("reasoning") if subscription else manifest.get("reasoning_effort")
    return Run(
        name=run_dir.name, path=run_dir,
        runner="subscription" if subscription else "local",
        version=payload_version(run_dir),
        payload_sha256=str((manifest.get("payload_files") or {}).get("aegis.py", "")),
        profile=str(manifest.get("profile") or "core"),
        model=str(manifest.get("model") or "-"), reasoning=str(reasoning or "off"),
        collected=str(manifest.get("date_utc") or manifest.get("created_utc") or "")[:10],
        window=manifest.get("context") if subscription else manifest.get("context_window"),
        expected=len(scenario_ids) * int(manifest.get("repeats") or 1),
        scenario_ids=scenario_ids, settings=run_settings(manifest, subscription),
        cases=[parse_case(r, subscription) for r in results if isinstance(r, dict)],
    )


def discover(paths: list[Path]) -> list[Path]:
    """Accept run folders, or folders whose direct children are run folders."""
    found: list[Path] = []
    for path in paths:
        if (path / "manifest.json").is_file():
            found.append(path)
        elif path.is_dir():
            found.extend(sorted(child for child in path.iterdir()
                                if (child / "manifest.json").is_file() and (child / "results.json").is_file()))
        else:
            raise ReportError(f"{path}: not a run folder or a folder of runs")
    return found


def step_label(call: dict) -> tuple[str, bool]:
    """Short label for one tool call and whether it failed."""
    tool, args = call.get("tool"), call.get("arguments") or {}
    result = call.get("result")
    result = result if isinstance(result, dict) else {}
    failed = bool(result.get("denied") or result.get("error")
                  or result.get("exit_code") not in (None, 0))
    if tool == "run_command":
        program, rest = args.get("program") or "", args.get("args") or []
        label = " ".join([program, *map(str, rest[:1])]) if program else str(args.get("command", ""))[:40]
    elif tool in ("read_file", "write_file", "edit_file", "list_files"):
        path = str(args.get("path") or ".").removeprefix(".agentic/")
        label = f"{tool.split('_')[0]} {path}"
    elif tool == "delegate_review":
        label = f"review {args.get('role', '')}".strip()
    else:
        label = str(tool)
    return label, failed


def flow(calls: list) -> list[tuple[str, int, bool]]:
    steps: list[tuple[str, int, bool]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        label, failed = step_label(call)
        if steps and steps[-1][0] == label and steps[-1][2] == failed:
            steps[-1] = (label, steps[-1][1] + 1, failed)
        else:
            steps.append((label, 1, failed))
    return steps


def case_evidence(archive: zipfile.ZipFile, prefix: str) -> dict:
    """Prompt, final answer and tool flow of one case, one entry per session."""
    names = set(archive.namelist())
    sessions = sorted({n[len(prefix):].split("/")[0] for n in names
                       if n.startswith(prefix + "session-")})
    bases = [prefix + s + "/" for s in sessions] or [
        b for b in (prefix, prefix + "coordinator/") if b + "request.txt" in names][:1]
    parts = []
    for base in bases:
        def text(name: str) -> str:
            return archive.read(base + name).decode("utf-8", "replace") if base + name in names else ""
        tools = json.loads(text("tools.json") or "[]")
        final = text("final.txt").strip()
        if len(final) > FINAL_TEXT_LIMIT:
            final = final[:FINAL_TEXT_LIMIT] + f"\n... ({len(final) - FINAL_TEXT_LIMIT:,} more characters)"
        parts.append({"session": base[len(prefix):].strip("/"), "request": text("request.txt").strip(),
                      "final": final, "flow": flow(tools if isinstance(tools, list) else [])})
    return {"parts": parts}


def attach_failed_evidence(run: Run, results: list) -> None:
    evidence = run.path / "evidence.zip"
    if not evidence.is_file():
        return
    directories = {(str(r.get("scenario")), int(r.get("repeat") or 1)): r.get("run_directory")
                   for r in results if isinstance(r, dict)}
    with zipfile.ZipFile(evidence) as archive:
        for case in run.cases:
            if case.passed:
                continue
            directory = directories.get((case.scenario, case.repeat)) or f"{case.scenario}-{case.repeat}"
            case.evidence = case_evidence(archive, f"runs/{directory}/")


def scenario_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    for name in SCENARIO_FILES:
        path = ROOT / "05_Software" / "aegis" / "evaluations" / name
        if path.is_file():
            for scenario in read_json(path).get("scenarios", []):
                catalog[scenario["id"]] = {"stage": scenario.get("kind") or scenario.get("stage"),
                                           "rubric": scenario.get("rubric") or []}
    return catalog


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path,
                        help="run folders, or folders whose children are run folders")
    parser.add_argument("--output", required=True, type=Path, help="HTML file to write")
    parser.add_argument("--version", action="append", default=[],
                        help="keep only runs on this AEGIS payload version; repeatable")
    parser.add_argument("--title", default="AEGIS prompt evaluation")
    args = parser.parse_args(argv)
    try:
        runs = [load_run(run_dir) for run_dir in discover(args.paths)]
        resolve_versions(runs)
        runs = [run for run in runs if not args.version or run.version in args.version]
        for run in runs:
            attach_failed_evidence(run, read_json(run.path / "results.json"))
    except (ReportError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not runs:
        print("error: no runs matched", file=sys.stderr)
        return 2
    page = render_page(args.title, runs, scenario_catalog())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page, encoding="utf-8", newline="\n")
    cases = sum(len(r.cases) for r in runs)
    print(f"wrote {args.output}: {len(runs)} run{'s' if len(runs) != 1 else ''}, {cases} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
