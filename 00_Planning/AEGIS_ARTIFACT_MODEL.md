<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Artifact Model

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-13
**Requirements source:** `AEGIS_PRODUCT_REQUIREMENTS.md`  
**Functional source:** `AEGIS_FUNCTIONAL_SPECIFICATION.md`  
**Release priorities:** `AEGIS_RELEASE_SCOPE.md`

## 1. Purpose

This document defines the durable repository artifacts used by AEGIS. It
establishes their ownership, layout, identity, relationships, lifecycle, and
resume behavior.

The model deliberately keeps a run together. A run has one summary file and
one file for each workflow stage. Stage evidence, findings, decisions, and
handoff state are sections of the relevant stage file, not separate artifact
types. Approvals and exceptions are represented as decisions.

The files under `00_Planning/templates/` are planning and reference material.
They are not installed into a target repository, listed in the AEGIS payload
manifest, or copied into a release archive. The Stage, Adoption, and exceptional
Abandonment references are snapshots emitted by the current codec from
synthetic default state. The remaining files are schematic planning examples
unless they explicitly say that they are renderer-generated. Command names and
implementation modules are outside this document.

## 2. Artifact principles

- **AM-PRINCIPLE-001:** The repository and its branches shall contain every
  durable fact needed to resume, review, validate, or deliver AEGIS work.
- **AM-PRINCIPLE-002:** Product-owned payload and project-owned data shall have
  an explicit, inspectable ownership boundary.
- **AM-PRINCIPLE-003:** A run shall be understandable by reading `run.md` and
  its eight ordered stage files, without reconstructing a web of small records.
- **AM-PRINCIPLE-004:** A completed or paused stage file shall be the durable
  snapshot from which another human or AI session continues.
- **AM-PRINCIPLE-005:** Evidence, findings, approvals, skips, waivers, scope
  changes, and revisions shall remain distinct concepts even though they are
  recorded inside their owning run or stage file.
- **AM-PRINCIPLE-006:** Human-facing artifacts shall remain readable and
  meaningfully reviewable as text.
- **AM-PRINCIPLE-007:** Machine-significant Markdown shall use versioned TOML
  front matter with stable field types.
- **AM-PRINCIPLE-008:** Missing or inconsistent information shall produce a
  finding and shall never be filled by invention.
- **AM-PRINCIPLE-009:** No artifact shall claim that skipped, waived, failed,
  incomplete, or abandoned work passed.
- **AM-PRINCIPLE-010:** Large raw output may be attached, but an attachment
  shall never replace the concise conclusion needed to resume the stage.
- **AM-PRINCIPLE-011:** Requirements, Specifications, Components, and their
  traceability shall contain only current project knowledge. Run and Stage
  artifacts remain the separate evidence and audit record of workflow actions.

## 3. Ownership boundary

The target repository contains one `.agentic/` root with two ownership
domains:

| Path | Owner | WAEGIS may replace it? | Purpose |
|---|---|---:|---|
| `.agentic/aegis/` | AEGIS product | Yes, as a complete versioned payload | CLI, workflows, adapters, launchers, manifest, and product documentation. |
| Every other path below `.agentic/` | Target repository | No | Configuration, project rules, requirements, components, tests, adoptions, and run history. |

- **AM-OWNER-001:** `.agentic/aegis/manifest.toml` and the payload files it
  lists shall be product-owned.
- **AM-OWNER-002:** `.agentic/config.toml`, `.agentic/rules.md`, and the
  requirements, components, tests, adoptions, and runs roots shall be project-
  owned, including when WAEGIS creates them during installation.
- **AM-OWNER-003:** WAEGIS shall not replace, delete, or silently rewrite
  project-owned artifacts during installation or payload replacement.
- **AM-OWNER-004:** Project-specific guidance shall live in
  `.agentic/rules.md`, never in the replaceable payload.
- **AM-OWNER-005:** The workflow shall instruct agents not to edit payload-
  owned files. Under the shipped defaults, a detected payload edit shall create
  a finding rather than refuse the edit.
- **AM-OWNER-006:** Removing `.agentic/aegis/` shall leave the application and
  all project-owned artifacts intact.
- **AM-OWNER-007:** WAEGIS itself shall not be installed inside the payload.

## 4. Default repository layout

```text
.agentic/
|-- aegis/                              # product-owned, replaceable payload
|   |-- manifest.toml
|   |-- README.md
|   |-- adapters/
|   |-- bin/
|   |-- cli/
|   `-- workflows/
|-- .runtime/                           # transient locks and recovery; not versioned
|-- config.toml                         # generated integration map
|-- rules.md                            # optional project-specific guidance
|-- requirements/                       # project documentation
|   |-- REQ-<32hex>.toml
|   `-- SPEC-<requirement-32hex>.md      # optional
|-- components/                         # project documentation
|   `-- COMP-<32hex>.md
|-- tests/                              # default project test root
|-- adoptions/                          # adoption workflow state
|   `-- ADOPT-<32hex>.md
`-- runs/                               # AEGIS workflow metadata
    |-- context.toml                    # local selected-Run pointer; not versioned
    |-- RUN-<32hex>/
    |   |-- run.md
    |   |-- 01-intake.md
    |   |-- 02-alignment.md
    |   |-- 03-requirement.md
    |   |-- 04-design.md
    |   |-- 05-check.md
    |   |-- 06-implementation.md
    |   |-- 07-validation.md
    |   |-- 08-delivery.md
    |   `-- ATTACH-<32hex>.<extension>   # optional large or raw material
    `-- ABANDON-RUN-<32hex>.md           # exceptional recovery record only
