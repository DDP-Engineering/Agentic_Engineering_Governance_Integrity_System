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

  stage         frame | specify | design | build | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-0d9f419b — Adopt Agentic Engineering Governance and Integrity System

stage: close
type: adopt
path: full
requirements: REQ-DATA-79ebcb34, REQ-DATA-ecc88768, REQ-FUNC-0ed3f1b4, REQ-FUNC-1407b21b, REQ-FUNC-29090f7f, REQ-FUNC-294b8bf7, REQ-FUNC-29f57326, REQ-FUNC-41d09b16, REQ-FUNC-428573c5, REQ-FUNC-4e4fb4c9, REQ-FUNC-574eb6e6, REQ-FUNC-5acb044e, REQ-FUNC-629674ff, REQ-FUNC-7761f525, REQ-FUNC-7a19b623, REQ-FUNC-7b02b6ae, REQ-FUNC-a6f115bd, REQ-FUNC-c771a1d1, REQ-FUNC-e04edca3, REQ-FUNC-e4f0da51, REQ-FUNC-e5c2b57d, REQ-FUNC-fda66019, REQ-NFR-4b767a8b, REQ-NFR-6f1a6621, REQ-NFR-9aec5e3a, REQ-NFR-bb398def, REQ-NFR-c6ba4132, REQ-NFR-e5017804, REQ-PLAT-0818067b, REQ-PLAT-0badc589, REQ-PLAT-0e917260, REQ-PLAT-133b74ac, REQ-PLAT-1b680071, REQ-PLAT-248442e0, REQ-PLAT-4253ae41, REQ-PLAT-47c97052, REQ-PLAT-4ce82986, REQ-PLAT-5afdbb8a, REQ-PLAT-5c1bc460, REQ-PLAT-608b140d, REQ-PLAT-67c5d05e, REQ-PLAT-7663bb1d, REQ-PLAT-7cd54b8e, REQ-PLAT-888ec3c2, REQ-PLAT-97b168cf, REQ-PLAT-a4fcb436, REQ-PLAT-b5a7fd61, REQ-PLAT-bc526721, REQ-PLAT-c1bc7244, REQ-PLAT-c820ce6c, REQ-PLAT-cebb1b2b, REQ-PLAT-cff1cf5e, REQ-PLAT-d5dd084c, REQ-PLAT-ef45ae63, REQ-PLAT-f183e3cc, REQ-REL-0b1d9e84, REQ-REL-25745fd4, REQ-REL-2c12ed5d, REQ-REL-2dd22908, REQ-REL-360930b1, REQ-REL-39719eb5, REQ-REL-3c9287e0, REQ-REL-5858abac, REQ-REL-5b6e4c2c, REQ-REL-5bd5c6ae, REQ-REL-5fc2eb80, REQ-REL-65d839d8, REQ-REL-6c4a525d, REQ-REL-7093e21e, REQ-REL-7289f5f4, REQ-REL-862a5141, REQ-REL-92820eeb, REQ-REL-995954b5, REQ-REL-9aaaf19c, REQ-REL-b2d83e85, REQ-REL-b3f193a8, REQ-REL-b6f54754, REQ-REL-bf10ed27, REQ-REL-c20d6246, REQ-REL-c5bc94c6, REQ-REL-ce2d823d, REQ-REL-d13d0127, REQ-REL-d204dc36, REQ-REL-de2680dc, REQ-REL-e8675f89, REQ-REL-ed654c7e, REQ-SEC-91dd1489, REQ-SEC-af5073fb, REQ-TEST-07679fdc, REQ-TEST-71e4e6b2, REQ-TEST-c33c5899, REQ-TEST-e2b43472
branch: master
opened: 2026-08-12

## Done checklist (current stage)

- [x] component breakdown proposed and reviewed by the owner
- [x] every agreed component has a knowledge page
- [x] every component's behaviors are covered by requirements
- [x] linked tests point at existing tests that verify them
- [x] untested and suspect behaviors logged as backlog, not hidden
- [x] no suspect behavior was found that required as-is defect wording
- [x] check reports no errors over the whole tree
- [x] report generated
- [ ] journal and report inside the adoption commit; agreed outcome delivered
- [ ] close-out: stage done set and committed only after that

## Components

