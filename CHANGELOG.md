<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to AEGIS are documented in this file.

## [Unreleased]

## [0.15.0] - 2026-10-25

### Removed

- Remove three test cases that depended on an AEGIS deployment in this
  repository, following removal of that workspace installation.
- Remove the deliver stage and `steps/6_deliver.md`. Validate now closes the
  task with the final proof, `report` and `advance` to `done`; commits, pushes,
  pull requests and merges follow the repository's own procedures. A journal
  still at `stage: deliver` closes through validate.
- Remove the September workflow-overhead study
  (`10_Workflow_Overhead_Analysis.html`) and six unused evidence images from
  the plugin installation guides.

### Added

- Add CLI journal writers: `advance`, `pause`, `log`, `ruling` and `verdict`
  write the header stage, Done checklist, Log, Rulings and State. They record
  the agent's decision and never refuse it; `advance` notes unticked checklist
  items, and unapproved explicit review at `done`, in the Log. Both print notes
  when frame, specify or design stops with its own journal section empty, and
  for a repeated header key, a quick-path journal without the requirement IDs
  it restores, and Rulings lines that `ruling` did not write.
- Add the `journal` operation (`aegis_journal`) to every agent adapter.
- Make `brief` print the path, the computed diagram decision and a `Read next`
  line naming the step file and the State `must_read` paths. While the State
  waits on the user, `Read next` also names the `advance` that moves on when
  they continue to the next stage, or close the task from validate. Adoption,
  which pauses after each component inside one stage, gets no such hint.
- Make `log` note a line that records a later stage's work, such as `final:`
  while the journal is still at build; the line is logged either way.
- Add `steps/review.md`, read only when explicit review is enabled.

- Extend development prompt evaluations across all eight step prompts, with
  real reviewer sessions, diagrams, autopilot and context-update cases.
- Run the fifteen capability evaluation cases against a local Chat Completions
  model, with fresh local reviewer sessions on one immutable snapshot.
- Record prompt tokens per run and per file read in local evaluations, flag
  runs above half or three quarters of the loaded window, and compare medians.
- Add a hold-out pricing evaluation domain that gates prompt changes and never
  shapes prompt rules, with frame, specify and design cases.
- Add a chained evaluation that runs five fresh stage sessions on one repository;
  its Build code is limited to two files and a restricted Python subset.
- Report configured semantic checks beside strict checks, and strict and
  semantic pass rates per case across repeats, in reports and comparisons.
- Add `--reasoning-effort` to the local evaluation runner. It is sent only when
  set, recorded in the manifest and compared as a control; a turn's reasoning
  is never sent back with the history.

### Changed

- **Breaking:** journals keep one CLI-written `## State` block instead of
  `## Handoff` and `## Stage report`. `brief`, `summary`, `status`, `check` and
  `report` read both formats; the first State write replaces the old sections.
- Rewrite `AGENTS.md` (31 KB to 9 KB) and the stage cards around the CLI
  writers, feature-by-feature work and concurrent branches. A stage session
  reads about 14 KB of workflow text instead of 58-75 KB.
- Generate journals, requirements and context pages without the payload license
  header; the journal template's authoring notes shrink from 220 to 40 lines.
- Give specify one deterministic atomicity rule and a five-column coverage
  table, and design about 30 lines under five headings.
- Have design compare every structure-node class in a diagram with the saved
  Design and classify each edge on its own; a mismatch is fixed in the
  diagram, never by changing the Design.
- Make the root digest route to `.agentic/AGENTS.md` instead of standing in for it.
- Have a frame example name a value the user has not given, such as `N days`,
  instead of choosing a number; models filled "at least one example" with
  invented periods. Start the reply with the printed summary block, never one
  written by hand.
- Have frame keep unverified conditions UNKNOWN: a request for new behavior
  does not establish a current defect or existing data.
- Leave branch creation to the developer, like commits: frame works on the
  current branch, which the journal records, and notes when that is the
  default branch.
- Make `task` refuse a bare task ID as its title and point to `brief`; such a
  call meant to resume a task and opened a second journal instead.
