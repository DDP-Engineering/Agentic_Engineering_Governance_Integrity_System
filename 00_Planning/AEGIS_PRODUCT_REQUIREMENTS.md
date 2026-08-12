<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Product Requirements Register

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-10

This document is the single authoritative register of product requirements for
the AEGIS product family. It defines what AEGIS and WAEGIS promise, the priority
of each promise, and its planning status. New product decisions are added here
before they are elaborated in downstream planning documents.

`AEGIS_FUNCTIONAL_SPECIFICATION.md` explains functional behavior and
`AEGIS_ARTIFACT_MODEL.md` records artifact-design decisions. Their `FS-*` and
`AM-*` identifiers are specification and design references, not additional
product requirements. If either document discovers a new product promise, that
promise shall first receive a `PR-*` identifier in this register.

Implementation details, schemas, concrete file layouts, and internal algorithms
remain in their relevant specification or design document.

---

## Requirements register governance

### Requirement identity

- Every authoritative product requirement has exactly one stable `PR-*`
  identifier in this document.
- Requirement meaning is owned by the complete text associated with that
  identifier. Summaries and downstream references do not replace it.
- A requirement is changed here before dependent specifications, artifact
  decisions, templates, acceptance criteria, or implementation are changed.
- This register contains only the current product definition. A changed
  requirement is updated directly; a removed requirement is deleted together
  with its dependent references. Version control, rather than this register,
  provides document history.

### Priority vocabulary

| Priority | Meaning |
|---|---|
| **Must** | Required for the first usable version 1 release. |
| **Should** | Intended product capability that may follow the first usable release and must be reported as deferred until delivered. |
| **Could** | Optional expansion that is not part of the initial release commitment. |

### Status vocabulary

| Status | Meaning |
|---|---|
| **Proposed** | Under consideration and not yet part of the accepted product definition. |
| **Accepted** | Part of the current product definition. |

All requirements listed below have status **Accepted** unless an individual
entry explicitly states another status. Section 13 contains no unresolved
product decisions at this time.

### Requirement priority register

Numeric entries are the three-digit suffixes belonging to the prefix in the
first column. For example, `001-003` in the `PR-ROLE` row represents
`PR-ROLE-001`, `PR-ROLE-002`, and `PR-ROLE-003`.

| Requirement area | Must | Should | Could |
|---|---|---|---|
| `PR-ROLE` | `001-007` | — | — |
| `PR-WORKFLOW` | `001-008` | — | — |
| `PR-RUN` | `001-007` | — | — |
| `PR-EVOL` | `001-005` | — | — |
| `PR-SNAPSHOT` | `001-004` | — | — |
| `PR-REPORT` | `001-003` | — | — |
| `PR-DELIVERY` | `001-004` | — | — |
| `PR-ART` | `001-004` | — | — |
| `PR-REQ` | `001, 003-004, 007-009` | `002, 005-006` | — |
| `PR-ADOPT` | — | `001-006` | — |
| `PR-DEFAULT` | `001-006` | — | — |
| `PR-POSTURE` | `001-006` | — | — |
| `PR-ESCAPE` | `001-010` | — | — |
| `PR-SUCCESS` | `001-005` | `006` | — |
| `PR-WAEGIS` | `001-002, 005-007` | `004` | `003` |
| `PR-SCOPE` | `001-009` | — | — |
| `PR-CONFIG` | `001-013` | — | — |
| `PR-PLAT` | `001-004` | — | — |
| `PR-RUNTIME` | `001-007` | — | — |
| `PR-OFF` | `001-006, 008-009` | `007` | — |
| `PR-MODEL` | `001-005` | — | — |
| `PR-PKG` | `001-009` | — | — |
| `PR-COMP` | `001-004` | — | — |
| `PR-TRACE` | `001-016` | — | — |
| `PR-RED` | `001-005` | — | — |
| `PR-INT` | `001-006` | — | `007` |
| `PR-ZONE` | `001-007` | — | — |
| `PR-COLLAB` | `001-008, 011` | `009-010` | — |
| `PR-PROTO` | `001-006` | — | — |
| `PR-ENC` | `001-004` | — | — |
| `PR-STATE` | `001-003` | — | — |
| `PR-HOST` | `003-004` | `001-002` | — |
| `PR-PAYLOAD` | `001-002, 004-005` | `003` | — |
| `PR-BOUND` | `001, 003-006` | — | `002` |

| Priority | Requirement count |
|---|---:|
| Must | 206 |
| Should | 17 |
| Could | 3 |
| **Total** | **226** |

This priority register is authoritative. `AEGIS_RELEASE_SCOPE.md` may present
the same information as a release-oriented view but shall not assign a
different priority or redefine requirement meaning.

---

## 1. Product scope

AEGIS v1 is defined by the requirements in this document. The product version
starts at **1**.

The initial product scope includes:

- the AEGIS governance payload used inside a target repository;
- the WAEGIS operator tool used to manage that payload;
- a workflow that assists human developers and guides AI agents;
- local audit evidence that records what work was requested, performed, and
  verified;
- offline operation on supported Windows and Linux platforms; and
- self-contained delivery packages suitable for offline use.

---

## 2. Product vision

**You paste the text of a ticket. AEGIS walks the agent from there to a
delivered, traceable change and makes it impossible for the agent to cheat its
way to green without you seeing it.**

That is the whole product.

For a human developer, **AEGIS is an assistant**. It removes bookkeeping,
answers questions such as "What do I have to retest after this change?", and
leaves an audit trail the developer would otherwise have to assemble by hand.

For an AI agent, **AEGIS is a guide**. It provides enough structure for the
agent to work on a real codebase without inventing scope. It also removes the
value of changing a test merely to make an implementation appear correct,
because changes to the evidence are made visible in the report.

> **AEGIS must never be the reason work does not get done, and it must never
> let work be recorded as done when it was not.**

Both principles are satisfied through the same operating posture:
**AEGIS records, compares, and reports. It does not prevent.**

### 2.1 Roles and responsibility

AEGIS defines responsibilities rather than requiring different people for each
role. In normal individual use, the developer is also the reviewer and WAEGIS
operator.

- **PR-ROLE-001:** The developer shall own scope, approvals, exception decisions, the
  final interpretation of findings, and every outward-facing Git action.
- **PR-ROLE-002:** When the developer instructs an AI agent to complete the Run
  without intermediate prompts, the agent shall be able to perform the workflow,
  record decisions and approvals, and continue through Delivery as the
  developer's representative.
- **PR-ROLE-003:** A workflow decision shall record the decision, actor, reason,
  and time. A decision recorded by an instructed AI agent shall have the same
  workflow effect as one entered directly by the developer.
