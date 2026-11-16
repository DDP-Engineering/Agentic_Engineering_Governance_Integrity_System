# 05 - Current implementation

This page describes current
capabilities, source ownership and verification methods. Release history is in
the [changelog](../CHANGELOG.md); dated build evidence is retained under
`07_Delivery/`, prompt observations under the development evaluation directory,
and implementation history in Git.

## Implemented capabilities

| Area | Current behavior |
|---|---|
| Workflow | Five working stages that end in `done`, an admission rule that sends bug fixes and local UI adjustments outside AEGIS, and a separate component-by-component adoption flow. Validate closes the task. |
| Interaction | Stage checkpoints by default, optional project-configured autopilot and immediate material deviation notices. AEGIS never commits, pushes or publishes; those stay with the developer. |
| Project context | Project-owned `context/project.md` and `context/environment.md`, scaffolded independently by `init` when absent and preserved byte-for-byte when present. |
| Current documentation | Positive actual responsibilities and behavior in project/component documents and active contracts, with proposals in draft/task records and history in journals/Git. |
| Durable artifacts | Frame cards, atomic requirement coverage, task designs, TOML requirements, Markdown specs and knowledge, append-only Log/Rulings, one CLI-written `## State` block, and anchor/evolution evidence. |
| Companion CLI | Offline-first standard-library Python scaffolding, journal writers (`advance`, `pause`, `log`, `ruling`, `verdict`) that record the agent's decisions and turn unfinished work into notes, never refusals, component discovery, traceability, configured execution and bounded reporting. |
| Verification | A 24-check advisory catalog, optional strict CI, focused/impacted test selection, dry-run previews, fallback refusal, timeouts, and complete saved evidence with optional compact presentation. |
| Coordination | Presence-only context pointers and a `Read next` line in `brief`, the recorded State through `summary`, one-level child tasks, independent review verdicts and bounded correction rounds. |
| Integrations | OpenCode, Codex, Pi, Qwen Code and Claude Code entry points backed by twelve shared adapter operations, including `journal`. |
| Host lifecycle | Complete package assembly, runtime discovery, owned installation/update/removal, verification jobs, duplicate prevention, cancellation and recovery. |
| Prompt evaluation | Ten core, fifteen capability and six hold-out scenarios in disposable Git repositories, covering all eight step guides, the common contract, task records, actual reviewer sessions, diagrams, autopilot, context updates and one feature carried through five fresh sessions. |

## Source ownership

```text
05_Software/aegis/
  template/.agentic/       canonical managed core
    templates/            six generic artifact templates
    steps/                five stage cards, review, adoption and diagram guides
    aegis.py              Python CLI
  integrations/           five host adapters and shared runtime
    tests/                JavaScript behavior tests
  tests/                  Python product suite and integration wrappers
  evaluations/            development scenarios and subscription baselines
  README.md               package overview

02_Tools/
  build_aegis_release.py  core archive and build-record builder
  build_agent_plugins.mjs complete host-package builder
  evaluate_aegis_*.py     development prompt collection and scoring tools
```

The managed core contains 18 files. Downstream projects own their context,
configuration and records. This maintainer checkout has no root `.agentic/`
deployment or installed review configuration. Maintain the canonical template;
when a downstream installation exists, update only its managed payload during
upgrade and preserve its project-owned files. Each missing context
file is scaffolded independently by `init`; existing project data keeps its bytes.
The downstream starter changelog remains empty.

## Project context lifecycle

Read the profile at frame/resume and relevant environment sections before setup,
build or verification. Select component, requirement, source and test references
instead of preloading the repository. Brief lists the two paths with `present`
or `not recorded`; their contents and accuracy require direct review.

Populate confirmed purpose, implementation and setup facts during frame or
adoption. New projects add responsibilities as they are implemented. Build
updates affected facts as changes become real; validate reconciles current
context, component pages and active contracts against the candidate and
authorized intent, editing existing sections in place; `check` reports a page
above `[context] page_kb` or a repeated level-two heading. Preserve unrelated sections and established requirements.
Missing or partial context is compatible with ordinary work.

Current documents contain one positive description of each actual behavior,
including meaningful error, security and compatibility responses. Draft
requirements/specs hold agreed proposals. Journals, Git and the changelog carry
past decisions and changes. Suspected defects remain task findings pending
clarification rather than becoming assumed active contracts.

## Verification methods and evidence

