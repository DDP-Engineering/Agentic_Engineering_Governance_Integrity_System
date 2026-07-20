#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file locate.py
@brief Payload resolution order (--payload > bundled marker > repo checkout).
@details Implements plan §5's payload resolution contract for task T3.2. An
         explicit ``--payload`` path wins, but only after validation that it
         looks like a payload root (contains the ``.agentic/workflow.toml``
         marker — plan §2 calls that file the single configuration surface,
         so every shippable payload has one). A bundled-install payload is a
         current resource resolved from the application-archive sibling tree,
         package data, or
         the executing zipapp. The final fallback is the repo-checkout
         template at ``05_Software/aegis/template/`` resolved relative to
         this installed module, mirroring how
         ``02_Tools/create_project_from_template.py`` resolves its
         ``TEMPLATE_ROOT``. Packaged zipapps extract their embedded payload to
         a content-addressed per-user cache; application archives expose the
         payload beside the launcher. Also owns ``read_payload_version``: the
         payload's
         own version is read from ``<payload>/.agentic/cli/pyproject.toml``
         ``[project].version`` (the canonical template version declaration
         per AGENTS.md), degrading to ``None`` rather than raising.
@details Pure resolution logic: no printing, no network, read-only filesystem
         access.
@author Eng. Dan Dumitru Pasare
@date 2026-07-12
@version 0.2.0
"""

# IMPORTS

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import tomllib
import uuid
import zipfile
from os import PathLike
from pathlib import Path, PurePosixPath

from ..engine.journal import waegis_home

# CONSTANTS

# @brief Payload-relative path whose presence marks a directory as a payload
#        root (plan §2: the single configuration surface every payload ships).
PAYLOAD_MARKER = ".agentic/workflow.toml"

# @brief Payload-relative path of the file declaring the payload's version.
PAYLOAD_VERSION_FILE = ".agentic/cli/pyproject.toml"

# @brief Package prefix used by the payload-bundled zipapp builder.
_ZIPAPP_PAYLOAD_PREFIX = "waegis/_bundled_payload/"

# DATA MODELS / TYPEDEFINITIONS


class PayloadLocateError(Exception):
    """
    @brief Base error for payload resolution failures.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class InvalidPayloadError(PayloadLocateError):
    """
    @brief An explicitly supplied ``--payload`` path is not a payload root.
    @details Raised only for the explicit-override case: the operator named a
             path, so a silent fallback to another candidate would hide their
             mistake.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


class PayloadNotFoundError(PayloadLocateError):
    """
    @brief No payload candidate resolved to an existing payload root.
    @author Eng. Dan Dumitru Pasare
    @date 2026-07-12
    @version 0.1.0
    """


# EXPORTED FUNCTIONS / PUBLIC API


def is_payload_root(path: str | PathLike[str]) -> bool:
    """
    @brief      Report whether a directory looks like an AEGIS payload root.
    @details    True when ``path`` is a directory containing the
                ``.agentic/workflow.toml`` marker file.
    @param[in]  path Candidate payload root directory.
    @return     ``True`` when the marker is present.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    root = Path(path)
    return root.is_dir() and (root / PAYLOAD_MARKER).is_file()


