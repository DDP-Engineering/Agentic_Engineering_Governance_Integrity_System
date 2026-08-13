#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2026 DDP Engineering
# SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
# -----------------------------------------------------------------------------
"""Inspect target identity/state and generate complete project configuration."""

from __future__ import annotations

import hashlib
import os
import re
import struct
import tomllib
from collections.abc import Iterator
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from waegis.domain.plans import PlanError, safe_relative

MAX_TEST_FILES_TO_INSPECT = 32
MAX_TEST_FILE_BYTES_TO_INSPECT = 64 * 1024
MAX_TEST_ROOT_DEPTH = 4
TEST_DISCOVERY_EXCLUDED_DIRECTORIES = frozenset(
    {
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "site-packages",
        "vendor",
        "venv",
    }
)
PYTEST_TEST_PATTERN = re.compile(
    rb"^[ \t]*(?:async[ \t]+)?def[ \t]+test_[A-Za-z0-9_]*[ \t]*\(",
    re.MULTILINE,
)


def resolve_target(value: str) -> Path:
    """Resolve one existing target directory without following later inputs."""
    target = Path(value).resolve()
    if not target.is_dir():
        raise PlanError("Target must be an existing directory")
    return target


def git_directory(target: Path) -> Path | None:
    """Resolve a normal Git directory or one standard linked-worktree pointer."""
    marker = target / ".git"
    if marker.is_dir():
        return marker.resolve()
    if not marker.is_file():
        return None
    try:
        text = marker.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None
    prefix = "gitdir:"
    if len(text.splitlines()) != 1 or not text.lower().startswith(prefix):
        return None
    value = text[len(prefix) :].strip()
    if not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = marker.parent / candidate
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError):
        return None
    if not resolved.is_dir() or not (resolved / "HEAD").is_file():
        return None
    return resolved


def _fingerprinted_files(target: Path) -> Iterator[tuple[Path, str]]:
    """Yield regular target files outside Git internals and recovery state."""
    for path in sorted(target.rglob("*"), key=lambda item: item.as_posix()):
        if not path.is_file():
            continue
        relative = path.relative_to(target).as_posix()
        if relative.startswith(".agentic/.runtime/"):
            continue
        if relative.startswith(".git/") and relative != ".git/info/exclude":
            continue
        yield path, relative


def _read_ignore_lines(path: Path) -> list[str]:
    """Read usable Git-ignore patterns without turning hints into prerequisites."""
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return []
    patterns: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith(r"\#"):
            line = line[1:]
        elif line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def _ignore_rules(target: Path) -> list[tuple[PurePosixPath, str]]:
    """Load repository-local ignore rules without invoking Git."""
    rules: list[tuple[PurePosixPath, str]] = []
    exclude = target / ".git/info/exclude"
    rules.extend(
        (PurePosixPath("."), pattern) for pattern in _read_ignore_lines(exclude)
    )
    ignore_files = sorted(
        (
            path
            for path in target.rglob(".gitignore")
            if path.is_file()
            and not path.relative_to(target).as_posix().startswith(".git/")
            and not path.relative_to(target)
            .as_posix()
            .startswith(".agentic/.runtime/")
        ),
        key=lambda path: (len(path.relative_to(target).parts), path.as_posix()),
    )
    for ignore_file in ignore_files:
        base_value = ignore_file.parent.relative_to(target).as_posix()
        base = PurePosixPath(".") if base_value == "." else PurePosixPath(base_value)
        rules.extend((base, pattern) for pattern in _read_ignore_lines(ignore_file))
    return rules


def _matches_ignore_pattern(
    relative: PurePosixPath, base: PurePosixPath, pattern: str
) -> bool:
    """Match common Git-ignore path, directory, glob, and anchored forms."""
    base_parts = () if base == PurePosixPath(".") else base.parts
    if relative.parts[: len(base_parts)] != base_parts:
        return False
    local_parts = relative.parts[len(base_parts) :]
    if not local_parts:
        return False
    directory_only = pattern.endswith("/")
    candidate_pattern = pattern.rstrip("/")
    anchored = candidate_pattern.startswith("/")
    candidate_pattern = candidate_pattern.lstrip("/")
    if not candidate_pattern:
        return False
    candidates = [
        PurePosixPath(*local_parts[:index])
        for index in range(1, len(local_parts))
    ]
    if not directory_only:
        candidates.append(PurePosixPath(*local_parts))
    if "/" in candidate_pattern or anchored:
        pattern_parts = PurePosixPath(candidate_pattern).parts
        return any(
            _match_ignore_parts(candidate.parts, pattern_parts)
            for candidate in candidates
        )
    return any(
        PurePosixPath(candidate.name).match(candidate_pattern)
        for candidate in candidates
    )


