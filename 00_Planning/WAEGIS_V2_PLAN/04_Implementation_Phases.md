# WAEGIS V2 — Implementation Phases (agent-ready)

Seven phases, each sized for one agent session, each ending with a green suite and a documented result. Run them strictly in order; every phase's prompt should carry the standard preamble below.

**Standard preamble for every phase prompt:**
```
Repo: D:\TEMP\2026_Agentic_Engineering_Governance_Integrity_System (branch: waegis2 — create from AEGIS_V2 in Phase 1)
Plan of record: 00_Planning/WAEGIS_V2_PLAN/ (read 00, 01, 02 before starting; 03 for interview work).
Hard rules: V1 (05_Software/waegis/) and the AEGIS payload are read-only reference material — never modify them.
waegis2 never imports waegis or aegis. stdlib only. No transactions, journals, step engines, or probes
beyond python/git (the forbidden list in 00_README §"Explicitly forbidden").
House style: post-sweep docstring rules (no @author/@date/@version tags anywhere).
Every phase ends with: cd 05_Software/waegis2 && python -m pytest tests -q fully green, plus the phase's
specific acceptance checks, plus a short result note appended to 00_Planning/WAEGIS_V2_PLAN/PROGRESS.md
(create it in Phase 1; one dated section per phase: what was done, deviations from plan, open items).
```

**Model guidance:** Phases 1, 5 are mechanical → Sonnet-class, default effort. Phases 2, 4, 6 carry the design and merge-logic risk → strongest available model, default-to-high effort. Phases 3, 7 → Sonnet-class. Independent review (see doc 05) after Phases 2, 4, and 6.

---

## Phase 1 — Scaffold and harvest

**Goal:** `05_Software/waegis2/` exists, contains the vendored library layer, imports cleanly, and its ported unit tests pass.

Tasks: create the package per doc 02's layout (pyproject, src/waegis2, tests, conftest with `pythonpath` wiring that also exports PYTHONPATH to child processes — port V1's lesson); vendor the harvest-verdict "keep" files (`analyze`, `workflow_toml`, `manifest`, `copier` [trim the re-verification passes per doc 02], `locate`, `gitops` subset, `prompts`, `answers`, `envelope`, `runner`, `toolchecks` subset, `version` with WIZARD_VERSION="2.0.0") fixing intra-package imports; extract `classify.py` from V1 `commands/upgrade.py` (the `_classify` function, `FileAction`, `ConflictDecision`, decision-normalization helpers — nothing else); port the V1 unit tests that cover exactly these modules; write the four anti-regrowth structural tests from doc 02 §5, including the ≤5,000-line budget test and the V1-manifest round-trip fixture test (generate the fixture with V1 now, commit it).

**Acceptance:** suite green; budget test passes; a V1-written manifest fixture loads and re-serializes byte-identically; `python -c "import waegis2"` works with V1 uninstalled.

## Phase 2 — gitsafety + the shared install flow (`new`/`adopt`)

**Goal:** `waegis new` and `waegis adopt` work end-to-end.

Tasks: `gitsafety.py` (clean-tree check with exact dirty listing, restore-command builder, offer-to-restore on failure, the single lockfile) — write its crash tests first (kill mid-copy, assert printed restore commands actually restore, per doc 05 §3); `interview.py` rendering doc 03's template over FieldSpecs extended with `consequence`/`example` fields (keys/validators untouched); `install.py` implementing the doc 01 §2 flow with `new`/`adopt` as aliases; `cli.py` with V1's command names and flags; conflict handling reusing the harvested copier hook contract and V1's decision vocabulary.

**Acceptance:** on a fixture JS repo: `adopt --dry-run` shows proposals with provenance and writes nothing; full `adopt` with scripted answers produces a manifest V1's `load_manifest` accepts and a `workflow.toml` **byte-identical** to V1's output for the same answers (this is the first parity gate — build the comparison into the test); `new` on an empty dir yields a repo whose `aegis run status` answers; dirty-tree refusal message lists the dirty paths; `--answers` V1 file accepted.

## Phase 3 — configure, check, repair

**Goal:** the maintenance commands.

Tasks: `configure.py` (precedence stored→proposals→defaults; owned-fields-only regeneration; optional gate/smoke re-run; git-restore guidance on failure); `check.py` (doc 01's finding list, 0/1/2 exit contract, `--json` additive-compatible with V1 doctor minus the journal group); `repair.py` (copier repair mode; never touches conflict-kept operator files — test this explicitly).

**Acceptance:** configure on a V1-installed fixture changes only owned fields (byte-diff proves comments/foreign keys untouched); check exit codes match V1 doctor on three fixtures (healthy / drifted / broken-wrapper); repair restores a deleted managed file and leaves a modified conflict-kept file alone.

## Phase 4 — upgrade

**Goal:** three-way upgrade without transactions.

Tasks: `upgrade.py` around harvested `classify.py`: plan (classify every path), render plan, per-file conflict decisions (interactive + answers + `--resolutions`), consent, clean-tree precondition, apply in classifier order with **manifest written last**, smoke check, git-restore guidance on failure, optional branch-and-commit modes, cross-major refusal, golden consent-transcript test (port the V1 pattern).

**Acceptance:** port V1's twelve classifier row tests (they must pass against the harvested core unchanged); upgrade a V1-1.1.0-installed fixture to a newer payload fixture and have V1's `analyze` accept the result; kill-mid-apply crash test: printed git commands restore the pre-upgrade state including the old manifest; KI-mid-apply re-raises after restore guidance.

## Phase 5 — packaging + docs

**Goal:** shippable artifact and honest docs.

Tasks: `packaging/build.py` (zipapp + SHA256SUMS per D3); a V2 README (what changed vs V1, the git-based safety model, the forbidden list); CHANGELOG.md for waegis2 with the 2.0.0 entry; verify the payload embeds/locates correctly in the zipapp.

**Acceptance:** built zipapp runs `new` and `adopt` end-to-end on a clean machine profile (fresh temp HOME); SHA256SUMS verifies.

## Phase 6 — parity harness and hardening

**Goal:** proof V2 can replace V1. This phase implements doc 05 and fixes whatever it finds.

Tasks: build the parity harness (doc 05 §2) running V1 and V2 side by side over the fixture matrix; run the crash matrix (doc 05 §3); fix divergences in V2 (or document intentional ones — safety-model messages will differ; file *contents* may not).

**Acceptance:** parity report shows byte-identical repo trees, manifests, and workflow.toml for every fixture scenario; all crash tests green; budget test still ≤5,000.

## Phase 7 (optional, after D1 ratified) — RepoWise

Harvest `repowise.py` + the repowise CLI subcommands; adapt the install/sync flows to gitsafety; port its tests. Outside the 5k budget; explicitly skippable forever.

---

## Sequencing note

Phases 1–6 ≈ six agent sessions plus three review sessions. Nothing here blocks or touches the AEGIS 2.1.0 / AudioMancer track — V1 remains the shipping installer throughout, and the retirement decision only arises after doc 05's criteria are met.
