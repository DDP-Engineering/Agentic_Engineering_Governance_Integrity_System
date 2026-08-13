<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Add the standalone offline acceptance-record catalog and fail-closed release
  evidence validator. Its catalog totals are authoritative regardless of the
  catalog name, and its records and reports identify results as operator-attested
  evidence that the validator did not execute. This is an IP-18 inventory slice,
  not release acceptance.

- Implement the clean-break AEGIS version 1 product through IP-17: the complete
  repository-local workflow and current project-knowledge runtime, thin host
  contract resources, the separate stdlib-only WAEGIS plan/apply lifecycle,
  and reproducible offline archive build/inspection seams with truthful
  unsupplied runtime-input locks. IP-18 release acceptance remains deferred.

- AEGIS Light 0.2.0: two advisory checks complete the catalog at seventeen.
  `stage-zone` reports source edited under a stage whose write zone does not
  include it — the documentation stages (`frame`, `specify`, `design`) and
  adoption's `survey`/`close` write only `.agentic/`, adoption's `components`
  may also add tests, and `build`/`deliver` are unconstrained; zones are
  overridable per stage in a new optional `[zones]` table in `aegis.toml`.
  `manual-verification` recognises a `verification` field that begins
  `Manual:` or `Inspection:` and names a method, recording the requirement as
  verified by hand instead of counting it among the tests still owed. It is a
  NOTE, so it stays printed and counted but can never fail `check --strict`.
  Both defaults live in the payload, so an upgraded repo gets them without
  touching its own `aegis.toml`.

- Replace the retired WAEGIS 1 distribution implementation with WAEGIS 3.0.0:
  a stdlib-only, ownership-aware AEGIS 3 wizard; payload-bearing zipapp; and
  Pythonless Windows/Linux x64 bundles built around that exact zipapp with
  locked CPython inputs, common release identity, and runtime-pointer support.
- Add deterministic hard-kill coverage for every install publication boundary,
  real-payload upgrade interruption coverage, and final Windows/Linux native
  retirement replays with no host Python available.

### Changed

- Define the AEGIS version 1 delivery matrix as eight archives under
  `07_Delivery/dist`: AEGIS and WAEGIS, with external or bundled runtimes, for
  Windows and Ubuntu. External editions check existing Python 3.12 and Git
  without installing them; bundled editions retain private locked runtimes.

- Consolidate offline release archive construction and inspection into the
  standalone stdlib-only `02_Tools/build_aegis_release.py` script, with its
  truthful local-input lock beside it and no separate package or test project.

- Refresh maintained AEGIS documentation for the 3.0 payload, remove obsolete
  deployment-tool compatibility claims and retired historical/planning
  indexes, and keep the operator catalog limited to maintained guidance.
- Exclude planning, repository-documentation, tool-documentation, and deeper
  software-documentation prose from automated content tests while retaining
  behavior tests for executable tools.
- Remove WAEGIS editions, RepoWise, and Git history automation. Mutating flows
  now require clean repositories, explicit complete plans and consent, exact
  pre-write recovery evidence, manifest-last publication, and operator-owned
  staging and commits.
- Align root, AEGIS, WAEGIS, copied-template, and deeper operator documentation
  with the AEGIS 3/WAEGIS 3 ownership, maintenance, upgrade, and external
  RepoWise boundaries.

### Fixed

- Replace full-AEGIS human-mode nested JSON dumps with deterministic labelled
  envelope fields, readable bounded help and scalar values, concise nested-data
  summaries with durable detail references, and actionable finding, artifact,
  error, and next-action lines while leaving machine JSON unchanged.

- Align standalone WAEGIS machine responses with the shared protocol: preserve
  equals-form JSON selection through parse and startup failures, emit strict
  compact UTF-8 JSON with exactly one trailing LF, and map every documented
  protocol error to its explicit exit class.

- Make the existing `run.list`, `requirement.list`, and `component.list`
  pagination navigable through a strictly validated optional decimal cursor
  while preserving stable ordering, the twenty-item page size, and response
  fields.

- Derive exact-operation revision help from the machine-revision policy so
  every required mutation documents `--expected-revision`, the read operation
  that returns it, and a usable example; document the fixed machine input
  envelope plus operation-specific `data` fields and constraints for every
  command that accepts `--input`.

- Add compact stage-specific common findings and structured recovery actions
  to all eight shipped AEGIS workflows, snapshot them per Run, and expose them
  through `stage.show` as advisory guidance without new gates or automatic
  transitions.

- Return Stage sections, evidence, findings, decisions, and escapes exactly
  once in `stage.show`, while preserving bounded omission accounting and the
  unique status, revision, timestamp, attachment, event, and work-state fields.

- Move external-runtime Git prerequisite checks behind the Python application
  boundary so missing Git returns the normal structured AEGIS or WAEGIS
  response with exit code 5, while help and version remain available without
  Git and interpreter discovery stays in the platform wrappers.

- Normalize TOML date, datetime, and time values in Markdown artifact front
  matter, reject non-finite JSON values, and contain presentation failures in
  the structured CLI error protocol.

- Reject Run and Stage mutations against delivered or abandoned Runs even when
  the disposable current-Run pointer still selects them, while preserving
  `run.show` and `stage.show` as read-only inspection paths.

- Detect bare pytest-style functions through a bounded WAEGIS source-text scan
  when no pytest configuration exists, and report the selected test framework
  with its evidence without executing target-project tests.

- Prevent extracted AEGIS and WAEGIS launchers from writing Python bytecode
  into product-owned package paths, so normal use leaves no removal residue.

- Record full-AEGIS Run change attribution at durable mutation boundaries from
  the opening Git snapshot; retain dirty-start state, report later paths and
  repository transitions without claiming authorship, and accept adoption only
  through explicitly scoped observed paths.

- Make `stage-show` return a deterministic, self-contained, profile-bounded
  resume context from the Run, exact requested Stage, relevant Requirement/
  Specification/Component trace graph, optional project rules, and applicable
  configured tool/risk context; report every omission and broken reference
  explicitly, redact secret-like command values, and preserve historical
  `--run`/`--stage` inspection as a revision-free, nonselecting, strictly
  read-only `stage.show` operation.
- Make `stage.show` propose one atomic continuation derived from current Run and
  Stage status, and make missing or stale revision errors propose the matching
  read operation that returns the current revision.
- Evaluate every included full/short AEGIS Stage's completion expectations from
  recorded state and publish unmet section, red-before-green, green-evidence,
  and configured-Validation findings atomically without blocking closure,
  approving or advancing the Stage, or launching configured commands; preserve
  Delivery terminal rules, immutable evidence/history, and read-only Check Git
  comparison behavior.
- Require explicit optimistic-concurrency revisions for applicable JSON-mode
  AEGIS mutations; reject missing tokens as `invalid_input` and stale tokens as
  `state_conflict` without changing target bytes, while preserving read-only,
  creation, human-mode, disposable-context, and exceptional-abandonment
  behavior and rejecting stale execution requests before process launch.
- Preserve completed Stage and Run bytes by rejecting ordinary project,
  attachment, trace-selection, execution, evidence, disposition, and
  abandonment mutations until the Stage is active; reject every unsupported
  Markdown artifact schema as `unsupported_schema`; and require complete,
  internally consistent execution facts for imported automated evidence.
- Require the latest applicable Delivery decision to be approved, fall back to
  the configured full test suite when linked tests or selectors are missing or
  unsafe, and use the real `stage-show` CLI token in all native host guidance
  while preserving `stage.show` as the machine-operation identifier.
- Render and parse Run, Specification, and Component artifacts through their
  canonical human-readable Markdown shapes instead of duplicated JSON state;
  keep Run intent, scope, Stage summaries, events, Requirement/Component links,
  handoff context, and concise opening attribution current; and require useful
  Component file-role and test-purpose documentation.
- Keep the manifest digest for the CRLF Windows launcher consistent across
  source checkouts and WAEGIS delivery, keep generated package metadata outside
  the canonical payload, and isolate Linux interrupt injection from Python's
  process-wait implementation.
- Accept standard linked Git worktree pointer files as WAEGIS lifecycle targets
  without mutating the primary repository's shared local exclusions.
- Restore the AEGIS 3 human-approval boundary in development-stage guidance;
  make `run context` report the authoritative lifecycle next step; and preserve
  distinct waiver targets, disabled guardrail modes, config-repair access from
  subdirectories, and bracket-bearing concrete paths.
- Explicitly load the OpenCode `.mjs` guard plugin; fail closed on trailing
  adapter diagnostics and guard timeouts; route notebook edits across copied
  host adapters; and distinguish governed delivery commands from ordinary Git
  commands while covering executable, prefix, and pipeline variants.
- Bound orphaned gate output without inherited-pipe hangs, preserve all
  PowerShell wrapper arguments through a JSON handoff, and make both installers
  repeatable across bracket-bearing Windows and Git Bash paths.

- Close AEGIS guard bypasses for UTF-8 policy input, unspaced and noclobber
  redirects, target-directory copies, patch moves, notebook edits, nested
  replaced text, workflow-config lookalikes, and delivery commands carrying
  executable-level flags; document that protected reads cover dedicated
  read/search tools rather than shell reads.
- Keep malformed graphs, summaries, component manifests, RepoWise artifacts,
  forms, and journals inside typed recovery paths; make unreadable or
  torn-journal runs abandonable and keep run-list recovery available without a
  valid workflow configuration.
- Restore response, stage-context, routing, coverage-report, argv, evidence-log,
  waiver-staleness, and documentation contracts, including immutable rerun
  logs and the universal `status`/`stage`/`artifact`/`next` envelope.
- Terminate complete gate/check process trees on timeout, release process-local
  locks after setup failures, reject run-ID collisions without overwriting,
  and publish delivery reports atomically with stable UTF-8 output.
- Parse working-tree state with bounded, strict, NUL-delimited Git output;
  preserve configured component-manifest metadata; avoid process-wide umask
  mutation during atomic writes; and retain pilot diagnostics when verification
  returns no artifact.

- Document durable gate output logs and their graph/journal references instead
  of claiming gate output exists only as a bounded journal tail.
- Route incomplete WAEGIS workflow configuration through the designed repair
  and reconstruction paths, require extracted ZIP payload members to be files,
  and avoid a redundant version-mismatch finding when metadata is unreadable.
- Validate installed AEGIS wrappers with the exact interpreter registered by
  each mutation, and re-ask live invalid conditional lists and quick-run path
  thresholds without weakening supplied-answer validation.
- Exclude local Hypothesis, uv, HTML coverage, and coverage-data products from
  payload inventory so development artifacts cannot enter a deployment.
- Propagate reparse-point inspection failures consistently across payload reads
  and repository writes instead of allowing containment checks to continue.
- Let healthy workflow reconfiguration run without resolving an unused payload,
  and direct same-version rebuild and kept-local workflow refusals to re-adopt.

### Removed

- Remove the optional Windows-only ReportLab start-guide PDF generator and its
  local-output contract; the maintained Markdown guide remains canonical.
- Remove dead and redundant WAEGIS implementation branches and refresh the CLI
  module description without changing command behavior.

## [3.0.0] - 2026-08-08

### Added

- Harden the constrained local-model pilot with a deterministic pre-network
  context guard: the exact UTF-8 serialized request is a conservative input
  upper bound, an explicit `max_tokens` allowance is included in each API
  request, and every planned request is preflighted before model discovery.
  An over-budget result makes zero GET/POST calls; later requests compare their
  preflight serialization and revalidate their guard. Pilot evidence also keeps
  the calculation and separates a current attempt's observed outcome from its
  immutable retry lineage.

- Expand the constrained local-model pilot into an append-only, Bonsai-only
  controlled full/quick AEGIS experiment. It preserves model discovery and
  exact request evidence, labels unverified context/thinking claims honestly,
  records one empty transcript per stage, and retains failed attempts.

- Add a constrained, stdlib-only local-model bootstrap pilot harness for
  disposable AEGIS payload copies. It accepts only an explicit loopback `/v1`
  endpoint, records raw API/command telemetry, prevents model-controlled shell
  execution, and preserves earlier evidence by refusing result overwrites.

- Add a payload-owned adapter conformance map and structural regressions for
  direct CLI, Codex, Claude Code, Pi, OpenCode, and Qwen Code. Host wrappers
  now route the canonical bounded bootstrap into shared skills without local
  stage procedures or all-reference context injection.

- Add safe `aegis verify impact [paths-file] --run` execution. The optional
  `[gates.test].impacted_command` is an argv-only focused-test prefix; AEGIS
  appends deterministic, deduplicated selectors with no shell interpolation,
  falls back to every full test command for incomplete or unsafe impact, and
  records focused/full-fallback mode, evidence, output, and journal state
  atomically. A no-command request remains explicit non-zero `nothing-ran`.

- Add an explicit `nothing-ran` execution outcome for managed checks and
  explicitly requested gate runs. When no command launches, the command exits
  non-zero, returns `execution_status`, `executed_count`, and a reason, writes
  an outcome journal event, and creates no passing evidence. Ordinary
  `verify run` keeps disabled gates distinct as `not-enforced` rather than
  falsely reporting an execution failure.

- Add a file-first quick-run check contract. New quick graphs persist a required
  red/green policy, mint and register run-local check definitions during
  implementation, reuse external or managed evidence recording for a real red
  then green result, and reject manual evidence as a substitute. Historical
  schema-3 quick graphs without the field remain readable with explicit legacy
  INV-3 not-applicable reporting.

- Add the versioned, read-only `aegis run context --json` bootstrap contract.
  It provides the current stage's single router/reference and bounded primary
  forms without serializing graph, journal, evidence, requirement, report, or
  configuration history; automated tests enforce its 4 KiB response and 30 KiB
  installable-template bootstrap-pack limits.

- Add a project-agnostic human explanation of the AEGIS adoption installation
  baseline, including every installation-manifest and workflow configuration
  field, the component inventory contract, and the requirements and knowledge
  workspaces and their reusable templates, coverage waivers, and adoption
  reports, plus workflow run records, their stage sequences, and every
  stage-form and validation-summary field, plus hook integrations. Begin
  splitting the combined explanation into lifecycle-oriented guides, starting
  with installation payload and configuration, followed by agent adapters,
  hooks, integrations, and skills, durable governance state, and workflow run
  records, then maintenance, upgrades, transactions, and legacy history.

### Fixed

- Remove the UTF-8 byte-order mark from the root `.gitattributes` so Git parses
  the first comment and applies repository attributes without a warning.

- Remove an unused AEGIS requirement-store import so the complete Ruff audit
  remains clean.

- Make `aegis stage show --json` report an unavailable prepared artifact
  without crashing from a duplicate `artifact` payload argument.

- Keep the canonical fresh-session route bounded. `run context --json` now
  supplies the validating entry point; `config validate` is reserved for
  repaired configuration and `config show` for explicit diagnosis, not routine
  host bootstrap. Adapter regressions now cover root host notes, host READMEs,
  the OpenCode primary agent, all wrappers, and mapped entry files.

- Correct the shared development router so new quick runs require registered
  run-local checks and red-before-green evidence, matching the existing CLI,
  form, and verification contracts.

