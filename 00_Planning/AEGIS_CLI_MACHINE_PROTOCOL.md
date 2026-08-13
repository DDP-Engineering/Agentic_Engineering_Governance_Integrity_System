<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS CLI and Machine Protocol Contract

**Status:** Working draft  
**Product version:** 1  
**Protocol version:** 1  
**Last updated:** 2026-08-10  
**Authoritative requirements:** `AEGIS_PRODUCT_REQUIREMENTS.md`  
**Functional behavior:** `AEGIS_FUNCTIONAL_SPECIFICATION.md`  
**Artifact design:** `AEGIS_ARTIFACT_MODEL.md`

## 1. Purpose and relationship

This document defines how humans, AI agents, host adapters, and WAEGIS invoke
AEGIS behavior. It specifies command organization, atomic operation boundaries,
machine input and output, error and exit-code semantics, and clean architecture
constraints.

Only `PR-*` entries in the Product Requirements Register are product
requirements. The `CP-*` identifiers below are protocol contract rules. Exact
Python modules and class names remain technical-architecture decisions.

The protocol is optimized for local models with limited instruction-following
capacity:

- one invocation requests one use case;
- one mutating invocation requests one primary domain action;
- machine mode never prompts;
- names, fields, enums, and response order remain stable;
- long detail stays in repository artifacts; and
- the response gives a small set of immediate atomic next actions.

**Implements:** `PR-PROTO`, `PR-MODEL`, `PR-HOST`, `PR-CONFIG`, `PR-ENC`,
`PR-STATE`, `PR-RUN`, `PR-ESCAPE`

## 2. Protocol principles

- **CP-PRINCIPLE-001:** A command represents one named application use case and
  never asks the caller to perform several workflow actions in one instruction.
- **CP-PRINCIPLE-002:** No command automatically completes multiple Stages or
  silently advances the Run through another Stage.
- **CP-PRINCIPLE-003:** A Run-scoped command identifies exactly one Run.
- **CP-PRINCIPLE-004:** A mutating command performs at most one domain action,
  such as recording one finding, completing one Stage, or changing one profile.
- **CP-PRINCIPLE-005:** A cohesive action may publish several files atomically
  when the Artifact Model requires them to represent one state transition.
- **CP-PRINCIPLE-006:** Defaults reduce arguments but never conceal which Run,
  Stage, command, outcome, or artifact was used.
- **CP-PRINCIPLE-007:** Machine responses use exact enums and identifiers rather
  than relying on prose interpretation.
- **CP-PRINCIPLE-008:** Every machine response identifies the next valid atomic
  actions or states that no immediate action is available.
- **CP-PRINCIPLE-009:** Findings and unfavorable engineering outcomes are
  results, not protocol failures.
- **CP-PRINCIPLE-010:** An operational error means AEGIS could not understand,
  perform, or durably record the requested use case.

## 3. Invocation model

### 3.1 Executables

```text
aegis [global options] <command> [command options]
waegis [global options] <command> [command options]
```

- **CP-INVOKE-001:** `aegis` exposes repository workflow operations.
- **CP-INVOKE-002:** `waegis` exposes operator lifecycle operations and remains
  a separate executable and package.
- **CP-INVOKE-003:** AEGIS and WAEGIS use the same response envelope and error
  vocabulary without requiring one package to import the other's runtime code.
- **CP-INVOKE-004:** A canonical CLI command shall be one lowercase token. A
  domain and action within that token shall be separated by hyphens, such as
  `run-list`, `stage-complete`, or `requirement-validate`.
- **CP-INVOKE-005:** The CLI shall have no nested command tree, underscore
  spellings, or compatibility aliases. Dotted operation identifiers remain the
  machine-protocol names and are not CLI syntax. The canonical CLI token is
  derived by replacing each dot and underscore in the operation identifier with
  a hyphen.

### 3.2 Global options

| Option | Meaning | Default |
|---|---|---|
| `--repo <path>` | Target repository root. | Current directory, resolved upward according to repository discovery rules. |
| `--format human\|json` | Output representation. | `human` |
| `--protocol-version <integer>` | Requested machine protocol version. | Latest version supported by this product version. |
| `--no-color` | Disable ANSI formatting in human output. | Color follows terminal capability. |
| `--expected-revision <sha256>` | Optimistic-concurrency token for a mutable target previously read by the caller. | Required for applicable machine-mode mutations. |
| `--help` | Show bounded help for the selected command. | Not applicable. |

- **CP-INVOKE-006:** `--format json` selects machine mode.
- **CP-INVOKE-007:** Machine mode is non-interactive. Missing information returns
  a structured error and one or more atomic corrective actions.
- **CP-INVOKE-008:** Machine mode emits no ANSI escape sequences, progress bars,
  prompts, headings, or explanatory text outside the response object.
- **CP-INVOKE-009:** Global options retain the same spelling across AEGIS and
  WAEGIS where they have the same meaning.
- **CP-INVOKE-010:** `<command> --help` returns bounded help for that exact
  command. Executable-level `--help` returns a bounded command catalog.

Examples:

```text
aegis run-list
aegis run-create --input ticket.json
aegis stage-show
aegis stage-set-section --input stage-section.json
aegis requirement-validate --requirement REQ-<32hex>
aegis --format json stage-show
waegis install-plan --target <path> --output install-plan.json
```

### 3.3 Run and Stage selection

- **CP-SELECT-001:** `<configured-runs-root>/context.toml`, defaulting to
  `.agentic/runs/context.toml`, stores at most one selected Run identity for the
  current working copy. Routine Run-scoped commands use that selection without
  requiring `--run`.
