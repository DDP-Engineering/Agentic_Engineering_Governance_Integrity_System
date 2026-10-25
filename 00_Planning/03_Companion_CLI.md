<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 03 - The companion CLI

The implemented companion is one standard-library Python file:
`.agentic/aegis.py`. It requires Python 3.11 or newer and is invoked from
the target project's root after payload installation:

```text
python .agentic/aegis.py <command>
```

The maintainer source checkout has no root `.agentic/` deployment. Its canonical
CLI is `05_Software/aegis/template/.agentic/aegis.py`; installed-path examples
here are for downstream projects, not a request to install AEGIS in this checkout.

It scaffolds files, writes the journal state the agent decides, reads durable
records, runs configured project commands, and reports findings. It never
judges whether a stage's work is done, infers approval, commits, pushes,
creates a pull request, or itself accesses the network. Configured project
commands may have side effects or require services; their execution semantics
remain those of the target repository.

## Implemented commands

| Command | Read/write boundary | Use |
|---|---|---|
| `init [--git]` | Creates missing data folders/config and each missing context scaffold, preserves existing project files, refreshes managed root digests, and maintains the managed anchor/evolution block in the root `.gitignore`. | Finish installation or upgrade. |
| `task <title> [--type] [--parent]` | Writes a new journal; a bare task ID as the title is refused. | Start governed feature, fix, change, or adoption work. |
| `advance <task> [--to] [--path] [--skipped]` | Writes the header stage, Done checklist, one Log line and the State, then prints the summary block and any notes. | A stage's work is finished, skipped, or must return to an earlier stage. |
| `pause <task> --next [--blocked]` | Writes the State as waiting or blocked, then prints the summary block and any notes. | A checkpoint, a blocking question, or the end of a session. |
| `log <task> <text>` | Appends one dated, stage-prefixed Log line. | A durable decision, verification result, discovery, blocker or deviation. |
| `ruling <task> --decision --reason --source [--supersedes]` | Appends the next numbered Ruling. | A settled scope, behavior or technical question that later sessions must not reopen. |
| `verdict <task> [--spec] [--quality] [--round]` | Writes the review verdicts and round into the State; refused while explicit review is disabled. | Validate, after each explicit review round. |
| `req <category> <title>` | Writes a new requirement scaffold. | Add a durable behavior contract. |
| `anchor --task` | Writes/replaces the active anchor JSON. | Capture the known starting point before implementation. |
| `evolution --task [--json] [--compact]` | Writes the matching evolution JSON. | Compare current repository state with the active anchor. |
| `status [task] [--all] [--json]` | Read-only. | List journals or inspect one task. |
| `brief <task>` | Read-only deterministic bounded resume view. | First when resuming a task. |
| `summary <task>` | Read-only print of the recorded State. | When the current snapshot is needed; `advance`, `pause` and `verdict` print it after writing. |
| `components` | Read-only title-and-path catalogue of component knowledge pages. | Choose which concise component page to inspect. |
| `check [--task] [--strict] [--run] [--full] [--json]` | Read-only unless `--run` executes configured commands. | Advisory governance feedback or CI proof. |
| `test [name] [--impacted] [--no-fallback] [--dry-run] [--base] [--task]` | Runs one configured command; `--task` appends its result. A preview or fallback refusal runs no command and writes no test evidence. | Inspect selection, run focused build checks, or retain consolidated verification evidence. |
| `report <task>` | Appends a dated delivery report to the journal. | At the end of validate, once the evidence is final and before `advance` to `done`. |
| `diagram [--component] [--task] [--out]` | Read-only unless `--out` writes the Mermaid text. | Inspect requirement coverage. |
| `trace [--format {md,csv}] [--out PATH]` | Read-only unless `--out` writes the export. | Export the requirement register with coverage and ownership. |
| `explain <path>` | Read-only. | Find requirements and journals governing a file or folder. |

`python .agentic/aegis.py --help` and each command's `--help` are the
authoritative syntax reference. `.agentic/CLI.md` gives the full contract,
examples, output rules, and exit behavior.

Use `test` without `--task` for ordinary inner-loop retries. Supply `--task`
only when that individual run is the durable consolidated red, focused green,
or final verification result the journal should retain. The option records
every invocation it receives; it does not decide whether a run is material or
deduplicate retries. Generated tasks, requirements and context files omit the
payload license header and marked template-only authoring notes while retaining
their data fields; existing records are never rewritten by scaffolding.

