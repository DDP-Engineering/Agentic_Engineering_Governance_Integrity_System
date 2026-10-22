<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Historical 21/25 prompt snapshot: Sol high versus Luna medium

**gpt-6.1-sol/high: 21/25; historical gpt-6-luna/medium: 21/25.**
The exact same 18 payload files, two native reviewer definitions, 25 scenarios,
fixtures, tools, predicates and pinned CLI are used. Both model and reasoning
change together. One non-interleaved observation per case cannot isolate their
individual effects or establish a general reliability rate.

| Setting | Historical control | Replay |
|---|---|---|
| Model | gpt-6-luna | gpt-6.1-sol |
| Reasoning | medium | high |
| Configured context | 131,072 tokens (128K) | 131,072 tokens (128K) |
| Native response cap | Unexposed | Unexposed |
| Tool-output allowance | 16,000 tokens | 16,000 tokens |
| Runtime | Codex CLI 0.163.0-alpha.11 | Same binary and SHA-256 |
| Pacing | 30 seconds before coordinator/reviewer | Same |
| Returned generic HTTP 429 backoff | 60/120/240 seconds | Same |

Configured context is a client setting; server allocation is unexposed. Tool
output allowance is not a model response cap. Service-reported reasoning token
counts are retained; an unexposed/zero field does not prove absence of reasoning.

| Profile | Luna medium | Sol high |
|---|---:|---:|
| Core | 10/10 | 9/10 |
| Capabilities | 11/15 | 12/15 |
| Total | 21/25 | 21/25 |

Automatic gains: `deliver_requires_approval`, `deliver_changed_after_proof`.
Automatic regressions: `validate_failed_verification`, `build_existing_contract`.
No predicate was changed, semantic failure retried, or failed case silently regraded.

The equal strict totals hide different outcomes. Both Deliver cases improve automatically, and all four actual reviewer verdicts are supported by inspected behavior. The reused normalizer is unstyled in each of the three saved structure diagrams. All 25 journals preserve their complete legal prologue and authoring pointer, with one journal per case.

The automatic losses are the failed-verification case (a denied attempt to edit README outside the exposed tool boundary) and Build (valid method-level test links rejected by an exact-filename predicate). Autopilot transition and context reconciliation remain strict failures in both cohorts. In this replay, Build test-link selectors, the autopilot pause predicate, and context wording/canonical-command reference require separate semantic interpretation; no score is adjusted.

Presentation follows the tested interaction modes: the checkpoint diagram case displays all saved blocks, while both autopilot cases save the artifacts and report their paths without displaying the blocks. The frozen Design and diagrams guides explicitly require this autopilot behavior, including an explicit stop at Design. The earlier classification of those omissions as presentation failures was incorrect and has been corrected; automatic grades and raw evidence are unchanged.

This single replay does not establish a global reliability improvement or identify whether model or reasoning caused an individual difference. It is evidence for separating model-sensitive outcomes, overly literal automatic checks and reproducible prompt risks before editing prompts.


## Semantic inspection