- **CP-SELECT-002:** The context pointer is local, non-authoritative, excluded
  from version control, and disposable. Every durable Run and Stage fact remains
  inside the selected Run directory.
- **CP-SELECT-003:** `run.create` selects the created Run. `run.select` changes
  the pointer atomically without changing either the previously selected Run or
  the newly selected Run. Delivery or abandonment clears the pointer when it
  still identifies the terminal Run.
- **CP-SELECT-004:** Stage-scoped commands use `current_stage` from the selected
  Run's `run.md` without requiring `--stage`. A command that starts or revisits
  another Stage updates `current_stage` through the Stage transition.
- **CP-SELECT-005:** Stage names are `intake`, `alignment`, `requirement`,
  `design`, `check`, `implementation`, `validation`, and `delivery`.
- **CP-SELECT-006:** `run.select` requires a complete canonical active Run
  identity. If no valid Run is selected, AEGIS selects and reports the sole
  active candidate or returns `ambiguous_run` with multiple candidates without
  changing state.

### 3.4 Rich and multiline input

Complex input uses:

```text
--input <repository-or-filesystem-path>
--input -
```

`--input -` reads UTF-8 JSON from standard input.

- **CP-INPUT-001:** Simple scalar values may use named options.
- **CP-INPUT-002:** Multiline text and structured records use an operation-
  specific JSON input object to avoid shell quoting and platform differences.
- **CP-INPUT-003:** A caller cannot provide the same field through both a named
  option and `--input`.
- **CP-INPUT-004:** Machine input declares its schema version and operation.
- **CP-INPUT-005:** The operation declared by the input must match the invoked
  flat command.
- **CP-INPUT-006:** Unknown required fields, wrong types, invalid enums, and
  conflicting sources return `invalid_input` without changing repository state.

Example input:

```json
{
  "schema": "aegis.machine.input",
  "schema_version": 1,
  "operation": "stage.set_section",
  "data": {
    "section": "restated_ask",
    "content": "Add a durable retry outcome without hiding the earlier failure."
  }
}
```

## 4. Small-model interaction contract

- **CP-MODEL-001:** Help for a command gives one purpose statement, its
  required arguments, its optional arguments, its result, and one minimal
  example.
- **CP-MODEL-002:** Help does not combine separate workflow actions into a
  suggested compound command.
- **CP-MODEL-003:** Every error names the invalid field or state and gives the
  smallest corrective action available.
- **CP-MODEL-004:** `next_actions` contains immediate atomic operations, not a
  paragraph instructing the model to plan several steps.
- **CP-MODEL-005:** A normal response returns no more than three immediate next
  actions. Additional possibilities remain discoverable through the relevant
  `show` operation.
- **CP-MODEL-006:** List operations paginate rather than loading the complete
  Requirement, Component, Run, finding, or traceability register into output.
- **CP-MODEL-007:** Default list page size is 20. The response reports
  `has_more` and an opaque `next_cursor` when more results exist.
- **CP-MODEL-008:** Long command output, diagnostics, or findings are stored in
  or referenced from repository artifacts. The response retains a concise
  truthful result.
- **CP-MODEL-009:** Output-size management never changes the operation outcome
  or blocks Stage closure; truncation is explicit and recoverable through a
  reference or paginated query.
- **CP-MODEL-010:** Machine response field order is deterministic even though
  JSON consumers must not depend on object ordering.
- **CP-MODEL-011:** A host adapter exposes either one protocol-operation
  dispatcher or a small context-filtered tool set; it does not require a local
  model to choose from the entire command catalog on every turn.
- **CP-MODEL-012:** In checkpoint interaction, a Stage handoff response exposes
  one concise summary and the four human choices `continue`, `review`,
  `revise`, and `park`. These choices are interaction guidance, not a compound
  `next_actions` program for the agent to execute without user input.

## 5. AEGIS command catalog

The dotted operation identifier is the stable machine name. The CLI token is
the single canonical human invocation spelling. Each row is one use case.

### 5.1 Product and configuration

| Operation | CLI tokens | Action |
|---|---|---|
| `help.show` | `help-show [--operation <id>]` | Return bounded command or operation help. |
| `version.show` | `version-show` | Return product and protocol versions. |
| `config.show` | `config-show` | Return the resolved project configuration and the configuration artifact from which it was read. |
| `config.validate` | `config-validate` | Report configuration and configured-path findings. |
| `payload.verify` | `payload-verify` | Compare the installed payload with its manifest and report ownership findings. |

`help.show` and `version.show` are common to AEGIS and WAEGIS. Configuration and
payload operations apply to an installed AEGIS repository.

### 5.2 Run operations

| Operation | CLI tokens | Action |
|---|---|---|
| `run.create` | `run-create --input <source>` | Create one Run from ticket text and record the opening repository state. |
| `run.select` | `run-select <run-id>` | Select one Run as the working context for this working copy. |
| `run.list` | `run-list` | List compact Run identities and states and identify the selected Run, if any. |
| `run.show` | `run-show [--run <id>]` | Return the selected Run summary, or an explicitly identified Run for read-only inspection. |
| `run.set_profile` | `run-set-profile --profile <full\|short>` | Change the selected active Run profile under the allowed transition rules. |
| `run.abandon` | `run-abandon --input <source>` | Record one normal or exceptional abandonment action for the selected Run. |

- **CP-RUN-001:** `run.create` input contains exactly one of `ticket_text` or
  `ticket_path`. It defaults the profile to `full` and work type to `change` so
  ticket text remains the only required product input; Intake can refine the
  work type without changing the ticket. Its optional `interaction_mode` is
  `checkpoint` or `continuous` and defaults to `checkpoint`; a caller may send
  `continuous` only to represent an explicit developer instruction, preserved
  in `execution_instruction`.
