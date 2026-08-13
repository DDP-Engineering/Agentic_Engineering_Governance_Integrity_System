<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Acceptance Plan

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-10  
**Authoritative requirements:** `AEGIS_PRODUCT_REQUIREMENTS.md`  
**Release priorities:** `AEGIS_RELEASE_SCOPE.md`  
**Functional behavior:** `AEGIS_FUNCTIONAL_SPECIFICATION.md`  
**Artifact design:** `AEGIS_ARTIFACT_MODEL.md`  
**CLI and machine protocol:** `AEGIS_CLI_MACHINE_PROTOCOL.md`

## 1. Purpose and authority

This document defines how AEGIS version 1 will be accepted as a product. It
turns the observable commitments in the Product Requirements Register into
repeatable scenarios and identifies the evidence required to make a release
decision.

Only `PR-*` entries are product requirements. `AC-*` identifiers name acceptance
scenarios; they do not add product behavior. `FS-*`, `AM-*`, and `CP-*` entries
provide the functional, artifact, and protocol detail used to construct the
checks.

If an acceptance scenario conflicts with a Product Requirement, the Product
Requirement is authoritative and this plan must be corrected. Internal module
names, classes, algorithms, and package decomposition remain Technical
Architecture decisions.

## 2. Acceptance principles

- Acceptance evaluates observable behavior, durable artifacts, package
  contents, and public interfaces. It does not approve an implementation merely
  because its internal design appears plausible.
- AEGIS remains advisory and non-blocking for the developer. The acceptance
  harness may still fail a release candidate when a `Must` product behavior is
  absent or false.
- A scenario passes only from recorded execution or explicit manual evidence.
  Expected behavior, an agent assertion, or an unexecuted command is not
  evidence.
- Human and machine interfaces must communicate the same outcome even when their
  presentation differs.
- Requirements, Specifications, Components, and traceability are checked as
  current project knowledge. Run and Stage artifacts are checked as workflow
  history and evidence.
- Acceptance must not require internet access or transmit repository, ticket, or
  evidence content.
- Scenarios shall remain independent of a particular AI provider or agent host
  except where a scenario explicitly verifies one host adapter or the reference
  local-model experience.
- Documentation under `00_Planning/` is reviewed directly. Automated acceptance
  tests shall verify product behavior and machine-significant templates, not
  freeze planning prose, headings, or file inventories.

## 3. Priority and verdict policy

### 3.1 Requirement priority

| Priority | Acceptance treatment |
|---|---|
| `Must` | Release-blocking. Every applicable requirement needs passing automated evidence or an approved explicit manual method. |
| `Should` | May be deferred. A deferred item is named in the release record with its reason and is never reported as delivered. |
| `Could` | Optional. If implemented, its acceptance scenario must pass without weakening any applicable `Must`. |

### 3.2 Scenario result

| Result | Meaning |
|---|---|
| `not_run` | No acceptance attempt has been recorded. |
| `passed` | The expected observable behavior was demonstrated by the required evidence. |
| `failed` | The product completed the attempt but contradicted an expected result. |
| `blocked` | The scenario could not execute because its acceptance environment or prerequisite was unavailable. |
| `not_applicable` | The scenario does not apply to this edition or candidate, with an approved reason. |
| `deferred` | A `Should` or `Could` capability is intentionally absent from this candidate and is declared as such. |

A `blocked`, `not_run`, or `not_applicable` `Must` does not count as passed.
`not_applicable` is valid for a `Must` only when the Product Requirement itself
defines the non-applicability.

### 3.3 Release verdict

A version 1 candidate is accepted only when:

1. all 211 `Must` requirements are mapped to applicable passing evidence;
2. the complete ticket-to-Delivery workflow passes on the required platform and
   test-framework matrix;
3. all four delivery editions pass their applicable offline package scenarios;
4. every failed or blocked scenario is visible and no unfavorable result is
   represented as passed;
5. all 17 `Should` and three `Could` requirements are either passed or explicitly
   declared deferred; and
6. the release record identifies the exact source revision, product version,
   package digests, environments, scenario results, and retained evidence.

## 4. Evidence contract

### 4.1 Automated evidence

Automated evidence records:

- scenario identifier and applicable Product Requirements;
- product version, source revision, and package digest;
- operating system, architecture, Python runtime, Git version, and package
  edition;
