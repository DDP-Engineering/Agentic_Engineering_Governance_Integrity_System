<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Functional Specification

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-10  
**Authoritative requirements:** `AEGIS_PRODUCT_REQUIREMENTS.md`  
**Artifact design:** `AEGIS_ARTIFACT_MODEL.md`  
**Release view:** `AEGIS_RELEASE_SCOPE.md`

## 1. Purpose and relationship

This document defines the observable behavior of AEGIS and WAEGIS: what a
developer or AI agent experiences, which workflow states exist, what each stage
does, how work resumes, and how AEGIS records truth without preventing work.

Only `PR-*` entries in the Product Requirements Register are product
requirements. The `FS-*` identifiers below are functional rules used to explain
and test those requirements; they do not create another requirements register.
When a new product promise is discovered, it must first be added to the Product
Requirements Register.

The Artifact Model owns exact paths, schemas, identifiers, and publication
ordering. The CLI and Machine Protocol Contract owns command names,
arguments, response schemas, and exit-code conventions.

- **FS-AUTH-001:** Product intent, priority, and status come from the Product
  Requirements Register.
- **FS-AUTH-002:** Functional behavior in this document must not contradict or
  weaken a referenced Product Requirement.
- **FS-AUTH-003:** Artifact structure must follow the Artifact Model without
  changing the observable workflow behavior defined here.
- **FS-AUTH-004:** Human and machine interfaces must communicate the same state,
  result, finding, evidence, and next-action meaning.

## 2. Product interaction and responsibility

**Implements:** `PR-ROLE`, `PR-WORKFLOW`, `PR-DEFAULT`, `PR-POSTURE`

### 2.1 Central interaction

- **FS-CORE-001:** A developer starts a Run by supplying the unmodified text of
  a ticket. AEGIS derives the scope, requirements, design, verification, and
  recorded outcome through the workflow.
- **FS-CORE-002:** AEGIS guides work through Intake, Alignment, Requirement,
  Design, Check, Implementation, Validation, and Delivery.
- **FS-CORE-003:** Each Stage provides a written, self-contained instruction
  usable by a human developer or a supported AI agent.
- **FS-CORE-004:** The human or AI performs the engineering work. AEGIS records
  state, computes comparisons and traceability, executes selected local tools,
  and reports evidence and findings.
- **FS-CORE-005:** Under shipped defaults, AEGIS does not refuse an edit,
  command, exception, or Stage closure because of a policy result.
- **FS-CORE-006:** A human-only Run and an AI-operated Run use the same stages,
  artifacts, decisions, evidence meanings, findings, and terminal outcomes.
- **FS-CORE-007:** Workflow effort remains proportional to the work; a small,
  understood change can use the short profile without losing truthful evidence.

### 2.2 Responsibilities and uninterrupted agent operation

- **FS-ROLE-001:** The developer owns scope, approvals, exception decisions,
  interpretation of findings, and every outward-facing Git action.
- **FS-ROLE-002:** When the developer instructs an AI agent to complete the Run
  without intermediate prompts, the agent performs the workflow and records
  decisions and approvals as the developer's representative.
- **FS-ROLE-003:** Agent-recorded decisions identify the agent as actor and have
  the same workflow effect as decisions entered directly by the developer.
- **FS-ROLE-004:** The AI follows the developer's Run instruction and preserves
  that instruction as context when it affects workflow interaction.
- **FS-ROLE-005:** The developer is also the normal reviewer. A separate reviewer
  persona is not required.
- **FS-ROLE-006:** The WAEGIS operator manages installation and payload lifecycle
  and will normally be the same developer.

## 3. Installed project experience and configuration

**Implements:** `PR-DEFAULT`, `PR-CONFIG`, `PR-PAYLOAD`, `PR-POSTURE`

### 3.1 First use

- **FS-CONFIG-001:** WAEGIS creates a complete project-owned integration
  configuration during installation.
- **FS-CONFIG-002:** The first Run can start without asking the developer to
  complete policy, choose a mode, define globs, or identify artifact folders.
- **FS-CONFIG-003:** The configuration identifies the Requirements, Components,
  tests, Adoptions, and Runs locations used by AEGIS.
- **FS-CONFIG-004:** Project-specific guidance is optional. Its absence selects
  the shipped workflow rules.
- **FS-CONFIG-005:** Configuration can relocate project-owned paths and add
  explicitly requested project behavior without becoming necessary for core
  workflow value.

### 3.2 Test-root selection

- **FS-CONFIG-006:** When WAEGIS confidently detects existing project test
  roots, it records those roots and does not move the tests.
- **FS-CONFIG-007:** When no existing test root is detected, the generated
  configuration selects `.agentic/tests/`.
- **FS-CONFIG-008:** More than one configured test root can be active.
- **FS-CONFIG-009:** AEGIS creates new tests within a configured test root using
  the target repository's selected language and framework conventions.
- **FS-CONFIG-010:** A linked test outside all configured test roots produces a
  finding and remains visible; it does not block the Run.

### 3.3 Validation command configuration

- **FS-CONFIG-011:** Configuration supports uniquely named local command entries
  categorized as tests, lints, or audits.
- **FS-CONFIG-012:** WAEGIS records test and lint commands it can detect
  confidently from the repository.
- **FS-CONFIG-013:** When no suitable command is detected, the relevant AEGIS
  adapter selects and reports its shipped default for the language and
  framework in use.
- **FS-CONFIG-014:** Each command has its own repository-relative working
  directory and timeout value.
- **FS-CONFIG-015:** A timeout value of zero means AEGIS imposes no automatic
  timeout. The operator can still cancel execution.
- **FS-CONFIG-016:** Adding a named repository audit makes it available to the
  Validation Stage without turning it into a gate.
- **FS-CONFIG-017:** A repository audit can implement changed-file scoping
  through its own command options so audit cost remains proportional.

## 4. Run lifecycle and working context

**Implements:** `PR-RUN`, `PR-EVOL`, `PR-SNAPSHOT`, `PR-DELIVERY`,
`PR-COLLAB`

### 4.1 Creation and identity

- **FS-RUN-001:** Valid ticket text creates a distinct Run with a locally
  generated collision-resistant identity.
- **FS-RUN-002:** The Run preserves the original ticket text verbatim and keeps
  later interpretations and scope changes separately visible.
- **FS-RUN-003:** Empty or unreadable ticket input returns a structured input
  error before a Run is created.
