+++
schema = 1
artifact_type = "stage"
run_id = "RUN-00000000000040008000000000000000"
stage = "implementation"
sequence = 6
status = "pending"
started_at = ""
updated_at = "2026-01-01T00:00:00Z"
completed_at = ""
attachments = []
state_json = "{\"allowed_sections\":[\"inputs\",\"implementation_changes\",\"test_integrity_comparison\",\"implementation_evidence\",\"component_documentation_review\",\"outputs_and_handoff\"],\"attachments\":[],\"common_findings\":[\"Changed paths exceed agreed scope without a recorded scope revision.\",\"Tests changed after the red witness without an explicit integrity conclusion.\"],\"decisions\":[],\"escapes\":[],\"events\":[],\"evidence\":[],\"findings\":[],\"instruction\":\"Implement the agreed behavior, record attributed changed paths, compare current test fingerprints with the immutable red witness, and review affected Component documentation. Test changes remain permitted and visible.\",\"recovery_actions\":[{\"condition\":\"Necessary work changes the agreed scope.\",\"guidance\":\"Record the included and excluded scope, reason, actor, and whether approval is required.\",\"operation\":\"scope.revise\"},{\"condition\":\"The red witness or test intent must be re-established.\",\"guidance\":\"Revisit Check with the concrete reason before continuing forward.\",\"operation\":\"stage.revisit\"}],\"sections\":{\"component_documentation_review\":\"None\",\"implementation_changes\":\"None\",\"implementation_evidence\":\"None\",\"inputs\":\"None\",\"outputs_and_handoff\":\"None\",\"test_integrity_comparison\":\"None\"},\"work_applied\":false}"
+++

# 6 - Implementation

## Stage instruction

Implement the agreed behavior, record attributed changed paths, compare current test fingerprints with the immutable red witness, and review affected Component documentation. Test changes remain permitted and visible.

## Inputs

None

## Implementation Changes

None

## Test Integrity Comparison

None

## Implementation Evidence

None

## Component Documentation Review

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
