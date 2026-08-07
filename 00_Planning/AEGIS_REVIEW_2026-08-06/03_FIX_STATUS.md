# Fix Status — all 23 findings closed

Every finding from [02_FINDINGS.md](02_FINDINGS.md), plus the two found while
fixing them, is implemented and verified. **Nothing is committed.**

| Suite | Baseline | Final |
|---|---|---|
| `05_Software/aegis` | 556 passed, 3 skipped | **565 passed, 3 skipped** |
| `05_Software/waegis` | 678 passed, 8 skipped | **698 passed, 8 skipped** |

29 new regression tests. No pre-existing test was modified or broken. Lint is
unchanged: the 6 `E731` in `waegis/tests/test_release_packaging_integrity.py`
and the 2 `F401` in `aegis` (`check_execution.py:27`,
`requirement_store.py:35`) are pre-existing — confirmed by re-running `ruff`
with every change stashed.

## Disposition

| ID | Finding | Fix |
|---|---|---|
| A1 | INV-7 matched AEGIS's own run artifacts | `.agentic/runs` excluded from the scan via a git pathspec, plus a shared `is_generated_run_artifact` for the working-tree audit |
| A2 | Waiving INV-7 invalidated the waiver | Fell out of A1 (`graph.json` lives under `runs/`). Stale waivers now surface as `stale_waivers` in `waive list` |
| A3 | `non-waivable` advertised, not enforced | Label withdrawn — see the reasoning below, which changed the recommendation |
| A4 | INV-7 named the pattern, not the file | Scan surface is now `(path, text)` sections; failures name the file. Matched text still never echoed |
| A5 | `scope-check`/`verify coverage` clean when disabled | Advisory findings inside `issues` (`COMPONENT-GUARD-NOT-ENFORCED`, `-PATH-UNMAPPED`, `-PATH-NOT-FOUND`) plus `enforcement` / `audit_status` keys |
| A6 | Adoption could not create requirements | `stage add` accepted at `component-adoption`; four documents corrected |
| A7 | `coverage_waivers.txt` never seeded | New `aegis adoption coverage-waivers [--write]` |
| A8 | Unreadable close blockers | Blocker id appended, trailing full stop stripped |
| N1 | `workflow.toml` tripped its own scanner | `[guardrails.secrets]` table excluded from the INV-7 surface; the rest of the file still scanned |
| N2 | `secret_scan.py` hook over-matched | Scans only values a call *introduces* — not paths, not replaced text |
| W1 | No test roots for below-root layouts | Depth-aware convention sweep |
| W2 | Source root fell back to the whole numbered tree | Same sweep; `04_Software/VoiceWeaver/src` now proposed directly |
| W3 | Gate extraction read only root build files | Nested project directories scanned; `pytest -q <dir>`, `ruff check <dir>`, `make -C <dir>`, `npm --prefix <dir>` |
| W4 | Colocated-tests false positive | Fell out of W1 |
| W5 | Gate command passed under AEGIS, failed under WAEGIS | Relative `argv[0]` resolved against the child's `cwd`, matching shell semantics |
| W6 | Adoption could not be resumed | Two fixes — see below |
| W7 | Handoff claimed "verified" with failing gates | Says "unverified", names the accepted-failing gates, points at `doctor` |
| W8 | Handoff pointed at a nonexistent doc section | `## Adopt An Existing Project` added to `PROMPT_CHEATSHEET.md` |
| W9 | Every guardrail deployed inactive | Handoff names each inactive policy and how to turn them on. Defaults unchanged |
| W10 | Required field with no default | Fell out of W1; retry message now restates the expected form |
| W11 | Python list repr in prompts | List defaults render comma-separated |
| W12 | One config validation error per invocation | Answers-file failures collected and reported together |
| W13 | `write_access_stages` needs all 15 stages | Error carries a paste-ready `[write_access_stages]` skeleton |

## Two findings whose diagnosis was wrong