```

- **AM-LAYOUT-001:** Every run shall have its own identifier-named directory.
  Files belonging to different runs shall never share one run directory.
- **AM-LAYOUT-002:** A normal run shall contain exactly one `run.md` and the
  eight canonical stage filenames.
- **AM-LAYOUT-003:** A short path shall keep all eight stage files. A stage not
  included by the selected profile shall be recorded as `omitted`; it shall not
  disappear from the layout.
- **AM-LAYOUT-004:** Requirements, specifications, components, and tests shall
  be project data, not run metadata. Runs shall reference them rather than own
  them.
- **AM-LAYOUT-005:** `.agentic/tests/` shall be the shipped default test root.
- **AM-LAYOUT-006:** When WAEGIS detects that a repository already has one or
  more test roots, it shall record those existing roots in `config.toml`
  instead of requiring tests to move into `.agentic/tests/`.
- **AM-LAYOUT-007:** Test roots shall be configurable because languages and
  frameworks use different layouts. Multiple test roots shall be allowed.
- **AM-LAYOUT-008:** A test root selected in `config.toml` is authoritative for
  discovery; `.agentic/tests/` is not additionally searched unless it is also
  selected.
- **AM-LAYOUT-009:** `<configured-runs-root>/context.toml`, defaulting to
  `.agentic/runs/context.toml`, shall be the optional local working-context
  pointer. It shall contain only the selected Run identity, be excluded from
  version control, and never be treated as audit or resume state.
- **AM-LAYOUT-010:** No separate directories shall exist for snapshots,
  evidence, findings, decisions, revisions, or delivery reports.
- **AM-LAYOUT-011:** Attachments shall be optional and stored immediately below
  their owning run directory.
- **AM-LAYOUT-012:** Adoption state may span multiple sessions but shall remain
  separate from a normal eight-stage run.
- **AM-LAYOUT-013:** `.agentic/.runtime/` may hold only transient lock and
  interrupted-publication recovery material. It shall not be authoritative
  project data, Run metadata, audit evidence, or agent context.

## 5. Project configuration

`.agentic/config.toml` is a generated integration map, not a policy form that a
developer must complete before AEGIS works. It describes where project
artifacts live, suggested project validation commands for the agent or
developer, and any optional advisory policy the project deliberately adds.

```toml
schema = 1
artifact_type = "project_config"

[paths]
requirements = ".agentic/requirements"
components = ".agentic/components"
tests = [".agentic/tests"]
adoptions = ".agentic/adoptions"
runs = ".agentic/runs"

[validation.tests.project]
command = ["python", "-m", "unittest", "discover", "-s", ".agentic/tests"]
working_directory = "."

# WAEGIS adds detected project lint commands when present.
# [validation.lints.project]
# command = ["python", "-m", "ruff", "check", "."]
# working_directory = "."

# Optional repository-specific advisory audit.
# [validation.audits.codestyle]
# command = ["python", "02_Tools/audits/audit_codestyle.py", "--changed-only"]
# working_directory = "."