- **FS-RUN-004:** A Run identifies its work type as `feature`, `change`,
  `quick_fix`, or `bug_fix`.
- **FS-RUN-005:** A Run owns its workflow metadata; Requirements, Components,
  and executable tests remain project artifacts referenced by the Run.

### 4.2 Run status

| Status | Meaning | Terminal |
|---|---|---:|
| `active` | Work can continue now or in a later session. | No |
| `delivered` | Delivery recorded an approved truthful outcome. | Yes |
| `abandoned` | Work ended without Delivery and the reason was recorded. | Yes |

- **FS-RUN-006:** A new Run is `active` with Intake as its current Stage.
- **FS-RUN-007:** Ending a human or model session does not change an active Run
  into a terminal or machine-local pause state.
- **FS-RUN-008:** A delivered or abandoned Run is not reopened. Follow-up work
  uses a new Run.
- **FS-RUN-009:** A correction to terminal audit information is additive and
  does not rewrite the terminal event or earlier unfavorable evidence.

### 4.3 Multiple Runs and selection

- **FS-CONTEXT-001:** Multiple Runs, including multiple active Runs, can coexist
  in one repository and branch.
- **FS-CONTEXT-002:** Each working copy retains at most one selected Run in a
  repository-local context pointer below the configured Runs root. Routine
  Run-scoped operations act on that Run without requiring its identifier again.
- **FS-CONTEXT-003:** The context pointer stores only the selected Run identity.
  The current Stage is read from that Run's `run.md`; it is never duplicated in
  the pointer. Durable resume and audit state remains inside the Run.
- **FS-CONTEXT-004:** Creating a Run selects it. The developer or instructed
  agent can explicitly select another Run. If the pointer is absent and exactly
  one active Run exists, AEGIS may select it and report that action. If several
  candidates exist, AEGIS lists them and requests selection rather than guess.
  Delivery or abandonment clears a pointer that still selects the terminal Run.
- **FS-CONTEXT-005:** Switching operational context does not alter another Run.
  Its latest durable Stage file remains the resume snapshot.
- **FS-CONTEXT-006:** Selecting a Run does not claim that it owns every current
  working-tree change.

### 4.4 Change attribution

- **FS-BASE-001:** Intake records the initial branch, revision, and staged,
  unstaged, untracked, deleted, and renamed paths needed to distinguish
  pre-existing changes from later observations.
- **FS-BASE-002:** A dirty working tree does not prevent Run creation, Stage
  progress, or Delivery.
- **FS-BASE-003:** Pre-existing changes remain visible and are excluded from
  claims that the Run produced them.
- **FS-BASE-004:** AEGIS reports observed timing and state when authorship cannot
  be established; it does not invent human or agent authorship.
- **FS-BASE-005:** A changed branch, revision, index, or worktree that weakens
  attribution produces a finding rather than a false claim or blocker.

## 5. Run profiles and Stage state

**Implements:** `PR-WORKFLOW`, `PR-POSTURE`, `PR-ESCAPE`

### 5.1 Profiles

- **FS-PROFILE-001:** The full profile includes all eight Stages and is the
  default.
- **FS-PROFILE-002:** The developer can select a short profile for small,
  well-understood work.
- **FS-PROFILE-003:** The short profile retains Intake, Alignment, Requirement,
  Check, Implementation, Validation, and Delivery and records Design as
  `omitted`.
- **FS-PROFILE-004:** Short-profile Alignment and Requirement may occur in one
  interaction while retaining separate Stage files and outcomes.
- **FS-PROFILE-005:** The short profile retains red-before-green, changed-test
  comparison, impacted Validation, findings, approvals, and truthful Delivery.
- **FS-PROFILE-006:** An active Run may change from short to full, making Design
  pending. It may change from full to short only before Design work is applied.
- **FS-PROFILE-007:** A profile change is recorded and does not erase earlier
  Stage history, evidence, findings, decisions, or project artifacts.

### 5.2 Stage status

Each Run contains all eight canonical Stage records:

| Status | Meaning |
|---|---|
| `pending` | Included by the profile, but not started. |
| `active` | Current focus of the Run. |
| `completed` | Work and its actual outcome were recorded. This does not mean every check passed. |
| `skipped` | Included work was deliberately bypassed with an actor and mandatory reason. |
| `omitted` | The selected profile did not include the Stage. |

- **FS-STAGE-001:** `passed` and `failed` are evidence outcomes, not Stage
  statuses.
- **FS-STAGE-002:** Normally one Stage is active and later included Stages are
  pending.
- **FS-STAGE-003:** A Stage can complete with open findings, failed evidence,
  uncertainty, or waived work when those facts are recorded truthfully.
- **FS-STAGE-004:** Deliberately unperformed included work is `skipped`, never
  `completed`, passed, or `omitted`.
- **FS-STAGE-005:** A profile-excluded Stage is `omitted` and requires no waiver.
- **FS-STAGE-006:** Completed or skipped work can be revisited by making the
  Stage active again. Earlier events remain visible.
- **FS-STAGE-007:** Work already applied cannot later be represented as skipped
  or omitted.
- **FS-STAGE-008:** Intake and Delivery cannot be skipped or omitted in a
  delivered Run.

### 5.3 Stage transitions

| From | To | Functional condition |
|---|---|---|
| `pending` | `active` | The Run advances to or revisits an included Stage. |
| `active` | `completed` | Work and its actual outputs, evidence, findings, decisions, and handoff are saved. |
| `pending` or `active` | `skipped` | The work has not already been applied and an actor plus mandatory reason are recorded. |
| `skipped` | `active` | The developer later chooses to perform the work; the earlier skip remains in history. |
| `completed` | `active` | Scope evolution, correction, or review requires another Stage pass; earlier completion remains in history. |
| `omitted` | `pending` | A profile change adds the Stage. |
| `pending` | `omitted` | A permitted profile change removes the not-yet-applied Stage. |

- **FS-STAGE-009:** Each transition appends a Stage event and updates the Run
  summary only after the Stage state is durable.
- **FS-STAGE-010:** A transition rejected because its source state is malformed
  or contradictory returns a structured state error and preserves the existing
  bytes for recovery or abandonment.

### 5.4 Common Stage contract

- **FS-STAGE-011:** Every Stage instruction states its purpose, inputs, expected
  work, expected outputs, common findings, escape actions, and handoff needs. A
  Stage read returns this instruction together with the Stage's current state,
  revision, and immediate next actions.