Use repository `AGENTS.md` for the validation obligations and
an installed target's `.agentic/aegis.toml` for its commands and layout. This
checkout's product verification runs directly against `05_Software/aegis/tests`;
it does not require a root workflow deployment. The product suite covers
isolated CLI/scaffolding behavior, context preservation and optional brief
pointers, traceability, configured execution, packaging and host integration
behavior. Focused tests precede the full product suite for executable changes.

Each delivery's build record under `07_Delivery/aegis-<version>/` retains the
complete product result for that version. Documentation-only refreshes reuse
it only for unchanged software/test sources; it is not a fresh test execution
and does not establish prompt compliance.

Host verification has separate scopes:

- Package checks inspect resources, runtime discovery and owned lifecycle.
- Backend checks inspect native registration, tool discovery and protocol calls.
- Desktop acceptance inspects the visible resources in the selected environment.
- Prompt evaluation exercises selected stages and independent reviews with the
  authorized model in bounded fixtures; complete native-host acceptance is a
  separate scope.

A result supports only its recorded candidate and environment. Package/backend
checks alone establish neither Desktop nor model-led acceptance. Small-context
operation is supported by selective reading and compact records; model compliance
requires its own measured evaluation. Consult [agent package guidance](../06_SoftwareDocu/Agent_Plugins.md)
for verification routes and links to recorded evidence.

## Prompt evaluation status

The development [evaluation guide](../05_Software/aegis/evaluations/README.md)
defines the fixtures, transport, predicates, provenance and semantic review.
Ten core cases exercise Frame, Validate and task-record resume. Fifteen
capability cases add Specify, Design, Build, closing a validated task, one
adoption component, enabled/disabled review, diagram settings, autopilot and
stale-context repair. Six hold-out cases use a second domain whose cases never
shaped a prompt rule; one of them carries a feature through five fresh sessions
on one repository and checks the result with a hidden acceptance test. Common
`.agentic/AGENTS.md` guidance and the task template participate in the same
fixtures; their individual causal contribution is not isolated.

A local runner drives an OpenAI-compatible Chat Completions server, with
optional reasoning effort; a subscription runner drives a native Codex CLI.
The evaluation folder keeps the latest `gpt-6-luna` subscription baselines;
other runs keep their raw evidence outside the repository.

Read strict grades with the semantic assessments. Some predicates are overly
literal or use checkpoint conventions for bounded autopilot transitions. In
autopilot, saving diagrams and reporting their path without displaying blocks is
the contract, not a display defect. Other failures are real model/tool errors;
do not remove them as infrastructure noise. External provider capacity,
transport, timeout and output-collection failures are excluded from comparable
semantic outcomes, while controlled fixture failures remain test stimuli.

Keep model, reasoning, configured context, actual output usage, response-cap
availability and elapsed time with every observation. The native response cap
and server context allocation are unexposed; a tool-output allowance is not a
model response cap. Collection uses pauses and bounded generic-429 backoff;
semantic failures are not selectively retried. Compare frozen whole cohorts
with unchanged scenarios/evaluator and report any intentionally changed reviewer
inputs.

Actual reviewers run in distinct fresh sessions against an immutable snapshot;
writing two approval fields alone is insufficient. Coverage remains bounded:
one chained lifecycle, and no adoption survey/close, native GUI discovery or
every-host role-routing acceptance in these scenarios.

## Builders and distribution

| Builder | Output |
|---|---|
| `python 02_Tools/build_aegis_release.py --version <x.y.z>` | Core Windows/Linux archives, checksums and build records under `07_Delivery/aegis-<version>/`, with matching source/changelog version. |
| `node 02_Tools/build_agent_plugins.mjs --output <fresh-output-directory>` | Five complete host-package directories, including shared libraries and launchers, using the existing core version. |

Distribute a complete assembled directory or an archive of it. Each recipient
installs into their own host profile and authenticates independently. Source
version assignment, local package construction, host installation and external
publication have separate outcomes and authority.

## Maintenance

1. Keep managed templates generic and project facts in project-owned files.
2. Preserve the assigned version unless a version change is requested.
3. Update current planning, user guides and affected generated companions with
   workflow, command, configuration or artifact changes.
4. Use behavior tests for executable changes and direct semantic/link/layout
   review for documentation-only changes.
5. Keep documentation-only maintenance and release operations outside AEGIS
   task governance.
6. Preserve the user's dirty work and require applicable authority for Git and
   external actions.
7. Keep dated verification evidence in task/build records and current guidance
   in these documents.
