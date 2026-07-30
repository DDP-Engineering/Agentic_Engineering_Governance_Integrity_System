<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 2.1 CLI Reference

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

## Command Inventory

The complete top-level interface is:

```text
aegis run ...
aegis stage ...
aegis requirement ...
aegis check ...
aegis evidence ...
aegis verify ...
aegis delivery ...
aegis adoption ...
aegis config ...
```

AEGIS 1.x commands and mutation flags do not exist.

## Run

```text
aegis run start <feature|fix|change|adoption>
aegis run status
aegis run resume
aegis run select <run-id>
```

`run start` creates and selects a draft run, prepares the intake form, and
returns its path. Put the statement, scope hints, and access mode in the form.

## Stage Lifecycle

```text
aegis stage prepare
aegis stage add
aegis stage show
aegis stage apply
aegis stage close
```

- `prepare` creates or reconstructs the current form.
- `add` creates another CLI-identified requirement/check form.
- `show` reports files, revision, readiness, and blockers.
- `apply` validates the entire stage directory before importing and does not
  advance.
- `close` is the explicit human approval action. It journals approval, advances,
  and prepares the next stage.

The standard stages are:

```text
intake → alignment → requirement → design → check → implementation → validation → delivery
```

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

## Requirements and Design

```text
aegis requirement list
aegis requirement show <id>
```

Requirement commands are read-only. Mutations occur only through requirement
stage forms. AEGIS generates UUID-backed IDs and durable companion specs.
Successful validation closure activates eligible Planned requirements.

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

The captured workspace policy permits one path. The wrong path returns the
configured mode and correct command. Check closure requires red evidence;
implementation closure requires prior red and current green evidence.

Manual evidence:

```text
aegis evidence prepare <add|supersede>
aegis evidence apply
aegis evidence show
```

## Deterministic Verification

```text
aegis verify run
aegis verify status
aegis verify gates [build|typecheck|lint|test|security]...
aegis verify invariants
aegis verify traceability
aegis verify coverage
aegis verify impact [paths-file]
aegis verify working-tree
```

`verify run` performs impact/regression selection, all enabled gates in the
fixed order shown above, invariants, traceability, coverage, working-tree review,
and then writes a validation summary for the human diff review. Every enabled
group executes even if an earlier group fails. Disabled groups are reported
`disabled`, never `passed`.

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

aegis config validate
aegis config show
```

Configuration and run graphs require schema 3. AEGIS 2.1 rejects schema 2 and
legacy graphs without migration or fallback.

`config validate` and `config show` also validate/display the optional
schema-1 `.agentic/integrations/repowise.toml`. Absence means disabled. RepoWise
execution intentionally has no AEGIS command: WAEGIS owns
`waegis repowise status|sync`, while AEGIS consumes only validated structural
artifacts during `repo-discovery`.
