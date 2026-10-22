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
