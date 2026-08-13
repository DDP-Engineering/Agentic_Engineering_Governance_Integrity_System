<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light 0.3.0 - implementation plan

Status: **implemented and validated locally**. Date: 2026-08-12.

Scope: the AEGIS Light product under `05_Software/aegis-light/`, its release
builder at `02_Tools/build_aegis_light_release.py`, its Markdown user guides
under `06_SoftwareDocu/AEGIS-Light/`, and its design record under
`00_Planning/AEGIS_LIGHT_PLAN/`.

The independent AEGIS and WAEGIS products are out of scope. The root checkout
is shared with another agent, so their dirty files, the shared root changelog,
and the installed root AEGIS Light 0.2.0 payload are preserved.

## 1. Approved outcome

AEGIS Light 0.3.0 ships two related guidance improvements:

1. Automated red-test evidence records the exact selector or command, its
   non-zero exit code, and the expected missing-behavior failure reason in the
   task journal before implementation.
2. The former combined delivery stage becomes `validate` followed by
   `deliver`. Validation contains everything that may still change the
   candidate and performs repository-wide proof last. Delivery presents,
   reports, commits, and publishes the unchanged candidate.

No Git witness commit, new check, fingerprint, hook, or gate is introduced.
The check catalog remains at seventeen checks.

## 2. Red-test journal evidence

The 0.2.0 build step recorded a short self-attested sentence saying that a test
was red. That conveyed intent but did not preserve enough information to rerun
the observation or distinguish missing behavior from a typo, collection error,
broken fixture, or environment failure.

The 0.3.0 build step uses this compact convention:

```markdown
- 2026-08-12 build red: command=`python -m pytest -q tests/test_app.py::test_new_behavior`; exit=1; expected missing behavior=the old result is returned.
```

The agent must confirm that the failure represents the missing behavior before
implementing. The full traceback does not belong in the journal. Requirements
whose verification begins `Manual:` or `Inspection:` use a separate
post-implementation observation naming the method, action, and result.

This remains agent-authored evidence, stated honestly. Its purpose is precise,
reproducible handoff without imposing intermediate commits or Git-specific
workflow.

## 3. Six-stage lifecycle

| Stage | Purpose |
|---|---|
| `frame` | Agree scope, path, and expected requirements. |
| `specify` | Write or update durable requirements and optional specs. |
| `design` | Record the non-trivial implementation decisions and test seams. |
| `build` | Observe red, implement to green, maintain traceability links. |
| `validate` | Review and reconcile the candidate, then prove the final tree. |
| `deliver` | Present, report, commit, publish, and close out. |

The full path is `frame -> specify -> design -> build -> validate -> deliver`.
The quick path is `frame -> build -> validate -> deliver`.

### 3.1 Validate

`validate` absorbs semantic diff review, backward transitions, requirement
reconciliation, component-knowledge updates, manual observations, and the full
strict verification run. Proof happens after every candidate-changing action.
If a correction changes the candidate, the relevant review and proof repeat.

Advancing to `stage: deliver` therefore means "validated, not yet published."

### 3.2 Deliver

`deliver` is publish-only by instruction. It confirms the validated candidate
has not changed, presents the evidence and exact diff for human approval,
appends and reads the report, commits, publishes the agreed outcome, and closes
the journal only after success.

If source, tests, requirements, specs, or knowledge change or need correction,
the journal returns to `validate` and the candidate is proved again. Returning
backward is the truthful response to stale validation.

### 3.3 No delivery write zone

`DEFAULT_ZONES` deliberately does not contain `deliver`. The current
`stage-zone` heuristic examines the complete diff since the merge base; it
cannot determine which stage introduced a source or test edit. Adding
`deliver = []` would therefore warn on every legitimate build change once the
task reached delivery.

The publish-only rule stays in agent instructions and the journal transition.
No misleading mechanical signal is added.

## 4. Implementation surface

### Payload

- `template/.agentic/AGENTS.md`: six-stage table, quick path, write-zone
  explanation, interaction wording, and per-stage prompts.
- `steps/4_build.md`: reproducible red record and transition to `validate`.
- `steps/5_validate.md`: candidate review/reconciliation followed by proof.
- `steps/6_deliver.md`: approval, report, commit/PR, and truthful close-out.
- `templates/task.md`: stage vocabulary.
- `aegis.py`: version 0.3.0, pointer digest, known stages, status mappings,
  scope-drift coverage for `validate`, and no delivery zone.

### Product and release material

- `05_Software/aegis-light/README.md`: 0.3.0 behavior and stage flow.
- `02_Tools/build_aegis_light_release.py`: exact payload inventory.
- `06_SoftwareDocu/AEGIS-Light/*.md` and paired `.pptx` guides: user-facing
  stage flow, examples, and version labels.
- `00_Planning/AEGIS_LIGHT_PLAN/`: implemented design record.

The presentation files remain outside the release payload, but they are
reconciled with the paired Markdown guides so the full documentation set tells
the same 0.3.0 story.

## 5. Focused regressions

Tests establish these contracts before payload edits:

- the payload inventory contains `5_validate.md` and `6_deliver.md`;
- build guidance records exact red command/selector, non-zero exit, and
  expected failure without Git witness machinery;
- `status` resolves `validate` and `deliver` to their distinct step files;
- validation and publication responsibilities remain distinct;
- neither `validate` nor `deliver` gains a default write zone.

## 6. Verification

- Focused regressions red for the missing behavior, then green.
- Full `05_Software/aegis-light/tests` suite green on Windows: **170 passed,
  1 skipped in 56.08s**.
- `python -m py_compile template/.agentic/aegis.py` green.
- CLI help/version smoke green.
- Release-builder payload verification and dry-run archive build green.
- Structural guards remain green: standard library only, no enforcement
  machinery, advisory default exit behavior, exact payload inventory.
- Final path audit confirms no edits under `05_Software/aegis/` or
  `05_Software/waegis/` were introduced by this task.

## 7. Deliberate exclusions

- No test-only or intermediate witness commit.
- No `red-witness` check or check-catalog change.
- No history parsing, fingerprinting, or test-content hashing.
- No delivery default zone.
- No stage-transition command.
- No adoption-flow change.
- No changes to independent AEGIS or WAEGIS implementations.
- No root installed-payload upgrade, root pointer rewrite, shared changelog
  edit, commit, push, or PR in this task.
