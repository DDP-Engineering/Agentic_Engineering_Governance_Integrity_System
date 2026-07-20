<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Worked Example - Bug Fix With AEGIS

> **Date**: June 17, 2026
> **Status**: Draft, aligned to the standalone AEGIS project.
> **Companion**: `Aegis_Example_Feature.md`.

## 1. Scenario

The checkout discount feature already exists. The project uses AEGIS
and has active requirement rows under `.agentic/requirements/`.
It may be driven from Codex through `.codex/skills/`, from Claude Code through
`CLAUDE.md` and `.claude/skills/`, from Pi through the `.pi/` adapter, from
OpenCode through `opencode.json` and `.opencode/`, or from Qwen Code through
`QWEN.md` and `.qwen/`; all five adapters point back
to the same `AGENTS.md` workflow contract.

The user reports:

```text
BUG: SAVE10 on a 19.99 order returns 17.98. It should return 17.99.
```

The workflow command placeholder is:

```text
<workflow>
```

Common replacements:

- Windows: `.\.agentic\tools\run.ps1`
- Ubuntu: `bash .agentic/tools/run.sh`

## 2. Intake Gate

The agent starts a fix run:

```text
<workflow> start --kind fix --statement "SAVE10 on a 19.99 order returns 17.98 instead of 17.99"
```

It inspects:

- existing requirements under `.agentic/requirements/`;
- the existing discount tests;
- `src/checkout/discounts.py` and related calculation code;
- `.agentic/knowledge/components/Checkout_Discounts.md`;
- `CHANGELOG.md` for recent related changes.

It runs:

```text
<workflow> audit traceability
<workflow> audit coverage
<workflow> impact src/checkout/discounts.py
```

Triage result:

```text
Existing requirement covers the intended behavior:
REQ-FUNC-012 - Valid percentage discounts reduce checkout total by the
configured rate and round monetary results to cents.

This is a code defect, not a new feature requirement.
```

Stop summary:

```text
Stage: intake
Artifacts changed: .agentic/runs/<run-id>/graph.json, .agentic/current_run
Evidence: none yet
Traceability status: impacted requirement REQ-FUNC-012 found
Needs human: confirm expected rounding rule if ambiguous
Next prompt options:
- Continue to Intent Alignment, then the requirement/check decision
- Revise bug scope
- Abort or park this run
```

## 3. Intent Alignment Gate

The agent records that the request is a local correction to already-contracted
rounding behavior, not permission to redesign checkout discounts:

```text
<workflow> alignment --source "bug report" --understanding "Correct SAVE10 cents rounding from 17.98 to 17.99 for a 19.99 order." --scope "in: existing discount rounding implementation, reproduction test, and component knowledge; out: discount policy changes" --acceptance "The reproduction passes and existing discount tests remain green." --risk low --decision proceed --reason "The expected behavior is covered by REQ-FUNC-012 and no open questions remain." --planned-path src/checkout/discounts.py --planned-path tests/test_checkout_discounts.py
```

Typical alignment stop:

```text
Stage: alignment
Understanding: restore the existing cents-rounding contract
Existing requirement: REQ-FUNC-012
Open questions: none
Decision: proceed
Needs human: approve the recorded fix boundary before requirement confirmation
```

## 4. Requirement Gate

For this bug, the accepted durable requirement already exists. The agent does
not invent a new requirement just because code is broken.

The requirement gate records or confirms the related run spec:

```text
S-0001 [behavior]
WHEN a valid percentage discount is applied to a cents-valued order, the
checkout total is rounded to the expected cent value.
```

The agent records it:

```text
<workflow> add-spec --id S-0001 --tag behavior --statement "WHEN a valid percentage discount is applied to a cents-valued order, the checkout total is rounded to the expected cent value." --status accepted
```

If no existing requirement covered the expected behavior, this gate would add or
update the durable requirement row first. That is the important bug-fix fork:

- covered contract: write reproduction check next;
- missing contract: update requirements before writing the check.

Stop summary:

```text
Stage: requirement
Artifacts changed: .agentic/runs/<run-id>/graph.json
Evidence: none yet
Requirement status: existing durable requirement confirmed
Needs human: approve reproduction check
```

## 5. Check Gate

The agent writes a reproduction test only. It does not edit source code.

Example test:

```text
tests/test_checkout_discounts.py::test_save10_rounds_1999_order_to_1799
```

The test cites `S-0001` and, where useful, the durable requirement ID
`REQ-FUNC-012`.

