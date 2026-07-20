#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_commands_analyze.py
@brief Tests for ``waegis analyze`` (T3.3): manifest states, drift, workflow
       inventory, human + ``--json`` rendering, and the repo-not-found failure.
@details Strictly offline, synthetic ``tmp_path`` fixture trees only. The
         known adapter directory name list is cross-checked against the real
         ``05_Software/aegis/template/`` directory so :data:`ADAPTER_DIR_NAMES`
         cannot silently drift from what the template actually ships.
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import json
from pathlib import Path

from waegis.commands.analyze import (
    ADAPTER_DIR_NAMES,
    AGENTIC_DIR_RELATIVE_PATH,
    EXIT_OK,
    EXIT_REPO_NOT_FOUND,
    analyze_report_json,
    build_analyze_report,
    render_analyze_report,
    run_analyze,
)
from waegis.payload.manifest import build_manifest, write_manifest

# LOCAL HELPERS


def _install_valid_manifest(root: Path, *, files: dict[str, str]) -> None:
    """
    @brief      Write real files under ``root`` and a matching valid manifest.
    @param[in]  root Repo root directory.
    @param[in]  files Mapping of repo-relative path to file content.
    @return     None
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    for rel_path, content in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    manifest = build_manifest(
        root,
        product="aegis",
        payload_version="0.4.0",
        mode="new",
        file_paths=list(files),
        installed_at="2026-07-13T00:00:00Z",
        installed_by="waegis 0.1.0",
    )
    write_manifest(root, manifest)


# TESTS

# --- adapter name drift guard --------------------------------------------------


def test_adapter_dir_names_match_the_real_template() -> None:
    """
    @brief      :data:`ADAPTER_DIR_NAMES` matches the agent adapter
                directories actually present in
                ``05_Software/aegis/template/`` — catches template drift
                rather than trusting a hardcoded guess.
    @return     None
    @exception  AssertionError If the constant and the real template diverge.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    template_root = Path(__file__).resolve().parents[2] / "aegis" / "template"
    real_adapter_dirs = {
        entry.name
        for entry in template_root.iterdir()
        if entry.is_dir() and entry.name.startswith(".") and entry.name != AGENTIC_DIR_RELATIVE_PATH
    }
    assert real_adapter_dirs == set(ADAPTER_DIR_NAMES)


# --- no-manifest cases -----------------------------------------------------


def test_plain_directory_reports_no_manifest_no_agentic(tmp_path: Path) -> None:
    """
    @brief      A plain directory with no ``.agentic/`` at all reports the
                absent-manifest state and ``agentic_present=False``; exit 0.
    @return     None
    @exception  AssertionError If the state, inventory, or exit code is wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    report = build_analyze_report(tmp_path)
    assert report.manifest.state == "absent"
    assert report.inventory.agentic_present is False
    assert report.drift is None

    stream = io.StringIO()
    assert run_analyze(tmp_path, as_json=False, stream=stream) == EXIT_OK


def test_legacy_agentic_without_manifest_reports_absent_distinctly(tmp_path: Path) -> None:
    """
    @brief      An ``.agentic/`` directory with no ``install-manifest.json``
                (pre-manifest legacy install) still reports the absent-manifest
                state, but ``agentic_present`` is True — distinguishing it from
                the no-``.agentic``-at-all case.
    @return     None
    @exception  AssertionError If the two no-manifest cases are not
                distinguished by ``agentic_present``.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    (tmp_path / ".agentic").mkdir()
    report = build_analyze_report(tmp_path)
    assert report.manifest.state == "absent"
    assert report.inventory.agentic_present is True


# --- invalid manifest --------------------------------------------------------


