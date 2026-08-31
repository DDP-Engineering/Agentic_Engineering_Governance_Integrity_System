<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# REQ-FUNC-9514e017 - Record optional independent review verdicts

## Behavior

Explicit review is controlled by a backward-compatible workspace setting and
is disabled by default. When enabled, validation asks two separate questions
against the same current candidate: whether it complies with approved scope,
requirements, specifications, and design; and whether its implementation is
correct, secure, tested, maintainable, portable, and free of unrequested work.
Both verdicts must be approved before delivery.

Disabling this feature records both verdicts as `disabled` and leaves the round
blank. It never disables semantic validation, tests, strict checks, evidence,
or the existing human delivery checkpoint. Missing, malformed, or stale
verdict evidence is displayed as `not recorded`, never approval.

## Data / interface

```toml
[review]
enabled = false
max_fix_cycles = 2
```

Missing `[review]` means `(False, 2)`. `enabled` accepts only a TOML Boolean.
`max_fix_cycles` accepts an exact non-Boolean integer from 0 through 5; a
missing value defaults to 2 and an invalid value safely permits zero cycles
while `check` warns. The journal stage report appends, in order:

```text
spec_compliance: approved | changes_required | disabled
implementation_quality: approved | changes_required | disabled
review_round: 1..6 | blank
```

`summary`, `brief`, and delivery report project recorded bound values in fixed
order. Any candidate change invalidates both previous verdicts.

## Acceptance

- Legacy configs and journals remain readable with review disabled.
- Each verdict can require changes independently.
- Delivery cannot describe incomplete, stale, malformed, or failed enabled
  verdicts as approved.
- Disabled explicit review leaves all pre-existing validation obligations.
