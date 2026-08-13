---
name: aegis
description: Continue an AEGIS-governed task using the repository-local CLI.
---

# AEGIS for Codex

Resume with `.agentic/aegis/bin/aegis --format json stage-show`. Follow the
returned Stage instruction, common findings, recovery actions, and next actions.
Before any `--input` call, use `help-show` to inspect its
`aegis.machine.input` data contract.

AEGIS never runs project tests, lints, or audits. Read command guidance with
`execution-list`, run the selected command with normal host tooling, and record
the observed outcome with `evidence-add`; attach large output when useful.

When `data.checkpoint.required` is true, present its outcome, changed artifacts,
evidence, findings, open questions, and proposed handoff. Offer Continue,
Review, Revise or reimplement, and Park, then stop for the developer; Delivery
offers Approve and close instead of Continue. Review and Park do not call an
operation. Continue uses `stage-start`; revision uses `stage-set-section` or
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
