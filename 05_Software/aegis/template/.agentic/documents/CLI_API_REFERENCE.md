<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0 CLI Reference

AEGIS uses a file-first interface designed to remain tractable for small local
models. Commands navigate work; generated schema-3 TOML and referenced Markdown
carry detailed content.

Use `aegis`, `python -m aegis`, or the repository wrappers:

```text
.\.agentic\tools\run.ps1 <group> <action>
bash .agentic/tools/run.sh <group> <action>
```

## Global Options

Only two global options exist:

```text
--run <run-id>   select a run without changing the worktree pointer
--json           emit stable JSON
```

They may appear before or after a grouped command. Default output always begins:

```text
status: <ok|blocked|failed>
stage: <stage-or-none>
artifact: <path-or-none>
next: <exact-command-or-none>
```

### Additional response keys by command

The four keys above are present on every response. Several commands add more,
depending on what they report:

| Key | Present on | Meaning |
|---|---|---|
| `run_profile` | `run status`; nested under `verification` on `verify run` and `verify status` | `"quick"` when the selected run used the proportional profile; absent otherwise. |
| `bypass_status` | `run status`; nested under `verification` on `verify run` and `verify status` | `"bypassed"` once a quick run's intake approval has closed. |
| `bypassed_stages` | Same as `bypass_status` | The four stages a quick run skips. |
| `readiness` | `run status` | Current stage state and readiness details. |
| `waived_blockers` | Nested inside `readiness` on `run status`, when present | The subset of stage blockers currently covered by an active waiver. |
| `waived_gates` | `verify gates` | Gate-failure blockers currently covered by an active waiver. |
| `advisories` | Commands with a non-blocking finding to surface (for example an advisory scope violation) | Human-readable advisory text; never affects `status` or the exit code. |
| `eligible_blockers` | `waive list` | Every blocker ID currently eligible for `aegis waive add`, with its description and state digest. |
| `waiver_history` | `waive list` | Previously recorded waivers for the selected run, including stale ones. |

### Exit-code contract

```text
0   status: ok        — the command succeeded outright
1   status: blocked    — a typed AEGIS error or an unwaived blocking finding
                          (ConfigurationError, PersistenceError,
                          RequirementValidationError, RunResolutionError,
                          StageOperationError, or a non-zero verification result)
2   (argparse)          — malformed invocation: unknown group/action, missing
                          required argument, or an invalid choice
```

Only exit code 0 means proceed without inspecting the response body further;
1 and 2 both require reading `error` (exit 1) or the parser's own stderr
(exit 2) before retrying.

## Command Inventory

The complete top-level interface is:

```text
aegis run ...
aegis stage ...
aegis requirement ...
aegis check ...
aegis evidence ...
aegis waive ...
aegis verify ...
aegis delivery ...
aegis adoption ...
aegis config ...
```

Legacy AEGIS 1.x commands and mutation flags do not exist.

## Run

```text
aegis run start <feature|fix|change|adoption> [--quick]
aegis run status
aegis run context
aegis run resume
aegis run select <run-id>
aegis run list
aegis run abandon --reason "<text>"
```

`run start` creates and selects a draft run, prepares the intake form, and
returns its path. Put the statement, scope hints, and access mode in the form.
`--quick` selects the proportional profile and is valid only for `fix` and
`change`; feature and adoption starts return a typed blocked response before
run state is created.

`run context --json` is the read-only fresh-session bootstrap surface. Its
versioned response names only `AGENTS.md`, the current stage's router and
reference, the prepared primary form, and the immediately preceding retained
primary form when available. It excludes `graph.json`, `journal.jsonl`,
evidence, requirement indexes, reports, and full configuration. If a preceding
form is unavailable, `unavailable_previous_stage_artifacts` gives a reason and
recovery command. Use `run status` for detailed diagnostics, not normal
bootstrap.

When the current primary form is unavailable, `artifact` is `"none"` and
`unavailable_current_artifact` gives the sole safe recovery command. A missing
form from an already applied stage is recovered with `stage show`, never by
preparing a revision that would regress applied state.

