<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Parallel-Branch Merge Simplification Plan

> Status: implementation plan; not yet implemented.
> Date: 2026-07-14.
> Target: `05_Software/aegis/` and `05_Software/aegis/template/`.
> Release target: AEGIS `1.0.0`. The requirement contract is intentionally
> breaking and will not preserve backward compatibility.

## 1. Outcome

Make AEGIS simple for humans and predictable for ADOR while eliminating routine
Git conflicts when two or three branches add requirements or select different
runs.

The normal human workflow remains:

```text
aegis start --kind change --statement "Describe the intended change"
aegis status
```

`.agentic/current_run` remains the local selector and becomes explicitly
Git-ignored in generated projects. Requirements become independent of workflow
runs, branches, commits, and GitHub/GitLab tickets. They use domain-based,
collision-resistant IDs and separate immutable revisions.

## 2. Ratified decisions

| ID | Decision | Consequence |
|---|---|---|
| D1 | Preserve `.agentic/current_run` as one plain-text run ID. | Human use and ADOR evidence lookup remain simple. |
| D2 | Ship a template-owned `.agentic/.gitignore`. | The selector and generated registries cannot create branch conflicts. |
| D3 | Keep `--run-id` optional. | Humans use the selector; automation may override it. |
| D4 | Do not introduce `--work-ref`, ticket arguments, or ticket-derived IDs. | AEGIS remains forge-neutral. |
| D5 | Use `REQ-<DOMAIN>-<ULID>`. | Parallel branches allocate IDs without coordination. |
| D6 | Do not store run, ticket, branch, or commit as requirement identity. | Requirements describe durable behavior. |
| D7 | Store one immutable Markdown file per requirement revision. | Independent additions merge cleanly and history stays readable. |
| D8 | Ignore generated registry caches and views. | Derived data cannot conflict or become stale committed state. |
| D9 | Audit canonical revisions directly. | Fresh-checkout CI does not need generated caches. |
| D10 | Retain Inactive and Obsolete requirements. | Humans can see and audit no-longer-active behavior. |
| D11 | Remove the old numeric/table format with no legacy parser or migration. | AEGIS 1.0 has one clear contract. |
| D12 | Preserve `.agentic/runs/<run-id>/` and its artifact names. | ADOR keeps its current evidence paths. |

## 3. Scope

### In scope

- Local current-run selection and run-switching commands.
- Optional explicit run targeting.
- Domain+ULID requirement IDs.
- Immutable per-requirement revisions.
- Human-readable requirement lifecycle, list, show, and history commands.
- Semantic detection of parallel revisions to the same requirement.
- Stateless traceability, coverage, registry, invariant, and delivery audits.
- AEGIS CLI, storage, hooks, tests, template instructions, skills, adapters,
  documentation, versions, and changelog.
- AEGIS-side tests for the current ADOR run/evidence contract.

### Out of scope

- GitHub, GitLab, Jira, or other work-item integration.
- Ticket/branch-derived run or requirement IDs.
- Automatic legacy-table conversion.
- Compatibility with `REQ-FUNC-001`, shared tables, or `Retired`.
- Cross-worktree global state.
- Multiple processes sharing one selector in one worktree; those processes must
  use `--run-id` or separate worktrees.
- ADOR changes unless compatibility tests prove they are necessary. Such work
  requires a separate coordinated change.

## 4. Current implementation findings

AEGIS `0.4.0` already reads and writes `.agentic/current_run` and stores
evidence under `.agentic/runs/<run-id>/`. The selector design is sound. The
development package ignores it, but the copied template does not ship an
equivalent scoped ignore rule.

Requirement conflicts come from:

- `REQ-<TYPE>-<integer>` and its shared next number;
- one Markdown table per requirement type;
- in-place activation of a table row;
- parallel allocation of the same number and edits to the same lines;
- generated JSON files, including current-run-derived `features.json`;
- registry audits that require generated files to exist.

Preserve the run selector; replace the shared requirement and registry surfaces.

## 5. Run-selection contract

### Filesystem

```text
.agentic/current_run                 local, ignored, one run ID plus newline
.agentic/runs/<run-id>/graph.json   committed run graph
.agentic/runs/<run-id>/journal.jsonl
.agentic/runs/<run-id>/report.md
```

Add `template/.agentic/.gitignore`:

```gitignore
/current_run
/registry/*.json
/registry/*.md
!/registry/.gitkeep
```

Do not ignore `.agentic/runs/`; run artifacts remain delivery evidence. Write
`current_run` atomically through a sibling temporary file and `os.replace`.

Resolve run-scoped commands in this order:

```text
1. Global --run-id <id>, when supplied.
2. .agentic/current_run.
3. A clear recovery error.
```

`--run-id` affects one invocation only and never rewrites the selector. A stale
selector after a branch switch must recommend `aegis run list`, `aegis run use
<id>`, or `aegis start ...`.

### CLI

Preserve:

```text
aegis start --kind feature|fix|change|adoption --statement "..."
```

Add:

```text
aegis run list [--json]
aegis run current [--json]
aegis run use <id>
aegis run clear
aegis --run-id <id> status
```

- `start` saves the graph, then selects it.
- `run list` shows ID, kind, stage, statement, update time, and current marker.
- `run use` validates the graph before changing the selector.
- `run clear` is idempotent.
- Existing run-scoped commands work without `--run-id`.
- `start`, `run *`, requirement commands, registry commands, traceability and
  coverage audits, and `impact` do not require an active run.
- No command requests or infers a forge ticket.

One worktree has one human-friendly current run. Parallel humans should use
separate worktrees or clones, each with its own ignored selector.

## 6. Durable requirement contract

### Identity

```text
REQ-<DOMAIN>-<ULID>
```

Example: `REQ-AUTH-01K0Z6W4J7N9A6D3X2M8Q5P1TR`.

- `DOMAIN` matches `[A-Z][A-Z0-9]{1,15}`.
- Generate ULIDs locally with the Python standard library.
- IDs include no run, ticket, date, branch, commit, or shared sequence.
- ID and domain are immutable.
- Moving behavior to another domain creates a new requirement and makes the old
  one Obsolete with a replacement link.
- `aegis requirement domains` reports observed domains; do not add a shared
  mutable domain registry.

### Canonical layout

```text
.agentic/requirements/
  README.md
  coverage_waivers.txt
  auth/
    REQ-AUTH-01K0Z6W4J7N9A6D3X2M8Q5P1TR/
      01K0Z6W4J8AP9Y2F6N7C3T5MQR.md
      01K0Z7A8M2X4V9B6D1H3Q5N8RC.md
```

Each revision filename is a ULID. Each file is a complete immutable snapshot
using Markdown with TOML front matter so Python 3.11 can parse it without an
extra dependency:

```markdown
+++
id = "REQ-AUTH-01K0Z6W4J7N9A6D3X2M8Q5P1TR"
domain = "AUTH"
revision = "01K0Z7A8M2X4V9B6D1H3Q5N8RC"
supersedes = ["01K0Z6W4J8AP9Y2F6N7C3T5MQR"]
status = "Active"
priority = "Must"
created_at = "2026-07-14T09:30:00Z"
revised_at = "2026-07-14T11:15:00Z"
related_components = ["services/auth"]
linked_tests = ["tests/test_auth.py::test_denies_expired_token"]
verification = "Automated pytest coverage"
status_reason = "Activation evidence passed"
superseded_by = []
+++

# Reject expired access tokens

The system must reject an expired access token before protected data is read.

## Rationale

Expired credentials must not authorize access.
```

Normal commands never edit or delete an older revision.

### Lifecycle

| Status | Meaning | Coverage effect |
|---|---|---|
| `Planned` | Intended but not proven. | Does not satisfy coverage. |
| `Active` | Current behavior with valid verification. | Satisfies coverage when links resolve. |
| `Inactive` | Temporarily not enforced; may be reactivated. | Does not satisfy coverage. |
| `Obsolete` | Permanently no longer required; terminal. | Does not satisfy coverage. |

```text
Planned  -> Active | Inactive | Obsolete
Active   -> Inactive | Obsolete
Inactive -> Active | Obsolete
Obsolete -> no transition
```

Every transition appends a revision. Active requires a resolvable linked test
or explicit manual verification. Inactive and Obsolete require a reason.
Obsolete may reference replacement requirements.

### Requirement CLI