- **CP-RUN-002:** Run creation may publish the Run summary, eight Stage files,
  initial repository baseline, and selected-context pointer as one cohesive
  creation transaction.
- **CP-RUN-003:** A successful `stage.complete` while Delivery is current
  performs the terminal Run transition as part of the same atomic publication.
  AEGIS exposes no separate Run-delivery command.
- **CP-RUN-004:** `run.abandon` records exactly one terminal abandonment and
  preserves existing work and evidence.

### 5.3 Scope

| Operation | CLI tokens | Action |
|---|---|---|
| `scope.revise` | `scope-revise --input <source>` | Append one scope change to the selected Run and identify affected work. |

- **CP-SCOPE-001:** `scope.revise` records one before-and-after decision with the
  actor, reason, and time.
- **CP-SCOPE-002:** `scope.revise` records the affected work but
  does not automatically revisit or complete affected Stages.

### 5.4 Stage operations

| Operation | CLI tokens | Action |
|---|---|---|
| `stage.show` | `stage-show [--run <id>] [--stage <name>]` | Return the current Stage instruction and state, or inspect an explicitly named Run or Stage without selecting it. |
| `stage.start` | `stage-start <stage-name>` | Start one pending Stage and make it current. |
| `stage.set_section` | `stage-set-section --input <source>` | Replace one named mutable prose section in the current Stage and append its event. |
| `stage.complete` | `stage-complete` | Evaluate expectations, record findings, and complete the current Stage; completing approved Delivery also marks the Run delivered. |
| `stage.skip` | `stage-skip --input <source>` | Record one approved skip and transition the current Stage to `skipped`. |
| `stage.revisit` | `stage-revisit <stage-name> --input <source>` | Record one reason, transition completed or skipped work to `active`, and make that Stage current. |

- **CP-STAGE-001:** `stage.show` returns the Stage's self-contained instruction
  together with its current-state summary, revision, and immediate next actions.
  Explicit read-only Run or Stage selection does not modify the working context.
- **CP-STAGE-002:** `stage.set_section` changes one allowed section and cannot
  replace front matter, identity, earlier event history, or another section.
  Ordinary factual context and handoff content are written through their named
  Stage sections; they have no separate entry operations.
- **CP-STAGE-003:** Allowed section names are declared by Stage schema so a
  misspelled or inapplicable section returns `invalid_input`.
- **CP-STAGE-004:** `stage.complete` can add findings discovered by completion
  evaluation but never launches a project command, approves the Stage, or starts
  the next Stage. When the selected Stage is Delivery and its approval is
  already recorded, completion atomically marks the Delivery Stage `completed`
  and the Run `delivered`, then clears the local pointer.
- **CP-STAGE-005:** `stage.skip` requires an actor and a non-empty reason and
  returns `invalid_transition` after the Stage work has been applied.
- **CP-STAGE-006:** Stage mutation returns the new artifact revision for
  optimistic concurrency.
- **CP-STAGE-007:** After an included non-Delivery Stage completes in
  checkpoint interaction, the response data contains its checkpoint summary
  and four human choices and does not recommend `stage.start` as an unattended
  next action. After the developer chooses continue, `stage.start` remains the
  atomic operation that begins the proposed next Stage.
- **CP-STAGE-008:** Review and park require no workflow mutation. Revise uses
  `stage.set_section` while the affected Stage is active or `stage.revisit`
  after it completed or was skipped.
- **CP-STAGE-009:** Delivery checkpoint data substitutes `approve_and_close`
  for `continue`. The agent calls `decision.add` and `stage.complete` only after
  that developer choice, unless the Run records explicit continuous mode.

### 5.5 Embedded Stage entries

These operations update append-only structured entries inside one Stage file.
Evidence states what happened, a finding states why it matters, and a decision
states what was chosen. They do not create standalone entry files.

| Operation | CLI tokens | Action |
|---|---|---|
| `evidence.add` | `evidence-add --input <source>` | Append one manual or imported evidence entry to the current Stage. |
| `finding.add` | `finding-add --input <source>` | Append one finding to the current Stage. |
| `finding.set_disposition` | `finding-set-disposition --finding <label> --input <source>` | Append one disposition decision in the current Stage. |
| `finding.waive` | `finding-waive --finding <label> --input <source>` | Append one waiver with its actor and reason in the current Stage. |
| `decision.add` | `decision-add --input <source>` | Append one approval, rejection, or approved exception to the current Stage. |
| `attachment.add` | `attachment-add --input <source>` | Import one supporting file into the selected Run and record it in the current Stage. |

- **CP-ENTRY-001:** Each invocation adds or changes one entry only.
- **CP-ENTRY-002:** An entry operation appends the Stage event before returning
  the new revision.
- **CP-ENTRY-003:** `evidence.add` cannot declare execution evidence passed or
  failed without the required command result fields.
- **CP-ENTRY-004:** `finding.set_disposition` preserves the original finding.
- **CP-ENTRY-005:** `decision.add` accepts `approved`, `rejected`, or
  `exception_approved` and records actor, target, reason or conditions, and time.
  `exception_approved` requires a mandatory reason, identifies the expectation
  that does not apply, and never records it as passed. Earlier decisions remain
  visible.
- **CP-ENTRY-006:** `attachment.add` copies content into the Run through atomic
  publication and never substitutes for a Stage conclusion.
- **CP-ENTRY-007:** An AI agent can record a decision and continue without a
  separate confirmation prompt only when the selected Run records explicit
  continuous-interaction delegation.

### 5.6 Requirements and Specifications

