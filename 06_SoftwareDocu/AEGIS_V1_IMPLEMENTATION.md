<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS version 1 implementation

## Acceptance evidence inventory

`02_Tools/aegis_acceptance.py` delivers only the first IP-18 slice: a
standard-library record validator and report compiler. It does not execute or
claim Windows/Ubuntu, pytest/unittest, external/bundled, network-denied,
local-model, archive, or manual acceptance evidence. Those matrices remain
required before release acceptance.

The compiler is intentionally fail-closed: candidate identities, package and
environment records, retained evidence paths and digests, retry chronology,
per-requirement passing coverage, approved lower-priority deferrals, and matrix
dimensions must all validate before it can emit `accepted`.

The reviewed acceptance catalog carries explicit package and workflow matrix
cases. Evidence cannot satisfy a case by declaring free-form labels: the
compiler derives the case from the retained candidate package digest and exact
environment identity. The catalog also corrects the traceability omission of
`PR-SCOPE-002` by assigning it to the existing cross-platform differential
scenario, which is the behavior that demonstrates framework independence.

## Product boundaries

AEGIS is copied into `.agentic/aegis/` and owns that complete manifest-listed
payload. Every other `.agentic/` path is project-owned. WAEGIS is a separate
operator application and is never installed as part of the payload.

Both products keep domain and application policy inward of ports and concrete
filesystem, process, Git-observation, and presentation adapters. They copy the
small common machine-envelope contract locally so neither runtime imports the
other and no third runtime package is required.

## AEGIS state and publication

Run and Stage Markdown documents hold their own versioned metadata, current
sections, append-preserved events, evidence, findings, dispositions, decisions,
escapes, and attachment references. Requirements, Specifications, and
Components contain only current project knowledge. Deleting or replacing them
does not delete application source or tests; the owning Stage retains the
durable action evidence.

Run, Specification, and Component codecs render and parse the canonical
Markdown artifact shapes directly. Their TOML front matter carries compact
identity and relationship data, including Run Stage summaries and Component
test links. Their named Markdown sections carry the human-readable state; no
duplicate `state_json` copy is authoritative. Run transitions keep the Stage
summary and event history current, Intake and Alignment sections update the Run
intent and scope, and project-knowledge operations maintain the Run's linked
Requirement and Component identities. Component inputs describe every member
file's role and every linked test's purpose.

Stage completion delegates recorded-state policy to a pure expectation
evaluator. Its explicit matrix contains every canonical section for all eight
full-profile Stages; the short profile removes only Design. Initial `None`,
empty, `unknown`, `not recorded`, and `pending` section values remain visible
as one stable Stage/section finding each. Check evaluates ordered automated test
evidence, immutable exact-byte fingerprints, Implementation start time, and the
latest `red_before_green` decision. It distinguishes missing, incomplete, late,
and unexpectedly passing red evidence; a complete `exception_approved` becomes
an informational `not_applicable` finding and never a pass. Alignment,
Requirement, and full-profile Design also report when no current target has an
approved latest decision. Implementation requires green test evidence unless
Check recorded that valid exception. Validation compares recorded outcomes
with the configured command identities.

The evaluator has no workspace, filesystem, Git, or process port. The
application service validates a caller-supplied stale Stage revision before
invoking it, assigns the next unused `F<n>` label, preserves equivalent open or
accepted earlier findings on revisit, and combines new expectation facts with
the existing read-only Check Git-comparison findings. One existing publication
transaction then writes the complete Stage findings/history and Run summary;
approved Delivery additionally clears the local pointer in that same
transaction. Completion neither records an approval nor starts the next Stage.

Stage resume assembly is a separate pure read-model service invoked only by
`stage.show`. It receives the already decoded Run and requested Stage, extracts
canonical Requirement and Component identities from their durable metadata and
state, loads those references through the workspace port, expands directly
linked Components by scanning at most 256 sorted Component documents, and then
adds the Requirements linked by the selected Components. The response includes
only that graph: bounded Requirement behavior/confirmation/file/test data,
optional bounded Specification sections, bounded Component purpose/interface/
file/Requirement/test data, and the derived file/test union. It never emits the
complete project registers.

The read model also returns bounded Run intent/scope/handoff and Stage sections,
evidence, findings, decisions, escapes, attachments, and events. Optional
`.agentic/rules.md` is `present`, `absent`, or `unreadable`; absence selects
shipped rules normally. Configured commands are filtered by Stage: Check and
Implementation receive tests, Validation and Delivery receive tests/lints/
audits, and earlier Stages receive no command vectors. Test roots and advisory
risk/protected-path configuration remain visible for every Stage. Common
secret-bearing command options and values are redacted before presentation.

Every text wrapper carries character totals and every collection wrapper
carries item totals, returned counts, omitted counts, and `truncated`. Stable
identity/path ordering and persisted event ordering make repeated reads
deterministic. The profile-specific budget map is returned with the data: full
allows 16 Requirements, 12 Components, 64 affected files/tests, and 24
commands; short allows 8, 6, 32, and 12. Full/short text caps are respectively
3,000/1,500 for Run fields, 12,000/8,000 for the Stage instruction,
3,000/1,500 per Stage section, 2,000/1,000 per project-artifact text field, and
8,000/4,000 for project rules. The same map declares entry, relationship,
opening-path, protected-pattern, and finding caps.