- [x] **AEGIS domain and protocol kernel** - canonical domain values, protocol envelopes, operation declarations, and revision policies; `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/domain/**`, `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/operation_types.py`, `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/operation_registry.py`, and focused domain/registry tests under `05_Software/aegis/tests/`.
- [x] **AEGIS workflow application** - Run and Stage lifecycle, project knowledge, traceability, execution orchestration, completion expectations, resume context, and port contracts; `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/**`, `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/ports/**`, and focused workflow/service tests under `05_Software/aegis/tests/`.
- [x] **AEGIS persistence and runtime adapters** - repository discovery, codecs, filesystem workspaces, atomic publication and recovery, Git observation, locking, configured processes, and runtime integrity; `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/**` and focused configuration, repository, transaction, publication, and integrity tests under `05_Software/aegis/tests/`.
- [x] **AEGIS CLI and host adapters** - composition root, flat CLI and JSON protocol, presenters, and Codex, Claude, Qwen, Pi, and OpenCode host transports/resources; `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/interface/**`, top-level runtime entry modules, payload host-adapter folders, and focused CLI/host tests under `05_Software/aegis/tests/`.
- [x] **WAEGIS lifecycle operator** - independent plan/apply lifecycle for repository initialization, installation, upgrade, removal, payload ownership, configuration generation, and recovery; `05_Software/waegis/src/waegis/**` and `05_Software/waegis/tests/**`.
- [x] **AEGIS Light companion** - stdlib-only single-file advisory CLI, workflow instructions, templates, release builder integration, and structural/behavioral regressions; `05_Software/aegis-light/template/.agentic/**`, `05_Software/aegis-light/tests/**`, and `02_Tools/build_aegis_light_release.py`.
- [x] **Release and acceptance tooling** - deterministic AEGIS archive build/inspection plus fail-closed acceptance catalog and retained-evidence report compilation; `02_Tools/build_aegis_release.py`, `02_Tools/runtime_inputs.toml`, `02_Tools/aegis_acceptance.py`, and `02_Tools/aegis_acceptance_catalog.json`.

## Log

- 2026-08-12 survey: Opened adoption on ddp/adopt-aegis-light because the checkout was on the default branch and preserved all pre-existing dirty work without modification.
- 2026-08-12 survey: Read the repository instructions, code-style reference, product READMEs, technical architecture, implementation guide, source layout, entry points, and existing test grouping.
- 2026-08-12 survey: Proposed seven bounded components around clean-architecture responsibilities and independently testable product or tooling boundaries.
- 2026-08-12 survey: Excluded planning and general documentation as standalone software components while retaining those documents as authoritative evidence during each component review.
- 2026-08-12 survey: Paused before component adoption for the required owner review of names, scopes, splits, and exclusions.
- 2026-08-12 survey: At owner direction, returned adoption directly to master and removed the temporary branch without commits or unique changes.
- 2026-08-12 components: Owner approved starting adoption with the proposed seven-component breakdown on master.
- 2026-08-12 components: Began the AEGIS domain and protocol kernel component; source and tests remain read-only during adoption.
- 2026-08-12 components: Corrected the surveyed registry path to its live application location before creating durable component records.
- 2026-08-12 components: Adopted eight observed kernel behaviors with active requirements, exact affected paths, and existing linked tests; no suspected defect or untested load-bearing behavior was found.
- 2026-08-12 components: A repository-root selector invocation failed during collection because package tests import `tests.*`; the identical package-directory invocation passed 20 focused tests.
- 2026-08-12 components: Completed the AEGIS domain and protocol kernel knowledge page and stopped after one component as required by the adoption workflow.
- 2026-08-12 components: Began the AEGIS workflow application component on master, excluding the already adopted operation registry and operation type declarations.
- 2026-08-12 components: Owner clarified that requirements under 00_Planning are authoritative, so workflow-application adoption paused before creating any component-two requirement.
- 2026-08-12 components: Reconciled component-one records into one traceability projection per applicable PR, CP, or TA statement and recorded the authoritative planning source in each rationale.
- 2026-08-12 components: Parsed all 16 authoritative projections and passed 29 focused tests covering their linked component behavior.
- 2026-08-12 components: Adopted the AEGIS workflow application from 17 authoritative planning statements and passed its seven focused test modules with 86 tests.
- 2026-08-12 components: Adopted the AEGIS persistence and runtime adapters from 15 authoritative planning statements and passed 73 focused tests.
- 2026-08-12 components: Logged missing explicit symlink and reparse-point escape regression coverage as the unhidden backlog for REQ-SEC-91dd1489.
- 2026-08-12 components: Adopted the AEGIS CLI and host adapters from 12 authoritative planning statements and passed 30 focused tests.
- 2026-08-12 components: Adopted WAEGIS from 13 authoritative planning statements; its suite passed 13 tests and retained one payload-digest startup failure caused by pre-existing dirty AEGIS bytes.
- 2026-08-12 components: Adopted AEGIS Light from ten implemented contracts in 00_Planning/AEGIS_LIGHT_PLAN and retained the explicitly deferred P6 pilot as unclaimed acceptance work.
- 2026-08-12 components: AEGIS Light validation passed 162 tests with one skipped test.
- 2026-08-12 components: Adopted release and acceptance tooling from nine planning contracts; compilation succeeded, ten tool tests passed, and the reviewed catalog parsed as 226 requirements and 58 scenarios.
- 2026-08-12 components: Logged missing focused regressions for bundled-runtime lock rejection and crafted unsafe archive inspection; no release-campaign evidence was executed or inferred.
- 2026-08-12 close: Completed all seven component records and linked the adoption journal to all 92 planning-derived requirement projections.
- 2026-08-12 close: Whole-tree AEGIS Light check reported zero errors and 16 warnings: three explicit test backlogs plus pre-existing dirty-tree layout, zone, and coverage signals.
- 2026-08-12 close: Full AEGIS package validation passed 172 tests in 249.15 seconds and the canonical CLI help smoke test completed.
- 2026-08-12 close: Generated the adoption report in this journal; commit, publication, and done transition remain intentionally withheld by owner instruction.

