# TASK-b513c8e4 - Preserve local exclusions and protocol finding meaning

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

- 2026-08-13 frame: implement G-16 versioned configured Run-pointer exclusions, G-17 recursive TOML temporal normalization, and G-18 bounded human finding meaning while preserving cumulative G-01 through G-15 work and all planning/review content.
- 2026-08-13 frame: exclude AEGIS Light implementation, managed payload, requirements, knowledge, specs, plans, repository-root `.gitignore`, full suites, `test --impacted`, staging, commits, pushes, branch changes, and network Git; the journal is the only authorized `.agentic` change.
- 2026-08-13 frame: full path is proportionate because the batch changes versioned installation data and externally visible protocol presentation; the explicit instruction to implement now authorizes continuing without the normal frame checkpoint.
- 2026-08-13 frame: remain on the current `master` branch as explicitly required instead of creating an AEGIS Light task branch.
- 2026-08-13 frame: existing governing requirements are PR-COLLAB-002, PR-COLLAB-004, AM-LAYOUT-009, AM-COLLAB-002, PR-PROTO-003, AM-DURABLE-008, PR-PROTO-005, and FS-AUTH-004; none will be edited.
- 2026-08-13 build red G-16: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_install_writes_a_versioned_exclusion tests/test_lifecycle.py::test_relocated_runs_pointer_is_excluded`; exit=1; expected missing behavior=no `.agentic/.gitignore` action exists and an existing project-owned exclusion receives neither local-state rule.
- 2026-08-13 build red G-17: command=`uv run --group dev python -m pytest -q tests/test_project_knowledge_trace.py::test_toml_datetime_in_a_requirement_is_read tests/test_configuration_codecs.py::test_toml_temporal_values_are_normalized_recursively`; exit=1; expected missing behavior=Requirement reads exit 70 and both workspace and codec TOML entry paths retain Python temporal objects.
- 2026-08-13 build red G-18: command=`uv run --group dev python -m pytest -q tests/test_cli_protocol.py::test_human_findings_carry_observation_and_severity`; exit=1; expected missing behavior=the single clipped Finding line omits observation and consequence rather than rendering required semantic fields independently.
- 2026-08-13 build advisory: the first `python .agentic/aegis.py check` reported four journal-header errors because full-AEGIS PR identifiers are not AEGIS Light requirement artifacts; the header was corrected to empty under the explicit no-requirements-change boundary, while the governing identifiers remain in this log.
- 2026-08-13 build green G-16: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_install_writes_a_versioned_exclusion tests/test_lifecycle.py::test_relocated_runs_pointer_is_excluded`; exit=0; result=2 passed, followed by 6 passed across fresh install, clone propagation, relocation, linked worktree, upgrade/removal/reinstall ownership, and interrupted atomic publication selectors.
- 2026-08-13 build green G-17: command=`uv run --group dev python -m pytest -q tests/test_project_knowledge_trace.py::test_toml_datetime_in_a_requirement_is_read tests/test_configuration_codecs.py::test_toml_temporal_values_are_normalized_recursively`; exit=0; result=2 passed, with the malformed-path selector included in the later 6-test focused compatibility run.
- 2026-08-13 build green G-18: command=`uv run --group dev python -m pytest -q tests/test_cli_protocol.py::test_human_findings_carry_observation_and_severity tests/test_cli_protocol.py::test_human_output_preserves_bounded_response_guidance tests/test_cli_protocol.py::test_human_output_is_bounded`; exit=0; result=3 passed, followed by the combined 6-test AEGIS compatibility run.
- 2026-08-13 build static: both WAEGIS and full-AEGIS changed Python/test sets passed `py_compile` and focused Ruff; both package CLI help commands exited 0; exact manifest verification found 59 files and direct payload verification reported 0 findings.
- 2026-08-13 build: advanced to validate without `test --impacted`, requirement links, or AEGIS Light knowledge updates because the explicit batch boundary prohibits those otherwise-normal workflow writes.
- 2026-08-13 validate: final focused WAEGIS lifecycle selection passed 6 and final focused full-AEGIS TOML/human selection passed 6; changed-file compilation, Ruff, both CLI help paths, direct payload verification with 0 findings, byte-exact 59-file Windows manifest generation, and scoped `git diff --check` all exited 0.
- 2026-08-13 validate advisory: `python .agentic/aegis.py check` exited 0 with errors=0 and warnings=82 from cumulative campaign journals, intentionally unlinked full-AEGIS requirements, and pre-existing outside-layout work; no AEGIS Light implementation or artifact was changed beyond this journal.
- 2026-08-13 validate: semantic review confirmed advisory behavior, configured relative pointer truthfulness, project-content preservation, linked-worktree and removal ownership, atomic plan publication, read-only temporal normalization with malformed paths, and independently bounded human finding fields; full AEGIS/WAEGIS suites remain explicitly deferred to the parent campaign.
- 2026-08-13 validate: advanced unpublished to deliver; no stage, commit, push, branch operation, network Git, full suite, or `test --impacted` was performed.
