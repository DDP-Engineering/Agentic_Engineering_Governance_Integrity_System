# AEGIS payload

This directory is the complete replaceable, manifest-owned AEGIS version 1
product payload. Do not place project rules, configuration, Requirements,
Components, tests, Adoptions, or Runs here; those are repository-owned siblings
below `.agentic/`.

Use `bin/aegis --format json stage-show` to resume the selected Run. The CLI's
operation registry is the sole source of command names, inputs, help, examples,
and dispatch. Host resources under `adapters/` translate the same
`aegis.machine.response` contract and own no workflow transition or approval.

Runs default to checkpoint interaction. At each included Stage handoff,
`data.checkpoint` gives hosts the concise summary and four choices to present
before continuing; Delivery substitutes Approve and close. Only a Run created
with structured `continuous` mode and a durable explicit developer instruction
may cross those handoffs without another prompt or record delegated Delivery
approval.

AEGIS is advisory by default. It never launches configured project tests,
lints, audits, or other validation commands. Use `execution-list` to read a
command guide, run it with normal host tooling, and use `evidence-add` to record
the observed outcome. AEGIS records findings, failures, timeouts, cancellations,
launch errors, waivers, skips, exceptions, and Delivery outcomes without
performing commit, branch, tag, merge, push, or pull-request actions.
