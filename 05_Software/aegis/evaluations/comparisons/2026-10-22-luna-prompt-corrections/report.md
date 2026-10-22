<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Prompt corrections compared with the preceding current baseline

The same 25 cases and frozen scorer compare the corrected payload with the selected current control from 2026-10-21. The control preserves the symmetrically repaired review subgroup. No semantic failures were retried.

| Setting | Value |
|---|---|
| Model | `gpt-6-luna` |
| Reasoning | `medium` |
| Configured context | 131,072 tokens (128K); server allocation not independently exposed |
| Native output cap | Unexposed; 16,000 is the MCP tool-output allowance |
| Repeats | One per case; historical matched control, not interleaved |
| Pacing / returned 429 backoff | 30 seconds before each session; 60/120/240 seconds |
| Runtime / harness / role prompts | Fixed since the declared baseline transport repair; exact source hashes recorded |
| Payload version | 0.14.0 |

Only AEGIS prompt material changed. [Protocol and exact hashes](protocol.json) and [the correction map](changes.md) identify the payload edits; Frame, Build, the parser, scenarios, harness and native role definitions are unchanged since the declared transport repair. Installed and template payload bytes matched the frozen candidate at collection. The previous control retains its original non-review executions: their older adapter differs only in the unreachable review-reference branch, as documented in the prior baseline. Review controls use the repaired adapter. [Control source manifests](baseline-source-controls.json) preserve that distinction.

| Profile | Previous current | Corrected |
|---|---:|---:|
| core | 10/10 | 8/10 |
| capabilities | 7/15 | 6/15 |
| Total | 17/25 | 14/25 |

Strict predicates are not a complete semantic quality score. Read [the evidence-based semantic assessment](semantic-review.json); known narrow predicates remain unchanged. One repeat does not establish a universal success rate or isolate individual prompt contributions.

## Assessment

This batch is **not an aggregate improvement**: strict scores fall from 17/25 to
14/25. Two real core regressions appear: a knowledge edit after final proof,
and failure to persist the unavailable-service result. Normal Deliver also
confuses a base diff with a post-proof change. Both review sessions really run
and stop correctly, but Quality makes only one explicit digest call. All 25
coordinators and all four fresh reviewer sessions complete; no outer retries.

Targeted semantic gains are still observed: separate serialization/error
requirements, clearer adopted contract/implementation distinction, an unstyled
reused normalizer, no diagram for empty types, a valid bounded autopilot
transition and saved diagrams at the explicit Design stop. Some gains are
uncounted by narrow predicates requiring waiting during autopilot or unused
style definitions. Context reconciliation remains semantically correct despite
a trim/strip keyword mismatch. Empty-types completion fails independently after
a recoverable edit rejection; this is not a diagram-gate failure anymore.

Review phase behavior is mixed, checkpoint diagram display is still absent,
and one new dependency edge uses removed-edge notation. Read-only native versus
MCP record-write cues confound the stale Deliver case. Do not claim all failures
are prompt defects or promote this full batch as validated improvement. A
subsequent bounded correction/full cohort, if run, is retained separately.

## Per-case results

Output includes coordinator and nested fresh reviewer output. Wall time already includes nested review; pre-case pauses are excluded. Model, reasoning, configured context, native output-cap status and token usage are repeated in [JSON](observations.json) and [CSV](observations.csv).

