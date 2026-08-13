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

# TASK-e1a9457f — Preserve unittest discover semantics for impacted execution

stage: deliver
type: fix
path: full
requirements: REQ-TEST-71e4e6b2
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

- 2026-08-13 frame: scope is only G-02, preserving configured `unittest discover` command semantics when `execution.run` consumes an impacted selection by executing the unchanged full suite and durably explaining the unsafe-subset fallback.
- 2026-08-13 frame: exclusions are every other review finding including F-07, both review directories, pre-existing dirty planning files, all AEGIS Light implementation/payload/managed files, configuration keys, gates, unrelated refactors, VoiceWeaver mutation, Git staging/branching/commit/push, and unrelated or concurrent work including G-01.
- 2026-08-13 frame: full path chosen because execution evidence gains externally visible effective-mode and fallback-reason facts; explicit user instruction keeps the checkout on master instead of creating a task branch, and autopilot continues through build and validate.
- 2026-08-13 frame: existing REQ-TEST-71e4e6b2 and authoritative PR-TRACE-002..005, FS-TRACE, CP-EXECUTION-001..003, FS-RESULT-001, and IP-09/IP-10 cover the behavior; no new requirement is proposed.
- 2026-08-13 specify: reused active REQ-TEST-71e4e6b2 unchanged because it already requires an explained full-suite fallback, and the user excludes AEGIS Light requirement edits made merely for traceability.
- 2026-08-13 specify: no specification artifact is needed because G-02 defines the command-shape test, unchanged-command fallback, durable explanation, and compatibility boundaries directly.

## Design

- Components: workflow application configured execution only (REQ-TEST-71e4e6b2; PR-TRACE-004; CP-EXECUTION-002/003).
- Interface: `execution.run --selection` retains its command shape and records an effective full-suite fallback when the configured test command is `unittest discover` (REQ-TEST-71e4e6b2; PR-TRACE-004/005).
- Data: execution evidence keeps the requested selection label, changes effective `selection_mode` to `full`, and adds a clear fallback reason while running the configured argv unchanged (REQ-TEST-71e4e6b2; FS-RESULT-001).
- Compatibility: pytest and direct-unittest selector arguments remain unchanged, and project results remain advisory and non-blocking (CP-EXECUTION-003; PR-CONFIG-012).
- Rejected alternative: rewriting `discover` into a direct unittest invocation could change discovery semantics and needlessly broadens the correction.
- Test seam: a synthetic installed repository configures a genuinely passing `python -m unittest discover` suite, records an impacted selection, executes it, and asserts unchanged command, passing outcome, effective full mode, and explicit reason.
- Expected files: `execution_operations.py`, `test_execution_integrity.py`, public full-AEGIS README/changelog because durable evidence semantics change, payload manifest metadata, and this journal.
- 2026-08-13 design: the journal note is sufficient; no separate spec or AEGIS Light requirement edit is warranted.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_selection_against_discover_does_not_record_failure`; exit=1; expected missing behavior=configured passing `unittest discover` received an appended impacted module, so execution evidence recorded `outcome=failed` instead of an explained full-suite fallback.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_selection_against_discover_does_not_record_failure tests/test_execution_integrity.py::test_test_execution_consumes_recorded_impacted_selection`; exit=0; result=2 passed in 11.59s, covering the discover fallback and preserved pytest selection behavior.
- 2026-08-13 build impacted: `python .agentic/aegis.py test --impacted` was not run because unchanged AEGIS Light requirement traceability would force the explicitly deferred complete AEGIS suite; no full-suite result is claimed.
- 2026-08-13 build scope exception: REQ-TEST-71e4e6b2 remains active and unchanged by explicit user instruction, so its affected_paths and linked_tests were not expanded merely for AEGIS Light traceability.
- 2026-08-13 build check: command=`python .agentic/aegis.py check`; exit=0 with 43 advisory warnings from pre-existing/excluded/concurrent files plus expected scope-drift, outside-layout, stage-zone, and uncovered-manifest notices; no excluded file was changed for those warnings.
- 2026-08-13 build: payload manifest regenerated from checkout-canonical bytes with product_version=1.0.0 and platform=windows.
- 2026-08-13 validate review: the scoped G-02 diff preserves the configured discovery argv, uses a non-blocking full-suite fallback only for `unittest discover`, durably records effective mode and reason, leaves pytest/direct-unittest branches unchanged, and contains no other review finding or AEGIS Light implementation change.
- 2026-08-13 validate knowledge: REQ-TEST-71e4e6b2 and the AEGIS workflow application knowledge page were re-read and remain true without traceability-only edits; the full-AEGIS README and changelog document the externally visible execution-evidence behavior.
- 2026-08-13 validate focused: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_selection_against_discover_does_not_record_failure tests/test_execution_integrity.py::test_test_execution_consumes_recorded_impacted_selection`; exit=0; result=2 passed in 11.16s on final runtime and test bytes.
- 2026-08-13 validate static: `python -m py_compile` for the touched runtime and test modules, touched-scope Ruff lint, `uv run --group dev python -B -m aegis --help`, direct payload `verify_payload()`, and scoped `git diff --check` all exited 0; payload verification reported product_version=1.0.0, platform=windows, and zero findings.
- 2026-08-13 validate deferral: the complete AEGIS suite and `check --strict --run` were not run because the user explicitly deferred the complete suite until the campaign ends, and no full-suite green result is claimed.
- 2026-08-13 validate live smoke: no VoiceWeaver mutation was attempted because the synthetic installed-repository regression exactly exercises the shipped runtime and configured discovery behavior without risking live project state; VoiceWeaver branch and history remain untouched.
- 2026-08-13 validate strict: command=`python .agentic/aegis.py check --task TASK-e1a9457f --strict`; exit=0; result=strict ok with 41 advisory warnings limited to pre-existing/excluded/concurrent files and expected scope-drift, outside-layout, or uncovered-source notices.