| Operation | CLI tokens | Action |
|---|---|---|
| `requirement.create` | `requirement-create --input <source>` | Create one Requirement artifact for the selected Run. |
| `requirement.update` | `requirement-update --requirement <id> --input <source>` | Update one Requirement artifact from the selected Run. |
| `requirement.delete` | `requirement-delete --requirement <id>` | Delete one Requirement and its dependent project-documentation links from the selected Run. |
| `requirement.show` | `requirement-show --requirement <id>` | Return one Requirement summary and traceability. |
| `requirement.list` | `requirement-list` | List compact Requirement summaries. |
| `requirement.validate` | `requirement-validate --requirement <id>` | Report schema and relationship findings for one Requirement. |
| `specification.set` | `specification-set --requirement <id> --input <source>` | Create or update the optional Specification from the selected Run. |
| `specification.delete` | `specification-delete --requirement <id>` | Delete the optional Specification and clear its Requirement link from the selected Run. |

- **CP-REQUIREMENT-001:** Creation accepts one structured behavior field. More
  than one supplied behavior item is invalid input; semantic ambiguity inside
  prose produces a finding for a recorded decision rather than an invented
  split.
- **CP-REQUIREMENT-002:** Mutations use the selected Run as their source context;
  Requirement reads do not require a selected Run.
- **CP-REQUIREMENT-003:** Requirement and Specification mutations atomically
  publish the resulting current project state before recording the action in
  the active Stage.
- **CP-REQUIREMENT-004:** `requirement.validate` reports findings and does not
  change the Requirement.
- **CP-REQUIREMENT-005:** `requirement.update` and `specification.set` replace
  the authoritative current project content without creating a historical copy.
- **CP-REQUIREMENT-006:** `requirement.delete` atomically deletes the Requirement
  and its optional Specification and removes references to the Requirement from
  current Component documents. It records the deletion in the current Stage but
  creates no retirement artifact or tombstone.
- **CP-REQUIREMENT-007:** `specification.delete` atomically deletes the
  Specification and clears the Specification path in its Requirement.
- **CP-REQUIREMENT-008:** Requirement and Specification deletion never
  implicitly deletes executable source or test files.

### 5.7 Components

| Operation | CLI tokens | Action |
|---|---|---|
| `component.create` | `component-create --input <source>` | Create one Component artifact for the selected Run. |
| `component.update` | `component-update --component <id> --input <source>` | Update one Component artifact and drift review from the selected Run. |
| `component.delete` | `component-delete --component <id>` | Delete one Component document from the selected Run. |
| `component.show` | `component-show --component <id>` | Return one concise Component context. |
| `component.list` | `component-list` | List compact Component summaries. |
| `component.validate` | `component-validate --component <id>` | Report file, Requirement, test, and drift findings. |
| `component.find` | `component-find --path <repository-path>` | Find Components containing or related to one path. |

- **CP-COMPONENT-001:** `component.show` is optimized as Intake context and does
  not include complete source content.
- **CP-COMPONENT-002:** `component.find` is read-only and returns uncertainty
  explicitly when no unique relationship exists.
- **CP-COMPONENT-003:** Updating behavior, interface, dependency, or file
  membership records the drift review result.
- **CP-COMPONENT-004:** `component.update` replaces the authoritative current
  Component content without creating a historical copy.
- **CP-COMPONENT-005:** `component.delete` records the deletion in the current
  Stage but creates no retirement artifact or tombstone and never implicitly
  deletes Requirements, source files, or tests.

### 5.8 Traceability and execution

| Operation | CLI tokens | Action |
|---|---|---|
| `trace.validate` | `trace-validate` | Report all cross-project and post-integration identity, Requirement, file, test, coverage, and Component findings. |
| `trace.impacted` | `trace-impacted --input <source>` | Compute and record one impacted-test selection for the selected Run. |
| `execution.list` | `execution-list [--stage <name>]` | List configured command guides and recorded command evidence for the current or named Stage in the selected Run. |

- **CP-EXECUTION-001:** `trace.impacted` records selection reasoning and either
  an impacted subset or a full-suite fallback in Validation Stage state.
- **CP-EXECUTION-002:** AEGIS has no operation that invokes a configured project
  command. The agent or developer runs a command using normal host tooling, then
  records the observed outcome through `evidence.add`.
- **CP-EXECUTION-003:** A test-command guide can be read with one previously
  recorded impacted selection. Lint and audit guides retain their configured
  arguments for the agent or developer.
- **CP-EXECUTION-004:** The agent or developer may run tests during Check or
  Implementation and may run tests, lints, and repository audits during
  Validation; AEGIS records the reported outcomes without invoking them.
- **CP-EXECUTION-005:** Test evidence reported during Check records relevant red
  fingerprints. Later reported test evidence compares current fingerprints and
  reports changed tests.
- **CP-EXECUTION-006:** Starting Check records the repository comparison point;
  completing Check reports implementation paths changed since that point.
- **CP-EXECUTION-007:** Evidence input records observed exit status, timeout,
  cancellation, or launch failure without asking AEGIS to control the process.
- **CP-EXECUTION-008:** The agent or developer may attach large external output;
  AEGIS stores the Attachment reference and a concise reported result in Stage
  evidence.

### 5.9 Adoption

| Operation | CLI tokens | Action |
|---|---|---|
| `adoption.create` | `adoption-create --input <source>` | Create one bounded Adoption journal. |
| `adoption.show` | `adoption-show --adoption <id>` | Return one Adoption resume summary. |
| `adoption.set_section` | `adoption-set-section --adoption <id> --input <source>` | Replace one Adoption section and append its event. |
| `adoption.complete` | `adoption-complete --adoption <id>` | Mark one Adoption completed after reporting remaining gaps. |
| `adoption.abandon` | `adoption-abandon --adoption <id> --input <source>` | Record one abandoned Adoption outcome. |

