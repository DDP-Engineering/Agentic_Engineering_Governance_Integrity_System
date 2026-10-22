<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Deliver, diagram display and evidence interpretation: Luna comparison

**The revised prompts score 21/25 against the preceding valid cohort at 18/25.** This is one observed comparison, not an established reliability rate. Functional delivery recording improves even though both Deliver cases remain strict failures. Review evidence interpretation and diagram semantics still need work.

| Setting | Value |
|---|---|
| Requested model | `gpt-6-luna` |
| Reasoning | `medium` |
| Configured context | 131,072 tokens (128K); client setting, server allocation unexposed |
| Native response cap | Unexposed; 16,000 is the MCP tool-output allowance |
| CLI/runtime | Same pinned 0.163.0-alpha.11 binary and hash |
| Pacing / returned generic 429 backoff | 30 seconds before each coordinator/reviewer; 60/120/240 seconds |
| Cohort | 25 unchanged independent scenarios; one valid observation each |
| External errors | 0 excluded observations |
| Payload version | 0.14.0; no release or version bump |

The control is the selected **corrected** 18/25 cohort in the [preceding report](../2026-10-22-luna-validation-records/report.md), including its first valid external-capacity recovery. It is not the original-master or earlier 17/25 control. The five changed prompt files are identified in [the correction map](changes.md), [exact diff](prompt-changes.diff), [word counts](prompt-sizes.json) and [protocol/hashes](protocol.json). Frame, Specify, Build, Adopt, task template, parser, scenarios, fixture, scorer and native role definitions are unchanged from that control. Installed/template/frozen payloads match.

| Profile | Previous | Revised |
|---|---:|---:|
| Core | 10/10 | 10/10 |
| Capabilities | 8/15 | 11/15 |
| Total | 18/25 | 21/25 |

Automatic fail-to-pass changes: `review_detects_missing_behavior`, `diagrams_enabled_types`, `diagrams_disabled`. Automatic pass-to-fail changes: none. Strict grades are preserved, including known narrow predicates. Read the [25-case semantic assessment](semantic-review.json) alongside the score.

## What the observations establish

- **Delivery identity and durable records improve.** Matching current/validated bindings are now recognized; a base diff is not mislabeled a post-proof change. Normal delivery saves its approval pause. The stale candidate saves header, full Validate checklist, Handoff and Stage report before summary, with no repair, revalidation or publication.
- **Delivery history is still not exact append-only.** Both cases remove one space from the same old fixture-evidence line while appending an outcome. This is a real strict failure of history preservation, without observed loss of its factual content. It is not an external error and was not retried. Some Deliver summaries also omit the required text fence. Normal Deliver still proposes including unrelated fixture-provided changes; their introduction is not attributable to the coordinator.
- **Checkpoint display improves.** All three saved Mermaid blocks are copied verbatim after the actual summary and before Design choices. The enabled case passes. Its normalizer node is nevertheless marked changed while Design calls it unchanged, a semantic regression not detected by this scorer. A Stage introduction still precedes the summary.
- **Current evidence is read more successfully in the missing-behavior case.** Both fresh roles read accepted untracked scope/current source/tests, identify AttributeError instead of required ValueError, and the coordinator saves the exhausted-policy blocker without repairs or final proof. Disabled-diagram Design now discovers the real component page and preserves the existing normalizer contract while proposing an additional queued interface.
- **Evidence interpretation is not generally solved.** In the ordinary enabled-review case, Spec compares base to HEAD and demands final proof before approval; Quality invents a second journal filename and treats the available journal as incomplete. Both sessions read the complete shared contract; [all four role reads are recorded](reviewer-contract-reads.json). The activation score passes, but does not certify verdict quality. All-approved review/fix-loop behavior remains unestablished.
- **Specify leaves the unstated escaping policy open** instead of inventing it, unlike the previous observation. Specify itself did not change, so individual-file causality is not established. Adopt still carries investigation/task history into current-state component knowledge. Some responses omit summary fences or a full boundary-choice menu.

The bounded autopilot transition retains the previous `awaits_user` failure: the candidate explicitly permits ready/completed/no at this requested transition-only stop, while the frozen predicate expects a pause. This declared contract interpretation remains visible and un-regraded. Context reconciliation must be read beside its narrow keyword predicate; see the actual assessment for this observation.

## External conditions and selection

The [predeclared protocol](protocol.json) excludes externally failed coordinator/reviewer runs from prompt scoring. [Selection](selection.json) uses the first operationally complete observation regardless of semantic grade, with bounded external-only recovery and every raw attempt retained. No semantic failure is selectively retried. A semantic tool misuse or invented evidence claim remains a prompt/model observation.

The unavailable verifier in `validate_failed_verification` is an intentional fixture condition that tests honest reporting; it is not a real service interruption to exclude. Coordinator/reviewer provider, transport and timeout failures are classified separately. The preceding control's capacity exclusion is preserved. A single current journal does not establish that the earlier independently observed duplicate-journal risk is solved.

## Per-scenario results

Times include nested review but exclude the pre-case pause. Output includes coordinator and reviewer tokens. Model, reasoning, configured context, native output-cap status, service-reported reasoning tokens and artifact source are repeated in [canonical JSON](canonical-observations.json) and [CSV](canonical-observations.csv). Cumulative input usage spans turns and does not measure peak context. Missing service reasoning counts are not evidence of zero reasoning.