- **FS-STAGE-012:** Each Stage records its status, inputs, decisions, work,
  evidence, findings, outputs, handoff, next action, and event history in its
  canonical Stage file. Approvals and exceptions are decision values rather
  than separate record categories.
- **FS-STAGE-013:** A missing category is stated explicitly as none or unknown;
  mandatory sections are not removed to imply success.
- **FS-STAGE-014:** Large or binary material can be attached, but the Stage file
  retains the conclusion, finding, decision, and next action.
- **FS-STAGE-015:** A Stage update reports unmet expectations but does not refuse
  closure under shipped policy.

## 6. Stage contracts

**Implements:** `PR-WORKFLOW`, `PR-REQ`, `PR-COMP`, `PR-TRACE`, `PR-RED`,
`PR-INT`, `PR-REPORT`, `PR-DELIVERY`

### 6.1 Intake

**Purpose:** Turn raw ticket text into a preserved intent and an initial,
evidence-based view of the affected repository area.

**Inputs:** Ticket text, generated configuration, optional project rules,
repository state, relevant Components, and linked Requirements and tests.

**Outputs:** Ticket restatement, initial scope, repository baseline, relevant
project knowledge, open questions, findings, and Alignment handoff.

- **FS-INTAKE-001:** Intake accepts ticket prose without requiring a prepared
  scope, requirement list, test plan, or task breakdown.
- **FS-INTAKE-002:** Intake reads project configuration and optional project
  rules before interpreting repository paths.
- **FS-INTAKE-003:** Intake locates relevant Component documents and reads their
  linked Requirements and tests before establishing scope.
- **FS-INTAKE-004:** Component file membership guides bounded source inspection
  instead of requiring the whole repository to be reread.
- **FS-INTAKE-005:** Missing, stale, or uncertain Component knowledge produces a
  finding and does not block Intake.
- **FS-INTAKE-006:** Intake distinguishes ticket intent from assumptions
  introduced by the human or AI.
- **FS-INTAKE-007:** Intake performs no required implementation or test edit.
- **FS-INTAKE-008:** A Run that should not proceed from Intake is abandoned
  rather than delivered with an empty intent.

### 6.2 Alignment

**Purpose:** Correct direction cheaply before Requirements, tests, or
implementation make misunderstanding expensive.

**Inputs:** Intake restatement, initial scope, repository observations, and open
questions.

**Outputs:** Included scope, exclusions, assumptions, remaining questions,
profile choice, approval, and any instruction to continue without prompts.

- **FS-ALIGN-001:** Alignment presents included work, exclusions, assumptions,
  and material open questions in language the developer can correct.
- **FS-ALIGN-002:** Developer correction changes the current interpretation but
  does not overwrite the ticket or earlier interpretation.
- **FS-ALIGN-003:** Open questions can remain when the Stage completes if the
  accepted assumptions or recommended responses and associated risk are
  recorded.
- **FS-ALIGN-004:** AEGIS may recommend pausing for risk or uncertainty but does
  not force a blocking pause under shipped policy.
- **FS-ALIGN-005:** Alignment does not write implementation code.
- **FS-ALIGN-006:** A skipped Alignment carries the unconfirmed Intake
  interpretation and skip reason through Delivery.

### 6.3 Requirement

**Purpose:** Express agreed behavior as independently understandable and
verifiable project Requirements.

**Inputs:** Aligned scope, existing Requirements, relevant Components, and
known tests.

**Outputs:** Created, updated, or deleted Requirement artifacts; optional
Specifications; impacted files; direct test links or manual methods; and gaps.

- **FS-REQ-001:** Each distinct behavior is represented by a separate
  Requirement artifact.
- **FS-REQ-002:** Requirement behavior remains understandable without the ticket,
  Run, or another Requirement statement.
- **FS-REQ-003:** Ticket and Run provenance remains in the owning Run and does
  not appear in the project Requirement artifact or its self-contained behavior
  statement.
- **FS-REQ-004:** Confirmation is stated separately as automated verification or
  a concrete justified manual method.
- **FS-REQ-005:** EARS phrasing is recommended only where it improves clarity.
- **FS-REQ-006:** A Specification is created only when the Requirement alone is
  insufficient to build the behavior.
- **FS-REQ-007:** Requirement priority uses `Must`, `Should`, or `Could`, and
  current lifecycle status is `draft` or `active`. Removing a Requirement
  deletes it rather than changing it to a historical lifecycle state.
- **FS-REQ-008:** Each automated Requirement directly identifies actual project
  tests, selectors, purposes, and the implementation files they cover.
- **FS-REQ-009:** A skipped Requirement Stage does not synthesize Requirements
  later; missing coverage remains visible through Delivery.

### 6.4 Design

**Purpose:** Explain the smallest solution that satisfies the Requirements.

**Inputs:** Requirements, Specifications, Components, and relevant repository
constraints.

**Outputs:** Concise solution, Requirement coverage, affected Components and
files, interfaces, alternatives, risks, and approval.

- **FS-DESIGN-001:** The design cites each Requirement it intends to satisfy.
- **FS-DESIGN-002:** The design identifies affected Components, files,
  interfaces, data, failure behavior, and meaningful alternatives.
- **FS-DESIGN-003:** Design detail remains proportional and does not require a
  speculative architecture for a small change.
- **FS-DESIGN-004:** Design does not create implementation code or falsely claim
  that tests were executed.
- **FS-DESIGN-005:** The short profile records Design as omitted and carries a
  concise implementation note in Requirement handoff information.

### 6.5 Check

**Purpose:** Create or select verification and preserve actual red evidence
before implementation.

**Inputs:** Requirements, Specifications, design or short-path implementation
note, configured test roots, and repository state.

**Outputs:** Test changes, risk purposes, actual red result, exact test
fingerprints, repository-change comparison, findings, and Implementation
handoff.

- **FS-CHECK-001:** Check creates or selects tests within configured project
  test roots and links them to Requirements and covered implementation files.
- **FS-CHECK-002:** Automated verification includes a happy path unless the
  Requirement has justified manual verification.
- **FS-CHECK-003:** Boundary, edge, negative, and failure-path tests are added
  according to risk rather than a fixed quota.
- **FS-CHECK-004:** Where red-before-green applies, Check records an actual
  failing execution before implementation begins.
