<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-PLAT-c820ce6c - Generate owner-aware validation configuration

## Behavior

WAEGIS performs one bounded, deterministic, dependency-pruned scan. It records
explicit conventional test directories and confidently detected co-located test
suites. Each suite is assigned to the nearest ancestor containing a recognized
project marker. A suite's configured working directory is that owner path,
relative to the governed repository, or `.` when the repository root owns it.

Detection is based on structured project files and bounded source signals, not
arbitrary prose. Supported command signals are:

| Ecosystem | Owner signal | Configured command |
|---|---|---|
| Python pytest | pytest configuration or pytest-style tests in a Python project | `python -m pytest` with owner-relative roots |
| Python unittest | Python project with unittest-style or otherwise conventional Python tests | `python -m unittest discover` per root |
| Node.js | `package.json` with a non-placeholder `scripts.test` | the detected lockfile runner's `test` command |
| Go | `go.mod` with bounded `*_test.go` evidence | `go test ./...` |
| Rust | `Cargo.toml` with a conventional test root or bounded `#[test]` evidence | `cargo test` |
| .NET | solution or project metadata with a conventional test project/root | `dotnet test` |
| Maven | `pom.xml` with a conventional test root | `mvn test` |
| Gradle | Gradle settings/build metadata with a conventional test root | `gradle test` |

Node.js runner precedence is `pnpm`, `yarn`, `bun`, then `npm`, selected from
the owning project or repository lockfile. Test commands remain guidance; WAEGIS
does not launch a target project's tools.

Suites with the same owner and command are combined. Independent suites receive
deterministic TOML-safe names. `[paths].tests` retains every discovered
repository-relative root once and in deterministic order. If a suite cannot be
classified confidently, WAEGIS preserves the existing reported fallback rather
than guessing a command from prose. If no existing suite is detected, the
shipped `.agentic/tests` unittest default remains unchanged.

Nested Git repositories, dependency directories, hidden directories, build
outputs, virtual environments, symlinks, and junctions remain outside the scan.

## Data / interface

The internal discovery result carries `roots`, `owner`, `framework`, `command`,
and `basis`. `render_config(target)` emits one `[validation.tests.<name>]` table
per combined suite with an argument-array `command` and a repository-relative
`working_directory`. No public CLI operation or project configuration schema is
added or changed.

## Examples

For `04_Software/VoiceApplication/tests` owned by
`04_Software/VoiceApplication/pyproject.toml` with pytest configuration:

```toml
[paths]
tests = ["04_Software/VoiceApplication/tests"]

[validation.tests.project]
command = ["python", "-m", "pytest", "tests"]
working_directory = "04_Software/VoiceApplication"
```

For independent `web/__tests__` and `service` Go tests, WAEGIS emits separate
Node.js and Go command tables with `web` and `service` working directories.

## Acceptance

- Nested Python configuration never silently changes its owner to repository
  root.
- Automated fixtures cover every ecosystem in the table and at least one
  repository containing multiple owners and languages.
- Duplicate suites, ambiguous ownership, excluded directories, and absent test
  evidence produce deterministic, safe results.
- Existing root-level pytest/unittest and no-test configuration remain
  compatible.
