---
description: Resume the selected AEGIS Run and follow its current Stage guidance.
---

Resume with `.agentic/aegis/bin/aegis --format json stage-show`. Follow the
returned Stage instruction, common findings, recovery actions, and next actions.
Before any `--input` call, use `help-show` to inspect its
`aegis.machine.input` data contract.

AEGIS never runs project tests, lints, or audits. Read command guidance with
`execution-list`, run the selected command with normal host tooling, and record
the observed outcome with `evidence-add`; attach large output when useful.

Run creation safety is mandatory. Leave `interaction_mode` unset unless the
current developer message explicitly delegates continuous execution without
intermediate prompts. A request to implement, validate, and report the task is
not continuous delegation. For continuous mode, copy the developer's
delegation verbatim into `execution_instruction`; never paraphrase or
manufacture it.

When `data.checkpoint.required` is true, present its outcome, changed artifacts,
evidence, findings, open questions, and proposed handoff. End every non-Delivery
checkpoint with this exact Markdown block so there is one choice per line:

Choose one:

- **Continue**
- **Review**
- **Revise or reimplement**
- **Park**

For Delivery, replace **Continue** with **Approve and close** and keep one
choice per line. Review and Park do not call an operation. After presenting
the checkpoint, make no further tool call and end the turn.
Continue uses `stage-start`; revision uses `stage-set-section` or
`stage-revisit`. Do not infer continuous authority or execute checkpoint next
actions from a general request, host permissions, prior autonomy, silence, or
completed work.

Only a Run whose returned `interaction_mode` is `continuous` and whose durable
execution instruction records explicit developer delegation may cross handoffs
without prompting. Such an agent records Delivery with
`approval_source: continuous_delegation`; checkpoint Delivery approval uses
`approval_source: developer` only after the developer chooses Approve and close.
Do not infer approvals, skips, or waivers. Keep commit, branch, push, merge, and
other outward Git actions outside AEGIS.