After quick-run intake closes, `run status` reports `run_profile="quick"`,
`bypass_status="bypassed"`, and the four bypassed stages. The intake approval
also creates one `run.stages_bypassed` journal event with the human approver,
intake revision, reason, and stage list. The validation summary and delivery
report repeat this state; no surface reports bypassed work as passed.

## Stage Lifecycle

```text
aegis stage prepare
aegis stage add [--category <category>]
aegis stage show
aegis stage apply
aegis stage close [--approver <identity>]
```

- `prepare` creates or reconstructs the current form.
- `add` creates another CLI-identified requirement/check form. It is accepted
  at the `requirement`, `check`, and `component-adoption` stages, and rejected
  everywhere else. `--category` selects the requirement category (defaults to
  `functional`); ignored at the check stage. At `component-adoption` it mints
  a requirement form, which is how an adoption run records the behavior it
  found in existing code.
- `show` reports files, revision, readiness, and blockers.
- `apply` validates the entire stage directory before importing and does not
  advance.
- `close` is the explicit human approval action. It journals approval, advances,
  and prepares the next stage. `--approver` names who is attributed with the
  approval; when omitted it defaults to `Name <email>` from the repository's
  git identity, falling back to `"human"` when git has none configured.

The standard stages are:

```text
intake → alignment → requirement → design → check → implementation → validation → delivery
```

The quick `fix`/`change` profile declares a separate four-stage sequence:

```text
intake -> implementation -> validation -> delivery
```

Alignment, requirement, design, and check are absent from the executable
sequence and are explicitly journaled as `bypassed` when intake closes. Every
remaining stage still requires prepare, apply, and explicit human close.

Adoption retains its seven specialized stages and uses the same lifecycle.
Delivery closure marks the run complete; it never pushes, publishes, merges, or
creates a pull request.

Forms live below:

```text
.agentic/runs/<run-id>/stages/<stage>/
```

Their common `[control]` table carries a requested access-mode change and
rationale, optional human-approved routing to an earlier stage and rationale,
the stage summary, and unresolved questions.

### Where state lives

Run state is spread across a fixed set of files, all under
`.agentic/runs/<run-id>/` unless noted otherwise. No command output collects
this list, so it is worth having in one place:

| Path | Contents |
|---|---|
| `graph.json` | The authoritative run graph — stage records, checks, evidence, waivers, solution design pin, completion/outcome. Every command reads and writes through this file. |
| `journal.jsonl` | Append-only event log for the run: one JSON record per stage transition, evidence capture, waiver, and gate run. Never rewritten, only appended. |
| `design.md` | The human-authored solution design document once the design stage is prepared; its content digest is pinned by INV-10. |
| `report.md` | The delivery report generated for human handoff review. |
| `validation-summary.json` | `verify run`'s persisted verdict: per-invariant results, gate status by group, and (for quick runs) `run_profile`/`bypass_status`/`bypassed_stages`. |
| `stages/<stage>/*.toml` | Generated and imported stage forms — see "Stage Lifecycle" above. |
| `.agentic/.workspace/state/current_run` | Worktree-local pointer naming the selected run ID; not part of the run directory and not tracked by Git — see `.gitignore`. |

`.agentic/requirements/` is separate from all of the above: it is the durable,
repository-wide requirement register, not run-local state, and survives every
run's completion.

## Requirements and Design

```text
aegis requirement list
aegis requirement show <id>
```

Requirement commands are read-only. Mutations occur only through requirement
stage forms. AEGIS generates UUID-backed IDs and durable companion specs.
Successful validation closure activates eligible Planned requirements.

Quick runs have no requirement, design, or ordinary check collection stage.
INV-1, INV-2, INV-8, and INV-10 report `not-applicable` with `holds=null`.
New quick runs evaluate INV-3 through their run-local checks; only a historical
quick graph without the persisted red/green policy reports INV-3 as
`legacy-not-applicable`.

The authoritative design is:

```text
.agentic/runs/<run-id>/design.md
```

`stage apply` records its digest and cited requirement snapshot digests.
`stage close` approves the proposal. Check and later stages require invariant
`INV-10`; changed design/requirement digests or earlier routing make approval
stale.

## Checks and Evidence

External mode:

```text
aegis check prepare
# run the immutable commands and complete evidence.toml
aegis check record
```

Managed mode:

```text
aegis check run
aegis check run <check-id>...
```

An explicit managed `check run` that resolves no check command exits non-zero
with `execution_status = "nothing-ran"`, `executed_count = 0`, and a reason. It
journals the outcome but creates no passing evidence. A launched command is
reported as an observed `pass` or `fail`; AEGIS does not infer zero collection
from a test framework's output.

The captured workspace policy permits one path. The wrong path returns the
configured mode and correct command. Check closure requires red evidence;
implementation closure requires prior red and current green evidence.

Quick runs have no ordinary check collection stage. New quick implementation
starts with `aegis check create`; fill the generated run-local definition and
run `aegis check register` before changing source. Its requirement and
specification citations are explicitly empty. Record a real red result, make
the repair, then record green through the external or managed path. The
implementation form must link every active green registered-check evidence ID;
manual, invented, superseded, red, or other-stage evidence is rejected.

External preparation and recording are valid only during check or
implementation, require a captured external mode and at least one imported
check, and require exactly one result row per immutable check ID and command.

A check whose stage evidence blocker already carries an active, exactly
matching waiver is excused and needs no row. `check prepare` omits it, and
`check record` measures completeness against the checks that remain. The
excused blocker is the one `waive list` offers for that stage:
`red-before-green:<check-id>` during check, and
`stage:implementation:<check-id>:green-evidence` during implementation. A
waiver that has gone stale excuses nothing, so its check owes a truthful
observation again. An excused check may not carry a result either: a waiver
records that the observation is unobtainable, so submitting one contradicts
the approval. Recording rejects such a row rather than accepting a fabricated
result. When every imported check is excused, both commands report that no
external check evidence is required; the stage closes on its waivers.

Recording validates the complete document before graph mutation. Permitted
surrounding whitespace in `result`, `summary`, and `output_log` is trimmed, and
the persisted result is the canonical `pass` or `fail` value that was
validated. Invalid or incomplete documents leave graph, journal, and form state
unchanged.

Recording a check again supersedes its older evidence rather than
accumulating beside it: a new observation retires prior active records with
the same result, and a genuine pass additionally retires earlier failed
attempts from the implementation, validation, and delivery stages. The
check-stage red witness is never retired by a pass — red-before-green keeps
its active red — and a new failure never retires an older pass, so a genuine
regression stays visible to verification. Superseded records remain in the
graph with a reference to the record that replaced them.

Reapplying the check stage preserves the evidence links of every check whose
identity and command are unchanged; their red/green state is re-derived from
the active evidence the graph already holds. A check whose command changed
returns to `unknown` with no links, because existing evidence no longer
proves anything about the new definition.

Manual evidence:

```text
aegis evidence prepare <add|supersede>
aegis evidence apply
aegis evidence show
```

## Run-Local Waivers

```text
aegis waive add <blocker-id> --reason "<human-approved reason>"
aegis waive list
```

`waive list` reports the currently eligible exact blocker IDs, active waivers,
the waivers that have gone stale, and the complete run-local waiver history
classified as `active`, `stale`, or `inactive`. Eligible IDs include failing
invariants such as `INV-10`, enforced gate failures such as `gate:test`,
per-check red-before-green failures such as `red-before-green:<check-id>`, and
exact stage, traceability, coverage, and working-tree findings.

A waiver whose pinned state has moved leaves `active_waivers` and appears under
`stale_waivers`, so the blocker returning is always accompanied by the record
that stopped covering it.

`INV-7` reports the `blocking` policy it enforces. It previously carried a
legacy `non-waivable` label while being offered by `waive list` and accepted by
`waive add`; the secrets scan matches unanchored substrings over whole changed
files, so it needs the escape hatch every other blocking rule has.

