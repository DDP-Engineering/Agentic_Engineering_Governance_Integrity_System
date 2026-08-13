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

# TASK-835ca8c4 — Add guided WAEGIS adoption wizard

stage: deliver
type: feature
path: full
requirements:
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged after requested proof
- [x] validation evidence, diff, exclusions, and outcome prepared for presentation
- [ ] delivery confirmed by the task owner
- [x] journal, tests, WAEGIS documentation, changelog, and distribution included
- [x] agreed guided-adoption outcome delivered
- [ ] close-out recorded only after the owner accepts the packaged wizard

## Log

- 2026-08-13 frame: Add a genuine no-argument human WAEGIS wizard while preserving all flat operations, machine behavior, exact digest authorization, repository safety, and the explicit exclusion of the AEGIS adoption guide.
- 2026-08-13 frame: Use the full path because interactive orchestration spans target inspection, optional Git initialization, install/upgrade selection, plan review, apply confirmation, cancellation, and post-apply guidance.
- 2026-08-13 build red: Initial interactive installation and cancellation tests failed because run_cli accepted no input/output streams and no no-argument workflow existed.
- 2026-08-13 build: Added explicit prompts for target selection, prerequisite and repository reporting, optional plan-authorized local Git initialization, automatic install or upgrade selection, external plan creation, summary and paged action review, default-no apply, and verification commands.
- 2026-08-13 build: Reused the canonical lifecycle application for every plan and apply so the wizard cannot bypass target fingerprints, canonical plan bytes, or exact digest authorization.
- 2026-08-13 build: Added installation success, cancellation, installed-target upgrade selection, local Git initialization, and human-help discovery coverage.
- 2026-08-13 build: Updated WAEGIS README and the root Unreleased changelog; 06_SoftwareDocu/AEGIS_ADOPTION_GUIDE.md was intentionally not changed.
- 2026-08-13 validate: The complete WAEGIS suite passed 53 tests in 15.52 seconds and the complete release-tool suite passed 15 tests in 10.476 seconds.
- 2026-08-13 validate: Ruff initially identified five overlong presentation lines; formatting corrected them, after which Ruff and Python compilation passed and five focused wizard/help tests passed.
- 2026-08-13 validate: Scoped diff hygiene passed.
- 2026-08-13 validate: Rebuilt and inspected the authoritative 86-file Windows external-runtime archive under 07_Delivery/dist with SHA-256 C04047B1A673799CB11DE9A1E8789B0A6B07AF9B4826CACBB83E1EE8DCFCE4DD.
- 2026-08-13 validate: Strengthened paged review after external testing by adding exact range headings, explicit complete or early-stop statements, and a 52-action regression proving consecutive display from 1 through 52 without gaps or duplicates.
- 2026-08-13 validate: After the review-strengthening change, Ruff and compilation passed, the complete WAEGIS suite passed 54 tests in 15.76 seconds, and the complete release-tool suite passed 15 tests in 10.653 seconds.
- 2026-08-13 validate: Rebuilt the authoritative 86-file archive with SHA-256 410A6AF1658BA48AE736C15DA9BE4A2441ADFADC391F09D94851DDD0453B4E4E.
- 2026-08-13 deliver: Candidate is ready for owner novice-developer testing on master with no staging, commit, or push.
