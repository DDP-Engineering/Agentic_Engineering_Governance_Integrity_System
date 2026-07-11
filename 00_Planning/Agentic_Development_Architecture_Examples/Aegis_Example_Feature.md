<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Worked Example - New Feature With AEGIS

> **Date**: June 17, 2026
> **Status**: Draft, aligned to the standalone AEGIS project.
> **Companion**: `Aegis_Example_BugFix.md`.

## 1. Scenario

A target project has adopted the template. The copied project contains:

- `.agentic/cli/` and `.agentic/tools/` for local workflow commands;
- `.agentic/workflow.toml` for roots, write zones, gates, and documentation;
- `.agentic/requirements/` for durable requirement registers;
- `.agentic/documents/` for operator references (`PROMPT_CHEATSHEET.md`, etc.);
- `.codex/skills/` for Codex behavior;
- `.claude/skills/`, `.claude/settings.json`, and `CLAUDE.md` for Claude Code
  behavior;
- `.pi/` for Pi behavior (bridge extension plus a Pi package reusing
  `.agentic/skills/`);
- `opencode.json` and `.opencode/` for OpenCode behavior (native skill
  wrappers, command prompts, and a local guard plugin reusing `.agentic/hooks/`);
- `.qwen/` and `QWEN.md` for Qwen Code behavior (native `settings.json` command
  hooks reusing `.agentic/hooks/`, skill wrappers, and command prompts);
- `AGENTS.md`, `CHANGELOG.md`;
- `05_SoftwareDocu/` with the component documentation template.

The user asks:

```text
Use the agentic development workflow.
Implement feature: Let customers apply a discount code at checkout.
Stop at each gate and wait for my approval.
```

The workflow command placeholder is:

```text
<workflow>
```

Common replacements:

- Windows: `.\.agentic\tools\run.ps1`
- Ubuntu: `bash .agentic/tools/run.sh`

## 2. Intake Gate

The agent reads:

- `AGENTS.md`;
- `.agentic/workflow.toml`;
- existing source, tests, requirements, and documentation indexes.

The human operator may use `.agentic/documents/PROMPT_CHEATSHEET.md` to choose
the next prompt, but the agent's workflow contract comes from `AGENTS.md`,
`.agentic/` config, and the active platform skills/adapters.

It starts a run:

```text
<workflow> start --kind feature --statement "Let customers apply a discount code at checkout"
```

Then it performs read-only orientation:

```text
<workflow> audit traceability
<workflow> audit coverage
<workflow> impact src/checkout/total.py
```

Typical intake output:

```text
Stage: intake
Artifacts changed: .agentic/runs/<run-id>/graph.json, .agentic/current_run
Evidence: none yet
Invariant status: expected blockers because no specs/checks/evidence exist
Needs human: confirm discount semantics
Next prompt options:
- Continue to requirement gate after clarifying percentage/fixed, stacking, and rounding
- Revise scope
- Abort or park this run
```

The human clarifies:

```text
Use percentage-only codes, one code per order, floor total at zero, and round to cents.
Continue to the requirement gate.
```

## 3. Requirement Gate

The agent writes the smallest testable spec items and updates durable
requirements.

Example run specs:

```text
S-0001 [behavior]
WHEN a valid percentage code is applied, the checkout total is reduced by that percentage.

S-0002 [behavior]
WHEN an invalid or expired code is applied, the checkout total is unchanged and the code is rejected.

S-0003 [property]
The checkout total must never be less than zero after discounts.
```

The agent records them:

```text
<workflow> add-spec --id S-0001 --tag behavior --statement "WHEN a valid percentage code is applied, the checkout total is reduced by that percentage." --status accepted
<workflow> add-spec --id S-0002 --tag behavior --statement "WHEN an invalid or expired code is applied, the checkout total is unchanged and the code is rejected." --status accepted
<workflow> add-spec --id S-0003 --tag property --statement "The checkout total must never be less than zero after discounts." --status accepted --threshold "total >= 0"
```

The durable register under `.agentic/requirements/functional.md` receives
planned rows linked to the related component, for example
`src/checkout/total.py`.

If this creates or materially changes a component, the requirement notes include
the expected `05_SoftwareDocu/Checkout_Discounts.md` update.

Stop summary:

```text
Stage: requirement
Artifacts changed:
- .agentic/runs/<run-id>/graph.json
- .agentic/requirements/functional.md
Evidence: none yet
Invariant status: INV-1 and INV-6 still blocking, as expected
Documentation status: component doc update required during implementation
Needs human: approve or revise S-0001..S-0003
```

## 4. Check Gate

After approval, the agent adds tests only. It does not edit source code.

Example checks:

```text
tests/test_checkout_discounts.py::test_valid_percentage_code_reduces_total
tests/test_checkout_discounts.py::test_invalid_code_is_rejected
tests/test_checkout_discounts.py::test_discount_never_makes_total_negative
```

Each check cites its spec ID in the test name, comment, or docstring.

The agent records the checks:

```text
<workflow> add-check --id C-0001 --cites-spec S-0001 --path tests/test_checkout_discounts.py --command "python -m pytest -q tests/test_checkout_discounts.py"
<workflow> add-check --id C-0002 --cites-spec S-0002 --path tests/test_checkout_discounts.py --command "python -m pytest -q tests/test_checkout_discounts.py"
<workflow> add-check --id C-0003 --cites-spec S-0003 --path tests/test_checkout_discounts.py --command "python -m pytest -q tests/test_checkout_discounts.py"
```

Then it runs the focused tests and confirms they fail before implementation:

```text
python -m pytest -q tests/test_checkout_discounts.py
<workflow> record-evidence --kind test-run --result fail --summary "Discount tests fail before implementation" --check-id C-0001
<workflow> record-evidence --kind test-run --result fail --summary "Discount tests fail before implementation" --check-id C-0002
<workflow> record-evidence --kind test-run --result fail --summary "Discount tests fail before implementation" --check-id C-0003
```

Stop summary:

```text
Stage: check
Artifacts changed: tests/test_checkout_discounts.py, .agentic/runs/<run-id>/graph.json
Evidence: red evidence recorded for C-0001..C-0003
Invariant status: INV-1/2/3 are now satisfiable; implementation still pending
Needs human: approve implementation
```

## 5. Implementation Gate

After approval, the agent edits only implementation files and required component
documentation.

Expected edits:

```text
src/checkout/total.py
src/checkout/discounts.py
05_SoftwareDocu/Checkout_Discounts.md
05_SoftwareDocu/README.md
```

The component document follows:

```text
05_SoftwareDocu/component_documentation_template.md
```

The agent uses `$write-component-documentation` in Codex,
`/write-component-documentation` in Claude Code,
`/skill:write-component-documentation` in Pi, the OpenCode native `skill`
tool with `write-component-documentation`, or the `write-component-documentation`
skill in Qwen Code because this is a new component
boundary. Then it runs the focused tests until green:

```text
python -m pytest -q tests/test_checkout_discounts.py
```

It records passing evidence and touched paths:

```text
<workflow> record-evidence --kind test-run --result pass --summary "Discount tests pass after implementation" --check-id C-0001
<workflow> record-evidence --kind test-run --result pass --summary "Discount tests pass after implementation" --check-id C-0002
<workflow> record-evidence --kind test-run --result pass --summary "Discount tests pass after implementation" --check-id C-0003
<workflow> record-change --id CU-0001 --path src/checkout/total.py --path src/checkout/discounts.py --path 05_SoftwareDocu/Checkout_Discounts.md --path 05_SoftwareDocu/README.md
```

Stop summary:

```text
Stage: implementation
Artifacts changed: source files and component documentation
Evidence: green focused tests for C-0001..C-0003
Invariant status: blocking invariants expected to pass after validation
Documentation status: new component document added and indexed
Needs human: approve validation
```

## 6. Validation Gate

Validation is read-only unless the human sends the run back to an earlier gate.

The agent runs:

```text
<workflow> invariants
<workflow> impact
<workflow> audit traceability
<workflow> audit coverage
python -m pytest -q
```

It also runs or manually performs:

```text
$documentation-audit or /documentation-audit
$python-codestyle-audit or /python-codestyle-audit
```

Read-only review checks:

- no tests were weakened or deleted;
- specs still match implementation;
- no secrets are present;
- touched paths are intentional;
- `05_SoftwareDocu/Checkout_Discounts.md` reflects current code;
- `CHANGELOG.md` is updated if the change is release-notable.

Stop summary:

```text
Stage: validation
Artifacts changed: none
Evidence: invariants pass, audits pass, full test suite passes
Documentation status: component docs current
Needs human: approve delivery preflight/report
```

## 7. Delivery Gate

The agent prepares delivery, but does not commit, push, or open a PR unless the
human explicitly approves.

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
Gate results: focused and full tests pass
Traceability status: requirements linked to checks
Documentation status: component documentation current
Risks/open notes: none or listed
Approval needed: commit, push, or PR
```

## 8. What This Example Demonstrates

- The workflow is gate-based and human-steered.
- Requirements are written before tests.
- Tests are red before implementation.
- Implementation includes source and component documentation.
- Validation checks behavior, traceability, scope, secrets, docs, and style.
- Delivery is blocked by deterministic preflight, not by model confidence.
- The generated project carries both run evidence and `CHANGELOG.md`.
