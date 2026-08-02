#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_workflow_configuration.py
@brief Verify strict schema-version-3 workflow configuration behavior.
@details Covers typed errors, policy consistency, normalization, immutable
         records, and the agent-facing config CLI commands.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest

import aegis.cli as cli_module
from aegis.cli import main
from aegis.config import ConfigurationError, effective_config_dict, load_config
from aegis.models import ALL_STAGES

# HELPER FUNCTIONS


def _write(repo_root: Path, text: str) -> Path:
    """@brief Write one workflow configuration test document."""
    path = repo_root / ".agentic" / "workflow.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _replace(text: str, old: str, new: str) -> str:
    """@brief Replace one unique fixture fragment and assert fixture drift."""
    assert text.count(old) == 1
    return text.replace(old, new)


def _error(repo_root: Path, code: str) -> ConfigurationError:
    """@brief Load an invalid document and return its typed error."""
    with pytest.raises(ConfigurationError) as exc_info:
        load_config(repo_root)
    assert exc_info.value.code == code
    return exc_info.value


# TESTS


def test_complete_unrestricted_configuration_parses_as_immutable_model(
    tmp_path: Path,
    write_unrestricted_workflow_toml: Callable[[Path], Path],
) -> None:
    """@brief The complete unrestricted fixture produces immutable records."""
    write_unrestricted_workflow_toml(tmp_path)

    config = load_config(tmp_path)

    assert config.schema_version == 3
    assert config.source_roots == ("src", "app", "lib")
    assert config.write_access.mode == "unrestricted"
    assert config.write_access.stages == {}
    assert config.secrets.mode == "disabled"
    with pytest.raises(FrozenInstanceError):
        config.schema_version = 3  # type: ignore[misc]


def test_missing_configuration_is_actionable(tmp_path: Path) -> None:
    """@brief A missing workflow.toml never creates an implicit configuration."""
    (tmp_path / ".agentic" / "workflow.toml").unlink()
    error = _error(tmp_path, "CONFIG-MISSING")

    assert error.key_path == ""
    assert "aegis config validate" in error.remediation
    assert str(error).startswith("CONFIG-MISSING:")


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("not = valid = toml", "CONFIG-TOML-INVALID"),
        ("[source]\nroots = [\"src\"]\n", "CONFIG-SCHEMA-UNSUPPORTED"),
        ("schema_version = \"2\"\n", "CONFIG-SCHEMA-UNSUPPORTED"),
    ],
)
def test_file_and_schema_failures_use_stable_codes(
    tmp_path: Path, text: str, code: str
) -> None:
    """@brief TOML and schema failures remain machine-classifiable."""
    _write(tmp_path, text)
    _error(tmp_path, code)


def test_missing_section_and_key_are_distinct(
    tmp_path: Path, unrestricted_workflow_toml: str
) -> None:
    """@brief Missing tables and keys use their exclusive error codes."""
    without_source = _replace(
        unrestricted_workflow_toml,
        '[source]\nroots = ["src", "app", "lib"]\n\n',
        "",
    )
    _write(tmp_path, without_source)
    _error(tmp_path, "CONFIG-SECTION-MISSING")

    missing_roots = _replace(
        unrestricted_workflow_toml,
        'roots = ["src", "app", "lib"]',
        "# roots deliberately omitted",
    )
    _write(tmp_path, missing_roots)
    _error(tmp_path, "CONFIG-KEY-MISSING")


def test_unknown_key_and_wrong_type_are_rejected(
    tmp_path: Path, unrestricted_workflow_toml: str
) -> None:
    """@brief Closed tables reject unknown keys and exact types are enforced."""
    unknown = _replace(
        unrestricted_workflow_toml,
        '[source]\nroots = ["src", "app", "lib"]',
        '[source]\nroots = ["src", "app", "lib"]\nlegacy = true',
    )
    _write(tmp_path, unknown)
    _error(tmp_path, "CONFIG-TYPE-INVALID")

    wrong_type = _replace(
        unrestricted_workflow_toml,
        "max_bundle_components = 5",
        "max_bundle_components = true",
    )
    _write(tmp_path, wrong_type)
    _error(tmp_path, "CONFIG-TYPE-INVALID")


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (
            '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
            '[guardrails.secrets]\nmode = "disabled"\npatterns = ["token"]',
        ),
        (
            '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
            '[guardrails.working_tree]\nmode = "restricted"\nblocked_patterns = []',
        ),
        (
            '[guardrails.scope]\nmode = "unrestricted"\nallowed_roots = []',
            '[guardrails.scope]\nmode = "advisory"\nallowed_roots = []',
        ),
        (
            '[gates.test]\nmode = "disabled"\ncommands = []',
            '[gates.test]\nmode = "enforce"\ncommands = []',
        ),
    ],
)
def test_policy_modes_reject_contradictory_rule_sets(
    tmp_path: Path, unrestricted_workflow_toml: str, old: str, new: str
) -> None:
    """@brief Dormant rules and empty restrictive modes are inconsistent."""
    _write(tmp_path, _replace(unrestricted_workflow_toml, old, new))
    _error(tmp_path, "CONFIG-INCONSISTENT")


