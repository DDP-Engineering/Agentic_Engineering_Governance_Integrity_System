<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage: component-adoption

Load this module only while in the `component-adoption` stage.

- Work only inside the approved local component scope or approved bundle
  exception.
- Run `<workflow> adoption scope-check <paths>` for planned touched paths when
  the component manifest is available. Read `enforcement` before the issue
  list: `not-enforced` means the baseline guard is off and only the advisory
  findings apply. `COMPONENT-PATH-UNMAPPED` means no component owns that path;
  `COMPONENT-PATH-NOT-FOUND` means the path is not in the working tree, which
  is expected for a path this run will create and a typo otherwise.
- Add or update component documentation, requirement links, known test commands,
  and adoption notes for the approved slice.
- Record the behavior the adopted code already promises as requirements with
  `<workflow> stage add --category <category>`, one per minted form, then
  `<workflow> stage apply`. This stage is the only place an adoption run can
  create requirements; the route has no requirement stage. They publish as
  `Planned` because an adoption run has no validation stage to activate them.
  Adding none is allowed when the slice promises nothing worth recording yet.
- Preserve behavior. If implementation changes appear necessary, stop and ask to
  switch to an `agentic-development` run.
- Record what was adopted and which gaps remain.
