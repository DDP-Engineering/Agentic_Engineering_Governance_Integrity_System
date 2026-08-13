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
requirements: REQ-FUNC-ba164e6e, REQ-PLAT-c820ce6c
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
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
- 2026-08-14 test: test --impacted (20 test ref(s)) exit 4 (0.8s)

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
- 2026-08-13 delivery feedback: Returned to build after read-only inspection of VoiceWeaver Run RUN-f58cc678954f483dbec3ffcd12fff576 confirmed the agent falsely selected continuous mode, fabricated an explicit-delegation instruction from an ordinary implementation request, completed Intake, Alignment, and Requirement, and started Design without checkpoints.
- 2026-08-13 build red: AEGIS host-guidance selector exited 1 because no host explicitly required verbatim delegation evidence and immediate turn termination, while two WAEGIS root-bridge selectors exited 1 because the bridge lacked checkpoint rules and upgrades did not refresh an older managed block.
- 2026-08-13 build green: The two AEGIS host-guidance selectors exited 0 with 2 passed in 0.04 seconds, and the two WAEGIS root-bridge lifecycle selectors exited 0 with 2 passed in 0.71 seconds after strengthening host instructions and managed root guidance.
- 2026-08-13 build regression: The complete AEGIS host-adapter module exited 0 with 3 passed in 0.05 seconds, the complete WAEGIS lifecycle module exited 0 with 27 passed in 12.23 seconds, AEGIS and WAEGIS targeted Ruff and compilation exited 0, the payload manifest regenerated and verified, and `git diff --check` exited 0.
- 2026-08-13 build impacted: `python .agentic/aegis.py test --impacted` again exited 1 because the pre-existing root-launched configuration cannot import either package namespace or collect mixed AEGIS and WAEGIS selectors; package-root focused commands above supplied the intended coverage without modifying AEGIS Light.
- 2026-08-13 build traceability: REQ-FUNC-ba164e6e now includes the WAEGIS-managed root bridge, lifecycle implementation, documentation, knowledge, and two root-bridge lifecycle tests while remaining active.
- 2026-08-14 validate review: The correction diff was reviewed against the observed VoiceWeaver failure, accepted checkpoint contract, managed-marker ownership, project-guidance preservation, idempotency, error paths, portability, security, and exclusions; no manual-only verification applies.
- 2026-08-14 validate concurrency: During validation, an external actor committed the earlier candidate as 83c9ac0 `AEGIS corrections. WIP.` and created untracked `temp_list.txt`; this task did not create, modify, stage, revert, or remove either, and the post-change suites validate the resulting current HEAD plus this corrective working-tree diff.
- 2026-08-14 validate proof: The revised complete AEGIS suite exited 0 with 230 passed in 335.43 seconds and collection confirmed 230 current tests; the complete WAEGIS suite exited 0 with 56 passed in 14.41 seconds.
- 2026-08-14 validate proof: AEGIS and WAEGIS Ruff, changed-source compilation, both CLI help checks, exact payload manifest verification, and `git diff --check` exited 0; AEGIS help reported 48 canonical operations.
- 2026-08-14 validate advisory: `python .agentic/aegis.py check --task TASK-86fec283 --strict` exited 1 with five pre-existing unknown-requirement errors in TASK-44bbb4ad and catalog warnings from pre-existing stale paths, empty links, open Delivery journals, expected documentation/host paths, and external `temp_list.txt`; the one stale path owned by REQ-FUNC-ba164e6e was removed before presentation.
- 2026-08-14 validate complete: The corrective candidate is validated and returned to Delivery presentation; no VoiceWeaver file was modified and no report, commit, push, merge, or other outward Git operation was performed by this task.
- 2026-08-14 delivery approval: The developer requested creation of a delivery while the standing no-branch, no-commit, and no-push constraints remain in effect, so the approved outcome is the local external-runtime archive matrix rather than a commit or pull request.
- 2026-08-14 delivery build: Four external-runtime archives for AEGIS and WAEGIS on Windows x86-64 and Ubuntu 22.04 x86-64 were rebuilt from the validated candidate; all four build commands and all four archive inspections exited 0 with 70 AEGIS files and 84 WAEGIS files per archive.
- 2026-08-14 delivery content: Corrected content inspection exited 0 and confirmed both AEGIS archives contain the strengthened checkpoint guidance while both WAEGIS archives contain the bounded nested-test scanner and refreshed checkpoint bridge; an earlier inspection probe named the wrong WAEGIS member prefix and raised KeyError without changing any artifact.
- 2026-08-14 delivery boundary: Bundled-runtime archives remain unavailable because locked Python and Git archives are unsupplied, and no artifact was committed, signed, uploaded, or published.
- 2026-08-14 delivery feedback: Returned to specify after VoiceWeaver inspection showed the detected nested pytest root was paired with repository-root execution, and the developer required the correction to remain valid across languages and test suites rather than hard-code the VoiceWeaver layout.
- 2026-08-14 specify: Expanded existing REQ-PLAT-c820ce6c instead of creating a duplicate, defining owner-aware suite discovery and native commands for nested Python, Node.js, Go, Rust, .NET, Maven, and Gradle projects with deterministic multi-suite output and honest fallbacks.
- 2026-08-14 specify: Added a requirement spec because the bounded ownership algorithm, supported structured signals, command selection, grouping, and fallback behavior are not buildable from one requirement sentence alone; VoiceWeaver and AEGIS Light remain excluded from writes.
- 2026-08-14 specify check: `python .agentic/aegis.py check --task TASK-86fec283` exited 0 at the process level and reported the known five errors in unrelated TASK-44bbb4ad plus pre-existing catalog warnings, with no format or traceability error in REQ-PLAT-c820ce6c, its spec, or this task journal; `git diff --check` exited 0.

