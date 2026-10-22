<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# AEGIS prompt corrections: matched Luna comparison

**The final valid observations score 18/25 against the previous current control at 17/25. This is a modest observed gain, not a demonstrated general reliability improvement.** All ten core cases pass; semantic regressions and unresolved behavior remain. The batch stays on the local evaluation branch and is not presented as release-ready.

## Configuration and experimental controls

| Setting | Value |
|---|---|
| Requested model | `gpt-6-luna` |
| Reasoning | `medium` |
| Configured context | 131,072 tokens (128K); client configuration, server allocation not independently exposed |
| Native response cap | Unexposed; 16,000 is the MCP tool-output allowance |
| Native CLI | Same pinned binary/hash, 0.163.0-alpha.11 |
| Pacing / returned generic 429 policy | 30 seconds before each CLI session; bounded 60/120/240-second backoff |
| Repeats | One complete cohort per frozen candidate; historical matched control, not interleaved |
| Evaluator | Same cases, fixtures, scorer, tools, runtime and native role prompts since declared baseline transport repair |
| Version | 0.14.0; no release or version bump |

The control is the selected **current** payload from 2026-10-21, not the earlier original-master 12/25 result. The original eight step files plus shared AGENTS/task guidance are exercised by 25 independent bounded scenarios. Exact changes and hashes are in [the correction map](changes.md), [control-to-candidate diff](baseline-prompt-changes.diff), [additional correction diff](preceding-prompt-changes.diff) and [protocol](protocol.json). Frame, Build and parser bytes are unchanged. Installed/template bytes matched the frozen candidate at collection.

The first full candidate scored 14/25 and is preserved in [its complete report](../2026-10-22-luna-prompt-corrections/report.md). A further restricted correction restored final-proof ordering and failure recording, while retaining the first cohort. No individual semantic failure was selectively rerun for a better score.

| Profile | Previous current | First candidate | Final valid observations |
|---|---:|---:|---:|
| Core | 10/10 | 8/10 | 10/10 |
| Capabilities | 7/15 | 6/15 | 8/15 |
| Total | 17/25 | 14/25 | 18/25 |

## External capacity is excluded from prompt scoring

One initial Spec-role process was rejected with **Selected model is at capacity**. The native CLI exposed no HTTP status code; its capacity message did not match the frozen returned-429 retry classifier. Per the user instruction, this is an external service condition and **does not count against the prompts**. The frozen runner retained that failure; repeating the same delegate call reused the cached failed observation rather than launching a second process.

The first operationally complete follow-up, selected regardless of its semantic grade, supplies this scenario in the canonical comparison. It completed both roles with no capacity error and still fails: Spec treats untracked files absent from HEAD as unavailable current scope instead of reading the available checkout files. Quality correctly identifies the accepted None/ValueError behavior missing. No semantic follow-up was retried. See [selection](selection.json), [user-steered recovery protocol](operational-recovery-protocol.json), [excluded external observation](excluded-external-observations.json) and [recovery results](operational-recovery-results.json).

The excluded execution also created an extra journal **before** the capacity rejection. This is a real independent semantic finding, retained in the raw evidence and semantic assessment; the follow-up does not erase it or demonstrate the duplicate-journal risk solved. The original [raw observations](observations.json) and every raw case grade remain unchanged.

## Evidence-based assessment

