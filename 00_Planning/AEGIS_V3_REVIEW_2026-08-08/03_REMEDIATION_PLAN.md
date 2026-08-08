<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0.0 - Remediation Plan

Sequenced batches. Each is independently shippable and independently testable.
Defect IDs refer to `01_DEFECTS.md`; `S` IDs to `02_SIMPLIFICATION.md`.

## Standing constraint

The established rule for full AEGIS is that **only bugs and workflow
obstructions justify a change** - no refactors, no added hardening, escape
hatches preferred over new gates.

Batches 1-4 sit inside that rule: every item is a defect that produces a wrong
result, a crash, or a dead end. **Batches 5 and 6 sit outside it** and need an
explicit owner decision before anyone starts. They are listed because the
owner asked about over-engineering, not because the standing rule authorizes
them.

Nothing in this plan adds a check. The two places where a guard must be
*widened* (V3-03 to V3-07) close bypasses in checks that already exist and are
already documented as covering those cases.

---

## Batch 1 - Pin UTF-8 on every stream

**Defects:** V3-01, V3-02, and the approver-corruption defect.
**Effort:** ~6 lines. **Risk:** very low. **Windows-only impact.**

The single highest value-to-effort item in the review. One omission - never
pinning UTF-8 - produces a silent guard fail-open, a crash after durable state
has already changed, and permanent mojibake in the audit trail.

| Change | Where |
| --- | --- |
| `sys.stdin.reconfigure(encoding="utf-8")` | the 6 hooks that read stdin |
| `sys.stdout.reconfigure(encoding="utf-8")` | `cli.py` `main()` |
| add `encoding="utf-8"` to the `git config` call | `cli.py:1235-1241` |

Setting `PYTHONUTF8=1` in the three transports' spawn environment is an
alternative for the hooks, but per-hook `reconfigure` is preferable: it works
regardless of how the hook is invoked, including the liveness check in
`hooks/README.md`.

**Acceptance evidence.** Reuse the review's harness shape - assert a control
and the failing case together, because the control is what proves the harness:

- With `[guardrails.secrets] patterns = ["CLÉ_SECRÈTE_[0-9]{4}"]`, a `Write`
  carrying `CLÉ_SECRÈTE_4242` must **deny** with no `PYTHONUTF8` set. An ASCII
  pattern must still deny (control).
- `aegis run abandon --reason "blocked until CI ≥ 3 green runs"` with stdout
  piped must exit 0 and print a complete body.
- `git config user.name "José Müller"` then `stage close` must persist
  `José Müller` in `graph.json`, byte-for-byte.

---

## Batch 2 - Stop crashing on the error path

**Defects:** V3-09, V3-10, V3-36, V3-25, V3-26, V3-39.
**Effort:** small; each has a correct sibling to copy. **Risk:** low.

These are the "stable app" core. Every one of them turns a recoverable
situation into a raw traceback or a closed loop, and several occur inside the
code meant to guide the operator out.

| Defect | Fix | Sibling that already does it right |
| --- | --- | --- |
| V3-09 | `isinstance(payload, dict)` guard + `AttributeError` in the `except` at the 3 loaders | `store.py:694-696`, `repowise.py:534` |
| V3-10 | Use `contained_relative_path` for disk/Git-sourced paths; keep `allow_glob=False` for operator input | `paths.py:76-95` exists for exactly this |
| V3-36 | Add `UnicodeDecodeError` to the existing `except` tuple | `store.py:460`, `store.py:512` |
| V3-25 | Write `complete` to `graph.json` on the unreadable-run abandon path | - |
| V3-26 | Let `abandon_run` tolerate a torn journal | `store.py:1212-1216` |
| V3-39 | Move `load_config` below the `run list` / `run abandon` branches | - |

**Acceptance evidence.**

- `graph.json` containing each of `[]`, `"text"`, `123`, `null`, `true` must
  produce a typed `RUN-POINTER-STALE` (or equivalent) and exit 1 with **no
  traceback**, for `run status`, `run list` and `verify run`. Same for
  `validation-summary.json` with `verify status`.
- With one uncommitted change to `app/[slug]/page.py`, `aegis verify impact`
  must succeed. Contrast case: `normal.py` already succeeds today.
- An unreadable run must be abandonable, and after abandoning must **not** be
  offered by the pointer-recovery message.
- `run list` and `run abandon` must work with a truncated `workflow.toml`.

---

## Batch 3 - Close the guard bypasses

**Defects:** V3-03, V3-04, V3-05, V3-06, V3-07, V3-08, V3-28, V3-29, V3-30.
**Effort:** moderate. **Risk:** medium - these change what gets denied.

