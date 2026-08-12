<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Technical Architecture

**Status:** Working draft  
**Product version:** 1  
**Last updated:** 2026-08-10  
**Authoritative requirements:** `AEGIS_PRODUCT_REQUIREMENTS.md`  
**Functional behavior:** `AEGIS_FUNCTIONAL_SPECIFICATION.md`  
**Artifact design:** `AEGIS_ARTIFACT_MODEL.md`  
**CLI and machine protocol:** `AEGIS_CLI_MACHINE_PROTOCOL.md`  
**Required proof:** `AEGIS_ACCEPTANCE_PLAN.md`

## 1. Purpose and authority

This document defines the implementation architecture for AEGIS and WAEGIS
version 1. It establishes dependency direction, source and payload boundaries,
runtime responsibilities, persistence and recovery mechanisms, platform
adapters, packaging structure, and test seams.

`TA-*` identifiers are architecture decisions. They are not additional product
requirements. Product behavior remains owned by `PR-*`; functional meaning,
artifact meaning, CLI behavior, and acceptance proof remain owned by their
respective planning documents.

The architecture starts from the version 1 contracts only. It contains no
compatibility layer, alternate artifact layout, command alias, or state migrator.

## 2. Architecture goals

- **TA-PRINCIPLE-001:** Domain and workflow policy shall be independent of CLI,
  host, filesystem, Git, process, and operating-system implementations.
- **TA-PRINCIPLE-002:** Every public operation shall have one application use
  case and one canonical operation identifier.
- **TA-PRINCIPLE-003:** AEGIS and WAEGIS runtime code shall use the Python
  standard library only.
- **TA-PRINCIPLE-004:** Windows and Linux differences shall be isolated behind
  narrow adapters and shall not appear in domain behavior.
- **TA-PRINCIPLE-005:** Repository artifacts are the authoritative product state.
  No server, database, user-home state, or required external cache shall exist.
- **TA-PRINCIPLE-006:** Requirements, Specifications, Components, configuration,
  and traceability contain only current project knowledge. Run and Stage files
  retain workflow evidence.
- **TA-PRINCIPLE-007:** One command shall perform one named use case and shall
  return one bounded result.
- **TA-PRINCIPLE-008:** Findings and unfavorable engineering outcomes are domain
  results, not application exceptions.
- **TA-PRINCIPLE-009:** Read operations shall not repair, migrate, normalize, or
  rewrite authoritative state.
- **TA-PRINCIPLE-010:** Abstractions shall exist only at replaceable or testable
  boundaries. Simple pure functions are preferred over wrapper objects with no
  independent responsibility.

## 3. System context and deployment boundary

```text
Human or AI host
        |
        | flat CLI or host adapter
        v
  AEGIS application -------------------- configured project tools
        |                                         |
        | repository-local artifacts              | subprocess execution
        v                                         v
  target Git repository <------------------ test / lint / audit command

Operator
   |
   | flat WAEGIS CLI
   v
 WAEGIS application ---- embedded AEGIS payload ----> target repository
```

- **TA-CONTEXT-001:** AEGIS runs inside or against one target repository and
  owns no outward integration or publication step.
- **TA-CONTEXT-002:** WAEGIS is an operator application outside the target
  repository. It plans and applies repository initialization, installation,
  upgrade, and removal.
- **TA-CONTEXT-003:** WAEGIS contains the AEGIS payload as versioned data. WAEGIS
  shall not import or invoke AEGIS workflow domain code to install it.
- **TA-CONTEXT-004:** Agent-host adapters are thin transports over the same AEGIS
  operation protocol. They contain no workflow decisions.

## 4. Clean architecture and dependency direction

| Layer | Responsibility | Allowed dependencies |
|---|---|---|
| Domain | Identities, values, aggregate state, transitions, trace relationships, findings, decisions, outcomes, and invariants. | Python standard library and other domain modules. |
| Application | One use case per operation, orchestration, transaction scope, port calls, and operation results. | Domain and port interfaces. |
| Ports | Required capabilities such as artifact storage, transactions, Git observation, process execution, clock, UUID, hashing, and platform services. | Domain value types and standard-library typing. |
| Interface adapters | Flat CLI parsing, JSON input, human/JSON presentation, and host transport. | Application dispatcher and protocol data types. |
| Infrastructure adapters | Filesystem codecs, transaction recovery, Git subprocesses, configured processes, platform locks, clocks, UUIDs, and hashing. | Ports, domain value types, and operating-system facilities. |
| Composition root | Concrete adapter selection and application assembly. | All outer layers; no domain policy. |

