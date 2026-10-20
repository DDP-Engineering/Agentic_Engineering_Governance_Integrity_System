<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->


# TASK-fcd51702 - Draw optional implementation diagrams for the human at design

stage: deliver
type: feature
path: full
interaction: autopilot
requirements: REQ-FUNC-ee1d2096, REQ-UX-b0bd0225, REQ-FUNC-f7220cb2, REQ-FUNC-cd29e673, REQ-FUNC-6343dfb8, REQ-FUNC-9db20045, REQ-FUNC-3e0263e7, REQ-FUNC-500cfb8b, REQ-FUNC-87aea7e9
parent:
branch: ddp/optional-diagrams
base: 52e07725789885e8ec444d8219bbb4e54ef9ecf0
opened: 2026-10-20

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [x] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Frame

Problem: Before build writes code, the human operator has no clear picture of
what the agent proposes to change. The payload requires two kinds of
diagram, but neither serves that need. Design owes a
`### Proposed architecture - TASK-<id>` diagram inside the journal only when
"component structure will change" (OBSERVED
`05_Software/aegis/template/.agentic/steps/3_design.md:73-78`, Done when :112).
Every component page owes a current-state `## Architecture` diagram, drawn at
adoption and reconciled at validate (OBSERVED `templates/component.md:72-97`,
`steps/adopt.md:80`, :148, `steps/5_validate.md:94`, :98-102, :192;
REQ-FUNC-500cfb8b). Both are obligations that stages must produce, maintain
and tick off. The proposed diagram carries no added/changed marks and sits
inside an already large journal.

Desired outcome: One optional setting controls every model-drawn diagram.
Off by default, and off when the setting is missing (STATED). When on, design
draws diagrams of the proposed implementation for the human, in a separate
file linked from the task, and shows them at the design checkpoint in
checkpoint mode (STATED). The diagrams are a communication aid only: no
stage, `check` rule, Done-when item, validate step or review verifies them
(STATED). The previously required diagrams are no longer drawn (STATED).

Actors: human operator (reads the diagrams at the design checkpoint); coding
agent, including small open-source models
such as qwen3.8-27b (STATED); downstream projects that copy the payload; the
AEGIS CLI (reads the configuration).

Primary scenario: the operator sets `[diagrams] enabled = true` -> a full-path
task reaches the end of design -> the agent writes
`.agentic/tasks/diagram_TASK-<id>.md` from the final Design note, links it
once from `## Design`, and in checkpoint mode shows the diagrams before the
design stage-boundary choices -> the operator reviews the proposed shape and
picks one of those choices.

Examples:
- E1 (every existing project): `aegis.toml` has no `[diagrams]` table. Design
  writes its note; no stage draws or asks for a diagram.
- E2: `enabled = true`, `types = ["structure", "sequence"]`; a task adds a CLI
  command that calls a plugin subprocess. Design writes one structure and one
  sequence diagram into `diagram_TASK-<id>.md` and shows both at the
  checkpoint.

Counterexamples:
- Quick-path fix with `enabled = true`: there is no design stage, so no diagram.
- Autopilot with `enabled = true`: the file is written but not displayed; no
  stop is added.
- `enabled = true` but design ends without a diagram file: no finding,
  warning or validate step reports it.

In scope:
- Payload (`05_Software/aegis/template/.agentic/`, mirrored into `.agentic/`):
  an optional diagram step at the end of `steps/3_design.md`, with drawing
  rules in a separate file read only when enabled; removal of the proposed
  architecture obligation (design step 8, its output and Done when) and of
  the component `## Architecture` obligation (`templates/component.md`,
  `steps/adopt.md`, `steps/5_validate.md`, mentions in `steps/4_build.md:52`
  and `AGENTS.md:144`); AGENTS.md artifact table and configuration text.
- `aegis.py`: the `[diagrams]` keys in `CONFIG_SHAPE` (OBSERVED :1779) and in
  `DEFAULT_CONFIG` written by `init` (OBSERVED :94), following the fail-safe
  `[review]` pattern (OBSERVED `review_settings` :394).
- Tests: replace the architecture-obligation tests in
  `05_Software/aegis/tests/test_structure.py` (:543, :662, :671, :709); add
  configuration tests beside the review ones in `test_cli_core.py` and
  `test_check.py`.
- Requirements: retire REQ-FUNC-500cfb8b; new requirement(s) for the option.
- Repository knowledge pages touched by the task, including removal of their
  `## Architecture` sections. Four pages carry one on this branch:
  `agent_integrations.md`, `core-cli-lifecycle.md`,
  `reusable-workflow-payload.md`, `validation-and-evidence-cli.md`.
- Documentation: root `CHANGELOG.md` Unreleased, `05_Software/aegis/README.md`,
  `06_SoftwareDocu/01_Install_and_Setup.md` and its deck settings slide
  (every setting is documented there - OBSERVED `CHANGELOG.md` Unreleased),
  `06_SoftwareDocu/03`, `05`, `07`, `08`, and `00_Planning/01`, `02` where they
  describe architecture diagrams.

Out of scope:
- Bundling `mermaid.js`, an HTML export, or any rendering command (STATED).
- Any verification of diagrams in `check`, validate, Done when or review
  (STATED).
- The `aegis diagram` requirement-coverage command. The human runs it; the
  model never draws it.
- Host integration code. Reviewer prompts and skills do not mention diagrams
  (OBSERVED: no hits for architecture/mermaid/diagram under
  `05_Software/aegis/integrations/` outside tests and vendor).
