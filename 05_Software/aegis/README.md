# AEGIS

AEGIS is an advisory governance workflow for agent-driven software development.
It keeps requirements, specifications, task journals, and component knowledge
as plain files in the target repository. The workflow is intentionally
non-blocking: agents read the instructions, record their work, and use the
heuristic check to find issues that need correction.
`check --strict` provides an optional CI boundary for errors and configured
promoted warnings; ordinary `check` remains advisory.

`python .agentic/aegis.py --version` prints the version. Optional OpenCode, Codex, Pi, Qwen Code and
Claude Code integrations are included in this version. They invoke the target checkout's installed AEGIS workflow;
they do not replace its contract or grant Git publication authority.

## Requirements and source layout

The core requires **Python 3.11 or newer** and only the Python standard library
at runtime. Git enables diff-based checks, impacted-test selection, anchors and
evolution. Optional host integrations require **Node.js 22+**, Python 3.11+,
Git and a compatible host installation.

| Path in this directory | Purpose |
|---|---|
| `template/.agentic/` | Reusable managed workflow payload; source of truth for downstream installations. |
| `integrations/` | Five host adapters, shared runtime and JavaScript behavior tests. |
| `tests/` | Python product suite, including wrappers that run integration tests. |

This source checkout has no repository-root `.agentic/` installation; the
template is maintained directly.

The CLI journal writers record the stage, Done checklist, Log, Rulings and
State; the agent edits Frame, Requirement coverage and Design. Frame records the
existing requirements that cover the work, and the State's next action names
one concrete action or question. New requirements start as drafts and
build activates them. Unknown behavior and unobserved proof remain explicit.

## Install

Copy `template/.agentic/` into the target repository, then run:

```bash
python .agentic/aegis.py init
```

`init` creates missing data folders, a default `aegis.toml` when absent, and
managed guidance blocks in `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`. It also
reports Git availability. When Git is installed but the target is not yet a
repository, `init --git` creates one explicitly.

For a core upgrade, replace only the managed payload files and rerun `init`
to refresh root guidance. Preserve repository-owned configuration, requirements,
specifications, journals, context, knowledge and evidence. See
[install and setup](../../06_SoftwareDocu/01_Install_and_Setup.md).

`init` also creates each missing `.agentic/context/project.md` and
`.agentic/context/environment.md` from generic Markdown templates. Existing
context files are preserved byte-for-byte. These are short current-state
orientation and setup guides: populate verified facts at frame/adoption and
update affected sections as implementation or setup changes. `brief` reports
their paths and presence without loading their contents. Missing context is
supported in older projects.

Project documents, component pages, and active requirements/specs describe
actual behavior positively. Keep proposals in draft/task records and history
in journals, Git, and the changelog. Preserve meaningful error and security
responses, and obtain authorization before changing established behavior.
See [project context](../../06_SoftwareDocu/Project_Context.md) for ownership,
formats, lifecycle, and examples.

## Use

```text
using aegis workflow, implement feature X
```

AEGIS admits only changes that add or change a durable product rule: logic,
data, security, performance, integrations, or a product-wide UI rule such as a
theme or accessibility convention. A bug fix that restores intended behavior, a
local UI adjustment, a refactor, or a test, docs or tooling fix is made
directly, with no journal or requirement; a fix that contradicts an active
requirement, adds behavior, or touches security or data handling uses AEGIS.
The user's explicit choice wins, and the agent names its choice in one
`LANE: direct|aegis - <why>` line.

The stages are frame, specify, design, build and validate, ending at done.
Specify and design have skip rules; frame, build and validate always run.

Each stage has one step file: what to read, the steps, a Finish block naming
the exact commands for checkpoint and autopilot, and a Done when list that the
CLI copies into the journal. The agent edits the Frame, Requirement coverage
and Design sections; the CLI writes the rest. `advance` moves to the next stage
on the path, or back with `--to`; `pause` stops for the user with one named
question or action; `log` and `ruling` append events and decisions; `verdict`
records explicit review results. They record the agent's decision without
judging it; `advance`, `pause` and `verdict` print the summary block that the
agent shows first. A
journal keeps one `## State` block: status, the reported stage and result, next
action, must-read paths, changed files, evidence, issues and review fields.
Journals written before it keep their Handoff and Stage report until the first
State write replaces them. `brief` resumes a task: it prints the State, the
computed diagram decision and a `Read next` line naming the step file and the
must-read paths.

