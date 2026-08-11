#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Read and verify an assembled AEGIS payload strictly as versioned data."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path

from waegis.domain.plans import PlanError, safe_relative


@dataclass(frozen=True, slots=True)
class PayloadManifest:
    """Hold exact manifest-owned payload bytes after digest verification."""

    version: str
    files: dict[str, bytes]
    digests: dict[str, str]

    @classmethod
    def load(cls, root: Path, *, verify: bool = True) -> PayloadManifest:
        """Load a manifest and reject absent, unsafe, duplicate, or changed files."""
        manifest_path = root / "manifest.toml"
        try:
            manifest_bytes = manifest_path.read_bytes()
            data = tomllib.loads(manifest_bytes.decode("utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise PlanError(f"Invalid payload manifest: {exc}") from exc
        if (
            data.get("schema") != 1
            or data.get("artifact_type") != "payload_manifest"
            or not isinstance(data.get("product_version"), str)
        ):
            raise PlanError("Payload manifest schema or version is invalid")
        files: dict[str, bytes] = {"manifest.toml": manifest_bytes}
        digests: dict[str, str] = {
            "manifest.toml": hashlib.sha256(manifest_bytes).hexdigest()
        }
        for entry in data.get("files", []):
            if not isinstance(entry, dict):
                raise PlanError("Payload manifest file entry is invalid")
            relative = safe_relative(str(entry.get("path", "")))
            if relative == "manifest.toml" or relative in files:
                raise PlanError(f"Duplicate payload manifest path: {relative}")
            try:
                candidate = (root / Path(relative)).resolve(strict=True)
                candidate.relative_to(root.resolve())
                content = candidate.read_bytes()
            except (OSError, ValueError) as exc:
                raise PlanError(f"Payload file is unavailable: {relative}") from exc
            actual = hashlib.sha256(content).hexdigest()
            expected = str(entry.get("sha256", ""))
            if verify and (actual != expected or len(content) != entry.get("size")):
                raise PlanError(f"Payload digest mismatch: {relative}")
            files[relative] = content
            digests[relative] = expected
        return cls(version=data["product_version"], files=files, digests=digests)

    def modified_installed_paths(self, target: Path) -> list[str]:
        """Report source-manifest paths whose installed bytes differ."""
        modified: list[str] = []
        payload_root = target / ".agentic" / "aegis"
        for relative, expected in self.digests.items():
            path = payload_root / Path(relative)
            if (
                path.exists()
                and hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                modified.append(relative)
        return sorted(modified)