- **FS-CHECK-005:** The red record includes the command or selector, working
  directory, operational outcome, concise failure, timestamp, and exact-byte
  SHA-256 fingerprints of relevant test files.
- **FS-CHECK-006:** A test that unexpectedly passes before implementation
  produces a finding because it does not demonstrate the intended red witness.
- **FS-CHECK-007:** When red-before-green genuinely does not apply, the developer
  or instructed agent records an `exception_approved` decision, mandatory
  reason, and alternative confirmation method.
- **FS-CHECK-008:** AEGIS compares repository state around Check and reports any
  implementation-file change as a finding without reverting or refusing it.
- **FS-CHECK-009:** Test edits made during Check remain ordinary project edits
  and are captured by their red fingerprints.

### 6.6 Implementation

**Purpose:** Implement the agreed behavior and expose any change to the recorded
tests.

**Inputs:** Requirements, design or implementation note, red evidence, test
fingerprints, and attributed repository state.

**Outputs:** Implementation changes, change attribution, green evidence,
test-fingerprint comparison, Component drift review, findings, and Validation
handoff.

- **FS-IMPLEMENT-001:** Implementation changes project code to satisfy the
  agreed Requirements and recorded verification.
- **FS-IMPLEMENT-002:** AEGIS records the changed implementation and test paths
  without claiming authorship it cannot establish.
- **FS-IMPLEMENT-003:** The selected focused tests can be executed during
  Implementation and their actual outcome is recorded.
- **FS-IMPLEMENT-004:** Current test fingerprints are compared with the Check
  fingerprints and every changed test path is named in a finding.
- **FS-IMPLEMENT-005:** A changed test remains permitted because correction can
  be legitimate; the developer or instructed agent records its explanation and
  disposition.
- **FS-IMPLEMENT-006:** A change to Component behavior, interface, dependency,
  or file membership triggers Component documentation review and update or a
  visible drift finding.
- **FS-IMPLEMENT-007:** An AI agent instructed to complete the workflow may
  record the Implementation decision and continue without another prompt.

### 6.7 Validation

**Purpose:** Re-run the complete safely determined impacted regression set and
record the actual outcome.

**Inputs:** Requirements, changed files, direct test links, implementation
evidence, configured validation commands, and open findings.

**Outputs:** Impacted selection explanation, automated and manual evidence,
lint and audit results, test-integrity conclusion, findings, waivers, and
Delivery handoff.

- **FS-VALIDATE-001:** Every changed covered implementation file selects all
  directly linked tests, including tests linked through other Requirements.
- **FS-VALIDATE-002:** Tests created or changed by the Run remain selected even
  when traceability is incomplete.
- **FS-VALIDATE-003:** AEGIS normally executes the safely determined impacted
  subset rather than the full suite.
- **FS-VALIDATE-004:** If selection cannot be established safely and completely,
  AEGIS selects the full configured suite and records why.
- **FS-VALIDATE-005:** Validation executes applicable named test, lint, and audit
  commands and records each outcome independently.
- **FS-VALIDATE-006:** Manual verification records actor, procedure, expected
  observation, actual observation, and time.
- **FS-VALIDATE-007:** Validation preserves failed, timed-out, cancelled, and
  unlaunched attempts when a later retry produces another result.
- **FS-VALIDATE-008:** Open findings or failed evidence do not prevent Stage
  completion; their consequences remain visible for Delivery.

### 6.8 Delivery

**Purpose:** Give the developer a concise, truthful outcome without requiring
reconstruction of the Run.

**Inputs:** Ticket intent, scope history, project artifacts, all Stage outcomes,
evidence, findings, decisions, skips, waivers, and Component drift state.

**Outputs:** Approved Delivery Stage, terminal Run outcome, and a clear boundary
before developer-owned Git actions.

- **FS-DELIVERY-001:** Delivery summarizes requested and delivered outcomes,
  scope differences, Requirement and Component changes, implementation paths,
  evidence, test changes, findings, residual risk, skips, waivers, and omitted
  Stages.
- **FS-DELIVERY-002:** Delivery references detailed Stage material rather than
  duplicating every recorded event.
- **FS-DELIVERY-003:** The work outcome is independently assessed as `achieved`,
  `partially_achieved`, or `not_achieved`.
- **FS-DELIVERY-004:** Delivery approval accepts the truthfulness and closure of
  the record; it does not turn missing, failed, skipped, waived, uncertain, or
  unverified work into a pass.
- **FS-DELIVERY-005:** After approval is recorded by the developer or instructed
  agent, completing the Delivery Stage shall atomically mark the Stage
  `completed`, mark the Run `delivered`, and clear its local selection pointer.
  No separate Run-delivery operation is required. Rejection leaves the Delivery
  Stage and Run active with the reason and next action.
- **FS-DELIVERY-006:** Delivery can be approved with open findings when their
  consequences remain visible.
- **FS-DELIVERY-007:** AEGIS stops before commit, push, tag, merge, pull request,
  or any other outward-facing Git operation and does not inspect or preflight
  those operations.

## 7. Durable Run and Stage behavior

**Implements:** `PR-SNAPSHOT`, `PR-ART`, `PR-STATE`, `PR-REPORT`

### 7.1 Run summary

- **FS-DURABLE-001:** Each Run has one summary containing identity, ticket,
  intent, current scope, relevant execution instruction, scope-change log, Stage
  summary, change attribution, current handoff, and terminal outcome.
- **FS-DURABLE-002:** The Run summary is the current-state pointer for the Run
  and does not duplicate full Stage content.
- **FS-DURABLE-003:** The Run summary is updated after the relevant Stage file so
  interruption cannot advertise unpublished Stage state.

### 7.2 Stage files as snapshots

- **FS-DURABLE-004:** Each canonical Stage file is the durable saved snapshot
  for that Stage.
- **FS-DURABLE-005:** Stage state is saved at Stage completion and whenever a
  session pauses with work that another session must resume.
- **FS-DURABLE-006:** A later session can continue from the Run summary, current
  Stage file, referenced project artifacts, and Attachments without chat
  history.
- **FS-DURABLE-007:** A Stage correction appends an event describing what
  changed, why, when, and by which actor.
- **FS-DURABLE-008:** Evidence, findings, decisions, skips, and waivers are
  distinct entries inside their owning Stage file. Ordinary factual context and
  handoff information are mutable Stage sections, not append-only entry types.