[policy]
risk_attention_threshold = "medium"
protected_scope_patterns = []
```

- **AM-CONFIG-001:** WAEGIS shall create a complete, usable `config.toml`
  during installation.
- **AM-CONFIG-002:** The developer shall not need to edit `config.toml` before
  the first run.
- **AM-CONFIG-003:** WAEGIS shall prefer confidently detected existing test
  roots over the default `.agentic/tests/` root.
- **AM-CONFIG-004:** If existing test roots cannot be detected confidently,
  WAEGIS shall use `.agentic/tests/` and report the uncertainty without
  blocking installation.
- **AM-CONFIG-005:** All configured paths shall be repository-relative, use
  `/` separators, and remain inside the repository.
- **AM-CONFIG-006:** Configuration may relocate project artifacts or add
  strictness explicitly requested by a team; it shall not be needed to turn on
  the product's normal value.
- **AM-CONFIG-007:** `.agentic/rules.md` shall be optional. Its absence shall
  mean that only the shipped rules apply.
- **AM-CONFIG-008:** Source roots shall not be required in the initial
  configuration schema. Intake shall establish source scope from Component
  file membership, Requirement impacted files, Git-tracked files, and bounded
  repository inspection.
- **AM-CONFIG-009:** A validation command shall belong to one of the named
  collections `tests`, `lints`, or `audits`.
- **AM-CONFIG-010:** Command names shall be unique within their collection and
  shall provide stable machine-interface names such as `project`, `codestyle`,
  or `logging_coverage`.
- **AM-CONFIG-011:** A command shall be stored as an executable and argument
  array, not as a shell command string, so the agent or developer can invoke it
  consistently on Windows and Linux.
- **AM-CONFIG-012:** Each command shall declare a repository-relative working
  directory. Timeout, cancellation, and output retention belong to the host
  that runs the command.
- **AM-CONFIG-013:** AEGIS shall never launch a configured project command.
  The agent or developer runs a selected command with normal host tooling and
  records its observed outcome through the evidence interface.
- **AM-CONFIG-014:** WAEGIS shall record test and lint commands that it can
  detect confidently from the repository. Where no command is detected, AEGIS
  shall use the shipped adapter default appropriate to the selected language
  and test framework and shall report what it selected.
- **AM-CONFIG-015:** Repository-specific audits shall be optional. Adding a
  named audit to `config.toml` shall make it available as Validation guidance.
- **AM-CONFIG-016:** Audit commands may implement changed-file scoping through
  their own arguments, such as `--changed-only`, so advisory work remains
  proportional to the Run.
- **AM-CONFIG-017:** Test, lint, and audit outcomes recorded by the agent or
  developer shall produce evidence and any applicable factual findings. None
  shall become a Delivery blocker under the shipped defaults.
- **AM-CONFIG-018:** The presence of a validation command shall make it active;
  it is active guidance for the agent or developer, and a separate `enabled`
  switch shall not be required.
- **AM-CONFIG-020:** Open questions and risk shall be recorded by Alignment,
  but configuration shall not force a blocking `pause` outcome. Proceeding
  shall record the accepted assumptions or recommended responses and the actor.
- **AM-CONFIG-021:** `risk_attention_threshold` shall control the prominence of
  advisory risk findings and shall not refuse work or prevent stage closure.
- **AM-CONFIG-022:** `protected_scope_patterns` shall be optional and empty by
  default. Under shipped policy, matching a protected path shall create a
  finding rather than refuse an edit.
- **AM-CONFIG-023:** Any stage-scoped write prevention based on protected paths
  shall remain separate opt-in strict policy and shall ship disabled.

## 6. Identities and filenames

- **AM-ID-001:** Independently created artifacts shall use a type prefix and a
  locally generated UUID version 4. The UUID shall use the operating system's
  secure randomness source and shall be serialized as 32 lowercase hexadecimal
  characters without hyphens.
- **AM-ID-002:** Identifier generation shall not use a shared counter.
- **AM-ID-003:** Creation shall check the destination namespace and shall
  regenerate an identifier rather than overwrite on collision.
- **AM-ID-004:** Duplicate identifiers discovered after a merge shall produce a
  finding; neither artifact shall silently win.

| Artifact | Identity or canonical name |
|---|---|
| Run | `RUN-<32hex>` directory |
| Requirement | `REQ-<32hex>.toml` |
| Specification | `SPEC-<requirement-32hex>.md` |
| Component | `COMP-<32hex>.md` |
| Adoption journal | `ADOPT-<32hex>.md` |
| Attachment | `ATTACH-<32hex>.<extension>` |
| Exceptional abandonment | `ABANDON-RUN-<run-32hex>.md` |
| Run summary | `run.md` inside its Run directory |
| Stage | one of the eight numbered canonical filenames |

- **AM-ID-005:** A Specification shall inherit its Requirement identity and
  shall not introduce another independent identifier.
- **AM-ID-006:** A Stage shall inherit its Run identity and stage name.
- **AM-ID-007:** An Attachment identity shall be unique within its Run.
- **AM-ID-008:** Internal identifiers and canonical paths shall agree.
- **AM-ID-009:** References to project source and test files shall use
  repository-relative paths; references to AEGIS artifacts shall use their
  identifiers or canonical repository-relative paths.

## 7. Common Markdown envelope

Run, Stage, Component, Specification, Adoption, and exceptional Abandonment
artifacts shall use TOML front matter followed by human-readable Markdown:

```markdown
+++
schema = 1
artifact_type = "stage"
run_id = "RUN-0123456789abcdef0123456789abcdef"
stage = "intake"
sequence = 1
status = "active"
state_json = "{\"allowed_sections\":[],\"events\":[],\"sections\":{}}"
+++

# 1 - Intake
```

- **AM-SCHEMA-001:** `schema` shall be a positive integer scoped to the
  `artifact_type`.
- **AM-SCHEMA-002:** `artifact_type` shall be stable lowercase snake case.
- **AM-SCHEMA-003:** Machine state shall be read from front matter or from the
  codec-defined Run, Component, and Specification body sections. It shall not
  be inferred from unrecognized Markdown headings or prose.
- **AM-SCHEMA-004:** A parser shall return a structured error for malformed or
  unsupported front matter and shall preserve the original file.
- **AM-SCHEMA-005:** A published artifact shall contain no angle-bracket
  placeholder.
- **AM-SCHEMA-006:** Timestamps shall be RFC 3339 UTC values ending in `Z`.
- **AM-SCHEMA-007:** Enum values shall use lowercase snake case except the exact
  priority vocabulary `Must`, `Should`, and `Could`.

### 7.1 Current renderer representation

The current codec uses two Markdown representations:

1. Run, Component, and Specification artifacts store selected tabular metadata
   in front matter and reconstruct their remaining state from codec-defined body
   sections.
2. Stage, Adoption, and exceptional Abandonment artifacts store their complete
   state as compact, key-sorted JSON in the TOML string field `state_json`.
   Their Markdown body is a generated projection and is not parsed back into
   state.

For a Stage, the generated projection begins with
`# <un-padded sequence> - <title-cased stage>`. It then renders the Stage
instruction, each allowed section with a title-cased heading and its current
text, and the `evidence`, `findings`, `decisions`, `escapes`, `attachments`, and
`events` collections as fenced, indented JSON arrays. The last heading is
`## Event history`; generated headings do not preserve punctuation or the
capitalization used by earlier hand-written planning examples.

