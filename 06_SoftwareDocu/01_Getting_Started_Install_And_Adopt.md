<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Getting Started: Installing and Adopting AEGIS

This note is for someone who has never run AEGIS before and needs to get it
into a repository for the first time. It answers one question: "how do I
actually get AEGIS running here?"

## The two real starting points

AEGIS itself never installs itself. A separate, stdlib-only tool called
WAEGIS does that job: it copies the AEGIS payload into a repository,
interviews you for the repository-specific configuration, and writes the
result. There are exactly two WAEGIS commands that get AEGIS into a
repository for the first time:

| You have... | Run | What it does |
| --- | --- | --- |
| A brand-new, empty (or not-yet-created) project | `waegis new TARGET` | Creates `TARGET`, optionally runs `git init` or clones a remote, copies the AEGIS payload in, and interviews you for the workspace configuration. |
| An existing repository with its own source and history | `waegis adopt TARGET` | Copies the AEGIS payload into the existing repository, resolving any file conflicts with your existing content one file at a time, and interviews you for the configuration, seeded from an automatic read-only analysis of the repository. |

Both commands are one linear sequence of small, resumable steps: check the
machine (OS, disk space, Python, Git, Node), confirm prerequisites, set up the
repository, copy the payload, generate `workflow.toml`, optionally run the
configured quality gates, verify the result, and hand off. If a run is
interrupted, re-running the same command resumes from the first unfinished
step rather than starting over.

There is no third WAEGIS command for "AEGIS is already installed here." If
`adopt` detects a current or older AEGIS payload already present, it stops
and tells you to run `waegis doctor` (same version, diagnose/repair) or
`waegis upgrade` (move to a newer compatible payload) instead.

## Before you start

- Python 3.11 or newer, and Git 2.30 or newer, must be on `PATH`. WAEGIS
  checks for both and tells you exactly what is missing; it never installs
  privileged software itself.
- Node 18 or newer is recommended: every AEGIS guard hook runs through Node.
  Its absence only warns — it does not block installation — but hooks will
  not run for the affected host adapters until Node is available.
- Run WAEGIS itself with any Python 3.11+ interpreter. It has no third-party
  runtime dependencies.

## Running `new`: a brand-new project

```text
waegis new TARGET
```

`TARGET` is the directory to create. Interactively, WAEGIS walks you through:

- confirming the machine prerequisites above;
- your Git identity, if none is configured globally (recorded repository-local
  instead, only if you supply it);
- whether to `git init` a fresh repository or clone one from a URL you supply;
- the same workspace interview `adopt` uses: source/test roots, the primary
  implementation language, the five optional quality gates (build, typecheck,
  lint, test, security — each independently disabled, advisory, or enforced),
  and whether the alignment stage is enabled;
- optional RepoWise discovery (see below) — initial indexing defaults to
  **No** for `new`;
- an initial commit.

## Running `adopt`: an existing repository

```text
waegis adopt TARGET
```

`TARGET` must already be a Git work tree. `adopt` differs from `new` in three
ways:

1. It first checks whether AEGIS is already installed and routes you to
   `doctor` or `upgrade` instead when appropriate.
2. It runs a **read-only analysis** of the repository first — proposing
   source/test roots, the primary language, and gate commands with their
   provenance (which file each proposal came from) — and asks you to confirm
   or override each proposed answer. Nothing from the analysis is ever
   applied automatically.
3. Copying the payload can hit real conflicts: a payload file (for example
   `AGENTS.md`) may already exist in your repository with different content.
   For every such conflict you choose, file by file: **keep-local** (keep
   yours, ignore the payload version), **take-payload** (overwrite with the
   payload), or **write-new** (keep yours untouched and write the payload
   version alongside it as `<file>.new`). Nothing you own is ever silently
   overwritten.

RepoWise initial indexing defaults to **Yes** for `adopt` (the opposite of
`new`) — an existing repository usually benefits immediately from discovery
context. At the end, `adopt` offers to commit the changes on a dedicated
branch (`chore/aegis-adoption` by default) separate from your own work; you
can decline and commit it yourself later.

