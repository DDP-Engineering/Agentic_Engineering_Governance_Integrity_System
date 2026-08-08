<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# WAEGIS 3

WAEGIS is the separate, standard-library-only wizard for analyzing,
configuring, installing, diagnosing, repairing, and upgrading AEGIS. WAEGIS is
not copied into a target repository.

WAEGIS 3.0.0 supports stable AEGIS payloads in `>=3.0.0,<4.0.0`. It preserves
the established package/import/command name `waegis`. WAEGIS 1 installations
are re-adopted through the normal conflict flow; their ownership metadata is
never trusted. AEGIS 2 and cross-major payloads are rejected before mutation.

WAEGIS 3 has one product shape. RepoWise, Core/Complete editions, cloning,
branch creation, staging, and commits are not part of it. `new` performs only
the Git initialization needed to create a repository. Operators review, stage,
and commit approved results themselves.

## Commands

```text
waegis new TARGET [...]
waegis adopt TARGET [...]
waegis analyze --repo PATH [--json]
waegis configure --repo PATH [...]
waegis check --repo PATH [--json]
waegis doctor --repo PATH [--json]
waegis repair --repo PATH [...]
waegis upgrade --repo PATH [...]
waegis version [--json]
```

`doctor` is an alias for `check`. Use `--help` on a command for its exact
options. Mutating commands accept `--dry-run`, `--yes`, `--non-interactive`,
`--answers`, `--json`, and `--break-lock` where applicable.

Examples:

```powershell
waegis analyze --repo D:\Source\project --json
waegis adopt D:\Source\project --answers answers.json --non-interactive --dry-run --json
waegis adopt D:\Source\project --answers answers.json --non-interactive --yes
waegis check --repo D:\Source\project
waegis repair --repo D:\Source\project --answers repair.json --non-interactive --yes
waegis upgrade --repo D:\Source\project --non-interactive --yes
```

`--dry-run` and all read-only commands write neither the repository nor the
runtime pointer. JSON mode writes one stable command envelope to stdout;
pre-mutation recovery evidence is flushed separately to stderr.

## Repository Safety

`adopt`, `configure`, `repair`, and `upgrade` require a clean Git repository.
WAEGIS rechecks cleanliness and the planned HEAD after acquiring its one
repository lock. There is no dirty-tree bypass.

Before its first repository write, WAEGIS prints and flushes an exact recovery
plan limited to the planned paths. Handled failures automatically run that
plan. If the process is killed after mutation, run the emitted commands before
retrying. Recovery uses explicit pathspecs after `--`; WAEGIS never performs a
broad repository clean.

The lock lives at the repository-specific path returned by Git for
`waegis-v3.lock`. `--break-lock` removes only a structurally valid lock whose
recorded local process is confirmed dead. Live, malformed, or unverifiable
locks fail closed.

## Ownership and the Install Manifest

WAEGIS writes `.agentic/install-manifest.json` only after the copied AEGIS
wrapper passes help, configuration validation, and coherent run-status smoke
checks. Manifest schema 2 records the exact payload identity and one initial
ownership class per path:

- `managed`: WAEGIS may repair or three-way-upgrade the file;
- `generated`: only `configure` may regenerate the file from owned answers;
- `seeded`: created only when absent, then repository-owned;
- `kept-local`: existing project bytes retained by an explicit decision;
- `sidecar`: payload bytes written beside a retained conflict for review.

The shipped generated workflow uses
`stage_form_retention = "latest"`; `configure` changes it only from an
explicit operator answer.

Repair touches only selected missing or drifted `managed` paths. Upgrade uses a
three-way comparison of the installed baseline, current bytes, and new payload.
Generated, seeded, kept-local, sidecar, requirements, component data,
knowledge, reports, run history, and workspace state are preserved.

An upgrade requires a valid WAEGIS 3 manifest and a strictly newer compatible
AEGIS 3 payload. Repositories without that manifest use `adopt`. For a detected
WAEGIS 1 installation, `adopt` requires an explicit migration answer and
reclassifies every path through ordinary conflict rules.

## Answers Files

Non-interactive operation accepts closed-schema JSON or TOML answers version
2. Unknown fields, stale conflict decisions, unsafe roots, and incomplete
conditional answers are rejected. A minimal JSON file is:

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

Repository analysis proposes values only from local evidence. It is read-only
and does not treat guessed commands as facts.

## Distribution Forms

One build produces three payload-equivalent artifacts:

```text
waegis.pyz
waegis-windows-x64.zip
waegis-linux-x64.tar.gz
release-manifest.json
SHA256SUMS
```

`waegis.pyz` requires a compatible Python 3.11+ interpreter. The two native
x64 bundles include locked CPython 3.13.13 and run without system Python. Each
native archive contains the exact published `waegis.pyz`; it does not contain a
second loose AEGIS payload tree.

Unpack a native bundle to a stable per-user or machine location before using
it. Run `waegis.cmd` on Windows or `./waegis` on Linux. Before a successful
mutating flow, the launcher-provided interpreter is atomically recorded at:

```text
WAEGIS_HOME/runtime-python
```

Installed AEGIS shell, PowerShell, and Node wrappers use that interpreter.
Moving or deleting the bundle makes the pointer invalid. `check` reports
`RUNTIME-POINTER-INVALID`; run a mutating command through the launcher at its
new stable location to repair the pointer. `AEGIS_PYTHON` remains the explicit
operator override and has precedence over the packaged runtime.

Artifacts contain a common payload digest and zipapp digest. Verify all files
before distribution:

```powershell
python packaging/build.py --verify --output dist
```

Checksums provide integrity, not publisher authenticity. Authenticity still
depends on the approved release channel.

## Building Releases

The runtime lock is closed and pins the exact upstream filename, URL, byte
size, SHA-256, Python version, target, and executable. An offline build uses
only already verified cache objects. An approved online builder may fetch only
the locked URLs:

```powershell
python packaging/build.py --fetch --output dist
python packaging/build.py --output dist
python packaging/build.py --verify --output dist
```

Use `--zipapp-only` for the Python-dependent artifact. Runtime downloads are
cached beneath `packaging/cache/` and are not committed. The Linux builder
materializes validated internal runtime links as regular files and excludes
the unused upstream `share/terminfo/` alias database. Unsafe, external,
broken, cyclic, special, duplicate, traversing, or case-colliding consumed
members fail the build. Final bundles contain no links or special members.

## Development

```powershell
uv sync --group dev
uv run --group dev python -B -m waegis --help
uv run --group dev python -m pytest -q tests
uv run --group dev ruff check packaging src tests
```

Runtime code is standard-library-only. Network access is not used by target
installation, analysis, configuration, health checking, repair, or upgrade.
The only supported network operation is an explicit `--fetch` on an approved
release builder for exact locked runtime inputs.