- fixture repository identity and its opening revision/state;
- exact command and arguments, working directory, start and finish time;
- process outcome, exit status, and concise output;
- relevant generated or changed artifacts and their content digests; and
- the acceptance result with references to retained raw output where needed.

### 4.2 Manual evidence

Manual evidence is permitted where the behavior cannot be confirmed reliably by
automation. It records:

- scenario identifier;
- actor and time;
- environment and package identity;
- procedure performed;
- expected observation;
- actual observation; and
- conclusion and reason.

Manual evidence is not a weaker vocabulary for an unexecuted automated check.

### 4.3 Retries and failures

An acceptance retry records a new attempt. It does not turn a timeout, launch
error, cancellation, or earlier product failure into a pass. The release record
may identify the accepted attempt, but all attempts used to judge the candidate
remain available as evidence.

## 5. Acceptance environments

### 5.1 Platform matrix

| Environment | Operating system | Architecture | Runtime purpose |
|---|---|---|---|
| `ENV-WIN-SYSTEM-312` | Windows 11 | x86-64 | External Python 3.12 and Git prerequisites. |
| `ENV-UBU-SYSTEM-312` | Ubuntu 22.04 LTS | x86-64 | External Python 3.12 and Git prerequisites. |
| `ENV-WIN-BUNDLED-312` | Windows 11 | x86-64 | Private bundled Python 3.12 and Git. |
| `ENV-UBU-BUNDLED-312` | Ubuntu 22.04 LTS | x86-64 | Private bundled Python 3.12 and Git. |

The complete forward workflow is exercised with Python 3.12 target repositories
using both `pytest` and standard-library `unittest` on Windows and Ubuntu.
External-runtime environments verify that the launchers check Python 3.12 and
Git without installing or modifying either prerequisite.

### 5.2 Delivery-edition matrix

Each supported platform receives and tests:

1. AEGIS without bundled external dependencies;
2. AEGIS with private Python 3.12 and Git;
3. WAEGIS containing AEGIS without bundled external dependencies; and
4. WAEGIS containing AEGIS with private Python 3.12 and Git.

Dependency-excluding editions are exercised with documented prerequisites
already present. Dependency-including editions are exercised on a host that does
not rely on system Python or Git for product operation.

### 5.3 Repository fixtures

| Fixture | Purpose |
|---|---|
| `REPO-CLEAN-PYTEST` | Clean Git repository, Python 3.12, existing `pytest` tests. |
| `REPO-CLEAN-UNITTEST` | Clean Git repository, Python 3.12, existing `unittest` tests. |
| `REPO-NO-TESTS` | Git repository with no detected test root or test command. |
| `REPO-EXISTING-MULTIROOT` | Existing repository with multiple test roots and named test, lint, and audit commands. |
| `REPO-NON-GIT` | Application directory without Git metadata. |
| `REPO-DIRTY` | Git repository with known staged, unstaged, and untracked changes before Run creation. |
| `REPO-COLLAB` | Two working copies and branches used for independent and overlapping work. |
| `REPO-SUBMODULE` | Simple parent repository with an independently governed Git submodule. |
| `REPO-MALFORMED` | Copies containing BOM, CRLF, Windows-1252, invalid encoding, malformed state, and unsafe paths. |
| `REPO-LARGE-OUTPUT` | Agent- or developer-run validation commands with bounded, large, slow, failing, cancelled, and unlaunchable reported outcomes. |

Fixtures contain only synthetic data and no credentials.

### 5.4 Offline environment

Offline scenarios deny outbound network access and provide no hosted service,
remote model, package registry, telemetry endpoint, or online documentation.
Third-party project commands may be omitted unless the scenario explicitly tests
the `Should` fully air-gapped integration boundary.

### 5.5 Local-model environment

The reference evaluation uses a local open-weights model in the
Qwen3.6-27B-class with a 128K context window, or the documented closest available
reference build. The exact model and runtime are recorded. Acceptance judges
whether one Stage can be understood and completed from bounded tool output and
durable context; it imposes no arbitrary context-overhead limit that prevents a
usable workflow.

## 6. Scenario format

Each scenario below defines:

- **Priority:** release treatment;
- **Method:** automated, fault-injection, package, model-assisted, or manual;
- **Exercise and expected result:** observable acceptance behavior; and
- **Requirements:** authoritative `PR-*` coverage.

Where a row covers mixed priorities, only its `Must` subset blocks the initial
release; the lower-priority subset is reported separately.

## 7. Installation, packages, and runtime

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-WAEGIS-001` | Must | Package + automated | On a clean Git repository, `waegis install-plan` reports every intended write and changes nothing. `install-apply` accepts only the exact plan digest, installs a usable default payload/configuration, and performs no outward Git action. | `PR-WAEGIS-001-002, 005-006`; `PR-DEFAULT-001-002` |
| `AC-WAEGIS-002` | Must | Package + automated | On `REPO-NON-GIT`, WAEGIS previews local initialization, performs `git init` only through the approved apply command, then installs AEGIS without staging, committing, branching, or pushing. | `PR-WAEGIS-007`; `PR-SCOPE-001`; `PR-BOUND-004` |
| `AC-WAEGIS-003` | Could | Package + automated/manual | If diagnosis and repair are included, an unhealthy installation is reported and an approved repair restores payload-owned files without changing project-owned data. Otherwise the capability is declared deferred. | `PR-WAEGIS-003` |
| `AC-WAEGIS-004` | Should | Package + automated | Upgrade plan is read-only; exact-digest apply replaces payload-owned files wholesale and preserves configuration, Requirements, Components, tests, Adoptions, and Runs. | `PR-WAEGIS-004-005`; `PR-PAYLOAD-003, 005`; `PR-SUCCESS-006` |
| `AC-WAEGIS-005` | Must | Package + automated | Removal preview identifies only payload-owned paths. Apply removes the payload while the application and all project-owned artifacts remain usable and present. | `PR-POSTURE-004-006`; `PR-ART-004`; `PR-PAYLOAD-005` |
| `AC-PKG-001` | Must | Package | All four editions exist for each of Windows and Ubuntu x86-64, producing eight transferable archives that perform their applicable first operation with network access denied. | `PR-PKG-001-006`; `PR-OFF-001-006` |
| `AC-PKG-002` | Must | Package + inspection | Bundled editions use private Python 3.12 and Git, remain relocatable, do not install or alter global runtimes/configuration, and record exact fixed bundled versions. | `PR-PKG-007, 009`; `PR-RUNTIME-004-005` |
| `AC-RUNTIME-001` | Must | Automated matrix | Dependency-excluding AEGIS and WAEGIS launchers check and run with external Python 3.12 and Git on both platforms without installing them; source uses the standard library only; bundled editions run with their private Python 3.12 and Git. | `PR-RUNTIME-001-007`; `PR-PKG-008` |
| `AC-PLATFORM-001` | Must | Automated differential | Equivalent inputs on Windows and Ubuntu produce the same states, enums, findings, operation identifiers, and semantic outcomes, with only documented platform path/presentation differences. | `PR-PLAT-001-004`; `PR-SCOPE-002, 005` |

## 8. Defaults, configuration, offline use, and model usability

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-CONFIG-001` | Must | Automated | Installation into `REPO-NO-TESTS` produces complete usable configuration, selects `.agentic/tests/`, and requires no policy, mode, glob, or source-root questionnaire before the first Run. | `PR-CONFIG-001-003`; `PR-DEFAULT-001-002` |
| `AC-CONFIG-002` | Must | Automated | Existing single and multiple test roots and confidently detectable `pytest`/`unittest` commands are configured without moving tests; uncertain detection uses and reports an applicable shipped default. | `PR-CONFIG-004-007`; `PR-SCOPE-003-005, 009` |
| `AC-CONFIG-003` | Must | Automated | Independently named test, lint, and audit command guides retain their working directories. Agent- or developer-recorded pass, fail, timeout, cancellation, and launch-error outcomes remain distinct, and no AEGIS operation launches the configured command. | `PR-CONFIG-006, 008-013` |
| `AC-DEFAULT-001` | Must | Automated + manual | With shipped configuration, edits, commands, findings, unfavorable evidence, and Stage closure are not refused. Strict prevention remains off and configuration can only add deliberately selected strictness. | `PR-DEFAULT-003-006`; `PR-POSTURE-001-003` |
| `AC-OFFLINE-001` | Must | Automated network-denied | Core AEGIS and WAEGIS operations complete with outbound networking denied, initiate no data transmission, contain no telemetry/analytics/update checks, and retain all data locally. | `PR-OFF-001-006, 008-009` |
| `AC-OFFLINE-002` | Should | Manual + integration | A fully air-gapped workflow completes when the operator separately supplies compatible local models and third-party project tools. Product behavior remains truthful when such a third-party tool is unavailable. | `PR-OFF-007` |
| `AC-MODEL-001` | Must | Model-assisted + recorded | The reference local model reads bounded Component/Requirement context, obtains one Stage instruction, performs atomic operations, and completes one representative Stage without loading the complete register or receiving compound next actions. | `PR-MODEL-001-005`; `PR-WORKFLOW-003`; `PR-PROTO-006` |
| `AC-REPO-001` | Must | Automated + inspection | A simple repository is governed as one AEGIS installation; monorepository/nested-repository limitations are stated; a Git submodule is treated as an independent repository with its own AEGIS state. | `PR-SCOPE-006-008` |

