#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_repo_workflow_toml.py
@brief workflow.toml generator tests (T4.1): plan §7 invariants, language
       presets, targeted-substitution byte fidelity, the never-save-invalid
       guard, empty-gate warnings, and FieldSpec composition.
@details Strictly offline. The primary fixtures use the REAL
         ``05_Software/aegis/template/.agentic/workflow.toml`` text (read-only)
         so the generator is proven against what it will actually rewrite;
         small synthetic bases cover the edge cases (multi-line arrays,
         missing owned keys, invalid TOML).
@author Eng. Dan Dumitru Pasare
@date 2026-07-13
@version 0.1.0
"""

# IMPORTS

from __future__ import annotations

import io
import tomllib
from pathlib import Path

import pytest

from waegis.io.prompts import ConsoleAsker, ScriptedAnswerError, ScriptedAsker, guard_answers
from waegis.repo import workflow_toml
from waegis.repo.workflow_toml import (
    COMPONENT_DOCS_ZONE,
    LANGUAGE_PRESETS,
    SUPPORTED_LANGUAGES,
    WORKFLOW_FIELD_SPECS,
    BaseFileMismatchError,
    GateWarning,
    InvariantViolationError,
    LanguagePresetError,
    generate_workflow_toml,
    normalize_gate_commands,
    normalize_roots,
    resolve_language_preset,
    verify_workflow_invariants,
)

# CONSTANTS

# @brief The real template workflow.toml this generator rewrites (read-only).
REAL_BASE_PATH = (
    Path(__file__).resolve().parents[2] / "aegis" / "template" / ".agentic" / "workflow.toml"
)

# @brief Default answers reused by tests that only vary one dimension.
DEFAULT_ANSWERS: dict[str, object] = {
    "source_roots": ["src"],
    "test_roots": ["tests"],
    "language": "python",
    "gate_test_cmds": [["uv", "run", "pytest", "-q"]],
    "gate_lint_cmds": [["ruff", "check", "."]],
    "alignment_enabled": True,
}

# @brief Synthetic minimal base: every generator-owned key present, one
#        untouched section, one owned key as a MULTI-LINE array (exercises the
#        bracket-balance value-span consumption) with a bracket inside a string.
SYNTHETIC_BASE = """# synthetic base for edge cases
[source]
roots = [
  "old",
  "with [bracket] inside",
]

[tests]
roots = ["oldtests"]

[traceability]
language = "python"
source_extensions = [".py"]
coverable_roots = ["old"]
test_file_patterns = ["test_*.py"]

[gates]
test = []
lint = []

[alignment]
enabled = true

[untouched]
# a comment that must survive
value = "keep me"

[write_zones]
check = ["oldtests/**"]
implementation = ["old/**", ".agentic/knowledge/components/**"]
component-adoption = [".agentic/**", "oldtests/**"]
"""

# LOCAL HELPERS


@pytest.fixture(scope="module")
def real_base_text() -> str:
    """
    @brief      Load the real template workflow.toml text once per module.
    @return     The base file text.
    @exception  OSError If the template file cannot be read.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    return REAL_BASE_PATH.read_text(encoding="utf-8")


def _generate(base_text: str, **overrides: object) -> workflow_toml.GeneratedWorkflow:
    """
    @brief      Generate with the default answers, selectively overridden.
    @param[in]  base_text Base TOML text.
    @param[in]  overrides Keyword overrides of :data:`DEFAULT_ANSWERS`.
    @return     The :class:`GeneratedWorkflow` result.
    @exception  WorkflowTomlError Propagated from the generator.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    answers = {**DEFAULT_ANSWERS, **overrides}
    return generate_workflow_toml(base_text, **answers)  # type: ignore[arg-type]


def _section_slice(text: str, section: str) -> str:
    """
    @brief      Extract one ``[section]``'s exact text slice (header through
                the line before the next section header or end of text).
    @param[in]  text Full TOML text.
    @param[in]  section Section name without brackets.
    @return     The exact substring of that section.
    @exception  AssertionError If the section header is not found.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    header = f"[{section}]"
    start = text.find(f"\n{header}")
    assert start != -1, f"section {header} not found"
    start += 1
    end = text.find("\n[", start)
    return text[start:] if end == -1 else text[start:end]


