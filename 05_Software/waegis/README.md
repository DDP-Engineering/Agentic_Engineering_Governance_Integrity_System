<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# WAEGIS 1.0

WAEGIS is the separate, stdlib-only guided wizard that analyzes, configures,
deploys, diagnoses, repairs, and upgrades compatible AEGIS payloads. It is never
copied into the target payload.

## Version Boundary

WAEGIS 1.0 supports AEGIS `>=2.0.0,<3.0.0`. AEGIS 1.x and cross-major upgrades
are rejected before mutation. Schema-2 workflow configurations are not migrated;
deploy a fresh AEGIS 2.x payload with schema 3.

## Commands

```text
waegis new TARGET [...]
waegis adopt TARGET [...]
waegis analyze --repo PATH [--json]
waegis configure --repo PATH [...]
waegis doctor --repo PATH [--json]
waegis repair --repo PATH [...]
waegis upgrade --repo PATH [...]
waegis version [--json]
```

Mutating commands support the existing dry-run, answers, non-interactive,
confirmation, JSON, and payload selection controls shown by `--help`. WAEGIS is
offline-first; subprocess access uses injectable runners.

## Schema-3 Configuration

WAEGIS generates and validates:

```toml
[interface]
stage_form_retention = "discard"
check_execution = "external"
```

It also handles independent `build`, `typecheck`, `lint`, `test`, and `security`
gate groups. Each group has `mode = "disabled"|"enforce"` and `commands = []`.
Disabled groups may retain commands; enforced groups require commands.

Repository analysis proposes commands only from explicit package scripts, tool
configuration, Make targets, or CI commands. It does not invent a security
command. Analyze/configure/doctor/new/adopt can inspect, configure, optionally
execute, and report the five groups in fixed order.

## Development

```powershell
uv sync --group dev
uv run --group dev python -m waegis --help
uv run --group dev python -m pytest -q tests
```

The install manifest and checkpoint journal retain their current version-1
layouts. Payload mutation is planned, previewed, journaled, verified, and
rollback-aware. WAEGIS remains independent from AEGIS runtime graph state.
