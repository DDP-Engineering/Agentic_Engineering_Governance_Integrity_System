#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""
@file repowise.py
@brief Offline RepoWise sidecar configuration, installation, and synchronization.
@details Keeps RepoWise optional and process-isolated. WAEGIS validates either
         the bundled 0.37.0 runtime or an external 0.37.x command, runs indexing
         with machine-readable progress, and writes artifacts that AEGIS later
         validates without importing or executing RepoWise.
"""

# IMPORTS

from __future__ import annotations

import hashlib
import json
import os
import platform
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any, Mapping, Sequence

from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .consent import ConsentDecision, mutation_consent
from .engine.journal import waegis_home
from .payload.manifest import (
    MANIFEST_RELATIVE_PATH,
    Manifest,
    ManifestState,
    hash_file,
    load_manifest,
    resolve_managed_path,
    write_manifest,
)
from .probes.runner import CommandRunner
from .transaction import (
    FileTransaction,
    TransactionCleanupError,
    TransactionError,
)

# CONSTANTS

REPOWISE_VERSION = "0.37.0"
REPOWISE_VERSION_SPEC = ">=0.37.0,<0.38.0"
INTEGRATION_PATH = Path(".agentic/integrations/repowise.toml")
INTEGRATION_RELATIVE_PATH = INTEGRATION_PATH.as_posix()
RUNTIME_PATH = Path(".agentic/integrations/repowise-runtime.json")
RECEIPT_PATH = Path(".agentic/integrations/repowise-receipt.json")
ARTIFACT_PATH = Path(".repowise/knowledge-graph.json")
STATE_PATH = Path(".repowise/state.json")
TOOLS_PATH = Path(".agentic/tools/repowise") / REPOWISE_VERSION
BUNDLE_MANIFEST = "repowise-bundle-manifest.json"
INTEGRATION_SCHEMA = 1
RUNTIME_SCHEMA = 1
RECEIPT_SCHEMA = 1
BUNDLE_SCHEMA = 1
VALID_SOURCES = frozenset({"disabled", "bundled", "external"})
VALID_PROFILES = frozenset({"deterministic", "ollama"})
VALID_ENFORCEMENT = frozenset({"advisory", "required"})
SUPPORTED_EDITIONS = frozenset({"core", "complete"})
# Matches any dotted release so an unsupported version is parsed first and
# then rejected with the explicit "outside >=0.37.0,<0.38.0" message, rather
# than misreported as a missing --version capability.
VERSION_PATTERN = re.compile(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)")
_CLOUD_ENV_MARKERS = (
    "OPENAI",
    "ANTHROPIC",
    "AZURE",
    "AWS_",
    "GOOGLE",
    "GEMINI",
    "OLLAMA",
    "LITELLM",
    "OPENROUTER",
    "DEEPSEEK",
    "KIMI",
)
REPOWISE_ANSWER_KEYS = frozenset(
    {
        "repowise_source",
        "repowise_external_command",
        "repowise_profile",
        "repowise_ollama_url",
        "repowise_model",
        "repowise_embedding_model",
        "repowise_enforcement",
        "repowise_sync",
    }
)


# DATA TYPES


@dataclass(frozen=True)
class RepoWiseSettings:
    """
    @brief Validated WAEGIS-side RepoWise configuration.
    """

    source: str = "disabled"
    external_command: tuple[str, ...] = ()
    profile: str = "deterministic"
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = ""
    embedding_model: str = ""
    enforcement: str = "advisory"
    sync: bool = False

    def to_dict(self) -> dict[str, Any]:
        """@brief Return a JSON-safe settings mapping."""
        result = asdict(self)
        result["external_command"] = list(self.external_command)
        return result


@dataclass(frozen=True)
class RepoWiseSyncResult:
    """
    @brief Result of one managed RepoWise synchronization.
    """

    ok: bool
    action: str
    message: str
    log: str | None
    resume_command: str | None
    profile: str
    fallback: bool = False

    def to_dict(self) -> dict[str, Any]:
        """@brief Return a JSON-safe synchronization result."""
        return asdict(self)


class RepoWiseError(RuntimeError):
    """
    @brief Validation or operational failure in RepoWise integration handling.
    """


# LOCAL HELPERS


def _utc_now() -> str:
    """@brief Return the current UTC time in stable ISO-8601 form."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(path: Path) -> str:
    """@brief Return the SHA-256 digest of one regular file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """
    @brief Atomically write one formatted JSON document through an exclusive temp.
    """
    _write_bytes(path, (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def _write_text(path: Path, text: str) -> None:
    """
    @brief Atomically write one UTF-8 text document through an exclusive temp.
    """
    _write_bytes(path, text.encode("utf-8"))


def _write_bytes(path: Path, data: bytes) -> None:
    """
    @brief Exclusively create, flush, and atomically replace a sibling file.
    @param[in] path Exact destination pathname.
    @param[in] data Complete replacement bytes.
    @return None.
    @exception OSError If the write or replacement fails.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(raw_temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    """@brief Read one JSON object or raise a contract-focused error."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepoWiseError(f"invalid RepoWise JSON file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RepoWiseError(f"RepoWise JSON file must contain an object: {path}")
    return data


def _ensure_repo(repo: Path) -> Path:
    """@brief Resolve and validate a repository directory."""
    resolved = repo.resolve()
    if not resolved.is_dir():
        raise RepoWiseError(f"repository does not exist: {resolved}")
    return resolved


def _is_loopback_url(value: str) -> bool:
    """@brief Return whether an HTTP(S) URL targets only the loopback host."""
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        and parsed.username is None
        and parsed.password is None
    )


def _validate_settings(settings: RepoWiseSettings) -> None:
    """@brief Enforce the strict RepoWise settings contract."""
    if settings.source not in VALID_SOURCES:
        raise RepoWiseError(f"invalid repowise_source: {settings.source!r}")
    if settings.profile not in VALID_PROFILES:
        raise RepoWiseError(f"invalid repowise_profile: {settings.profile!r}")
    if settings.enforcement not in VALID_ENFORCEMENT:
        raise RepoWiseError(f"invalid repowise_enforcement: {settings.enforcement!r}")
    if settings.source == "external" and not settings.external_command:
        raise RepoWiseError("repowise_external_command is required for an external source")
    if settings.source != "external" and settings.external_command:
        raise RepoWiseError("repowise_external_command is valid only for an external source")
    if settings.profile == "ollama" and not _is_loopback_url(settings.ollama_url):
        raise RepoWiseError("repowise_ollama_url must use a loopback HTTP(S) endpoint")


def _normalize_command(raw: Any) -> list[str]:
    """@brief Normalize an external command from a prompt or answers file."""
    if isinstance(raw, str):
        result = shlex.split(raw, posix=os.name != "nt")
    elif isinstance(raw, list):
        result = [str(item) for item in raw]
    else:
        raise ValueError("expected a command string or an array of command arguments")
    if not result or any(not item.strip() for item in result):
        raise ValueError("the RepoWise command cannot be empty")
    return result


def _integration_text(settings: RepoWiseSettings) -> str:
    """@brief Render the strict AEGIS RepoWise integration policy."""
    enabled = settings.source != "disabled"
    mode = settings.enforcement if enabled else "disabled"
    source = settings.source if enabled else "none"
    return (
        "# Optional RepoWise discovery integration. Absence also means disabled.\n"
        f"schema_version = {INTEGRATION_SCHEMA}\n"
        'provider = "repowise"\n'
        f'mode = "{mode}"\n'
        f'source = "{source}"\n'
        f'version_spec = "{REPOWISE_VERSION_SPEC}"\n'
        f'artifact = "{ARTIFACT_PATH.as_posix()}"\n'
        f'state = "{STATE_PATH.as_posix()}"\n'
        "require_head_match = true\n"
        "require_worktree_match = true\n"
    )


def _updated_install_manifest(
    repo: Path,
    settings: RepoWiseSettings,
    *,
    policy_sha256: str,
) -> Manifest | None:
    """
    @brief Build the RepoWise-owned install manifest without writing it.
    @param[in] repo Target AEGIS repository.
    @param[in] settings Validated RepoWise settings.
    @param[in] policy_sha256 Digest of the planned policy bytes.
    @return Updated manifest, or ``None`` when no install manifest exists.
    @exception RepoWiseError If an existing install manifest is invalid.
    """
    load = load_manifest(repo)
    if load.state is ManifestState.ABSENT:
        return None
    if load.state is not ManifestState.VALID or load.manifest is None:
        raise RepoWiseError("cannot configure RepoWise with an invalid WAEGIS install manifest")
    manifest = load.manifest
    files = dict(manifest.files)
    files.pop(INTEGRATION_RELATIVE_PATH, None)
    generated = tuple(sorted(set(manifest.generated) | {INTEGRATION_RELATIVE_PATH}))
    configuration = dict(manifest.configuration)
    raw_generated = configuration.get("generated_files")
    generated_files = dict(raw_generated) if isinstance(raw_generated, Mapping) else {}
    generated_files[INTEGRATION_RELATIVE_PATH] = {"sha256": policy_sha256}
    configuration["generated_files"] = generated_files
    configuration["repowise"] = {
        "schema_version": INTEGRATION_SCHEMA,
        "source": settings.source,
        "profile": settings.profile,
        "ollama_url": settings.ollama_url,
        "model": settings.model,
        "embedding_model": settings.embedding_model,
        "enforcement": settings.enforcement,
    }
    return replace(
        manifest,
        files=files,
        generated=generated,
        configuration=configuration,
    )


def _amend_install_manifest(repo: Path, settings: RepoWiseSettings) -> None:
    """
    @brief Record the RepoWise policy as generated project-local configuration.
    @details A repository without an install manifest is valid for direct unit
             use. When a valid WAEGIS manifest exists, this function removes
             the template policy from the verbatim payload inventory, records
             its current generated digest, and preserves non-secret settings
             needed by repair.
    @param[in] repo Target AEGIS repository.
    @param[in] settings Validated RepoWise settings.
    @return None
    @exception RepoWiseError If an existing install manifest is invalid.
    @exception OSError If the manifest cannot be written.
    """
    policy = resolve_managed_path(repo, INTEGRATION_RELATIVE_PATH)
    updated = _updated_install_manifest(
        repo,
        settings,
        policy_sha256=hash_file(policy).sha256,
    )
    if updated is None:
        return
    write_manifest(repo, updated)


def _tree_digest(root: Path) -> tuple[str, int]:
    """@brief Return a stable digest and size excluding the self-describing manifest."""
    digest = hashlib.sha256()
    total = 0
    for path in sorted(
        item
        for item in root.rglob("*")
        if item.is_file() and item.relative_to(root).as_posix() != BUNDLE_MANIFEST
    ):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), total


def _manifest_files_valid(root: Path, manifest: Mapping[str, Any]) -> None:
    """@brief Validate every declared runtime file without accepting traversal."""
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise RepoWiseError("RepoWise bundle manifest files must be a non-empty array")
    root_resolved = root.resolve()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise RepoWiseError("invalid RepoWise bundle file entry")
        relative = Path(str(item["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise RepoWiseError(f"unsafe RepoWise bundle path: {relative}")
        target = (root / relative).resolve()
        if root_resolved not in target.parents:
            raise RepoWiseError(f"RepoWise bundle path escapes its root: {relative}")
        if not target.is_file() or target.is_symlink():
            raise RepoWiseError(f"RepoWise bundle file is missing or unsafe: {relative}")
        if target.stat().st_size != item["size"] or _sha256(target) != item["sha256"]:
            raise RepoWiseError(f"RepoWise bundle file digest mismatch: {relative}")


def _load_bundle_manifest(root: Path) -> dict[str, Any]:
    """@brief Load and strictly validate the native RepoWise bundle manifest.
    """
    manifest = _load_json(root / BUNDLE_MANIFEST)
    required = {
        "schema_version",
        "edition",
        "repowise_version",
        "platform",
        "launcher",
        "source",
        "source_sha256",
        "tree_sha256",
        "packaged_size",
        "unpacked_size",
        "files",
    }
    unknown = sorted(set(manifest) - required)
    missing = sorted(required - set(manifest))
    if unknown or missing:
        raise RepoWiseError(
            "invalid RepoWise bundle manifest keys"
            f"; missing={missing or 'none'}; unknown={unknown or 'none'}"
        )
    if manifest["schema_version"] != BUNDLE_SCHEMA:
        raise RepoWiseError("unsupported RepoWise bundle manifest schema")
    if manifest["edition"] != "complete" or manifest["repowise_version"] != REPOWISE_VERSION:
        raise RepoWiseError("bundle is not the Complete RepoWise 0.37.0 payload")
    source = manifest["source"]
    if (
        not isinstance(source, dict)
        or set(source) != {"tag", "commit", "archive"}
        or source["tag"] not in {"v0.37.0", "0.37.0"}
        or not isinstance(source["commit"], str)
        or not re.fullmatch(r"[0-9a-f]{40}", source["commit"])
        or source["archive"] != "repowise-0.37.0-source.zip"
    ):
        raise RepoWiseError("RepoWise bundle source provenance is invalid")
    if manifest["platform"] != runtime_platform():
        raise RepoWiseError(
            f"RepoWise bundle targets {manifest['platform']}, not {runtime_platform()}"
        )
    if (
        not isinstance(manifest["packaged_size"], int)
        or manifest["packaged_size"] <= 0
        or not isinstance(manifest["unpacked_size"], int)
        or manifest["unpacked_size"] <= 0
        or manifest["packaged_size"] > manifest["unpacked_size"]
    ):
        raise RepoWiseError("RepoWise bundle packaged/unpacked sizes are invalid")
    _manifest_files_valid(root, manifest)
    source_archive = root / str(source["archive"])
    if (
        not isinstance(manifest["source_sha256"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", manifest["source_sha256"])
        or not source_archive.is_file()
        or _sha256(source_archive) != manifest["source_sha256"]
    ):
        raise RepoWiseError("RepoWise exact source archive digest is invalid")
    digest, size = _tree_digest(root)
    if digest != manifest["tree_sha256"] or size != manifest["unpacked_size"]:
        raise RepoWiseError("RepoWise bundle tree digest or unpacked size does not match")
    launcher = Path(str(manifest["launcher"]))
    if launcher.is_absolute() or ".." in launcher.parts or not (root / launcher).is_file():
        raise RepoWiseError("RepoWise bundle launcher is unsafe or missing")
    return manifest


def _runtime_command(repo: Path, runtime: Mapping[str, Any]) -> list[str]:
    """@brief Resolve the configured RepoWise command for execution.
    """
    command = runtime.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) and item for item in command)
    ):
        raise RepoWiseError("RepoWise runtime command must be a non-empty string array")
    resolved = list(command)
    first = Path(resolved[0])
    if not first.is_absolute() and (repo / first).exists():
        resolved[0] = str((repo / first).resolve())
    elif not first.is_absolute():
        located = shutil.which(resolved[0])
        if located:
            resolved[0] = located
    launcher = Path(resolved[0])
    if os.name == "nt" and launcher.suffix.lower() in {".bat", ".cmd"}:
        if not launcher.is_file():
            raise RepoWiseError(f"RepoWise command is missing: {launcher}")
        return ["cmd.exe", "/d", "/c", *resolved]
    return resolved


def _command_version(
    command: Sequence[str],
    repo: Path,
    *,
    home: Path | None = None,
) -> str:
    """@brief Run a RepoWise version capability probe and return its version.
    """
    try:
        completed = subprocess.run(
            [*command, "--version"],
            cwd=repo,
            env=_offline_environment(
                RepoWiseSettings(),
                "deterministic",
                home=home,
            ),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepoWiseError(f"cannot execute RepoWise version probe: {exc}") from exc
    output = f"{completed.stdout}\n{completed.stderr}"
    match = VERSION_PATTERN.search(output)
    if completed.returncode != 0 or match is None:
        raise RepoWiseError("RepoWise command lacks a working --version capability")
    return match.group(1)


def _validate_command_capabilities(
    command: Sequence[str],
    repo: Path,
    *,
    home: Path | None = None,
) -> None:
    """@brief Confirm the RepoWise 0.37 CLI surfaces used by managed sync.
    """
    required = {
        "init": (
            "--resume",
            "--no-prose",
            "--embedder",
            "--progress",
            "--no-editor-setup",
            "--no-claude-md",
            "--no-agents",
            "--no-codex",
            "--no-distill-hook",
        ),
        "update": ("--progress", "--index-only", "--no-agents"),
    }
    for action, tokens in required.items():
        try:
            completed = subprocess.run(
                [*command, action, "--help"],
                cwd=repo,
                env=_offline_environment(
                    RepoWiseSettings(),
                    "deterministic",
                    home=home,
                ),
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RepoWiseError(
                f"cannot probe RepoWise {action} capability: {exc}"
            ) from exc
        output = f"{completed.stdout}\n{completed.stderr}"
        missing = [token for token in tokens if token not in output]
        if completed.returncode != 0 or missing:
            raise RepoWiseError(
                f"RepoWise {action} lacks required capability: "
                + ", ".join(missing or ("working --help",))
            )


def _git_output(repo: Path, *args: str) -> str:
    """@brief Return stripped Git output, or an empty string outside Git."""
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def _repository_fingerprints(repo: Path) -> tuple[str, str]:
    """@brief Return Git HEAD and the byte-sensitive AEGIS worktree digest.
    """
    head = _git_output(repo, "rev-parse", "--verify", "HEAD").lower()
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--",
                ".",
                ":(exclude).agentic/**",
                ":(exclude).repowise/**",
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return head, hashlib.sha256(b"non-git").hexdigest()
    if completed.returncode != 0:
        return head, hashlib.sha256(b"non-git").hexdigest()
    digest = hashlib.sha256(completed.stdout)
    for record in completed.stdout.split(b"\0"):
        if len(record) < 4:
            continue
        text = record[3:].decode("utf-8", errors="surrogateescape")
        candidate = text.rsplit(" -> ", 1)[-1]
        path = repo / candidate
        try:
            path.resolve().relative_to(repo.resolve())
        except (OSError, ValueError):
            continue
        if path.is_file() and not path.is_symlink():
            digest.update(candidate.encode("utf-8", errors="surrogateescape"))
            digest.update(_sha256(path).encode("ascii"))
    return head, digest.hexdigest()


def _receipt_current(repo: Path) -> bool:
    """@brief Return whether the generated receipt matches current artifacts.
    """
    receipt_file = repo / RECEIPT_PATH
    artifact = repo / ARTIFACT_PATH
    state = repo / STATE_PATH
    if not receipt_file.is_file() or not artifact.is_file() or not state.is_file():
        return False
    try:
        receipt = _load_json(receipt_file)
        runtime = _load_json(repo / RUNTIME_PATH)
        head, worktree = _repository_fingerprints(repo)
        return (
            receipt.get("schema_version") == RECEIPT_SCHEMA
            and receipt.get("provider") == "repowise"
            and isinstance(receipt.get("repowise_version"), str)
            and str(receipt["repowise_version"]).startswith("0.37.")
            and receipt.get("source") in {"bundled", "external"}
            and receipt.get("source") == runtime.get("source")
            and receipt.get("profile") == runtime.get("profile")
            and receipt.get("completed") is True
            and receipt.get("head") == head
            and receipt.get("worktree_fingerprint") == worktree
            and receipt.get("artifact_sha256") == _sha256(artifact)
            and receipt.get("state_sha256") == _sha256(state)
        )
    except (OSError, RepoWiseError):
        return False


def _resume_command(repo: Path) -> str:
    """@brief Return the exact public synchronization resume command."""
    return f'waegis repowise sync --repo "{repo}"'


def _ollama_available(url: str, required_models: Sequence[str]) -> bool:
    """@brief Confirm the loopback Ollama endpoint and requested local models.
    """
    endpoint = url.rstrip("/") + "/api/tags"
    try:
        request = Request(endpoint, headers={"Accept": "application/json"})
        with urlopen(request, timeout=3) as response:
            if not 200 <= int(response.status) < 300:
                return False
            document = json.loads(response.read().decode("utf-8"))
        models = document.get("models") if isinstance(document, dict) else None
        if not isinstance(models, list):
            return False
        available = {
            str(item.get("name") or item.get("model"))
            for item in models
            if isinstance(item, dict) and (item.get("name") or item.get("model"))
        }
        return all(not model or model in available for model in required_models)
    except (OSError, URLError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return False


def _offline_environment(
    settings: RepoWiseSettings,
    profile: str,
    *,
    home: Path | None = None,
) -> dict[str, str]:
    """@brief Build a cloud-scrubbed, user-config-isolated managed environment.
    """
    environment = {
        key: value
        for key, value in os.environ.items()
        if not any(marker in key.upper() for marker in _CLOUD_ENV_MARKERS)
    }
    environment.update(
        {
            "DO_NOT_TRACK": "1",
            "REPOWISE_TELEMETRY_DISABLED": "1",
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "WAEGIS_REPOWISE_OFFLINE": "1",
        }
    )
    isolated_home = (home if home is not None else waegis_home()) / "repowise-home"
    isolated_config = isolated_home / ".config"
    isolated_data = isolated_home / ".local" / "share"
    isolated_home.mkdir(parents=True, exist_ok=True)
    isolated_config.mkdir(parents=True, exist_ok=True)
    isolated_data.mkdir(parents=True, exist_ok=True)
    environment.update(
        {
            "HOME": str(isolated_home),
            "USERPROFILE": str(isolated_home),
            "APPDATA": str(isolated_config),
            "LOCALAPPDATA": str(isolated_data),
            "XDG_CONFIG_HOME": str(isolated_config),
            "XDG_DATA_HOME": str(isolated_data),
            "REPOWISE_SKIP_EDITOR_SETUP": "1",
        }
    )
    if profile == "ollama":
        environment["OLLAMA_BASE_URL"] = settings.ollama_url
        if settings.embedding_model:
            environment["OLLAMA_EMBEDDING_MODEL"] = settings.embedding_model
    return environment


def _action_for(repo: Path) -> str:
    """@brief Select init, resume, update, or no-op from current index state.
    """
    if _receipt_current(repo):
        return "no-op"
    if (repo / STATE_PATH).is_file() and (repo / ARTIFACT_PATH).is_file():
        return "update"
    checkpoints = repo / ".repowise" / "checkpoints"
    if checkpoints.exists() and any(checkpoints.iterdir()):
        return "resume"
    if (repo / STATE_PATH).is_file():
        return "update"
    return "init"


def _command_for(
    command: Sequence[str],
    repo: Path,
    action: str,
    settings: RepoWiseSettings,
    profile: str,
) -> list[str]:
    """@brief Construct the fixed, non-interactive RepoWise command.
    """
    if action == "update":
        result = [*command, "update", str(repo), "--progress", "json", "--no-agents"]
        if profile == "ollama":
            result.extend(["--provider", "ollama"])
            if settings.model:
                result.extend(["--model", settings.model])
        else:
            result.append("--index-only")
        return result
    result = [*command, "init", str(repo)]
    if action == "resume":
        result.append("--resume")
    result.extend(
        [
            "--mode",
            "standard",
            "--yes",
            "--progress",
            "json",
            "--exclude",
            ".agentic/tools/**",
            "--exclude",
            ".agentic/runs/**",
            "--no-claude-md",
            "--no-agents",
            "--no-codex",
            "--no-editor-setup",
            "--no-distill-hook",
        ]
    )
    if profile == "ollama":
        result.extend(["--prose", "--provider", "ollama"])
        if settings.model:
            result.extend(["--model", settings.model])
        result.extend(["--embedder", "ollama" if settings.embedding_model else "mock"])
    else:
        result.extend(["--no-prose", "--embedder", "mock"])
    return result


def _progress_message(line: str, elapsed: float) -> str | None:
    """@brief Convert one RepoWise JSON progress line into concise human text."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, dict):
        return None
    stage = event.get("stage") or event.get("event") or event.get("type")
    counts = []
    for key in ("files", "nodes", "edges", "processed", "total"):
        if isinstance(event.get(key), (int, float)):
            counts.append(f"{key}={event[key]}")
    suffix = " " + " ".join(counts) if counts else ""
    return f"repowise: {stage or 'progress'} elapsed={int(elapsed)}s{suffix}"


def _pump_process_output(source: IO[str], events: queue.Queue[str | None]) -> None:
    """@brief Forward process output to a queue so monitoring can heartbeat.
    """
    try:
        for line in source:
            events.put(line)
    finally:
        events.put(None)


def _validate_generated_artifacts(repo: Path) -> None:
    """@brief Validate the RepoWise graph and state schemas consumed by AEGIS.
    """
    graph = _load_json(repo / ARTIFACT_PATH)
    state = _load_json(repo / STATE_PATH)
    if (
        graph.get("version") != "1.0.0"
        or graph.get("schema_version") != 1
        or not isinstance(graph.get("project"), dict)
        or not isinstance(graph.get("nodes"), list)
    ):
        raise RepoWiseError("RepoWise knowledge graph schema is invalid")
    if not isinstance(graph.get("edges"), list) or not isinstance(graph.get("layers"), list):
        raise RepoWiseError("RepoWise knowledge graph lacks nodes/edges/layers")
    if not isinstance(state.get("last_sync_commit"), str):
        raise RepoWiseError("RepoWise state lacks a string last_sync_commit")


def _write_receipt(
    repo: Path,
    *,
    version: str,
    source: str,
    profile: str,
) -> None:
    """@brief Write a fresh validated synchronization receipt."""
    head, worktree = _repository_fingerprints(repo)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "provider": "repowise",
        "repowise_version": version,
        "source": source,
        "profile": profile,
        "completed": True,
        "head": head,
        "worktree_fingerprint": worktree,
        "artifact": ARTIFACT_PATH.as_posix(),
        "artifact_sha256": _sha256(repo / ARTIFACT_PATH),
        "state": STATE_PATH.as_posix(),
        "state_sha256": _sha256(repo / STATE_PATH),
        "synced_at": _utc_now(),
    }
    _write_json(repo / RECEIPT_PATH, receipt)


