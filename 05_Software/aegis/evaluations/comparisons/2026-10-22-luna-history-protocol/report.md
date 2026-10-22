<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Delivery history, reviewer evidence and diagram markers

**Revised: 19/25; preceding valid control: 21/25.** One historical matched cohort does not establish a general reliability rate. Strict scores and semantic findings are reported separately. This is not a demonstrated global improvement; the tested local candidate is not recommended for integration in its current form.

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

The control is the selected **corrected** cohort from [the preceding 21/25 report](../2026-10-22-luna-delivery-evidence/report.md). The scenario JSON, fixtures, tools, scorer, adapter bridge code and native runtime remain fixed. Five payload guides and the **two exercised native reviewer prompts** intentionally change in this experiment. The role prompts are experimental inputs, not evaluator logic. Ten host reviewer source copies are synchronized, but only the Codex pair receives live observations. [Protocol and hashes](protocol.json), [correction map](changes.md), [exact diff](prompt-changes.diff), [prompt sizes](prompt-sizes.json) and `reviewer-prompts/control/` / `reviewer-prompts/candidate/` retain their provenance. Installed/template/frozen payloads match.

| Profile | Control | Revised |
|---|---:|---:|
| Core | 10/10 | 10/10 |
| Capabilities | 11/15 | 9/15 |
| Total | 21/25 | 19/25 |

Automatic gains: `deliver_requires_approval`, `deliver_changed_after_proof`. Automatic regressions: `build_existing_contract`, `review_disabled_no_delegation`, `diagrams_enabled_types`, `diagrams_empty_types`. No predicates are changed or failed cases silently regraded.

## Assessment: targeted gains, no demonstrated overall improvement

**Do not integrate this batch as a demonstrated global upgrade.** The strict
score is 19/25 against the 21/25 control; confirmed regressions remain. The
first complete candidate scored 20/25 and is preserved in
[its report](../2026-10-22-luna-history-evidence/report.md). The follow-up is one
bounded whole-cohort correction, not selective reruns of failed cases.

| Whole snapshot | Core | Capabilities | Total |
|---|---:|---:|---:|
| Previous control | 10/10 | 11/15 | 21/25 |
| First candidate | 10/10 | 10/15 | 20/25 |
| Final candidate | 10/10 | 9/15 | 19/25 |

Targeted improvements are observed:

- Both Deliver cases pass, including exact historical Log preservation,
  matching versus mismatching candidate identity and durable approval/return
  records. They pass in both new complete cohorts.
- Reviewer evidence interpretation improves: current untracked scope and
  actual assertions/runs are read, pending final proof is not demanded before
  approvals, and missing accepted None/ValueError behavior is independently
  identified. Final roles make dedicated candidate calls before and after
  the entire inspection. The ordinary case now observes two genuine approvals
  followed by actual final strict proof. This is one bounded happy path, not
  evidence of a full correction/re-review loop.
- Reused normalizer nodes are unstyled in the three saved final diagram files,
  matching their explicit node maps and Design. Node classification does not
  certify every edge: some new connections still use unchanged-edge notation.

Four automatic pass-to-fail changes offset the two Deliver gains:

- Build performs actual red/edit/green but omits anchor, then falsely calls
  the available operation unavailable. Evolution fails because the anchor
  was never recorded. This is a model execution/evidence error, not an
  external condition.
- Disabled review correctly launches no roles and runs full proof, but places
  its Log outcome below the Rulings heading, creating an invalid ruling.
- Enabled diagrams are saved with corrected node classes, but their Mermaid
  blocks are again omitted from the checkpoint response.
- Empty diagram types are respected, but read_file is used on the src
  directory. Windows returns EACCES/PermissionError, which the frozen host
  classifies as denied. The strict no_forbidden_actions failure is retained;
  it is incorrect tool use and a platform-sensitive proxy, not a prohibited
  write or a diagram-gate violation. No adjusted score is substituted.

The pre-existing bounded-autopilot awaits_user convention difference and the
context trim/strip keyword predicate remain raw failures. Context correctly
removes surrounding whitespace and lowercases, preserves operator notes and
uses the configured unittest route; final proof actually runs after the edits.
The first candidate's real missing-autopilot-diagrams and skipped-context-proof
regressions are repaired in the final candidate. Its explicit Design stop also
preserves the full Log again. These improvements within previously failing
cases do not create extra strict passes against the original control.

The license notice is not removed, but three final journals add the word
file to the license-reference line. Only 22/25 complete prologues are verbatim;
see [the exact text audit](legal-prologue-audit.json). All 25 authoring pointers
remain. Summary fences and full choice menus are also inconsistent.

One observation per snapshot, coupled prompt changes and model variability do
not isolate causality or establish a reliability rate. Build's own step bytes
are unchanged, while shared Task guidance changes. Both semantic gains and
regressions must remain visible. The frozen evaluator and the eight non-role
sources were not changed to improve a score. The tested final payload remains
an experimental local candidate, with no commit/publication or version bump.


## Per-scenario comparison

Wall time includes nested review and excludes the pre-case pause. Output includes coordinator and fresh reviewer tokens. Model, reasoning, configured context, output-cap status, service-reported reasoning tokens and source artifacts are repeated in [canonical JSON](canonical-observations.json) and [CSV](canonical-observations.csv). Cumulative input usage spans turns, not peak context occupancy; an unexposed reasoning count is not proven zero reasoning.

