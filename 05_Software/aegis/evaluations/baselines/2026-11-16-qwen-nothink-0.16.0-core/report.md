# AEGIS prompt baseline

Model: `qwen/qwen3.8-27b`. Profile: `core`. Runs: 10.
Automated scenario passes: 10/10.
Semantic rubric: pending human review; automated passes are not overall acceptance.
Median duration: 47.5 seconds.
Total model requests: 111; tool calls: 162; reviewer sessions: 0.
Unavailable read requests: 2; forbidden-action attempts: 0. Unavailable reads are diagnostics; forbidden actions fail the scope check.
Degenerate responses (one short unit repeated over 1,000+ characters): 0 coordinator, 0 reviewer.
Context window: 65,536 tokens; median peak prompt: 9,383; runs above 50%: 0; runs above 75%: 0.

| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | Tools | Peak prompt | Window | Prompt total | Output |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| frame_existing_fix | 1 | completed | 11/11 | 1/1 | 69.0 | 15 | 9,744 | 15% | 59,589 | 2,541 |
| frame_ambiguous_retention | 1 | completed | 10/10 | 3/3 | 54.1 | 16 | 9,341 | 14% | 66,933 | 1,745 |
| frame_new_interface | 1 | completed | 10/10 | 2/2 | 98.1 | 26 | 12,632 | 19% | 176,159 | 3,405 |
| task_stale_handoff | 1 | completed | 12/12 | - | 60.1 | 19 | 20,186 | 31% | 153,427 | 1,636 |
| task_superseded_ruling | 1 | completed | 13/13 | - | 20.0 | 8 | 6,255 | 10% | 33,733 | 603 |
| task_unrecorded_evidence | 1 | completed | 13/13 | - | 9.6 | 4 | 3,099 | 5% | 12,023 | 322 |
| validate_clean_checkpoint | 1 | completed | 13/13 | - | 46.7 | 22 | 9,041 | 14% | 96,309 | 1,550 |
| validate_failed_verification | 1 | completed | 13/13 | - | 48.2 | 21 | 8,406 | 13% | 76,597 | 1,717 |
| validate_stale_verdicts | 1 | completed | 12/12 | - | 44.9 | 20 | 10,782 | 16% | 77,566 | 1,375 |
| validate_review_exhausted | 1 | completed | 12/12 | - | 31.2 | 11 | 9,425 | 14% | 56,153 | 971 |

## Failed automatic checks


## Failed semantic checks

Semantic checks are deterministic proxies reported beside the strict checks; they never change a strict pass.


## Pass rate by case

| Scenario | Strict passes | Semantic passes |
|---|---:|---:|
| frame_existing_fix | 1/1 | 1/1 |
| frame_ambiguous_retention | 1/1 | 1/1 |
| frame_new_interface | 1/1 | 1/1 |
| task_stale_handoff | 1/1 | - |
| task_superseded_ruling | 1/1 | - |
| task_unrecorded_evidence | 1/1 | - |
| validate_clean_checkpoint | 1/1 | - |
| validate_failed_verification | 1/1 | - |
| validate_stale_verdicts | 1/1 | - |
| validate_review_exhausted | 1/1 | - |

## Most expensive reads

| Path | Reads | Tokens | Tokens per read | Characters |
|---|---:|---:|---:|---:|
| `.agentic/AGENTS.md` | 5 | 13,907 | 2,781 | 53,930 |
| `.agentic/CLI.md` | 1 | 10,200 | 10,200 | 41,052 |
| `.agentic/steps/5_validate.md` | 4 | 6,697 | 1,674 | 25,764 |
| `.agentic/tasks/TASK-aaaaaaaa.md` | 10 | 5,358 | 535 | 19,098 |
| `.agentic/steps/1_frame.md` | 4 | 4,689 | 1,172 | 18,816 |
| `.agentic/steps/4_build.md` | 2 | 2,174 | 1,087 | 8,546 |
| `.agentic/knowledge/normalization.md` | 7 | 1,454 | 207 | 4,858 |
| `.agentic/requirements/functional/REQ-FUNC-11111111.toml` | 7 | 1,298 | 185 | 3,836 |
| `.agentic/steps/review.md` | 2 | 1,140 | 570 | 4,338 |
| `.agentic/templates/task.md` | 1 | 1,102 | 1,102 | 4,167 |
| `tests/test_normalize.py` | 6 | 992 | 165 | 2,658 |
| `.agentic/tasks/TASK-2f2fa17f.md` | 3 | 774 | 258 | 2,525 |

## Limits

This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.
Reviewer findings are scripted inputs; independent reviewer quality is not measured.
One-stage sessions do not establish full-workflow completion or statistical reliability.
Missing token usage remains unknown. Repeated input tokens include conversation replay.
Read costs share each request's prompt growth among its tool results by length.
Server sampling defaults, hardware and load can affect results even at temperature zero.
No prompt changes are made by the harness.