def _assert_invariants(document: dict, source_roots: list[str], test_roots: list[str]) -> None:
    """
    @brief      Assert plan §7 invariants 1–3 directly on a parsed document,
                independently of the module's own verifier.
    @param[in]  document Parsed TOML document.
    @param[in]  source_roots Expected implementation roots.
    @param[in]  test_roots Expected test roots.
    @return     None
    @exception  AssertionError If any invariant does not hold.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    implementation = document["write_zones"]["implementation"]
    coverable = document["traceability"]["coverable_roots"]
    check = document["write_zones"]["check"]
    component_adoption = document["write_zones"]["component-adoption"]
    for root in source_roots:
        assert f"{root}/**" in implementation
        assert root in coverable
    for root in test_roots:
        assert f"{root}/**" in check
        assert f"{root}/**" in component_adoption
    assert ".agentic/knowledge/components/**" in implementation


# GOLDEN TESTS PER LANGUAGE PRESET (real base file)


def test_golden_python_from_real_base(real_base_text: str) -> None:
    """
    @brief      Python preset over the real base: every answered key lands and
                all §7 invariants hold in the re-parsed output.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError On any mismatch.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = _generate(real_base_text)
    document = tomllib.loads(result.text)
    assert document["source"]["roots"] == ["src"]
    assert document["tests"]["roots"] == ["tests"]
    assert document["traceability"]["language"] == "python"
    assert document["traceability"]["source_extensions"] == [".py"]
    assert document["traceability"]["coverable_roots"] == ["src"]
    assert document["traceability"]["test_file_patterns"] == ["test_*.py", "*_test.py"]
    assert document["gates"]["test"] == [["uv", "run", "pytest", "-q"]]
    assert document["gates"]["lint"] == [["ruff", "check", "."]]
    assert document["alignment"]["enabled"] is True
    assert document["write_zones"]["check"] == ["tests/**"]
    assert document["write_zones"]["implementation"] == ["src/**", COMPONENT_DOCS_ZONE]
    assert document["write_zones"]["component-adoption"] == [".agentic/**", "tests/**"]
    _assert_invariants(document, ["src"], ["tests"])
    assert result.warnings == ()


def test_golden_typescript_from_real_base(real_base_text: str) -> None:
    """
    @brief      TypeScript preset over the real base: preset-specific
                extensions/patterns land and invariants hold.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError On any mismatch.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = _generate(real_base_text, language="typescript")
    document = tomllib.loads(result.text)
    assert document["traceability"]["language"] == "typescript"
    assert document["traceability"]["source_extensions"] == [".ts", ".tsx"]
    assert document["traceability"]["test_file_patterns"] == [
        "*.test.ts",
        "*.spec.ts",
        "*.test.tsx",
        "*.spec.tsx",
    ]
    _assert_invariants(document, ["src"], ["tests"])


def test_golden_go_from_real_base(real_base_text: str) -> None:
    """
    @brief      Go preset over the real base: preset-specific values land and
                invariants hold.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError On any mismatch.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = _generate(real_base_text, language="go", source_roots=["cmd", "internal"])
    document = tomllib.loads(result.text)
    assert document["traceability"]["language"] == "go"
    assert document["traceability"]["source_extensions"] == [".go"]
    assert document["traceability"]["test_file_patterns"] == ["*_test.go"]
    _assert_invariants(document, ["cmd", "internal"], ["tests"])


