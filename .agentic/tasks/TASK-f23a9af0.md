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

# TASK-f23a9af0 — Define per-stage human checkpoint interaction

stage: deliver
type: change
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

- 2026-08-13 frame: Scope confirmed by the developer is to define default per-Stage human checkpoints in the product requirements and implementation documents, excluding executable code, AEGIS Light, and VoiceWeaver changes.
- 2026-08-13 frame: Full path selected because the documents define externally observable agent interaction behavior; the existing branch is retained as explicitly requested for the review campaign.
- 2026-08-13 frame: Update the existing product workflow requirements and add one repository-local functional requirement for the checkpoint interaction contract.
- 2026-08-13 specify: Added REQ-FUNC-ba164e6e as a draft product-behavior requirement because documentation is in scope while executable implementation remains pending.
- 2026-08-13 design: Store checkpoint versus continuous as explicit Run interaction state, expose the four choices as host guidance rather than a CLI policy blocker, and retain existing Stage statuses so park remains ordinary resumable state.
- 2026-08-13 build manual observation: Inspection across the product requirements, functional specification, artifact model, CLI protocol, implementation plan, acceptance plan, and release scope found consistent default-checkpoint and explicit-continuous semantics.
- 2026-08-13 validate: Documentation contract and unique requirement-ID checks passed, and git diff --check passed; no software suite was run because executable implementation was explicitly out of scope and repository rules require direct review for planning documents.
- 2026-08-13 validate: `python .agentic/aegis.py check --task TASK-f23a9af0 --strict` exited 1 from five pre-existing unknown-requirement errors in TASK-44bbb4ad; it also reported expected outside-layout planning-document warnings and unrelated open-task warnings.
- 2026-08-13 validate: No component knowledge page changed because this task updates the accepted product contract and implementation plan, while runtime component behavior remains pending.

## Design

- Components: product workflow contract, durable Run and Stage model, machine protocol, host-adapter implementation slice, and acceptance evidence (`REQ-FUNC-ba164e6e`).
- Interface: add `checkpoint` and `continuous` Run interaction modes; checkpoint responses expose concise summaries and continue, review, revise or reimplement, and park choices (`REQ-FUNC-ba164e6e`).
- Data: persist the interaction mode in `run.md`; park keeps the Run active and adds no new terminal or paused status (`REQ-FUNC-ba164e6e`).
- Rejected alternative: mandatory CLI transition blocking, because AEGIS guides and records agent work without obstructing direct developer operations (`REQ-FUNC-ba164e6e`).
- Verification seam: acceptance scenario AC-STAGE-002 exercises every checkpoint choice and a separately delegated continuous Run; this documentation-only task uses cross-document inspection.