@pytest.mark.parametrize(
    ("old", "new", "key_path"),
    [
        (
            '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
            '[guardrails.secrets]\nmode = "enforce"\npatterns = ["["]',
            "guardrails.secrets.patterns",
        ),
        (
            'test_file_patterns = ["test_*.py", "*_test.py"]',
            'test_file_patterns = ["test_[.py"]',
            "traceability.test_file_patterns",
        ),
        (
            'roots = ["src", "app", "lib"]',
            'roots = ["src", "src/../secret"]',
            "source.roots",
        ),
        (
            'roots = ["src", "app", "lib"]',
            'roots = ["./src", "src"]',
            "source.roots",
        ),
    ],
)
def test_invalid_and_duplicate_normalized_rules_are_rejected(
    tmp_path: Path,
    unrestricted_workflow_toml: str,
    old: str,
    new: str,
    key_path: str,
) -> None:
    """@brief Regexes, globs, paths, and normalized duplicates are validated."""
    _write(tmp_path, _replace(unrestricted_workflow_toml, old, new))
    error = _error(tmp_path, "CONFIG-RULE-INVALID")
    assert error.key_path == key_path


def test_stage_restricted_mode_requires_every_supported_stage(
    tmp_path: Path, unrestricted_workflow_toml: str
) -> None:
    """@brief A stage-restricted map is closed and complete over ALL_STAGES."""
    incomplete = _replace(
        unrestricted_workflow_toml,
        '[guardrails.write_access]\nmode = "unrestricted"',
        '[guardrails.write_access]\nmode = "stage_restricted"\n\n'
        '[guardrails.write_access.stages]\nintake = []',
    )
    _write(tmp_path, incomplete)
    _error(tmp_path, "CONFIG-KEY-MISSING")

    stage_lines = "\n".join(
        f'{stage} = ["src/**"]' if stage == "implementation" else f"{stage} = []"
        for stage in ALL_STAGES
    )
    complete = _replace(
        unrestricted_workflow_toml,
        '[guardrails.write_access]\nmode = "unrestricted"',
        '[guardrails.write_access]\nmode = "stage_restricted"\n\n'
        f"[guardrails.write_access.stages]\n{stage_lines}",
    )
    _write(tmp_path, complete)

    config = load_config(tmp_path)
    assert tuple(config.write_access.stages) == tuple(ALL_STAGES)
    assert config.write_access.stages["validation"] == ()
    assert effective_config_dict(config)["guardrails"]["write_access"]["active_rule_count"] == 1