**W6 was misdiagnosed, and needed two fixes rather than one.** The review said
`repo.prior-install` refuses because the payload is present. That is the
symptom. The cause is that the resume fingerprint hashes the *whole* answers
mapping, so adding the one answer the stop instructs you to add
(`accept_failing_gates`) changed the hash and disqualified the resume — the
documented fix silently destroyed the thing it was meant to unblock. Fixing
that alone was still not enough: resume only seeds green steps as a
*re-detection hint*, so `repo.prior-install` re-runs regardless and finds the
install anyway. Both were fixed — the journal now records its initial answers
and resume accepts additions while still refusing changes; and the step
recognises a run resuming its own incomplete adoption. Verified by reproducing
the original two-run sequence end to end: run 1 stops at `deploy.gates`, run 2
completes with **exit 0**.

**A3's recommendation was reversed by better reasoning.** The review left the
choice open between enforcing `non-waivable` and withdrawing it. Enforcing it
would not have made secrets unwaivable: the same match also raises
`working-tree:secret-pattern:<path>`, a separate blocker that stays waivable,
so rejecting `waive add INV-7` only moves the waiver one blocker to the left.
The label was also never a policy decision — `CLI_API_REFERENCE.md` documented
it as retained "for zero-waiver output compatibility", and the documented
non-waivable floor is data-integrity failures (schema, locks, journal), not
process rules. Withdrawn.

## Corrections to the review's own text

Recorded so the analysis stays trustworthy rather than quietly improved.

- **A7's premise is false.** The review states "the adoption route already
  computes this set". It cannot: `config.py::_coverage` rejects any
  `coverable_roots` while coverage is disabled, which is WAEGIS's adoption
  default, so during adoption the uncovered set is empty by schema. The command
  therefore works at the moment the set first exists — right after coverage is
  switched on, which is the moment of pain the finding actually describes.
- **A2 overstated the disappearance.** `waive list` already emitted
  `waiver_history` with `"status": "stale"`; the information existed, just not
  beside the active list. "Vanishes with no explanation" should read "is not
  surfaced where anyone looks".
- **A4's "the information exists" was true of a different check.** The path was
  in the working-tree blocker id because `audit_working_tree` scans whole file
  contents. INV-7 scans diff text and had no path to hand — it had to be
  derived, not forwarded.
- **A5 conflated two causes.** `scope-check` early-returns on an unresolved
  minimum; `verify coverage` early-returns on the mode. Same symptom, different
  code path.
- **A8's slug detail is wrong.** `BLOCKER_SLUG_LIMIT` is 72, not 60, and the
  hash is appended only on overflow.
- **W11 was half a defect.** The Python list repr (`default: ['04_Software']`)
  was real. The "questions run together on one line" was an artifact of piping
  stdin — with a real terminal the operator's own newline separates them. Not
  fixed, because there is nothing wrong.
- **W12 was slightly overstated.** The three errors came from two fields, not
  three; `write_access_stages` cannot check exactness before it knows the value
  is a mapping. Batching across fields is still worth having.

## Deliberately not done

- **A5's `audit_local_scope` was left byte-identical** and wrapped instead. It
  also feeds INV-9 and the delivery report, where *any* non-empty issue list is
  a failure — leaking `COMPONENT-PATH-UNMAPPED` there would fail INV-9 for every
  touched path outside a component. A regression wearing a fix's clothes.
- **W9's defaults were not changed.** Shipping guardrails off is defensible
  under the "do not block a new adopter" rule; the defect was that it was
  invisible. Only the visibility was fixed.
- **W13 does not default unlisted stages.** "May write nothing" would silently
  wall off whichever stage was forgotten. The mapping stays exact; the error
  now carries the skeleton.
- **The deep schema validators still fail fast** (one message per invocation).
  Batching them is a refactor of the whole schema layer, which the constraints
  rule out, and the failures an operator actually hits are at the field layer,
  which is now batched.

## New findings, not fixed

1. **Adoption requirements stay `Planned` indefinitely.** Correct — nothing has
   proved them — but activation happens at validation closure and the adoption
   route has no validation stage, so INV-8 will fire on the first standard run
   that touches them. Documented, not engineered around.
2. **The A7 "offer" is a document, not a prompt.** Emitting it through
   `show_stage`'s warnings channel at `baseline-review` was rejected: that is on
   the `run status` hot path and the computation walks every coverage root and
   reads every requirement record. Owner decision if you want it louder.
3. **Two pre-existing ruff `F401`** in `check_execution.py:27` and
   `requirement_store.py:35`, in files nobody touched.
