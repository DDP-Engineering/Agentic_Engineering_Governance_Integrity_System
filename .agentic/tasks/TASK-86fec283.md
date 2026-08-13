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

# TASK-86fec283 — Implement per-stage checkpoint interaction

stage: deliver
type: feature
path: full
requirements: REQ-FUNC-ba164e6e
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

- 2026-08-13 frame: Scope confirmed by the developer is to implement the accepted per-Stage checkpoint contract across AEGIS Run state, Stage lifecycle, protocol responses, presentation, five host adapters, payload inventory, tests, and documentation, excluding AEGIS Light, VoiceWeaver, WAEGIS executable code unless unavoidable, and all outward Git operations.
- 2026-08-13 frame: Full path selected because the change adds externally observable workflow interaction, durable Run data, and machine-protocol behavior.
- 2026-08-13 frame: The current master branch is retained by explicit developer instruction despite the generic task-branch guidance.
- 2026-08-13 frame: Reuse and implement draft requirement REQ-FUNC-ba164e6e; no duplicate requirement is proposed.
- 2026-08-13 frame: The developer explicitly directed progression through implementation and final validation, with the required stop at the Delivery presentation.
- 2026-08-13 specify: Reused REQ-FUNC-ba164e6e as the single behavior requirement, replaced its planning-only inspection with automated implementation verification, and expanded its affected paths to the runtime, adapters, tests, documentation, and manifest expected to change.
- 2026-08-13 specify: No separate repository-local specification is needed because the accepted product, functional, artifact, machine-protocol, implementation, acceptance, and release documents already define the buildable contract.
- 2026-08-13 specify: `python .agentic/aegis.py check --task TASK-86fec283` exited 0 but reported five pre-existing unknown-requirement errors in TASK-44bbb4ad, plus unrelated empty-test and open-Delivery warnings; it reported no format error in REQ-FUNC-ba164e6e or this journal.

## Design

