# WAEGIS V2 — Scope and Requirements

## 1. Safety model

V2 replaces persistent transactions with strict preconditions, a complete
precomputed mutation set, atomic publication, and Git recovery.

1. **A clean committed repository is mandatory.** Every mutating command on an
   existing repository requires a valid `HEAD` and no staged, unstaged, or
   untracked changes. There is no `--allow-dirty` option. The refusal lists the
   exact dirty paths and tells the operator to commit or stash them.
2. **The complete write and recovery plan exists before consent.** The preview
   classifies every destination as tracked-overwrite, exact new file,
   unchanged, kept-local, or sidecar. Before the first write, WAEGIS prints and
   flushes exact path-scoped recovery commands. Human mode repeats them in the
   plan; JSON mode emits one structured recovery record to stderr before
   mutation and reserves stdout for the final single JSON result. WAEGIS never
   emits a broad repository-wide clean command.
3. **Git is the existing-repository undo.** Tracked paths use
   `git restore --source=HEAD --staged --worktree -- <paths>`. Exact new files,
   including ignored destinations, use
   `git clean -fdx -- <exact-file-paths>` only after WAEGIS verifies that every
   path belongs to the precomputed new-file set. Handled failures attempt that
   scoped rollback automatically and report whether it succeeded. Hard-kill
   tests execute the preprinted commands verbatim.
4. **`new` has a stronger precondition.** `TARGET` must not exist. WAEGIS may
   then create it and run `git init`; failure recovery is deletion of the
   directory WAEGIS created. An existing directory is refused; the operator
   may remove an empty directory and retry `new`, or initialize and commit a
   repository before using `adopt`.
5. **The manifest is the completion marker.** Files and configuration are
   applied first, then the real bundled AEGIS wrapper must pass `--help` and
   `config validate --json`. `run status --json` must either return the stable
   `status`/`stage`/`artifact`/`next` envelope for an existing run or the
   expected `RUN-POINTER-MISSING` state for a fresh install. Only then is the
   V2 manifest atomically written last.
6. **Rerun is resume.** An interrupted run has no valid completion manifest.
   Replanning treats payload-identical files as already converged, preserves
   explicit conflict decisions from an answers file, and completes to the same
   end state as an uninterrupted run.
7. **Concurrency uses one small lock.** A mutating invocation creates one
   `O_CREAT|O_EXCL` lock containing PID, host, command, repository, and start
   time. A hard kill leaves visible evidence. Time alone never breaks it;
   `--break-lock` requires explicit operator action after the owner process is
   confirmed dead. The clean-tree check knows how to ignore only that exact
   lock while recovery runs.
8. **Payload integrity has two distinct meanings.** The build embeds a closed
   payload inventory (canonical path, size, SHA-256) and the installer verifies
   archive entries against it before use. A published `SHA256SUMS` lets the
   operator verify the distribution artifact out of band; an adjacent unsigned
   checksum is corruption detection, not authenticity. Installed managed files
   are hashed once into the install manifest.

All destinations pass the harvested canonical path, containment, case-collision,
and symlink/reparse-point checks before they enter a plan.

## 2. Commands

### `waegis new TARGET` and `waegis adopt TARGET`

They share one install implementation. `new` requires an absent target and runs
`git init`. `adopt` requires an existing clean Git repository and uses read-only
analysis to propose interview answers.

The ordered flow is:

1. resolve the bundled or explicit payload and verify its closed inventory;
2. validate command prerequisites and target state;
3. for `adopt`, analyze only evidence present in the repository;
4. collect answers interactively or from the V2 answers schema;
5. compute conflicts, ownership dispositions, the exact mutation set, and the
   exact Git recovery plan;
6. render the full plan; `--dry-run` stops here and `--yes` supplies consent;
7. acquire the repository lock and recheck the preconditions;
8. stage content outside the repository, then atomically publish each file;
9. generate `workflow.toml` from the bundled schema-3 template;
10. run wrapper `--help`, `config validate --json`, and coherent-status smoke;
11. atomically write manifest schema 2 last and release the lock;
12. report changed, kept, sidecar, and operator-next-action paths.

WAEGIS does not create branches or commits. `new`, `adopt`, and `upgrade`
finish by showing exact review and commit guidance; Git identity therefore is
not a global prerequisite.

A repository with a V1 manifest is handled as an ordinary adoption with one
extra warning and one explicit migration consent. A minimal detector may read
only enough top-level JSON to distinguish V1 from V2. It must not load or trust
V1 file ownership, generated paths, skipped paths, answers, or hashes.