- **PR-ROLE-004:** The AI agent shall perform workflow work, maintain artifacts,
  run checks, and prepare findings and reports according to the developer's
  instructions.
- **PR-ROLE-005:** Review shall remain a developer responsibility rather than a
  separate required persona. The same developer may review and approve the
  completed work.
- **PR-ROLE-006:** The operator shall install and maintain AEGIS through WAEGIS.
  The operator will usually be the same developer, but the responsibility shall
  remain explicit.
- **PR-ROLE-007:** AEGIS is designed primarily to guide AI-agent work, while
  preserving a complete human-operated path for developers who choose to run
  the workflow without an AI agent.

### 2.2 AEGIS run

One AEGIS run transforms ticket text into a delivered, traceable change:

| # | Stage | Input | Output |
|---|---|---|---|
| 1 | **Intake** | Ticket text | The request restated and the affected part of the repository identified. |
| 2 | **Alignment** | Restated request and initial scope | What will be done, what will not be done, and any open questions. This is the inexpensive point at which to correct course. |
| 3 | **Requirement** | Agreed scope | One requirement per behavior, with its verification method. A specification is added when the requirement alone is not sufficient to implement the behavior. |
| 4 | **Design** | Requirements | A concise solution design that cites the requirements it satisfies. |
| 5 | **Check** | Approved design | Failing tests, recorded as red evidence before implementation begins. |
| 6 | **Implementation** | Red tests | Implementation changes that make the tests pass. If a recorded test changes during this stage, the report makes that change visible. |
| 7 | **Validation** | Green tests and implementation changes | The complete impacted regression set is selected and rerun. The full test suite is used when the impacted set cannot be established safely. |
| 8 | **Delivery** | Requirements, design, changes, and evidence | An approved delivery report. An instructed AI agent may record the approval and complete Delivery without another prompt. AEGIS stops; the developer remains responsible for committing the work. |

- **PR-WORKFLOW-001:** The input to a run shall be the ticket text supplied by
  the developer. AEGIS shall not require the developer to convert it into a
  scope statement, task breakdown, or requirement list before Intake.
- **PR-WORKFLOW-002:** AEGIS shall derive the initial scope and requirements
  through its workflow rather than requiring the developer to prepare them in
  advance.
- **PR-WORKFLOW-003:** A run shall use the eight stages in the table above. Each
  stage shall provide a written, self-contained instruction that a human
  operator or AI agent can follow without reconstructing the workflow contract.
  Reading a stage shall return that instruction together with its current state.
- **PR-WORKFLOW-004:** Alignment shall let the developer correct scope and
  resolve open questions before implementation code is written.
- **PR-WORKFLOW-005:** The developer shall be able to choose a proportional
  short path for small fixes and changes. The short path shall retain truthful
  evidence while reducing unnecessary ceremony.
- **PR-WORKFLOW-006:** AEGIS shall end its workflow at an approved Delivery
  report. An AI agent instructed to complete the workflow may record that
  approval without another prompt. Commit, push, tag, merge, and pull-request
  operations are outside AEGIS scope and remain under the developer's direct
  control.
- **PR-WORKFLOW-007:** AEGIS shall not inspect, guard, or preflight an
  outward-facing Git operation. Read-only local Git inspection used to build
  traceability or integrity evidence is permitted, but AEGIS shall not observe
  or interfere with publication and integration commands.
- **PR-WORKFLOW-008:** Every stage shall be resumable from recorded repository
  state. A later session, on another supported computer and using another AI
  model, shall be able to continue without re-deriving completed work.

### 2.3 Run identity, change attribution, and working context

- **PR-RUN-001:** Each ticket shall be handled through a distinct run with its
  own collision-resistant identifier, workflow state, artifacts, evidence,
  findings, approvals, and outcome.
- **PR-RUN-002:** Multiple recorded runs, regardless of their progress or
  outcome, shall be able to coexist in the same repository and branch without
  their state or evidence being combined.
- **PR-RUN-003:** Each working copy shall have at most one run selected as its
  working context. Routine workflow operations shall use that selected run and
  shall not require its identifier to be repeated. Every operation and created
  artifact shall still be associated with the selected run explicitly in its
  result and durable record.
- **PR-RUN-004:** The developer or instructed agent shall be able to switch the
  selected working context. The previous run's latest durable Stage state shall
  remain its resume snapshot, and selecting another run shall not alter the
  first run's recorded state.
- **PR-RUN-005:** AEGIS shall record the repository state at the beginning of a
  run sufficiently to distinguish changes that already existed from changes
  first observed during the run.
- **PR-RUN-006:** An existing staged, unstaged, or untracked change shall not
  prevent a run from starting or continuing. Pre-existing changes shall remain
  visible and shall not be represented as work produced by the run.
- **PR-RUN-007:** When AEGIS cannot establish who or what produced a change, it
  shall report only the observed timing and state of that change rather than
  claim authorship it cannot prove.

### 2.4 Scope evolution

Software work may reveal information that was not available during Alignment.
The workflow must allow the agreed scope to evolve without silently rewriting
history or forcing a useful run to be abandoned and restarted.

- **PR-EVOL-001:** During an active run, the developer or instructed agent may
  revise the ticket interpretation, scope, requirements, or design.
- **PR-EVOL-002:** A revision shall preserve the original ticket text and the
  earlier recorded decision. It shall record what changed, why it changed, the
  actor, and when.
- **PR-EVOL-003:** After a revision, AEGIS shall identify completed stages,
  artifacts, evidence, and validation whose conclusions may need to be
  reconsidered.
- **PR-EVOL-004:** Scope evolution shall not require the run to restart or be
  abandoned. The developer or instructed agent shall be able to revisit the
  affected work or continue with the unresolved impact recorded as a finding.
- **PR-EVOL-005:** Work already applied that falls outside the revised scope
  shall remain visible. Its removal, retention, or later handling shall be a
  recorded developer decision rather than a silent deletion from the run.

### 2.5 Stage snapshots and delivery summary

The durable handoff between sessions is the stage snapshot, not the model's
conversation memory. The Delivery report is a concise final summary of those
records rather than the primary state store for the run.

- **PR-SNAPSHOT-001:** Every stage shall save a durable repository snapshot at
  completion and whenever a session hands unfinished work to a later session.
- **PR-SNAPSHOT-002:** A snapshot shall contain the stage's relevant inputs,
  decisions, created or updated artifacts, evidence, findings, unresolved
  questions, and next action.