def _match_ignore_parts(
    path_parts: tuple[str, ...], pattern_parts: tuple[str, ...]
) -> bool:
    """Match one slash-containing ignore glob relative to its rule file."""
    if not pattern_parts:
        return not path_parts
    if pattern_parts[0] == "**":
        return _match_ignore_parts(path_parts, pattern_parts[1:]) or bool(
            path_parts
        ) and _match_ignore_parts(path_parts[1:], pattern_parts)
    if not path_parts or not fnmatchcase(path_parts[0], pattern_parts[0]):
        return False
    return _match_ignore_parts(path_parts[1:], pattern_parts[1:])


def ignored_target_paths(target: Path) -> list[str]:
    """Return existing repository-ignored files using only local rule files."""
    rules = _ignore_rules(target)
    ignored: list[str] = []
    for _path, relative in _fingerprinted_files(target):
        if (
            relative == ".gitignore"
            or relative.endswith("/.gitignore")
            or relative == ".git/info/exclude"
        ):
            continue
        state = False
        pure = PurePosixPath(relative)
        for base, raw_pattern in rules:
            negative = raw_pattern.startswith("!") and not raw_pattern.startswith(r"\!")
            pattern = raw_pattern[1:] if negative else raw_pattern
            if pattern.startswith(r"\!"):
                pattern = pattern[1:]
            if _matches_ignore_pattern(pure, base, pattern):
                state = not negative
        if state:
            ignored.append(relative)
    return ignored


def _git_index_hash_bytes(git_root: Path) -> int:
    """Return the configured object-id width without running Git."""
    common = git_root
    common_pointer = git_root / "commondir"
    if common_pointer.is_file():
        try:
            value = common_pointer.read_text(encoding="utf-8").strip()
            common = (git_root / value).resolve()
        except (OSError, UnicodeError, RuntimeError):
            return 20
    try:
        config = (common / "config").read_bytes()
    except OSError:
        return 20
    if re.search(rb"(?im)^\s*objectformat\s*=\s*sha256\s*$", config):
        return 32
    return 20


def _decode_index_v4_offset(data: bytes, position: int) -> tuple[int, int]:
    """Decode Git index-v4's prefix-removal variable integer."""
    if position >= len(data):
        raise ValueError
    byte = data[position]
    position += 1
    value = byte & 0x7F
    while byte & 0x80:
        if position >= len(data):
            raise ValueError
        byte = data[position]
        position += 1
        value = ((value + 1) << 7) | (byte & 0x7F)
    return value, position


