<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS

Status: the hardened CLI lifecycle is implemented: `new`, `adopt`, `analyze`,
`configure`, `doctor`, `repair`, `upgrade`, and `version`. Core implementation
through packaging exists, but release readiness remains open until the Ubuntu
and clean-machine lifecycle/archive journeys are recorded. Network
`self-update`, the GUI, and the AI advisor are deliberately deferred and are
not exposed in normal help.

The install manifest and checkpoint journal each have one current unreleased
layout, both numbered `1`. Current fields are mandatory; there is no reader,
migration, or version-bump path for earlier partial implementations.

**WAEGIS** is the guided wizard that configures and deploys the AEGIS platform
(the `05_Software/aegis/template/` payload) into a target repository, in a way a
person with no repo-setup knowledge can follow. It is a **separate package** from
the AEGIS payload and is **never copied into that payload** (AD-1).

The implemented command and lifecycle contracts are documented in this README
and beside their corresponding modules under `src/waegis/`. Historical task
plans are not required to operate or maintain the package.

Older source docstrings retain compact section and decision tokens such as
`plan §4`, `D12`, or `AD-9` as provenance labels. They do not point to a shipped
document and are not normative; the current code, tests, CLI help, and this
README define the supported behavior.

## Principles

- Stdlib-only, Python >= 3.11, offline-first; all subprocess and network access
  sits behind injectable runner interfaces so tests run offline (AD-3).
- Deterministic core; the optional AI advisor is proposed last and never
  required (AD-5).
- Every mutation is planned, previewed, and verified; runs are journaled and
  safe to abort and re-run (AD-8).

## Commands

```text
waegis new TARGET [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis adopt TARGET [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis analyze --repo PATH [--json]
waegis configure --repo PATH [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis doctor --repo PATH [--json]
waegis repair --repo PATH [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis upgrade --repo PATH [--answers F] [--dry-run] [--non-interactive] [--yes] [--json] [--payload PATH]
waegis version [--json]
```

`--json` always disables prompting and emits exactly one envelope with
`schema_version`, `command`, `status`, `exit_code`, `plan`, `result`, and
`messages`. A non-interactive mutation requires explicit `--yes`. Exit codes
are `0` success, `1` warning/approval or decisions required, `2` validation or
verification failure, and `3` operational/internal failure.

## Step engine (`src/waegis/engine/`, task T1.1)

Both journeys (`new`, `adopt`) are one ordered catalog of steps executed by a
single engine (plan §4). The engine depends only on the standard library and
itself — it never prints and never imports the `io/`, `probes/`, `payload/`,
`repo/`, or `commands/` layers.

- `step.py` — the contract: `StepSpec` (a step is data — `detect`/`act`/`verify`
  callables with `verify` required, so a verify-less step is unrepresentable),
  `StepResult`, the `Automation`/`Phase`/`StepStatus` enums, `Remediation`, the
  minimal `Asker` prompting protocol, the `EngineContext` passed to every step,
  and the `EngineEvent` types + `EventSink` the runner reports through.
- `catalog.py` — `Catalog`: registration with duplicate-id, unknown-precondition,
  and cycle rejection at construction; stable precondition-aware ordering;
  `applies(ctx)` filtering so one catalog serves both modes.
- `plan.py` — the plan-preview data model (`Plan`/`PlannedStep`), no formatting.
- `runner.py` — `run()`: build plan → preview → approval gate → per-step
  detect (skip if green) / assisted-confirm / act / verify; failure or decline
  stops the run and surfaces `on_fail`; `--dry-run` stops after the preview.
  A compatible incomplete resume seed is a hint only: every green step must
  pass its current `detect()` before it can be skipped.
- `journal.py` — one checkpoint JSON per run under the WAEGIS home
  (`WAEGIS_HOME` env override, else `%APPDATA%\waegis` on Windows, else
  `~/.config/waegis`): per-step timestamps and outcomes, non-secret answers, and
  artifacts. Secret values are never routed into a result, so they cannot be
  journaled. Completed journals are never resume candidates; incomplete runs
  additionally require command/catalog/target/answers/payload fingerprints.

Prompting and console/GUI rendering live outside the engine: T1.2 supplies the
`ConsoleAsker`/`ScriptedAsker`, and T1.3 supplies the event-driven renderer.

## Prompt and answers-file primitives (`src/waegis/io/`, task T1.2)

- `prompts.py` — `FieldSpec` (description/"why", example, detected default,
  validator, secret flag), ported from the proven ador-init design. Both
  askers below satisfy the frozen T1.1 `Asker` protocol (`confirm`/`ask`)
  unchanged and additionally expose `ask_field(spec)`, a `FieldSpec`-aware
  entry point layered on top rather than a protocol change:
  - `ConsoleAsker` — interactive prompting over injectable `stdin`/`stdout`
    (tests never touch a real terminal). Shows the description unless terse,
    shows the example and detected default inline, re-prompts on invalid input
    with the validator's message, and accepts the default unvalidated on empty
    input. Secret fields are read through an injectable no-echo reader
    (`getpass.getpass` by default) and the raw value is never written to
    stdout.
  - `ScriptedAsker` — answers from a preloaded mapping. A missing required key
    raises `MissingAnswerError` naming the key (the `--non-interactive`
    contract); an invalid scripted value raises `ScriptedAnswerError` — there
    is no operator to re-prompt in scripted mode.
  - `guard_answers` — the never-save-invalid guard: validates a complete
    answer set against a list of `FieldSpec`s and refuses to proceed/persist
    (raising `InvalidAnswersError` with every offending key) when any value is
    invalid.