- **PR-SNAPSHOT-003:** A later AI or human session shall be able to resume from
  the snapshot without reconstructing relevant state from conversation history
  or repeating completed analysis.
- **PR-SNAPSHOT-004:** Snapshots shall be independent of a particular model,
  agent host, computer, or user account and shall travel with the branch.
- **PR-REPORT-001:** Delivery shall produce a concise report summarizing the
  ticket intent, agreed scope, exclusions, requirements, implementation files,
  stage outcomes, red and green evidence, impacted validation, changed-test
  findings, skips, waivers, and unverified or uncertain work.
- **PR-REPORT-002:** The Delivery report shall reference durable stage evidence
  rather than duplicate every recorded detail.
- **PR-REPORT-003:** A developer shall be able to judge the delivered work from
  the report and referenced artifacts without reconstructing the run from chat
  history.

### 2.6 Meaning of Delivery

- **PR-DELIVERY-001:** Reaching Delivery shall mean that the run has a complete,
  developer-approved, truthful record and has reached a recorded workflow
  outcome. It shall not by itself mean that every check passed or that every
  intended behavior was achieved.
- **PR-DELIVERY-002:** Delivery approval shall accept the accuracy of the report
  and authorize closure of the AEGIS workflow. Approval shall not change a
  failed, skipped, waived, missing, uncertain, or unverified result into a pass.
  Completing the Delivery stage after approval shall also set the run outcome
  to `delivered`; no additional run-closing action shall be required.
- **PR-DELIVERY-003:** The Delivery report shall assess the intended work as
  `achieved`, `partially_achieved`, or `not_achieved`, independently of whether
  the report itself has been approved.
- **PR-DELIVERY-004:** A run may reach Delivery with findings or incomplete work
  when the developer approves that truthful outcome. Every unresolved item
  shall remain visible in the report and referenced evidence.

### 2.7 Human-readable artifact promise

- **PR-ART-001:** Requirements, specifications, component documentation, stage
  snapshots, evidence records, findings, and delivery reports shall be stored
  as repository artifacts.
- **PR-ART-002:** Durable artifacts shall be human-readable, version-control
  friendly, and meaningfully reviewable as text differences.
- **PR-ART-003:** Artifacts shall remain readable without the agent host or AI
  model that created them.
- **PR-ART-004:** Upgrading or removing the AEGIS payload shall preserve
  current project-owned artifacts and project-owned Run history and audit
  evidence unless the developer explicitly requests their removal.

### 2.8 Requirements model

- **PR-REQ-001:** One requirement shall describe exactly one behavior or
  function. Distinct behaviors shall be represented by distinct requirements.
- **PR-REQ-002:** EARS phrasing shall be recommended but not mandatory. Clear,
  self-contained prose shall be accepted when it communicates the requirement
  more effectively.
- **PR-REQ-003:** Requirement text shall be understandable and verifiable
  without external context. Ticket identifiers, run identifiers, and
  cross-references to other requirements shall not appear in the requirement
  statement itself. Ticket and run provenance shall remain in the owning Run,
  not in the project Requirement artifact.
- **PR-REQ-004:** A requirement shall state its verification method separately
  from the behavior being required.
- **PR-REQ-005:** A requirement may include an optional specification when the
  requirement alone is insufficient for implementation, such as when defining
  a format, protocol, or non-obvious algorithm.
- **PR-REQ-006:** Specifications shall use a common template while allowing the
  content needed by the behavior being specified.
- **PR-REQ-007:** A requirement shall have current lifecycle states for being
  drafted and being in force. A requirement that no longer belongs to the
  current project definition shall be deleted rather than retained in a
  retired, deprecated, superseded, or tombstone state.
- **PR-REQ-008:** Each requirement shall be stored as its own artifact.
  Independently created requirements shall use collision-resistant identifiers
  so work on separate branches does not collide merely because it was created
  concurrently.
- **PR-REQ-009:** Requirement priority shall use the vocabulary `Must`, `Should`,
  and `Could`.

### 2.9 Adoption workflow

Adoption is a separate, reverse-direction workflow for bringing an existing
repository under AEGIS. It starts from the software and tests that exist and
derives the documentation, requirements, and traceability that describe them.

- **PR-ADOPT-001:** AEGIS shall provide an adoption workflow for an existing
  repository that does not yet have complete AEGIS artifacts.
- **PR-ADOPT-002:** Adoption shall discover the repository's existing software
  components and document each discovered component using the component model
  and template.
- **PR-ADOPT-003:** Adoption shall derive requirements from behavior that is
  actually implemented and tested. It shall not replace observed behavior with
  behavior that is merely assumed or desired.
- **PR-ADOPT-004:** Adoption shall link existing tests to the derived
  requirements and populate the impacted-file coverage needed by the
  traceability model.
- **PR-ADOPT-005:** Adoption shall be incremental, interruptible, and resumable.
  It shall proceed one component at a time and may continue over as many
  sessions as necessary.
- **PR-ADOPT-006:** Adoption shall record behavior, coverage, or relationships
  it could not derive as explicit gaps. It shall not invent requirements or
  links to create the appearance of complete adoption.

### 2.10 First-run experience

A developer who has just installed AEGIS has read nothing and configured
nothing. What they receive must already be the product:

- **Install, then work.** There is no policy file to complete, mode to select,
  or path pattern to define before AEGIS becomes useful. The shipped defaults
  are the intended experience rather than a starting point that must be tuned.
- **Nothing is refused.** AEGIS does not refuse an edit, command, or stage
  closure. A first-time user cannot be stopped by a rule they have not yet
  learned.
- **Value arrives in the report.** AEGIS provides value through evidence and
  findings the developer reads, not through permissions it denies.

- **PR-DEFAULT-001:** AEGIS shall provide its complete core workflow and
  reporting value immediately after installation without mandatory project
  configuration.
- **PR-DEFAULT-002:** Default operation shall not require the developer to
  create a policy file, choose an operating mode, or define file globs.
- **PR-DEFAULT-003:** No default capability shall reject an edit, command, or
  stage closure.
- **PR-DEFAULT-004:** Findings shall be recorded and reported without being
  represented as permissions that AEGIS grants or denies.
- **PR-DEFAULT-005:** A capability that adds enforcement or stricter policy
  shall be optional, shall be disabled by default, and shall not be required to
  obtain the product's core value.
- **PR-DEFAULT-006:** Configuration may add only the strictness that a team has
  deliberately selected. Configuration shall not determine whether AEGIS is
  functional or whether its core value is available.

Any capability that must be enabled before it becomes useful is not part of the
default product experience. It is an option for a team that has deliberately
chosen additional policy, and it ships disabled.

