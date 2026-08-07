<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# AEGIS 2.1

AEGIS is the offline-first, project-local Agentic Engineering Governance &
Integrity System. The runnable Python package is embedded under
`template/.agentic/cli/src/aegis/`; tests import that exact shipped source.

## Contract

- standard stages: intake, alignment, requirement, design, check,
  implementation, validation, delivery;
- proportional quick `fix`/`change` stages: intake, implementation,
  validation, delivery, with one human-approved journal record marking the
  four collapsed stages `bypassed`, never passed;
- stage lifecycle: prepare, optional add, apply, explicit human close;
- strict configuration/run graph schema 3 with no schema-2 migration;
- file-first forms for intent, requirements, checks, evidence, and stage control;
- canonical stage completion checklists generated as TOML comments from one
  CLI-owned contract, with tested `Done when` projections in the standard,
  adoption, and delivery references;
- a versioned, read-only `run context --json` bootstrap response that names
  only the selected stage's router, reference, primary form, and retained
  predecessor form, independent of evidence-history size;
- authoritative run-local `design.md` and blocking design invariant;
- external or managed red-before-green check evidence;
- canonical, complete-document external evidence validation before graph
  mutation, with immutable check identity and command matching;
- deterministic build, typecheck, lint, test, and security gates, all optional;
- explicit `nothing-ran` outcomes for managed checks and explicitly requested
  gate execution that launch zero commands;
- safe `verify impact --run` focused test execution through a configured argv
  prefix, with deterministic selector selection and a complete-test fallback;
- consolidated impact/gates/invariants/traceability/coverage/working-tree
  verification before human diff review;
- exact human-approved, run-local process waivers with mandatory reasons,
  digest-pinned staleness, graph persistence, and separate journal events;
- no outward Git/publication action when delivery closes.
- atomic, flushed graph/journal/requirement/RepoWise state publication with
  bounded Windows/POSIX process locks and typed stale-update conflicts;
- optional schema-1 RepoWise discovery integration, with validated receipts,
  artifact hashes, repository fingerprints, and advisory/required policy.

The top-level CLI groups are exactly `run`, `stage`, `requirement`, `check`,
`evidence`, `waive`, `verify`, `delivery`, `adoption`, and `config`. Global
options are `--run` and `--json`.

## Development

```powershell
uv sync --group dev
uv run --group dev python -B -m aegis --help
uv run --group dev python -m pytest -q tests
```

Typical workflow:

```text
aegis config validate
aegis run start feature
# edit returned intake form
aegis stage apply
aegis stage close
```

Repeat prepare/apply/close through delivery. Use `stage add` for requirement and
check collections, `check prepare/record` or `check run` for evidence, and
`verify run` at validation.

An explicit `check run` or `verify gates` request that launches no command exits
non-zero with `execution_status = "nothing-ran"`, `executed_count = 0`, and a
reason; it journals that outcome and writes no passing evidence. A command that
does launch remains `pass`, `fail`, or `waived` as its observed result requires.
`verify run` is an aggregate audit instead: disabled gate groups are reported
as `not-enforced`, not as a failed nothing-ran execution.

When `[gates.test].impacted_command` is configured as an argv prefix, `aegis
verify impact [paths-file] --run` appends the complete, sorted linked-test set
as individual argv values with `shell = false`. Any incomplete coverage, unsafe
selector, empty selection, or omitted prefix reports the exact reason and runs
every configured full test command. If no focused or full test command can
launch, the explicit request is non-zero `nothing-ran`; normal gate evidence,
logs, waiver behavior, and transactional publication still apply.

For a fresh stage session, read `AGENTS.md`, run `aegis run context --json`,
then follow `unavailable_current_artifact` recovery exactly; never prepare an
already applied stage. Read only the returned router, reference, current form,
and retained predecessor form. `run status` remains the detailed diagnostic
command; routine recovery never reads `graph.json` or `journal.jsonl`.

Each primary stage form begins with its generated completion checklist. The
checklist is presentation guidance, not submitted TOML data: AEGIS imports the
same payload and records the same stage digest when comments alone change.
`requirement` and `check` show the checklist once in their shared `stage.toml`;
the item forms do not repeat it. The `Done when` list in each standard,
adoption, and delivery reference is a tested projection of the same CLI-owned
contract, so it cannot drift from the generated form.

