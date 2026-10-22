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
