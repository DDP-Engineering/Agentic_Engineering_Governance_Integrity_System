<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Implementation Plan

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-10  
**Authoritative requirements:** `AEGIS_PRODUCT_REQUIREMENTS.md`  
**Functional behavior:** `AEGIS_FUNCTIONAL_SPECIFICATION.md`  
**Artifact design:** `AEGIS_ARTIFACT_MODEL.md`  
**CLI and machine protocol:** `AEGIS_CLI_MACHINE_PROTOCOL.md`  
**Required proof:** `AEGIS_ACCEPTANCE_PLAN.md`  
**Implementation boundaries:** `AEGIS_TECHNICAL_ARCHITECTURE.md`

## 1. Purpose and authority

This document sequences the implementation of AEGIS and WAEGIS version 1. It
turns the established product, functional, artifact, protocol, acceptance, and
architecture contracts into small deliverable slices.

`IP-*` identifiers identify implementation slices and milestones. They are
planning references, not additional product requirements. If implementation
reveals a contract problem, the owning planning document shall be revised
before the implementation silently chooses different behavior.

The plan begins with the version 1 product. Work is performed in
`05_Software/aegis/` and `05_Software/waegis/`.

## 2. Delivery method

- **IP-RULE-001:** Each slice shall deliver observable behavior through a real
  public command, durable artifact, or recovery invariant.
- **IP-RULE-002:** Focused failing tests shall be recorded before behavior code
  where the behavior is testable. Green evidence shall be recorded after the
  smallest implementation that satisfies the slice.
- **IP-RULE-003:** A slice may establish a narrow supporting seam, but shall not
  build a speculative framework for later slices.
- **IP-RULE-004:** AEGIS runtime source shall be implemented in
  `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/`, so development
  tests exercise the bytes delivered to target repositories.
- **IP-RULE-005:** WAEGIS runtime source shall remain in
  `05_Software/waegis/src/waegis/`. It treats the AEGIS payload as data and does
  not import the AEGIS workflow runtime.
- **IP-RULE-006:** Runtime code shall use the Python standard library only.
  Development and acceptance tooling may use declared development tools.
- **IP-RULE-007:** Focused tests run during a slice. The complete applicable
  package suite runs at each milestone and once more for the release candidate.
- **IP-RULE-008:** Human output wording may evolve without freezing prose in
  tests. Machine schemas, operation identifiers, state transitions, artifact
  schemas, and semantic results are tested exactly.
- **IP-RULE-009:** Every behavior, command, layout, or workflow change updates
  its relevant package documentation and copied payload resources in the same
  slice.
- **IP-RULE-010:** A slice is not complete when tests pass but its required
  evidence, documentation, or acceptance linkage remains absent.

## 3. Slice readiness and completion

### 3.1 Ready to start

A slice is ready when:

1. all listed predecessor slices are complete;
2. its referenced requirements and acceptance scenarios remain current;
3. its public operations and artifacts are defined by the protocol and Artifact
   Model;
4. representative normal, invalid, interrupted, and platform-relevant cases
   are identified; and
5. no unresolved choice would change its public contract.

### 3.2 Complete

A slice is complete when:

1. its observable outcome works through the public interface;
2. focused tests demonstrate the intended red and green evidence where
   applicable;
3. invalid operator input produces structured failure without corrupting state;
4. mutable state honors revision and publication rules applicable to the slice;
5. human and JSON presentations have the same semantic result;
6. relevant documentation and payload resources are current;
7. the applicable focused and package tests pass on the development platform;
8. any remaining platform or package verification is explicitly carried into
   its milestone; and
9. the implementation record maps changed files and tests to the Product
   Requirements and Acceptance scenarios named by the slice.

## 4. Dependency sequence