```text
aegis requirement create --domain <domain> --statement "..." \
  [--title "..."] [--priority Must|Should|Could] \
  [--rationale "..."] [--component <component>]...

aegis requirement revise --id <id> [changed fields...]
aegis requirement activate --id <id> \
  [--linked-test <test-id>]... --verification "..."
aegis requirement deactivate --id <id> --reason "..."
aegis requirement obsolete --id <id> --reason "..." \
  [--superseded-by <requirement-id>]...
aegis requirement list [--domain <domain>] [--status <status>] [--json]
aegis requirement show --id <id> [--revision <revision-id>] [--json]
aegis requirement history --id <id> [--json]
aegis requirement domains [--json]
aegis requirement audit [--json]
```

`deactivate` creates an Inactive revision; it deletes nothing.

### Human visibility

- `requirement list` shows every current requirement by default, including
  Inactive and Obsolete.
- Status filters provide focused lists.
- `requirement show` displays reason, verification, and replacements.
- `requirement history` displays every revision chronologically.
- `aegis status` includes counts for all four statuses.
- `registry sync` generates an ignored `requirements.md` with four sections.
- Canonical revisions stay committed and browseable without the CLI.

## 7. Parallel revisions to one requirement

Different requirements merge as different paths. Parallel changes to one
requirement add unique revision files, so Git can merge them. The audit reports
`REQ-DIVERGENT-HEADS` when two revisions supersede the same previous head.

Resolve explicitly:

```text
aegis requirement reconcile --id <id> \
  --head <revision-a> --head <revision-b> \
  --statement "Resolved requirement text" \
  --reason "Reconciled parallel revisions"
```

The new revision supersedes both heads. Delivery stays blocked until one
resolved head exists.

Audits detect invalid IDs, path/metadata mismatch, duplicate revisions, unknown
predecessors, cycles, zero/divergent heads, illegal transitions, mutation of an
existing revision, missing reasons, unknown replacements, and Active
requirements without valid verification.

## 8. Registry redesign

Canonical committed data:

- requirement revisions and waivers;
- run graphs, journals, and reports;
- component knowledge and manifest.

Generated ignored data:

- `.agentic/registry/requirements.json`;
- `.agentic/registry/checks.json`;
- `.agentic/registry/components.json`;
- `.agentic/registry/requirements.md`.

Remove `features.json`. Runs may cite requirements, but the requirement registry
must not depend on the selected run.

- `registry sync` validates canonical sources and atomically generates views.
- `registry audit` validates canonical sources; missing caches are not errors.
- Traceability, coverage, invariants, impact, and preflight use the canonical or
  in-memory model.
- Fresh-checkout CI passes without `registry sync`.

## 9. ADOR compatibility

Preserve:

- `.agentic/current_run` containing one run ID;
- `.agentic/runs/<id>/graph.json`;
- `.agentic/runs/<id>/journal.jsonl`;
- `.agentic/runs/<id>/report.md`;
- status, invariants, gates, report, and preflight without a run argument;
- `requirement activate --id ...`;
- `registry sync`.

Add AEGIS contract tests that start a run without a ticket, verify the selector,
invoke the run commands without `--run-id`, and verify the evidence paths.
Perform a read-only compatibility review against current ADOR before release.
Do not change ADOR unless this exposes a real mismatch; then stop and create a
separate coordinated ADOR plan.

ADOR may continue using the selector in its isolated checkout/container.
`--run-id` is future hardening, not mandatory human workflow.

## 10. Breaking cutover

Remove numeric IDs/examples, shared tables, `Retired`, in-place row updates,
cache-required audits, `features.json`, and ticket/work-reference concepts.

Do not add a legacy parser, ID map, old-status aliases, automatic conversion, or
dual read/write. Legacy tables may only be detected to produce a clear AEGIS
1.0 error. Existing repositories must back up and deliberately re-author
requirements. WAEGIS must not hide this cutover.

## 11. Implementation work packages

### WP0 - Contract tests

Add failing tests for ignored selector behavior, run switching, explicit
override, stale recovery, ULIDs, revisions, lifecycle, obsolete visibility,
parallel additions, divergent heads/reconciliation, stateless registries, and
ADOR paths.

### WP1 - Local run selector

Change `template/.agentic/.gitignore`, `store.py`, `cli.py`, and workflow,
scaffold, and hook tests. Implement atomic selection, run discovery, global
override, run subcommands, one resolver, and stale diagnostics. Verify scaffold
copies the scoped ignore file without replacing the target root `.gitignore`.