Validate reviews and reconciles the candidate, updates component knowledge and
project context, runs the final proof once after the last edit, appends
`report` and closes the task with `advance` to `done`. Commits, pushes, pull
requests and merges follow the repository's own procedures, outside AEGIS.
See the [prompt evaluations](evaluations/README.md) for measured model behavior
and the limits of automatic checks; the harness covers every step file, real
reviewer activation, diagrams, autopilot, context updates, a hold-out domain
and a chained lifecycle.

Component knowledge pages are concise implementation routes. Their `Routing`
signals select the owning component and point to its first source and focused
test seams; boundaries, invariants, behaviors, and files
provide the context needed to change it safely. A `Change map` is useful for a
component with multiple independent edit-and-test seams and can be omitted for
a simple component. The page reduces broad discovery, but the exact source and
tests remain authoritative and are inspected before implementation. A legacy
page without Routing supplies only provisional orientation from its available
sections and is migrated to the current template during validation of changes
to its component.
List the available component titles and paths before choosing what to read:

```text
python .agentic/aegis.py components
```

The command accepts no arguments, parses only page titles, creates no index,
and does not select a component automatically. Titles are bounded to one safe
output field, and links cannot escape the knowledge directory; the chosen
page, exact source, and tests remain the authority.

For an automated requirement, write and observe the expected failing test
before implementation, recording its command, non-zero exit and failure reason.
Anchor the repository after that red result and compare it after implementation:

```text
python .agentic/aegis.py anchor --task TASK-<id>
python .agentic/aegis.py evolution --task TASK-<id>
```

These commands are advisory. They record added, modified, and removed
Git-visible files without blocking development or claiming tamper-proof
evidence. Git-ignored files and generated Python bytecode caches are excluded.

Both sidecars stay out of Git by default. `[records] commit_fingerprints` is
`false`, so `init` maintains a marked block in the root `.gitignore` that
excludes them and the journal's recorded evolution line remains the durable
evidence. Set it to `true` and rerun `init` to remove the block and commit
them with the journal. AEGIS never untracks a file; `init` prints the
`git rm --cached` command for a human to run.
Requirements with a declared `Manual:` or `Inspection:` method instead need a
recorded observation after implementation, with the anchor taken before edits.

Three commands read the register back rather than adding to it:

```text
python .agentic/aegis.py diagram --out docs/coverage.mmd
python .agentic/aegis.py explain src/some/file.py
python .agentic/aegis.py trace --format csv --out docs/traceability-matrix.csv
```

`diagram` draws every requirement as a Mermaid flowchart coloured by how the
behavior is verified; `explain` names the requirements and journals that
already govern a path. `trace` exports every requirement as a Markdown table
or CSV, including coverage, component, verification, linked tests and affected
paths. All three read only files already in the repository. Use `--out` for
portable encoding; stdout follows the console encoding.

See the [CLI contract](template/.agentic/CLI.md) for complete syntax.

Large work may opt in to one level of independently governed child tasks:

```text
python .agentic/aegis.py task "Implement decoder" --type feature --parent TASK-<id>
```

The link exists only in the child. Reverse lookup sees only journals in the
current checkout; each child retains its own branch/base and validation, while
the parent proves the integrated candidate.

## Efficient verification and records

AEGIS keeps runner commands project-configured. Prepare the repository's documented
environment once, use focused native tests during build, and run full strict
verification after final edits and review. Impacted routing is optional: the project
runner must honor the selected files/tests. Preview without executing or recording
proof, then refuse expensive fallback when using it inside the build loop:

```text
python .agentic/aegis.py test --impacted --base HEAD --dry-run
python .agentic/aegis.py test --impacted --base HEAD --no-fallback
python .agentic/aegis.py check --task TASK-<id> --strict --run
```

