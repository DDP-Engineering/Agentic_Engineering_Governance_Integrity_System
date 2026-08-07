# WP0 Implementation Record

- Date: 2026-08-07
- Initial implementation commit: `ad33af3`
- Correction agent host: Codex
- Exact correction model: current task model; not exposed in the task record
- Reasoning level: current task setting; not exposed in the task record
- Starting branch: `AEGIS_V2`
- Starting tracked state: clean at `ad33af3`
- Starting untracked paths:
  - `00_Planning/AEGIS_HEAVY_IMPROVEMENT_2026-08-07/`
  - `00_Planning/AEGIS_REVIEW_2026-08-06/`

## Scope

Close the findings from the independent review of WP0 without beginning WP1:

- make WAEGIS adoption propose the shared `latest` retention default;
- remove copied claims about generated checklists and bounded stage context that
  are not implemented until WP1/WP2;
- make fresh-session recovery follow the state-aware `run status` `next`
  command without re-preparing an applied stage;
- correct unsupported alignment/design skip guidance;
- synchronize maintained retention documentation and the root changelog;
- make clean-checkout validation use managed environments;
- preserve a clean copied template during test collection and CLI validation.

## Red observation

### WAEGIS adoption default

Command:

```powershell
uv run --group dev python -m pytest -q tests/test_waegis_v1.py::test_adoption_proposes_shared_latest_retention_default
```

Observed before the implementation change:

```text
1 failed
assert 'discard' == 'latest'
```

### Copied guidance and maintained defaults

Command:

```powershell
uv run --group dev python -m pytest -q tests/test_documentation_workflow.py::test_template_fresh_session_guidance_matches_current_form_contract tests/test_documentation_workflow.py::test_maintained_documentation_names_latest_as_retention_default
```

Observed before the documentation changes:

```text
2 failed
```

The failures identified the premature generated-checklist claim, unsupported
skip semantics, and maintained documentation that still named `discard` as the
default.

### Release hygiene

The first complete AEGIS run reported `569 passed, 3 skipped, 1 failed`. The
failure found generated `__pycache__`/`.pyc` files inside the copied template.
The suite now disables bytecode writes during collection while continuing to
reject any pre-existing cache. CLI help uses Python `-B` for the same reason.

## Changes

- `waegis.commands.adopt._seeded_workflow_specs` now proposes `latest`.
- A direct adoption-path regression test protects the proposal instead of
  testing only the shared generator default.
- Template `AGENTS.md` now describes a state-aware restart: `run status` is
  authoritative, and `stage prepare` runs only when the reported `next` command
  requests it. Applied stages remain applied and proceed to review/close.
- Alignment is bypassed only by the quick profile; a full run always includes
  it.
- Design is bypassed only by the quick profile; a trivial full-run design stays
  brief but still satisfies its required form and document contract.
- AEGIS/WAEGIS READMEs, template setup/configuration/upgrade guides, and deep
  software documentation name `latest` as the shipped default.
- Root and package validation commands use `uv run --group dev`; CLI help also
  uses `-B` so it does not dirty copied payload material.
- `tests/conftest.py` prevents test imports from creating bytecode in the copied
  template while leaving pre-existing cache visible to release-hygiene tests.
- Documentation command coverage extracts invocations from both template
  `AGENTS.md` and all seven development-stage references, including fenced and
  inline examples, and validates every extracted command through the real CLI
  parser.
- Every development-stage reference makes `stage prepare` conditional on the
  state-aware `run status` `next` value. Regression states cover applied close,
  external check evidence, and validation verification so none routes through a
  new prepared revision.
- Repository documentation coverage rejects CLI validation commands that omit
  `-B` or invoke the editable entry point directly.
- Root `CHANGELOG.md` records the default and guidance correction under
  Unreleased. The downstream `template/CHANGELOG.md` remains empty.

## Validation

Focused AEGIS documentation/CLI tests:

```text
36 passed
```

The documentation command audit covers 26 distinct `<workflow>` invocations
from template `AGENTS.md` and the seven development-stage references.

Focused lifecycle/quick/gate/traceability tests:

```text
116 passed
```

Focused WAEGIS adoption tests:

```text
26 passed
```

Complete AEGIS suite:

```text
571 passed, 3 skipped
```

Complete WAEGIS suite:

```text
699 passed, 8 skipped
```

Managed CLI validation:

```powershell
uv run --group dev python -B -m aegis --help
uv run --group dev python -B -m waegis --help
```

Both commands passed. `python -m py_compile` passed for every Python file
changed by the correction.

## Context effect

No generated checklist or compact context command was added. The correction
removes premature context claims; WP1 and WP2 retain ownership of the canonical
checklist and measured context-pack work. No context-budget acceptance is
claimed in WP0.

## Review

- Initial review source: fresh-task findings supplied as an attachment
- Initial findings received: 2 high, 4 medium
- Follow-up review source: applied-stage restart findings supplied as an
  attachment
- Follow-up findings received: 1 high, 2 medium, and 1 workspace validation
  blocker
- Resolution: all initial and follow-up findings are addressed in the correction
  boundary
- Re-review: completed by an independent agent; no blocking findings remain and
  WP0 is safe to commit

## Remaining risk

- No known blocking WP0 risk remains.
- WP1 has not started and remains a separate implementation boundary.
