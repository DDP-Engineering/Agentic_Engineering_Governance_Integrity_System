| Scenario | Previous | Revised | Seconds P/R | Output tokens P/R | Failed revised checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 63.0 / 39.3 | 2,022 / 2,239 | — |
| `frame_ambiguous_retention` | pass | pass | 37.0 / 41.5 | 2,336 / 2,200 | — |
| `frame_new_interface` | pass | pass | 55.8 / 35.5 | 1,828 / 2,379 | — |
| `task_stale_handoff` | pass | pass | 90.6 / 23.2 | 1,724 / 1,620 | — |
| `task_superseded_ruling` | pass | pass | 65.1 / 22.4 | 1,113 / 1,222 | — |
| `task_unrecorded_evidence` | pass | pass | 38.7 / 26.9 | 1,254 / 1,399 | — |
| `validate_clean_checkpoint` | pass | pass | 83.1 / 46.9 | 3,133 / 3,268 | — |
| `validate_failed_verification` | pass | pass | 61.6 / 33.6 | 5,037 / 1,935 | — |
| `validate_stale_verdicts` | pass | pass | 23.0 / 34.0 | 1,730 / 2,120 | — |
| `validate_review_exhausted` | pass | pass | 72.8 / 26.1 | 1,276 / 1,467 | — |
| `specify_exact_serialization` | pass | pass | 47.6 / 56.9 | 3,793 / 3,483 | — |
| `build_existing_contract` | pass | pass | 40.1 / 53.2 | 2,001 / 2,670 | — |
| `deliver_requires_approval` | fail | pass | 69.4 / 43.5 | 2,568 / 2,637 | — |
| `deliver_changed_after_proof` | fail | pass | 47.2 / 28.7 | 2,302 / 2,101 | — |
| `adopt_existing_component` | pass | pass | 59.6 / 35.6 | 2,022 / 1,947 | — |
| `review_enabled_current` | pass | pass | 150.1 / 144.8 | 3,530 / 4,450 | — |
| `review_disabled_no_delegation` | pass | pass | 69.5 / 36.9 | 2,715 / 2,327 | — |
| `review_detects_missing_behavior` | pass | fail | 150.7 / 132.0 | 4,967 / 4,604 | independent_read_evidence |
| `diagrams_enabled_types` | pass | fail | 59.9 / 51.4 | 3,996 / 4,853 | diagrams_shown_after_summary |
| `diagrams_disabled` | pass | pass | 70.4 / 56.4 | 3,349 / 4,823 | — |
| `diagrams_empty_types` | pass | pass | 93.0 / 48.7 | 5,277 / 4,378 | — |
| `diagrams_skipped_design` | pass | pass | 27.7 / 53.2 | 1,979 / 2,972 | — |
| `autopilot_design_transition` | fail | fail | 38.0 / 83.3 | 3,349 / 5,762 | awaits_user; diagram_artifact_and_link; generated_structure; generated_sequence; generated_state; structure_change_markers; autopilot_diagram_reported |
| `autopilot_explicit_stage_stop` | pass | fail | 74.2 / 52.4 | 5,641 / 4,232 | preserves_history |
| `validate_stale_context` | fail | fail | 47.6 / 35.7 | 3,693 / 2,362 | fresh_successful_proof; project_current_behavior |
