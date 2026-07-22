<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS

Status: Draft / bootstrap.

This starter template provides a manual, tool-agnostic workflow for governed
feature and bugfix work with agentic development assistants. A natural prompt
such as "Implement feature X" should activate the bundled development skill.
The assistant then performs one disciplined gate at a time, records state and
evidence, asks clarification questions when needed, and waits for the human to
continue.

The template is intentionally generic. Project-specific facts live in
`.agentic/workflow.toml`; the workflow tools, skills, hooks, and invariant
checks stay reusable across languages and frameworks.

## Contents

- `template/.agentic/cli/src/aegis/` - the single-source Python CLI
  and deterministic workflow checks, delivered into target repositories and
  imported directly by this project's tests.
- `template/.agentic/hooks/` - standalone guardrail hook scripts (the runtime
  source of truth) invoked by the Codex, Claude Code, Pi, OpenCode, and Qwen
  Code adapters.
- `template/` - files copied into target repositories, including bundled
  `.agentic/cli/`, `.agentic/tools/`, `.agentic/hooks/`, `.agentic/skills/`
  (shared, platform-neutral skill procedures), `.codex/`, `.claude/`, `.pi/`,
  `.opencode/`, and `.qwen/` adapters, plus `CLAUDE.md`, `QWEN.md`, and
  `opencode.json`.
- `template/.pi/` - Pi adapter and Pi package. A TypeScript extension bridges Pi
  tool events to the same `.agentic/hooks/` guards, and `pi.skills` reuses the
  shared `.agentic/skills/` procedures with no duplication. See
  `template/.pi/README.md`.
- `template/.opencode/` and `template/opencode.json` - OpenCode adapter. A
  local plugin bridges OpenCode tool events to the same `.agentic/hooks/`
  guards, OpenCode skills wrap the shared `.agentic/skills/` procedures, and
  command prompts expose common workflow commands.
- `template/.qwen/` and `template/QWEN.md` - Qwen Code adapter. Native
  `settings.json` command hooks call the same `.agentic/hooks/` guards with no
  bridge code, `context.fileName` keeps `AGENTS.md` authoritative, Qwen skills
  wrap the shared `.agentic/skills/` procedures, and command prompts expose
  common workflow commands. See `template/.qwen/README.md`.
- `template/CHANGELOG.md` - starter changelog copied with each target project.
- `template/.agentic/documents/CLI_API_REFERENCE.md` - human-readable command
  API reference for the bundled workflow CLI, including examples, stages,
  skills, hooks, and written `.agentic` artifacts.
- `template/.agentic/documents/PROMPT_CHEATSHEET.md` - human operator prompt
  examples copied with the workflow.
- `template/.agentic/documents/WORKFLOW_CHEATSHEET.svg` - visual one-page
  workflow reference copied with the workflow.
- `tests/` - unit and fixture tests for the template itself, run against the
  single-source CLI under `template/.agentic/cli/src`.
- `../../00_Planning/PROMPT_CHEATSHEET.md` - planning reference copy of the
  prompt cheat sheet.

## Quick Start

From this folder, use the project dev dependency group so pytest and lint tools
come from the repository configuration instead of a global Python install:

```powershell
uv sync --group dev
```

Then run workflow commands:

```powershell
uv run --group dev python -m aegis config validate
uv run --group dev python -m aegis config show --effective --json
uv run --group dev python -m aegis start --kind feature --statement "Implement feature X" --scope-hint generated/client
uv run --group dev python -m aegis next
uv run --group dev python -m aegis alignment --source "human prompt" --understanding "Implement feature X." --scope "in: feature X; out: unrelated behavior" --acceptance "Feature X is covered by a passing check." --risk low --decision proceed --reason "No open questions and low risk"
uv run --group dev python -m aegis set-stage check --reason "Human-approved test revision"
uv run --group dev python -m aegis set-access-mode repo-wide --reason "Human-approved broad maintenance"
uv run --group dev python -m aegis supersede-evidence --id <old-evidence-id> --by <new-evidence-id> --reason "Passing rerun supersedes an external failure"
uv run --group dev python -m aegis requirement create --category functional --priority Must --requirement "Feature X behaves as specified." --rationale "Durable behavior contract." --verification "Inspection: inspect Feature X"
uv run --group dev python -m aegis requirement list --status Planned --json
uv run --group dev python -m aegis requirement activate --id <requirement-id> --linked-test <test-id> --verification "Automated test"
uv run --group dev python -m aegis working-tree audit
uv run --group dev python -m aegis status
uv run --group dev python -m aegis invariants
uv run --group dev python -m aegis audit traceability
uv run --group dev python -m aegis audit coverage
uv run --group dev python -m aegis impact
uv run --group dev python -m aegis report
```