Adoption renders as `# Adoption <ADOPT-ID>` followed by one fenced, indented
JSON object. Exceptional Abandonment renders as `# Exceptional abandonment`
followed by the same JSON-object projection. The compact `state_json` value,
not either body projection, is authoritative for these artifact types.

Parsing and rendering shall preserve the metadata and structured state. Byte-
for-byte identity after a parse/render cycle is not required because parsing
the key-sorted `state_json` can normalize dictionary order in the indented JSON
projection. Redesigning this representation for more reviewable diffs is
deferred; planning references shall describe and exercise the current codec
rather than imply that redesign has occurred.

## 8. Run summary

`run.md` is the authoritative summary and current-state pointer for one run. It
shall contain:

1. the Run identity, status, profile, work type, timestamps, and branch at
   opening;
2. the ticket text preserved verbatim;
3. the restated intent and current scope;
4. the interaction mode, defaulting to `checkpoint`, and the developer's
   execution instruction when it explicitly selects `continuous` interaction;
5. the scope-change log;
6. a compact outcome and last-updated time for every stage;
7. change-attribution information;
8. the current stage and next action; and
9. the terminal outcome: delivered or abandoned.

- **AM-RUN-001:** Run status shall be `active`, `delivered`, or `abandoned`.
- **AM-RUN-002:** The original ticket text shall not be overwritten when scope
  changes.
- **AM-RUN-003:** A scope change shall be appended to the scope-change log with
  timestamp, previous interpretation, new interpretation, actor, reason, and
  affected artifacts.
- **AM-RUN-004:** Scope changes shall not require separate Revision files.
- **AM-RUN-005:** Run interaction mode shall be `checkpoint` or `continuous` and
  shall default to `checkpoint`. `continuous` shall be recorded only when the
  developer explicitly asks the AI agent to complete the workflow without
  intermediate prompts; the Run shall preserve that execution instruction as
  ordinary context.
- **AM-RUN-006:** A decision recorded by an AI agent under explicit continuous
  delegation shall identify the agent as actor and shall have the same workflow
  effect as a decision entered directly by the developer.
- **AM-RUN-007:** `run.md` shall summarize stage state but shall not duplicate
  the full stage contents.
- **AM-RUN-008:** Multiple recorded Runs may exist, but one working copy shall
  select at most one Run and one operation shall act on exactly that Run.
- **AM-RUN-009:** The selected Run's `current_stage` shall be the only working
  Stage pointer. If no valid Run is selected, AEGIS shall select the sole active
  candidate or list multiple candidates rather than guess.
- **AM-RUN-010:** Absence of an execution instruction, an ambiguous autonomy
  request, host permissions, or prior agent behavior shall resolve to
  `checkpoint`, never `continuous`.
- **AM-RUN-011:** Parking a checkpoint shall leave the Run `active` and its
  durable Stage state resumable. It shall not add another Run status or depend
  on chat history to recover the next action.

## 9. Stage files as durable snapshots

Every Stage file has the same machine envelope, a complete `state_json` object,
an embedded stage-specific instruction, and generated stage-specific sections.
It shall contain enough information for a new session to continue without chat
history.

### 9.1 Common stage state

- **AM-STAGE-001:** Stage status shall be `pending`, `active`, `completed`,
  `skipped`, or `omitted`.
- **AM-STAGE-002:** `omitted` means the selected run profile never included the
  stage. `skipped` means included work was intentionally bypassed through an
  escape hatch.
- **AM-STAGE-003:** A skip shall include the actor and a mandatory reason, shall
  not be recorded as passed, and shall not be available after that stage's work
  has already been applied.
- **AM-STAGE-004:** A waiver shall identify the waived finding or expectation,
  the actor, and a mandatory reason.
- **AM-STAGE-005:** A Stage file shall contain its self-contained instruction and
  record its inputs, decisions, work, evidence, findings, outputs, handoff, next
  action, and append-only event history. Ordinary factual context belongs in
  the applicable Stage section; approvals and exceptions are decisions.
- **AM-STAGE-006:** Sections may state `None`; absent facts shall not be implied
  by deleting mandatory sections.
- **AM-STAGE-007:** A pause or stage close shall atomically publish the Stage
  file only after its new attachments and project artifacts exist.
- **AM-STAGE-008:** `run.md` shall be atomically updated after the Stage file so
  interruption cannot make the summary claim unpublished stage state.
- **AM-STAGE-009:** The latest valid Stage file is the saved resume snapshot.
  No separate Snapshot artifact shall exist.
- **AM-STAGE-010:** Material corrections shall be appended to the event history
  with what changed, why, when, and by which actor. The Stage file shall contain
  its own correction history.