- **FS-DURABLE-009:** Attachments hold only large or raw supporting material.
  They never hold the only copy of an outcome, finding, decision, or next action.

### 7.3 Atomic and interrupted publication

- **FS-DURABLE-010:** New project artifacts and Attachments are published before
  a Stage references them; the Stage is published before the Run summary.
- **FS-DURABLE-011:** An interrupted write leaves either the earlier complete
  artifact or the later complete artifact, never a partial file presented as
  valid.
- **FS-DURABLE-012:** Malformed or unreadable state is preserved and produces a
  structured, path-specific error.
- **FS-DURABLE-013:** Recovery does not invent successful publication, evidence,
  approval, or Stage completion.

## 8. Scope evolution, approvals, and escape hatches

**Implements:** `PR-EVOL`, `PR-ROLE`, `PR-ESCAPE`, `PR-DELIVERY`

### 8.1 Scope evolution

- **FS-SCOPECHANGE-001:** The developer or instructed agent can revise the
  interpretation, scope, Requirements, design, or profile of an active Run.
- **FS-SCOPECHANGE-002:** The Run scope-change log preserves the earlier
  interpretation and records the new interpretation, actor, reason, time, and
  affected artifacts.
- **FS-SCOPECHANGE-003:** After a scope change, AEGIS identifies earlier Stages,
  evidence, project artifacts, and Validation conclusions requiring review.
- **FS-SCOPECHANGE-004:** Affected completed Stages can be revisited without
  restarting the Run or erasing earlier events.
- **FS-SCOPECHANGE-005:** Work outside revised scope remains visible until the
  developer decides to retain, remove, or handle it separately.

### 8.2 Decisions

- **FS-APPROVAL-001:** A workflow decision is recorded in the Stage that owns
  its target.
- **FS-APPROVAL-002:** A decision identifies its value, actor, target, reason or
  conditions, and time.
- **FS-APPROVAL-003:** Decision value is `approved`, `rejected`, or
  `exception_approved`. An exception decision requires a mandatory reason and
  records the expectation that does not apply and the resulting alternative.
- **FS-APPROVAL-004:** Earlier decisions remain in Stage history. A later
  approval states what changed since rejection. A decision recorded by an
  instructed AI agent has the same workflow effect as one entered by the
  developer and identifies the agent as actor.
- **FS-APPROVAL-005:** A decision is not a cryptographic identity guarantee and
  is not described as a security control. `exception_approved` never means
  `passed`.

### 8.3 Skips and waivers

- **FS-ESCAPE-001:** Every operation that can otherwise trap work offers an
  escape action usable by the developer or instructed agent.
- **FS-ESCAPE-002:** A skip identifies the Stage, actor, mandatory reason, time,
  and effect on the Run.
- **FS-ESCAPE-003:** A waiver identifies the finding or expectation, actor,
  mandatory reason, time, and accepted consequence.
- **FS-ESCAPE-004:** A skip is unavailable after the relevant work has already
  been applied.
- **FS-ESCAPE-005:** Skipped and waived work is never represented as passed and
  remains visible through Delivery.
- **FS-ESCAPE-006:** An omitted Stage is distinguished from a skipped Stage and
  requires no escape approval.

## 9. Evidence, findings, and command outcomes

**Implements:** `PR-TRACE`, `PR-RED`, `PR-INT`, `PR-CONFIG`, `PR-REPORT`

### 9.1 Evidence

- **FS-EVIDENCE-001:** Evidence is recorded in the Stage that produced or
  evaluated it.
- **FS-EVIDENCE-002:** Automated evidence records the named command or selector,
  working directory, time, operational outcome, concise result, relevant tests,
  and Attachment reference when raw output is retained.
- **FS-EVIDENCE-003:** Manual evidence records actor, procedure, expected
  observation, actual observation, and time.
- **FS-EVIDENCE-004:** Earlier evidence remains visible after a retry or later
  superseding result.
- **FS-EVIDENCE-005:** Human-readable and machine-readable views communicate the
  same evidence outcome.

### 9.2 Command outcomes

| Outcome | Meaning |
|---|---|
| `passed` | The command completed with its configured successful exit status. |
| `failed` | The command completed with a configured failing exit status. |
| `timed_out` | AEGIS ended the command after its configured nonzero timeout. |
| `cancelled` | The operator or instructed agent cancelled the command. |
| `launch_error` | The command could not be started. |

- **FS-RESULT-001:** `failed` is used only when a command actually completed with
  a failing status.
- **FS-RESULT-002:** `timed_out`, `cancelled`, and `launch_error` leave the test,
  lint, or audit conclusion unknown; they are neither pass nor completed fail.
- **FS-RESULT-003:** Each non-passing outcome records its actual operational
  reason and produces an advisory finding.
- **FS-RESULT-004:** Retrying a command appends evidence and does not erase the
  earlier attempt.
- **FS-RESULT-005:** Command cancellation is a recorded escape action and does
  not trap the Run.

### 9.3 Findings

- **FS-FINDING-001:** A finding records a stable Stage-local label, severity,
  factual observation, consequence, and disposition.
- **FS-FINDING-002:** Disposition is `open`, `resolved`, `accepted`, `waived`, or
  `not_applicable`.
- **FS-FINDING-003:** Disposition changes append reasoning and do not rewrite the
  original observation.
- **FS-FINDING-004:** Findings report conditions and recommended action but do
  not grant or deny permission under shipped policy.

## 10. Requirements, Components, tests, and traceability

**Implements:** `PR-REQ`, `PR-COMP`, `PR-TRACE`, `PR-ADOPT`

### 10.1 Project artifacts

- **FS-PROJECT-001:** Requirements, optional Specifications, Components, and
  executable tests are project-owned data rather than Run metadata.
- **FS-PROJECT-002:** Requirements and Components remain human-readable and
  version-control friendly without requiring the creating host or model.
- **FS-PROJECT-003:** Tests are executable project files directly linked from
  Requirements and Components.
- **FS-PROJECT-004:** A Requirement directly records its impacted files and real
  test links or manual confirmation method.
- **FS-PROJECT-005:** A Component directly records its files, Requirements, and
  relevant real tests.
- **FS-PROJECT-006:** Requirements, Specifications, Components, and their
  traceability contain only current authoritative project knowledge. Updating
  them replaces their current content; removing them deletes them without a
  retired state, tombstone, superseded copy, or embedded change history.