Unsupported test-name suffixes broaden safely to file-level selection; unsafe file
paths still refuse selection. Existing callers keep full-suite fallback unless
`--no-fallback` is specified. A dry-run success is not a test result. Do not run a
separate full `test` immediately before final strict verification.

New task and requirement records omit the payload license header and marked
template-only explanations; fields and existing records are preserved. Evolution supports `--compact --json` for
paths/statuses/areas, retaining complete hashes in the saved evidence. Host adapters
expose `no_fallback` for impacted runs and `compact` for evolution on supporting
payloads. See `06_SoftwareDocu/09_CLI_Reference.md` for the command contracts.

## Documentation layout

In `.agentic/aegis.toml`, set optional `[layout] docs` globs for project
documentation, such as `docs = ["docs/", "README.md", "CHANGELOG.md"]`.
Declared documentation no longer produces `outside-layout` warnings, while
remaining in secret scanning. It does not count as source or test coverage
and does not change stage write zones. Overlapping source/tests globs retain
their existing checks; an omitted or empty docs list preserves prior behavior.

## Compact resume and stage reporting

```text
python .agentic/aegis.py brief TASK-<id>
python .agentic/aegis.py summary TASK-<id>
```

`brief` is the first re-entry view: deterministic, read-only, and bounded to
240-character values, eight active rulings, and twenty visible children. It
includes the parent, checklist, State, resolved interaction mode,
configured review state, diagram decision, active rulings and visible
children, and ends with a `Read next` line naming the current step file and
the State `must_read` paths. Read those next, then the full journal wherever
required.

Every session ends with `advance` or `pause`, which write the State and print
the `summary` block; the reply starts with that block before detailed
explanation. Reported stage/result and current journal stage are separate. Missing evidence
stays `not recorded`; stale or shortened records require journal review.
With autopilot off, every completed stage ends at a user choice checkpoint.

Interaction defaults are project configuration:

```toml
[interaction]
autopilot = false
```

Missing or invalid values mean off. Checkpoint mode presents stage-specific
choices: continue, revise, go back or stop. Autopilot flows
between stages through validate; a decision-blocking question still stops it,
and AEGIS never commits or publishes. New
task journals record the resolved mode so it remains stable across resumes;
an explicit user instruction can override the configured default for that task.

The append-only task Log is deliberately narrower than a session transcript.
It keeps stage transitions, material engineering changes, consolidated
verification, blockers, approvals, deviations, and the closing outcome. Routine
tool activity, corrected retries, and detail already held in another durable
artifact stay out of it.

For models with limited context, start with `brief` and read what its
`Read next` line names; validate still reads the whole journal.
Frame, Specify, and Design also share a compact semantic-analysis cycle:
analyze selected evidence, challenge gaps and contradictions, write the durable
artifact, then audit it. Material claims are labelled stated, observed,
inferred, or unknown. The journal retains a structured Frame and requirement
coverage table; design depth grows when interfaces, state, trust, concurrency,
migration, or operational risk require it. The proposal stays in the task
during design. Build updates directly affected docstrings, usage examples,
and setup instructions. Validate updates component knowledge after
implementation corrections and before final review and proof. Earlier
component updates are appropriate when another agent needs current facts for a
handoff.
The [prompt cheatsheet](../../06_SoftwareDocu/08_Prompt_Cheatsheet.md) gives
one-stage sessions for small models; actual model compliance requires model
runs. See `template/.agentic/CLI.md` for the journal commands and output limits.

New journals also carry their `interaction: checkpoint|autopilot` mode,
append-only supersedable Rulings, and the State block with its review fields. Optional explicit review defaults off:

```toml
[review]
enabled = false
max_fix_cycles = 2
```

When enabled, specification compliance and implementation quality are judged
independently for the same candidate, using `approved` or `changes_required`.
A candidate edit invalidates both verdicts. The workflow allows
`1 + max_fix_cycles` total rounds, then pauses as blocked for the user if
changes remain required. The protocol is `steps/review.md`, read only when
review is enabled; disabled review does not skip semantic review, full
validation or the strict check.