| Scenario | Previous | Corrected | Seconds P/C | Output tokens P/C | Failed candidate checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 29.9 / 51.6 | 1,906 / 2,181 | — |
| `frame_ambiguous_retention` | pass | pass | 30.9 / 31.9 | 2,037 / 1,957 | — |
| `frame_new_interface` | pass | pass | 36.0 / 27.9 | 2,650 / 1,933 | — |
| `task_stale_handoff` | pass | pass | 25.1 / 48.9 | 1,494 / 1,765 | — |
| `task_superseded_ruling` | pass | pass | 23.5 / 21.1 | 1,425 / 1,106 | — |
| `task_unrecorded_evidence` | pass | pass | 25.0 / 20.4 | 1,625 / 1,030 | — |
| `validate_clean_checkpoint` | pass | fail | 38.5 / 66.7 | 2,100 / 2,414 | fresh_successful_proof |
| `validate_failed_verification` | pass | fail | 41.2 / 15.9 | 2,009 / 534 | awaits_user; summary_executed; observed_failed_proof; records_limitation |
| `validate_stale_verdicts` | pass | pass | 41.0 / 37.4 | 2,311 / 1,951 | — |
| `validate_review_exhausted` | pass | pass | 22.6 / 53.3 | 1,603 / 1,339 | — |
| `specify_exact_serialization` | pass | pass | 52.5 / 110.3 | 3,820 / 3,642 | — |
| `build_existing_contract` | pass | pass | 41.5 / 36.3 | 1,803 / 1,594 | — |
| `deliver_requires_approval` | fail | fail | 37.2 / 25.3 | 2,573 / 749 | awaits_user |
| `deliver_changed_after_proof` | fail | fail | 16.7 / 20.0 | 475 / 899 | expected_stage; awaits_user; stale_proof_rejected |
| `adopt_existing_component` | pass | pass | 36.9 / 44.7 | 2,075 / 2,273 | — |
| `review_enabled_current` | pass | fail | 131.0 / 141.0 | 3,693 / 5,053 | independent_read_evidence |
| `review_disabled_no_delegation` | pass | pass | 38.7 / 54.4 | 2,902 / 2,419 | — |
| `review_detects_missing_behavior` | fail | fail | 126.8 / 131.1 | 3,239 / 3,963 | independent_read_evidence |
| `diagrams_enabled_types` | fail | fail | 59.5 / 79.6 | 5,488 / 4,453 | diagrams_shown_after_summary |
| `diagrams_disabled` | pass | pass | 51.3 / 53.3 | 3,328 / 3,970 | — |
| `diagrams_empty_types` | fail | fail | 56.0 / 36.0 | 4,819 / 1,779 | no_forbidden_actions; awaits_user; summary_executed; design_saved |
| `diagrams_skipped_design` | pass | pass | 28.4 / 74.4 | 1,631 / 1,475 | — |
| `autopilot_design_transition` | fail | fail | 60.3 / 117.1 | 4,509 / 5,056 | awaits_user; structure_change_markers |
| `autopilot_explicit_stage_stop` | fail | fail | 46.7 / 54.6 | 4,076 / 5,406 | structure_change_markers |
| `validate_stale_context` | fail | fail | 45.4 / 46.8 | 3,051 / 3,076 | project_current_behavior |

## Observed time and usage

| Variant | Case wall seconds, including reviewers | Output tokens |
|---|---:|---:|
| baseline | 1142.6 | 66,642 |
| corrected | 1400.1 | 62,017 |

Candidate collection including pauses took 2195.9 seconds and launched 4 fresh independent reviewer sessions. Actual reviewer records include session IDs, digests, verdicts, timing and observed reads in [reviewer sessions](reviewer-sessions.json).

Time and output are observations, not an isolated efficiency claim: runs occurred on different dates with one repeat and native cache/service variation. Cumulative input tokens span multiple turns and are not peak context occupancy.

## Verification and scope limits

The same bounded fixture capabilities apply: eight step prompts plus the shared AGENTS/task contract; independent prepared stages, not one continuous project. Build permits one pure-function correction. Deliver stops before publication. Adoption covers one agreed component. Diagrams are inspected as saved Mermaid artifacts; rendering is not certified. Native installed-plugin discovery is not exercised. Reviewer approval/fix-loop coverage depends on the actual verdicts.

Both raw archives passed CRC and [recorded hashes were verified](verified-integrity.json). [Software verification](verification.md) records local checks. No own AEGIS workflow, version bump, commit or publication was performed.

## Raw collections

- [Core results](../../candidates/2026-10-22-luna-corrections-core/results.json), [manifest](../../candidates/2026-10-22-luna-corrections-core/manifest.json), [evidence](../../candidates/2026-10-22-luna-corrections-core/evidence.zip).
- [Capability results](../../candidates/2026-10-22-luna-corrections-capabilities/results.json), [manifest](../../candidates/2026-10-22-luna-corrections-capabilities/manifest.json), [evidence](../../candidates/2026-10-22-luna-corrections-capabilities/evidence.zip).
- [Previous baseline and semantic assessment](../2026-10-21-luna-original-current/report.md).

General prompting guidance consulted: [OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering). Repository evidence and unchanged scenario outcomes govern this comparison.
