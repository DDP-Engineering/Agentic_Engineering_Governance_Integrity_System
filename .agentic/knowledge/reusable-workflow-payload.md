<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Reusable workflow payload

## Routing

Use this page for core workflow stages, adoption, artifact scaffolding, current
project context, resume guidance, and the optional design diagrams (`[diagrams]`,
`steps/diagrams.md`, `diagram_TASK-<id>.md`). Start with
`05_Software/aegis/template/.agentic/AGENTS.md` and the affected step/template;
CLI scaffolding and brief rendering live in `aegis.py`. Focused verification
starts in `test_cli_core.py`, `test_run_report.py`, and `test_structure.py` under
`05_Software/aegis/tests/`. Host bridge behavior belongs to the integration
source and tests under `05_Software/aegis/integrations/`.

## Purpose and boundaries

The canonical payload is the generic, copyable AEGIS workflow distributed to
other repositories. It contains the operator contract, task stages, adoption
procedure, the optional design diagram guide, generic artifact templates, CLI
reference, and implementation.
Each downstream project owns its context, requirements, component pages and
task records. The payload keeps one six-stage workflow: optional children,
configured interaction, durable rulings, a current handoff, optional bounded
review and optional design diagrams enrich the existing journal without adding
a stage or service. Repository maintenance and delivery tooling live in `02_Tools/`.

## Invariants

- Initialization preserves each existing project context file byte-for-byte.
- The configuration initialization writes names every key the CLI reads,
  live or as a commented default with its rationale.
- Project context, component pages and active contracts describe current
  positive behavior; draft records hold proposals and journals retain history.
- Current documentation is reconciled with exact evidence and authorized
  intent; established contracts remain binding when implementation disagrees.
- The managed payload stays generic and the installed project owns its facts.
- Design diagrams illustrate a proposal for the human; no stage completion,
  validation step, review verdict or check finding depends on them, and the
  Design text stays authoritative.

## Public interface

Downstream repositories copy `template/.agentic/` to `.agentic/` and run
`python .agentic/aegis.py init`. Agents use `AGENTS.md` and the stage files to
perform ordinary work or component-by-component adoption, while the templates
define durable artifact formats.

## Key behaviors

- `REQ-FUNC-d60b322b` - Guide ordinary work through separated workflow stages.
- `REQ-FUNC-32fe33a0` - Guide component-by-component repository adoption.
- `REQ-FUNC-b8f0efc5` - Provide durable workflow artifact templates.
- `REQ-FUNC-87aea7e9` - Scaffold missing project/environment context at init
  while preserving project-owned files.
- `REQ-PLAT-e675406e` - Ship a complete self-contained offline workflow
  payload.
- `REQ-UX-ccb4ca06` - State material development and verification departures
  when they happen without turning corrected internal tool errors into
  deviations or pausing the work.

- `REQ-FUNC-ee1d2096` - Where `[diagrams] enabled = true`, draw Mermaid
  diagrams of the proposed implementation at design into
  `.agentic/tasks/diagram_TASK-<id>.md`, linked once from `## Design`.
- `REQ-UX-b0bd0225` - Show those diagrams at the design checkpoint, after the
  stage summary and before the stage-boundary choices.
- `REQ-FUNC-f7220cb2` - Keep diagram generation off unless `enabled` is the
  Boolean `true`.
- `REQ-FUNC-6343dfb8` - Keep diagrams outside every stage obligation, review
  verdict and check finding.

- `REQ-UX-84868466` - Present a consistent report and concrete next choices at
  checkpoint boundaries without deferring deviation notices.
- `REQ-UX-94a33d75` - Resume from compact reporting and relevant durable
  records while preserving required full reads and unresolved issues.
- `REQ-FUNC-3bc8597c` - Keep optional child work one level deep, independently
  governed, and integrated by its visible parent candidate.
- `REQ-FUNC-e55c43d1` - Start re-entry with a deterministic bounded brief.
- `REQ-FUNC-9514e017` - Record two optional independent review verdicts.
- `REQ-FUNC-cbff6478` - Bound fix and re-review cycles before human escalation.
- `REQ-FUNC-7ea14fe4` - Preserve append-only rulings and a replaceable handoff.

Every stage file includes brief-first resume, report, ruling, handoff and
stage-choice reminders. The task template provides compatible interaction,
parent and review fields,
append-only rulings, one replaceable handoff, and a replaceable latest report
beside the append-only log. Checkpoint mode stops after every stage by default;
configured autopilot flows between stages while publication approval remains.

The project profile and environment guide live under `.agentic/context/`.
Frame/adoption populates current facts, build updates affected facts as changes
become real, and validate reconciles them. Brief exposes their paths and presence
for selective loading. Component pages route deeper implementation discovery.

## Files

- `05_Software/aegis/template/.agentic/AGENTS.md` - Workflow contract and
  operator prompts.
- `05_Software/aegis/template/.agentic/CLI.md` - CLI contract and examples.
- `05_Software/aegis/template/.agentic/steps/` - Ordinary-work and adoption
  procedures, plus the optional design diagram guide `diagrams.md`.
- `05_Software/aegis/template/.agentic/templates/` - Durable artifact
  scaffolds.
- `05_Software/aegis/template/.agentic/LICENSE.txt` - Payload license.
- `05_Software/aegis/tests/test_structure.py` - Payload invariants and
  structural regression tests.
- `05_Software/aegis/tests/test_cli_core.py` - Initialization and scaffolding.
- `05_Software/aegis/tests/test_run_report.py` - Bounded resume reporting.