`start` selects the new run for the current Git worktree by atomically writing
`.agentic/.workspace/state/current_run`. The entire `.agentic/.workspace/`
directory is ignored and must never be staged or copied between worktrees. The
retired `.agentic/current_run` path is not read as a fallback. Missing,
malformed, or stale state produces a stable `RUN-POINTER-*` message explaining
how to start or select a valid run.

Every graph-dependent leaf accepts `--run-id <existing-run-id>` after its
complete subcommand path, for example `status --run-id ...`,
`gates run --run-id ...`, and `requirement activate --run-id ...`. Explicit
selection wins over the worktree pointer and never rewrites it. Repository-wide
commands such as `config`, `audit`, `impact`, `working-tree audit`, and
`requirement create/show/list/update` reject the option.

Repeat `--scope-hint` to record the intended run scope for reviewers and later
workflow stages. Hints are persisted in the run intent and journal, but never
authorize paths outside an explicit `[guardrails.scope]` policy.

In a target repository, copy the files under `template/` into the repo root,
then configure the complete schema-version-2 `.agentic/workflow.toml`. Every
repository restriction has an explicit mode; disabled/unrestricted modes use
empty rule collections, while active modes require their rules. Validate the
file with `aegis config validate` and inspect normalized behavior with
`aegis config show --effective` before starting governed work. The shared skill procedures live
once under `.agentic/skills/`. For Codex-compatible workflows, `.codex/skills/`
provides thin adapters that point to them. For Claude Code workflows,
`CLAUDE.md` points back to `AGENTS.md` and `.claude/skills/` provides matching
thin adapters around the same shared skills. For Pi workflows, `.pi/` ships a
bridge extension plus a Pi package whose `pi.skills` reuses the same shared
skills directly (`pi install ./.pi`, then trust the project); see
`template/.pi/README.md`. For OpenCode workflows, `opencode.json` and
`.opencode/` provide project config, a default `aegis` primary agent,
native skill wrappers, command prompts, and a local guard plugin; start OpenCode
from the repository root. Plain `opencode run` uses the workflow agent, and
`opencode run --command workflow-status` exposes the workflow command shortcuts
from the CLI. For Qwen Code
workflows, `QWEN.md` points back to `AGENTS.md` and `.qwen/` provides native
command-hook bindings, thin skill wrappers, and command prompts; start Qwen Code
from the repository root and trust the project. Qwen hook matchers cover both
friendly tool aliases and raw write/shell identifiers across supported builds;
see `template/.qwen/README.md`.
The template also includes a `.agentic/knowledge/components/` component
knowledge convention for new or materially changed software components.
The `agentic-adoption` skill guides existing-project adoption through
repo-discovery, component-map approval, single-component component-adoption,
baseline-review, and adoption-delivery without application behavior changes.

Every agent-facing procedure begins with `config validate --json` and
`config show --effective --json`, reports all effective restriction modes and
active rule counts, and identifies the selected worktree run or explicit
`--run-id`. AEGIS policy remains separate from host/platform safety.

Use WAEGIS to preview and deploy the bundled AEGIS payload into a new project:

```powershell
waegis new D:\Path\To\NewProject --dry-run
waegis new D:\Path\To\NewProject
```

For an existing repository, use the adoption workflow:

```powershell
waegis adopt D:\Path\To\ExistingRepo --dry-run
waegis adopt D:\Path\To\ExistingRepo
```

WAEGIS resolves adoption conflicts explicitly, writes the install manifest,
configures the repository, and verifies the deployment. The deployed payload
includes `.agentic/` (with the shared `.agentic/skills/` procedures),
`.codex/`, `.claude/`, `.pi/`, `.opencode/`, and `.qwen/` adapters, `AGENTS.md`,
`CLAUDE.md`, `QWEN.md`, `opencode.json`, and `CHANGELOG.md`. Adoption artifacts such as
`.agentic/components.toml`,
`.agentic/knowledge/components/`, and `.agentic/reports/adoption/` are included.
The `.pi/` adapter's install-on-demand `node_modules/` is excluded. WAEGIS is a
separate lifecycle tool and is not copied into the deployed payload.

The copied project can run the bundled CLI immediately:

```powershell
.\.agentic\tools\run.ps1 --help
```

```bash
bash .agentic/tools/run.sh --help
```

For a project-local virtual environment, run:

```powershell
.\.agentic\tools\install.ps1
```

```bash
bash .agentic/tools/install.sh
```

The install scripts prefer `uv` when available and fall back to standard
`venv`/`pip`. Python 3.11 or newer is required. The current CLI has no
third-party runtime dependencies.

## Manual Gate Model

The default workflow stages are:

1. `intake`
2. `alignment`
3. `requirement`
4. `check`
5. `implementation`
6. `validation`
7. `delivery`

Adoption runs use the adoption-specific stages `adoption-intake`,
`adoption-alignment`, `repo-discovery`, `component-map`, `component-adoption`,
`baseline-review`, and `adoption-delivery`. Use `agentic-adoption` when an
existing project needs a component map or when a feature/fix targets a component
below `baseline-usable`.

