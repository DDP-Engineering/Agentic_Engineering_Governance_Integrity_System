#!/usr/bin/env python3
"""
Run real subscription CLI sessions for optional AEGIS capabilities.

Fresh reviewer sessions use existing native role prompts, immutable
snapshots and read-only MCP tools. No API keys or global setup changes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("aegis_capabilities", ROOT / "02_Tools/evaluate_aegis_capabilities.py")
cap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cap)
core = cap.core
SELF = Path(__file__).resolve()
#: the core profile's only transport-specific addition to the shared core instructions
MCP_ROUTING = ("\n\nThe five documented tools are exposed by the evaluation MCP server. Use "
               "only those tools; all repository access must go through them. Do not use "
               "native file, shell, patch, web, app or delegation tools.")

def read(path: Path):
    return json.loads(path.read_text("utf-8"))


def retry_delay(status, error, retry):
    """Retry only generic operational429 failures, with bounded backoff."""
    if (status != "provider_error" or retry >= 3 or not re.search(r"\b429\b|Too Many Requests", error, re.I)
            or re.search(r"insufficient_quota|credit_balance|usage[ _]limit|weekly[ _]limit|billing", error, re.I)):
        return None
    hint = re.search(r"Retry-After\s*:\s*(\d+(?:\.\d+)?)", error, re.I)
    return max([60, 120, 240][retry], float(hint.group(1)) if hint else 0)


def terminate_tree(process):
    """End only this launched CLI process tree after its deadline."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=15)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=15)


def run_cli(folder: Path, repo: Path, payload: Path, initial: dict, settings: dict,
            prompt: str, system: str, reviewer=False, schema=None, capability=True, timeout=None) -> dict:
    """Preserve CLI observations; never infer successful execution from prose."""
    folder.mkdir(parents=True, exist_ok=False)
    client = folder / "client"
    client.mkdir()
    core.write(folder / "request.txt", prompt)
    core.write(folder / "instructions.txt", system)
    core.dump(folder / "initial.json", initial)
    config = {"folder": str(folder), "repo": str(repo), "payload": str(payload),
              "initial": initial, "settings": settings, "reviewer": reviewer, "capability": capability}
    core.dump(folder / "host.json", config)
    options = {"project_doc_max_bytes": 0, "features.shell_tool": False,
        "features.memories": False, "features.multi_agent": False, "web_search": "disabled",
        "model_reasoning_effort": settings["reasoning"], "model_context_window": settings["context"],
        "model_instructions_file": str(folder / "instructions.txt"),
        "mcp_servers.evaluation.command": sys.executable,
        "mcp_servers.evaluation.args": [str(SELF), "serve", "--config", str(folder / "host.json")],
        "mcp_servers.evaluation.required": True, "mcp_servers.evaluation.startup_timeout_sec": 30,
        "mcp_servers.evaluation.tool_timeout_sec": 900 if capability and not reviewer else 60,
        "mcp_servers.evaluation.default_tools_approval_mode": "approve"}
    tools = core.TOOLS if not capability else cap.TOOLS
    if reviewer:
        tools = cap.REVIEW_TOOLS
    for tool in tools:
        options["mcp_servers.evaluation.tools." + tool["function"]["name"] + ".output_token_limit"] = 16000
    command = [settings["cli"], "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
        "--json", "-s", "read-only", "-C", str(client), "-m", settings["model"], "-o", str(folder / "final.txt")]
    for key, value in options.items():
        command += ["-c", key + "=" + json.dumps(value)]
    if schema is not None:
        core.dump(folder / "schema.json", schema)
        command += ["--output-schema", str(folder / "schema.json")]
    command += ["-"]
    core.dump(folder / "cli-command.json", command)
    env = {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_API_KEY"}}
    started = time.monotonic()
    status = "completed"
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    with (folder / "cli-events.jsonl").open("w", encoding="utf-8") as stdout, (folder / "cli-stderr.txt").open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr,
            text=True, encoding="utf-8", env=env, creationflags=flags, start_new_session=os.name != "nt")
        core.dump(folder / "process.json", {"pid": process.pid, "requested_model": settings["model"],
            "reasoning": settings["reasoning"], "context_configured": settings["context"], "fresh_session": True})
        try:
            process.communicate(prompt, timeout=timeout if timeout is not None else (600 if reviewer else 1800))
            if process.returncode:
                status = "provider_error"
        except subprocess.TimeoutExpired:
            terminate_tree(process)
            status = "run_timeout"
    events = []
    for line in (folder / "cli-events.jsonl").read_text("utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    violations = [e for e in events if e.get("type") == "item.completed"
        and e.get("item", {}).get("type") in {"command_execution", "file_change", "web_search", "collab_tool_call"}]
    transport = [e for e in events if e.get("type") == "item.completed"
        and e.get("item", {}).get("type") == "mcp_tool_call" and e["item"].get("error")]
    if violations:
        status = "host_violation"
    elif transport:
        status = "transport_error"
    usage = [e["usage"] for e in events if e.get("type") == "turn.completed" and e.get("usage")]
    error = "\n".join(e.get("message", "") or e.get("error", {}).get("message", "") for e in events if e.get("type") in {"error", "turn.failed"})
    result = {"status": status, "seconds": round(time.monotonic() - started, 3), "pid": process.pid,
        "thread_id": next((e.get("thread_id") for e in events if e.get("type") == "thread.started"), None),
        "usage": usage, "output_tokens": sum(u.get("output_tokens", 0) for u in usage),
        "reasoning_tokens": sum(u.get("reasoning_output_tokens", 0) for u in usage),
        "native_violations": len(violations), "error": error}
    if status == "completed" and (not usage or not (folder / "final.txt").is_file()):
        result["status"] = "incomplete_output"
    core.dump(folder / "execution.json", result)
    return result