- **FS-PROJECT-007:** Deleting a Requirement atomically deletes its optional
  Specification and removes references to it from current Component documents.
  It does not implicitly delete executable source or test files.
- **FS-PROJECT-008:** Deleting a Specification atomically clears its reference
  from the Requirement. Deleting a Component removes its documentation without
  implicitly deleting its Requirements, source files, or tests.
- **FS-PROJECT-009:** The owning Run records that a project artifact was created,
  updated, or deleted. Project artifacts do not duplicate that Run history or
  provenance.

### 10.2 Components

- **FS-COMP-001:** Every governed functional or implementation domain has a
  Component document identifying its purpose, boundary, interfaces,
  dependencies, files and roles, Requirements, tests, known gaps, and drift
  status.
- **FS-COMP-002:** Component documentation is concise enough to be the primary
  Intake context before bounded source inspection.
- **FS-COMP-003:** Behavior, interface, dependency, or file-membership changes
  trigger drift review.
- **FS-COMP-004:** Missing or stale Component documentation produces a finding
  and work item but does not block the Run.

### 10.3 Traceability and impacted selection

- **FS-TRACE-001:** AEGIS computes `Requirement -> impacted files -> real tests`
  from Requirement and Component artifacts.
- **FS-TRACE-002:** Every automated Requirement has at least one happy-path test
  unless justified manual verification applies.
- **FS-TRACE-003:** Every linked test identifies the implementation files it
  covers and at least one Requirement.
- **FS-TRACE-004:** Missing paths, dangling links, and incomplete coverage
  produce findings and backlog information rather than blocking work.
- **FS-TRACE-005:** A changed covered file selects all linked tests across all
  affected Requirements.
- **FS-TRACE-006:** AEGIS computes cross-file consistency and impacted selection
  without requiring the whole register in model context.

## 11. Red-before-green and test integrity

**Implements:** `PR-RED`, `PR-INT`, `PR-ZONE`

- **FS-INTEGRITY-001:** Check records actual red evidence and exact-byte SHA-256
  fingerprints of relevant test files before implementation.
- **FS-INTEGRITY-002:** Implementation or Validation records current
  fingerprints and compares them with the red fingerprints.
- **FS-INTEGRITY-003:** Every changed test between red and green is named in the
  Stage and Delivery findings.
- **FS-INTEGRITY-004:** The red witness remains visible after a test correction,
  retry, or green result.
- **FS-INTEGRITY-005:** Test-change detection depends on recorded content, not on
  host hooks, editor integration, or the tool used to edit the test.
- **FS-INTEGRITY-006:** Detection is active without project configuration and
  never prevents the edit.
- **FS-INTEGRITY-007:** Repository comparison around Check similarly exposes
  implementation changes made during that Stage without refusing or reverting
  them.
- **FS-INTEGRITY-008:** Optional preventive write zones can be provided as
  explicitly selected strict policy, remain host-specific, and ship disabled.

## 12. Resume and abandonment

**Implements:** `PR-SNAPSHOT`, `PR-ESCAPE`, `PR-STATE`, `PR-COLLAB`

### 12.1 Resume

- **FS-RESUME-001:** A later human or AI session reads the Run summary and
  current Stage before taking a Run-scoped action.
- **FS-RESUME-002:** Resume identifies the current scope, completed and open
  Stage work, linked project artifacts, evidence, findings, decisions, and next
  action without re-deriving them from chat.
- **FS-RESUME-003:** Resume works on another supported computer, platform, model,
  or host from the branch's repository state.
- **FS-RESUME-004:** A missing or unreadable reference produces a finding or
  structured error and does not cause AEGIS to invent replacement state.

### 12.2 Normal abandonment

- **FS-ABANDON-001:** Ending an active Run without Delivery is a first-class
  `abandoned` outcome with actor, time, mandatory reason, last useful state, and
  remaining work.
- **FS-ABANDON-002:** Normal abandonment records the terminal outcome in the Run
  summary and the stopping context in the current Stage file, then clears the
  local pointer when it still selects that Run.
- **FS-ABANDON-003:** Abandonment does not delete project changes, project
  artifacts, evidence, findings, or Stage history.

### 12.3 Exceptional abandonment

- **FS-ABANDON-004:** If the Run summary or directory cannot be safely updated,
  AEGIS can create an exceptional sibling abandonment record outside that Run
  directory.
- **FS-ABANDON-005:** The exceptional record identifies the Run, actor, time,
  reason, last known state, unreadable paths, and diagnostics.
- **FS-ABANDON-006:** AEGIS preserves unreadable bytes and does not overwrite
  them to manufacture a normal terminal state.

## 13. Collaboration and post-integration validation

**Implements:** `PR-COLLAB`, `PR-RUN`, `PR-REQ`, `PR-STATE`

- **FS-COLLAB-001:** Durable workflow state needed for resume and audit lives in
  the repository and branch, not a server, shared database, user-home file,
  required machine cache, or worktree-external scratch.
- **FS-COLLAB-002:** Independently created Runs, Requirements, Components,
  Adoptions, and Attachments use collision-resistant independent identities.
- **FS-COLLAB-003:** Normal work modifies no shared identifier counter, global
  registry, or durable selected-context pointer. The local working-context
  pointer is excluded from version control and never merged across branches.
- **FS-COLLAB-004:** Independent work on separate branches does not conflict
  merely because each developer created AEGIS artifacts.
- **FS-COLLAB-005:** Concurrent edits to the same Requirement, Component, test,
  Run, or Stage remain genuine source-control overlap visible to the developer.
- **FS-COLLAB-006:** After integration, `trace-validate` reports duplicate
  identities, missing targets, broken traceability, conflicting Component
  membership, and diverged coverage.
- **FS-COLLAB-007:** Post-integration trace validation is advisory and fixed
  forward; AEGIS does not silently select a branch winner.

## 14. WAEGIS lifecycle

**Implements:** `PR-WAEGIS`, `PR-PAYLOAD`, `PR-DEFAULT`, `PR-POSTURE`

### 14.1 Installation

- **FS-INSTALL-001:** WAEGIS targets a new or existing project directory.
- **FS-INSTALL-002:** Before its first write, WAEGIS previews every file and
  repository-state change it intends to make.