# EXPORTED FUNCTIONS / PUBLIC API


def runtime_platform() -> str:
    """
    @brief Return the supported native package platform identifier.
    @return ``windows-x64`` or ``linux-x64``.
    @exception RepoWiseError If the host is unsupported.
    """
    machine = platform.machine().lower()
    if machine not in {"amd64", "x86_64"}:
        raise RepoWiseError(f"unsupported RepoWise architecture: {machine}")
    if os.name == "nt":
        return "windows-x64"
    if sys.platform.startswith("linux"):
        return "linux-x64"
    raise RepoWiseError(f"unsupported RepoWise operating system: {sys.platform}")


def distribution_edition() -> str:
    """
    @brief Detect whether this WAEGIS distribution is Core or Complete.
    @return ``core`` or ``complete``.
    @exception RepoWiseError On an invalid edition override.
    """
    edition = os.environ.get("WAEGIS_EDITION", "").strip().lower()
    if not edition:
        edition = "complete" if locate_bundled_repowise(required=False) is not None else "core"
    if edition not in SUPPORTED_EDITIONS:
        raise RepoWiseError(f"invalid WAEGIS edition: {edition!r}")
    return edition


def locate_bundled_repowise(*, required: bool = True) -> Path | None:
    """
    @brief Locate the platform-native RepoWise bundle shipped by Complete.
    @param[in] required Raise when no bundle is found.
    @return Bundle root or ``None``.
    @exception RepoWiseError If required and unavailable.
    """
    candidates = []
    override = os.environ.get("WAEGIS_REPOWISE_BUNDLE")
    if override:
        candidates.append(Path(override))
    executable = Path(sys.argv[0]).resolve().parent
    candidates.extend(
        [
            executable / "repowise",
            Path(__file__).resolve().parent / "_bundled_repowise",
        ]
    )
    for candidate in candidates:
        if (candidate / BUNDLE_MANIFEST).is_file():
            return candidate.resolve()
    if required:
        raise RepoWiseError("this WAEGIS distribution does not contain bundled RepoWise 0.37.0")
    return None