- Make focused impact testing fall back to the complete test gate whenever any
  requirement matched by a changed path lacks linked tests, preventing a
  linked peer requirement from masking incomplete coverage.

- Keep aggregate `verify run` gate journaling truthful when every gate policy
  is disabled. It now reports and journals those groups only as
  `not-enforced`; the explicit `gate.execution.nothing-ran` event remains
  exclusive to `verify gates` requests that launch zero commands.

- Publish external and managed quick-check evidence with its journal events as
  one rollback-capable transaction. A journal-write failure now restores the
  preceding graph and leaves no active evidence persisted.

- Correct WP2 fresh-session context recovery: `adoption-delivery` now routes to
  the adoption skill and reference, and a missing current form is explicitly
  unavailable with a safe recovery command rather than being advertised as a
  readable artifact. Public lifecycle budget coverage now measures indented CLI
  output after full, quick, and adoption handoffs with 1,000 evidence rows.

- Reconcile check evidence state instead of silently discarding it, closing
  two defects found on a real downstream run. Reapplying the check stage now
  preserves the red/green links and state of every check whose identity and
  command are unchanged, re-deriving them from the active evidence the graph
  still holds (`stage_forms._apply_checks` previously rebuilt every check
  with default `unknown`/`None` link fields, so any reapply orphaned all
  recorded evidence and INV-3 misreported green checks as missing red
  evidence). Recording a check observation now supersedes its older active
  evidence through the shared `check_execution._update_check_states` rule:
  a new record retires prior active records with the same result, and a
  genuine pass additionally retires earlier failed attempts from the
  implementation/validation/delivery stages, so INV-4 stops reporting a
  live regression for a check that later truly passed. The check-stage red
  witness is never retired by a pass, and a new failure never retires an
  older pass, keeping red-before-green and genuine regressions honest. Both
  paths share the new `store.relink_check_evidence` helper, which never
  leaves a link pointing at superseded evidence.

### Changed

