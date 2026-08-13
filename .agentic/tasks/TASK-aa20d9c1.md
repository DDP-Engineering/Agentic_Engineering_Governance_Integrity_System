<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-aa20d9c1 — Make Delivery recovery guidance self-contained

stage: deliver
type: fix
path: full
requirements: REQ-FUNC-0ed3f1b4
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [ ] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed only after the outcome succeeded

## Log

- 2026-08-13 frame: scope is only independently confirmed G-03, making both existing Delivery terminal-precondition errors self-contained through exact corrective operations, fixed fields, bounded next actions, and matching shipped Delivery guidance without weakening either check.
- 2026-08-13 frame: exclusions are every other review finding, both review directories, pre-existing dirty planning files, all AEGIS Light implementation/payload/plans/managed files, global input-schema or error-envelope work, new gates, broad next-action changes, VoiceWeaver mutation, Git staging/branching/commit/push, and unrelated or concurrent work including G-01/G-02.
- 2026-08-13 frame: full path chosen because machine errors and workflow guidance change externally visible behavior; explicit user instruction keeps the checkout on master instead of creating a task branch, and autopilot continues through build and validate.
- 2026-08-13 frame: existing REQ-FUNC-0ed3f1b4 and authoritative PR-DELIVERY-001..004, PR-POSTURE-002, PR-ESCAPE, PR-MODEL, FS-DELIVERY, FS-INTERFACE, CP-MODEL-003/004, and CP-STAGE cover the behavior; no new requirement is proposed.
- 2026-08-13 frame confirmation: current Delivery completion still enforces exact approval and terminal assessment values, but both error results have empty next_actions and shipped delivery.toml omits the exact correcting operations and inputs.
- 2026-08-13 specify: reused active REQ-FUNC-0ed3f1b4 unchanged because the full-AEGIS planning contract already defines approval-controlled truthful closure, and the user's scope excludes traceability-only AEGIS Light requirement edits.
- 2026-08-13 specify: no specification artifact is needed because G-03 directly defines both error messages, atomic corrective action shapes, allowed assessment values, and compatibility boundaries.

## Design

