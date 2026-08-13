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
- Keep the runnable AEGIS implementation under `05_Software/aegis/` and the
  runnable WAEGIS guided wizard under `05_Software/waegis/`. WAEGIS is a
  separate, stdlib-only package that configures and deploys the AEGIS payload;
  it is never copied into `05_Software/aegis/template/`.
- Treat everything under `05_Software/aegis/template/` as
  template material copied verbatim into downstream projects. Keep it generic
  and free of this repository's own development history, version records, or
  project-specific facts. In particular, `template/CHANGELOG.md` is a downstream
  starter and must stay empty (no release entries).
- Keep folder boundaries clear across planning, documentation, tools,
  hardware, hardware documentation, software, software documentation, delivery,
  and support material.
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
only, tracked in `aegis`'s `__init__.__version__` / payload version, `waegis`'s
`version.py` `WIZARD_VERSION`, and the existing changelogs.

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
uv run --group dev python -m pytest -q tests
```

For CLI changes, also verify:

```powershell
uv run --group dev python -B -m aegis --help
```

For Python changes inside `05_Software/waegis/`, run at minimum:

```powershell
python -m py_compile <changed_file.py>
uv run --group dev python -m pytest -q tests
uv run --group dev python -B -m waegis --help
```

When behavior changes:

- add or update targeted tests
- prefer focused tests before broad runs
- state what was validated and what remains unverified

## Versioning and Changelog Rules

- The repository-root `CHANGELOG.md` is the canonical record of all template
  project updates. Accrue changes under `## [Unreleased]` using Keep a Changelog
  sections (Added, Changed, Fixed, Removed).
- When the user gives a command such as "assign a version to the changelog", in
  the same change:
  1. roll `## [Unreleased]` into a new dated `## [x.y.z] - YYYY-MM-DD` section in
     the root `CHANGELOG.md`;
  2. bump the project/template version to that same `x.y.z` in every version
     declaration under `template/` (currently
     `template/.agentic/cli/pyproject.toml` and `template/.pi/package.json`;
     if a future versioned `template/.opencode/package.json` is added, keep it
     in sync too), keeping them in sync;
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

<!-- AEGIS-LIGHT:BEGIN (managed by .agentic/aegis.py init) -->

## AEGIS Light workflow

The full contract is `.agentic/AGENTS.md` - read it before starting work.
This digest is enough to act on if you read nothing else.

Stages, one step file each in `.agentic/steps/`: **frame** (agree scope,
open the task journal) -> **specify** (write the requirement, and a spec
when useful) -> **design** (a short note for non-trivial work) -> **build**
(failing test first, then the implementation, until green) -> **validate**
(review, knowledge, full suite and strict check) -> **deliver** (approval,
report, commit/PR). A small fix or change may take the quick path,
frame -> build -> validate -> deliver.

To resume: `python .agentic/aegis.py status` lists the task journals; open
`.agentic/tasks/TASK-<id>.md`, read its `stage:` line and `## Log`, open
that stage's step file, and continue at the first unticked item of
`## Done checklist`.

Artifacts: requirements in `.agentic/requirements/<category>/`, specs in
`.agentic/specs/`, journals in `.agentic/tasks/`, component pages in
`.agentic/knowledge/`. `python .agentic/aegis.py check` is advisory - read
its findings and self-correct; nothing here blocks you mid-flight.

<!-- AEGIS-LIGHT:END -->