| Scenario | Previous | Revised | Seconds P/R | Output tokens P/R | Failed revised checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 63.0 / 49.4 | 2,022 / 3,699 | — |
| `frame_ambiguous_retention` | pass | pass | 37.0 / 44.0 | 2,336 / 2,462 | — |
| `frame_new_interface` | pass | pass | 55.8 / 24.2 | 1,828 / 1,671 | — |
| `task_stale_handoff` | pass | pass | 90.6 / 24.2 | 1,724 / 1,363 | — |
| `task_superseded_ruling` | pass | pass | 65.1 / 19.6 | 1,113 / 1,083 | — |
| `task_unrecorded_evidence` | pass | pass | 38.7 / 32.9 | 1,254 / 1,416 | — |
| `validate_clean_checkpoint` | pass | pass | 83.1 / 50.1 | 3,133 / 3,067 | — |
| `validate_failed_verification` | pass | pass | 61.6 / 54.4 | 5,037 / 4,045 | — |
| `validate_stale_verdicts` | pass | pass | 23.0 / 29.4 | 1,730 / 2,157 | — |
| `validate_review_exhausted` | pass | pass | 72.8 / 36.7 | 1,276 / 1,992 | — |
| `specify_exact_serialization` | pass | pass | 47.6 / 64.4 | 3,793 / 4,074 | — |
| `build_existing_contract` | pass | fail | 40.1 / 43.0 | 2,001 / 2,452 | actual_red_anchor_edit_green_evolution |
| `deliver_requires_approval` | fail | pass | 69.4 / 23.9 | 2,568 / 1,505 | — |
| `deliver_changed_after_proof` | fail | pass | 47.2 / 58.4 | 2,302 / 2,571 | — |
| `adopt_existing_component` | pass | pass | 59.6 / 29.1 | 2,022 / 1,945 | — |
| `review_enabled_current` | pass | pass | 150.1 / 136.4 | 3,530 / 4,315 | — |
| `review_disabled_no_delegation` | pass | fail | 69.5 / 35.5 | 2,715 / 1,831 | parseable_records |
| `review_detects_missing_behavior` | pass | pass | 150.7 / 167.2 | 4,967 / 5,121 | — |
| `diagrams_enabled_types` | pass | fail | 59.9 / 105.8 | 3,996 / 4,259 | diagrams_shown_after_summary |
| `diagrams_disabled` | pass | pass | 70.4 / 69.6 | 3,349 / 3,996 | — |
| `diagrams_empty_types` | pass | fail | 93.0 / 104.1 | 5,277 / 4,616 | no_forbidden_actions |
| `diagrams_skipped_design` | pass | pass | 27.7 / 69.6 | 1,979 / 3,820 | — |
| `autopilot_design_transition` | fail | fail | 38.0 / 92.5 | 3,349 / 4,962 | awaits_user |
| `autopilot_explicit_stage_stop` | pass | pass | 74.2 / 41.5 | 5,641 / 3,362 | — |
| `validate_stale_context` | fail | fail | 47.6 / 50.5 | 3,693 / 3,042 | project_current_behavior |

## Time, usage and controls

| Variant | Selected case seconds including review | Output tokens |
|---|---:|---:|
| baseline | 1635.9 | 72,635 |
| corrected | 1456.5 | 74,826 |

Physical candidate collection took 2246.1 seconds including pacing, with 4 selected fresh role sessions and 4 distinct session IDs. [Reviewer sessions](canonical-reviewer-sessions.json) retain verdicts, actual reads, digest observations, snapshot stability, time and tokens. The fixed native fallback does not forward arbitrary coordinator briefs; the role developer prompts and installed shared contract are the inputs inspected here. Time differences are observations, not isolated prompt-speed effects: service/cache variation, one historical control and concurrent local software checks are confounds.

[Selection](selection.json) preserves every raw attempt and selects the first operationally valid observation irrespective of semantic grade. Only actual external provider/transport/timeout/output-collection failures are excluded and eligible for bounded recovery. No semantic failure is selectively retried. The deliberately unavailable verifier in `validate_failed_verification` is a controlled stimulus, not an external model failure to remove. Any independent finding before an external interruption remains in the raw evidence.

[Software verification](verification.md) retains the initial full-suite asynchronous polling failure and successful isolated rerun; it does not claim an all-green full rerun. Existing focused checks passed 70 tests. No product Python, executable adapter code, test or model predicate changed this iteration. [Archive CRC checks](archive-checks.json), [raw integrity verification](verified-integrity.json), [control manifests](baseline-source-controls.json), [verified raw control rows](baseline-verified-observations.json) and [final frozen-source checks](final-verification.json) and [actual reviewer-input checks](reviewer-input-audit.json) support provenance.

The saved-record audit finds verbatim legal prologues in 22/25 cases and authoring pointers in 25/25. [Record observations](record-observations.json) retain journal counts, summary fences, copied diagram blocks and post-proof writes. One cohort cannot establish that historical duplicate-journal risks are solved.

Limits remain: independent prepared stages, not a continuous project; one pure-function Build correction; Deliver before publication; one-component Adopt; native fresh-role fallback rather than installed-plugin discovery. Mermaid is inspected as source, not rendered or syntax-certified. Results do not certify every prompt instruction, host or interaction combination. No own AEGIS workflow, task journal, commit, push, publication or version bump was used.

## Raw collections

- [Core results](../../candidates/2026-10-22-luna-history-protocol-core/results.json), [manifest](../../candidates/2026-10-22-luna-history-protocol-core/manifest.json), [archive](../../candidates/2026-10-22-luna-history-protocol-core/evidence.zip).
- [Capability results](../../candidates/2026-10-22-luna-history-protocol-capabilities/results.json), [manifest](../../candidates/2026-10-22-luna-history-protocol-capabilities/manifest.json), [archive](../../candidates/2026-10-22-luna-history-protocol-capabilities/evidence.zip).

Both physical candidate collections together took 4283.744 seconds (71.4 minutes), excluding preparation/analysis time. The final 25-case cohort alone took 2246.067 seconds including pacing and reported 74,826 output tokens. No external model errors occurred in either cohort.