This batch restores coverage the guards are already documented as providing. It
does not add a new policy.

1. **`guard_shell_write` tokenizing** (V3-03, V3-04). Pre-split each segment on
   `(?<=\S)(?=(?:[0-9]+|&)?>)` before `shlex`, and handle `>|`. Note the two
   dead branches this also explains: `_SEGMENT_SPLIT_RE` strips `|` and `&`
   before `_REDIRECT_TOKEN_RE` ever runs, so that regex's `\|?` group and `&`
   alternative are unreachable today.
2. **`-t` operand order** (V3-05). When `-t DEST` is present, the destination is
   `DEST`, not the last non-flag.
3. **`*** Move to:`** (V3-06). Extract the destination as a write target.
4. **Unknown tool names** (V3-07). Make `guard_write_zone` default to the
   strict case, matching `guard_read_path.py:113-116`, and read
   `notebook_path` - `secret_scan.py:54` already lists it.
5. **Workflow-config carve-out** (V3-28). Replace `endswith` with equality
   against the resolved repo-relative `.agentic/workflow.toml`, in all four
   hooks.
6. **`MultiEdit` nested `old_string`** (V3-29). Strip replaced-text keys
   recursively inside `edits[]`.
7. **`delivery_preflight` matching** (V3-30). Match on the resolved argv verb,
   not a raw substring, so an inserted `-c`/`--no-pager` cannot evade it.
8. **Read policy through the shell** (V3-08). Decide explicitly: either wire
   `guard_read_path` into each adapter's shell branch, or **document** that
   read protection covers tool reads only. Also correct the false justification
   at `tests/test_hooks.py:891-921` and the liveness check in
   `hooks/README.md:136-140`, which currently passes on a host with no read
   enforcement.

**Acceptance evidence.** Every case in the `01_DEFECTS.md` section B table must
deny, and each paired control must continue to deny. Add the unspaced redirect
form to the parametrized case list at `tests/test_hooks.py:1368-1400`, which
today only exercises the spaced form.

---

## Batch 4 - Restore the contracts

**Defects:** V3-11, V3-12, V3-13, V3-14, V3-21, V3-31, V3-35.
**Effort:** small to moderate. **Risk:** low.

| Defect | Fix |
| --- | --- |
| V3-11 | Make `stage_context._COLLECTION_STAGES` and `stage_forms.COLLECTION_STAGES` **the same object**, imported from one module. One word today; the shared constant is what stops it recurring. |
| V3-12 | Add `status` and `next` to the `run context` payload. |
| V3-13 | Do not persist `route_to`/`route_rationale` into `record.payload`, or clear them when preparing the next revision. |
| V3-14 | Either give `stage prepare` a `--force`, or change the five error messages to name a command that works. |
| V3-21 | Render coverage as `not-enforced` in `report.md` when disabled, mirroring `cli.py:767-774`. |
| V3-31 | Add the `graph.complete` guard to `apply_evidence_form`, mirroring `stage_forms.py:218-222`. |
| V3-35 | Correct `INVARIANTS.md` (INV-3 quick-run, INV-7 policy) and the three wrong rows in `CLI_API_REFERENCE.md:44-54`. Documentation only. |

**Acceptance evidence.**

- Extend the adoption context test to sample `component-adoption` and
  `baseline-review`, not only `adoption-delivery`. The current test steps over
  the one broken pair.
- `run context --json` must contain `status` and `next` on every stage.
- Route to a prior stage once, walk forward, and confirm the regenerated form
  carries **no** `route_to` and that a second close does not re-route.
- Render `report.md` against the shipped default config and assert
  `not-enforced`, not `PASS`.

---

## Batch 5 - Deletions *(needs owner approval - outside the standing rule)*

**Items:** S1, S2, S3, S9, S11, plus the S5 documentation correction.
**Effort:** mechanical. **Risk:** low for S1; low-medium for S2.
**Removes roughly 2,800 lines.**

Recommended order, most clearly justified first:

1. **S1 - `local_model_pilot`** (1,557 lines). Not deployed, not packaged, not
   referenced by WAEGIS; its own output schema names a finished one-off
   evaluation. Retires V3-58.
2. **S9, S11 - dead helpers and unreachable branches** (~95 lines). Includes
   deleting `tests/test_hooks.py:91`, a test whose only purpose is covering
   unused code.
3. **S5 documentation** - correct the two rows describing `spec_items` as
   carrying content it never carries. Retire the model itself at the next
   schema revision, not now.