For a genuinely small fix, use `aegis run start fix --quick` (or
`change --quick`). Quick runs keep intake, implementation changed paths plus
active linked evidence, deterministic validation, delivery reporting, and all
four human closes. Requirement/check/design-dependent invariants and audits are
explicitly not applicable, while enabled gates, secrets, scope, and
working-tree review still run. Feature and adoption runs cannot use `--quick`.

New quick runs register one or more run-local check definitions during
implementation with `check create` and `check register`, record a real red
result before their green result through the existing external or managed check
paths, and link the resulting active green check evidence in the implementation
form. They evaluate INV-3; only schema-3 quick graphs written before this
policy retain explicit legacy INV-3 not-applicable reporting. Manual evidence
does not substitute for a quick check.

When an eligible process blocker must be overcome once, inspect exact IDs with
`aegis waive list`, obtain explicit human approval, and record
`aegis waive add <blocker-id> --reason "<reason>"`. A waiver stays local to the
selected run and exact blocker state; digest changes make it stale. Failed
checks and invariants remain failed and render as `WAIVED`, never passed.
Malformed schema/graph state, lock conflicts, and stale-update conflicts remain
non-waivable.

External evidence is accepted only during check or implementation when the
prepared stage captured external execution and imported at least one check.
`check record` validates every row before mutation, trims permitted surrounding
whitespace from result/summary/output-log fields, and persists canonical
`pass`/`fail` results. Expected configuration, run, workflow, or command-input
failures retain the stable blocked response; unexpected programming exceptions
remain ordinary failures with diagnostic context.

## Template

Everything under `template/` is copied verbatim into downstream projects:

- `.agentic/` — CLI, workflow configuration, forms/state conventions, guards,
  shared skills, requirements, component knowledge, documents, and wrappers;
- `.codex/`, `.claude/`, `.pi/`, `.opencode/`, `.qwen/` — thin host adapters
  around shared state, hooks, and skills;
- `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `opencode.json` — host entry points;
- `CHANGELOG.md` — deliberately empty downstream starter.

Project-specific policy belongs in schema-3 `.agentic/workflow.toml`. The
default interface is `stage_form_retention = "latest"` plus external check
execution, so the final form from each stage remains available for a fresh
session; all five gates ship disabled. The optional `[quick.changed_paths]`
policy accepts
`disabled|advise` plus a positive `max_paths`; absence is disabled with a
retained threshold of 10, and an above-threshold response is advisory only.

The optional `.agentic/integrations/repowise.toml` remains separate from schema
3. AEGIS reads and normalizes current RepoWise artifacts during
`repo-discovery`; it never imports RepoWise Python code or executes its CLI.
Disabled and absent integration are equivalent.

The template itself must contain source and durable starter material only.
Structural tests reject `__pycache__/`, `.pyc`, `.pyo`, obsolete current-version
branding, divergent adapter versions, and release content in the empty
downstream `template/CHANGELOG.md`. WAEGIS payload copying and release staging
independently exclude interpreter, test, coverage, package-manager, and adapter
dependency caches instead of relying on Git ignore rules.

Graph mutations serialize the complete authoritative reload, validation,
mutation, and save operation per run. Same-requirement updates serialize per
requirement and verify the loaded source digest before publication; requirement
reads and UUID-backed creation retain their existing behavior. Lock files under
`.agentic/.workspace/locks/` are persistent worktree-local coordination files:
process exit releases the operating-system lock, so operators must not delete a
file to bypass a live owner.

WAEGIS 1.2 is the recommended deployment/configuration tool and supports AEGIS
`>=2.0.0,<3.0.0`. Its Core and Complete editions remain outside the copied
payload; Complete can install RepoWise 0.37.0 as a project-local sidecar. Its
interviews and doctor do not yet manage the optional quick changed-path policy;
that awareness remains a follow-up outside this AEGIS-only change.

New adopters should begin with
[`template/.agentic/documents/WHY_AEGIS.md`](template/.agentic/documents/WHY_AEGIS.md).
The companion
[`GLOSSARY.md`](template/.agentic/documents/GLOSSARY.md) defines the workflow
vocabulary, and [`INVARIANTS.md`](template/.agentic/documents/INVARIANTS.md)
explains every `INV-*` result. [`MERGE_AND_REBASE.md`](template/.agentic/documents/MERGE_AND_REBASE.md)
is the mid-merge playbook for concurrent `.agentic/` state. See also
`template/.agentic/documents/CLI_API_REFERENCE.md` and
`template/.agentic/documents/WORKFLOW_CONFIGURATION.md`.
