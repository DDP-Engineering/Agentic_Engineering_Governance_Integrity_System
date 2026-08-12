# AEGIS persistence and runtime adapters

## Purpose

This component translates filesystems, Git, codecs, clocks, hashing, UUIDs, and
configured processes into the application ports. It owns safe repository access
and complete before-or-after publication, but it does not decide workflow
acceptability or reinterpret findings.

## Public interface

- `discover_repository()` resolves an installed Git worktree boundary.
- Codec functions parse and canonically render configuration, Requirements,
  Runs, Stages, Components, Specifications, Adoptions, and Abandonments.
- `FileWorkspace` implements bounded reads, Git observation, publication,
  resource loading, payload verification, and configured execution.
- `atomic_replace()`, `TransactionStore`, and `WorkspaceLock` provide durable
  atomic publication, recovery, optimistic concurrency, and local serialization.
- `execute_process()` launches shell-free process groups with concurrent output
  draining, timeout, and cancellation.
- System clock, UUIDv4, and SHA-256 services provide injected runtime facts.

## Key behaviors

- `REQ-REL-6c4a525d`, `REQ-REL-b6f54754`, `REQ-REL-39719eb5` - atomic complete
  publication and interruption recovery.
- `REQ-REL-92820eeb` - stale revisions fail before preparation.
- `REQ-PLAT-47c97052`, `REQ-REL-0b1d9e84`, `REQ-REL-c5bc94c6` - canonical
  encoding, exact-byte hashes, and malformed-byte preservation.
- `REQ-PLAT-1b680071`, `REQ-SEC-91dd1489` - installed-boundary discovery and
  repository path safety.
- `REQ-PLAT-97b168cf`, `REQ-PLAT-4253ae41` - read-only machine-stable Git
  observation without mutation capabilities.
- `REQ-PLAT-ef45ae63`, `REQ-REL-3c9287e0`, `REQ-REL-5858abac` - shell-free
  process groups, bounded cancellation, and deadlock-free output retention.
- `REQ-REL-995954b5` - advisory payload ownership findings.

## Files

- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/__init__.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/codecs.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/discovery.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/payload.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/process.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/publication.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/services.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/transactions.py`
- `05_Software/aegis/template/.agentic/aegis/cli/src/aegis/infrastructure/workspace.py`
- `05_Software/aegis/tests/test_configuration_codecs.py`
- `05_Software/aegis/tests/test_repository_discovery.py`
- `05_Software/aegis/tests/test_transactions.py`
- `05_Software/aegis/tests/test_atomic_publication.py`
- `05_Software/aegis/tests/test_runtime_integrity_contracts.py`
- `05_Software/aegis/tests/test_execution_integrity.py`
- `05_Software/aegis/tests/test_services.py`

## Adoption notes

Adopted from authoritative planning statements and 73 passing focused tests on
2026-08-12. Explicit filesystem symlink/reparse-point escape coverage was not
found for `REQ-SEC-91dd1489`; its empty `linked_tests` is retained as an honest
post-adoption backlog item. Pre-existing workspace changes were not modified.