- **TA-LAYER-001:** Dependencies point inward. Domain and Application modules
  shall not import interface or infrastructure modules.
- **TA-LAYER-002:** Ports use `typing.Protocol` where structural substitution is
  useful; an abstract base class shall be used only when shared lifecycle logic
  is required.
- **TA-LAYER-003:** Domain types shall use small dataclasses, enums, and pure
  functions. They shall not open files, read environment variables, invoke Git,
  start processes, or print.
- **TA-LAYER-004:** Application use cases return explicit result values. They do
  not select presentation wording or process exit codes.
- **TA-LAYER-005:** Infrastructure adapters translate external facts into domain
  values without deciding whether a Stage, finding, or Delivery is acceptable.
- **TA-LAYER-006:** The composition root is the only module that constructs the
  complete object graph.

## 5. Authoritative source and payload layout

### 5.1 AEGIS source of truth

The runnable AEGIS implementation is developed in the exact template subtree
that is copied into a target repository:

```text
05_Software/aegis/
|-- pyproject.toml
|-- template/
|   `-- .agentic/
|       |-- aegis/                         # product-owned payload
|       |   |-- manifest.toml
|       |   |-- cli/
|       |   |   |-- pyproject.toml
|       |   |   `-- src/
|       |   |       `-- aegis/
|       |   |-- workflows/
|       |   |-- adapters/
|       |   |-- defaults/
|       |   `-- templates/
|       |-- config.toml                    # project-owned starter
|       |-- rules.md                       # project-owned starter
|       |-- requirements/
|       |-- components/
|       |-- tests/
|       |-- adoptions/
|       `-- runs/
`-- tests/
```

- **TA-SOURCE-001:** AEGIS runtime source shall have one authoritative copy under
  `template/.agentic/aegis/cli/src/aegis/`.
- **TA-SOURCE-002:** Repository-level development packaging shall import that
  source directly so tests execute the same bytes delivered downstream.
- **TA-SOURCE-003:** Everything below `template/` is generic downstream material
  and shall contain no facts about this repository's own planning or history.
- **TA-SOURCE-004:** Product-owned payload resources and project-owned starter
  artifacts shall remain separated by the `.agentic/aegis/` boundary.

### 5.2 WAEGIS source of truth

```text
05_Software/waegis/
|-- pyproject.toml
|-- src/
|   `-- waegis/
|-- tests/
`-- dist/                                  # generated release output
```

Release archive construction and inspection are repository tools rather than
WAEGIS runtime source:

```text
02_Tools/
|-- build_aegis_release.py
`-- runtime_inputs.toml
```

- **TA-SOURCE-005:** WAEGIS runtime source shall remain under `src/waegis/` and
  shall be independently importable and executable.
- **TA-SOURCE-006:** WAEGIS tests may inspect an assembled AEGIS payload as data
  but shall not add AEGIS runtime source to WAEGIS's import path.
- **TA-SOURCE-007:** Release build, runtime-input locking, and archive inspection
  logic shall remain in the standalone `02_Tools/build_aegis_release.py` script
  and shall not become part of either product runtime.
- **TA-SOURCE-008:** Generated archives, private runtimes, and package staging
  directories are build outputs, not authoritative source.

## 6. AEGIS runtime modules

The internal package layout is organized by architectural responsibility:

```text
aegis/
|-- __init__.py
|-- __main__.py
|-- composition.py
|-- domain/
|   |-- identifiers.py
|   |-- values.py
|   |-- run.py
|   |-- stage.py
|   |-- project.py
|   |-- evidence.py
|   |-- trace.py
|   `-- results.py
|-- application/
|   |-- dispatcher.py
|   |-- operation_registry.py
|   |-- context.py
|   |-- run_operations.py
|   |-- stage_operations.py
|   |-- entry_operations.py
|   |-- requirement_operations.py
|   |-- component_operations.py
|   |-- trace_operations.py
|   |-- execution_operations.py
|   `-- adoption_operations.py
|-- ports/
|   |-- artifacts.py
|   |-- transactions.py
|   |-- repository.py
|   |-- processes.py
|   `-- services.py
|-- interface/
|   |-- cli.py
|   |-- input.py
|   |-- human_presenter.py
|   `-- json_presenter.py
`-- infrastructure/
    |-- discovery.py
    |-- filesystem.py
    |-- codecs.py
    |-- publication.py
    |-- git.py
    |-- process.py
    |-- platform.py
    `-- services.py