## Delivery report (2026-08-12)

- stage: close; type: adopt; path: full; branch: master
- requirements:
  - REQ-DATA-79ebcb34 - Plain-file traceability and resumable journals
  - REQ-DATA-ecc88768 - Inventory every archive member and release identity
  - REQ-FUNC-0ed3f1b4 - Close delivery only after approval
  - REQ-FUNC-1407b21b - Idempotent repository initialization
  - REQ-FUNC-29090f7f - Keep component context concise and current
  - REQ-FUNC-294b8bf7 - Keep adoption incremental and resumable
  - REQ-FUNC-29f57326 - Bound machine response content honestly
  - REQ-FUNC-41d09b16 - Present one application result consistently
  - REQ-FUNC-428573c5 - Assemble bounded relevant stage context
  - REQ-FUNC-4e4fb4c9 - Upgrade without losing project data
  - REQ-FUNC-574eb6e6 - Model software as file-backed components
  - REQ-FUNC-5acb044e - Heuristic integrity reporting
  - REQ-FUNC-629674ff - Preview installation before writing
  - REQ-FUNC-7761f525 - Maintain current requirement-file-test traceability
  - REQ-FUNC-7a19b623 - Keep human and machine result semantics equal
  - REQ-FUNC-7b02b6ae - Durable task and requirement scaffolding
  - REQ-FUNC-a6f115bd - Return structured errors instead of tracebacks
  - REQ-FUNC-c771a1d1 - Install AEGIS into repositories
  - REQ-FUNC-e04edca3 - Keep each ticket in a distinct run
  - REQ-FUNC-e4f0da51 - Command execution and delivery reporting
  - REQ-FUNC-e5c2b57d - Keep workflow meaning identical across hosts
  - REQ-FUNC-fda66019 - Expose the eight-stage workflow
  - REQ-NFR-4b767a8b - Construct the object graph only at composition
  - REQ-NFR-6f1a6621 - Bounded small-model-friendly output
  - REQ-NFR-9aec5e3a - Advisory governance by default
  - REQ-NFR-bb398def - Depend only on the Python standard library
  - REQ-NFR-c6ba4132 - Keep WAEGIS persistence independent
  - REQ-NFR-e5017804 - Keep dependencies pointing inward
  - REQ-PLAT-0818067b - Authorize local repository initialization separately
  - REQ-PLAT-0badc589 - Identify relocatable project artifact locations
  - REQ-PLAT-0e917260 - Declare each product version once
  - REQ-PLAT-133b74ac - Portable standard-library operation
  - REQ-PLAT-1b680071 - Discover the installed Git repository boundary
  - REQ-PLAT-248442e0 - Use one canonical flat command spelling
  - REQ-PLAT-4253ae41 - Expose no mutating Git operations
  - REQ-PLAT-47c97052 - Render canonical UTF-8 text
  - REQ-PLAT-4ce82986 - Reserve machine stdout for one JSON response
  - REQ-PLAT-5afdbb8a - Invoke the same protocol from host adapters
  - REQ-PLAT-5c1bc460 - Support named categorized validation commands
  - REQ-PLAT-608b140d - Declare operation metadata once
  - REQ-PLAT-67c5d05e - Provide machine output for every command
  - REQ-PLAT-7663bb1d - Keep host adapters policy-free
  - REQ-PLAT-7cd54b8e - Support multiple agent hosts
  - REQ-PLAT-888ec3c2 - Use repository-relative response paths
  - REQ-PLAT-97b168cf - Use read-only machine-stable Git observation
  - REQ-PLAT-a4fcb436 - Configure command working directories and timeouts
  - REQ-PLAT-b5a7fd61 - Check external runtime prerequisites without installation
  - REQ-PLAT-bc526721 - Support the initial five agent hosts
  - REQ-PLAT-c1bc7244 - Avoid outward and integration Git actions
  - REQ-PLAT-c820ce6c - Generate complete detected or default configuration
  - REQ-PLAT-cebb1b2b - Support multiple configured test roots
  - REQ-PLAT-cff1cf5e - Default to unlimited command execution time
  - REQ-PLAT-d5dd084c - Keep AEGIS and WAEGIS protocol envelopes aligned
  - REQ-PLAT-ef45ae63 - Execute command argument arrays without a shell
  - REQ-PLAT-f183e3cc - Use one flat argparse subparser per command
  - REQ-REL-0b1d9e84 - Hash exact bytes before normalization
  - REQ-REL-25745fd4 - Use the manifest as payload ownership authority
  - REQ-REL-2c12ed5d - Record the run opening repository state
  - REQ-REL-2dd22908 - Supply expected revisions for machine mutations
  - REQ-REL-360930b1 - Resume every stage from repository state
  - REQ-REL-39719eb5 - Recover according to the atomic decision
  - REQ-REL-3c9287e0 - Cancel only the configured process group
  - REQ-REL-5858abac - Drain process output without deadlocks
  - REQ-REL-5b6e4c2c - Separate payload ownership from project data
  - REQ-REL-5bd5c6ae - Bind retained evidence to one release candidate
  - REQ-REL-5fc2eb80 - Build a version-consistent transferable archive
  - REQ-REL-65d839d8 - Return state conflict for stale revisions
  - REQ-REL-6c4a525d - Publish state atomically
  - REQ-REL-7093e21e - Distinguish structured protocol error classes
  - REQ-REL-7289f5f4 - Make lifecycle plans exact and digestible
  - REQ-REL-862a5141 - Avoid unsupported change authorship
  - REQ-REL-92820eeb - Reject stale reads before transaction preparation
  - REQ-REL-995954b5 - Report modified payload files as findings
  - REQ-REL-9aaaf19c - Leave incomplete process conclusions unknown
  - REQ-REL-b2d83e85 - Compile acceptance verdicts without manufacturing passes
  - REQ-REL-b3f193a8 - Produce the eight offline release editions
  - REQ-REL-b6f54754 - Recover workflow state after interruption
  - REQ-REL-bf10ed27 - Keep lifecycle planning read-only
  - REQ-REL-c20d6246 - Classify configured process outcomes exactly
  - REQ-REL-c5bc94c6 - Preserve malformed authoritative bytes
  - REQ-REL-ce2d823d - Preserve pre-existing dirty work
  - REQ-REL-d13d0127 - Exempt non-overwriting operations from revision tokens
  - REQ-REL-d204dc36 - Verify exact local bundled runtime inputs
  - REQ-REL-de2680dc - Record unresolved adoption gaps
  - REQ-REL-e8675f89 - Revalidate plans before applying
  - REQ-REL-ed654c7e - Embed the exact AEGIS payload in WAEGIS editions
  - REQ-SEC-91dd1489 - Reject repository path escapes
  - REQ-SEC-af5073fb - Reject unsafe or inconsistent archives before extraction
  - REQ-TEST-07679fdc - Focused regression with safe fallback
  - REQ-TEST-71e4e6b2 - Fallback when impacted traceability is unsafe
  - REQ-TEST-c33c5899 - Require executed red-before-green evidence
  - REQ-TEST-e2b43472 - Validate the authoritative acceptance catalog
- diff vs merge base: 129 file(s) changed, 7950 line(s) added
- checks: errors=0 warnings=16 notes=0
- checklist: 8/10 done; open: journal and report inside the adoption commit; agreed outcome delivered; close-out: stage done set and committed only after that
- components: 7/7 adopted
