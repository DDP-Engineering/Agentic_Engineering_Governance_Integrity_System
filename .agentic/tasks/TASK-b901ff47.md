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
  parent        optional top-level TASK-id; blank for an ordinary task
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.

Stage report is one replaceable latest snapshot, not an evidence store.
Use plain one-line fields with no fences or bullets inside that section.
stage is the reported stage; current must match the journal header after any
transition. result is in_progress | completed | paused | blocked | skipped.
Keep all observations and decisions in the append-only Log as well.
Leave unknown fields blank; summary prints not recorded, never an assumed pass.
Refresh after work or decisions even if current has not changed.
-->

# TASK-b901ff47 — Develop portable Pi and Qwen Code AEGIS integrations

stage: deliver
type: feature
path: full
requirements: REQ-FUNC-0549bf24, REQ-SEC-88bf2840, REQ-FUNC-52d2e370, REQ-FUNC-f976517c, REQ-PLAT-81e13664, REQ-REL-2de0ed39, REQ-PLAT-15c09d6e
parent:
branch: task/agent-plugins
base: 5ff5b0af6abdf64e207f217d023adb501d41fe5c
opened: 2026-09-03

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-09-03 frame: <scope agreed, exclusions, chosen path and why>

- 2026-09-03 frame: The user asks for the same portable AEGIS agent packages just developed, now for pi.dev and QwenLM/qwen-code; carry forward Windows/Linux packaging, the existing workflow scope and no local model testing.
- 2026-09-03 frame: Scope is native Pi tools/commands/skill plus isolated review launch, native Qwen extension/skill/commands/review roles and local tool transport, config-preserving lifecycle, behavior tests and current documentation under 05_Software/aegis/integrations.
- 2026-09-03 frame: Exclude core or managed-template changes, provider/authentication setup, model pinning, real-host installation, version assignment, commit, push and registry publication.
- 2026-09-03 frame: Full path is required for new host interfaces and installation boundaries; retain existing task/agent-plugins branch because it is already a task branch with uncommitted approved OpenCode/Codex work.
- 2026-09-03 frame: The preceding package scope was approved and the current user explicitly asks for the same work on two named hosts; this is authorized continuation of that concrete package scope, not Git delivery approval.
- 2026-09-03 frame: Inspected official web and installed primary documentation; installed host versions are Pi 0.84.4 and Qwen Code 0.22.3, both support local extension discovery, and Pi has no built-in subagent mechanism.
- 2026-09-03 frame: Preserve all prior files; work/pi-qwen-starting-files.json records their starting hashes, and the two pre-existing RTM exports remain excluded from changes.

- 2026-09-03 specify: Proceed with the same requested two-host package scope; native Pi reviewer launch accounts for its lack of built-in subagents.

- 2026-09-03 specify: REQ-FUNC-0549bf24 covers Expose AEGIS operations in Pi.
- 2026-09-03 specify: REQ-SEC-88bf2840 covers Launch independent Pi review sessions.
- 2026-09-03 specify: REQ-FUNC-52d2e370 covers Load the Qwen AEGIS workflow extension.
- 2026-09-03 specify: REQ-FUNC-f976517c covers Expose AEGIS tools over local protocol.
- 2026-09-03 specify: REQ-PLAT-81e13664 covers Install Pi and Qwen integrations without config replacement.
- 2026-09-03 specify: REQ-REL-2de0ed39 covers Protect Pi and Qwen installation ownership.
- 2026-09-03 specify: REQ-PLAT-15c09d6e covers Assemble all supported AEGIS host packages.

- 2026-09-03 design: Seven native-host requirements drafted; static check reports no format errors.

- 2026-09-03 build: Designed native Pi/Qwen resources over the existing runner, with explicit review and installation boundaries.

- 2026-09-03 build red: command=node --test --test-name-pattern=build: 05_Software/aegis/integrations/tests/additional.test.mjs; exit=1; expected missing behavior=builder reports only OpenCode/Codex instead of all four requested hosts.

- 2026-09-03 build: Four-host assembly regression is green; five native-interface behavior groups are red against explicit stubs.

- 2026-09-03 build red: command=`node --test --test-name-pattern='pi:|pi_review:|qwen:|protocol:|install:' 05_Software/aegis/integrations/tests/additional.test.mjs`; exit=1; expected missing behavior=Pi registered zero tools, review argv lacked read-only tools, Qwen manifest lacked workspace binding, protocol lacked initialization response, and installer explicitly threw not implemented. All five failures observed before native implementation; interface reds were batched rather than strictly one requirement at a time.