```text
IP-01 Runnable protocol spine
  |
  v
IP-02 Configuration and artifact codecs
  |
  v
IP-03 Durable publication and concurrency
  |
  v
IP-04 Run identity and selected context
  |
  v
IP-05 Stage lifecycle and resume snapshots
  |
  +----------------------+
  v                      v
IP-06 Decisions       IP-07 Requirements and Specifications
and escape hatches       |
  |                      v
  |                   IP-08 Components
  |                      |
  +----------+-----------+
             v
          IP-09 Trace graph and impacted selection
             |
             v
          IP-10 Configured command execution
             |
             v
          IP-11 Red/green and change integrity
             |
             v
          IP-12 Delivery and abandonment
             |
       +-----+-----+
       v           v
   IP-13 Adoption  IP-14 Host adapters
       \           /
        +----+-----+
             v
          IP-15 WAEGIS planning and installation
             |
             v
          IP-16 WAEGIS upgrade and removal
             |
             v
          IP-17 Platform packages
             |
             v
          IP-18 Release acceptance
```

The two branches after `IP-12` may be implemented in either order. All other
arrows are hard implementation dependencies.

## 5. Implementation slices

### IP-01 — Runnable protocol spine

**Outcome:** Both package development layouts are valid, and AEGIS exposes a
small working flat CLI using the final dispatch and response architecture.

**Implement:**

- the AEGIS package skeleton and composition root;
- domain/application/result boundaries and injected clock, UUID, and hash
  services;
- the single operation registry and mechanical dotted-to-flat name mapping;
- `help-show` and `version-show`;
- `argparse` parsing, bounded help, human presentation, one-line JSON
  presentation, protocol exit classes, and the outer structured-error boundary;
- repository-root discovery sufficient to distinguish an installed repository;
  and
- canonical atomic replacement for one file, ready for later repositories.

**Test and evidence:** registry uniqueness for all 56 declared operations;
canonical command mapping; human/JSON semantic parity for implemented
operations; invalid operation/input behavior; one-line UTF-8 JSON; traceback
containment; deterministic services; repository discovery; and single-file
interruption behavior.

**Coverage:** `PR-PROTO`, `PR-ENC-004`, `PR-MODEL-003-005`,
`PR-RUNTIME-001-002`; `AC-PROTO-001` through `AC-PROTO-003` (initial subset),
`AC-RUNTIME-001` (source subset).

**Depends on:** none.

### IP-02 — Configuration and artifact codecs

**Outcome:** AEGIS can find, read, validate, and canonically render its installed
configuration and version 1 artifact schemas without rewriting malformed input.

**Implement:**

- repository and configured-root path values with escape prevention;
- explicit encoding boundary for UTF-8, BOM, CRLF, and permitted Windows-1252
  input;
- deterministic TOML writer and bounded Markdown/front-matter codecs;
- configuration loading, defaults, validation-command definitions, timeout
  values, and selected test roots;
- `config-show`, `config-validate`, and `payload-verify`; and
- payload manifest ownership and digest verification.

**Test and evidence:** codec round trips; malformed schema and encoding errors;
exact-byte digests; path traversal and repository-escape cases; default and
multiple test roots; configured test/lint/audit definitions; payload/project
ownership separation; and read operations that leave bytes unchanged.

**Coverage:** `PR-CONFIG`, `PR-DEFAULT-001-002`, `PR-ENC`, `PR-ART`,
`PR-PAYLOAD`; `AC-CONFIG-001` through `AC-CONFIG-003` (configuration subset),
`AC-ENC-001`, `AC-PAYLOAD-001`, `AC-ART-001` (schema subset).

**Depends on:** `IP-01`.

### IP-03 — Durable publication and concurrency

**Outcome:** One-file and cohesive multi-file mutations expose a complete
before-or-after state after interruption and reject stale concurrent writes.

**Implement:**

- repository-local workspace locking for Windows and POSIX;
- expected-revision validation;
- transaction preparation below `.agentic/.runtime/`;
- commit decision, rollback, roll-forward, digest verification, and cleanup;
- repositories for planned file creation, replacement, and deletion; and
- startup recovery before authoritative reads or mutations.

**Test and evidence:** stale revision preservation; active-writer contention;
process termination at every publication boundary; recovery of create, update,
and delete transactions; malformed recovery plan behavior; no partial state;
and removal of completed transient recovery material.

**Coverage:** `PR-STATE`, `PR-COLLAB-008, 011`, `PR-SNAPSHOT-001`,
`PR-SUCCESS-004`; `AC-PROTO-005`, `AC-STATE-001` (persistence foundation).

**Depends on:** `IP-02`.

