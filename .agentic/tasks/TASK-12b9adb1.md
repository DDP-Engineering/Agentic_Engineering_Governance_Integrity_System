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
  parent        optional top-level TASK-id; blank for an ordinary task
  branch        the branch this task is delivered on
  base          the commit this task started from, filled in at creation;
                the delivery report and `check --task` measure the diff
                against it, so leave it alone once it is written. Empty
                when the repository had no history yet.
  opened        YYYY-MM-DD

Header lines are edited in place; log lines are only ever appended.
Keep each log line to one sentence.

Stage report is one replaceable latest snapshot, not an evidence store.
Use plain one-line fields with no fences or bullets inside that section.
stage is the reported stage; current must match the journal header after any
transition. result is in_progress | completed | paused | blocked | skipped.
Keep all observations and decisions in the append-only Log as well.
Leave unknown fields blank; summary prints not recorded, never an assumed pass.
Refresh after work or decisions even if current has not changed.
-->

# TASK-12b9adb1 — Develop portable OpenCode and Codex AEGIS plugins

stage: deliver
type: feature
path: full
requirements: REQ-FUNC-ffc5802a, REQ-FUNC-1ca0ff21, REQ-FUNC-92f78e33, REQ-SEC-16e8890a, REQ-DATA-5e4bf048, REQ-REL-0ef6add6, REQ-PLAT-a3ae118a, REQ-REL-7a97428b, REQ-PLAT-af657d59
parent:
branch: task/agent-plugins
base: 5ff5b0af6abdf64e207f217d023adb501d41fe5c
opened: 2026-09-03

## Done checklist (current stage)

- [x] validated candidate confirmed unchanged; otherwise returned to validate
- [x] validation evidence, diff, exclusions, and outcome presented
- [ ] delivery confirmed by the human
- [ ] journal and report included in the delivery commit
- [ ] agreed outcome delivered, normally a PR
- [ ] close-out committed after the outcome succeeded, or carried by the
      delivery commit where nothing could fail after it

## Log

- 2026-09-03 frame: The user requests portable AEGIS integrations for OpenCode on Linux and Windows, CLI and Desktop, a similar Codex plugin/package, and development in this repository's 05_Software directory.
- 2026-09-03 frame: Use 05_Software/aegis/integrations/opencode and codex for host-specific packages and a shared subdirectory only for implementation actually reused, consistent with the root rule keeping runnable AEGIS implementation under 05_Software/aegis.
- 2026-09-03 frame: In scope are agent/skill prompts, two review roles, native host registration, shared installed-AEGIS invocation and tracked verification, portable local installation/removal, focused behavior tests, and documentation.
- 2026-09-03 frame: Exclude AEGIS workflow/CLI contract changes, changes to the managed downstream template, provider/authentication setup, model pinning, automatic repository adoption, publication, commits, pushes and version assignment; do not test with local models.
- 2026-09-03 frame: Choose the full path because these packages introduce new user-facing integration interfaces, platform behavior and installation/storage boundaries.
- 2026-09-03 frame: No existing task or requirement covers these integrations; the checkout initially had only unrelated untracked .agentic/rtm.csv and .agentic/rtm.md, which remain protected.
- 2026-09-03 frame: Created branch task/agent-plugins from 5ff5b0af6abdf64e207f217d023adb501d41fe5c under the frame instruction; no commit or push was made.
- 2026-09-03 frame: Proposed requirement - OpenCode shall register an Aegis primary agent through its backend configuration for CLI/TUI and Desktop.
- 2026-09-03 frame: Proposed requirement - OpenCode shall expose the five AEGIS workflow commands and eleven bounded tools.
- 2026-09-03 frame: Proposed requirement - Codex shall discover an AEGIS workflow skill from an installable native plugin package.
- 2026-09-03 frame: Proposed requirement - Both integrations shall provide independently scoped specification and implementation review roles with their host's available permission controls.
- 2026-09-03 frame: Proposed requirement - Each integration shall invoke the selected checkout's installed AEGIS CLI and use its existing journal as workflow state.
- 2026-09-03 frame: Proposed requirement - Tracked verification shall preserve process state/output and prevent duplicate adapter-managed runs for one checkout.
- 2026-09-03 frame: Proposed requirement - Installers shall register the selected host integration on Linux and Windows while preserving unrelated configuration and credentials.
- 2026-09-03 frame: Proposed requirement - Package updates/removal shall preserve modified or unowned files and active or uncertain verification jobs.
- 2026-09-03 frame: Proposed requirement - Runtime discovery and package checks shall operate without invoking a model, with explicit reporting of unverified Desktop behavior.
- 2026-09-03 frame: The earlier personal OpenCode adapter is in the Codex workspace outputs/opencode-aegis and remains installed globally; a portable work-in-progress is in outputs/opencode-aegis-plugin, not yet moved into this repository.
- 2026-09-03 frame: The portable prototype contains config-hook registration, runtime discovery and an installer that preserves the main JSON/JSONC configuration; it has not passed its new portability checks.
- 2026-09-03 frame: DEVIATION frame - node outputs/opencode-aegis-plugin/bin/setup.mjs doctor exited 1 because the bundled jsonc-parser UMD entry retained a dynamic require of ./impl/format; repair its ESM bundling and verify during build, with no pass inferred.
- 2026-09-03 frame: Linux test tools were prepared under /tmp/opencode-aegis-check.UAa6wP in Ubuntu-24.04 WSL: Node 22.23.2 verified against upstream SHA256, OpenCode 1.18.18 and Python 3.12.3; no Linux adapter or native Desktop tests have run.
- 2026-09-03 frame: No local or remote model requests were made during this portability work; earlier Windows personal-adapter results are historical evidence only, not proof of these new packages.
- 2026-09-03 frame: Repository checkpoint mode requires presenting this expanded two-host scope and proposed requirements for confirmation before specify/design/build; waiting for that confirmation.

