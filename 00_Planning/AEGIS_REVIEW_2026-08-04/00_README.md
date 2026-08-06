# AEGIS V2 Review — 2026-08-04

Review of the **full AEGIS payload** (`05_Software/aegis`, CLI 2.1.0,
schema_version 3) on branch `AEGIS_V2`. AEGIS Light is out of scope.

## Constraints this review was written under

The owner's rules, applied to every finding:

1. **Only two things justify a change**: a real software bug, or a workflow
   problem that obstructs the developer/agent.
2. **No over-engineering for hardening or protection.** AEGIS is run by a
   developer plus an LLM on their own git repo. It is not a security boundary
   against a hostile user, and git is already the recovery mechanism.
3. **The workflow must assist the agent, not block him.** Every gate needs an
   escape hatch; every dead end needs a documented way out.
4. **No large changes.** Nothing here requires a refactor across modules or a
   substantially rewritten test suite.

Anything that failed those tests was moved into a clearly-labelled *observations*
section rather than dropped silently, so the reasoning is on file and the same
ground is not re-covered later.

## Baseline

`python -m pytest` in `05_Software/aegis` → **433 passed in 27.29s**, before any
change. Every bug reported here is therefore something the suite does not cover;
suite-green is not evidence against any of them.

## Documents

| File | Contents |
|---|---|
| [01_BUGS.md](01_BUGS.md) | 16 software defects from source analysis, each with a failure scenario and an implementable fix |
| [02_WORKFLOW.md](02_WORKFLOW.md) | 12 workflow obstructions + 9 documentation defects |
| [03_CODE_HEALTH.md](03_CODE_HEALTH.md) | Dead-code sweep (result: none), one latent duplication trap, and the observations deliberately *not* proposed as work |
| [04_FIELD_TEST.md](04_FIELD_TEST.md) | What happened installing V2 into a real repo (`F:\2026_VoiceWeaver`, 1.4.1 → 2.1.0) and driving a real change: 7 more bugs, 4 more workflow findings |

Findings are labelled `B<n>` (bugs) and `W<n>` / `D<n>` (workflow, docs),
numbered continuously across documents. The IDs are reference labels, not
rankings — the implementation order is below.

## Verification standard

Findings are marked **EXECUTED** (reproduced by running the code during this
review) or **READ** (confirmed by reading the source plus the absence of covering
tests). Agent-proposed findings that did not survive verification were dropped
and are not listed.

Reproduced by execution: B1, B3, B10, B17–B23, W1, W2, W4, W13–W16, and the doc
mismatches D1, D2. **B11 was found by source analysis and then independently
reproduced in the field test** — three gate evidence records, the last one
passing with 104 tests green, and the gate still reported `failed`.

The field test ran against `F:\2026_VoiceWeaver` on a scratch branch
`aegis-v2-test`. Two local commits were made; **nothing was pushed and no remote
was touched.**

## The five findings that matter most

**1. INV-1 makes every full run after the first unpassable — [B10](01_BUGS.md)**
INV-1 compares the repository-wide durable requirement register against one run's
run-local checks. There is no durable check register anywhere in the payload, so
the invariant is structurally unsatisfiable from the second full run onward.
Executed: a two-requirement register with a run citing only its own requirement
yields `holds=False, policy=blocking`. In a repository carrying 110 requirements
(VoiceWeaver) or 495 (AudioMancer), every full feature run fails INV-1 listing
every requirement it did not touch. Quick runs bypass INV-1 entirely, which is
why `--quick` work has not surfaced it. **Needs an owner decision** between the
two options in B10.

**2. A fixed gate can never go green again — [B11](01_BUGS.md)**
`gates.py` contains no supersession logic. A failing gate's evidence stays
`active` forever, so after you fix the test, `verify run` still exits 1 and the
delivery hook still denies every push. The equivalent logic exists for *check*
evidence and simply excludes gates.

