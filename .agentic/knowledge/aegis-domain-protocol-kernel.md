# AEGIS domain and protocol kernel

## Purpose

This component defines the small immutable values shared across AEGIS and the
declarative version 1 operation catalog consumed by dispatch, CLI construction,
and help. It does not implement workflow use cases, persistence, process
launching, presentation, or host integration.

## Public interface

- `RepositoryPath` and `WorkingDirectory` validate canonical repository-local
  locations used by project configuration and mutations.
- `ProjectConfig` and `ValidationCommand` carry validated project paths,
  configured commands, and advisory policy without depending on codecs.
- `CancellationToken`, `ExecutionRequest`, and `ExecutionResult` form the
  platform-neutral configured-process contract.
- `ProtocolError` and `OperationResult.to_envelope()` define stable structured
  machine results before human or JSON presentation.
- `ArgumentDefinition`, `OperationDefinition`, `MachineRevisionPolicy`, and
  `OperationContext` describe registry entries and executor inputs.
- `ALL_OPERATIONS`, `command_for()`, `operations_for()`, `find_operation()`, and
  `find_command()` expose the canonical cross-product operation catalog.

## Key behaviors

- `REQ-PLAT-888ec3c2` - response paths use canonical repository-relative form
  under `CP-RESPONSE-006`.
- `REQ-PLAT-0badc589` - project configuration identifies relocatable
  repository-owned artifact locations under `PR-CONFIG-002`.
- `REQ-PLAT-cebb1b2b` - project configuration supports multiple test roots
  under `PR-CONFIG-005`.
- `REQ-PLAT-5c1bc460` - validation commands retain unique categorized names
  under `PR-CONFIG-006`.
- `REQ-PLAT-a4fcb436` - each command carries its own working directory and
  timeout under `PR-CONFIG-008`.
- `REQ-PLAT-cff1cf5e` - zero timeout remains unlimited while cancellation stays
  available under `PR-CONFIG-009`.
- `REQ-REL-c20d6246` - process results retain the five outcomes required by
  `PR-CONFIG-010`.
- `REQ-REL-9aaaf19c` - incomplete process outcomes retain an unknown engineering
  conclusion under `PR-CONFIG-011`.
- `REQ-FUNC-29f57326` - a response exposes at most three next actions under
  `CP-MODEL-005`.
- `REQ-FUNC-ba164e6e` - Run creation declares checkpoint or explicitly delegated
  continuous interaction without treating four human choices as next actions.
- `REQ-FUNC-a6f115bd` - supported input cannot escape as an unhandled traceback
  under `PR-PROTO-003`.
- `REQ-PLAT-608b140d` - one registry declaration owns operation metadata under
  `TA-MODULE-003`.
- `REQ-PLAT-248442e0` - every operation has one canonical flat command under
  `PR-PROTO-006`.
- `REQ-REL-2dd22908` - machine mutations use caller revisions under
  `CP-REVISION-002`.
- `REQ-REL-d13d0127` - non-overwriting operations retain the revision exemption
  required by `CP-REVISION-004`.
- `REQ-NFR-bb398def` - runtime dependencies remain stdlib-only under
  `PR-RUNTIME-007`.
- `REQ-NFR-e5017804` - domain and application dependencies point inward under
  `TA-LAYER-001`.

## Files

- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/domain/__init__.py` -
  declares the inward domain package boundary.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/domain/values.py` -
  validates canonical repository paths and working directories.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/domain/configuration.py` -
  defines validated project and command configuration values.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/domain/execution.py` -
  defines cancellation, request, outcome, and engineering-conclusion values.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/domain/results.py` -
  defines structured errors and deterministic machine response envelopes.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/operation_types.py` -
  defines operation arguments, execution context, declarations, and revision
  policy categories.
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/application/operation_registry.py` -
  declares all version 1 operations, product visibility, inputs, help,
  examples, executors, and revision policies.
- `05_Software/aegis/tests/test_configuration_codecs.py` - verifies path and
  project-configuration value contracts through the codec boundary.
- `05_Software/aegis/tests/test_cli_protocol.py` - verifies structured and
  bounded machine envelopes.
- `05_Software/aegis/tests/test_execution_integrity.py` - verifies exact
  process outcomes and cancellation semantics.
- `05_Software/aegis/tests/test_operation_registry.py` - verifies the complete
  catalog, canonical commands, product boundaries, metadata, and examples.
- `05_Software/aegis/tests/test_machine_revision_contract.py` - verifies every
  operation's revision policy.
- `05_Software/aegis/tests/test_architecture.py` - verifies stdlib-only imports,
  inward dependencies, and registry-driven adapters.

## Adoption notes

Adopted from observed source and passing tests on 2026-08-12. Requirement
records are traceability projections of authoritative `PR-*`, `CP-*`, and
`TA-*` statements under `00_Planning/`; they do not replace those sources. No
suspected defect or untested load-bearing behavior was identified in this
bounded component.
