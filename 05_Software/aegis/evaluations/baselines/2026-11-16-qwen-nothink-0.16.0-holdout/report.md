# AEGIS prompt baseline

Model: `qwen/qwen3.8-27b`. Profile: `holdout`. Runs: 6.
Automated scenario passes: 6/6.
Semantic rubric: pending human review; automated passes are not overall acceptance.
Median duration: 73.9 seconds.
Total model requests: 125; tool calls: 195; reviewer sessions: 0.
Unavailable read requests: 3; forbidden-action attempts: 0. Unavailable reads are diagnostics; forbidden actions fail the scope check.
Degenerate responses (one short unit repeated over 1,000+ characters): 0 coordinator, 0 reviewer.
Context window: 65,536 tokens; median peak prompt: 11,722; runs above 50%: 0; runs above 75%: 0.

| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | Tools | Peak prompt | Window | Prompt total | Output |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| holdout_frame_existing_fix | 1 | completed | 11/11 | 1/1 | 65.3 | 19 | 10,481 | 16% | 79,291 | 2,349 |
| holdout_frame_ambiguous_policy | 1 | completed | 10/10 | 3/3 | 71.9 | 16 | 10,122 | 15% | 70,721 | 2,607 |
| holdout_frame_new_format | 1 | completed | 10/10 | 2/2 | 70.0 | 16 | 10,118 | 15% | 76,747 | 2,517 |
| holdout_specify_exact_format | 1 | completed | 17/17 | 1/1 | 75.8 | 24 | 12,963 | 20% | 129,323 | 2,842 |
| holdout_design_recalculation | 1 | completed | 15/15 | 3/3 | 89.2 | 25 | 14,138 | 22% | 116,942 | 3,282 |
| holdout_chain_percent_validation | 1 | completed | 16/16 | 2/2 | 275.4 | 95 | 13,575 | 21% | 546,635 | 9,942 |

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
| `.agentic/AGENTS.md` | 8 | 22,416 | 2,802 | 86,288 |
| `.agentic/tasks/TASK-560cdecb.md` | 5 | 9,036 | 1,807 | 32,344 |
| `.agentic/steps/1_frame.md` | 4 | 4,738 | 1,184 | 18,816 |
| `.agentic/steps/2_specify.md` | 3 | 3,725 | 1,241 | 13,578 |
| `.agentic/templates/requirement.toml` | 3 | 3,413 | 1,137 | 12,501 |
| `.agentic/steps/3_design.md` | 3 | 2,889 | 963 | 10,554 |
| `.agentic/knowledge/pricing.md` | 9 | 1,840 | 204 | 5,913 |
| `.agentic/steps/5_validate.md` | 1 | 1,817 | 1,817 | 6,441 |
| `tests/test_pricing.py` | 10 | 1,704 | 170 | 4,823 |
| `.agentic/requirements/functional/REQ-FUNC-22222222.toml` | 9 | 1,670 | 185 | 5,112 |
| `.agentic/tasks/TASK-aaaaaaaa.md` | 2 | 1,181 | 590 | 4,455 |
| `.agentic/steps/4_build.md` | 1 | 1,127 | 1,127 | 4,273 |

## Limits

This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.
Reviewer findings are scripted inputs; independent reviewer quality is not measured.
One-stage sessions do not establish full-workflow completion or statistical reliability.
Missing token usage remains unknown. Repeated input tokens include conversation replay.
Read costs share each request's prompt growth among its tool results by length.
Server sampling defaults, hardware and load can affect results even at temperature zero.
No prompt changes are made by the harness.
