# AEGIS Light companion

## Purpose

AEGIS Light is a separate, guidance-first companion for repositories that need
durable engineering discipline without local enforcement. Its complete payload
is a small, standard-library-only `.agentic/` tree whose instructions, journals,
requirements, knowledge pages, and advisory checks remain readable without a
service or external state store.

## Public interface

- `python .agentic/aegis.py init` safely completes deployment into a repository.
- `task new`, `req new`, and `status` create and resume plain-file work.
- `check` reports format, traceability, scope, secret, and hygiene findings;
  strict failure is an explicit CI-oriented opt-in.
- `test --impacted` selects linked regressions and falls back visibly to the
  configured full command when a safe focused set cannot be derived.
- `report` appends a delivery summary to the selected task journal.
- `02_Tools/build_aegis_light_release.py` verifies and packages the payload.

## Key behaviors

- `REQ-NFR-9aec5e3a` - advisory-by-default governance.
- `REQ-PLAT-133b74ac` - portable standard-library execution.
- `REQ-FUNC-1407b21b` - idempotent initialization and ownership preservation.
- `REQ-FUNC-7b02b6ae`, `REQ-DATA-79ebcb34` - durable artifacts and resume.
- `REQ-FUNC-5acb044e` - stable heuristic integrity reporting.
- `REQ-TEST-07679fdc` - focused regression with a safe full-suite fallback.
- `REQ-FUNC-e4f0da51` - truthful command and delivery reporting.
- `REQ-NFR-6f1a6621` - bounded output suitable for small-model sessions.
- `REQ-REL-5fc2eb80` - version-consistent transferable release packaging.

## Files

- `05_Software/aegis-light/template/.agentic/aegis.py` - single-file CLI.
- `05_Software/aegis-light/template/.agentic/AGENTS.md` and `steps/` -
  lifecycle and adoption instructions.
- `05_Software/aegis-light/template/.agentic/templates/` - artifact starters.
- `05_Software/aegis-light/tests/` - CLI, check, runner, report, structure, and
  release-builder regressions.
- `02_Tools/build_aegis_light_release.py` - release verification and archive.

## Adoption notes

Adopted from the implemented design record under
`00_Planning/AEGIS_LIGHT_PLAN/` on 2026-08-12. The plan marks phases P1-P5
implemented and P6 pilot/calibration remaining; this adoption records the
observed product and does not claim that deferred pilot evidence.