- Make stage completion guidance declarative for all standard and adoption
  lifecycle stages. AEGIS now renders the canonical machine and human
  completion checklist as TOML comments in each primary stage form (once in a
  collection stage's `stage.toml`), while standard, adoption, and delivery
  references are tested projections of the same contract. Stage digests now
  hash canonical parsed TOML payloads, so comment-only guidance edits do not
  stale form state or waivers.
- Change the shipped and WAEGIS-proposed stage-form retention default from
  `discard` to `latest`, keeping each stage's final form available for a fresh
  agent session without retaining superseded revisions. Correct the WAEGIS
  adoption proposal, setup and metadata documentation, and stage guidance so
  copied instructions describe only implemented lifecycle and form behavior.
- Let `check_execution.prepare_check_evidence` / `record_check_evidence` accept
  a partial external evidence document. A check whose stage evidence blocker is
  already covered by an active, exactly matching waiver is excused: it gets no
  generated `[[result]]` row, and completeness is measured against the checks
  that remain rather than every imported check. Excused status reuses the
  blockers `stage_forms.stage_blockers` already evaluates
  (`red-before-green:<check-id>` during check,
  `stage:implementation:<check-id>:green-evidence` during implementation), so a
  stale or absent waiver excuses nothing. Recording rejects a row submitted for
  an excused check, and both commands refuse when every check is excused.
  Previously the only way to record real evidence while one check stayed waived
  was to fabricate a result for it.
- Replace `requirements.update_requirement`'s 15-parameter (13 keyword-only)
  signature with a single `patch: RequirementPatch` argument; the three
  `value`/`clear_value` mutual-exclusion checks moved into
  `RequirementPatch.__post_init__`. Updated call sites in
  `requirements.activate_requirement` and
  `stage_forms._activate_green_requirements`. No behavior change.
- Fix `config.py`'s import block to sort alphabetically by module name
  (matching `store.py`/`persistence.py`/`requirement_store.py`/
  `stage_schema.py`), and add a `[tool.ruff.lint.isort]` config
  (`force-sort-within-sections = true`) encoding that convention so
  `ruff check --select I` can verify it.
- Replace the `timeout: int = 300` literal duplicated in `gates.py`,
  `verification.py`, and `check_execution.py` with a single
  `gates.DEFAULT_GATE_TIMEOUT_SECONDS` constant.
- Split `cli.py`'s `_verify_command` into one helper per verification action
  (`_verify_run`, `_verify_status`, `_verify_gates`, `_verify_invariants`,
  `_verify_audit`, `_verify_impact`, `_verify_working_tree`), mirroring the
  existing `_stage_command`/`_check_command` pattern.
- Split `repowise.py`'s `inspect_repowise` into `_missing_required_evidence`,
  `_load_and_validate_artifacts`, `_compute_staleness_warnings`, and
  `_write_discovery_snapshot` helpers.
- Split `config.py`'s `_Parser.parse()` into section-sized private methods
  (`_parse_source_tests_requirements`, `_parse_documentation_components`,
  `_parse_knowledge_reports`, `_parse_traceability`, `_parse_adoption`,
  `_parse_alignment`, `_parse_guardrails`). No behavior change in any of the
  above; parsing/dispatch results and error codes are unchanged.
- Deduplicate repository-path/glob normalization (`config.py`,
  `requirement_store.py`) into shared `paths.normalize_repository_path` /
  `paths.validate_glob`; each module still raises its own typed error with
  unchanged codes and messages.
- Deduplicate the evidence-form TOML load/quote/retire helpers
  (`evidence_forms.py`, `check_execution.py`, and `stage_forms.py`'s
  `_string`) into a shared internal `_form_io.py` module. No behavior change.

### Fixed

- Fix `gates._run_command` reporting a real gate as an unlaunchable
  configuration error (exit 127) when Windows refuses direct exec with
  `PermissionError` — a resolved directory, or a shim `CreateProcess` will not
  launch itself. An argv-eligible command is now retried once through the
  shell; a failing retry still synthesizes 124/127 on the normal evidence path.
  Commands that already required shell mode, and non-Windows platforms, are
  unchanged. Ported from the correction made in the AudioMancer payload.
- Fix `waegis upgrade` reporting "upgrade failed and was rolled back" for every
  apply-phase exception, including two cases where that was untrue: a
  `TransactionCleanupError` raised *after* the commit marker (the payload was
  durably upgraded on disk and nothing was rolled back) and a
  `TransactionRollbackError` (rollback did not complete, so the repository may
  be partially upgraded). `_apply_upgrade_transactional` now raises a typed
  `UpgradeApplyError` carrying the transaction's terminal state, and the
  command reports each outcome distinctly — matching the branch `configure` and
  `repair` already had. A committed-but-cleanup-pending upgrade also journals as
  a completed run instead of a failed one. The `--json` `result` mapping gained
  `applied`, `rolled_back`, and `cleanup_pending`; upgrade exit codes are
  unchanged.
- Fix `SocketTransport.connect` (WAEGIS network probes) hanging well past its
  `timeout` against a stalled DNS server: `socket.create_connection` resolves
  the address before the socket carrying that timeout exists, so `getaddrinfo`
  was unbounded. The TCP attempt now runs on a daemon worker thread joined for
  at most `timeout`, and a resolver stall is reported as `timed_out`. The
  thread is deliberately not pooled: `ThreadPoolExecutor` joins its workers in
  an `atexit` hook, which would move the same stall from the probe to
  interpreter shutdown. The `gaierror` -> `dns_failure`, refused, and TLS
  classifications are unchanged.
- Fix `engine.journal.Journal.flush` staging through a fixed
  `<run-id>.json.tmp` sibling, the same shared-temp-path defect fixed in
  `write_manifest`; it now uses a `uuid4`-suffixed name with
  cleanup-on-failure.
- Report that a `branch-commit` `waegis upgrade` whose apply left files on disk
  did not commit them, naming the branch. The Git commit step runs only for a
  clean apply, so a committed-but-cleanup-pending upgrade previously left the
  new payload uncommitted in the working tree without saying so.
- Fix `payload.manifest.write_manifest` staging through a fixed
  `install-manifest.json.tmp` name shared by every caller, so two concurrent
  WAEGIS invocations against one repository could clobber each other's staged
  bytes and publish a broken manifest through an otherwise atomic
  `os.replace`. It now uses a `uuid4`-suffixed temp name with
  cleanup-on-failure, matching `io.answers.save_answers_file`.
- Fix `io.prompts.ConsoleAsker.ask_field` letting `EOFError` from the secret
  reader (`getpass` at closed/exhausted stdin) escape, contradicting its
  documented `MissingAnswerError` contract and crashing an unattended run with
  a raw traceback. EOF on a secret field now raises `MissingAnswerError(key)`,
  the same as EOF on a plain field.
- Fix `Graph.from_dict` (AEGIS core) to raise the documented `ValueError` when
  `stage_records` is not an object, instead of leaking a raw `AttributeError`.

## [WAEGIS 1.2.0] - 2026-08-01

Component versions in this release: AEGIS payload 2.1.0 (content updated in
place per owner decision — schema and version unchanged), WAEGIS 1.2.0, and
optional bundled RepoWise 0.37.0. The WAEGIS MINOR bump carries the new
public non-interactive decision keys (`accept_failing_gates`,
`adopt_over_existing_install`, `accept_nested_repository`); see the
Migration note below.

### Added

- Add the copied AEGIS merge/rebase playbook for concurrent `.agentic/` state,
  including conflict resolution, post-merge staleness remediation, rebase
  guidance, entry-point links, and an explicit WAEGIS payload-inventory check.
- Add proportional `--quick` profiles for small fix/change runs. The declared
  intake, implementation, validation, and delivery sequence preserves all four
  human closes, journals the collapsed middle stages as `bypassed`, reports
  absent-stage invariants/audits as not applicable, requires real
  implementation evidence, and retains full verification for machinery that
  still runs.
- Add the optional `[quick.changed_paths]` soft advisory with closed
  `disabled|advise` modes and a positive threshold. It ships disabled with an
  effective default of 10 and only recommends restarting a full run when scope
  grows; it never blocks or routes the active run.
- Add exact per-step AEGIS waivers through `waive add` and `waive list`.
  Human-approved reasons, CLI-minted IDs, run-local graph records, separate
  journal events, and blocker-state digests make each exception visible,
  auditable, and stale after relevant content changes.
- Apply active waivers to stage readiness, red-before-green, blocking
  invariants, enforced gates, traceability, coverage, and working-tree
  findings while retaining the underlying failure and rendering it as
  `WAIVED`, never passed. Schema corruption, persistence locks, and stale
  updates remain non-waivable.
- Report a waived failing quality gate in `waegis doctor`'s journal group.
  Payload integrity and verification status are separate dimensions, so a
  repository with zero drift no longer reads as healthy while its latest
  wizard run holds an accepted failing gate. The warning names the gate, the
  command, the run and its timestamp, and the evidence log, and clears only
  when a later run records the same gate command as passing. In `--json` this
  is one further finding object inside the existing `journal` group array; the
  envelope shape, group names, and finding field names are unchanged, and
  journals written before failed-gate evidence existed are read tolerantly.

### Changed

- Document the deployment self-containment contract: every RepoWise
  deployment is exactly one of `source-only`, `external-runtime`, or
  `offline-bundled-runtime`, and a Git clone versus a delivered working
  directory have different self-containment properties whenever bundled
  RepoWise is in play. The WAEGIS README states the contract and which
  edition/answer combination produces each state, `waegis repowise status`
  names the resulting state in human output, the bundled/external interview
  questions state the portability consequence, the template's
  `REPOWISE_INTEGRATION.md` and `GLOSSARY.md` use the same vocabulary, the
  Complete delivery guidance ties it to the existing license/source/notices/
  SBOM/provenance/hash requirements, and the WAEGIS V2 plan's D1 carries the
  same terms forward. Documentation and message-string changes only; no
  schema, CLI flag, or packaging behavior changed.
- Separate general mutation consent from accepting a failing enforced quality
  gate. `--yes` and `--non-interactive` approve the rendered filesystem/Git
  mutation plan only; waiving a gate failure is now its own decision, stated by
  the new `accept_failing_gates` answer key or by an interactive confirmation
  that spells out the consequence. This is enforced structurally rather than
  case by case: a scripted asker will not auto-answer "yes" to any
  confirmation whose default is to refuse, so every present and future
  default-refuse safety question inherits the rule. Two further questions of
  that class gained answer keys so they stay answerable without a console —
  `adopt_over_existing_install` (continue adopting over a repository that
  already carries a valid install manifest) and `accept_nested_repository`
  (create TARGET inside another Git work tree).
  **Migration:** automation that previously relied on blanket `--yes` to carry
  it past one of these questions now fails loudly, naming the missing decision;
  add the corresponding key to its answers file. Absence of a key always means
  refusal, never acceptance. Note one deliberate asymmetry: when an interactive
  console is present, these decision questions are still asked on the console
  even if the answers file carries the key — the decision keys are consumed
  only where no operator can be asked (`--non-interactive`). Because this adds
  public answer keys without removing or renaming anything, it is recommended
  to ship as a MINOR release.

- Canonicalize adoption and upgrade conflict decisions through one shared
  payload normalizer while preserving the public upgrade exit aliases and the
  deprecated always-false `conservative` report field.
- Document the valid-manifest-only upgrade contract, release hygiene checklist,
  and exact prerequisite/adoption workflow for retaining a future
  self-governed AEGIS/WAEGIS release run.
- Make AEGIS graph mutations, evidence-ID allocation, journal publication, and
  same-requirement updates concurrency-safe with bounded repository/run or
  requirement-scoped Windows/POSIX process locks, authoritative reloads, and
  typed stale-update/lock-timeout failures.
- Reuse one stdlib-only atomic writer for graph, journal, requirement,
  active-run pointer, and AEGIS RepoWise JSON state: unique exclusive sibling
  temporaries are flushed and fsynced before atomic replacement, unpublished
  files are cleaned safely, and parent-directory durability is attempted where
  supported.
- Make the WAEGIS zipapp, Core/Complete ZIP and tar.gz archives, embedded
  RepoWise source, normalized SBOM/manifests, release manifest, and checksums
  byte-reproducible for identical declared source/runtime/wheel/epoch and
  Python/uv/zlib toolchain inputs. One SOURCE_DATE_EPOCH/commit/fallback epoch
  now drives explicit portable ordering, timestamps, modes, ownership, ZIP
  creator/compression metadata, and the filename-free gzip header.
- Assign explicit plumbing, mutation, and clone timeouts to all WAEGIS Git
  operations, and centralize repeated probe timeout defaults within their
  owning modules.

### Fixed

- Split configured quality-gate command strings with the host's own path
  syntax. `shlex` defaults to POSIX mode, where a backslash is an escape
  character, so on Windows every native path written unquoted lost its
  separators before the child process started: the gate
  `uv run --directory 05_Software\pkg python -m pytest` reached uv as
  `--directory 05_Softwarepkg` and exited nonzero while the identical suite
  passed by hand from the package root (a latent defect found while
  investigating the AudioMancer gate observation, and distinct from it — the
  deployment's own gate strings used forward slashes and were split
  correctly). Escape processing is now disabled on
  Windows while POSIX quote handling is kept, so a quoted path keeps working
  and its quotes are still removed; on every other host the split is unchanged
  byte for byte. Gate commands run from the repository root as before.
- Make `RUN-POINTER-MISSING` state the recovery command. The worktree-local
  active-run pointer is deliberately Git-ignored while runs under
  `.agentic/runs/` are durable, so losing the pointer leaves the run fully
  recoverable — but the message named neither the run nor `aegis run select`,
  which is the command that recovers it. The guidance now names the exact
  `aegis run select <id>` when a single incomplete run makes the choice
  unambiguous, lists every candidate when it does not, and keeps the previous
  start-a-run advice when there is nothing to select. A corrupt `graph.json`
  no longer hides the runs beside it. The error code and result fields are
  unchanged.

- Retain enough evidence to diagnose a failed quality gate without rerunning
  it. A failing gate command now records its argv, resolved working directory,
  exit code, duration, timeout, and bounded stdout/stderr tails, and writes the
  full output to one log file per failure under the WAEGIS home; the journal
  and `--json` result carry the bounded tails plus the log path and the exact
  reproduction command, so the envelope stays bounded while the evidence stays
  complete. Both output surfaces show the one-line failure, the log path, and
  the reproduction command. Everything persisted is redacted with the
  repository's own configured secret patterns rather than a second list
  invented for the purpose, and a passing gate still records its outcome and
  nothing else. The result distinguishes a clean deployment, a rejected gate
  failure, and a gate failure that was explicitly accepted, using the existing
  outcome vocabulary unchanged.
- Report a failed RepoWise synchronization in `waegis configure`'s human
  output. A run whose configuration succeeded but whose indexing failed
  previously printed only that the configuration was updated and verified,
  which reads as an unqualified success; it now states the synchronization
  status, the concise error, the isolated log path, and the resume command —
  the same facts the JSON result already carried. A successful synchronization
  adds no output.
- Prevent Click's Windows-only pre-parser from expanding WAEGIS-managed
  RepoWise exclusion globs into surplus positional paths when matches exist;
  use literal option binding for wildcard-capable values, bypass the Complete
  batch launcher during managed execution, preserve paths with spaces, and
  restore RepoWise's unsolicited project-local MCP/VS Code setup before
  artifact validation and receipt creation.
- Persist the workflow answers in the install manifest when adopting an
  existing repository, so a later configuration no longer has to restate the
  whole workflow to request one setting. New and adopt now store one
  allowlisted, canonically-normalized answer shape, which keeps adoption-only
  answers and RepoWise runtime data out of the durable configuration.
  Configuration of an install whose manifest records no answers reconstructs
  them from the existing valid workflow file and writes the completed set back
  after a successful run, so an earlier adoption is repaired in place without a
  new command or flag. Regenerating from an already-generated file now replaces
  the conditional baseline-threshold key and stage write-access table instead of
  emitting a second copy of each.
- Synchronize current AEGIS 2.1.0 / WAEGIS 1.1.0 template branding and schema
  documentation, enforce structural version parity and an empty downstream
  changelog, and exclude Python bytecode plus interpreter/test/coverage caches
  from payload copying and release staging.
- Normalize validated external check results, summaries, and output-log paths
  before persistence; enforce the same stage, captured-mode, and non-empty
  imported-check preconditions for preparation and recording; and reject an
  incomplete, duplicate, unknown, malformed, command-mismatched, or
  result/exit-status-inconsistent evidence document before graph mutation.
- Restrict the AEGIS CLI blocked-response boundary to explicit configuration,
  run-resolution, stage-operation, command-input, requirement, persistence, and
  RepoWise integration errors so incidental `ValueError`, process-control
  exceptions, and parser exits retain their normal diagnostic behavior.
- Reject option-like, control-character, and invalid Git clone/branch inputs
  before execution, use the documented clone option terminator, and scrub
  embedded clone credentials from Git failure results.
- Require explicit approval for every WAEGIS mutation, including programmatic,
  JSON, non-interactive, transaction-recovery, journal, Git, and RepoWise
  paths; preserve read-only dry runs/no-op plans, fail closed on EOF or an
  exhausted scripted confirmation queue, and retain process-control semantics.
- Move RepoWise policy, runtime metadata, and install-manifest updates into one
  persistent WAEGIS transaction with verified policy/runtime writes, a
  manifest-last barrier, truthful rollback/cleanup reporting, idempotent crash
  recovery, and no-op detection.
- Validate runtime locks as closed schemas; stream runtime downloads through
  exclusive unique siblings with digest-before-replace cleanup; prevalidate and
  deterministically materialize runtime link graphs; and verify exact internal
  archive schema, target, safe membership, regular-file type, and digests while
  rejecting duplicates, case collisions, undeclared files, encryption, links,
  and special entries before atomic artifact publication.
- Reject manual-evidence import before a current AEGIS stage is prepared, bound
  requirement-ID collision retries, and normalize malformed nested graph
  records to the graph loader's typed schema-error contract.
- Preserve the missing-executable probe response while capturing other process
  launch `OSError` variants, and require the stable AEGIS JSON response keys
  during WAEGIS smoke verification.

### Removed

- Remove the two unreachable legacy upgrade implementations, the unused private
  smoke verifier duplicate, dead conservative classification plumbing, stale
  helper/exit documentation, confirmed unused imports/locals, and 75 ignored
  Python bytecode files from the copied-verbatim template tree.

### Security

- Authenticate closed-schema WAEGIS transaction state with a protected
  WAEGIS-home HMAC key and separately authenticated repository/operation
  ownership records; bind backups by generated name, size, and SHA-256; reject
  legacy or forged state, unowned storage, links, junctions, reparse points,
  unsafe paths, and destination type substitution before target mutation.
- Serialize WAEGIS recovery and transaction application with repository-scoped
  cross-process locks, restore backups by exact-path atomic replacement, and
  clean only individually validated transaction objects without recursive
  deletion.

## [2.1.0] - 2026-07-29

Component versions in this release: AEGIS payload 2.1.0, WAEGIS 1.1.0, and
optional bundled RepoWise 0.37.0. Workflow and run-graph schema remain 3;
the RepoWise integration file uses schema 1.

### Added

- Add an optional, process-isolated RepoWise discovery bridge. AEGIS validates
  policy, receipts, graph/state schemas, hashes, Git HEAD, and worktree
  fingerprints before copying normalized proposals into a durable
  run-local repository-discovery snapshot.
- Add WAEGIS `repowise status` and `repowise sync`, interactive and
  answers-file lifecycle configuration, deterministic and loopback-only Ollama
  profiles, advisory/required enforcement, progress journaling, interruption
  handling, and exact resume commands.
- Add Core and Complete WAEGIS delivery editions. Complete packages can carry a
  native, locked RepoWise 0.37.0 sidecar, exact source archive and commit/tag
  provenance, hashes, notices, SBOM, package manifest, and unpacked-size data.
- Add native Complete packaging for Windows x64 and Linux x64, clean exact-tag
  source validation, binary-wheel-only dependency installation, path traversal
  protection, disk-space checks, project-local sidecar installation, and
  offline network guards. Cross-platform companions must identify the same
  RepoWise tag and commit; stale Complete artifacts are rejected.
- Pin a separate Python 3.12.13 runtime for the RepoWise sidecar so the locked
  NumPy 1.26.4 native wheels remain installable; WAEGIS Core stays on its
  existing Python 3.13 runtime.
- Generate the corresponding RepoWise source ZIP directly from the pinned Git
  commit so Windows and Linux Complete artifacts remain byte-identical despite
  host line-ending filters.

### Changed

- Release AEGIS 2.1.0 and WAEGIS 1.1.0 while retaining WAEGIS compatibility
  `>=2.0.0,<3.0.0`.
- Make RepoWise an optional advisory discovery provider rather than
  authoritative AEGIS state. Human-entered adoption discovery is never
  silently replaced, and only explicitly `required` stale/unavailable data
  blocks repository discovery.
- Keep target installation and managed bundled indexing fully offline: no pip,
  uv, GitHub, PyPI, telemetry, editor registration, agent setup, or external
  update service is invoked.
- Treat the mutable RepoWise policy as generated project configuration in the
  WAEGIS install manifest. Repair reconstructs it from non-secret metadata;
  explicit `new` or committed `adopt` selection records it in a separate,
  policy-only commit while the default disabled Core path remains unchanged.
- Refuse Complete-to-Core use while a project selects the bundled sidecar;
  reconfigure the project to external or disabled first.

### Security

- Constrain managed bundled RepoWise network access to loopback and reject
  non-loopback Ollama endpoints.
- Preserve RepoWise as a separately installed AGPL sidecar and require exact
  corresponding source and notices in Complete delivery artifacts.

## [2.0.0] - 2026-07-29

Component versions in this release: AEGIS payload 2.0.0, WAEGIS 1.0.0.

### Added

- Add the authoritative design stage between requirement and check, including
  proposal revisions, requirement/document digests, approval invalidation, and
  `INV-10 Solution design`.
- Add schema-3 run-local stage forms with captured retention and check-execution
  policy, atomic collection import, automatic IDs, reconstruction, routing, and
  access-change controls.
- Add external and managed deterministic check evidence, generated manual
  evidence/supersession forms, red-before-green enforcement, and automatic
  requirement activation at successful validation closure.
- Add build, typecheck, lint, test, and security gate groups with independent
  disabled/enforce modes and fixed execute-all ordering.
- Add consolidated verification covering impact selection, enabled gates,
  invariants, traceability, coverage, working-tree review, and validation
  summary generation.
- Add an offline ReportLab generator for the maintained new-project PDF guide.

### Changed

- Replace the flag-heavy CLI with the hard-break grouped interface:
  `run`, `stage`, `requirement`, `check`, `evidence`, `verify`, `delivery`,
  `adoption`, and `config`.
- Make generated forms the input boundary for intent, alignment, requirements,
  design, checks, implementation, validation, delivery, access changes,
  routing, and evidence.
- Keep requirement commands read-only and move all mutations into the
  requirement stage.
- Merge regression guidance into checks, implementation, validation, and
  regression traceability, including contract variants, parity, stale-state
  cleanup, rollback, boundaries, concurrency, and idempotency.
- Release WAEGIS 1.0.0 with schema-3 generation, all five gate groups, AEGIS
  compatibility `>=2.0.0,<3.0.0`, and cross-major upgrade rejection.
- Update planning architecture, examples, template documents, agent adapters,
  the start-guide PDF, and all five maintained presentation decks for the
  eight-stage AEGIS 2.0 contract.

### Removed

- Remove all AEGIS 1.x command aliases, expert flags, schema-2 migration,
  legacy graph loading, manual activation commands, and compatibility shims.
- Remove cross-major WAEGIS upgrades.

## [1.4.1] - 2026-07-28

Component versions in this release: AEGIS payload 1.4.1, WAEGIS 0.6.0. The two
are versioned independently; this changelog tracks the project as a whole.

### Fixed

- **Codex guards were entirely absent in every installed repository.**
  `.codex/hooks.json` carried the `_legal`/`_comment*` annotation keys used
  across the other adapters' JSON, but Codex parses that file with a strict
  deserializer accepting exactly two top-level keys, `description` and `hooks`.
  An unknown key does not get ignored — it rejects the whole file, so Codex
  registered **no hooks at all**: the read guard, write-zone guard, secret scan,
  shell-write guard, delivery preflight, and evidence recorder were all silently
  inactive. Tool calls were not blocked; they were never inspected. The hook
  wiring itself was always schema-valid and is unchanged.

  The defect survived because nothing validated adapter configurations against
  the hosts that actually parse them: the payload tests asserted AEGIS semantics
  over `json.loads` output, and `waegis doctor` checked only that the adapter
  *directory* existed. Valid JSON in a present directory is not a loadable host
  config, and both checks reported healthy over a repository with no enforcement.

### Added

- **`waegis doctor` gained `runnability.adapter-configs`**, which parses each
  strictly-deserialized adapter config and verifies its top-level keys against
  the set its host accepts. Severity is `fail`, ranking with the missing-hook
  check rather than the informational adapter-directory one: a config the host
  discards removes enforcement rather than degrading it.
- **`waegis upgrade` now reports hook configs that need re-trust.** Codex binds
  per-hook trust to the file's content hash, so any rewrite of
  `.codex/hooks.json` — including a correct payload upgrade — returns its hooks
  to "review required" and stops them running until re-reviewed in the `/hooks`
  panel. A successful upgrade could therefore turn enforcement off while every
  other signal reported health. The human report ends with an action-required
  block naming the affected files, and the `--json` result gains an additive
  `hook_configs_needing_retrust` key.
- **Payload test `test_strict_host_configs_use_only_supported_top_level_keys`**,
  which blocks the original defect at the source, plus a companion check keeping
  annotation keys `_`-prefixed in the configs whose hosts do tolerate them.
- **`.codex/README.md`**, the adapter reference the Codex directory never had.

### Changed

- `.agentic/hooks/README.md` documents the two Codex gates that stand in front
  of the guards — project trust and per-hook review — alongside the existing
  Node-on-PATH and launch-directory fail-opens. All four share a shape: the
  guards are absent, nothing reports it, and the session looks healthy.
- `.pi/README.md` no longer claims project trust is "the one behavioral
  difference from the Codex and Claude adapters". Codex requires both a project
  trust step and a per-hook review; only Claude Code needs neither.

## [1.4.0] - 2026-07-25

Component versions in this release: AEGIS payload 1.4.0, WAEGIS 0.5.0. The two
are versioned independently; this changelog tracks the project as a whole.

### Added

- **Requirement companion specs (`spec_ref`).** Requirement snapshots carry an
  optional `spec_ref` naming a companion spec file (data structures, interface
  and message formats, exact dialog and copy text, example payloads, worked
  acceptance examples) so an implementation cannot drift from what was analysed,
  while the `requirement` sentence stays a single testable behavior.
  `requirement create/update` gained `--spec-ref`/`--clear-spec-ref`; a
  non-empty reference must resolve to an existing file at write time, and a
  later-deleted target is reported as `REQ-SPEC-MISSING` by `audit
  traceability`. Ships `.agentic/requirements/spec_template.md`.
- **`resume` command.** A read-only bootstrap brief — current and next stage,
  intent, alignment, spec items, checks, recent evidence, and the run's cited
  requirements resolved with their `spec_ref` — so a fresh agent session
  continues an existing run without prior chat context.

### Changed

- The requirement snapshot schema gains a required `spec_ref` key (empty string
  when unused); snapshots written before this change are rejected rather than
  migrated. The `schema_version` stays `1` (nothing is released yet, so it is
  bumped only when live data must migrate).
- The `agentic-development` and `agentic-adoption` skills are restructured into
  thin routers that dispatch to per-stage modules under `reference/`, so a
  session — including a resumed one — loads only the current stage's guidance
  rather than the whole workflow, cutting the always-loaded footprint for
  small-context runners.

## [1.3.0] - 2026-07-25

Component versions in this release: AEGIS payload 1.3.0, WAEGIS 0.4.0. The two
are versioned independently; this changelog tracks the project as a whole.

### Added

- **Shell write guard (`guard_shell_write.py`).** A new AEGIS pre-tool hook
  extends the configured write-zone and protected-path policy to file writes
  performed through the shell — output redirection (`>`/`>>`), `tee`,
  `cp`/`mv`/`install`, `dd of=`, and `sed -i` — closing a gap where
  `guard_write_zone.py`, wired only to the dedicated editing tools, never saw a
  repository file written from a shell command. It enforces only on targets
  inside the repository (writes to `/tmp`, `/dev/null`, and other external paths
  are untouched) and is wired into every adapter's shell matcher (Claude Code,
  Codex, Qwen Code, OpenCode, Pi). Best-effort by design; the delivery
  working-tree audit remains the backstop.