## Delivery report (2026-08-14)

- stage: deliver; type: feature; path: full; branch: master
- requirements:
  - REQ-FUNC-ba164e6e - Pause for developer choice after each stage
- diff vs merge base: 22 file(s) changed, 253 line(s) added
- checks: errors=5 warnings=67 notes=0
- checklist: 4/6 done; open: journal and report included in the delivery commit; close-out committed only after the outcome succeeded

## Design refinement (2026-08-14)

- Interface: every shipped host adapter and the WAEGIS-managed root bridge will instruct agents to end checkpoint summaries with `Choose one:` followed by Continue, Review, Revise or reimplement, and Park as four separate Markdown list lines; Delivery substitutes Approve and close for Continue (`REQ-FUNC-ba164e6e`).
- Data: machine checkpoint choices and workflow operations remain unchanged because this is a presentation contract only (`REQ-FUNC-ba164e6e`).
- Rejected alternative: relying on prose that merely names the four choices permits hosts to collapse them into one sentence and does not satisfy the requested scannable layout (`REQ-FUNC-ba164e6e`).
- Test seams: the existing native-host guidance test will require the exact four-line Markdown block in all five native/starter pairs, and WAEGIS root-bridge lifecycle tests will require the same block in generated guidance (`REQ-FUNC-ba164e6e`).
- 2026-08-14 build red: command=`uv run --group dev python -m pytest -q tests/test_host_adapters.py::test_native_host_guidance_routes_resume_through_stage_show`; exit=1; expected missing behavior=all shipped host guidance lacked the exact vertical Markdown checkpoint-choice block.
- 2026-08-14 build red: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_install_creates_root_agents_bridge_when_missing tests/test_lifecycle.py::test_install_prefixes_existing_root_agents_guidance_once`; exit=1; expected missing behavior=fresh and refreshed WAEGIS-managed root guidance lacked the exact vertical Markdown checkpoint-choice block.
- 2026-08-14 build green: the complete AEGIS host-adapter module exited 0 with 3 passed in 0.04 seconds, and both WAEGIS root-bridge selectors exited 0 with 2 passed in 0.60 seconds after the exact four-line Markdown block was added.
- 2026-08-14 build static: targeted AEGIS and WAEGIS Ruff, WAEGIS compilation, exact 62-file payload manifest regeneration and verification, and `git diff --check` exited 0.
- 2026-08-14 build impacted: `python .agentic/aegis.py test --impacted --task TASK-86fec283` exited 1 because the pre-existing root-launched configuration cannot import package-local AEGIS or WAEGIS test namespaces; package-root focused commands above supplied the intended coverage.
- 2026-08-14 build check: `python .agentic/aegis.py check --task TASK-86fec283 --full` exited 0 at the process boundary while its advisory result retained five unrelated TASK-44bbb4ad errors and 65 historical or expected warnings, with no defect in this refinement's requirement, tests, or journal.
- 2026-08-14 validate review: The vertical-choice refinement was reviewed against the requested output, all five host loaders, canonical/native byte parity, fresh and refreshed WAEGIS root bridges, Markdown rendering, Delivery substitution, portability, existing dirty work, and the no-publish boundary; no implementation defect remained.
- 2026-08-14 validate traceability: REQ-FUNC-ba164e6e remains active with current prose, verification, affected paths, and linked tests, and the AEGIS adapter and WAEGIS lifecycle knowledge pages now record the vertical-list contract; no manual-only verification applies.
- 2026-08-14 validate proof: The complete AEGIS suite exited 0 with 230 passed in 306.99 seconds and the complete WAEGIS suite exited 0 with 56 passed in 12.24 seconds after the final behavior and test changes.
- 2026-08-14 validate static: Both CLI help checks, targeted Ruff and compilation, exact 62-file payload manifest verification, five-host literal block inspection, and `git diff --check` exited 0.
- 2026-08-14 validate advisory: `python .agentic/aegis.py check --task TASK-86fec283 --strict` exited 1 only on the known five unrelated TASK-44bbb4ad errors and retained 65 historical or expected warnings, including external `temp_list.txt`; no task-owned error was reported.
- 2026-08-14 validate complete: The refinement is validated and returned to Delivery presentation without staging, commit, push, archive rebuild, deployment, VoiceWeaver modification, or any other outward action.