### `waegis analyze --repo PATH`

Read-only repository facts, V2 manifest/drift state when present, and proposed
interview answers with provenance. A V1 manifest is reported only as an
unsupported prior installation. Human and `--json` output use V2's documented
contract.

### `waegis configure --repo PATH`

Requires a valid V2 manifest and a clean tree. Precedence is current valid
`workflow.toml` values, explicitly supplied answers, repository proposals, then
payload defaults. The command changes only WAEGIS-owned fields and validates
the result through the bundled AEGIS CLI before updating manifest configuration
metadata last.

The payload template supplies the complete schema. WAEGIS owns only the fields
it interviews:

- source and test roots;
- traceability language, source extensions, and test-file patterns;
- component baseline mode and minimum;
- requirement-coverage mode, roots, and exclusions;
- adoption source-change mode;
- alignment enabled and protected-scope mode/patterns;
- interface form retention and check execution;
- five gate modes and commands;
- guardrail modes and their rule collections;
- optional `[quick.changed_paths]` mode and positive `max_paths`.

WAEGIS preserves every other valid schema-3 key byte-for-byte. In the current
AEGIS contract that includes requirement/documentation/knowledge/report paths,
component-manifest location, adoption bundle settings, alignment pause/risk and
recommended-response settings, gate timeouts, and
`[gates.test].impacted_command`. Operator comments and unknown future keys are
also preserved; if the bundled AEGIS parser rejects a future key, configure
fails without publishing the edit.

### `waegis check --repo PATH` (alias: `doctor`)

Read-only health inspection with deterministic 0/1/2 results:

- V2 manifest absent/valid/invalid, with minimal V1 detection;
- managed-file drift and kept/generated ownership summaries;
- real wrapper `config validate --json` result and configured-root existence;
- wrapper `--help` and coherent fresh/active status behavior;
- required shared hook-file presence;
- Node resolution as a warning when installed adapters use the Node bridge;
- strict parsing of only the adapter formats whose host contract is actually
  known (currently `.codex/hooks.json` with top-level `description|hooks`);
- payload version readback and compatible update availability.

The JSON schema is V2-owned and golden-tested. `doctor` is an alias, not a
second implementation.

### `waegis repair --repo PATH`

Restores missing or drifted **managed** payload files after an explicit plan and
consent. It never rewrites generated configuration, seeded/project-owned files,
kept-local conflicts, sidecars, requirements, component data, knowledge,
reports, run history, or workspace state. A missing/invalid `workflow.toml` is
diagnosed and routed to `configure`; repair does not guess configuration.

Repair uses the same precondition, recovery plan, smoke, and manifest-last
flow as install.

### `waegis upgrade --repo PATH`

Requires a valid V2 manifest and a clean tree. The harvested three-way
classifier compares the installed baseline, current bytes, and new payload for
managed paths. It preserves generated, seeded, and kept-local dispositions;
new payload paths are assigned ownership before planning. Conflicts use the
same keep-local/take-payload/sidecar vocabulary as adoption.

The command does not create a branch or commit. It applies the approved plan,
runs AEGIS validation/smoke, and atomically writes the new manifest last. V1,
manifest-less, incompatible-range, and unsupported manifest-schema repositories
are refused before mutation with an exact next action.

### `waegis repowise ...`

Not part of V2 core. RepoWise configuration remains an external/manual AEGIS
integration. Any future lifecycle automation is a separately designed and
approved tool after V2 retirement; it is not a WAEGIS 3 command, edition, or
retirement dependency. V2 must not ship a placeholder that tells operators to
use V1 after V1 retirement.

### `waegis version`

Reports the WAEGIS version, bundled AEGIS payload version, supported payload
range, manifest schema, and packaging/runtime mode. It is read-only and has
human and JSON output.

## 3. Exit and interaction contract

| Code | Meaning |
|---:|---|
| 0 | Command succeeded; `check` found no warnings or failures |
| 1 | `check` completed with warnings and no failures, or a successful mutation has a non-fatal post-success advisory |
| 2 | Usage, validation, prerequisite, health-failure, or runtime error; no successful mutation is claimed |
| 3 | More operator input or consent is required; JSON and non-interactive modes never prompt |

`--dry-run` is always read-only and returns 0 for a complete plan, 2 for an
invalid request, or 3 when answers/conflict decisions are still missing.
`--json` writes one JSON document to stdout and never mixes prompts or progress
text into it. A mutating JSON invocation that has passed consent emits its
pre-mutation recovery record to stderr and flushes it before the first write;
all other diagnostics go to the final document or stderr as documented.