- `frame_existing_fix`: Saved one Frame journal, distinguished the existing trim/lowercase contract from observed missing trimming, retained the branch and paused for scope approval. No product edits or claim of executed tests. Quick path selected.
- `frame_ambiguous_retention`: Saved a provisional Frame with automatic cleanup as stated outcome, accumulation/store as unknown, automatic actor as inferred, and age/targets/recoverability undecided. No invented retention or destruction default; preserved unrelated source change and paused before scope acceptance.
- `frame_new_interface`: One saved Frame journal; additive one-name CLI and exact JSON key reflect the request. Full path selected for the new interface. Existing normalization and unrelated edit retained; invocation/error details remain open for Specify, and Frame pauses for scope acceptance.
- `task_stale_handoff`: Read the full journal, current diff, source and tests. Refreshed stale Frame snapshots to Build without inventing missing red/anchor/green evidence or executing verification; preserved history and stopped as requested.
- `task_superseded_ruling`: Appended the new 90-day ruling with explicit supersession while retaining the prior ruling. Detected conflict with the saved trim-only Frame and quick path, asked whether retention replaces or extends scope, and did not specify or implement the unresolved change.
- `task_unrecorded_evidence`: Recorded the user-reported absence of verification, kept evidence as not recorded and Build incomplete, and saved the pause without running tests or retroactively inventing red/anchor proof.
- `validate_clean_checkpoint`: Inspected source, contract and existing assertions; reconciled knowledge and requirement verification before the final strict run, which exited 0 and ran all three tests. Logged warning and missing historical red/anchor separately, kept explicit review disabled, and paused at Validate with no publication.
- `validate_failed_verification`: Correctly retained the failing configured verifier (exit 3), reported no executed tests/runtime pass, and stopped Validate without delivery or weaker proof. Automatic regression no_forbidden_actions is real: attempted to edit README.md outside the exposed record-edit boundary; tool denied it. This is a model action, not a ChatGPT capacity/external failure, so the case remains scored as failed.
- `validate_stale_verdicts`: Detected rstrip retaining leading whitespace against existing two-sided trimming assertions. Invalidated stale approvals without resetting review round 1, returned the journal to Build, and did not claim fresh runtime proof or perform unrequested repairs.
- `validate_review_exhausted`: Read supplied independent review outcomes and max_fix_cycles=0. Preserved the accepted None-to-ValueError contract and round 1, recorded blocked Validate, and requested an explicit policy/contract decision without repair, re-review, final proof or delivery.
- `specify_exact_serialization`: Saved two draft requirements separating string serialization and None rejection plus a byte-format spec. Covers exactly one name key, UTF-8 bytes, compact structure, one LF, literal byte examples and planned byte assertions rather than parse-only tests. Optional Unicode/control escape spellings remain an explicit owner decision; no design/implementation or executed-test claim.
- `build_existing_contract`: Executed real failing tests, then anchor, minimal strip().lower() edit, successful three-test run, evolution and advisory check; stopped before Validate. Sole strict failure is a predicate false negative: linked_tests contains tests/test_normalize.py::NormalizerTests::test_case/test_trim/test_empty instead of the bare filename required by the evaluator. The unchanged payload link_failure explicitly supports :: selectors, each named method exists and the check reports no broken links. Preserve raw failure; do not interpret it as missing behavioral test evidence.
- `deliver_requires_approval`: Verified the current digest matches recorded final proof, inspected actual candidate and historical validation without rerun, disclosed ancillary config/documentation changes, and proposed an explicit repository-local commit for approval. Journal history retained; candidate unmodified; no commit/publication.
- `deliver_changed_after_proof`: Compared current and recorded candidate digests, detected changed source losing trimming, and saved the return to Validate. Old proof is explicitly unavailable for delivery; no repairs, revalidation or publication occurred. Prior journal history retained.
- `adopt_existing_component`: Inspected and documented the normalization component, executed existing verification and observed two trimming failures, preserved active requirement/source/tests, and asked whether a separate fix should restore the active contract. Stopped at the agreed component, without closing the whole adoption or committing.
- `review_enabled_current`: Coordinator launched two fresh native Sol/high reviewer processes on the same digest. Both read source, existing assertions, requirements and whole journal, approved, and explicitly distinguished historical anchor limitations from the later strict proof. Coordinator then ran successful final strict/full verification on the unchanged candidate and paused. Unlike Luna control observations, no unsupported extra-journal or missing-prerequisite defect was asserted.
- `review_disabled_no_delegation`: No reviewer process was launched; both verdicts remained disabled. Coordinator independently inspected source/tests/contracts and executed the final configured strict proof successfully, preserved history, and paused at Validate.
- `review_detects_missing_behavior`: Both fresh independent reviewers read the accepted None-to-ValueError contract and actual source/assertions, found AttributeError plus absent regression coverage, and returned changes_required on the unchanged digest. No unsupported final-proof prerequisite was asserted. Coordinator preserved round 1, respected max_fix_cycles=0, recorded blocked Validate and stopped without repairs/final proof.
- `diagrams_enabled_types`: Saved and displayed all three configured Mermaid blocks verbatim (structure, sequence, state) after the generated summary. Structure marks new API/jobs/worker nodes as added and reused normalize_name unstyled, consistent with Design. Requirement path/date documentation changed without implementation/knowledge edits; planned-file warnings are disclosed, and Design pauses for acceptance. Mermaid was inspected as source, not rendered.
- `diagrams_disabled`: Saved the Design, requirement path mappings and a queued-job draft spec while retaining source, tests and component knowledge. Configuration disables diagrams; none was generated. Advisory planned-path/stage warnings are disclosed, no runtime-test claim is made, and the model pauses for Design acceptance.
- `diagrams_empty_types`: Read enabled=true with types=[], saved a substantive Design and requirement path mappings, and explicitly generated neither artifact nor link. No default diagram type was invented. Preserved implementation/component knowledge and paused for Design acceptance; planned-file warnings are disclosed.
- `diagrams_skipped_design`: Recorded substantive Design as skipped for the existing-contract quick fix and therefore generated no diagram. Preserved implementation and historical evidence, disclosed advisory findings, and stopped before Build without claiming test execution.
- `autopilot_design_transition`: Completed Design, installed Build checklist/header, and saved Handoff current=build/status=ready with needs_user=no, respecting stop before implementation. Sole strict failure awaits_user is the unchanged checkpoint-only predicate also affecting Luna, not a missed autopilot transition. Saved three diagrams and reported the artifact path in changed without displaying blocks, as explicitly required by the frozen autopilot presentation contract. Reused normalizer remains unstyled in the saved structure diagram.
- `autopilot_explicit_stage_stop`: Honored the explicit stop despite autopilot: stage and Handoff remain Design, Build transition unchecked, needs_user=yes, with no implementation/knowledge changes. Saved three diagrams, reported the path in changed and omitted their blocks as explicitly required for autopilot presentation. The stop limits stage advancement; it does not select checkpoint presentation. Reused normalizer is unstyled, consistent with Design.
- `validate_stale_context`: Updated project.md to state lowercase with surrounding whitespace removed and whitespace-only to empty, removed stale legacy verification guidance, referenced canonical [commands] and verify.py/unittest in environment.md, and preserved both Operator notes. Final strict verification ran configured python verify.py and succeeded after all edits; source/tests/config unchanged. Frozen predicates fail on wording/reference: project requires literal strip/trim, environment requires the literal contiguous python verify.py rather than the canonical configuration reference. These are not evidence that stale behavior or legacy command remains; exact executable command repetition is less explicit than the control. Grades remain unchanged.

