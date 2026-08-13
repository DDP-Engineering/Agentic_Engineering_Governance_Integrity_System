+++
schema = 1
artifact_type = "stage"
run_id = "RUN-00000000000040008000000000000000"
stage = "delivery"
sequence = 8
status = "pending"
started_at = ""
updated_at = "2026-01-01T00:00:00Z"
completed_at = ""
attachments = []
state_json = "{\"allowed_sections\":[\"requested_and_delivered_outcome\",\"project_artifact_changes\",\"implementation_changes\",\"evidence_summary\",\"test_integrity\",\"findings_and_residual_risk\",\"skips_waivers_and_omitted_stages\",\"component_drift_review\",\"delivery_decision\",\"terminal_result\"],\"attachments\":[],\"common_findings\":[\"The delivery claim is stronger than recorded evidence or omits a failed check.\",\"Residual risk, skipped work, waivers, or changed tests are not disclosed.\"],\"decisions\":[],\"escapes\":[],\"events\":[],\"evidence\":[],\"findings\":[],\"instruction\":\"Summarize requested and delivered outcomes, current project changes, actual evidence, changed tests, findings, skips, waivers, omissions, and residual risk. Approval accepts report truthfulness; AEGIS stops before outward Git actions.\",\"recovery_actions\":[{\"condition\":\"The report is incomplete but the recorded evidence is sufficient.\",\"guidance\":\"Correct the affected summary section without changing the underlying evidence.\",\"operation\":\"stage.set_section\"},{\"condition\":\"Missing evidence or work requires an earlier completed Stage.\",\"guidance\":\"Revisit that Stage with the concrete reason; Delivery remains unfinished.\",\"operation\":\"stage.revisit\"}],\"sections\":{\"component_drift_review\":\"None\",\"delivery_decision\":\"None\",\"evidence_summary\":\"None\",\"findings_and_residual_risk\":\"None\",\"implementation_changes\":\"None\",\"project_artifact_changes\":\"None\",\"requested_and_delivered_outcome\":\"None\",\"skips_waivers_and_omitted_stages\":\"None\",\"terminal_result\":\"None\",\"test_integrity\":\"None\"},\"work_applied\":false}"
+++

# 8 - Delivery

## Stage instruction

Summarize requested and delivered outcomes, current project changes, actual evidence, changed tests, findings, skips, waivers, omissions, and residual risk. Approval accepts report truthfulness; AEGIS stops before outward Git actions.

## Requested And Delivered Outcome

None

## Project Artifact Changes

None

## Implementation Changes

None

## Evidence Summary

None

## Test Integrity

None

## Findings And Residual Risk

None

## Skips Waivers And Omitted Stages

None

## Component Drift Review

None

## Delivery Decision

None

## Terminal Result

None

## Evidence

```json
[]
```

## Findings

```json
[]
```

## Decisions

```json
[]
```

## Escapes

```json
[]
```

## Attachments

```json
[]
```

## Event history

```json
[]
```
