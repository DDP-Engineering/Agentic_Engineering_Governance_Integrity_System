# AEGIS prompt baseline

Model: `qwen/qwen3.8-27b`. Profile: `core`. Runs: 10.
Automated scenario passes: 10/10.
Semantic rubric: pending human review; automated passes are not overall acceptance.
Median duration: 213.4 seconds.
Total model requests: 123; tool calls: 200; reviewer sessions: 0.
Unavailable read requests: 1; forbidden-action attempts: 0. Unavailable reads are diagnostics; forbidden actions fail the scope check.
Degenerate responses (one short unit repeated over 1,000+ characters): 0 coordinator, 0 reviewer.
Context window: 65,536 tokens; median peak prompt: 13,264; runs above 50%: 0; runs above 75%: 0.

| Scenario | Run | Execution | Automatic checks | Semantic | Seconds | Tools | Peak prompt | Window | Prompt total | Output |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| frame_existing_fix | 1 | completed | 11/11 | 1/1 | 218.7 | 23 | 12,688 | 19% | 119,794 | 8,196 |
| frame_ambiguous_retention | 1 | completed | 10/10 | 3/3 | 314.3 | 19 | 11,414 | 17% | 92,561 | 11,587 |
| frame_new_interface | 1 | completed | 10/10 | 2/2 | 263.2 | 21 | 11,886 | 18% | 106,550 | 9,957 |
| task_stale_handoff | 1 | completed | 12/12 | - | 544.1 | 18 | 21,075 | 32% | 95,269 | 20,281 |
| task_superseded_ruling | 1 | completed | 13/13 | - | 112.5 | 11 | 18,961 | 29% | 110,631 | 3,694 |
| task_unrecorded_evidence | 1 | completed | 13/13 | - | 95.1 | 8 | 17,166 | 26% | 77,982 | 2,962 |
| validate_clean_checkpoint | 1 | completed | 13/13 | - | 178.2 | 27 | 13,114 | 20% | 141,775 | 6,424 |
| validate_failed_verification | 1 | completed | 13/13 | - | 271.8 | 29 | 13,414 | 20% | 161,092 | 10,066 |
| validate_stale_verdicts | 1 | completed | 12/12 | - | 134.5 | 25 | 12,512 | 19% | 119,295 | 4,770 |
| validate_review_exhausted | 1 | completed | 12/12 | - | 208.1 | 19 | 21,323 | 32% | 176,783 | 7,091 |

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
| `.agentic/CLI.md` | 4 | 37,110 | 9,277 | 164,208 |
| `.agentic/AGENTS.md` | 10 | 27,610 | 2,761 | 107,860 |
| `.agentic/steps/5_validate.md` | 4 | 6,656 | 1,664 | 25,764 |
| `.agentic/tasks/TASK-aaaaaaaa.md` | 12 | 6,414 | 534 | 23,145 |
| `.agentic/steps/1_frame.md` | 4 | 4,519 | 1,129 | 18,816 |
| `.agentic/templates/task.md` | 3 | 2,073 | 691 | 12,501 |
| `.agentic/knowledge/normalization.md` | 6 | 1,128 | 188 | 4,164 |
| `.agentic/requirements/functional/REQ-FUNC-11111111.toml` | 8 | 1,111 | 138 | 4,384 |
| `tests/test_normalize.py` | 7 | 726 | 103 | 3,101 |
| `.agentic/templates/component.md` | 2 | 712 | 356 | 6,620 |
| `.agentic/steps/review.md` | 1 | 549 | 549 | 2,169 |
| `.agentic/tasks/TASK-e2425df8.md` | 1 | 494 | 494 | 1,740 |

## Limits

This is a constrained tool-host baseline, not Codex/Claude/OpenCode host certification.
Reviewer findings are scripted inputs; independent reviewer quality is not measured.
One-stage sessions do not establish full-workflow completion or statistical reliability.
Missing token usage remains unknown. Repeated input tokens include conversation replay.
Read costs share each request's prompt growth among its tool results by length.
Server sampling defaults, hardware and load can affect results even at temperature zero.
No prompt changes are made by the harness.
