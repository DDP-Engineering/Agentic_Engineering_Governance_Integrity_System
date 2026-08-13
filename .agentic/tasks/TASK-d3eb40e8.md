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

# TASK-d3eb40e8 — Document cross-platform AEGIS adoption

stage: deliver
type: change
path: quick
requirements:
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged after requested proof
- [x] validation evidence, diff, exclusions, and outcome prepared for presentation
- [ ] delivery confirmed by the task owner
- [x] journal and documentation included in the candidate
- [x] agreed documentation outcome delivered
- [ ] close-out recorded only after the owner accepts the guide

## Log

- 2026-08-13 frame: Add an end-user AEGIS adoption guide under 06_SoftwareDocu for Windows and Linux, excluding project-specific paths, branches, release numbers, product behavior changes, and publication actions.
- 2026-08-13 frame: Use the quick path because this is documentation-only work grounded in existing WAEGIS and AEGIS contracts and introduces no runtime behavior.
- 2026-08-13 build: Added AEGIS_ADOPTION_GUIDE.md with archive extraction, prerequisite verification, package verification, Git initialization, plan review, digest-confirmed install, installed-payload verification, first-use guidance, upgrade, removal, and troubleshooting flows.
- 2026-08-13 build: Updated 06_SoftwareDocu/README.md to identify the new platform-neutral end-user guide.
- 2026-08-13 validate: Reviewed every command against the WAEGIS operation registry, packaged launcher names, release prerequisite generation, and installed AEGIS launcher layout.
- 2026-08-13 validate: Confirmed the guide contains no VoiceWeaver path, local branch, repository source path, or AEGIS/WAEGIS release number.
- 2026-08-13 validate: Documentation was reviewed directly as required; no automated prose test or full test suite was run.
- 2026-08-13 validate: command=`git diff --check -- 06_SoftwareDocu/AEGIS_ADOPTION_GUIDE.md 06_SoftwareDocu/README.md`; exit=0.
- 2026-08-13 validate: Added an owner-requested opening warning that the archive, extracted WAEGIS utility, lifecycle plans, logs, and temporary installer artifacts must remain outside the target repository, and reinforced the boundary in extraction instructions.
- 2026-08-13 validate: Restructured the guide after wizard implementation so no-argument guided install and upgrade are the primary novice flow, including prerequisite reporting, external plan summary and paging, default-no exact apply, cancellation, and printed verification commands.
- 2026-08-13 validate: Moved flat plan and apply commands into an advanced manual section, retained explicit removal instructions, and removed novice-facing machine-format guidance.
- 2026-08-13 validate: Documented exact plan page ranges and the final complete-versus-stopped review statement after external wizard testing exposed ambiguous missing console lines.
- 2026-08-13 validate: Rechecked headings, placeholders, project neutrality, and scoped diff hygiene directly; no automated prose test was added or run.
- 2026-08-13 deliver: Candidate is ready for owner review on master with no staging, commit, push, or product-code change.