The agent records the check:

```text
<workflow> add-check --id C-0001 --cites-spec S-0001 --path tests/test_checkout_discounts.py --command "python -m pytest -q tests/test_checkout_discounts.py::test_save10_rounds_1999_order_to_1799"
```

Then it proves the bug is real:

```text
python -m pytest -q tests/test_checkout_discounts.py::test_save10_rounds_1999_order_to_1799
<workflow> record-evidence --kind test-run --result fail --summary "SAVE10 cents rounding bug reproduced: expected 17.99, got 17.98" --check-id C-0001
```

Stop summary:

```text
Stage: check
Artifacts changed: tests/test_checkout_discounts.py, .agentic/runs/<run-id>/graph.json
Evidence: C-0001 red evidence recorded
Invariant status: red-before-green basis established
Needs human: approve implementation
```

If the reproduction test unexpectedly passes, the agent stops and reports that
the bug is not reproduced in the current environment.

## 6. Implementation Gate

After approval, the agent edits only implementation files and required
documentation.

Likely source change:

```text
src/checkout/discounts.py
```

The root cause may be truncation instead of rounding. The implementation fixes
the monetary rounding rule without changing test expectations.

Because this is a material behavior fix for the discount component, the agent
updates:

```text
.agentic/knowledge/components/Checkout_Discounts.md
```

If the fix is user-visible or release-notable, the agent also updates:

```text
CHANGELOG.md
```

The agent runs the reproduction test and linked impact tests:

```text
python -m pytest -q tests/test_checkout_discounts.py::test_save10_rounds_1999_order_to_1799
python -m pytest -q tests/test_checkout_discounts.py
```

Then records evidence and touched paths:

```text
<workflow> record-evidence --kind test-run --result pass --summary "SAVE10 cents rounding reproduction now passes" --check-id C-0001
<workflow> record-change --id CU-0001 --path src/checkout/discounts.py --path tests/test_checkout_discounts.py --path .agentic/knowledge/components/Checkout_Discounts.md --path CHANGELOG.md
```

Stop summary:

```text
Stage: implementation
Artifacts changed: source, reproduction test, component docs, changelog if release-notable
Evidence: C-0001 green evidence recorded
Documentation status: discount component doc updated
Needs human: approve validation
```

## 7. Validation Gate

Validation is read-only unless the human routes back to a previous gate.

The agent runs:

```text
<workflow> invariants
<workflow> impact
<workflow> audit traceability
<workflow> audit coverage
python -m pytest -q
```

It also performs:

```text
$documentation-audit or /documentation-audit
$python-codestyle-audit or /python-codestyle-audit
```

Read-only review checks:

- reproduction test was not weakened after implementation;
- linked existing behavior still passes;
- no unrelated tests were deleted;
- `.agentic/knowledge/components/Checkout_Discounts.md` matches the fixed behavior;
- `CHANGELOG.md` reflects the fix if release-notable;
- no secrets or unexpected files are in the diff.

Stop summary:

```text
Stage: validation
Artifacts changed: none
Evidence: invariants pass, audits pass, full test suite passes
Traceability status: REQ-FUNC-012 linked to reproduction test
Documentation status: component doc current
Needs human: approve delivery preflight/report
```

## 8. Delivery Gate

The agent prepares delivery:

```text
<workflow> registry sync
<workflow> registry audit
<workflow> delivery-preflight
<workflow> report
```

Delivery output:

```text
Delivery preflight: pass
Report: .agentic/runs/<run-id>/report.md
Gate results: reproduction, focused, and full tests pass
Traceability status: impacted requirement verified
Documentation status: component docs current
Risks/open notes: none or listed
Approval needed: commit, push, or PR
```

The commit message can bind the code change back to the workflow evidence:

```text
fix(checkout): round percentage discount cents correctly

Intent: <run-id>
Spec-Touched: S-0001
Requirement-Touched: REQ-FUNC-012
Tests-Added: tests/test_checkout_discounts.py::test_save10_rounds_1999_order_to_1799
```

## 9. What This Example Demonstrates

- A bug fix starts by finding the existing behavior contract.
- If the contract exists, the first new test is a reproduction test.
- If the contract is missing, the workflow returns to requirement authoring.
- The reproduction test must fail before implementation.
- The fix updates source plus component documentation when behavior changes.
- Changelog updates are part of delivery hygiene for release-notable fixes.
- Delivery is blocked by preflight and human approval, not by model confidence.