- `answers.py` — the `--answers FILE` seam (AD-9): `load_answers_file` reads
  TOML (`tomllib`) or JSON by extension; `unknown_keys` collects (never fails
  on) keys the current catalog does not expect; `save_answers_file` excludes
  every `secret` field by construction; `require_non_interactive_answers`
  reports every missing required key in one `MissingAnswersError`, not just
  the first.

## Console renderer and reports (`src/waegis/io/console.py` and `reports.py`, task T1.3)

Rendering and reporting live outside the engine (the engine never imports
`io/`); both modules only read the plan/result/event data T1.1 defines.

- `console.py`:
  - `render_plan_preview(plan, stream)` — the "terraform plan"-style step
    table (id, title, phase, automation, change) the operator approves before
    any mutation; `--dry-run` stops right after this render.
  - `LiveStatusRenderer` — an `EventSink` that renders each step's
    `pending -> running -> detected-skip/done/failed` transition as the
    runner's event stream arrives. Uses the plain-ASCII marker set
    (`[OK]`/`[FAIL]`/`[SKIP]`/`[..]`) by default; a richer glyph set
    (`✓`/`✗`/`⏭`/`…`/`○`) is used only when a caller explicitly opts in
    (`use_glyphs=True`), and every write is checked against the target
    stream's reported encoding, falling back to ASCII per call so a Windows
    console without a UTF-8 code page can never see a `UnicodeEncodeError` or
    mojibake.
  - `plan_preview_json`, `step_result_json`, `run_summary_json` /
    `run_summary_to_dict` — the `--json` twins (the WADORE seam, frozen per
    plan §15 D13): the plan-preview and step-result shapes serialize the
    existing `Plan`/`StepResult` `to_dict()` verbatim; the run-summary shape
    (`mode, dry_run, ok, stopped_at, results`) is new here since `RunSummary`
    itself has no `to_dict`.
- `reports.py`:
  - `render_environment_report` / `environment_report_json` — renders
    probe-style findings (`{findings: [{name, status, detail, guidance}]}`).
    This task defines only the rendering shape, built against a small
    structural `ProbeFinding` protocol; T2.1/T2.2 supply real probe results.
  - `BlockingPointReport`, `render_blocking_point_report`,
    `blocking_point_report_json` — the IT-forwardable blocking-point template
    (plan §4/§12, R7) for a step the wizard could not complete itself: what
    was attempted (the exact command), what happened (the exact error), why
    the wizard needs it, a copyable "ask IT" request, and the alternative
    paths — in a fixed order, human and JSON
    (`{step_id, title, attempted, what_happened, why, it_request,
    alternatives}`).

M1 acceptance (plan §13): `tests/test_engine_end_to_end.py` runs the toy
3-step catalog to completion both interactively (`ScriptedAsker` + the console
renderer) and via an answers file, then re-runs it against the same journal
and confirms every step detects-and-skips.

## Machine/tool probes (`src/waegis/probes/`, task T2.1)

No probe module calls `subprocess` directly; every probe accepts an
injectable runner, so the whole probe suite stays offline in tests.

- `runner.py` — `CommandRunner` (protocol) and `SubprocessCommandRunner` (the
  real implementation, ported from the ador `doctor.py` design). `run(argv,
  *, timeout=5.0)` returns a `CommandResult` whose `found` flag distinguishes
  "the executable does not exist" from "the executable ran and exited
  non-zero" — the distinction the python probe's fallback order depends on.
  `combined_output()` joins stdout+stderr since some tools (older Python,
  some `py` launcher variants) print `--version` text to stderr instead of
  stdout.
- `machine.py` — `probe_os_support()` (OS + release vs the plan §8.1 support
  matrix: Windows 11, Ubuntu 22+; outside the matrix is always `"warn"`, never
  `"fail"`, per plan §8.1/§10.1), `probe_architecture()` (informational),
  `probe_disk_space(path, *, minimum_bytes)` (`"fail"` below the caller's
  minimum — disk space genuinely blocks deployment, unlike the OS check).
  Reads `platform.system()`/`platform.release()`/`platform.machine()` and
  `shutil.disk_usage()` directly (no wrapper) so tests monkeypatch those
  functions and pass identically on Windows and Linux CI.
- `tools.py` — `probe_python(runner)` tries `py -3`, `python3`, `python` in
  that order (plan §8.1 `prereq.python`), falling through a candidate that is
  not found or exits non-zero, verdict >= 3.11; `probe_git(runner)` (>= 2.30);
  `probe_uv(runner)` (optional — absence is `"info"`, never a failure).
  Version parsing tolerates real-world output shapes (`git version
  2.43.0.windows.1`, `Python 3.11.9`, `uv 0.4.18`) and degrades to a `"warn"`
  finding rather than raising when output does not match. Each blocked/missing
  case carries OS-keyed install guidance with a concrete `winget`/`apt-get`
  command (generic fallback for other operating systems).

Every probe returns a `waegis.io.reports.ProbeFindingRecord` directly (no
adapter needed) so results slot straight into `render_environment_report` /
`environment_report_json` (T1.3).

