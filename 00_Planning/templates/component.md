<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Mandatory project knowledge stored under the Components path selected in
.agentic/config.toml. Intake reads relevant Components before source discovery.
Keep this short, current, and more useful than re-reading the whole component.
Update it in place, or delete it when the Component no longer belongs to the
project. Workflow provenance remains in the owning Run.
-->

+++
schema = 1
artifact_type = "component"
id = "COMP-00000000000000000000000000000000"
status = "active" # draft | active
name = "<component name>"
files = ["<repository-relative implementation path>"]
requirement_ids = ["REQ-00000000000000000000000000000000"]
reviewed_at = 2026-01-01T00:00:00Z

[[test_links]]
path = "<configured test root>/<test file>"
selector = "<framework selector, or empty>"
+++

# <component name>

## Purpose and boundary

<State what the component owns and deliberately does not own.>

## Interfaces

<Describe entry points, inputs, outputs, and contracts used by other software.>

## Behaviors and requirements

- `REQ-00000000000000000000000000000000` - <one-line behavior>
- `(gap)` - <observed behavior not yet represented by a Requirement>

## File roles

- `<repository-relative implementation path>` - <role in this component>

## Tests

- `<test path or selector>` - <behavior and implementation files covered>

## Dependencies

- <Dependency and why it exists, or none>

## Known gaps

- <Missing, uncertain, or stale knowledge, or none>

## Drift review

- Behavior current: <yes | no | uncertain>
- Interfaces current: <yes | no | uncertain>
- Dependencies current: <yes | no | uncertain>
- File membership current: <yes | no | uncertain>
- Review finding: <finding label and owning Run/Stage, or none>
