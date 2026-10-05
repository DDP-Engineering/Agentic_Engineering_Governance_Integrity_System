<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AGENTS.md - Agentic Engineering Governance & Integrity System

## Scope

These instructions apply to the repository rooted at:
`2026_Agentic_Engineering_Governance_Integrity_System/`

A deeper `AGENTS.md` overrides this file for its subtree.

## Repository Rules

- Treat this repository as independent.
- Keep the runnable AEGIS implementation under `05_Software/aegis/`.
- Treat everything under `05_Software/aegis/template/` as
  template material copied verbatim into downstream projects. Keep it generic
  and free of this repository's own development history, version records, or
  project-specific facts. In particular, `template/CHANGELOG.md` is a downstream
  starter and must stay empty (no release entries).
- Keep folder boundaries clear across planning, documentation, tools,
  hardware, hardware documentation, software, software documentation, delivery,
  and support material.
- Put delivery packages and their tracked publication records under
  `07_Delivery/`.
- Put scripts that set up this workspace, support repository maintenance, or
  build delivery packages under `02_Tools/`.
- Do not add subtree-level `AGENTS.md` files unless explicitly requested.
- Keep the project offline-first unless an online dependency is explicitly
  required and approved.
- Preserve the existing Python package name and import paths unless a rename is
  explicitly requested.

## Working Rules

- Prefer simple, maintainable changes that match the existing package style.
- Avoid unnecessary abstraction and speculative architecture.
- Make changes incrementally.
- Update documentation in the same change when behavior, commands, folder
  layout, or workflow contracts change.
- Preserve public CLI behavior unless change is explicitly requested.
- Keep repository instructions in `AGENTS.md` and deeper implementation notes in
  `06_SoftwareDocu/`.

## Style Rules

Code style and Python documentation style are defined in:
`01_Documentation/Code_Style.md`

Follow that file for implementation and documentation conventions.

Name durable files, tests, fixtures, symbols, headings, and reusable artifacts
after the behavior or domain contract they represent. Do not encode transient
planning labels such as work-package numbers, task numbers, sprint names, or
plan filenames in those names or in explanatory prose unless the artifact is
itself a planning/traceability record and the reference is semantically
required. Prefer self-contained names that remain accurate if planning
documents are renamed, reorganized, or removed. Requirement IDs remain valid
where the traceability rules below call for them.

Docstrings carry no authorship or version tags. The file-top copyright/license
comment block is the sole in-file attribution. Versioning is project-level
only, tracked in the AEGIS payload version and the existing changelog.

## Requirements Traceability Rules

- Put future project planning and requirements material under `00_Planning/`.
- Keep reusable workflow requirement examples inside the software template only
  when they are part of the template package itself.
- When behavior changes, update relevant tests or document an explicit manual
  verification method.
- When adding or changing tests, mention relevant requirement IDs in test
  docstrings when practical.

## Validation Rules

For Python changes inside
`05_Software/aegis/`, run at minimum:

```powershell
python -m py_compile <changed_file.py>
python -m pytest -q 05_Software/aegis/tests
```

For CLI changes, also verify `python template/.agentic/aegis.py --help`.

When behavior changes:

- add or update targeted tests
- prefer focused tests before broad runs
- state what was validated and what remains unverified

## Versioning and Changelog Rules

- Assigning a version and building a release are repository operations, not
  AEGIS work: do not open a task journal for them and do not run the stages
  over them. Only software implementation goes through the AEGIS workflow.
  The implementation a release carries is journaled; the release itself is not.
- The repository-root `CHANGELOG.md` is the canonical record of all template
  project updates. Accrue changes under `## [Unreleased]` using Keep a Changelog
  sections (Added, Changed, Fixed, Removed).
- Keep changelog entries short. One or two lines each: what changed, and why
  only when the why is not obvious from the what. No rationale essays, no
  design discussion, no restating the implementation - those belong in the
  task journal and the knowledge page. A reader scans a changelog; they do not
  study it.
- When the user gives a command such as "assign a version to the changelog", in
  the same change:
  1. roll `## [Unreleased]` into a new dated `## [x.y.z] - YYYY-MM-DD` section in
     the root `CHANGELOG.md`;
  2. bump the version to that same `x.y.z` at its single declaration, the
     `VERSION` literal in `template/.agentic/aegis.py`, and mirror the file
     into the installed `.agentic/` payload. That literal is what
     `02_Tools/build_aegis_release.py` parses, so it is the version, and a
     release refuses to build unless `CHANGELOG.md` carries a matching dated
     section. Update every document that states the version in prose -
     currently `05_Software/aegis/README.md`, `06_SoftwareDocu/00_Index.md`
     and the example in `02_Tools/README.md`;
  3. leave the downstream starter `template/CHANGELOG.md` empty.