def test_malformed_manifest_reports_error_without_crashing(tmp_path: Path) -> None:
    """
    @brief      A malformed ``install-manifest.json`` reports the invalid
                state with the validation error surfaced, and does not raise;
                exit code is still 0 (plan §10.1: analyze renders no health
                verdicts, so a reportable finding like an invalid manifest is
                not a command failure at this command's level).
    @return     None
    @exception  AssertionError If the command raises, or the state/error/exit
                code are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    manifest_dir = tmp_path / ".agentic"
    manifest_dir.mkdir()
    (manifest_dir / "install-manifest.json").write_text("{not valid json", encoding="utf-8")

    report = build_analyze_report(tmp_path)
    assert report.manifest.state == "invalid"
    assert report.manifest.error is not None
    assert report.drift is None

    stream = io.StringIO()
    exit_code = run_analyze(tmp_path, as_json=False, stream=stream)
    assert exit_code == EXIT_OK
    assert "invalid" in stream.getvalue()


# --- valid manifest, no drift -----------------------------------------------


def test_valid_manifest_no_drift_reports_fields_and_zero_drift(tmp_path: Path) -> None:
    """
    @brief      A valid manifest matching the files on disk reports every
                manifest field and zero modified/missing files.
    @return     None
    @exception  AssertionError If any field or the drift counts are wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _install_valid_manifest(tmp_path, files={"AGENTS.md": "# AGENTS\n", ".agentic/cli.py": "print(1)\n"})

    report = build_analyze_report(tmp_path)
    assert report.manifest.state == "valid"
    assert report.manifest.product == "aegis"
    assert report.manifest.payload_version == "0.4.0"
    assert report.manifest.installed_at == "2026-07-13T00:00:00Z"
    assert report.manifest.installed_by == "waegis 0.1.0"
    assert report.manifest.mode == "new"
    assert report.manifest.file_count == 2
    assert report.manifest.generated_count == 0
    assert report.manifest.skipped_count == 0
    assert report.drift is not None
    assert report.drift.modified == ()
    assert report.drift.missing == ()


# --- valid manifest with drift ----------------------------------------------


def test_valid_manifest_with_drift_lists_modified_and_missing(tmp_path: Path) -> None:
    """
    @brief      One file edited and one file deleted after install: drift
                correctly lists both, and full paths are present in the
                ``--json`` output.
    @return     None
    @exception  AssertionError If either file is missing from the expected
                drift bucket, or the JSON omits the full paths.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _install_valid_manifest(
        tmp_path,
        files={"AGENTS.md": "# AGENTS\n", "edited.txt": "original\n", "deleted.txt": "gone soon\n"},
    )
    (tmp_path / "edited.txt").write_text("changed!\n", encoding="utf-8", newline="\n")
    (tmp_path / "deleted.txt").unlink()

    report = build_analyze_report(tmp_path)
    assert report.drift is not None
    assert report.drift.modified == ("edited.txt",)
    assert report.drift.missing == ("deleted.txt",)

    payload = json.loads(analyze_report_json(report))
    assert payload["drift"]["modified"] == ["edited.txt"]
    assert payload["drift"]["missing"] == ["deleted.txt"]


# --- adapter directory inventory --------------------------------------------


def test_adapter_inventory_reports_present_subset(tmp_path: Path) -> None:
    """
    @brief      A repo with a subset of the known adapter directories present
                reports exactly that subset as present, the rest absent.
    @return     None
    @exception  AssertionError If any adapter is misreported.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".qwen").mkdir()

    report = build_analyze_report(tmp_path)
    assert report.inventory.adapters["claude"] is True
    assert report.inventory.adapters["qwen"] is True
    assert report.inventory.adapters["codex"] is False
    assert report.inventory.adapters["opencode"] is False
    assert report.inventory.adapters["pi"] is False


