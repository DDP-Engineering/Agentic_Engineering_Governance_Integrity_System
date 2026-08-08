#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_documentation_workflow.py
@brief Workflow support module for test_documentation_workflow.
@details Covers expected workflow behavior through focused pytest checks.
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import re
import shlex
import subprocess
from pathlib import Path

from aegis.cli import _build_parser, _normalize_global_options
from aegis.config import load_config
from aegis.invariants import evaluate
from aegis.models import ALL_STAGES, ChangeUnit, Check, Graph, Intent, StageRecord
from aegis.stage_schema import STAGE_DONE_WHEN
from aegis.stage_forms import next_command

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# @brief Directory names that hold install-on-demand, gitignored third-party
#        artifacts (the .pi/ vitest toolchain). Template-hygiene walks skip these
#        because they are not part of the shipped template deliverable.
_DEPENDENCY_DIRS = {"node_modules", ".vitest", ".git", ".opencode-cache"}

# @brief Generated Python distribution-metadata directory suffix excluded from
#        template-hygiene walks because editable package builds create it locally.
_GENERATED_METADATA_SUFFIX = ".egg-info"

_DEVELOPMENT_STAGE_REFERENCES = (
    "intake",
    "alignment",
    "requirement",
    "design",
    "check",
    "implementation",
    "validation",
)

_ADOPTION_STAGE_REFERENCES = (
    "adoption-intake",
    "adoption-alignment",
    "repo-discovery",
    "component-map",
    "component-adoption",
    "baseline-review",
    "adoption-delivery",
)

_GRAPH_SIZE_CLAIM = re.compile(
    r"(?:graph|verify run).{0,160}(?:~?\d+\s*(?:kb|mb)|tens of kilobytes)",
    flags=re.IGNORECASE | re.DOTALL,
)


# TESTS