def _tracked_target_paths(target: Path) -> set[str] | None:
    """Read tracked paths from the local Git index, failing closed on ambiguity."""
    git_root = git_directory(target)
    if git_root is None:
        return set()
    index_path = git_root / "index"
    if not index_path.exists():
        return set()
    try:
        data = index_path.read_bytes()
        signature, version, count = struct.unpack(">4sII", data[:12])
        if signature != b"DIRC" or version not in {2, 3, 4}:
            return None
        hash_bytes = _git_index_hash_bytes(git_root)
        position = 12
        previous = b""
        paths: set[str] = set()
        for _entry in range(count):
            entry_start = position
            flags_position = entry_start + 40 + hash_bytes
            if flags_position + 2 > len(data):
                return None
            flags = struct.unpack(">H", data[flags_position : flags_position + 2])[0]
            position = flags_position + 2
            if version >= 3 and flags & 0x4000:
                position += 2
            if version == 4:
                removed, position = _decode_index_v4_offset(data, position)
                if removed > len(previous):
                    return None
            else:
                removed = len(previous)
            terminator = data.find(b"\0", position)
            if terminator < 0:
                return None
            suffix = data[position:terminator]
            raw_path = previous[: len(previous) - removed] + suffix
            relative = raw_path.decode("utf-8", errors="strict")
            paths.add(safe_relative(relative))
            previous = raw_path
            if version == 4:
                position = terminator + 1
            else:
                entry_bytes = terminator + 1 - entry_start
                position = entry_start + ((entry_bytes + 7) // 8) * 8
        return paths
    except (OSError, UnicodeError, ValueError, struct.error, PlanError):
        return None


def target_fingerprint(target: Path) -> str:
    """Hash tracked and unignored bytes without invoking a Git process."""
    digest = hashlib.sha256()
    digest.update(os.fsencode(str(target)))
    ignored = set(ignored_target_paths(target))
    tracked = _tracked_target_paths(target)
    for path, relative in _fingerprinted_files(target):
        if relative in ignored and tracked is not None and relative not in tracked:
            continue
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            raise PlanError(f"Cannot inspect target path: {relative}") from exc
        digest.update(b"\0")
    digest.update(b"git=1" if git_directory(target) is not None else b"git=0")
    return f"sha256:{digest.hexdigest()}"


def ensure_output_outside(target: Path, output: str) -> Path:
    """Require the operator-owned plan output to remain outside the target."""
    path = Path(output).resolve()
    if path == target or path.is_relative_to(target):
        raise PlanError("Plan output must be outside the target repository")
    return path


def _safe_directory_within(target: Path, path: Path) -> bool:
    """Return whether a directory is real, non-linked, and inside the target."""
    try:
        if path.is_symlink() or os.path.isjunction(path) or not path.is_dir():
            return False
        return path.resolve().is_relative_to(target)
    except (OSError, RuntimeError):
        return False


def detected_test_roots(target: Path) -> list[str]:
    """Return conventional test roots from a bounded, pruned repository walk."""
    target = target.resolve()
    candidate_names = ("tests", "test")
    roots: set[str] = set()
    for directory, directories, _filenames in os.walk(target, followlinks=False):
        parent = Path(directory)
        relative_parent = parent.relative_to(target)
        parent_depth = 0 if relative_parent == Path(".") else len(relative_parent.parts)
        descend: list[str] = []
        for name in sorted(directories):
            path = parent / name
            child_depth = parent_depth + 1
            if (
                name.startswith(".")
                or name.casefold() in TEST_DISCOVERY_EXCLUDED_DIRECTORIES
                or not _safe_directory_within(target, path)
            ):
                continue
            if name in candidate_names:
                if child_depth <= MAX_TEST_ROOT_DEPTH:
                    roots.add(path.relative_to(target).as_posix())
                continue
            if child_depth < MAX_TEST_ROOT_DEPTH:
                descend.append(name)
        directories[:] = descend
    order = {name: index for index, name in enumerate(candidate_names)}
    return sorted(
        roots,
        key=lambda value: (
            len(PurePosixPath(value).parts),
            PurePosixPath(value).parent.as_posix().casefold(),
            order[PurePosixPath(value).name],
        ),
    )


def _nested_pytest_configuration(target: Path, roots: list[str]) -> str | None:
    """Return the first nearest pytest signal owned by a nested test project."""
    inspected: set[Path] = set()
    for root in roots:
        root_path = target / root
        conftest = root_path / "conftest.py"
        if conftest.is_file() and not conftest.is_symlink():
            relative = conftest.relative_to(target).as_posix()
            return f"{relative} is present"
        project = root_path.parent
        while project != target and project not in inspected:
            inspected.add(project)
            for name in ("pytest.ini", "conftest.py"):
                candidate = project / name
                if candidate.is_file() and not candidate.is_symlink():
                    relative = candidate.relative_to(target).as_posix()
                    return f"{relative} is present"
            pyproject = project / "pyproject.toml"
            try:
                project_text = (
                    pyproject.read_text(encoding="utf-8")
                    if pyproject.is_file() and not pyproject.is_symlink()
                    else ""
                )
            except (OSError, UnicodeError):
                project_text = ""
            if "[tool.pytest" in project_text:
                relative = pyproject.relative_to(target).as_posix()
                return f"{relative} contains a [tool.pytest] section"
            project = project.parent
    return None


def _matching_test_files(target: Path, roots: list[str]) -> Iterator[Path]:
    """Yield conventional Python test files without following directory links."""
    for root in roots:
        root_path = target / root
        for directory, directories, filenames in os.walk(root_path, followlinks=False):
            directories.sort()
            for filename in sorted(filenames):
                if not (
                    filename.endswith(".py")
                    and (
                        filename.startswith("test_") or filename.endswith("_test.py")
                    )
                ):
                    continue
                path = Path(directory) / filename
                if path.is_file() and not path.is_symlink():
                    yield path


def _detect_test_framework(
    target: Path, roots: list[str], project_text: str
) -> tuple[str, str]:
    """Choose a framework from configuration or a bounded source-text scan."""
    if (target / "pytest.ini").is_file():
        return "pytest", "pytest.ini is present"
    if (target / "conftest.py").is_file():
        return "pytest", "conftest.py is present"
    if "[tool.pytest" in project_text:
        return "pytest", "pyproject.toml contains a [tool.pytest] section"
    nested_configuration = _nested_pytest_configuration(target, roots)
    if nested_configuration is not None:
        return "pytest", nested_configuration

    unittest_basis: str | None = None
    for index, path in enumerate(_matching_test_files(target, roots)):
        if index >= MAX_TEST_FILES_TO_INSPECT:
            break
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_TEST_FILE_BYTES_TO_INSPECT)
        except OSError:
            continue
        relative = path.relative_to(target).as_posix()
        if b"unittest.TestCase" in content:
            if unittest_basis is None:
                unittest_basis = f"unittest.TestCase usage detected in {relative}"
            continue
        if PYTEST_TEST_PATTERN.search(content):
            return (
                "pytest",
                f"pytest-style test function or method detected in {relative}",
            )

    if unittest_basis is not None:
        return "unittest", unittest_basis
    if not roots:
        return "unittest", "no existing test root was detected"
    return (
        "unittest",
        "no pytest configuration or pytest-style test function or method was detected "
        "in the bounded test scan",
    )


