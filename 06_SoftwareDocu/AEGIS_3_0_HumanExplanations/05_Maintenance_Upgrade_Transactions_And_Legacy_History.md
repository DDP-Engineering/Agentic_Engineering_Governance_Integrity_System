<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Maintenance, Upgrades, Recovery, and Legacy History

WAEGIS maintenance changes the installed governance payload or its owned
configuration. AEGIS workflow runs record work performed under that payload;
the two lifecycles do not share state machines.

## Maintenance commands

| Command | Behavior |
|---|---|
| `waegis analyze --repo PATH` | Read-only repository evidence and installation-state proposals. |
| `waegis check --repo PATH` | Read-only manifest, drift, wrapper, hook, adapter, Node, root, version, and runtime-pointer health. |
| `waegis doctor --repo PATH` | Exact alias for `check`. |
| `waegis configure --repo PATH` | Regenerate only explicitly WAEGIS-owned workflow policy. |
| `waegis repair --repo PATH` | Restore only approved missing/drifted `managed` paths. |
| `waegis upgrade --repo PATH` | Three-way upgrade to a strictly newer compatible AEGIS 3 payload. |
| `waegis adopt PATH` | Establish schema-2 ownership in a clean existing repository, including explicit WAEGIS 1 re-adoption. |

Read-only and dry-run commands do not write the repository, lock, payload
cache, or runtime pointer. Mutating commands render the complete plan before
consent and leave Git staging, commits, and branches to the operator.

## Clean-tree and lock contract

Existing-repository mutations require a clean worktree/index and a valid HEAD.
WAEGIS checks those conditions during planning, takes one repository-specific
`waegis-v3.lock`, then rechecks both cleanliness and the planned HEAD.

A lock records a closed local-process identity and random token. Age alone
never makes it stale. A live, malformed, foreign, or unverifiable lock fails
closed. `--break-lock` is accepted only when the structurally valid recorded
local process is confirmed dead; read-only commands never break locks.

## Exact Git recovery

WAEGIS 3 has no persistent transaction directory and no target-local backup
copies. Before the first repository write, it prints and flushes an exact
recovery record containing:

- the planned HEAD;
- every planned tracked path restored from that HEAD;
- every exact planned new path removed through `git clean -fdx --`;
- `--` before every pathspec.

Handled failures and `KeyboardInterrupt` execute this plan automatically. A
hard-killed process cannot run cleanup, so the operator executes the already
printed commands, confirms the original tree/index, and reruns with
`--break-lock` only for the dead owner. Recovery never runs a broad clean,
changes HEAD, creates a commit, or touches unrelated ignored/untracked paths.

## Health, repair, and upgrade authority

`check` compares every manifest record with current bytes and its disposition.
Its exit model is 0 for healthy, 1 for actionable warnings, and 2 for invalid
or failed health. It also asks the real AEGIS wrapper for configuration and
run-status evidence.

Repair may write only `managed` records and always republishes the manifest
after AEGIS smoke. Generated workflow drift is routed to `configure`.
Seeded, kept-local, sidecar, requirements, specifications, component data,
knowledge, reports, run history, and workspace state remain project-owned.

Upgrade compares three values for each managed path: installed baseline hash,
current hash/absence, and new payload hash/absence. Unambiguous add, replace,
remove, converge, and preserve outcomes are planned automatically. Every true
conflict requires an exact keep/take/sidecar decision. Generated and seeded
paths retain their authority; new project-data paths default to seeded rather
than managed. The new manifest and payload identity are published last.

An upgrade requires a valid schema-2 manifest, installed AEGIS within
`>=3.0.0,<4.0.0`, and a strictly newer AEGIS 3 payload. Missing, invalid,
WAEGIS 1, cross-major, and same/older versions refuse before mutation.

## Runtime pointer lifecycle

Native WAEGIS bundles record their packaged interpreter at
`WAEGIS_HOME/runtime-python` immediately before an approved mutation. Installed
AEGIS wrappers use the same interpreter. A moved or deleted bundle leaves a
diagnosable invalid pointer; `check` does not repair it because it is read-only.
Run a mutating command from the bundle's new stable location to replace it
atomically. `AEGIS_PYTHON` is the explicit higher-precedence override.

## Legacy boundaries

WAEGIS 1 manifests are detected only by their top-level schema/version marker.
Their file ownership, answers, transaction state, and runtime claims are not
loaded or migrated. `adopt` requires explicit acknowledgement and applies the
normal conflict rules to every differing path.

Historical AEGIS workflow records remain repository audit material and are not
rewritten by WAEGIS. Old `.agentic/.waegis-transactions/` content is outside
the WAEGIS 3 protocol; make a repository copy and review it manually rather
than treating it as executable recovery authority.

RepoWise lifecycle is also outside WAEGIS 3. Optional externally managed
discovery remains advisory to AEGIS and cannot replace current payload,
manifest, policy, or workflow evidence.