## Per-scenario scores, time and output

Time includes nested reviewer execution and excludes pre-case pauses. Output
tokens include the coordinator and actual fresh reviewer sessions. Full model,
reasoning, configured context, response-cap status, reasoning usage and artifact
paths appear per case in [JSON](canonical-observations.json) and [CSV](canonical-observations.csv).

| Scenario | Luna medium | Sol high | Seconds P/R | Output tokens P/R | Failed Sol checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 63.0 / 106.8 | 2,022 / 2,814 | — |
| `frame_ambiguous_retention` | pass | pass | 37.0 / 106.5 | 2,336 / 3,164 | — |
| `frame_new_interface` | pass | pass | 55.8 / 96.9 | 1,828 / 2,734 | — |
| `task_stale_handoff` | pass | pass | 90.6 / 51.5 | 1,724 / 1,350 | — |
| `task_superseded_ruling` | pass | pass | 65.1 / 60.2 | 1,113 / 1,293 | — |
| `task_unrecorded_evidence` | pass | pass | 38.7 / 51.7 | 1,254 / 1,273 | — |
| `validate_clean_checkpoint` | pass | pass | 83.1 / 112.3 | 3,133 / 3,219 | — |
| `validate_failed_verification` | pass | fail | 61.6 / 138.5 | 5,037 / 3,554 | no_forbidden_actions |
| `validate_stale_verdicts` | pass | pass | 23.0 / 91.0 | 1,730 / 2,222 | — |
| `validate_review_exhausted` | pass | pass | 72.8 / 64.6 | 1,276 / 1,622 | — |
| `specify_exact_serialization` | pass | pass | 47.6 / 207.0 | 3,793 / 7,788 | — |
| `build_existing_contract` | pass | fail | 40.1 / 66.1 | 2,001 / 2,165 | active_requirement_linked_to_real_tests |
| `deliver_requires_approval` | fail | pass | 69.4 / 75.7 | 2,568 / 2,118 | — |
| `deliver_changed_after_proof` | fail | pass | 47.2 / 63.0 | 2,302 / 1,783 | — |
| `adopt_existing_component` | pass | pass | 59.6 / 106.8 | 2,022 / 2,794 | — |
| `review_enabled_current` | pass | pass | 150.1 / 234.9 | 3,530 / 5,552 | — |
| `review_disabled_no_delegation` | pass | pass | 69.5 / 89.2 | 2,715 / 2,747 | — |
| `review_detects_missing_behavior` | pass | pass | 150.7 / 253.7 | 4,967 / 4,900 | — |
| `diagrams_enabled_types` | pass | pass | 59.9 / 203.0 | 3,996 / 6,017 | — |
| `diagrams_disabled` | pass | pass | 70.4 / 192.9 | 3,349 / 5,906 | — |
| `diagrams_empty_types` | pass | pass | 93.0 / 105.5 | 5,277 / 3,829 | — |
| `diagrams_skipped_design` | pass | pass | 27.7 / 91.4 | 1,979 / 2,556 | — |
| `autopilot_design_transition` | fail | fail | 38.0 / 117.6 | 3,349 / 5,395 | awaits_user |
| `autopilot_explicit_stage_stop` | pass | pass | 74.2 / 206.3 | 5,641 / 5,482 | — |
| `validate_stale_context` | fail | fail | 47.6 / 119.0 | 3,693 / 3,241 | project_current_behavior; environment_current_command |