### IP-04 — Run identity and selected working context

**Outcome:** Raw ticket text creates a durable Run with eight Stage files, and
multiple Runs can coexist while one local pointer selects the working context.

**Implement:**

- UUIDv4-derived identities and canonical filenames;
- Run and Stage domain aggregates and codecs;
- read-only Git observation of opening `HEAD`, index, worktree, and untracked
  state;
- `run-create`, `run-select`, `run-list`, `run-show`, and `run-set-profile`;
- the local unversioned `context.toml` pointer; and
- full/short profile state with explicit `omitted` Stage status.

**Test and evidence:** raw text as the only required input; collision-free Run
creation; eight canonical Stage files; dirty-repository baseline attribution;
multiple active/terminal Runs; switching and clearing context; ambiguous or
missing selection; profile transitions; and multi-working-copy identity tests.

**Coverage:** `PR-RUN`, `PR-WORKFLOW-001, 004-005`, `PR-SNAPSHOT`,
`PR-COLLAB-001-007`; `AC-RUN-002` through `AC-RUN-004`, `AC-COLLAB-001`,
`AC-PROTO-004` (Run subset).

**Depends on:** `IP-03`.

### IP-05 — Stage lifecycle and resumable snapshots

**Outcome:** A developer or agent can read one self-contained Stage instruction,
record its current content, advance truthfully, stop, and resume in a new
session.

**Implement:**

- product-owned instructions and allowed-section schemas for all eight Stages;
- Stage transition rules and event append behavior;
- `stage-show`, `stage-start`, `stage-set-section`, `stage-complete`, and
  `stage-revisit`;
- atomic Stage-then-Run summary publication; and
- bounded resume context from the Run, current Stage, relevant project
  artifacts, and rules.

**Test and evidence:** every legal/illegal transition; one-section replacement;
front-matter and event preservation; Delivery completion preconditions without
premature terminal transition; stop/resume at every Stage position; bounded
ordered context; and a representative local-model-readable Stage session.

**Coverage:** `PR-WORKFLOW-002-004, 008`, `PR-SNAPSHOT`, `PR-MODEL`,
`PR-SUCCESS-002`; `AC-STAGE-001`, `AC-MODEL-001`, `AC-PROTO-004` (Stage
subset), `AC-ART-001` (Run/Stage subset).

**Depends on:** `IP-04`.

### IP-06 — Evidence, findings, decisions, scope, and escape hatches

**Outcome:** The current Stage can retain what happened, why it matters, what
was decided, and any approved deviation without blocking work or falsifying a
result.

**Implement:**

- embedded evidence, finding, disposition, decision, waiver, attachment, skip,
  and scope-evolution records;
- `evidence-add`, `finding-add`, `finding-set-disposition`, `finding-waive`,
  `decision-add`, `attachment-add`, `scope-revise`, and `stage-skip`;
- `approved`, `rejected`, and `exception_approved` decisions; and
- represented-human attribution for explicitly instructed uninterrupted agent
  work.

**Test and evidence:** append preservation; required actor/reason/target fields;
distinct skipped, waived, exception-approved, omitted, passed, and rejected
meaning; applied-work skip rejection; attachment atomicity; scope before/after
and affected-work recording; no permission denial from default findings; and
agent-directed continuation without an extra prompt.

**Coverage:** `PR-ROLE`, `PR-EVOL`, `PR-ESCAPE-001-002, 004-009`,
`PR-DEFAULT-003-006`, `PR-POSTURE`; `AC-EVOL-001`, `AC-ROLE-001`,
`AC-ESCAPE-001`, `AC-DEFAULT-001`.

**Depends on:** `IP-05`.

### IP-07 — Requirements and Specifications

**Outcome:** Runs can create, inspect, validate, update, and delete current
Requirement knowledge and its optional Specification without retaining obsolete
project-document history.

**Implement:**

- Requirement and Specification domain models, codecs, repositories, and
  templates;
- `requirement-create`, `requirement-update`, `requirement-delete`,
  `requirement-show`, `requirement-list`, `requirement-validate`,
  `specification-set`, and `specification-delete`;
- one-behavior validation, separate confirmation, priority, and current status;
  and
- cohesive current-state publication plus owning-Stage evidence.

