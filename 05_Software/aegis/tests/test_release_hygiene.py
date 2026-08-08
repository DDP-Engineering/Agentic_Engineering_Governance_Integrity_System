#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file test_release_hygiene.py
@brief Structural release-identity and copied-template hygiene checks.
@details Keeps current AEGIS/WAEGIS declarations synchronized while treating
         historical release records as history. The copied-verbatim template
         must remain free of generated interpreter state and release content.
"""

# IMPORTS

from __future__ import annotations

import json
from pathlib import Path
import tomllib

from aegis import __version__ as AEGIS_VERSION
from waegis import __version__ as WAEGIS_PACKAGE_VERSION
from waegis.version import WIZARD_VERSION

# CONSTANTS

AEGIS_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = AEGIS_ROOT.parents[1]
TEMPLATE_ROOT = AEGIS_ROOT / "template"
WAEGIS_ROOT = REPOSITORY_ROOT / "05_Software" / "waegis"
CURRENT_TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
}


# LOCAL HELPERS


def _toml(path: Path) -> dict:
    """@brief Read one UTF-8 TOML document for a structural assertion."""
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _current_template_texts() -> tuple[Path, ...]:
    """
    @brief      Enumerate current user-facing/source template text.
    @details    The empty downstream changelog is checked separately; historical
                root release records are intentionally outside this current-text
                scan.
    @return     Sorted template-relative text paths.
    @exception  None.
    """
    return tuple(
        sorted(
            (
                path
                for path in TEMPLATE_ROOT.rglob("*")
                if path.is_file()
                and path.name != "CHANGELOG.md"
                and path.suffix.lower() in CURRENT_TEXT_SUFFIXES
            ),
            key=lambda path: path.relative_to(TEMPLATE_ROOT).as_posix(),
        )
    )


# TESTS


def test_current_aegis_version_declarations_agree() -> None:
    """
    @brief      Keep every current AEGIS package and versioned adapter aligned.
    @return     None.
    @exception  AssertionError If any declaration diverges.
    """
    declarations = {
        "development project": _toml(AEGIS_ROOT / "pyproject.toml")["project"]["version"],
        "embedded project": _toml(
            TEMPLATE_ROOT / ".agentic" / "cli" / "pyproject.toml"
        )["project"]["version"],
        "embedded package": AEGIS_VERSION,
    }
    versioned_adapters = []
    for manifest_path in sorted(TEMPLATE_ROOT.glob(".*/package.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "version" in manifest:
            label = manifest_path.relative_to(TEMPLATE_ROOT).as_posix()
            declarations[label] = manifest["version"]
            versioned_adapters.append(label)

    assert versioned_adapters
    assert set(declarations.values()) == {"3.0.0"}, declarations


def test_current_waegis_version_declarations_agree() -> None:
    """
    @brief      Keep WAEGIS package metadata and the current delivery record aligned.
    @return     None.
    @exception  AssertionError If any current declaration diverges.
    """
    project = _toml(WAEGIS_ROOT / "pyproject.toml")
    delivery_manifest = json.loads(
        (
            REPOSITORY_ROOT
            / "07_Delivery"
            / f"waegis-{WIZARD_VERSION}"
            / "release-manifest.json"
        ).read_text(encoding="utf-8")
    )

    assert project["project"]["dynamic"] == ["version"]
    assert project["tool"]["setuptools"]["dynamic"]["version"]["attr"] == (
        "waegis.version.WIZARD_VERSION"
    )
    assert WAEGIS_PACKAGE_VERSION == WIZARD_VERSION == "1.2.0"
    assert delivery_manifest["waegis_version"] == WIZARD_VERSION


def test_current_template_material_names_the_current_product_line() -> None:
    """
    @brief      Reject obsolete product branding in current shipped template text.
    @return     None.
    @exception  AssertionError If current material names an obsolete minor line.
    """
    obsolete = ("AEGIS 2.0", "AEGIS 2.1", "WAEGIS 1.0")
    offending = {
        path.relative_to(TEMPLATE_ROOT).as_posix(): marker
        for path in _current_template_texts()
        for marker in obsolete
        if marker in path.read_text(encoding="utf-8")
    }

    assert offending == {}
    assert "AEGIS 3.0" in (TEMPLATE_ROOT / "AGENTS.md").read_text(encoding="utf-8")


def test_historical_changelog_versions_are_not_current_branding_failures() -> None:
    """
    @brief      Prove valid historical release text remains outside current checks.
    @return     None.
    @exception  AssertionError If history was rewritten or enters the live scan.
    """
    historical = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "AEGIS payload 2.0.0" in historical
    assert all(path.name != "CHANGELOG.md" for path in _current_template_texts())


def test_copied_template_contains_no_interpreter_cache_artifacts() -> None:
    """
    @brief      Keep copied-verbatim payload material free of Python caches.
    @return     None.
    @exception  AssertionError If a cache directory or bytecode file is present.
    """
    artifacts = tuple(
        path.relative_to(TEMPLATE_ROOT).as_posix()
        for path in TEMPLATE_ROOT.rglob("*")
        if path.name == "__pycache__" or path.suffix.lower() in {".pyc", ".pyo"}
    )

    assert artifacts == ()


def test_downstream_template_changelog_remains_empty() -> None:
    """
    @brief      Preserve the downstream starter changelog as an empty file.
    @return     None.
    @exception  AssertionError If repository release history leaks downstream.
    """
    assert (TEMPLATE_ROOT / "CHANGELOG.md").read_bytes() == b""


# END OF FILE