`adopt` finishes by printing the exact operator prompt to hand to your agent
tool to start the in-repo adoption workflow (`adoption-intake` →
`adoption-alignment` → `repo-discovery` → `component-map` →
`component-adoption` → `baseline-review` → `adoption-delivery`) — this is
where component mapping, requirement discovery, and the adoption baseline
actually happen, entirely inside AEGIS rather than WAEGIS.

## Command-line flags that apply to both

| Flag | Meaning |
| --- | --- |
| `--answers <file>` | A TOML or JSON file that pre-supplies interview answers, so the run does not need to prompt for everything interactively. |
| `--dry-run` | Show the plan and stop; nothing is changed. |
| `--non-interactive` | Never prompt. Every required answer must come from `--answers`; a missing one fails loudly, listing every missing key at once rather than one at a time. |
| `--yes` | Approve the rendered mutation plan without an interactive confirmation. It does **not** decide RepoWise source/indexing or accepting a failing quality gate — those always need an explicit answer or an interactive confirmation. |
| `--json` | Emit one machine-readable JSON result instead of human-readable console output. |
| `--payload <path>` | Use an explicit payload directory instead of the one WAEGIS ships with (mainly for development/testing of AEGIS itself). |

A programmatic call that supplies `--non-interactive` and `--json` without an
interactive asker, and without `--yes`, returns a `needs-input` result rather
than guessing — it never silently picks defaults for mutating decisions.

## Core vs. Complete, and RepoWise

WAEGIS ships as two editions, chosen when you download it (not by a
command-line flag):

| Edition | What it includes |
| --- | --- |
| **Core** | The WAEGIS wizard and the AEGIS payload. RepoWise defaults to disabled. It can still link to an already-installed, external RepoWise `>=0.37.0,<0.38.0` command. |
| **Complete** | Everything Core has, plus a separate, pinned, offline RepoWise 0.37.0 runtime it can install directly into the target repository as a project-local sidecar. |

RepoWise is optional discovery tooling: it analyzes the repository structure
and can propose additional context AEGIS may use during `repo-discovery`. It
is never authoritative — AEGIS independently validates whatever RepoWise
produces before using it, and disabling it entirely changes nothing about
whether AEGIS itself works.

During the interview, the RepoWise-related answer is one of:

| `repowise_source` | Meaning |
| --- | --- |
| `disabled` (default unless you choose otherwise) | No RepoWise integration at all. The repository stays fully self-contained: a plain `git clone` reproduces everything. |
| `external` | Links to a RepoWise command already installed on the machine. The command itself is not stored in the repository — a fresh clone on another machine must re-link it. |
| `bundled` | Complete edition only. Installs the pinned RepoWise runtime under `.agentic/tools/repowise/0.37.0/<platform>/`. That runtime is excluded from Git, so a Git clone alone will not carry it — only a full copy of the working directory, or re-running the Complete installer, restores it. |

Inspect or (re-)synchronize RepoWise explicitly at any time, independent of
`new`/`adopt`:

```text
waegis repowise status --repo "<project>"
waegis repowise sync --repo "<project>"
```

## Installing without WAEGIS

WAEGIS is the supported, tracked installation path: it writes the install
manifest that later lets `doctor`, `repair`, and `upgrade` reason about what
was installed and detect drift. There is a manual fallback for the rare case
where you cannot run WAEGIS at all: copy the contents of the AEGIS `template/`
directory directly into your repository, then run the copied
`.agentic/tools/install.ps1` / `install.sh` (installs a local virtual
environment) or `.agentic/tools/run.ps1` / `run.sh` (runs the CLI directly,
no virtual environment) to get a working `aegis` command. You would then hand
-write `.agentic/workflow.toml` yourself instead of answering an interview,
and there would be no install manifest to detect drift or support a future
`waegis upgrade`. This path exists mechanically, but it forgoes everything
WAEGIS otherwise gives you for free — treat `new`/`adopt` as the normal way
in, and this only as a last resort.

## What happens next

Once `new` or `adopt` finishes, AEGIS itself is installed and configured but
has not done any governed work yet. The command prints the exact next prompt
to give your agent tool, sourced from the copied
`.agentic/documents/PROMPT_CHEATSHEET.md`. Every interview answer this section
described — gates, alignment, scope, RepoWise source — remains editable
afterward through `.agentic/workflow.toml`; none of it is a one-time,
install-only choice.