- 2026-09-03 build red: command=node --test --test-name-pattern=pi:register (actual selector: pi: register) 05_Software/aegis/integrations/tests/additional.test.mjs; exit=1; native Pi schema validation exposed defaulted job action incorrectly marked required by Zod output schema; matching regression failed before correction.

- 2026-09-03 build red: command=node --test --test-name-pattern=install: 05_Software/aegis/integrations/tests/additional.test.mjs; exit=1; edited owned runtime settings were probed before ownership refusal; require preflight ownership validation before runtime discovery.

- 2026-09-03 build green: node new native suite has 9 behavioral cases; Windows pytest wrapper 6 passed, Linux native suite 9 passed; python .agentic/aegis.py test --impacted --base HEAD selected both old and new integration groups, 12 passed in 41.05s, exit=0.
- 2026-09-03 build native: isolated Pi 0.84.4 and Qwen Code 0.22.3 installs on Windows and Ubuntu 24.04 discovered the expected commands/skill/agents, Qwen MCP connected, Pi status read actual installed AEGIS successfully, and doctor/update/uninstall preserved settings; evidence=work/pi-qwen-windows-3/verification.json and work/pi-qwen-linux-3.log in the Codex workspace.
- 2026-09-03 build native: Pi SDK loader validated all eleven input schemas and rejected malformed task arguments on both platforms; its actual CLI parser accepted fresh-review tool restrictions; no model requests or real-host installation were made.
- 2026-09-03 build correction: the first green unit run emitted invalid draft-07 target warnings, corrected to draft-7; native SDK then exposed defaulted job action marked required, corrected using input schema generation; owned runtime edits now fail preflight before probing.
- 2026-09-03 build evidence: anchor 101917f924617b0e predates implementation; evolution covers 33 expected files (25 additions, 8 modifications, no removals); categories for new host paths reflect the earlier anchor configuration, while current layout includes both hosts.
- 2026-09-03 build boundaries: initial-file hashes confirm original OpenCode/Codex runtime resources, managed payload and protected RTM exports remain unchanged; shared builder/docs and new native-host modules are intentional changes.
- 2026-09-03 build static: check --task TASK-b901ff47 --json exit=0, errors=0, warnings=12, notes=3; eleven warnings concern pre-existing task journals and one is the unchanged 449337-byte vendored bundle omitted by bounded scanning; previous complete pattern scan found zero matches and its bytes still match the starting snapshot, so retain it as accepted scan-scope limitation.
- 2026-09-03 build limitation: no Desktop UI interaction or model-driven review/workflow was exercised, preserving the user's no-local-model-testing constraint; CLI/SDK/protocol evidence is not GUI or model-compliance proof.
- 2026-09-03 build process deviation: interface red cases were batched and their earlier stubs preceded those interface checks; only the assembly regression preceded the first implementation edit and anchor, so this is not strict per-requirement test-first history.
- 2026-09-03 design reconciliation: Pi exposes its workflow skill through resources_discover and keeps reviewer prompts outside slash-prompt discovery to avoid presenting them as isolated agents; Qwen uses no external MCP SDK, sharing the existing bundled Zod input validation.

- 2026-09-03 validate: Implemented native Pi and Qwen packages, lifecycle, tests and installation documentation.

- 2026-09-03 validate review: round=1; candidate=21c8b7ad2110509634282502bfaaf5309551a22e37d7ea62007f8da4bc5fa26c; spec_compliance=approved and implementation_quality=approved; independent read-only reviews inspected actual files/evidence and verified all 210 manifest hashes before/after, with no actionable findings.
- 2026-09-03 validate limitation: MCP request-cancellation dispatch has code inspection but no dedicated new behavior test; existing shared adapter cancellation tests remain covered, and no stronger protocol cancellation claim is made.

