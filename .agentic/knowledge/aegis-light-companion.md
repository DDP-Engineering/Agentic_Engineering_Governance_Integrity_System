# AEGIS Light companion

## Purpose

AEGIS Light is a separate, guidance-first companion for repositories that need
durable engineering discipline without local enforcement. Its complete payload
is a small, standard-library-only `.agentic/` tree whose instructions, journals,
requirements, knowledge pages, and advisory checks remain readable without a
service or external state store.

Version 0.4.0 uses six task stages. Build records a reproducible red command,
non-zero exit, and expected missing-behavior reason; validate reconciles and
proves the candidate; deliver presents and publishes it without a misleading
stage-local write-zone claim, and closes out in the delivery commit itself
wherever nothing can fail after that commit.

## Public interface

- `python .agentic/aegis.py init` safely completes deployment into a repository.
- `task`, `req`, and `status` create and resume plain-file work; the commands
  are flat, and `req` accepts a category by folder name or by the abbreviation
  its identifier carries.
- `check` reports format, traceability, scope, secret, and hygiene findings;
  strict failure is an explicit CI-oriented opt-in. Findings alone never make
  it exit non-zero; a usage error does.
- `test --impacted` selects linked regressions and falls back visibly to the
  configured full command when a safe focused set cannot be derived or cannot
  be launched. `--base <revision>` chooses the diff basis.
- `[commands] workdir` runs configured commands below the repository root and
  rewrites substituted test paths to match, so no command needs to change
  directory itself.
- `report` appends a delivery summary to the selected task journal, measured
  from the commit that journal records as its starting point.
- No configured command carries a time limit unless the repository sets one,
  shared through `[commands] timeout` or per command through `[timeouts]`.
- `02_Tools/build_aegis_light_release.py` verifies and packages the payload.

## Key behaviors

- `REQ-NFR-9aec5e3a` - advisory-by-default governance.
- `REQ-PLAT-133b74ac` - portable standard-library execution.
- `REQ-FUNC-1407b21b` - idempotent initialization and ownership preservation.
- `REQ-FUNC-7b02b6ae`, `REQ-DATA-79ebcb34` - durable artifacts and resume.
- `REQ-FUNC-5acb044e` - stable heuristic integrity reporting.
- `REQ-TEST-07679fdc` - focused regression with a safe full-suite fallback,
  including a set too long for the platform to launch.
- `REQ-PLAT-83b50d11`, `REQ-TEST-2bfb7a86` - a configured command working
  directory, with substituted test references rebased onto it.
- `REQ-TEST-5d8f424b` - an oversized focused set reduced to its test files.
- `REQ-TEST-db8d4d31` - a selectable impacted diff basis.
- `REQ-PLAT-2e23ac26` - requirement categories by identifier abbreviation.
- `REQ-UX-e9952f0f` - truthful exit-behavior help for `check`.
- `REQ-FUNC-dcb42072` - close-out folded into a local-only delivery commit.
- `REQ-PLAT-7365bed5`, `REQ-PLAT-19a2faa6` - no shipped time limit, and a
  per-command limit where a repository wants one.
- `REQ-REL-bcd7400b` - a command stopped by its limit reported as unproven.
- `REQ-DATA-71fcf08e`, `REQ-FUNC-791ebe07` - a recorded task base commit, and
  task reporting measured against it.
- `REQ-FUNC-e4f0da51` - truthful command and delivery reporting.
- `REQ-TEST-a67ee43e` - reproducible red-test journal evidence.
- `REQ-FUNC-24ea4f73` - separate validation from publication.
- `REQ-NFR-6f1a6621` - bounded output suitable for small-model sessions.
- `REQ-REL-5fc2eb80` - version-consistent transferable release packaging.

## Files

- `05_Software/aegis-light/template/.agentic/aegis.py` - single-file CLI.
- `05_Software/aegis-light/template/.agentic/AGENTS.md` and `steps/` -
  six-stage lifecycle and adoption instructions.
- `05_Software/aegis-light/template/.agentic/templates/` - artifact starters.
- `05_Software/aegis-light/tests/` - CLI, check, runner, report, structure, and
  release-builder regressions.
- `02_Tools/build_aegis_light_release.py` - release verification and archive.

## Adoption notes

Adopted from the implemented design record under
`00_Planning/AEGIS_LIGHT_PLAN/` on 2026-08-12. The plan marks phases P1-P5
implemented and P6 pilot/calibration remaining; this adoption records the
observed product and does not claim that deferred pilot evidence.