- Diagrams at frame or any other stage.
- Redrawing a diagram, drawing a new one, or explaining one when the operator
  asks. That stays between the operator and the model, and AEGIS does not
  specify it (STATED, RULING-005).
- CodeGraph. It is an evaluation that stays on `ddp/codegraph-plugin-plan`
  and is not planned for the official distribution, so this task owes it no
  compatibility or merge (STATED, RULING-006).
- Version assignment and release (repository operation).
- Reducing journal Log or knowledge-page size (separate proposal).
- Downstream projects such as `D:\2026_AI_SDLC\ai-sdlc`.
- Housekeeping of the untracked `.agentic/knowledge/codegraph/` folder.

Constraints:
- Offline-first and self-contained: no new dependency (STATED; root
  `AGENTS.md` Repository Rules).
- The payload stays generic, with no project facts (root `AGENTS.md`).
- Local models are planned for a 128k context baseline. The default-off read
  cost must not grow: the design step adds a pointer of about one line, and
  the drawing rules are read only when enabled (INFERRED from the STATED
  small-model requirement).
- Preserve established contracts except the user-authorized retirement
  (STATED); every other config key and stage behavior stays unchanged.
- Frame, specify and design write only under `.agentic/` (payload write
  zones).
- Documentation changes ship in the same change. No automated tests assert
  prose under `06_SoftwareDocu/` or `00_Planning/` (root `AGENTS.md`).

Success signals:
- S1: With no `[diagrams]` table, with `enabled = false`, or with an invalid
  value, the payload instructs no diagram anywhere. The config check warns
  only on a wrongly typed value.
- S2: `init` writes `[diagrams]` with `enabled = false` and the types key, each
  with its rationale.
- S3: With `enabled = true`, the design step names the file, the link, the
  enabled types and the checkpoint display. Build, validate and reviewers
  are never told to read the file.
- S4: A file named `diagram_TASK-<id>.md` under `.agentic/tasks/` is not
  treated as a journal by `status`, `check` or `brief`. Changing it does not
  change the host review candidate.
- S5: No payload file requires, reconciles or ticks off `## Architecture` or
  `Proposed architecture`. REQ-FUNC-500cfb8b is retired, and tests guard the
  new text and the configuration handling.

Evidence:
- STATED: everything in Desired outcome; the file location
  `.agentic/tasks/diagram_<task_id>.md`; no `mermaid.js`; types are
  configurable; on-demand redraws and explanations are outside AEGIS; branch
  from master; CodeGraph is a separate evaluation; support for small
  open-source models; A1-A6 confirmed.
- OBSERVED: journals are discovered with `glob("TASK-*.md")` (`aegis.py:548`,
  :1225, :2314). The host review candidate skips `.agentic/tasks/`
  (`05_Software/aegis/integrations/shared/adapter.mjs:94`). Anchor and
  evolution skip `.agentic/` (`aegis.py:620`). `outside-layout` exempts
  `.agentic/` (`aegis.py:2530`). The managed `.gitignore` block covers only
  anchor/evolution sidecars (`[records]` in `DEFAULT_CONFIG`). The payload
  mirror matches `.agentic/` apart from bytecode. Branch
  `ddp/optional-diagrams` was cut from master `52e0772` (AEGIS 0.13.0).
- OBSERVED in the user-supplied reference project `D:\2026_AI_SDLC\ai-sdlc\.agentic`
  (147 journals): median journal 26.7 KB and maximum 130 KB; the Log section
  holds 41% of journal bytes. Its 36 journal diagrams have a median of
  675 bytes. Its 4 component diagrams have a median of 46 nodes and a
  maximum of 117.
- INFERRED: `diagram_TASK-<id>.md` matches none of the journal globs and
  stays outside the review candidate. Mermaid text in Markdown is the format
  that satisfies "no `mermaid.js`" while rendering in GitHub/GitLab and in
  capable viewers.
- UNKNOWN: see Unknowns.

Assumptions (confirmed by the user at the frame checkpoint):
- A1: The file is named `diagram_TASK-<hex>.md`, using the full task ID so a
  search for the ID finds both files.
- A2: Diagrams are Mermaid text in that Markdown file. Offered types are
  `structure` (flowchart), `sequence` and `state`, with `types` defaulting to
  `["structure"]`. Added/changed/removed marks are guidance, not checked.
- A3: In autopilot with `enabled = true`, the file is still written and its
  path is reported. Only the display is skipped.
- A4: The Design text is authoritative, and the diagram illustrates it.
- A5: When validate updates a component page for a task, it removes that
  page's `## Architecture` section. Existing pages are otherwise untouched.
- A6: Redrawing a diagram adds no Log entry. This is satisfied by leaving
  redraws outside AEGIS (RULING-005): the payload says nothing about them.

Unknowns:
- U1: Which host chats render Mermaid. This was not measured per host, and
  no behavior depends on it.
- U2: Whether `brief` or the root pointer digest should name the setting.
  Design decides; the default is no, to keep the default-off read cost flat.
- U3 (resolved): no merge with `ddp/codegraph-plugin-plan` is planned
  (RULING-006).

Decision-blocking questions: none.

Proposed behaviors:
- PB1 (S1, S2): `[diagrams]` with `enabled` (bool, default false) and `types`
  (list). Missing, false or invalid means off. `init` writes both, and the
  config check warns on wrong types.
