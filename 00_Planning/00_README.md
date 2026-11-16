# AEGIS implementation overview

The current AEGIS source (`aegis.py --version` prints its version) includes the core and five
optional host integrations, evidence-led stage artifacts, focused verification,
compact progress records, current project/environment context and bounded
component discovery. Checkpoint mode presents user choices after every stage;
configured autopilot continues between stages. AEGIS never commits, pushes or
publishes.
Delivery packages and build records live under `07_Delivery/`. Source version
assignment and delivery construction are separate operations.
The runnable product is at `05_Software/aegis/`; the reusable core payload is
`05_Software/aegis/template/.agentic/`; host adapters are under
`05_Software/aegis/integrations/`; user guides are under `06_SoftwareDocu/`.

This directory records the implemented design. If it differs from the
installed payload, `.agentic/aegis.py --help`, `.agentic/AGENTS.md`, and
the payload step files are authoritative. Update this record when the
implementation or workflow contract changes. Integration behavior is defined
by its source, native resources and package guides; it does not add stages or
commands to the Python CLI.

This source checkout has no root `.agentic/` installation. Installed-path
examples refer to downstream projects; inspect the canonical payload under
`05_Software/aegis/template/.agentic/` when maintaining AEGIS itself. Repository
maintenance follows the root `AGENTS.md` without recreating a workflow deployment.

## What AEGIS is

AEGIS is an offline-first, advisory software-development workflow. A small
standard-library Python CLI scaffolds durable files, runs configured commands,
and reports governance findings. The workflow itself is Markdown that an agent
or developer reads and follows.

The core creates no hidden run store, hosted service, hooks, or separate
permission system. Git and ordinary repository files retain workflow history.
The optional integrations add host resources and an explicit local job cache
for detached verification; that cache is operational state, not a replacement
for the repository journal. Claude Code also has bounded advisory hooks.

## Core and host integrations

The host provides the model session and its existing permission system. The
AEGIS adapter reads the nearest Git checkout's installed contract, runs its
local CLI, and returns results for the coordinator to assess. The coordinator
records the durable material outcome through the CLI journal writers, which the
adapters' `journal` operation runs, and follows user authority; no adapter
decides a stage transition or grants Git permission.

| Host | Implemented entry points | Independent review support |
|---|---|---|
| OpenCode | Aegis primary agent, five commands, twelve native tools. | Two read-oriented subagents. |
| Codex | Native plugin, `aegis:aegis` skill and local bridge with twelve operations. | Two custom review-role definitions and bundled review prompts. |
| Pi | Extension, skill, five commands and twelve native tools. | Launcher for separate nonpersistent review processes. |
| Qwen Code | Extension, skill, five commands and twelve local MCP tools. | Two native read-oriented agents. |
| Claude Code | Plugin, workflow skill, five namespaced commands, twelve local MCP tools and two hook event types. | Two native read-tool agents. |

Codex does not receive the five slash commands or an OpenCode-style primary
agent selector. Pi has no built-in subagent facility; its launcher creates
fresh processes. These host differences do not change the workflow contract.

Shared integration code handles runtime discovery, owned installation,
candidate fingerprints, verification jobs, cancellation and recovery. The
package builder includes this code in each distributable. Installers preserve
unrelated host configuration and do not distribute credentials or model
settings. See [artifacts](02_Artifacts_And_Formats.md) for ownership and
[collaboration](04_Collaboration_And_Small_Models.md) for review limits.

## Current model

- One shared semantic cycle governs durable stage output: **Analyze** evidence,
  **Challenge** gaps and contradictions, **Write** the artifact, then **Audit**
  it. Material claims are labeled `STATED`, `OBSERVED`, `INFERRED`, or
  `UNKNOWN`; the protocol asks for reviewable artifacts, not hidden reasoning.
  Mixed-source clauses are labeled separately: an inspected test assertion is
  not an executed test, and a requested feature does not prove a current defect.
- Five fixed working stages that end in `done`: `frame -> specify -> design ->
  build -> validate -> done`. Validate closes the task; a journal left at the
  former `deliver` stage closes through validate.
- AEGIS admits only changes that add or change a durable product rule: logic,
  data, security, performance, integrations or a product-wide UI rule. Bug
  fixes that restore intended behavior, local UI adjustments, refactors and
  test, docs or tooling fixes are made directly, with no journal or
  requirement. The admission rule is in [workflow](01_Workflow_And_Stages.md).
  Specify and design have skip rules; there is one stage order.