**Test and evidence:** UUID filenames; one self-contained behavior; no ticket or
Run provenance in Requirement content; EARS as recommendation only; optional
Specification linkage; pagination; optimistic concurrency; current-content
replacement; deletion of dependent Specification/Component references without
source or test deletion; and interrupted create/update/delete recovery.

**Coverage:** `PR-REQ`, `PR-ART-004`, `PR-TRACE-001`; `AC-REQ-001` through
`AC-REQ-003`, `AC-COLLAB-001`, `AC-STATE-001` (Requirement subset).

**Depends on:** `IP-05`; uses `IP-06` for owning-Stage evidence.

### IP-08 — Components and Intake context

**Outcome:** Current Component documentation supplies concise, trusted Intake
context and remains reviewable when its boundary or files change.

**Implement:**

- Component domain model, codec, repository, and template;
- `component-create`, `component-update`, `component-delete`, `component-show`,
  `component-list`, `component-validate`, and `component-find`;
- file-membership and related-path lookup; and
- drift review for behavior, interface, dependency, and file-set changes.

**Test and evidence:** concise Component context; required purpose/boundaries/
interfaces/dependencies/files/Requirement/test fields; uncertain path lookup;
pagination; update replacement; deletion boundaries; optimistic concurrency;
conflicting membership findings; and interrupted mutation recovery.

**Coverage:** `PR-COMP`, `PR-WORKFLOW-002`, `PR-COLLAB`; `AC-COMP-001`,
`AC-COLLAB-001` through `AC-COLLAB-003`, `AC-STATE-001` (Component subset).

**Depends on:** `IP-07`.

### IP-09 — Trace graph and impacted-test selection

**Outcome:** AEGIS computes current Requirement-to-file-to-test relationships,
reports inconsistencies, and selects a safe impacted set or an explained full
suite fallback.

**Implement:**

- in-memory trace graph construction from configured roots;
- real test-path discovery without separate test registration artifacts;
- `trace-validate` as the single repository-consistency operation;
- `trace-impacted` with per-test reasons and full-suite fallback; and
- post-integration identity, link, coverage, and Component membership findings.

**Test and evidence:** complete graph union across Requirements; manually tested
Requirements; missing/dangling paths; duplicate identities; filename mismatch;
incomplete and diverged coverage; Component conflicts; safe subset and unsafe
fallback; read-only validation; and two-branch integration fixtures.

**Coverage:** `PR-TRACE`, `PR-COLLAB-009-010`, `PR-SUCCESS-005`;
`AC-TRACE-001` through `AC-TRACE-003`, `AC-COLLAB-002`, `AC-COLLAB-003`.

**Depends on:** `IP-07`, `IP-08`.

### IP-10 — Configured command execution

**Outcome:** One named configured test, lint, or audit command executes locally
and records an exact, durable outcome without confusing project failure with an
AEGIS protocol failure.

**Implement:**

- cross-platform argument-array process runner with `shell=False`;
- working-directory and executable resolution;
- unlimited and positive timeouts, cancellation, and process-group cleanup;
- concurrent standard-output/error draining and bounded result tails;
- Attachment streaming for large output; and
- `execution-list` and `execution-run` for one named command.

**Test and evidence:** pass, fail, timeout, cancellation, launch error, signals/
termination, large output, nonzero project exit with successful AEGIS protocol,
unsafe working directories, independent test/lint/audit commands, and zero as
no AEGIS-imposed timeout on Windows and Linux adapters.

**Coverage:** `PR-CONFIG-006, 008-013`, `PR-REPORT-002`, `PR-PLAT`;
`AC-CONFIG-003`, `AC-EXEC-001`, `AC-PROTO-002` (captured-output subset).

**Depends on:** `IP-06`, `IP-09`.

### IP-11 — Red-before-green and change integrity

**Outcome:** Check records real red evidence and test fingerprints; later green
execution makes test and implementation changes visible without refusing them.

**Implement:**

- exact-byte test fingerprint capture and immutable red evidence;
- later comparison for changed tests;
- read-only Git comparison points for Check and implementation changes;
- staged, unstaged, untracked, renamed, deleted, `HEAD`, and index change
  classification; and