- PB2 (S3, S4): where enabled, design ends by writing
  `.agentic/tasks/diagram_TASK-<id>.md` from the final Design, with one
  section per enabled type that applies, and links it once from `## Design`.
- PB3 (S3): in checkpoint mode, the design presentation shows the diagrams
  before the stage-boundary choices. Autopilot reports only the path.
- PB4: withdrawn at the frame checkpoint. On-demand redraws and explanations
  are outside AEGIS (RULING-005).
- PB5 (S1, S3, S5): no stage, Done-when item, `check` rule or review requires
  or reads diagrams.
- PB6 (S5): component pages carry no `## Architecture` section. The template,
  adopt and validate drop it, and REQ-FUNC-500cfb8b is retired.

Path and reason: full.

| criterion | yes | no | evidence |
|---|---|---|---|
| no new externally observable behavior | | no | new optional design output and display |
| no new interface or data format | | no | new `[diagrams]` config table and a new task file |
| no new dependency | yes | | Mermaid text only, nothing bundled |
| an existing requirement covers the behavior | | no | REQ-FUNC-500cfb8b is retired, not reused |
| no security- or data-handling change | yes | | config and Markdown only |

Children: none. The payload edits are small and tightly coupled.

## Requirement coverage

Behavior inventory (Frame outcome | actor/system | trigger or state | response | observable result):

- PB1 | config + agent | `[diagrams]` missing, `false`, or not a boolean | diagrams off | no stage draws; `init` writes `enabled = false`
- PB1 | `check` | `enabled` not a boolean, `types` not a list of known names | advisory warning | one WARN config finding naming the key
- PB2 | agent at design | `enabled = true` and a design note exists | write diagram file and link it | `.agentic/tasks/diagram_TASK-<id>.md` plus one Design link
- PB2 boundary | agent | quick path, skipped design, or a type the design does not cover | no file, or a skip line | nothing owed
- PB3 | agent at the design checkpoint | checkpoint mode and a file was written | show the diagrams | diagrams appear after the summary and before the choices; autopilot reports the path only
- PB5 | every stage, review and `check` | diagram file present or absent | no dependency | identical findings and Done when lists
- PB6 | template, adopt, validate | component page work | no `## Architecture` section | validate removes a retired section from a page it updates

| Frame outcome | Atomic behavior | Requirement | Positive case | Boundary or failure | Verification | Design decision or no impact |
|---|---|---|---|---|---|---|
| PB2 | Design writes the diagram file and one Design link when enabled | REQ-FUNC-ee1d2096 (spec) | enabled + design note: file with one section per covered type | no design note: no file; uncovered type: one skip line | structural test of design step and guide; journal-discovery test | new `steps/diagrams.md` guide plus one design pointer step |
| PB3 | Checkpoint shows the diagrams before the design choices | REQ-UX-b0bd0225 | checkpoint: summary, then diagrams, then choices | autopilot: no display and no stop | structural test | design checkpoint order: summary, diagrams, choices |
| PB1 | Diagrams stay off unless `enabled` is the boolean `true` | REQ-FUNC-f7220cb2 | `init` writes `enabled = false`; missing table works | `enabled = "true"` stays off | init, structural and check-silent tests | `DEFAULT_CONFIG` `[diagrams]` off; old diagram steps removed |
| PB1 | `check` warns on invalid diagrams settings | REQ-FUNC-cd29e673 | valid values: no finding | non-boolean, non-list, unknown name: WARN | check tests | `CONFIG_SHAPE` entry plus `DIAGRAM_TYPES` warning |
| PB1 | `init` documents every validated key, `[diagrams]` included (reused) | REQ-FUNC-87aea7e9 | generated config names both keys | none new | existing generated-config test | no design impact; covered by existing test |
| PB5 | No stage obligation, review or `check` finding depends on diagrams | REQ-FUNC-6343dfb8 | Done when, build, validate, deliver: no diagram duty | same findings with and without a diagram file | structural and check tests | no diagram text in Done when, later stages or `check` |
| PB6 | Component knowledge routes work without an architecture section (revised) | REQ-FUNC-9db20045 | template has no `## Architecture` | legacy page section removed when validate updates the page | structural test | validate migration removes a retired section |
| PB6 | Component architecture diagram obligation removed (retired) | REQ-FUNC-500cfb8b | none | none | retirement; its structural tests removed | retired; its two tests removed |
| Design proposals stay distinct from current knowledge (verification revised) | Design records a proposal and leaves component pages unchanged | REQ-FUNC-3e0263e7 | design text states the proposal | design does not edit component pages | structural test, renamed | design keeps component pages unchanged until validate |

## Design

Components: Reusable workflow payload (step, guide and template text), Core
CLI lifecycle (`DEFAULT_CONFIG` written by `init`), Validation and evidence
CLI (`check_config`), and the release builder's payload inventory.

Requirements coverage:
- REQ-FUNC-ee1d2096 (spec): a new `steps/diagrams.md` guide holds every
  drawing rule from the spec. `3_design.md` gains one step after the audit:
  "If `.agentic/aegis.toml` sets `[diagrams] enabled = true` (a TOML boolean),
  read `.agentic/steps/diagrams.md` and draw what it describes; otherwise draw
  nothing." Constraint: the default-off read cost stays at that one step
  (REQ-FUNC-f7220cb2 rationale).
- REQ-UX-b0bd0225: the design checkpoint step orders the presentation as
  summary, then the diagrams of a file this stage wrote, then the design
  choices. The guide repeats the order, and states that autopilot adds no
  display and no stop.