- **`waegis doctor` hook-launcher check.** A new `runnability.hook-runtime`
  finding warns when `node` does not resolve on `PATH`. Every adapter launches
  the guards through `node .agentic/tools/run_hook.mjs`, and a host treats a
  hook that could not launch as a non-blocking error, so a missing Node.js
  silently disables enforcement. The requirement is now documented in
  `.agentic/hooks/README.md`.

### Changed

- `INV-7` (clean secrets) also scans `git diff --cached`, catching a secret in a
  staged-but-never-committed file in a repository with no `HEAD` yet.
- `secret_scan.py` serializes scanned input with `ensure_ascii=False`, so a
  configured pattern can match a secret containing non-ASCII characters.

### Fixed

- The working-tree audit only splits a Git status entry on `" -> "` for
  rename/copy records, so a file whose own name contains that sequence is no
  longer misparsed.
- The `run.sh` wrapper folds a registered runtime path to forward slashes, so a
  Windows interpreter path resolves reliably under Git Bash.

### Removed

- The unused `aegis.paths.is_allowed_path` helper; policy consumers compose
  `relative_to_root`/`contained_relative_path` with `matches_pattern` directly.

## [1.2.0] - 2026-07-24

Component versions in this release: AEGIS payload 1.2.0, WAEGIS 0.3.0. The two
are versioned independently; this changelog tracks the project as a whole.

### Changed

- Require a resolvable test (or an explicit manual method) for every non-Retired
  requirement, not only `Active` ones. The traceability audit previously raised
  `REQ-NO-VERIFICATION` only for an `Active` requirement that lacked a resolvable
  linked test and a `Manual:`/`Inspection:` verification, so a `Planned`
  requirement could sit untested indefinitely and still pass delivery preflight —
  a drafted contract with no test was invisible to regression gating.
  `audit traceability` now applies the same rule to every non-Retired
  requirement (`Planned` and `Active`); `Retired` requirements and explicit
  `Manual:`/`Inspection:` verification remain exempt. Because delivery preflight
  already blocks on any traceability finding, a release now requires every
  non-Retired requirement to carry at least one resolvable test or a manual
  method.
- Strengthen requirement-stage guidance for completeness and atomicity: one
  requirement per behavior, decompose the feature before drafting, write failure
  and boundary behaviors as their own requirements, enumerate and trace
  acceptance criteria, cover the applicable requirement categories, and report a
  requirement-stage review checklist at the gate.

## [1.1.0] - 2026-07-23

Component versions in this release: AEGIS payload 1.1.0, WAEGIS 0.3.0. The two
are versioned independently; this changelog tracks the project as a whole.

### Changed

- Declare and check the Node requirement that was previously only implied. The
  adapters use `node:`-prefixed builtin imports, `import.meta.url`,
  `pathToFileURL`, and nullish coalescing, so a real minimum has always
  existed, but nothing stated or verified it: on an interpreter too old to
  parse them a guard failed at launch, which every host reads as a
  *non-blocking* hook error and lets the tool call through unguarded. The Pi
  package manifest now declares `engines.node >= 18` and `waegis doctor`
  reports anything below that floor.

  `prereq.node` stays a warning rather than an error, deliberately. The wizard
  stops at the first non-green step with no override, so failing here would
  make AEGIS undeployable for an OpenCode-only project — OpenCode runs the
  guard plugin in its own runtime and needs no system Node, and a Pi project
  always has one because Pi is installed with `npm`. Nothing about the
  installed payload is wrong without Node either: install it afterwards and
  every hook works with no repair or re-run. The severity therefore reflects
  "recoverable later" while the message now carries the security consequence —
  that the Claude Code, Codex, and Qwen Code adapters run their tool calls
  completely unchecked until it is resolved — which is what an operator needs
  in order to act. The runtime requirements are documented with the same
  distinction.
- Normalize recorded change-unit paths at the point they are recorded.
  `record-change` now accepts repository-relative or absolute-inside-repository
  paths, stores one canonical repository-relative form, drops repeated
  spellings of the same path, and refuses a path that resolves outside the
  repository.
- Give `waegis new` and `waegis adopt` the same crash safety the mutating
  lifecycle commands already had. Both now run their payload copy inside a
  persistent rollback transaction and recover an interrupted prior run against
  TARGET before doing anything else. `copy_payload` gained an `on_apply` seam
  that wraps only the write phase and receives the exact destinations about to
  be written, so the copier still carries no dependency on the transaction
  layer. `--dry-run` neither stages nor recovers a transaction.
- Make every hook transport fail closed and resolve the same interpreter. The
  Claude Code/Codex/Qwen Code launcher, the OpenCode plugin, and the Pi bridge
  now offer one ordered candidate list (`py -3` then `python` on Windows,
  `python3` then `python` elsewhere), each probed on `PATH` before use, and all
  three treat a guard that could not run as a block instead of an allow.
  `run_hook.mjs` is now importable without executing its launcher body.
- Document that every agent must be launched from the repository root, and why
  it is a safety requirement rather than a convenience. Agent hosts locate their
  project configuration relative to the launch directory, so a session started
  in a subdirectory finds no project config, registers no hooks, and runs with
  every guard silently absent — the tool calls are not blocked, they are never
  inspected, and nothing reports it. The gap opens before any hook loads, so no
  hook can detect it. Recorded in the shared hooks README with the evidence, in
  each adapter's own notes, and in the CLI runtime requirements, together with a
  way to confirm guards are live in a session. Anchoring the hook commands to
  the Git root was considered and rejected: it fails in a project without a
  `.git` directory, disagrees with `find_repository_root`, which resolves
  `.agentic/` first, has no single form valid across `bash`, PowerShell, and
  `cmd.exe`, and would not close this gap in any case, because the commands
  already resolve correctly whenever the configuration containing them loads.
- Remove the obsolete `create_project_from_template.py` compatibility wrapper;
  deployment documentation and integration tests now use WAEGIS directly.
- Expand the AEGIS architecture presentation with complete maintained-adapter
  coverage, explicit Alignment and Check stages, WAEGIS deployment guidance,
  and the protective Aegis naming concept.
- Synchronize the planning and copied prompt cheat sheets with WAEGIS-managed
  deployment, OpenCode and Qwen Code usage, scope hints, the lightweight
  documentation-change recipe, and worktree-local concurrency guidance.
- Refresh the stack architecture to separate WAEGIS deployment from AEGIS
  operation, distinguish seven stages from six approval transitions, and
  replace obsolete policy, requirement-table, and worktree roadmap statements.
- Bring the feature, bug-fix, and existing-repository adoption examples onto
  the same WAEGIS-to-AEGIS handoff, stage terminology, and delivery working-tree
  audit contract.
- Require component-manifest paths and baseline thresholds to be passed
  explicitly by AEGIS consumers, and remove unused write-hook compatibility
  state accessors plus the obsolete empty registry directory.

### Fixed

- Make `run.sh` resolve the registered interpreter on Windows. It is a bash
  script, so it took the POSIX branch unconditionally — but bash on Windows is
  Git Bash, a supported way to use the repository, and packaged WAEGIS registers
  its interpreter under `APPDATA` there. Looking only in `~/.config/waegis`
  silently missed it and fell through to the system candidates, where bare
  `python` on a stock Windows host is the Microsoft Store alias stub: it
  launches, exits non-zero and writes nothing. The wrapper now mirrors
  `run_hook.mjs` exactly — `WAEGIS_HOME`, then the Windows roaming profile,
  then the POSIX config directory — and offers `py -3` before `python` on
  Windows. It also trims `AEGIS_PYTHON` and the pointer file's contents, as the
  Node and PowerShell launchers already did.
- Give both CLI wrappers the same exit status when no interpreter is available.
  `run.ps1` reported it with a plain `Write-Error`, which under the script's
  `$ErrorActionPreference = "Stop"` raises a terminating error and ends the
  script with status 1, never reaching its own `exit`; `run.sh` used an explicit
  2. Both now exit 2. The replacement deliberately avoids `[Console]::Error`:
  a static .NET call fails outright under PowerShell Constrained Language Mode,
  which is the configuration a locked-down corporate host is most likely to be
  running — and exactly where a missing-interpreter message matters most.
  `test_guard_transport_parity.py` now covers both wrappers: shared resolution
  order, the Windows pointer location, the candidate order, the shared exit
  status, and the absence of Constrained-Language-unsafe constructs.
- Start verifying that `guard_read_path.py` was installed. `HOOK_FILES` listed
  four of the five guards the payload ships, omitting the protected-read guard,
  which arrived with the protected-read policy without the list being updated
  alongside it. Both consumers — the `verify.hooks-present` wizard step and
  `waegis doctor`'s runnability check — report success over the listed names
  only, so a `guard_read_path.py` that failed to copy was never looked for:
  setup finished green, doctor reported "all hook files present", and the
  protected-read policy silently enforced nothing. The list is now complete,
  and a test derives the expected set from the real template instead of
  restating it, so the next hook added fails that test rather than going
  unchecked.
- Correct the Qwen adapter README, which still described the guard as failing
  open when Python cannot be run. Every transport now fails closed; the Pi and
  OpenCode notes were updated with that change and this one was missed.
- Stop protected-read policy from being bypassable through a host's search
  tools. Every adapter routed only its single canonical read tool to
  `guard_read_path.py`, so an enforced `protected_paths` read policy could be
  sidestepped by asking the same host for the same bytes through its grep tool,
  and for protected file names through its glob or directory-listing tool. All
  four tool classes now reach the guard on Claude Code (`Read`/`Grep`/`Glob`),
  Qwen Code (`read_file`/`read_many_files`/`grep_search`/`glob`/`list_directory`,
  including the display aliases older builds emit), OpenCode
  (`read`/`grep`/`glob`/`list`), and Pi (`read`/`grep`/`find`/`ls`); Codex has no
  distinct read tool and reads through `shell`, already matched. Adapters now
  forward the real tool name so the guard can distinguish a read that must name
  a file — still denied when it names none — from a search whose scope argument
  is optional. A `pattern` argument is read as a path only for glob-style tools,
  never for grep, where it is a content regex.

  Known limitation, now documented rather than implied: an unscoped
  repository-wide search carries no path to inspect and is allowed, so it may
  still surface a line from a protected file. No supported host lets a pre-tool
  hook rewrite tool output, so this guard blocks a protected path from being
  targeted and is not a secrecy boundary.
- Stop WAEGIS rollback journals from being committable. `.agentic/.waegis-transactions/`
  holds verbatim backup copies of the files a deployment command is about to
  overwrite, and it was not in the template `.gitignore`, so a `git add -A` run
  while an install was in flight would commit the operator's own pre-change file
  content. The exposure grew when `new` and `adopt` became transactional,
  because both now create the directory.
- Stop an `apply_patch` envelope from bypassing the write-zone guard when the
  host sends it under a key other than `command`. The shared path extractor read
  `command` alone and returned no paths for any other key — and a write-zone
  guard that extracts no paths has nothing to block, so the call proceeded. The
  envelope is now read from `command`, `cmd`, `script`, `patch`, and `input`,
  matching the hedge the OpenCode adapter already applied on its own side, and
  a path carried by more than one key is reported once.
- Stop an unreadable working tree from being reported as a clean one. The
  delivery working-tree audit read only `git status` stdout and ignored the
  exit code, and git leaves stdout empty when it fails — so a directory that is
  not a repository, a broken index, or an unreadable object store produced
  output byte-identical to a genuinely clean tree and `delivery-preflight`
  passed without having inspected anything. A missing `git` executable behaved
  differently but no better: it raised `FileNotFoundError` out of the audit, and
  the delivery hook surfaced that traceback as its deny reason. Both now record
  a `git-status-unavailable` blocking finding. This is a behavior change:
  `working-tree` and `delivery-preflight` no longer pass outside a git
  repository, where previously the git-based scans no-opped by documented
  design. `impact` is unaffected — it widens its result set from `git status`
  as a convenience, so the blocking judgement stays in one place.
- Stop WAEGIS from losing subprocess output containing non-ASCII paths. The
  probe command runner requested text mode without pinning an encoding, so
  output was decoded with the host locale — `cp1252` on a stock Windows
  install. A Git command reporting a path such as `Ё.txt` emits UTF-8 bytes
  `cp1252` cannot map, and because that decode runs inside `subprocess`'s own
  reader thread, the failure never surfaced as an error: the thread died and
  the runner returned `stdout=None`, violating its own `str` contract. Probes
  testing the output for truthiness saw "no output"; probes calling `.strip()`
  saw an `AttributeError` far from the cause. Decoding is now pinned to UTF-8
  with replacement, matching how the AEGIS side already reads git.
- Stop the alignment protected-scope gate from silently never firing for a
  directory pattern. It was the one policy consumer still matching with
  `fnmatch.fnmatch` instead of the shared `matches_pattern`, and `fnmatch` has
  no tree-rooted form: a pattern of `src/security` — the most natural way to
  write the setting — did not match `src/security/auth.py`, so a planned change
  to a protected path recorded a `proceed` decision without ever pausing. A
  trailing separator was also significant, so `src/security/` and
  `src/security` behaved differently. The gate now matches through
  `matches_pattern`, which every other scope, working-tree, component, and hook
  check already uses. Latent in the shipped template, which configures
  `mode = "disabled"`, and live for anyone who enables it.
- Stop a recorded change-unit path that points outside the repository from
  making a run unusable. The scope invariant resolved every recorded path
  against the repository root and let the resulting error escape, so a single
  such path aborted `status`, `invariants`, `report`, and `delivery-preflight`
  with a traceback — and the delivery hook surfaced that traceback as its deny
  reason — until the run graph was repaired by hand. The invariant now reports
  an escaping path as its own finding, distinct from a path that is simply
  outside the configured roots.
- Stop an interrupted `waegis new` or `waegis adopt` from leaving a
  half-installed payload behind. Both wrote payload files one at a time with no
  rollback journal, so a failure or interruption partway through left the files
  written up to that point on disk with no manifest recording them — and, for
  adoption, with the operator's own overwritten files unrecoverable. Only
  `configure`, `repair`, and `upgrade` were transactional.
- Stop one unrelated directory under `.agentic/.waegis-transactions/` from
  making every mutating WAEGIS command fail. Transaction recovery loaded every
  subdirectory unconditionally, so a leftover directory carrying no
  `state.json` raised out of the recovery step that runs before any other work.
  A malformed state document that *is* present still raises: that is a real
  interrupted run whose journal was damaged.
