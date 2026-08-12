# WAEGIS lifecycle operator

## Purpose

WAEGIS is the independent operator application that plans and applies local
repository initialization, AEGIS installation, upgrade, and removal. It treats
the AEGIS payload as versioned data and does not participate in engineering
workflow stages or outward Git operations.

## Public interface

- The flat `waegis` CLI and `python -m waegis` expose help, version,
  repository-init, install, upgrade, and remove plan/apply operations.
- Plan operations analyze the target and write an exact operator-owned JSON plan.
- Apply operations require the exact plan digest and unchanged target
  preconditions before publication.
- Target analysis detects existing Git/worktree state, test roots, commands,
  unsafe paths, and project-owned data.
- Independent WAEGIS transactions recover only an already authorized plan.

## Key behaviors

- `REQ-FUNC-c771a1d1`, `REQ-FUNC-629674ff` - install with a prior read-only plan.
- `REQ-FUNC-4e4fb4c9`, `REQ-REL-5b6e4c2c` - upgrade while preserving separated
  project-owned data.
- `REQ-PLAT-c1bc7244`, `REQ-PLAT-0818067b` - no outward Git; local initialization
  is separately planned and authorized.
- `REQ-REL-bf10ed27`, `REQ-REL-7289f5f4`, `REQ-REL-e8675f89` - read-only exact
  plans, digests, and precondition revalidation.
- `REQ-REL-25745fd4` - manifest-authoritative payload ownership.
- `REQ-PLAT-c820ce6c` - detected or complete default integration configuration.
- `REQ-NFR-c6ba4132` - independent publication and recovery.
- `REQ-PLAT-d5dd084c` - locally implemented protocol-envelope parity.

## Files

- `05_Software/waegis/src/waegis/__init__.py`, `__main__.py`, `version.py`, and
  `composition.py` - product identity, entry point, and composition.
- `05_Software/waegis/src/waegis/application/` - lifecycle use cases and registry.
- `05_Software/waegis/src/waegis/domain/` - plan and result values.
- `05_Software/waegis/src/waegis/ports/` - injected service contracts.
- `05_Software/waegis/src/waegis/infrastructure/` - Git initialization, payload,
  target analysis, and independent transactions.
- `05_Software/waegis/src/waegis/interface/` - flat CLI and presentation.
- `05_Software/waegis/tests/test_lifecycle.py` - plan/apply and recovery behavior.
- `05_Software/waegis/tests/test_cli_protocol.py` - process entry and protocol.

## Adoption notes

Adopted from 13 authoritative planning statements on 2026-08-12. The suite
reported 13 passed and one failed: `test_python_module_forwards_process_arguments`
correctly refused startup because the pre-existing dirty full-AEGIS payload no
longer matches its embedded digest. Adoption did not modify that payload or
hide the integrity result.
