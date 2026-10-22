<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Delivery history, reviewer evidence and diagram markers

**Revised: 20/25; preceding valid control: 21/25.** One historical matched cohort does not establish a general reliability rate. Strict scores and semantic findings are reported separately.

| Setting | Value |
|---|---|
| Model | `gpt-6-luna` |
| Reasoning | `medium` |
| Configured context | 131,072 tokens (128K); server allocation unexposed |
| Native response cap | Unexposed; 16,000 is the MCP tool-output allowance |
| Runtime | Same pinned native CLI 0.163.0-alpha.11 and hash |
| Pacing / generic returned 429 backoff | 30 seconds per coordinator/reviewer; 60/120/240 seconds |
| Observations | 25 independent unchanged scenarios; one valid observation per candidate case |
| External observations excluded | 0 |
| Version | 0.14.0; no release/version bump |

The control is the selected **corrected** cohort from [the preceding 21/25 report](../2026-10-22-luna-delivery-evidence/report.md). The scenario JSON, fixtures, tools, scorer, adapter bridge code and native runtime remain fixed. Three payload guides and the **two exercised native reviewer prompts** intentionally change in this experiment. The role prompts are experimental inputs, not evaluator logic. Ten host reviewer source copies are synchronized, but only the Codex pair receives live observations. [Protocol and hashes](protocol.json), [correction map](changes.md), [exact diff](prompt-changes.diff), [prompt sizes](prompt-sizes.json) and `reviewer-prompts/control/` / `reviewer-prompts/candidate/` retain their provenance. Installed/template/frozen payloads match.

| Profile | Control | Revised |
|---|---:|---:|
| Core | 10/10 | 10/10 |
| Capabilities | 11/15 | 10/15 |
| Total | 21/25 | 20/25 |

Automatic gains: `deliver_requires_approval`, `deliver_changed_after_proof`. Automatic regressions: `review_detects_missing_behavior`, `diagrams_enabled_types`, `autopilot_explicit_stage_stop`. No predicates are changed or failed cases silently regraded.

## Evidence-based assessment

This first complete candidate is retained, not selected case by case. It fixes
both Deliver history failures and preserves matching/mismatching candidate
handling. Node maps leave the reused normalizer unstyled in observed artifacts.
Both fresh reviewer pairs interpret focused versus final proof correctly, read
current scope and find the real None/ValueError omission without invented
journal/history requirements. These are useful semantic improvements.

The whole strict score nevertheless falls from 21 to 20. Fail-to-pass: both
Deliver cases. Pass-to-fail: missing-behavior review (one dedicated Quality
digest call instead of two; terminal Git metadata also contains matching
bindings), enabled diagram display (link only), and explicit Design stop (existing Log section removed by a full journal rewrite). These are retained genuine protocol failures,
not external capacity failures or selectively retried outcomes.

Additional regressions within already failing cases: bounded autopilot omits
enabled diagram generation entirely, and context reconciliation omits final
proof by misreading a no-test/config-modification limit as no execution. The
old universal awaits_user and context-word predicate differences also remain
visible. No predicates are weakened or regraded.

A bounded follow-up will clarify explicit candidate-operation boundaries,
numbered diagram generation/presentation actions, preservation of the existing journal/Log during Design edits and heading-only appends and the difference between modifying verification configuration and
running existing configured commands. It will recollect every one of the same
25 scenarios, preserve this full candidate and compare with the original 21/25
control. No individual semantic failure is replaced.

The ordinary review still blocks on a policy diff supplied by the fixture;
Quality approves but Spec requests changes. This is distinct from attributing
that diff to the coordinator. No all-approved final-proof review path is proven.
Summary fences/choice menus and current-state Adopt prose remain inconsistent.
Mermaid is inspected as text, with no renderer certification.


## Per-scenario comparison

Wall time includes nested review and excludes the pre-case pause. Output includes coordinator and fresh reviewer tokens. Model, reasoning, configured context, output-cap status, service-reported reasoning tokens and source artifacts are repeated in [canonical JSON](canonical-observations.json) and [CSV](canonical-observations.csv). Cumulative input usage spans turns, not peak context occupancy; an unexposed reasoning count is not proven zero reasoning.

