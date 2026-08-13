+++
schema = 1
artifact_type = "stage"
run_id = "RUN-00000000000040008000000000000000"
stage = "intake"
sequence = 1
status = "active"
started_at = "2026-01-01T00:00:00Z"
updated_at = "2026-01-01T00:00:00Z"
completed_at = ""
attachments = []
state_json = "{\"allowed_sections\":[\"inputs\",\"configured_project_paths\",\"relevant_project_knowledge\",\"restated_ask\",\"initially_affected_repository_area\",\"facts_and_uncertainties\",\"outputs_and_handoff\"],\"attachments\":[],\"common_findings\":[\"The restatement adds scope or loses a constraint from the ticket.\",\"An assumption is presented as a confirmed repository fact.\"],\"decisions\":[],\"escapes\":[],\"events\":[{\"actor\":\"reference-generator\",\"event\":\"stage_started\",\"result\":\"Intake became active.\",\"time\":\"2026-01-01T00:00:00Z\"}],\"evidence\":[],\"findings\":[],\"instruction\":\"Start from the unchanged ticket text. Read project configuration, optional rules, relevant Components, linked Requirements, tests, and the opening Git state. Restate the ask, identify bounded scope, and expose uncertainty without requiring prepared scope.\",\"recovery_actions\":[{\"condition\":\"Context is incomplete but bounded work can continue.\",\"guidance\":\"Record known facts, explicit uncertainties, and the next focused inspection.\",\"operation\":\"stage.set_section\"},{\"condition\":\"The request is withdrawn or no truthful development path remains.\",\"guidance\":\"End the Run with the actor and concrete reason; do not fabricate progress.\",\"operation\":\"run.abandon\"}],\"sections\":{\"configured_project_paths\":\"None\",\"facts_and_uncertainties\":\"None\",\"initially_affected_repository_area\":\"None\",\"inputs\":\"None\",\"outputs_and_handoff\":\"None\",\"relevant_project_knowledge\":\"None\",\"restated_ask\":\"None\"},\"work_applied\":false}"
+++

# 1 - Intake

## Stage instruction

Start from the unchanged ticket text. Read project configuration, optional rules, relevant Components, linked Requirements, tests, and the opening Git state. Restate the ask, identify bounded scope, and expose uncertainty without requiring prepared scope.

## Inputs

None

## Configured Project Paths

None

## Relevant Project Knowledge

None

## Restated Ask

None

## Initially Affected Repository Area

None

## Facts And Uncertainties

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
[
  {
    "time": "2026-01-01T00:00:00Z",
    "actor": "reference-generator",
    "event": "stage_started",
    "result": "Intake became active."
  }
]
```