- 2026-09-03 validate proof: command=python .agentic/aegis.py check --task TASK-b901ff47 --strict --run --json; exit=0; elapsed=139.12s; configured pytest=381 passed, 2 skipped in 137.84s, configured Ruff=all checks passed; errors=0, accepted warnings=12, notes=3; candidate=21c8b7ad2110509634282502bfaaf5309551a22e37d7ea62007f8da4bc5fa26c; unchanged before/after proof.
- 2026-09-03 validate skips: test_repo_evolution.py::test_symlink_fingerprint_does_not_walk_external_content skipped because symlink creation unavailable, and test_run_report.py::test_symlinked_journal_cannot_escape_on_posix skipped for Windows semantics; mapped recorded progress to unchanged 383-test collection and inspected source skip reasons, without rerunning the suite.
- 2026-09-03 validate evidence: final evolution refreshed at 2026-09-03T11:46:42.004098Z covers all 33 expected changes since anchor; seven requirements active and linked, knowledge reconciled, source/requirements/docs remain identical to both approved reviews and final proof.
- 2026-09-03 deliver handoff: implementation and verification complete; evidence and exclusions presented; retain task/agent-plugins with no staging, commit, push, new release version or publication authority inferred; final proof and review records are available in the Codex workspace outputs/AEGIS-Pi-Qwen.

## Rulings

<!-- Append decisions here; never edit history. Supersede with a new ruling.
- RULING-001 | date=YYYY-MM-DD | decision=<decision> | reason=<reason> | source=user | supersedes=none
source: user | repository | requirement | technical
-->

## Design

- Pi uses an auto-discovered index.js extension with five commands, eleven tools and resources_discover for its skill/prompts; all operations reuse the unchanged shared adapter (REQ-FUNC-0549bf24).
- Pi review.mjs launches an explicit fresh Pi process with only read,grep,find,ls and no discovered extensions, skills or prompt templates; it uses the user's configured model and does not claim an operating-system sandbox (REQ-SEC-88bf2840).
- Qwen uses its native qwen-extension.json, Markdown skill/commands and two agents with read-only tool allowlists; the coordinator remains the main conversation so native reviewers can be delegated without nested-agent assumptions (REQ-FUNC-52d2e370).
- Qwen supplies a dependency-free MCP stdio server for eleven bounded operations, with initialization/version negotiation, schema validation, protocol errors, bounded input and explicit cancellation handling; cwd is bound to the host workspace (REQ-FUNC-f976517c).
- Shared operation schemas and execution glue are reused by Pi and Qwen, without changing the OpenCode/Codex entry points, adapter, worker or managed payload.
- Installers copy complete owned packages to Pi extensions/aegis and Qwen extensions/aegis, locations documented for native discovery; they use the existing ownership/cache protections and leave main settings/auth files unchanged (REQ-PLAT-81e13664, REQ-REL-2de0ed39).
- Runtime settings remain inside each installed package; Qwen's owned manifest pins Node and workspace cwd, while Pi records a portable native CLI location for its review launcher.
- Builder adds pi/qwen targets and retains byte-equivalent OpenCode/Codex package contents apart from intentionally added reusable modules (REQ-PLAT-15c09d6e).
- Reject installing a broad third-party agent framework: use native host interfaces and the existing bounded AEGIS runner, with no added provider integration or system-wide dependency changes.
- Test seams: native Pi factory command/tool execution, Pi review subprocess argument allowlist, real Qwen extension discovery, JSON-RPC discovery/calls against real AEGIS fixtures, transactional owned-file/cache behavior and four-host package imports.
- Add Node tests under integrations/tests and a Python bridge under 05_Software/aegis/tests; update the shared integration knowledge page, READMEs, deeper docs and root Unreleased entry.
- Native registration tests use isolated Windows and Linux configurations and no model requests; native Desktop and model-driven reviews remain explicitly unverified.

## Handoff

current: deliver
status: waiting
next: Optional Git publication requires explicit user approval; implementation is ready.
must_read: .agentic/tasks/TASK-b901ff47.md, .agentic/steps/6_deliver.md
blockers: no authority for staging, commit, push or publication

## Stage report

stage: validate
result: completed
current: deliver
changed: Pi and Qwen integrations implemented and validated; 33 expected file changes since anchor.
evidence: 381 tests passed, 2 skipped; lint passed; Windows/Linux native checks passed; both round-1 reviews approved the unchanged candidate.
issues: 12 accepted static warnings; Windows symlink skips; Desktop/model-driven workflows unverified.
next: Use the prepared packages; obtain explicit approval before any Git publication.
needs_user: no for requested implementation; explicit approval required only for Git publication
spec_compliance: approved
implementation_quality: approved
review_round: 1
