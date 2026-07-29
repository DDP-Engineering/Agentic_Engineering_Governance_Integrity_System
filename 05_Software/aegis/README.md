<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# AEGIS 2.0

AEGIS is the offline-first, project-local Agentic Engineering Governance &
Integrity System. The runnable Python package is embedded under
`template/.agentic/cli/src/aegis/`; tests import that exact shipped source.

## Contract

- standard stages: intake, alignment, requirement, design, check,
  implementation, validation, delivery;
- stage lifecycle: prepare, optional add, apply, explicit human close;
- strict configuration/run graph schema 3 with no schema-2 migration;
- file-first forms for intent, requirements, checks, evidence, and stage control;
- authoritative run-local `design.md` and blocking design invariant;
- external or managed red-before-green check evidence;
- deterministic build, typecheck, lint, test, and security gates, all optional;
- consolidated impact/gates/invariants/traceability/coverage/working-tree
  verification before human diff review;
- no outward Git/publication action when delivery closes.

The top-level CLI groups are exactly `run`, `stage`, `requirement`, `check`,
`evidence`, `verify`, `delivery`, `adoption`, and `config`. Global options are
`--run` and `--json`.

## Development

```powershell
uv sync --group dev
uv run --group dev python -m aegis --help
uv run --group dev python -m pytest -q tests
```

Typical workflow:

```text
aegis config validate
aegis run start feature
# edit returned intake form
aegis stage apply
aegis stage close
```

Repeat prepare/apply/close through delivery. Use `stage add` for requirement and
check collections, `check prepare/record` or `check run` for evidence, and
`verify run` at validation.

## Template

Everything under `template/` is copied verbatim into downstream projects:

- `.agentic/` — CLI, workflow configuration, forms/state conventions, guards,
  shared skills, requirements, component knowledge, documents, and wrappers;
- `.codex/`, `.claude/`, `.pi/`, `.opencode/`, `.qwen/` — thin host adapters
  around shared state, hooks, and skills;
- `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `opencode.json` — host entry points;
- `CHANGELOG.md` — deliberately empty downstream starter.

Project-specific policy belongs in schema-3 `.agentic/workflow.toml`. The
default interface is `discard` retention plus `external` check execution; all
five gates ship disabled.

WAEGIS 1.0 is the recommended deployment/configuration tool and supports AEGIS
`>=2.0.0,<3.0.0`. It remains outside the copied payload.

See `template/.agentic/documents/CLI_API_REFERENCE.md` and
`template/.agentic/documents/How_To_Start_A_New_Project.md`.