def test_preset_table_actually_varies_output(real_base_text: str) -> None:
    """
    @brief      Two different presets produce different traceability values —
                the preset table is not decorative.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If two presets emit identical traceability.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    ts = tomllib.loads(_generate(real_base_text, language="typescript").text)["traceability"]
    go = tomllib.loads(_generate(real_base_text, language="go").text)["traceability"]
    assert ts["source_extensions"] != go["source_extensions"]
    assert ts["test_file_patterns"] != go["test_file_patterns"]
    assert ts["language"] != go["language"]


def test_every_preset_generates_and_satisfies_invariants(real_base_text: str) -> None:
    """
    @brief      Every entry of the preset table generates successfully from
                the real base and satisfies invariants 1–3 (invariant 6:
                presets ship for all required languages).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If a preset is missing or generation fails.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    required = {"python", "typescript", "javascript", "java", "csharp", "go", "rust", "cpp"}
    assert required <= set(LANGUAGE_PRESETS)
    assert "other" in SUPPORTED_LANGUAGES and "other" not in LANGUAGE_PRESETS
    for language, preset in LANGUAGE_PRESETS.items():
        document = tomllib.loads(_generate(real_base_text, language=language).text)
        assert document["traceability"]["language"] == preset.language
        assert document["traceability"]["source_extensions"] == list(preset.source_extensions)
        assert document["traceability"]["test_file_patterns"] == list(preset.test_file_patterns)
        _assert_invariants(document, ["src"], ["tests"])


# PROPERTY-STYLE ROOT-COMBINATION TESTS


@pytest.mark.parametrize(
    ("source_roots", "test_roots"),
    [
        (["src"], ["tests"]),
        (["src", "app", "lib"], ["tests", "test"]),
        (["core", "modules", "plugins"], ["spec"]),
        (["src/main/java"], ["src/test/java"]),
        (["a", "b", "c", "d", "e"], ["t1", "t2", "t3"]),
    ],
)
def test_invariants_hold_for_arbitrary_root_sets(
    real_base_text: str, source_roots: list[str], test_roots: list[str]
) -> None:
    """
    @brief      Invariants 1–3 hold in the parsed output for arbitrary
                source/test root combinations, including multi-root and
                nested-path roots (the plan §7 property).
    @param[in]  real_base_text The real template workflow.toml text.
    @param[in]  source_roots Roots to configure.
    @param[in]  test_roots Test roots to configure.
    @return     None
    @exception  AssertionError If any invariant does not hold.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = _generate(real_base_text, source_roots=source_roots, test_roots=test_roots)
    document = tomllib.loads(result.text)
    _assert_invariants(document, source_roots, test_roots)
    assert document["source"]["roots"] == source_roots
    assert document["tests"]["roots"] == test_roots
    assert document["traceability"]["coverable_roots"] == source_roots


# INVARIANT 4: UNTOUCHED CONTENT SURVIVES BYTE-FOR-BYTE


def test_untouched_sections_survive_byte_for_byte(real_base_text: str) -> None:
    """
    @brief      Sections no answer touches ([secrets], [components],
                [requirements], [adoption]) survive as exact text slices —
                catching reformatting or comment loss, not just parsed
                equivalence (invariant 4).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If any untouched slice changed.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    generated = _generate(real_base_text).text
    for section in ("secrets", "components", "requirements", "adoption", "working_tree"):
        assert _section_slice(real_base_text, section) == _section_slice(generated, section)


def test_comments_and_license_banner_are_preserved(real_base_text: str) -> None:
    """
    @brief      The license banner and the comment lines of touched sections
                are preserved (comment-preserving strategy, plan §7).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If a comment line was lost.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    generated = _generate(real_base_text).text
    base_comment_lines = [line for line in real_base_text.splitlines() if line.lstrip().startswith("#")]
    for comment in base_comment_lines:
        assert comment in generated, f"comment lost: {comment!r}"


def test_only_owned_lines_differ_from_base(real_base_text: str) -> None:
    """
    @brief      Diffing base vs. output line-by-line shows changes only on the
                twelve generator-owned assignment lines.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If a non-owned line changed.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    generated = _generate(real_base_text).text
    base_lines = real_base_text.splitlines()
    generated_lines = generated.splitlines()
    assert len(base_lines) == len(generated_lines)  # every owned value is single-line in the real base
    owned_keys = {
        "roots",
        "language",
        "source_extensions",
        "coverable_roots",
        "test_file_patterns",
        "test",
        "lint",
        "enabled",
        "check",
        "implementation",
        "component-adoption",
    }
    for base_line, generated_line in zip(base_lines, generated_lines):
        if base_line == generated_line:
            continue
        key = base_line.split("=", 1)[0].strip()
        assert key in owned_keys, f"non-owned line changed: {base_line!r} -> {generated_line!r}"