4. **S3 - `[alignment]`**. Decide: delete the table and its operator
   documentation, or implement one blocker. Leaving a governance tool
   advertising an inactive restriction is the worst of the three options.
5. **S2 - RepoWise** (~1,010 lines). Retires V3-32, V3-33 and V3-34. If full
   deletion is too aggressive for this release, the **minimum** is to move the
   two `inspect_repowise` calls inside the action branch of `_config_command`,
   so a disabled optional integration cannot block `config validate`.

**Acceptance evidence.** The suite stays green with no test deleted except
those covering the removed code, and `aegis --help` plus a full run still
behave identically on a scratch deployment.

---

## Batch 6 - Fail-open analysis *(needs owner decision - behavior change)*

**Defects:** V3-15, V3-16, V3-34.
**Effort:** moderate. **Risk:** medium-high - blast radius across every policy
consumer.

These are real fail-open defects, but unlike batches 1-4 the fixes change what
matches, so a repository that validates today may report new findings after.
Ship them deliberately, not folded into another batch.

- **V3-15 / V3-34 - Git-root vs `repo_root`.** Both are the same root cause:
  `git status --porcelain` emits Git-root-relative paths that are treated as
  `repo_root`-relative. Rebase the paths through
  `git rev-parse --show-toplevel`, or refuse to run when `repo_root` is not the
  Git root. WAEGIS already refuses a non-root target, so the second option
  aligns the hand-adoption path with the deployed one. Note every current test
  uses one directory as both roots.
- **V3-16 - glob semantics.** `matches_pattern` is shared by scope checks,
  working-tree audit, and the read/write hooks, so changing it moves every
  policy consumer at once. Two independent sub-decisions: make `**/` match zero
  directories (fixes the root-file miss - fail-open in a deny-list), and stop
  `*` crossing `/` (fixes the write allow-list over-grant). The second is the
  more dangerous to change and the more dangerous to leave.

**Acceptance evidence.** Table-driven cases for `matches_pattern` covering root
files, single- and multi-segment `*`, and the tree-rooted form. A working-tree
audit fixture where `repo_root` sits **below** the Git root must produce the
same findings as the flat layout.

---

## Batch 7 - Remaining items

Everything not listed above: V3-18, V3-19, V3-20, V3-22, V3-23, V3-24, V3-27,
V3-33, V3-37, V3-38, V3-40 to V3-60, and simplification items S4, S6, S7, S8,
S10, S12 plus the performance items.

Three deserve promotion into an earlier batch if they are hit in practice:

- **V3-19** (managed-check log overwrites the active red witness) corrupts
  evidence an auditor would rely on, and `gates.py:204` already contains the
  fix to copy.
- **V3-24** (INV-9 aborts the whole invariant pass) repeats a failure the
  module docstring records fixing twice before, and it takes down `waive list` -
  the escape hatch for the very blocker it raises.
- **V3-18** (`impacted_command` set semantics) makes a workspace unusable from
  a legal configuration, and `load_config` is the entry point for every command
  *and* every hook.

Of the simplification items, **S6** is the one that most directly answers the
owner's concern: INV-8's missing-row branch makes one defect cost two waiver
approvals, and deleting three lines removes it with no loss of protection.

---

## Suggested sequencing

| Order | Batch | Gate before starting |
| --- | --- | --- |
| 1 | Batch 1 - UTF-8 | none |
| 2 | Batch 2 - error path | none |
| 3 | Batch 4 - contracts | none |
| 4 | Batch 3 - guards | none |
| 5 | Batch 7 - the three promoted items | none |
| 6 | Batch 5 - deletions | **owner approval** |
| 7 | Batch 6 - fail-open analysis | **owner decision** |

Batch 4 is placed before Batch 3 because V3-11 and V3-12 block agent sessions
today, while the guard bypasses require someone to write the bypassing form.

## Regression baseline

Recorded at review time, on `master` at `8a72b5a`, so any change can be
compared against it:

- `uv run --group dev python -m pytest -q tests` -> **639 passed, 3 skipped**
- `ruff check` -> clean
- Branch coverage over the package -> **85%**
  (`evidence_forms.py` 59%, `repowise.py` 65%, `report.py` 67% are the floor)
- Static dead-symbol sweep -> **0** unreferenced module-level symbols

Note that the suite passing is **not** sufficient evidence for batches 1, 3 or
6: none of V3-01 to V3-08 or V3-15 to V3-16 is currently detected by any test.
Each needs a new case built the way the review built them - **paired with a
control**, since in three of these the naive harness silently passes.