- **FS-INSTALL-003:** Dry-run preview makes no target change.
- **FS-INSTALL-004:** Installation writes require operator authorization after
  preview.
- **FS-INSTALL-005:** For a non-Git target, WAEGIS offers local `git init` after
  preview and authorization. Declining leaves the target unchanged.
- **FS-INSTALL-006:** Except for authorized local initialization, WAEGIS does
  not stage, commit, branch, tag, merge, push, or create pull requests.
- **FS-INSTALL-007:** Installation separates replaceable payload files from
  repository-owned configuration, rules, Requirements, Components, tests,
  Adoptions, and Runs. It also configures the local context pointer to remain
  excluded from version control without treating that pointer as project data.
- **FS-INSTALL-008:** Installation does not require application source, runtime,
  build, test, packaging, or deployment code to call AEGIS.

### 14.2 Removal, upgrade, and optional repair

- **FS-REMOVE-001:** Removing the AEGIS payload leaves the target application
  and project-owned data intact and usable through the project's own toolchain.
- **FS-UPGRADE-001:** WAEGIS previews an upgrade, replaces payload-owned files
  wholesale, and preserves project-owned artifacts.
- **FS-UPGRADE-002:** Incompatible project-owned state is reported rather than
  silently rewritten or discarded.
- **FS-REPAIR-001:** Optional future diagnosis and repair can examine and
  restore payload-owned files without overwriting project-owned data.

## 15. Adoption workflow

**Implements:** `PR-ADOPT`, `PR-COMP`, `PR-TRACE`

- **FS-ADOPT-001:** Adoption is a separate reverse workflow for repositories
  with pre-existing software and tests.
- **FS-ADOPT-002:** One Adoption journal covers one Component or bounded area
  and is interruptible and resumable.
- **FS-ADOPT-003:** Adoption derives Component knowledge and Requirements from
  behavior actually implemented or demonstrated by existing tests.
- **FS-ADOPT-004:** Adoption directly links real existing tests, derived
  Requirements, and impacted implementation files.
- **FS-ADOPT-005:** Uncertain behavior, ownership, and coverage remain explicit
  gaps rather than invented completeness.
- **FS-ADOPT-006:** Adoption can complete, continue later, or be abandoned with
  its completed work and next action preserved.

## 16. Runtime, offline operation, and packages

**Implements:** `PR-SCOPE`, `PR-PLAT`, `PR-RUNTIME`, `PR-OFF`, `PR-MODEL`,
`PR-PKG`

### 16.1 Repository and supported project scope

- **FS-ENV-001:** AEGIS operates in a Git repository; WAEGIS can prepare a
  non-Git project through authorized local initialization.
- **FS-ENV-002:** Initial verified topology is one project and AEGIS installation
  at the root of one Git repository.
- **FS-ENV-003:** A Git submodule is an independent repository boundary and can
  have its own AEGIS installation.
- **FS-ENV-004:** Initial verified target-project support is Python 3.12 with
  `pytest` and standard-library `unittest`.
- **FS-ENV-005:** Project commands and selectors remain language- and framework-
  independent in meaning so support can expand without changing the workflow.

### 16.2 Product runtime and platforms

- **FS-ENV-006:** Workflow states and outcomes have the same meaning on Windows
  11 or later and Ubuntu 22.04 LTS on x86-64.
- **FS-ENV-007:** Dependency-excluding editions operate with Python 3.11 or
  later and compatible Git.
- **FS-ENV-008:** Dependency-including editions contain a private Python 3.12
  runtime; complete WAEGIS editions can also contain private compatible Git.
- **FS-ENV-009:** Bundled tools do not replace or modify global Python, Git, or
  operating-system configuration.
- **FS-ENV-010:** AEGIS and WAEGIS runtime code depends only on the Python
  standard library.

### 16.3 Offline, local-model, and context behavior

- **FS-OFFLINE-001:** Every AEGIS and WAEGIS operation works without network
  access and initiates no telemetry, analytics, update check, or data transfer.
- **FS-OFFLINE-002:** Ticket text, source, configuration, artifacts, evidence,
  findings, and project data remain local.
- **FS-OFFLINE-003:** Network behavior of the selected agent host, model, project
  tool, or operating system is outside the AEGIS guarantee and is not attributed
  to AEGIS.
- **FS-OFFLINE-004:** The workflow is usable by a Qwen3.6-27B-class local model
  with 128K context without requiring that exact model.
- **FS-OFFLINE-005:** AEGIS computes cross-file consistency and returns concise
  results instead of requiring the whole register in model context.
- **FS-OFFLINE-006:** Context and output size can be measured for usability but
  never becomes a Stage or Delivery blocker.

### 16.4 Delivery editions

- **FS-PACKAGE-001:** Releases provide platform-specific archives for AEGIS
  without bundled dependencies, AEGIS with bundled dependencies, WAEGIS without
  bundled dependencies, and WAEGIS with bundled dependencies.
- **FS-PACKAGE-002:** Dependency-including archives require no runtime download
  before first use.
- **FS-PACKAGE-003:** Dependency-excluding archives document exact prerequisites
  and work offline once they are present.
- **FS-PACKAGE-004:** Bundled versions remain fixed within one product release
  and are refreshed only through another product update.
- **FS-PACKAGE-005:** A bundled runtime is assembled for its target platform and
  is not a copied machine-specific virtual environment.

## 17. Human and machine interfaces

**Implements:** `PR-PROTO`, `PR-ENC`, `PR-HOST`, `PR-MODEL`

- **FS-INTERFACE-001:** Every operation communicates its action, selected Run,
  resulting state, evidence, findings, and available next actions in human-
  readable form.
- **FS-INTERFACE-002:** A Run status view answers current Stage, known decisions,
  unresolved questions and findings, latest evidence, and valid next actions.
- **FS-INTERFACE-003:** Every command offers a machine-readable mode with a
  versioned schema and the same semantics as human output.
- **FS-INTERFACE-004:** Operator-producible input returns structured success or
  error rather than an unhandled traceback.
- **FS-INTERFACE-005:** Structured errors distinguish invalid input, missing
  prerequisites, repository-state problems, command outcomes, unsupported
  state, and internal failure.
- **FS-INTERFACE-006:** Default output is short, plain, stable, and points to
  durable detail rather than flooding model context.
- **FS-INTERFACE-007:** Every text read and write uses explicit encoding;
  product text has one canonical encoding.
