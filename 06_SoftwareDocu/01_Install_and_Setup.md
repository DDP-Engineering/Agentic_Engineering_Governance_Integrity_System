# AEGIS - install and setup

Install the repository core in three steps, then add a host integration if
you want native agents, skills, commands or tools. The core guides and never
blocks: it scaffolds files, writes task-journal state and reports advisory
findings. Optional integrations also use host permissions and, for Claude
Code, bounded advisory hooks.

## What you need

- Python 3.11 or newer on PATH (`python` on Windows, usually `python3`
  on Linux - the examples below use `python`).
- git (recommended; without it the diff-based checks politely skip
  themselves and everything else still works).
- Any coding agent: Claude Code, Codex CLI, Qwen Code, OpenCode, or a
  local model harness. Online or offline - both are first-class.

## Step 1 - copy one folder

Copy `<extracted-release>/.agentic/` into your repository root as
`<repo>/.agentic/`. When installing from this source repository, the payload is
at `05_Software/aegis/template/.agentic/`. These are two locations for the same
core payload; the release archive does not contain a `template/` parent.

## Step 2 - run init

```bash
python .agentic/aegis.py init
```

This finishes the installation, idempotently:

- creates the data folders (`requirements/`, `specs/`, `tasks/`,
  `knowledge/`, `context/`),
- creates each missing `context/project.md` and `context/environment.md` from
  generic templates, without the payload license header or template notes,
  preserving existing files independently,
- writes a default `.agentic/aegis.toml` - **only if absent**; an
  existing one is never touched,
- creates or appends the root pointer files `AGENTS.md`, `CLAUDE.md`,
  `QWEN.md` (a short digest under markers that routes the agent to
  `.agentic/AGENTS.md`; your existing content in those files is preserved),
- adds or removes the managed anchor/evolution block in the root
  `.gitignore` to match `[records] commit_fingerprints`, and reports how many
  sidecars are still tracked instead of running a Git write,
- reports whether Git is installed and whether this directory is already a
  Git repository.

If Git is installed but the project has no repository yet, initialize it
explicitly through AEGIS:

```bash
python .agentic/aegis.py init --git
```

Plain `init` never creates a Git repository silently. If Git itself is missing,
AEGIS finishes installing but explains that diff checks, impacted tests,
anchors, and evolution reports remain unavailable until Git is installed.

Review the diff and commit only with explicit authorization. Re-running `init`
preserves project data and configuration and refreshes the managed pointer
blocks when needed; text outside those blocks is preserved.

The context scaffolds start with empty headings. During frame or adoption,
populate verified current project and environment facts, linking existing setup
docs and configuration. New projects add responsibilities as they are built;
existing projects describe inspected implementation. See
[project context](Project_Context.md) for the format and update lifecycle.

## Step 3 - tell the config about your project

Open `.agentic/aegis.toml` and configure the project command and layout:

```toml
[commands]
test = "pytest -q"                    # how to run your test suite
test_impacted = "pytest -q {tests}"   # optional: focused regression

[layout]
source = ["src/"]                     # where your production code lives
tests  = ["tests/"]                   # where your tests live
docs   = ["docs/", "README.md"]       # optional: documentation paths
```

`docs` is optional. It stops declared documentation from being reported as
outside the layout, while keeping it in the diff and secret scan. It is not
counted as source, tests, or a stage write zone.

If your application lives in a subfolder rather than at the repository
root, add one more line and let AEGIS handle the rest:

```toml
[commands]
workdir = "app"                       # run commands here, not at the root
```

Do not put a directory change inside the commands themselves. AEGIS
substitutes repository-relative test paths into `test_impacted`, so a
command that moves itself would resolve those paths a second time and find
nothing. With `workdir` set, the paths are rewritten to match.

Nothing limits how long a command may run. If you want a limit - a hung
linter, a CI budget - ask for one per command:

```toml
[timeouts]
test = 5400                           # seconds; this command only
lint = 120
```

A command stopped by its limit is reported as having proved nothing, which
is different from a suite that ran and failed.

