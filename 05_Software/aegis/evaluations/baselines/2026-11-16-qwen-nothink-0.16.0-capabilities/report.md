# AEGIS prompt baseline

Model: `qwen/qwen3.8-27b`. Profile: `capabilities`. Runs: 15.
Automated scenario passes: 13/15.
Semantic rubric: pending human review; automated passes are not overall acceptance.
Median duration: 82.7 seconds.
Total model requests: 211; tool calls: 337; reviewer sessions: 4.
Unavailable read requests: 3; forbidden-action attempts: 0. Unavailable reads are diagnostics; forbidden actions fail the scope check.
Degenerate responses (one short unit repeated over 1,000+ characters): 0 coordinator, 0 reviewer.
Context window: 65,536 tokens; median peak prompt: 13,181; runs above 50%: 0; runs above 75%: 0.

| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | Tools | Peak prompt | Window | Prompt total | Output |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| specify_exact_serialization | 1 | completed | 18/18 | 1/1 | 82.7 | 27 | 14,164 | 22% | 174,857 | 3,055 |
| build_existing_contract | 1 | completed | 16/16 | - | 38.8 | 19 | 8,548 | 13% | 93,117 | 1,290 |
| deliver_requires_approval | 1 | completed | 16/16 | - | 40.0 | 14 | 8,205 | 12% | 52,493 | 1,478 |
| deliver_changed_after_proof | 1 | completed | 13/14 | - | 33.3 | 9 | 5,653 | 9% | 27,793 | 1,241 |
| adopt_existing_component | 1 | completed | 17/17 | - | 65.0 | 25 | 13,181 | 20% | 129,834 | 2,354 |
| review_enabled_current | 1 | completed | 16/16 | - | 149.2 | 23 | 14,629 | 22% | 128,890 | 1,803 |
| review_disabled_no_delegation | 1 | completed | 14/14 | - | 43.8 | 22 | 9,475 | 14% | 83,052 | 1,434 |
| review_detects_missing_behavior | 1 | completed | 17/17 | - | 154.0 | 11 | 12,030 | 18% | 68,523 | 1,378 |
| diagrams_enabled_types | 1 | completed | 19/19 | 2/2 | 107.8 | 29 | 14,060 | 22% | 172,057 | 3,852 |
| diagrams_disabled | 1 | completed | 14/14 | - | 113.1 | 38 | 28,182 | 43% | 411,854 | 3,537 |
| diagrams_empty_types | 1 | completed | 14/14 | - | 89.7 | 30 | 17,091 | 26% | 204,245 | 2,961 |
| diagrams_skipped_design | 1 | completed | 14/14 | - | 40.0 | 13 | 8,967 | 14% | 62,656 | 1,302 |
| autopilot_design_transition | 1 | completed | 15/21 | - | 97.1 | 26 | 13,391 | 20% | 137,564 | 3,469 |
| autopilot_explicit_stage_stop | 1 | completed | 21/21 | - | 85.0 | 23 | 12,838 | 20% | 131,808 | 2,959 |
| validate_stale_context | 1 | completed | 19/19 | - | 66.3 | 28 | 14,315 | 22% | 154,302 | 2,172 |

## Failed automatic checks

- deliver_changed_after_proof / 1: stage_prompt_read
- autopilot_design_transition / 1: diagram_artifact_and_link, generated_structure, generated_sequence, generated_state, structure_change_markers, autopilot_diagram_reported

## Failed semantic checks

Semantic checks are deterministic proxies reported beside the strict checks; they never change a strict pass.


## Pass rate by case

| Scenario | Strict passes | Semantic passes |
|---|---:|---:|
| specify_exact_serialization | 1/1 | 1/1 |
| build_existing_contract | 1/1 | - |
| deliver_requires_approval | 1/1 | - |
| deliver_changed_after_proof | 0/1 | - |
| adopt_existing_component | 1/1 | - |
| review_enabled_current | 1/1 | - |
| review_disabled_no_delegation | 1/1 | - |
| review_detects_missing_behavior | 1/1 | - |
| diagrams_enabled_types | 1/1 | 1/1 |
| diagrams_disabled | 1/1 | - |
| diagrams_empty_types | 1/1 | - |
| diagrams_skipped_design | 1/1 | - |
| autopilot_design_transition | 0/1 | - |
| autopilot_explicit_stage_stop | 1/1 | - |
| validate_stale_context | 1/1 | - |

## Most expensive reads

| Path | Reads | Tokens | Tokens per read | Characters |
|---|---:|---:|---:|---:|
| `.agentic/AGENTS.md` | 11 | 31,151 | 2,831 | 118,646 |
| `.agentic/tasks/TASK-aaaaaaaa.md` | 18 | 10,390 | 577 | 38,952 |
| `.agentic/CLI.md` | 1 | 10,189 | 10,189 | 41,052 |
| `.agentic/steps/5_validate.md` | 5 | 8,254 | 1,650 | 32,205 |
| `.agentic/steps/3_design.md` | 6 | 5,661 | 943 | 21,108 |
| `.agentic/steps/2_specify.md` | 3 | 3,452 | 1,150 | 13,578 |
| `.agentic/templates/requirement.toml` | 3 | 3,262 | 1,087 | 12,501 |
| `.agentic/steps/diagrams.md` | 2 | 2,624 | 1,312 | 10,396 |
| `.agentic/templates/task.md` | 2 | 2,170 | 1,085 | 8,334 |
| `.agentic/knowledge/normalization.md` | 10 | 1,918 | 191 | 6,697 |
| `.agentic/requirements/functional/REQ-FUNC-11111111.toml` | 12 | 1,905 | 158 | 6,576 |
| `.agentic/steps/adopt.md` | 1 | 1,838 | 1,838 | 7,590 |

## Limits

This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.
Reviewer sessions are fresh local sessions with the same model and endpoint.
One-stage sessions do not establish full-workflow completion or statistical reliability.
Missing token usage remains unknown. Repeated input tokens include conversation replay.
Read costs share each request's prompt growth among its tool results by length.
Server sampling defaults, hardware and load can affect results even at temperature zero.
No prompt changes are made by the harness.