- `network.py` (task T2.2) — the network subset of the analysis doc's
  corporate-restriction probe matrix (proxy, TLS interception, generic host
  reachability; package-manager/WSL/admin-rights probes are out of scope
  here). No probe module calls `socket`/`ssl`/`winreg` directly: `Transport`
  (protocol) + `SocketTransport` (real implementation) is the injectable seam
  for `connect(host, port, *, use_tls, timeout=5.0) -> ConnectResult`
  (`connected`/`timed_out`/`refused`/`dns_failure`, plus peer-certificate
  issuer/subject when TLS succeeded); `RegistryReader` + `WinInetRegistryReader`
  is the equivalent seam for the best-effort Windows system-proxy registry
  read. `probe_proxy_configuration(env, *, registry=None, transport=None,
  target=None)` checks `HTTP_PROXY`/`HTTPS_PROXY` env vars (fixed precedence
  order so conflicting casings resolve deterministically) before falling back
  to the registry, and only attempts a direct-vs-proxied connectivity check
  when both `target` and `transport` are explicitly supplied.
  `probe_tls_interception(transport, host, port=443)` compares the presented
  certificate's issuer against a list of known public CA name fragments and
  reports a mismatch as "possible TLS interception", naming the issuer.
  `probe_host_reachability(transport, host, port)` reports
  reachable/timed-out/refused/DNS-failure with guidance text keyed to the
  failure kind (not per-OS — these are network conditions). Offline-first is
  structural, not just tested: every function requires an explicit host and
  an explicit transport/registry with no defaults, so nothing in this module
  can open a real socket or registry handle unless the caller passes one.
  `to_blocking_point_report(finding, *, step_id, title, attempted, why,
  alternatives=...)` maps a failed finding directly onto
  `waegis.io.reports.BlockingPointReport` with no changes needed to
  `reports.py`.

## Install manifest (`src/waegis/payload/manifest.py`, task T3.1)

The frozen schema-v1 `.agentic/install-manifest.json` contract (plan §6,
AD-6) that every wizard copy writes and that `analyze`/`doctor`/`upgrade`
depend on:

- `Manifest`/`FileEntry` — the data model: `manifest_version, product,
  payload_version, installed_at, installed_by, mode, files, generated,
  skipped, payload_digest, configuration`, in that field order in the serialized
  JSON. `files` maps a repo-relative POSIX path to its original as-shipped
  `{sha256, size}`.
- `hash_file` — byte-exact sha256: binary-mode reads with no newline
  translation, so a byte-identical copy (however it was made, on whatever
  OS) reproduces the same hash, while bytes that actually differ (e.g. a
  CRLF rewrite of an LF original) hash differently.
- Managed paths are repository-relative and confined. Traversal, absolute,
  drive/UNC paths, repeated separators, normalization/case collisions, and
  source or destination symlink/reparse-point escapes are rejected.
- `build_manifest` / `write_manifest` / `read_manifest` — build a manifest by
  hashing a caller-supplied file list, then write it as 2-space
  pretty-printed JSON with a stable sorted `files` key order, or read one
  back. The manifest never lists itself and is excluded from any hashing the
  caller does. `installed_by` defaults to `f"waegis {WIZARD_VERSION}"` read
  from `waegis.version` at call time.
- `manifest_from_dict` — schema validation: rejects a missing required
  top-level key, an unknown `manifest_version`, or a malformed per-file entry
  (missing `sha256`/`size`) with an error naming the offending key rather
  than silently coercing it.
- `compute_drift` — local-vs-manifest-original drift: `modified` (hash
  differs from the recorded original) and `missing` (recorded file no longer
  on disk) only. A file on disk the manifest never recorded is deliberately
  ignored here — that "extra" case needs a *new* payload's file list to
  detect and belongs to T3.2/T6.2.
- `load_manifest` / `ManifestState` — the absent/invalid/valid tri-state
  callers (`analyze`, `doctor`, `upgrade`) branch on, so a repo with no
  manifest yet (`ABSENT`) is never confused with one whose manifest exists
  but fails to parse/validate (`INVALID`).

This module is pure data per the `io/` convention (T1.3): it never prints;
callers render.

## Payload copier and locator (`src/waegis/payload/copier.py` and `locate.py`, task T3.2)

The copy step both wizards run: absorbs the proven safe-copy semantics of
`02_Tools/create_project_from_template.py` (which is now a thin wrapper over
this module) and emits the T3.1 install manifest on every real copy.

- `locate.py` — payload resolution per plan §5: an explicit `--payload` path
  wins but is validated first (`InvalidPayloadError` unless it contains the
  `.agentic/workflow.toml` marker); application archives use their sibling
  `payload` directory and a standalone zipapp extracts its embedded payload
  into a content-addressed per-user cache; the final fallback is the
  repo-checkout template at `05_Software/aegis/template/`. `PayloadNotFoundError`
  is raised when nothing resolves. `read_payload_version` reads the payload's own version from
  `.agentic/cli/pyproject.toml` `[project].version`, degrading to `None`.
- `copier.py` — `copy_payload(payload_root, target, *, mode, ...)`:
  - **Byte-verbatim**: every file is copied with `shutil.copy2` (binary, no
    newline translation), so the copied file's `hash_file()` always equals
    the source's — proven by a direct hash-equality test, and the reason the
    manifest (hashed at the target) records the as-shipped hashes.
  - **Exclusions**: the shared `should_exclude` predicate ports the legacy
    rules (`__pycache__`, `.pytest_cache`, `.ruff_cache`, `node_modules`,
    `.vitest`, `*.pyc`, `*.egg-info`, `.uv-cache*`), with one fix: glob
    patterns match every path component, so files *inside* a `*.egg-info` /
    `.uv-cache*` directory are excluded too (the legacy predicate skipped
    the directory but still copied its contents).
  - **Strict new-project mode** (no hook, no force): any pre-existing
    destination file raises a typed `OverwriteRefusedError` naming the path —
    exact legacy parity, including refusing on byte-identical files and on
    dry-run.
  - **Adoption mode** (`on_conflict` hook supplied): each payload file is
    classified does-not-exist (copied) / exists-identical (left in place,
    still recorded in the manifest `files` since content matches) /
    exists-different (a conflict). **A conflict is never resolved
    internally**: the caller-supplied `ConflictDecisionHook` is called
    exactly once per conflict (never for identical or missing files) and
    returns keep-local / take-payload / write-new (payload written verbatim
    as `<name>.new` beside the kept local file). `force=True` is the legacy
    override, implemented as an internal constant take-payload hook;
    combining it with a caller hook raises `ValueError`.
  - **No partial writes**: scan/classify/decide (including every hook call)
    is read-only and completes before the apply phase, so a refusal, an
    invalid hook return, or a hook exception leaves the target untouched.
  - **Dry-run** returns the would-be copied list and the classified conflict
    list without calling the hook and without writing anything (no manifest).
  - **Manifest emission**: `build_manifest`/`write_manifest` (T3.1) write
    `<target>/.agentic/install-manifest.json` with `files` = every
    payload-sourced file present at the target, `skipped` = keep-local and
    write-new decisions, `generated` passed through from the caller (T4.1
    extends it), and `payload_version` read from the payload itself
    (fallback `"unknown"`). Sidecar `.new` files are not manifest entries;
    a manifest shipped inside a payload source is never copied.
  - Returns a structured `CopyResult` (copied / identical / conflicts /
    resolutions / skipped / manifest); the module never prints, imports no
    network code, and touches nothing outside the payload root (read) and
    target root (write).

