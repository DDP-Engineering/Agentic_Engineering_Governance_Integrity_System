# WAEGIS 3 Review — Remediation Plan

**Date:** 2026-08-08
**Input:** [00_FINDINGS.md](00_FINDINGS.md). Finding IDs below refer to that document.
**Constraint (owner):** keep the implementation lean — fixes only, no new defensive layers, no verification passes beyond what a finding itself requires. Every batch must end with the full suite green (`uv run --group dev python -m pytest -q tests`), ruff clean, and both line guards still passing. One session per batch, single agent, no parallel sessions.

## Batch 1 — correctness fixes (do before the GO/NO-GO signature)

Scope: F-01, F-02, F-04. Small, isolated, each with a regression test that fails first.

1. **F-01** `workflow_toml.py`: move the two trailing `answers[...] = value["traceability"][...]` assignments inside the existing `try` so a missing key raises `WorkflowError`.
   *Red test:* a workflow text without `traceability.source_extensions` → `plan_repair` and `plan_configure` produce their designed refusal/reconstruction paths, no `KeyError`.
2. **F-02** `locate.py`: in `extract_zipapp_payload`, register `seen`/`folded` only for non-directory members (move the two `add` calls below the `is_dir()` continue; fold F-11's redundant `path in seen` test into the same edit).
   *Red test:* crafted ZIP with a directory entry named like an expected payload file → `PayloadError` "missing members", not success.
3. **F-04** `check.py`: make `VERSION-MISMATCH` conditional on `installed_version is not None`.
   *Red test:* unreadable installed `pyproject.toml` yields exactly one version finding.

Acceptance: suite green; the three new tests fail on the pre-fix source (verify by stash or by writing the test first); no public shape changes.

## Batch 2 — runtime coherence and interview robustness

Scope: F-03, F-05. Slightly more judgment; keep diffs minimal.

1. **F-03** `publication.py`: in `apply_publication`/`apply_install` flows, `register_runtime` already returns the selected interpreter — thread that value into `validate_aegis` (parameter with default `sys.executable` for the read-only `check` caller). No second selection pass, no new probing.
   *Red test:* with `AEGIS_PYTHON` pointing at a distinct (stub) interpreter, the wrapper validation subprocess receives that interpreter, matching the registered pointer.
2. **F-05** `interview.py`: on `ValueError` from a live-asked answer's conversion/validation in `_conditional_list` (and the `quick_max_paths` int case), re-ask instead of aborting; scripted/answers-file behavior unchanged (still a hard error).
   *Red test:* scripted ConsoleAsker input sequence `"" then "python -m pytest"` for an enforced gate completes.

Acceptance: suite green; the crash matrix (`test_crash_recovery_matrix.py`) still passes unmodified — the F-03 change must not alter the publication order or recovery semantics.

## Batch 3 — dead code, stale text, disk hygiene

Scope: F-06 … F-13. Mechanical; zero behavior change intended.

- Delete the dead statement (`install.py:231`), the unreachable re-raise (`locate.py`), the redundant path checks (`manifest.canonical_path`, `locate.resolve_payload`, `answers.parse_answers`).
- Refresh the stale `cli.py` module docstring to describe the finished surface.
- Remove the V1 bytecode residue directories under `src/waegis/` (`commands/`, `engine/`, `io/`, `payload/`, `probes/`, `repo/`, and V1-only entries in `src/waegis/__pycache__`) — untracked, so this is a disk-only cleanup; no commit content beyond the source edits above.

Acceptance: suite green; `git status` shows only the intended source/doc edits; byte-identical rebuild of `waegis.pyz` except where deleted source lines change it (expected — record the new digest the same way Phase 7 did).

## Batch 4 (optional, owner's call) — consolidation

Scope: F-14 … F-18, F-20. This batch trades churn in the most sensitive code for the removal of duplicate safety logic. Recommendation: **do F-14 and F-16; take F-15/F-17/F-18/F-20 only if their diffs stay trivially reviewable.**

1. **F-14**: extract the shared stage→publish→validate→manifest-last→rollback boundary so `apply_install` wraps it with the `new`-target pre-step and `apply_publication` with removals. Behavior must be byte-identical; the existing crash matrix and install/upgrade flow tests are the proof — do not weaken or restructure them in the same commit.
2. **F-16**: single `_is_reparse` with one decided `OSError` behavior (recommend: propagate, matching copier — the manifest call sites already run inside containment error handling).
3. **F-20**: make `plan_configure` resolve the payload only when reconstructing, so plain re-interviews work without a payload present. Add one test: configure on a healthy repo with no payload available succeeds.
4. F-15/F-17/F-18: move duplicates to one home each; no signature changes.

Acceptance: suite green including crash matrix; core line guard **decreases** (consolidation must not grow the count); a full `packaging/build.py --verify` round-trip passes.

## Documentation notes (fold into the next docs touch, no dedicated session)

- F-21: state the same-version-rebuild dead end (repair needs exact identity, upgrade needs strictly newer; re-adopt is the route) in the WAEGIS README, and name re-adopt in both refusal messages if they are ever touched for another reason.
- F-22: extend the configure refusal message for kept-local workflows to name the re-adopt/take-payload route.
- F-24/F-25/F-26/F-27: recorded as accepted limitations in 00_FINDINGS.md §E; no action.

## Explicitly out of scope (anti-regrowth)

Per the owner's instruction and the plan's standing philosophy, this review does **not** recommend: extra verification passes after extraction beyond the F-02 one-line fix, retry/backoff machinery, broader adapter parsers, lock heartbeats, fsync additions, or any new abstraction beyond the single shared publication boundary in F-14. If a future incident motivates one of these, it needs its own written justification against an observed failure — not this plan.