- Confirmed observations: two independent Specify requirements; explicit contract-versus-implementation documentation; valid saved autopilot transition instead of malformed report; no diagram for empty types; enabled diagram artifacts at an explicit Design stop. Final-proof ordering and unavailable-verification recording recover the first cohort regressions.
- The strict gain consists of `diagrams_empty_types` and `autopilot_explicit_stage_stop` changing fail to pass, offset by `diagrams_disabled` changing pass to fail. Core stays equal to the control.
- Remaining real problems: both Deliver cases leave pause/return records unsaved; normal Deliver still conflates base diffs with post-proof changes despite a matching candidate digest; disabled-diagram Design invents a scope conflict; actual checkpoint diagrams are not displayed; initial pre-capacity duplicate journal; Spec current-tree/HEAD confusion.
- Review activation works, but final-proof prerequisites are still inconsistently misread. Both role sessions in each canonical enabled case are real and complete; genuine None-input omission is detected by Quality in the recovered case. Native plugin discovery and an approved-review happy path are not established.
- Additional semantic limits: the non-ASCII escaping policy is fixed without an explicit owner choice in both the control and final Specify sample; Adopt includes task/investigation material in current-state knowledge; some summary fences and full boundary-choice menus are omitted.
- Both context files are correctly reconciled and final proof runs afterward. Its raw failure is a narrow trim/strip keyword predicate despite equivalent surrounding-whitespace wording. Extra evolution work is honestly disclosed.
- Bounded-autopilot ready/completed/no is an explicit candidate recording clarification versus the frozen universal pause expectation. Treat this as a contract interpretation to review, not an unequivocal scorer bug or a free score adjustment.

Read the [25-case semantic assessment](semantic-review.json) beside strict grades. One valid observation per snapshot cannot establish statistical reliability, isolate effects of individual files, or rule out model variability. The external-capacity case was excluded operationally, not regraded. No failure keyword was silently changed into a pass.

## Per-scenario comparison

Output includes service-reported coordinator and fresh reviewer output. Wall time includes nested review but excludes the pre-case pause. Model, reasoning, context, native output-cap status, reasoning tokens and artifact source are repeated per row in [canonical JSON](canonical-observations.json) and [CSV](canonical-observations.csv).

| Scenario | Control | Candidate | Seconds C/N | Output tokens C/N | Failed candidate checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 29.9 / 75.1 | 1,906 / 2,613 | — |
| `frame_ambiguous_retention` | pass | pass | 30.9 / 29.4 | 2,037 / 2,601 | — |
| `frame_new_interface` | pass | pass | 36.0 / 113.3 | 2,650 / 2,253 | — |
| `task_stale_handoff` | pass | pass | 25.1 / 25.0 | 1,494 / 1,381 | — |
| `task_superseded_ruling` | pass | pass | 23.5 / 50.8 | 1,425 / 1,048 | — |
| `task_unrecorded_evidence` | pass | pass | 25.0 / 25.0 | 1,625 / 1,366 | — |
| `validate_clean_checkpoint` | pass | pass | 38.5 / 42.8 | 2,100 / 2,644 | — |
| `validate_failed_verification` | pass | pass | 41.2 / 41.4 | 2,009 / 2,466 | — |
| `validate_stale_verdicts` | pass | pass | 41.0 / 84.9 | 2,311 / 2,241 | — |
| `validate_review_exhausted` | pass | pass | 22.6 / 41.6 | 1,603 / 2,035 | — |
| `specify_exact_serialization` | pass | pass | 52.5 / 70.0 | 3,820 / 3,754 | — |
| `build_existing_contract` | pass | pass | 41.5 / 84.1 | 1,803 / 1,716 | — |
| `deliver_requires_approval` | fail | fail | 37.2 / 35.4 | 2,573 / 1,117 | awaits_user |
| `deliver_changed_after_proof` | fail | fail | 16.7 / 35.8 | 475 / 399 | expected_stage; awaits_user; summary_executed |
| `adopt_existing_component` | pass | pass | 36.9 / 79.4 | 2,075 / 1,982 | — |
| `review_enabled_current` | pass | pass | 131.0 / 196.9 | 3,693 / 5,522 | — |
| `review_disabled_no_delegation` | pass | pass | 38.7 / 37.3 | 2,902 / 2,807 | — |
| `review_detects_missing_behavior` | fail | fail | 126.8 / 193.0 | 3,239 / 4,282 | independent_read_evidence |
| `diagrams_enabled_types` | fail | fail | 59.5 / 63.7 | 5,488 / 6,717 | diagrams_shown_after_summary |
| `diagrams_disabled` | pass | fail | 51.3 / 36.8 | 3,328 / 714 | awaits_user; design_saved |
| `diagrams_empty_types` | fail | pass | 56.0 / 70.4 | 4,819 / 2,979 | — |
| `diagrams_skipped_design` | pass | pass | 28.4 / 43.2 | 1,631 / 2,951 | — |
| `autopilot_design_transition` | fail | fail | 60.3 / 67.3 | 4,509 / 5,554 | awaits_user |
| `autopilot_explicit_stage_stop` | fail | pass | 46.7 / 43.2 | 4,076 / 3,390 | — |
| `validate_stale_context` | fail | fail | 45.4 / 45.4 | 3,051 / 3,972 | project_current_behavior |

