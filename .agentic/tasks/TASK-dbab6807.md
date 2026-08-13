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

# TASK-dbab6807 — Render human-friendly WAEGIS help

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
- [x] journal, tests, documentation, and archive included in the candidate
- [x] agreed usability outcome delivered
- [ ] close-out recorded only after the owner accepts the packaged help

## Log

- 2026-08-13 frame: Replace the successful human WAEGIS help JSON dump with a readable registry-derived command reference while preserving machine JSON behavior, other human envelopes, and lifecycle semantics.
- 2026-08-13 frame: Use the quick path because the change is a presentation-only usability fix with focused protocol coverage and no lifecycle or data-contract change.
- 2026-08-13 build red: Three focused CLI tests failed because human help lacked Usage and command signatures and printed the operations list as one JSON line.
- 2026-08-13 build: Added a dedicated successful human help renderer with one command signature and purpose per registry operation plus concise plan-review-apply guidance.
- 2026-08-13 build: Removed machine-mode advertising from first-use human help at the owner's request while retaining explicit JSON behavior unchanged.
- 2026-08-13 build: Updated WAEGIS documentation, the cross-platform adoption guide, and the Unreleased changelog entry.
- 2026-08-13 validate: Focused help tests passed after the final wording change with 3 passed in 0.97 seconds.
- 2026-08-13 validate: Before the final wording-only removal, the complete WAEGIS suite passed 49 tests in 9.51 seconds and the complete release-tool suite passed 15 tests in 8.703 seconds.
- 2026-08-13 validate: Python compilation and scoped diff hygiene passed, and direct source help rendered the intended operator reference.
- 2026-08-13 validate: Rebuilt the Windows external-runtime WAEGIS archive and executed its extracted packaged launcher successfully with the final help output and exit 0.
- 2026-08-13 validate: The rebuilt archive SHA-256 is 97F210496A2D3CCCFB47F8550581603697BA8BE519A480107248C882DA3D16C6.
- 2026-08-13 validate: Rebuilt and inspected the authoritative archive at 07_Delivery/dist/waegis-1.0.0-windows-x86_64-external-runtime.zip with 86 files; VoiceWeaver remains only the external manual adoption target for subsequent steps.
- 2026-08-13 deliver: Candidate is ready for owner testing on master with no staging, commit, or push.
