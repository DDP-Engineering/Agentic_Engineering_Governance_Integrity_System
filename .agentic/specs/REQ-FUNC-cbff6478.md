<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-cbff6478 - Bound fix and re-review cycles

## Behavior

Enabled explicit review starts at round one and allows at most
`1 + max_fix_cycles` total rounds. A default of two fix cycles therefore
allows three total review rounds. When either verdict requires changes and a
cycle remains, the agent records the findings, clears both verdicts while the
candidate changes, returns to the appropriate existing stage, fixes only the
recorded findings, reruns relevant proof, increments the round, and performs
both reviews again.

Specification ambiguity or scope expansion returns to the existing human
checkpoint. When either verdict still requires changes on the final allowed
round, validation records `result: blocked` and `needs_user: yes` and does not
advance to deliver. Only an explicit human ruling that changes scope or policy
can reset the counter. The CLI validates and reports state; it never fixes code
or invokes reviewers.

## Data / interface

The supported policy range is zero through five fix cycles, making valid
enabled review rounds one through six. Re-review after any code, test,
documentation, requirement, design, or evidence change consumes a round.
Advisory checks compare recorded round and bound verdicts with the workspace
policy and flag partial pairs, exceeded bounds, or unapproved deliver state.

## Acceptance

- Disabled review has no explicit fix loop and preserves normal validation.
- Any candidate change invalidates both verdicts before another round.
- The loop cannot silently expand scope or run without a configured bound.
- Exhaustion blocks outside deliver with `needs_user: yes`.
