# WAEGIS 3 Implementation Review — Findings

**Date:** 2026-08-08
**Reviewer:** independent adversarial pass (Claude), read-only — no implementation files were modified.
**Scope:** every file under `05_Software/waegis/src/waegis/` (26 modules, ~5,556 lines), `packaging/build.py` + `packaging/runtime_bundle.py`, the structural/crash test surface, the AEGIS-side `waegis`-importing test modules, and the payload template facts the code depends on (hooks list, `run.sh`/`run.ps1`, ownership-referenced paths — all verified present).
**Review stance requested by owner:** find bugs, dead code, and redundancy; do not push toward more guards/checks — the target is a lean but trustworthy tool.

## Verdict

The implementation is in good shape. The safety spine — canonical-path validation, closed manifest/inventory schemas, clean-committed-HEAD precondition, pre-emitted exact recovery, lock-in-`.git`, stage-outside-repo + atomic replace + validate + manifest-last — is coherent and consistently applied across install/configure/repair/upgrade. The classifier truth table is correct on all rows I traced. Packaging is deterministic and verified end to end. No consent bypass, no write outside `contained_destination`, and no divergence between printed recovery commands and actual mutations was found.

What follows is everything that did surface, ranked. Nothing here is release-blocking on its own; F-01 and F-02 are the two I would fix before the owner signs `GO_NO_GO.md`.

---

## A. Bugs (medium)

### F-01 — `workflow_answers` can raise a raw `KeyError` that escapes every handler (crash instead of clean refusal)

`src/waegis/workflow_toml.py:328-329`. The function's big `try` block ends at line 327, but the last two reads sit **after** the `except`:

```python
    answers["source_extensions"] = value["traceability"]["source_extensions"]
    answers["test_file_patterns"] = value["traceability"]["test_file_patterns"]
```

A hand-edited `.agentic/workflow.toml` that parses as TOML but lacks `traceability.source_extensions` (or `test_file_patterns`) raises `KeyError`, not `WorkflowError`. Blast radius:

- `repair.plan_repair` (`repair.py:63-65`) catches only `(OSError, UnicodeError, WorkflowError)` → `KeyError` escapes → `_run_repair`'s handler catches `ValueError` subclasses only → **unhandled traceback** instead of the designed "workflow configuration needs waegis configure" refusal.
- `configure._read_workflow` (`configure.py:76-81`) same catch tuple → `plan_configure` crashes instead of taking the reconstruction route.
- `check.py` is unaffected (its `_root_findings` has its own `KeyError` catch), which is exactly the behavior the other two callers were meant to have.

**Fix:** move the two assignments inside the existing `try`. Two-line change, no new guard.

### F-02 — zipapp payload extraction: a directory entry can satisfy the completeness check for an expected file

`src/waegis/locate.py:159-167`. In `extract_zipapp_payload`, `seen.add(path)` / `folded.add(key)` happen **before** `if info.is_dir(): continue`. A crafted archive containing a *directory* member named `payload/AGENTS.md/` (and no file) puts `AGENTS.md` into `seen`, so the final `missing = sorted(set(expected) - seen)` check passes while no file was extracted.

Mitigations already in place: the freshly extracted tree is consumed by `_read_payload_bytes` / `_payload_bytes`, which re-verify each member's size+hash on read, so an incomplete extraction cannot silently install — it fails later with a *misleading* error ("cannot read payload member"), and the cache-hit path re-runs `verify_inventory`. So the practical impact is a wrong diagnostic on a hostile archive, not a bad install. Still, it contradicts the module's stated "closed membership" guarantee.

**Fix (either, not both):** record `seen`/`folded` only for non-directory members, or run `verify_inventory(temporary_payload, inventory)` once before `os.replace`. The first is one moved line and adds no verification pass — prefer it.

## B. Bugs (low)

### F-03 — Validation runs a different interpreter than the one WAEGIS registers for AEGIS

