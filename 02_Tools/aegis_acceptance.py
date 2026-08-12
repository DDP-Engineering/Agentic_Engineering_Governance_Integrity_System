#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file aegis_acceptance.py
@brief Compiles fail-closed, offline AEGIS acceptance verdicts.
@details Validation never executes records, project commands, network requests,
         or Git mutations. Records contain only observations retained by callers.
"""

import argparse
import datetime as datetime_module
import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any

RESULTS = frozenset({"not_run", "passed", "failed", "blocked", "not_applicable", "deferred"})
OUTCOMES = frozenset({"passed", "failed", "timed_out", "cancelled", "launch_error"})
SHA256_LENGTH = 64
MAX_RETAINED_OUTPUT_CHARS = 4096


class ValidationError(ValueError):
    """@brief Indicates a record is not a trustworthy acceptance input."""


def canonical_digest(value: Any) -> str:
    """@brief Returns the deterministic SHA-256 of JSON-compatible data."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require(value: Any, label: str) -> Any:
    if not value:
        raise ValidationError(f"missing {label}")
    return value


def _timestamp(value: Any, label: str) -> datetime_module.datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValidationError(f"{label} timestamp needs RFC3339 UTC Z form")
    try:
        parsed = datetime_module.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValidationError(f"invalid {label} timestamp") from error
    if parsed.tzinfo is None:
        raise ValidationError(f"{label} timestamp needs an offset")
    return parsed


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != SHA256_LENGTH:
        raise ValidationError(f"invalid {label} SHA-256")
    try:
        int(value, 16)
    except ValueError as error:
        raise ValidationError(f"invalid {label} SHA-256") from error
    return value.lower()


def _root(path: pathlib.Path) -> pathlib.Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise ValidationError("evidence root is not a directory")
    return resolved


def _evidence_path(root: pathlib.Path, reference: Any, digest: Any, size: Any) -> pathlib.Path:
    if not isinstance(reference, str) or not reference or "\\" in reference:
        raise ValidationError("evidence reference must be portable relative path")
    pure = pathlib.PurePosixPath(reference)
    if pure.is_absolute() or ":" in pure.parts[0] or ".." in pure.parts:
        raise ValidationError("unsafe evidence reference")
    path = (root / pathlib.Path(*pure.parts)).resolve()
    if root not in path.parents or not path.is_file():
        raise ValidationError("evidence reference escapes root or is not a file")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValidationError("invalid evidence size")
    content = path.read_bytes()
    if len(content) != size or hashlib.sha256(content).hexdigest() != _sha256(digest, "evidence"):
        raise ValidationError("evidence digest or size mismatch")
    return path


def _load(path: str) -> dict[str, Any]:
    with pathlib.Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def _atomic_write(path: str, content: str, force: bool) -> None:
    target = pathlib.Path(path).resolve()
    if target.exists() and not force:
        raise ValidationError("refusing overwrite without --force")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".aegis-acceptance-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    except BaseException:
        pathlib.Path(temporary).unlink(missing_ok=True)
        raise


def validate_catalog(catalog: dict[str, Any]) -> None:
    """@brief Validates reviewed, machine-significant catalog data."""
    scenarios = catalog.get("scenarios", [])
    requirements = catalog.get("requirements", {})
    identifiers = [item.get("id") for item in scenarios]
    if len(identifiers) != len(set(identifiers)) or any(not str(value).startswith("AC-") for value in identifiers):
        raise ValidationError("catalog scenario IDs must be unique")
    if catalog.get("catalog_name") == "AEGIS version 1 acceptance catalog":
        totals = [len(identifiers), len(requirements), list(requirements.values()).count("Must"), list(requirements.values()).count("Should"), list(requirements.values()).count("Could")]
        if totals != [58, 226, 206, 17, 3]:
            raise ValidationError("authoritative catalog totals are invalid")
    for scenario in scenarios:
        covered = scenario.get("requirements", [])
        if scenario.get("priority") not in {"Must", "Should", "Could", "Must/Should"} or not scenario.get("method") or not covered or any(item not in requirements for item in covered):
            raise ValidationError("invalid catalog scenario")
    if set(requirements) != {item for scenario in scenarios for item in scenario["requirements"]}:
        raise ValidationError("catalog has unmapped or unknown requirement")
    if any(priority not in {"Must", "Should", "Could"} for priority in requirements.values()):
        raise ValidationError("invalid requirement priority")
    matrix = catalog.get("required_matrices", {})
    for field in ("package_cases", "workflow_cases"):
        cases = matrix.get(field, [])
        if not cases or len({case.get("id") for case in cases}) != len(cases):
            raise ValidationError("invalid required matrix cases")