- **AM-STAGE-011:** Earlier unfavorable evidence and findings shall remain in
  the stage history even when later evidence supersedes them.

### 9.2 Stage-specific responsibility

| File | Durable responsibility |
|---|---|
| `01-intake.md` | Ticket interpretation, repository/config/component discovery, initial scope, baseline state, uncertainties. |
| `02-alignment.md` | Agreed scope, exclusions, open questions, developer corrections, profile choice, approval. |
| `03-requirement.md` | Requirements/specifications created, updated, or deleted; traceability decisions, gaps, approval. |
| `04-design.md` | Solution design, requirement coverage, alternatives, risks, affected components and files, approval or omission. |
| `05-check.md` | Tests created or selected, exact red evidence, fingerprints, non-applicability decision, findings. |
| `06-implementation.md` | Implementation changes, changed-file attribution, test-integrity comparison, implementation evidence, findings. |
| `07-validation.md` | Impacted-test selection, execution evidence, wider regression decision, manual verification, findings and waivers. |
| `08-delivery.md` | Concise run outcome, scope/result comparison, evidence summary, test changes, unresolved findings, escape decisions, final approval. |

- **AM-STAGE-012:** Intake shall read `config.toml`, relevant Component
  artifacts, and their linked Requirements and tests before establishing scope.
- **AM-STAGE-013:** Intake shall report missing or stale Component information
  as a finding without blocking work.
- **AM-STAGE-014:** Requirement shall create or update project Requirement and
  optional Specification artifacts; the stage file shall record their paths
  and decisions, not copy their full content.
- **AM-STAGE-015:** Check shall preserve an actual failing result when red-
  before-green applies.
- **AM-STAGE-016:** Completing an approved `08-delivery.md` shall publish that
  Stage as `completed`, `run.md` as `delivered`, and the local context as
  unselected in one atomic operation. No separate Run-delivery operation is
  required. Delivery does not mean commit, push, tag, merge, or pull request.
- **AM-STAGE-017:** In checkpoint interaction, every included Stage handoff
  shall expose a concise projection of outcome, changed artifacts, evidence,
  findings, open questions, and proposed next Stage, plus continue, review,
  revise or reimplement, and park choices.
- **AM-STAGE-018:** A non-Delivery Stage may be durably completed before its
  checkpoint is presented, but the agent shall not start the next Stage until
  the developer chooses continue. Review and park shall not mutate workflow
  state; revision shall use the existing Stage update or revisit history.
- **AM-STAGE-019:** Delivery shall remain active until approve-and-close is
  explicitly chosen in checkpoint interaction. Continuous interaction may
  record approval only when `run.md` contains the explicit delegation defined
  by AM-RUN-005.
- **AM-STAGE-020:** Automated Stage-completion findings shall be limited to the
  common structural checks for minimum non-blank sections, designated existing
  references, recorded execution outcomes, and applicable approval or
  delegation. Engineering-quality concerns belong to agent-authored findings
  and developer checkpoint decisions.

## 10. Embedded evidence, findings, and decisions

### 10.1 Evidence

- **AM-EVIDENCE-001:** Evidence shall be recorded in the Stage that produced or
  evaluated it.
- **AM-EVIDENCE-002:** Automated evidence shall include timestamp, command or
  selector, working directory, exit status, concise observed result, and the
  tests covered by the claim.
- **AM-EVIDENCE-003:** Manual evidence shall include timestamp, procedure,
  expected observation, actual observation, and actor.
- **AM-EVIDENCE-004:** A red test record shall include the SHA-256 fingerprint
  of each relevant test file's exact bytes.
- **AM-EVIDENCE-005:** The later green record shall compare those fingerprints
  and name every test file that changed between red and green.
- **AM-EVIDENCE-006:** Changed tests shall create a finding, not a blocker.
- **AM-EVIDENCE-007:** Raw output too large for a readable Stage file may be
  stored as an Attachment. The Stage shall retain a concise result and the
  attachment path and digest.
- **AM-EVIDENCE-008:** Later evidence may supersede a result but shall never
  erase the earlier red witness or failure.
- **AM-EVIDENCE-009:** Automated command outcome shall be exactly one of
  `passed`, `failed`, `timed_out`, `cancelled`, or `launch_error`.
- **AM-EVIDENCE-010:** `failed` shall mean that the command completed and
  returned a failing exit status. It shall not describe a command that timed
  out, was cancelled, or could not be launched.
- **AM-EVIDENCE-011:** A timed-out, cancelled, or unlaunched command shall leave
  the test, lint, or audit result unknown. AEGIS shall record the operational
  outcome and a finding and shall never present it as a test failure or pass.
- **AM-EVIDENCE-012:** Retrying a timed-out, cancelled, failed, or unlaunched
  command shall append new evidence and shall preserve the earlier attempt.

### 10.2 Findings

- **AM-FINDING-001:** A finding shall be a distinct entry inside its owning
  Stage with a stable stage-local label, severity, observation, consequence,
  and disposition.
- **AM-FINDING-002:** Finding disposition shall be `open`, `resolved`,
  `accepted`, `waived`, or `not_applicable`.
- **AM-FINDING-003:** Resolving or accepting a finding shall append the decision
  and shall not rewrite the original observation.
