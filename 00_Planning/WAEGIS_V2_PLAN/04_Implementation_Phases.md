# WAEGIS V2 — Implementation Phases

Seven ordered phases build and integrate V2. Each phase ends with focused tests,
the complete WAEGIS suite, CLI help, and a dated result in
`00_Planning/WAEGIS_V2_PLAN/PROGRESS.md`. The result records actual line counts,
deviations, decision adherence, and validation evidence.

## Standard phase preamble

```text
Repository: D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System
Plan of record: 00_Planning/WAEGIS_V2_PLAN/

Read AGENTS.md, 01_Documentation/Code_Style.md, and plan documents 00-02 before
editing; read 03 for interview work and 05 for test/retirement work.

Work on a dedicated branch/worktree. At Phase 1 start, record the exact V1
baseline commit in PROGRESS.md. Replace only 05_Software/waegis/ during core
implementation. Keep package/import/command name waegis. Read V1 thereafter
through the recorded Git baseline; do not create 05_Software/waegis2/.

WAEGIS remains stdlib-only, never imports aegis at runtime, and contains none of
the forbidden architecture in 00_README.md. The AEGIS template is reference-only
until the explicit integration phase.

For every changed WAEGIS Python file run py_compile. Before closing a phase run:
  cd 05_Software/waegis
  uv run --group dev python -m pytest -q tests
  uv run --group dev python -B -m waegis --help
Also run the phase-specific acceptance commands below.
```

Independent adversarial review follows Phases 2, 4, and 7. Findings are fixed
before the next phase or retirement decision.

## Phase 1 — Baseline, scaffold, and pure contracts

**Goal:** establish the exact V1 baseline, replace the package skeleton in its
existing location, and implement the pure safety-critical libraries before any
command can mutate a repository.

Tasks:

1. Run and record the unmodified V1 suite, CLI help, source/test/packaging line
   counts, supported OS/runtime assumptions, and baseline commit.
2. Replace the source/test skeleton under `05_Software/waegis/` while retaining
   project name, import path, command, stdlib dependency policy, and repository
   style.
3. Implement/harvest WAEGIS version 3.0.0 with AEGIS
   `>=3.0.0,<4.0.0`, `runner`, `ownership`, manifest schema 2,
   payload inventory/enumeration, safe locate/extraction, conflict types, and
   the pure three-way classifier.
4. Add golden manifest and payload-inventory fixtures created by V2 itself.
5. Add all anti-regrowth structural tests from doc 02.

Acceptance:

- `python -c "import waegis"` works with no `waegis2` or installed `aegis`;
- manifest round-trip is byte-identical and adversarial schema/path tests pass;
- the real template inventory has exactly one ownership class per path;
- a one-byte payload mutation, extra/missing entry, link, traversal, and case
  collision are rejected;
- every harvested classifier row passes pure unit tests;
- core line budget is green.

## Phase 2 — Git safety and shared install (`new`/`adopt`)

**Goal:** implement the complete install flow with no transaction, journal, or
Git-history automation.

Tasks:

1. Implement `gitsafety.py` test-first: clean `HEAD`, dirty-path report, exact
   tracked/new recovery sets, `--` pathspec separation, handled-failure
   rollback, lock metadata, dead-owner `--break-lock`, and absent-target cleanup.
2. Harvest and trim repository analysis, prompts, answers, and schema-3
   `workflow.toml` editing; add the conditional interview order from doc 03 and
   `[quick.changed_paths]` support.
3. Implement `install.py` and the initial CLI/JSON boundary in the exact order
   from doc 01. Emit and flush recovery commands before the first write,
   including the structured stderr record used by mutating JSON mode.
   Validate/smoke before publishing manifest schema 2 last.
4. Add V1 top-level detection without loading or trusting V1 ownership fields.

Acceptance on Python and JavaScript fixtures:

- `adopt --dry-run` shows answer provenance, ownership, every conflict, exact
  write paths, and exact recovery paths while writing nothing;
- staged, unstaged, and untracked dirt each fail with all paths listed;
- no `--allow-dirty` option exists;
- all-default install validates through the bundled
  `aegis config validate --json`;
- fresh `run status --json` is accepted specifically through the documented
  `RUN-POINTER-MISSING` outcome, while an active-run fixture validates the
  stable envelope;
- V1-installed adoption uses explicit migration consent and ordinary per-file
  conflicts, replacing the old manifest only at successful completion;
- no branch, index, or commit changes are made;
- immediate rerun after a simulated interruption converges.

## Phase 3 — Analyze, configure, check, and repair

**Goal:** complete the read-only and narrow maintenance surface.

Tasks:

1. Finish public `analyze` with evidence provenance and V2-owned JSON.
2. Implement `configure` against the explicit owned/preserved field matrix.
   Current valid values take precedence; AEGIS validation precedes manifest
   metadata publication.
3. Implement `check`/`doctor` using the real wrapper as the schema oracle, the
   exact known strict Codex adapter key set, Node warning, hook inventory, drift,
   version readback, and 0/1/2 behavior.
4. Implement managed-file-only `repair`; route generated configuration failures
   to `configure` and never rewrite project-owned dispositions.

Acceptance:

- configure changes only selected owned fields and preserves comments, advanced
  keys, gate timeouts, `impacted_command`, and all non-owned bytes;
- quick policy add/remove changes only that table;
- check returns 0/1/2 for healthy/warn/fail fixtures and reports a V1 manifest
  as unsupported re-adoption input;