## 6. WAEGIS command catalog

WAEGIS mutations use explicit plan-then-apply operations. Planning is read-only;
applying one plan is one authorized lifecycle use case.

### 6.1 Repository initialization

| Operation | CLI tokens | Action |
|---|---|---|
| `repository_init.plan` | `repository-init-plan --target <path> --output <path>` | Preview local Git initialization and write the operator-owned plan outside the target. |
| `repository_init.apply` | `repository-init-apply --target <path> --plan <path> --confirm-digest <sha256>` | Apply the exact previewed local initialization. |

### 6.2 Installation

| Operation | CLI tokens | Action |
|---|---|---|
| `install.plan` | `install-plan --target <path> --output <path>` | Analyze the target and write an operator-owned installation plan without modifying the target. |
| `install.apply` | `install-apply --target <path> --plan <path> --confirm-digest <sha256>` | Apply the exact authorized installation plan. |

### 6.3 Upgrade and removal

| Operation | CLI tokens | Action |
|---|---|---|
| `upgrade.plan` | `upgrade-plan --target <path> --output <path>` | Preview payload replacement and write an operator-owned plan without modifying the target. |
| `upgrade.apply` | `upgrade-apply --target <path> --plan <path> --confirm-digest <sha256>` | Apply one authorized payload upgrade while preserving project data. |
| `remove.plan` | `remove-plan --target <path> --output <path>` | Preview payload removal and write an operator-owned plan without modifying the target. |
| `remove.apply` | `remove-apply --target <path> --plan <path> --confirm-digest <sha256>` | Remove only the exact authorized payload-owned paths. |

- **CP-WAEGIS-001:** Every apply operation verifies that the supplied plan
  digest matches the plan bytes and that the target has not changed in a way
  that invalidates the plan.
- **CP-WAEGIS-002:** A stale or mismatched plan returns `state_conflict` and
  instructs the caller to create a new plan.
- **CP-WAEGIS-003:** Machine mode treats `--confirm-digest` as explicit operator
  authorization and never opens an interactive confirmation.
- **CP-WAEGIS-004:** Plan and apply operations do not stage, commit, branch, tag,
  merge, push, or create pull requests.
- **CP-WAEGIS-005:** Installation configuration contains detected project paths
  and validation command guides or the applicable shipped defaults, and keeps
  the working-context pointer excluded from version control.
- **CP-WAEGIS-006:** Upgrade and removal operate only on manifest-owned payload
  paths and preserve repository-owned data.

## 7. Optimistic concurrency and revisions

- **CP-REVISION-001:** Every mutable Run, Stage, Requirement, Specification,
  Component, and Adoption response includes a content revision digest while the
  target exists.
- **CP-REVISION-002:** A machine caller that read a mutable artifact supplies
  `--expected-revision <sha256>` on a later mutation of that artifact.
- **CP-REVISION-003:** A mismatched revision returns `state_conflict`, preserves
  both existing and caller-supplied information, and proposes a new read action.
- **CP-REVISION-004:** Create and append-only operations that cannot overwrite an
  observed mutable value do not require an expected revision.
- **CP-REVISION-005:** Revision digests are concurrency tokens, not evidence
  fingerprints or cryptographic identity guarantees.
- **CP-REVISION-006:** Successful mutation returns the new revision after atomic
  publication when the target remains. Successful deletion returns a null
  target revision and a `deleted` artifact action.

## 8. Machine response envelope

### 8.1 Encoding and transport

- **CP-RESPONSE-001:** Machine output is one compact JSON object followed by one
  LF character on standard output.
- **CP-RESPONSE-002:** Machine output uses UTF-8 without a byte-order mark.
- **CP-RESPONSE-003:** Standard error remains empty in machine mode whenever the
  AEGIS process starts sufficiently to produce a protocol response.
- **CP-RESPONSE-004:** Caller-reported project-command output never interleaves
  with the JSON response; fuller output is referenced through an Attachment.
- **CP-RESPONSE-005:** JSON uses strings for UUIDs, timestamps, paths, digests,
  enums, and integer-sized values whose representation must remain stable.
- **CP-RESPONSE-006:** Repository paths in data use repository-relative `/`
  separators. The explicitly selected repository root can be returned as an
  absolute platform path.

### 8.2 Required envelope

Every response contains these fields with stable types:

```json
{
  "schema": "aegis.machine.response",
  "schema_version": 1,
  "product": "AEGIS",
  "product_version": "1.0.0",
  "operation": "stage.show",
  "operation_id": "OP-d9428888f2d64e6f9c2d70e1965815b7",
  "operation_status": "completed",
  "run_id": "RUN-78aa94df7bbb4d548a83b54c05a2677a",
  "stage": "intake",
  "revision": "sha256:<64-lowercase-hex>",
  "outcome": null,
  "message": "Intake is active.",
  "data": {},
  "findings": [],
  "artifacts": [],
  "next_actions": [],
  "error": null,
  "truncated": false,
  "details_ref": null
}
```

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | Constant response family name. |
| `schema_version` | integer | Machine response version. |
| `product` | string | `AEGIS` or `WAEGIS`. |
| `product_version` | string | Installed product version. |
| `operation` | string | Stable operation identifier from the catalogs. |
| `operation_id` | string | UUIDv4 identity for this invocation result. |
| `operation_status` | string | `completed` or `error`. |
| `run_id` | string or null | Selected Run when applicable. |
| `stage` | string or null | Selected Stage when applicable. |
| `revision` | string or null | Current or newly published content revision. |
| `outcome` | string or null | Domain outcome when the operation defines one. |
| `message` | string | One concise factual summary. |
| `data` | object | Operation-specific bounded result. |
| `findings` | array | Bounded finding summaries. |
| `artifacts` | array | Artifacts read, created, or changed. |
| `next_actions` | array | Zero to three atomic action descriptors. |
| `error` | object or null | Structured operational error. |
| `truncated` | boolean | Whether bounded arrays or detail have more data. |
| `details_ref` | string or null | Repository artifact or cursor for further detail. |