def bundled_payload_root() -> Path | None:
    """
    @brief      Resolve the payload bundled with a packaged waegis install.
    @details    Application archives expose a sibling ``payload`` directory.
                Installed packages may contain ``waegis/_bundled_payload``.
                A standalone ``.pyz`` stores that tree inside the archive and
                extracts it once into a content-addressed per-user cache.
    @return     Resolved bundled payload root, or ``None`` for a source build.
    @exception  PayloadLocateError If a zipapp contains an unsafe payload entry.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    explicit = os.environ.get("WAEGIS_BUNDLED_PAYLOAD")
    candidates = []
    if explicit:
        candidates.append(Path(explicit))
    executable = Path(sys.argv[0]).resolve()
    candidates.append(executable.parent / "payload")
    candidates.append(Path(__file__).resolve().parents[1] / "_bundled_payload")
    for candidate in candidates:
        if is_payload_root(candidate):
            return candidate.resolve()
    if executable.is_file() and zipfile.is_zipfile(executable):
        return _extract_zipapp_payload(executable)
    return None


def _extract_zipapp_payload(archive: Path) -> Path | None:
    """@brief Safely extract and cache the payload embedded in a zipapp."""
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    cache = waegis_home() / "payload-cache" / digest
    if is_payload_root(cache):
        return cache.resolve()
    temporary = cache.with_name(f"{cache.name}.tmp-{uuid.uuid4().hex[:8]}")
    found = False
    try:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                if not info.filename.startswith(_ZIPAPP_PAYLOAD_PREFIX):
                    continue
                relative_text = info.filename[len(_ZIPAPP_PAYLOAD_PREFIX) :]
                if not relative_text:
                    continue
                relative = PurePosixPath(relative_text)
                if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                    raise PayloadLocateError(f"unsafe bundled payload path: {info.filename!r}")
                if ((info.external_attr >> 16) & 0o170000) == 0o120000:
                    raise PayloadLocateError(f"bundled payload contains a symlink: {info.filename!r}")
                destination = temporary.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                with bundle.open(info) as source, open(destination, "wb") as target:
                    shutil.copyfileobj(source, target)
                found = True
        if not found or not is_payload_root(temporary):
            shutil.rmtree(temporary, ignore_errors=True)
            return None
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.exists():
            shutil.rmtree(cache)
        os.replace(temporary, cache)
        return cache.resolve()
    except PayloadLocateError:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    except (OSError, zipfile.BadZipFile) as exc:
        shutil.rmtree(temporary, ignore_errors=True)
        raise PayloadLocateError(f"cannot extract bundled payload from {archive}: {exc}") from exc


def repo_checkout_payload_root() -> Path | None:
    """
    @brief      Resolve the repo-checkout template payload relative to this
                installed module.
    @details    From ``.../05_Software/waegis/src/waegis/payload/locate.py``
                walk up to ``05_Software/`` and descend into
                ``aegis/template/`` — the same shape as the legacy script's
                ``TEMPLATE_ROOT`` resolution.
    @return     The template directory when it exists and looks like a payload
                root, else ``None``.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    candidate = Path(__file__).resolve().parents[4] / "aegis" / "template"
    return candidate if is_payload_root(candidate) else None


def locate_payload(explicit: str | PathLike[str] | None = None) -> Path:
    """
    @brief      Resolve the payload root per the plan §5 order:
                explicit ``--payload`` > bundled install > repo checkout.
    @param[in]  explicit Optional operator-supplied ``--payload`` path. When
                given it is used as-is after validation and no fallback is
                attempted.
    @return     The resolved payload root directory.
    @exception  InvalidPayloadError If ``explicit`` is given but is not a
                payload root (missing directory or missing marker).
    @exception  PayloadNotFoundError If no candidate resolves to an existing
                payload root.
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    if explicit is not None:
        root = Path(explicit)
        if not is_payload_root(root):
            raise InvalidPayloadError(
                f"--payload path does not look like a payload root (missing {PAYLOAD_MARKER}): {root}"
            )
        return root.resolve()

    bundled = bundled_payload_root()
    if bundled is not None and is_payload_root(bundled):
        return bundled.resolve()

    checkout = repo_checkout_payload_root()
    if checkout is not None:
        return checkout.resolve()

    raise PayloadNotFoundError(
        "no AEGIS payload found: no --payload override was given, this waegis build "
        "exposes no bundled payload, and no repo-checkout template exists "
        "at 05_Software/aegis/template/ relative to the waegis package"
    )


def read_payload_version(payload_root: str | PathLike[str]) -> str | None:
    """
    @brief      Read the payload's own version from its version declaration.
    @details    Parses ``<payload_root>/.agentic/cli/pyproject.toml`` and
                returns ``[project].version``. Degrades to ``None`` (never
                raises) when the file is absent, unparseable, or the field is
                missing/not a string — callers decide the fallback (T3.2's
                copier uses ``"unknown"``).
    @param[in]  payload_root Payload root directory.
    @return     The version string, or ``None`` when it cannot be determined.
    @exception  None
    @author     Eng. Dan Dumitru Pasare
    @date       2026-07-12
    @version    0.1.0
    """
    version_file = Path(payload_root) / PAYLOAD_VERSION_FILE
    try:
        with open(version_file, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    version = data.get("project", {}).get("version") if isinstance(data.get("project"), dict) else None
    return version if isinstance(version, str) and version else None


# END OF FILE