- Stop the OpenCode and Pi guards from silently allowing a tool call whenever
  the shared Python hook could not produce a decision. Both transports read only
  the hook's stdout and ignored its exit status, so a crashed guard, an
  unlaunchable interpreter, or a missing interpreter was indistinguishable from
  a guard that ran and permitted the call. On Windows the OpenCode plugin also
  spawned bare `python` without probing `PATH`, which resolves to the Microsoft
  Store alias stub when no interpreter is installed: it launches, exits
  non-zero, writes nothing, and every guard allowed.
- Normalize a crashed hook to the blocking exit status in
  `.agentic/tools/run_hook.mjs`. It previously forwarded the hook's own status,
  and exit `1` is only a *non-blocking* hook error for Claude Code, Codex, and
  Qwen Code, so a guard that raised let the tool call proceed unchecked.
- Keep WAEGIS release staging aligned with deployment exclusions so Node/Vitest
  state, uv caches, Python bytecode, and generated package metadata cannot enter
  release payloads, and normalize Linux tar modes so Windows-hosted builds
  preserve executable launchers, runtimes, shell scripts, and LF-only shebangs.
- Align WAEGIS schema-version-2 verification with the strict AEGIS contract for
  closed tables, exact scalar types, normalized repository paths and globs,
  regular expressions, conditional fields, and filesystem-aware baseline
  manifests.
- Apply delivery preflight to Qwen's raw `run_shell_command` tool identifier
  and reject unsupported explicit gate names instead of silently succeeding.

## [1.0.0] - 2026-07-22

### Added

- Add the strict immutable schema-version-2 AEGIS configuration model,
  actionable `ConfigurationError` contract, shared hook bootstrap, and
  `aegis config validate` / `aegis config show --effective` commands.
- Add WAEGIS generation and validation for every explicit configuration mode,
  active rule collection, and complete stage-restricted write mapping.
- Add typed active-run resolution with stable `RUN-POINTER-*` and
  `RUN-ID-NOT-FOUND` errors, strict run-ID/graph validation, and atomic
  per-worktree pointer publication under `.agentic/.workspace/state/`.
- Add UUIDv4-backed TOML requirement snapshots, deterministic atomic
  persistence, agent-facing create/show/list/update/activate commands, and
  process-local requirement-to-test and requirement-to-path indexes.
- Add `WAEGIS_02_Safe_AEGIS_Upgrade.pptx`, an operator guide for safely upgrading an existing AEGIS deployment with WAEGIS.

### Changed

- Make the template policy explicitly unrestricted or disabled, remove
  structural-to-policy inference, and require gate commands as complete command
  strings under an explicit gate mode.
- Move the active-run pointer from `.agentic/current_run` to ignored
  `.agentic/.workspace/state/current_run`; the old pointer is unsupported,
  `load_graph` requires an explicit resolved ID, and state-aware hooks use the
  shared resolver instead of parsing pointers independently.
- Replace shared Markdown requirement registers and generated registry caches
  with one canonical current snapshot per requirement; traceability, coverage,
  impact, INV-8, reports, and delivery preflight now read live TOML records.
- Integrate explicit `--run-id` selection across every graph-dependent CLI
  leaf, make CLI orchestration load one strict configuration model per
  operation, and pass that model through gates, invariants, reports,
  requirements, component checks, and delivery preflight.
- Refresh `WAEGIS_01_Setup_And_First_Adoption.pptx` for WAEGIS 0.2.0.
- Align agent instructions, canonical skills, adapter wrappers, onboarding,
  configuration references, architecture maps, examples, and operator
  artifacts with the schema-version-2 configuration model, UUIDv4 TOML
  requirement snapshots, per-worktree active-run selection, and live delivery
  checks without a generated registry.
- Extend the WAEGIS payload compatibility upper bound through AEGIS 1.x so the
  wizard accepts and reports the bundled AEGIS 1.0.0 payload.

### Fixed

- Exclude generated Python `*.egg-info` metadata directories from the AEGIS
  template legal-header test so editable package builds do not create a false
  failure.
- Fix `waegis upgrade` branch-and-commit mode to consume `GitOpResult` status and failure details through its actual data-model fields.
- Keep the realistic WAEGIS upgrade fixture aligned with the category-based
  requirement snapshot layout shipped by the current AEGIS payload.

## [0.5.0] - 2026-07-20

### Added

- `aegis start` now accepts repeatable `--scope-hint` values, persists them in
  `Intent.scope_hint`, includes them in the `run.started` journal event, and
  makes intentional extra roots available to INV-5 without hand-editing run
  state. Scope hints remain advisory and do not relax write zones or protected
  files (backlog T12).

### Changed

- Repair the T15 documentation bundle without restoring intentionally removed
  planning artifacts: first-reader READMEs now point only to maintained
  sources, the architecture and worked examples describe current component
  knowledge, adoption stages, and Intent Alignment, WAEGIS catalog counts match
  the executable catalogs, shipped skills use repository-neutral audit command
  placeholders, and operator/configuration guides document lightweight changes,
  parallel work, glob semantics, and language-specific traceability behavior.
- Remove the unconsumed AEGIS `Defect` model, `Graph.defects`, and
  `ChangeUnit.evidence` from current graph serialization while keeping legacy
  graph files readable by ignoring those retired keys. Workflow reports now
  surface `Evidence.failure_kind` as `kind/result (classification): summary`.
  WAEGIS now registers all eight supported commands directly through dedicated
  parsers and handlers, with the unreachable generic stub factory/exit constant
  removed and CLI docstrings corrected to match the current flags (backlog T14).
- Harden the WAEGIS lifecycle and supersede the earlier Unreleased T6.2
  behavior: completed journals always run a fresh detection pass; only
  fingerprint-compatible incomplete journals may replay allowlisted answers.
  `upgrade` now requires a current valid manifest and a clean Git worktree,
  collects every decision before approval, stages persistent backups, rolls
  back automatically on apply/smoke failure or a recovered interruption, and
  writes the manifest last. Manifestless/earlier-layout upgrade and restamping
  are no longer supported.
- Release the AEGIS payload as `0.5.0` and the independently versioned WAEGIS
  wizard as `0.2.0`. WAEGIS continues to accept AEGIS payloads in
  `>=0.4.0,<1.0`; `manifest_version` and `journal_version` remain at `1` while
  all current fields stay mandatory. No compatibility reader or migration path
  is provided for earlier partial layouts.
- Standardize command JSON as one non-interactive envelope and exit codes as
  0 success, 1 warning/input/approval required, 2 validation/verification
  failure, and 3 operational/internal failure. Non-interactive mutations
  require `--yes`.

### Fixed

- Embedded AEGIS package metadata now matches the CLI project version and is
  protected by a scaffold parity test; the package marker's stray second
  docstring was removed. `add-spec` and `add-check` now reject duplicate
  run-local IDs before mutating the graph, while `impact` reuses the robust
  working-tree Git parser so renames contribute both current and previous paths
  and quoted paths are decoded consistently (backlog T13).
- Qwen Code hook matchers previously covered only the friendly `Edit`,
  `WriteFile`, and `Bash` names, so builds emitting raw `write_file`, `replace`,
  or `run_shell_command` identifiers could bypass the matcher before the shared
  guard received the payload. PreToolUse and PostToolUse now match the friendly
  and raw-name unions while preserving the same guard commands and order
  (backlog T8).
- Component ownership used raw `fnmatch`, so a bare directory entry such as
  `src/module` did not own files below it and could follow a different
  case-sensitivity policy from write-zone and scope checks. Component lookup
  now uses the shared `matches_pattern` policy: bare directories cover their
  subtree, explicit `/**` patterns remain valid, and similarly named siblings
  remain outside the component (backlog T11).
- Registry audit previously checked only cache presence and JSON syntax, so a
  requirement register edited after `registry sync` could pass delivery with
  stale `requirements.json` or `checks.json` data. The read-only audit now
  compares cached requirement records and linked-test keys with the live
  registers, reports `REGISTRY-STALE`, and names `registry sync` as the repair;
  `delivery-preflight` inherits the deterministic failure (backlog T10).
- Requirement activation previously wrote an `Active` register row even when a
  freshly supplied linked-test identifier did not resolve. Activation now
  validates every new link before writing, reports all unresolved identifiers
  and reasons as a clean CLI error, and leaves the register unchanged; valid
  links and manual-only activation retain their existing behavior (backlog T9).
- The PreToolUse secret hook used only four hardcoded patterns while INV-7 and
  working-tree audit honored repository-specific `[secrets].patterns`. The hook
  now scans the union of built-in and configured regexes across every adapter;
  missing/malformed configuration and invalid user regexes remain fail-open and
  cannot crash or block tool use by themselves (backlog T6).
- Adapter secret-file deny lists had drifted from the canonical write-zone
  protection list, and `gh pr merge` could bypass the controls used for PR
  creation. Claude Code and Qwen now deny every canonical secret/key glob for
  read and edit/write tools, Codex covers the corresponding filesystem-profile
  extensions, and PR merges are intercepted by the shared preflight plus the
  Claude, Qwen, and OpenCode permission layers (backlog T5).
- Claude Code, Codex, and Qwen previously ran `secret_scan.py` only for Bash
  input, so secrets pasted through edit/write tools were not intercepted until
  a later invariant or working-tree audit. Their edit matchers now run the
  secret scan alongside `guard_write_zone.py` (including Codex's Windows
  command twin), matching the existing OpenCode and Pi coverage (backlog T4).
- AEGIS's write-zone hook reported a no-run fallback as an ordinary intake
  write-zone violation, leaving a fresh agent without the actual recovery
  action. It now keeps the denial behavior unchanged but identifies that no
  active run exists, includes Windows and POSIX `start` examples, and lists
  the blocked paths; active-run stage messages are unchanged (backlog T7).
- AEGIS `store.repo_root_from` resolved the workflow root as the bare process
  working directory with no validation, so invoking the CLI (directly, via
  `run_aegis.py`/`run.ps1`/`run.sh`, or through a hook) with the working
  directory mistakenly set to a project's own `.agentic` folder — or a
  previously self-nested copy of it — silently created another
  `.agentic/.agentic/...` layer instead of failing, since every write path
  (`write_current_run`, `init_graph`) calls `mkdir(parents=True,
  exist_ok=True)` unconditionally. Reproduced directly against `aegis.cli.main`
  in a scratch sandbox before the fix. Now raises a clear `SystemExit` when the
  resolved root is itself named `.agentic` or nested inside one
  (`05_Software/aegis/template/.agentic/cli/src/aegis/store.py`; regression
  tests in `05_Software/aegis/tests/test_store.py`).
- AEGIS `invariants._clean_secrets` (INV-7) only scanned the unstaged
  `git diff`, so a secret in a newly created or already-`git add`-ed file
  never appeared in the scan. Now scans `git diff HEAD` (staged + unstaged
  against the last commit) plus the content of untracked, non-ignored files
  (`05_Software/aegis/template/.agentic/cli/src/aegis/invariants.py`).
- AEGIS `gates._argv_for_simple_command` used
  `shlex.split(command, posix=os.name != "nt")`, whose non-POSIX mode on
  Windows only treats a quote as significant when it starts a token — a
  quoted argument containing a space (e.g. `pytest -k "test name with
  space"`) silently split into two malformed tokens, letting a gate command
  run a different (narrower/no-op) command than configured. Replaced with a
  `shlex.shlex` lexer in POSIX quoting mode with `escape` cleared, which
  groups quoted spans correctly on every platform while still preserving
  literal Windows backslashes
  (`05_Software/aegis/template/.agentic/cli/src/aegis/gates.py`).
- AEGIS `working_tree._git_status` never undid Git's default C-style
  quoting/octal-escaping of non-ASCII filenames, so a protected, blocked, or
  secret-bearing file with a non-ASCII name (e.g. `café.txt`) could dodge
  every path-pattern check in delivery preflight. Added
  `-c core.quotepath=false` to the `git status` call plus a defense-in-depth
  unquoting helper for the remaining quoted-character cases
  (`05_Software/aegis/template/.agentic/cli/src/aegis/working_tree.py`).
- Claude Code adapter: `.claude/settings.json` hook commands were plain
  project-root-relative strings instead of the documented
  `${CLAUDE_PROJECT_DIR}`-anchored form, which can resolve incorrectly in
  worktree/subagent sessions where `cwd` diverges from the project root. Now
  anchored per Claude Code's hook-reliability guidance.
- Qwen Code adapter: the hook `matcher` in `.qwen/settings.json` included
  tool-name aliases (`MultiEdit`, `write_file`, `replace`, `apply_patch`) that
  are not documented Qwen Code tool names (likely copied from the
  Claude/Codex adapters). Reduced to the two confirmed real names
  (`Edit|WriteFile`).
- Pi adapter: a doc comment in `.pi/extensions/agentic-guard/hook-bridge.ts`
  and `.pi/README.md` incorrectly stated `pi.exec()`'s `ExecOptions` include a
  `cwd` field; current Pi docs show only `{ signal, timeout }`. Corrected in
  both places.
- Confine every managed payload/manifest path to its repository: reject
  traversal, absolute/drive/UNC paths, ambiguous separators,
  normalization/case collisions, and source/target symlink or reparse escapes.
- Make the AEGIS cache-hygiene test hermetic by checking tracked deliverables,
  so Python caches created by another test cannot fail the suite.
- Exclude managed `.agentic` and agent-adapter code from host-project language
  and source-root proposals after installation.
- Materialize Linux embedded-runtime links with streamed byte copies so full
  release archives build reliably on Windows without symlink privileges or
  `CopyFile2` sharing violations.

- WAEGIS `deploy.workflow-toml`: `normalize_gate_commands` (task T4.1,
  `05_Software/waegis/src/waegis/repo/workflow_toml.py`) unconditionally
  rejected any `str` answer, so a real console operator typing a non-empty
  `gate_test_cmds`/`gate_lint_cmds` value — including the prompt's own
  printed example, `[["uv", "run", "pytest", "-q"]]` — could never get past
  the prompt: `ConsoleAsker.ask_field` re-prompts forever on an invalid
  answer, so only accepting the empty `[]` default was ever reachable
  interactively. Found during task T4.4 live verification (`waegis new`
  run against a real empty target on Windows 11). Fixed by parsing a `str`
  answer as JSON before the existing list-of-argv-lists validation; a flat
  list (`["pytest", "-q"]`) remains rejected as ambiguous, and malformed
  JSON re-prompts with a corrected example. Adds two regression tests in
  `05_Software/waegis/tests/test_repo_workflow_toml.py`: a direct
  `normalize_gate_commands` JSON-string test and a `ConsoleAsker`
  integration test proving the prompt's own example text is now accepted
  on the first try. This closes milestone M4's T4.4 live-verification
  requirement on Windows 11; Ubuntu 22 was not available in this session
  and remains unverified (see
  `06_SoftwareDocu/WAEGIS_Live_Verification_New.md`).

### Added

- Add real `waegis configure`, `waegis repair`, and `waegis version` commands.
  Configure rewrites owned workflow fields only and commits generated metadata
  last; repair restores only hash-matching originals, requires explicit
  modified-file decisions, regenerates configuration from current metadata,
  and uses persistent rollback transactions. Doctor findings now expose typed
  lifecycle actions.