- Components: Run/Stage application policy, Run Markdown codec and resume projection, operation registry, human presenter, host starters, payload manifest, and package documentation (`REQ-FUNC-ba164e6e`).
- Interface: `run.create` accepts optional `interaction_mode` with `checkpoint` default and requires a durable execution instruction for `continuous`; Run reads and resume context return the resolved mode (`REQ-FUNC-ba164e6e`).
- Interface: Stage completion and checkpoint-ready Delivery reads return `data.checkpoint` with a concise summary, four human choices, and a `required` flag; continuous responses retain the summary and expose the existing atomic next action (`REQ-FUNC-ba164e6e`).
- Interface: Delivery decisions record `approval_source` as `developer` or `continuous_delegation`; delegated approval is valid only for a Run durably marked continuous (`REQ-FUNC-ba164e6e`).
- Data: store `interaction_mode` in Run front matter, normalize a missing legacy field to `checkpoint`, and preserve the explicit continuous instruction in the existing readable Run section (`REQ-FUNC-ba164e6e`).
- Data: checkpoint choices are presentation guidance rather than new workflow states or operations; review and park carry no operation, continue uses `stage.start`, and revise uses `stage.set_section` or `stage.revisit` (`REQ-FUNC-ba164e6e`).
- Rejected alternative: a new paused status or checkpoint-choice mutation would duplicate conversational state and mechanically obstruct direct CLI use (`REQ-FUNC-ba164e6e`).
- Test seams: Run/Stage workflow tests cover defaults, legacy reads, persistence, profiles, summaries, choices, mutation boundaries, continue, and revisit; Delivery tests cover approval gating and continuous delegation (`REQ-FUNC-ba164e6e`).
- Test seams: protocol, presenter, registry, resume, and host-adapter tests cover machine shape, human output, input metadata, resumed mode, and equivalent five-host guidance (`REQ-FUNC-ba164e6e`).
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_run_stage_workflow.py::test_run_interaction_mode_defaults_legacy_and_continuous_resume tests/test_run_stage_workflow.py::test_checkpoint_handoffs_cover_every_included_full_and_short_stage tests/test_run_stage_workflow.py::test_checkpoint_revision_uses_existing_revisit_and_continuous_recommends_start tests/test_delivery_adoption.py::test_delivery_checkpoint_requires_developer_approval_or_continuous_delegation tests/test_operation_registry.py::test_input_operations_document_the_machine_envelope_and_data_fields tests/test_host_adapters.py::test_native_host_guidance_routes_resume_through_stage_show tests/test_cli_protocol.py::test_human_output_presents_checkpoint_summary_and_four_choices`; exit=1; expected missing behavior=seven focused tests failed on absent interaction_mode and checkpoint response fields, approval-source contract, host checkpoint guidance, and human checkpoint rendering.
- 2026-08-13 build green: The same seven-selector command exited 0 with 7 passed in 31.69 seconds after the smallest runtime, codec, presenter, adapter, and approval-source changes.
- 2026-08-13 build regression: An eight-file focused pytest command timed out at the 304-second launcher bound without a pytest summary; process inspection confirmed no surviving duplicate, and a narrower adjacent selector set then exited 0 with 21 passed in 53.56 seconds.
- 2026-08-13 build regression: One attempted 11-selector command exited 4 before collection because the named execution-integrity selector did not exist; the corrected 21-test command above supplied the intended coverage.
- 2026-08-13 build impacted: `python .agentic/aegis.py test --impacted` exited 1 before test execution because the pre-existing root-launched command cannot import the package-local `tests` namespace and selected the pre-existing stale `test_registry_declares_all_56_unique_protocol_operations` trace link; a rootdir-corrected representative selector exited 0 with 1 passed.
- 2026-08-13 build regression: Presenter and host-adapter follow-up exited 0 with 4 passed, targeted Ruff exited 0, Python compilation exited 0, payload manifest generation and exact verification exited 0, and `git diff --check` exited 0.
- 2026-08-13 build traceability: REQ-FUNC-ba164e6e is active with seven focused linked tests and current implementation, adapter, documentation, manifest, and knowledge paths.
- 2026-08-13 build check: `python .agentic/aegis.py check --task TASK-86fec283 --full` exited 0 while reporting its advisory result as ERROR from five pre-existing unknown-requirement entries in TASK-44bbb4ad, plus unrelated open-task, empty-test, and expected outside-layout documentation warnings; it reported no defect in this task's requirement or journal.
- 2026-08-13 validate review: Returned to build because a legacy Delivery decision with value approved but no structured approval_source could satisfy the completion gate, which would infer authority contrary to REQ-FUNC-ba164e6e.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_delivery_adoption.py::test_legacy_delivery_approval_without_source_cannot_close_checkpoint_run`; exit=1; expected missing behavior=legacy approved decision without approval_source completed Delivery instead of remaining active.
- 2026-08-13 build green: The legacy approval-source selector exited 0 with 1 passed in 6.26 seconds after Delivery completion began requiring an explicit authorized approval source.
- 2026-08-13 build regression: The eight linked checkpoint-contract selectors exited 0 with 8 passed in 34.68 seconds, and the complete Delivery adoption test module exited 0 with 15 passed in 60.29 seconds.
- 2026-08-13 build static: Targeted Ruff and Python compilation both exited 0, the five starter/native adapter pairs were byte-identical, contract JSON and Delivery TOML parsed, the Delivery workflow remained within its 1,600-byte bound at 1,587 bytes, and the regenerated payload manifest verified exactly.
- 2026-08-13 build complete: The linked requirement is active with eight focused tests; the pre-existing AEGIS Light impacted-runner defect remains documented, so validation will use the package-correct full AEGIS suite without changing AEGIS Light or running the out-of-scope WAEGIS suite.
- 2026-08-13 validate review: The complete implementation, protocol, adapter, test, documentation, traceability, and manifest diff was reviewed against the accepted planning documents, design, error paths, compatibility, portability, security, exclusions, and preservation rules; no candidate defect remained, no manual-only requirement applies, and all four affected component knowledge pages remain current.
- 2026-08-13 validate proof: `uv run --group dev python -m pytest -q tests` exited 0 with 275 passed in 531.06 seconds; this was the single complete AEGIS suite run, and no WAEGIS suite was run.
- 2026-08-13 validate proof: `uv run --group dev ruff check .`, changed-source `python -m py_compile ...`, `uv run --group dev python -B -m aegis --help`, exact payload manifest verification, and `git diff --check` each exited 0; CLI help reported 49 canonical operations.
- 2026-08-13 validate advisory: `python .agentic/aegis.py check --task TASK-86fec283 --strict` exited 1 with five pre-existing unknown-requirement errors in TASK-44bbb4ad and 49 pre-existing or expected warnings; `--run` was intentionally omitted because the configured command also runs the unchanged WAEGIS full suite, contrary to the developer's explicit validation boundary, while the applicable full AEGIS suite was proven separately.
- 2026-08-13 validate complete: The candidate is validated and advanced to Delivery for presentation only; no report, commit, push, merge, or other outward Git operation is authorized.