## `waegis analyze` (`src/waegis/commands/analyze.py`, task T3.3)

The read-only reporting command (plan §5/§10.1): manifest inventory + drift +
"which workflows are installed", with **no health verdicts** — that is
`doctor`'s job (T6.1). A thin reporting layer over T3.1's
`load_manifest`/`compute_drift`; it never reimplements manifest parsing or
drift computation.

- `run_analyze(repo, *, as_json, stream)` — validates `--repo` exists and is a
  directory (the one genuine operational failure this command has, exit 1);
  otherwise always exits 0, since a missing manifest, an invalid manifest, or
  drifted files are informational findings, not command failures, at this
  command's level.
- `build_analyze_report(repo)` — pure data computation, separable from
  rendering: distinguishes the three manifest states
  (absent/invalid/valid), computes drift only when the manifest is valid, and
  inspects `.agentic/` plus every known agent adapter directory
  (`.claude`, `.codex`, `.opencode`, `.pi`, `.qwen` — cross-checked by test
  against the real `05_Software/aegis/template/` directory so the list cannot
  silently drift).
- `render_analyze_report` — plain-ASCII human report (counts only for drift);
  `analyze_report_json` — the frozen `--json` shape (full modified/missing
  file lists), a new WADORE-relevant surface:
  `{repo, manifest: {state, error, product, payload_version, installed_at,
  installed_by, mode, file_count, generated_count, skipped_count},
  drift: {modified, missing} | null, inventory: {agentic_present, adapters}}`.
  `drift` is `null` unless `manifest.state == "valid"`.

CLI wiring (`src/waegis/cli.py`): `analyze` is the first subcommand to get its
own subparser (`--repo` required, `--json` flag) instead of the generic
not-implemented stub; every other subcommand's stub registration and exit
code (2) are unchanged.

## workflow.toml generator (`src/waegis/repo/workflow_toml.py`, task T4.1)

The single generator serving both `waegis new` and `waegis adopt` (only the
answer *source* differs — interview vs. analysis proposals). It rewrites the
real template `.agentic/workflow.toml` rather than emitting a file from
scratch, and enforces every plan §7 invariant before returning.

- `WORKFLOW_FIELD_SPECS` — the plan §7 answer table as `FieldSpec`s
  (`source_roots`, `test_roots`, `language`, `gate_test_cmds`,
  `gate_lint_cmds`, `alignment_enabled`), composing directly with
  `ConsoleAsker`/`ScriptedAsker.ask_field` and `guard_answers` (T1.2). The
  shared validators accept both console strings (comma-separated roots,
  yes/no booleans) and typed answers-file values.
- `LANGUAGE_PRESETS` — a structured table (`LanguagePreset` dataclass per
  entry: `python`, `typescript`, `javascript`, `java`, `csharp`, `go`,
  `rust`, `cpp`) supplying `[traceability].language`, `source_extensions`,
  and `test_file_patterns`; adding a language is one dict entry. `"other"`
  has no preset and requires explicit extensions/patterns
  (`LanguagePresetError` otherwise — invariant 6); explicit values override
  the preset for any language (the colocated-tests escape hatch, D12).
- `generate_workflow_toml(base_toml_text, *, ...) -> GeneratedWorkflow` —
  pure text-in/text-out (the calling step reads the base file, writes the
  result, and owns `.gitkeep` creation for missing roots). **Rewrite
  strategy: targeted text substitution** — a section-aware line scanner
  replaces only the twelve generator-owned keys (`source.roots`,
  `tests.roots`, the four `[traceability]` keys, `gates.test/lint`,
  `alignment.enabled`, `write_zones.check/implementation/component-adoption`);
  every other line, comments included, passes through **byte-identical**
  (proven by exact string-slice tests). Comments are preserved, not
  regenerated.
- Invariants (plan §7) are enforced on the **re-parsed** output before the
  function returns (never-save-invalid guard, invariant 5): every source
  root as `<root>/**` in implementation and verbatim in `coverable_roots`
  (1); every test root as `<root>/**` in check and component-adoption (2);
  implementation always contains `.agentic/knowledge/components/**` (3);
  everything else byte/value-identical to the base (4). Violations raise
  `InvariantViolationError` naming the invariant.
  `verify_workflow_invariants` (invariants 1–3 on any parsed document) is
  public for reuse by `waegis doctor` (T6.1).
- Empty gates generate successfully but return structured `GateWarning`
  records naming each empty gate ("will pass without checking anything") —
  the calling step (T4.3) journals/prints them; the module never does.

## Git operations (`src/waegis/repo/gitops.py`, task T4.2)