- red-before-green expectations for both full and short profiles.

**Test and evidence:** real failing then passing tests; unchanged and legitimately
changed tests; immutable original red witness; exception-approved inapplicable
red; every Git-state mutation form; editor/host independence; findings rather
than blocking; and no Git mutation by AEGIS.

**Coverage:** `PR-RED`, `PR-INT-001-006`, `PR-ZONE`, `PR-BOUND-004`;
`AC-RED-001`, `AC-RED-002`, `AC-INT-001`, `AC-ZONE-001`, `AC-BOUND-001`
(Git-action subset).

**Depends on:** `IP-10`.

### IP-12 — Delivery, complete workflows, and abandonment

**Outcome:** Full and short Runs reach an approved, truthful Delivery or a
recorded abandonment while preserving all evidence needed by a later reader.

**Implement:**

- Delivery summary derivation from current Run/Stage evidence;
- `achieved`, `partially_achieved`, and `not_achieved` outcomes;
- atomic Delivery Stage completion and Run terminal transition through
  `stage-complete`;
- `run-abandon` for normal and exceptional unreadable-state cases; and
- complete full/short workflow fixtures from ticket text to terminal outcome.

**Test and evidence:** requested-versus-delivered outcome; changed artifacts and
code; executed evidence; test changes; findings/escapes/residual risk; approval
of report accuracy; no separate delivery command; pointer clearing; normal
abandonment; sibling exceptional record preserving unreadable bytes; full and
short end-to-end flows; and no outward Git operation.

**Coverage:** `PR-WORKFLOW`, `PR-REPORT`, `PR-DELIVERY`, `PR-ESCAPE-003, 010`,
`PR-SUCCESS-003-004`; `AC-RUN-001`, `AC-RUN-002`, `AC-ABANDON-001`,
`AC-DELIVERY-001`, `AC-BOUND-001`.

**Depends on:** `IP-11`.

### IP-13 — Adoption workflow

**Outcome:** An existing repository can be documented incrementally, one bounded
area at a time, with honest gaps and cross-session resume.

**Implement:**

- Adoption aggregate, codec, journal template, and repository;
- `adoption-create`, `adoption-show`, `adoption-set-section`,
  `adoption-complete`, and `adoption-abandon`;
- links to current Requirements, Components, tests, and files; and
- bounded resume context and completion-gap reporting.

**Test and evidence:** one-Component incremental adoption; only observed
behavior derived; existing tests/files linked; unknowns retained as gaps;
interruption and another-session resume; completion with visible gaps; and
abandonment without rewriting project knowledge.

**Coverage:** `PR-ADOPT`, `PR-SNAPSHOT`, `PR-TRACE`; `AC-ADOPT-001`,
`AC-STAGE-001` (resume principle).

**Depends on:** `IP-12`.

### IP-14 — Host adapter contract

**Outcome:** Direct human CLI use and supported AI hosts consume the same Stage
instructions, operation identifiers, machine results, and workflow meaning.

**Implement:**

- a host-adapter conformance contract over the local machine protocol;
- generic adapter resources under `.agentic/aegis/adapters/`;
- host integration resources for Claude Code, Codex, Qwen Code, OpenCode, and
  Pi; and
- bounded operation discovery suitable for a limited local model.

**Test and evidence:** identical operation/result fixtures across direct CLI and
adapters; no adapter-owned workflow transitions or approvals; representative
resume-and-continue flow per supported host; human-only CLI flow; no dependence
on hooks for fingerprint detection; and the reference local-model Stage
exercise.

**Coverage:** `PR-HOST`, `PR-ROLE`, `PR-MODEL`, `PR-SCOPE-005`;
`AC-HOST-001`, `AC-HOST-002`, `AC-MODEL-001`, `AC-ROLE-001`.

**Depends on:** `IP-12`.

### IP-15 — WAEGIS planning, repository initialization, and installation

**Outcome:** WAEGIS can analyze a target, preview every write, optionally
initialize local Git through a separately approved plan, and install a usable
AEGIS payload from an exact digest.

**Implement:**

- independent WAEGIS package layers, composition root, registry, presenters,
  and protocol envelope;
- target analysis, payload manifest, ownership, plan model, digest, and
  precondition validation;