- Write the component and requirement templates and the build card with
  language-neutral `<source file>` and `<test file>` placeholders; link a test
  as `<test file>::<test name>` only where the test runner accepts that
  selector.
- Have adoption create requirements with `req`, and name the State among its
  resume records.
- Give each evaluated payload its own fixture-state format, root digest and CLI
  commands, keep the compared host contract payload-independent, and score
  either record format; scenario prompts no longer name Handoff or Stage report.
- Give local core evaluations the installed root digest that the native core
  profile already supplies, so both transports start from one instruction text.
- Default local evaluation deadlines to 2,400 s per case and 900 s per request;
  add optional top-p, top-k and presence-penalty sampling, a `loop` outcome for
  repeated tool calls or text, and a count of degenerate responses.
- Align the user guides and slide decks with the State, the CLI journal
  writers, closing in validate, review/proof ordering and diagram presentation.
- Keep the planning record to the current implementation, and align it and
  the product, tools and root READMEs with the journal writers, the State,
  twelve adapter operations and the absence of a repository-root `.agentic/`.

### Fixed

- Read a journal header key written twice by its first written value, the line
  the writers update. An agent's inserted `requirements:` line was hidden by
  the template's empty one.
- Point the arrows in the five plugin installation flow figures, and in the
  PDFs that embed them, from step 1 to step 5; they pointed backwards.
- Count an evaluation `read_file` on a directory as an unavailable capability,
  not a forbidden action; Windows previously failed such cases.
- Reject non-string evaluation tool paths as tool errors instead of stopping
  the evaluation host.
- Read the loaded context window after each evaluation case, because LM Studio
  loads idle models on demand, and ignore server load state in comparisons.
- Count a tool name passed as a `run_command` program, a CLI command the
  evaluated payload lacks, or a malformed `req` scaffold as an unavailable
  capability rather than a forbidden action; let `req --help` run; and accept
  labelled missing-evidence reports such as `unavailable: no tests run`.
- Let the evaluated CLI decide which `req` categories exist (harness 11). The
  hold-out and capability hosts refused aliases such as `func` that the CLI
  accepts, with a message about argument shape, and a model retried the call
  until the loop limit. A `git` program repeated as its first argument is now
  a wrong call too, unless what follows is a write.
- Make the evaluation `read_file` read whole lines from a 1-based `offset` for
  `limit` lines and report `total_lines`, `eof` and `next_offset` (harness 12).
  It counted characters, and a model that read the numbers as lines paged a
  7 KB journal 60-400 characters at a time until the turn limit. Harness 12
  results are not comparable with harness 11 where sessions page through files.
- Score two capability predicates by the behavior, not one spelling (harness
  13): linked tests may be `file::test` node ids, the documented form, as long
  as each names a test the file defines; project context may state the trim
  in any words, such as "surrounding whitespace removed". Every model failed
  the first and Qwen the second while doing the right thing.
- Accept "no verification evidence available" as a missing-evidence report
  (harness 14); Qwen wrote it after correctly running nothing.

## [0.14.0] - 2026-10-20

### Added

- Add a local prompt-evaluation harness with ten frame, validate and task-record
  scenarios, recorded model/tool evidence and controlled baseline comparisons.
- `[records] commit_fingerprints` (default `false`): `init` maintains a
  managed block in the root `.gitignore` that keeps anchor and evolution
  sidecars out of git, removes it when the setting is `true`, and names
  sidecars that are still tracked without running any git write. A new
  `fingerprints-tracked` check reports a repository that disagrees with the
  setting.
- Document every configuration setting with the value `init` writes and the
  behavior that applies when the key is absent, in the installation guide and
  as a new settings slide in its deck.
- Optional `[diagrams]` setting, off by default: design draws Mermaid diagrams
  of the proposed implementation into `tasks/diagram_TASK-<id>.md` for review.

### Changed

- Clarify frame, validate and task prompts with plain-field examples, synchronized
  pause records, stale-verdict clearing and explicit limits on record-only work.
