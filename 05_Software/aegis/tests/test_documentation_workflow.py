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
@author Eng. Dan Dumitru Pasare
@date 2026-06-20
@version 0.7.0
"""

# IMPORTS

from __future__ import annotations

from collections.abc import Callable
import subprocess
from pathlib import Path

from aegis.config import load_config
from aegis.invariants import evaluate
from aegis.models import ChangeUnit, Graph, Intent

# CONSTANTS

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# @brief Directory names that hold install-on-demand, gitignored third-party
#        artifacts (the .pi/ vitest toolchain). Template-hygiene walks skip these
#        because they are not part of the shipped template deliverable.
_DEPENDENCY_DIRS = {"node_modules", ".vitest", ".git", ".opencode-cache"}

# @brief Generated Python distribution-metadata directory suffix excluded from
#        template-hygiene walks because editable package builds create it locally.
_GENERATED_METADATA_SUFFIX = ".egg-info"


# TESTS


def test_default_documentation_config(tmp_path: Path) -> None:
    """
    @brief      Handle test default documentation config workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.3.0
    """
    cfg = load_config(tmp_path)

    assert cfg.documentation_roots == (".agentic/knowledge/components",)
    assert cfg.component_documentation_template == ".agentic/knowledge/components/component_template.md"
    assert cfg.alignment_enabled is True
    assert cfg.alignment_pause_on_open_questions is True
    assert cfg.alignment_risk_threshold == "medium"
    assert cfg.alignment_allow_recommended_responses is True
    assert cfg.alignment_protected_scope_patterns == ()


def test_alignment_config_reads_policy(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Verify intent-alignment policy configuration is loaded.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.2.0
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
    assert cfg.alignment_protected_scope_patterns == ("src/security/**",)


def test_documentation_config_reads_roots_and_template(
    tmp_path: Path,
    replace_workflow_toml: Callable[[str, str], Path],
) -> None:
    """
    @brief      Handle test documentation config reads roots and template workflow behavior.
    @param[in]  tmp_path Input value used by the workflow helper.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.2
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.3.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.4.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.2
    """
    template_root = PACKAGE_ROOT / "template"

    assert (template_root / ".agentic" / "knowledge" / "components" / "component_template.md").exists()
    assert (template_root / ".agentic" / "knowledge" / "components" / "index.md").exists()
    assert not (template_root / "05_SoftwareDocu").exists()
    assert "[documentation]" in (template_root / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    assert "Component Documentation Contract" in (template_root / "AGENTS.md").read_text(encoding="utf-8")


def test_template_declares_alignment_workflow_contract() -> None:
    """
    @brief      Verify template docs and skills declare intent-alignment behavior.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-03
    @version    0.1.0
    """
    template_root = PACKAGE_ROOT / "template"

    workflow_toml = (template_root / ".agentic" / "workflow.toml").read_text(encoding="utf-8")
    agents_md = (template_root / "AGENTS.md").read_text(encoding="utf-8")
    development = (template_root / ".agentic" / "skills" / "agentic-development" / "SKILL.md").read_text(encoding="utf-8")
    adoption = (template_root / ".agentic" / "skills" / "agentic-adoption" / "SKILL.md").read_text(encoding="utf-8")

    assert "[alignment]" in workflow_toml
    assert "risk_threshold = \"medium\"" in workflow_toml
    assert "`alignment`" in agents_md
    assert "Before any `add-spec` call" in development
    assert "Before moving from `adoption-alignment` to discovery" in adoption


def test_installable_template_includes_bundled_skills() -> None:
    """
    @brief      Handle test installable template includes bundled skills workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.1
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

    # The neutral source carries the full procedures, not just adapter pointers.
    development = (skills_root / "agentic-development" / "SKILL.md").read_text(encoding="utf-8")
    assert "Stage Procedure" in development
    documentation = (skills_root / "documentation-audit" / "SKILL.md").read_text(encoding="utf-8")
    assert "Manual review checklist" in documentation
    adoption = (skills_root / "agentic-adoption" / "SKILL.md").read_text(encoding="utf-8")
    assert "No application behavior changes during adoption" in adoption
    assert "repo-discovery" in adoption
    assert "component-map" in adoption
    assert "component-adoption" in adoption
    assert "local scope before change" in adoption


def test_installable_template_includes_claude_skill_wrappers() -> None:
    """
    @brief      Handle test installable template includes claude skill wrappers workflow behavior.
    @return     Result produced by the workflow helper.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.1
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-25
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.1
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.1
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.1.0
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
    @author     Eng. Dan Dumitru Pasare
    @date       2026-06-20
    @version    0.2.0
    """
    template_root = PACKAGE_ROOT / "template"
    exempt_suffixes = {".json"}
    exempt_names = {".gitkeep"}
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


def test_agent_instructions_require_effective_configuration_bootstrap() -> None:
    """
    @brief      Verify canonical skills and adapter wrappers require WP6 bootstrap.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.2
    """
    template_root = PACKAGE_ROOT / "template"
    skill_names = {
        "agentic-adoption",
        "agentic-development",
        "agentic-delivery",
        "documentation-audit",
        "python-codestyle-audit",
        "regression-traceability",
        "write-component-documentation",
    }

    for name in skill_names:
        canonical = (
            template_root / ".agentic" / "skills" / name / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert "<workflow> config validate" in canonical
        assert "<workflow> config show --effective" in canonical
        assert "selected" in canonical.lower()
        assert "run" in canonical.lower()
        assert "external" in canonical.lower()

        for adapter in (".codex", ".claude", ".opencode", ".qwen"):
            wrapper = (
                template_root / adapter / "skills" / name / "SKILL.md"
            ).read_text(encoding="utf-8")
            assert "Before invoking the shared procedure" in wrapper
            assert "<workflow> config validate" in wrapper
            assert "<workflow> config show --effective" in wrapper


def test_operator_documents_describe_only_current_workflow_contracts() -> None:
    """
    @brief      Verify maintained operator documents expose the schema-2 contract.
    @return     None.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-22
    @version    0.1.1
    """
    documents_root = PACKAGE_ROOT / "template" / ".agentic" / "documents"
    maintained = {
        "WORKFLOW_CONFIGURATION.md",
        "POLICY_CONFIGURATION.md",
        "How_To_Start_A_New_Project.md",
        "CLI_API_REFERENCE.md",
        "PROMPT_CHEATSHEET.md",
    }

    combined = "\n".join(
        (documents_root / name).read_text(encoding="utf-8")
        for name in maintained
    )
    assert "schema_version = 2" in combined
    assert "<workflow> config validate" in combined
    assert "<workflow> config show --effective" in combined
    assert ".agentic/.workspace/state/current_run" in combined
    assert "UUIDv4" in combined
    assert "requirements/registry" not in combined
    assert "write_zones" not in combined


# END OF FILE