## 9. CLI, machine protocol, encoding, and durable state

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-PROTO-001` | Must | Automated catalog | Every operation has exactly one flat lowercase CLI token derived by replacing dots and underscores with hyphens. Command help is bounded; no nested or alias spelling is accepted as canonical. | `PR-PROTO-001-002, 005-006` |
| `AC-PROTO-002` | Must | Automated | Every command has human and JSON modes with the same meaning. JSON mode emits exactly one UTF-8 JSON line, no prompt, ANSI, progress text, traceback, or interleaved project-command output. | `PR-PROTO-001-005`; `PR-MODEL-005` |
| `AC-PROTO-003` | Must | Automated generated-input | Operator-producible invalid values, types, enums, paths, encodings, transitions, and schema versions return the documented structured error and exit class without corrupting state or exposing a traceback. | `PR-PROTO-002-004`; `PR-ENC-004` |
| `AC-PROTO-004` | Must | Automated client | A small client creates a Run from ticket text, reads current context, changes one section, records one entry, and receives no more than the bounded immediate atomic next actions. Each invocation performs only its named use case. | `PR-MODEL-003-005`; `PR-PROTO-001-006`; `PR-RUN-003` |
| `AC-PROTO-005` | Must | Automated concurrency | A stale `--expected-revision` returns `state_conflict`, preserves current content, and provides a read action. A valid revision publishes one complete new state. | `PR-STATE-001-003`; `PR-COLLAB-008, 011` |
| `AC-ENC-001` | Must | Automated matrix | Canonical product text is UTF-8. Supported input correctly handles UTF BOMs, CRLF, and Windows-1252; undecodable content produces a path-specific structured error without silent replacement. | `PR-ENC-001-004`; `PR-PLAT-003` |
| `AC-STATE-001` | Must | Fault-injection | Process termination is injected before, during, and after publication of representative Run, Stage, Requirement, Component, Attachment, and context mutations. Recovery exposes either the previous or new complete state and never invented completion. | `PR-STATE-001-003`; `PR-SNAPSHOT-001`; `PR-SUCCESS-004` |
| `AC-PAYLOAD-001` | Must | Automated + inspection | Manifest verification distinguishes payload-owned and project-owned paths. An agent edit to payload content is permitted but reported; rules/configuration remain outside the payload and removal preserves them. | `PR-PAYLOAD-001-002, 004-005`; `PR-DEFAULT-003-004` |

## 10. Runs, Stages, decisions, and Delivery

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-RUN-001` | Must | End-to-end matrix | Raw ticket text in each platform/framework combination reaches approved Delivery through Intake, Alignment, Requirement, Design, Check, Implementation, Validation, and Delivery. Each Stage has its instruction and durable state; AEGIS performs no commit or other outward Git action. | `PR-WORKFLOW-001-004, 006-013`; `PR-DELIVERY-001-002`; `PR-BOUND-004` |
| `AC-RUN-002` | Must | End-to-end matrix | A developer-selected short Run for a small fix records Design as profile-omitted, retains Requirement, red-before-green, implementation, impacted Validation, and truthful Delivery, and costs proportionately less ceremony. | `PR-WORKFLOW-005`; `PR-POSTURE-001, 003`; `PR-RED-003` |
| `AC-RUN-003` | Must | Automated | Multiple active and terminal Runs coexist. One local unversioned pointer selects at most one Run; selection can switch without changing either Run; routine commands use selected Run/current Stage; ambiguous selection changes nothing. | `PR-RUN-001-004`; `PR-COLLAB-001-004` |
| `AC-RUN-004` | Must | Automated | Run creation in `REPO-DIRTY` records opening `HEAD`, staged, unstaged, and untracked state. Pre-existing work is not attributed to the Run and uncertain attribution is reported rather than invented. | `PR-RUN-005-007` |
| `AC-STAGE-001` | Must | Automated + cross-session | A session stops during every Stage position in representative Runs. A new session resumes from `run.md`, current Stage, relevant project artifacts, and saved evidence without chat history or re-deriving completed work. | `PR-WORKFLOW-008`; `PR-SNAPSHOT-001-004`; `PR-SUCCESS-002` |
| `AC-STAGE-002` | Must | Host end-to-end + inspection | Without explicit continuous delegation, every included Stage handoff presents a concise outcome, artifacts, evidence, findings, open questions, proposed handoff, and continue/review/revise-or-reimplement/park choices, then waits. Continue starts the next Stage, review and park do not mutate state, revision uses recorded Stage history, and Delivery requires approve-and-close. A separately exercised explicitly delegated Run crosses the same handoffs without prompts. | `PR-ROLE-001-004`; `PR-WORKFLOW-009-010` |
| `AC-STAGE-003` | Must | Automated | Stage completion reports only blank configured required sections, unresolved designated existing references, malformed or absent outcomes for recorded command executions, and applicable approval or continuous-delegation state. It creates no automatic finding about scope precision, design quality, test adequacy, red-witness quality, finding importance, or risk acceptability. Actual execution, Git, fingerprint, and traceability facts remain visible in Stage checkpoints and Delivery. | `PR-WORKFLOW-011-013` |
| `AC-EVOL-001` | Must | Automated | `scope-revise` preserves original ticket and prior Run interpretation, records actor/reason/time and before/after scope, identifies affected completed work/evidence, and permits fix-forward continuation without restarting. | `PR-EVOL-001-005` |
| `AC-ROLE-001` | Must | End-to-end + inspection | Developer-operated, instructed-agent, and human-only Runs share the same contract. An agent defaults to Stage checkpoints and does not infer uninterrupted authority; an agent explicitly instructed to finish may record approvals and continue without prompts. Each decision records the represented actor, target, reason/conditions, and time. | `PR-ROLE-001-007`; `PR-ESCAPE-008` |
| `AC-ESCAPE-001` | Must | Automated | Each skippable Stage can be skipped before work is applied with actor and reason; applied work cannot be retroactively skipped. Skipped, waived, exception-approved, and profile-omitted states remain distinct and never become passed. | `PR-ESCAPE-001-002, 004-009`; `PR-DEFAULT-004` |
| `AC-ABANDON-001` | Must | Fault-injection + automated | Normal abandonment records a terminal Run outcome while preserving evidence. When Run state is unreadable, exceptional abandonment creates the sibling record without overwriting unreadable bytes. | `PR-ESCAPE-003, 010`; `PR-STATE-002-003` |
| `AC-DELIVERY-001` | Must | Automated + manual judgement | Delivery concisely states requested/delivered outcome, artifact/code changes, actual evidence, changed tests, findings, escapes, residual risk, and `achieved`, `partially_achieved`, or `not_achieved`. Approval accepts report accuracy, not automatic claim satisfaction. | `PR-REPORT-001-003`; `PR-DELIVERY-001-004`; `PR-SUCCESS-003-004` |