- **AM-FINDING-004:** Findings shall report truth and shall not prevent work
  under the shipped defaults.

### 10.3 Decisions

- **AM-APPROVAL-001:** A decision shall be recorded in the Stage that owns its
  target.
- **AM-APPROVAL-002:** Decision value shall be `approved`, `rejected`, or
  `exception_approved` and shall include timestamp, actor, target, and reason or
  conditions.
- **AM-APPROVAL-003:** An `exception_approved` decision shall identify the
  expectation that does not apply, its mandatory reason, its effect, and any
  alternative confirmation. It shall never be recorded as passed.
- **AM-APPROVAL-004:** Earlier decisions shall remain visible. A later approval
  shall state what changed since a prior rejection.
- **AM-APPROVAL-005:** An AI agent may record Delivery approval and continue
  without another developer prompt only when the current Run records explicit
  continuous-interaction delegation.
- **AM-APPROVAL-006:** Checkpoint-mode approval shall come from the developer's
  presented choice; an agent shall not synthesize it from completion evidence
  or from the lack of a rejection.

### 10.4 Skips and waivers

- **AM-ESCAPE-001:** A skip or waiver shall be recorded in the Stage that owns
  the bypassed work or finding.
- **AM-ESCAPE-002:** Each entry shall include timestamp, type, target, actor,
  mandatory reason, and effect on the Stage outcome.
- **AM-ESCAPE-003:** Escape use shall remain visible in Delivery.

## 11. Requirements, specifications, and tests

### 11.1 Requirement artifact

Each `REQ-<32hex>.toml` shall be authoritative for one behavior and shall
contain:

- identity, title, current status, and `Must / Should / Could` priority;
- one self-contained behavior statement;
- a separately stated confirmation method;
- impacted implementation files;
- automated-test links or an explicit manual-test classification;
- optional Specification path;
- rationale; and
- the timestamp of the current update.

- **AM-REQ-001:** A Requirement artifact shall not contain ticket identifiers,
  Run identifiers, source-Run provenance, or cross-references needed to
  understand its behavior. Workflow provenance remains in the owning Run.
- **AM-REQ-002:** Requirement status shall be `draft` or `active`.
- **AM-REQ-003:** An automated Requirement shall contain at least one linked
  real project test with `happy_path` among its purposes.
- **AM-REQ-004:** A manual Requirement shall contain a concrete manual method.
- **AM-REQ-005:** One Requirement file may contain multiple `[[tests]]` links,
  but shall still describe exactly one behavior.
- **AM-REQ-006:** A test link shall contain the real repository-relative test
  path, an optional framework selector, risk purposes, and the implementation
  files it covers.
- **AM-REQ-007:** The test link inside the Requirement shall replace a separate
  AEGIS test-registration artifact.
- **AM-REQ-008:** Risk purposes shall support at least `happy_path`,
  `boundary`, `edge`, `negative`, and `failure_path`.
- **AM-REQ-009:** Risk-based depth shall add non-happy-path purposes when the
  behavior's impact, likelihood, complexity, or failure cost justifies them.
- **AM-REQ-010:** A changed covered implementation file shall select the linked
  test or selector for validation.
- **AM-REQ-011:** If traceability cannot safely determine the impacted set,
  validation shall select the full configured suite and record why.
- **AM-REQ-012:** Updating a Requirement shall replace its authoritative current
  content in place. Removing a Requirement shall delete its file without
  publishing a retirement record, tombstone, superseded copy, or embedded
  change history.
- **AM-REQ-013:** Requirement links to impacted files, tests, manual methods, and
  an optional Specification shall describe only the current relationships.

### 11.2 Test files

- **AM-TEST-001:** Tests are executable project files, not AEGIS metadata.
- **AM-TEST-002:** New tests shall be created under a test root selected by
  `config.toml` and according to the repository's language and framework.
- **AM-TEST-003:** With the shipped default, new tests shall live below
  `.agentic/tests/`.
- **AM-TEST-004:** When an existing repository test root is configured, new
  tests shall live there unless the developer explicitly chooses another
  configured root.
- **AM-TEST-005:** AEGIS shall not move existing tests merely to conform to the
  default layout.
- **AM-TEST-006:** AEGIS shall validate that linked test paths exist and lie
  below a configured test root; inconsistencies shall be findings.

### 11.3 Specification

- **AM-SPEC-001:** A Specification shall be optional and shall exist only where
  the Requirement alone is not buildable.
- **AM-SPEC-002:** It shall inherit the Requirement identity and reference that
  Requirement explicitly in its front matter.
- **AM-SPEC-003:** Updating a Specification shall replace its current content.
  Deleting a Specification shall delete its file and clear the Requirement's
  Specification path in one atomic publication.
- **AM-SPEC-004:** Deleting a Requirement shall also delete its Specification in
  the same atomic publication because a Specification cannot exist without its
  Requirement.

## 12. Components

Components are mandatory project documentation and the primary repository
context source during Intake.

- **AM-COMP-001:** A Component shall describe one functional or implementation
  domain and its file membership.
- **AM-COMP-002:** It shall record purpose, boundary, interfaces, dependencies,
  files and their roles, linked Requirements, relevant test paths/selectors,
  known gaps, and drift-review state.