def settings_from_answers(
    answers: Mapping[str, Any],
    *,
    default_source: str = "disabled",
    default_sync: bool = False,
) -> RepoWiseSettings:
    """
    @brief Parse strict RepoWise answers-file keys into validated settings.
    @param[in] answers Complete answers mapping.
    @param[in] default_source Source used when no explicit answer exists.
    @param[in] default_sync Synchronization default.
    @return Validated settings.
    @exception RepoWiseError On invalid types, values, or endpoints.
    """
    command_value = answers.get("repowise_external_command", [])
    if command_value:
        try:
            command_value = _normalize_command(command_value)
        except ValueError as exc:
            raise RepoWiseError(f"invalid repowise_external_command: {exc}") from exc
    elif not isinstance(command_value, list):
        raise RepoWiseError("repowise_external_command must be an array of command arguments")
    sync_value = answers.get("repowise_sync", default_sync)
    if not isinstance(sync_value, bool):
        raise RepoWiseError("repowise_sync must be true or false")
    settings = RepoWiseSettings(
        source=str(answers.get("repowise_source", default_source)),
        external_command=tuple(command_value),
        profile=str(answers.get("repowise_profile", "deterministic")),
        ollama_url=str(answers.get("repowise_ollama_url", "http://127.0.0.1:11434")),
        model=str(answers.get("repowise_model", "")),
        embedding_model=str(answers.get("repowise_embedding_model", "")),
        enforcement=str(answers.get("repowise_enforcement", "advisory")),
        sync=sync_value,
    )
    _validate_settings(settings)
    return settings