- `repository-init-plan`, `repository-init-apply`, `install-plan`, and
  `install-apply`;
- detected/default project configuration and version-control exclusions; and
- WAEGIS-local transaction publication and recovery.

**Test and evidence:** read-only plan generation; byte-exact digest approval;
stale target/plan rejection; non-Git initialization only on apply; clean,
existing-tests, no-tests, and dirty target fixtures; immediately usable
defaults; WAEGIS/AEGIS envelope parity; interruption recovery; and proof of no
stage/commit/branch/push operation.

**Coverage:** `PR-WAEGIS-001-002, 005-007`, `PR-DEFAULT-001-002`, `PR-SCOPE-001`,
`PR-BOUND-004`; `AC-WAEGIS-001`, `AC-WAEGIS-002`, `AC-CONFIG-001`,
`AC-CONFIG-002`, `AC-DEFAULT-001`.

**Depends on:** `IP-13`, `IP-14`.

### IP-16 — WAEGIS upgrade and removal

**Outcome:** WAEGIS replaces or removes only manifest-owned payload content and
preserves all current project data.

**Implement:**

- `upgrade-plan`, `upgrade-apply`, `remove-plan`, and `remove-apply`;
- installed-versus-source manifest comparison;
- exact ownership classification for replace/delete/preserve actions; and
- atomic upgrade/removal with target precondition revalidation.

**Test and evidence:** plan read-only behavior; modified payload reporting;
wholesale payload replacement; preservation of configuration, rules,
Requirements, Specifications, Components, tests, Adoptions, Runs, and
application files; stale plan rejection; interrupted apply recovery; payload
removal followed by successful project tests; and no outward Git action.

**Coverage:** `PR-WAEGIS-004-005`, `PR-PAYLOAD-003, 005`, `PR-POSTURE-004-006`,
`PR-SUCCESS-006`; `AC-WAEGIS-004`, `AC-WAEGIS-005`, `AC-PAYLOAD-001`.

**Depends on:** `IP-15`.

### IP-17 — Platform archives and offline runtime

**Outcome:** All four delivery editions exist for each target platform as eight
self-contained transferable archives for Windows 11 and Ubuntu 22.04 x86-64,
are written below `07_Delivery/dist/`, and work with networking denied.

**Implement:**

- dependency-excluding AEGIS and WAEGIS archives with exact prerequisites;
- dependency-including AEGIS and WAEGIS archives with private Python 3.12 and
  Git;
- platform launchers and relocatable private-runtime resolution;
- checked-in runtime input lock manifest and generated archive inventory; and
- reproducible offline build/inspection tooling for local runtime inputs.

**Test and evidence:** archive inventory/digests; clean extraction; relocation;
first applicable operation; external Python 3.12/Git prerequisite checks;
private Python 3.12/Git;
network-denied execution; no telemetry/update request; no global PATH,
registration, association, or Git-configuration change; platform semantic
parity; and Python 3.12 target projects with `pytest` and `unittest`.

**Coverage:** `PR-PKG`, `PR-RUNTIME`, `PR-PLAT`, `PR-OFF`, `PR-SCOPE-003-005,
009`; `AC-PKG-001`, `AC-PKG-002`, `AC-RUNTIME-001`, `AC-PLATFORM-001`,
`AC-OFFLINE-001`, `AC-OFFLINE-002`.

**Depends on:** `IP-16`.

### IP-18 — Release acceptance and product-success audit

**Outcome:** A version 1 candidate has a truthful acceptance record covering
every applicable `AC-*` scenario and can be judged without reconstructing the
implementation effort.

**Implement:**

- automated acceptance orchestration and fixtures;
- Windows/Ubuntu, external/bundled runtime, clean/dirty/non-Git, framework,
  interruption, multi-working-copy, network-denied, and local-model matrices;
- a release-candidate evidence inventory keyed by Acceptance scenario; and
- the final product-success demonstration and release verdict record.

**Test and evidence:** execute the order and evidence contract in
`AEGIS_ACCEPTANCE_PLAN.md`; record every pass, failure, retry, blocked result,
and approved lower-priority deferral; verify package hashes and exact bundled
versions; run the full package suites; run `AC-SUCCESS-001`; and inspect the
candidate for standard-library-only runtime imports and unintended data
transmission/outward Git facilities.

