<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-f5c7ab2d - Correct test discovery and external Python launchers

stage: deliver
type: fix
path: full
requirements:
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [ ] validated candidate confirmed unchanged; otherwise returned to validate
- [ ] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed only after the outcome succeeded

## Log

- 2026-08-13 frame: scope is only G-14 in runnable WAEGIS, allowing indented pytest test methods and deterministically detecting safe conventional test roots one or two levels below the repository root while preserving top-level and multiple-root behavior.
- 2026-08-13 frame: exclusions are AEGIS Light except this journal, all planning and review files, runnable AEGIS and its payload or manifests, framework expansion, whole-tree traversal, blocking policy, unrelated remediation, Git staging/branching/commit/push, and the campaign-wide AEGIS/WAEGIS suites.
- 2026-08-13 frame: full path chosen because generated installation configuration changes observably; the explicit instruction to implement now authorizes continuous work and requires staying on the current master branch instead of creating a task branch.
- 2026-08-13 frame: PR-CONFIG-004, PR-CONFIG-007, PR-SCOPE-009, PR-DEFAULT-001, AC-CONFIG-002, and IP-15 already cover this correction, so no new AEGIS Light requirement, specification, knowledge, or design artifact is proposed.

## Design

- Components: WAEGIS bounded target inspection and generated full-AEGIS project configuration.
- Interface: existing config TOML shape and warning envelope remain unchanged; only confidently selected test roots and pytest detection improve.
- Safety: inspect only repository depth one and two, never descend through symlink or junction directories, reject resolved paths outside the target, and retain deterministic top-level-first ordering.
- Compatibility: retain top-level `tests` before `test`, retain multiple roots, pytest/unittest only, and the existing advisory default when detection remains uncertain.
- Test seam: synthetic Git repositories exercise installed configuration and execute the selected pytest command for class-style and nested-root layouts.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_class_style_pytest_is_detected tests/test_lifecycle.py::test_nested_test_root_is_detected`; exit=1; expected missing behavior=class-style pytest selected unittest and `python/tests` was ignored in favor of `.agentic/tests`, producing two intended assertion failures.
- 2026-08-13 frame expansion: the user batched G-15 into this journal, authorizing full-AEGIS source wrappers and WAEGIS release-wrapper generation while retaining every prior exclusion and the no-stage/no-commit/no-push boundary.
- 2026-08-13 specify expansion: PR-PKG-008, PR-RUNTIME-001, PR-PROTO-001, AC-RUNTIME-001, and AC-PROTO-002 require exact Python 3.12 discovery across compliant launcher names and a parseable machine envelope when no compatible interpreter exists.
- 2026-08-13 design expansion: bundled runtimes remain first, external wrappers probe exact-3.12 `python3.12`, Windows `py -3.12`, then exact-3.12 `python3` and `python`, and an interpreter-independent wrapper response reports `missing_prerequisite` without plaintext stderr when every probe fails.
- 2026-08-13 design expansion: focused extracted-archive tests exercise the canonical AEGIS source wrapper and generated WAEGIS wrapper through a venv-style `python` shim and through an empty PATH, providing behavioral drift coverage without building bundled editions.
- 2026-08-13 build G-15 red: command=`python -m unittest -v tests.test_release_launchers.ReleaseLauncherTests.test_launcher_accepts_a_venv_provided_3_12 tests.test_release_launchers.ReleaseLauncherTests.test_launcher_prerequisite_failure_is_an_envelope`; exit=1; expected missing behavior=both AEGIS and WAEGIS wrappers rejected a PATH-provided exact-3.12 `python` shim with plaintext stderr, and the missing-Python Windows branches returned 0 instead of an exit-5 JSON envelope.
- 2026-08-13 build G-14 green: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_bare_function_tests_are_detected_as_pytest tests/test_lifecycle.py::test_class_style_pytest_is_detected tests/test_lifecycle.py::test_nested_test_root_is_detected tests/test_lifecycle.py::test_test_root_discovery_is_bounded_and_deterministic tests/test_lifecycle.py::test_detection_basis_is_reported tests/test_lifecycle.py::test_install_uses_unittest_for_existing_tests_without_pytest_signal`; exit=0; result=6 passed in 2.84s on the final WAEGIS source and test bytes.
- 2026-08-13 build G-15 green: command=`python -m unittest -v` with the six focused external-launcher, missing-Git, venv-Python, missing-Python, repository-free, and Windows extracted-archive selectors; exit=0; result=6 passed in 6.792s after CRLF normalization and manifest refresh.
- 2026-08-13 build manifest: regenerated the cumulative full-AEGIS payload manifest from checkout-canonical bytes with product_version=1.0.0 and platform=windows; exact builder and runtime verification report 58 owned files and zero findings.
- 2026-08-13 build deferral: AEGIS Light `test --impacted`, the complete AEGIS suite, and the complete WAEGIS suite were not run because the user explicitly deferred campaign-wide suites to the parent task.
- 2026-08-13 validate review: G-14 remains a bounded depth-one/two directory scan with deterministic top-level-first ordering, explicit link/junction/outside rejection, pytest/unittest-only detection, and unchanged advisory configuration shape; G-15 retains bundled precedence and the exact 3.12 pin while making both source and generated wrappers behaviorally equivalent.
- 2026-08-13 validate documentation: WAEGIS, full-AEGIS, release-tool README text and the root Unreleased changelog describe the changed detection and launcher behavior, and the cumulative Windows payload manifest matches all current payload bytes.
- 2026-08-13 validate static: focused `py_compile`, touched-scope Ruff, canonical and generated POSIX `sh -n`, WAEGIS and AEGIS module help, release-builder help, exact builder/runtime payload verification, and scoped `git diff --check` all exited 0.
- 2026-08-13 validate payload CLI caveat: `uv run --group dev python -B -m aegis --repo template --format json payload-verify` exited 1 because repository discovery intentionally requires an installed root-level payload, so the applicable direct source-template builder and runtime verifiers were used and both reported zero findings.
- 2026-08-13 validate platform caveat: extracted Windows external-runtime launchers were executed for AEGIS and WAEGIS, while Ubuntu wrappers received archive-structure and Git-for-Windows `sh -n` checks only; native Ubuntu execution and dependency-bundled archive execution remain unverified because no such environment or locked bundled inputs were supplied.
- 2026-08-13 validate strict: command=`python .agentic/aegis.py check --task TASK-f5c7ab2d --strict`; exit=1 with six pre-existing unknown-product-requirement errors in unrelated `TASK-4c7e9a13` and 55 advisory warnings from pre-existing/excluded/unlinked cumulative work, including expected scope-drift because AEGIS Light requirement edits were forbidden.
- 2026-08-13 validate deferral: no full suite or `check --strict --run` result is claimed; campaign-wide AEGIS/WAEGIS suites remain explicitly deferred to the parent task.