def lifecycle_repowise(
    repo: Path,
    answers: Mapping[str, Any],
    *,
    lifecycle: str,
    interactive: bool,
    asker: Any | None,
    stream: IO[str] | None,
    home: Path | None = None,
    yes: bool = False,
) -> dict[str, Any]:
    """
    @brief Resolve, configure, and optionally synchronize RepoWise after lifecycle success.
    @details ``--yes`` approval is intentionally outside this helper. The caller
             supplies the original interactive asker, so plan approval can never
             silently opt into RepoWise or a long indexing operation.
    @param[in] repo Successfully deployed AEGIS repository.
    @param[in] answers Loaded lifecycle answers.
    @param[in] lifecycle One of new, adopt, upgrade, or configure.
    @param[in] interactive Whether questions may be asked.
    @param[in] asker Unwrapped interactive asker.
    @param[in] stream Optional human output stream.
    @param[in] home Optional WAEGIS journal root override.
    @return Separate configuration and synchronization outcome.
    @exception RepoWiseError On invalid answers, configuration, or installation.
    """
    from .io.prompts import FieldSpec

    if interactive and asker is None:
        raise RepoWiseError("interactive RepoWise planning requires an asker")
    edition = distribution_edition()
    explicit_source = answers.get("repowise_source")
    source: str
    if explicit_source is not None:
        source = str(explicit_source)
    elif not interactive:
        source = "disabled"
    elif edition == "complete":
        bundle = locate_bundled_repowise()
        if bundle is None:
            raise RepoWiseError(
                "the complete edition should bundle RepoWise, but no bundled "
                "payload could be located"
            )
        manifest = _load_bundle_manifest(bundle)
        if stream is not None:
            stream.write(
                "RepoWise 0.37.0 provides offline structural repository discovery. "
                f"The bundled payload is about {manifest['packaged_size']} bytes and "
                f"uses {manifest['unpacked_size']} bytes unpacked.\n"
            )
        if asker.confirm("Install the bundled offline RepoWise structural index?", default=True):
            source = "bundled"
        elif asker.confirm("Link to an external RepoWise installation instead?", default=False):
            source = "external"
        else:
            source = "disabled"
    else:
        if stream is not None:
            stream.write(
                "This Core edition does not contain RepoWise. "
                "An external RepoWise 0.37.x command can still be linked.\n"
            )
        source = (
            "external"
            if asker.confirm("Link to an external RepoWise installation?", default=False)
            else "disabled"
        )
    if source == "bundled" and edition != "complete":
        raise RepoWiseError("bundled RepoWise requires the WAEGIS Complete edition")
    resolved = dict(answers)
    resolved["repowise_source"] = source
    if source == "external" and not resolved.get("repowise_external_command"):
        if not interactive or asker is None:
            raise RepoWiseError(
                "repowise_external_command is required when repowise_source is external"
            )
        resolved["repowise_external_command"] = asker.ask_field(
            FieldSpec(
                key="repowise_external_command",
                description="Command used to invoke the existing RepoWise 0.37.x installation.",
                example="repowise",
                validator=_normalize_command,
            )
        )
    if source != "disabled" and "repowise_profile" not in resolved and interactive:
        resolved["repowise_profile"] = asker.ask_field(
            FieldSpec(
                key="repowise_profile",
                description=(
                    "Deterministic uses structural indexing and the mock embedder; "
                    "Ollama may add local prose but AEGIS still imports structure only."
                ),
                default="deterministic",
                choices=("deterministic", "ollama"),
            )
        )
    if resolved.get("repowise_profile") == "ollama":
        if "repowise_ollama_url" not in resolved and interactive:
            resolved["repowise_ollama_url"] = asker.ask_field(
                FieldSpec(
                    key="repowise_ollama_url",
                    description="Loopback Ollama endpoint. Remote endpoints are rejected.",
                    default="http://127.0.0.1:11434",
                )
            )
        if "repowise_model" not in resolved and interactive:
            resolved["repowise_model"] = asker.ask_field(
                FieldSpec(
                    key="repowise_model",
                    description="Optional installed Ollama prose model name.",
                    default="",
                )
            )
        if "repowise_embedding_model" not in resolved and interactive:
            resolved["repowise_embedding_model"] = asker.ask_field(
                FieldSpec(
                    key="repowise_embedding_model",
                    description="Optional installed Ollama embedding model name.",
                    default="",
                )
            )
    settings = settings_from_answers(resolved)
    current = repowise_status(repo)
    configuration_planned = not (
        settings.source == "disabled" and current["mode"] == "disabled"
    )
    if configuration_planned and stream is not None:
        stream.write(
            "RepoWise plan: configure "
            f"source={settings.source}, enforcement={settings.enforcement}; "
            "indexing remains a separate decision.\n"
        )
    consent = mutation_consent(
        mutation_planned=configuration_planned,
        yes=yes,
        asker=asker if interactive else None,
        prompt="Apply this RepoWise configuration plan?",
    )
    if consent is not ConsentDecision.APPROVED:
        raise RepoWiseError(
            "RepoWise configuration was not approved"
            if consent is ConsentDecision.DECLINED
            else "RepoWise configuration requires explicit approval"
        )
    if settings.source == "disabled" and current["mode"] == "disabled":
        configured = {
            "source": "disabled",
            "mode": "disabled",
            "profile": settings.profile,
            "installation": None,
            "policy": str(repo / INTEGRATION_PATH),
            "runtime": (
                str(repo / RUNTIME_PATH)
                if (repo / RUNTIME_PATH).is_file()
                else None
            ),
            "changed": False,
        }
    else:
        configured = configure_repowise(repo, settings, home=home)
    explicit_sync = "repowise_sync" in answers
    if explicit_sync:
        sync_selected = settings.sync
    elif not interactive or source == "disabled":
        sync_selected = False
    else:
        default_sync = lifecycle == "adopt"
        if lifecycle in {"upgrade", "configure"}:
            default_sync = not repowise_status(repo).get("current", False)
        sync_selected = asker.confirm(
            "Initialize or refresh the RepoWise repository index now?",
            default=default_sync,
        )
    if source == "disabled" or not sync_selected:
        command = None if source == "disabled" else _resume_command(repo.resolve())
        if command and stream is not None:
            stream.write(f"RepoWise indexing was deferred. Start it with:\n{command}\n")
        return {
            "edition": edition,
            "aegis": "ok",
            "configuration": configured,
            "sync": {
                "ok": True,
                "action": "disabled" if source == "disabled" else "deferred",
                "resume_command": command,
            },
        }
    synchronized = sync_repowise(repo, stream=stream, home=home)
    return {
        "edition": edition,
        "aegis": "ok",
        "configuration": configured,
        "sync": synchronized.to_dict(),
    }


