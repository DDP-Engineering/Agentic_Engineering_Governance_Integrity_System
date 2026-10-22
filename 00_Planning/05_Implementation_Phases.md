<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# 05 - Current implementation

The assigned source version is **AEGIS 0.14.0**. This page describes current
capabilities, source ownership and verification methods. Release history is in
the [changelog](../CHANGELOG.md); dated build evidence is retained under
`07_Delivery/`, prompt observations under the development evaluation directory,
and implementation history in Git.

## Implemented capabilities

| Area | Current behavior |
|---|---|
| Workflow | Six ordinary stages, a quick path for eligible repairs, and a separate component-by-component adoption flow. |
| Interaction | Stage checkpoints by default, optional project-configured autopilot, explicit publication authority, and immediate material deviation notices. |
| Project context | Project-owned `context/project.md` and `context/environment.md`, scaffolded independently by `init` when absent and preserved byte-for-byte when present. |
| Current documentation | Positive actual responsibilities and behavior in project/component documents and active contracts, with proposals in draft/task records and history in journals/Git. |
| Durable artifacts | Frame cards, atomic requirement coverage, task designs, TOML requirements, Markdown specs and knowledge, append-only Log/Rulings, replaceable Handoff/Stage report, and anchor/evolution evidence. |
| Companion CLI | Offline-first standard-library Python scaffolding, component discovery, traceability, configured execution and bounded reporting. |
| Verification | A 22-check advisory catalog, optional strict CI, focused/impacted test selection, dry-run previews, fallback refusal, timeouts, and complete saved evidence with optional compact presentation. |
| Coordination | Presence-only context pointers in `brief`, stage reporting through `summary`, one-level child tasks, independent review verdicts and bounded correction rounds. |
| Integrations | OpenCode, Codex, Pi, Qwen Code and Claude Code entry points backed by eleven shared adapter operations. |
| Host lifecycle | Complete package assembly, runtime discovery, owned installation/update/removal, verification jobs, duplicate prevention, cancellation and recovery. |
| Prompt evaluation | Ten core scenarios plus fifteen capability scenarios, covering all eight step guides, common contract, task records, actual reviewer sessions, diagrams, autopilot and context updates in disposable Git repositories. |

## Source ownership

```text
05_Software/aegis/
  template/.agentic/       canonical managed core
    templates/            six generic artifact templates
    steps/                six stages, adoption, diagram guide
    aegis.py              Python CLI
  integrations/           five host adapters and shared runtime
    tests/                JavaScript behavior tests
  tests/                  Python product suite and integration wrappers
  evaluations/            development scenarios, frozen comparisons and evidence
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
authorized intent. Preserve unrelated sections and established requirements.
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

The [2026-10-22 build record](../07_Delivery/aegis-0.14.0/BUILD.md) retains the
last complete product result: 548 passed, 2 skipped. Documentation-only refreshes
reuse that result only for unchanged software/test sources; it is not a fresh
test execution and does not establish prompt compliance.

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
Ten original cases exercise Frame, Validate and task-record resume. Fifteen
capability cases add Specify, Design, Build, Deliver, one adoption component,
enabled/disabled review, diagram settings, autopilot and stale-context repair.
Common `.agentic/AGENTS.md` guidance and the task template participate in the
same fixtures; their individual causal contribution is not isolated.

Recorded matched comparisons include:

| Frozen snapshot | Model / reasoning | Configured context | Strict result |
|---|---|---|---|
| [Delivery/evidence control](../05_Software/aegis/evaluations/comparisons/2026-10-22-luna-delivery-evidence/report.md) | gpt-6-luna / medium | 131,072 tokens | 21/25 |
| [Subsequent history/reviewer/node-marker candidate](../05_Software/aegis/evaluations/comparisons/2026-10-22-luna-history-protocol/report.md) | gpt-6-luna / medium | 131,072 tokens | 19/25 |
| [Exact 21/25 control replay](../05_Software/aegis/evaluations/comparisons/2026-10-22-sol-high-control-replay/report.md) | gpt-6.1-sol / high | 131,072 tokens | 21/25 |

The later candidate improves observed delivery-history preservation, reviewer
evidence interpretation and reused-node classification, but introduces other
recording, Build and checkpoint-display failures. It is not a demonstrated
overall improvement. The Sol replay uses the historical control, not that later
candidate, and changes model and reasoning together. Neither score is a general
reliability rate. The current local delivery explicitly carries the experimental
prompt revisions; a package passing software checks does not promote them to
proven prompt improvements.

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
inputs. No model was invoked for this documentation refresh.

Actual reviewers run in distinct fresh sessions against an immutable snapshot;
writing two approval fields alone is insufficient. Coverage remains bounded:
there is no complete uninterrupted lifecycle, adoption survey/close, publication,
native GUI discovery or every-host role-routing acceptance in these scenarios.

## Proposed follow-up work

Two discussed changes remain proposals, not implemented capabilities:

- A structured journal-update command could validate typed boundary fields and
  preserve legal text/history mechanically. Current stage changes use file tools;
  `summary` and `brief` remain read-only projections.
- Shorter prompts could assign shared rules one canonical owner while retaining
  stage-specific timing and critical reminders. Any shortening needs the same
  frozen-scenario comparison; fewer tokens alone does not establish improvement.

Confirmed semantic regressions and proxy limits in the recorded assessments
remain inputs for the next controlled experiment. No new flow, writer command
or prompt revision is introduced by updating these planning documents.

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