## 4. Non-goals

- No dirty-tree bypass.
- No persistent operation resume or transaction recovery.
- No clone workflow; clone first, then use `adopt`.
- No Git branch, stage, or commit automation.
- No system/network/corporate-environment diagnostics beyond direct
  prerequisites used by the command.
- No schema-2 workflow migration.
- No V1 artifact compatibility beyond safe top-level detection and guidance.
- No WAEGIS enforcement role after the AEGIS payload is installed.
- No Core/Complete edition framework in the V2 implementation.

## 5. Final owner decisions (2026-08-08)

| ID | Question | Final disposition |
|---|---|---|
| D1 | RepoWise in V2? | **Excluded from V2 core.** Keep AEGIS's disabled/external integration contract documented. If lifecycle automation is still valuable, design a separately approved tool after V2 retirement gates pass. |
| D2 | Where does V2 live? | **Resolved by repository policy:** replace WAEGIS on a dedicated branch under `05_Software/waegis/`; keep package/import/command name `waegis`. Preserve V1 by its recorded baseline commit/tag, not a sibling package. |
| D3 | Packaging/runtime prerequisite? | **Ship both forms from one source/payload:** (A) payload-bearing `waegis.pyz`, requiring compatible Python 3.11+ on the operator/target; and (B) Pythonless `windows-x64` ZIP and `linux-x64` tar.gz bundles containing that exact zipapp, a pinned CPython runtime, and a thin launcher. The payload occurs once inside the zipapp; there is no duplicate loose payload tree and no Core/Complete edition. |
| D4 | Version number? | **WAEGIS 3.0.0**, aligned with the AEGIS 3 release line. “V2” remains the architecture/plan name, not the shipped semantic version. |
| D5 | Source budget? | **≤9,500 core non-test Python lines and ≤1,000 packaging/launcher lines**, excluding any future separately approved RepoWise tool. Record actual harvested/fresh totals each phase; either guard may decrease but not increase without owner approval. |
| D6 | Payload range? | **AEGIS `>=3.0.0,<4.0.0`.** WAEGIS 3 supports only the AEGIS 3 major line and refuses cross-major install/upgrade before mutation. |
| D7 | Git history automation? | **Dropped.** WAEGIS may run `git init` only for an absent `new` target. It never creates branches, stages files, or commits; it prints exact review/commit guidance instead. This keeps failure recovery entirely worktree-scoped. |

## 6. Acceptance requirements

- **R1 — V1 entry:** one ordinary V2 `adopt` can replace a V1 installation
  without trusting V1 ownership data or losing a project-owned byte.
- **R2 — AEGIS oracle:** every generated configuration passes the bundled
  wrapper's `config validate --json`; smoke accepts both active-run status and
  the normal fresh-install `RUN-POINTER-MISSING` state.
- **R3 — Recovery:** every mutating command emits a complete exact recovery
  plan before its first write; crash tests prove those commands restore the
  original tree and an immediate rerun converges.
- **R4 — Ownership:** manifest schema 2 distinguishes managed, generated,
  seeded/project-owned, kept-local, and sidecar paths. Repair and upgrade obey
  those dispositions.
- **R5 — Preservation:** upgrade tests prove preservation of workflow policy,
  requirements/specifications, component data, knowledge, reports, run history,
  workspace state, and every unselected/kept adapter file.
- **R6 — UX:** interview questions follow doc 03, ask dependent details only
  when enabled, show proposal provenance, and make Enter select the displayed
  safe default.
- **R7 — Stable package boundary:** implementation remains stdlib-only under
  `05_Software/waegis/`, imports as `waegis`, and is never copied into the AEGIS
  payload.
- **R8 — Bounded size:** core source remains within D5 and contains none of the
  forbidden architecture listed in doc 00.
- **R9 — Distribution honesty:** the zipapp works offline with compatible
  Python 3.11+, while each runtime bundle works offline without system Python.
  All three artifacts use the same zipapp and embedded payload; their closed
  inventories detect payload/runtime tampering, and published digests are
  described as corruption detection rather than unauthenticated signatures.
- **R10 — Platform evidence:** the full WAEGIS suite and install/check/upgrade
  acceptance path pass on supported Windows and one native POSIX runner.
- **R11 — Documentation:** behavior, commands, package layout, safety model,
  prerequisites, and migration guidance are updated in the root changelog,
  WAEGIS README, AEGIS README/template documents, and `06_SoftwareDocu/` in the
  same integration change. The downstream `template/CHANGELOG.md` stays empty.