- Keep inferred scope and missing historical evidence explicit, preserve complete
  return checklists, and qualify continuation choices by proof and review state.
- Require shared task-record authoring guidance for limited updates, with concrete
  resume decisions and no placeholder Rulings for missing authority.
- Keep next actions about current execution and distinguish observed absence
  or environment facts from scope exclusions and dependency policy.
- Increase the prompt-evaluation output budget to 16,384 tokens per response
  to accommodate local-model reasoning.
- Use repo-relative paths in workflow transitions, instructions, CLI guidance,
  and host prompts so agents can open the intended files from the checkout root.
- Reconcile component knowledge in validate before final review and proof;
  update during build only when needed for an agent handoff.
- Accept `[review] max_fix_cycles` from 0 through 255 instead of 0 through 5;
  the default stays 2 and total review rounds remain `1 + max_fix_cycles`.
- Name `[layout] default_branch` in the configuration `init` writes and in
  the configuration guide, so every key the CLI reads is discoverable from
  the generated file.
- State how the default branch resolves where the CLI reference relies on it.
- Carry `[layout] default_branch` and `[interaction] autopilot` into the
  configuration table of the Folders & Files guide and deck.

### Removed

- The design `### Proposed architecture` and component `## Architecture`
  diagrams; validate drops a retired section from a page it updates.

### Fixed

- Support discoverable, bounded read-only Git inspection in prompt evaluations
  and recognize explicit missing-verification reports without masking real runs.

## [0.13.0] - 2026-09-10

### Added

- Project-owned project/environment context scaffolds and compact resume pointers.

### Changed

- Align planning and user guides with current context behavior and keep dated
  verification history in task/build records; refresh installation PDFs.
- Keep project, component, and active behavior documentation current and positive;
  record proposals and investigation history in draft/task records.

- Default to a user choice checkpoint after every workflow stage, with optional
  project-configured autopilot that never bypasses publication approval.

## [0.12.0] - 2026-09-08

### Added

- Add test command previews and opt-in refusal of full-suite fallback, plus
  compact evolution responses that preserve complete saved evidence.

### Fixed

- Broaden unsupported test-name selectors to validated file references without
  interpolating their text into shell commands.

### Changed

- Prefer project-native focused build tests and one final full validation;
  omit template-only scaffold notes and repeated stage instructions.

- Make task journals compact progress-and-evidence ledgers by consolidating
  verification and excluding routine tool activity and duplicated artifacts.

## [0.11.0] - 2026-09-04

### Added

- Add a read-only `components` command that lists component knowledge titles
  and paths for low-context navigation.

### Changed

- Limit `DEVIATION` notices to material scope, implementation, contract, or
  verification departures; corrected internal tool errors are operational detail.

- Turn component knowledge pages into concise implementation routes with
  selection signals, boundaries, invariants and focused change-and-test seams.

## [0.10.0] - 2026-09-03

### Added

- Added portable Claude Code AEGIS plugin resources, bounded context hooks,
  local MCP tools and Windows/Linux owned lifecycle.

- Portable Pi and Qwen Code AEGIS extensions with native tools/commands,
  independent review support and configuration-preserving Windows/Linux setup.

- Portable OpenCode and Codex integrations with AEGIS agents/skills, independent
  review roles, safe local installation and shared tracked verification.

### Changed

- Strengthen Frame, Specify and Design with evidence classification, durable
  idea capture, behavior-coverage checks, concrete verification guidance, and
  complexity-proportionate design that keeps proposals separate from current
  component knowledge.

- Align the root overview and planning documents with the core workflow, five
  host integrations, package ownership and verified implementation limits.

## [0.9.1] - 2026-09-02

### Added

- Read-only `trace` command exports the complete requirement register as Markdown
  or CSV, with coverage, ownership, verification, tests and affected paths.

### Fixed

- Use the configured Python runtime for this repository's impacted tests.

## [0.9.0] - 2026-08-31

### Added

- Added optional one-level child tasks, deterministic bounded briefs, and durable rulings and handoffs for coordinated offline work.
- Added optional independent review verdicts with configurable bounded fix and re-review cycles.