- **FS-INTERFACE-008:** Supported text inputs tolerate UTF byte-order marks,
  CRLF, and Windows-1252 where the input contract permits general text.
- **FS-INTERFACE-009:** Undecodable input returns a path-specific structured
  error without silent replacement or corruption.
- **FS-INTERFACE-010:** Host adapters can change invocation, transport, and
  presentation but not Stage, approval, evidence, finding, or Delivery meaning.
- **FS-INTERFACE-011:** Supported host integrations target Claude Code, Codex,
  Qwen Code, OpenCode, and Pi under one workflow contract.
- **FS-INTERFACE-012:** Each AEGIS and WAEGIS operation has one canonical flat,
  lowercase, hyphen-separated CLI command. The CLI requires no nested resource
  and action grammar or alternate spellings.

## 18. Product boundaries and optional hardening

**Implements:** `PR-BOUND`, `PR-WORKFLOW`, `PR-INT`, `PR-ZONE`

- **FS-BOUND-001:** AEGIS is not a project-management system and does not own
  tickets, estimates, sprints, assignments, or schedules.
- **FS-BOUND-002:** AEGIS is not CI. Optional strict CI integration requires
  deliberate team configuration and ships disabled.
- **FS-BOUND-003:** AEGIS and WAEGIS stop before outward-facing Git actions and
  do not observe or preflight them.
- **FS-BOUND-004:** AEGIS is not a security product. Secret or protected-path
  assistance is a developer convenience and finding, not a control or guarantee.
- **FS-BOUND-005:** Optional write prevention is separate host-specific
  hardening, requires explicit team selection, and does not replace default
  detection and reporting.

## 19. Functional acceptance scenarios

The Acceptance Plan turns these into executable or explicit manual
checks. At minimum, the applicable Product Requirements must be demonstrable
through these observable scenarios:

1. WAEGIS previews and installs a usable default payload and generated
   configuration into a clean Python 3.12 Git repository.
2. WAEGIS previews local initialization of a non-Git project and performs
   `git init` only after authorization.
3. A repository without detected tests selects `.agentic/tests/`; a repository
   with existing tests selects its detected test roots without moving them.
4. A full Run converts raw ticket text into approved Delivery through all eight
   Stages and their canonical files.
5. A short Run records Design as omitted while retaining Requirements,
   red-before-green, Validation, and truthful Delivery.
6. Intake reads relevant Components, Requirements, and real tests and reports
   stale or missing knowledge without blocking.
7. A dirty working tree does not block a Run and pre-existing changes are not
   attributed to it.
8. Multiple Runs coexist; an operation selects one without a shared durable
   context pointer or mutation of another Run.
9. Scope changes preserve the ticket and earlier interpretation and identify
   completed work needing reconsideration.
10. Another session on another supported computer or host resumes from
    `run.md`, the current Stage, and linked project artifacts without chat.
11. Check records actual red evidence and test fingerprints before
    implementation.
12. An implementation-file change during Check is reported without being
    refused or reverted.
13. A test changed between red and green is named in findings and Delivery while
    the edit remains permitted.
14. A covered implementation change selects all linked real tests, including
    tests linked through another Requirement.
15. Incomplete traceability selects the full suite and explains why.
16. Named test, lint, and repository-audit commands record independent advisory
    outcomes during Validation.
17. A timed-out, cancelled, or unlaunched command remains unknown rather than
    being represented as a test failure or pass; retry preserves both attempts.
18. Failed evidence can reach an approved `partially_achieved` or
    `not_achieved` Delivery without falsifying the outcome.
19. A skipped Stage, waived finding, and profile-omitted Stage remain distinct.
20. An agent instructed to complete the workflow records approvals and continues
    through Delivery without intermediate prompts.
21. Normal abandonment is recorded inside readable Run state; exceptional
    abandonment remains possible without overwriting unreadable Run state.
22. Interrupted publication retains one complete state and does not manufacture
    completion or success.
23. Human and machine output communicate the same state and outcomes, including
    findings and structured errors.
24. AEGIS and WAEGIS operate without network access and initiate no data
    transmission.
25. Removing the payload preserves the target application and project-owned
    configuration, Requirements, Components, tests, Adoptions, and Runs.
26. Updating a Requirement, Specification, Component, or traceability link
    replaces its current project content, while deleting one leaves no project
    retirement record or historical copy and remains visible in the owning Run.

## 20. Product-requirement traceability by functional area

| Functional area | Authoritative Product Requirement areas |
|---|---|
| Interaction and responsibility | `PR-ROLE`, `PR-WORKFLOW`, `PR-DEFAULT`, `PR-POSTURE` |
| Installed project configuration | `PR-CONFIG`, `PR-PAYLOAD`, `PR-DEFAULT` |
| Run lifecycle and context | `PR-RUN`, `PR-EVOL`, `PR-SNAPSHOT`, `PR-DELIVERY`, `PR-SUCCESS` |
| Stage behavior | `PR-WORKFLOW`, `PR-REQ`, `PR-COMP`, `PR-TRACE`, `PR-RED`, `PR-REPORT` |
| Durable state and resume | `PR-ART`, `PR-SNAPSHOT`, `PR-STATE`, `PR-COLLAB` |
| Evidence and integrity | `PR-TRACE`, `PR-RED`, `PR-INT`, `PR-ZONE`, `PR-CONFIG` |
| Findings, approvals, and escapes | `PR-ROLE`, `PR-ESCAPE`, `PR-DELIVERY` |
| Project Requirements and Components | `PR-REQ`, `PR-COMP`, `PR-TRACE` |
| Adoption | `PR-ADOPT` |
| Collaboration | `PR-COLLAB`, `PR-RUN`, `PR-STATE` |
| WAEGIS lifecycle | `PR-WAEGIS`, `PR-PAYLOAD`, `PR-POSTURE` |
| Runtime, platform, offline, and packaging | `PR-SCOPE`, `PR-PLAT`, `PR-RUNTIME`, `PR-OFF`, `PR-MODEL`, `PR-PKG` |
| Interfaces and hosts | `PR-PROTO`, `PR-ENC`, `PR-HOST` |
| Product boundaries | `PR-BOUND`, `PR-WORKFLOW`, `PR-INT`, `PR-ZONE` |

The CLI and Machine Protocol Contract exposes these behaviors, and the
Acceptance Plan defines their required proof. The next planning deliverable is
the Technical Architecture.