- **CP-RESPONSE-007:** All envelope fields are present even when their value is
  null, empty, or false.
- **CP-RESPONSE-008:** `operation_status = completed` means the use case was
  performed and any state change was durably recorded. It does not mean tests,
  lints, audits, findings, or intended work passed.
- **CP-RESPONSE-009:** `operation_status = error` means no requested state
  transition was claimed complete.
- **CP-RESPONSE-010:** `outcome` uses the domain enum defined for the operation;
  callers never infer it from `message`.

### 8.3 Finding summary

```json
{
  "label": "F1",
  "code": "test_changed_after_red",
  "severity": "warning",
  "summary": "tests/orders/test_service.py changed after red evidence.",
  "disposition": "open",
  "artifact": ".agentic/runs/RUN-.../06-implementation.md"
}
```

- **CP-FINDING-001:** Finding summaries use stable `code` values and concise
  human-readable `summary` values.
- **CP-FINDING-002:** Detailed observation, consequence, reasoning, and history
  remain in the owning Stage artifact.
- **CP-FINDING-003:** Findings can accompany a completed operation and exit code
  zero.

### 8.4 Artifact reference

```json
{
  "type": "stage",
  "id": null,
  "path": ".agentic/runs/RUN-.../06-implementation.md",
  "action": "updated",
  "revision": "sha256:<64-lowercase-hex>"
}
```

`action` is `read`, `created`, `updated`, `deleted`, or `verified`. A deleted
artifact has a null `revision` because no current target content remains.

### 8.5 Next action

```json
{
  "operation": "stage.set_section",
  "arguments": {
    "section": "restated_ask"
  },
  "reason": "Record the ticket restatement."
}
```

- **CP-NEXT-001:** Next actions identify an operation and structured arguments,
  not a shell command string.
- **CP-NEXT-002:** Each next action requests one use case.
- **CP-NEXT-003:** The response does not imply that suggested actions have been
  approved or performed.

## 9. Execution outcomes

Configured test, lint, and audit execution returns one outcome:

| Outcome | Process meaning | Engineering conclusion |
|---|---|---|
| `passed` | Command completed with configured success status. | Passed for the recorded invocation. |
| `failed` | Command completed with configured failure status. | Failed for the recorded invocation. |
| `timed_out` | The reported command exceeded its available time limit. | Unknown. |
| `cancelled` | The reported command was cancelled. | Unknown. |
| `launch_error` | The reported command could not start. | Unknown. |

- **CP-OUTCOME-001:** Every outcome above is a completed AEGIS operation when
  the attempt and result were durably recorded.
- **CP-OUTCOME-002:** All five outcomes therefore use process exit code zero for
  the AEGIS invocation and `operation_status = completed`.
- **CP-OUTCOME-003:** The engineering outcome appears in `outcome` and in Stage
  evidence; it is not encoded through the AEGIS process exit code.
- **CP-OUTCOME-004:** A retry receives a new operation identity and evidence
  entry and preserves the earlier attempt.
- **CP-OUTCOME-005:** Reported timeout and cancellation include the observed
  limit or cancelling actor and the available host observation.

Example of a durably recorded failing validation command:

```json
{
  "schema": "aegis.machine.response",
  "schema_version": 1,
  "product": "AEGIS",
  "product_version": "1.0.0",
  "operation": "evidence.add",
  "operation_id": "OP-d9428888f2d64e6f9c2d70e1965815b7",
  "operation_status": "completed",
  "run_id": "RUN-78aa94df7bbb4d548a83b54c05a2677a",
  "stage": "validation",
  "revision": "sha256:<64-lowercase-hex>",
  "outcome": "failed",
  "message": "Reported tests.project failure recorded as evidence.",
  "data": {
    "category": "tests",
    "name": "project",
    "exit_status": 1,
    "evidence_label": "E2"
  },
  "findings": [
    {
      "label": "F2",
      "code": "validation_failed",
      "severity": "high",
      "summary": "The selected project tests failed.",
      "disposition": "open",
      "artifact": ".agentic/runs/RUN-.../07-validation.md"
    }
  ],
  "artifacts": [],
  "next_actions": [
    {
      "operation": "stage.show",
      "arguments": {},
      "reason": "Review evidence and findings."
    }
  ],
  "error": null,
  "truncated": false,
  "details_ref": null
}
```

## 10. Structured errors

### 10.1 Error object

```json
{
  "code": "invalid_transition",
  "summary": "Implementation cannot start while Check is pending.",
  "field": "stage",
  "path": ".agentic/runs/RUN-.../05-check.md",
  "retryable": true,
  "details": {
    "current_status": "pending",
    "requested_status": "active"
  }
}
```

- **CP-ERROR-001:** Operator-producible input and repository state return a
  complete response envelope with a structured error instead of an unhandled
  traceback.
- **CP-ERROR-002:** `summary` is factual, short, and sufficient to choose a next
  action without parsing exception text.
- **CP-ERROR-003:** `details` is a bounded object with stable operation-specific
  fields.