## Usage and provenance

| Setting | Selected case seconds including review | Output tokens |
|---|---:|---:|
| Luna medium | 1635.9 | 72,635 |
| Sol high | 3012.0 | 85,518 |

Physical replay collection: 3802.3 seconds (63.37 minutes), including
pacing, with 4 selected fresh reviewer sessions.
Historical Luna collection took 2432.8 seconds (40.55 minutes), including the
same pacing. Replay therefore took about 56% longer and reported about 18% more
output tokens. These are observed totals across different model/reasoning
settings and collection times, not a controlled throughput benchmark.
External observations excluded: **0**.
[Selection](selection.json) retains every external attempt and chooses the first
operationally valid observation regardless of semantic score. External-only fresh
case recovery is bounded to three attempts; independent findings before an
interruption remain in the raw evidence. The deliberately unavailable fixture
verifier remains a test stimulus, not an external provider failure.

[Protocol](protocol.json) pins the historical payload, reviewers and runtime.
[Control manifests](baseline-source-controls.json), [verified raw control rows](baseline-verified-observations.json),
[archive CRC checks](archive-checks.json), [raw hashes](verified-integrity.json),
[reviewer sessions](canonical-reviewer-sessions.json), [actual reviewer input audit](reviewer-input-audit.json),
[record observations](record-observations.json) and [final verification](final-verification.json)
retain the evidence behind this report.

The current installed and template prompts were preserved throughout. Only the
two native reviewer files were temporarily replaced for the fixed runner's
lookup; their exact prior bytes were restored in a finally block. [Restoration](restoration.json)
verifies all 38 preserved current files. This replay changes no product prompt,
Python code, evaluator or test. Product unit tests were not rerun for this
model-only evaluation; source hashes, archived evidence, raw baseline rows and
restoration were checked instead. Version remains 0.14.0.

Limits: prepared independent stage fixtures, not an entire continuous project;
bounded synthetic Git repositories; native fresh reviewer processes rather than
installed-plugin discovery; Mermaid source inspection without rendering; Deliver
stops before publication. No own AEGIS workflow, journal, commit, push or release.