`publication.py:117` and `check.py:125` pin `AEGIS_PYTHON=sys.executable` for wrapper runs, while `register_runtime` (`runtime.py:91-97`, called at every mutation boundary) selects by the precedence *explicit `AEGIS_PYTHON` → `WAEGIS_PACKAGED_RUNTIME` → `sys.executable`* and registers that pointer for the deployed wrappers. When an operator sets `AEGIS_PYTHON` to a custom interpreter, WAEGIS validates the install with `sys.executable` but registers the custom one — the smoke proof and the runtime the repo will actually use can differ. (In the native bundles the two coincide, which is why the Phase 5/7 smokes couldn't see this.)

**Fix:** pass the `select_runtime(runner)` result (or the value `register_runtime` returned earlier in the same apply) as `AEGIS_PYTHON` in `validate_aegis`; in read-only `check`, keep `sys.executable` but say so in the finding text, or prefer a valid registered pointer when present.

### F-04 — `check` double-reports one root cause

`check.py:243-248`. When the installed `pyproject.toml` is unreadable, `installed_version` stays `None`, so both `VERSION-UNREADABLE` **and** `VERSION-MISMATCH` (`None != manifest.payload_version`) fire for the same defect. Make the mismatch check `elif installed_version is not None and installed_version != manifest.payload_version`.

### F-05 — Interactive interview aborts on empty required list instead of re-asking

`prompts.py` re-prompts only on invalid *choice* answers. For a required list question (e.g. gate commands with no analysis proposal, default rendered as empty), pressing Enter yields `[]` → `_list_value` raises `InterviewError` → the whole command exits 2, losing every answer given so far. A retry loop in `_conditional_list` (or letting `_ask_missing` re-ask on `ValueError` from validation) would match the ConsoleAsker's own retry behavior. UX robustness only; scripted/answers paths are unaffected.

## C. Dead code and stale text

| # | Location | Finding |
|---|---|---|
| F-06 | `install.py:231` | `resolved_target = target.resolve() if target.exists() else target.absolute()` is immediately overwritten in both the `new` and `adopt` branches. Delete. |
| F-07 | `locate.py:191-193` | In `extract_zipapp_payload`'s outer `except (OSError, BadZipFile, InventoryError)`, the `if isinstance(exc, PayloadError): raise` line is unreachable — `PayloadError` is a `ValueError` and none of the caught types subclass it (PayloadErrors raised inside simply propagate past this handler). Delete the two lines. |
| F-08 | `manifest.py:172` | In `canonical_path`, the drive-letter regex and the second `value.startswith("//")` are dead: any `:` is rejected by the per-part loop below, and `"//" in value` was rejected on the previous line. Optional cleanup. |
| F-09 | `cli.py:12-14` | Module docstring still says "Phase 1 exposes only the read-only version implementation. Later phases attach command orchestrators" — stale since Phase 2–4 landed. |
| F-10 | `locate.py:113` | `packaged[1] if packaged and explicit is None else …` — the `explicit is None` test is redundant (`packaged` is `None` whenever `explicit` was given). |
| F-11 | `locate.py:160` | `if path in seen or key in folded` — the first disjunct is subsumed by the casefolded one (revisit together with F-02). |
| F-12 | `answers.py:125` | `if conflicts or "conflicts" in answers:` — the first disjunct is redundant (truthy `conflicts` implies the key is present). |
| F-13 | disk hygiene | `src/waegis/` still contains gitignored **V1 bytecode residue**: `commands/`, `engine/`, `io/`, `payload/`, `probes/`, `repo/` exist only as `__pycache__` directories, and `src/waegis/__pycache__` holds V1-only `.pyc` files (`transaction`, `consent`, `lifecycle`, `repowise`, `verification`, …). Untracked, harmless to git and to the zipapp build (which globs `*.py`), but misleading to humans and tools browsing the canonical tree. Delete the directories. |

## D. Redundancy (consolidation candidates — apply only where the diff stays small)

| # | Location | Finding |
|---|---|---|
| F-14 | `install.apply_install` vs `publication.apply_publication` | ~60 lines of near-identical stage→publish→validate→manifest-last→rollback→lock/stage-cleanup logic, differing only in the `new`-target creation pre-step and the absence of removals. Two copies of the most safety-critical block in the product is the one duplication worth paying to remove: any future fix (e.g. F-03) must currently be made twice. Extract one shared boundary that `apply_install` parameterizes; keep behavior byte-identical and let the crash matrix prove it. |
| F-15 | `install._sidecar_path` / `upgrade._sidecar_path` | Byte-identical duplicates. Move one copy to a shared module (e.g. `classify.py` or `copier.py`). |
| F-16 | `manifest._is_reparse` / `copier._is_reparse` | Near-duplicates with a **behavioral divergence**: manifest's version swallows `OSError` (returns False), copier's propagates. Unify on one implementation with one decided error behavior. |
| F-17 | `packaging/build.py` and `packaging/runtime_bundle.py` | `_digest` and `_zip_info` are duplicated across the two build modules. Cosmetic; both are build-time only. |
| F-18 | hex-digest validation | `copier.parse_inventory`, `build.verify_release`, and `gitsafety.head_oid` each re-implement the lowercase-hex check that `manifest._require_hash`/`_SHA256` already owns. Cosmetic. |
| F-19 | double `require_clean` around lock acquisition | `apply_publication` (and adopt-mode `apply_install`) check clean before *and* after `acquire_lock`. The post-lock check is the load-bearing one; the pre-lock check only produces a friendlier failure without lock churn. Acceptable — recommend keeping but noting intent in the docstring so it isn't "fixed" into a third copy later. |
| F-20 | `configure.py:127-128` | `plan_configure` resolves the payload and reads its template unconditionally, but uses the template only when reconstructing an invalid/missing workflow. A pure re-interview therefore *requires* a resolvable compatible payload (source checkout, `--payload`, or zipapp) for no functional reason. Resolve lazily in the `reconstructs` branch. |

## E. Design observations (document rather than change)

- **F-21 — Same-version rebuilt payload is a dead end.** `repair` demands the exact installed identity (version+digest); `upgrade` demands strictly newer semver. A payload rebuilt at the same version with different bytes can be neither repaired against nor upgraded to; the only route is re-adopt. Given release discipline (release-manifest identity), acceptable — but the README/operator docs should state it, and the refusal messages could name re-adopt.
- **F-22 — Kept-local workflow permanently blocks `configure`.** After an adopt where `.agentic/workflow.toml` got a keep-local decision, `configure` refuses forever ("manifest does not grant configure authority", `configure.py:158-159`) and the only route back is re-adopt with take-payload. Correct by design; the refusal message should name that route.
- **F-23 — Asymmetric answers strictness.** Unused `conflicts.*` entries are refused as stale (good), but a stray `migration_v1: true` on a non-migration adopt is silently ignored. Harmless; noted for consistency if answers handling is ever touched.
- **F-24 — Recovery leaves empty directories.** `git clean -fdx -- <new paths>` removes files, not the parent directories a failed install created; git-invisible empty dirs can remain after recovery. The crash matrix passes because git-tree/index equality holds. Cosmetic; not worth code.
- **F-25 — `_parse_porcelain_z` mangles backslashes in POSIX filenames.** `record[3:].replace("\\", "/")` corrupts a (legitimate, rare) POSIX filename containing `\`. Windows-first project; accept and note.
- **F-26 — `NODE-MISSING` warns on every no-Node host.** The trigger is presence of `run_hook.mjs`, which the payload always ships, so the warning fires even where no Node-bridge adapter is in use. This matched the Phase 5/7 smoke evidence (the Linux advisory); accept, or scope the trigger to actual adapter configs later.
- **F-27 — `_replace_key` assumes single-line owned assignments.** A future template using a multi-line TOML array for an owned key would be corrupted by the line-based edit — and then *caught* by the final parse-back (fail-safe, no bad output possible). If the payload template ever moves, a one-assertion structural test pinning owned keys to single lines would keep the failure message honest. Not needed today.

## F. What was checked and found clean (for the record)

- Three-way classifier: all reachable input combinations trace to the correct action; `CONFLICT`/`PRESERVE_LOCAL` asserts are unreachable-safe.
- Ownership tables reference only paths that exist in the current template; `REQUIRED_HOOKS` matches `.agentic/hooks/` exactly; `run.sh`/`run.ps1` both ship.
- Manifest/inventory schemas: closed-field validation, case-fold collision checks, self-listing refusal, atomic writes — consistent everywhere.
- Lock lifecycle: O_EXCL creation race-safe, token-guarded release, proven-dead-owner break only, lives under `git rev-parse --git-path` so recovery/clean can never delete it.
- Recovery-plan honesty: the write set passed to `build_recovery_plan` covers every mutated path including manifest and sidecars, in install, configure, repair, and upgrade; removals included for upgrade.
- Gitignored-managed-destination hole is closed in both plan paths (`build_recovery_plan` and the `unchanged`-op tracked check).
- Packaging: deterministic timestamps/order, closed release membership, runtime tar link resolution with cycle/escape checks, offline-by-default `--fetch` gate.
- AEGIS-side: the five `waegis`-importing test modules now use the preserved package's `enumerate_payload`/ownership plus a test-only materializer — the V1 coupling WP9 flagged is resolved.
- Line guards: core 5,556 ≤ 9,500 and packaging 531 ≤ 1,000, enforced by `test_structure_guards.py`.