## [0.8.0] - 2026-08-28

### Added

- Read-only `summary` command for compact recorded stage reports, with explicit
  missing/stale state and visible output limits.
- Optional documentation layout globs avoid stray-file warnings while keeping
  documentation in secret scanning.

### Changed

- Standardize stage reports and summary-first resume instructions for limited
  context, preserving existing approvals and full validation requirements.

## [0.7.2] - 2026-08-22

### Fixed

- The delivery report harvests a deviation only where the marker carries a
  real workflow stage (`DEVIATION <stage>: ...` or its ` - ` spelling). 0.7.1
  accepted any word after the marker, so ordinary prose about deviations - and
  a journal quoting the marker itself - was listed in the report as recorded
  judgement.

- The delivery report no longer drops a deviation written on a line of its
  own. 0.7.1 harvested only `- ` bullets, so the exact unbulleted shape
  `AGENTS.md` prints in its own contract block was invisible to `report`.

- `diagram` and `explain` now classify coverage by the outcome `check` reaches
  for the same record, through one shared classifier rather than a second
  reading. 0.7.1 pivoted on whether a linked file existed while `check`
  pivoted on whether `linked_tests` was non-empty, so a requirement whose only
  linked test had been deleted was drawn as deliberate hand-verification, and
  a draft was drawn as an uncovered behavior.

### Added

- Two coverage classes, so each one maps onto a single `check` outcome:
  `broken` for a requirement whose linked test does not resolve, matching the
  `no-linked-tests` warning, and `draft` for a record `check` is deliberately
  silent about. The `diagram` CLI reference now tabulates every class against
  the finding it stands for.

### Changed

- Clarify that AEGIS governs software development only; repository and
  package or delivery operations follow the repository's own procedures.

- Produce separately named Windows ZIP and Linux tar.gz delivery archives.

## [0.7.1] - 2026-08-22

### Fixed

- `explain` now matches a directory against its own trailing-slash
  `affected_paths` entry, instead of calling the governed directory ungoverned.

- `explain` normalizes `.` and `..` segments in a relative path, so equivalent
  spellings of one file give one answer, and rejects a path that escapes the
  repository or carries a drive letter the platform did not read as absolute.

- The delivery report harvests only marker-shaped deviations
  (`DEVIATION <stage> - ...`), not sentences that mention the word, and no
  longer re-counts its own earlier reports on a second run.

- Wrapped `## Done checklist` items are rejoined when a journal is parsed, so
  `report` and `status` no longer cut an item at the line break.

- `diagram` calls a requirement tested only when its linked test file exists,
  the same judgement `check` makes, and gives colliding component names
  distinct Mermaid subgraph ids.

- `diagram --component` with `--task` now exits 1 with one error line, matching
  the documented exit behavior for an expected CLI error.

- Repaired a corrupted Windows path example in the `explain` CLI reference.

## [0.7.0] - 2026-08-21

### Added

- Add the `explain` command: given a repository path it reports every
  requirement whose `affected_paths` cover it, grouped under the component
  whose knowledge page claims each one, with status, coverage and spec, then
  the task journals that list them. A directory entry covers the files
  beneath it, absolute and native-separator paths are accepted, and a path no
  requirement covers is stated plainly - and called a finding when it sits
  inside the configured source or test globs. The register was written once
  per behavior and read almost never because nothing led from code back to
  it; this is that direction.

- Carry each component's architecture in its knowledge page. The component
  template gains an `## Architecture` section holding a Mermaid diagram of
  that component's own logic; adoption draws one per component while its
  source is still open, `design` revises it to the shape the change will
  produce and labels it as intended, and `validate` reconciles it with the
  built code and drops that label. Authored rather than derived, so it works
  in any language and can show a shape that does not exist yet.