`waive add <blocker-id> --reason "<reason>" [--approver <identity>]` records one
explicit human approval. The reason must contain non-whitespace text, the
blocker must be currently eligible, and the ID must be exact; wildcard, bulk,
and force forms do not exist. `--approver` names who is attributed with the
approval; when omitted it defaults to `Name <email>` from the repository's git
identity, falling back to `"human"` when git has none configured. The CLI
mints a `WVR-<uuid>` ID, appends the schema-3 waiver record to the selected
run graph, and appends a separate `waiver.added` journal event.

Every waiver is scoped to the selected run. It also stores the current blocker
state digests, so a later change to pinned content makes the record stale and
the blocker returns. For example, an `INV-10` waiver no longer applies after
the approved design or one of its cited requirement snapshots changes.

A waiver neutralizes blocking behavior without rewriting history. The
invariant still has `holds=false`, a gate still has failed evidence, and audit
findings remain present. Machine summaries and `report.md` render the item as
`WAIVED` and include its reason and timestamp; they never render it as passed.
Disabled gates remain `disabled`, not passed or waived.

The exact non-waivable integrity floor is:

- malformed, unsupported, or closed-schema workflow, graph, stage, evidence,
  requirement, or integration state, including corrupted run identity or
  selection data;
- live persistence-lock conflicts (`PERSISTENCE-LOCK-TIMEOUT`);
- stale graph mutations (`GRAPH-STALE-UPDATE`);
- stale requirement mutations (`REQUIREMENT-STALE-UPDATE`); and
- atomic-publication or journal-integrity failures.

These failures protect data rather than process and therefore never appear as
eligible blocker IDs. Correct the state or retry the operation. A waiver also
does not synthesize an applied stage or shorten the lifecycle. Only an eligible
run started explicitly with `--quick` uses the declared shorter lifecycle.

## Deterministic Verification

```text
aegis verify run
aegis verify status
aegis verify gates [build|typecheck|lint|test|security]...
aegis verify invariants
aegis verify traceability
aegis verify coverage
aegis verify impact [paths-file]
aegis verify impact [paths-file] --run
aegis verify working-tree
```

`verify run` performs impact/regression selection, all enabled gates in the
fixed order shown above, invariants, traceability, coverage, working-tree review,
and then writes a validation summary for the human diff review. Every enabled
group executes even if an earlier group fails. Disabled groups are reported
`not-enforced`, never `passed`. Waived failures are reported `waived` with their
original failed state, reason, and timestamp; they are never reported `passed`.

`verify gates [names...]` is an explicit execution request. If every selected
group is disabled and no command launches, it exits non-zero and reports
`execution_status = "nothing-ran"`, `executed_count = 0`, and a reason in both
JSON and plain output (`NOTHING RAN`). It writes an outcome journal event and
no passing evidence. This does not change aggregate `verify run`: disabled
groups there remain `not-enforced`, and its other audits still run normally.

For a quick run, requirement/check traceability and coverage audits, plus
INV-1, INV-2, INV-8, and INV-10, report `not-applicable - quick run` and cannot
become pass results or waiver targets. New quick runs evaluate INV-3 from their
registered red/green evidence; legacy graphs retain the explicit N/A result.
Impact analysis, enabled gates, the secrets scan, remaining invariants, scope
advisory, and working-tree review still execute. The summary includes the quick
profile and the explicit bypassed-stage list.

`verify impact` without `--run` is reporting-only. With `--run`, AEGIS builds a
stable union of linked selectors and appends them as individual argv entries to
`[gates.test].impacted_command`; it never interpolates them into a shell
command. Any uncovered source, requirement without a linked test, unsafe
selector, empty selection, or missing focused prefix selects `full-fallback`
and runs every configured full test command instead. The response and journal
name `focused` or `full-fallback`, the selectors, and the precise fallback
reason. If neither route can launch a command, the explicit request returns
non-zero `nothing-ran`.