def test_every_restrictive_policy_mode_parses_when_rules_are_complete(
    tmp_path: Path, unrestricted_workflow_toml: str
) -> None:
    """@brief All ratified restrictive policy modes accept complete rules."""
    text = unrestricted_workflow_toml
    replacements = [
        (
            '[components.baseline_guard]\nmode = "disabled"',
            '[components.baseline_guard]\nmode = "enforce"\n'
            'minimum_completion_level = "baseline-usable"',
        ),
        (
            '[traceability.coverage]\nmode = "disabled"\ncoverable_roots = []\nexclude = []',
            '[traceability.coverage]\nmode = "enforce"\n'
            'coverable_roots = ["src"]\nexclude = []',
        ),
        (
            '[adoption.source_changes]\nmode = "unrestricted"',
            '[adoption.source_changes]\nmode = "blocked"',
        ),
        (
            '[alignment.protected_scope]\nmode = "disabled"\npatterns = []',
            '[alignment.protected_scope]\nmode = "enforce"\npatterns = ["infra/**"]',
        ),
        (
            '[gates.test]\nmode = "disabled"\ncommands = []',
            '[gates.test]\nmode = "enforce"\ncommands = ["pytest -q"]',
        ),
        (
            '[guardrails.secrets]\nmode = "disabled"\npatterns = []',
            '[guardrails.secrets]\nmode = "enforce"\npatterns = ["token-[0-9]+"]',
        ),
        (
            '[guardrails.protected_paths]\nmode = "disabled"\npatterns = []\noperations = []',
            '[guardrails.protected_paths]\nmode = "enforce"\n'
            'patterns = ["private/**"]\noperations = ["read", "write"]',
        ),
        (
            '[guardrails.working_tree]\nmode = "unrestricted"\nblocked_patterns = []',
            '[guardrails.working_tree]\nmode = "restricted"\nblocked_patterns = ["dist/**"]',
        ),
        (
            '[guardrails.scope]\nmode = "unrestricted"\nallowed_roots = []',
            '[guardrails.scope]\nmode = "enforce"\nallowed_roots = ["src"]',
        ),
        (
            '[guardrails.delivery]\nmode = "disabled"\ncommand_patterns = []',
            '[guardrails.delivery]\nmode = "enforce"\ncommand_patterns = ["git   push"]',
        ),
    ]
    for old, new in replacements:
        text = _replace(text, old, new)
    _write(tmp_path, text)
    (tmp_path / ".agentic" / "components.toml").write_text(
        "[components]\n", encoding="utf-8"
    )

    config = load_config(tmp_path)

    assert config.component_baseline_guard.mode == "enforce"
    assert config.coverage.mode == "enforce"
    assert config.adoption_source_changes.mode == "blocked"
    assert config.protected_paths.operations == ("read", "write")
    assert config.delivery.command_patterns == ("git push",)


def test_config_cli_validate_show_and_json_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    write_unrestricted_workflow_toml: Callable[[Path], Path],
) -> None:
    """@brief CLI config commands expose deterministic success and error JSON."""
    write_unrestricted_workflow_toml(tmp_path)
    monkeypatch.chdir(tmp_path)

    main(["config", "validate", "--json"])
    validated = json.loads(capsys.readouterr().out)
    assert validated["status"] == "ok"
    assert validated["schema_version"] == 3

    main(["config", "show", "--json"])
    shown = json.loads(capsys.readouterr().out)
    assert shown["config"] == effective_config_dict(load_config(tmp_path))
    assert shown["config"]["guardrails"]["secrets"]["active_rule_count"] == 0

    (tmp_path / ".agentic" / "workflow.toml").unlink()
    with pytest.raises(SystemExit) as exc_info:
        main(["config", "validate", "--json"])
    assert exc_info.value.code == 1
    error = json.loads(capsys.readouterr().out)
    assert error["code"] == "CONFIG-MISSING"
    assert error["key_path"] == ""


def test_graph_command_loads_configuration_once_at_cli_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Verify one graph command parses workflow policy exactly once.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest monkeypatch fixture.
    @param[in] capsys Pytest output capture fixture.
    @return None.
    """
    monkeypatch.chdir(tmp_path)
    main(["run", "start", "feature", "--json"])
    capsys.readouterr()

    original = cli_module.load_config
    calls = 0

    def counting_load_config(repo_root: Path):  # type: ignore[no-untyped-def]
        """@brief Count canonical parser invocations for one CLI operation."""
        nonlocal calls
        calls += 1
        return original(repo_root)

    monkeypatch.setattr(cli_module, "load_config", counting_load_config)
    main(["run", "status", "--json"])

    assert calls == 1
    assert json.loads(capsys.readouterr().out)["run_id"]


def test_invalid_configuration_stops_command_before_state_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    @brief Verify ordinary CLI actions fail closed before writing run state.
    @param[in] tmp_path Temporary repository root.
    @param[in] monkeypatch Pytest monkeypatch fixture.
    @param[in] capsys Pytest output capture fixture.
    @return None.
    """
    (tmp_path / ".agentic" / "workflow.toml").unlink()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as raised:
        main(["run", "start", "feature", "--json"])

    assert raised.value.code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "blocked"
    assert output["code"] == "CONFIG-MISSING"
    assert not (tmp_path / ".agentic" / "runs").exists()
    assert not (tmp_path / ".agentic" / ".workspace").exists()


# END OF FILE
