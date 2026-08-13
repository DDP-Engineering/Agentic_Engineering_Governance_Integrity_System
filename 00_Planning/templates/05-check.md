+++
schema = 1
artifact_type = "stage"
run_id = "RUN-00000000000040008000000000000000"
stage = "check"
sequence = 5
status = "pending"
started_at = ""
updated_at = "2026-01-01T00:00:00Z"
completed_at = ""
attachments = []
state_json = "{\"allowed_sections\":[\"inputs\",\"test_work\",\"recorded_red_evidence\",\"test_fingerprints_at_red\",\"red_before_green_decision\",\"outputs_and_handoff\"],\"attachments\":[],\"common_findings\":[\"The selected test passes before implementation or does not exercise the requested behavior.\",\"The proposed check is unsafe, overbroad, or outside configured test roots.\"],\"decisions\":[],\"escapes\":[],\"events\":[],\"evidence\":[],\"findings\":[],\"instruction\":\"Create or select proportional verification under configured test roots. Run the selected test with normal host tooling, then use evidence-add to record its actual outcome and exact-byte test fingerprints. When red-before-green genuinely does not apply, use decision-add with target red_before_green, value exception_approved, reason, and alternative_confirmation.\",\"recovery_actions\":[{\"condition\":\"Red-before-green genuinely does not apply.\",\"guidance\":\"Record target red_before_green, value exception_approved, a reason, and alternative_confirmation.\",\"operation\":\"decision.add\"},{\"condition\":\"Check is disproportionate and no Stage work was applied.\",\"guidance\":\"Skip with the concrete reason; missing verification remains visible downstream.\",\"operation\":\"stage.skip\"}],\"sections\":{\"inputs\":\"None\",\"outputs_and_handoff\":\"None\",\"recorded_red_evidence\":\"None\",\"red_before_green_decision\":\"None\",\"test_fingerprints_at_red\":\"None\",\"test_work\":\"None\"},\"work_applied\":false}"
+++

# 5 - Check

## Stage instruction

Create or select proportional verification under configured test roots. Run the selected test with normal host tooling, then use evidence-add to record its actual outcome and exact-byte test fingerprints. When red-before-green genuinely does not apply, use decision-add with target red_before_green, value exception_approved, reason, and alternative_confirmation.

## Inputs

None

## Test Work

None

## Recorded Red Evidence

None

## Test Fingerprints At Red

None

## Red Before Green Decision

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