def test_default_documentation_config(tmp_path: Path) -> None:
    """
    @brief      Handle test default documentation config workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    cfg = load_config(tmp_path)

    assert cfg.documentation_roots == (".agentic/knowledge/components",)
    assert cfg.component_documentation_template == ".agentic/knowledge/components/component_template.md"
    assert cfg.alignment_enabled is True
    assert cfg.alignment_pause_on_open_questions is True
    assert cfg.alignment_risk_threshold == "medium"
    assert cfg.alignment_allow_recommended_responses is True
    assert cfg.alignment_protected_scope.patterns == ()


def test_alignment_config_reads_policy(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify intent-alignment policy configuration is loaded.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    replace_workflow_toml(
        "pause_on_open_questions = true", "pause_on_open_questions = false"
    )
    replace_workflow_toml('risk_threshold = "medium"', 'risk_threshold = "high"')
    replace_workflow_toml(
        "allow_recommended_responses = true", "allow_recommended_responses = false"
    )
    replace_workflow_toml(
        '[alignment.protected_scope]\nmode = "disabled"\npatterns = []',
        '[alignment.protected_scope]\nmode = "enforce"\npatterns = ["src/security/**"]',
    )

    cfg = load_config(tmp_path)

    assert cfg.alignment_enabled is True
    assert cfg.alignment_pause_on_open_questions is False
    assert cfg.alignment_risk_threshold == "high"
    assert cfg.alignment_allow_recommended_responses is False
    assert cfg.alignment_protected_scope.patterns == ("src/security/**",)


def test_documentation_config_reads_roots_and_template(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Handle test documentation config reads roots and template workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    replace_workflow_toml(
        'roots = [".agentic/knowledge/components"]',
        'roots = ["docs/components", "05_SoftwareDocu"]',
    )
    replace_workflow_toml(
        'component_template = ".agentic/knowledge/components/component_template.md"',
        'component_template = "docs/components/component_template.md"',
    )

    cfg = load_config(tmp_path)

    assert cfg.documentation_roots == ("docs/components", "05_SoftwareDocu")
    assert cfg.component_documentation_template == "docs/components/component_template.md"


def test_documentation_root_is_in_scope(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Handle test documentation root is in scope workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.scope]\nmode = "unrestricted"\nallowed_roots = []',
        '[guardrails.scope]\nmode = "advisory"\n'
        'allowed_roots = [".agentic/knowledge/components"]',
    )
    graph = Graph(
        run_id="RUN-0001",
        stage="implementation",
        intent=Intent(id="I-0001", kind="feature", statement="Add component docs"),
        change_units=[ChangeUnit(id="CU-0001", touched_paths=[".agentic/knowledge/components/New_Component.md"])],
    )

    result = next(
        item
        for item in evaluate(tmp_path, graph, load_config(tmp_path))
        if item.id == "INV-5"
    )

    assert result.holds


def test_unconfigured_path_remains_out_of_scope(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Handle test unconfigured path remains out of scope workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    replace_workflow_toml(
        '[guardrails.scope]\nmode = "unrestricted"\nallowed_roots = []',
        '[guardrails.scope]\nmode = "advisory"\n'
        'allowed_roots = [".agentic/knowledge/components"]',
    )
    graph = Graph(
        run_id="RUN-0001",
        stage="implementation",
        intent=Intent(id="I-0001", kind="feature", statement="Add component docs"),
        change_units=[ChangeUnit(id="CU-0001", touched_paths=["notes/New_Component.md"])],
    )

    result = next(
        item
        for item in evaluate(tmp_path, graph, load_config(tmp_path))
        if item.id == "INV-5"
    )

    assert not result.holds
    assert "notes/New_Component.md" in result.message


def test_template_includes_component_documentation_assets() -> None:
    """
    @brief      Handle test template includes component documentation assets workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_root = PACKAGE_ROOT / "template"

    assert (template_root / ".agentic" / "knowledge" / "components" / "component_template.md").exists()
    assert (template_root / ".agentic" / "knowledge" / "components" / "index.md").exists()
    assert not (template_root / "05_SoftwareDocu").exists()
    assert "[documentation]" in (template_root / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    assert "Component Documentation Contract" in (template_root / "AGENTS.md").read_text(encoding="utf-8")
    assert load_config(template_root).interface.stage_form_retention == "latest"


def test_template_declares_alignment_workflow_contract() -> None:
    """
    @brief      Verify template docs and skills declare intent-alignment behavior.
    @return     None.
    @exception  None
    """
    template_root = PACKAGE_ROOT / "template"

    workflow_toml = (template_root / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    agents_md = (template_root / "AGENTS.md").read_text(encoding="utf-8")
    development = (template_root / ".agentic" / "skills" / "agentic-development" / "SKILL.md").read_text(encoding="utf-8")
    adoption = (template_root / ".agentic" / "skills" / "agentic-adoption" / "SKILL.md").read_text(encoding="utf-8")

    assert "[alignment]" in workflow_toml
    assert "risk_threshold = \"medium\"" in workflow_toml
    assert "`alignment`" in agents_md
    assert "requirement, design, check" in development
    assert "<workflow> stage apply" in development
    assert "<workflow> stage close" in adoption


def test_template_fresh_session_guidance_matches_current_form_contract() -> None:
    """@brief Keep copied restart guidance within implemented CLI behavior."""
    template_root = PACKAGE_ROOT / "template"
    agents = (template_root / "AGENTS.md").read_text(encoding="utf-8")
    references = (
        template_root
        / ".agentic"
        / "skills"
        / "agentic-development"
        / "reference"
    )
    alignment = (references / "alignment.md").read_text(encoding="utf-8")
    design = (references / "design.md").read_text(encoding="utf-8")
    applied_graph = Graph(
        run_id="RUN-0001",
        stage="intake",
        intent=Intent(id="I-0001", kind="feature", statement="Resume safely"),
        stage_records={
            "intake": StageRecord(
                stage="intake",
                revision=1,
                status="applied",
                retention="latest",
                check_execution="external",
            )
        },
    )
    applied_check_graph = Graph(
        run_id="RUN-0002",
        stage="check",
        intent=Intent(id="I-0002", kind="feature", statement="Resume evidence"),
        checks=[Check(id="CHK-0001", level="unit", cites_spec=[])],
        stage_records={
            "check": StageRecord(
                stage="check",
                revision=1,
                status="applied",
                retention="latest",
                check_execution="external",
            )
        },
    )
    applied_validation_graph = Graph(
        run_id="RUN-0003",
        stage="validation",
        intent=Intent(id="I-0003", kind="feature", statement="Resume verification"),
        stage_records={
            "validation": StageRecord(
                stage="validation",
                revision=1,
                status="applied",
                retention="latest",
                check_execution="external",
                payload={},
            )
        },
    )

    assert next_command(applied_graph) == "aegis stage close"
    assert next_command(applied_check_graph) == "aegis check prepare"
    assert next_command(applied_validation_graph) == "aegis verify run"
    assert "bootstrap sequence:" in agents
    assert "<workflow> run context --json" in agents
    assert "named in required_reads" in agents
    assert "Do not read `graph.json` or `journal.jsonl`" in agents
    assert "needs three commands" not in agents
    assert 'its "Done when" list as comments' not in agents
    assert "everything a stage needs is in the two forms above" not in agents
    assert "[alignment] enabled = false" not in alignment
    assert "The quick path bypasses this stage by profile" in alignment
    assert "Beyond that" not in design
    assert "A full run never skips design" in design
    for stage in _DEVELOPMENT_STAGE_REFERENCES:
        reference = (references / f"{stage}.md").read_text(encoding="utf-8")
        assert "**Resume rule:**" in reference
        assert "reports it as `next`" in reference
        assert "Otherwise do not prepare a new revision" in reference


def test_template_adapters_route_fresh_sessions_through_bounded_context() -> None:
    """@brief Requirement AEGIS-WP2-CTX keeps every adapter on one bootstrap."""
    template_root = PACKAGE_ROOT / "template"
    adapters = (
        template_root / ".codex" / "README.md",
        template_root / ".claude" / "README.md",
        template_root / ".pi" / "README.md",
        template_root / ".opencode" / "README.md",
        template_root / ".qwen" / "README.md",
    )
    routers = (
        template_root / ".agentic" / "skills" / "agentic-development" / "SKILL.md",
        template_root / ".agentic" / "skills" / "agentic-adoption" / "SKILL.md",
        template_root / ".agentic" / "skills" / "agentic-delivery" / "SKILL.md",
    )

    for path in (*adapters, *routers):
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "run context --json" in text, path
        assert "stage prepare" in text, path
        assert "required_reads" in text, path
    for path in adapters:
        assert "read graph.json" not in path.read_text(encoding="utf-8"), path


def test_adapter_entry_points_delegate_to_payload_owned_contracts() -> None:
    """@brief AEGIS-WP7 keeps every mapped host route thin and bounded."""
    template_root = PACKAGE_ROOT / "template"
    adapter_contract = (
        template_root / ".agentic" / "documents" / "ADAPTER_CONFORMANCE.md"
    ).read_text(encoding="utf-8")
    deep_contract = (
        PACKAGE_ROOT.parents[1]
        / "06_SoftwareDocu"
        / "06_AEGIS_Adapter_And_Context_Conformance.md"
    ).read_text(encoding="utf-8")
    skill_names = (
        "agentic-adoption",
        "agentic-development",
        "agentic-delivery",
        "regression-traceability",
        "documentation-audit",
        "python-codestyle-audit",
        "write-component-documentation",
    )
    fresh_entry_points = (
        template_root / "AGENTS.md",
        template_root / ".codex" / "README.md",
        template_root / "CLAUDE.md",
        template_root / ".claude" / "README.md",
        template_root / ".pi" / "README.md",
        template_root / ".opencode" / "README.md",
        template_root / ".opencode" / "agents" / "aegis.md",
        template_root / "QWEN.md",
        template_root / ".qwen" / "README.md",
    )
    mapped_paths = (
        "AGENTS.md",
        ".agentic/tools/run.ps1",
        ".agentic/tools/run.sh",
        ".codex/README.md",
        ".codex/config.toml",
        ".codex/hooks.json",
        "CLAUDE.md",
        ".claude/README.md",
        ".claude/settings.json",
        ".pi/README.md",
        ".pi/package.json",
        ".pi/settings.json",
        ".pi/extensions/agentic-guard/",
        "opencode.json",
        ".opencode/README.md",
        ".opencode/agents/aegis.md",
        ".opencode/commands/",
        ".opencode/plugins/",
        "QWEN.md",
        ".qwen/README.md",
        ".qwen/settings.json",
        ".qwen/commands/",
    )

    for host in ("Codex", "Claude Code", "Pi", "OpenCode", "Qwen Code"):
        assert host in adapter_contract
    for path in mapped_paths:
        assert path in adapter_contract
    for text in (adapter_contract, deep_contract):
        normalized = " ".join(text.split())
        assert "run context --json" in normalized
        assert "stage prepare only when named" in normalized
        assert "graph.json" in normalized
        assert "journal.jsonl" in normalized
        assert "nothing-ran" in normalized
        assert "verify impact --run" in normalized
        assert "config show" in normalized
        assert "not" in normalized and "fresh-session" in normalized

    for path in fresh_entry_points:
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for token in ("AGENTS.md", "run context --json", "stage prepare", "required_reads"):
            assert token in normalized, path
        assert normalized.index("AGENTS.md") < normalized.index("run context --json"), path
        assert normalized.index("run context --json") < normalized.index("required_reads"), path
        assert "reference/" not in text, path
        for internal_name in ("graph.json", "journal.jsonl"):
            for match in re.finditer(re.escape(internal_name), text):
                guidance = text[max(0, match.start() - 100):match.end()].lower()
                assert "do not" in guidance or "outside" in guidance, path

    agents = (template_root / "AGENTS.md").read_text(encoding="utf-8")
    normalized_agents = " ".join(agents.split())
    assert "config show --json` only for explicit policy diagnosis" in normalized_agents
    assert "must not be added to the bounded context pack" in normalized_agents

    for host in (".codex", ".claude", ".opencode", ".qwen"):
        for name in skill_names:
            path = template_root / host / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            assert f".agentic/skills/{name}/SKILL.md" in text, path
            assert "reference/" not in text, path
            assert "graph.json" not in text, path
            assert "journal.jsonl" not in text, path
            assert "config validate --json" not in text, path
            assert "config show --json" not in text, path

        for name in ("agentic-adoption", "agentic-development", "agentic-delivery"):
            path = template_root / host / "skills" / name / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            assert "defines no stage procedure" in text, path
            assert "run context --json" in text, path
            assert "stage prepare" in text, path
            assert "required_reads" in text, path
            assert "config validate --json" not in text, path

        for name in (
            "regression-traceability",
            "documentation-audit",
            "python-codestyle-audit",
            "write-component-documentation",
        ):
            path = template_root / host / "skills" / name / "SKILL.md"
            assert "adds no bootstrap, recovery, or policy procedure" in path.read_text(encoding="utf-8"), path

    pi_manifest = (template_root / ".pi" / "package.json").read_text(encoding="utf-8")
    assert '"../.agentic/skills"' in pi_manifest

    for path in (
        template_root / ".opencode" / "agents" / "aegis.md",
        *(template_root / ".opencode" / "commands").glob("*.md"),
        *(template_root / ".qwen" / "commands").glob("*.md"),
    ):
        text = path.read_text(encoding="utf-8")
        assert "reference/" not in text, path

    assert (template_root / ".codex" / "config.toml").is_file()
    assert (template_root / ".codex" / "hooks.json").is_file()
    assert (template_root / ".claude" / "settings.json").is_file()
    assert (template_root / "opencode.json").is_file()
    assert (template_root / ".opencode" / "plugins" / "agentic-guard.mjs").is_file()
    assert (template_root / ".qwen" / "settings.json").is_file()


def test_maintained_documentation_names_latest_as_retention_default() -> None:
    """@brief Keep maintained setup and metadata guides on the shipped default."""
    repository_root = PACKAGE_ROOT.parents[1]
    documents = (
        PACKAGE_ROOT / "README.md",
        PACKAGE_ROOT
        / "template"
        / ".agentic"
        / "documents"
        / "How_To_Start_A_New_Project.md",
        PACKAGE_ROOT
        / "template"
        / ".agentic"
        / "documents"
        / "WORKFLOW_CONFIGURATION.md",
        PACKAGE_ROOT
        / "template"
        / ".agentic"
        / "documents"
        / "UPGRADING.md",
        repository_root / "06_SoftwareDocu" / "04_Configuring_AEGIS.md",
        repository_root / "06_SoftwareDocu" / "05_Reading_AEGIS_Metadata.md",
        repository_root / "05_Software" / "waegis" / "README.md",
    )

    for path in documents:
        text = path.read_text(encoding="utf-8")
        assert 'stage_form_retention = "latest"' in text, path
        assert "`discard` (the default)" not in text, path


def test_repository_validation_guidance_preserves_template_hygiene() -> None:
    """@brief Keep repository CLI checks from writing copied-template bytecode."""
    repository_root = PACKAGE_ROOT.parents[1]
    readme = (repository_root / "README.md").read_text(encoding="utf-8")

    assert "uv run --group dev python -B -m aegis --help" in readme
    assert "uv run --group dev python -m aegis --help" not in readme
    assert "uv run --group dev aegis --help" not in readme


def test_installable_template_includes_bundled_skills() -> None:
    """
    @brief      Handle test installable template includes bundled skills workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_skills = PACKAGE_ROOT / "template" / ".codex" / "skills"
    expected = {
        "agentic-adoption",
        "agentic-development",
        "agentic-delivery",
        "regression-traceability",
        "write-component-documentation",
        "documentation-audit",
        "python-codestyle-audit",
    }

    assert expected <= {path.name for path in template_skills.iterdir() if path.is_dir()}
    assert not (template_skills / "codestyle-audit").exists()

    for name in expected:
        text = (template_skills / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}" in text
        assert f".agentic/skills/{name}/SKILL.md" in text
        assert "project-specific application name" not in text


def test_installable_template_includes_neutral_skill_bodies() -> None:
    """
    @brief      Verify the shared skill procedures live in `.agentic/skills`.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    skills_root = PACKAGE_ROOT / "template" / ".agentic" / "skills"
    expected = {
        "agentic-adoption",
        "agentic-development",
        "agentic-delivery",
        "regression-traceability",
        "write-component-documentation",
        "documentation-audit",
        "python-codestyle-audit",
    }

    assert expected <= {path.name for path in skills_root.iterdir() if path.is_dir()}

    for name in expected:
        text = (skills_root / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}" in text
        assert "Copyright (c) 2026 DDP Engineering" in text
        assert "project-specific application name" not in text

    # The neutral source carries the full procedures, now in per-stage reference
    # modules dispatched from the router, not just adapter pointers.
    development = (skills_root / "agentic-development" / "SKILL.md").read_text(encoding="utf-8")
    assert "Stage Lifecycle" in development
    assert "reference/requirement.md" in development
    assert "reference/design.md" in development
    reference_dir = skills_root / "agentic-development" / "reference"
    for stage in _DEVELOPMENT_STAGE_REFERENCES:
        assert (reference_dir / f"{stage}.md").is_file()
    requirement_module = (reference_dir / "requirement.md").read_text(encoding="utf-8")
    assert "one independently observable contract" in requirement_module
    assert "stage apply" in requirement_module
    assert "companion Markdown" in requirement_module
    documentation = (skills_root / "documentation-audit" / "SKILL.md").read_text(encoding="utf-8")
    assert "Manual review checklist" in documentation
    adoption = (skills_root / "agentic-adoption" / "SKILL.md").read_text(encoding="utf-8")
    assert "must not change runtime product behavior" in adoption
    assert "repo-discovery" in adoption
    assert "component-map" in adoption
    assert "component-adoption" in adoption
    assert "local scope before change" in adoption
    adoption_reference = skills_root / "agentic-adoption" / "reference"
    for module in (
        "adoption-intake.md",
        "adoption-alignment.md",
        "repo-discovery.md",
        "component-map.md",
        "component-adoption.md",
        "baseline-review.md",
        "adoption-delivery.md",
    ):
        assert (adoption_reference / module).is_file()


def test_development_stage_references_have_operational_structure() -> None:
    """
    @brief Verify every development-stage reference exposes the same usable structure.
    @return None.
    @exception None
    """
    reference_dir = (
        PACKAGE_ROOT
        / "template"
        / ".agentic"
        / "skills"
        / "agentic-development"
        / "reference"
    )
    required_sections = (
        "**Purpose:**",
        "**Read first:**",
        "**Steps:**",
        "**Outputs:**",
        "**Done when:**",
        "**Skip when:**",
        "## If you are stuck",
    )

    for stage in _DEVELOPMENT_STAGE_REFERENCES:
        text = (reference_dir / f"{stage}.md").read_text(encoding="utf-8")
        assert f"# Stage: {stage.title()}" in text
        assert all(section in text for section in required_sections)

    check = (reference_dir / "check.md").read_text(encoding="utf-8")
    assert "INV-3" in check
    assert "<workflow> check create" in check
    assert "<workflow> check register" in check
    assert "real red/green evidence" in check
    assert "evidence prepare add" not in check


def test_stage_reference_checklists_match_the_canonical_contract() -> None:
    """@brief WP1 keeps all lifecycle-reference checklists in exact parity."""
    skills_root = PACKAGE_ROOT / "template" / ".agentic" / "skills"
    references = {
        **{
            stage: skills_root / "agentic-development" / "reference" / f"{stage}.md"
            for stage in _DEVELOPMENT_STAGE_REFERENCES
        },
        **{
            stage: skills_root / "agentic-adoption" / "reference" / f"{stage}.md"
            for stage in _ADOPTION_STAGE_REFERENCES
        },
        "delivery": skills_root / "agentic-delivery" / "SKILL.md",
    }

    assert set(references) == set(ALL_STAGES)
    assert len(references) == len(ALL_STAGES)
    for stage, path in references.items():
        text = path.read_text(encoding="utf-8")
        assert all(
            section in text
            for section in (
                "**Purpose:**",
                "**Read first:**",
                "**Steps:**",
                "**Outputs:**",
                "**Done when:**",
                "**Skip when:**",
            )
        ), path
        section = text.split("**Done when:**", 1)[1].split("**Skip when:**", 1)[0]
        actual = [
            (" ".join(match.group(2).split()), match.group(1) == "human")
            for match in re.finditer(
                r"^- \[ \] \[(machine|human)\] (.+)$",
                section,
                flags=re.MULTILINE,
            )
        ]
        expected = [
            (" ".join(item.text.split()), item.human)
            for item in STAGE_DONE_WHEN[stage]
        ]

        assert actual == expected, path
        assert path.stat().st_size <= 5 * 1024, path


def test_documented_workflow_commands_match_the_cli_parser() -> None:
    """
    @brief Verify every documented workflow invocation is accepted by the CLI parser.
    @return None.
    @exception None
    """
    reference_dir = (
        PACKAGE_ROOT
        / "template"
        / ".agentic"
        / "skills"
        / "agentic-development"
        / "reference"
    )
    sources = [
        (PACKAGE_ROOT / "template" / "AGENTS.md").read_text(encoding="utf-8"),
        *(
            (reference_dir / f"{stage}.md").read_text(encoding="utf-8")
            for stage in _DEVELOPMENT_STAGE_REFERENCES
        ),
    ]
    commands = {
        match.split("#", 1)[0].strip()
        for text in sources
        for match in re.findall(r"<workflow>\s+([^`\r\n]+)", text)
    }
    required_commands = {
        "config validate --json",
        "config show --json",
        "run start fix --quick",
        "check create",
        "check register",
        "stage show",
        "evidence prepare <add|supersede>",
    }
    assert required_commands <= commands

    parser = _build_parser()
    for command in sorted(commands):
        concrete = (
            command.replace("<feature|fix|change>", "fix")
            .replace("<add|supersede>", "add")
            .replace("[<check-id>...]", "CHK-0001")
            .replace("<check-id>", "CHK-0001")
            .replace("<category>", "functional")
            .replace("<blocker-id>", "INV-1")
            .replace("<human-approved reason>", "approved reason")
            .replace('"<reason>"', '"approved reason"')
        )
        parser.parse_args(_normalize_global_options(shlex.split(concrete)))


def test_copied_template_material_avoids_project_specific_measurements() -> None:
    """
    @brief Verify copied material contains no source-project names or graph-size claims.
    @return None.
    @exception None
    """
    template_root = PACKAGE_ROOT / "template"
    offenders = []

    for path in template_root.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(template_root).parts
        if any(
            part in _DEPENDENCY_DIRS
            or part.endswith(_GENERATED_METADATA_SUFFIX)
            for part in relative_parts
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if (
            "VoiceWeaver" in text
            or "AudioMancer" in text
            or _GRAPH_SIZE_CLAIM.search(text)
        ):
            offenders.append(path.relative_to(template_root).as_posix())

    assert offenders == []


def test_installable_template_includes_claude_skill_wrappers() -> None:
    """
    @brief      Handle test installable template includes claude skill wrappers workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_skills = PACKAGE_ROOT / "template" / ".claude" / "skills"
    expected = {
        "agentic-adoption",
        "agentic-development",
        "agentic-delivery",
        "regression-traceability",
        "write-component-documentation",
        "documentation-audit",
        "python-codestyle-audit",
    }

    assert expected <= {path.name for path in template_skills.iterdir() if path.is_dir()}
    assert not (template_skills / "codestyle-audit").exists()

    for name in expected:
        text = (template_skills / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}" in text
        assert "AGENTS.md" in text
        assert f".agentic/skills/{name}/SKILL.md" in text
        assert "Claude Code invocation" in text
        assert "project-specific application name" not in text


def test_installable_template_includes_opencode_skill_wrappers() -> None:
    """
    @brief      Verify the installable template includes OpenCode skill wrappers.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_skills = PACKAGE_ROOT / "template" / ".opencode" / "skills"
    expected = {
        "agentic-adoption",
        "agentic-development",
        "agentic-delivery",
        "regression-traceability",
        "write-component-documentation",
        "documentation-audit",
        "python-codestyle-audit",
    }

    assert expected <= {path.name for path in template_skills.iterdir() if path.is_dir()}

    for name in expected:
        text = (template_skills / name / "SKILL.md").read_text(encoding="utf-8")
        assert f"name: {name}" in text
        assert "AGENTS.md" in text
        assert f".agentic/skills/{name}/SKILL.md" in text
        assert "OpenCode invocation" in text
        assert "project-specific application name" not in text


def test_template_includes_claude_adapter_assets() -> None:
    """
    @brief      Handle test template includes claude adapter assets workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_root = PACKAGE_ROOT / "template"

    assert (template_root / "CLAUDE.md").exists()
    assert (template_root / ".claude" / "settings.json").exists()
    assert (template_root / ".claude" / "README.md").exists()
    assert (template_root / ".claude" / "agents" / "README.md").exists()
    assert "AGENTS.md" in (template_root / "CLAUDE.md").read_text(encoding="utf-8")


def test_template_hooks_are_standalone_files() -> None:
    """
    @brief      Handle test template hooks are standalone files workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    hooks_root = PACKAGE_ROOT / "template" / ".agentic" / "hooks"
    expected = {
        "guard_write_zone.py",
        "secret_scan.py",
        "post_tool_evidence.py",
        "delivery_preflight.py",
    }

    assert expected <= {path.name for path in hooks_root.iterdir() if path.is_file()}
    for name in expected:
        text = (hooks_root / name).read_text(encoding="utf-8")
        assert "from aegis.hooks" not in text


def test_documentation_audit_defaults_to_changed_component_docs() -> None:
    """
    @brief      Handle test documentation audit defaults to changed component docs workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    skill = (
        PACKAGE_ROOT
        / "template"
        / ".agentic"
        / "skills"
        / "documentation-audit"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "changed implementation files" in skill
    assert "`.agentic/knowledge/components/*.md`" in skill
    assert "only when explicitly requested or when their scope changes" in skill
    update_step = skill.split(
        "Update stale or missing component documentation directly:"
    )[1].split("6.")[0]
    assert "root README or package README files" not in update_step


def test_prompt_cheatsheet_is_not_authoritative_workflow_source() -> None:
    """
    @brief      Handle test prompt cheatsheet is not authoritative workflow source workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    text = (PACKAGE_ROOT / "template" / ".agentic" / "documents" / "PROMPT_CHEATSHEET.md").read_text(encoding="utf-8")

    assert "human operator flyer" in text
    assert "not an agentic delivery contract" in text
    assert "evidence source" in text


def test_template_includes_local_cli_bootstrap() -> None:
    """
    @brief      Handle test template includes local cli bootstrap workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_root = PACKAGE_ROOT / "template"

    assert (template_root / ".agentic" / "cli" / "pyproject.toml").exists()
    assert (template_root / ".agentic" / "cli" / "src" / "aegis" / "cli.py").exists()
    assert (template_root / ".agentic" / "cli" / "src" / "aegis" / "working_tree.py").exists()
    assert (template_root / ".agentic" / "tools" / "run_aegis.py").exists()
    assert (template_root / ".agentic" / "tools" / "run.ps1").exists()
    assert (template_root / ".agentic" / "tools" / "run.sh").exists()
    assert (template_root / ".agentic" / "tools" / "run_hook.mjs").exists()
    assert (template_root / ".agentic" / "tools" / "install.ps1").exists()
    assert (template_root / ".agentic" / "tools" / "install.sh").exists()


def test_template_has_no_generated_python_cache() -> None:
    """
    @brief      Handle test template has no generated python cache workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    repository_root = PACKAGE_ROOT.parents[1]
    result = subprocess.run(
        ["git", "-C", str(repository_root), "ls-files", "--", "05_Software/aegis/template"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    tracked = [Path(line) for line in result.stdout.splitlines() if line]
    assert not any("__pycache__" in path.parts for path in tracked)
    assert not any(path.suffix == ".pyc" for path in tracked)
    assert not any(path.name.endswith(".egg-info") for path in tracked)


def test_template_text_files_have_legal_header() -> None:
    """
    @brief      Handle test template text files have legal header workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    """
    template_root = PACKAGE_ROOT / "template"
    exempt_suffixes = {".json"}
    exempt_names = {".gitkeep", "CHANGELOG.md"}
    missing = []

    for path in template_root.rglob("*"):
        if not path.is_file():
            continue
        # Skip install-on-demand dependencies and generated Python package
        # metadata; neither is shipped template material.
        relative_parts = path.relative_to(template_root).parts
        if any(part in _DEPENDENCY_DIRS or part.endswith(_GENERATED_METADATA_SUFFIX) for part in relative_parts):
            continue
        if path.suffix.lower() in exempt_suffixes or path.name in exempt_names:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "Copyright (c) 2026 DDP Engineering" not in text:
            missing.append(path.relative_to(template_root).as_posix())

    assert missing == []


def test_agent_instructions_keep_configuration_diagnosis_outside_fresh_recovery() -> None:
    """
    @brief      Verify fresh recovery does not inject broad configuration output.
    @return     None.
    @exception  None
    """
    template_root = PACKAGE_ROOT / "template"
    agents = (template_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "<workflow> config validate --json" in agents
    assert "<workflow> config show --json" in agents
    normalized_agents = " ".join(agents.split())
    assert "only for explicit policy diagnosis" in normalized_agents
    assert "not a fresh-session bootstrap input" in normalized_agents
    assert "--run <run-id>" in agents

    for name in ("agentic-adoption", "agentic-development"):
        canonical = (template_root / ".agentic" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        assert "after a configuration repair" in canonical
        assert "fresh-session bootstrap step" in canonical

    for adapter in (".codex", ".claude", ".opencode", ".qwen"):
        for name in (
            "agentic-adoption",
            "agentic-development",
            "agentic-delivery",
            "documentation-audit",
            "python-codestyle-audit",
            "regression-traceability",
            "write-component-documentation",
        ):
            wrapper = (
                template_root / adapter / "skills" / name / "SKILL.md"
            ).read_text(encoding="utf-8")
            assert "AGENTS.md" in wrapper
            assert f".agentic/skills/{name}/SKILL.md" in wrapper
            assert "config validate --json" not in wrapper
            assert "config show --json" not in wrapper


def test_operator_documents_describe_only_current_workflow_contracts() -> None:
    """
    @brief      Verify maintained operator documents expose current AEGIS/WAEGIS contracts.
    @return     None.
    @exception  None
    """
    documents_root = PACKAGE_ROOT / "template" / ".agentic" / "documents"
    maintained = {
        "WORKFLOW_CONFIGURATION.md",
        "POLICY_CONFIGURATION.md",
        "How_To_Start_A_New_Project.md",
        "CLI_API_REFERENCE.md",
        "PROMPT_CHEATSHEET.md",
        "REPOWISE_INTEGRATION.md",
        "UPGRADING.md",
    }

    combined = "\n".join(
        (documents_root / name).read_text(encoding="utf-8")
        for name in maintained
    )
    assert "schema_version = 3" in combined
    assert "<workflow> config validate" in combined
    assert "<workflow> config show --json" in combined
    assert ".agentic/.workspace/state/current_run" in combined
    assert "AEGIS generates" in combined
    assert "schema_version = 1" in combined
    assert "RepoWise 0.37.0" in combined
    assert "requirements/registry" not in combined
    assert "write_zones" not in combined
    assert "WAEGIS 3" in combined
    assert "WAEGIS 3 does not manage RepoWise" in combined
    assert "waegis repowise" not in combined.lower()
    assert ">=2.0.0,<3.0.0" not in combined


def test_maintained_aegis_documentation_uses_current_release_branding() -> None:
    """
    @brief Verify maintained AEGIS entry points describe the 3.0 payload.
    @return None.
    @exception None
    """
    repository_root = PACKAGE_ROOT.parents[1]
    root_readme = (repository_root / "README.md").read_text(encoding="utf-8")
    package_readme = (PACKAGE_ROOT / "README.md").read_text(encoding="utf-8")
    template_agents = (PACKAGE_ROOT / "template" / "AGENTS.md").read_text(
        encoding="utf-8"
    )

    assert "AEGIS 3.0" in root_readme
    assert package_readme.startswith(
        "<!-- Copyright (c) 2026 DDP Engineering. "
        "SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->"
        "\n\n# AEGIS 3.0"
    )
    assert "This repository uses AEGIS 3.0" in template_agents
    assert "AEGIS 2.1" not in root_readme
    assert "AEGIS 2.1" not in package_readme
    assert "AEGIS 2.1" not in template_agents
    assert ">=2.0.0,<3.0.0" not in package_readme


def test_documentation_catalog_marks_current_and_historical_material() -> None:
    """
    @brief Verify the software catalog separates current and historical guides.
    @return None.
    @exception None
    """
    repository_root = PACKAGE_ROOT.parents[1]
    software_root = repository_root / "06_SoftwareDocu"
    catalog = (software_root / "README.md").read_text(encoding="utf-8")
    historical = (
        software_root / "AEGIS_2_1_HumanExplanations" / "README.md"
    ).read_text(encoding="utf-8")
    normalized_historical = " ".join(historical.replace(">", " ").split())
    removed_entries = {
        "AEGIS_PERSISTENCE_AND_CONCURRENCY.md",
        "SELF_GOVERNED_RELEASE.md",
        "WAEGIS_RELEASE_REPRODUCIBILITY.md",
        "WAEGIS_REPOWISE_WINDOWS_EXECUTION.md",
        "WAEGIS_TRANSACTION_RECOVERY.md",
    }

    assert "Operator path" in catalog
    assert "Historical Material" in catalog
    assert "Historical archive" in historical
    assert "not the current AEGIS 3.0" in normalized_historical
    assert all(name not in catalog for name in removed_entries)

# END OF FILE
