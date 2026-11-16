# AEGIS prompt baseline

Model: `qwen/qwen3.8-27b`. Profile: `capabilities`. Runs: 15.
Automated scenario passes: 15/15.
Semantic rubric: pending human review; automated passes are not overall acceptance.
Median duration: 386.0 seconds.
Total model requests: 237; tool calls: 442; reviewer sessions: 4.
Unavailable read requests: 5; forbidden-action attempts: 0. Unavailable reads are diagnostics; forbidden actions fail the scope check.
Degenerate responses (one short unit repeated over 1,000+ characters): 0 coordinator, 0 reviewer.
Context window: 65,536 tokens; median peak prompt: 16,555; runs above 50%: 0; runs above 75%: 0.

| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | Tools | Peak prompt | Window | Prompt total | Output |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| specify_exact_serialization | 1 | completed | 18/18 | 1/1 | 746.7 | 37 | 27,440 | 42% | 327,410 | 25,337 |
| build_existing_contract | 1 | completed | 16/16 | - | 121.2 | 27 | 12,414 | 19% | 146,752 | 4,290 |
| deliver_requires_approval | 1 | completed | 16/16 | - | 333.2 | 26 | 14,023 | 21% | 128,826 | 11,771 |
| deliver_changed_after_proof | 1 | completed | 14/14 | - | 218.7 | 12 | 10,913 | 17% | 53,661 | 8,357 |
| adopt_existing_component | 1 | completed | 17/17 | - | 341.2 | 24 | 13,208 | 20% | 123,085 | 12,125 |
| review_enabled_current | 1 | completed | 16/16 | - | 620.6 | 31 | 17,213 | 26% | 214,358 | 8,339 |
| review_disabled_no_delegation | 1 | completed | 14/14 | - | 316.5 | 29 | 16,555 | 25% | 173,939 | 10,993 |
| review_detects_missing_behavior | 1 | completed | 17/17 | - | 606.2 | 22 | 15,033 | 23% | 110,243 | 4,495 |
| diagrams_enabled_types | 1 | completed | 19/19 | 2/2 | 590.6 | 38 | 19,423 | 30% | 276,422 | 21,708 |
| diagrams_disabled | 1 | completed | 14/14 | - | 276.4 | 27 | 14,813 | 23% | 136,917 | 10,292 |
| diagrams_empty_types | 1 | completed | 14/14 | - | 386.0 | 36 | 17,963 | 27% | 209,978 | 13,324 |
| diagrams_skipped_design | 1 | completed | 14/14 | - | 403.6 | 24 | 13,449 | 20% | 109,149 | 14,362 |
| autopilot_design_transition | 1 | completed | 21/21 | - | 1006.9 | 36 | 20,748 | 32% | 272,289 | 36,033 |
| autopilot_explicit_stage_stop | 1 | completed | 21/21 | - | 975.4 | 37 | 21,282 | 32% | 267,197 | 33,292 |
| validate_stale_context | 1 | completed | 19/19 | - | 311.5 | 36 | 17,578 | 27% | 225,518 | 10,971 |

## Failed automatic checks


## Failed semantic checks

Semantic checks are deterministic proxies reported beside the strict checks; they never change a strict pass.


## Pass rate by case

| Scenario | Strict passes | Semantic passes |
|---|---:|---:|
| specify_exact_serialization | 1/1 | 1/1 |
| build_existing_contract | 1/1 | - |
| deliver_requires_approval | 1/1 | - |
| deliver_changed_after_proof | 1/1 | - |
| adopt_existing_component | 1/1 | - |
| review_enabled_current | 1/1 | - |
| review_disabled_no_delegation | 1/1 | - |
| review_detects_missing_behavior | 1/1 | - |
| diagrams_enabled_types | 1/1 | 1/1 |
| diagrams_disabled | 1/1 | - |
| diagrams_empty_types | 1/1 | - |
| diagrams_skipped_design | 1/1 | - |
| autopilot_design_transition | 1/1 | - |
| autopilot_explicit_stage_stop | 1/1 | - |
| validate_stale_context | 1/1 | - |

## Most expensive reads

| Path | Reads | Tokens | Tokens per read | Characters |
|---|---:|---:|---:|---:|
| `.agentic/AGENTS.md` | 15 | 41,727 | 2,781 | 161,790 |
| `.agentic/tasks/TASK-aaaaaaaa.md` | 27 | 15,989 | 592 | 67,640 |
| `.agentic/CLI.md` | 1 | 10,278 | 10,278 | 41,052 |
| `.agentic/steps/5_validate.md` | 6 | 9,989 | 1,664 | 38,646 |
| `.agentic/steps/3_design.md` | 6 | 5,479 | 913 | 21,108 |
| `.agentic/templates/task.md` | 6 | 5,017 | 836 | 25,002 |
| `.agentic/templates/requirement.toml` | 4 | 2,853 | 713 | 16,668 |
| `.agentic/steps/2_specify.md` | 2 | 2,164 | 1,082 | 9,052 |
| `.agentic/requirements/functional/REQ-FUNC-11111111.toml` | 14 | 2,108 | 150 | 7,672 |
| `.agentic/steps/adopt.md` | 1 | 1,819 | 1,819 | 7,590 |
| `.agentic/knowledge/normalization.md` | 12 | 1,745 | 145 | 7,923 |
| `.agentic/steps/diagrams.md` | 3 | 1,632 | 544 | 15,594 |

## Limits

This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.
Reviewer sessions are fresh local sessions with the same model and endpoint.
One-stage sessions do not establish full-workflow completion or statistical reliability.
Missing token usage remains unknown. Repeated input tokens include conversation replay.
Read costs share each request's prompt growth among its tool results by length.
Server sampling defaults, hardware and load can affect results even at temperature zero.
No prompt changes are made by the harness.
