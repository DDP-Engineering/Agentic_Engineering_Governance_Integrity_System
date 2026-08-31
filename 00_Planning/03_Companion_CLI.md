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
commit, push, create a pull request, or access the network.

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