- **CP-ERROR-004:** Internal diagnostics and tracebacks are not exposed as the
  machine protocol. The response contains only the stable error code, bounded
  safe detail, and recovery action available to the caller.
- **CP-ERROR-005:** An error response preserves the requested target state and
  does not claim a mutation completed.

### 10.2 Error codes

| Code | Meaning |
|---|---|
| `invalid_input` | Missing, malformed, conflicting, or unsupported caller input. |
| `not_found` | Requested repository object or configured command guide does not exist. |
| `ambiguous_run` | Run selection is required because several candidates exist. |
| `invalid_transition` | Requested domain transition is not valid from current state. |
| `state_conflict` | Expected revision, plan digest, or observed state is stale. |
| `malformed_state` | Required repository state cannot be parsed safely. |
| `unsupported_schema` | Artifact or protocol schema is newer or unsupported. |
| `capability_unavailable` | A recognized Should or Could operation is not included in the installed product edition. |
| `repository_error` | Repository root, path, or Git state cannot support the operation. |
| `missing_prerequisite` | Required local executable or runtime is unavailable. |
| `publication_failed` | The operation could not publish durable state atomically. |
| `internal_error` | An unexpected AEGIS defect prevented completion. |

- **CP-ERROR-006:** A project command reported as unable to launch uses the
  recorded evidence outcome `launch_error`, not `missing_prerequisite`.
- **CP-ERROR-007:** `missing_prerequisite` applies when the requested AEGIS or
  WAEGIS use case cannot begin or be recorded because a required local product
  prerequisite is absent.
- **CP-ERROR-008:** Policy findings do not use error codes.
- **CP-ERROR-009:** `version.show` reports available optional capabilities so a
  caller can avoid invoking a deferred operation.

## 11. Exit codes

| Exit code | Protocol meaning |
|---:|---|
| `0` | Operation completed and any result was durably recorded. Findings and unfavorable engineering outcomes may be present. |
| `2` | Invalid invocation or input. |
| `3` | Target not found or Run selection ambiguous. |
| `4` | Invalid transition, stale revision, malformed state, unsupported schema, or unavailable optional capability. |
| `5` | Repository problem or missing local prerequisite. |
| `6` | Durable publication failed. |
| `70` | Unexpected internal AEGIS or WAEGIS failure. |

- **CP-EXIT-001:** Exit codes classify protocol execution, not engineering
  quality.
- **CP-EXIT-002:** Passed, failed, timed-out, cancelled, and launch-error project
  commands all return AEGIS exit code zero after evidence is recorded.
- **CP-EXIT-003:** Human and machine modes use the same exit code for the same
  operation status.
- **CP-EXIT-004:** A process failure before Python or the AEGIS executable starts
  lies outside the protocol because AEGIS cannot emit a response.

## 12. Human output contract

- **CP-HUMAN-001:** Human output leads with the operation outcome and selected
  Run or target.
- **CP-HUMAN-002:** It then shows concise findings, changed artifacts, and
  immediate next actions.
- **CP-HUMAN-003:** A failed test is labeled as a recorded test failure, not an
  AEGIS command failure.
- **CP-HUMAN-004:** A timeout, cancellation, or launch error states that the
  engineering result is unknown.
- **CP-HUMAN-005:** Human output can use headings and color but communicates the
  same enums, counts, identities, paths, and outcome as machine output.
- **CP-HUMAN-006:** Detailed raw command output is shown only when explicitly
  requested or by opening its Attachment.

Example:

```text
Validation command recorded: tests.project -> failed
Run: RUN-78aa94df7bbb4d548a83b54c05a2677a
Stage: validation
Finding: F2 validation_failed
Evidence: E2 in .agentic/runs/RUN-.../07-validation.md
Next: review the Validation Stage
```

## 13. Clean architecture constraints

### 13.1 Dependency direction

| Boundary | Responsibility | May depend on |
|---|---|---|
| Domain | Run, Stage, Requirement, Component, evidence, finding, decision, transition, and outcome rules. | Python standard library and domain types only. |
| Application use cases | One service per protocol operation; authorization, orchestration, transaction boundary, and result construction. | Domain and declared ports. |
| Interface adapters | CLI parsing, JSON input/output, human presentation, and host translation. | Application use cases and protocol data types. |
| Infrastructure adapters | Filesystem publication, TOML/Markdown persistence, Git observation, hashing, clock, and UUID generation. | Declared ports and external operating-system facilities. |

- **CP-ARCH-001:** Dependencies point inward. Domain and application behavior do
  not import CLI parsers, host adapters, filesystem implementations, Git
  subprocesses, or presentation code.
- **CP-ARCH-002:** Each catalog operation maps to one application use-case
  service with one input type and one result type.
- **CP-ARCH-003:** CLI and host adapters translate transport only and contain no
  Stage, approval, evidence, finding, or Delivery policy.
- **CP-ARCH-004:** Artifact repositories expose load, validate, compare-revision,
  and atomic-publish ports rather than leaking filesystem operations into the
  domain.
- **CP-ARCH-005:** Git access is a read-only observation port for AEGIS workflow
  behavior. WAEGIS local initialization is a separate explicitly authorized
  infrastructure use case.
- **CP-ARCH-006:** AEGIS has no project-command process-runner port. Evidence
  recording preserves caller-observed outcomes without exposing host-process
  details to the domain.
- **CP-ARCH-007:** Clock, UUIDv4 generation, hashing, and platform path behavior
  enter through replaceable ports so domain and application tests remain
  deterministic.
- **CP-ARCH-008:** The machine response presenter consumes an application result
  and cannot reinterpret an unfavorable outcome as success or error.
