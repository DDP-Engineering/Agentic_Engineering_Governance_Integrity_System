# AEGIS prompt baseline

Model: `qwen/qwen3.8-27b`. Profile: `holdout`. Runs: 6.
Automated scenario passes: 6/6.
Semantic rubric: pending human review; automated passes are not overall acceptance.
Median duration: 282.0 seconds.
Total model requests: 133; tool calls: 237; reviewer sessions: 0.
Unavailable read requests: 0; forbidden-action attempts: 0. Unavailable reads are diagnostics; forbidden actions fail the scope check.
Degenerate responses (one short unit repeated over 1,000+ characters): 0 coordinator, 0 reviewer.
Context window: 65,536 tokens; median peak prompt: 14,484; runs above 50%: 0; runs above 75%: 0.

| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | Tools | Peak prompt | Window | Prompt total | Output |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| holdout_frame_existing_fix | 1 | completed | 11/11 | 1/1 | 286.1 | 23 | 13,222 | 20% | 134,715 | 10,357 |
| holdout_frame_ambiguous_policy | 1 | completed | 10/10 | 3/3 | 277.8 | 19 | 11,902 | 18% | 88,948 | 9,558 |
| holdout_frame_new_format | 1 | completed | 10/10 | 2/2 | 243.1 | 18 | 10,567 | 16% | 80,104 | 9,195 |
| holdout_specify_exact_format | 1 | completed | 17/17 | 1/1 | 291.1 | 34 | 17,171 | 26% | 183,782 | 10,371 |
| holdout_design_recalculation | 1 | completed | 15/15 | 3/3 | 242.1 | 26 | 15,747 | 24% | 131,076 | 8,218 |
| holdout_chain_percent_validation | 1 | completed | 16/16 | 2/2 | 837.8 | 117 | 18,299 | 28% | 735,174 | 30,966 |

## Failed automatic checks


## Failed semantic checks

Semantic checks are deterministic proxies reported beside the strict checks; they never change a strict pass.


## Pass rate by case

| Scenario | Strict passes | Semantic passes |
|---|---:|---:|
| holdout_frame_existing_fix | 1/1 | 1/1 |
| holdout_frame_ambiguous_policy | 1/1 | 1/1 |
| holdout_frame_new_format | 1/1 | 1/1 |
| holdout_specify_exact_format | 1/1 | 1/1 |
| holdout_design_recalculation | 1/1 | 1/1 |
| holdout_chain_percent_validation | 1/1 | 1/1 |

## Most expensive reads

| Path | Reads | Tokens | Tokens per read | Characters |
|---|---:|---:|---:|---:|
| `.agentic/AGENTS.md` | 10 | 27,953 | 2,795 | 107,860 |
| `.agentic/tasks/TASK-149cd5fd.md` | 8 | 10,303 | 1,287 | 40,042 |
| `.agentic/steps/1_frame.md` | 4 | 4,561 | 1,140 | 18,816 |
| `.agentic/steps/2_specify.md` | 4 | 4,420 | 1,105 | 18,104 |
| `.agentic/templates/task.md` | 4 | 3,060 | 765 | 16,668 |
| `.agentic/templates/requirement.toml` | 3 | 3,056 | 1,018 | 12,501 |
| `.agentic/tasks/TASK-aaaaaaaa.md` | 4 | 3,000 | 750 | 11,705 |
| `.agentic/steps/4_build.md` | 2 | 2,339 | 1,169 | 8,546 |
| `.agentic/steps/3_design.md` | 2 | 1,846 | 923 | 7,036 |
| `.agentic/knowledge/pricing.md` | 9 | 1,739 | 193 | 5,913 |
| `.agentic/steps/5_validate.md` | 1 | 1,722 | 1,722 | 6,441 |
| `.agentic/requirements/functional/REQ-FUNC-22222222.toml` | 10 | 1,656 | 165 | 5,680 |

## Limits

This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.
Reviewer findings are scripted inputs; independent reviewer quality is not measured.
One-stage sessions do not establish full-workflow completion or statistical reliability.
Missing token usage remains unknown. Repeated input tokens include conversation replay.
Read costs share each request's prompt growth among its tool results by length.
Server sampling defaults, hardware and load can affect results even at temperature zero.
No prompt changes are made by the harness.