- **AM-COMP-003:** Component prose shall be short enough to read instead of
  re-reading the entire source during Intake.
- **AM-COMP-004:** Component documentation shall be reviewed whenever behavior,
  interface, dependency, or file membership changes.
- **AM-COMP-005:** A missing or stale Component shall create a finding and a
  documentation task, not block the run.
- **AM-COMP-006:** Component links shall point directly to project Requirement
  artifacts and real project tests; no Test registration shall be required.
- **AM-COMP-007:** Updating a Component shall replace its authoritative current
  content. Removing a Component shall delete its document without a retired
  state, tombstone, superseded copy, source-Run provenance, or embedded change
  history.

## 13. Adoption

- **AM-ADOPT-001:** One `ADOPT-<32hex>.md` shall track adoption of one Component
  or bounded repository area.
- **AM-ADOPT-002:** It shall record observed implementation, observed tests,
  derived Components and Requirements, traceability established, unresolved
  gaps, completed work, and the next action.
- **AM-ADOPT-003:** Adoption shall be incrementally and atomically updated so a
  later session can resume it.
- **AM-ADOPT-004:** Adoption shall preserve uncertainty and shall not invent
  behavior or coverage to appear complete.
- **AM-ADOPT-005:** Adoption status shall be `active`, `completed`, or
  `abandoned`.

## 14. Abandonment

- **AM-ABANDON-001:** Normal abandonment shall set the Run status to
  `abandoned`, record the decision in `run.md`, and record the stopping context
  in the currently active Stage file. It shall clear the local pointer when that
  pointer still selects the abandoned Run.
- **AM-ABANDON-002:** Normal abandonment shall not create a separate artifact.
- **AM-ABANDON-003:** If the Run directory or `run.md` is unreadable or cannot
  be safely updated, AEGIS shall create
  `.agentic/runs/ABANDON-RUN-<32hex>.md` as an exceptional recovery record.
- **AM-ABANDON-004:** The exceptional record shall identify the Run, actor,
  timestamp, reason, last known state, unreadable paths, and any preserved
  diagnostic details.
- **AM-ABANDON-005:** AEGIS shall never overwrite unreadable Run bytes in order
  to record abandonment.

## 15. Attachments

- **AM-ATTACH-001:** Attachments shall be used only when content would make a
  Stage file materially harder to read or cannot be represented safely as
  Markdown.
- **AM-ATTACH-002:** Each Attachment reference shall include path, media or
  content type, byte length, SHA-256 digest, purpose, and owning Stage.
- **AM-ATTACH-003:** An Attachment shall not contain the only copy of a finding,
  approval, conclusion, next action, or evidence result.
- **AM-ATTACH-004:** Attachments shall remain inside their owning Run and shall
  never be shared by path across Runs.

## 16. Paths, encoding, and atomic publication

- **AM-DURABLE-001:** Stored repository paths shall be relative to repository
  root, use `/` separators, and contain no drive prefix, leading `/`, empty
  segment, `.` segment, or `..` segment.
- **AM-DURABLE-002:** AEGIS-created TOML and Markdown shall use UTF-8 without a
  byte-order mark and LF line endings.
- **AM-DURABLE-003:** General text readers shall explicitly tolerate UTF byte-
  order marks, CRLF, and Windows-1252 where needed for real repository input.
- **AM-DURABLE-004:** Fingerprints shall use exact raw bytes before text or
  newline normalization.
- **AM-DURABLE-005:** Durable files shall be written to a temporary sibling,
  flushed, and atomically replaced.
- **AM-DURABLE-006:** Interruption shall leave either the earlier valid file or
  the complete later valid file, never a partially published authoritative
  artifact.
- **AM-DURABLE-007:** New project artifacts and Attachments shall be published
  before the Stage that references them; the Stage shall be published before
  `run.md` summarizes it.
- **AM-DURABLE-008:** A malformed file shall remain preserved and shall produce
  a path-specific structured error.
- **AM-DURABLE-009:** Artifacts shall not require secrets, credentials, or
  environment-variable values to be stored.
- **AM-DURABLE-010:** Transient recovery material shall remain inside the
  repository at `.agentic/.runtime/`, shall be excluded from version control,
  and shall be sufficient to restore a complete before-or-after state after an
  interrupted multi-file publication.
- **AM-DURABLE-011:** AEGIS shall remove completed recovery transactions after
  successful publication or recovery. Their temporary copies shall not become
  retained project history.

## 17. Collaboration and post-integration validation

- **AM-COLLAB-001:** Independent Runs, Requirements, Components, Adoptions, and
  Attachments shall use independent identifier-named paths.
- **AM-COLLAB-002:** Normal work shall modify no shared sequence counter or
  global registry. The local selected-context pointer shall be excluded from
  version control so independent working copies do not merge it.
- **AM-COLLAB-003:** Concurrent edits to the same Requirement, Component,
  Adoption, Run, or Stage file shall remain genuine merge overlap visible to
  the developer.
- **AM-COLLAB-004:** Tests remain ordinary project files and follow the
  repository's existing merge behavior.
- **AM-COLLAB-005:** `trace-validate` shall report duplicate identities, missing
  targets, broken traceability, conflicting file membership, and diverged
  coverage, then allow the developer to fix forward.