def test_adapter_inventory_reports_none_present_as_not_a_failure(tmp_path: Path) -> None:
    """
    @brief      A repo with none of the known adapter directories present
                reports every adapter as absent, and this is not a command
                failure (exit 0).
    @return     None
    @exception  AssertionError If any adapter is misreported or exit != 0.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    report = build_analyze_report(tmp_path)
    assert all(present is False for present in report.inventory.adapters.values())

    stream = io.StringIO()
    assert run_analyze(tmp_path, as_json=False, stream=stream) == EXIT_OK


# --- --repo not found ---------------------------------------------------------


def test_repo_not_found_is_a_genuine_operational_failure(tmp_path: Path) -> None:
    """
    @brief      A ``--repo`` path that does not exist produces a clear error
                and a non-zero exit code — the one case distinct from every
                informational (manifest/drift/inventory) finding above.
    @return     None
    @exception  AssertionError If the exit code is 0 or no message is written.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    missing = tmp_path / "does-not-exist"
    stream = io.StringIO()
    exit_code = run_analyze(missing, as_json=False, stream=stream)
    assert exit_code == EXIT_REPO_NOT_FOUND
    assert exit_code != EXIT_OK
    assert stream.getvalue().strip() != ""


def test_repo_path_that_is_a_file_is_also_a_failure(tmp_path: Path) -> None:
    """
    @brief      A ``--repo`` path that exists but is a file, not a directory,
                is also a genuine operational failure.
    @return     None
    @exception  AssertionError If the exit code is 0.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    a_file = tmp_path / "not-a-dir.txt"
    a_file.write_text("x", encoding="utf-8")
    stream = io.StringIO()
    assert run_analyze(a_file, as_json=False, stream=stream) == EXIT_REPO_NOT_FOUND


# --- --json shape -------------------------------------------------------------


def test_json_output_is_valid_json_with_documented_keys_no_manifest(tmp_path: Path) -> None:
    """
    @brief      ``--json`` output for the no-manifest case parses via
                ``json.loads`` and carries the documented top-level and
                manifest-section keys.
    @return     None
    @exception  AssertionError If parsing fails or a documented key is absent.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    stream = io.StringIO()
    exit_code = run_analyze(tmp_path, as_json=True, stream=stream)
    assert exit_code == EXIT_OK

    payload = json.loads(stream.getvalue())
    assert set(payload) == {"schema_version", "command", "status", "exit_code", "plan", "result", "messages"}
    assert payload["command"] == "analyze"
    report = payload["result"]
    assert report["manifest"]["state"] == "absent"
    assert report["drift"] is None
    assert set(report["inventory"]) == {"agentic_present", "adapters"}
    assert isinstance(report["configuration_proposals"], dict)


def test_json_output_is_valid_json_with_documented_keys_valid_manifest_with_drift(tmp_path: Path) -> None:
    """
    @brief      ``--json`` output for the valid-manifest-with-drift case parses
                via ``json.loads`` and carries every documented field.
    @return     None
    @exception  AssertionError If parsing fails or a documented key/value is
                wrong.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _install_valid_manifest(tmp_path, files={"AGENTS.md": "# AGENTS\n", "edited.txt": "original\n"})
    (tmp_path / "edited.txt").write_text("changed!\n", encoding="utf-8", newline="\n")

    stream = io.StringIO()
    exit_code = run_analyze(tmp_path, as_json=True, stream=stream)
    assert exit_code == EXIT_OK

    payload = json.loads(stream.getvalue())
    report = payload["result"]
    assert report["manifest"]["state"] == "valid"
    assert report["manifest"]["product"] == "aegis"
    assert report["manifest"]["file_count"] == 2
    assert report["drift"]["modified"] == ["edited.txt"]
    assert report["drift"]["missing"] == []


# --- human rendering does not crash and mentions key facts -------------------


def test_human_render_mentions_manifest_and_inventory_sections(tmp_path: Path) -> None:
    """
    @brief      The human report includes the ``Manifest``, ``Drift``, and
                ``Workflow inventory`` sections for a valid-manifest repo.
    @return     None
    @exception  AssertionError If a section header is missing.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    _install_valid_manifest(tmp_path, files={"AGENTS.md": "# AGENTS\n"})
    report = build_analyze_report(tmp_path)
    stream = io.StringIO()
    render_analyze_report(report, stream)
    text = stream.getvalue()
    assert "Manifest:" in text
    assert "Drift:" in text
    assert "Workflow inventory:" in text
    assert "no drift detected" in text


# END OF FILE