def _candidate_indexes(candidate: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    _require(candidate.get("product_version"), "product version")
    revision = _require(candidate.get("source_revision"), "source revision")
    if not isinstance(revision, str):
        raise ValidationError("source revision must be a recorded string")
    _timestamp(_require(candidate.get("created_at"), "creation"), "creation")
    for key in ("python", "git", "runtime"):
        if not isinstance(candidate.get(key), dict) or not candidate[key]:
            raise ValidationError(f"missing {key} identity")
    packages: dict[str, dict[str, Any]] = {}
    package_keys: set[tuple[str, str, str]] = set()
    for package in candidate.get("packages", []):
        digest = _sha256(package.get("digest"), "package")
        key = (str(package.get("edition")), str(package.get("platform")), str(package.get("architecture")))
        if not all(key) or not package.get("runtime") or key in package_keys or digest in packages:
            raise ValidationError("duplicate or incomplete package identity")
        package_keys.add(key)
        packages[digest] = package
    if not packages:
        raise ValidationError("candidate needs package identities")
    environments: dict[str, dict[str, Any]] = {}
    for environment in candidate.get("environments", []):
        identity = str(environment.get("id", ""))
        required = ("os", "platform", "architecture", "runtime", "framework")
        if not identity or identity in environments or not all(environment.get(key) for key in required):
            raise ValidationError("duplicate or incomplete environment identity")
        environments[identity] = environment
    if not environments:
        raise ValidationError("candidate needs environment identities")
    return packages, environments


def _validate_evidence(item: dict[str, Any], scenario: dict[str, Any], record: dict[str, Any], packages: dict[str, dict[str, Any]], environments: dict[str, dict[str, Any]], root: pathlib.Path, expected_result: str) -> set[str]:
    if item.get("scenario_id") != scenario["id"]:
        raise ValidationError("evidence scenario binding mismatch")
    binding = item.get("candidate", {})
    candidate = record["candidate"]
    if binding != {"product_version": candidate["product_version"], "source_revision": candidate["source_revision"], "catalog_digest": record["catalog_digest"]}:
        raise ValidationError("evidence candidate binding mismatch")
    environment = environments.get(item.get("environment_id"))
    package = packages.get(item.get("package_digest"))
    if environment is None or package is None:
        raise ValidationError("evidence environment or package binding mismatch")
    if package.get("platform") != environment.get("platform") or package.get("architecture") != environment.get("architecture"):
        raise ValidationError("bound package and environment platform mismatch")
    covered = set(item.get("covered_requirements", []))
    if not covered or not covered <= set(scenario["requirements"]):
        raise ValidationError("evidence requirement coverage mismatch")
    if item.get("kind") == "automated":
        argv = item.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
            raise ValidationError("automated argv must be non-empty string array")
        if not isinstance(item.get("working_directory"), str) or not item["working_directory"]:
            raise ValidationError("invalid working directory identity")
        start = _timestamp(item.get("started_at"), "automated start")
        finish = _timestamp(item.get("finished_at"), "automated finish")
        if finish < start or item.get("outcome") not in OUTCOMES:
            raise ValidationError("invalid automated outcome chronology")
        if item["outcome"] == "passed" and item.get("exit_status") != 0:
            raise ValidationError("passed automated evidence needs exit status zero")
        if expected_result == "passed" and item.get("conclusion") != "passed":
            raise ValidationError("passed attempt has contradictory automated evidence")
        output = item.get("output", {})
        total = output.get("total_chars")
        omitted = output.get("omitted_chars")
        if not isinstance(output.get("text"), str) or isinstance(total, bool) or isinstance(omitted, bool) or not isinstance(total, int) or not isinstance(omitted, int) or total < 0 or omitted < 0 or len(output["text"]) > MAX_RETAINED_OUTPUT_CHARS or total != len(output["text"]) + omitted or output.get("truncated") != (omitted > 0):
            raise ValidationError("invalid bounded output")
        raw = item.get("raw_output", {})
        _evidence_path(root, raw.get("path"), raw.get("sha256"), raw.get("size"))
        fixture = item.get("fixture", {})
        opening = fixture.get("opening_revision")
        if not fixture.get("identity") or not isinstance(opening, str) or not fixture.get("opening_state"):
            raise ValidationError("incomplete fixture identity")
        for artifact in item.get("artifacts", []):
            if artifact.get("action") not in {"created", "changed", "generated", "deleted"}:
                raise ValidationError("invalid artifact action")
            _evidence_path(root, artifact.get("path"), artifact.get("sha256"), artifact.get("size"))
    elif item.get("kind") == "manual":
        if "manual" not in scenario["method"].lower():
            raise ValidationError("manual evidence is not permitted by scenario method")
        for key in ("actor", "time", "procedure", "expected", "actual", "conclusion", "reason"):
            _require(item.get(key), f"manual {key}")
        _timestamp(item["time"], "manual")
        if item["conclusion"] != expected_result:
            raise ValidationError("passed manual evidence needs passed conclusion")
    else:
        raise ValidationError("unknown evidence kind")
    return covered


def validate_record(record: dict[str, Any], catalog: dict[str, Any], evidence_root: pathlib.Path) -> None:
    """@brief Validates record integrity without deriving a release verdict."""
    validate_catalog(catalog)
    root = _root(evidence_root)
    if record.get("schema_version") != 1 or record.get("catalog_digest") != canonical_digest(catalog):
        raise ValidationError("record schema or catalog digest is invalid")
    packages, environments = _candidate_indexes(record.get("candidate", {}))
    scenarios = {item["id"]: item for item in catalog["scenarios"]}
    results = record.get("results", [])
    if len(results) != len(scenarios) or {item.get("scenario_id") for item in results} != set(scenarios):
        raise ValidationError("results must cover each scenario exactly once")
    for entry in results:
        result = entry.get("result")
        attempts = entry.get("attempts", [])
        if result not in RESULTS or (result != "not_run" and not attempts):
            raise ValidationError("invalid result or missing attempt")
        latest_time: datetime_module.datetime | None = None
        for attempt in attempts:
            if attempt.get("result") not in RESULTS:
                raise ValidationError("unknown attempt result")
            attempt_time = _timestamp(attempt.get("time"), "attempt")
            if latest_time is not None and attempt_time < latest_time:
                raise ValidationError("attempts are not chronological")
            latest_time = attempt_time
            if attempt["result"] in {"deferred", "not_applicable"}:
                for key in ("actor", "reason", "time", "requirements"):
                    _require(attempt.get(key), f"approval {key}")
                approved = set(attempt["requirements"])
                scenario_requirements = set(scenarios[entry["scenario_id"]]["requirements"])
                if not approved <= scenario_requirements:
                    raise ValidationError("approval requirement coverage mismatch")
                if attempt["result"] == "deferred" and any(catalog["requirements"][item] == "Must" for item in approved):
                    raise ValidationError("Must requirement cannot be deferred")
                if attempt["result"] == "not_applicable":
                    authorized = set(scenarios[entry["scenario_id"]].get("non_applicable_requirements", []))
                    if any(catalog["requirements"][item] == "Must" and item not in authorized for item in approved):
                        raise ValidationError("Must non-applicability lacks catalog authority")
            if attempt["result"] == "passed":
                evidence = attempt.get("evidence", [])
                if not evidence:
                    raise ValidationError("passed attempt needs evidence")
                for item in evidence:
                    finish = _timestamp(item.get("finished_at", item.get("time")), "evidence finish")
                    if finish > attempt_time:
                        raise ValidationError("attempt precedes retained evidence")
                    _validate_evidence(item, scenarios[entry["scenario_id"]], record, packages, environments, root, "passed")
            elif attempt["result"] in {"failed", "blocked", "not_run"}:
                if not attempt.get("reason"):
                    raise ValidationError("unfavorable attempt needs reason")
                evidence = attempt.get("evidence", [])
                if evidence:
                    for item in evidence:
                        _validate_evidence(item, scenarios[entry["scenario_id"]], record, packages, environments, root, attempt["result"])
                elif not isinstance(attempt.get("blocker"), dict) or not attempt["blocker"].get("kind"):
                    raise ValidationError("unfavorable attempt needs evidence or blocker")
        if attempts and entry["result"] != attempts[-1]["result"]:
            raise ValidationError("entry result must equal latest attempt")


def compile_verdict(record: dict[str, Any], catalog: dict[str, Any], evidence_root: pathlib.Path) -> dict[str, Any]:
    """@brief Compiles requirement and matrix coverage into a deterministic verdict."""
    try:
        validate_record(record, catalog, evidence_root)
    except ValidationError as error:
        return {"verdict": "incomplete", "errors": [str(error)], "unfavorable": [], "retries": [], "deferrals": [], "missing_matrices": [], "evidence_references": [], "known_limitations": []}
    scenarios = {item["id"]: item for item in catalog["scenarios"]}
    entries = {item["scenario_id"]: item for item in record["results"]}
    covered: set[str] = set()
    deferred: set[str] = set()
    non_applicable: set[str] = set()
    unfavorable: list[str] = []
    retries: list[str] = []
    unfavorable_attempts: list[dict[str, Any]] = []
    evidence_refs: list[str] = []
    for identifier, entry in entries.items():
        if len(entry["attempts"]) > 1:
            retries.append(identifier)
        if entry["result"] in {"failed", "blocked", "not_run"}:
            unfavorable.append(identifier)
        for index, attempt in enumerate(entry["attempts"], start=1):
            if attempt["result"] in {"failed", "blocked", "not_run"}:
                unfavorable_attempts.append({"scenario_id": identifier, "index": index, "time": attempt["time"], "result": attempt["result"], "reason": attempt.get("reason", ""), "evidence": [item.get("raw_output", {}).get("path") for item in attempt.get("evidence", [])]})
        latest = entry["attempts"][-1] if entry["attempts"] else {}
        if entry["result"] == "passed":
            for evidence in latest.get("evidence", []):
                covered.update(evidence["covered_requirements"])
                if evidence["kind"] == "automated":
                    evidence_refs.append(evidence["raw_output"]["path"])
        if entry["result"] == "deferred":
            deferred.update(latest["requirements"])
        if entry["result"] == "not_applicable":
            non_applicable.update(latest["requirements"])
    requirements = catalog["requirements"]
    must_missing = sorted(item for item, priority in requirements.items() if priority == "Must" and item not in covered and item not in non_applicable)
    lower_missing = sorted(item for item, priority in requirements.items() if priority in {"Should", "Could"} and item not in covered and item not in deferred)
    invalid_deferrals = sorted(item for item in deferred if requirements.get(item) == "Must")
    matrix = catalog.get("required_matrices", {})
    packages, environments = _candidate_indexes(record["candidate"])
    passing_evidence = [evidence for entry in entries.values() if entry["result"] == "passed" for evidence in entry["attempts"][-1].get("evidence", [])]
    matrix_missing: list[str] = []
    for case in matrix.get("package_cases", []):
        if not any(all(packages[evidence["package_digest"]].get(key) == value for key, value in case.items() if key != "id") for evidence in passing_evidence):
            matrix_missing.append(f"package:{case['id']}")
    for case in matrix.get("workflow_cases", []):
        if not any(all(environments[evidence["environment_id"]].get(key) == value for key, value in case.items() if key != "id") for evidence in passing_evidence):
            matrix_missing.append(f"workflow:{case['id']}")
    errors = [f"missing Must requirement evidence: {item}" for item in must_missing]
    errors += [f"lower-priority requirement neither passed nor deferred: {item}" for item in lower_missing]
    errors += [f"invalid Must deferral: {item}" for item in invalid_deferrals]
    errors += [f"missing verified matrix evidence: {item}" for item in matrix_missing]
    if entries[matrix.get("required_success_scenario", "AC-SUCCESS-001")]["result"] != "passed":
        errors.append("AC-SUCCESS-001 is not passing")
    scenario_results = {result: sum(entry["result"] == result for entry in entries.values()) for result in sorted(RESULTS)}
    requirement_results = {priority: {"passed": sum(requirements[item] == priority and item in covered for item in requirements), "deferred": sum(requirements[item] == priority and item in deferred for item in requirements)} for priority in ("Must", "Should", "Could")}
    return {"verdict": "accepted" if not errors else "incomplete", "errors": errors, "candidate": record["candidate"], "catalog_digest": record["catalog_digest"], "catalog_totals": {"scenarios": len(scenarios), "requirements": len(requirements)}, "scenario_results": scenario_results, "requirement_results": requirement_results, "unfavorable": sorted(unfavorable), "unfavorable_attempts": unfavorable_attempts, "retries": sorted(retries), "deferrals": sorted(deferred), "missing_matrices": sorted(matrix_missing), "evidence_references": sorted(set(evidence_refs)), "known_limitations": record["candidate"].get("known_limitations", [])}


def _record_template(catalog: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": 1, "catalog_digest": canonical_digest(catalog), "candidate": candidate, "results": [{"scenario_id": item["id"], "result": "not_run", "attempts": []} for item in catalog["scenarios"]]}


def _markdown(report: dict[str, Any], timestamp: str) -> str:
    candidate = report.get("candidate", {})
    lines = ["# AEGIS acceptance completion record", "", f"Verdict: `{report['verdict']}`", f"Report timestamp: `{timestamp}`", f"Product version: `{candidate.get('product_version', 'unavailable')}`", f"Source revision: `{candidate.get('source_revision', 'unavailable')}`", f"Catalog digest: `{report.get('catalog_digest', 'unavailable')}`", "", "## Missing evidence", ""]
    decision = report.get("verdict_decision", {})
    lines.insert(4, f"Verdict actor: `{decision.get('actor', 'unavailable')}`")
    lines.insert(5, f"Verdict timestamp: `{decision.get('timestamp', 'unavailable')}`")
    lines.extend(f"- {item}" for item in report["errors"])
    lines.extend(["", "## Candidate packages", ""])
    lines.extend(f"- `{item}`" for item in candidate.get("packages", []))
    lines.extend(["", "## Candidate environments", ""])
    lines.extend(f"- `{item}`" for item in candidate.get("environments", []))
    lines.extend(["", "## Unfavorable attempts and retries", ""])
    lines.extend(f"- {item}" for item in report.get("unfavorable_attempts", []))
    lines.extend(f"- retry: {item}" for item in report.get("retries", []))
    lines.extend(["", "## Retained evidence", ""])
    lines.extend(f"- {item}" for item in report["evidence_references"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """@brief Provides catalog, init, validation, and report commands."""
    parser = argparse.ArgumentParser(description="Offline AEGIS acceptance-record validator")
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("catalog")
    for name in ("init", "validate", "report"):
        command = subcommands.add_parser(name)
        command.add_argument("--catalog", default=str(pathlib.Path(__file__).with_name("aegis_acceptance_catalog.json")))
    init = subcommands.choices["init"]
    init.add_argument("--candidate-json", required=True)
    init.add_argument("--output", required=True)
    init.add_argument("--force", action="store_true")
    validate = subcommands.choices["validate"]
    validate.add_argument("record")
    validate.add_argument("--evidence-root", required=True)
    report = subcommands.choices["report"]
    report.add_argument("record")
    report.add_argument("--evidence-root", required=True)
    report.add_argument("--json-output", required=True)
    report.add_argument("--markdown-output", required=True)
    report.add_argument("--report-timestamp", required=True)
    report.add_argument("--verdict-actor", required=True)
    report.add_argument("--verdict-timestamp", required=True)
    report.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    catalog = _load(getattr(args, "catalog", str(pathlib.Path(__file__).with_name("aegis_acceptance_catalog.json"))))
    if args.command == "catalog":
        validate_catalog(catalog)
        print(json.dumps(catalog, sort_keys=True, indent=2))
        return 0
    if args.command == "init":
        candidate = _load(args.candidate_json)
        record = _record_template(catalog, candidate)
        validate_record(record, catalog, pathlib.Path(args.output).parent)
        _atomic_write(args.output, json.dumps(record, sort_keys=True, indent=2) + "\n", args.force)
        return 0
    record = _load(args.record)
    verdict = compile_verdict(record, catalog, pathlib.Path(args.evidence_root))
    if args.command == "validate":
        print(json.dumps(verdict, sort_keys=True))
        return 0 if verdict["verdict"] == "accepted" else 1
    _timestamp(args.report_timestamp, "report")
    _timestamp(args.verdict_timestamp, "verdict")
    if not args.verdict_actor:
        raise ValidationError("verdict actor is required")
    verdict["verdict_decision"] = {
        "actor": args.verdict_actor,
        "timestamp": args.verdict_timestamp,
    }
    json_content = json.dumps(verdict, sort_keys=True, indent=2) + "\n"
    markdown_content = _markdown(verdict, args.report_timestamp)
    _atomic_write(args.json_output, json_content, args.force)
    _atomic_write(args.markdown_output, markdown_content, args.force)
    return 0 if verdict["verdict"] == "accepted" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValidationError, OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}")
