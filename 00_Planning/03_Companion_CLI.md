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
the repository root:

```text
python .agentic/aegis.py <command>
```

It scaffolds files, reads durable records, runs configured project commands,
and reports findings. It does not advance a journal stage, infer approval,
commit, push, create a pull request, or itself access the network. Configured
project commands may have side effects or require services; their execution
semantics remain those of the target repository.

## Implemented commands

| Command | Read/write boundary | Use |
|---|---|---|
| `init [--git]` | Creates missing data folders/config and refreshes managed root digests. | Finish install or refresh root pointers after a payload upgrade. |
| `task <title> [--type] [--parent]` | Writes a new journal. | Start governed feature, fix, change, or adoption work. |
| `req <category> <title>` | Writes a new requirement scaffold. | Add a durable behavior contract. |
| `anchor --task` | Writes/replaces the active anchor JSON. | Capture the known starting point before implementation. |
| `evolution --task` | Writes the matching evolution JSON. | Compare current repository state with the active anchor. |
| `status [task] [--all] [--json]` | Read-only. | List journals or inspect one task. |
| `brief <task>` | Read-only deterministic bounded resume view. | First when resuming a task. |
| `summary <task>` | Read-only latest stage-report projection. | After recording a stage completion or pause. |
| `check [--task] [--strict] [--run] [--full] [--json]` | Read-only unless `--run` executes configured commands. | Advisory governance feedback or CI proof. |
| `test [name] [--impacted] [--base] [--task]` | Runs one configured command; may append a task-log line. | Focused build loop or full configured suite. |
| `report <task>` | Appends a delivery report to the journal. | After validation, before a granted delivery action. |
| `diagram [--component] [--task] [--out]` | Read-only unless `--out` writes the Mermaid text. | Inspect requirement coverage. |
| `trace [--format {md,csv}] [--out PATH]` | Read-only unless `--out` writes the export. | Export the requirement register with coverage and ownership. |
| `explain <path>` | Read-only. | Find requirements and journals governing a file or folder. |

`python .agentic/aegis.py --help` and each command's `--help` are the
authoritative syntax reference. `.agentic/CLI.md` gives the full contract,
examples, output rules, and exit behavior.

## Resume commands are complementary

`brief` and `summary` are intentionally different:

| Command | Output | What it is for |
|---|---|---|
| `brief TASK-<id>` | Task identity, stage, branch/base, requirements, checklist, bound stage report, review policy, rulings, handoff, visible children, and details pointer. | Bounded re-entry before reading the current step and handoff sources. |
| `summary TASK-<id>` | The latest bound stage report: result, current stage, changes, evidence, issues, next action, user need, review fields, and details pointer. | Compact reporting after a stage completion or pause. |

Both commands are deterministic reads of durable files. Neither runs tests,
consults Git, writes state, proves that the candidate is still valid, or grants
authority. A truncation/stale marker means read the full journal.

## Configuration-backed execution

`test` runs the named `[commands]` entry (default `test`). With
`--impacted`, it uses the selected requirement-linked tests; with an empty
selection or no `test_impacted` command, it falls back to the full suite and
states why. `--base HEAD` limits impact selection to uncommitted work.

`check --run` executes eligible plain `[commands]` entries. Template
commands containing `{`, reserved `timeout`/`workdir` keys, and
side-effect-looking names are skipped unless `[check] run` explicitly allows
them. `[timeouts]` and `[commands] timeout` bound command duration. A
timed-out command proves nothing; a command that completes unsuccessfully is a
`command-failed` error.

## Governance checks

`check` currently implements 21 checks. They cover:

- requirement parsing, IDs, journal headers, and specification references;
- path coverage, linked tests, stale paths, scope drift, and source/test
  relationship;
- secrets in added diff lines, self-contained requirement prose, unticked
  delivery checklists, layout, stage zones, and configuration shapes;
- anchor/evolution evidence, configured-command completion, timeouts, and
  empty `--run` execution;
- manual verification declarations and enabled explicit-review evidence.

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
when explicitly requested. An upgrade replaces the 15 managed payload files,
preserves repository-owned records and `aegis.toml`, and then reruns
`init` to refresh root digests. Review the repository diff before any commit.

Machine-readable JSON is available for `anchor`, `evolution`, `status`,
and `check`. Each emits one schema-versioned document on stdout; `check
--run` sends command progress to stderr so stdout remains parseable.
`trace` exports Markdown (default) or CSV, not JSON.

## Separate host operations

The integrations expose eleven shared operations. These are adapter interfaces,
not additional Python CLI subcommands. OpenCode and Pi register native
`aegis_*` tools; Qwen and Claude expose them through local stdio MCP; Codex uses
a command bridge.

| Operation | Behavior and boundary |
|---|---|
| `status` | Read task state and tracked verification state. |
| `resume` | Read `brief`, check branch alignment and remember a session-local task pointer. |
| `read` | Read the installed contract, CLI reference, configuration, step or journal. |
| `summary` | Read the recorded stage report; no fresh proof. |
| `check` | Run static checks, optionally strict, without configured tests. |
| `scaffold` | Coordinator creates a task or requirement scaffold. |
| `evidence` | Coordinator invokes `anchor`, `evolution` or `report`. |
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