Small, typed git primitives over the T2.1 `CommandRunner`, used by the
`repo.target-path`/`repo.init-or-clone`/`repo.initial-commit` steps (T4.3)
and reused by the adoption branch (T5.2). Every call shapes as `git -C
<path> <subcommand> ...` — git's own `-C` flag supplies the working
directory as an argv element, so the shared `CommandRunner` Protocol needed
no extension for this task.

- `is_work_tree(runner, path) -> bool` — never raises; not-found or
  non-zero both report `False`.
- `ls_files(runner, path) -> list[str] | None` (task T5.1) — `git ls-files
  -z` (NUL-separated, avoids git's quoting of non-ASCII names); returns the
  tracked-path list (empty for a fresh repo), or `None` for any expected
  failure (git missing, not a work tree). The `None`-vs-`[]` distinction lets
  the T5.1 inventory decide whether to fall back to a filesystem walk.
- `init_repo(runner, path, *, initial_branch="main") -> GitOpResult` — tries
  `init -b <branch>` first; falls back to plain `init` + `symbolic-ref HEAD`
  when git's own stderr shows `-b` is unrecognized (older git), detected
  from the real error text rather than a probed version string.
- `clone_repo(runner, url, path) -> GitOpResult` — pre-checks a non-empty
  target directory itself (uniform error, zero git invocations) before ever
  calling the runner; otherwise passes git's own clone failure through.
- `get_identity(runner, path) -> GitIdentity` / `set_identity(runner, path,
  name, email, *, local=True) -> GitOpResult` — `GitIdentity.name`/`.email`
  are each `None` when unset (three representable states: both, one,
  neither); reads via plain `git config` (repo-local falling through to
  global, git's own resolution); writes default to `--local` and require an
  explicit `local=False` to write `--global`.
- `status_porcelain(runner, path) -> list[str]` — raw non-empty
  `status --porcelain` lines, unparsed (the one current caller only needs
  emptiness or a raw line; a per-status-code parser would be speculative).
- `add_all` / `commit` / `create_branch(runner, path, name, *,
  checkout=True)` — thin, argv-exact wrappers (`add -A`, `commit -m
  <message>` with the message as a single argv element, `checkout -b
  <name>` or `branch <name>`); `create_branch` raises `ValueError` on an
  empty name (a programmer error), never on a git failure.

All functions return `GitOpResult`/`GitIdentity`/`bool`/`list[str]`/
`list[str] | None`, never a raw `CommandResult`; no function raises for an
expected git failure.

## Repo analysis heuristics (`src/waegis/repo/analyze.py`, task T5.1)

The Wizard E (`waegis adopt`) analysis engine the `analyze.repo` step (T5.2)
calls (plan §9). **Deterministic, read-only, ranked proposals** — this module
produces data and a renderer; it never decides, writes, executes a candidate
command, or mutates the target repo. Distinct from
`src/waegis/commands/analyze.py`, which is the manifest/drift report for the
`waegis analyze` command (T3.3).

- `analyze_repo(repo, *, runner) -> RepoAnalysis` — the entry point:
  `collect_inventory` then `analyze_inventory`. `collect_inventory` prefers
  `gitops.ls_files`; when git is absent/not a work tree it walks the
  filesystem honoring the **top-level `.gitignore` only** (simplified glob
  matching — a documented scope limit, not full git-ignore semantics).
  `analyze_inventory(repo, inventory)` is the injectable seam the
  very-large-repo test uses (synthetic `Inventory`, no files materialized).
- **Language ranking** — extension histogram weighted by both file count and
  total bytes, plus a per-family build-marker boost. The top `language` is
  always an exact `workflow_toml.LANGUAGE_PRESETS` key (or `"other"`), so the
  T5.2 handoff into `generate_workflow_toml` never hits a name mismatch.
- **Build systems** — presence of pyproject/setup, package.json (+ lockfiles),
  Maven, Gradle, CMake, Cargo, go.mod, `*.csproj`/`*.sln`, Makefile,
  Dockerfile; each contributes to ranking and to gate extraction.
- **Source/test roots** — `RootProposal`s (path + confidence + provenance
  reason). Conventions first (`src/main/java` and `src/test/java` before
  generic `src`; Go `cmd`/`pkg`/`internal`; Swift `Sources`; Python packages
  with `__init__.py`; `tests`/`test`/`spec`/`__tests__`); a
  >= 90%-coverage top-level-dir fallback (low confidence) when nothing matches.
  Each `.path` passes `workflow_toml.normalize_roots` unchanged.
- **Colocated tests** — files matching the top language's preset
  `test_file_patterns` sitting outside every detected test root (e.g.
  `*_test.go`) raise `ColocatedTests(detected=True, …)` with the plan D12
  note that write zones must become file-pattern-based; T5.2 decides how to
  act.
- **Gate candidates** — `GateCandidate` carries structured provenance
  (`source_file` + `source_detail`), the verbatim `raw` string, and the §7
  argv shape (`list[list[str]]` per `gate_test_cmds`/`gate_lint_cmds`).
  Sources: package.json `scripts.test`/`scripts.lint` (as the
  lockfile-selected package-manager invocation), `pyproject.toml`
  pytest/ruff config sections, `Makefile` `test:`/`lint:` targets
  (`make <target>`), and CI `run:`/`script:` lines (line-scanned, no YAML
  parser). Never executed; a shell-syntax line `shlex` cannot safely split
  becomes `argv=None`, `needs_review=True` ("manual review required")
  instead of a wrong argv. CI lines matching neither test nor lint keywords
  are dropped.
- **Adoption risk flags** — reuse the `io/reports.py` `ProbeFindingRecord`
  shape: `risk.submodules`, `risk.lfs`, `risk.monorepo`, `risk.large-repo`
  (> 10,000 files, heuristic-only warning — never refuses to run),
  `risk.prior-install` (`.agentic/` or an adapter dir, manifest presence
  noted), and a per-file `risk.guaranteed-conflict` (status `"conflict"`) for
  a pre-existing root `AGENTS.md`/`CLAUDE.md` (never overwrite — detection
  only; the copier + T5.2 own resolution).
- `render_repo_analysis` / `RepoAnalysis.to_dict` / `repo_analysis_json` —
  the same render/to_dict/json trio used across `io/reports.py` and
  `commands/analyze.py`; the `--json` field names are a frozen contract
  (plan D13).
- `ADAPTER_DIR_NAMES` lives here now as the single source of truth
  (`.claude/.codex/.opencode/.pi/.qwen`, cross-checked against
  `05_Software/aegis/template/`) and is re-exported by
  `commands/analyze.py`.

## `waegis new` (`src/waegis/commands/new.py`, task T4.3)

The Wizard N journey (plan §8.1): every step of the table registered as a real
`StepSpec` over the shared engine, executed as
`waegis new TARGET [--answers F] [--dry-run] [--non-interactive] [--json]
[--payload PATH]`.

- **Catalog** — 18 steps in execution order (`home.init`, `machine.os`,
  `machine.disk`, `prereq.python`, `prereq.node`, `prereq.git`, `prereq.git-identity`,
  `net.proxy`, `repo.target-path`, `repo.init-or-clone`,
  `deploy.payload-copy`, `deploy.workflow-toml`, `deploy.gates`,
  `verify.cli-smoke`, `verify.workflow-smoke`, `verify.hooks-present`,
  `repo.initial-commit`, `handoff.summary`), preconditions chained linearly in
  table order so the P0→P5 phase order is structural. `net.proxy` `applies()`
  only when a `clone_url` answer requests a remote clone (T2.2's real proxy
  probe is wired in; a local `git init` flow skips the step entirely).
- **Documented step decisions** — `machine.os` is report-only
  (warn-not-block); `machine.disk` fails verification only below the 1 GiB
  minimum (a true blocker); `prereq.python`/`prereq.git` never run privileged
  installs (the wizard shows the probe's OS-keyed command, waits, and
  re-probes); `prereq.git-identity` accepts a pending repo-local identity from
  the `git_user_name`/`git_user_email` answers, applied by
  `repo.init-or-clone` right after `git init`; `verify.workflow-smoke` accepts
  the embedded CLI's coherent "No active agentic run" response as the healthy
  fresh-install outcome (the real CLI exits non-zero on `status` before any
  run is started); `repo.initial-commit` proves a commit exists via
  `gitops.head_commit` (an empty porcelain status alone is also what a failed
  git call produces).
- **Manifest amendment** — `deploy.payload-copy` writes the manifest via
  `copy_payload`; only after `deploy.workflow-toml` actually rewrites
  `workflow.toml` from answers is the manifest re-read and the path moved from
  `files` into `generated`, keeping the manifest truthful at every checkpoint,
  drift reports clean, and re-run detect green.
- **Smoke invocations** (confirmed against the real scripts, run with
  `cwd=TARGET` because the embedded CLI resolves its repo root from the
  working directory): Windows `powershell -NoProfile -ExecutionPolicy Bypass
  -File .agentic\tools\run.ps1 ...`; POSIX `bash .agentic/tools/run.sh ...`
  (the script requires bash, not `sh`).
- **Command seam** — `--non-interactive` validates the answers against the six
  workflow FieldSpecs with their interactive defaults stripped (a
  machine-driven run must pin the configuration explicitly) and fails before
  the engine or journal starts, naming every missing key at once; `--answers`
  without `--non-interactive` uses the answers first and prompts for the rest;
  `--dry-run` stops after the plan preview and writes nothing (no journal);
  `--json` emits exactly one common command envelope. Only a fingerprint-matched
  incomplete run can replay non-secret answers, and every step is re-detected;
  completed runs always start a fresh detection pass.

## `waegis adopt` (`src/waegis/commands/adopt.py`, task T5.2)

The Wizard E journey (plan §8.2): deploy the AEGIS payload into an *existing*
repository, resolving payload/local conflicts file by file. Same CLI shape as
`waegis new` (`waegis adopt TARGET [--answers F] [--dry-run] [--non-interactive]
[--json] [--payload PATH]`).

- **Shared, not forked** — the P0–P2 machine/prereq/network prefix, the
  `deploy.gates` step, and the three `verify.*` smoke steps are the **same**
  `StepSpec` objects Wizard N runs (`commands/new.py` exposes them as
  `COMMON_PREFIX_STEPS`, `GATES_STEP`, `VERIFY_STEPS`, sliced from one ordered
  step list). `net.proxy` `applies()` is false for adopt (no clone URL), so it
  is filtered out. `deploy.workflow-toml` reuses Wizard N's shared
  detect/verify/on_fail with an adopt-specific `act`.
- **Catalog** — 19 steps in execution order: the shared prefix (including
  `prereq.node`), then
  `repo.validate-existing`, `repo.prior-install`, `analyze.repo`,
  `deploy.adoption-copy`, `deploy.workflow-toml`, `deploy.gates`, the three
  `verify.*` steps, `repo.adoption-commit`, `handoff.adoption`.
- **Prior-install routing** — `repo.prior-install` routes four ways, which
  `ManifestState` (three values) alone cannot: it collapses "no `.agentic`" and
  "bare `.agentic` without a manifest" both into `ABSENT`, so the step adds an
  explicit `.agentic` directory check. Routes: `none` (continue); `current`
  (manifest at the bundled version → suggest `waegis doctor`, confirm
  continue/stop); `older` (different version → suggest `waegis upgrade`, confirm
  continue/stop); `legacy` (`.agentic` without a usable manifest → conservative
  path, no fast-path skip in `deploy.adoption-copy`). Declining "continue" stops
  the run before the copy.
- **Proposals, never auto-applied** — `analyze.repo` renders T5.1's read-only
  `analyze_repo` output and confirms **each** proposed field
  (`source_roots`/`test_roots`/`language`/`gate_test_cmds`/`gate_lint_cmds`/
  `alignment_enabled`) via `ctx.asker`/FieldSpec seeded from the proposal (gate
  provenance surfaced). A scripted answer overrides its proposal; the confirmed
  answers — not the proposals — feed `deploy.workflow-toml`.
- **Conflict resolution** — `deploy.adoption-copy` is the first real caller of
  the copier's ADOPTION mode: it drives the `ConflictDecisionHook` from
  `ctx.asker` (per-file keep-local / take-payload / write-`.new`) or from a
  pre-supplied `adoption_conflicts` answer table (`{path: decision}`), journals
  each decision, and verifies each was applied on disk exactly as chosen.
- **Adoption branch** — `repo.adoption-commit` creates `chore/aegis-adoption`
  (override via the `adoption_branch` answer) and commits the installed payload
  and generated configuration; `handoff.adoption` prints the real
  adoption-intake operator prompt extracted from the copied
  `PROMPT_CHEATSHEET.md` (so it cannot drift), names the present agent adapters,
  and states that WAEGIS's job ends there — the in-repo `agentic-adoption`
  workflow takes over.
- **Command seam** — the read-only analysis is pre-computed once so
  `--non-interactive` reports every *unproposable* required key at once
  (`source_roots`/`test_roots` when the analysis proposed none, plus the two
  `other`-language extras) before the engine starts; `--answers`/`--dry-run`/
  `--json`/resume behave exactly as in Wizard N.

## `waegis doctor` (`src/waegis/commands/doctor.py`, task T6.1)

The health-verdict diagnostic (plan §10.1): `waegis doctor --repo PATH
[--json]`. Unlike `waegis analyze` (read-only, no verdicts, exit reflects
only whether the report could be produced), doctor attaches an
`ok`/`warn`/`fail` verdict to every finding and exits the **worst** one found:
0 healthy, 1 warnings-only, 2 at least one failure (a `--repo` that does not
exist or is not a directory returns a distinct exit code, 3, so it can never
be misread as a health verdict). Every group reuses the same building blocks
`analyze`/`new`/`adopt` already established rather than reimplementing them:

- **Machine** — re-runs `probe_os_support`, `probe_disk_space`,
  `probe_python`, `probe_git`, `probe_uv` (T2.1's tool/machine probes; no
  network probe belongs to any doctor group per the plan §10.1 table).
- **Manifest** — a four-way state, mirroring T5.2's `repo.prior-install`
  routing since `ManifestState` alone cannot tell "never installed" from
  "legacy pre-manifest install" apart: `valid` (`ok`), `invalid`/corrupt
  (`fail`), legacy (`.agentic` present, no manifest; `warn`), none (`warn`).
  Plus `manifest.update-available`: the installed `payload_version` compared
  against the currently bundled payload's real version (`warn` when the
  bundled payload is strictly newer).
- **Drift** — reuses `compute_drift`; any modified/missing file is `warn`,
  never `fail` (drift alone does not mean broken). The full modified/missing
  lists are `--json`-only; the human view shows counts (mirrors `analyze`'s
  verbosity split).
- **workflow.toml** — parses via `tomllib` (`fail` if it cannot); every
  configured `[source].roots`/`[tests].roots` entry exists on disk (`warn`
  per missing root); write-zone alignment via `repo/workflow_toml.py`'s
  `verify_workflow_invariants`, re-used exactly rather than reimplemented
  (`fail` if it raises — a real foreign/manual edit on an *installed* repo,
  unlike T4.1's generation-time guard which prevents this at the source);
  `[gates].test`/`[gates].lint` non-empty (`warn` each if empty);
  `[components].manifest` path exists (`warn` if configured but missing).
- **Runnability** — wrapper scripts (`run.ps1`/`run.sh`) present (`fail` if
  either is missing) and the platform-appropriate one answers `--help` with
  exit 0 through the injected `CommandRunner` (`fail` otherwise); the four
  core hook files present (`fail`); known agent adapter directories present
  (`warn` per missing one). Reuses `commands/new.py`'s
  `_wrapper_invocation`/`HOOK_FILES` rather than re-deriving the invocation
  shape; the fail/warn severity split is doctor-specific (new.py's own
  `verify.hooks-present` collapses both into one undifferentiated check).
- **Journal** — the most recent `Journal` recorded for this `--repo` path:
  completed (`ok`), stopped mid-run (`warn`, names the stopping step), no
  prior run at all (`ok` — informational absence, not a failure).

`--json` shape (frozen, new): `{repo, overall_status, exit_code, groups:
{machine, manifest, drift, workflow_toml, runnability, journal}}`, where each
group is a list of `{name, status, detail, guidance}` findings except `drift`,
which additionally carries the full `modified`/`missing` file lists
(`{findings, modified, missing}`) — a deliberate, documented exception to the
otherwise-uniform group shape.

## `waegis upgrade` (`src/waegis/commands/upgrade.py`, task T6.2)

The three-way, manifest-driven payload upgrade (plan §10.2): `waegis upgrade
--repo PATH [--dry-run] [--json] [--payload PATH]`. The **highest
data-loss-risk** command in WAEGIS — every write path is built so an operator's
local edits can never be silently destroyed.

- **Three-way classification** — for every payload file (with `generated` paths
  and the manifest's own path excluded) it compares `O` (the manifest's recorded
  as-shipped original hash), `L` (the current on-disk bytes) and `N` (the new
  payload), assigning one of nine `FileAction`s: `UNCHANGED`,
  `AUTO_APPLY_NEW` (`L=O`, `N≠O`), `KEEP_LOCAL` (`L≠O`, `N=O`),
  `ALREADY_CONVERGED` (`L≠O`, `N≠O`, `L=N`), `ADD_NEW` / `NEW_CONVERGED` (new
  upstream files), `DELETE_REMOVED` / `KEEP_MODIFIED_REMOVED` (files upstream
  dropped — deleted only when locally unmodified, else kept and reported as a
  preserved local edit), and `CONFLICT`. An absent side (`None`) is unequal to
  every hash, so "operator deleted the file" and "upstream dropped it" fall out
  of the same comparisons.
- **`generated` protection** — `.agentic/workflow.toml` is removed from the
  comparison entirely: never classified, never in any action list, never
  written, and preserved verbatim in the rewritten manifest's `generated`.
  (Doctor validates generated files against the new payload instead.)
- **Conflicts are never auto-resolved** — a true three-way conflict goes through
  a caller-supplied `UpgradeConflictHook` reusing copier's `ConflictDecision`
  (keep-local / take-payload / write-`<file>.new`), the same non-negotiable rule
  as the T3.2 copier. The interactive CLI path drives it with a `ConsoleAsker`;
  the non-interactive path requires decisions in `--answers` and stops with
  exit 1 before writing when any decision is missing.
  `run_upgrade()` exposes `on_conflict`/`resolutions`/`asker` parameters as the
  test and future-WADORE seam (the frozen §5 CLI has no `--answers`).
- **Transactional apply ordering** - (1) classify, (2) collect every decision,
  (3) render and approve the fully resolved plan, (4) stage persistent backups,
  (5) apply every file write byte-verbatim, (6) run the post-apply `verify.cli-smoke` +
  `verify.workflow-smoke` re-verify (reusing `commands/new.py`'s
  `_wrapper_invocation` / `NO_ACTIVE_RUN_MARKER` rules through an injected
  `CommandRunner`), and (7) **only** on a fully successful apply + smoke
  re-verify rewrite the manifest (new `payload_version`, new original hashes) —
  the single `write_manifest` call, textually last. Smoke failure, an apply
  exception, or recovery of a process-terminated transaction restores every
  staged path automatically.
- **Current manifest required** - absent, invalid, or earlier partial manifest
  layouts are rejected. WAEGIS has no upgrade/restamp compatibility path for
  them; install/adopt the current payload explicitly instead.
- **copier reuse** — `should_exclude`, `hash_file`, `ConflictDecision`,
  `SIDECAR_SUFFIX`, and the byte-verbatim `shutil.copy2` primitive are reused;
  `copy_payload` is deliberately **not** called (its conflict model is two-way
  and it writes its manifest inline via `build_manifest`, which re-hashes disk
  and would mis-record a kept-local file's original) — the three-way
  orchestration and rewrite-last barrier are new logic.

`--json` uses the common envelope. The resolved plan carries Git mode, payload
digest, actions, and decisions; the result carries apply, rollback, smoke, and
manifest-write outcomes.

## Configure and repair

`configure` regenerates only WAEGIS-owned `workflow.toml` fields, preserving
comments and all unowned sections. It uses current manifest answers first and
repository-analysis proposals as defaults, shows field-level changes, runs the
selected gates/smoke checks, and commits generated-file metadata last through a
persistent rollback transaction.

`doctor` remains read-only and reports typed `configure`, `repair`, or `upgrade`
actions. `repair` restores a missing managed file only when the selected payload
contains bytes matching its recorded original hash. Modified files require an
explicit `keep-local`, `take-payload`, or `write-new` decision. Generated drift
is repaired from current stored answers; absent configuration metadata routes
to `configure` rather than guessing.

## Packaging and registered runtime

`packaging/build_release.py` builds the payload-bundled zipapp and the Windows
x64/Linux x64 application archives. Embedded CPython inputs are pinned in
`packaging/runtime-lock.json`; final artifacts have `SHA256SUMS`, an external
release manifest, and per-archive file manifests. Use `--verify-only` to verify
an existing output directory.

Application launchers atomically register their embedded interpreter in the
per-user WAEGIS `runtime-python` pointer. Deployed AEGIS CLI wrappers and hook
adapters resolve Python in this order: `AEGIS_PYTHON`, registered WAEGIS
runtime, supported system Python. Git remains an external prerequisite.

Network self-update is not implemented: distribute application archives
side-by-side manually until authenticated release signatures are designed.

## Development

From this folder, use the project dev dependency group so pytest and lint tools
come from the repository configuration:

```powershell
uv sync --group dev
uv run --group dev python -m pytest -q tests
python -m waegis --help
```

The suite has two tiers: the default offline tier (fake CommandRunner/
Transport everywhere, no subprocesses) and a small `integration`-marked tier
that runs real git and the real wrapper scripts against the real template
payload (still no network). Select them explicitly with:

```powershell
uv run --group dev python -m pytest -q tests -m "not integration"   # offline only
uv run --group dev python -m pytest -q tests -m integration          # real-subprocess tier
```

## Package layout

```text
src/waegis/
  __init__.py  __main__.py  cli.py  version.py
  engine/   step.py  catalog.py  runner.py  journal.py  plan.py
  io/       prompts.py  answers.py  console.py  reports.py
  probes/   machine.py  tools.py  network.py
  payload/  manifest.py  copier.py  locate.py
  repo/     gitops.py  analyze.py  workflow_toml.py
  commands/ new.py  adopt.py  analyze.py  doctor.py  upgrade.py
tests/
```

## License

This project is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See `LICENSE.txt` for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