def configure_repowise(
    repo: Path,
    settings: RepoWiseSettings,
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    """
    @brief Configure RepoWise policy and execution metadata transactionally.
    @param[in] repo Target AEGIS repository.
    @param[in] settings Validated settings.
    @param[in] home Optional WAEGIS journal root override.
    @return Configuration and installation summary.
    @exception RepoWiseError On invalid configuration, apply, rollback, or cleanup.
    @exception KeyboardInterrupt Re-raised after rollback handling.
    @exception SystemExit Re-raised after rollback handling.
    """
    repo = _ensure_repo(repo)
    _validate_settings(settings)
    command: list[str] = []
    installation: dict[str, Any] | None = None
    if settings.source == "bundled":
        installation = install_bundled_repowise(repo)
        command = list(installation["command"])
    elif settings.source == "external":
        version = _command_version(settings.external_command, repo, home=home)
        if not version.startswith("0.37."):
            raise RepoWiseError(
                f"external RepoWise {version} is outside {REPOWISE_VERSION_SPEC}"
            )
        _validate_command_capabilities(
            settings.external_command,
            repo,
            home=home,
        )
        command = list(settings.external_command)
    runtime_base = {
        "schema_version": RUNTIME_SCHEMA,
        "source": settings.source,
        "command": command,
        "profile": settings.profile,
        "ollama_url": settings.ollama_url,
        "model": settings.model,
        "embedding_model": settings.embedding_model,
    }
    policy_path = resolve_managed_path(repo, INTEGRATION_RELATIVE_PATH)
    runtime_path = resolve_managed_path(repo, RUNTIME_PATH.as_posix())
    manifest_path = resolve_managed_path(repo, MANIFEST_RELATIVE_PATH)
    old_policy = policy_path.read_bytes() if policy_path.is_file() else None
    old_runtime = runtime_path.read_bytes() if runtime_path.is_file() else None
    old_manifest = manifest_path.read_bytes() if manifest_path.is_file() else None
    prior_runtime: dict[str, Any] | None = None
    if old_runtime is not None:
        try:
            candidate = json.loads(old_runtime.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            candidate = None
        if isinstance(candidate, dict):
            prior_runtime = candidate
    configured_at = _utc_now()
    if prior_runtime is not None and all(
        prior_runtime.get(key) == value for key, value in runtime_base.items()
    ):
        prior_timestamp = prior_runtime.get("configured_at")
        if isinstance(prior_timestamp, str):
            configured_at = prior_timestamp
    runtime = {**runtime_base, "configured_at": configured_at}
    policy_text = _integration_text(settings)
    policy_bytes = policy_text.encode("utf-8")
    runtime_bytes = (
        json.dumps(runtime, indent=2, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    updated_manifest = _updated_install_manifest(
        repo,
        settings,
        policy_sha256=hashlib.sha256(policy_bytes).hexdigest(),
    )
    manifest_bytes = (
        None
        if updated_manifest is None
        else (
            json.dumps(updated_manifest.to_dict(), indent=2, ensure_ascii=False)
            + "\n"
        ).encode("utf-8")
    )
    changed = (
        old_policy != policy_bytes
        or old_runtime != runtime_bytes
        or old_manifest != manifest_bytes
    )
    if not changed:
        return {
            "source": settings.source,
            "mode": settings.enforcement if settings.source != "disabled" else "disabled",
            "profile": settings.profile,
            "installation": installation,
            "policy": str(policy_path),
            "runtime": str(runtime_path),
            "changed": False,
        }
    transaction: FileTransaction | None = None
    try:
        transaction = FileTransaction.begin(
            repo,
            command="configure-repowise",
            paths=(
                INTEGRATION_RELATIVE_PATH,
                RUNTIME_PATH.as_posix(),
                MANIFEST_RELATIVE_PATH,
            ),
        )
        transaction.mark("applying")
        if old_policy != policy_bytes:
            _write_text(policy_path, policy_text)
        if policy_path.read_bytes() != policy_bytes:
            raise RepoWiseError("RepoWise policy verification failed after write")
        try:
            policy_document = tomllib.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            raise RepoWiseError("RepoWise policy verification failed after write") from exc
        if (
            policy_document.get("provider") != "repowise"
            or policy_document.get("schema_version") != INTEGRATION_SCHEMA
        ):
            raise RepoWiseError("RepoWise policy verification returned unexpected metadata")
        if old_runtime != runtime_bytes:
            _write_json(runtime_path, runtime)
        if runtime_path.read_bytes() != runtime_bytes or _load_json(runtime_path) != runtime:
            raise RepoWiseError("RepoWise runtime verification failed after write")
        if updated_manifest is not None and old_manifest != manifest_bytes:
            write_manifest(repo, updated_manifest)
        if manifest_bytes is not None and manifest_path.read_bytes() != manifest_bytes:
            raise RepoWiseError("RepoWise install-manifest verification failed after write")
        transaction.mark("verified")
        transaction.commit()
    except BaseException as exc:
        if transaction is not None and transaction.phase != "committed":
            try:
                transaction.rollback()
            except Exception as rollback_exc:
                note = (
                    "RepoWise configuration rollback failed; authenticated transaction "
                    f"{transaction.state['id']} was retained: {rollback_exc}"
                )
                if hasattr(exc, "add_note"):
                    exc.add_note(note)
                if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    raise
                raise RepoWiseError(note) from exc
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise RepoWiseError(
                f"RepoWise configuration failed; rollback succeeded: {exc}"
            ) from exc
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            if hasattr(exc, "add_note") and transaction is not None:
                exc.add_note(
                    "RepoWise configuration was committed; terminal transaction "
                    "cleanup will be retried by recovery"
                )
            raise
        if isinstance(exc, TransactionCleanupError) or (
            transaction is not None and transaction.phase == "committed"
        ):
            raise RepoWiseError(
                "RepoWise configuration committed successfully, but transaction "
                "cleanup failed; the next mutating invocation will retry cleanup"
            ) from exc
        if isinstance(exc, RepoWiseError):
            raise
        if isinstance(exc, TransactionError):
            raise RepoWiseError(f"RepoWise transaction could not begin: {exc}") from exc
        raise
    return {
        "source": settings.source,
        "mode": settings.enforcement if settings.source != "disabled" else "disabled",
        "profile": settings.profile,
        "installation": installation,
        "policy": str(policy_path),
        "runtime": str(runtime_path),
        "changed": True,
    }


def commit_repowise_configuration(
    repo: Path,
    runner: CommandRunner,
    *,
    message: str,
) -> bool:
    """
    @brief Commit only tracked RepoWise policy and install-manifest changes.
    @details New/adopt commit the AEGIS deployment before the separate RepoWise
             transaction. This helper creates a second narrow commit only when
             those two tracked files changed. Runtime, receipt, index, and tool
             files remain ignored and cannot enter the commit.
    @param[in] repo Target AEGIS repository.
    @param[in] runner Injectable command runner.
    @param[in] message Commit message.
    @return True when a commit was created; false when both paths were clean.
    @exception RepoWiseError If Git cannot inspect or commit the paths.
    """
    paths = (INTEGRATION_RELATIVE_PATH, MANIFEST_RELATIVE_PATH)
    status = runner.run(
        ("git", "-C", str(repo), "status", "--porcelain", "--", *paths),
        timeout=30,
    )
    if not status.ok():
        raise RepoWiseError(
            "cannot inspect RepoWise configuration changes: "
            + (status.combined_output().strip() or "git status failed")
        )
    if not status.stdout.strip():
        return False
    committed = runner.run(
        (
            "git",
            "-C",
            str(repo),
            "commit",
            "--only",
            "-m",
            message,
            "--",
            *paths,
        ),
        timeout=120,
    )
    if not committed.ok():
        raise RepoWiseError(
            "cannot commit RepoWise configuration: "
            + (committed.combined_output().strip() or "git commit failed")
        )
    return True


def install_bundled_repowise(repo: Path) -> dict[str, Any]:
    """
    @brief Install or verify the Complete edition's project-local sidecar.
    @details The runtime directory is copied to a sibling staging path, fully
             verified, then renamed. Failed staging never affects AEGIS.
    @param[in] repo Target repository.
    @return Installation summary including the project-relative command.
    @exception RepoWiseError On missing bundle, insufficient space, or drift.
    """
    repo = _ensure_repo(repo)
    bundle = locate_bundled_repowise()
    if bundle is None:
        raise RepoWiseError(
            "no bundled RepoWise payload could be located for installation"
        )
    manifest = _load_bundle_manifest(bundle)
    target = repo / TOOLS_PATH / runtime_platform()
    needed = int(manifest["unpacked_size"])
    free = shutil.disk_usage(target.parent if target.parent.exists() else repo).free
    if free < needed + max(64 * 1024 * 1024, needed // 10):
        raise RepoWiseError(
            f"insufficient disk space for RepoWise: need {needed} bytes plus reserve, have {free}"
        )
    if target.is_dir():
        try:
            current = _load_bundle_manifest(target)
            digest, size = _tree_digest(target)
            if (
                digest == current["tree_sha256"] == manifest["tree_sha256"]
                and size == current["unpacked_size"] == manifest["unpacked_size"]
                and current["source_sha256"] == manifest["source_sha256"]
            ):
                launcher = Path(str(current["launcher"]))
                return {
                    "status": "present",
                    "path": str(target),
                    "packaged_size": int(manifest["packaged_size"]),
                    "unpacked_size": needed,
                    "tree_sha256": digest,
                    "command": [(TOOLS_PATH / runtime_platform() / launcher).as_posix()],
                }
        except (OSError, KeyError, RepoWiseError) as verify_error:
            # A digest mismatch means drift and a re-install is intended; an
            # OSError here (e.g. permissions) would otherwise resurface later
            # as a confusing staging failure, so keep the reason.
            reinstall_reason = f"{type(verify_error).__name__}: {verify_error}"
        else:
            reinstall_reason = "installed tree does not match bundle manifest"
    else:
        reinstall_reason = None
    staging = target.with_name(f"{target.name}.partial-{uuid.uuid4().hex}")
    backup = target.with_name(f"{target.name}.backup-{uuid.uuid4().hex}")
    try:
        staging.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle, staging, symlinks=False)
        staged_manifest = _load_bundle_manifest(staging)
        if target.exists():
            os.replace(target, backup)
        os.replace(staging, target)
        if backup.exists():
            shutil.rmtree(backup)
    except (OSError, RepoWiseError) as exc:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if backup.exists() and not target.exists():
            os.replace(backup, target)
        detail = f"failed to install bundled RepoWise: {exc}"
        if reinstall_reason is not None:
            detail += f" (re-install triggered by: {reinstall_reason})"
        raise RepoWiseError(detail) from exc
    launcher = Path(str(staged_manifest["launcher"]))
    return {
        "status": "installed",
        "path": str(target),
        "packaged_size": int(staged_manifest["packaged_size"]),
        "unpacked_size": needed,
        "tree_sha256": staged_manifest["tree_sha256"],
        "command": [(TOOLS_PATH / runtime_platform() / launcher).as_posix()],
    }


def repowise_status(repo: Path) -> dict[str, Any]:
    """
    @brief Inspect RepoWise configuration, sidecar, and index freshness.
    @param[in] repo Target repository.
    @return JSON-safe status mapping.
    @exception RepoWiseError On malformed configuration.
    """
    repo = _ensure_repo(repo)
    policy_file = repo / INTEGRATION_PATH
    if not policy_file.is_file():
        return {
            "configured": False,
            "source": "disabled",
            "mode": "disabled",
            "profile": None,
            "installed": False,
            "index": "missing",
            "current": False,
        }
    try:
        with policy_file.open("rb") as handle:
            policy = tomllib.load(handle)
    except (tomllib.TOMLDecodeError, OSError, UnicodeError) as exc:
        raise RepoWiseError(
            f"RepoWise integration policy is unreadable or invalid TOML: {exc}"
        ) from exc
    expected = {
        "schema_version",
        "provider",
        "mode",
        "source",
        "version_spec",
        "artifact",
        "state",
        "require_head_match",
        "require_worktree_match",
    }
    if set(policy) != expected or policy.get("schema_version") != INTEGRATION_SCHEMA:
        raise RepoWiseError("RepoWise integration policy is not strict schema 1")
    if policy.get("provider") != "repowise":
        raise RepoWiseError("RepoWise integration provider must be repowise")
    if policy.get("mode") not in {"disabled", "advisory", "required"}:
        raise RepoWiseError("RepoWise integration mode is invalid")
    if policy.get("source") not in {"none", "bundled", "external"}:
        raise RepoWiseError("RepoWise integration source is invalid")
    if policy.get("version_spec") != REPOWISE_VERSION_SPEC:
        raise RepoWiseError(
            f"RepoWise integration version_spec must be {REPOWISE_VERSION_SPEC}"
        )
    if policy.get("artifact") != ARTIFACT_PATH.as_posix():
        raise RepoWiseError(
            f"RepoWise integration artifact must be {ARTIFACT_PATH.as_posix()}"
        )
    if policy.get("state") != STATE_PATH.as_posix():
        raise RepoWiseError(
            f"RepoWise integration state must be {STATE_PATH.as_posix()}"
        )
    for key in ("require_head_match", "require_worktree_match"):
        if type(policy.get(key)) is not bool:
            raise RepoWiseError(f"RepoWise integration {key} must be boolean")
    if policy["mode"] == "disabled" and policy["source"] != "none":
        raise RepoWiseError("disabled RepoWise integration requires source none")
    if policy["mode"] != "disabled" and policy["source"] == "none":
        raise RepoWiseError("enabled RepoWise integration requires a runtime source")
    runtime_file = repo / RUNTIME_PATH
    runtime = _load_json(runtime_file) if runtime_file.is_file() else {}
    if policy["mode"] != "disabled" and not runtime:
        raise RepoWiseError("enabled RepoWise integration lacks runtime metadata")
    command = _runtime_command(repo, runtime) if policy["mode"] != "disabled" else []
    installed = bool(command and (Path(command[0]).is_file() or shutil.which(command[0])))
    artifact_present = (repo / ARTIFACT_PATH).is_file()
    state_present = (repo / STATE_PATH).is_file()
    current = _receipt_current(repo)
    index = "current" if current else ("stale" if artifact_present and state_present else "missing")
    return {
        "configured": True,
        "source": policy["source"],
        "mode": policy["mode"],
        "profile": runtime.get("profile"),
        "installed": installed,
        "version_spec": policy["version_spec"],
        "index": index,
        "current": current,
        "artifact": str(repo / ARTIFACT_PATH),
        "receipt": str(repo / RECEIPT_PATH),
        "next": None if current or policy["mode"] == "disabled" else _resume_command(repo),
    }


def sync_repowise(
    repo: Path,
    *,
    stream: IO[str] | None = None,
    home: Path | None = None,
) -> RepoWiseSyncResult:
    """
    @brief Initialize, resume, or update RepoWise and record validated evidence.
    @param[in] repo Target repository.
    @param[in] stream Optional human progress stream; omitted for JSON callers.
    @param[in] home Optional WAEGIS journal root override.
    @return Synchronization result with log and resume command.
    @exception RepoWiseError On invalid or disabled configuration.
    """
    repo = _ensure_repo(repo)
    status = repowise_status(repo)
    if status["mode"] == "disabled":
        raise RepoWiseError("RepoWise is disabled; enable it with waegis configure")
    runtime = _load_json(repo / RUNTIME_PATH)
    command = _runtime_command(repo, runtime)
    version = _command_version(command, repo, home=home)
    if not version.startswith("0.37."):
        raise RepoWiseError(f"RepoWise {version} is outside {REPOWISE_VERSION_SPEC}")
    _validate_command_capabilities(command, repo, home=home)
    settings = RepoWiseSettings(
        source=str(runtime["source"]),
        external_command=(
            tuple(str(item) for item in runtime.get("command", []))
            if runtime["source"] == "external"
            else ()
        ),
        profile=str(runtime.get("profile", "deterministic")),
        ollama_url=str(runtime.get("ollama_url", "http://127.0.0.1:11434")),
        model=str(runtime.get("model", "")),
        embedding_model=str(runtime.get("embedding_model", "")),
        enforcement=str(status["mode"]),
    )
    _validate_settings(settings)
    action = _action_for(repo)
    if action == "no-op":
        return RepoWiseSyncResult(
            ok=True,
            action=action,
            message="RepoWise index is already current",
            log=None,
            resume_command=None,
            profile=settings.profile,
        )
    profile = settings.profile
    fallback = profile == "ollama" and not _ollama_available(
        settings.ollama_url,
        (settings.model, settings.embedding_model),
    )
    if fallback:
        profile = "deterministic"
        if stream is not None:
            stream.write("warning: loopback Ollama is unavailable; using deterministic indexing\n")
    arguments = _command_for(command, repo, action, settings, profile)
    log_directory = (
        home if home is not None else waegis_home()
    ) / "logs" / "repowise"
    log_directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_directory / f"{stamp}-{uuid.uuid4().hex[:6]}.jsonl"
    started = time.monotonic()
    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            arguments,
            cwd=repo,
            env=_offline_environment(settings, profile, home=home),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None, "Popen(stdout=PIPE) guarantees a stream"
        events: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(
            target=_pump_process_output,
            args=(process.stdout, events),
            daemon=True,
        )
        reader.start()
        with log_path.open("w", encoding="utf-8") as log:
            while True:
                try:
                    line = events.get(timeout=15)
                except queue.Empty:
                    if stream is not None:
                        stream.write(
                            f"repowise: heartbeat elapsed={int(time.monotonic() - started)}s\n"
                        )
                    if process.poll() is not None and not reader.is_alive():
                        break
                    continue
                if line is None:
                    break
                log.write(line)
                log.flush()
                message = _progress_message(line, time.monotonic() - started)
                if message and stream is not None:
                    stream.write(message + "\n")
            return_code = process.wait()
    except KeyboardInterrupt:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        return RepoWiseSyncResult(
            ok=False,
            action=action,
            message="RepoWise synchronization was interrupted",
            log=str(log_path),
            resume_command=_resume_command(repo),
            profile=profile,
            fallback=fallback,
        )
    except OSError as exc:
        return RepoWiseSyncResult(
            ok=False,
            action=action,
            message=f"cannot run RepoWise: {exc}",
            log=str(log_path),
            resume_command=_resume_command(repo),
            profile=profile,
            fallback=fallback,
        )
    if return_code != 0:
        return RepoWiseSyncResult(
            ok=False,
            action=action,
            message=f"RepoWise exited with status {return_code}",
            log=str(log_path),
            resume_command=_resume_command(repo),
            profile=profile,
            fallback=fallback,
        )
    try:
        _validate_generated_artifacts(repo)
        _write_receipt(
            repo,
            version=version,
            source=settings.source,
            profile=profile,
        )
    except (OSError, RepoWiseError) as exc:
        return RepoWiseSyncResult(
            ok=False,
            action=action,
            message=f"RepoWise output validation failed: {exc}",
            log=str(log_path),
            resume_command=_resume_command(repo),
            profile=profile,
            fallback=fallback,
        )
    return RepoWiseSyncResult(
        ok=True,
        action=action,
        message="RepoWise synchronization completed and artifacts were verified",
        log=str(log_path),
        resume_command=None,
        profile=profile,
        fallback=fallback,
    )


# END OF FILE
