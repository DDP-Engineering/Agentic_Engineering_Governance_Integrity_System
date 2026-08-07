<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage: baseline-review

Load this module only while in the `baseline-review` stage.

- Run `<workflow> adoption baseline` when available.
- Review whether each adopted component meets the configured baseline, such as
  documented ownership, mapped paths, known gates, and traceability.
- Classify remaining gaps as blocking, follow-up, or accepted legacy risk.
- If `traceability.coverage.mode` is to be enabled for this repository, record
  it as a follow-up gap together with the seeding step: enable coverage, then
  run `<workflow> adoption coverage-waivers` to list every pre-existing module
  with no Active test-linked requirement, and `--write` to append that list to
  `.agentic/requirements/coverage_waivers.txt` with its provenance comment.
  Without it the first enforced audit reports one finding per legacy module,
  none of them caused by the run that hits them. The command reports and
  writes nothing while coverage is disabled, because the schema forbids
  coverable roots in that mode.
- If a future behavior-changing run targets a component below `baseline-usable`,
  stop and recommend a component adoption slice first.
- Stop with baseline status and the next safe feature or adoption prompt.