- 2026-09-03 specify: User said proceed, approving the presented full-path two-host plugin scope; no Git publication authority was added.

- 2026-09-03 design: Created nine draft requirements; static check found zero format errors, expected not-yet-created paths and pre-existing journal warnings.

- 2026-09-03 build: Design records separate host registration with shared checkout-local runner; no managed AEGIS payload changes are planned.

- 2026-09-03 build red: command=`node outputs/opencode-aegis-plugin/bin/setup.mjs doctor` in the existing Codex prototype workspace; exit=1; expected packaging failure=JSONC parser UMD dependency cannot load as bundled ESM, before repository implementation import.
- 2026-09-03 build: Anchor cacf33d6a0262a89 records the repository before plugin source import; reuse the pre-existing OpenCode adapter without inventing missing-behavior red evidence for existing functions.
- 2026-09-03 build: DEVIATION build - existing prototype behavior is regression-verified, not represented as newly developed test-first; new installer and Codex behavior receive focused verification.

- 2026-09-03 build: Repaired JSONC bundling using jsonc-parser's ESM entry; the assembled OpenCode doctor found all three agents, five commands and eleven tools without models.
- 2026-09-03 build: Added owned-file lifecycle tests before the new module; initial run exited 1 because the module did not yet exist, so this is interface-development evidence, not a valid behavioral red record.
- 2026-09-03 build red: command=`node --test --test-name-pattern=cancels 05_Software/aegis/integrations/tests/adapter.test.mjs` under Ubuntu WSL with the actual payload; exit=1; expected missing behavior=configured test and its child survived cancellation because AEGIS creates separate process sessions; the fixture killed only its recorded survivors.
- 2026-09-03 build: Added Linux descendant enumeration with process-start-time checks; rerunning the cancellation test passed with no surviving configured test or child.
- 2026-09-03 build: command=`python -m pytest -q 05_Software/aegis/tests/test_agent_integrations.py`; exit=0; 6 tests passed in 26.25s, covering the Node integration groups with actual AEGIS fixtures.
- 2026-09-03 build: command=`node --test 05_Software/aegis/integrations/tests/*.test.mjs` under Ubuntu 24.04 WSL with Node 22.23.2 and Python 3.12.3; exit=0; 15 tests passed, including process-tree cancellation.
- 2026-09-03 build: Native host verification in isolated Windows and Linux configuration directories confirmed OpenCode 1.18.18's three agents/five commands/eleven tools, Codex 0.151.0 install/update/remove and enabled aegis:aegis skill discovery through app-server skills/list.
- 2026-09-03 build: Host validation caught a missing-directory fresh Codex install and an unsupported local-marketplace upgrade command; fixed by creating CODEX_HOME and re-adding the same local catalog before native plugin add.
- 2026-09-03 build: The first skill-discovery harness assertion expected unnamespaced aegis, but the host correctly returns aegis:aegis; corrected the harness and documented the actual name.
- 2026-09-03 build: Same-version Codex update was verified with a changed script in a throwaway package; the installed cache contained the new script, without a product version bump.
- 2026-09-03 build: Native host evidence is in the Codex workspace work/hosts-windows-5/verification.json and WSL /tmp/opencode-aegis-check.UAa6wP/hosts-linux-2/verification.json; all helper servers were scoped to loopback and stopped.
- 2026-09-03 build: Plugin manifest validation passed on the assembled package, skill validation passed, and the new pytest bridge passes ruff; all runtime/model/provider configuration changes stayed inside temporary test homes.
- 2026-09-03 build: DEVIATION build - imported prototype behavior and new declarative skill/registration files do not have fabricated per-requirement behavioral red histories; concrete regression, local-host registration and new cancellation red/green evidence cover the candidate.
- 2026-09-03 build: Added package documentation, root Unreleased entry, component knowledge and configuration source/test paths; the managed payload and project version remain unchanged.

