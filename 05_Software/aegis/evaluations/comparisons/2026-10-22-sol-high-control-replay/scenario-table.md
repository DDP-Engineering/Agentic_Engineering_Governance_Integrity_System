| Scenario | Luna medium | Sol high | Seconds P/R | Output tokens P/R | Failed Sol checks |
|---|---|---|---:|---:|---|
| `frame_existing_fix` | pass | pass | 63.0 / 106.8 | 2,022 / 2,814 | — |
| `frame_ambiguous_retention` | pass | pass | 37.0 / 106.5 | 2,336 / 3,164 | — |
| `frame_new_interface` | pass | pass | 55.8 / 96.9 | 1,828 / 2,734 | — |
| `task_stale_handoff` | pass | pass | 90.6 / 51.5 | 1,724 / 1,350 | — |
| `task_superseded_ruling` | pass | pass | 65.1 / 60.2 | 1,113 / 1,293 | — |
| `task_unrecorded_evidence` | pass | pass | 38.7 / 51.7 | 1,254 / 1,273 | — |
| `validate_clean_checkpoint` | pass | pass | 83.1 / 112.3 | 3,133 / 3,219 | — |
| `validate_failed_verification` | pass | fail | 61.6 / 138.5 | 5,037 / 3,554 | no_forbidden_actions |
| `validate_stale_verdicts` | pass | pass | 23.0 / 91.0 | 1,730 / 2,222 | — |
| `validate_review_exhausted` | pass | pass | 72.8 / 64.6 | 1,276 / 1,622 | — |
| `specify_exact_serialization` | pass | pass | 47.6 / 207.0 | 3,793 / 7,788 | — |
| `build_existing_contract` | pass | fail | 40.1 / 66.1 | 2,001 / 2,165 | active_requirement_linked_to_real_tests |
| `deliver_requires_approval` | fail | pass | 69.4 / 75.7 | 2,568 / 2,118 | — |
| `deliver_changed_after_proof` | fail | pass | 47.2 / 63.0 | 2,302 / 1,783 | — |
| `adopt_existing_component` | pass | pass | 59.6 / 106.8 | 2,022 / 2,794 | — |
| `review_enabled_current` | pass | pass | 150.1 / 234.9 | 3,530 / 5,552 | — |
| `review_disabled_no_delegation` | pass | pass | 69.5 / 89.2 | 2,715 / 2,747 | — |
| `review_detects_missing_behavior` | pass | pass | 150.7 / 253.7 | 4,967 / 4,900 | — |
| `diagrams_enabled_types` | pass | pass | 59.9 / 203.0 | 3,996 / 6,017 | — |
| `diagrams_disabled` | pass | pass | 70.4 / 192.9 | 3,349 / 5,906 | — |
| `diagrams_empty_types` | pass | pass | 93.0 / 105.5 | 5,277 / 3,829 | — |
| `diagrams_skipped_design` | pass | pass | 27.7 / 91.4 | 1,979 / 2,556 | — |
| `autopilot_design_transition` | fail | fail | 38.0 / 117.6 | 3,349 / 5,395 | awaits_user |
| `autopilot_explicit_stage_stop` | pass | pass | 74.2 / 206.3 | 5,641 / 5,482 | — |
| `validate_stale_context` | fail | fail | 47.6 / 119.0 | 3,693 / 3,241 | project_current_behavior; environment_current_command |