```

- **TA-MODULE-001:** This layout defines responsibilities, not a requirement that
  every type occupy its own file. Related small types may remain together.
- **TA-MODULE-002:** One application function or service implements each of the
  56 protocol operations. Operations are grouped by resource module rather than
  spread across 56 single-function files.
- **TA-MODULE-003:** `operation_registry.py` declares operation identifier,
  canonical flat command, input decoder, help metadata, use-case callable, and
  presenter data once.
- **TA-MODULE-004:** The flat CLI command is derived mechanically from its
  operation identifier by replacing dots and underscores with hyphens.
- **TA-MODULE-005:** `dispatcher.py` resolves one registry entry and invokes one
  use case. It shall not contain a command-name conditional chain that duplicates
  the registry.
- **TA-MODULE-006:** Workflow instructions, schemas, defaults, and templates are
  product resources loaded through a resource port rather than embedded as long
  strings in use-case modules.

## 7. Domain model

### 7.1 Identities and values

- **TA-DOMAIN-001:** `RunId`, `RequirementId`, `ComponentId`, `AdoptionId`, and
  `AttachmentId` validate their canonical prefix and UUIDv4-derived 32 lowercase
  hexadecimal characters.
- **TA-DOMAIN-002:** Identity creation uses an injected UUID service; parsing an
  existing identity never generates a replacement.
- **TA-DOMAIN-003:** Repository paths are normalized domain values containing
  relative `/`-separated paths only. Conversion to native paths occurs at the
  filesystem boundary.
- **TA-DOMAIN-004:** Timestamps are timezone-aware UTC values supplied by an
  injected clock and rendered in one canonical form.
- **TA-DOMAIN-005:** Statuses, priorities, outcomes, severities, dispositions,
  decisions, execution outcomes, and Stage names are enums with exact protocol
  values.

### 7.2 Aggregates

| Aggregate | Owns |
|---|---|
| Run | Identity, original ticket, profile, work type, current Stage, opening repository state, scope evolution, Stage summaries, and terminal outcome. |
| Stage | Stage status, instruction identity, current sections, evidence, findings, decisions, attachments, escapes, and event history. |
| Requirement | One current behavior, confirmation, priority/status, impacted files, current test/manual links, and optional Specification path. |
| Component | Current component purpose, boundary, interfaces, dependencies, files, Requirement/test links, gaps, and drift review. |
| Adoption | Current resumable reverse-workflow state for one bounded area. |
| Trace graph | In-memory current relationships among Requirements, files, tests, Specifications, and Components. |

- **TA-DOMAIN-006:** Aggregate transition functions return a new state plus
  domain findings/events; they do not mutate loaded state invisibly.
- **TA-DOMAIN-007:** Run evidence is append-preserving where the contracts require
  historical truth. Project-knowledge aggregate updates replace current content.
- **TA-DOMAIN-008:** A Specification is subordinate to one Requirement and has no
  independent identity lifecycle.
- **TA-DOMAIN-009:** Findings state an observed condition and consequence.
  Decisions state the current approved, rejected, or exception-approved choice.
- **TA-DOMAIN-010:** A domain finding never raises an operational exception merely
  because it is severe or unfavorable.

## 8. Operation execution pipeline

Every AEGIS invocation follows one pipeline:

1. parse executable-global options and one flat command;
2. resolve the operation registry entry;
3. decode and validate scalar and structured input;
4. discover and validate the repository root and project configuration;
5. acquire the applicable workspace lock and recover unfinished publication;
6. resolve selected Run/current Stage when the operation requires them;
7. validate expected revisions and transition prerequisites;
8. invoke exactly one application use case;
9. publish its transaction, if any;
10. construct one application result; and
11. present that result as human text or one JSON line.

- **TA-OP-001:** Input decoding completes before the use case changes state.
- **TA-OP-002:** Repository discovery walks upward only from `--repo` or the
  current directory and never consults a user-home configuration.
- **TA-OP-003:** A read-only operation may name an explicit Run or Stage without
  changing the local selected context.
- **TA-OP-004:** A mutation requiring Run context uses the selected Run and the
  Run's current Stage rather than accepting redundant routine identifiers.
- **TA-OP-005:** Use cases do not automatically invoke other catalog operations.
  A cohesive transaction may still update every artifact required for one
  domain action.
- **TA-OP-006:** The application result contains operation, target context,
  revision, outcome, data, findings, artifacts, next actions, error, truncation,
  and detail reference in protocol-ready values.

## 9. CLI and machine-protocol architecture

- **TA-CLI-001:** The CLI uses one `argparse` top-level subparser per flat command.
  There is no nested resource/action parser.
- **TA-CLI-002:** Command definitions are generated from the operation registry;
  help and dispatch cannot drift into separate command vocabularies.
- **TA-CLI-003:** `--input -` reads bytes from standard input exactly once.
  File input is read through the encoding boundary and scalar input through
  `argparse` values.
- **TA-CLI-004:** Machine mode directs all project-process output into capture
  adapters and reserves standard output for one compact JSON response plus LF.
- **TA-CLI-005:** Human and JSON presenters consume the same application result.
  Neither presenter recalculates findings, outcomes, or next actions.
- **TA-CLI-006:** Dotted operation identifiers are the internal and JSON protocol
  names. Hyphenated command tokens are interface spelling only.
- **TA-CLI-007:** Machine schemas use explicit decoders and validators implemented
  with standard-library types. No runtime JSON-schema package is required.
- **TA-CLI-008:** List use cases return cursor-page domain values. Presenters do
  not load or truncate an unbounded register after the use case returns.

## 10. Artifact codecs and repositories

### 10.1 Codec responsibilities

Each durable artifact type has one codec with four operations:

```text
bytes -> decode -> parse -> validate -> domain aggregate
domain aggregate -> render -> canonical bytes
```

- **TA-CODEC-001:** TOML input uses `tomllib`. A small deterministic TOML writer
  supports only the value shapes required by AEGIS schemas.
- **TA-CODEC-002:** JSON uses the standard `json` module with explicit UTF-8 and
  stable compact separators in machine mode.
- **TA-CODEC-003:** Markdown artifacts use a bounded parser for TOML front matter,
  declared level-two sections, and structured tables owned by the schema. AEGIS
  shall not implement a general Markdown renderer.
- **TA-CODEC-004:** Canonical rendering uses UTF-8 without BOM and LF endings.
- **TA-CODEC-005:** General repository text ingestion may detect UTF BOMs,
  normalize CRLF after decoding, and fall back to Windows-1252 only where the
  input contract permits general text.
- **TA-CODEC-006:** Evidence fingerprints and revision digests operate on exact
  bytes before text normalization.
- **TA-CODEC-007:** A malformed authoritative artifact is returned as a
  path-specific load error and its bytes are not rewritten.

### 10.2 Repository interfaces

- **TA-STORE-001:** Separate repositories own Runs, Stages, Requirements,
  Components, Adoptions, Attachments, configuration, and local context.
- **TA-STORE-002:** Repositories expose domain operations such as load, list,
  render, current revision, and planned mutation rather than arbitrary path
  reads and writes.
- **TA-STORE-003:** Requirement and Component lists are derived by scanning their
  configured roots. No shared counter or authoritative global register exists.
- **TA-STORE-004:** Current revisions are lowercase SHA-256 digests of exact
  authoritative bytes with the `sha256:` protocol prefix.
- **TA-STORE-005:** The selected context repository owns only
  `<runs-root>/context.toml`. It is local, disposable, and excluded from version
  control.

## 11. Atomic publication and recovery

### 11.1 Per-file publication

- **TA-PUBLISH-001:** Every new file is written to a temporary sibling on the
  same filesystem, flushed, and installed with `os.replace`.
- **TA-PUBLISH-002:** Parent directories are created before preparation; a target
  path is never assembled from an unresolved user string or unsafe traversal.
- **TA-PUBLISH-003:** A successful replacement is followed by the strongest
  standard-library-supported file and directory flush available on the current
  platform.

### 11.2 Multi-file recovery transaction

Cohesive mutations such as Run creation, Delivery completion, and Requirement
deletion may change several files. They use a repository-local recovery area:

```text
.agentic/.runtime/
|-- write.lock
`-- transactions/
    `-- TXN-<32hex>/
        |-- plan.json
        |-- decision
        |-- before/
        `-- after/
```