## 11. Current project knowledge and traceability

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-REQ-001` | Must | Automated schema + review | Each Requirement file has collision-resistant identity, one self-contained behavior, separate confirmation, `Must/Should/Could` priority, and `draft/active` status. Ticket/Run provenance is absent from project Requirement content. | `PR-REQ-001, 003-004, 007-009` |
| `AC-REQ-002` | Should | Automated + review | EARS remains a recommendation rather than a parser gate. When a Requirement is not buildable alone, its optional Specification uses the common template and supplies the necessary build detail. | `PR-REQ-002, 005-006` |
| `AC-REQ-003` | Must | Automated | Requirement, Specification, and traceability updates replace current content. Deletion removes the Requirement, its Specification, and Component references atomically, leaves no retirement artifact/history, does not delete source/tests, and remains recorded in the owning Run. | `PR-REQ-003, 007-008`; `PR-TRACE-001`; `PR-ART-004` |
| `AC-COMP-001` | Must | Automated + review | Components document purpose, boundaries, interfaces, dependencies, files, Requirements, and tests concisely enough for Intake. Behavior/interface/file changes trigger drift review; update replaces current content and removal deletes the Component document. | `PR-COMP-001-004`; `PR-WORKFLOW-002` |
| `AC-ART-001` | Must | Automated parse + manual review | Requirements, Specifications, Components, Runs, Stages, evidence, findings, and Delivery are human-readable text, version-control-reviewable, host-independent, and parse according to their declared schemas on both platforms. | `PR-ART-001-004`; `PR-SNAPSHOT-004` |
| `AC-TRACE-001` | Must | Automated | Complete Requirement-to-impacted-file-to-real-test links select the union of all tests covering changed files, including tests linked through other Requirements, without separate test-registration files. | `PR-TRACE-001-003, 006-010`; `PR-SUCCESS-005` |
| `AC-TRACE-002` | Must | Automated | Missing paths, dangling links, or incomplete coverage create findings. When a safe complete impacted set cannot be computed, selection falls back to the full configured suite and records why. | `PR-TRACE-004-005, 011` |
| `AC-TRACE-003` | Must | Automated + review | Every automated Requirement has a happy-path test; a bug fix normally has a red regression. Additional boundary, edge, corner, negative, and failure-path tests follow recorded risk rather than quotas; manual verification has a concrete reason/method. | `PR-TRACE-006-007, 012-016` |
| `AC-ADOPT-001` | Should | End-to-end + cross-session | Adoption incrementally discovers one existing Component, derives only observed behavior, creates current Requirements/Components, links existing tests/files, records gaps honestly, and resumes across sessions until completed or abandoned. | `PR-ADOPT-001-006` |

## 12. Red-before-green, execution evidence, and integrity

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-RED-001` | Must | Automated end-to-end | The agent or developer executes a relevant test and records an actual failing result and test fingerprint in Check before implementation; later execution records green. The original red witness remains immutable in both full and short Runs. | `PR-RED-001-003`; `PR-INT-001, 004` |
| `AC-RED-002` | Must | Automated | Genuinely inapplicable red-before-green uses an approved exception with actor and reason. Missing, skipped, or waived red evidence is visible in Delivery and is never rendered as passed. | `PR-RED-004-005`; `PR-ESCAPE-007-009` |
| `AC-INT-001` | Must | Automated | After red evidence, one test is changed legitimately and another is unchanged. Green comparison names only the changed test, reports a finding without blocking, and works identically regardless of editor or host hooks. | `PR-INT-001-006` |
| `AC-ZONE-001` | Must | Automated Git-state matrix | Check entry records `HEAD`, index, working tree, untracked paths, and implementation fingerprints. Staged, unstaged, untracked, renamed, deleted, and `HEAD`/index changes during Check are reported without staging, reverting, refusing, or altering them. | `PR-ZONE-001-007` |
| `AC-EXEC-001` | Must | Automated | The agent or developer may run tests during Check/Implementation and tests, lints, and audits during Validation through normal host tooling. Pass, fail, timeout, cancellation, and launch error are recorded accurately; large output is attached and summarized; no AEGIS operation launches a project command. | `PR-CONFIG-006, 008-013`; `PR-REPORT-002` |
| `AC-HARDEN-001` | Could | Automated/manual | If preventive write zones are implemented, they are opt-in and ship off; enabling them does not change default fingerprint detection or falsify refused/allowed outcomes. Otherwise they are declared deferred. | `PR-INT-007` |

