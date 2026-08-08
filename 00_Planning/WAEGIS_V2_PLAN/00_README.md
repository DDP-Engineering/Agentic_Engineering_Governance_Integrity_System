# WAEGIS V2 ("lite") — Plan Overview

**Date:** 2026-07-31
**Aligned:** 2026-08-08 against AEGIS 3.0.0 (in-tree), the
AEGIS WP9 NO-GO disposition, the repository instructions, and WAEGIS 1.2.0 at
current HEAD.
**Status:** PLANNED — implementation has not started. WAEGIS 1 remains the
shipping installer until the retirement gates in
[05_Validation_And_Parity.md](05_Validation_And_Parity.md) pass.

The owner finalized the remaining scope decisions on 2026-08-08: RepoWise is
outside the V2 core; releases contain both a Python-required zipapp and
Pythonless Windows/Linux x64 runtime bundles; AEGIS support is
`>=3.0.0,<4.0.0`; WAEGIS never creates branches, stages files, or commits; and
the architecture planned here ships as WAEGIS 3.0.0.

The owner decision from 2026-08-08 remains authoritative: V2 is a hard break
from V1's manifest schema, answers files, JSON output shapes, transaction
state, and internal architecture. The hard break does not authorize a package
rename: repository policy keeps the runnable wizard under
`05_Software/waegis/` with the `waegis` import path and command.

## Why a V2

WAEGIS 1 is correct but substantially larger than its distribution role
requires: 26,226 Python source lines, 2,448 packaging lines, and 18,495 test
lines at the audited HEAD. Its HMAC transactions, ownership records, resumable
step engine, machine/network probe fleet, embedded-runtime release framework,
and RepoWise lifecycle dominate the maintenance cost.

The V2 thesis is narrower: WAEGIS installs and maintains the AEGIS payload in a
Git repository. A clean committed tree is the precondition, Git is the
recovery baseline, an atomic V2 manifest is the successful-completion marker,
and the shipped AEGIS CLI is the configuration and runnability oracle.

## Target shape

| Area | WAEGIS 1 | WAEGIS V2 target |
|---|---:|---:|
| Core Python source | 26,226 lines | **≤ 9,500 lines**, with the guard allowed only to decrease |
| Packaging source | 2,448 lines | **≤ 1,000 lines** for the zipapp and two runtime bundles |
| Tests | 18,495 lines | about 8,000 focused unit, behavior, crash, and acceptance lines |
| Commands | Nine public command groups | Same useful vocabulary, with `check` as the primary name and `doctor` as an alias; V2 flags and JSON are their own contract |
| Recovery | Authenticated transactions, journals, ownership records, external locks | clean-tree precondition, exact Git restore plan emitted before mutation, atomic files, manifest last |
| Probes | OS, disk, Python, Git, Node, identity, proxy, and TLS | Git plus an artifact-appropriate Python runtime; Node is a runnability warning when hook adapters are installed |
| Verification | Multiple hash and byte-comparison tiers | build-time payload inventory verification, then one installed-file hash for the manifest |
| Packaging | Reproducible native archives, embedded CPython, Complete/RepoWise edition | payload-bearing zipapp plus Pythonless Windows x64 ZIP and Linux x64 tar.gz built around that exact zipapp; one payload copy and no editions |

## Implementation strategy

Use a fresh implementation in the existing package boundary, harvesting only
the proven logic that still belongs:

- repository proposal heuristics;
- schema-3, comment-preserving `workflow.toml` editing;
- canonical path validation and payload enumeration;
- per-file conflict decisions;
- the three-way upgrade classifier;
- injectable command, prompt, and stream seams.

Do not create `05_Software/waegis2/` or a `waegis2` package. Development occurs
on a dedicated branch/worktree and replaces the contents of
`05_Software/waegis/`; the exact V1 baseline commit is recorded before the
replacement begins and remains available through Git throughout development.
This satisfies both the repository layout contract and the requirement that V1
remain recoverable until V2 is accepted.

## Compatibility stance

V2 is not a drop-in artifact-level replacement for V1:

1. V2 uses `install-manifest.json` schema 2 and does not manage a V1 manifest.
   A minimal top-level detector may recognize V1 solely to issue safe
   `re-adopt with WAEGIS 3` guidance; V1 ownership data is never trusted.
2. Generated configuration is accepted only when the bundled payload's
   `<workflow> config validate --json` command succeeds. Byte parity with V1's
   generator is not required.
3. A V1-installed repository enters V2 through ordinary `adopt`. Every existing
   differing payload path is treated as repository-owned until the operator
   explicitly chooses an outcome.
4. V2 retains familiar command names for operator continuity, not V1-compatible
   flags, answers keys, exit payloads, or console transcripts.
5. WAEGIS 3 supports AEGIS `>=3.0.0,<4.0.0`; cross-major payload upgrades are
   refused before mutation.
6. The package location and import path remain `05_Software/waegis/` and
   `waegis`; AEGIS tests are updated for changed behavior, not redirected to a
   second package.

## Explicitly forbidden in V2

- HMAC or signed local state;
- transaction or ownership-record subsystems;
- resumable journals or a step/catalog engine;
- an `--allow-dirty` bypass;
- automatic Git branch creation or commit-history mutation;
- age-only lock breaking;
- network, proxy, TLS, OS, or disk probe fleets;
- repeated hashing or byte comparison of the same copied content in one flow;
- runtime imports from `aegis` or V1 code;
- editions or bundled RepoWise lifecycle inside the V2 core;
- a sibling `waegis2` package.

Adding any forbidden item requires an owner decision tied to an observed
failure that the simpler design cannot handle.

## Documents

| File | Contents |
|---|---|
| [01_Scope_And_Requirements.md](01_Scope_And_Requirements.md) | Safety model, commands, ownership rules, exit contract, decisions, and acceptance requirements |
| [02_Architecture.md](02_Architecture.md) | Existing-package module map, line budgets, manifest contract, and harvest/drop map |
| [03_Interview_UX.md](03_Interview_UX.md) | Consequence-style, conditional interview catalog and defaults |
| [04_Implementation_Phases.md](04_Implementation_Phases.md) | Seven ordered implementation and integration phases |
| [05_Validation_And_Parity.md](05_Validation_And_Parity.md) | Unit, crash, cross-platform acceptance, and V1 retirement gates |
| [06_AEGIS_Contract_Audit.md](06_AEGIS_Contract_Audit.md) | Evidence from the current AEGIS/WAEGIS implementations and the corrections made to this plan |
| [PROGRESS.md](PROGRESS.md) | Baseline, phase status, decisions, line counts, and validation evidence |
