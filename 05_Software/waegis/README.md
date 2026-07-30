<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# WAEGIS 1.1

WAEGIS is the separate, stdlib-only guided wizard that analyzes, configures,
deploys, diagnoses, repairs, and upgrades compatible AEGIS payloads. It is never
copied into the target payload.

## Version Boundary

WAEGIS 1.1 supports AEGIS `>=2.0.0,<3.0.0`. AEGIS 1.x and cross-major upgrades
are rejected before mutation. Schema-2 workflow configurations are not migrated;
deploy a fresh AEGIS 2.x payload with schema 3.

## Core and Complete Editions

- **Core** contains the normal WAEGIS/AEGIS payload and defaults RepoWise to
  disabled.
- **Complete** adds a separate native RepoWise 0.37.0 runtime with locked
  dependencies, exact corresponding source, hashes, AGPL and third-party
  notices, SBOM, manifest, and size metadata.

Complete installs its selected sidecar beneath
`.agentic/tools/repowise/0.37.0/<platform>/`. Target installation and managed
indexing do not download packages or contact GitHub, PyPI, telemetry, or update
services. Core can still link an external RepoWise `>=0.37.0,<0.38.0`.

## Commands

```text
waegis new TARGET [...]
waegis adopt TARGET [...]
waegis analyze --repo PATH [--json]
waegis configure --repo PATH [...]
waegis doctor --repo PATH [--json]
waegis repair --repo PATH [...]
waegis upgrade --repo PATH [...]
waegis repowise status --repo PATH
waegis repowise sync --repo PATH
waegis version [--json]
```

Every mutating invocation uses one approval contract. `--yes` explicitly
approves the displayed mutation plan. Without it, a human command may ask
through its live console; programmatic calls without an asker, `--json`, and
`--non-interactive` return `needs-input` before transaction recovery, journal
creation, target creation, branch creation, or file writes. A no-op plan and
`--dry-run` need no approval; dry runs remain read-only. Standalone
`repowise sync` follows the same rule and accepts `--yes` and
`--non-interactive`. WAEGIS is offline-first; subprocess access uses injectable
runners.

`clone_url` accepts the existing HTTPS, SSH, SCP-style, `file://`, and local
path forms, but rejects empty non-optional values, control characters, and any
value whose first non-whitespace character is `-`. Clone execution uses
`git clone -- <repo> <dir>`, and credential-bearing URLs are sanitized before
reporting. Adoption and upgrade branch names share Git-compatible ref
validation: empty, option-like, control-character, traversal-like, reserved,
and otherwise invalid ref names are rejected before branch creation.

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

## RepoWise Lifecycle

Interactive `new`, `adopt`, and `upgrade` offer bundled RepoWise when running
Complete, otherwise an external link; `configure` changes RepoWise only when
RepoWise answers are explicitly supplied. `--yes` never chooses a RepoWise
source or indexing action: those choices must be interactive or present in the
answers file. Any resulting RepoWise configuration plan is displayed and
covered by explicit approval, while indexing remains a separate decision.
Non-interactive execution defaults to disabled unless the answers file
explicitly supplies:

```toml
repowise_source = "disabled" # disabled | bundled | external
repowise_external_command = ["repowise"]
repowise_profile = "deterministic" # deterministic | ollama
repowise_ollama_url = "http://127.0.0.1:11434"
repowise_model = ""
repowise_embedding_model = ""
repowise_enforcement = "advisory" # advisory | required
repowise_sync = false
```

Only loopback Ollama URLs are accepted. Missing Ollama or requested models cause
a warning and deterministic fallback. A failed index does not roll back the
successful AEGIS deployment or sidecar configuration; output includes the log
and exact `waegis repowise sync --repo "<project>"` resume command.

RepoWise is advisory discovery input, never authoritative AEGIS workflow state.
WAEGIS writes a versioned receipt; AEGIS independently validates the graph,
state, hashes, Git HEAD, and worktree fingerprint before using proposals.

The default disabled Core policy remains part of the normal AEGIS deployment
commit. When `new` or a committed `adopt` explicitly selects bundled or
external RepoWise, WAEGIS records the mutable policy and its install-manifest
digest in a second, narrow `Configure RepoWise via WAEGIS 1.1.0` commit. Runtime,
receipt, index, and tool files remain ignored. An adoption deliberately left
uncommitted keeps this policy change with the operator's other pending changes.

## Release Packaging

Core retains:

```text
waegis-windows-x64.zip
waegis-linux-x64.tar.gz
waegis.pyz
```

Native Complete builds add:

```text
waegis-complete-windows-x64.zip
waegis-complete-linux-x64.tar.gz
```

The bundled RepoWise sidecar uses its own pinned Python 3.12.13 runtime.
WAEGIS Core retains its existing Python 3.13 runtime. This separation is
required because RepoWise 0.37.0 locks NumPy 1.26.4, which has native Python
3.12 wheels but no Python 3.13 wheels.

Build one native Complete artifact from a clean exact RepoWise 0.37.0 checkout:

```powershell
python packaging/build_release.py --repowise-source D:\Source\repowise
```

Run the builder natively on each target OS and combine the publication
artifacts. Release production may populate pinned build caches; target
installation never compiles or resolves dependencies. Complete-to-Core use is
refused while a project selects the bundled runtime; configure it to external
or disabled first.

## Development

```powershell
uv sync --group dev
uv run --group dev python -m waegis --help
uv run --group dev python -m pytest -q tests
```

The install manifest and checkpoint journal retain their current version-1
layouts. Payload mutation is planned, previewed, journaled, verified, and
rollback-aware. WAEGIS remains independent from AEGIS runtime graph state.