def review_schema():
    """Constrain serialization only; verdicts and findings remain model-produced."""
    props = {"task": {"type": "string"}, "candidate": {"type": "string"},
        "verdict": {"type": "string", "enum": ["approved", "changes_required"]},
        "findings": {"type": "array", "items": {"type": "string"}},
        "inspected_paths": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}}}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def launch_review(config: dict, arguments: dict) -> dict:
    """Execute a requested role once; hide its verdict from the other role."""
    folder, repo, payload = (Path(config[k]) for k in ("folder", "repo", "payload"))
    ledger_path = folder / "reviews.json"
    ledger = read(ledger_path) if ledger_path.exists() else []
    for previous in ledger:
        if previous["role"] == arguments["role"]:
            if previous["candidate"] != arguments["candidate"]:
                raise ValueError("review round consumed; candidate changed without a new policy decision")
            return {**previous, "reused_observation": True}
    snapshot = folder / "review-snapshot"
    if not snapshot.exists():
        shutil.copytree(repo, snapshot, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        core.dump(folder / "review-snapshot-hashes.json", core.files(snapshot))
    if core.candidate(snapshot) != arguments["candidate"] or core.candidate(repo) != arguments["candidate"]:
        raise ValueError("candidate changed between reviews; no second verdict reused")
    initial = {**config["initial"], "files": core.files(snapshot), "candidate": core.candidate(snapshot)}
    role = arguments["role"]
    system = cap.role_prompt(role) + (
        "\nEvaluation transport: use only the read-only MCP tools. candidate_digest replaces the bridge candidate "
        "operation and aegis_candidate; it returns the supplied evaluation digest. No bridge executable is needed. "
        "The full snapshot and actual Git diff are available; no coordinator conversation or other review result is supplied. "
        "Return the role verdict in the schema's verdict field, with findings and limitations. Do not infer that a draft or test name alone proves behavior.")
    prompt = f"Independently review TASK-aaaaaaaa, candidate {arguments['candidate']}. Read the complete task, accepted scope and current source/tests. Verify the digest before and after inspection."
    attempts = []
    budget_started = time.monotonic()
    for retry in range(4):
        delay = 30 if retry == 0 else retry_delay(attempts[-1]["status"], attempts[-1]["error"], retry - 1)
        if delay is None or time.monotonic() - budget_started + delay >= 840:
            break
        time.sleep(delay)
        target = folder / "reviewers" / (role + "-attempt-" + str(retry + 1))
        result = run_cli(target, snapshot, payload, initial, config["settings"], prompt, system, reviewer=True,
            schema=review_schema(), timeout=max(1, min(600, 840 - (time.monotonic() - budget_started))))
        attempts.append(result)
        if retry_delay(result["status"], result["error"], retry) is None:
            break
    result = dict(attempts[-1])
    tools = read(target / "tools.json") if (target / "tools.json").exists() else []
    response = None
    if result["status"] == "completed":
        try:
            response = read(target / "final.txt")
            if (response["task"] != "TASK-aaaaaaaa" or response["candidate"] != arguments["candidate"]
                    or response["verdict"] not in {"approved", "changes_required"}):
                raise ValueError("review response identity or verdict mismatch")
        except (ValueError, KeyError, TypeError) as exc:
            result.update(status="invalid_review_response", error=str(exc))
    result.update(role=role, candidate=arguments["candidate"], response=response,
        verdict=response.get("verdict") if response else None,
        observed_reads=sorted({e["arguments"]["path"] for e in tools if e["tool"] == "read_file" and "text" in e["result"]}),
        digest_reads=sum(e["tool"] == "candidate_digest" and e["result"].get("candidate") == arguments["candidate"] for e in tools),
        denied_actions=sum(bool(e["result"].get("denied")) for e in tools),
        snapshot_unchanged=core.files(snapshot) == read(folder / "review-snapshot-hashes.json"),
        attempts=attempts, run_directory=str(target.relative_to(folder)))
    ledger.append(result)
    core.dump(ledger_path, ledger)
    return result


def serve(path: Path):
    """Serve one fixture; reviewer identity is set by the launcher, never tool args."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    config = read(path)
    root, payload = Path(config["repo"]), Path(config["payload"])
    host = cap.CapabilityHost(root, config["initial"], core.files(payload), reviewer=config["reviewer"],
        delegate=lambda a: launch_review(config, a)) if config["capability"] else core.Host(root, config["initial"], core.files(payload))
    commands = core.aegis_commands(payload)  # the payload's own CLI, as the local runner names it
    tools = cap.tools_for(commands) if config["capability"] else core.tools_for(commands)
    if config["reviewer"]:
        tools = cap.REVIEW_TOOLS
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            if "id" not in request:
                continue
            method = request["method"]
            if method == "initialize":
                result = {"protocolVersion": request["params"]["protocolVersion"], "capabilities": {"tools": {}},
                          "serverInfo": {"name": "aegis-evaluation-capabilities", "version": "1"}}
            elif method == "tools/list":
                result = {"tools": [{"name": t["function"]["name"], "description": t["function"]["description"],
                    "inputSchema": t["function"]["parameters"]} for t in tools]}
            elif method == "tools/call":
                p = request["params"]
                observation = host.call(p["name"], p.get("arguments", {}))
                core.dump(Path(config["folder"]) / "tools.json", host.events)
                result = {"content": [{"type": "text", "text": json.dumps(observation, ensure_ascii=False)}], "isError": False}
            elif method == "ping":
                result = {}
            else:
                raise ValueError("unsupported MCP method")
            response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        except Exception as exc:
            response = {"jsonrpc": "2.0", "id": request.get("id"), "error": {"code": -32603, "message": str(exc)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


def execute(args):
    """Freeze sources and collect complete baseline cases with all failures."""
    out, work = args.output.resolve(), args.work_dir.resolve()
    if out.exists() or work.exists() or out.is_relative_to(work) or work.is_relative_to(out):
        raise ValueError("output/work directories must be new and disjoint")
    capability = args.profile == "capabilities"
    cases = read(cap.SUITE if capability else core.SUITE)["scenarios"]
    entry = core.bootstrap_text(args.payload)  # init installs the evaluated payload's digest
    system = cap.instructions(entry) if capability else core.instructions(entry) + MCP_ROUTING
    if args.cases:
        names = set(args.cases.split(","))
        if names - {c["id"] for c in cases}:
            raise ValueError("unknown capability scenario")
        cases = [c for c in cases if c["id"] in names]
    out.mkdir(parents=True)
    work.mkdir(parents=True)
    payload = work / "frozen-payload"
    shutil.copytree(args.payload, payload, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    settings = {"cli": str(args.cli.resolve()), "model": args.model, "reasoning": args.reasoning, "context": args.context}
    version = subprocess.run([settings["cli"], "--version"], capture_output=True, text=True, check=True).stdout.strip()
    sources = [SELF, Path(cap.__file__), Path(cap.stages.__file__), Path(core.__file__), cap.SUITE, core.SUITE, cap.PROFILE,
        cap.ROLE_DIR / "aegis-spec-review.toml", cap.ROLE_DIR / "aegis-quality-review.toml",
        ROOT / "05_Software/aegis/integrations/codex/plugins/aegis/skills/aegis/SKILL.md"]
    manifest = {**settings, "date_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "cli_version": version,
        "cli_sha256": core.digest(args.cli.read_bytes()), "payload_files": core.files(payload),
        "sources": {str(p.relative_to(ROOT)): core.digest(p.read_bytes()) for p in sources},
        "scenario_ids": [c["id"] for c in cases], "repeats": 1, "output_cap_tokens": None,
        "context_source": "configured client setting, not independent server verification",
        "review_mode": "coordinator-triggered fresh native CLI processes with existing Codex adapter role prompts; not installed-plugin discovery" if capability else "unchanged supplied-review fixtures; no live delegation",
        "pacing": {"before_each_cli_seconds": 30, "operational429_backoff_seconds": [60, 120, 240]},
        "profile": args.profile, "system_sha256": core.digest(system.encode()),
        "entry_sha256": core.digest(entry.encode()),
        "aegis_commands": list(core.aegis_commands(payload)),
        "limitations": ["synthetic repositories", "one repeat", "native output cap/backend identity not exposed",
                        "Mermaid rendering not automatically certified", "all prompts fixed; semantic grading separate"]}
    core.dump(out / "manifest.json", manifest)
    for p in sources:
        target = out / "sources" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    results, all_attempts = [], []
    started = time.monotonic()
    for case in cases:
        attempts = []
        for retry in range(4):
            delay = 30 if retry == 0 else retry_delay(attempts[-1]["status"], attempts[-1]["error"], retry - 1)
            if delay is None:
                break
            print("WAIT " + str(delay) + " " + case["id"], flush=True)
            time.sleep(delay)
            run = work / (case["id"] + "-attempt-" + str(retry + 1))
            run.mkdir()
            initial = cap.prepare(run / "repo", payload, case) if capability else core.prepare(run / "repo", payload, case)
            print("START " + case["id"], flush=True)
            execution = run / "coordinator"
            result = run_cli(execution, run / "repo", payload, initial, settings, case["prompt"], system, capability=capability)
            events = read(execution / "tools.json") if (execution / "tools.json").exists() else []
            reviews = read(execution / "reviews.json") if (execution / "reviews.json").exists() else []
            final = (execution / "final.txt").read_text("utf-8") if (execution / "final.txt").exists() else ""
            grade = cap.score(run / "repo", case, initial, events, payload, reviews, final) if capability else core.score(run / "repo", case, initial, events, payload)
            result.update(scenario=case["id"], run_directory=run.name, evaluation=grade,
                passed=result["status"] == "completed" and grade["passed"], coordinator_tool_calls=len(events),
                reviewer_sessions=len(reviews), reviewer_output_tokens=sum(v["output_tokens"] for v in reviews),
                reviewer_reasoning_tokens=sum(v["reasoning_tokens"] for v in reviews), wait_before_seconds=delay)
            attempts.append(result)
            all_attempts.append(result)
            core.dump(out / "attempts.json", all_attempts)
            core.dump(run / "result.json", result)
            print("DONE " + json.dumps({k: result[k] for k in ["scenario", "status", "passed", "seconds", "reviewer_sessions"]}), flush=True)
            if retry_delay(result["status"], result["error"], retry) is None:
                break
        results.append(result)
        core.dump(out / "results.json", results)
        if result["status"] != "completed":
            break
    core.dump(out / "timing.json", {"collection_wall_seconds": round(time.monotonic() - started, 3),
        "coordinator_wall_seconds_including_nested_reviews": round(sum(v["seconds"] for v in all_attempts), 3)})
    for p in sources:
        assert core.digest(p.read_bytes()) == manifest["sources"][str(p.relative_to(ROOT))], str(p)
    assert core.files(payload) == manifest["payload_files"]
    core.archive(out, work, payload)
    core.dump(out / "integrity.json", {str(p.relative_to(out)): core.digest(p.read_bytes()) for p in out.rglob("*") if p.is_file()})
    print("FINISHED " + str(out), flush=True)


def main():
    """Require explicit native runtime, model and fresh artifact destinations."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    server = sub.add_parser("serve")
    server.add_argument("--config", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--cli", type=Path, required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--reasoning", default="medium", choices=["low", "medium", "high", "xhigh"])
    run.add_argument("--context", type=int, default=131072)
    run.add_argument("--payload", type=Path, default=core.PAYLOAD)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--work-dir", type=Path, required=True)
    run.add_argument("--cases")
    run.add_argument("--profile", choices=["core", "capabilities"], default="capabilities")
    args = parser.parse_args()
    if args.operation == "run" and args.context <= 0:
        parser.error("--context must be positive")
    if args.operation == "serve":
        serve(args.config)
    else:
        execute(args)


if __name__ == "__main__":
    main()