### 2.11 Product principles

- **Assist the human.** Reduce manual governance and traceability work without
  taking ownership of engineering decisions away from the developer.
- **Guide the agent.** Provide explicit scope, workflow, and evidence so an AI
  agent does not have to invent missing project rules.
- **Remain non-blocking.** Findings must be visible, but AEGIS itself must not
  prevent legitimate development work from continuing.
- **Report truthfully.** Skipped, incomplete, changed, failed, or missing work
  must never be represented as completed or passed.
- **Preserve evidence.** The audit trail must allow a human to understand what
  was requested, what was changed, what was tested, and what remains uncertain.

### 2.12 Development posture

- **PR-POSTURE-001:** AEGIS shall assist established software-development work,
  including features, changes, quick fixes, and bug fixes. It shall not require
  a team to replace its existing development process with a process invented by
  AEGIS.
- **PR-POSTURE-002:** AEGIS shall not block development. Every gate, check,
  invariant, and audit result shall produce a finding for the developer to
  review. None shall refuse an action or prevent a stage from closing.
- **PR-POSTURE-003:** AEGIS shall keep its workflow effort proportional to the
  work. A small fix shall require a small amount of process.
- **PR-POSTURE-004:** AEGIS shall be removable. Removing the AEGIS payload from
  a repository shall leave the repository usable and shall not delete or damage
  artifacts owned by the developer or project.
- **PR-POSTURE-005:** Installing AEGIS shall not make the target application
  depend on AEGIS in order to build, run, test, package, deploy, or operate.
- **PR-POSTURE-006:** When AEGIS is not being invoked, its presence shall not
  alter the target application's runtime behavior or require application code
  to import or call AEGIS.

### 2.13 Escape hatches and truthful outcomes

No workflow stage shall trap a run. When work cannot or should not continue
through the normal path, the developer must have an honest way to continue or
end it.

- **PR-ESCAPE-001:** Every operation capable of stopping work shall have an
  escape hatch.
- **PR-ESCAPE-002:** A developer shall be able to skip any of the six stages
  between the workflow terminals: Alignment, Requirement, Design, Check,
  Implementation, and Validation. Intake and Delivery remain the recorded
  intent and outcome of a delivered run.
- **PR-ESCAPE-003:** A run that ends without delivery shall use abandonment as a
  first-class, recorded outcome with a mandatory reason. It shall not be erased,
  emptied, or represented as delivered.
- **PR-ESCAPE-004:** A skipped stage shall have a distinct `skipped` state. It
  shall remain distinguishable from a stage that was not included in the
  selected run profile.
- **PR-ESCAPE-005:** A skipped stage shall not prevent the run from reaching
  Delivery. The Delivery report shall retain and display the skip.
- **PR-ESCAPE-006:** A stage whose work has already been applied shall not be
  eligible to be skipped. Applied work must remain represented by its actual
  recorded outcome.
- **PR-ESCAPE-007:** Every skip, waiver, or other escape hatch shall require a
  mandatory free-text reason. The actor, reason, time, and resulting state shall
  be recorded in the audit trail. A non-skip, non-waiver exception shall be
  recorded as a decision with the value `exception_approved`.
- **PR-ESCAPE-008:** An AI agent instructed to complete the workflow may record
  and use an escape hatch without another developer prompt. The mandatory reason
  and truthful outcome requirements remain unchanged.
- **PR-ESCAPE-009:** A skipped or waived item shall be reported as `skipped` or
  `waived`, never as `passed`. Using an escape hatch shall never falsify the
  audit trail.
- **PR-ESCAPE-010:** Abandonment shall remain available when the run's own state
  is unreadable. AEGIS shall preserve the unreadable state as evidence and
  record the abandonment separately without claiming that the damaged run was
  successfully delivered or repaired.

### 2.14 Product success

AEGIS succeeds when it makes governed agent work easier to continue and easier
to trust without becoming an obstacle.

- **PR-SUCCESS-001:** A developer shall be able to install AEGIS and begin a run
  without first configuring policy or learning optional hardening features.
- **PR-SUCCESS-002:** A different AI session, model, computer, or human operator
  shall be able to resume work from repository snapshots without repeating
  completed stages.
- **PR-SUCCESS-003:** The developer shall be able to understand what was
  requested, changed, tested, skipped, waived, failed, or left uncertain from
  the durable artifacts and concise Delivery report.
- **PR-SUCCESS-004:** Missing or changed evidence shall remain visible and shall
  never be transformed into a successful result by presentation or omission.
- **PR-SUCCESS-005:** Impacted validation shall normally avoid running the full
  test suite while retaining an explicit full-suite fallback when traceability
  is insufficient.
- **PR-SUCCESS-006:** Installation, upgrade, removal, interruption, and
  cross-branch work shall preserve project-owned data and truthful history.

---

## 3. Products in the family

| Product | Role | Ships into a target repository? |
|---|---|---|
| **AEGIS** | The governance payload: the workflow, artifacts, and companion CLI used while engineering work is performed. | Yes. AEGIS is the payload delivered into the target repository. |
| **WAEGIS** | The operator wizard that contains an AEGIS payload, analyzes a repository, installs and upgrades the payload, and may provide optional diagnosis and repair. | No. WAEGIS remains an operator tool outside the target repository. |

The two products have distinct responsibilities. AEGIS governs and records
work inside a repository. WAEGIS manages the lifecycle of the AEGIS payload
from outside that repository.

### 3.1 WAEGIS lifecycle

- **PR-WAEGIS-001:** An operator shall be able to use WAEGIS to install AEGIS
  into a new or existing repository.
- **PR-WAEGIS-002:** Before an installation performs its first write, WAEGIS
  shall provide a dry-run preview of the files and repository state it would
  create, replace, or otherwise modify. The dry run itself shall not modify the
  target repository.
- **PR-WAEGIS-003:** Diagnosis and repair shall be an optional WAEGIS
  capability that is not included in the initial release. A later release may
  add installation-health checks and repair of product-owned payload files
  without overwriting repository-owned project data.
- **PR-WAEGIS-004:** An operator shall be able to use WAEGIS to upgrade a
  repository to a newer AEGIS payload without losing repository-owned rules,
  configuration, workflow state, evidence, or other project data.
- **PR-WAEGIS-005:** Payload-owned files and repository-owned project data shall
  remain strictly separated so installation, repair, and upgrade can identify
  what WAEGIS may replace.
- **PR-WAEGIS-006:** Except for repository initialization under PR-WAEGIS-007,
  WAEGIS shall not stage, commit, create or switch branches, tag, merge, push,
  or create pull requests. Repository review and every outward-facing or
  integration Git action shall remain under the operator's control.
