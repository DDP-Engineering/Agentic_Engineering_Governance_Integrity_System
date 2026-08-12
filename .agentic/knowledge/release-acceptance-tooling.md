# Release and acceptance tooling

## Purpose

The repository tools build and inspect deterministic offline AEGIS/WAEGIS
release archives and compile a fail-closed release-candidate verdict from
retained acceptance evidence. Packaging and evidence validation are separate:
the validator inventories and checks a campaign but does not execute it.

## Public interface

- `build_aegis_release.py build` assembles one product/platform/runtime edition
  from repository bytes and, for bundled editions, exact locked local runtimes.
- `build_aegis_release.py inspect` validates archive paths, members, inventory,
  digests, identity, edition rules, and runtime metadata before extraction.
- `aegis_acceptance.py catalog` validates and renders the reviewed catalog.
- `init` creates a candidate-bound 58-scenario record with every result not run.
- `validate` and `report` authenticate retained evidence and compile a
  deterministic accepted or incomplete verdict without executing commands.

## Key behaviors

- `REQ-REL-b3f193a8`, `REQ-PLAT-b5a7fd61` - eight offline editions and external
  prerequisite checks.
- `REQ-REL-d204dc36` - exact locked inputs for private bundled runtimes.
- `REQ-DATA-ecc88768`, `REQ-SEC-af5073fb` - complete archive inventories and
  pre-extraction safety/integrity checks.
- `REQ-REL-ed654c7e` - exact AEGIS payload embedding in WAEGIS packages.
- `REQ-TEST-e2b43472` - authoritative acceptance catalog validation.
- `REQ-REL-5bd5c6ae`, `REQ-REL-b2d83e85` - candidate-bound evidence and
  fail-closed verdict compilation.

## Files

- `02_Tools/build_aegis_release.py` - deterministic builder and inspector.
- `02_Tools/runtime_inputs.toml` - checked-in local runtime lock declarations.
- `02_Tools/aegis_acceptance.py` - record validator and verdict compiler.
- `02_Tools/aegis_acceptance_catalog.json` - reviewed 58-scenario catalog.
- `02_Tools/tests/test_release_launchers.py` - package launcher checks.
- `02_Tools/tests/test_aegis_acceptance.py` - evidence and verdict regressions.

## Adoption notes

Adopted from the Product Requirements, Technical Architecture, Acceptance Plan,
and implementation-plan IP-17/IP-18 contracts on 2026-08-12. The catalog parses
with 226 requirements and 58 scenarios, but no campaign evidence was supplied
or executed during adoption; release acceptance therefore remains unclaimed.
Explicit focused regressions were not found for mismatched bundled-runtime lock
inputs or crafted unsafe archive-member inspection, so their requirements keep
empty `linked_tests` and remain visible adoption backlog.