- repeated check is byte-for-byte read-only and idempotent;
- repair restores a missing managed file but leaves generated, seeded,
  kept-local, sidecar, and locally modified project data untouched;
- every changed configuration passes the bundled AEGIS validator.

## Phase 4 — Upgrade

**Goal:** perform ownership-aware three-way V2-to-V2 upgrades with manifest-last
publication and Git recovery.

Tasks:

1. Build the upgrade planner around the pure classifier and ownership rules.
2. Resolve every conflict interactively or through exact answers-file paths;
   render consent only after all decisions are known.
3. Apply through the shared safety/publication flow, preserving project-owned
   dispositions and writing the new manifest after AEGIS validation/smoke.
4. Refuse V1, absent/invalid manifest, incompatible payload range, unsupported
   manifest schema, and unresolved conflicts before mutation.

Acceptance:

- every classifier row is represented, including additions, removals,
  converged paths, local modifications, conflicts, generated/seeded/kept paths,
  and sidecars;
- `--dry-run` is byte-for-byte read-only;
- upgrade preserves workflow policy, requirements/specs, component data,
  knowledge, reports, run history, workspace state, and kept adapter paths;
- payload version readback and manifest hashes identify the new payload;
- no Git branch, index, or commit mutation occurs;
- hard-kill and `KeyboardInterrupt` cases restore with the preprinted exact
  commands and immediately rerun to the uninterrupted end state.

## Phase 5 — Packaging and operator documentation

**Goal:** build both final D3 distribution forms with honest prerequisites and
one integrity contract.

Tasks:

1. Implement the payload-bearing zipapp, closed internal inventory, safe
   extraction/cache, release manifest, and published SHA-256 file.
2. Implement `windows-x64` ZIP and `linux-x64` tar.gz bundles containing that
   exact zipapp, pinned locked CPython, and thin native launchers. Do not add a
   second loose payload copy. Set and atomically register
   `WAEGIS_PACKAGED_RUNTIME` so installed AEGIS wrappers continue to run without
   system Python. Do not restore the V1 edition, RepoWise, SBOM, or generic
   reproducibility framework.
3. Rewrite `05_Software/waegis/README.md` for V2 commands, clean-tree recovery,
   V1 re-adopt, ownership, packaging/runtime prerequisites, and offline use.
4. Accrue the V2 change under the root `CHANGELOG.md` Unreleased section. Do not
   create a package-local changelog. The target WAEGIS 3.0.0 version is approved,
   but do not release/date the section or change the shipping V1 declaration
   before the V2 implementation reaches its release gate.

Acceptance:

- artifact verification detects a changed byte;
- the zipapp installs/checks/upgrades the real payload offline with compatible
  system Python and fails clearly without it;
- both native bundles install/check/upgrade the same payload offline with
  system Python unavailable, persist a valid runtime pointer, and diagnose a
  moved/deleted bundle until its launcher is rerun;
- all artifact forms report WAEGIS 3.0.0, AEGIS 3.0.0, the same payload and
  zipapp digests, and no edition concept;
- cache extraction is content-addressed, traversal-safe, and concurrency-safe;
- core and packaging/launcher line guards are green;
- `template/CHANGELOG.md` remains exactly empty.

## Phase 6 — Acceptance and crash harness

**Goal:** execute the complete matrix from doc 05 on Windows and fix every
failure without weakening the safety or ownership contracts.

Tasks:

1. Run the real-payload fixture matrix for install, V1 entry, configure, check,
   repair, and upgrade.
2. Run every subprocess hard-kill, handled-failure, interrupt, lock, and exact
   Git recovery case.
3. Run the zipapp and both runtime bundles with networking disabled, including
   explicit system-Python-present/absent and runtime-pointer lifecycle cases.
4. Produce a machine-readable and human acceptance report in the planning
   folder; record deviations and final actual line counts.

Acceptance:

- every matrix row is green;
- every preprinted recovery plan restores the original tree exactly;
- every immediate rerun converges;
- every project-owned preservation assertion is green;
- core remains within 9,500 lines, packaging/launchers remain within 1,000
  lines, and all anti-regrowth tests pass.

## Phase 7 — Cross-platform integration and retirement evidence

**Goal:** integrate V2 with the repository and collect all evidence required to
replace V1; this phase is mandatory. RepoWise is outside the V2 retirement
scope and is not a substitute for it.

Tasks:

1. Run the complete WAEGIS suite and install/check/dry-run-upgrade/real-upgrade
   path on one native POSIX runner as well as Windows.
2. Update AEGIS tests that import `waegis` for V2 behavior while keeping the
   existing import path. Run the complete AEGIS suite with no WAEGIS-importing
   exclusions.
3. Update the AEGIS README, affected generic template documents/adapters, root
   README if scope changed, and deeper `06_SoftwareDocu/` maintenance guidance.
   Remove V1 transaction/runtime claims and the template `.gitignore` entry for
   `.agentic/.waegis-transactions/` only when the V2 integration is active.
4. Replay the retirement matrix on two representative repositories, including
   one V1 migration and one V2-to-V2 upgrade. Do not start with the largest or
   most critical repository.
5. Verify implementation adherence to the recorded D1/D3/D6/D7 decisions and
   record a go/no-go result. Do not remove V1 from the release line or claim V2
   supported until every doc 05 gate passes.

Acceptance:

- Windows and POSIX evidence is green;
- complete AEGIS and WAEGIS suites are green with no relevant exclusions;
- all integration documentation describes V2 and no copied template file
  contains project-specific planning history;
- two-repository retirement evidence is complete;
- owner signs the final go/no-go record.