- **PR-WAEGIS-007:** When the target is not a Git repository, WAEGIS shall offer
  local repository initialization with `git init`. The dry-run preview and
  operator authorization shall occur before initialization. This local setup is
  not an outward-facing Git action.

### 3.2 Target repository and language scope

- **PR-SCOPE-001:** AEGIS v1 shall operate on Git repositories. WAEGIS shall be
  able to prepare a non-Git project through the authorized initialization
  defined by PR-WAEGIS-007.
- **PR-SCOPE-002:** AEGIS shall be designed to support repositories across
  programming languages and test frameworks rather than impose the language or
  framework used to implement AEGIS itself.
- **PR-SCOPE-003:** Initial verified language support shall target Python 3.12,
  with Java, C++, and other language ecosystems as future expansion targets.
  Adding a language shall not change the core workflow contract.
- **PR-SCOPE-004:** AEGIS shall use the repository's own build and test tools
  through project-defined commands and selectors. It shall not require target
  projects to adopt a single AEGIS-specific test framework.
- **PR-SCOPE-005:** The workflow, artifacts, findings, and Delivery report shall
  retain the same meaning across supported languages and test frameworks.
- **PR-SCOPE-006:** The initial verified repository topology shall be one
  project governed by one AEGIS installation at the root of one Git repository.
- **PR-SCOPE-007:** Monorepositories and unregistered nested Git repositories
  shall not be included in the initial verified scope.
- **PR-SCOPE-008:** A Git submodule shall be treated as an independent
  repository boundary. The parent repository's AEGIS installation shall treat
  it as an external referenced repository; the submodule may have its own AEGIS
  installation and workflow state.
- **PR-SCOPE-009:** Initial verified test-framework support for Python 3.12
  shall include `pytest` and the Python standard library's `unittest`
  framework. Target repositories shall remain free to use other frameworks as
  unverified integrations through the project-defined command model.

### 3.3 Project integration and validation commands

- **PR-CONFIG-001:** WAEGIS shall generate a complete project integration
  configuration during installation so AEGIS is usable without requiring the
  developer to complete a configuration form before the first run.
- **PR-CONFIG-002:** Project configuration shall identify the repository-owned
  locations for Requirements, Components, tests, Adoption state, and Run state.
  These locations shall be relocatable without changing workflow meaning.
- **PR-CONFIG-003:** When no existing repository test root is detected, the
  shipped project configuration shall use `.agentic/tests/` as the default test
  root.
- **PR-CONFIG-004:** When WAEGIS confidently detects existing repository test
  roots, it shall configure AEGIS to use those roots rather than require tests
  to be moved into the shipped default location.
- **PR-CONFIG-005:** Project configuration shall support multiple test roots for
  repositories whose language, framework, or organization requires them.
- **PR-CONFIG-006:** AEGIS shall support uniquely named local validation
  commands categorized as tests, lints, or repository-specific audits.
- **PR-CONFIG-007:** WAEGIS shall record test and lint commands that it can
  detect confidently. When it cannot detect a command, AEGIS shall use an
  appropriate shipped adapter default and report the command it selected.
- **PR-CONFIG-008:** Each validation command shall support its own repository-
  relative working directory and optional execution timeout.
- **PR-CONFIG-009:** The shipped timeout value shall impose no automatic time
  limit. A developer or instructed agent shall still be able to cancel a
  running command through a recorded escape hatch.
- **PR-CONFIG-010:** AEGIS shall distinguish the command outcomes `passed`,
  `failed`, `timed_out`, `cancelled`, and `launch_error`.
- **PR-CONFIG-011:** A timed-out, cancelled, or unlaunched command shall leave
  the corresponding test, lint, or audit result unknown. It shall never be
  reported as passed or as a completed failing result. A retry shall preserve
  the earlier attempt as evidence.
- **PR-CONFIG-012:** Test, lint, and audit execution shall produce recorded
  evidence and findings. Their results shall remain advisory and shall not
  prevent stage closure or Delivery under the shipped defaults.
- **PR-CONFIG-013:** A project shall be able to add named repository-specific
  audits to Validation. An audit may use its own changed-file option so its work
  remains proportional to the Run.

---

## 4. Supported platforms

- **PR-PLAT-001:** AEGIS and WAEGIS shall support Microsoft Windows 11 and
  later Windows releases.
- **PR-PLAT-002:** AEGIS and WAEGIS shall support Linux, with Ubuntu 22.04 LTS
  as the initial reference distribution.
- **PR-PLAT-003:** Product behavior and recorded results shall be consistent
  across supported platforms. Workflow semantics, state transitions, findings,
  and report meaning shall be identical on Windows and Linux. Packaging, paths,
  and process-launch details may differ where required by the operating system
  but shall not change product meaning.
- **PR-PLAT-004:** Initial Windows and Ubuntu delivery packages shall target the
  x86-64 architecture, also known as AMD64.

### 4.1 Python runtime baseline

- **PR-RUNTIME-001:** The minimum supported system interpreter shall be Python
  3.12.
- **PR-RUNTIME-002:** AEGIS and WAEGIS source code shall remain compatible with
  the Python 3.12 release line.
- **PR-RUNTIME-003:** Compatibility validation shall include Python 3.12 on
  Windows 11 and Ubuntu 22.04 LTS.
- **PR-RUNTIME-004:** The first dependency-bundled editions shall include Python
  3.12. A later product release may move the bundled runtime while preserving
  the documented minimum system-interpreter contract.
- **PR-RUNTIME-005:** A bundled Python runtime shall be assembled separately
  for each supported platform. It shall not be implemented by copying a normal
  virtual environment, because such environments are not generally portable
  between locations or machines.
- **PR-RUNTIME-006:** Code shall not use syntax or standard-library behavior
  unavailable in Python 3.12.
- **PR-RUNTIME-007:** Runtime code for AEGIS and WAEGIS shall depend only on the
  Python standard library. Normal operation shall not require third-party Python
  packages.

---

## 5. Offline and self-contained operation

- **PR-OFF-001:** AEGIS and WAEGIS shall work fully offline. No product operation
  shall require network access.
- **PR-OFF-002:** Core product behavior shall not depend on hosted services,
  cloud accounts, remote APIs, or online package repositories.
- **PR-OFF-003:** Each product shall be self-contained to the greatest practical
  extent appropriate to its delivery edition. Templates and other product
  assets shall be included. External runtimes and tools may either be bundled
  or declared as prerequisites, depending on the edition.