- **AM-COLLAB-006:** No server, shared database, user-home state, machine cache,
  or worktree-external state shall be required to interpret or resume work.

## 18. Cross-artifact validation

AEGIS shall report at least:

1. malformed or unsupported schemas;
2. canonical-path and internal-identity mismatches;
3. Run-directory, `run_id`, and Stage-name disagreements;
4. missing or duplicate canonical Stage files;
5. invalid Stage transitions or `run.md` summaries that disagree with Stages;
6. skips or waivers without an actor and reason;
7. decisions missing actor, reason, time, or applicable Run context;
8. missing Requirement, Specification, Component, test, or Attachment targets;
9. automated Requirements without a happy-path test link;
10. manual Requirements without a concrete method;
11. linked tests outside configured test roots or without covered files;
12. changed tests between recorded red and green evidence;
13. changed Component files without recorded drift review;
14. delivered Runs without Delivery approval;
15. normal or exceptional abandonment inconsistencies;
16. payload files missing from or differing from the manifest;
17. paths that escape the repository or are unsafe on supported platforms; and
18. temporary files left by interrupted publication;
19. duplicate validation command names, invalid working directories, or malformed
    argument arrays; and
20. command evidence that confuses failure with timeout, cancellation, or
    launch error.

- **AM-VALIDATE-001:** Validation output shall be concise, stable, machine-
  readable, and model-readable.
- **AM-VALIDATE-002:** Validation shall name the relevant artifact, Stage, or
  repository path for every finding.
- **AM-VALIDATE-003:** Validation shall not modify project artifacts or block
  workflow operations under the shipped defaults.

## 19. Template set

The planning/reference set is:

| Template | Purpose |
|---|---|
| `payload_manifest.toml` | Product-owned payload identity and file inventory. |
| `config.toml` | Generated project path, validation-command, and advisory-policy integration map. |
| `rules.md` | Optional project-specific guidance. |
| `requirement.toml` | One behavior and its direct impacted-file/test traceability. |
| `spec.md` | Optional build-level detail for one Requirement. |
| `component.md` | Mandatory component knowledge used during Intake. |
| `adoption.md` | Renderer-generated incremental existing-repository adoption reference. |
| `context.toml` | Non-authoritative selected-Run pointer for one working copy. |
| `run.md` | Run identity, ticket, scope, execution instruction, stage summary, and outcome. |
| `01-intake.md` through `08-delivery.md` | Renderer-generated default Stage state and resume references. |
| `abandonment.md` | Renderer-generated exceptional fallback reference for an unreadable normal Run. |

- **AM-TEMPLATE-001:** Templates shall contain no project-specific fact,
  completed evidence, real identifier, or default success claim.
- **AM-TEMPLATE-002:** Placeholder values shall be visibly synthetic and shall
  fail publication validation until replaced.
- **AM-TEMPLATE-003:** Standalone TOML reference files and TOML snippets in
  planning Markdown examples shall parse with standard-library `tomllib` on the
  supported Python 3.12 runtime. A schematic planning Markdown file is not a
  runtime artifact unless it is explicitly marked as renderer-generated.
- **AM-TEMPLATE-004:** The eight Stage templates shall share a common state and
  history shape while retaining stage-specific instructions and sections.
- **AM-TEMPLATE-005:** The renderer-generated Stage, Adoption, and exceptional
  Abandonment references shall parse through the current artifact codec and
  round-trip their metadata and structured state.
- **AM-TEMPLATE-006:** No file under `00_Planning/templates/` shall be treated as
  a payload file or copied into a release artifact. Runtime authority remains
  the codec and workflow resources under `05_Software/aegis/template/`.

## 20. Acceptance conditions

The artifact model is ready for technical design when the templates and
validation rules demonstrate that:

1. deleting `.agentic/aegis/` preserves all project data and application code;
2. WAEGIS generates a usable path map without developer configuration;
3. a repository without detected tests uses `.agentic/tests/`, while a
   repository with tests uses its detected configured roots;
4. multiple Runs coexist while each working copy has at most one local selected
   context that is not merged as project state;
5. another session resumes from `run.md` and the current Stage file without
   chat history;
6. evidence, findings, decisions, skips, waivers, and corrections remain visible
   inside their owning Stage without separate artifact directories;
7. Requirement-to-file-to-test traceability is complete without Test
   registration files;
8. red and green evidence exposes every changed test fingerprint;
9. normal abandonment stays in the Run and unreadable state can still be
   abandoned through the exceptional sibling record;
10. interruption cannot publish a partial authoritative file; and
11. test, lint, and named audit commands retain distinct pass, failure,
    timeout, cancellation, and launch-error outcomes; and
12. updating or deleting a Requirement, Specification, Component, or
    traceability relationship leaves only current project knowledge while the
    owning Run retains the workflow evidence; and
13. every renderer-generated machine-artifact reference parses with its
    declared schema on Windows and Ubuntu.

The CLI and Machine Protocol Contract operates on these artifacts, the
Acceptance Plan defines their required proof, the Technical Architecture
defines their implementation boundaries, and the Implementation Plan sequences
their delivery.
