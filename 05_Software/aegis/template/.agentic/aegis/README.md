# AEGIS payload

This directory is the complete replaceable, manifest-owned AEGIS version 1
product payload. Do not place project rules, configuration, Requirements,
Components, tests, Adoptions, or Runs here; those are repository-owned siblings
below `.agentic/`.

Use `bin/aegis --format json stage-show` to resume the selected Run. The CLI's
operation registry is the sole source of command names, inputs, help, examples,
and dispatch. Host resources under `adapters/` translate the same
`aegis.machine.response` contract and own no workflow transition or approval.

AEGIS is advisory by default. It records findings, failures, timeouts,
cancellations, launch errors, waivers, skips, exceptions, and Delivery outcomes
without performing commit, branch, tag, merge, push, or pull-request actions.
