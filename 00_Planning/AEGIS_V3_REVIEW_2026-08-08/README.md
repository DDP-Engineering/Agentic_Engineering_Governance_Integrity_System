<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0.0 Implementation Review - 2026-08-08

Read-only review of the runnable AEGIS payload under `05_Software/aegis/`.
No repository file was modified. WAEGIS and AEGIS Light were out of scope.

## Documents

| Document | Contents |
| --- | --- |
| `01_DEFECTS.md` | Every defect found, severity-ordered, with reproduction and fix sketch. |
| `02_SIMPLIFICATION.md` | Dead code, unenforced configuration, and redundant checks to remove. |
| `03_REMEDIATION_PLAN.md` | Sequenced batches with effort, risk, and acceptance evidence. |

## Verdict

The implementation is in good structural health. It is **not** a sprawling or
speculative codebase: there are zero unreferenced module-level symbols across
594 package symbols and 34 hook symbols, the linter is clean, all 639 tests
pass, every version declaration agrees at 3.0.0, and the 39-command CLI surface
matches `CLI_API_REFERENCE.md` exactly. A stock deployment drives a real run
end-to-end without a stumble.

The defects are not architectural. They cluster into four concrete, local
patterns:

1. **The guardrail hooks do not hold.** Six independent bypasses were
   reproduced against working controls, including ordinary shell syntax
   (`echo x>file`) and a silent fail-open for every non-ASCII policy pattern on
   Windows. This is the layer whose whole purpose is to hold.
2. **Error paths crash instead of reporting.** Malformed durable state escapes
   the CLI error boundary as raw Python tracebacks - including inside the code
   that builds the operator's recovery message, so a broken run takes down its
   own escape hatch.
3. **Two copies of one constant disagree.** `component-adoption` is a
   collection stage in one table and not in the other, so `aegis run context`
   cannot see the form that stage exists to produce.
4. **Analysis silently fails open.** Path matching misses repository-root files
   for `**/` patterns and lets `*` cross directory separators, and the
   working-tree audit evaluates nothing when `.agentic` sits below the Git root.

The most common shape, by a wide margin, is **a fix that was applied in one
place and not in its siblings**. Five of the highest-severity defects are
literally this: `store.py` validates a JSON top-level type in one of three
readers; `gates.py` fixed a log-name collision that `check_execution.py` still
has; `guard_read_path.py` fails closed on an unknown tool while
`guard_write_zone.py` fails open. That is a good problem to have - each fix is
small, local, and already has a correct sibling to copy.

## On over-engineering

The owner's constraint was to avoid burdening the implementation with more
checks. Reviewed against that constraint, the finding is that AEGIS is **not**
over-engineered in the abstract, but it does carry weight that earns nothing:

- ~2,300 lines of code and tests exist for a **RepoWise integration that cannot
  succeed** and a **model-evaluation pilot that shipped its answer**.
- The `[alignment]` configuration table - five keys, a cross-field consistency
  rule, and operator documentation describing it as blocking - **is validated
  and then never read by anything**.
- `spec_items` is a **mandatory** schema-3 key that is **always empty**, and two
  documents describe content it never carries.
- INV-8's missing-row branch reports the same defect INV-2 already reports, so
  one problem costs the human two waiver approvals.

None of these require new checks to fix. Every item in `02_SIMPLIFICATION.md`
is a **deletion**. The single most valuable thing available here is removing
about 2,900 lines that no user can reach.

## Recommended posture

Fix batches 1 and 2 in `03_REMEDIATION_PLAN.md` (guard bypasses, crash-to-
traceback paths, the stage-table split). They are small, independently
testable, and each has a correct sibling in the codebase to copy from. Then
take the deletions in batch 3, which reduce surface without changing behavior.
Everything below that is genuinely optional.

## Method and scope of confidence

Reviewed: the full `05_Software/aegis/` tree - CLI package (22 modules), the 7
guardrail hooks, the 5 host adapters, template documents, launcher scripts, and
`tools/local_model_pilot.py`.

Evidence gathered:

- Baseline run of the suite: **639 passed, 3 skipped**; `ruff check` clean.
- Branch coverage measured over the package: **85%** overall; lowest are
  `evidence_forms.py` 59%, `repowise.py` 65%, `report.py` 67%.
- Static dead-symbol sweep across every text file in the repository: **zero**
  unreferenced module-level symbols.
- A stock template was deployed into a scratch Git repository and driven
  through a real run; guard bypasses and crash paths were reproduced there
  against working controls.

Findings carry an explicit verification tag:

- **[reproduced]** - reproduced first-hand in a scratch deployment, with a
  control case proving the test harness was sound.
- **[code-verified]** - confirmed by executing or reading the exact code path;
  deterministic and not dependent on environment.
- **[reported]** - established by a reviewing agent through execution, recorded
  here without independent re-execution. Treat as high-confidence but confirm
  before acting.

Not covered: WAEGIS, AEGIS Light, real-host adapter behavior (Codex, Claude
Code, Pi, OpenCode, Qwen were read as configuration, not run), and non-Windows
execution. Several findings are POSIX-only or Windows-only and are marked.
