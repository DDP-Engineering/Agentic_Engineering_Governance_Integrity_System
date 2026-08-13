#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_aegis_acceptance.py
@brief Focused regressions for fail-closed acceptance evidence.
@details Uses only synthetic catalogs, records, and retained temporary files.
"""

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

TOOLS = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(TOOLS))

import aegis_acceptance as acceptance

PROVENANCE_NOTICE = (
    "Operator-attested evidence only: this tool validates acceptance records "
    "and retained evidence; it executes no acceptance scenarios or project commands."
)


def sha256(content: bytes) -> str:
    """@brief Returns a SHA-256 suitable for retained evidence."""
    return hashlib.sha256(content).hexdigest()


class AcceptanceTests(unittest.TestCase):
    """@brief Tests integrity, coverage, matrix, and CLI contracts."""

    def setUp(self) -> None:
        requirements = {"PR-MUST-001": "Must", "PR-SHOULD-001": "Should"}
        requirements.update({f"PR-MUST-{index:03d}": "Must" for index in range(2, 207)})
        requirements.update({f"PR-SHOULD-{index:03d}": "Should" for index in range(2, 18)})
        requirements.update({f"PR-COULD-{index:03d}": "Could" for index in range(1, 4)})
        scenarios = [{"id": "AC-ONE-001", "priority": "Must", "method": "Automated", "requirements": ["PR-MUST-001"]}, {"id": "AC-SUCCESS-001", "priority": "Must/Should", "method": "Automated/manual", "requirements": ["PR-MUST-001", "PR-SHOULD-001"]}]
        scenarios.append({"id": "AC-EXTRA-001", "priority": "Must/Should", "method": "Automated", "requirements": list(requirements)[2:]})
        scenarios.extend({"id": f"AC-EXTRA-{index:03d}", "priority": "Must", "method": "Automated", "requirements": ["PR-MUST-001"]} for index in range(2, 57))
        self.catalog = {"schema_version": 1, "catalog_name": "synthetic acceptance catalog", "requirements": requirements, "scenarios": scenarios, "required_matrices": {"required_success_scenario": "AC-SUCCESS-001", "package_cases": [{"id": "aegis-win", "edition": "aegis", "platform": "windows", "architecture": "x86_64", "runtime": "external"}], "workflow_cases": [{"id": "win-pytest", "platform": "windows", "architecture": "x86_64", "framework": "pytest"}]}}

    def candidate(self) -> dict:
        return {"product_version": "1.0.0", "source_revision": "a" * 40, "created_at": "2026-08-12T00:00:00Z", "python": {"implementation": "CPython", "version": "3.12"}, "git": {"version": "2.0"}, "runtime": {"identity": "external"}, "packages": [{"edition": "aegis", "platform": "windows", "architecture": "x86_64", "runtime": "external", "digest": "b" * 64}], "environments": [{"id": "win-pytest", "os": "Windows", "platform": "windows", "architecture": "x86_64", "runtime": "external", "framework": "pytest"}], "known_limitations": ["synthetic"]}

    def record(self) -> dict:
        return {"schema_version": 1, "catalog_digest": acceptance.canonical_digest(self.catalog), "candidate": self.candidate(), "results": [{"scenario_id": item["id"], "result": "not_run", "attempts": []} for item in self.catalog["scenarios"]]}

    def evidence(self, root: pathlib.Path, scenario: str, covered: list[str]) -> dict:
        content = b"retained output"; (root / "output.txt").write_bytes(content)
        return {"kind": "automated", "scenario_id": scenario, "candidate": {"product_version": "1.0.0", "source_revision": "a" * 40, "catalog_digest": acceptance.canonical_digest(self.catalog)}, "environment_id": "win-pytest", "package_digest": "b" * 64, "covered_requirements": covered, "argv": ["python", "-m", "pytest"], "working_directory": ".", "started_at": "2026-08-12T00:00:00Z", "finished_at": "2026-08-12T00:00:01Z", "outcome": "passed", "exit_status": 0, "conclusion": "passed", "output": {"text": "ok", "total_chars": 2, "omitted_chars": 0, "truncated": False}, "raw_output": {"path": "output.txt", "sha256": sha256(content), "size": len(content)}, "fixture": {"identity": "fixture", "opening_revision": "c" * 40, "opening_state": "clean"}, "artifacts": [], "matrix": {"edition": "aegis", "platform": "windows", "runtime": "external", "framework": "pytest"}}

    def passing(self, root: pathlib.Path) -> dict:
        record = self.record()
        for item in record["results"]:
            requirements = next(x["requirements"] for x in self.catalog["scenarios"] if x["id"] == item["scenario_id"])
            item["result"] = "passed"; item["attempts"] = [{"result": "passed", "time": "2026-08-12T00:00:02Z", "evidence": [self.evidence(root, item["scenario_id"], requirements)]}]
        return record

    def test_requirement_coverage_and_matrix_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); record = self.passing(root)
            report = acceptance.compile_verdict(record, self.catalog, root)
            self.assertEqual("accepted", report["verdict"])
            self.assertEqual(PROVENANCE_NOTICE, report["provenance"])
            record["results"][1]["attempts"][0]["evidence"][0]["covered_requirements"] = ["PR-MUST-001"]
            report = acceptance.compile_verdict(record, self.catalog, root)
            self.assertIn("PR-SHOULD-001", " ".join(report["errors"]))
            record = self.passing(root)
            record["candidate"]["packages"][0]["edition"] = "other"
            self.assertIn("missing verified matrix evidence", " ".join(acceptance.compile_verdict(record, self.catalog, root)["errors"]))

    def test_binding_retry_timestamp_and_path_defects_reject(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); record = self.passing(root)
            evidence = record["results"][0]["attempts"][0]["evidence"][0]
            evidence["scenario_id"] = "AC-SUCCESS-001"
            with self.assertRaises(acceptance.ValidationError): acceptance.validate_record(record, self.catalog, root)

    def test_unfavorable_attempt_and_matrix_spoof_reject(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            record = self.passing(root)
            record["results"][0]["attempts"] = [{"result": "failed", "time": "2026-08-12T00:00:02Z"}]
            record["results"][0]["result"] = "failed"
            with self.assertRaises(acceptance.ValidationError):
                acceptance.validate_record(record, self.catalog, root)
            catalog = json.loads(json.dumps(self.catalog))
            catalog["required_matrices"]["package_cases"].append({"id": "waegis-ubuntu", "edition": "waegis", "platform": "ubuntu", "architecture": "x86_64", "runtime": "external"})
            record = self.passing(root)
            record["catalog_digest"] = acceptance.canonical_digest(catalog)
            for result in record["results"]:
                result["attempts"][0]["evidence"][0]["candidate"]["catalog_digest"] = record["catalog_digest"]
            evidence = record["results"][0]["attempts"][0]["evidence"][0]
            evidence["matrix"] = {"edition": "waegis", "platform": "ubuntu"}
            self.assertEqual("incomplete", acceptance.compile_verdict(record, catalog, root)["verdict"])

    def test_native_working_directory_and_package_environment_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            record = self.passing(root)
            evidence = record["results"][0]["attempts"][0]["evidence"][0]
            evidence["working_directory"] = "C:\\work\\fixture"
            acceptance.validate_record(record, self.catalog, root)
            record["candidate"]["environments"][0]["platform"] = "ubuntu"
            with self.assertRaises(acceptance.ValidationError):
                acceptance.validate_record(record, self.catalog, root)
            record = self.passing(root); attempt = record["results"][0]["attempts"][0]; attempt["result"] = "failed"
            with self.assertRaises(acceptance.ValidationError): acceptance.validate_record(record, self.catalog, root)
            record = self.passing(root); evidence = record["results"][0]["attempts"][0]["evidence"][0]; evidence["raw_output"]["path"] = "..\\escape"
            with self.assertRaises(acceptance.ValidationError): acceptance.validate_record(record, self.catalog, root)

    def test_deferred_must_and_artifact_digest_reject(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); record = self.passing(root)
            record["results"][0] = {"scenario_id": "AC-ONE-001", "result": "deferred", "attempts": [{"result": "deferred", "time": "2026-08-12T00:00:01Z", "actor": "r", "reason": "no", "requirements": ["PR-MUST-001"]}]}
            self.assertIn("Must requirement cannot be deferred", " ".join(acceptance.compile_verdict(record, self.catalog, root)["errors"]))
            record = self.passing(root); evidence = record["results"][0]["attempts"][0]["evidence"][0]; evidence["artifacts"] = [{"action": "changed", "path": "output.txt", "sha256": "0" * 64, "size": 1}]
            with self.assertRaises(acceptance.ValidationError): acceptance.validate_record(record, self.catalog, root)

    def test_must_not_applicable_needs_catalog_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); record = self.passing(root)
            record["results"][0] = {"scenario_id": "AC-ONE-001", "result": "not_applicable", "attempts": [{"result": "not_applicable", "time": "2026-08-12T00:00:01Z", "actor": "r", "reason": "no", "requirements": ["PR-MUST-001"]}]}
            with self.assertRaises(acceptance.ValidationError): acceptance.validate_record(record, self.catalog, root)

    def test_totals_invariant_applies_to_a_renamed_catalog(self) -> None:
        catalog = json.loads(json.dumps(self.catalog))
        catalog["catalog_name"] = "renamed acceptance catalog"
        catalog["scenarios"].pop()
        with self.assertRaisesRegex(acceptance.ValidationError, "authoritative catalog totals"):
            acceptance.validate_catalog(catalog)

    def test_cli_init_validate_report_and_overwrite(self) -> None:
        command = [sys.executable, str(TOOLS / "aegis_acceptance.py")]
        self.assertEqual(0, subprocess.run(command + ["--help"], capture_output=True, text=True, check=False).returncode)
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary); candidate = root / "candidate.json"; candidate.write_text(json.dumps(self.candidate()), encoding="utf-8")
            record = root / "record.json"; catalog = TOOLS / "aegis_acceptance_catalog.json"
            done = subprocess.run(command + ["init", "--catalog", str(catalog), "--candidate-json", str(candidate), "--output", str(record)], capture_output=True, text=True, check=False)
            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual(PROVENANCE_NOTICE, json.loads(record.read_text(encoding="utf-8"))["provenance"])
            validated = subprocess.run(command + ["validate", "--catalog", str(catalog), "--evidence-root", str(root), str(record)], capture_output=True, text=True, check=False)
            self.assertNotEqual(0, validated.returncode)
            self.assertEqual(PROVENANCE_NOTICE, json.loads(validated.stdout)["provenance"])
            self.assertNotEqual(0, subprocess.run(command + ["init", "--catalog", str(catalog), "--candidate-json", str(candidate), "--output", str(record)], capture_output=True, text=True, check=False).returncode)
            report = subprocess.run(command + ["report", "--catalog", str(catalog), "--evidence-root", str(root), "--json-output", str(root / "report.json"), "--markdown-output", str(root / "report.md"), "--report-timestamp", "2026-08-12T00:00:00Z", "--verdict-actor", "release-reviewer", "--verdict-timestamp", "2026-08-12T00:00:00Z", str(record)], capture_output=True, text=True, check=False)
            self.assertNotEqual(0, report.returncode)
            report_json = json.loads((root / "report.json").read_text(encoding="utf-8"))
            report_markdown = (root / "report.md").read_text(encoding="utf-8")
            self.assertEqual(PROVENANCE_NOTICE, report_json["provenance"])
            self.assertIn(PROVENANCE_NOTICE, report_markdown)
            self.assertIn("release-reviewer", report_markdown)


if __name__ == "__main__":
    unittest.main()