**3. Requirements can only be created as `functional` — [W1](02_WORKFLOW.md)**
`stage add` hardcodes `_new_requirement_id("functional")`, the validator rejects
any `category` that disagrees with the ID prefix, and the docs demand seven other
categories while `AGENTS.md:63` forbids inventing IDs. The agent is caught
between two rules it cannot both obey. Fix is one `--category` flag.

**4. A run cannot be abandoned — [W2](02_WORKFLOW.md)**
`aegis run` offers only `start|status|resume|select`. No abandon/abort/cancel verb
exists, and `MERGE_AND_REBASE.md:125` forbids deleting the run directory — yet
`AGENTS.md:214` ends its stop menu with "…or abort". A developer who changes
their mind has no exit, and the agent will hallucinate the command.

**5. Routing backwards is gated by the blockers you are routing away from — [W3](02_WORKFLOW.md)**
To route from implementation back to requirement, you must first produce red
*and* green evidence for checks you are about to delete, or waive one blocker per
check. The honest correction costs more than pushing forward dishonestly. And per
[B13](01_BUGS.md), doing it correctly resets your requirements to `Planned` and
destroys their `created_on`.

## Suggested implementation order

**Phase 1 — make a run passable and recoverable** (nothing else matters until this holds)
1. **B10** — INV-1 scope. *Decided 2026-08-04: implement **Option A** — scope
   coverage to run-owned requirements. Option B is rejected.*
2. **B11** — gate supersession: a fixed gate must be able to go green
3. **B17** — capture gate stdout/stderr into `output_log`; without it an agent
   cannot diagnose any gate failure, which compounds B11

**Phase 2 — remove the dead ends** (small, high leverage)
4. **W4** — stop `config validate` misdirecting to a new run (one function)
5. **W1** — `stage add --category` (one flag)
6. **W2** + **W16** — `run abandon` + `run list`, and warn when `run start` leaves a run behind
7. **W5** — hooks must not deny writes to `workflow.toml` (~3 lines × 4 hooks)
8. **B1** — INV-9 `AttributeError` (one line)
9. **B14** — move one call inside a `try`
10. **B18** — delivery `stage close` must re-check blocking invariants
11. **W13** — write `documents/UPGRADING.md` (pure prose; unblocks every existing 1.x repo)

**Phase 3 — correctness**
12. **B13**, **B3**, **B12**, **B2**, **B6**, **B19** (`--approver`), **W14** (validate enums at `apply`, name the tokens)

**Phase 4 — ergonomics**
13. **W11** — every error message ends with its remediation command (pure text)
14. **W9** — render the field help that already exists in the schema
15. **W3**, **W6**, **W7**, **W8**, **W10**, **W12**, **W15**, **B20**, **B21**, **B22**

**Phase 5 — documentation and packaging**
16. **D1–D9**, **H1**'s one-line comment from `03_CODE_HEALTH.md`, and **B23**
    (drop `egg-info`, add `.venv/` to `.gitignore`, fix `install.ps1` stderr handling)

## Decisions on record

**B10 — INV-1 semantics. Decided 2026-08-04: Option A.** INV-1 means *"every
requirement this run owns is covered by a check."* Repository-wide coverage
remains the job of `audit_traceability`'s `REQ-LINK-MISSING`. Option B (checking
durable `linked_tests` repository-wide) is rejected as the larger change and
substantially redundant with that audit.

**W22 — INV-6 for adoption runs. Decided 2026-08-04: report not-applicable.**
Adoption runs have no evidence-producing stage, so INV-6 can never hold for them.
It must return `not-applicable` with `holds=null` for adoption runs, exactly as it
already does for quick runs — reusing the existing `_quick_not_applicable`
machinery and preserving the honest three-way distinction between
`not-applicable`, `waived`, and `disabled`. Once that lands, **extend B18 from
`delivery` to `adoption-delivery`** so both close paths re-check blocking
invariants. Rejected: requiring adoption runs to carry evidence (a real change to
the adoption profile and stage schema, larger than anything else remaining), and
leaving B18 delivery-only (an undocumented asymmetry where adoption gets a weaker
close gate). **Assigned to Batch 5.**

