<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# TASK-4c7e9a13 - Prevent empty test runs from becoming red witnesses

stage: deliver
type: fix
path: quick
requirements:
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged after final proof except for this journal-only delivery record
- [x] correction evidence, diff, exclusions, and intended local-only outcome prepared for presentation
- [x] delivery instruction confirmed by the delegated request: stop without stage, commit, push, branch, or PR actions
- [ ] journal and report included in a delivery commit; explicitly forbidden for this task
- [ ] agreed outcome delivered as a commit or PR; explicitly forbidden for this task
- [ ] close-out committed only after the outcome succeeded; explicitly forbidden for this task

## Log

- 2026-08-13 deliver correction: Cleared full-AEGIS `PR-*` identifiers from the AEGIS Light machine-readable `requirements:` header; their authoritative traceability remains in this log because they are product requirements, not AEGIS Light requirement artifact IDs.
- 2026-08-13 frame: Fix only full-AEGIS execution interpretation so recognized pytest and unittest-discovery exit 5 results cannot become Check red witnesses; exclude AEGIS Light beyond this journal, planning/review files, WAEGIS, the shipped default command, unrelated cumulative remediation, Git publication, and the campaign full suite.
- 2026-08-13 frame: Quick path is proportionate because existing PR-DEFAULT-001, PR-CONFIG-003, PR-CONFIG-010, PR-CONFIG-011, PR-RED-001, and PR-RED-002 already require immediately usable defaults, truthful unknown execution evidence, and actual failing-test red proof without a new interface or dependency.
- 2026-08-13 frame: The delegated instruction fixes the current branch and forbids branch creation, so the journal intentionally records the current `master` checkout.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_empty_test_root_does_not_produce_a_red_witness tests/test_execution_integrity.py::test_pytest_exit_five_does_not_produce_a_red_witness tests/test_execution_integrity.py::test_non_test_exit_five_remains_a_genuine_failure`; exit=1; expected missing behavior=unittest discovery and pytest no-collection both returned `failed` instead of unknown `launch_error`, while the unrelated lint exit-5 control passed.
- 2026-08-13 build green: the focused five-selector command covering shipped unittest empty discovery, empty pytest, unrelated lint exit 5, genuine failing-test red proof, and the five process outcomes exited 0 with 5 passed.
- 2026-08-13 build: The smallest compatible change classifies only recognized pytest and Python unittest-discovery exit 5 as reasoned compatibility `launch_error` evidence with unknown engineering conclusion and `no_tests_ran = true`; the generic process adapter and shipped `.agentic/tests` command remain unchanged.
- 2026-08-13 validate: Semantic review covered runner recognition, arbitrary non-test exit 5, genuine failures, unrelated launch errors, advisory findings, exact evidence persistence, Windows path normalization, documentation, manifest bytes, and preservation of cumulative G-01 through G-12 work.
- 2026-08-13 validate: final focused pytest command exited 0 with 5 passed in 28.89s; `py_compile` with an external cache and focused Ruff both exited 0; `python -B -m aegis --help` exited 0; direct source-template `verify_payload()` returned `()`; targeted `git diff --check` exited 0.
- 2026-08-13 validate: The campaign full suite, AEGIS Light `test --impacted`, and AEGIS Light strict run were deliberately deferred because the delegated scope forbids them; no full-suite conclusion is claimed.
- 2026-08-13 deliver: Candidate remains unstaged and uncommitted on the shared current branch; no branch, reset, restore, clean, network Git, stage, commit, push, or PR action was performed.
- 2026-08-13 build reopen: Parent review confirmed `_command_module` could mistake `-m pytest` or `-m unittest` arguments of an arbitrary launcher for Python module execution, so the task returned from Deliver to Build for one bounded classifier correction and regression.
- 2026-08-13 build red correction: command=`uv run --group dev python -m pytest -q tests/test_execution_integrity.py::test_arbitrary_test_command_with_pytest_arguments_keeps_exit_five_failed`; exit=1; expected missing behavior=the arbitrary `some-tool -m pytest` exit-5 result was misclassified as `launch_error` instead of remaining `failed`.
- 2026-08-13 build green correction: the six-selector focused G-13 command covering both no-tests runners, unrelated lint exit 5, arbitrary `some-tool -m pytest` exit 5, genuine red proof, and generic process outcomes exited 0 with 6 passed in 35.78s.
- 2026-08-13 build correction: `_command_module` now requires a bounded Python launcher basename before accepting `-m`; plain, absolute/venv, versioned, `pythonw`, and Windows `py` launchers remain recognized, while direct pytest executables retain their prior path.
- 2026-08-13 validate correction: a direct six-case classifier matrix returned `[False, False, True, True, True, True]` for arbitrary pytest/unittest tools versus the active interpreter, absolute Windows venv Python, versioned Python, and Windows `py` launcher forms.
- 2026-08-13 validate correction: `py_compile` with an external cache and focused Ruff exited 0; direct source-template `verify_payload()` returned `()`; targeted source, test, documentation, changelog, and manifest `git diff --check` exited 0.
- 2026-08-13 validate correction: The full suite and AEGIS Light `test --impacted` remain deliberately deferred under the delegated boundary; no full-suite conclusion is claimed and excluded scope remains untouched.
- 2026-08-13 deliver correction: Candidate remains unstaged and uncommitted on `master`; no reset, restore, clean, network Git, branch, stage, commit, push, or PR action was performed.