The assistant should stop at each gate and summarize current state, changed
artifacts, evidence, unmet invariants, and suggested next prompts. Hooks provide
guardrails and evidence capture, but deterministic CLI checks remain the source
of truth.

Intent Alignment is a first-class stage before requirement/spec work. The
assistant records its understanding, scope, assumptions, acceptance target, open
questions, risk, and proceed/pause decision with `aegis alignment`.
The record is stored in the active `graph.json`, appended to `journal.jsonl` as
`alignment.recorded`, and shown in `status` and generated reports. The
`[alignment]` section in `.agentic/workflow.toml` controls whether the stage is
enabled and when open questions, risk, or protected planned paths force a pause
decision. When automated continuation is acceptable, questions can include
recommended responses that state what the agent will assume without waiting for
a human reply. The template stays tracker-neutral and does not post comments.

## Component Documentation Support

The bundled workflow includes component documentation support for repositories
that adopt the template:

- `write-component-documentation` creates or updates component pages under
  `.agentic/knowledge/components/`.
- `agentic-adoption` maps existing components and records baseline readiness
  before behavior-changing work touches legacy areas.
- `documentation-audit` checks changed implementation files against relevant
  component pages by default. Broad README, overview, setup, and validation docs
  are reviewed only when explicitly requested or when their scope changes.
- `python-codestyle-audit` reviews Python style expectations when Python files
  changed.

The installable template provides
`.agentic/knowledge/components/component_template.md`. Repositories using
`stage_restricted` write access must include their component-documentation paths
in the relevant stage lists; the unrestricted template has no implicit zones.

Component ownership patterns use the workflow's shared path matcher. A bare
directory entry in `.agentic/components.toml`, such as `src/package/billing`,
covers that directory and its complete subtree; explicit `/**` patterns remain
supported, and similarly named sibling directories are not included.

## Access Modes

Workflow runs start in `standard` access mode. When
`guardrails.write_access.mode = "stage_restricted"`, the write guard applies the
current stage's complete configured path list. Under `unrestricted`, it does not
resolve a run merely to authorize a write.

For broad maintenance tasks, a human may explicitly start or switch a run to
`repo-wide` access mode with a reason. Under stage-restricted policy this
bypasses stage lists, but never bypasses configured protected paths. It does not
override external filesystem, sandbox, approval, or operating-system controls.

## Evidence And Delivery Corrections

Workflow evidence is append-only by default. If a validation or implementation
failure is later proven to be an environment, command, or operator issue, record
the passing rerun and use `supersede-evidence` to mark the old failure as
non-blocking while preserving history.

When evidence includes `failure_kind`, generated reports render the
classification after the result, for example `test-run/fail (env): ...`.
Current graphs persist change units as an id plus touched paths and do not carry
the unused defect collection. Older graph files containing legacy
`change_units[].evidence` or top-level `defects` keys remain readable; those
retired keys are ignored when loaded.

Use `set-stage` when the human routes work back to an earlier gate. Use
`requirement activate` after linked checks pass so durable requirement
snapshots do not remain `Planned`. Supplied linked-test identifiers replace the
complete current set and must resolve before the TOML snapshot is updated; a
rejected activation names the identifier and reason and leaves the file
unchanged. Manual-only activation uses an explicit `Manual:` or `Inspection:`
verification method.

Run-local spec and check identifiers are unique: `add-spec` and `add-check`
reject an identifier already stored in the active graph without modifying it.

`working-tree audit` reports untracked files separately. Arbitrary local files,
such as notes or saved messages, are advisory by default. Delivery preflight
blocks only active configured protected paths, blocked patterns under
`[guardrails.working_tree]`, configured secret matches, adoption-source policy,
or other blocking preflight findings.

## Regression And Traceability Support

Durable requirements live in `.agentic/requirements/` as one complete TOML
snapshot per UUIDv4-backed requirement. Use `requirement list` before creating
a requirement, keep the same ID for revisions of the same behavioral contract,
and use `requirement update` to replace complete linked-test or affected-path
sets. The workflow tools read the canonical files directly to:

- verify linked tests resolve;
- prevent `Active` requirements without verification;
- detect coverable source files without requirement coverage;
- maintain a waiver ratchet for legacy modules;
- map changed files to impacted requirements and linked tests.

When `impact` receives no explicit paths, it uses the same Git-status parser as
`working-tree audit`. Renames contribute both the current and previous path, and
Git-quoted paths are decoded consistently.

Before delivery, run:

```powershell
python -m aegis audit traceability
python -m aegis audit coverage
python -m aegis delivery-preflight
```

No generated requirement registry or cache exists. Traceability, coverage,
impact, reports, invariants, and delivery preflight build any reverse mappings
in memory from the current TOML snapshots.
