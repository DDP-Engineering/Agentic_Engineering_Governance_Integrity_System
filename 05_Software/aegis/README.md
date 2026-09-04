<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 0.11.0

AEGIS is an advisory governance workflow for agent-driven software development.
It keeps requirements, specifications, task journals, and component knowledge
as plain files in the target repository. The workflow is intentionally
non-blocking: agents read the instructions, record their work, and use the
heuristic check to find issues that need correction.
`check --strict` provides an optional CI boundary for errors and configured
promoted warnings; ordinary `check` remains advisory.

The project version is **0.11.0**. Optional OpenCode, Codex, Pi, Qwen Code and
Claude Code integrations are included in this version. They invoke the target checkout's installed AEGIS workflow;
they do not replace its contract or grant Git publication authority.

## Requirements and source layout

The core requires **Python 3.11 or newer** and only the Python standard library
at runtime. Git enables diff-based checks, impacted-test selection, anchors and
evolution. Optional host integrations require **Node.js 22+**, Python 3.11+,
Git and a compatible host installation.

| Path in this directory | Purpose |
|---|---|
| `template/.agentic/` | Reusable 15-file managed workflow payload; source of truth for downstream installations. |
| `integrations/` | Five host adapters, shared runtime and JavaScript behavior tests. |
| `tests/` | Python product suite, including wrappers that run integration tests. |

The repository-root `.agentic/` is this project's installed instance, with its
own configuration and records. It is separate from the reusable template.

## Install

Copy `template/.agentic/` into the target repository, then run:

```bash
python .agentic/aegis.py init
```

`init` creates missing data folders, a default `aegis.toml` when absent, and
managed guidance blocks in `AGENTS.md`, `CLAUDE.md`, and `QWEN.md`. It also
reports Git availability. When Git is installed but the target is not yet a
repository, `init --git` creates one explicitly.

For a core upgrade, replace only the 15 managed payload files and rerun `init`
to refresh root guidance. Preserve repository-owned configuration, requirements,
specifications, journals, knowledge and evidence. See
[install and setup](../../06_SoftwareDocu/01_Install_and_Setup.md).

## Use

```text
using aegis workflow, implement feature X
```

The stages are frame, specify, design, build, validate, and deliver. The quick
path is frame, build, validate, deliver, but size alone does not qualify a change.
An existing requirement must already cover the behavior being changed. There
must be no new externally observable behavior, interface, data format or
dependency, and no security- or data-handling behavior changes. Record the
eligibility reason in frame; validation and authority limits still apply.

Component knowledge pages are concise implementation routes. Their `Routing`
signals select the owning component and point to its first source and focused
test seams; boundaries, invariants, current architecture, behaviors, and files
provide the context needed to change it safely. A `Change map` is useful for a
component with multiple independent edit-and-test seams and can be omitted for
a simple component. The page reduces broad discovery, but the exact source and
tests remain authoritative and are inspected before implementation. A legacy
page without Routing supplies only provisional orientation from its available
sections and is migrated to the current template when its component is touched.
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
includes the parent, checklist, bound report, configured review state, active
rulings, stage-bound handoff, and visible children. Read its current step and
handoff `must_read` files next, then the full journal wherever required.

The agent records one fixed report at stage completion or pause, then copies
the read-only `summary` output into chat before detailed explanation.
Reported stage/result and current journal stage are separate. Missing evidence
stays `not recorded`; stale or shortened records require journal review.
No new approval stops, dependencies, or model calls are introduced.

The append-only task Log is deliberately narrower than a session transcript.
It keeps stage transitions, material engineering changes, consolidated
verification, blockers, approvals, deviations, and delivery outcomes. Routine
tool activity, corrected retries, and detail already held in another durable
artifact stay out of it.

For models with limited context, start with `brief`, current-stage
instructions, and handoff sources. Required full validation and delivery reads
still apply.
Frame, Specify, and Design also share a compact semantic-analysis cycle:
analyze selected evidence, challenge gaps and contradictions, write the durable
artifact, then audit it. Material claims are labelled stated, observed,
inferred, or unknown. The journal retains a structured Frame and requirement
coverage table; design depth grows when interfaces, state, trust, concurrency,
migration, or operational risk require it. Proposed architecture stays in the
task until validation reconciles the current component knowledge page.
The payload's prompt cheatsheet includes explicit one-stage sessions; actual
model compliance and 64K-context performance require separate model runs.
See `template/.agentic/CLI.md` for the optional journal record and output limits.

New journals also carry append-only supersedable Rulings, one replaceable
Handoff (`current`, `next`, `must_read`, `blockers`, `status`), and compatible
review fields. Optional explicit review defaults off:

```toml
[review]
enabled = false
max_fix_cycles = 2
```

When enabled, specification compliance and implementation quality are judged
independently for the same candidate, using `approved` or `changes_required`.
A candidate edit invalidates both verdicts. The workflow allows
`1 + max_fix_cycles` total rounds, then blocks for a human if changes remain
required.
Review disabled does not skip semantic review, full validation, strict checks,
or the delivery checkpoint.

## Optional host integrations

| Host | AEGIS resources |
|---|---|
| OpenCode | Primary Aegis agent, two review subagents, five commands and eleven native tools. |
| Codex | Native plugin, `aegis:aegis` skill, two review-role definitions and an eleven-operation command bridge. |
| Pi | Extension, skill, five commands, eleven tools and a launcher for fresh reviewer processes. |
| Qwen Code | Extension, skill, five commands, two review agents and eleven local MCP tools. |
| Claude Code | Plugin, workflow skill, five namespaced commands, two review agents, eleven local MCP tools and bounded advisory hooks. |

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