- **PR-OFF-004:** A delivery edition that excludes external dependencies shall
  state its prerequisites explicitly. Those prerequisites shall be obtainable
  and installable for an offline environment.
- **PR-OFF-005:** Product data and audit evidence shall remain locally
  available and usable when the machine is disconnected from a network.
- **PR-OFF-006:** The offline guarantee applies to AEGIS and WAEGIS. A
  third-party agent host or model selected by the developer may use a network;
  supporting that host shall not represent it as an offline product.
- **PR-OFF-007:** A fully air-gapped workflow shall remain possible by combining
  AEGIS with an offline-capable agent host, a local model, and locally available
  project toolchains.
- **PR-OFF-008:** AEGIS and WAEGIS shall not transmit ticket text, repository
  content, source code, configuration, workflow artifacts, evidence, findings,
  or usage data over a network.
- **PR-OFF-009:** AEGIS and WAEGIS shall contain no telemetry, analytics,
  automatic update check, or other background communication. Network behavior
  of a separately selected agent host, model, project tool, or operating-system
  service remains outside the product guarantee defined by PR-OFF-006.

Offline capability is a core product property, not an optional operating mode.

### 5.1 Local-model and context constraints

- **PR-MODEL-001:** AEGIS shall be operable by a local open-weights model. The
  reference capability target shall be a Qwen3.6-27B-class model with a 128K
  context window.
- **PR-MODEL-002:** The reference model is a capability and context target, not
  a hosted service dependency. AEGIS shall not require that specific model or
  any network model endpoint.
- **PR-MODEL-003:** AEGIS shall manage its workflow context for practical
  usability so one stage of one task remains a coherent unit of model work.
  Context overhead shall be measured to improve the experience, not enforced as
  a limit that blocks or refuses work.
- **PR-MODEL-004:** AEGIS tooling shall compute cross-file consistency. The
  model shall read a bounded consistency report rather than load the complete
  requirement, component, evidence, or traceability register into its context.
- **PR-MODEL-005:** Agent-facing tool output shall use a short, plain, stable
  line format by default. Detailed or lengthy evidence may remain in repository
  artifacts with a useful summary and reference in interactive output. Output
  size shall not become a workflow gate.

Context overhead means the model context consumed by AEGIS itself: stage
instructions, snapshots, component summaries, requirement metadata, and tool
responses. It excludes the ticket and project source needed for the actual
engineering task. AEGIS may measure this overhead to improve usability, but no
fixed context quota is required for a run or stage to proceed.

---

## 6. Delivery packages

- **PR-PKG-001:** AEGIS and WAEGIS shall be distributed as complete release
  archives suitable for offline transfer and installation.
- **PR-PKG-002:** A delivery package may use a portable archive, such as ZIP,
  or an appropriate application archive or package for the target operating
  system.
- **PR-PKG-003:** Each release shall provide the following four delivery
  editions for each supported platform, producing eight platform-specific
  archives in the initial Windows and Ubuntu matrix:

  1. **AEGIS without external dependencies:** the AEGIS payload and its product
     assets, with external runtimes and tools declared as prerequisites and not
     included in the package.
  2. **AEGIS with external dependencies:** AEGIS plus a private Python runtime
     and the Git runtime required for repository inspection.
  3. **WAEGIS without external dependencies:** WAEGIS containing the AEGIS
     payload, with external runtimes and tools declared as prerequisites and
     not included in the package.
  4. **WAEGIS with external dependencies:** WAEGIS containing AEGIS, a private
     Python runtime, and a private Git distribution.

- **PR-PKG-004:** An edition that includes external dependencies shall be
  usable without downloading additional runtime components before first use.
- **PR-PKG-005:** An edition that excludes external dependencies shall contain
  an exact prerequisite list and shall operate offline once those prerequisites
  are present.
- **PR-PKG-006:** AEGIS and WAEGIS shall ship as platform-specific packages.
- **PR-PKG-007:** Bundled Python and Git runtimes shall remain private to the
  product package. They shall not replace, modify, or require installation into
  the operating system's global runtime or Git configuration.
- **PR-PKG-008:** Dependency-excluding editions shall require Python 3.12 and a
  compatible Git installation, with exact prerequisites documented in the
  package and checked by the product launcher.
- **PR-PKG-009:** Bundled Python and Git versions shall remain fixed within a
  released AEGIS or WAEGIS version. Dependency refreshes, including security and
  maintenance refreshes, shall be delivered only through a new product update.

The final archive format and exact bundled Git version remain design decisions.
The initial architecture, Python runtime, and dependency-refresh policy are
defined above.

---

## 7. Components

The component is AEGIS's unit for understanding and documenting software. A
component may contain one file or multiple files joined by a common
functionality or implementation domain.

- **PR-COMP-001:** AEGIS shall model software as components. Each component
  shall identify the files that implement its common functionality or
  implementation domain.
- **PR-COMP-002:** Every component shall have documentation created from a
  common component template.
- **PR-COMP-003:** Component documentation shall provide the primary component
  context a session reads instead of repeatedly rereading the component's
  entire source. It shall therefore remain concise, current, and factually
  accurate. It shall be updated directly when the Component changes and deleted
  when the Component no longer belongs to the current project definition.
- **PR-COMP-004:** Component documentation shall be reviewed for drift whenever
  the component's behavior, public or internal interfaces, or file membership
  changes.

---

## 8. Traceability and impacted validation

- **PR-TRACE-001:** AEGIS shall maintain traceability from each requirement to
  its impacted implementation files and from those files to their tests:
  **requirement -> impacted files -> tests**. Traceability shall describe only
  current project relationships; updating or deleting a project artifact shall
  update or remove its dependent links rather than preserve historical links.
- **PR-TRACE-002:** Validation shall include the tests created or changed for
  the current requirement and every additional test associated with an
  implementation file affected by the change.
- **PR-TRACE-003:** AEGIS shall normally run the complete impacted test set
  instead of the full test suite, so validation remains fast enough for regular
  development work.
- **PR-TRACE-004:** When AEGIS cannot determine a safe and complete impacted
  test set, it shall select the full test suite and report why the fallback was
  necessary.
- **PR-TRACE-005:** The delivery report shall state which tests were selected,
  why they were selected, and whether validation used an impacted subset or the
  full test suite.
- **PR-TRACE-006:** Every requirement shall be linked to automated tests or
  explicitly categorized as manually tested, with a recorded reason, when
  automation cannot reasonably confirm the behavior.
- **PR-TRACE-007:** Automated verification shall include at least one happy-path
  test for each requirement unless the requirement is categorized as manually
  tested with a recorded reason.