# INVARIANT 5: NEVER-SAVE-INVALID GUARD


def test_verifier_rejects_missing_source_root_glob() -> None:
    """
    @brief      verify_workflow_invariants raises invariant 1 when a source
                root's glob is absent from [write_zones].implementation.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    document = {
        "traceability": {"coverable_roots": ["src"]},
        "write_zones": {
            "implementation": [COMPONENT_DOCS_ZONE],
            "check": ["tests/**"],
            "component-adoption": [".agentic/**", "tests/**"],
        },
    }
    with pytest.raises(InvariantViolationError) as excinfo:
        verify_workflow_invariants(document, source_roots=["src"], test_roots=["tests"])
    assert excinfo.value.invariant == 1
    assert "src/**" in str(excinfo.value)


def test_verifier_rejects_missing_test_root_in_component_adoption() -> None:
    """
    @brief      verify_workflow_invariants raises invariant 2 when a test
                root's glob is missing from [write_zones].component-adoption.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    document = {
        "traceability": {"coverable_roots": ["src"]},
        "write_zones": {
            "implementation": ["src/**", COMPONENT_DOCS_ZONE],
            "check": ["tests/**"],
            "component-adoption": [".agentic/**"],
        },
    }
    with pytest.raises(InvariantViolationError) as excinfo:
        verify_workflow_invariants(document, source_roots=["src"], test_roots=["tests"])
    assert excinfo.value.invariant == 2


def test_verifier_rejects_missing_component_docs_zone() -> None:
    """
    @brief      verify_workflow_invariants raises invariant 3 when
                .agentic/knowledge/components/** is absent from implementation.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    document = {
        "traceability": {"coverable_roots": ["src"]},
        "write_zones": {
            "implementation": ["src/**"],
            "check": ["tests/**"],
            "component-adoption": [".agentic/**", "tests/**"],
        },
    }
    with pytest.raises(InvariantViolationError) as excinfo:
        verify_workflow_invariants(document, source_roots=["src"], test_roots=["tests"])
    assert excinfo.value.invariant == 3


def test_generate_raises_when_rewrite_output_is_corrupted(
    real_base_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief      If the internal rewrite produced output violating invariant 3,
                generate_workflow_toml raises instead of returning it — the
                enforcement is wired into the generator, not just available.
    @param[in]  real_base_text The real template workflow.toml text.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If broken output is returned instead of raising.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    original = workflow_toml._apply_answers

    def corrupted(base_text: str, owned: dict) -> str:
        """
        @brief      Wrap the real rewrite and strip the component-docs zone.
        @param[in]  base_text Base TOML text.
        @param[in]  owned Owned (section, key) values.
        @return     The corrupted rewrite output.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return original(base_text, owned).replace(f'"{COMPONENT_DOCS_ZONE}"', '"docs/**"')

    monkeypatch.setattr(workflow_toml, "_apply_answers", corrupted)
    with pytest.raises(InvariantViolationError) as excinfo:
        _generate(real_base_text)
    assert excinfo.value.invariant == 3


