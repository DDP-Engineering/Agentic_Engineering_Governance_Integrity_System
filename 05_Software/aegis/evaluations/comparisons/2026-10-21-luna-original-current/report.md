<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Original/current AEGIS prompt comparison

The paired baseline selects **25 scenarios per variant** and **8 fresh reviewer sessions**. Both variants use matched per-case evaluator controls, native runtime, cases and settings. AEGIS prompts stayed fixed.

The initial 50 executions are preserved. An adapter rejected a task ID plus brief despite declaring a generic text reference. Internal reference normalization was repaired without changing the model-visible tool schema or instructions (hashes verified). The entire three-case review subgroup was then recollected for both variants and selected symmetrically before inspecting outcomes. Core uses unchanged core.Host; all other capability fixtures have review disabled, so the repaired branch is unreachable there. Their existing observations remain valid. No semantic outcome was selectively retried. See [the selection/provenance rule](selection.json), [transport controls](review-transport-protocol.json) and [the initial unmodified observations](observations.json).

| Configuration | Value |
|---|---|
| Requested model | `gpt-6-luna` |
| Reasoning | `medium` |
| Configured context | 131,072 tokens (128K); client setting, server allocation not independently exposed |
| Native output cap | Unexposed; the 16,000-token MCP output allowance is a tool limit |
| Native CLI | 0.163.0-alpha.11; exact binary hash in manifests |
| Pacing | 30 seconds before every coordinator/reviewer CLI session |
| Returned generic429 policy | 60/120/240-second bounded backoff; no quota/billing or semantic retries |
| Repeats/order | One per case; original core, original capabilities, current core, current capabilities |

Original is master commit `ebdafdbb1e5bbdc5ed86f9ed6dba7673effe9aa1`. Current is the pre-run local payload. Both retain AEGIS 0.14.0 and identical parser bytes. Only `AGENTS.md`, `steps/1_frame.md`, `steps/5_validate.md` and `templates/task.md` differ. All eighteen installed current files match the frozen template.

## Observed automatic scores

| Profile | Original | Current |
|---|---:|---:|
| core | 6/10 | 10/10 |
| capabilities | 6/15 | 7/15 |
| Total | 12/25 | 17/25 |

**These are frozen strict predicates, not a complete quality score.** The [initial semantic review](semantic-review.json) and [selected review-subgroup assessment](review-transport-semantic-review.json) identify actual prompt/record issues, model capability confusion, fixture effects and narrow scoring predicates. Do not count every raw failure as a prompt defect.

Known interpretation limits include `remains pending` not matching the old missing-evidence predicate; an initial harmless unsupported `git ls-tree` being classified as denied during otherwise real independent inspection; the added autopilot transition case requiring waiting/needs_user=yes even when no decision is missing; authorize not matching an approval-keyword predicate; and removes surrounding whitespace not matching strip/trim. Raw grades are preserved rather than silently rewritten.

Concrete current improvements include saved Frame requirement IDs/license prologues, coherent paused resume records and clearing stale approvals without inventing fresh verdicts. Broader observations remain mixed: stale Deliver returns are not persisted, diagram configuration/presentation/change markers are inconsistent, and an autopilot transition leaves a malformed report unrepaired. Adopt contract-versus-implementation wording and Specify atomicity rationale need semantic clarification. Both context files were correctly updated in both variants; their raw failures have different causes, including a wording false negative. See [the bounded next targets](next-targets.md) and [direct feature observations](feature-observations.json).

## Per-scenario observations

Output is the service-reported coordinator plus fresh reviewer output. Case wall time already includes nested reviewers. Model/reasoning/context/output-cap and source-collection fields are repeated in [CSV](canonical-observations.csv) and [JSON](canonical-observations.json).