Missing Requirement, Specification, Component, source, or test paths produce
stable resume findings; unavailable project artifacts retain their identity and
path in the response. Incomplete Component drift review produces a stale-
context finding, and tests outside configured roots remain visible with an
uncertain-coverage finding. A bounded Component scan reports its total, scanned,
and omitted counts, so a large repository never implies a complete graph when
discovery was capped. Any omission sets the machine envelope's `truncated`
flag and points `details_ref` to the durable Stage snapshot. Assembly does not
publish, execute a process, access a network, observe live Git state, or alter
the selected context; explicit historical Run/Stage reads use the same schema.

Delivery closure reads append-preserved decisions in reverse order and accepts
only a latest applicable `delivery` decision of `approved`; a later rejection
therefore keeps the Stage and Run active. Impacted-test computation validates
each linked path and selector at selection time. Missing or repository-unsafe
tests, tests outside every configured root, and option-like or malformed
selectors are omitted from the executable subset and cause an explained
full-suite fallback. The dotted `stage.show` identifier remains the machine
operation, while shipped native-host command guidance uses the flat
`stage-show` CLI token.

Application mutation seams validate that the selected current Stage is active
before they publish project knowledge, Stage entries, attachments, trace
selections, execution evidence, or abandonment context. Stage lifecycle
operations retain their own transition rules, so `stage.revisit` remains the
explicit way to make completed or skipped work mutable again. Rejected
mutations do not publish either Stage or Run bytes, and execution rejection
occurs before the configured process is launched.

Every successful Run/Stage publication also performs a read-only repository
comparison against the Run opening snapshot. The Run retains the original
branch, HEAD, index, and classified dirty state; later paths are recorded as
observed with unknown authorship, never as Run-produced. An explicit
`scope.revise` `affected_work` path is the sole current adoption authority and
only adopts a path already observed for that Run. Repository branch, HEAD, or
index transitions remain non-blocking attribution findings. `run.show` and
`stage.show` are pure reads and cannot refresh or alter this durable state.

The Markdown codec owns one schema table for Run, Stage, Component,
Specification, Adoption, and exceptional Abandonment artifacts. Each version 1
reader accepts only exact integer schema `1`; unsupported versions and boolean
lookalikes become `unsupported_schema` without parsing another shape or
rewriting the source. Automated entries accepted through `evidence.add` require
the execution facts defined by the artifact contract: command or selector,
working directory, one of the five operational outcomes, a consistent exit
status, concise observed result, and an explicit list of tests covered by the
claim. Timestamping remains runtime-owned, and manual evidence keeps its
separate actor/procedure/expected/actual contract.

Mutations prepare exact before/after bytes below `.agentic/.runtime/`, validate
expected revisions under a working-copy lock, persist the commit decision, and
recover to a complete before-or-after state. Runtime material is transient and
never authoritative project data.

The central operation registry classifies every AEGIS and WAEGIS operation by
its machine-revision policy. JSON mutations that replace an observed value
require an explicit caller token: Run operations compare `run.md`; Stage
transitions, entries, attachments, impacted selections, and executions compare
the current or requested Stage file; Requirement updates/deletions and both
Specification operations compare the Requirement; Component and Adoption
mutations compare their own artifact. Normal abandonment compares `run.md`,
while exceptional abandonment remains available without a token because it
creates a separate record and preserves unreadable Run bytes.

Read-only operations, unique-identity creation, the disposable selected-Run
pointer, and WAEGIS's independent plan/digest lifecycle do not use this AEGIS
caller-revision rule. Human mode continues to use the revision loaded by the
use case when the caller does not supply one. In JSON mode, central dispatch
returns `invalid_input` before invoking a required mutation when the token is
missing. Existing publication comparison returns `state_conflict` for stale
tokens before transaction preparation. `execution.run` additionally compares
the Stage token before process launch, then retains the same token for its
atomic evidence publication.

Configured commands execute as argument arrays with `shell=False`, isolated
process groups, concurrently drained output, explicit timeout/cancellation,
and the five exact outcomes. Unfavorable project outcomes remain successful
AEGIS protocol records with truthful engineering conclusions.

## WAEGIS lifecycle

Every mutation has a read-only `*-plan` operation and a separate `*-apply`.
Plans are operator-owned JSON outside the target, enumerate exact writes or
deletions and ownership, and are authorized by the SHA-256 of their exact
bytes. Apply revalidates both the digest and target fingerprint before its
first target write. Interrupted filesystem publication rolls the same
authorized plan forward from WAEGIS-local recovery data.

Installation creates complete detected/default configuration, preserves
existing project data, and adds only local context/runtime exclusions. Upgrade
and removal use the installed payload manifest as the sole ownership boundary.
Only `repository-init-apply` can run Git, and that adapter exposes only local
`git init`.

## Release tooling and validation boundary

The standalone `02_Tools/build_aegis_release.py` script builds stable ZIP member
order, timestamps, bytes, prerequisites, and exact archive inventories, and can
inspect those archives without extracting them. Dependency-excluding Windows
and Ubuntu archive shapes are buildable from source. Dependency-including builds
refuse until `02_Tools/runtime_inputs.toml` contains real local Python 3.12 and
Git archives with exact versions and SHA-256 digests.

The repository does not retain a separate automated test package for this
maintenance script. Compilation and explicit build/inspect smoke commands check
the local tool path; supported-host, Ubuntu, private-runtime, network-denied,
and downstream-repository acceptance remain part of the later IP-18 campaign.