- Add the `diagram` command: it draws the requirement register as a Mermaid
  flowchart, grouping each requirement under the component whose knowledge
  page claims it and coloring it by whether a linked test, a declared
  `Manual:`/`Inspection:` method, or nothing yet verifies the behavior.
  Requirements no page claims are grouped apart instead of dropped, so an
  unclaimed behavior is visible rather than absent. `--component` and
  `--task` narrow the picture, which a register past a few dozen entries
  needs; `--out` writes UTF-8 explicitly, because a console under a legacy
  code page mangles the characters on the way out. Everything drawn is read
  from files already in the repository: no model, no network, no renderer.

### Changed

- Lead the delivery report with the deviations the task recorded, above the
  diff size and check totals, and say plainly when none were recorded. A
  warning count tells an approver how much happened, never which judgement
  calls were made on their behalf, and the delivery checkpoint is the one
  moment the workflow guarantees a human is reading.
- Rejoin wrapped log lines when parsing a journal, so a deviation survives the
  margin and `status` stops printing half-sentences.

## [0.6.0] - 2026-08-18

### Added

- Add deviation notices to the interaction modes: the agent now states an
  anomaly in the conversation at the moment it records one, as a single
  `DEVIATION <stage>:` line, instead of leaving the journal to reveal it at
  the delivery checkpoint. A notice never pauses the work, waits for no
  reply, and is not suppressed by autopilot. The build, validate and deliver
  steps name the points that raise one - an accepted `check` warning, a
  non-zero exit or a skipped verification, an unexpected `anchor` or
  `evolution` report, a manual method standing in for an automatable test, a
  retired requirement, and unrequested work found in diff review - and
  delivery still presents every deviation in full, because a notice informs
  but never approves.

### Changed

- Carry the deviation notice into the digest `init` writes into `CLAUDE.md`,
  `AGENTS.md` and `QWEN.md`. The digest is what an agent acts on when it reads
  nothing else, so omitting the rule there would have left every downstream
  repository silent by default.
- Update the user guides for deviation notices: the FAQ gains a "What is a
  `DEVIATION` line?" entry and separates the agent's spoken judgement from
  `check`'s own `WARN`/`NOTE` findings, the checkpoint and autopilot
  walkthroughs now show a notice arriving mid-run, and the autopilot guidance
  states that it suppresses the frame stop but never the notices.

### Fixed

- Clear the repository lint failure so `check --strict --run` exits 0. The
  payload gains explicit `check=False` on the two `subprocess.run` calls that
  already read `returncode`, a single `startswith` tuple, parenthesized
  implicit string concatenations, `re.MULTILINE` in place of `re.M`, and
  sorted imports; no behavior changes. Two findings are suppressed with a
  stated reason rather than "fixed": the journal date stays on the local
  calendar, and the capture sink is a deliberately long-lived handle.

## [0.5.0] - 2026-08-14

### Added

- Add advisory `anchor` and `evolution` commands that fingerprint Git-visible
  repository files around implementation, retain compact timestamped change
  reports, and add NOTE-only scoped-task guidance when records are missing.
- Add Git availability and repository detection to `init`, with explicit
  opt-in repository creation through `init --git`.

### Changed

- Consolidated the repository around AEGIS. The former lightweight package,
  documentation, workflow markers, and release record now use the AEGIS name.

### Fixed

- Treat Boolean command timeout values as invalid instead of converting
  `true` into a one-second limit.
- Apply `[check] ignore` to unscanned secret-diff gaps, and scan added content
  lines beginning with two literal plus signs.
- Keep impacted-test selection and repository evolution stable when Python
  creates `.pyc`/`.pyo` files or `__pycache__/` directories under source roots.
- Restore `validate` to the quick-path sequence in the frame-stage guidance.
- Flush the `test` command announcement before child output, identify malformed
  journals by filename in human status output, and correct small workflow and
  CLI reference inconsistencies.
- Migrate legacy `AEGIS-LIGHT` managed guidance markers during `init` and
  collapse duplicate old/new blocks left by an interrupted upgrade.

## [0.4.0] - 2026-08-14

### Added

- Advisory task workflow with requirements, specifications, knowledge pages,
  structured checks, focused test selection, and machine-readable reporting.