- 2026-09-03 validate: Both host packages and shared runtime implemented with focused Windows/Linux and native registration evidence.

- 2026-09-03 validate: DEVIATION - impacted selection fell back to the full suite because 02_Tools/README.md lacked coverage; actual result was 1 failed, 374 passed, 2 skipped, with the new integration pytest license header missing the required word License.
- 2026-09-03 validate: Added the missing affected path and README layout classifications before round-1 review; no product behavior or managed template changed.
- 2026-09-03 validate: Round 1 candidate 0826593caa6826579bad8566dc025a5b3dcbf1f9e89b0a3fb1e466e1a8f59ed9 received independent spec_compliance=changes_required and implementation_quality=changes_required.
- 2026-09-03 validate: Specification review found untracked runtime cache overrides bypassing active-job protection and native Codex cache edits outside lifecycle ownership; quality review independently confirmed the cache-override flaw.
- 2026-09-03 build: Returned from validate for the first bounded fix cycle, clearing both current verdicts; fixes are limited to recorded lifecycle findings and the observed license-header test failure.
- 2026-09-03 build red: node --test --test-name-pattern="cache changes|untracked cache" 05_Software/aegis/integrations/tests/lifecycle.test.mjs exited 1 with two expected behavior failures: cache movement ignored the requested cache lock and installed runtime accepted an untracked cache override.
- 2026-09-03 build: Installed runtime now refuses untracked cache overrides, lifecycle checks both old/new caches, and focused cache tests passed after the fix.
- 2026-09-03 build: Native Codex registration now records and checks the effective cache contents before update/removal, rejects unowned cache files, and serializes registration with a separate transaction lock; documented partial-registration recovery remains explicit.
- 2026-09-03 build: Fixed the observed license-header text and added native-cache edit/addition/deletion regression coverage; both independent verdicts remain cleared until round 2.
- 2026-09-03 build: Linux native host verification also passed same-version cache refresh in /tmp/opencode-aegis-check.UAa6wP/hosts-linux-3/verification.json, without model requests.

