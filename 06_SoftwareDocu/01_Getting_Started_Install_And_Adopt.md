<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Getting Started: Installing and Adopting AEGIS 3

AEGIS does not install itself. WAEGIS 3 is the separate, standard-library-only
wizard that deploys the generic AEGIS 3 payload, generates the repository
configuration, validates the copied CLI, and writes an ownership-aware install
receipt. WAEGIS itself is never copied into the repository.

## Choose the entry point

| Starting point | Command | Contract |
|---|---|---|
| An absent target path | `waegis new TARGET` | Creates the directory, runs `git init`, installs AEGIS, and leaves staging/commit decisions to the operator. |
| A clean existing Git repository | `waegis adopt TARGET` | Analyzes local evidence, resolves every differing path explicitly, installs AEGIS, and preserves unrelated project bytes. |

WAEGIS does not clone repositories. Clone with Git first, then use `adopt`.
It never creates a branch, stages files, or commits. `new` rejects an existing
directory, including an empty one; `adopt` rejects a missing target, a non-root
Git path, a repository without HEAD, and every dirty-tree shape.

For an existing WAEGIS 3 installation, use `check`, `configure`, `repair`, or
`upgrade`. A detected WAEGIS 1 receipt is not an upgrade baseline: use `adopt`,
explicitly acknowledge migration, and resolve ordinary per-path conflicts.
WAEGIS 1 ownership data is never trusted.

## Prerequisites and distribution choices

Git is an external prerequisite. Node is required only for host adapters that
use the Node bridge; `check` reports its absence as an actionable warning.

Choose one WAEGIS artifact:

- `waegis.pyz` requires a compatible Python 3.11+ interpreter;
- `waegis-windows-x64.zip` includes locked CPython for Windows x64;
- `waegis-linux-x64.tar.gz` includes locked CPython for Linux x64.

Unpack a native bundle to a stable location and run `waegis.cmd` (Windows) or
`./waegis` (Linux). The first successful mutating flow atomically records the
selected interpreter at `WAEGIS_HOME/runtime-python`, allowing the installed
AEGIS shell, PowerShell, and Node wrappers to work without system Python.
Moving or deleting the bundle invalidates the pointer. `check` diagnoses it;
run a mutating command through the launcher at its new stable location to
repair it.

All target workflows are offline. Only an approved release builder using the
explicit packaging `--fetch` option may retrieve the exact locked CPython
archives.

## Preview, then install

Start with analysis for an existing repository:

```powershell
waegis analyze --repo D:\Source\project --json
```

Preview without writes:

```powershell
waegis new D:\Source\new-project --answers answers.json --non-interactive --dry-run --json
waegis adopt D:\Source\project --answers answers.json --non-interactive --dry-run --json
```

Apply the complete reviewed plan:

```powershell
waegis new D:\Source\new-project --answers answers.json --non-interactive --yes
waegis adopt D:\Source\project --answers answers.json --non-interactive --yes
```

Interactive operation asks only conditional questions that affect the chosen
configuration. Non-interactive operation uses a closed answers-version-2 JSON
or TOML document and reports every missing key together. Unknown answers and
stale conflict decisions are errors.

A minimal JSON file is:

```json
{
  "answers_version": 2,
  "answers": {
    "language": "python",
    "source_roots": ["src"],
    "test_roots": ["tests"]
  }
}
```

The interview covers repository roots and the explicitly WAEGIS-owned subset
of schema-3 policy. Advanced/operator-owned TOML remains under repository
control. Analysis proposes values only from observed files and records the
reason for each proposal; it does not invent build or security commands.

## Conflict and consent behavior

For every differing destination during `adopt`, choose exactly one action:

- `keep-local`: keep project bytes and record project ownership;
- `take-payload`: install the AEGIS bytes after recovery evidence is durable;
- `sidecar`: keep project bytes and write the AEGIS version beside them for
  review.

There is no global overwrite default. A sidecar name includes the WAEGIS
version and is collision-safe.

Mutating commands render the complete plan before consent. `--yes` approves
that rendered plan; it does not fill missing answers or conflicts.
`--non-interactive` never prompts, and `--json` emits one stable result envelope
to stdout. `--dry-run` needs no consent and is byte-for-byte read-only.

## Clean-tree recovery

`adopt`, `configure`, `repair`, and `upgrade` require a clean repository both
before planning and after lock acquisition. Before its first repository write,
WAEGIS prints and flushes exact path-scoped Git recovery commands. Handled
failures execute them automatically. If the process is killed after mutation,
run the preprinted commands, then rerun with `--break-lock` only when the lock's
recorded process is confirmed dead.

Recovery uses only the planned tracked/new paths. It never resets a branch,
performs a broad clean, or removes unrelated ignored files. WAEGIS 3 does not
create `.agentic/.waegis-transactions/` or store backup copies in the target.

## Installation receipt and ownership

The final `.agentic/install-manifest.json` uses schema 2. It is published only
after the copied AEGIS wrapper passes `--help`, `config validate --json`, and a
coherent fresh `run status --json` result. Each payload path receives one
initial disposition: `managed`, `generated`, or `seeded`. Explicit conflict
outcomes may add `kept-local` and `sidecar` records.

This receipt is the authority boundary for later maintenance:

- `check` is read-only and reports manifest, drift, wrapper, hook, adapter,
  Node, configured-root, payload-version, and runtime-pointer findings;
- `configure` changes only explicitly owned workflow policy;
- `repair` restores only approved `managed` paths;
- `upgrade` performs an ownership-aware three-way comparison against a
  strictly newer compatible AEGIS 3 payload.

Requirements, specifications, component knowledge, reports, run history,
workspace state, generated policy, seeded files, and retained conflicts are not
treated as generic managed payload.

After any successful mutation, inspect `git status`, review the exact bytes,
then stage and commit them using the repository's normal process.

## RepoWise boundary

RepoWise is not a WAEGIS 3 feature or installation option. AEGIS retains an
optional external/manual discovery policy, but WAEGIS does not install,
configure, synchronize, or lifecycle-manage RepoWise. Any future automation is
a separate tool and cannot supply authoritative AEGIS governance state.

## Manual fallback

The template can be copied manually and run through
`.agentic/tools/run.ps1`/`run.sh`, but a manual copy has no WAEGIS schema-2
manifest. It therefore gives up tracked ownership, drift diagnosis, repair, and
safe upgrade. Use `new` or `adopt` for the supported maintained installation.