| Scenario | Original | Current | Wall seconds O/C | Output tokens O/C |
|---|---|---|---:|---:|
| `frame_existing_fix` | fail | pass | 26.9 / 29.9 | 1,836 / 1,906 |
| `frame_ambiguous_retention` | pass | pass | 35.5 / 30.9 | 2,799 / 2,037 |
| `frame_new_interface` | pass | pass | 41.0 / 36.0 | 2,209 / 2,650 |
| `task_stale_handoff` | fail | pass | 34.3 / 25.1 | 1,054 / 1,494 |
| `task_superseded_ruling` | pass | pass | 26.3 / 23.5 | 1,348 / 1,425 |
| `task_unrecorded_evidence` | fail | pass | 23.8 / 25.0 | 1,011 / 1,625 |
| `validate_clean_checkpoint` | pass | pass | 56.0 / 38.5 | 2,441 / 2,100 |
| `validate_failed_verification` | pass | pass | 43.2 / 41.2 | 2,631 / 2,009 |
| `validate_stale_verdicts` | fail | pass | 30.2 / 41.0 | 1,764 / 2,311 |
| `validate_review_exhausted` | pass | pass | 24.4 / 22.6 | 1,054 / 1,603 |
| `specify_exact_serialization` | pass | pass | 58.8 / 52.5 | 4,949 / 3,820 |
| `build_existing_contract` | pass | pass | 38.4 / 41.5 | 2,669 / 1,803 |
| `deliver_requires_approval` | fail | fail | 17.5 / 37.2 | 829 / 2,573 |
| `deliver_changed_after_proof` | fail | fail | 14.6 / 16.7 | 716 / 475 |
| `adopt_existing_component` | pass | pass | 33.7 / 36.9 | 1,631 / 2,075 |
| `review_enabled_current` | fail | pass | 128.3 / 131.0 | 4,429 / 3,693 |
| `review_disabled_no_delegation` | pass | pass | 45.3 / 38.7 | 2,033 / 2,902 |
| `review_detects_missing_behavior` | fail | fail | 119.0 / 126.8 | 3,443 / 3,239 |
| `diagrams_enabled_types` | fail | fail | 39.1 / 59.5 | 3,348 / 5,488 |
| `diagrams_disabled` | fail | pass | 46.9 / 51.3 | 3,828 / 3,328 |
| `diagrams_empty_types` | pass | fail | 45.7 / 56.0 | 4,532 / 4,819 |
| `diagrams_skipped_design` | fail | pass | 17.4 / 28.4 | 772 / 1,631 |
| `autopilot_design_transition` | fail | fail | 57.5 / 60.3 | 3,875 / 4,509 |
| `autopilot_explicit_stage_stop` | pass | fail | 46.6 / 46.7 | 3,763 / 4,076 |
| `validate_stale_context` | fail | fail | 35.8 / 45.4 | 2,028 / 3,051 |

## Time and observed usage

Canonical case totals exclude the initial superseded review subgroup. Physical collection totals include all 56 coordinator executions, 14 fresh reviewer sessions and all pauses.

| Variant | Canonical case seconds including nested review | Canonical output tokens | Physical collection seconds | Physical output tokens | Outer retries |
|---|---:|---:|---:|---:|---:|
| original | 1086.0 | 60,992 | 2297.2 | 70,570 | 0 |
| current | 1142.6 | 66,642 | 2224.1 | 74,610 | 0 |

Reasoning and output are reported as exposed by native usage; no inferred combined token budget is claimed. Time is observational: one repeat, serial order, native caching/service variation and local software-test load during part of the original collection prevent an isolated speed claim. The native service does not expose full per-request pacing or backend model identity.

## Shared contract and preserved records

| Observation | Original | Current |
|---|---:|---:|
| Full installed AGENTS read by coordinator | 25/25 | 25/25 |
| Saved journal license prologue | 19/25 | 25/25 |

Read coverage and actual step paths are recorded per case; reading a file alone is not successful behavioral coverage. All eight step prompts have dedicated behavior cases, and the shared AGENTS contract plus task template participate in the pair. Because four files change together, this collection cannot attribute effects exclusively to one file. [Prompt sizes](prompt-sizes.json) record whitespace-delimited word counts, distinct from model token usage.

## Actual reviewer sessions

Activation is observed independently of the overall scenario grade. Each row is a real fresh native session. Full thread IDs, process IDs, candidate digests, observed reads and actual findings are in [the selected reviewer ledger](canonical-reviewer-sessions.json).

