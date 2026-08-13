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

# TASK-a9ef4c00 — Detect nested software project tests

stage: deliver
type: fix
path: quick
requirements:
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged after requested proof
- [x] validation evidence, diff, exclusions, and outcome prepared for presentation
- [ ] delivery confirmed by the task owner
- [x] journal, tests, WAEGIS documentation, changelog, and distribution included
- [x] agreed nested-project discovery outcome delivered
- [ ] close-out recorded only after the owner accepts the packaged plan

## Log

- 2026-08-13 frame: Correct WAEGIS installation discovery for conventional tests and pytest configuration in nested software projects, rebuild the Windows distribution, and explicitly exclude the AEGIS adoption guide and AEGIS product behavior.
- 2026-08-13 frame: Use the quick path because this is a bounded WAEGIS discovery fix with focused regression coverage and no public lifecycle protocol change.
- 2026-08-13 build red: The nested software-project and bounded-discovery tests failed because test roots below depth two were omitted.
- 2026-08-13 build: Replaced depth-two enumeration with a deterministic walk bounded at depth four that prunes hidden, environment, dependency, cache, build, distribution, vendor, and linked directories.
- 2026-08-13 build: Added nested owning-project pytest.ini, conftest.py, and pyproject.toml recognition while retaining repository-root precedence and bounded source inspection.
- 2026-08-13 build: Updated the existing nested lifecycle regression to reproduce the VoiceWeaver-shaped 04_Software/VoiceApplication/tests layout and verify the nested pytest configuration basis.
- 2026-08-13 build: Updated only WAEGIS README and the root Unreleased changelog; 06_SoftwareDocu/AEGIS_ADOPTION_GUIDE.md was intentionally not changed.
- 2026-08-13 validate: Focused red-to-green proof passed with 2 tests, then the complete WAEGIS suite passed 49 tests in 12.99 seconds.
- 2026-08-13 validate: Python compilation passed and the complete release-tool suite passed 15 tests in 10.721 seconds.
- 2026-08-13 validate: Scoped diff hygiene passed.
- 2026-08-13 validate: Rebuilt and inspected the authoritative 86-file Windows external-runtime archive under 07_Delivery/dist with SHA-256 49155543395FAB367FF74180EB39BFAADE11F79AA4FC226F98383D00321D9A27.
- 2026-08-13 deliver: Candidate is ready for owner adoption testing on master with no staging, commit, or push.
