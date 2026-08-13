<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

<!--
Task journal. One file per task, at .agentic/tasks/TASK-<id>.md, kept
after delivery as the task's historical record.

The header is the block of "key: value" lines directly under the title.
Keep it exactly in that form — one key per line, no blank lines inside
the block, no comments between the lines — so it stays machine-readable.

  stage         frame | specify | design | build | validate | deliver | done
                (adoption journals: survey | components | close | done)
  type          feature | fix | change | adopt
  path          full | quick
  requirements  comma-separated requirement IDs, empty until specify
  branch        the branch this task is delivered on
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.
-->

# TASK-44bbb4ad — Deliver host-specific AEGIS guidance through WAEGIS

stage: deliver
type: fix
path: full
requirements: PR-HOST-001, PR-HOST-002, PR-WAEGIS-001, PR-WAEGIS-004, PR-WAEGIS-005
branch: master
opened: 2026-08-13

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged except for journal-only delivery records
- [x] validation evidence, diff, exclusions, and outcome presented in the delegated handoff
- [x] delivery publication is explicitly excluded by the parent instructions
- [x] journal included in the shared-tree handoff
- [x] agreed outcome delivered as an uncommitted shared-checkout candidate
- [x] close-out publication omitted because staging, commits, branches, pushes, and PRs are prohibited

## Log

- 2026-08-13 frame: Scope is host-valid Claude, Codex, OpenCode, Pi, and Qwen starter guidance plus WAEGIS create-if-absent lifecycle delivery, canonical payload resources, focused tests, manifest, maintained docs, and changelog; exclusions are planning, AEGIS Light beyond this journal, unrelated dirty work, suites, archives, real-host execution, and all Git mutations.
- 2026-08-13 frame: Full path selected because host file formats and WAEGIS install behavior are externally observable; the delegated brief confirms scope, and its journal-only constraint requires reusing PR-HOST-001, PR-HOST-002, PR-WAEGIS-001, PR-WAEGIS-004, and PR-WAEGIS-005 without creating or editing requirement, spec, design, or knowledge artifacts.
- 2026-08-13 specify/design: Existing full-AEGIS requirements and architecture establish thin host-specific transports, manifest authority for payload ownership, project-data preservation, and no outward Git action; the implementation design maps manifest-owned canonical adapter starters to create-if-absent external destinations.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_host_adapters.py::test_native_host_guidance_routes_resume_through_stage_show tests/test_host_adapters.py::test_native_host_guidance_uses_loader_metadata_and_canonical_starters`; exit=1; expected missing behavior=two failures show absent loader frontmatter, expanded help/stage guidance, corrected Pi path, and canonical starter resources.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_host_guidance_lifecycle_preserves_project_ownership`; exit=1; expected missing behavior=upgrade does not create the missing corrected Pi starter from the payload resource.
- 2026-08-13 build red: command=`uv run --group dev python -m pytest -q tests/test_host_adapters.py`; exit=1; expected missing behavior=adapter contract omits the current `adoption.list` operation from `operations_for("AEGIS")` while the two batch-specific adapter tests pass.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_host_adapters.py`; exit=0; result=3 passed, including loader metadata, canonical synchronization, and the current adapter contract.
- 2026-08-13 build green: command=`uv run --group dev python -m pytest -q tests/test_lifecycle.py::test_install_plan_is_read_only_and_apply_requires_exact_current_plan tests/test_lifecycle.py::test_upgrade_and_remove_use_manifest_ownership_and_preserve_project_data tests/test_lifecycle.py::test_install_delivers_host_guidance tests/test_lifecycle.py::test_upgrade_preserves_edited_host_guidance`; exit=0; result=4 passed.
- 2026-08-13 validate: `python -m py_compile` passed for the changed AEGIS test and WAEGIS lifecycle/test modules; scoped Ruff passed for all three Python files; WAEGIS CLI help completed successfully.
- 2026-08-13 validate: actual WAEGIS payload loading with digest verification completed at version 1.0.0 with 64 files, and lifecycle coverage verified external project-owned copies do not affect payload verification.
- 2026-08-13 validate: registry inspection found 57 total operation definitions and 49 returned by `operations_for("AEGIS")`; `adapters/contract.json` now matches the 49 AEGIS-visible operations exactly without adding the eight WAEGIS-only lifecycle operations.
- 2026-08-13 validate: scoped `git diff --check` passed; semantic review confirmed create-if-absent project ownership, obstruction preservation, legacy Pi non-interference, manifest-only removal, offline stdlib behavior, and no outward Git action.
- 2026-08-13 validate: the explicitly limited campaign skipped AEGIS Light check/impacted execution and all complete or impacted product/tool suites; real Claude Code, Codex, OpenCode, Pi, and Qwen Code loading remains unverified by design.
