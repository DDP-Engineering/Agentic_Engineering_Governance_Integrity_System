<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Worked Example - Existing Repository Adoption

> **Date**: July 22, 2026
> **Status**: Current worked example, aligned to AEGIS and WAEGIS.
> **Companions**: `Aegis_Example_Feature.md`,
> `Aegis_Example_BugFix.md`.

## 1. Scenario

A mature target repository exists before AEGIS is introduced.
It already has source code, tests, deployment scripts, and human-authored
documentation, but it does not yet have reliable agentic traceability.

The operator first previews deployment with `waegis adopt <target> --dry-run`,
then runs `waegis adopt <target>`. WAEGIS configures, deploys, and verifies the
payload from outside the target repository. Its job ends at the verified
installation boundary; the in-repository AEGIS adoption workflow begins after
that handoff.

The deployed workflow adds:

- `.agentic/cli/` and `.agentic/tools/` for local workflow commands;
- `.agentic/workflow.toml` for explicit structure and repository-policy modes;
- `.agentic/components.toml` as the durable component map;
- `.agentic/requirements/` for UUID-backed current TOML snapshots;
- `.agentic/knowledge/components/` for workflow-owned component knowledge;
- `.agentic/reports/adoption/` for adoption summaries;
- `.agentic/documents/` for operator references;
- `.codex/`, `.claude/`, `.pi/`, `.opencode/`, and `.qwen/` adapters that all
  point back to the same workflow contract.

The user asks:

```text
Use the agentic adoption workflow for this existing repository.
Do not change application behavior.
Start with adoption-intake and adoption-alignment. After I approve alignment,
perform repo-level discovery and propose the smallest useful component adoption
slice.
Stop at each stage boundary and wait for my approval before advancing.
```

The workflow command placeholder is:

```text
<workflow>
```

Common replacements:

- Windows: `.\.agentic\tools\run.ps1`
- Ubuntu: `bash .agentic/tools/run.sh`

## 2. Adoption Intake Stage

Before repository inspection, the agent runs:

```text
<workflow> config validate --json
<workflow> config show --effective --json
```

It reports all effective restriction modes and active rule counts, distinguishes
AEGIS policy from external safety, and states that this worktree will select the
new adoption run.

The agent reads:

- `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `opencode.json`, `.codex/`, `.pi/`,
  `.opencode/`, and `.qwen/` adapter notes when present;
- `.agentic/workflow.toml`;
- any existing `.agentic/components.toml`;
- root README, build/test instructions, package metadata, and deployment notes;
- source and test directory names, without editing them.

It starts an adoption run:

```text
<workflow> start --kind adoption --statement "Adopt existing repository for agentic workflow use"
```

Then it reports the intended slice before changing adoption artifacts:

```text
Stage: adoption-intake
Adoption scope: repo-level discovery only
Artifacts changed: .agentic/runs/<run-id>/graph.json, .agentic/.workspace/state/current_run
Behavior-change check: No application behavior changes
Needs human: approve adoption alignment
Next prompt options:
- Continue to adoption-alignment
- Restrict discovery to a named subsystem
- Park or abort this adoption run
```

## 3. Adoption Alignment Stage

Before repository discovery, the agent records the no-behavior-change boundary,
the intended discovery depth, assumptions, open questions, and the proposed
first adoption slice:

```text
<workflow> alignment --source "human adoption request" --understanding "Discover the existing repository and propose the smallest baseline-usable component slice without changing application behavior." --scope "in: read-only repository discovery and workflow-owned adoption artifacts; out: product behavior and production configuration" --acceptance "A reviewed component map and one approved adoption slice are produced without runtime changes." --risk low --decision proceed --reason "The no-behavior-change boundary is explicit; discovery remains read-only." --planned-path .agentic/components.toml --planned-path .agentic/reports/adoption
```

Typical alignment stop:

```text
Stage: adoption-alignment
Understanding: map the repository before adopting one approved component
Assumptions: existing build and test commands remain authoritative
Open questions: none
Decision: proceed
Needs human: approve repo-discovery
```

## 4. Repo Discovery Stage

After approval, the agent performs read-only discovery of the existing project.
It identifies:

- development environment: language runtimes, package managers, local commands,
  generated artifacts, and known local setup constraints;
- deploy environment: build pipeline, packaging, runtime services, secrets
  boundaries, infrastructure descriptors, and release commands;
- repository shape: source roots, test roots, CLI/UI/service boundaries,
  scripts, configuration, and documentation roots;
- likely components: paths, responsibilities, entry points, dependencies,
  owners if visible, tests, and deploy impact;
- candidate risks: missing tests, unclear ownership, ambiguous behavior, or
  broad cross-component coupling.

Typical discovery commands are read-only:

```text
<workflow> status
<workflow> audit traceability
<workflow> audit coverage
```

If paths are already known, the agent may run local impact checks:

```text
<workflow> impact src/billing/invoices.py
```

Typical repo-discovery output:

```text
Stage: repo-discovery
Adoption scope: whole repository, read-only
Discovered components:
- Billing: src/billing/**, tests/billing/**
- Checkout: src/checkout/**, tests/checkout/**
- Admin UI: web/admin/**, web/tests/admin/**
Behavior-change check: No application behavior changes
Recommended next slice: Billing only, because it has clear paths and tests
Needs human: approve component-map updates
```

## 5. Component Map Stage

After approval, the agent creates or updates `.agentic/components.toml`.

Example component map:

```toml
[components.billing]
name = "Billing"
paths = ["src/billing/**"]
tests = ["tests/billing/**"]
criticality = "high"
adoption_status = "discovered"
baseline_notes = "Invoice creation, tax calculation, and payment handoff are present. Characterization tests need review."

[components.checkout]
name = "Checkout"
paths = ["src/checkout/**"]
tests = ["tests/checkout/**"]
criticality = "high"
adoption_status = "discovered"
baseline_notes = "Discount and total calculation tests exist, but edge-case coverage is unknown."

[components.admin_ui]
name = "Admin UI"
paths = ["web/admin/**"]
tests = ["web/tests/admin/**"]
criticality = "medium"
adoption_status = "discovered"
baseline_notes = "UI workflows need manual smoke-test mapping."
```

Then the agent checks the map:

```text
<workflow> adoption component-status
<workflow> adoption baseline
```

Typical component-map output:

```text
Stage: component-map
Adoption scope: component inventory only
Artifacts changed: .agentic/components.toml
Behavior-change check: No application behavior changes
Baseline status: components discovered, none baseline-usable yet
Needs human: approve Billing as the first component-adoption slice
```

## 6. Component Adoption Stage

After the human approves a single component, the agent works only inside that
local scope. For the Billing example, the approved scope is:

- `src/billing/**` for read-only behavior characterization;
- `tests/billing/**` for characterization tests;
- `.agentic/requirements/<category>/*.toml` for current snapshots tied to
  observed behavior;
- `.agentic/knowledge/components/Billing.md` for durable component knowledge;
- `.agentic/reports/adoption/` for adoption summaries.

Before changing adoption artifacts, the agent checks scope:

```text
<workflow> adoption scope-check src/billing/invoices.py tests/billing/test_invoices.py
```

The agent then characterizes existing behavior. It may add or improve tests
that describe current behavior, including negative cases and corner cases, but
it must not intentionally change runtime product behavior during adoption.

Example run specs and durable snapshot creation:

```text
<workflow> add-spec --id S-0001 --tag behavior --statement "WHEN a draft invoice has no line items, invoice finalization is rejected with the existing validation error." --status accepted
<workflow> add-spec --id S-0002 --tag behavior --statement "WHEN invoice tax is calculated for a supported region, the total matches the current tax table behavior." --status accepted
<workflow> add-spec --id S-0003 --tag property --statement "WHEN payment handoff fails, the invoice remains unpaid and the current retry state is preserved." --status accepted
<workflow> requirement list --category functional --json
<workflow> requirement create --category functional --priority Must --requirement "A draft invoice with no line items is rejected by the existing validation behavior." --rationale "Preserve observed invoice finalization behavior during adoption." --verification "Automated test" --affected-path src/billing/invoices.py
```

Example check rows:

```text
<workflow> add-check --id C-0001 --cites-spec S-0001 --path tests/billing/test_invoice_finalization.py --command "python -m pytest -q tests/billing/test_invoice_finalization.py"
<workflow> add-check --id C-0002 --cites-spec S-0002 --path tests/billing/test_invoice_tax.py --command "python -m pytest -q tests/billing/test_invoice_tax.py"
<workflow> add-check --id C-0003 --cites-spec S-0003 --path tests/billing/test_payment_handoff.py --command "python -m pytest -q tests/billing/test_payment_handoff.py"
```

The component document records what was learned, not desired future behavior:

```text
.agentic/knowledge/components/Billing.md
```

Typical component-adoption output:

```text
Stage: component-adoption
Adoption scope: Billing
Artifacts changed: tests/billing/**, .agentic/requirements/functional/REQ-FUNC-<uuid>.toml, .agentic/knowledge/components/Billing.md
Behavior-change check: No application behavior changes
Evidence: characterization tests pass against current behavior
Remaining gaps: payment retry timing still needs manual confirmation
Needs human: approve baseline-review
```

## 7. Baseline Review Stage

The agent reviews whether the component is safe enough for normal feature or
fix work.

```text
<workflow> adoption baseline
<workflow> adoption component-status
<workflow> audit traceability
<workflow> audit coverage
```

If the baseline is not met, the agent does not hide that behind a green report.
It records a blocker or recommends another adoption slice.

If the baseline is met, `.agentic/components.toml` can move the component from
`discovered` to `baseline-usable`:

```toml
[components.billing]
adoption_status = "baseline-usable"
baseline_notes = "Core invoice finalization, tax calculation, and payment handoff behavior are characterized by linked tests and component knowledge."
```

Typical baseline-review output:

```text
Stage: baseline-review
Adoption scope: Billing
Baseline status: baseline-usable
Artifacts changed: .agentic/components.toml, .agentic/reports/adoption/billing.md
Behavior-change check: No application behavior changes
Needs human: approve adoption-delivery or choose next component
```

## 8. Adoption Delivery Stage

The agent prepares a delivery summary for the adoption slice:

```text
<workflow> impact src/billing/invoices.py tests/billing/test_invoice_finalization.py
<workflow> working-tree audit
<workflow> audit traceability
<workflow> audit coverage
<workflow> adoption baseline
<workflow> delivery-preflight
<workflow> report
```

The final adoption report should make the handoff obvious:

```text
Stage: adoption-delivery
Adoption scope: Billing
Report: .agentic/runs/<run-id>/report.md
Adoption summary: .agentic/reports/adoption/billing.md
Component map: .agentic/components.toml
Component knowledge: .agentic/knowledge/components/Billing.md
Behavior-change check: No application behavior changes
Next safe work:
- Normal feature/fix work may target Billing
- Checkout remains discovered and should be adopted before behavior-changing work
```

## 9. What This Example Demonstrates

- WAEGIS deploys and verifies the payload before the in-repository adoption run.
- AEGIS adoption starts with intake and alignment, then discovery, never
  implementation.
- Adoption is a separate run kind: `start --kind adoption`.
- The default adoption slice is one component unless a bundle is explicitly
  approved.
- `.agentic/components.toml` is the durable component map.
- `.agentic/knowledge/components/` is the workflow-owned component knowledge
  home.
- Characterization tests describe current behavior before future behavior
  changes.
- Adoption may add tests, requirements, component knowledge, and reports, but it
  must not change runtime application behavior.
- A component below `baseline-usable` should block normal behavior-changing
  feature work until the human approves adoption or accepts the risk.