- 2026-09-03 build: python -m pytest -q 05_Software/aegis/tests/test_agent_integrations.py 05_Software/aegis/tests/test_structure.py::test_every_test_file_carries_the_license_header exited 0 with 7 passed in 26.34s.
- 2026-09-03 build: python .agentic/aegis.py test --impacted --base HEAD selected the six integration test references and exited 0 with 6 passed in 26.19s.
- 2026-09-03 build: Linux Node integration suite exited 0 with 18 passed in 7.05s, including old/new cache reservations and native cache ownership regression checks.
- 2026-09-03 build: Isolated native host checks passed on Windows and Linux; modifying the actual installed Codex skill caused both update and uninstall to refuse while preserving bytes, then restored bytes permitted native same-version refresh and removal.
- 2026-09-03 build: Final native evidence is in work/hosts-windows-6/verification.json and /tmp/opencode-aegis-check.UAa6wP/hosts-linux-4/verification.json; no model calls were made and helper servers were stopped.
- 2026-09-03 validate: Re-read the nine requirements and reconciled shared runtime/native ownership behavior with package documentation and the component knowledge page; source plugin and skill validators and focused ruff passed.
- 2026-09-03 validate: DEVIATION - the advisory diff scanner cannot read the 449337-byte untracked vendor bundle under its bounded-file limit; a direct complete-file scan of both vendor modules using all four unchanged AEGIS secret patterns found zero matches, without suppressing the advisory warning.
- 2026-09-03 validate: Native Desktop UI and complete model-driven workflows remain unverified; Windows skips for unavailable symlink creation and differing symlink semantics are reported rather than counted as passes.

- 2026-09-03 validate: Round 2 candidate 0328ce67c59d4fb7aaa92eafe58bde2e5cf3079a15622b9e599b7319a76bf0c4 received independent spec_compliance=changes_required and implementation_quality=changes_required solely for stale OpenCode README cache-override guidance; both functional findings were confirmed resolved.
- 2026-09-03 build: The second and final bounded fix cycle replaces that stale sentence with installer update --cache guidance, preserving executable overrides and distinguishing unpacked packages; no executable behavior changed.
- 2026-09-03 validate: OpenCode registration regression and assembled Codex plugin validation passed after the documentation correction; compileall passed and both verdicts were cleared for round 3.
- 2026-09-03 validate: Round 3 candidate digest is 0edfadf6868f5d9e66f130d8122352826b936840db51acff5ae47599d748d87e across 177 Git-visible files excluding task evidence, delivery output and protected RTM exports.
- 2026-09-03 validate: Preserved the obsolete generated build under ignored 07_Delivery/dist/agent-plugins-before-review and assembled the current packages under 07_Delivery/dist/agent-plugins-unreleased using the builder --output option; these are local artifacts, not publication records.

- 2026-09-03 validate: Round 3 independent spec_compliance=approved and implementation_quality=approved both bind candidate 0edfadf6868f5d9e66f130d8122352826b936840db51acff5ae47599d748d87e; all 177 manifest files matched during both reviews and no actionable findings remain.

- 2026-09-03 validate: Final python .agentic/aegis.py check --task TASK-12b9adb1 --strict --run exited 0; configured full pytest passed in 130.2s and full ruff passed in 0.2s, with 0 errors, 10 warnings and 3 notes.
- 2026-09-03 validate: DEVIATION - accepted nine pre-existing review/delivery warnings on four older journals and one bounded vendor-scan warning covered by a direct complete-file scan; three prior manual-verification notes remain unchanged.
- 2026-09-03 validate: Final text-mode proof records successful commands, not pytest counts; do not infer a final numeric count from the earlier 374-pass/one-failure/two-skip run.
- 2026-09-03 validate: Reviewed the final evolution of 41 non-agentic paths (36 added, five modified, none removed); source, requirements, knowledge, docs and exclusions are current and the reviewed 177-file candidate digest remains unchanged after final proof.
- 2026-09-03 validate: All validation checklist items are satisfied with explicit native Desktop/model exclusions and accepted deviations; advance to deliver as validated, not published.
- 2026-09-03 deliver: Prepared local verified Windows ZIP and Linux tar.gz packages for both hosts, installation guidance and verification evidence; intended diff is 55 files with 49 added and 6 modified, excluding the two protected RTM exports.
- 2026-09-03 deliver: User authorization covers development and local deliverables, not commit/PR publication; no staging, commit, push, registry publication, real-host installation or product version bump occurred.