## 13. Collaboration, hosts, and boundaries

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-COLLAB-001` | Must | Multi-working-copy automated | Two developers create separate Runs, Requirements, Components, and tests on separate branches/computers. UUID identities and one-artifact-per-file layout create no shared counter/global-register conflict; repository branches are the only durable state store. | `PR-COLLAB-001-007`; `PR-REQ-008`; `PR-RUN-001-002` |
| `AC-COLLAB-002` | Must | Git integration + inspection | Branches that update the same Requirement or test produce an ordinary visible source-control conflict. AEGIS never silently selects one branch's artifact, evidence, or coverage as the winner. | `PR-COLLAB-008, 011` |
| `AC-COLLAB-003` | Should | Automated | After integration, `trace-validate` reports duplicate identities, missing targets, broken traceability, conflicting Component membership, and diverged coverage as advisory findings and performs no repair or branch selection. | `PR-COLLAB-009-010` |
| `AC-HOST-001` | Must | Adapter contract | Every implemented host adapter invokes the same operation identifiers and produces the same workflow states, decisions, evidence, findings, defaults, and Delivery meaning as direct CLI use. | `PR-HOST-003-004`; `PR-SCOPE-005` |
| `AC-HOST-002` | Should | Host matrix | Claude Code, Codex, Qwen Code, OpenCode, and Pi each stop at a default checkpoint, present the four developer choices, and complete a representative resume-and-continue flow; each also honors explicit continuous delegation through the same protocol. Missing adapters are explicitly deferred. | `PR-HOST-001-002`; `PR-WORKFLOW-009-010` |
| `AC-BOUND-001` | Must | Automated observation + review | AEGIS performs no project test, lint, audit, or validation command, commit, push, tag, branch, merge, pull-request, or outward-Git preflight; owns no tickets/sprints/assignment; does not claim CI enforcement or security-control guarantees; security conveniences remain findings. | `PR-WORKFLOW-006-007`; `PR-CONFIG-009`; `PR-BOUND-001, 003-006` |
| `AC-BOUND-002` | Could | Automated/manual | If strict CI integration is provided, it is explicitly selected, remains outside default local behavior, and does not redefine AEGIS as CI. Otherwise it is declared deferred. | `PR-BOUND-002` |

## 14. Product-success audit

`AC-SUCCESS-001` is the final release audit. It does not replace the scenarios
above and cannot manufacture evidence for them.

| Scenario | Priority | Method | Exercise and expected result | Requirements |
|---|---|---|---|---|
| `AC-SUCCESS-001` | Must/Should | Evidence audit + representative demonstration | A fresh developer installs and begins without configuration; another session resumes; Delivery is understandable without reconstruction; missing/changed evidence remains visible; impacted validation normally avoids the full suite; applicable install/upgrade/remove/interruption/collaboration scenarios have truthful results. | `PR-SUCCESS-001-006` |

## 15. Product-requirement coverage matrix

The matrix provides a compact completeness view. Detailed acceptance evidence
references the individual Product Requirement identifiers within each area.

| Product Requirement area | Acceptance scenarios |
|---|---|
| `PR-ROLE` | `AC-ROLE-001`, `AC-STAGE-002`, `AC-RUN-001`, `AC-HOST-001` |
| `PR-WORKFLOW` | `AC-RUN-001`, `AC-RUN-002`, `AC-STAGE-001`, `AC-STAGE-002`, `AC-STAGE-003`, `AC-COMP-001`, `AC-HOST-002`, `AC-BOUND-001` |
| `PR-RUN` | `AC-RUN-003`, `AC-RUN-004`, `AC-PROTO-004`, `AC-COLLAB-001` |
| `PR-EVOL` | `AC-EVOL-001` |
| `PR-SNAPSHOT` | `AC-STAGE-001`, `AC-STATE-001`, `AC-ART-001` |
| `PR-REPORT` | `AC-DELIVERY-001`, `AC-EXEC-001` |
| `PR-DELIVERY` | `AC-RUN-001`, `AC-DELIVERY-001` |
| `PR-ART` | `AC-WAEGIS-005`, `AC-REQ-003`, `AC-ART-001` |
| `PR-REQ` | `AC-REQ-001`, `AC-REQ-002`, `AC-REQ-003`, `AC-COLLAB-001` |
| `PR-ADOPT` | `AC-ADOPT-001` |
| `PR-DEFAULT` | `AC-WAEGIS-001`, `AC-CONFIG-001`, `AC-DEFAULT-001`, `AC-PAYLOAD-001` |
| `PR-POSTURE` | `AC-WAEGIS-005`, `AC-DEFAULT-001`, `AC-RUN-002` |
| `PR-ESCAPE` | `AC-ROLE-001`, `AC-ESCAPE-001`, `AC-ABANDON-001`, `AC-RED-002` |
| `PR-SUCCESS` | `AC-WAEGIS-004`, `AC-TRACE-001`, `AC-STATE-001`, `AC-DELIVERY-001`, `AC-SUCCESS-001` |
| `PR-WAEGIS` | `AC-WAEGIS-001` through `AC-WAEGIS-005` |
| `PR-SCOPE` | `AC-WAEGIS-002`, `AC-CONFIG-002`, `AC-PLATFORM-001`, `AC-REPO-001` |
| `PR-CONFIG` | `AC-CONFIG-001` through `AC-CONFIG-003`, `AC-EXEC-001` |
| `PR-PLAT` | `AC-PLATFORM-001`, `AC-ENC-001`, platform matrix scenarios |
| `PR-RUNTIME` | `AC-RUNTIME-001`, `AC-PKG-002` |
| `PR-OFF` | `AC-PKG-001`, `AC-OFFLINE-001`, `AC-OFFLINE-002` |
| `PR-MODEL` | `AC-MODEL-001`, `AC-PROTO-002`, `AC-PROTO-004` |
| `PR-PKG` | `AC-PKG-001`, `AC-PKG-002`, `AC-RUNTIME-001` |
| `PR-COMP` | `AC-COMP-001`, `AC-COLLAB-001` |
| `PR-TRACE` | `AC-REQ-003`, `AC-TRACE-001` through `AC-TRACE-003` |
| `PR-RED` | `AC-RUN-002`, `AC-RED-001`, `AC-RED-002` |
| `PR-INT` | `AC-RED-001`, `AC-INT-001`, `AC-HARDEN-001` |
| `PR-ZONE` | `AC-ZONE-001` |
| `PR-COLLAB` | `AC-RUN-003`, `AC-PROTO-005`, `AC-COLLAB-001` through `AC-COLLAB-003` |
| `PR-PROTO` | `AC-MODEL-001`, `AC-PROTO-001` through `AC-PROTO-004` |
| `PR-ENC` | `AC-PROTO-003`, `AC-ENC-001` |
| `PR-STATE` | `AC-PROTO-005`, `AC-STATE-001`, `AC-ABANDON-001` |
| `PR-HOST` | `AC-HOST-001`, `AC-HOST-002` |
| `PR-PAYLOAD` | `AC-WAEGIS-004`, `AC-WAEGIS-005`, `AC-PAYLOAD-001` |
| `PR-BOUND` | `AC-WAEGIS-002`, `AC-BOUND-001`, `AC-BOUND-002` |

## 16. Acceptance execution order

The scenarios do not prescribe implementation architecture, but they should be
made executable in an order that finds fundamental contract failures early:

1. artifact/template parsing, encoding, UUID identity, and current-state
   project knowledge;
2. flat CLI dispatch, response envelope, structured errors, and atomic
   publication;
3. Run selection, Stage snapshots, resume, decisions, and escape outcomes;
4. red-before-green, fingerprints, Git-state comparison, execution outcomes,
   and impacted validation;
5. complete and short ticket-to-Delivery workflows;
6. installation, removal, offline behavior, and platform parity;
7. delivery-edition packaging and private runtimes;
8. collaboration and host invariants; and
9. lower-priority Adoption, upgrade, post-integration trace validation,
   hardening, and CI scenarios
   when included in a candidate.

## 17. Acceptance completion record

The release acceptance record shall contain:

- candidate product version and source revision;
- package names, editions, platforms, and SHA-256 digests;
- exact runtime and Git versions;
- one result for every applicable `AC-*` scenario;
- links to automated and manual evidence;
- all failed, blocked, not-applicable, and retried attempts;
- approved reasons for every deferred `Should` and `Could` requirement;
- known limitations and unverified integrations; and
- the final release verdict, actor, and time.

The Technical Architecture identifies the implementation boundaries needed to
satisfy these scenarios. The Implementation Plan sequences their delivery
without changing their observable outcomes or the Product Requirements they
cover.
