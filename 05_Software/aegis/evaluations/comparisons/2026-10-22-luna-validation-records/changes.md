<!-- Copyright (c) 2026 DDP Engineering. LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Validation order and durable records

The preceding complete prompt-correction cohort scored 14/25 against the
17/25 current control. It is retained in full. This further bounded correction
uses the same original control and a new complete cohort; it does not retry
or replace individual failed results.

The [diff against the control](baseline-prompt-changes.diff) includes the first
batch's atomicity, contract/implementation, diagram-gate and valid-transition
clarifications. The [additional diff](preceding-prompt-changes.diff) is limited
to observed execution-order and record-completion issues:

- Validate states the full order at entry: finish candidate edits, review,
  final proof, journal-only reporting. A failed command still requires a saved
  limitation and summary within the user's scope.
- Deliver distinguishes a diff since the Git base from a change after proof,
  using available candidate binding before asserting a mismatch.
- Shared record guidance distinguishes a failed exact-text edit from a host
  permission refusal. It requires a permitted, authorized record operation
  before claiming a write was denied, without granting new authority.
- Design repeats the actual checkpoint response order at entry and requires
  repairing a rejected journal edit rather than abandoning the record.
- Diagram guidance retains the canonical three style definitions while leaving
  unchanged nodes unstyled. Newly added test/dependency edges use the added
  convention rather than removed-edge notation.

No scenario, scorer, fixture, runtime, native role prompt or AEGIS Python code
changed. Frame and Build step bytes remain fixed. The payload stays 0.14.0.
Settings remain gpt-6-luna, medium, configured 131072 context, 30-second session
pauses and returned-429 backoff of 60/120/240 seconds. Native output cap is
unexposed; 16000 is the MCP output allowance. One repeat per frozen candidate
cannot establish a general success rate or isolate an individual file's effect.