- **PR-TRACE-008:** Every test shall be linked to at least one requirement.
- **PR-TRACE-009:** Every test shall define the implementation files or file set
  it covers.
- **PR-TRACE-010:** A change to a covered file shall select every linked test for
  impacted validation, including tests associated with other requirements.
- **PR-TRACE-011:** Missing links, incomplete coverage, and other traceability
  defects shall be reported as findings. An incomplete traceability register is
  a backlog to improve, not a reason to block work.
- **PR-TRACE-012:** Automated verification beyond the required happy path shall
  use a risk-based, proportional approach rather than a fixed number of tests or
  a mandatory quota for each test category.
- **PR-TRACE-013:** The risk assessment shall consider the likelihood and impact
  of failure, changed boundaries and interfaces, input variability, error
  handling, implementation complexity, and known regression history to the
  extent relevant to the change.
- **PR-TRACE-014:** Relevant boundary, edge, corner, negative, and failure-path
  tests shall be included when the assessed risk justifies them. Categories
  with no credible risk for the change shall not require ceremonial tests.
- **PR-TRACE-015:** A bug fix shall normally include a regression test that
  reproduces the reported defect before implementation. When that is not
  practical, manual verification or the recorded escape hatch shall apply.
- **PR-TRACE-016:** The run shall record the material risks covered by its tests
  and any known material risk intentionally left untested, with the reason.
  This record shall remain proportional to the size and risk of the work.

---

## 9. Test evidence, write zones, and integrity

### 9.1 Red before green

- **PR-RED-001:** AEGIS shall require recorded evidence that a test failed
  before implementation and passed after implementation before describing the
  requirement as having complete red-before-green evidence.
- **PR-RED-002:** A red result shall be captured from actual test execution and
  retained as evidence. A statement that a test was red shall not substitute
  for recorded execution evidence.
- **PR-RED-003:** Red-before-green evidence shall apply to the proportional
  short path as well as the full workflow, with reduced ceremony rather than
  reduced truthfulness.
- **PR-RED-004:** When red-before-green is genuinely inapplicable, the developer
  or instructed agent may record an `exception_approved` decision under
  PR-ESCAPE-007 and shall provide the mandatory reason and alternative
  confirmation method.
- **PR-RED-005:** Missing, skipped, or waived red-before-green evidence shall be
  visible in the Delivery report and shall never be rendered as passed. It
  shall produce a finding rather than block the run.

### 9.2 Write zones

AEGIS shall define the files that an agent is expected to change in each
workflow stage. In particular:

- during **Check**, tests may be created or changed, but implementation files
  are outside the intended write zone; and
- during **Implementation**, implementation files may be changed, but recorded
  tests are outside the intended write zone.

Changes outside these intended zones must not be invisible. The product must
make it possible for the developer to determine whether such a change was a
legitimate correction or an attempt to make the evidence fit the
implementation.

### 9.3 Test integrity: detected, not prevented

Editing a test instead of correcting the implementation destroys the value of
red-before-green. AEGIS does not address that shortcut by forbidding the edit.
Prevention would place a wall in front of an unconfigured first-time user,
would require host-specific integration, and could be bypassed by editing with
another tool.

AEGIS makes the change visible instead. Detection requires no setup, works
regardless of which editor or agent changed the file, and leaves the judgement
with the developer. A changed test may be a legitimate correction; AEGIS
records what happened without deciding the developer's conclusion.

- **PR-INT-001:** When a test is recorded red, AEGIS shall record a fingerprint
  of that test's content alongside the red result.
- **PR-INT-002:** When the same test is later recorded green, AEGIS shall compare
  its red and green fingerprints. The Delivery report shall identify every
  changed test by name.
- **PR-INT-003:** A changed-test report shall be a finding, not a blocker. AEGIS
  shall leave the judgement about a correction or improper change to the
  developer or instructed agent recording the decision.
- **PR-INT-004:** A recorded red result shall be immutable. Later evidence may
  supersede the failure as the current result, but shall never delete, replace,
  or retire the original red witness.
- **PR-INT-005:** Test-change detection shall be computed from recorded evidence
  and content. It shall not depend on hooks, the host agent application, the
  developer's editor, or the tool used to modify the test.
- **PR-INT-006:** Test-change detection shall require no configuration and shall
  be enabled by default.
- **PR-INT-007:** Stage-scoped prevention that refuses out-of-zone writes shall
  be available only as opt-in project hardening and shall ship disabled. It
  shall never be the mechanism on which test-integrity detection or core product
  value depends.

### 9.4 Check-stage repository comparison

Check-stage detection shall use Git, but it shall not rely on a plain
end-of-stage `git diff` alone.

- **PR-ZONE-001:** AEGIS shall detect implementation files changed during the
  Check stage by comparing the repository state at Check entry with its state
  at Check completion.
- **PR-ZONE-002:** At Check entry, AEGIS shall record a baseline containing the
  current `HEAD`, the index and working-tree state, untracked paths, and content
  fingerprints for known implementation files.
- **PR-ZONE-003:** At Check completion, AEGIS shall repeat the inspection and
  compare it with the recorded baseline. This comparison shall support a
  working tree that already contained changes when Check began.
- **PR-ZONE-004:** Git inspection shall account for staged changes, unstaged
  changes, untracked files, deletions, and renames. Machine-readable,
  NUL-delimited Git output shall be used so all valid repository paths can be
  handled safely.
- **PR-ZONE-005:** Every implementation path whose content or repository state
  changed during Check shall appear as an out-of-zone finding in the audit
  trail and delivery report.
- **PR-ZONE-006:** A change to `HEAD`, the active worktree, or the index during
  Check shall be recorded because it may invalidate the original baseline.
- **PR-ZONE-007:** Baseline inspection shall be read-only. AEGIS shall not stage,
  commit, reset, restore, or otherwise alter developer files or Git state while
  collecting integrity evidence.

Optional prevention may require adapters for individual agent applications.
Those adapters are separate hardening integrations; fingerprint-and-report
detection remains host-independent and non-blocking.

---

## 10. Multi-developer collaboration

AEGIS shall support multiple developers working on the same repository from
different computers and on different branches.

- **PR-COLLAB-001:** AEGIS shall support multiple developers working
  concurrently on separate branches and separate computers.
- **PR-COLLAB-002:** AEGIS shall require no server, shared database, or shared
  runtime. The repository and its branches shall be the only persistent store
  for workflow state and audit evidence.
- **PR-COLLAB-003:** A developer shall be able to create, resume, and audit work
  on one computer without access to state held by another developer's computer.
