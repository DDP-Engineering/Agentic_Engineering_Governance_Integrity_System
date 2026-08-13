# AEGIS workflow application

## Purpose

This component implements AEGIS use-case policy for Runs, Stages, project
knowledge, traceability, configured execution, Delivery, Adoption, and bounded
resume context. It depends on declared ports and returns protocol-ready results;
it does not implement filesystem, Git, process, or presentation adapters.

## Public interface

- `Dispatcher` resolves a registry operation, enforces machine revision input,
  constructs the application context, and invokes one use case.
- Resource operation modules implement product, workflow, project-knowledge,
  execution, abandonment, and Adoption operations.
- `evaluate_stage_expectations()` evaluates advisory completion facts from
  durable state without I/O or command execution.
- `assemble_stage_resume_context()` builds bounded relevant Run, Stage,
  Requirement, Component, rules, and tool context.
- Repository, workspace, clock, UUID, and hash protocols define every external
  capability consumed by application policy.

## Key behaviors

- `REQ-FUNC-fda66019`, `REQ-REL-360930b1` - eight stages and durable resume.
- `REQ-FUNC-e04edca3` - distinct Run state per ticket.
- `REQ-REL-2c12ed5d`, `REQ-REL-ce2d823d`, `REQ-REL-862a5141` - truthful opening
  snapshots, dirty-work preservation, and no unsupported authorship.
- `REQ-FUNC-0ed3f1b4` - approval-controlled truthful Delivery closure.
- `REQ-FUNC-ba164e6e` - default per-Stage checkpoints, durable continuous
  delegation, choice-preserving handoffs, and Delivery approval provenance.
- `REQ-FUNC-294b8bf7`, `REQ-REL-de2680dc` - resumable Adoption with visible gaps.
- `REQ-TEST-71e4e6b2` - linked impacted tests with explicit full-suite fallback.
- `REQ-FUNC-574eb6e6`, `REQ-FUNC-29090f7f`, `REQ-FUNC-7761f525` - current
  Component knowledge and Requirement-file-test traceability.
- `REQ-TEST-c33c5899` - actual immutable red-before-green evidence.
- `REQ-REL-65d839d8` - stale revisions preserve state and return conflict.
- `REQ-FUNC-428573c5` - bounded relevant Stage context.
- `REQ-REL-7093e21e` - distinct structured operational error classes.

## Files

- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/__init__.py`
  - declares the application package boundary.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/dispatcher.py`
  - resolves and invokes one registered use case.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/product_operations.py`
  - returns bounded help, version, and unavailable-capability results.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/workflow_operations.py`
  - orchestrates Run, Stage, evidence, findings, decisions, and Delivery state.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/project_operations.py`
  - manages current Requirements, Specifications, Components, and traceability.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/execution_operations.py`
  - validates and records configured command execution and fingerprints.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/lifecycle_operations.py`
  - manages normal/exceptional abandonment and incremental Adoption.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/stage_expectations.py`
  - evaluates the full/short Stage expectation matrices.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/resume_context.py`
  - assembles deterministic bounded Stage context.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/ports/__init__.py`
  - declares the port package boundary.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/ports/repository.py`
  - defines installed-repository discovery values and errors.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/ports/services.py`
  - defines injected clock, UUID, and exact-byte hash services.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/ports/workspace.py`
  - defines bounded repository observation, codec, publication, and execution
  capabilities.
- `05_Software/aegis/tests/test_run_stage_workflow.py` - Run and Stage lifecycle.
- `05_Software/aegis/tests/test_stage_completion_expectations.py` - completion
  findings, red/green evidence, and atomic closure.
- `05_Software/aegis/tests/test_stage_resume_context.py` - bounded resume graph.
- `05_Software/aegis/tests/test_project_knowledge_trace.py` - current knowledge
  and trace selection.
- `05_Software/aegis/tests/test_delivery_adoption.py` - Delivery and Adoption.
- `05_Software/aegis/tests/test_machine_revision_contract.py` - concurrency
  tokens and preservation.
- `05_Software/aegis/tests/test_cli_protocol.py` - application result semantics.

## Adoption notes

Adopted from authoritative planning statements and observed passing tests on
2026-08-12. The pre-existing edits in several files were read as current
working-tree behavior and were not modified. No additional suspected defect or
untested load-bearing behavior was identified.