`task "<title>"` creates a new journal and returns its ID/path. A bare task ID
as the title is refused with a pointer to `brief`, so resuming never opens a
second journal. The journal writers own the header stage, Done checklist, Log,
Rulings and `## State`; the agent edits Frame, Requirement coverage and Design
with file tools. The writers record the agent's decision and never judge
whether a stage's work is done: unticked checklist items, review verdicts not
both approved at `done`, an empty stage section at a stop, a Log line that
belongs to a later stage and a record an edit put out of shape print notes,
never refusals. Malformed input, such as an unknown stage or an empty `--next`,
exits 1 and writes nothing.

## Resume commands are complementary

`brief` and `summary` are intentionally different:

| Command | Output | What it is for |
|---|---|---|
| `brief TASK-<id>` | Task identity, stage, path, branch/base, parent, requirements, context paths/presence, checklist, State, outcome, interaction mode, review policy, diagrams, active rulings, visible children, Read next and details pointer. | Bounded re-entry, then reading what Read next names. |
| `summary TASK-<id>` | The recorded State: reported stage and result, current stage, requirements, changes, evidence, issues, next action, user need, review fields and details pointer. | The current snapshot; `advance`, `pause` and `verdict` print it after writing. |

Both commands are deterministic reads of durable files. Neither runs tests,
consults Git, writes state, proves that the candidate is still valid, or grants
authority. A truncation/stale marker means read the full journal.

Every session ends with `advance` or `pause`. The reply starts with the block
they print, copied in a text fence with its Details and truncation markers and
never written by hand. Exit zero does not mean every field was present.
Checklist verification and evidence interpretation remain the agent's
responsibility; these views do not validate those claims.

Context lists `.agentic/context/project.md` and `.agentic/context/environment.md`
as `present` or `not recorded`. Brief reads neither body and creates nothing.
Presence establishes the file's existence, not its accuracy or completeness.
Read the profile and relevant environment sections, then follow selected
component, requirement, source and test links. Legacy projects may omit either
file. The full fixed output order is documented in `.agentic/CLI.md`.

## Component catalogue

`components` accepts no arguments and prints one bounded printable title and
lexical repository-relative path per `.agentic/knowledge/*.md` page in
deterministic path order. It uses the first level-one heading or the filename
stem when a heading is absent. It interprets no body metadata, creates no
index, performs no automatic routing, and writes nothing. Unreadable pages,
link escapes, resolution loops, and non-printable catalogue paths fail through
the bounded CLI error path without partial output.

## Configuration-backed execution

`test` runs the named `[commands]` entry (default `test`). With
`--impacted`, it uses the selected requirement-linked tests; with an empty
selection or no `test_impacted` command, it falls back to the full suite and
states why unless `--no-fallback` was requested. That option requires
`--impacted` and exits 1 before execution when selection is unavailable.
`--base HEAD` limits impact selection to uncommitted work.

`--dry-run` prints the selected command and working directory without executing
or appending a journal result. Exit zero means the preview succeeded, not that
tests passed. Combined with `--no-fallback`, unavailable selection still exits 1.

Unsupported selector suffixes, including names with spaces, quotes or Unicode,
are discarded in favor of the validated test file. Duplicate references to a
broadened file become one argument. Unsafe or repository-escaping file paths
are not interpolated. AEGIS does not translate test frameworks: the configured
runner must honor both file references and any supported exact selectors.
Paths containing spaces still need a native project command.

Build uses focused native commands or verified impacted routing. The instructions
schedule full strict verification after final edits and review, avoiding a separate
full `test` immediately beforehand. Environment preparation uses project-owned
readiness checks and the environment guide's canonical references. Configured
commands, paths and timeouts remain authoritative in `aegis.toml`.

`check --run` executes eligible plain `[commands]` entries. Template
commands containing `{` and reserved `timeout`/`workdir` keys are always
skipped. Side-effect-looking command names are skipped unless `[check] run`
explicitly allows them. `[timeouts]` and `[commands] timeout` bound command duration. A
timed-out command proves nothing; a command that completes unsuccessfully is a
`command-failed` error.

## Governance checks

`check` currently implements 22 checks. They cover:

- requirement parsing, IDs, journal headers, and specification references;
- path coverage, linked tests, stale paths, scope drift, and source/test
  relationship;
- secrets in added diff lines, self-contained requirement prose, unticked
  items left at the former `deliver` stage, layout, stage zones, and
  configuration shapes;
- anchor/evolution evidence, configured-command completion, timeouts, and
  empty `--run` execution;
- manual verification declarations, enabled explicit-review evidence, and
  anchor/evolution sidecar tracking against `[records] commit_fingerprints`.

The default diff base is the configured `[layout] default_branch`, then
`origin/HEAD`, then local `master` or `main`. Without Git or a merge base,
diff-derived checks emit a NOTE while non-diff checks continue.