Design diagrams for the human are optional and default off:

```toml
[diagrams]
enabled = false
types = ["structure"]
```

With `enabled = true`, design ends by drawing Mermaid diagrams of the proposed
implementation (`structure`, `sequence` or `state`, as listed in `types`) into
`.agentic/tasks/diagram_TASK-<id>.md`, links the file from `## Design`, and
shows the diagrams at the design checkpoint. They only illustrate the design:
no stage, review or `check` finding depends on them, and AEGIS bundles no
renderer.

## Optional host integrations

| Host | AEGIS resources |
|---|---|
| OpenCode | Primary Aegis agent, two review subagents, five commands and twelve native tools. |
| Codex | Native plugin, `aegis:aegis` skill, two review-role definitions and a twelve-operation command bridge. |
| Pi | Extension, skill, five commands, twelve tools and a launcher for fresh reviewer processes. |
| Qwen Code | Extension, skill, five commands, two review agents and twelve local MCP tools. |
| Claude Code | Plugin, workflow skill, five namespaced commands, two review agents, twelve local MCP tools and bounded advisory hooks. |

Entry points differ by host: Codex does not receive OpenCode's primary-agent
selector or the five slash commands. Pi's reviewer launcher uses separate
nonpersistent processes because Pi has no built-in subagents. Each user keeps
their own host authentication, model selection and effective permissions.

Shared runtime code resolves the selected Git checkout and invokes its local
`.agentic/aegis.py`. Static `check` operations do not run tests. The tracked
`run` operation starts configured verification and returns a job ID; use `job`
to inspect completion, output, exit status and candidate changes before
recording proof. Jobs survive host restarts, with reservations for duplicate
prevention and uncertain-process recovery. This protection applies to adapters
sharing the same cache; it does not detect manually launched suites.

Assemble the complete packages from the **repository root**:

```sh
node 02_Tools/build_agent_plugins.mjs
```

The builder creates five package directories under
`07_Delivery/agent-plugins-unreleased/`. Use `--output PATH` for another location;
existing host package directories cannot be overwritten. It copies shared
libraries into each package, including `plugins/aegis/lib/` for Codex and Claude.
Raw integration source folders are incomplete installation inputs and can
cause the missing `lib/bridge.mjs` error.

Assembly preserves the existing version and makes no model requests, runs no
tests and performs no registry publication. Share a complete host directory or
an archive made from it. After extraction, use `sh install.sh` on Linux,
`Install-AEGIS.cmd` on Windows, or `node setup.mjs install`; `doctor`, `update`
and `uninstall` are also available through `setup.mjs`.

CLI and Desktop share resources when they use the same supported backend and
configuration. Remote backends and WSL CLI environments need their own install;
Claude Desktop WSL plugin sessions are currently unsupported. Backend/native
resource checks have been performed on Windows and Ubuntu under WSL without
model requests. Desktop UI interaction, complete model-driven workflows and
actual model-led reviewer behavior remain unverified.

See [Agent plugins](../../06_SoftwareDocu/Agent_Plugins.md) for host-specific
prerequisites, lifecycle protection and cache behavior, and
[implementation status](../../00_Planning/05_Implementation_Phases.md) for
dated verification evidence and tested host versions.

## Development

From **this package directory** (`05_Software/aegis/`), use a Python environment
with `pytest` and `ruff` installed, with Git and Node.js 22+ available:

```bash
python -m pytest -q tests
python -m ruff check .
python template/.agentic/aegis.py --help
```

The suite includes JavaScript integration behavior checks through Python
wrappers. These use temporary fixtures and make no model requests; passing them
does not establish Desktop UI or model-workflow acceptance.

Review documentation-only changes directly, outside AEGIS. Do not create
workflow journals or tests that assert prose or links for those updates.
Core archive construction and plugin assembly are separate repository
operations; see [Tools](../../02_Tools/README.md) for both builders.

## License

PolyForm Noncommercial 1.0.0. See the [license](template/.agentic/LICENSE.txt).