- Existing-repository adoption is a separate `survey -> components -> close
  -> done` flow, not a seventh ordinary stage.
- Frame cards, requirement-coverage tables, designs, requirements,
  specifications, journals, current project/environment context, knowledge pages,
  anchors, and evolution reports
  are plain files below `.agentic/`.
- The CLI writes the journal's stage, Done checklist, Log, Rulings and State
  through `advance`, `pause`, `log`, `ruling` and `verdict`; the agent edits
  Frame, Requirement coverage and Design. Every session ends with `advance` or
  `pause`, and the summary block they print opens the reply. The Log retains
  only stage transitions, material engineering changes, consolidated
  verification, blockers, approvals and deviations; earlier lines are never
  edited.
- Build uses project-native focused tests or a configured runner that honors
  impacted references. `--dry-run` previews execution; `--no-fallback` refuses
  a full-suite fallback. Full strict verification follows final edits and review.
- New task, requirement and context records omit the payload license header and
  marked template-only notes; they belong to the project. Existing records and
  full saved fingerprints remain intact. Compact output is a presentation
  choice, not evidence deletion or automatic test-result reuse.
- `check` is advisory by default. `check --strict` is the optional CI
  boundary that fails on errors and configured promoted warnings.
  `uncovered-source` looks only at a scoped task's own diff; `context-size` and
  `duplicate-heading` keep current-state pages short and edited in place.
- Explicit review is optional policy, not a stage. When enabled it records
  specification-compliance and implementation-quality verdicts with a bounded
  fix-and-re-review loop; ordinary validation remains required either way.
  Reviewers inspect current files, including untracked scope, and focused proof;
  final full strict proof follows approvals. Invalidating verdicts retains the
  consumed round and historical findings.
- Project and component documents describe actual positive behavior and setup.
  Frame/adoption populates known facts, build updates affected facts and validate
  reconciles them against the candidate and established requirements, editing
  existing sections in place within `[context] page_kb`. Proposed
  capabilities remain in draft/task records.
- `brief` is the bounded resume view, including current-context paths and
  presence without reading their bodies; its `Read next` line names the step
  file and the State `must_read` paths, and, while the State waits on the user,
  the `advance` that moves on. `summary` prints the recorded State.
- `components` is a read-only, no-argument title-and-path catalogue for
  selecting concise component knowledge before exact source and tests. It
  creates no metadata registry and does not choose a component automatically.
- Optional Design diagrams follow the enablement/types gates. Checkpoint mode
  displays saved blocks between summary and choices; autopilot saves and reports
  their path without displaying them or adding a stop. An explicit Design stop
  still completes applicable artifacts.
- Validate corrects first and proves last: after review and record
  reconciliation, one final `check --strict --run` proves the candidate, and any
  later candidate edit needs fresh review and proof. Validate then appends the
  report and closes the task to `done`; committing, pushing and merging follow
  the repository's procedures.

AEGIS applies to changes that add or change a durable product rule; other
software changes are made directly. Repository maintenance, versioning,
release construction, package publication, and deployment follow the
repository's own procedures rather than opening an AEGIS journal.
Documentation-only updates in this repository are reviewed directly, outside
AEGIS, under the maintainer's scope instruction.

## Planning record

| Document | Current purpose |
|---|---|
| [01_Workflow_And_Stages.md](01_Workflow_And_Stages.md) | Admission rule, lifecycle, interaction boundaries, review policy, and resume behavior. |
| [02_Artifacts_And_Formats.md](02_Artifacts_And_Formats.md) | Ownership split, directory layout, configuration, and durable formats. |
| [03_Companion_CLI.md](03_Companion_CLI.md) | Core CLI commands, separate host operations, and execution boundaries. |
| [04_Collaboration_And_Small_Models.md](04_Collaboration_And_Small_Models.md) | Branch-based collaboration and bounded re-entry for constrained models. |
| [05_Implementation_Phases.md](05_Implementation_Phases.md) | Current capabilities, verification routes, ownership and maintenance. |

Start with the [user guide index](../06_SoftwareDocu/00_Index.md) or
[agent package guide](../06_SoftwareDocu/Agent_Plugins.md) for installation.
[Implementation status](05_Implementation_Phases.md) distinguishes product tests,
package/backend checks and representative model-led prompt evaluations from
Desktop acceptance and complete host workflows that require separate evidence.
