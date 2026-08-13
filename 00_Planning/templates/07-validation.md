+++
schema = 1
artifact_type = "stage"
run_id = "RUN-00000000000040008000000000000000"
stage = "validation"
sequence = 7
status = "pending"
started_at = ""
updated_at = "2026-01-01T00:00:00Z"
completed_at = ""
attachments = []
state_json = "{\"allowed_sections\":[\"inputs\",\"impacted_test_selection\",\"automated_validation_evidence\",\"manual_validation_evidence\",\"test_integrity_conclusion\",\"outputs_and_handoff\"],\"attachments\":[],\"common_findings\":[\"Impacted selection omits a linked test without a reason or fallback.\",\"Test, lint, audit, or manual results are merged into a stronger conclusion than evidence supports.\"],\"decisions\":[],\"escapes\":[],\"events\":[],\"evidence\":[],\"findings\":[],\"instruction\":\"Select the complete safe impacted tests with reasons, or record and run the full-suite fallback. Record test, lint, audit, and manual outcomes independently without turning findings into blockers.\",\"recovery_actions\":[{\"condition\":\"A configured safe validation command still needs evidence.\",\"guidance\":\"Run the named command and preserve its independent operational outcome.\",\"operation\":\"execution.run\"},{\"condition\":\"A completed or skipped implementation step must be corrected.\",\"guidance\":\"Revisit Implementation with the concrete reason, then resume the forward path.\",\"operation\":\"stage.revisit\"}],\"sections\":{\"automated_validation_evidence\":\"None\",\"impacted_test_selection\":\"None\",\"inputs\":\"None\",\"manual_validation_evidence\":\"None\",\"outputs_and_handoff\":\"None\",\"test_integrity_conclusion\":\"None\"},\"work_applied\":false}"
+++

# 7 - Validation

## Stage instruction

Select the complete safe impacted tests with reasons, or record and run the full-suite fallback. Record test, lint, audit, and manual outcomes independently without turning findings into blockers.

## Inputs

None

## Impacted Test Selection

None

## Automated Validation Evidence

None

## Manual Validation Evidence

None

## Test Integrity Conclusion

None

## Outputs And Handoff

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