The security group runs only explicitly configured deterministic tooling. Its
result is evidence from that tooling, not an authoritative security-assurance
claim.

## Delivery, Adoption, and Configuration

```text
aegis delivery show
aegis delivery report

aegis adoption component-status
aegis adoption scope-check <path>...
aegis adoption baseline
aegis adoption coverage-waivers [--write]

aegis config validate
aegis config show
```

`scope-check` reports `enforcement` (`enforced` or `not-enforced`) and
`minimum_completion_level` beside its `issues`, so a disabled component
baseline guard is distinguishable from a clean result. Its issue list carries
non-blocking advisories — `COMPONENT-GUARD-NOT-ENFORCED`,
`COMPONENT-PATH-UNMAPPED` (no component owns the path), and
`COMPONENT-PATH-NOT-FOUND` (the path is not in the working tree) — alongside
the blocking `COMPONENT-BASELINE-MISSING`. Only blocking issues set the exit
code. `verify coverage` reports `audit_status = "not-enforced"` for the same
reason when `traceability.coverage.mode` is disabled.

`coverage-waivers` lists every coverable module with no Active test-linked
requirement that is not already waived. It writes nothing without `--write`,
which appends the list to the first requirement root's
`coverage_waivers.txt` under a comment naming the run it came from. Use it
immediately after enabling `traceability.coverage.mode`, so pre-existing
legacy modules do not have to be transcribed by hand; it reports nothing while
coverage is disabled, where the schema forbids coverable roots.

Configuration and run graphs require schema 3. AEGIS 3.0 rejects schema 2 and
earlier legacy graphs without migration or fallback.

The schema-3 run graph has an additive `profile` field: its absence means
`full`, preserving existing graphs and full-run serialization; `quick` is valid
only with `fix` or `change`. Hand-edited kind/profile/stage *mismatches* — a
stage name invalid for the run's kind/profile, or stage records that conflict
with it — return a typed stage-operation block. This is not tamper-proofing
against a hostile user (per policy, out of scope — see "What is working and
should not be touched"); it exists so a genuine authoring mistake fails loudly
rather than corrupting state.

That check does not by itself catch a hand-edit that *jumps* `graph.stage`
forward to a stage the schema does consider legitimate for that kind/profile,
skipping the stages between (for example editing `"stage": "intake"` directly
to `"stage": "delivery"`). What actually stops that case from completing a run
with zero recorded work is a second, independent mechanism: `stage close` at
`delivery` and `adoption-delivery` re-checks every blocking invariant and
refuses to close while one fails un-waived (B18, 2026-08-04) — so a jump to
delivery with no requirement, check, or evidence work done fails on INV-6 (and
usually others) at the close attempt, even though the jump itself was never
independently detected.

The optional proportionality policy is:

```toml
[quick.changed_paths]
mode = "advise"
max_paths = 10
```

Modes are `disabled` and `advise`; `max_paths` is a positive integer. If the
table is absent, the effective ship-open default is `disabled` with threshold
10. In `advise` mode, closing quick-run implementation with more than the
configured number of unique changed paths returns `QUICK-SCOPE-ADVISORY` and
guidance to carry the context into `aegis run start <fix|change>`. It never
blocks, routes, or mutates the current run.

`config validate` validates the core workflow policy and remains available to
repair it even when the optional RepoWise policy is malformed. `config show`
validates and displays the optional schema-1
`.agentic/integrations/repowise.toml`; absence means disabled. RepoWise
execution intentionally has no AEGIS command. Separately managed external
tooling may produce its artifacts; AEGIS consumes only validated structural
data during `repo-discovery`. WAEGIS 3 does not manage RepoWise.

Expected AEGIS configuration, run-resolution, workflow, command-input,
requirement, persistence, and RepoWise integration failures produce the stable
`blocked` response and exit code 1. Argparse errors retain parser output and
exit code 2. Interrupts, explicit process exits, and unexpected programming
exceptions are not reclassified as governance blocks.