- Components: full-AEGIS workflow application and shipped Delivery definition only (REQ-FUNC-0ed3f1b4; PR-DELIVERY-001..004; CP-STAGE-004).
- Interface: each existing Delivery `stage.complete` precondition error names the exact corrective operation and required fixed input and returns one immediate atomic next action (CP-MODEL-003/004; FS-INTERFACE-001/005).
- Data: approval recovery fixes `value=approved` and `target=delivery` while leaving actor/reason caller supplied; assessment recovery fixes `section=terminal_result` and exposes all three content choices without selecting one (PR-DELIVERY-002/003; FS-DELIVERY-003/005).
- Compatibility: both terminal truthfulness checks and all advisory behavior remain unchanged; no new refusal, registry schema, or global next-action mechanism is introduced (PR-POSTURE-002; PR-ESCAPE; PR-DELIVERY-004).
- Rejected alternative: removing either check would make terminal Delivery untruthful, while a global error/input-schema sweep would exceed G-03 and overlap later review findings.
- Test seam: drive a synthetic installed short-profile Run to active Delivery, trigger the approval error, record the exact approval decision, then trigger the terminal assessment error and assert both full response contracts.
- Expected files: `workflow_operations.py`, `workflows/delivery.toml`, `test_delivery_adoption.py`, root changelog if required by repository policy, payload manifest metadata, and this journal.
- 2026-08-13 design: the journal note is sufficient; no separate spec or AEGIS Light requirement edit is warranted.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_delivery_adoption.py::test_delivery_gate_errors_name_their_required_input`; exit=1; expected missing behavior=the first Delivery precondition error names neither `decision.add`, value `approved`, nor target `"delivery"` and provides no corrective next action.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_delivery_adoption.py::test_delivery_gate_errors_name_their_required_input tests/test_delivery_adoption.py::test_approved_delivery_atomically_completes_stage_run_and_pointer tests/test_delivery_adoption.py::test_delivery_latest_applicable_decision_must_be_approved`; exit=0; result=3 passed in 22.19s after preserving the latest-decision wording contract.
- 2026-08-13 build impacted: `python .agentic/aegis.py test --impacted` was not run because unchanged AEGIS Light requirement traceability would fall back to the explicitly deferred complete AEGIS suite; no full-suite result is claimed.
- 2026-08-13 build scope exception: REQ-FUNC-0ed3f1b4 remains active and unchanged by explicit user instruction, so its affected_paths and linked_tests were not expanded merely for AEGIS Light traceability.
- 2026-08-13 build check: command=`python .agentic/aegis.py check`; exit=0 with 55 advisory warnings limited to pre-existing/excluded/concurrent files plus expected outside-layout, stage-zone, scope-drift, and uncovered-source notices; no excluded file was changed for those warnings.
- 2026-08-13 build: payload manifest regenerated from checkout-canonical bytes with product_version=1.0.0 and platform=windows after the runtime and workflow changes.
- 2026-08-13 validate review: the scoped G-03 diff preserves both terminal truthfulness preconditions, retains latest-decision semantics, gives each error one atomic correction, exposes all assessment choices without choosing one, and introduces no new gate, registry schema, or unrelated next-action change.
- 2026-08-13 validate knowledge: REQ-FUNC-0ed3f1b4 and the AEGIS workflow application knowledge page were re-read and remain true without traceability-only edits; the full-AEGIS README and root changelog document the externally visible error and guidance contract.
- 2026-08-13 validate focused: command=`uv run --group dev python -m pytest -q tests/test_delivery_adoption.py::test_delivery_gate_errors_name_their_required_input tests/test_delivery_adoption.py::test_approved_delivery_atomically_completes_stage_run_and_pointer tests/test_delivery_adoption.py::test_delivery_latest_applicable_decision_must_be_approved`; exit=0; result=3 passed in 21.07s on final runtime, workflow, and test bytes.
- 2026-08-13 validate static: `python -m py_compile` for the touched runtime and test modules, touched-file `ruff check`, `uv run --group dev python -B -m aegis --help`, direct payload `verify_payload()`, workflow TOML parsing/bounded-guidance inspection, and scoped `git diff --check` all exited 0.
- 2026-08-13 validate format caveat: optional `ruff format --check` exited 1 only because cumulative pre-existing lines in workflow_operations.py and test_delivery_adoption.py would be reformatted; no unrelated formatting rewrite was applied, while Ruff lint is green.
- 2026-08-13 validate payload: direct verification reported product_version=1.0.0, platform=windows, 57 owned files, and zero findings; Delivery guidance is 401 characters with four recovery actions and contains every required operation, field, and value.
- 2026-08-13 validate strict: command=`python .agentic/aegis.py check --task TASK-aa20d9c1 --strict`; exit=0; result=strict ok with 41 advisory warnings limited to pre-existing/excluded/concurrent files and expected outside-layout or uncovered-source notices from the explicit no-traceability-edit scope.
- 2026-08-13 validate deferral: the complete AEGIS suite and `check --strict --run` were not run because the user explicitly deferred the complete suite until campaign end, and no full-suite green result is claimed.
- 2026-08-13 validate live smoke: no VoiceWeaver mutation was attempted because the synthetic installed-repository regression exercises both Delivery obstruction routes without risking live project state; VoiceWeaver history remains untouched.
- 2026-08-13 review regression: parent command=`uv run --group dev python -m pytest -q tests/test_delivery_adoption.py::test_delivery_gate_errors_name_their_required_input tests/test_delivery_adoption.py::test_delivery_latest_applicable_decision_must_be_approved tests/test_run_stage_workflow.py::test_shipped_workflow_guidance_has_bounded_advisory_shape`; exit=1; result=1 failed and 2 passed because delivery.toml was 1736 bytes against the existing 1600-byte budget, so the task returned to build.
- 2026-08-13 rebuild: compressed delivery.toml from 1736 to 1580 bytes without changing its four recovery operations or omitting the exact approval, terminal assessment, caller-supplied field, incomplete-report, or revisit guidance.
- 2026-08-13 rebuild green: command=`uv run --group dev python -m pytest -q tests/test_delivery_adoption.py::test_delivery_gate_errors_name_their_required_input tests/test_delivery_adoption.py::test_delivery_latest_applicable_decision_must_be_approved tests/test_run_stage_workflow.py::test_shipped_workflow_guidance_has_bounded_advisory_shape`; exit=0; result=3 passed in 13.86s on the regenerated cumulative payload bytes.
- 2026-08-13 rebuild manifest: regenerated with product_version=1.0.0 and platform=windows after the final 1580-byte Delivery workflow change.
- 2026-08-13 rebuild deferral: no impacted or full-suite command was run because the complete suite remains explicitly deferred and prohibited for this correction.
- 2026-08-13 revalidate review: the compressed Delivery workflow remains self-contained and advisory, preserves all four recovery meanings and exact fixed inputs, changes no test budget or runtime behavior, and is 20 bytes below the existing limit.
- 2026-08-13 revalidate static: `python -m py_compile` for the three focused Python modules, focused `ruff check`, `uv run --group dev python -B -m aegis --help`, direct payload `verify_payload()`, and scoped `git diff --check` all exited 0.
- 2026-08-13 revalidate payload: product_version=1.0.0, platform=windows, 57 owned files, zero findings, and delivery.toml=1580 bytes after final manifest regeneration.
- 2026-08-13 revalidate strict: command=`python .agentic/aegis.py check --task TASK-aa20d9c1 --strict`; exit=0; result=strict ok with the same 41 pre-existing/excluded or expected no-traceability-edit warnings.
- 2026-08-13 revalidate deferral: the complete suite and `check --strict --run` remain unrun by explicit instruction, and no full-suite result is claimed.