**Coverage:** all Product Requirements and all 58 Acceptance scenarios, with
priority interpreted exactly as defined by the Acceptance Plan.

**Depends on:** `IP-17`.

## 6. Milestones

| Milestone | Included slices | Demonstrable result | Required broad validation |
|---|---|---|---|
| **M1 — Protocol foundation** | `IP-01` through `IP-03` | The real CLI exposes final command/protocol structure and durable state primitives. | AEGIS package suite on Python 3.12; codec, protocol, and fault-injection suites. |
| **M2 — Resumable workflow core** | `IP-04` through `IP-06` | Ticket text creates a resumable Run with Stage state, decisions, findings, and truthful escapes. | AEGIS package suite; cross-session workflow matrix; Windows/POSIX persistence adapters. |
| **M3 — Traceable delivery** | `IP-07` through `IP-12` | Current project knowledge, impacted tests, red/green evidence, and complete Delivery work end to end. | AEGIS package suite; full/short workflow, real Git, subprocess, and integrity matrices. |
| **M4 — Adoption and hosts** | `IP-13` through `IP-14` | Existing repositories and direct/agent hosts use the same resumable contract. | Adoption resume suite, adapter contract suite, local-model exercise, supported-host matrix. |
| **M5 — Operator lifecycle** | `IP-15` through `IP-16` | WAEGIS safely initializes, installs, upgrades, and removes the payload. | AEGIS and WAEGIS package suites; plan/apply, ownership, and WAEGIS fault-injection matrices. |
| **M6 — Release candidate** | `IP-17` through `IP-18` | Eight offline archives, four per target platform, are accepted. | Complete Acceptance Plan and product-success audit. |

No milestone result substitutes for the slice-level evidence beneath it.

## 7. Cross-cutting verification tracks

### 7.1 Protocol stability

Beginning with `IP-01`, every added operation is checked against the one
registry for canonical command spelling, input decoding, output schema, bounded
next actions, JSON-line discipline, exit class, and help metadata. The complete
56-operation catalog becomes executable incrementally without introducing
temporary public commands.

### 7.2 Persistence integrity

Beginning with `IP-03`, every new mutable repository receives the same adapter
contract tests for revision conflicts, interruption, recovery, digest
verification, malformed state, and cleanup. Fault injection expands with each
new artifact type rather than waiting for the final milestone.

### 7.3 Cross-platform parity

Pure domain/use-case suites run on every supported development interpreter.
Filesystem locking, process execution, path safety, Git parsing, encoding, and
launchers receive Windows and Linux integration coverage at the first slice
that introduces them. Package-level equivalence is confirmed in `IP-17`.

### 7.4 Offline and dependency discipline

Runtime dependency inspection begins with `IP-01`. Network-denied smoke tests
begin when the first useful installed operation exists and expand through
WAEGIS and packages. Release acceptance verifies that no core path imports an
undeclared third-party runtime package or initiates data transmission.

### 7.5 Current project knowledge versus Run evidence

Requirement, Specification, Component, configuration, and traceability tests
assert direct replacement or deletion of obsolete project knowledge. Run and
Stage tests independently assert preservation of evidence, findings, decisions,
scope changes, red witnesses, execution outcomes, and terminal results.

## 8. Implementation records

Each completed slice shall leave a concise record containing:

- slice and milestone identifiers;
- Product Requirements and Acceptance scenarios addressed;
- files and public operations changed;
- focused red and green evidence;
- broader suite/static/package results;
- manual or platform checks performed;
- known failed, blocked, deferred, or unverified checks; and
- documentation and payload resources updated.

The record describes the implementation work; it does not create a second
product-requirement register or duplicate the authoritative acceptance record.

## 9. Start point

Implementation starts with `IP-01 — Runnable protocol spine`. Its first
demonstration is intentionally small: the delivered AEGIS package runs
`help-show` and `version-show` through the real registry, application dispatcher,
structured result, and human/JSON presenters while using the final repository
discovery and single-file publication seams.

No source implementation begins before this plan and its authoritative input
documents agree on the slice's observable contract.