| Variant/case | Role | Verdict | Seconds | Output tokens | Digest reads / snapshot unchanged |
|---|---|---|---:|---:|---|
| original/review_enabled_current | aegis-spec-review | changes_required | 19.7 | 1223 | 2 / True |
| original/review_enabled_current | aegis-quality-review | changes_required | 13.8 | 730 | 1 / True |
| original/review_detects_missing_behavior | aegis-spec-review | changes_required | 17.7 | 1151 | 3 / True |
| original/review_detects_missing_behavior | aegis-quality-review | changes_required | 12.7 | 714 | 1 / True |
| current/review_enabled_current | aegis-spec-review | changes_required | 19.3 | 997 | 2 / True |
| current/review_enabled_current | aegis-quality-review | changes_required | 13.5 | 723 | 2 / True |
| current/review_detects_missing_behavior | aegis-spec-review | changes_required | 18.7 | 745 | 1 / True |
| current/review_detects_missing_behavior | aegis-quality-review | changes_required | 18.8 | 914 | 2 / True |

The same model, medium reasoning and configured 128K apply to every reviewer. Roles use unchanged native adapter instructions and independent immutable snapshots; the second role receives neither the first verdict nor coordinator record edits. This tests the fresh-agent fallback, not installed-plugin discovery. Some extra scope findings concern configuration/knowledge changes introduced during fixture preparation, not model implementation work. Three selected role sessions made only one explicit digest-tool call, despite unchanged snapshot evidence; that protocol-adherence check is separate from activation and functional findings. Both roles returned changes_required in every enabled case, so approved-review continuation and the repair/re-review loop were not observed.

## Scope and evidence limits

- Build covers one existing regression with real red/anchor/edit/green/evolution, while an exact AST guard permits only the original or corrected pure function. It does not evaluate arbitrary coding or new-test authoring.
- Deliver tests pre-publication approval and stale-proof rejection; no commit, push, PR or deployment is attempted.
- Adopt covers one agreed component and an observed contract mismatch; survey and publication are outside this sample.
- Diagrams are checked as saved artifacts, links, types and presentation. Semantic inspection found marker inconsistencies; Mermaid syntax/rendering is not certified.
- Initial Deliver, skipped-Design and disabled-review cases claimed MCP record writes were unavailable because native CLI sandbox metadata is read-only, without attempting the advertised writes. This transport/model confusion must not be attributed to a stage prompt alone.
- The cases are independent prepared stage sessions, rather than a single uninterrupted Frame-to-Deliver project run. Synthetic fixtures, one repeat and one model configuration provide representative observations, not exhaustive AEGIS certification.

## Verification and reproducibility

Software verification is recorded separately after the transport repair; changed Python files compiled. [Verification details](verification.md) include the isolated existing-test repair. All six evidence archives pass CRC checks and every recorded integrity hash was verified. Historical records were removed as requested; no old result was reused as a control.

[Protocol](protocol.json), [payload provenance](provenance.json), [archive checks](all-archive-checks.json), [integrity verification](verified-integrity.json), [installed/template match](installed-template-match.json), [initial semantic review](semantic-review.json), [review-subgroup assessment](review-transport-semantic-review.json), [proposed next targets](next-targets.md).

- [original/core manifest](../../baselines/2026-10-21-luna-original-core/manifest.json), [raw results](../../baselines/2026-10-21-luna-original-core/results.json), [evidence archive](../../baselines/2026-10-21-luna-original-core/evidence.zip)
- [original/capabilities manifest](../../baselines/2026-10-21-luna-original-capabilities/manifest.json), [raw results](../../baselines/2026-10-21-luna-original-capabilities/results.json), [evidence archive](../../baselines/2026-10-21-luna-original-capabilities/evidence.zip)
- [original/review-transport manifest](../../baselines/2026-10-21-luna-original-review-transport/manifest.json), [raw results](../../baselines/2026-10-21-luna-original-review-transport/results.json), [evidence archive](../../baselines/2026-10-21-luna-original-review-transport/evidence.zip)
- [current/core manifest](../../candidates/2026-10-21-luna-current-core/manifest.json), [raw results](../../candidates/2026-10-21-luna-current-core/results.json), [evidence archive](../../candidates/2026-10-21-luna-current-core/evidence.zip)
- [current/capabilities manifest](../../candidates/2026-10-21-luna-current-capabilities/manifest.json), [raw results](../../candidates/2026-10-21-luna-current-capabilities/results.json), [evidence archive](../../candidates/2026-10-21-luna-current-capabilities/evidence.zip)
- [current/review-transport manifest](../../candidates/2026-10-21-luna-current-review-transport/manifest.json), [raw results](../../candidates/2026-10-21-luna-current-review-transport/results.json), [evidence archive](../../candidates/2026-10-21-luna-current-review-transport/evidence.zip)