The pytest commands above are examples for a Python project. AEGIS does not
choose a framework, install dependencies or translate selectors. Use your
project's documented runtimes, dependency setup, services and readiness checks
before starting tests. Diagnose missing prerequisites directly instead of
repeatedly launching a full suite.

### Verify focused routing before using it

Configure `test` as the full suite. Add `test_impacted` only when the project's
runner accepts the linked file references and supported exact selectors.
A wrapper that ignores its arguments will still run the full suite.

```text
python .agentic/aegis.py test --impacted --base HEAD --dry-run
python .agentic/aegis.py test --impacted --base HEAD --no-fallback
```

The first command previews the selected command and working directory. Inspect
whether it selects focused tests or would fall back to the full command. It
executes nothing, and exit zero is not passing test evidence. The second refuses
unavailable selection with exit 1 and no test execution or journal result.
Without `--no-fallback`, existing full-suite fallback remains enabled.

Confirm the runner actually honors selection from its own output. If it does
not, use a native focused project command. Unsupported test-name suffixes can
broaden safely to a validated file reference; paths containing spaces still
need a native project command. See the [CLI reference](09_CLI_Reference.md#test)
for selection and workdir rules.

During build, use focused checks. After final edits and review, run
`check --task TASK-<id> --strict --run` with the full suite included in its eligible
commands; `check --task TASK-<id> --dry-run` lists what it would run, with each
command's limit, and runs none of it. Avoid a separate full `test` immediately
beforehand. This is workflow guidance, not an execution quota or automatic reuse
of previous test results.

Everything else in the file is optional tuning and can wait. The full list
is below.

## Settings reference

`aegis.toml` is both the configuration and its own reference: the keys most
projects never change are written as commented defaults with their rationale,
so the file `init` hands you already names every setting the CLI reads. This
section repeats them with what `init` writes and what applies when a key is
absent.

`init` writes this file **only when it is missing**. Upgrading AEGIS never
touches an existing one, which is also why a key added by a later version is
not added to your file - take it from here.

### Top level

| Setting | `init` writes | When absent |
|---|---|---|
| `schema` | `1` | `check` warns that the schema should be the integer 1. |

### `[commands]` - what AEGIS runs

| Setting | `init` writes | When absent |
|---|---|---|
| `test` | `"pytest -q"` | `aegis test` reports that no runnable entry named `test` exists, and `check --run` has nothing to prove. |
| `test_impacted` | commented `"pytest -q {tests}"` | Focused selection is unavailable, so `test --impacted` falls back to the full command unless you pass `--no-fallback`. |
| `<name>` | commented `lint = "ruff check ."` | Any other entry you add, such as `lint` or `build`, is a command `check --run` executes. |
| `timeout` | commented `0` | No limit. Zero, a negative number and an unreadable value all mean no limit too. |
| `workdir` | commented `"app"` | Commands run at the repository root. A directory that escapes the root or does not exist falls back to the root, and `check` reports it. |

Never put a directory change inside a command. AEGIS substitutes
repository-relative paths into `{tests}`, so a command that moves itself would
resolve them a second time and find nothing. `workdir` rewrites those paths to
match instead.

### `[timeouts]` - one limit per command

| Setting | `init` writes | When absent |
|---|---|---|
| `<command name>` | commented `test = 5400` and `lint = 120` | No limit for that command. A value here wins over `[commands] timeout`, and only a positive integer sets a limit at all. |

Nothing is limited by default, because a limit short enough to cut off a
healthy suite would report a failure that never happened. A command stopped by
its limit is reported as having proved nothing, which is not the same as a
suite that ran and failed.

### `[layout]` - what the heuristics treat as code

| Setting | `init` writes | When absent |
|---|---|---|
| `source` | `["src/"]` | No source globs, so the traceability heuristics have nothing to match. |
| `tests` | `["tests/"]` | No test globs. |
| `docs` | `[]` | Documentation is reported as sitting outside the layout. It stays in the diff and the secret scan either way. |
| `default_branch` | commented `"develop"` | The base is whatever `origin/HEAD` points at, then a local `master`, then a local `main`, and nothing at all when none of those resolve. |

`default_branch` names the ref every diff is measured from, so it decides what
`check`, `test --impacted` and `report` consider changed. Set it when the
branch your work merges into is not the one AEGIS would find on its own.

### `[interaction]` - when the agent stops

| Setting | `init` writes | When absent |
|---|---|---|
| `autopilot` | `false` | `false`. An invalid value resolves to `false` as well, and `check` reports it. |

`false` stops after every completed stage and presents the next choices.
`true` flows between stages through validate; a decision-blocking question
still stops it. AEGIS never commits or publishes in either mode. An explicit
instruction for one task overrides this default and is recorded in that task's
journal header, so the choice survives a resume.

### `[review]` - optional explicit verdicts

| Setting | `init` writes | When absent |
|---|---|---|
| `enabled` | `false` | `false`. Ordinary semantic review, the full suite and the strict check stay part of validate whichever way this is set. |
| `max_fix_cycles` | `2` | `2`. A value outside 0 through 255 resolves to 0, and `check` reports it. |

With `enabled = true`, validate follows `.agentic/steps/review.md`: two
independent reviewers, verdicts recorded with `verdict`, and at most
`1 + max_fix_cycles` rounds.

### `[context]` - size of the pages read at every frame

| Setting | `init` writes | When absent |
|---|---|---|
| `page_kb` | `24` | No budget. `0` means no budget as well. |

`check` reports a project context or knowledge page above the budget as
`context-size`.

### `[diagrams]` - optional design diagrams

| Setting | `init` writes | When absent |
|---|---|---|
| `enabled` | `false` | `false`. Any value other than the Boolean `true` also means `false`, and `check` reports a non-Boolean. |
| `types` | `["structure"]` | `["structure"]`. An empty list draws nothing; `check` reports a non-list or a name other than `structure`, `sequence` or `state`. |

With `enabled = true`, design ends by drawing Mermaid diagrams of the proposed
implementation into `.agentic/tasks/diagram_TASK-<id>.md`, links the file from
the task's `## Design`. Checkpoint responses show the saved Mermaid blocks
after the stage summary and before choices. Autopilot saves the same applicable
artifacts and reports their path, without displaying blocks or adding a stop.
An explicit Design stop retains that mode's presentation and the Design header.
An empty types list creates no file or link; unknown types are ignored. A
skipped Design draws nothing. Node classes describe proposed node
edits independently of edge changes. The diagrams
illustrate the design for you: no stage, review or `check` finding depends on
them, and AEGIS bundles no renderer - GitHub, GitLab and many Markdown
previews draw Mermaid, and a terminal shows its text.

### `[records]` - fingerprint sidecars

| Setting | `init` writes | When absent |
|---|---|---|
| `commit_fingerprints` | `false` | `false`. `init` keeps a managed block in the root `.gitignore` that excludes `.agentic/tasks/*.anchor.json` and `*.evolution.json`; the journal log line is the durable record. `true` removes the block so the sidecars are committed. `check` reports `fingerprints-tracked` when the repository disagrees. |

### `[zones]` - what each stage may write

Every stage may always write under `.agentic/`. A value names the `[layout]`
globs that stage may write as well - `"source"`, `"tests"`, or nothing.

| Stage | Default |
|---|---|
| `frame`, `specify`, `design`, `survey`, `close` | nothing beyond `.agentic/` |
| `components` | `["tests"]` |
| `build`, `validate` | unlisted, so unconstrained |

`init` writes each of these as a commented line. Zones are advisory like
everything else: `check` reports an edit outside the current stage's zone as
`stage-zone`, and never stops one.

### `[check]` - the advisory report

| Setting | `init` writes | When absent |
|---|---|---|
| `ignore` | `[]` | Nothing is excluded from the checks. |
| `secret_patterns_extra` | `[]` | Only the built-in secret patterns apply. |
| `strict_promote` | `[]` | `--strict` fails on errors, a failed `--run` command among them, and on no warnings. |
| `run` | commented `["test", "lint"]` | `check --run` executes every `[commands]` entry except names that read as side effects - `deploy`, `migrat`, `publish`, `release`, `push`, `upload` - which are skipped with a visible line. |


## First contact

Tell your agent:

```
using aegis workflow, implement feature <what you want>
```

The root `AGENTS.md` digest routes the agent to `.agentic/AGENTS.md`. It opens
a task journal and walks the stages: frame, specify, design, build and
validate, then done. Only changes that add or change a durable product rule
use AEGIS: a bug fix that restores intended behavior or a local UI adjustment
is made directly, as [Direct changes](04_Example_Direct_Change.md) explains.
The agent records each stage boundary with `advance` or
`pause`, and committing stays with you. Check where things stand at any time
with:

```bash
python .agentic/aegis.py status
```

`status` lists **open** tasks; closed ones (`stage: done`) are hidden
with a count - add `--all` to see them too.

and get the advisory findings report with:

```bash
python .agentic/aegis.py check
```

Git is also used by the optional repository-state commands. `anchor` and
`evolution` report a concise error when Git is unavailable; this does not stop
the rest of the advisory workflow from being used.

Ordinary `check` findings do not produce a failing exit. `--strict` fails on
errors and promoted warnings. Invalid invocation or an operational error is a
different case; inspect the exit code and output. The core itself makes no
network calls, but configured commands and the chosen host/provider may do so.

## Optional: install a host integration

The core works through file and shell access. A host package adds convenient
entry points and tracked verification jobs; it still requires the target
checkout's installed `.agentic/aegis.py` and its workflow files.

| Host | Entry point after installation |
|---|---|
| OpenCode CLI / Desktop backend | Select **Aegis**; `/aegis-status` or `/aegis-start <request>`. |
| Codex CLI / Desktop backend | Open a new task and invoke the `aegis:aegis` skill. |
| Pi | `/aegis-status` or `/aegis-start <request>`. |
| Qwen Code | `/aegis-status` or `/aegis-start <request>`. |
| Claude Code CLI / local Desktop Code | `/aegis:status` or `/aegis:start <request>`. |

Build complete packages from this repository root with Node.js 22+:

```sh
node 02_Tools/build_agent_plugins.mjs --output <fresh-output-directory>
```

Distribute the appropriate complete `aegis-<host>` directory, or a ZIP of it.
On the recipient's computer, extract it and run `Install-AEGIS.cmd` on Windows
or `sh install.sh` on Linux. The cross-platform alternative is
`node setup.mjs install`, followed by `node setup.mjs doctor` in that package.
The recipient needs Node.js 22+, Python 3.11+, Git and a compatible host.
Each user keeps their own host sign-in, provider and model configuration.

CLI and Desktop share an installation only when using the same backend and
profile. Remote backends and WSL CLI environments need their own installation.
Claude Desktop WSL plugin sessions are currently unsupported; native local
Desktop Code and native CLI use the supported installation path. See
[Agent_Plugins.md](Agent_Plugins.md) for host versions, profile options, all
twelve operations and the limits of the recorded verification.

## Upgrade, undo, uninstall

- **Core upgrade:** replace only the payload-owned files (`AGENTS.md`, `CLI.md`,
  `steps/`, `templates/`, `aegis.py`, `LICENSE.txt`), then run `init` to refresh
  root pointer blocks. Preserve `aegis.toml`, requirements, specs, knowledge,
  journals and task sidecars. Review the diff before any authorized commit.
  Older journals stay readable: one with `## Handoff` and `## Stage report`
  keeps them until the first `advance` or `pause` replaces both with a
  `## State` block, and one left at `stage: deliver` closes through validate
  with `advance`.
- **Core undo:** restore only the intended changes or revert an approved commit.
  A Git checkout does not include uncommitted work from another machine.
- **Core removal:** preserve any records you need, remove `.agentic/` and remove
  only its marked blocks from root `AGENTS.md`, `CLAUDE.md` and `QWEN.md`.
- **Host lifecycle:** use the package's `setup.mjs update`, `doctor` and
  `uninstall`. Host registration, ownership records and runtime paths live in
  the user's profile; verification jobs/logs live in a separate cache and are
  retained on removal. Core removal does not uninstall these packages.

Host updates/removal refuse changed owned files and active or uncertain jobs.
Inspect and preserve those files or jobs before resolving a conflict; do not
delete a reservation merely to start another verification run.
