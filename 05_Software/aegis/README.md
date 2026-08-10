<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS package

This directory develops and tests the AEGIS runtime from the exact source tree
delivered to repositories:

```text
template/.agentic/aegis/cli/src/aegis/
```

The repository-level `pyproject.toml` points its editable package and test
imports at that tree. There is no second development copy of the runtime.

## Current version 1 protocol foundation

The runnable foundation provides:

- one registry containing the complete 56-operation AEGIS/WAEGIS protocol
  catalog, product ownership, CLI inputs, help metadata, and executor bindings;
- the 48-operation AEGIS command catalog with mechanically derived flat command
  tokens and no aliases;
- working `help-show` and `version-show` use cases, including complete bounded
  exact-operation help with arguments, result, and one minimal example;
- human output and the version 1 one-line JSON response envelope;
- structured protocol errors and documented exit classes without traceback
  output;
- injected clock, UUIDv4, and SHA-256 services;
- installed Git-repository discovery, with every explicit `--repo` validated;
  and
- atomic single-file replacement through a flushed temporary sibling and
  `os.replace`.

The remaining AEGIS catalog operations are intentionally unavailable at this
foundation stage. Invoking one returns `capability_unavailable` with exit code
4 when its declared arguments are valid. Missing, unknown, or malformed
arguments return structured `invalid_input`; catalog presence is not
represented as implemented behavior.

## Development

From this directory:

```powershell
uv run --group dev python -m pytest -q tests
uv run --group dev ruff check .
uv run --group dev python -B -m aegis --help
uv run --group dev python -B -m aegis --format json version-show
```

Runtime dependencies are limited to the Python standard library. Pytest,
Ruff, setuptools, and uv are development or packaging tools only.

## Public commands in this foundation

```text
aegis help-show
aegis help-show --operation run.create
aegis version-show
aegis --format json version-show
aegis --repo C:\path\to\installed-project version-show
```

Global options precede the flat command. Machine mode writes exactly one
compact UTF-8 JSON object plus LF to standard output and keeps standard error
empty after the protocol starts. Omitting `--repo` keeps package-level help and
version available before project configuration exists; supplying it requests
installed-repository validation and never gets ignored.