This area is transient, excluded from version control, never read by an agent as
project context, and contains no authoritative project history.

- **TA-PUBLISH-004:** Before touching target paths, the transaction stores the
  exact before-state, intended after-state, target/deletion list, and digests in
  a prepared transaction directory on the same filesystem.
- **TA-PUBLISH-005:** An atomic decision file selects rollback or commit. Before a
  commit decision, recovery restores the complete before-state. After a commit
  decision, recovery finishes the complete after-state.
- **TA-PUBLISH-006:** AEGIS performs recovery under the workspace lock before any
  authoritative read or mutation and never presents a partially applied
  transaction as valid state.
- **TA-PUBLISH-007:** The transaction verifies every final target digest before
  it reports completion, then removes its transient before/after bytes.
- **TA-PUBLISH-008:** A recovery bundle surviving interruption is recovery state,
  not project history. It is removed immediately after successful rollback or
  roll-forward.
- **TA-PUBLISH-009:** Failure to prepare or recover returns a structured
  publication/repository-state error and preserves the bundle for diagnosis; it
  never guesses a successful outcome.
- **TA-PUBLISH-010:** Authoritative publication order remains project artifacts
  and Attachments, then owning Stage, then Run summary/context.

## 12. Concurrency

- **TA-CONCURRENCY-001:** Optimistic concurrency uses the caller's expected
  content revision and detects stale reads before transaction preparation.