| Scenario | Previous | Revised | Seconds P/R | Output tokens P/R | Failed revised checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 63.0 / 39.3 | 2,022 / 2,239 | — |
| `frame_ambiguous_retention` | pass | pass | 37.0 / 41.5 | 2,336 / 2,200 | — |
| `frame_new_interface` | pass | pass | 55.8 / 35.5 | 1,828 / 2,379 | — |
| `task_stale_handoff` | pass | pass | 90.6 / 23.2 | 1,724 / 1,620 | — |
| `task_superseded_ruling` | pass | pass | 65.1 / 22.4 | 1,113 / 1,222 | — |
| `task_unrecorded_evidence` | pass | pass | 38.7 / 26.9 | 1,254 / 1,399 | — |
| `validate_clean_checkpoint` | pass | pass | 83.1 / 46.9 | 3,133 / 3,268 | — |
| `validate_failed_verification` | pass | pass | 61.6 / 33.6 | 5,037 / 1,935 | — |
| `validate_stale_verdicts` | pass | pass | 23.0 / 34.0 | 1,730 / 2,120 | — |
| `validate_review_exhausted` | pass | pass | 72.8 / 26.1 | 1,276 / 1,467 | — |
| `specify_exact_serialization` | pass | pass | 47.6 / 56.9 | 3,793 / 3,483 | — |
| `build_existing_contract` | pass | pass | 40.1 / 53.2 | 2,001 / 2,670 | — |
| `deliver_requires_approval` | fail | pass | 69.4 / 43.5 | 2,568 / 2,637 | — |
| `deliver_changed_after_proof` | fail | pass | 47.2 / 28.7 | 2,302 / 2,101 | — |
| `adopt_existing_component` | pass | pass | 59.6 / 35.6 | 2,022 / 1,947 | — |
| `review_enabled_current` | pass | pass | 150.1 / 144.8 | 3,530 / 4,450 | — |
| `review_disabled_no_delegation` | pass | pass | 69.5 / 36.9 | 2,715 / 2,327 | — |
| `review_detects_missing_behavior` | pass | fail | 150.7 / 132.0 | 4,967 / 4,604 | independent_read_evidence |
| `diagrams_enabled_types` | pass | fail | 59.9 / 51.4 | 3,996 / 4,853 | diagrams_shown_after_summary |
| `diagrams_disabled` | pass | pass | 70.4 / 56.4 | 3,349 / 4,823 | — |
| `diagrams_empty_types` | pass | pass | 93.0 / 48.7 | 5,277 / 4,378 | — |
| `diagrams_skipped_design` | pass | pass | 27.7 / 53.2 | 1,979 / 2,972 | — |
| `autopilot_design_transition` | fail | fail | 38.0 / 83.3 | 3,349 / 5,762 | awaits_user; diagram_artifact_and_link; generated_structure; generated_sequence; generated_state; structure_change_markers; autopilot_diagram_reported |
| `autopilot_explicit_stage_stop` | pass | fail | 74.2 / 52.4 | 5,641 / 4,232 | preserves_history |
| `validate_stale_context` | fail | fail | 47.6 / 35.7 | 3,693 / 2,362 | fresh_successful_proof; project_current_behavior |

## Time, usage and controls

| Variant | Selected case seconds including review | Output tokens |
|---|---:|---:|
| baseline | 1635.9 | 72,635 |
| corrected | 1242.3 | 73,450 |

Physical candidate collection took 2037.7 seconds including pacing, with 4 selected fresh role sessions and 4 distinct session IDs. [Reviewer sessions](canonical-reviewer-sessions.json) retain verdicts, actual reads, digest observations, snapshot stability, time and tokens. The fixed native fallback does not forward arbitrary coordinator briefs; the role developer prompts and installed shared contract are the inputs inspected here. Time differences are observations, not isolated prompt-speed effects: service/cache variation, one historical control and concurrent local software checks are confounds.

[Selection](selection.json) preserves every raw attempt and selects the first operationally valid observation irrespective of semantic grade. Only actual external provider/transport/timeout/output-collection failures are excluded and eligible for bounded recovery. No semantic failure is selectively retried. The deliberately unavailable verifier in `validate_failed_verification` is a controlled stimulus, not an external model failure to remove. Any independent finding before an external interruption remains in the raw evidence.

[Software verification](verification.md) retains the initial full-suite asynchronous polling failure and successful isolated rerun; it does not claim an all-green full rerun. Existing focused checks passed 70 tests. No product Python, executable adapter code, test or model predicate changed this iteration. [Archive CRC checks](archive-checks.json), [raw integrity verification](verified-integrity.json), [control manifests](baseline-source-controls.json), [verified raw control rows](baseline-verified-observations.json) and [final frozen-source checks](final-verification.json) support provenance.

The saved-record audit finds full legal prologues in 24/25 cases and authoring pointers in 24/25. [Record observations](record-observations.json) retain journal counts, summary fences, copied diagram blocks and post-proof writes. One cohort cannot establish that historical duplicate-journal risks are solved.

Limits remain: independent prepared stages, not a continuous project; one pure-function Build correction; Deliver before publication; one-component Adopt; native fresh-role fallback rather than installed-plugin discovery. Mermaid is inspected as source, not rendered or syntax-certified. Results do not certify every prompt instruction, host or interaction combination. No own AEGIS workflow, task journal, commit, push, publication or version bump was used.

## Raw collections

- [Core results](../../candidates/2026-10-22-luna-history-evidence-core/results.json), [manifest](../../candidates/2026-10-22-luna-history-evidence-core/manifest.json), [archive](../../candidates/2026-10-22-luna-history-evidence-core/evidence.zip).
- [Capability results](../../candidates/2026-10-22-luna-history-evidence-capabilities/results.json), [manifest](../../candidates/2026-10-22-luna-history-evidence-capabilities/manifest.json), [archive](../../candidates/2026-10-22-luna-history-evidence-capabilities/evidence.zip).