Plain `check` remains advisory even when it prints findings. `check --strict`
exits non-zero for errors and warning slugs listed in `[check] strict_promote`;
`--strict` implies complete finding output. Usage/configuration errors and
`test` command failures also return non-zero because the requested command
itself could not complete.

## Installation and upgrade

Install by copying the release payload to `<repo>/.agentic/`, then run:

```text
python .agentic/aegis.py init
```

Plain `init` does not create a Git repository. `init --git` does so only
when explicitly requested. An upgrade replaces the 18 managed payload files,
preserves repository-owned context, records and `aegis.toml`, and then reruns
`init` to refresh root digests. Review the repository diff before any commit.

`init` creates `context/project.md` and `context/environment.md` independently
from their managed Markdown templates only when absent. Existing bytes, including
empty files, are preserved. Scaffolds provide headings, not inferred project
facts. Populate current facts during frame/adoption and reconcile affected
sections as implementation or setup changes. History stays in task/Git records.

Machine-readable JSON is available for `anchor`, `evolution`, `status`,
and `check`. Each emits one schema-versioned document on stdout; `check
--run` sends command progress to stderr so stdout remains parseable.
`trace` exports Markdown (default) or CSV, not JSON. For evolution,
`--compact --json` returns paths, statuses and areas without before/after hashes;
the saved evidence remains complete. Ordinary JSON output is unchanged.

## Separate host operations

The integrations expose twelve shared operations. These are adapter interfaces,
not additional Python CLI subcommands. OpenCode and Pi register native
`aegis_*` tools; Qwen and Claude expose them through local stdio MCP; Codex uses
a command bridge.

| Operation | Behavior and boundary |
|---|---|
| `status` | Read task state and tracked verification state. |
| `resume` | Read `brief`, check branch alignment and remember a session-local task pointer. |
| `read` | Read the installed contract, CLI reference, configuration, step or journal. |
| `summary` | Read the recorded State; no fresh proof. |
| `check` | Run static checks, optionally strict, without configured tests. |
| `scaffold` | Coordinator creates a task or requirement scaffold. |
| `evidence` | Coordinator invokes `anchor`, `evolution` or `report`. |
| `journal` | Coordinator records `advance`, `pause`, `log`, `ruling` or `verdict` through the installed CLI, which never judges whether a stage is done. |
| `candidate` | Fingerprint the Git-visible candidate for comparison. |
| `diff` | Read Git status/diff and untracked paths; inspect untracked contents separately. |
| `run` | Coordinator starts tracked final validation or a named configured test command. |
| `job` | Read progress/results or, with coordinator authority and exact ID, cancel a job. |

`run` returns promptly with a job ID. For `kind: validate`, the detached worker
runs `check --task ID --strict --run --json`; `kind: test` selects a configured
command name, never arbitrary shell text supplied to the adapter. Poll `job`
until completion and inspect the full result and candidate comparison. A
static check, successful job submission or exit zero with a changed candidate
does not establish final proof.

For impacted `kind: test` runs, `no_fallback: true` forwards `--no-fallback`.
`kind: validate` rejects selection overrides. The evidence operation accepts
`compact: true` only for evolution. The Codex bridge spells these options
`--no-fallback` and `--compact`. They are opt-in and require a supporting
payload; default calls keep compatibility with older payloads. Preview directly
through the payload CLI rather than creating a verification job.

For example, from a complete installed Codex plugin:

```text
node <absolute-plugin-root>/scripts/aegis.mjs status --root <absolute-repository-root>
```

Each Codex invocation is stateless. Supply task IDs explicitly for task-scoped
operations. Its `--role reviewer` guard refuses mutations and cancellation but
does not authenticate the caller or replace host permissions.

## Host entry points and setup

OpenCode, Pi and Qwen provide `/aegis-start`, `/aegis-resume`, `/aegis-status`,
`/aegis-check` and `/aegis-validate`. Claude uses the namespaced equivalents
`/aegis:start`, `/aegis:resume`, `/aegis:status`, `/aegis:check` and
`/aegis:validate`. Codex uses the `aegis:aegis` skill and bridge rather than
these five slash commands. Native command dispatch differs by host; prompt
commands may invoke the host's configured model.

From an extracted complete package, use `node setup.mjs install`,
`node setup.mjs doctor`, `node setup.mjs update` or `node setup.mjs uninstall`.
The Windows/POSIX launchers call the same setup code. These commands manage the
host installation separately from the repository's core payload; consult the
[package guide](../06_SoftwareDocu/Agent_Plugins.md) for host-specific options.
No installer supplies credentials or chooses a model for another user.
