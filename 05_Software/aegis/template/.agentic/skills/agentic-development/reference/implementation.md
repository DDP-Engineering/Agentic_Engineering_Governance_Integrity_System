<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Implementation

Implement only the approved design and current requirements/checks. Route back
through the form control section if a contract, check, or design must change.

Run linked checks first. Run full regression for shared, cross-cutting, or
untraced changes. Record green evidence through the configured external or
managed check path; fixes require prior red evidence.

Complete the implementation form with its generated change-unit ID, summary,
normalized changed paths, documentation effects, and linked evidence. Planned
requirements activate automatically only after successful validation closure.
Apply the form and stop for human approval.

## Routing back from implementation

Set `control.route_to` and `control.route_rationale` in the implementation
form, then `aegis stage apply` and `aegis stage close`. Routing takes effect at
close, not at apply.

A route does not require the evidence this stage would otherwise have produced.
Blockers shaped `<check-id> is missing prior red evidence` and
`<check-id> has no active green evidence` are deferred, and the exact list is
recorded on the `stage.routed` journal event as `blockers_deferred`. Everything
else still applies: an empty `changed_paths`, an unresolved question, or a
`route_to` that does not name an earlier stage all still refuse the close.

Requirement `status` and `created_on` survive the round trip, so re-applying
the requirement stage after routing back does not reset an already-Active
requirement or lose its creation date.