- 2026-09-03 deliver: Presented stage summary, final validation, accepted deviations, 55-file diff and exclusions; local installation instructions and shareable packages are available, while Git publication awaits approval.

## Rulings

- RULING-001 | date=2026-09-03 | decision=Develop both host integrations under 05_Software in the AEGIS repository | reason=User-selected canonical development location | source=user | supersedes=none
- RULING-002 | date=2026-09-03 | decision=Do not test using local models | reason=Explicit user constraint; use structural and process behavior verification instead | source=user | supersedes=none
- RULING-003 | date=2026-09-03 | decision=Use 05_Software/aegis/integrations for source, 06_SoftwareDocu for deeper documentation, 02_Tools for repository build scripts and 07_Delivery for built packages | reason=Repository folder boundaries | source=repository | supersedes=none

## Design

- OpenCode source lives in integrations/opencode; its config hook registers three agents and five commands, with eleven typed tools invoking the shared adapter (REQ-FUNC-1ca0ff21).
- Codex source lives in integrations/codex/plugins/aegis; its native plugin manifest discovers an AEGIS skill whose local Node bridge invokes the same adapter (REQ-FUNC-92f78e33).
- Codex review definitions are standalone TOML roles installed under CODEX_HOME/agents; plugin prompts also carry review instructions when custom roles are unavailable, without claiming permission isolation stronger than the host provides (REQ-SEC-16e8890a).
- Shared adapter, detached worker, runtime discovery and owned-file lifecycle code live in integrations/shared; package assembly copies shared files into each self-contained package root (REQ-REL-0ef6add6).
- The existing CLI schema 1 and checkout-local journals remain authoritative; the shared cache stores only jobs/logs, not a second task database (REQ-REL-0ef6add6).
- OpenCode installs a loader without editing its JSON/JSONC configuration; Codex uses a private local marketplace through its native CLI, without provider/model/authentication changes (REQ-REL-7a97428b).
- Installation records discovered executable paths for Desktop and uses per-file ownership hashes, conflict checks, backups and active-job checks for lifecycle operations (REQ-REL-7a97428b, REQ-PLAT-af657d59).
- Build outputs go to 07_Delivery via 02_Tools/build_agent_plugins.mjs; maintain one project version read from the existing AEGIS source, without assigning a new product version.
- Reject separate Windows executable implementations: one Node/Python runtime and thin Windows/POSIX launchers keep platform behavior in a single source.
- Tests attach to config hooks, installed package imports, owned-file transactions, runtime probes, shared CLI fixtures, cancellation/duplicate handling and isolated host registration endpoints.
- Add a pytest bridge under 05_Software/aegis/tests so the existing full verification includes Node integration behavior; copy the actual managed payload into temporary test repos only.
- Deeper documentation goes under 06_SoftwareDocu; root/package READMEs and root Unreleased changelog describe the new integration surface.
- No existing component knowledge page covers these integrations, so no architecture update is owed during design; create the accurate component page during validation.

## Handoff

current: deliver
status: waiting for publication approval
next: Present the ready local packages; commit/PR publication requires separate human approval.
must_read: .agentic/tasks/TASK-12b9adb1.md, .agentic/steps/6_deliver.md, 07_Delivery/dist/agent-plugins-0.9.1-unreleased/VERIFICATION.md
blockers: none for local use; no Git publication authority

## Stage report

stage: deliver
result: paused
current: deliver
changed: OpenCode and Codex AEGIS integrations implemented, reviewed and packaged for Windows/Linux.
evidence: Final full test and lint commands passed; strict check exit 0; both independent reviews approved round 3; native Windows/Linux checks passed.
issues: Ten accepted advisory warnings and three prior notes; Desktop/model workflows unverified; publication not authorized.
next: Use the prepared packages; approve commit/PR publication only if desired.
needs_user: yes - the AEGIS delivery checkpoint requires approval before commit/PR publication
spec_compliance: approved
implementation_quality: approved
review_round: 3