- **PR-COLLAB-004:** No durable AEGIS workflow state shall live in the user's
  home directory, a machine-local cache, or worktree-local scratch storage.
  Product executables and bundled runtimes are distribution assets, not workflow
  state, and are outside this restriction. A repository-local, version-control-
  excluded pointer to the selected Run is non-authoritative interface state and
  is also outside this restriction; losing it shall not lose workflow state or
  prevent resume after the Run is selected again.
- **PR-COLLAB-005:** Independently created requirements, evidence records, and
  other mergeable AEGIS artifacts shall use one artifact per file and identifiers
  generated without cross-branch coordination.
- **PR-COLLAB-006:** Artifact identifiers shall be designed to avoid collisions
  across computers and branches. AEGIS shall detect and report any duplicate
  that nevertheless appears after integration.
- **PR-COLLAB-007:** Independent work on different requirements and different
  tests shall not create AEGIS-specific merge conflicts merely because it was
  performed concurrently.
- **PR-COLLAB-008:** Normal source-control conflicts may still occur when
  branches change the same implementation code, update the same requirement,
  or create or modify the same test artifact. These conflicts represent genuine
  overlap and shall remain visible for human resolution.
- **PR-COLLAB-009:** After branch integration, `trace-validate` shall report at
  least duplicate identifiers, dangling links, and diverged impacted-file
  coverage.
- **PR-COLLAB-010:** Post-integration trace findings shall be advisory and fixed
  forward by the developer. Trace validation shall not introduce a separate
  blocking ceremony.
- **PR-COLLAB-011:** AEGIS shall not silently select one branch's requirement,
  test, evidence, or audit record when conflicting versions are merged.

AEGIS is responsible for avoiding unnecessary conflicts in its own artifact
design. It is not responsible for concealing or automatically deciding genuine
conflicts between developers' changes.

---

## 11. Machine protocol, state, and payload integrity

### 11.1 Machine interface

- **PR-PROTO-001:** Every AEGIS command shall provide a machine-readable output
  mode for agents and automation.
- **PR-PROTO-002:** Machine-readable output shall conform to an explicitly
  versioned schema. Schema identity and version shall be available in the
  command output.
- **PR-PROTO-003:** No input that an operator or agent can provide through a
  supported interface shall cause AEGIS to abandon the protocol with an
  unhandled traceback. The command shall return a structured error in the
  selected output mode.
- **PR-PROTO-004:** Structured errors shall distinguish invalid input,
  unavailable prerequisites, repository-state problems, execution failures,
  and internal failures without requiring the agent to parse a traceback.
- **PR-PROTO-005:** Human-readable output and machine-readable output may use
  different representations, but shall communicate the same result, findings,
  and outcome.
- **PR-PROTO-006:** Every AEGIS and WAEGIS CLI operation shall have one
  canonical flat command spelling. Commands shall use lowercase hyphen-separated
  tokens without a nested command tree or compatibility aliases.

### 11.2 Encoding discipline

- **PR-ENC-001:** AEGIS and WAEGIS shall use an explicit encoding for every text
  read and write. They shall not depend on the operating system's implicit
  locale or default encoding.
- **PR-ENC-002:** Product-owned text artifacts shall use a documented canonical
  encoding.
- **PR-ENC-003:** Text input handling shall tolerate common Windows editor
  output, including UTF byte-order marks, CRLF line endings, and Windows-1252
  text where the input contract permits text files.
- **PR-ENC-004:** An input that cannot be decoded safely shall produce a
  structured, path-specific error rather than a crash or silent text
  corruption.

### 11.3 Durable state integrity

- **PR-STATE-001:** AEGIS state shall be published atomically. An interrupted or
  killed process shall leave either the previous complete state or the new
  complete state, never a partially published artifact presented as valid.
- **PR-STATE-002:** Workflow state and audit evidence shall remain recoverable
  after process interruption.
- **PR-STATE-003:** Recovery shall preserve the truthful audit trail and shall
  not manufacture a successful result for an operation whose publication did
  not complete.

### 11.4 Multi-host adapters

- **PR-HOST-001:** AEGIS shall be usable from multiple agent applications through
  host-specific adapters where integration is required.
- **PR-HOST-002:** The initial supported agent hosts shall be Claude Code,
  Codex, Qwen Code, OpenCode, and Pi.
- **PR-HOST-003:** The workflow contract, states, defaults, findings, and report
  meaning shall be identical across supported hosts.
- **PR-HOST-004:** A host adapter may translate transport and presentation but
  shall not redefine workflow semantics or weaken the machine protocol.

### 11.5 Payload ownership

- **PR-PAYLOAD-001:** The AEGIS payload shall be product-managed. The agent
  workflow contract shall instruct agents not to edit payload-owned files.
- **PR-PAYLOAD-002:** An agent modification to a payload-owned file shall be
  reported as an ownership finding. Default AEGIS behavior shall remain
  non-blocking; optional hardening may refuse the write when a team enables it.
- **PR-PAYLOAD-003:** WAEGIS shall replace payload-owned files wholesale during
  upgrade rather than merge project-specific edits into them.
- **PR-PAYLOAD-004:** Project-specific rules and configuration shall live in
  repository-owned artifacts outside the replaceable payload.
- **PR-PAYLOAD-005:** Installation, repair, removal, and upgrade shall preserve
  repository-owned artifacts.

---

## 12. Product boundaries

- **PR-BOUND-001:** AEGIS is not a continuous-integration system. Enforcement
  belongs to the project's CI environment rather than the default AEGIS
  workflow.
- **PR-BOUND-002:** A team may integrate strict AEGIS checks into its CI
  environment, but that integration shall be explicit, optional, and disabled
  unless the team chooses it.
- **PR-BOUND-003:** AEGIS is not a project-management tool. It shall not own or
  manage tickets, estimates, sprints, team assignments, or project scheduling.
  Ticket text is workflow input, not project-management state owned by AEGIS.
- **PR-BOUND-004:** AEGIS shall not perform outward-facing Git operations, as
  defined by PR-WORKFLOW-006 and PR-WORKFLOW-007. Commit, push, tag, merge, and
  pull-request operations remain outside the product boundary.
- **PR-BOUND-005:** AEGIS is not a security product. Secret detection,
  protected-path warnings, and similar assistance may be offered only as
  developer conveniences.
- **PR-BOUND-006:** Security-related conveniences shall be described as findings
  or assistance, never as security controls or guarantees. They shall not be
  used to claim that AEGIS prevents, contains, or remediates security threats.

---

## 13. Open product decisions

No unresolved product-level decisions are recorded at this time. New questions
shall be placed here as the product definition develops.