### WP2 - Requirement storage and ULID

Rewrite `requirements.py` and optionally add one small `ulid.py`. Update the
requirements README, remove old register files, and rewrite traceability tests.
Implement stdlib ULIDs, front-matter parsing, recursive discovery, revision
graph/head resolution, the new template layout, and legacy rejection. Delete
the table parser/writer.

### WP3 - Lifecycle and human views

Implement create, revise, activate, deactivate, obsolete, list, show, history,
domains, audit, and reconcile. Append every mutation. Update status, reports,
and invariants so only verified Active requirements satisfy coverage while all
statuses remain visible.

### WP4 - Stateless registries and merge audits

Generate ignored views atomically, remove `features.json`, make audits and
preflight cache-independent, add divergent-head/immutability checks, and add a
two/three-branch merge simulation.

### WP5 - Instructions, skills, hooks, and adapters

Update template AGENTS/Claude/Qwen guidance, AEGIS development/delivery and
traceability skills, and Codex/Claude/Pi/OpenCode/Qwen prompts/tests. State that
work begins from a human statement, requirements use domain+ULID, runs cite but
do not own requirements, `current_run` is the default, and revisions are
immutable. No operational numeric-ID/table examples may remain.

### WP6 - Human documentation

Update the AEGIS README, CLI reference, prompt cheatsheet, configuration/start
guide, affected diagrams/documents, component docs, and deeper software docs.
Cover the two-command flow, run recovery, domain choice, lifecycle/history,
parallel worktrees, semantic reconciliation, ADOR compatibility, and the
no-migration warning.

### WP7 - Release

Release AEGIS `1.0.0`. Update the main and embedded Python project versions, Pi
package version, and any added declarations. Roll the root changelog and keep
`template/CHANGELOG.md` empty. Isolate unrelated WAEGIS changes before adjusting
its compatibility declaration; it must reject unsafe legacy upgrades.

## 12. Validation

Focused tests:

```powershell
python -m pytest -q tests/test_workflow_core.py
python -m pytest -q tests/test_requirements_traceability.py
python -m pytest -q tests/test_hooks.py
python -m pytest -q tests/test_scaffold.py
```

Full validation:

```powershell
python -m py_compile <each changed Python file>
python -m pytest -q tests
python -m aegis --help
python -m aegis run --help
python -m aegis requirement --help
```

Also run existing Pi, OpenCode, Qwen, hook, and scaffold tests.

Merge simulation:

1. Create a temporary repository from the template.
2. Branches A, B, and C start separate runs and create different requirements.
3. Merge without selector, registry, ID, or shared-table conflicts.
4. Verify unique IDs and clean audits with an empty registry.
5. Generate registries and verify Git remains clean.
6. Merge two revisions of one requirement, observe divergent heads, reconcile,
   and verify clean audits.
7. Run the ADOR compatibility sequence read-only against
   `D:\TEMP\2026_AgenticDeliveryOrchestrator`.

## 13. Definition of done

- `current_run` is preserved, atomic, plain text, and ignored.
- Humans use runs without repeatedly typing IDs.
- Run list/current/use/clear and stale recovery are simple.
- Automation can use `--run-id`.
- No command requires or implies a forge ticket.
- Requirements use only `REQ-<DOMAIN>-<ULID>` and have no work ownership.
- Requirements are independent immutable revisions.
- Inactive and Obsolete requirements remain visible with full history.
- Two or three branches add requirements without renumbering/text conflicts.
- Same-requirement divergence blocks until explicit reconciliation.
- Registries are ignored, reproducible, and not required by audits.
- ADOR finds current run and evidence at existing paths.
- Legacy tables, numeric IDs, and `Retired` are removed.
- Instructions, adapters, docs, tests, versions, and changelog agree.
- Full validation passes.

## 14. Execution order

```text
WP0 contract tests
  -> WP1 local run selector
  -> WP2 requirement storage
  -> WP3 lifecycle and human views
  -> WP4 stateless registries and merge audits
  -> WP5 instructions/adapters
  -> WP6 documentation
  -> WP7 release and compatibility validation
```

Do not begin by changing ADOR. The preserved ignored `current_run` contract is
the compatibility strategy. Plan coordinated ADOR work only if the explicit
compatibility test reveals a real mismatch.