- **TA-CONCURRENCY-002:** A repository-local OS lock serializes recovery and
  publication inside one working copy. POSIX and Windows implementations use
  their standard-library locking facilities behind one port.
- **TA-CONCURRENCY-003:** Lock acquisition shall not wait indefinitely. A busy
  workspace returns `state_conflict` with a bounded retry/read next action.
- **TA-CONCURRENCY-004:** The operating system releases the active lock when a
  process dies; durable recovery is determined from the transaction bundle, not
  from a process identifier alone.
- **TA-CONCURRENCY-005:** Separate branches and working copies coordinate through
  Git artifacts and UUID identities, not through cross-machine locks.

## 13. Repository discovery, path safety, and Git observation

- **TA-REPO-001:** Repository discovery accepts an explicit `--repo` or walks
  upward from the current directory to a valid `.agentic/config.toml` and Git
  worktree boundary.
- **TA-REPO-002:** AEGIS workflow operations require the configured repository to
  be a Git worktree. WAEGIS owns the separately authorized `git init` use case.
- **TA-REPO-003:** All stored paths are validated lexically and after filesystem
  resolution. Symlinks/reparse points that escape the repository are rejected as
  unsafe targets.
- **TA-REPO-004:** AEGIS Git access is a read-only subprocess adapter using
  argument arrays and machine-stable output such as porcelain-v2 `-z` records.
- **TA-REPO-005:** The Git observer may inspect worktree root, `HEAD`, index,
  staged/unstaged state, untracked paths, and exact content. It exposes no
  staging, commit, branch, merge, tag, push, pull-request, or remote operation.
- **TA-REPO-006:** WAEGIS's Git initializer is a separate adapter reachable only
  from `repository-init-apply` after exact plan-digest confirmation.
- **TA-REPO-007:** A configured or bundled Git executable is resolved explicitly;
  AEGIS does not change global Git configuration or depend on shell aliases.

## 14. Trace validation and impacted selection

- **TA-TRACE-001:** `trace-validate` scans current Requirement, Specification,
  Component, configured test-root, and Run-reference artifacts and builds one
  in-memory trace graph.
- **TA-TRACE-002:** The graph is computed by tooling and is not stored as an
  authoritative registry or loaded into the model context.
- **TA-TRACE-003:** Validation reports duplicate identities, filename/identity
  mismatch, missing targets, dangling links, malformed paths, incomplete test
  coverage, conflicting Component file membership, and diverged coverage.