## Observed usage and time

| Variant | Selected case seconds, including review | Output tokens |
|---|---:|---:|
| baseline | 1142.6 | 66,642 |
| corrected | 1631.4 | 68,504 |

The final full cohort plus operational recovery physically collected 26 coordinators and 6 fresh role-process attempts in 2608.7 seconds including pauses. One role attempt was externally rejected. The canonical comparison contains 25 completed coordinators and four completed, distinct fresh reviewer sessions. [Canonical reviewer records](canonical-reviewer-sessions.json) retain IDs, digests, observed reads, verdicts, output and time; [initial cohort reviewer records](reviewer-sessions.json) retain the capacity error.

Time is observational: service/cache variation, different dates, one sample and concurrent local software tests prevent an isolated prompt-speed claim. Cumulative input usage spans turns and does not measure peak context occupancy. Native backend identity/output cap are not independently exposed.

## Verification and limits

Final offline software verification: **551 passed, 2 skipped**; focused structural guards 58 passed; changed Python test compiled. [Verification details](verification.md) preserve the initial wording-guard failure and successful rerun. The model-evaluation harness and its predicates were not changed.

All three raw candidate archives passed CRC and their recorded integrity hashes were verified. [Raw record inspection](record-observations.json) confirms complete legal prologues and authoring pointers in all 25 initial cohort cases, while retaining the extra-journal observation. [Verified hashes](verified-integrity.json), [archive checks](archive-checks.json), [source controls](baseline-source-controls.json) and [metrics](metrics.json) support the comparison.

Scope remains bounded: independently prepared stages, not a continuous project; one pure-function Build change; pre-publication Deliver; one-component Adopt; live fresh-review fallback rather than installed-plugin discovery. Mermaid artifacts are inspected as text, not rendered or syntax-certified. An all-approved review/fix-loop flow is not demonstrated.

No own AEGIS workflow, commit, push, publication or version bump was performed. The payload stays 0.14.0. The prompt batch remains experimental because semantic regressions persist despite the modest strict gain.

## Preserved collections

- [Initial core results](../../candidates/2026-10-22-luna-validation-records-core/results.json), [manifest](../../candidates/2026-10-22-luna-validation-records-core/manifest.json), [evidence](../../candidates/2026-10-22-luna-validation-records-core/evidence.zip).
- [Initial capability results](../../candidates/2026-10-22-luna-validation-records-capabilities/results.json), [manifest](../../candidates/2026-10-22-luna-validation-records-capabilities/manifest.json), [evidence](../../candidates/2026-10-22-luna-validation-records-capabilities/evidence.zip).
- [Selected valid recovery](../../candidates/2026-10-22-luna-review-capacity-diagnostic-1/results.json), [manifest](../../candidates/2026-10-22-luna-review-capacity-diagnostic-1/manifest.json), [evidence](../../candidates/2026-10-22-luna-review-capacity-diagnostic-1/evidence.zip).
- [Previous current control](../2026-10-21-luna-original-current/report.md) and [first complete candidate](../2026-10-22-luna-prompt-corrections/report.md).

General prompting guidance consulted: [official OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering). Repository evidence and unchanged observed checks determine the conclusions.