- **CP-ARCH-009:** AEGIS and WAEGIS can share protocol definitions at build time
  while remaining independently runnable, standard-library-only packages.

### 13.2 Transaction boundaries

- **CP-ARCH-010:** One mutating use case owns one publication transaction.
- **CP-ARCH-011:** Project artifacts and Attachments are published before the
  Stage referencing them; the Stage is published before the Run summary.
- **CP-ARCH-012:** The application service returns completed only after every
  authoritative publication required by the use case is durable.
- **CP-ARCH-013:** On publication failure, earlier complete state remains
  authoritative and the result is `publication_failed`.
- **CP-ARCH-014:** Read-only operations never repair, normalize, or migrate state
  as a side effect.

### 13.3 Command registration

- **CP-ARCH-015:** Command names, operation identifiers, input schemas, output
  schemas, and help metadata are declared once and reused by parsing and help
  generation.
- **CP-ARCH-016:** Each operation shall have exactly one canonical flat command
  name. The registry shall declare no aliases.
- **CP-ARCH-017:** Host adapters invoke application use cases through the same
  operation identifiers used by the CLI.

## 14. Protocol versioning

- **CP-VERSION-001:** `schema_version` versions the response envelope separately
  from product and artifact versions.
- **CP-VERSION-002:** Adding an optional operation-specific `data` field can
  remain within a protocol version when its absence has a defined meaning.
- **CP-VERSION-003:** Removing a required field, changing its type, changing an
  enum's meaning, or changing error/exit semantics requires a protocol-version
  increment.
- **CP-VERSION-004:** Consumers ignore unknown optional fields within a supported
  version. AEGIS returns `unsupported_schema` when the caller requests a
  protocol version it cannot produce.
- **CP-VERSION-005:** Stable operation identifiers do not change within product
  version 1 without a documented protocol change.
- **CP-VERSION-006:** Human wording can improve without a protocol increment when
  machine fields and meaning remain unchanged.

## 15. Protocol acceptance scenarios

The Acceptance Plan must demonstrate at least:

1. Every catalog operation has one canonical flat, lowercase, hyphen-separated
   command that produces human output and a version-1 JSON response with the
   same operation meaning.
2. Machine mode never prompts and emits exactly one UTF-8 JSON line without
   command output or ANSI contamination.
3. A local-model client creates a Run from ticket text, obtains one Intake
   instruction, records one section, and receives one atomic next action at a
   time.
4. Missing Run selection with multiple active Runs returns `ambiguous_run` and
   candidate identities without changing state.
5. A stale expected revision returns `state_conflict` and preserves current
   state.
6. Stage completion records findings but does not execute validation, approve
   the Stage, or start another Stage.
7. Each embedded-entry command changes one Stage entry and preserves earlier
   history.
8. Requirement and Component reads work without Run selection; their mutations
   identify one source Run.
9. AEGIS never launches a project test, lint, audit, or validation command.
10. Passed, failed, timed-out, cancelled, and launch-error outcomes are recorded
    through evidence input and retain distinct `outcome` values.
11. Invalid input, invalid transition, missing prerequisite, publication
    failure, and internal failure return their documented structured error and
    exit code without a traceback response.
12. Large project-command output can be attached as evidence and does not expand
    the machine response unboundedly.
13. Paginated lists let a limited-context model inspect large Run, Requirement,
    Component, and finding sets without loading the complete register.
14. WAEGIS apply refuses a stale or altered plan as `state_conflict` and writes
    only after exact digest confirmation.
15. Windows and Ubuntu produce the same operation identifiers, response fields,
    enums, findings, and next-action meanings.
16. Host adapters invoke the same application use cases and cannot change
    workflow semantics.
17. An interrupted mutation leaves the prior complete state and returns or
    recovers as `publication_failed` without claiming completion.
18. Updating a Requirement, Specification, or Component replaces its current
    project content; deleting it leaves no retirement record, tombstone, or
    historical copy while the current Stage retains the deletion evidence.

## 16. Traceability

| Contract area | Product Requirements | Functional rules |
|---|---|---|
| Atomic commands and limited-model interaction | `PR-MODEL`, `PR-PROTO`, `PR-POSTURE` | `FS-CORE`, `FS-INTERFACE` |
| Run and Stage operations | `PR-WORKFLOW`, `PR-RUN`, `PR-SNAPSHOT`, `PR-ESCAPE` | `FS-RUN`, `FS-CONTEXT`, `FS-STAGE`, `FS-DURABLE` |
| Project artifacts and traceability | `PR-REQ`, `PR-COMP`, `PR-TRACE` | `FS-PROJECT`, `FS-TRACE` |
| Validation command guidance and outcomes | `PR-CONFIG`, `PR-RED`, `PR-INT` | `FS-CONFIG`, `FS-RESULT`, `FS-INTEGRITY` |
| Machine response and errors | `PR-PROTO`, `PR-ENC`, `PR-STATE` | `FS-INTERFACE`, `FS-EVIDENCE` |
| WAEGIS lifecycle | `PR-WAEGIS`, `PR-PAYLOAD`, `PR-DEFAULT` | `FS-INSTALL`, `FS-UPGRADE`, `FS-REMOVE` |
| Hosts and architecture boundaries | `PR-HOST`, `PR-RUNTIME`, `PR-MODEL` | `FS-INTERFACE`, `FS-ENV` |

The Acceptance Plan defines the required proof for this protocol, the Technical
Architecture defines its implementation boundaries, and the Implementation Plan
sequences its delivery. Implementation shall not change this protocol without
updating the Product Requirements, Functional Specification, and Artifact Model
where their owned meaning is affected.