def test_generate_raises_when_rewrite_touches_untouched_section(
    real_base_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief      If the rewrite accidentally changed a non-owned value, the
                invariant-4 re-check catches it before returning.
    @param[in]  real_base_text The real template workflow.toml text.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If drifted output is returned instead of raising.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    original = workflow_toml._apply_answers

    def drifting(base_text: str, owned: dict) -> str:
        """
        @brief      Wrap the real rewrite and corrupt an untouched value.
        @param[in]  base_text Base TOML text.
        @param[in]  owned Owned (section, key) values.
        @return     The drifted rewrite output.
        @exception  None
        @author     Eng. Dan Dumitru Pasare
        @version    0.1.0
        """
        return original(base_text, owned).replace(
            'default_completion_level = "baseline-usable"',
            'default_completion_level = "drifted"',
        )

    monkeypatch.setattr(workflow_toml, "_apply_answers", drifting)
    with pytest.raises(InvariantViolationError) as excinfo:
        _generate(real_base_text)
    assert excinfo.value.invariant == 4


def test_generate_raises_when_rewrite_output_is_unparseable(
    real_base_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    @brief      Rewrite output that no longer parses as TOML raises the
                invariant-5 round-trip error, never returning broken text.
    @param[in]  real_base_text The real template workflow.toml text.
    @param[in]  monkeypatch Pytest monkeypatch fixture.
    @return     None
    @exception  AssertionError If unparseable output is returned.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    monkeypatch.setattr(workflow_toml, "_apply_answers", lambda text, owned: "not = valid = toml")
    with pytest.raises(InvariantViolationError) as excinfo:
        _generate(real_base_text)
    assert excinfo.value.invariant == 5


# LANGUAGE "OTHER" (invariant 6)


def test_other_language_without_explicit_values_raises(real_base_text: str) -> None:
    """
    @brief      language="other" without source_extensions/test_file_patterns
                raises a clear LanguagePresetError (invariant 6).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    with pytest.raises(LanguagePresetError, match="other"):
        _generate(real_base_text, language="other")
    with pytest.raises(LanguagePresetError):
        resolve_language_preset("other", source_extensions=[".zig"])  # patterns still missing


def test_other_language_with_explicit_values_uses_them_verbatim(real_base_text: str) -> None:
    """
    @brief      language="other" with explicit values succeeds and emits
                exactly what was supplied.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If the supplied values were altered.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = generate_workflow_toml(
        real_base_text,
        source_roots=["src"],
        test_roots=["tests"],
        language="other",
        gate_test_cmds=[["zig", "build", "test"]],
        gate_lint_cmds=[],
        alignment_enabled=True,
        source_extensions=[".zig"],
        test_file_patterns=["*_test.zig"],
    )
    document = tomllib.loads(result.text)
    assert document["traceability"]["language"] == "other"
    assert document["traceability"]["source_extensions"] == [".zig"]
    assert document["traceability"]["test_file_patterns"] == ["*_test.zig"]


def test_explicit_values_override_a_preset(real_base_text: str) -> None:
    """
    @brief      Explicit extensions/patterns override the preset for a known
                language (the colocated-tests escape hatch, plan §15 D12).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If the override did not win.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = _generate(real_base_text, language="python", test_file_patterns=["check_*.py"])
    document = tomllib.loads(result.text)
    assert document["traceability"]["test_file_patterns"] == ["check_*.py"]
    assert document["traceability"]["source_extensions"] == [".py"]  # preset kept


def test_unknown_language_raises(real_base_text: str) -> None:
    """
    @brief      An unsupported language raises with the supported list named.
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    with pytest.raises(LanguagePresetError, match="unsupported language"):
        _generate(real_base_text, language="cobol")


# EMPTY-GATE WARNINGS


def test_empty_gates_generate_with_named_warnings(real_base_text: str) -> None:
    """
    @brief      Empty gates still generate successfully and the returned
                warning data names each empty gate (plan §7 loud warning).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If warnings are missing or misnamed.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    both = _generate(real_base_text, gate_test_cmds=[], gate_lint_cmds=[])
    assert [warning.gate for warning in both.warnings] == ["test", "lint"]
    assert all("pass without checking anything" in warning.message for warning in both.warnings)
    document = tomllib.loads(both.text)
    assert document["gates"]["test"] == [] and document["gates"]["lint"] == []

    only_lint = _generate(real_base_text, gate_lint_cmds=[])
    assert only_lint.warnings == (
        GateWarning(gate="lint", message="gate 'lint' is configured empty and will pass without checking anything"),
    )

    assert _generate(real_base_text).warnings == ()


# BASE-FILE EDGE CASES (synthetic fixtures)


def test_synthetic_base_with_multiline_array_is_rewritten() -> None:
    """
    @brief      An owned key written as a multi-line array (with a bracket
                inside a string) is consumed and replaced as one value span.
    @return     None
    @exception  AssertionError If the rewrite mangles the value span.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    result = _generate(SYNTHETIC_BASE, source_roots=["src", "app"])
    document = tomllib.loads(result.text)
    assert document["source"]["roots"] == ["src", "app"]
    assert document["untouched"]["value"] == "keep me"
    assert "# a comment that must survive" in result.text
    _assert_invariants(document, ["src", "app"], ["tests"])


def test_base_missing_an_owned_key_raises() -> None:
    """
    @brief      A base lacking a generator-owned key raises
                BaseFileMismatchError naming it, never emitting a file with
                missing settings.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    crippled = SYNTHETIC_BASE.replace("component-adoption = [\".agentic/**\", \"oldtests/**\"]\n", "")
    with pytest.raises(BaseFileMismatchError, match=r"\[write_zones\].component-adoption"):
        _generate(crippled)


def test_invalid_base_toml_raises() -> None:
    """
    @brief      A base that does not parse as TOML raises BaseFileMismatchError.
    @return     None
    @exception  AssertionError If no/incorrect error is raised.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    with pytest.raises(BaseFileMismatchError, match="not valid TOML"):
        _generate("[source\nroots = ?")


# ANSWER VALIDATION


@pytest.mark.parametrize(
    "bad_roots",
    [[], [""], ["src", "src"], ["/abs"], ["C:/abs"], ["../up"], ["src/*"], "  ,  "],
)
def test_invalid_roots_are_rejected(real_base_text: str, bad_roots: object) -> None:
    """
    @brief      Empty, duplicate, absolute, traversal, and glob roots are
                rejected by the shared roots validator.
    @param[in]  real_base_text The real template workflow.toml text.
    @param[in]  bad_roots The invalid roots answer.
    @return     None
    @exception  AssertionError If the invalid roots are accepted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    with pytest.raises(ValueError):
        _generate(real_base_text, source_roots=bad_roots)


def test_roots_accept_comma_separated_string_and_normalize_slashes() -> None:
    """
    @brief      The roots validator accepts console-style comma-separated
                strings and normalizes backslashes/trailing slashes.
    @return     None
    @exception  AssertionError If normalization differs.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    assert normalize_roots("src, app/") == ["src", "app"]
    assert normalize_roots(["src\\main\\java"]) == ["src/main/java"]


def test_flat_gate_command_list_is_rejected() -> None:
    """
    @brief      A flat list of strings is rejected as an ambiguous gate answer
                (one command or several?) rather than guessed at.
    @return     None
    @exception  AssertionError If the ambiguous shape is accepted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    with pytest.raises(ValueError):
        normalize_gate_commands(["pytest", "-q"])
    with pytest.raises(ValueError):
        normalize_gate_commands([[]])
    assert normalize_gate_commands([]) == []
    assert normalize_gate_commands([["pytest", "-q"]]) == [["pytest", "-q"]]


def test_gate_commands_console_string_is_parsed_as_json() -> None:
    """
    @brief      Regression (T4.4 live verification): a ``str`` answer — the
                only shape ``ConsoleAsker``/an answers-file text value can ever
                produce — is parsed as JSON rather than rejected outright.
    @details    Before this fix, every non-empty string typed at the console
                for ``gate_test_cmds``/``gate_lint_cmds`` failed validation
                unconditionally (the validator only accepted an already-built
                ``Sequence``), so a real operator could never configure a
                non-empty gate interactively — ``ConsoleAsker.ask_field``
                re-prompts forever on an invalid answer.
    @return     None
    @exception  AssertionError If a valid JSON string is rejected, or malformed
                JSON is silently accepted.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    assert normalize_gate_commands('[["uv", "run", "pytest", "-q"]]') == [["uv", "run", "pytest", "-q"]]
    assert normalize_gate_commands("[]") == []
    with pytest.raises(ValueError):
        normalize_gate_commands("not json")
    with pytest.raises(ValueError):
        normalize_gate_commands('["pytest", "-q"]')  # still ambiguous once parsed


def test_console_asker_accepts_typed_gate_command_on_first_try() -> None:
    """
    @brief      Regression (T4.4 live verification): typing the prompt's own
                JSON example for ``gate_test_cmds`` at a real ``ConsoleAsker``
                must succeed on the first try, not print a rejection and
                re-prompt.
    @return     None
    @exception  AssertionError If the console answer is rejected.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    spec = next(s for s in WORKFLOW_FIELD_SPECS if s.key == "gate_test_cmds")
    stdin = io.StringIO('[["uv", "run", "pytest", "-q"]]\n')
    stdout = io.StringIO()
    asker = ConsoleAsker(stdin=stdin, stdout=stdout)
    result = asker.ask_field(spec)
    assert result == [["uv", "run", "pytest", "-q"]]
    assert "must be" not in stdout.getvalue()


# FIELDSPEC COMPOSITION (T1.2 primitives)


def test_field_specs_defaults_via_guard_answers() -> None:
    """
    @brief      guard_answers over WORKFLOW_FIELD_SPECS with no answers yields
                exactly the plan §7 defaults.
    @return     None
    @exception  AssertionError If a default differs from plan §7.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    normalized = guard_answers(WORKFLOW_FIELD_SPECS, {})
    assert normalized == {
        "source_roots": ["src"],
        "test_roots": ["tests"],
        "language": "python",
        "gate_test_cmds": [],
        "gate_lint_cmds": [],
        "alignment_enabled": True,
    }


def test_field_specs_compose_with_scripted_asker() -> None:
    """
    @brief      ScriptedAsker.ask_field resolves and validates the workflow
                fields (string and typed forms); an invalid scripted value
                raises ScriptedAnswerError, not a silent acceptance.
    @return     None
    @exception  AssertionError If composition with T1.2 primitives breaks.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    specs = {spec.key: spec for spec in WORKFLOW_FIELD_SPECS}
    asker = ScriptedAsker(
        {
            "source_roots": "src, app",
            "test_roots": ["tests"],
            "language": "Go",
            "gate_test_cmds": [["go", "test", "./..."]],
            "alignment_enabled": "no",
        }
    )
    assert asker.ask_field(specs["source_roots"]) == ["src", "app"]
    assert asker.ask_field(specs["test_roots"]) == ["tests"]
    assert asker.ask_field(specs["language"]) == "go"
    assert asker.ask_field(specs["gate_test_cmds"]) == [["go", "test", "./..."]]
    assert asker.ask_field(specs["gate_lint_cmds"]) == []  # default applies
    assert asker.ask_field(specs["alignment_enabled"]) is False

    bad = ScriptedAsker({"language": "cobol"})
    with pytest.raises(ScriptedAnswerError):
        bad.ask_field(specs["language"])


def test_generated_answers_flow_into_generator(real_base_text: str) -> None:
    """
    @brief      End-to-end composition: answers normalized by guard_answers
                feed generate_workflow_toml directly (the T4.3 wiring shape).
    @param[in]  real_base_text The real template workflow.toml text.
    @return     None
    @exception  AssertionError If the composed flow fails.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    answers = guard_answers(
        WORKFLOW_FIELD_SPECS,
        {"source_roots": "src, app", "language": "rust", "gate_test_cmds": [["cargo", "test"]]},
    )
    result = generate_workflow_toml(real_base_text, **answers)
    document = tomllib.loads(result.text)
    _assert_invariants(document, ["src", "app"], ["tests"])
    assert document["traceability"]["language"] == "rust"
    assert [warning.gate for warning in result.warnings] == ["lint"]


# INDEPENDENT ROUND TRIP (stdlib tomllib only, bypassing the module)


def test_written_file_round_trips_through_stdlib_tomllib(
    real_base_text: str, tmp_path: Path
) -> None:
    """
    @brief      The generated text, written to disk and read back with
                tomllib.load directly (not this module's parser call),
                satisfies invariants 1–3 — guarding against the module's
                internal validation diverging from its actual output.
    @param[in]  real_base_text The real template workflow.toml text.
    @param[in]  tmp_path Pytest tmp directory.
    @return     None
    @exception  AssertionError If the independently parsed file violates an
                invariant.
    @author     Eng. Dan Dumitru Pasare
    @version    0.1.0
    """
    source_roots = ["src", "app", "lib"]
    test_roots = ["tests", "test"]
    result = _generate(real_base_text, source_roots=source_roots, test_roots=test_roots)
    target = tmp_path / "workflow.toml"
    target.write_text(result.text, encoding="utf-8", newline="\n")
    with open(target, "rb") as handle:
        document = tomllib.load(handle)
    _assert_invariants(document, source_roots, test_roots)
    assert document["source"]["roots"] == source_roots
    assert document["tests"]["roots"] == test_roots


# END OF FILE