No open questions remain — every finding in this review is now mechanical.

## Implementing this review

Work in batches, one fresh session each, so context stays clean and every batch
ends on a green test run. Suggested grouping by file coupling:

| # | Batch | Findings | Files |
|---|---|---|---|
| 1 | Gates ✅ **DONE 2026-08-04** | B11, B17, B12, B16 | `gates.py` |
| 2 | Invariants ✅ **DONE 2026-08-04** | B10, B1, W8 *(partial — see W17)*, W12 *(withdrawn, revert in Batch 3)* | `invariants.py` |
| 3 | CLI surface ✅ **DONE 2026-08-04** | W12 revert, W2, W16, W1, W4, B19, B20, B21, B22 | `invariants.py`, `cli.py`, `store.py`, `models.py`, `stage_forms.py`, `verification.py`, `requirement_store.py` |
| 4 | Stage forms ✅ **DONE 2026-08-04** | W18, B13, B18, B3, W14, W9, W3, W7 + **B26 fixed in passing** | `invariants.py`, `stage_forms.py`, `requirement_store.py`, `_form_io.py`, `stage_schema.py`, 2 docs |
| 5 | Hooks, paths & degradation ✅ **DONE 2026-08-04** | W22, B27, W20, W21, W5, W17, W19, B14, B15, B2, B6, B7, B4, B5, B8 | `hooks/*.py`, `waiver_targets.py`, `requirements.py`, `verification.py`, `store.py`, `cli.py`, `stage_forms.py`, `invariants.py`, `working_tree.py`, `paths.py`, `persistence.py` |
| 6 | Docs & packaging ✅ **DONE 2026-08-04** | W11, W13, D1–D10, H1 + B25, B23, B24 | `documents/`, `skills/`, `.gitignore`, `install.ps1`, `gates.py`, `stage_forms.py` |
| 7 | **Release prep** (remaining) | **B28**, full-profile field test, CHANGELOG + version bump | `tools/run.sh` |

**Batch 4 result (2026-08-04):** W18, B13, B18, B3, W14, W9, W3, W7 implemented.
Test suite **477 → 505**, independently re-run and confirmed. One test edited with
justification (`test_invalid_required_integration_is_not_a_waiver_target` →
`..._is_a_waiver_target`; it asserted the non-waivable floor that W7 removes).

**B26 was found and fixed in passing, and the scope expansion was justified** —
B18 was unimplementable without it, because INV-10 fails on every full run once
validation closes. This review missed B26 entirely; it is the same severity class
as B10 and B11. Four follow-ups raised: **B27**, **B25**, **W20**, **W21**.

**Baseline for Batch 5 onward is 505 passing.**

**Batch 5 result (2026-08-04):** all 15 findings implemented. Test suite
**505 → 533 passed, 3 skipped**, independently re-run and confirmed. No test
edited, no scope expansion needed, nothing new raised.

B27 was deliberately narrowed and the narrowing is endorsed: the drift check
covers only the records activation would touch, because blocking on drift in a
requirement the close will not rewrite would be a *new gate* rather than a fix,
and INV-10 already reports it at delivery. The check sits in
`_standard_stage_blockers` at validation rather than inside
`_activate_green_requirements`, since by the time `_approve_stage` runs, the close
is already accepted. A shared `_activatable_requirements` selector keeps the check
and the write from drifting apart.

**⚠ The 3 skipped tests are Windows-only skips, so B5 (POSIX file modes) and B7
(backslash filenames) are currently UNVERIFIED.** Run the suite once on
Linux or macOS before release — see "Before release" below.

**Baseline for Batch 6 is 533 passed / 3 skipped.**

**Batch 3 result (2026-08-04):** W12 reverted; W2, W16, W1, W4, B19, B20, B21, B22
implemented. Test suite **448 → 477**, independently re-run and confirmed. Two
pre-existing tests were edited with justification, both asserting
`approver == "human"` — the exact literal B19 replaces — and neither was weakened.
Two new findings raised: **W18** (unsorted offender list, Batch 4 task 0) and
**W19** (a corrupt-graph run cannot be abandoned, Batch 5).