- **TA-TRACE-004:** `trace-validate` is the only general repository-consistency
  command. Post-integration checks are part of this operation.
- **TA-TRACE-005:** `trace-impacted` walks current file-to-test links across every
  Requirement and returns the union of linked tests with selection reasons.
- **TA-TRACE-006:** Any condition that makes the impacted graph unsafe or
  incomplete selects the complete configured suite and records the exact reason.
- **TA-TRACE-007:** Trace validation and selection are read-only computations;
  findings do not repair links or rewrite project knowledge.

## 15. Configured process execution

- **TA-PROCESS-001:** Configuration stores commands as argument arrays, never as
  implicit shell text. The process runner defaults to `shell=False`.
- **TA-PROCESS-002:** The runner validates the repository-relative working
  directory and resolves executable selection through the configured/bundled
  runtime environment.
- **TA-PROCESS-003:** A timeout of zero maps to no AEGIS-imposed timeout. Positive
  values use a monotonic clock.
- **TA-PROCESS-004:** Windows and POSIX adapters start a controllable process
  group and implement cancellation/timeout escalation without terminating
  unrelated processes.
- **TA-PROCESS-005:** Standard output and error are drained concurrently to avoid
  pipe deadlocks. Bounded tails remain in the response/evidence; large complete
  output is streamed to an Attachment.
- **TA-PROCESS-006:** The runner returns exactly `passed`, `failed`, `timed_out`,
  `cancelled`, or `launch_error`, plus exit status and timing where applicable.
- **TA-PROCESS-007:** A completed project-command failure is evidence with a
  successful AEGIS protocol response. Process launch/publication failures remain
  operational errors only where AEGIS cannot durably record the outcome.

## 16. Stage instructions, context, and host adapters

- **TA-HOST-001:** Each Stage's instruction and allowed section schema is one
  product-owned resource under `.agentic/aegis/workflows/`.
- **TA-HOST-002:** `stage-show` assembles bounded context from the Run summary,
  current Stage, directly relevant Components/Requirements, project rules, and
  concise tool findings. It does not concatenate the complete repository
  register.
- **TA-HOST-003:** Context assembly applies stable ordering, pagination, and
  explicit omission references rather than arbitrary character truncation.
- **TA-HOST-004:** Host adapters under `.agentic/aegis/adapters/` invoke the same
  dotted operations and machine envelope as the CLI, normally through the local
  AEGIS executable.
- **TA-HOST-005:** A host adapter may translate tool registration and transport
  but may not approve, advance a Stage, reinterpret findings, or edit payload
  policy.
- **TA-HOST-006:** Human-only operation uses the same CLI, instructions,
  artifacts, and decisions and needs no separate domain path.

## 17. WAEGIS architecture

WAEGIS uses the same inward dependency rule with a smaller domain:

```text
waegis/
|-- domain/          # plan, manifest, ownership, target analysis
|-- application/     # repository-init, install, upgrade, remove operations
|-- ports/           # target filesystem, payload source, Git init, services
|-- interface/       # flat CLI and presenters
|-- infrastructure/  # filesystem, archive, runtime and platform adapters
`-- composition.py
```

- **TA-WAEGIS-001:** Analysis and every `*-plan` operation are read-only against
  the target. The plan is written only to the explicit operator-owned output
  path.
- **TA-WAEGIS-002:** A plan contains target identity/state, exact writes,
  replacements/deletions, ownership classification, prerequisites, warnings,
  and SHA-256 digest.
- **TA-WAEGIS-003:** Apply recomputes target preconditions and plan digest before
  its first target write. Any mismatch returns `state_conflict`.
- **TA-WAEGIS-004:** The AEGIS payload manifest is the sole authority for
  payload-owned installation, replacement, verification, and removal paths.
- **TA-WAEGIS-005:** Project configuration generation is a dedicated use case
  that detects roots/commands and otherwise applies complete shipped defaults.
- **TA-WAEGIS-006:** WAEGIS uses its own publication/recovery implementation and
  tests. It shall not import AEGIS persistence code at runtime.
- **TA-WAEGIS-007:** AEGIS and WAEGIS each implement the small protocol envelope
  locally; parity tests enforce identical schema identity, fields, enums, and
  error meaning without creating a third runtime package.

## 18. Packaging architecture

### 18.1 Dependency-excluding editions

- **TA-PACKAGE-001:** AEGIS without dependencies contains the complete
  `.agentic/aegis/` payload, project-owned starter artifacts, platform launcher,
  and an exact Python/Git prerequisite document.
- **TA-PACKAGE-002:** WAEGIS without dependencies contains the WAEGIS package,
  embedded AEGIS payload, platform launcher, and prerequisite document.
- **TA-PACKAGE-003:** Both use external Python 3.12 and a resolved compatible
  Git executable without downloading or installing either. Platform launchers
  check their presence before product startup.

### 18.2 Dependency-including editions

- **TA-PACKAGE-004:** Bundled editions contain platform-specific private Python
  3.12 and Git distributions assembled for the destination operating system.
- **TA-PACKAGE-005:** Private runtimes live below the extracted product archive
  and are invoked through product launchers. They do not modify system PATH,
  file associations, Python registration, Git configuration, or global install
  locations.
- **TA-PACKAGE-006:** A bundled runtime is an assembled relocatable distribution,
  not a copied virtual environment.

### 18.3 Build and manifest

- **TA-PACKAGE-007:** Packaging is an offline build step that accepts explicit
  local runtime inputs and verifies them against a checked-in lock manifest.
- **TA-PACKAGE-008:** Every archive has a generated inventory with path, byte
  length, SHA-256 digest, ownership, platform, architecture, product/protocol
  version, Python version, and Git version.
- **TA-PACKAGE-009:** WAEGIS embeds the exact AEGIS payload archive or directory
  represented by the release inventory; it does not reconstruct payload files
  from WAEGIS code.
- **TA-PACKAGE-010:** Windows and Ubuntu archives are built and accepted
  independently for x86-64.
- **TA-PACKAGE-011:** The four editions on each target platform produce eight
  release archives under `07_Delivery/dist/`.

## 19. Error and result architecture

| Category | Examples | Protocol treatment |
|---|---|---|
| Domain finding | Missing test link, changed test, out-of-zone edit, failed validation | Successful operation response with findings/outcome. |
| Invalid input | Wrong field, enum, schema, unsafe path | Structured `invalid_input`; no mutation. |
| Invalid state | Wrong Stage transition, missing selected Run | Structured state/transition error; no mutation. |
| Concurrency | Stale revision, active writer | Structured `state_conflict`; no overwritten state. |
| Prerequisite | Git/Python/project command unavailable | Structured prerequisite or recorded `launch_error`, according to whether evidence can be durably recorded. |
| Publication | Filesystem/flush/recovery failure | Structured `publication_failed`; no claimed completion. |
| Internal | Unexpected implementation defect | Structured internal error without traceback in protocol output. |

- **TA-ERROR-001:** Domain results and operational errors use separate types.
- **TA-ERROR-002:** One outer exception boundary maps known adapter/application
  errors and unexpected `Exception` values into the protocol envelope.
- **TA-ERROR-003:** Keyboard cancellation is handled explicitly and never
  mislabeled as a test failure or internal crash.
- **TA-ERROR-004:** Diagnostic traceback text may be retained locally in a
  bounded diagnostic Attachment when state permits, but never appears as the
  machine protocol response.
- **TA-ERROR-005:** Presenters derive process exit codes from protocol status,
  not from domain finding severity.

## 20. Versioning and schema discipline

- **TA-VERSION-001:** Product version, protocol schema version, payload version,
  and each artifact schema version are explicit independent values.
- **TA-VERSION-002:** Version 1 readers accept only their declared schema and
  return `unsupported_schema` for unsupported input. They do not guess or
  silently rewrite another shape.
- **TA-VERSION-003:** Requirement, Specification, and Component updates render
  only current content and contain no revision history.
- **TA-VERSION-004:** Command registry and response schema changes follow the
  machine-protocol compatibility rules; no alternate CLI alias is introduced.
- **TA-VERSION-005:** AEGIS version is declared once in `aegis.__init__`; WAEGIS
  version is declared once in `waegis.version`; package manifests consume those
  values during build.

## 21. Testing architecture

| Test layer | Purpose |
|---|---|
| Domain tests | Pure transitions, enums, identity/path validation, trace rules, outcomes, and invariants. |
| Use-case tests | One operation with fake ports, including findings, errors, revisions, and next actions. |
| Adapter contract tests | Every real/fake implementation of artifact, transaction, Git, process, clock, UUID, hash, and lock ports. |
| Codec tests | Canonical round trips, malformed inputs, BOM/CRLF/Windows-1252, exact-byte fingerprints, and schema rejection. |
| CLI protocol tests | All 56 command mappings, human/JSON parity, one-line output, exit classes, help, pagination, and invalid input. |
| Persistence tests | Per-file replacement, multi-file rollback/roll-forward, process-kill matrix, lock contention, and stale revision. |
| Repository integration tests | Real Git worktrees, dirty state, changed `HEAD`/index, submodules, unsafe paths, and trace selection. |
| Process integration tests | Real child processes for pass, fail, timeout, cancellation, launch error, and large output. |
| WAEGIS integration tests | Plan/apply digest, ownership, non-Git initialization, install, removal, and optional upgrade. |
| Package acceptance tests | Extracted dependency-including/excluding editions on Windows and Ubuntu with networking denied. |

- **TA-TEST-001:** Tests inject deterministic clock, UUID, hash fixtures, and
  fake ports only at declared architecture boundaries.
- **TA-TEST-002:** Focused behavior tests precede implementation changes; broad
  integration and acceptance suites confirm cross-boundary behavior.
- **TA-TEST-003:** Protocol tests assert schemas, fields, enums, and behavior, not
  incidental human wording.
- **TA-TEST-004:** Documentation tests shall not freeze prose or planning-file
  layout. Machine-significant TOML/front matter and JSON examples may be parsed.
- **TA-TEST-005:** Fault-injection workers are separate processes so termination
  tests exercise real filesystem and lock cleanup behavior.
- **TA-TEST-006:** Cross-platform parity compares normalized semantic results
  while preserving platform-specific raw paths only in diagnostics.

## 22. Architecture-to-acceptance mapping

| Architecture area | Principal acceptance scenarios |
|---|---|
| Source/payload ownership | `AC-WAEGIS-004`, `AC-WAEGIS-005`, `AC-PAYLOAD-001`, `AC-ART-001` |
| Clean layers and operation registry | `AC-PROTO-001`, `AC-PROTO-004`, `AC-HOST-001` |
| Domain and current project knowledge | `AC-REQ-001` through `AC-REQ-003`, `AC-COMP-001`, `AC-DELIVERY-001` |
| Artifact codecs and encoding | `AC-ENC-001`, `AC-ART-001`, `AC-PROTO-003` |
| Publication and concurrency | `AC-STATE-001`, `AC-PROTO-005`, `AC-ABANDON-001` |
| Repository and Git observation | `AC-RUN-004`, `AC-ZONE-001`, `AC-BOUND-001` |
| Trace graph | `AC-TRACE-001` through `AC-TRACE-003`, `AC-COLLAB-003` |
| Process execution | `AC-CONFIG-003`, `AC-EXEC-001`, `AC-RED-001` |
| Context and host adapters | `AC-MODEL-001`, `AC-STAGE-001`, `AC-HOST-001`, `AC-HOST-002` |
| WAEGIS | `AC-WAEGIS-001` through `AC-WAEGIS-005` |
| Runtime and packages | `AC-PKG-001`, `AC-PKG-002`, `AC-RUNTIME-001`, `AC-PLATFORM-001`, `AC-OFFLINE-001` |

## 23. Implementation constraints and next deliverable

The Implementation Plan shall decompose this architecture into small vertical
slices. Each slice must:

- deliver an observable operation or invariant;
- name its Product Requirements and Acceptance scenarios;
- add focused failing tests before implementation where applicable;
- preserve the inward dependency direction;
- use only standard-library runtime dependencies;
- update the payload and documentation together; and
- avoid introducing dormant compatibility, migration, enforcement, or online
  infrastructure.

The first slice should establish the package skeleton, operation registry, flat
CLI dispatch, protocol result/envelope, deterministic services, repository-root
discovery, and atomic single-file publication. The sequence and completion
criteria are defined by `AEGIS_IMPLEMENTATION_PLAN.md`.