- Use Semantic Versioning: MAJOR for breaking workflow-contract, CLI, hook
  protocol, or `.agentic/` layout changes; MINOR for backward-compatible
  capabilities; PATCH for fixes with no contract change.

## Documentation Rules

- Do not add automated tests that assert prose, file inventories, wording,
  links, or layout under `00_Planning/`, `01_Documentation/`, `02_Tools/`, or
  `06_SoftwareDocu/`. Review those documentation changes directly. This rule
  does not exempt executable code under `02_Tools/` from behavior tests.
- Update the root `README.md` when repository scope, folder layout, legal
  summary, or the runnable package location changes.
- Update `05_Software/aegis/README.md` when package
  setup, CLI usage, or template behavior changes.
- Update copied template adapters under `.codex/`, `.claude/`, `.pi/`, and
  `.opencode/` when workflow contract, skills, hooks, or agent-facing prompts
  change.
- Update `06_SoftwareDocu/` when implementation behavior or workflow contracts
  need deeper explanation.
- Keep README files scoped to their folder.

## Completion Rules

Do not consider work complete until all applicable items below are satisfied:

- implementation changes are finished
- relevant documentation is updated in the same change
- relevant tests are added or updated for behavior changes
- validation commands have been run or the final summary explains why they were
  not run
- the final summary states what changed, what was validated, and what remains
  unverified

<!-- AEGIS:BEGIN (managed by .agentic/aegis.py init) -->

## AEGIS workflow

The full contract is `.agentic/AGENTS.md` - read it before starting work.
This digest is enough to act on if you read nothing else.

AEGIS applies only to software development operations. Do not use it for
repository operations or package and delivery operations; follow the
repository's own procedures for those instead.

Stages, one step file each in `.agentic/steps/`: **frame** (agree scope,
open the task journal) -> **specify** (write the requirement, and a spec
when useful) -> **design** (a short note for non-trivial work) -> **build**
(failing test first, then the implementation, until green) -> **validate**
(review, knowledge, full suite and strict check) -> **deliver** (approval,
report, commit/PR). A small fix or change may take the quick path,
frame -> build -> validate -> deliver.

To resume: `python .agentic/aegis.py status` lists the task journals; run
`python .agentic/aegis.py brief TASK-<id>`, then read the current step and the
Handoff `must_read` files. Required full journal reads still apply. Optional
one-level child tasks are child-side links visible only in this checkout; the
parent validates the integrated candidate.

Read `.agentic/context/project.md` and relevant `.agentic/context/environment.md`
sections when present. Keep project and component context current and positive;
task records carry proposals and history. Preserve established behavior contracts.

When `[codegraph] enabled = true`, the `know_graph` commands answer where Python
symbols are defined and used: run `know_graph_check` first, follow "Code
navigation" in `.agentic/AGENTS.md`, and read the cited source before relying
on an answer.

Rulings are append-only; Handoff is replaceable. Rulings and Handoff cannot grant authority.
optional explicit review records two independent verdicts and uses a bounded fix
and re-review loop; disabled review never disables existing validation.

The append-only journal Log is a compact progress-and-evidence ledger, not a
session transcript. Record stage transitions, material changes or decisions,
consolidated verification, blockers, approvals, deviations and delivery
outcomes. Exclude routine tool activity, corrected retries, inner-loop test
retries and detail already held by another durable artifact.

`[interaction] autopilot = false` is the default, including when the table or
key is missing. Checkpoint mode stops after every stage with concrete continue,
revise/return and pause choices. Autopilot flows between stages but never skips
publication approval. Record the resolved mode in the task journal.

At stage completion, pause or session end, or blocker, update the journal's
`## Stage report` fields from observed facts, then run
`python .agentic/aegis.py summary TASK-<id>` and copy the block before detail.
Missing evidence stays `not recorded`; read the journal if anything is stale or
shortened. Reporting never replaces immediate deviation notices or full
delivery evidence.

Artifacts: requirements in `.agentic/requirements/<category>/`, specs in
`.agentic/specs/`, journals in `.agentic/tasks/`, component pages in
`.agentic/knowledge/`. `python .agentic/aegis.py check` is advisory - read
its findings and self-correct; nothing here blocks you mid-flight.

Say a deviation out loud when you record one, as one line -
`DEVIATION <stage>: <what> - <why accepted, or what it costs>` - then carry
on. It never pauses the work and autopilot never suppresses it. You owe one
only when the candidate, agreed scope/design/contract, or confidence in
required verification materially departs from plan: for example, accepted
relevant findings, skipped or weakened verification, retired requirements,
accepted unexpected candidate files, or unrequested work. Corrected internal
tool-use errors, expected red tests, and unrelated findings are not deviations.

<!-- AEGIS:END -->