| Scenario | Previous | Revised | Seconds P/R | Output tokens P/R | Failed revised checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 75.1 / 63.0 | 2,613 / 2,022 | — |
| `frame_ambiguous_retention` | pass | pass | 29.4 / 37.0 | 2,601 / 2,336 | — |
| `frame_new_interface` | pass | pass | 113.3 / 55.8 | 2,253 / 1,828 | — |
| `task_stale_handoff` | pass | pass | 25.0 / 90.6 | 1,381 / 1,724 | — |
| `task_superseded_ruling` | pass | pass | 50.8 / 65.1 | 1,048 / 1,113 | — |
| `task_unrecorded_evidence` | pass | pass | 25.0 / 38.7 | 1,366 / 1,254 | — |
| `validate_clean_checkpoint` | pass | pass | 42.8 / 83.1 | 2,644 / 3,133 | — |
| `validate_failed_verification` | pass | pass | 41.4 / 61.6 | 2,466 / 5,037 | — |
| `validate_stale_verdicts` | pass | pass | 84.9 / 23.0 | 2,241 / 1,730 | — |
| `validate_review_exhausted` | pass | pass | 41.6 / 72.8 | 2,035 / 1,276 | — |
| `specify_exact_serialization` | pass | pass | 70.0 / 47.6 | 3,754 / 3,793 | — |
| `build_existing_contract` | pass | pass | 84.1 / 40.1 | 1,716 / 2,001 | — |
| `deliver_requires_approval` | fail | fail | 35.4 / 69.4 | 1,117 / 2,568 | preserves_history |
| `deliver_changed_after_proof` | fail | fail | 35.8 / 47.2 | 399 / 2,302 | preserves_history |
| `adopt_existing_component` | pass | pass | 79.4 / 59.6 | 1,982 / 2,022 | — |
| `review_enabled_current` | pass | pass | 196.9 / 150.1 | 5,522 / 3,530 | — |
| `review_disabled_no_delegation` | pass | pass | 37.3 / 69.5 | 2,807 / 2,715 | — |
| `review_detects_missing_behavior` | fail | pass | 193.0 / 150.7 | 4,282 / 4,967 | — |
| `diagrams_enabled_types` | fail | pass | 63.7 / 59.9 | 6,717 / 3,996 | — |
| `diagrams_disabled` | fail | pass | 36.8 / 70.4 | 714 / 3,349 | — |
| `diagrams_empty_types` | pass | pass | 70.4 / 93.0 | 2,979 / 5,277 | — |
| `diagrams_skipped_design` | pass | pass | 43.2 / 27.7 | 2,951 / 1,979 | — |
| `autopilot_design_transition` | fail | fail | 67.3 / 38.0 | 5,554 / 3,349 | awaits_user |
| `autopilot_explicit_stage_stop` | pass | pass | 43.2 / 74.2 | 3,390 / 5,641 | — |
| `validate_stale_context` | fail | fail | 45.4 / 47.6 | 3,972 / 3,693 | project_current_behavior |

## Usage, time and verification

| Variant | Selected case seconds, including review | Output tokens |
|---|---:|---:|
| baseline | 1631.4 | 68,504 |
| corrected | 1635.9 | 72,635 |

The physical candidate collection took 2432.8 seconds including pacing. The canonical candidate has 4 completed fresh role sessions, with 4 distinct session IDs. [Reviewer records](canonical-reviewer-sessions.json) retain actual reads, before/after candidate observations, immutable-snapshot checks, findings, timing and tokens. The controlled native fallback does not forward arbitrary coordinator briefs to reviewers; shared installed instructions are observed, but brief-forwarding behavior is not tested.

Time is observational. One historical matched control, native service/cache variation and the concurrent early software test run do not support an isolated prompt-speed claim. The coupled prompt edits and one sample do not isolate individual-file effects or show statistical reliability.

Offline validation: **551 passed, 2 skipped**; focused structural guards **58 passed**; changed Python guard compiled; CLI help and diff checks succeed. [Verification](verification.md) records the initial literal guard mismatch and successful rerun; the model scorer remained unchanged. [Integrity checks](verified-integrity.json), [archive CRC checks](archive-checks.json), [source controls](baseline-source-controls.json), [verified raw control rows](baseline-verified-observations.json) and [final payload checks](final-verification.json) support provenance.

The actual saved record audit finds full license prologues in 25/25 cases and the authoring pointer in 25/25. [Record observations](record-observations.json) retain journal counts, summary fences, diagram-copy checks and post-proof write ordering. Literal legal/header preservation is distinct from the Deliver log-whitespace failures.

Coverage remains bounded: independent prepared stages rather than one continuous project; one pure-function Build correction; pre-publication Deliver; one-component Adopt; actual fresh-role fallback rather than native installed-plugin discovery. Mermaid source is inspected as text; rendering and syntax certification are not exercised. No own AEGIS workflow, commit, push, publication or release was performed. This prompt batch remains experimental.

## Preserved raw collections

- [Core results](../../candidates/2026-10-22-luna-delivery-evidence-core/results.json), [manifest](../../candidates/2026-10-22-luna-delivery-evidence-core/manifest.json), [evidence archive](../../candidates/2026-10-22-luna-delivery-evidence-core/evidence.zip).
- [Capability results](../../candidates/2026-10-22-luna-delivery-evidence-capabilities/results.json), [manifest](../../candidates/2026-10-22-luna-delivery-evidence-capabilities/manifest.json), [evidence archive](../../candidates/2026-10-22-luna-delivery-evidence-capabilities/evidence.zip).