**Baseline for Batch 4 onward is 477 passing.**

**Batch 1 result (2026-08-04):** B11, B17, B12 implemented in `gates.py`; B16
verified subsumed by B11 and its suggested stage filter deliberately **not**
applied (see "Known residual, accepted" in `01_BUGS.md` — do not reinstate it).
Test suite **433 → 440**, independently re-run and confirmed. One pre-existing
test in `test_aegis_v2_policy.py` was narrowed with justification: B12 necessarily
routes a missing executable through the shell on Windows, so the synthesized
exit 127 no longer applies there; the exact-127 assertion is now POSIX-only and
the cross-platform property (non-zero exit, command named in stderr) is retained.
New finding **B24** raised from that work. `verification.py` was not modified.

**Batch 2 result (2026-08-04):** B10 (Option A), B1 and W8 implemented in
`invariants.py`; test suite **440 → 448**, independently re-run and confirmed; no
test edited. Three corrections came out of it:

- **B10's proposed empty-`owned` fallback was rejected, correctly.** Falling back
  to the full register would have reintroduced B10 during intake and alignment of
  every run after the first, when the register is populated but the run has not
  yet imported its requirement stage record. It also buys nothing on a genuine
  first run, where the register is empty and `missing` is empty either way. The
  implemented behaviour distinguishes "no record yet" (vacuous pass) from "record
  applied but naming nothing" (loud, waivable failure).
- **W12 is withdrawn and must be reverted** — see `02_WORKFLOW.md`. It silently
  widens human approvals, including INV-5 and INV-9 where the offender's identity
  is the whole substance of the approval. First task of Batch 3.
- **W8 is only half-closed.** New finding **W17**: `waive list` still raises,
  because `waiver_targets` and `verification.py:115` load the register
  independently of `evaluate()`. Assigned to Batch 5.

**Batch 3 result (2026-08-04):** W12 reverted, then W2, W16, W1, W4, B19, B20,
B21 and B22 implemented. Test suite **448 → 477**, with a new
`tests/test_cli_surface.py`. Two previously-passing tests were edited, both
because they asserted the literal `approver == "human"` that B19 deliberately
replaces; each edit is annotated in place and neither weakened an assertion
(one now pins the git-derived default exactly, the other passes `--approver`
explicitly). Decisions taken:

- **`run abandon` is terminal.** `graph.outcome` is optional-by-absence like
  `profile` and `waivers`, so every pre-2.1.0 graph still loads against the
  closed schema and only `""` and `"abandoned"` are legal values. `run select`
  refuses an abandoned run outright and names `aegis --run <id> run status` as
  the read-only route; `run status` reports it as `complete: true`,
  `outcome: "abandoned"`, `next: "none"`. Marking it complete is what makes
  every mutating stage command decline it, so there is no second enforcement
  path to keep in step.
- **`--approver` defaults to git, falls back to `"human"`.** `models.py` accepts
  any non-empty string and keeps `"human"` — a repository with no configured git
  identity behaves exactly as it did before.
- **B20 was scoped by whether a run is genuinely needed.** `requirement
  list/show` and `config *` tolerate an unresolvable run; `stage *` and every
  other mutating command still fail hard on `RUN-POINTER-STALE`. The stale
  message now names the parse cause and reuses `_pointer_missing_remediation`,
  with the unloadable run excluded so it is never offered back as its own
  remedy.
- **B21 does not touch `_gate_result`.** `run_verification` now records its
  aggregate verdict in `validation-summary.json` as `status`, and `verify
  status` exits on that. B16's rejected stage filter was not reinstated.

**Baseline for Batch 4 onward is 477 passing.**

> **Note on running the suite:** `test_release_hygiene.py:161` fails if
> `__pycache__` or `.pyc` files exist anywhere under `template/`. Running Python
> against the template creates them. Use `PYTHONDONTWRITEBYTECODE=1`, or clean
> with `find template -name __pycache__ -type d -exec rm -rf {} +` before running
> the suite. This is the test doing its job, not a regression.