def render_config(target: Path) -> tuple[bytes, list[str]]:
    """Generate immediately usable test paths and a shipped command default."""
    roots = detected_test_roots(target)
    warnings: list[str] = []
    pyproject = target / "pyproject.toml"
    try:
        project_text = (
            pyproject.read_text(encoding="utf-8") if pyproject.is_file() else ""
        )
    except (OSError, UnicodeError):
        project_text = ""
        warnings.append("pyproject.toml could not be inspected confidently.")
    test_framework, detection_basis = _detect_test_framework(
        target, roots, project_text
    )
    warnings.append(
        f"Selected {test_framework} test framework: {detection_basis}."
    )
    ruff_detected = (
        (target / "ruff.toml").is_file()
        or (target / ".ruff.toml").is_file()
        or "[tool.ruff" in project_text
    )
    if roots:
        tests = ", ".join(f'"{root}"' for root in roots)
    else:
        roots = [".agentic/tests"]
        tests = '".agentic/tests"'
        warnings.append("No existing test root was detected; using .agentic/tests.")
    validation: list[str] = []
    if test_framework == "pytest":
        validation.extend(
            [
                "[validation.tests.project]",
                'command = ["python", "-m", "pytest"]',
                'working_directory = "."',
                "",
            ]
        )
    else:
        for index, root in enumerate(roots, start=1):
            name = "project" if len(roots) == 1 else f"project_{index}"
            validation.extend(
                [
                    f"[validation.tests.{name}]",
                    'command = ["python", "-m", "unittest", '
                    f'"discover", "-s", "{root}"]',
                    'working_directory = "."',
                    "",
                ]
            )
    if ruff_detected:
        validation.extend(
            [
                "[validation.lints.ruff]",
                'command = ["python", "-m", "ruff", "check", "."]',
                'working_directory = "."',
                "",
            ]
        )
    text = f"""schema = 1
artifact_type = "project_config"

[paths]
requirements = ".agentic/requirements"
components = ".agentic/components"
tests = [{tests}]
adoptions = ".agentic/adoptions"
runs = ".agentic/runs"

{chr(10).join(validation)}
[policy]
risk_attention_threshold = "medium"
protected_scope_patterns = []
"""
    return text.encode("utf-8"), warnings


def configured_project_roots(config: bytes) -> tuple[str, ...]:
    """Return every safe project-owned root named by one AEGIS configuration."""
    try:
        data = tomllib.loads(config.decode("utf-8-sig"))
        paths = data["paths"]
        tests = paths["tests"]
        if not isinstance(paths, dict) or not isinstance(tests, list) or not tests:
            raise ValueError
        values = [
            paths["requirements"],
            paths["components"],
            *tests,
            paths["adoptions"],
            paths["runs"],
        ]
        if not all(isinstance(value, str) for value in values):
            raise ValueError
        return tuple(sorted({safe_relative(value) for value in values}))
    except (
        UnicodeError,
        tomllib.TOMLDecodeError,
        KeyError,
        TypeError,
        ValueError,
        PlanError,
    ) as exc:
        raise PlanError(
            "Existing .agentic/config.toml is invalid; it was preserved unchanged"
        ) from exc


def configured_run_pointer(config: bytes) -> tuple[str, str | None]:
    """Return repository and `.agentic/.gitignore` Run-pointer paths."""
    try:
        data = tomllib.loads(config.decode("utf-8-sig"))
        paths = data.get("paths", {})
        runs_root = paths.get("runs", ".agentic/runs")
        if not isinstance(runs_root, str):
            raise ValueError
        runs_root = safe_relative(runs_root)
    except (UnicodeError, tomllib.TOMLDecodeError, ValueError, PlanError) as exc:
        raise PlanError(
            "Existing .agentic/config.toml is invalid; it was preserved unchanged"
        ) from exc
    repository_pointer = (PurePosixPath(runs_root) / "context.toml").as_posix()
    try:
        relative_root = PurePosixPath(runs_root).relative_to(".agentic")
    except ValueError:
        return repository_pointer, None
    versioned_pointer = (relative_root / "context.toml").as_posix()
    return repository_pointer, versioned_pointer
