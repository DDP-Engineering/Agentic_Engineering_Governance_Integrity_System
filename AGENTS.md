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
  project-specific facts.
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

Code style is defined in `01_Documentation/Code_Style.md`.

Follow that file for implementation and documentation conventions.

Name durable files, tests, fixtures, symbols, headings, and reusable artifacts
after the behavior or domain contract they represent. Do not encode transient
planning labels such as work-package numbers, task numbers, sprint names, or
plan filenames in those names or in explanatory prose unless the artifact is
itself a planning/traceability record and the reference is semantically
required. Prefer self-contained names that remain accurate if planning
documents are renamed, reorganized, or removed. Requirement IDs remain valid
where the traceability rules below call for them.

Docstrings carry no authorship or version tags. Licensing is declared once in
`REUSE.toml`: files carry no license header, except the payload under
`05_Software/aegis/template/.agentic/`, which keeps a short SPDX tag because it
is copied into other repositories. Versioning is project-level
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

Versions, the changelog and version assignment follow
`01_Documentation/Releases.md`. They are repository operations, not AEGIS work.

## Documentation Rules

- Do not add automated tests that assert prose, file inventories, wording,
  links, or layout under `00_Planning/`, `01_Documentation/`, `02_Tools/`, or
  `06_SoftwareDocu/`. Review those documentation changes directly. This rule
  does not exempt executable code under `02_Tools/` from behavior tests.
- Update the root `README.md` when repository scope, folder layout, legal
  summary, or the runnable package location changes.
- Update `05_Software/aegis/README.md` when package
  setup, CLI usage, or template behavior changes.
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