- Add payload digests and normalized non-secret generated-configuration
  metadata to the single current install-manifest layout, plus payload
  compatibility enforcement across mutating commands.
- Add payload-bundled zipapp and Windows x64/Linux x64 application-archive
  packaging with pinned embedded CPython assets, internal/external file
  manifests, release hashes, and verification. Packaged interpreters register
  through an atomic per-user runtime pointer; deployed AEGIS CLI wrappers and
  hook adapters resolve `AEGIS_PYTHON`, that pointer, then system Python.
  Network self-update, GUI, and AI remain deferred and hidden from help.

- Record the initial `waegis upgrade` three-way implementation
  (task T6.2, milestone M6, plan §10.2) in
  `05_Software/waegis/src/waegis/commands/upgrade.py`; lifecycle stabilization
  remained open. The following historical detail records
  replacing the not-implemented stub — the three-way, manifest-driven payload
  upgrade and the highest data-loss-risk command in WAEGIS (plan §14). For every
  payload file it compares three hashes — `O` (the manifest's recorded
  as-shipped original), `L` (the current on-disk bytes), `N` (the new payload)
  — and classifies each into exactly one of nine actions: unchanged,
  auto-apply-new (`L=O`, `N≠O`), keep-local (`L≠O`, `N=O`), already-converged
  (`L≠O`, `N≠O`, `L=N`), add-new / new-converged (new upstream files),
  delete-removed / keep-modified-removed (files upstream dropped — deleted only
  when locally unmodified, otherwise **kept and reported as a preserved local
  edit**), and conflict. A true three-way conflict (`L≠O`, `N≠O`, `L≠N`, or an
  untracked local file colliding with a new upstream file) is **never**
  auto-resolved: it goes through a caller-supplied hook reusing copier's
  `ConflictDecision` vocabulary (keep-local / take-payload / write-`<file>.new`).
  `generated` files (`.agentic/workflow.toml`) are excluded from the comparison
  entirely — never classified, never written — and preserved verbatim in the
  rewritten manifest. Apply ordering enforces a **manifest-rewrite-last
  barrier**: (1) classify (read-only; `--dry-run` stops here having written
  nothing), (2) decide every conflict through the hook, (3) apply all file
  writes, (4) run the post-apply `verify.cli-smoke` + `verify.workflow-smoke`
  re-verify (reusing `commands/new.py`'s wrapper-invocation and healthy-response
  rules), and (5) **only** on a fully successful apply + smoke re-verify rewrite
  the manifest with the new `payload_version` and new original hashes. If the
  smoke re-verify fails, applied files remain but the manifest is left
  untouched (it still truthfully describes the pre-upgrade state), so a re-run
  or a manual revert both stay coherent — and because the manifest is only
  rewritten last, an upgrade aborted mid-apply is safely resumable: a second run
  reclassifies already-applied files as already-converged and never
  double-applies. A repo with no manifest (or an invalid one) takes a
  documented conservative path: no `O` exists, so every colliding local file
  becomes a conflict needing a decision (nothing is auto-applied), new-payload
  files are added, local-only files are left untouched, and `.agentic/workflow.toml`
  is protected as `generated`. The frozen §5 CLI stays four flags; because it
  has no `--answers`, the `--json` (non-interactive) path stops-and-reports on
  any conflict (exit 1, nothing written) while the interactive path prompts via
  `ConsoleAsker` — `run_upgrade()` exposes `on_conflict`/`resolutions`/`asker`
  parameters as the test and future-WADORE seam. `copy_payload` is deliberately
  not reused (its conflict model is two-way and it writes its manifest inline
  via `build_manifest`, which re-hashes disk and would mis-record a kept-local
  file's original); only `should_exclude`, `hash_file`, `ConflictDecision`,
  `SIDECAR_SUFFIX`, and the byte-verbatim `shutil.copy2` primitive are reused,
  with the three-way orchestration and rewrite-last barrier written fresh. Exit
  codes (frozen from 0.1.0): 0 complete / 1 conflicts need decisions / 2 applied
  but smoke re-verify failed / 3 operational (`--repo`/payload not found). Wires
  the real `upgrade` subparser into `cli.py`, leaving only `version`,
  `self-update`, and `gui` as generic stubs. Adds
  `05_Software/waegis/tests/test_commands_upgrade.py` (32 tests): an exhaustive
  per-row O/L/N matrix asserting both the action and the resulting manifest, the
  `generated`-exclusion guarantee, conflict-hook cardinality and each decision's
  outcome, removed-upstream (unmodified vs. modified), dry-run byte-identity,
  smoke-failure / rewrite-last ordering, resume-after-partial-apply, the
  no-manifest and invalid-manifest conservative paths, `--json` (healthy and
  conflict-present), a realism test driving the real
  `05_Software/aegis/template/` tree as the new payload, and CLI-stub regression
  guards.
- Implement `waegis doctor --repo PATH [--json]` (task T6.1, milestone M6,
  plan §10.1) in `05_Software/waegis/src/waegis/commands/doctor.py`, opening
  milestone M6 and replacing the not-implemented stub. Unlike `analyze`
  (read-only, no verdicts), doctor attaches an `ok`/`warn`/`fail` health
  verdict to every finding and exits the worst one found (0 healthy / 1
  warnings / 2 failures per plan §10.1; a nonexistent/non-directory `--repo`
  returns a distinct exit code, 3, so it can never be misread as a health
  verdict). Six check groups, each re-using the same building blocks
  `analyze`/`new`/`adopt` already established rather than reimplementing
  them: **Machine** re-runs the P0/P1 machine and tool probes
  (`probe_os_support`, `probe_disk_space`, `probe_python`, `probe_git`,
  `probe_uv`); **Manifest** resolves a four-way state (valid / invalid /
  legacy pre-manifest / not installed — mirrors T5.2's `repo.prior-install`
  routing, since `ManifestState` alone cannot tell "never installed" from
  "legacy install" apart) plus a new `update available` check comparing the
  installed `payload_version` against the currently bundled payload's real
  version; **Drift** reuses `compute_drift` (any modified/missing file is
  `warn`, never `fail` — drift alone does not mean broken); **workflow.toml**
  parses via `tomllib`, checks every configured root exists on disk, and
  re-runs `repo/workflow_toml.py`'s `verify_workflow_invariants` exactly (that
  function is public specifically for this reuse) so a foreign/manual edit
  that breaks write-zone alignment on an installed repo is caught as a real
  `fail`, plus `warn`-level empty-gate and missing-components-manifest
  checks; **Runnability** re-checks wrapper-script presence and a real
  `--help` smoke invocation through the injected `CommandRunner`, hook-file
  presence (`fail`), and known adapter-directory presence (`warn`) — reusing
  `commands/new.py`'s `_wrapper_invocation`/`HOOK_FILES` rather than
  re-deriving the CommandRunner invocation shape, with doctor-specific
  differentiated severities computed locally instead of new.py's single
  undifferentiated hooks-and-adapters boolean; **Journal** reports whether the
  most recent wizard run for this repo completed or names the step it stopped
  at (informational absence when no prior run exists). Adds a new, frozen
  `--json` shape (`{repo, overall_status, exit_code, groups: {machine,
  manifest, drift, workflow_toml, runnability, journal}}`, with `drift`
  additionally carrying full modified/missing file lists — the human view
  shows counts only, mirroring `analyze`'s verbosity split). Wires the real
  `doctor` subparser (`--repo` required, `--json`) into `cli.py`, alongside
  `new`/`adopt`/`analyze`; every other stub (`upgrade`, `version`,
  `self-update`, `gui`) is unchanged. Adds
  `05_Software/waegis/tests/test_commands_doctor.py` (16 tests: healthy-repo
  all-ok, drift, update-available distinct from drift, a workflow.toml
  write-zone invariant violation, empty gates as warn-not-fail, a missing
  hook file, the manifest four-way state reported distinctly, the journal
  group's three distinct outcomes, three explicit verdict-aggregation tests,
  the `--repo`-not-found exit code, and the `--json` shape for both a healthy
  and a mixed-verdict repo) plus two new `test_cli_smoke.py` cases replacing
  doctor's entry in the generic not-implemented-stub regression check.

- Implement the WAEGIS Wizard E catalog and the `waegis adopt` command
  (task T5.2, milestone M5, plan §8.2) in
  `05_Software/waegis/src/waegis/commands/adopt.py`, completing the second
  wizard journey: deploying the AEGIS payload into an existing repository.
  Reuses Wizard N's P0–P2 machine/prereq/network prefix, the `deploy.gates`
  step, and the three identical `verify.*` smoke steps as the **same**
  `StepSpec` objects (exposed from `commands/new.py` as `COMMON_PREFIX_STEPS`,
  `GATES_STEP`, `VERIFY_STEPS` — new.py's `build_new_catalog` refactored to
  slice them from one ordered list, its behavior and 312 tests unchanged),
  plus the mode-agnostic helpers and the shared `deploy.workflow-toml`
  detect/verify/on_fail. New adopt-only steps: `repo.validate-existing`
  (git work-tree summary, submodule/LFS from T5.1's risk flags,
  warn-not-block on a dirty tree, operator confirms); `repo.prior-install`
  (four-way routing — none / current→`doctor` / older→`upgrade` / legacy
  conservative-path — which `ManifestState` alone cannot produce, so an
  explicit `.agentic` directory check supplies the fourth branch);
  `analyze.repo` (renders T5.1's `analyze_repo` and confirms **each**
  proposed field via `ctx.asker`/FieldSpec seeded from the proposal, gate
  provenance surfaced — nothing auto-applied); `deploy.adoption-copy` (the
  first real caller of the copier's ADOPTION mode, driving the
  `ConflictDecisionHook` from `ctx.asker` or a pre-supplied
  `adoption_conflicts` table, journaling and verifying every keep-local /
  take-payload / write-`.new` decision); an adopt-specific
  `deploy.workflow-toml` act (generates from the confirmed analysis answers,
  reusing new.py's manifest-amendment-at-generation-time pattern);
  `repo.adoption-commit` (branch `chore/aegis-adoption`, override via
  `adoption_branch`); and `handoff.adoption` (prints the real adoption-intake
  prompt extracted from the copied `PROMPT_CHEATSHEET.md`, so it cannot
  drift). `run_adopt` mirrors `run_new`'s plan §5 CLI contract
  (`TARGET [--answers F] [--dry-run] [--non-interactive] [--json]
  [--payload PATH]`), pre-computing the read-only analysis once so the
  non-interactive contract reports every unproposable required key at once
  before the engine starts. Adds `gitops.current_branch`, wires the real
  `adopt` subparser into `cli.py`, and adds 23 tests
  (`test_commands_adopt_catalog.py`, `test_commands_adopt_prior_install.py`,
  `test_commands_adopt_run.py`, `test_commands_adopt_e2e.py`) covering
  catalog registration + shared-object identity, four-way routing, the
  non-interactive/dry-run/JSON parity set, and an integration suite (real
  payload/git/shell): full green adoption, operator override beating the
  proposal, resume-skips-all, and per-decision conflict resolution.

- Implement the WAEGIS Wizard E repo analysis heuristics (task T5.1,
  milestone M5, plan §9) in
  `05_Software/waegis/src/waegis/repo/analyze.py`: a deterministic,
  read-only, ranked-proposal analysis engine for existing-project adoption.
  File inventory prefers `git ls-files` (new `ls_files` primitive added to
  `repo/gitops.py`, following its `_git_c`/`str | None` convention) and
  falls back to a filesystem walk honoring the top-level `.gitignore`
  (deliberately simplified glob semantics — documented scope limit). An
  extension histogram weighted by both file count and total bytes, plus
  build-marker boosts, produces a ranked language guess whose top value is
  always an exact `workflow_toml.LANGUAGE_PRESETS` key (or `"other"`), so
  T5.2 can hand the proposal straight to `generate_workflow_toml`. Detects
  build systems (pyproject/setup, package.json + lockfiles, Maven, Gradle,
  CMake, Cargo, go.mod, `*.csproj`/`*.sln`, Makefile, Dockerfile), proposes
  confidence-tagged `source_roots`/`test_roots` (conventional layouts first
  — `src/main/java` and `src/test/java` before generic `src`; Go
  `cmd`/`pkg`/`internal`; Swift `Sources`; Python packages — then a
  >= 90%-coverage fallback), and flags colocated tests (e.g. `*_test.go`
  beside sources) with the plan D12 write-zone note. Gate-command candidates
  carry structured provenance (`source_file` + `source_detail`) and are
  never executed: package.json `scripts.test`/`scripts.lint` (as the
  lockfile-selected package-manager invocation), `pyproject.toml`
  pytest/ruff config sections, `Makefile` `test:`/`lint:` targets, and
  CI `run:`/`script:` lines (line-scanned, no YAML parser); a shell-syntax
  line `shlex` cannot safely split becomes a `needs_review` "manual review
  required" candidate instead of a wrong argv. Adoption risk flags reuse the
  `io/reports.py` `ProbeFindingRecord` shape: submodules, LFS, monorepo
  signals, > 10,000-file heuristic-only warning, prior/partial install
  (`.agentic/` or an adapter dir, manifest presence noted), and a
  per-file guaranteed-conflict flag (`"conflict"` status) for a pre-existing
  root `AGENTS.md`/`CLAUDE.md` (never overwrite — detection only). Ships the
  `RepoAnalysis` dataclass with a `render_repo_analysis`/`to_dict`/
  `repo_analysis_json` trio (frozen `--json` field names, plan D13). This
  module produces data only — it never decides, writes, or mutates the
  target repository; every value is a proposal the operator confirms in
  T5.2. `ADAPTER_DIR_NAMES` moves here as the single source of truth and is
  re-exported by `commands/analyze.py` (still cross-checked against
  `05_Software/aegis/template/`). Adds `tests/test_repo_analyze.py`,
  `tests/test_repo_analyze_gates.py`, and four `ls_files` cases in
  `tests/test_repo_gitops.py` (all offline; fake-CommandRunner-scripted
  `git ls-files` output and injected large inventories); suite grows from
  282 to 312 tests, all green.
- Implement the WAEGIS Wizard N catalog and the real `waegis new` command
  (task T4.3, milestone M4) in
  `05_Software/waegis/src/waegis/commands/new.py`: all 17 plan §8.1 steps
  registered as `StepSpec`s over the shared engine with a linear
  precondition chain realizing the P0→P5 phase order; `net.proxy` wires
  T2.2's real proxy probe and `applies()` only when a `clone_url` answer
  requests a remote clone. Documented step decisions: `machine.os` is
  report-only (warn-not-block) while `machine.disk` blocks only below the
  1 GiB minimum; `prereq.python`/`prereq.git` guide with the probe's
  OS-keyed install command and re-probe (the wizard never performs
  privileged installs); `prereq.git-identity` records a pending repo-local
  identity from `git_user_name`/`git_user_email` answers, applied right
  after `git init`; `verify.workflow-smoke` accepts the embedded CLI's
  coherent "No active agentic run" response as the healthy fresh-install
  outcome. `deploy.payload-copy` runs the strict (never-overwrite) copier
  and verifies drift-clean hashes plus a source-payload file-count match;
  `deploy.workflow-toml` interviews the T4.1 FieldSpecs, journals every
  empty-gate `GateWarning` loudly, creates missing roots with `.gitkeep`
  on confirm, and amends the install manifest by moving
  `.agentic/workflow.toml` from `files` into `generated` at generation
  time (keeping the manifest truthful at every checkpoint and re-run
  detect green); `deploy.gates` records every gate outcome and requires an
  explicit, journaled acceptance for failing/empty/deferred gates; the
  smoke steps run the real wrappers (`powershell -NoProfile
  -ExecutionPolicy Bypass -File run.ps1` on Windows, `bash run.sh` on
  POSIX) inside TARGET; `handoff.summary` surfaces the first operator
  prompt from the copied `PROMPT_CHEATSHEET.md`. The command wires the
  full plan §5 contract (`TARGET [--answers F] [--dry-run]
  [--non-interactive] [--json] [--payload PATH]`) into `cli.py` (only the
  `new` stub replaced): `--non-interactive` fails before the engine
  starts naming every missing required key (workflow answers must be
  pinned explicitly — interactive defaults are not silently applied),
  `--dry-run` writes nothing (no journal), `--json` emits exactly one
  frozen-shape document, exit codes follow analyze's 0/1 convention, and
  a re-run auto-discovers the latest prior journal for the same TARGET to
  resume-skip green steps. Supporting additions: `gitops.head_commit`
  (proving a commit exists — an empty porcelain status is also what a
  failed git call yields), an optional `cwd` keyword on
  `CommandRunner.run`/`SubprocessCommandRunner.run` (the embedded
  workflow CLI resolves its repo root from the working directory, so the
  smoke and gate commands must run inside TARGET), and a registered
  `integration` pytest marker. Tests: 31 new (catalog/§8.1 parity,
  per-step offline units over the fake CommandRunner including the exact
  smoke argv + cwd, command-level seam tests, and two
  `integration`-marked end-to-end runs with the real payload, real git,
  and real wrapper scripts proving the full green run and the
  all-steps-skipped resume; deselect with `-m "not integration"`).

- Implement WAEGIS git primitives (task T4.2, milestone M4) in
  `05_Software/waegis/src/waegis/repo/gitops.py`: `is_work_tree`,
  `init_repo` (with an older-git fallback when `-b` is unsupported,
  detected from git's real stderr rather than a probed version string),
  `clone_repo` (pre-checks a non-empty target before ever invoking git),
  `get_identity`/`set_identity` (repo-local by default, explicit
  `--global` opt-in, three-state identity via `GitIdentity`),
  `status_porcelain`, `add_all`, `commit`, and `create_branch` — all typed
  wrappers (`GitOpResult`/`GitIdentity`) over the T2.1
  `waegis.probes.runner.CommandRunner`, reused as-is: every git call is
  `git -C <path> ...`, so the path is just another argv element and the
  shared `CommandRunner` Protocol needed no extension. No function raises
  for an expected git failure; raised exceptions are reserved for
  programmer errors (e.g. an empty branch name). Adds
  `05_Software/waegis/tests/test_repo_gitops.py` (23 offline tests via a
  fake `CommandRunner`: work-tree detection, init with and without `-b`
  support, clone success/pre-existing-target/failure, identity's
  both/one/neither-set states, repo-local vs. global identity writes,
  porcelain status parsing including a rename-format line, exact-argv
  regression guards for `add`/`commit`/`create_branch`, and a Windows-style
  path construction test that is host-OS-agnostic).

- Implement the WAEGIS `workflow.toml` generator (task T4.1, opening
  milestone M4) in `05_Software/waegis/src/waegis/repo/workflow_toml.py` —
  the single generator serving both `waegis new` and `waegis adopt` (only
  the answer source differs). `WORKFLOW_FIELD_SPECS` expresses the plan §7
  answer table (`source_roots`, `test_roots`, `language`, `gate_test_cmds`,
  `gate_lint_cmds`, `alignment_enabled`) as T1.2 `FieldSpec`s whose shared
  validators accept both console strings and typed answers-file values.
  `LANGUAGE_PRESETS` is a structured `LanguagePreset` table (python,
  typescript, javascript, java, csharp, go, rust, cpp) supplying
  `[traceability].language`/`source_extensions`/`test_file_patterns`;
  `"other"` requires explicit extensions/patterns (`LanguagePresetError`
  otherwise — plan §7 invariant 6) and explicit values override any preset
  (the D12 colocated-tests escape hatch). `generate_workflow_toml` is pure
  text-in/text-out and rewrites the real template base by **targeted text
  substitution**: a section-aware, string-aware line scanner replaces only
  the twelve generator-owned keys (`source.roots`, `tests.roots`, four
  `[traceability]` keys, `gates.test/lint`, `alignment.enabled`,
  `write_zones.check/implementation/component-adoption`, with
  component-adoption keeping its leading `.agentic/**` entry) while every
  other line — comments included — passes through byte-identical; comments
  are preserved, not regenerated. Plan §7 invariants 1–4 are re-verified on
  the tomllib-re-parsed output before returning (never-save-invalid guard,
  invariant 5), raising a typed `InvariantViolationError` that names the
  failed invariant; `verify_workflow_invariants` (invariants 1–3) is public
  for `waegis doctor` (T6.1) reuse; a base missing an owned key raises
  `BaseFileMismatchError` instead of emitting a file with missing settings.
  Empty gates generate successfully but return structured `GateWarning`
  records naming each empty gate for the calling step to journal (plan §7
  "loud, recorded warning"). Adds
  `05_Software/waegis/tests/test_repo_workflow_toml.py` (28 offline tests
  against the real `05_Software/aegis/template/.agentic/workflow.toml` plus
  synthetic edge-case bases: golden tests for every preset, property-style
  multi-root invariant checks, exact byte-slice survival of untouched
  sections and all comments, corrupted-rewrite guard tests via monkeypatch,
  "other"-language validation both ways, empty-gate warnings, answer
  validation, `ScriptedAsker`/`guard_answers` composition, and an
  independent stdlib-tomllib round-trip of the written file).

- Implement `waegis analyze --repo PATH [--json]` (task T3.3), closing
  milestone M3. `05_Software/waegis/src/waegis/commands/analyze.py`: a
  thin, read-only reporting layer over T3.1's `load_manifest`/
  `compute_drift` — per plan §10.1, `analyze` is the read-only subset of
  `doctor` and renders **no health verdicts**; it exits 0 whenever the
  report was produced (a missing manifest, an invalid manifest, or drifted
  files are informational findings, not command failures) and non-zero only
  when `--repo` does not exist or is not a directory. Reports the three
  manifest states (absent/present-invalid/present-valid) distinctly,
  modified/missing drift (only computed for a valid manifest), and a
  workflow inventory (`.agentic/` presence plus each known agent adapter
  directory — `.claude`, `.codex`, `.opencode`, `.pi`, `.qwen`, read from
  and cross-checked against the real `05_Software/aegis/template/`
  directory). Human rendering follows `io/console.py`'s plain-ASCII
  encoding-safety convention; `--json` emits a new frozen, WADORE-relevant
  field-name contract (`repo`, `manifest{...}`, `drift{...}|null`,
  `inventory{...}`). `05_Software/waegis/src/waegis/cli.py`: `analyze` is
  the first subcommand to get a real subparser (`--repo` required, `--json`
  flag) in place of the generic not-implemented stub; every other
  subcommand's stub registration and exit code (2) are unchanged. Adds
  `05_Software/waegis/tests/test_commands_analyze.py` (no-manifest,
  legacy-`.agentic`-without-manifest, invalid-manifest, valid-manifest with
  and without drift, adapter inventory subset/none-present,
  `--repo`-not-found, `--json` shape, adapter-name drift guard against the
  real template) and extends `tests/test_cli_smoke.py` with the CLI-wiring
  regression guard (every non-`analyze` subcommand still stubs out at exit
  2).

- Implement the WAEGIS manifest-aware payload copier and payload locator
  (task T3.2) under `05_Software/waegis/src/waegis/payload/`. `locate.py`:
  payload resolution per plan §5 — an explicit `--payload` path wins but is
  validated first (`InvalidPayloadError` unless it contains the
  `.agentic/workflow.toml` marker), the bundled-install candidate is a stub
  returning "not found" until T7.x packaging exists, and the fallback is the
  repo-checkout template at `05_Software/aegis/template/` resolved relative
  to the installed package (`PayloadNotFoundError` when nothing resolves);
  `read_payload_version` reads the payload's own version from
  `.agentic/cli/pyproject.toml` `[project].version`, degrading to `None`.
  `copier.py`: `copy_payload` absorbs the
  `create_project_from_template.py` safe-copy semantics — shared
  `should_exclude` predicate, byte-verbatim `shutil.copy2` copies (a copied
  file's `hash_file()` provably equals the source's), strict new-project
  mode raising a typed `OverwriteRefusedError` on any pre-existing
  destination file (identical included, dry-run included — legacy parity) —
  and adds adoption conflict classification (does-not-exist /
  exists-identical / exists-different with both sides' size and sha256), a
  caller-supplied `ConflictDecisionHook` called exactly once per
  exists-and-different file and never bypassed internally (`force=True` is
  the legacy override, implemented as an internal constant take-payload
  hook; combining it with a caller hook raises `ValueError`), keep-local /
  take-payload / write-`<name>.new` outcomes, a no-partial-write guarantee
  (all classification, refusals, and hook calls complete read-only before
  the apply phase), and install-manifest emission via T3.1's
  `build_manifest`/`write_manifest` (`files` = every payload-sourced file at
  the target, `skipped` = keep-local/write-new decisions, `generated` passed
  through for T4.1, sidecar `.new` files never manifest entries, a manifest
  shipped inside a payload source never copied). Returns a structured
  `CopyResult`; the module never prints and imports no network code. Adds
  offline `tests/test_payload_locate.py` and `tests/test_payload_copier.py`
  (synthetic fixtures for resolution order, byte-verbatim proof by direct
  source-vs-destination hash equality, dry-run, refusal with untouched
  target, all three adoption classifications and decisions, hook cardinality
  and failure modes, every exclusion rule) plus a real-payload end-to-end
  test copying `05_Software/aegis/template/` and verifying manifest file
  count and every hash against the source template.

- Implement the WAEGIS install manifest module (task T3.1, opening milestone
  M3) under `05_Software/waegis/src/waegis/payload/manifest.py`: the frozen
  schema-v1 `.agentic/install-manifest.json` contract (plan §6, AD-6) —
  `Manifest`/`FileEntry` dataclasses, byte-exact sha256 hashing (`hash_file`,
  binary-mode reads, no newline translation), POSIX-normalized file keys so a
  manifest built or read on Windows stores/loads the same forward-slash keys
  as on POSIX, `build_manifest`/`write_manifest`/`read_manifest` (2-space
  pretty JSON, stable sorted `files` key order, the manifest never lists
  itself and is excluded from hashing), `manifest_from_dict` validation that
  rejects a missing top-level key, an unknown `manifest_version`, or a
  malformed per-file entry with an error naming the offending key,
  `compute_drift` (modified/missing only — "extra" file detection needs a new
  payload's file list and is T3.2/T6.2's job), and `load_manifest` /
  `ManifestState` distinguishing absent / invalid / valid so `analyze`,
  `doctor`, and `upgrade` can each branch on exactly those three states.
  `installed_by` defaults to `f"waegis {WIZARD_VERSION}"` read from
  `waegis.version` at call time. Adds offline
  `tests/test_payload_manifest.py` (synthetic `tmp_path` fixtures only, never
  touching `05_Software/aegis/template/`) covering the round-trip, a
  golden-file parse/re-serialize contract, hash stability across copy
  mechanisms with a genuine CRLF-vs-LF byte-difference contrast, Windows-style
  backslash path normalization, every validation failure mode, the
  modified/missing/ignored-extra drift boundary, and the absent/invalid/valid
  load states.

- Implement the WAEGIS network/corporate probes (task T2.2) under
  `05_Software/waegis/src/waegis/probes/network.py`: the network subset of
  the analysis doc's corporate-restriction probe matrix — proxy detection,
  a TLS-interception heuristic, and generic host reachability
  (package-manager/WSL/admin-rights probes are out of scope for this task).
  Adds an injectable `Transport` protocol (`connect(host, port, *, use_tls,
  timeout) -> ConnectResult` reporting `connected`/`timed_out`/`refused`/
  `dns_failure` plus peer-certificate issuer/subject on a successful TLS
  connect) with a real `SocketTransport` implementation, and an injectable
  `RegistryReader` protocol for a best-effort Windows WinINet system-proxy
  registry read, with a real `WinInetRegistryReader` implementation that
  degrades to `None` on any failure (non-Windows, missing key, permission
  denied) rather than raising. `probe_proxy_configuration` checks
  `HTTP_PROXY`/`HTTPS_PROXY` env vars (and lowercase variants) in a fixed
  precedence order before falling back to the registry, and only attempts a
  direct-vs-proxied connectivity check when the caller supplies both an
  explicit target host/port and a transport. `probe_tls_interception`
  compares the presented certificate's issuer against a list of known public
  CA name fragments and reports a mismatch as "possible TLS interception,"
  naming the issuer; it never runs against a hardcoded external host —
  callers must supply one explicitly. `probe_host_reachability` reports
  reachable/timed-out/refused/DNS-failure with guidance text keyed to the
  failure kind rather than the OS. `to_blocking_point_report` maps a failed
  finding directly onto the existing `waegis.io.reports.BlockingPointReport`
  shape (attempted, what happened, why, copyable ask-IT text, alternative
  paths) with no changes to `reports.py`. Offline-first is structural: every
  function requires an explicit host and an explicit transport/registry with
  no defaults, so nothing in the module can open a real socket or registry
  handle unless the caller passes one. Adds offline
  `tests/test_probes_network.py` (via the new `tests/_fake_transport.py`
  fake) covering proxy detection (no proxy, env var, Windows-registry
  fallback, conflicting env-var casings, direct/proxied connectivity
  outcomes), the TLS-interception pass/warn/fail cases, all four
  reachability outcomes with distinct guidance text, blocking-point
  construction rendering through `io/reports.py` unmodified, and a
  regression guard proving no function opens a real socket when called
  without an explicit host.

- Implement the WAEGIS `CommandRunner` primitive and the machine/tool probes
  (task T2.1, opening milestone M2) under
  `05_Software/waegis/src/waegis/probes/`: `runner.py` adds the injectable
  `CommandRunner` protocol (ported from the ador `doctor.py` design) and its
  real `SubprocessCommandRunner` implementation, with `CommandResult.found`
  distinguishing "executable not found" from "executable ran and exited
  non-zero" and `combined_output()` covering tools that print `--version`
  text to stderr. `machine.py` adds `probe_os_support` (OS + version vs the
  plan's support matrix — Windows 11, Ubuntu 22+ — warn-not-block outside the
  matrix), `probe_architecture`, and `probe_disk_space` (free space at a path
  vs a caller-supplied minimum). `tools.py` adds `probe_python` (tries
  `py -3`, `python3`, `python` in order, falling through a candidate that is
  not found or exits non-zero; verdict >= 3.11), `probe_git` (verdict >=
  2.30), and `probe_uv` (optional; absence is informational, not a failure),
  each with OS-keyed install guidance (`winget`/`apt-get` commands, generic
  fallback for other operating systems) and real-world version string parsing
  (`git version 2.43.0.windows.1`, `Python 3.11.9`, `uv 0.4.18`). Every probe
  returns a `waegis.io.reports.ProbeFindingRecord` and never calls
  `subprocess` directly or prints, so probe results slot straight into
  `render_environment_report`/`environment_report_json` (T1.3). Adds offline
  `tests/test_probes_runner.py`, `tests/test_probes_machine.py`, and
  `tests/test_probes_tools.py` (via the new `tests/_fake_command_runner.py`
  fake), covering every found/not-found/too-old/unparseable-output
  combination, the documented python fallback order, OS/arch detection via
  `platform` monkeypatching (CI-portable, no real-OS assumptions), disk
  checks via `shutil.disk_usage` monkeypatching, differing Windows/Ubuntu
  guidance text, and the `ProbeFinding`/`environment_report_json` round trip.

- Implement the WAEGIS console renderer and reports (task T1.3, closing
  milestone M1) under `05_Software/waegis/src/waegis/io/`: `console.py` adds
  `render_plan_preview` (the "terraform plan"-style step table the operator
  approves before any mutation), `LiveStatusRenderer` (an `EventSink` that
  renders each step's `pending -> running -> detected-skip/done/failed`
  transition with the plain-ASCII marker set `[OK]`/`[FAIL]`/`[SKIP]`/`[..]`
  by default, an opt-in richer glyph set, and a per-write encoding check so a
  restrictive Windows console encoding can never raise
  `UnicodeEncodeError`/emit mojibake), and the `--json` twins
  (`plan_preview_json`, `step_result_json`, `run_summary_json`/
  `run_summary_to_dict`) that serialize the existing frozen `Plan`/
  `StepResult` `to_dict()` shapes plus a new `RunSummary` field-name contract
  (`mode, dry_run, ok, stopped_at, results`) — the WADORE seam frozen per plan
  §15 D13. `reports.py` adds the environment report (`render_environment_report`
  / `environment_report_json`) over a small structural `ProbeFinding` protocol
  (`name, status, detail, guidance`) that later probe result types (T2.1/T2.2)
  can satisfy without inheriting from it, and the blocking-point ("ask IT")
  report (`BlockingPointReport`, `render_blocking_point_report`,
  `blocking_point_report_json`) rendering the analysis doc's exact template —
  what was attempted, what happened, why the wizard needs it, a copyable ask-IT
  request, and the alternative paths — in a fixed field order, human and JSON.
  Adds offline `tests/test_io_console.py` and `tests/test_io_reports.py`
  (plan-preview render + `--json` round trip, live-status ASCII/glyph
  rendering and event order, the `cp1252`-encoding-fallback safety test, and
  both report shapes over fixed mixed pass/fail findings), plus
  `tests/test_engine_end_to_end.py` proving the M1 acceptance criterion: the
  toy 3-step catalog (T1.1) runs to completion both interactively
  (`ScriptedAsker` + the console renderer) and via an answers file
  (`io/answers.py`), and a second run against the same journal detects and
  skips every step.
- Implement the WAEGIS prompt and answers-file primitives (task T1.2) under
  `05_Software/waegis/src/waegis/io/`: `prompts.py` ports the ador-init
  `FieldSpec` design (description/"why", example, detected default, validator,
  secret flag) plus `ConsoleAsker` (interactive prompting over injectable
  stdin/stdout, description shown unless terse, re-prompt on invalid input with
  the validator's message, empty input accepts the default unvalidated, secret
  fields read through an injectable no-echo reader) and `ScriptedAsker`
  (answers from a mapping; a missing required key raises `MissingAnswerError`
  naming the key — the `--non-interactive` contract — and an invalid scripted
  value raises `ScriptedAnswerError` with no re-prompt loop); both satisfy the
  frozen T1.1 `Asker` protocol unchanged and layer a `FieldSpec`-aware
  `ask_field` on top. Adds the never-save-invalid `guard_answers` helper.
  `answers.py` adds the `--answers FILE` seam: TOML (`tomllib`)/JSON load by
  extension with unknown-key collection (warned, not failed), secret-excluding
  save (a minimal stdlib TOML writer, since `tomllib` is read-only, plus JSON),
  and `require_non_interactive_answers` which reports every missing required
  key in one `MissingAnswersError` rather than the first. Adds an offline
  `tests/test_io_prompts.py` and `tests/test_io_answers.py` suite (FieldSpec
  validation/re-prompt/default/hint rendering, ScriptedAsker missing/invalid
  answers, secret no-echo + save exclusion, TOML/JSON round-trip, unknown-key
  warnings, all-missing-keys-at-once reporting, malformed-file errors, and the
  guard rejecting one invalid value in an otherwise-valid set).
- Implement the WAEGIS step engine core (task T1.1) under
  `05_Software/waegis/src/waegis/engine/`: the shared step contract
  (`StepSpec` with a required `verify`, `StepResult`, `Automation`/`Phase`/
  `StepStatus`, `Remediation`, the minimal `Asker` prompting protocol, the
  `EngineContext` with secret-free answer recording, and the `EngineEvent`
  types + `EventSink` through which the runner reports without printing);
  `Catalog` registration with duplicate-id/unknown-precondition/cycle rejection
  and stable precondition-aware ordering plus `applies()` filtering; the
  plan-preview data model (`Plan`/`PlannedStep`); the runner loop (plan preview
  → approval gate → per-step detect/act/verify, assisted-step confirmation,
  failure-stop with `on_fail`, `--dry-run`, resume seeding); and the checkpoint
  `Journal` (one JSON per run under the WAEGIS home — `WAEGIS_HOME` /
  `%APPDATA%\waegis` / `~/.config/waegis` — with round-trip load and green-step
  resume). The engine depends only on the standard library and itself. Adds an
  offline engine test suite (toy 3-step catalog: full green run, detect-skip
  re-run, act-failure surfaces `on_fail` and stops, verify-after-act,
  assisted-without-confirmation, dry-run mutates nothing; catalog validation and
  `applies()` filtering; journal round-trip, resume, and `WAEGIS_HOME` override).
- Scaffold the WAEGIS guided wizard as a new stdlib-only package under
  `05_Software/waegis/` (task T0.1): `pyproject.toml` (name `waegis`, version
  0.1.0, no runtime deps, `waegis` script, pytest config), the §12 module
  skeleton with compliant headers, `version.py` carrying the wizard version and
  the compatible AEGIS payload range `>=0.4.0,<1.0` (AD-11), a `waegis` CLI
  whose planned subcommands (`new`, `adopt`, `analyze`, `doctor`, `upgrade`,
  `version`, `self-update`, `gui`) are stubs that exit 2 "not implemented", a
  README stub, and smoke/version tests. WAEGIS is never copied into the AEGIS
  payload.
- Amend the root `AGENTS.md` repository and validation rules to name both the
  `05_Software/aegis/` and `05_Software/waegis/` packages, and update the root
  `README.md` layout and pointers to mention WAEGIS.
- Add `00_Planning/WAEGIS_Wizard_Implementation_Plan.md`, the task-by-task
  implementation plan for the WAEGIS guided configuration and deployment
  wizard (new-project and existing-project journeys, install manifest,
  `analyze`/`doctor`/`upgrade` lifecycle, self-contained packaging).
- Add first-class Intent Alignment support with an `alignment` CLI command,
  `[alignment]` workflow policy defaults, independent standard/adoption stages,
  graph and journal persistence, status/report visibility, and shared
  development/adoption skill instructions.
- Add a Qwen Code adapter under `template/.qwen/` with `settings.json` (native
  `PreToolUse`/`PostToolUse` command hooks mapping to the shared `.agentic/hooks/`
  guards, `context.fileName` pointing at `AGENTS.md`, and secret/delivery permission
  denies), thin skill wrappers, `/workflow-*` command prompts, a README, and a
  `template/QWEN.md` adapter note.
- Add Qwen Code adapter parity tests and a `guard_write_zone` case for Qwen's
  `WriteFile` tool name.
- Add an OpenCode `aegis` primary agent and make it the project
  default agent so OpenCode loads the shared workflow discipline before
  behavior-changing work.
- Add a Python `dev` dependency group for `pytest` and `ruff` so validation
  tooling is managed by the project instead of global installs.

### Changed

- Refactor `02_Tools/create_project_from_template.py` into a thin wrapper
  over the WAEGIS payload copier (task T3.2). The public CLI (`target`,
  `--force`, `--dry-run`, `--existing-repo`), the refuse-overwrite default,
  the dry-run preview, the exit codes, and the printed
  "Copied/Would copy N template files" message are unchanged, with one new
  user-visible side effect: every real (non-dry-run) copy now also writes
  `<target>/.agentic/install-manifest.json` (mode `"new"`, or `"adopt"`
  under `--existing-repo`; payload version read from the template's
  `.agentic/cli/pyproject.toml`) — the enabler for
  `waegis analyze`/`doctor`/`upgrade`. `--dry-run` writes nothing, including
  no manifest, and the manifest is not counted in the printed N. Two
  behavior refinements: an overwrite refusal now happens before any file is
  written (previously files earlier in the walk were already copied when the
  refusal fired), and the `*.egg-info`/`.uv-cache*` exclusion patterns now
  exclude those directories' *contents* too (previously the directory was
  skipped but its files were still copied). The script's scaffold tests gain
  manifest-presence and dry-run-writes-no-manifest checks.

- Rebrand the project as **AEGIS** (Agentic Engineering Governance & Integrity
  System), forked from the `2026_AgenticDevelopmentWorkflowTemplate` codebase
  (history not carried over). The CLI command, Python package, and console
  entry point are now `aegis` (was `agentic-workflow` / `agentic_workflow`);
  the dev package directory is `05_Software/aegis/`. This is a breaking
  CLI-contract rename.
- Renumber the top-level repository layout to reserve `03_Hardware/` and
  `04_HardwareDocu/`: `04_Software/` -> `05_Software/` and
  `05_SoftwareDocu/` -> `06_SoftwareDocu/`. `02_Tools/create_project_from_template.py`
  and all documentation were updated to the new paths.
- Teach the shared `guard_write_zone` hook to recognize Qwen Code's `WriteFile`
  (and raw `write_file`/`replace`) tool names so the write-zone guard applies
  identically across the Codex, Claude Code, Pi, OpenCode, and Qwen Code adapters.
- Route OpenCode workflow command prompts through the `aegis` agent
  and document CLI command usage with `opencode run --command`.

### Fixed

- WAEGIS answers files: JSON is now decoded as `utf-8-sig`, so an answers
  file written by Windows PowerShell's `Out-File -Encoding utf8` (which
  prepends a BOM) loads the same as a BOM-less one
  (`05_Software/waegis/src/waegis/io/answers.py`; found during the T4.3
  real-console verification run).

## [0.4.0] - 2026-06-25

### Added

- Add an OpenCode adapter with `opencode.json`, native skill wrappers, command
  prompts, and a local plugin that maps OpenCode tool events to the shared
  `.agentic/hooks/` guard scripts.
- Add OpenCode adapter parity tests and Node unit tests for plugin hook
  decision parsing, protected-read blocking, and tool-event mapping.

## [0.3.0] - 2026-06-23

### Added

- Add existing-project adoption run kind and adoption-specific workflow stages.
- Add component manifest support for adopted component and bundle status.
- Add adoption CLI commands for baseline summaries, local scope checks, and
  component status reporting.
- Add the `agentic-adoption` shared skill plus Codex, Claude Code, and Pi
  adapter documentation for existing-project adoption mode.
- Add a worked planning example for adopting an existing repository without
  application behavior changes.
- Add explicit existing-repository and dry-run options to the template creation
  helper script.
- Add adoption delivery preflight blocking for application source changes unless
  adoption behavior changes are explicitly enabled.
- Validate component manifests in adoption commands, registry checks, and
  delivery preflight so invalid adoption baselines cannot appear clean.

### Changed

- Move workflow-owned component documentation defaults from `06_SoftwareDocu/`
  to `.agentic/knowledge/components/`.
- Sync the delivered and planning prompt cheatsheets with adoption-mode prompts.
- Refresh planning artifact-flow diagrams to show adoption artifacts, component
  maps, local scope checks, and `.agentic/knowledge/` documentation.
- Document existing-repository adoption usage for the template creation helper.
- Update the root README with adoption artifacts, worked examples, and
  existing-repository scaffold usage.

## [0.2.0] - 2026-06-21

### Added

- Add a Pi (pi.dev) adapter under `template/.pi/` as a third agent adapter
  alongside `.codex/` and `.claude/`. A TypeScript bridge extension maps Pi
  tool events onto the shared `.agentic/hooks/` guard scripts (reused
  byte-for-byte), and the Pi package manifest reuses `.agentic/skills/` through
  `pi.skills` with no skill duplication. Includes vitest specs and Python
  parity tests.

### Changed

- Relicense the project from AGPL-3.0 + Non-Commercial to the PolyForm
  Noncommercial License 1.0.0 (SPDX `LicenseRef-PolyForm-Noncommercial-1.0.0`).
  Replace `LICENSE.txt`, remove the now-redundant `LICENSE_NC.txt`, and update
  the legal headers across sources, documents, and configs. Commercial use
  requires a separate commercial license from DDP Engineering.
- Relocate the operator references (`PROMPT_CHEATSHEET.md`,
  `CLI_API_REFERENCE.md`, `How_To_Start_A_New_Project.md`,
  `WORKFLOW_CHEATSHEET.svg`) from the template root into `.agentic/documents/`.
- Exclude the `.pi/` adapter's install-on-demand `node_modules/` from the
  template scaffolder.
- Document Pi as the third adapter across the stack architecture and worked
  examples, and add versioning/changelog rules to the root `AGENTS.md`.

### Removed

- Remove the `.agentic/specs/` directory; run spec items are recorded in the
  run `graph.json`.

### Fixed

- Point the template hygiene tests (`test_scaffold`,
  `test_documentation_workflow`) at the relocated `.agentic/documents/`
  cheatsheet paths.

## [0.1.0] - 2026-06-17

### Added

- Bootstrap standalone `aegis` project structure.
- Add copyable AEGIS payload with `.agentic/` CLI, tools, hooks,
  requirements, policy, and workflow configuration.
- Add Codex adapter under `.codex/` with bundled workflow skills and hook
  bindings.
- Add Claude Code adapter under `.claude/` plus `CLAUDE.md`, using thin skill
  wrappers that reference the shared workflow instructions.
- Add component documentation convention under `06_SoftwareDocu/`, including
  template, documentation audit, and write-component-documentation support.
- Add requirement traceability, coverage, impact, invariant, delivery preflight,
  and report support in the Python CLI.
- Add repository scaffold helper under `02_Tools/`.
- Add planning architecture documents, worked examples, delivery prompt cheat
  sheet, and visual workflow cheat sheet SVG.
- Add DDP Engineering AGPL-3.0 plus Non-Commercial license files and legal
  headers.