Start with Batch 1 — B17 makes every later batch easier to debug, because gate
failures finally carry their output.

Prompt for each session (swap the batch line):

> Read `00_Planning/AEGIS_REVIEW_2026-08-04/00_README.md`, then implement
> **Batch 1 (Gates): findings B11, B17, B12, B16** as specified in `01_BUGS.md`
> and `04_FIELD_TEST.md`. Only these findings — do not fix anything else you
> notice, and do not refactor. Add the regression tests each finding names. Run
> `python -m pytest` in `05_Software/aegis` and report the count against the
> 433-passing baseline. Do not commit.

## Before release

All six batches are complete. Windows: **543 passed / 3 skipped**.

1. ✅ **POSIX run done 2026-08-04** (WSL Ubuntu 24.04, Python 3.12.3):
   **538 passed, 7 skipped, 1 failed.** The three Windows-only skips ran and
   passed, so **B5** (file modes) and **B7** (backslash filenames) are now
   genuinely verified. The 7 skips are Node-runtime tests (Node is absent in that
   WSL image) — expected, not a defect. Counts reconcile exactly: 546 tests on
   both platforms.

   The 1 failure was **B28**, a pre-existing POSIX-only bug this review had
   missed: `run.sh` uses external `dirname`, so with an empty `PATH` it silently
   resolved its launcher against the caller's cwd. Not introduced by any batch.
   ✅ **Fixed 2026-08-04** in `run.sh` and `install.sh` (which carried the same
   pattern).

   **Final state — both platforms green, zero failures:**

   | Platform | Result |
   |---|---|
   | Windows | 543 passed, 3 skipped |
   | POSIX (WSL Ubuntu 24.04, Python 3.12.3) | 539 passed, 7 skipped |

   546 tests on both. The differing skip counts are platform-specific tests only:
   POSIX file modes and backslash filenames skip on Windows; Node-runtime tests
   skip in the WSL image, which has no Node.

**Nothing remains to implement.** The two items below are validation and release
mechanics, not code.

2. **Field-test a FULL run, not `--quick`.** The original field test in
   `04_FIELD_TEST.md` exercised only the quick profile, which bypasses four
   stages. Every headline bug this review fixed — **B10** (INV-1 scope), **B11**
   (gate supersession), **B26** (INV-10 vs activation) — lives on the *full* path
   and has never been exercised end to end outside unit tests. Drive one full
   `feature` run in `F:\2026_VoiceWeaver` through requirement → design → check →
   implementation → validation → delivery, on a repository that already carries a
   populated requirement register, and confirm it reaches `complete: true` without
   a waiver. That single run is the real acceptance test for this review.

3. **Then commit**, with a CHANGELOG entry and a version bump. The payload
   currently reports 2.1.0; this is a substantial correctness release.

## What is working and should not be touched

- The invariant layer's waiver coverage — all ten invariants have a real escape
  hatch, and `verification.py:185` correctly excludes waived failures from the
  exit code, so the hatch reaches the delivery hook.
- `waiver_targets.collect_waiver_targets`, which unifies stage, invariant, gate,
  audit, and working-tree blockers into one discoverable `waive list`.
- `next_command` (`stage_forms.py:511-576`), and `close_stage` auto-preparing the
  successor stage.
- The three-way honesty of `not-applicable` vs `waived` vs `disabled`.
- The shipped template shipping every gate and guardrail `disabled` /
  `unrestricted` — exactly right for the stated philosophy.
- `ConfigurationError`'s message format, which names the offending key, the legal
  values, and the follow-up command. It is the model the other error messages in
  W11 should copy.
- The concurrency core: lock order is consistently run → journal on every live
  path, and the four-way digest state machine in `graph_transaction` is sound.
- **No dead code, no V1 leftovers, no obsolete schema handling.** The payload is
  clean on that axis — see 03_CODE_HEALTH.md for the verification method.