- REQ-FUNC-f7220cb2: `DEFAULT_CONFIG` gains `[diagrams]` with
  `enabled = false` and `types = ["structure"]`, each commented. Design step 8
  and its Output and Done-when lines are removed. The `## Architecture`
  section leaves `templates/component.md`; adopt step 7 and its Done-when line
  are removed; validate step 4 and its Done-when line are removed.
- REQ-FUNC-cd29e673: `CONFIG_SHAPE["diagrams"] = {"enabled": bool, "types":
  list}` reuses the generic type warnings ("[diagrams] enabled should be
  bool", "[diagrams] types should be list"). A new constant
  `DIAGRAM_TYPES = ("structure", "sequence", "state")` drives one extra
  warning in `check_config`: "[diagrams] types should name only structure,
  sequence, state".
- REQ-FUNC-87aea7e9: no new decision. The existing generated-config test
  covers the new keys once they are in `CONFIG_SHAPE`.
- REQ-FUNC-6343dfb8: no Done-when line, build, validate or deliver text, or
  `check` rule mentions the file. The guide states that nothing later reads
  it. Journal discovery is unchanged: `glob("TASK-*.md")` (`aegis.py:548`,
  :1225, :2314) does not match `diagram_TASK-*.md`.
- REQ-FUNC-9db20045: the validate step 3 legacy-migration sentence also names
  a retired `## Architecture` section, so a page validate updates loses it.
  "Architecture" leaves the reconcile list, `AGENTS.md:144` and
  `4_build.md:52`.
- REQ-FUNC-3e0263e7: design keeps the proposal in the task and states that
  component pages stay unchanged until validate reconciles them with the
  built code. This sentence replaces the old "do not replace the current
  diagram" wording.
- REQ-FUNC-500cfb8b: retired. Its two structural tests are removed.

Interfaces: the configuration keys, the file path, the link line and the file
format are as in `specs/REQ-FUNC-ee1d2096.md`. No CLI command, option or
output changes; `brief` and the root pointer digest stay unchanged (U2:
nothing in the CLI consumes the setting).

State and data: the agent writes the diagram file and commits it with the
journal. The host review fingerprint skips it (`adapter.mjs:94`), and so do
anchor and evolution (`aegis.py:620`).

Failure and compatibility:
- A missing table, a non-boolean value or `false` means off, and `check`
  warns about wrong types.
- An older `aegis.py` ignores the unknown `[diagrams]` table.
- Existing journals keep their old `### Proposed architecture` blocks as
  history.
- Downstream component pages lose `## Architecture` only when validate
  updates them; this repository's four pages are cleaned in this task (A5).

Test seams:
- `test_structure.py`: the guide pointer and guide contents (ee1d2096,
  f7220cb2), presentation order (b0bd0225), no diagram duty in Done-when
  lists or later stages (6343dfb8), and the rewritten component-routing and
  design-depth tests (9db20045, 3e0263e7).
- `test_cli_core.py`: init writes the defaults (f7220cb2); `status` ignores
  `diagram_TASK-*.md` (ee1d2096).
- `test_check.py`: invalid settings warn, valid and missing settings are
  silent (cd29e673), and findings are identical with and without a diagram
  file (6343dfb8).
- The `EXPECTED_FILES` and `EXPECTED_PAYLOAD` inventories gain
  `steps/diagrams.md`.

Alternatives:
- Rules inside `3_design.md`: rejected, because every design read would pay
  about 40 lines while the feature is off.
- `.agentic/diagrams/`: rejected, because the host review fingerprint would
  include it.
- `TASK-<id>.diagrams.md`: rejected, because it matches the journal glob.
- A `diagram_settings()` helper and a `brief` line: rejected, because no CLI
  code consumes them.
- HTML or `mermaid.js`: rejected (RULING-002).

Expected files:
- Payload, mirrored to `.agentic/`: `AGENTS.md`, `CLI.md`, `aegis.py`,
  `steps/3_design.md`, `steps/4_build.md`, `steps/5_validate.md`,
  `steps/adopt.md`, `steps/diagrams.md` (new), `templates/component.md`.
- Tooling: `02_Tools/build_aegis_release.py`.
- Tests: `test_structure.py`, `test_cli_core.py`, `test_check.py`.
- Knowledge: the four pages with `## Architecture`.
- Docs: `CHANGELOG.md`, `05_Software/aegis/README.md`,
  `06_SoftwareDocu/01_Install_and_Setup.md` and its deck, `02`, `03`, `05`,
  `07`, `08`, `09`, and `00_Planning/01`, `02`.

Risks:
- Renumbering adopt and validate steps can leave a stale "steps 1-7"
  reference; build rereads both files.
- A small model may misread the boolean. The pointer names the exact value.
- Mermaid syntax errors are not caught; this is accepted, because diagrams
  are illustration only (RULING-001).

Open decisions: none. No architecture drawing owed: no component structure
changes; the task adds a guide file and a config table.

## Log

- 2026-10-20 frame: full path, because the task adds the optional `[diagrams]`
  config table and a new task file, and retires REQ-FUNC-500cfb8b. Branch
  `ddp/optional-diagrams` was cut from master `52e0772` at the user's choice.
  Scope is presented at the checkpoint, awaiting acceptance.
- 2026-10-20 frame: the user revised scope at the checkpoint. PB4 is
  withdrawn: on-demand redraws and explanations are outside AEGIS. CodeGraph
  is a separate evaluation with no planned merge. A1-A6 are confirmed. The
  revised scope awaits acceptance.
- 2026-10-20 frame: the user accepted the revised scope and switched the task
  to autopilot through implementation, with no commit or push; the user
  reviews before delivery. Frame checklist complete; advanced to specify.
- 2026-10-20 specify: 5 created (REQ-FUNC-ee1d2096 with spec, REQ-UX-b0bd0225,
  REQ-FUNC-f7220cb2, REQ-FUNC-cd29e673, REQ-FUNC-6343dfb8), 2 revised
  (REQ-FUNC-9db20045 drops current architecture from component knowledge;
  REQ-FUNC-3e0263e7 verification wording), 1 reused (REQ-FUNC-87aea7e9),
  1 retired (REQ-FUNC-500cfb8b). Check shows no format errors; stale-paths
  name the future diagram guide. Advanced to design.
- 2026-10-20 specify: DEVIATION specify - retired REQ-FUNC-500cfb8b and narrowed
  REQ-FUNC-9db20045, as authorized by RULING-003; downstream component pages
  keep existing diagrams until validate updates them; open TASK-699c6286 also
  lists REQ-FUNC-500cfb8b and is to be named at delivery.
- 2026-10-20 design: design note recorded in `## Design`, with every
  requirement mapped in Requirement coverage. No architecture drawing owed:
  no component structure change. Check shows no format errors. Design
  checklist complete; advanced to build.
- 2026-10-20 build red: REQ-FUNC-cd29e673, REQ-FUNC-f7220cb2;
  command=`python -m pytest -q 05_Software/aegis/tests/test_check.py -k diagram 05_Software/aegis/tests/test_cli_core.py::test_init_writes_diagrams_disabled_with_structure_type 05_Software/aegis/tests/test_cli_core.py::test_status_never_lists_a_diagram_file_as_a_journal`;
  exit=1; expected missing behavior=no `[diagrams]` entry in `CONFIG_SHAPE` or
  `DEFAULT_CONFIG` (6 failed). The status-discovery test (REQ-FUNC-ee1d2096)
  and the check-independence test (REQ-FUNC-6343dfb8) pass on the first run:
  the existing journal glob and check already satisfy them, so they stay as
  regression guards.
- 2026-10-20 build red: REQ-FUNC-ee1d2096, REQ-UX-b0bd0225, REQ-FUNC-f7220cb2,
  REQ-FUNC-6343dfb8, REQ-FUNC-9db20045;
  command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py -k "diagram or design_scales or component_knowledge_routes or payload_inventory"`;
  exit=1; expected missing behavior=`steps/diagrams.md` does not exist, and
  the payload still carries the Proposed architecture and `## Architecture`
  obligations (6 failed). The design-depth test (REQ-FUNC-3e0263e7) passes
  against existing wording.
- 2026-10-20 build: anchor recorded at 52e0772 over 185 files, after both red
  runs and before the first implementation edit.
- 2026-10-20 build green: REQ-FUNC-ee1d2096, REQ-UX-b0bd0225, REQ-FUNC-f7220cb2,
  REQ-FUNC-cd29e673, REQ-FUNC-6343dfb8, REQ-FUNC-9db20045, REQ-FUNC-3e0263e7,
  REQ-FUNC-87aea7e9;
  command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py 05_Software/aegis/tests/test_check.py 05_Software/aegis/tests/test_cli_core.py 05_Software/aegis/tests/test_release_builder.py`;
  exit=0; 257 passed. These four files are the touched seams; the impacted
  preview expands to 6 files because `aegis.py` changed. Four structure tests
  that require stage reporting now iterate stage files only, because
  `steps/diagrams.md` runs inside design (coverage of every stage file is
  unchanged). The payload is mirrored into `.agentic/`, and both payload
  inventories name the new guide. REQ-FUNC-500cfb8b is retired with its two
  tests removed.
- 2026-10-20 build: docs updated: CHANGELOG, aegis README, install/settings
  guide and deck slide, folders guide and deck, feature and adoption examples
  and decks, FAQ, prompt cheatsheet, CLI reference doc, and planning 01/02.
  Evolution shows 26 changed files, as expected.
- 2026-10-20 build: remaining check warnings come from repository state, not
  from the candidate: `secret-in-diff` names the untracked CodeGraph database
  generated on the evaluation branch; `fingerprints-tracked` names the 30
  sidecars master already tracks; `outside-layout` names the planning docs,
  which this repository's `[layout]` does not list. The stale Handoff is
  refreshed at this transition. Build checklist complete; advanced to
  validate.
- 2026-10-20 validate: I reviewed the diff hunk by hunk against the Frame,
  the nine requirements, the spec and the Design. No unrequested behavior
  found. The integrations, the root pointer digest and the copied adapters
  carry no diagram text.
- 2026-10-20 validate: knowledge reconciled. `## Architecture` is removed from
  `agent_integrations`, `core-cli-lifecycle`, `reusable-workflow-payload` and
  `validation-and-evidence-cli` (A5), and the load-bearing prose from those
  sections is folded into Purpose and boundaries or Invariants. The payload
  page now lists the four diagram behaviors, the new invariant and the guide.
  The validation page lists REQ-FUNC-cd29e673 and a configuration Change-map
  row. `product-verification-suite` (prose-only Architecture) and
  `release-builder-and-delivery-records` (one inventory entry) are not
  materially changed and stay as they are. Project and environment context
  need no change.
- 2026-10-20 validate: requirements re-read. Status, prose, verification,
  affected paths and links are current. The retired REQ-FUNC-500cfb8b drops
  its two deleted test links. Inspection for REQ-FUNC-32fe33a0 (adopt.md was
  edited): `steps/adopt.md` still carries the survey, owner review,
  one-component source-and-test evidence, routing knowledge, untested and
  suspected behavior handling, the report, and the outcome-dependent close-out.
  The docs under `06_SoftwareDocu/` and `00_Planning/` were reviewed directly;
  deck text was checked in the slide XML.
- 2026-10-20 validate: review round 1 started on candidate
  5a14e13975ff1f6738461def0704f5edd936de98b4fbe9aafd5129bb250c58be (host
  fingerprint, 294 files, HEAD 52e0772).
- 2026-10-20 validate: before any verdict, the candidate changed:
  `REQ-FUNC-9db20045.toml` was normalized back to LF after an edit had written
  CRLF. Review round 1 runs on candidate 96ee1367cc92be4d6811049c9ca4f1e7e4d2fbdde68c860a8d0831bae7dae1e7.
- 2026-10-20 validate: review round 1 on 96ee1367. Specification compliance:
  changes_required. Major: `06_SoftwareDocu/Project_Context.md:21` still lists
  architecture among the component-page contents. Minor: no Inspection
  records for REQ-FUNC-b8f0efc5 or REQ-UX-62a24243; stale Stage report; the
  check-side discovery test is not linked to REQ-FUNC-ee1d2096; the guide
  example breaks its own `==>` rule; the diagrams-between-report-and-choices
  order is not reconciled with REQ-UX-84868466 in the record; `types = []` and
  non-list `types` are unspecified for the agent; the REQ-FUNC-9db20045
  verification omits the retired-section migration; S1 does not mention the
  unknown-name warning. Implementation quality: approved. Minor: the same
  doc and example findings; the validate migration wording never says
  remove; the check-independence test runs without git; the design
  fail-safe sentence is unguarded; the same `types` cases; CHANGELOG Added
  entry is longer than two lines. Routed to build to fix only these findings;
  both verdicts are cleared.
- 2026-10-20 build red: REQ-FUNC-ee1d2096, REQ-FUNC-9db20045 (review round 1
  fixes); command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py::test_design_draws_diagrams_only_through_the_enabled_guide 05_Software/aegis/tests/test_structure.py::test_component_knowledge_routes_implementation_work 05_Software/aegis/tests/test_check.py::test_check_findings_ignore_a_diagram_file_in_the_git_diff`;
  exit=1; expected missing behavior=the guide does not state the
  non-list/empty `types` handling or show `==>`/`-.->`/`:::removed` in its
  example, and validate does not say to remove a retired section (2 failed).
  The git-diff variant of the check-independence test passes on the first run
  because the behavior already holds. The original anchor stays the baseline.
- 2026-10-20 build green (review round 1 fixes): REQ-FUNC-ee1d2096,
  REQ-FUNC-6343dfb8, REQ-FUNC-9db20045, REQ-FUNC-f7220cb2;
  command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py 05_Software/aegis/tests/test_check.py 05_Software/aegis/tests/test_cli_core.py 05_Software/aegis/tests/test_release_builder.py`;
  exit=0; 258 passed.
  - Guide and spec now state that a non-list `types` counts as missing and
    that an empty list writes no file or link. Their examples show `==>`,
    `-.->` and `:::removed`.
  - Validate step 3 says to remove a retired `## Architecture` section and to
    keep any still-true constraint in Purpose and boundaries or Invariants.
  - The design fail-safe sentence is now guarded by a test.
  - The git-diff check-independence test is linked to REQ-FUNC-6343dfb8 and
    REQ-FUNC-ee1d2096, and the REQ-FUNC-9db20045 verification names the
    retired-section removal.
  - `Project_Context.md` no longer lists architecture, and the CHANGELOG
    Added entry is two lines.
  - The mirror is synced.
- 2026-10-20 build: records for the round 1 findings that need no candidate
  edit.
  - Inspection REQ-FUNC-b8f0efc5: `templates/component.md` carries Routing,
    Purpose and boundaries, Public interface, Invariants, Change map, Key
    behaviors and Files. The AGENTS.md artifact table names component
    knowledge and the optional diagram file. The task template is unchanged
    and keeps its parent, ruling, handoff, stage-report and review scaffolds.
  - Inspection REQ-UX-62a24243: the index, installation, folder, feature,
    quick-fix, adoption, team, FAQ, prompt and CLI-reference guides were read
    against the payload. 01, 02, 03, 05, 07, 08, 09 and Project_Context now
    describe the `[diagrams]` setting and the removed architecture sections;
    00, 04 and 06 carry no diagram or architecture text.
  - Decks: slide XML search found architecture text only in decks 02, 03 and
    05 (now edited) and none in 07 or 08. The settings slide in deck 01 gained
    a `[diagrams]` row.
  - The diagrams sit between the design report and the design choices: this
    is the user-accepted presentation (RULING-001) and part of the design
    report, so the REQ-UX-84868466 order of report before choices holds.
  - S1 is refined by REQ-FUNC-cd29e673: `check` also warns on an unknown
    diagram type name.
- 2026-10-20 build: evolution now covers 28 changed files. Check shows no
  candidate warning beyond the repository-state warnings explained above.
  Advanced to validate. Review round 2 runs on candidate 02eec0660b648d5b13b78f3edf72ffb4213fc5ff5bd70dcf2ea235204dfc45fc (host
  fingerprint, 294 files).
- 2026-10-20 validate: review round 2 on 02eec066. Both verdicts are
  changes_required.
  - Major: `02_Tools/README.md`, `00_Planning/02`, `03` and `05` still state a
    17-file payload with seven step files. The guide makes 18 files and eight
    step files.
  - Minor: the `00_Planning/02` configuration table lacks `[diagrams]`.
  - Minor: the Stage report is stale.
  - Minor: the CHANGELOG Removed entry is three lines.
  - Minor: the git-diff test lacks `@needs_git`.
  - Nits: `CLI.md` and the `DEFAULT_CONFIG` comment omit the non-list and
    empty `types` cases. The guide's skip line does not name the type, and it
    says "three headers" against four strings. A list holding only unknown
    names is unspecified. Routing does not separate the design diagrams from
    the `diagram` coverage command.
  Routed to build to fix only these findings; both verdicts are cleared. Round
  3 is the last allowed round.
- 2026-10-20 build red: REQ-FUNC-ee1d2096 (review round 2 fixes);
  command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py::test_design_draws_diagrams_only_through_the_enabled_guide`;
  exit=1; expected missing behavior=the guide does not say that a list with
  no known name counts as an empty list.
- 2026-10-20 build green (review round 2 fixes): REQ-FUNC-ee1d2096,
  REQ-FUNC-cd29e673, REQ-FUNC-6343dfb8;
  command=`python -m pytest -q 05_Software/aegis/tests/test_structure.py 05_Software/aegis/tests/test_check.py 05_Software/aegis/tests/test_cli_core.py 05_Software/aegis/tests/test_release_builder.py`;
  exit=0; 258 passed. `py_compile` and `aegis.py --help` succeed.
  - Docs now state an 18-file payload with eight step files: `00_Planning/02`,
    `03` and `05`, and `02_Tools/README.md`.
  - `00_Planning/02` gains a `[diagrams]` configuration row.
  - The CHANGELOG Removed entry is two lines.
  - The git-diff test is marked `@needs_git`.
  - `CLI.md`, the CLI reference doc and the `DEFAULT_CONFIG` comment state
    the non-list and no-known-name `types` cases.
  - The guide and spec keep the type heading with the skip line and say
    "headers in the table".
  - Knowledge Routing separates the design diagrams (payload page) from the
    coverage `diagram` command (validation page).
  - A repository-wide sweep and a deck slide-XML sweep find no other payload
    count. The mirror is synced.
- 2026-10-20 build: evolution and check refreshed; no candidate warning beyond
  the repository-state warnings explained earlier. Advanced to validate.
  Review round 3 (final) runs on candidate 23933f1117771672f0301b5febb36e18dfc32e42ee7bc404a2489da73dd10da5 (host fingerprint,
  294 files).
- 2026-10-20 validate: before any round 3 verdict, `check` reported
  `uncovered-source` for `02_Tools/README.md`. REQ-FUNC-ee1d2096 now lists
  that file in its affected paths, and the warning is gone. Review round 3
  runs on candidate 6566cdb858af38239e0c53c64496df3871c07f089a896204f93f98f9a163b127 (294 files).
- 2026-10-20 validate: review round 3 on 6566cdb8: specification compliance
  approved; implementation quality approved. Non-blocking minors are left
  as they are:
  - the line length and wording of the CLI reference config paragraph;
  - REQ-FUNC-ee1d2096 verification is broader than its test on applicability
    text;
  - the Design Expected files predate the round fixes (the Log records them);
  - the CHANGELOG does not mention the new payload file;
  - the guide example's Sequence section and ragged wraps.
- 2026-10-20 validate: correction to the round 2 record. The sweep did miss
  one payload count: root `README.md:182` says "15-file managed payload".
  That statement was already wrong at HEAD (17 files) and is now 18. It is
  left unchanged, because any candidate edit invalidates the final review
  round and the counter is exhausted.
- 2026-10-20 validate: DEVIATION validate - root `README.md:182` keeps a stale
  payload count (pre-existing). Fixing it needs a user ruling to reopen review;
  the candidate is otherwise approved.
- 2026-10-20 validate final proof:
  command=`python .agentic/aegis.py check --task TASK-fcd51702 --strict --run`;
  exit=0. Ran `test` (`python -m pytest -q 05_Software/aegis/tests`, ok in
  208.6s) and `lint` (`python -m ruff check 05_Software/aegis`, ok).
  errors=0, warnings=21, notes=4.
  - Remaining warnings, accepted: `secret-in-diff` on the untracked CodeGraph
    database from the evaluation branch; `fingerprints-tracked` on 30 sidecars
    master already tracks; `outside-layout` on four `00_Planning` docs, which
    this repository's `[layout]` does not list; pre-existing review-state,
    scope-drift and unticked-deliver findings on other open tasks.
  - The candidate fingerprint is unchanged at 6566cdb8, the reviewed
    candidate, and evolution was refreshed after the last candidate edit.
  - Validate checklist complete; advanced to deliver.
- 2026-10-20 deliver: the user reviewed the candidate and approved delivery:
  commit and push on `ddp/optional-diagrams`, with no Co-Authored-By trailer.
  - After review and before this approval, the user asked for two repository
    operations, which are not part of this task: assigning version 0.14.0
    (changelog, `VERSION`, plugin manifests, docs, deck labels) and building
    the 0.14.0 delivery while removing 0.13.0 (`07_Delivery/`, PDF version
    labels). Their verification: the builder's full product suite (463
    passed, 2 skipped) and ruff are clean, and the delivery record is
    `07_Delivery/aegis-0.14.0/BUILD.md`.
  - The commit carries them with the task changes. It excludes the
    anchor/evolution sidecars and the generated CodeGraph database.
  - Open TASK-699c6286 also lists the retired REQ-FUNC-500cfb8b; its owner
    decides how to treat it.

## Rulings

- RULING-001 | date=2026-10-20 | decision=One optional [diagrams] setting controls every model-drawn diagram; it is off by default and off when missing; diagrams are drawn at design for the human, shown at the design checkpoint outside autopilot, and verified by no stage, check rule, Done-when item or review | reason=the diagram only clarifies the proposed implementation to the human operator | source=user | supersedes=none
- RULING-002 | date=2026-10-20 | decision=Diagrams live in .agentic/tasks/diagram_<task id>.md linked from the task Design; no mermaid.js or renderer is bundled | reason=keep the journal lean and AEGIS simple and self-contained | source=user | supersedes=none
- RULING-003 | date=2026-10-20 | decision=The design Proposed architecture diagram and the component knowledge-page Architecture diagram are no longer required or drawn | reason=only the diagrams setting governs diagram generation | source=user | supersedes=none
- RULING-004 | date=2026-10-20 | decision=Work on branch ddp/optional-diagrams cut from master 52e0772 rather than from ddp/codegraph-plugin-plan | reason=user choice; keeps this change apart from in-progress CodeGraph work | source=user | supersedes=none
- RULING-005 | date=2026-10-20 | decision=AEGIS specifies only the diagrams design draws by default; redrawing, drawing new diagrams or explaining them on the operator's request is left to the operator and the model and appears nowhere in the payload | reason=on-demand diagram work is a conversation, not a workflow obligation | source=user | supersedes=none
- RULING-006 | date=2026-10-20 | decision=This task owes no compatibility or merge with ddp/codegraph-plugin-plan | reason=CodeGraph is an evaluation that stays on its own branch and is not planned for the official AEGIS distribution | source=user | supersedes=none
- RULING-007 | date=2026-10-20 | decision=Run the remaining stages in autopilot without committing or pushing; stop at deliver before any publication so the user can review the uncommitted candidate | reason=the user reviews the implementation before anything is recorded in Git | source=user | supersedes=none

## Handoff

current: deliver
status: waiting
next: User reviews the uncommitted candidate and chooses the delivery outcome (commit/PR, changes, return to validate, or pause); no commit or push before that choice (RULING-007)
must_read: .agentic/tasks/TASK-fcd51702.md, .agentic/steps/6_deliver.md
blockers: none

## Stage report

stage: validate
result: paused
current: deliver
changed: optional [diagrams] design diagrams (new steps/diagrams.md guide, config, check warning), removal of the old architecture-diagram obligations, tests, docs, decks and knowledge; 46 tracked files changed plus 11 new
evidence: check --task TASK-fcd51702 --strict --run exit 0 (full pytest suite ok 208.6s, ruff ok, errors 0, warnings 21 explained); review round 3 both approved on 6566cdb8
issues: DEVIATION root README.md:182 stale payload count (pre-existing); open TASK-699c6286 also lists retired REQ-FUNC-500cfb8b; repository-state warnings explained in Log
next: user reviews the uncommitted candidate and chooses the delivery outcome
needs_user: yes
spec_compliance: approved
implementation_quality: approved
review_round: 3

## Delivery report (2026-10-20)

- stage: deliver; type: feature; path: full; branch: ddp/optional-diagrams
- requirements:
  - REQ-FUNC-ee1d2096 - Draw proposed-implementation diagrams at design when enabled
  - REQ-UX-b0bd0225 - Show generated diagrams at the design checkpoint
  - REQ-FUNC-f7220cb2 - Keep diagram generation disabled unless explicitly enabled
  - REQ-FUNC-cd29e673 - Warn about invalid diagrams settings
  - REQ-FUNC-6343dfb8 - Keep diagrams outside every stage obligation
  - REQ-FUNC-9db20045 - Route implementation work through component knowledge
  - REQ-FUNC-3e0263e7 - Record a proportionate traceable design
  - REQ-FUNC-500cfb8b - Keep a current component architecture diagram in its knowledge page
  - REQ-FUNC-87aea7e9 - Initialize a copied AEGIS payload
- deviations: 2 recorded
  - specify - retired REQ-FUNC-500cfb8b and narrowed REQ-FUNC-9db20045, as authorized by RULING-003; downstream component pages keep existing diagrams until validate updates them; open TASK-699c6286 also lists REQ-FUNC-500cfb8b and is to be named at delivery.
  - validate - root `README.md:182` keeps a stale payload count (pre-existing). Fixing it needs a user ruling to reopen review; the candidate is otherwise approved.
- explicit review: enabled; spec_compliance=approved; implementation_quality=approved; review_round=3
- diff vs task base 52e0772: 99 file(s) changed, 3608 line(s) added; 2 file(s) not content-scanned
- checks: errors=0 warnings=41 notes=4
- checklist: 3/6 done; open: journal and report included in the delivery commit; agreed outcome delivered, normally a PR; close-out committed after the outcome succeeded, or carried by the delivery commit where nothing could fail after it
