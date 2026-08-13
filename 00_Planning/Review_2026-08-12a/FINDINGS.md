<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Findings — second pass, 2026-08-12a

`SRC` = `05_Software/aegis/template/.agentic/aegis/cli/src/aegis`.
`WSRC` = `05_Software/waegis/src/waegis`.

None of these overlap `F-01`..`F-22` in `Review_2026-08-12`. Where a finding is
adjacent to one, the difference is stated explicitly.

## Index

| | Title | Sev | Scope |
|---|---|---|---|
| G-01 | A reported green bypasses the fingerprint comparison entirely | S1 | Defect |
| G-02 | `--selection` records a false `failed` for a passing suite | S1 | Defect |
| G-03 | Delivery is unreachable without reading the runtime source | S1 | Obstruction |
| G-04 | The zone comparison walks the whole repository | S2 | Defect |
| G-05 | The Delivery record omits open findings | S2 | Defect |
| G-06 | A later red witness silently replaces the comparison base | S2 | Defect |
| G-07 | Exceptional abandonment leaves the Run recorded as `active` | S2 | Defect |
| G-08 | One corrupt `run.md` hides every Run in the repository | S2 | Obstruction |
| G-09 | `requirement-create` refuses where a finding already exists | S2 | Obstruction |
| G-10 | Commands are refused outside three Stages, with no escape | S2 | Obstruction |
| G-11 | No closed enum is ever enumerated, in help or in errors | S2 | Obstruction |
| G-12 | Component drift review is self-declared and never re-armed | S2 | Defect |
| G-13 | The shipped no-tests default records a false red | S2 | Defect |
| G-14 | Test-root detection misses class-style pytest and nested roots | S2 | Defect |
| G-15 | External-runtime launchers reject compliant Python 3.12 | S2 | Defect |
| G-16 | The Git exclusion never reaches a second developer | S2 | Defect |
| G-17 | A TOML datetime yields `internal_error` with no path | S2 | Defect |
| G-18 | Human output drops every finding's content | S2 | Defect |
| G-19 | A scope revision identifies no affected work | S2 | Defect |
| G-20 | Shipped guidance is 8.3% of designed guidance | S2 | Defect |
| G-21 | `07_Delivery/README.md` documents the retired 2.x generation | S2 | Truthfulness |
| G-22 | `recorded_state` omits selection, out-of-zone and green provenance | S3 | Defect |
| G-23 | `recorded_state` asserts a valid witness for a skipped Check | S3 | Defect |
| G-24 | Stage transitions attribute every action to `"operator"` | S3 | Truthfulness |
| G-25 | `evaluated_expectation_count` reports the finding count | S3 | Truthfulness |
| G-26 | `stage.show` proposes an action its own revision cannot satisfy | S3 | Defect |
| G-27 | `--expected-revision` must precede the command token | S3 | Defect |
| G-28 | Error envelopes null out `run_id`, `stage` and `revision` | S3 | Defect |
| G-29 | `next_actions.arguments` keys are not CLI-invokable | S3 | Defect |
| G-30 | The five host files are one file copied five times | S3 | Defect |
| G-31 | Structured rows are delivered as JSON text inside text wrappers | S3 | Defect |
| G-32 | A third to a half of every `stage-show` is truncation bookkeeping | S3 | Defect |
| G-33 | Requirement text is never checked for the identifiers PR-REQ-003 forbids | S3 | Defect |
| G-34 | `trace.validate` cannot see an orphan test | S3 | Defect |
| G-35 | A staged-only change during Check is never named | S3 | Defect |
| G-36 | The Delivery prefill duplicates prior evidence as a Python repr | S3 | Defect |
| G-37 | An Adoption journal cannot be rediscovered | S3 | Obstruction |
| G-38 | A profile change records no actor and no reason | S3 | Defect |
| G-39 | Component behaviours are bound to requirements by list position | S3 | Defect |
| G-40 | WAEGIS startup failure escapes the protocol envelope | S3 | Defect |
| G-41 | Plan authorisation is invalidated by ignored files | S3 | Defect |
| G-42 | The dry-run preview is not reviewable | S3 | Defect |
| G-43 | The four shipped v1 archives have no published digests | S3 | Truthfulness |
| G-44 | `CHANGELOG.md` claims implementation through IP-17 | S3 | Truthfulness |
| G-45 | `AEGIS_V1_IMPLEMENTATION.md` documents the wrong execution rule | S3 | Truthfulness |
| G-46 | No deferral report for any of the 17 `Should` requirements | S3 | Truthfulness |
| G-47 | The payload ships no `templates/` or `defaults/` directory | S3 | Truthfulness |
| G-48 | Undecodable `--input` returns `path: null` | S4 | Defect |
| G-49 | A fresh install reports four findings on its first `config-validate` | S4 | Defect |
| G-50 | No validation reports a pending interrupted transaction | S4 | Defect |
| G-51 | Audits cannot scope themselves to changed files | S4 | Deferred |
| G-52 | WAEGIS gates filesystem-only operations behind Git | S4 | Defect |
| G-53 | The two AEGIS archives are not platform-specific | S4 | Truthfulness |

---

# S1

## G-01 — A reported green bypasses the fingerprint comparison entirely, and Delivery then certifies a clean red-to-green

**Severity** S1 · **Scope** Defect

**Where** `SRC/application/execution_operations.py:196-217` is the only site that
computes `red_fingerprint_comparison`. `SRC/application/stage_expectations.py:344-356`
accepts any entry with `kind=automated, category=tests, outcome=passed` as green.

**Reproduce** (executed)

1. Honest `execution-run` at Check over `tests/test_calc.py` — real red witness with
   fingerprints.
2. `stage-complete`, `stage-start implementation`.
3. Rewrite `tests/test_calc.py` to `assert True`.
4. Record the green with `evidence-add {kind: automated, category: tests,
   name: project, outcome: passed, …}` instead of `execution-run`.
5. `stage-complete`.

Result: no `test_changed_after_red`, no `implementation_green_evidence_missing`, and
the AEGIS-owned Delivery block reads

```
- changed_tests: []
- red_before_green: {"approved_exception":false,"valid_witness":true}
```

**Why** `F-01` closed the red door by stripping `red_witness` and `fingerprints` from
`evidence.add`. That strip loop is correct — verified, including against
`attachment-add` and `decision-add` variants. But the objective it protects is
reached identically through green: `evidence.add` may still assert
`outcome: passed`, and nothing ever compares the test bytes when it does. Violates
PR-INT-002, PR-SUCCESS-004, PR-DELIVERY-001, FS-INTEGRITY-002/003.

**Change** Two parts, both detection-only.

1. Mark green test evidence with provenance — `executed` when written by
   `execution.run`, `reported` when written by `evidence.add`. `evidence.add` must
   not be able to set it, using the same strip mechanism `F-01` already added.
2. Add a `fingerprint_comparison` fact to `_delivery_recorded_state`
   (`SRC/application/workflow_operations.py:379-390`) that reads `not_performed`
   when no AEGIS-launched green exists for the Run.

**Prove** `test_reported_green_records_absent_fingerprint_comparison` — drive the
sequence above and assert the Delivery record states `not_performed`.

**Do not** block `evidence.add`, require `execution.run` for green, or add a Stage
gate. Reporting a green by hand stays legal; it stops being indistinguishable from
an executed one. Do not treat `F-01` as closing this — implement both.

---

## G-02 — `execution-run --selection` records a false `failed` for a suite that passes

**Severity** S1 · **Scope** Defect

**Where** `SRC/application/execution_operations.py:74-76`

```python
elif "unittest" in executable:
    module = path.removesuffix(".py").replace("/", ".")
    arguments.append(f"{module}.{selector}" if selector else module)
```

**Reproduce** (executed) With the shipped default
`python -m unittest discover -s .agentic/tests`:

- `execution-run --category tests --name project` → `outcome: passed`.
- `trace-impacted`, then `execution-run --category tests --name project
  --selection SEL-…` → `outcome: failed`, finding `execution_failed`.

`.agentic/tests/test_uploader.py` becomes `.agentic.tests.test_uploader` — with a
leading dot — and is appended to a `discover` command, where the trailing positional
is read as a *pattern*. The Delivery record then carries
`non_passing_executions: [{"outcome":"failed","stage":"validation"}]` permanently.

**Why** Impacted-test selection is the entire purpose of Validation, and with the
shipped default configuration it is guaranteed to record the opposite of the truth.
This is not a missing feature; it is AEGIS breaking a working suite and then
recording the breakage as an engineering conclusion. Distinct from `F-07`, which is
about the default command not matching a common repository shape — here the suite
passes and AEGIS breaks it.

**Change** Do not append modules to a `discover` invocation. Detect `discover` in the
configured argv and either replace it with `python -m unittest <modules>`, or record
`mode: full` with an explicit reason that the selection could not be applied to this
command shape. Argument construction must never change the engineering conclusion.

**Prove** `test_selection_against_discover_does_not_record_failure` — a passing suite
executed with a selection records `passed` or an explained full-suite fallback, never
`failed`.

**Do not** add a configuration key for the invocation style, and do not silently drop
the selection without recording that it was dropped.

---

## G-03 — Delivery is unreachable without reading the runtime Python source

**Severity** S1 · **Scope** Obstruction

**Where** `SRC/application/workflow_operations.py:1538-1553` requires a decision whose
`target` is the literal string `"delivery"`. `:1554-1565` requires the prose section
`terminal_result` to equal exactly `achieved`, `partially_achieved` or
`not_achieved`.

**Reproduce** (executed) At Delivery, `decision-add {value: approved,
target: "delivery_report", actor, reason}` → exit 0, silently accepted. Then
`stage-complete` → `invalid_transition`, `"Delivery requires its latest applicable
decision to be approved."`, repeated verbatim on every retry. After correcting the
target, `stage-complete` → `invalid_transition`, `"Delivery requires achieved,
partially_achieved, or not_achieved assessment."` — the values are named, the
*location* is not.

Neither string `"delivery"` nor `terminal_result` appears in
`workflows/delivery.toml`, in any help payload, in any `error.details`, or in any
host file.

**Why** Two hard blocks at the terminal Stage of the workflow, in a product whose
stated posture is that no default capability rejects a stage closure
(PR-DEFAULT-003, PR-POSTURE-002). Also PR-MODEL-001 and PR-WORKFLOW-003: the shipped
guidance does not permit reaching the product's own terminal state.

**Change** Both errors must name the exact required input and carry it in
`next_actions`: `decision.add` with `target: "delivery"`, and `stage.set_section`
with `section: terminal_result` and the three permitted values. `delivery.toml`
should name both, exactly as `check.toml` now names
`decision-add … target red_before_green`.

**Prove** `test_delivery_gate_errors_name_their_required_input` — assert both error
payloads carry the operation and argument that resolves them.

**Do not** remove the gates. They are the one place where a hard stop is defensible,
because Delivery is terminal. Fix the guidance, not the rule.

---

# S2

## G-04 — The Check zone comparison hashes the whole repository, producing false accusations AEGIS itself caused

**Severity** S2 · **Scope** Defect

**Where** `SRC/infrastructure/workspace.py:300-309`

```python
working_files = {}
for path in self.root.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(self.root).as_posix()
    if relative.startswith(".git/") or relative.startswith(".agentic/.runtime/"):
        continue
    working_files[relative] = revision_of(path.read_bytes())
```

Diffed at `SRC/application/workflow_operations.py:1618-1630`. Git's ignore rules
never enter the picture.

**Reproduce** (executed) One `execution-run` at Check, on a repository with an
ordinary `.gitignore`, yields five findings naming files the AEGIS-launched pytest
created:

```
Implementation path changed during Check: .pytest_cache/.gitignore
Implementation path changed during Check: .pytest_cache/CACHEDIR.TAG
Implementation path changed during Check: .pytest_cache/README.md
Implementation path changed during Check: .pytest_cache/v/cache/lastfailed
Implementation path changed during Check: .pytest_cache/v/cache/nodeids
```

Cost, measured on a 5,012-file repository with an ignored `node_modules`:
advance to Check **15.34 s**, Check complete **3.67 s**, `05-check.md` =
**1,078,960 bytes** — one SHA-256 per repository file, stored twice
(`git_baseline` and `git_completion`).

**Why** This is the `F-02` defect in a second location. `F-02`'s fix corrected
`_fingerprints` to use `git_visible_files`; the zone path was never touched. AEGIS's
core out-of-zone signal therefore fires on its own artifacts. Violates PR-ZONE-002
("known implementation files"), PR-ZONE-005, PR-INT-003 and PR-SUCCESS-001.

**Change** Source the path set from `git_visible_files` (`workspace.py:119-155`), the
helper `F-02` already added, rather than an unfiltered `rglob`.

**Prove** `test_zone_comparison_ignores_gitignored_paths` — run a Check execution in
a repository with a `.gitignore` and assert zero `check_out_of_zone_change` findings.

**Do not** add a denylist, a configuration key, or a size cap. The repository's own
`.gitignore` is sufficient — this is the same conclusion `DESIGN_FINGERPRINT_SCOPE.md`
already reached for `F-02`. **Sequencing: do not close `F-02` without this.**

---

## G-05 — The Delivery record omits open findings, so a report can claim "no findings" over 46 of them

**Severity** S2 · **Scope** Defect

**Where** `SRC/application/workflow_operations.py:379-390` — the `categories` tuple
carries `skipped_or_omitted_stages`, `waiver_escapes`, `non_passing_executions`,
`changed_tests` and `red_before_green`. There is no finding count.

**Reproduce** (executed) Complete Intake with every section empty (7 findings), skip
the six middle Stages, start Delivery, set every section to `"Everything is fine. No
findings. No skips."` with `terminal_result: achieved`, approve, complete.
`stage-complete` → exit 0, `delivered`. `recorded_state` names the six skipped
Stages and nothing about findings. A second run — the 16-operation empty delivery —
carries **46 open findings across seven Stages** while `recorded_state` reports only
`design omitted`.

**Why** `F-03`'s mechanism is correct and works: the block is regenerated at
completion, cannot be written by `stage.set_section`, and demonstrably contradicts a
lying author about skips. Its category list simply does not include the thing an
author is most likely to lie about. Violates PR-REPORT-001, PR-SUCCESS-004,
PR-DELIVERY-004.

**Change** One entry in the same tuple `F-03` already owns: `open_findings`, as counts
by severity plus the Stage names holding them.

**Prove** `test_recorded_state_reports_open_findings` — deliver a Run with open
findings and prose denying them; assert the counts appear.

**Do not** judge the author's prose, block completion, or reopen findings. Record the
number beside the claim and let the reader decide.

---

## G-06 — A later red witness silently replaces the original as the comparison base, including one Check itself rejects

**Severity** S2 · **Scope** Defect

**Where** `SRC/application/execution_operations.py:200-206` selects
`next(reversed(check_state["evidence"]) … if item.get("red_witness"))` — the *latest*
entry carrying the bare flag. `stage_expectations._valid_red_witness` (`:139-150`)
requires `time < implementation_started_at`; the comparison path applies no such
test.

**Reproduce** (executed) Honest red at Check → complete → start Implementation
(`started_at` fixed) → gut `tests/test_calc.py` and add a throwaway failing
`tests/test_tmp.py` → `stage-revisit check` → `execution-run` (red #2, late,
fingerprints taken over the gutted file) → `stage-complete` (no red finding: red #1
still validates) → resume Implementation, delete the throwaway, `execution-run` →
`changed_tests: ['tests/test_tmp.py']`. The gutted test is not flagged.

**Why** The witness Check accepts and the witness the comparison uses are different
records. PR-INT-004 requires the original to remain authoritative. Violates
PR-INT-004, PR-INT-002, PR-SUCCESS-004, FS-INTEGRITY-004.

**Change** Compare against the *earliest* valid witness, or union the changed set
across every recorded witness. Prefer the union: it cannot be gamed by ordering and
needs no notion of which witness is canonical.

**Prove** `test_comparison_uses_every_recorded_red_witness` — the revisit sequence
above must flag `tests/test_calc.py`.

**Do not** forbid revisit, forbid a second witness, or invalidate the later one.
Both records stay; only the comparison base changes.

---

## G-07 — Exceptional abandonment leaves the Run recorded as `active`, and names the wrong unreadable path

**Severity** S2 · **Scope** Defect

**Where** `SRC/application/lifecycle_operations.py:150-155` (recoverability test) and
`:170` (`"unreadable_paths": [run_path]`, hardcoded to `run.md`). The fallback fires
on *any* recoverable load error from `_load_current`, including an unreadable Stage
file while `run.md` is perfectly readable — and in that case deliberately does not
touch `run.md`.

**Reproduce** (executed) Corrupt `01-intake.md` only. Then:

```
run-abandon {"actor":"agent","reason":"Stage unreadable."} → exit 0
  "Exceptional abandonment recorded without overwriting unreadable Run state."
  unreadable_paths: [".agentic/runs/RUN-…/run.md"]      ← run.md is readable
run-list   → status: "active"
run-show   → outcome: "Active"
run-select <id> → exit 0        ← the abandoned Run can be worked on again
```

**Why** An `ABANDON-*.md` sibling says `abandoned` while the Run says `active`
forever. Violates PR-ESCAPE-003 (abandonment is a recorded outcome), PR-ESCAPE-009
(never falsify the audit trail), PR-ESCAPE-010, FS-ABANDON-005.

**Change** In the fallback branch, attempt `_load_run(workspace, selected)`
independently. If `run.md` decodes, write the terminal `abandoned` status normally and
keep the sibling record for the unreadable Stage bytes. Record the actually failing
path from `load_error.path` rather than assuming `run.md`.

**Prove** `test_exceptional_abandonment_closes_a_readable_run` and
`test_unreadable_paths_names_the_failing_path`.

**Do not** attempt to repair the corrupt Stage file, and do not refuse the
abandonment. Preserving unreadable bytes stays correct.

---

## G-08 — One malformed `run.md` makes every Run in the repository undiscoverable

**Severity** S2 · **Scope** Obstruction

**Where** `SRC/application/workflow_operations.py:1045-1046`

```python
for run_id in _run_ids(workspace)[:20]:
    metadata, state, revision, _ = _load_run(workspace, run_id)
```

No per-run guard — unlike `SRC/application/lifecycle_operations.py:74-77`, which
correctly skips unloadable runs.

**Reproduce** (executed) Two Runs; overwrite one `run.md` with `corrupt\n`:

```
run-list → exit 4  malformed_state  "missing TOML front matter"  data: {}
```

The healthy Run remains fully workable — `run-select`, `stage-show`, `run-abandon`
all exit 0 — but only if the id is already known, and `run-list` is the only way to
learn it. This is the operation an agent calls first on resume.

**Why** PR-RUN-002, PR-ESCAPE-001, PR-SNAPSHOT-003, PR-SUCCESS-002.

**Change** Wrap the per-run load in `try/except (UseCaseError, WorkspaceError)` and
emit the entry with `status: "unreadable"` and its path, exactly as `run.abandon`
already tolerates.

**Prove** `test_run_list_degrades_over_an_unreadable_run`.

**Do not** add a repair step or a validation gate. Listing must degrade, not refuse.

---

## G-09 — `requirement-create` refuses where an advisory finding already exists and is unreachable

**Severity** S2 · **Scope** Obstruction

**Where** `SRC/application/project_operations.py:149-157` raises `invalid_input` when
an automated Requirement has no happy-path test link. `_requirement_findings`
(`:428-434`) already carries the correct advisory code `missing_happy_path`, which
this path makes unreachable.

**Reproduce** (executed) `requirement-create` for an automated Requirement at the
Requirement Stage → exit 2, `"Automated Requirements need a happy-path real test
link."` Check — where tests are created — is two Stages later, so the file cannot
exist yet and the caller must invent a path to satisfy the rejection.

**Why** PR-TRACE-011 and FS-TRACE-004 both say findings and backlog information
rather than blocking work. PR-DEFAULT-003 says no default capability rejects an edit.
This is prevention plus ceremony, in a Stage that structurally cannot comply.

**Change** Create the Requirement and attach the existing `missing_happy_path`
finding.

**Prove** `test_automated_requirement_without_happy_path_is_created_with_a_finding`.

**Do not** relax the link validation for links that *are* supplied; a supplied path
that does not exist stays a finding too.

---

## G-10 — Configured commands are refused outside three Stages, with no finding and no escape

**Severity** S2 · **Scope** Obstruction

**Where** `SRC/application/execution_operations.py:135-143`

```python
if category == "tests" and stage not in {"check", "implementation", "validation"}:
    raise UseCaseError("invalid_transition",
        "Tests execute only during Check, Implementation, or Validation.")
if category in {"lints", "audits"} and stage != "validation":
    raise UseCaseError("invalid_transition",
        "Lints and audits execute only during Validation.")
```

`SRC/application/resume_context.py:540-548` contradicts it, admitting `delivery` to
the tests/lints/audits set.

**Reproduce** (executed) At Delivery, `stage-show` advertises `tests.project` with its
full command vector; `execution-run --category tests --name project` → exit 4,
`invalid_transition`. AEGIS hands the agent a tool and then refuses it.

**Why** An agent cannot run the suite at Intake to learn the baseline, cannot lint
during Implementation, cannot re-run anything at Delivery. PR-DEFAULT-003 names
commands explicitly: "No default capability shall reject an edit, **command**, or
stage closure." There is no escape hatch and no finding — only a refusal.

**Change** Two parts. (a) Reconcile the two lists so `stage-show` never advertises a
command the Stage will refuse. (b) Convert the refusal to an advisory finding —
record the execution, note that the Stage is outside the expected window, and let the
Run continue.

**Prove** `test_execution_outside_the_expected_stage_records_a_finding` and
`test_advertised_commands_are_runnable_in_the_advertising_stage`.

**Do not** widen the *expectation* — Check/Implementation/Validation stays the
documented shape. Only the enforcement becomes a record.

---

## G-11 — No closed enum is ever enumerated, in help or in errors, so field-at-a-time discovery does not terminate

**Severity** S2 · **Scope** Obstruction

**Where** Six enums gate input: requirement `status`, `priority`,
`verification_kind`, `tests[].purposes` (`SRC/application/project_operations.py:39,
95, 99, 103`), decision `value` (`SRC/application/workflow_operations.py:53`),
evidence `kind` (`:1932`). Every rejection is a bare sentence with `details: {}`.

**Reproduce** (executed) 12 consecutive identical responses of `"Requirement status
is invalid."` while guessing values; 2 identical `"Decision value is invalid."`
before the reviewer stopped and read the source. Because the error names the same
field again for the next wrong guess and never narrows the space, the loop has no
exit.

**Why** PR-PROTO-004 defines `details` as bounded operation-specific fields.
CP-MODEL-003 and PR-MODEL-001 require a small local model to drive the surface
without the source.

**Change** Put `{"allowed": [...]}` into `error.details` at every enum rejection.

**Prove** `test_enum_rejection_lists_allowed_values` parameterised over all six.

**Do not** relax any enum, and do not expand this into a general schema-publication
project. Six literals in six error paths.

---

## G-12 — Component drift review is self-declared and never re-armed

**Severity** S2 · **Scope** Defect

**Where** `SRC/application/project_operations.py:882-887` raises `component_drift`
only when the caller's own `drift_review` map is not `yes`/`not_applicable`.
`reviewed_at` is stamped `now` on every write (`:694`) and is never compared against
anything. Nothing records the state of the component's files at review time, so
"reviewed" can never expire.

**Reproduce** (executed) Create a Component over `src/retry.py` with `drift_review`
all `yes` → `trace-validate` 0 findings. Replace `src/retry.py` with an unrelated
class and add an undocumented `src/retry_backoff.py`. `trace-validate` → 0 findings.
`component-validate` → 0 findings. `component-find --path src/retry_backoff.py` →
empty, `"uncertainty": "no unique exact Component relationship"`, no finding.

**Why** Component pages are what a session reads *instead of* the source, so a stale
one actively misinforms. The artifact model asks for exactly this check (§18 item 13,
"changed Component files without recorded drift review"). Violates PR-COMP-004,
PR-COMP-003, AM-COMP-004.

**Change** Record a digest per component file alongside `drift_review`, and raise the
existing advisory `component_drift` when a file's current bytes differ.

**Prove** `test_component_drift_is_reported_after_a_member_file_changes`.

**Do not** gate anything on drift, and do not auto-update the component page. The
Delivery `component_drift_review` section already prompts the human; this gives the
prompt something true to say.

---

## G-13 — The shipped no-tests default records a false red

**Severity** S2 · **Scope** Defect

**Where** `WSRC/infrastructure/target.py:172-175` configures
`python -m unittest discover -s .agentic/tests` against a directory containing only
`.gitkeep`. `SRC/infrastructure/process.py:130` maps any non-zero exit to `failed`.

**Reproduce** (executed, through AEGIS's own runner) `ExecutionRequest(("python",
"-m","unittest","discover","-s",".agentic/tests"))` → `outcome = failed`,
`exit_status = 5`, stderr `NO TESTS RAN`. A fresh install therefore produces a
plausible-looking red witness before any test exists.

**Why** PR-CONFIG-003 in effect, PR-DEFAULT-001, and it undercuts the whole PR-RED
family: the first red an agent records on a new install can be an artifact of the
installer.

**Change** Distinguish "no tests ran" from "tests failed". unittest's exit 5 and
pytest's exit 5 both mean no tests collected; map that to a distinct outcome (or to
`launch_error` with the reason recorded) so it never satisfies a red witness.

**Prove** `test_empty_test_root_does_not_produce_a_red_witness`.

**Do not** change the shipped default away from `.agentic/tests`; the default is
correct, its interpretation is not. Related to but distinct from `F-07`, which is
about detection choosing the wrong framework.

---

## G-14 — Test-root detection misses class-style pytest and every non-root test directory

**Severity** S2 · **Scope** Defect

**Where** `WSRC/infrastructure/target.py:21` anchors `BARE_PYTEST_TEST_PATTERN` at
`^def test_`, so an indented method never matches. `:96` restricts roots to a literal
top-level `tests` or `test`.

**Reproduce** (executed) `tests/test_calc.py` containing `class TestCalc:` with
`def test_add(self)` → install warns `"no pytest configuration or bare pytest-style
test function was detected"`, configures `python -m unittest discover -s tests`,
which exits **5 / NO TESTS RAN**, while `python -m pytest -q` in the same repository
reports **2 passed**. Second shape: `python/tests/test_a.py` → `"no existing test
root was detected"`, and the developer's real tests are ignored entirely.

**Why** PR-CONFIG-004, PR-CONFIG-007, PR-SCOPE-009, PR-DEFAULT-001. `F-07`'s fix is
real and works for the shape it named (bare functions at a top-level root); these two
shapes are at least as common.

**Change** Allow indented `def test_` in the pattern, and search one or two levels
deep for directories named `tests`/`test` before concluding none exists.

**Prove** `test_class_style_pytest_is_detected` and
`test_nested_test_root_is_detected`.

**Do not** add framework auto-detection beyond pytest/unittest, and do not scan the
whole tree.

---

## G-15 — External-runtime launchers reject compliant Python 3.12 installations, in plaintext

**Severity** S2 · **Scope** Defect

**Where** `bin/aegis:11,15` requires an executable literally named `python3.12`.
`bin/aegis.cmd:8,13` and `02_Tools/build_aegis_release.py:260-278` require the `py`
launcher.

**Reproduce** (executed) `sh ext/u1/bin/waegis --format json version-show` on a
machine whose `python3` is 3.14 → `WAEGIS requires Python 3.12.` on stderr, exit 5,
no envelope. A pyenv, conda, uv or venv-provided 3.12 exposed as `python3`, or a
Windows Store / embeddable 3.12 without `py`, satisfies `PREREQUISITES.md` and is
still refused.

**Why** PR-PKG-008, PR-RUNTIME-001, and PR-PROTO-001 — this is the one prerequisite
failure a machine caller cannot parse. Same class as `F-10` (which fixed the
Git-absent path), different branch.

**Change** Probe candidates in order — `python3.12`, `py -3.12`, then any `python3`
/ `python` whose `--version` reports 3.12 — and emit the failure through the same
envelope `F-10` added.

**Prove** `test_launcher_accepts_a_venv_provided_3_12` and
`test_launcher_prerequisite_failure_is_an_envelope`.

**Do not** widen the accepted version range. 3.12 stays pinned; only discovery
changes.

---

## G-16 — The version-control exclusion is machine-local and never reaches a second developer

**Severity** S2 · **Scope** Defect

**Where** `WSRC/application/lifecycle.py:262-280` writes `.agentic/runs/context.toml`
and `.agentic/.runtime/` into `.git/info/exclude`. Git never clones, fetches or
versions that file. The path is also hardcoded, so a relocated `runs` root is
excluded nowhere at all.

**Reproduce** (executed) Install, commit, `git clone`. In the clone,
`.git/info/exclude` has no AEGIS entries; after touching the two paths:

```
?? .agentic/.runtime/
?? .agentic/runs/context.toml
```

The clone's developer never runs `install.apply` — the payload is already committed —
so they never receive the exclusion. Any `git add -A` commits one machine's selected-
Run pointer into shared history, and the next developer inherits it.

**Why** PR-COLLAB-004, PR-COLLAB-002, AM-LAYOUT-009, AM-COLLAB-002.

**Change** Write a project-owned, versioned `.agentic/.gitignore` containing
`.runtime/` and the *configured* runs-pointer path, alongside `config.toml` at
install. One file, propagates with the repository, no ceremony.

**Prove** `test_install_writes_a_versioned_exclusion` and
`test_relocated_runs_pointer_is_excluded`.

**Do not** touch `.gitignore` at the repository root, and do not remove the
`.git/info/exclude` write — keep both during a transition.

---

## G-17 — A TOML datetime in a Requirement yields `internal_error` with no path

**Severity** S2 · **Scope** Defect

**Where** `SRC/infrastructure/codecs.py:418` applies
`_normalize_toml_temporal_values` to Markdown front matter, but
`SRC/infrastructure/workspace.py:189-197` (`load_toml`, the path used for every
`REQ-*.toml`) does not. `F-09`'s prescribed remedy edits `parse_markdown_document`
only, so it will not reach this.

**Reproduce** (executed, against live source) Change one line of a working
`REQ-*.toml` to `updated_at = 2026-01-01T00:00:00Z` — the exact form the shipped
`00_Planning/templates/requirement.toml:40` demonstrates. `requirement-show` → exit
70, `{"code":"internal_error", "summary":"An unexpected AEGIS failure prevented
completion.", "field":null, "path":null}`. `requirement-list` lists the file happily
and `trace-validate` completes, so nothing points at the offending file.

**Why** PR-PROTO-003, AM-DURABLE-008. The envelope itself holds — no traceback — so
`F-09`'s boundary half is present and working.

**Change** Apply `_normalize_toml_temporal_values` inside `workspace.load_toml` and
`codecs._load_toml` (`:88`). One line each, in the same change as `F-09`.

**Prove** `test_toml_datetime_in_a_requirement_is_read`.

**Do not** rewrite the file on read, and do not reject the datetime.

---

## G-18 — Human output drops every finding's content

**Severity** S2 · **Scope** Defect

**Where** `SRC/interface/human_presenter.py:55-60`

```python
rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
lines.append(f"{key}: {rendered}")
for finding in result.findings:
    lines.append(f"Finding: {finding.get('code', 'unknown')}")
```

Severity, observation, consequence, artifact path and next-action arguments are all
dropped.

**Reproduce** (executed) `--format human run-show` = 4,228 characters over 7 lines,
longest line 3,755. Findings render as a bare code.

**Why** PR-PROTO-005 and FS-AUTH-004 require the human and machine interfaces to
communicate the same finding meaning. This matters more than the volume complaint in
`F-20`: the `F-01` remediation currently in flight puts the honest-exception
instructions *inside* the `check_red_witness_missing` observation text, and a human
never sees them.

**Change** Render each finding as severity, code, observation, consequence and
artifact path.

**Prove** `test_human_findings_carry_observation_and_severity`.

**Do not** redesign the whole human presenter here — `F-20` owns the layout. This is
the information-loss half only.

---

## G-19 — A scope revision identifies no affected work

**Severity** S2 · **Scope** Defect

**Where** `SRC/application/workflow_operations.py:2179-2230`. The only use of
`affected_work` is `_adopt_explicitly_scoped_paths` (`:709-729`), which adopts
already-observed paths and never looks at Stage state.

**Reproduce** (executed) Complete Intake; complete Alignment with `agreed_scope =
"Only src/calc.py."` and an approved decision; start Requirement; then
`scope-revise {before, after, actor, reason, affected_work:["src/other.py"]}` →
exit 0, `findings: []`, `next_actions: []`. `run-show` → Intake and Alignment still
`completed`, untouched. `stage-show --stage alignment` → `findings total_count: 0`.
Alignment is where the superseded scope was agreed and approved, and nothing marks it
for review.

**Why** PR-EVOL-003 is unconditional. PR-EVOL-004 literally names a finding as the
alternative to revisiting: "continue with the unresolved impact recorded as a
finding."

**Change** On `scope.revise`, append one advisory finding to the current Stage naming
every Stage whose status is `completed` or `skipped` at revision time, plus the Run's
`requirement_ids` and `component_ids`.

**Prove** `test_scope_revision_records_affected_completed_stages`.

**Do not** invalidate, reopen or block anything. The prior pack filed this under
"needs an owner decision"; it is reported here as a defect because the requirement is
unconditional and the fix is a finding, not a gate.

---

## G-20 — The shipped guidance is 8.3% of the guidance that was designed

**Severity** S2 · **Scope** Defect

**Where** `05_Software/aegis/template/.agentic/aegis/workflows/*.toml` — 8 files,
3,701 bytes, of which the `instruction` prose is **1,856 characters total**
(avg 232/Stage; min 196 `validation`, max 313 `check`). Against
`00_Planning/templates/0*.md` at 22,412 bytes.

**Reproduce** (executed) A full ticket-to-Delivery run driven using *only* what
ships — `--help`, `help-show`, the workflow instructions delivered inside
`stage-show`, the five host files, `README.md`, `rules.md`, `config.toml` — hit **17
points of insufficiency**: 9 required reading the runtime Python (2 files), 4
required `AEGIS_CLI_MACHINE_PROTOCOL.md`, which does not ship, 3 were resolved by
blind trial-and-error, 1 was an unworkaroundable defect (`G-02`). Two of the source
reads (`G-03`) are hard blocks. `grep aegis.machine.input` over every shipped
`*.md`/`*.toml`/`*.json` returns **0 hits**.

**Why** PR-MODEL-001 requires a small local model to drive AEGIS. FS-STAGE-011
requires every Stage instruction to state purpose, inputs, expected work, expected
outputs, **common findings, escape actions** and handoff needs; the shipped
instructions name sections and nothing else. PR-WORKFLOW-003.

**Change** This is one product decision, not an implementation task, and it is the
decision with the largest effect per line changed. The cheapest version that removes
the blocks: ship the `data` field shape for the 21 `--input` operations, the
`--expected-revision` requirement for the 24 operations that need it, and the enum
values (`G-11`) — all inside the existing help metadata. `F-11` and the first half of
`F-19` already touch that metadata; do all of it in one change.

**Prove** `test_help_documents_input_shape_for_every_input_operation` and
`test_help_names_expected_revision_where_required`.

**Do not** port the 22,412 bytes of templates verbatim into the payload — that trades
one context problem for another. Ship the machine-checkable facts first, prose second.

---

## G-21 — `07_Delivery/README.md` documents the retired 2.x generation as current, including enforcement guards

**Severity** S2 · **Scope** Truthfulness

**Where** `07_Delivery/README.md` lines 33-40 (claims `dist/` holds `waegis.pyz`,
`waegis-windows-x64.zip`, `waegis-complete-*`), line 77 (`python waegis.pyz
version`), line 202 ("Python 3.11 or newer is required" — contradicts
PR-RUNTIME-001), **lines 143-146** ("read, write-zone, secret, shell-write, delivery,
and evidence guards" plus Codex hook enforcement), and the Legacy section
(`.agentic/tools/`, `.agentic/.venv/`, RepoWise 0.37.0, `waegis doctor`).

A stale 600,043-byte `07_Delivery/dist/waegis.pyz` from that generation — 199 members,
containing `aegis/gates.py` — is still in the current output directory.

**Why** None of it exists in v1. Lines 143-146 advertise exactly the blocking,
hook-based enforcement posture that v1 was designed to remove, in the one document a
recipient of the release reads first. PR-BOUND-001, PR-BOUND-005, PR-BOUND-006,
PR-RUNTIME-001. Distinct from `F-17`, which addresses only the eight-versus-four
archive sentence.

**Change** Rewrite the document for v1 and delete the stale `waegis.pyz`.

**Do not** treat this as a software change. Nothing in `05_Software` is wrong here.

---

# S3

## G-22 — `recorded_state` omits impacted selection, out-of-zone changes and green provenance

`SRC/application/workflow_operations.py:379-390`. Reproduced: an author overwrites
`findings_and_residual_risk` with "Nothing to report." and `recorded_state` names no
`check_out_of_zone_change`; overwrites `evidence_summary` and `recorded_state` never
states impacted-versus-full. PR-TRACE-005, PR-ZONE-005 ("shall appear … in the
delivery report"), PR-REPORT-001. Extension of the `F-03` mechanism, which is
otherwise correct. Fold into `G-05`.

## G-23 — `recorded_state` asserts a valid witness for a skipped Check with no green

Reproduced: Check skipped after one red execution, Implementation and Validation
skipped; `recorded_state` reads `red_before_green:
{"approved_exception":false,"valid_witness":true}` and says nothing about green.
`DESIGN_RED_BEFORE_GREEN.md` §5 requires this case to read "No red evidence was
established". PR-RED-005, PR-DELIVERY-001. Folds into `G-01`'s fix.

## G-24 — Stage transitions attribute every action to `"operator"`

Hardcoded at `SRC/application/workflow_operations.py:1384`, `:1419`, `:1670`,
`:1679`, `:1144`, `:2150`, and `SRC/application/project_operations.py:207`. Neither
`stage.start` nor `stage.complete` accepts an actor. Reproduced in an agent-actor
Run: `run_opened` records `actor: "agent"`; every `stage_started` and
`stage_completed` records `actor: "operator"`. Escapes and decisions attribute
correctly. PR-ROLE-003, and PR-RUN-007's principle of not claiming what cannot be
established. **Fix:** default the transition actor to the Run's recorded actor rather
than the literal `"operator"`. Do not make it a required argument.

## G-25 — `evaluated_expectation_count` reports the finding count

`SRC/application/workflow_operations.py:1723`: `"evaluated_expectation_count":
len(expectation_findings)`. A clean Delivery returns `0` after 10 section
expectations and one approval expectation all passed — a reader concludes nothing was
checked. PR-PROTO-005, CP-PRINCIPLE-007. **Fix:** count the expectations, or rename
the field. One line.

## G-26 — `stage.show` proposes an action its own revision cannot satisfy

`stage.show` with no `--stage` returns the *current* Stage's revision and a
`next_action` of `stage.start <next>`; `stage-start` validates against the *target*
Stage artifact. Reproduced as a deterministic 3-iteration non-terminating loop.
Mitigated by the in-flight `F-08` work — the `state_conflict` response now carries
`next_actions: [{stage.show, {stage: "alignment"}}]`
(`SRC/application/operation_types.py:164-168`) — so an agent that honours the
*error's* arguments escapes after one wasted call, times 7 transitions per Run.
CP-NEXT-001. **Fix:** put `{"stage_name": name, "expected_revision": <that Stage's
revision>}` in the proposed action. Do it inside the `F-08` change already in flight.

## G-27 — `--expected-revision` must precede the command token, and nothing says so

`SRC/interface/cli.py:84-89` declares it on the root parser. Placed after the command
it yields `"The command arguments are invalid."` with `details.reason: "unrecognized
arguments: --expected-revision sha256:…"`. Adjacent to `F-11` but distinct: `F-11` is
that the option is undocumented; this is that its placement is still wrong for a
caller who copies the help example and appends. **Fix:** when a known global option
appears in the unrecognized set, say "global options precede the command". Fold into
`F-11`.

## G-28 — Error envelopes null out `run_id`, `stage` and `revision`

Every error collected — `invalid_input` on a missing revision, `state_conflict`,
`invalid_transition` at Delivery — carries `"run_id":null,"stage":null,
"revision":null` although the context pointer names an active Run and Stage.
CP-RESPONSE-007 requires the fields present. An agent that keys state off the
envelope loses its Run on every error. **Fix:** populate the selection fields on error
results built after repository resolution.

## G-29 — `next_actions.arguments` keys are not CLI-invokable, and two spellings disagree

`stage.show` emits `{"operation":"stage.start","arguments":{"stage_name":"alignment"}}`
while the CLI takes a bare positional; the `state_conflict` builder emits
`{"stage":"alignment"}` for the same concept
(`SRC/application/operation_types.py:168` versus `:162`). Nothing in the payload maps
either to a command line. CP-NEXT-001, PR-HOST-001. **Fix:** one argument name per
concept, and one shipped statement of how an argument name maps to its option or
positional.

## G-30 — The five host files are one file copied five times, in formats no host loads

`.claude/skills/aegis/SKILL.md`, `.codex/skills/aegis/SKILL.md`,
`.opencode/agents/aegis.md`, `.pi/agents/aegis.md`, `.qwen/commands/aegis.md` all
hash to `5a2865a9…`, 506 bytes each. None carries YAML front matter; a Claude Code
`SKILL.md` without `name`/`description` is not discovered, and the OpenCode and Qwen
files are not in those hosts' formats. Five different loaders cannot be satisfied by
one format, so at most one of the five is a valid host artifact. PR-HOST-001
("host-*specific* adapters"), PR-HOST-002 — both `Should`. Distinct from `F-14` (not
delivered by WAEGIS at all) and `F-19` (thin): even delivered and enriched, four of
five are in the wrong shape. **Fix:** give each file the metadata its host's loader
requires.

## G-31 — Structured rows are delivered as JSON text inside text-budget wrappers

`run_summary.stages[]` returns `{"content": "{\"name\":\"intake\",\"path\":…}",
"total_characters":136, …}` — a machine consumer must JSON-decode a field inside an
already-decoded response, and a human sees escaped braces. Same for `scope_changes`
and command arguments. PR-MODEL-005, PR-PROTO-005. **Fix:** return the row as an
object and apply the budget to the collection.

## G-32 — A third to a half of every `stage-show` is truncation bookkeeping

Every scalar is wrapped in `{content, total_characters, returned_characters,
omitted_characters, truncated}` and every list in `{items, total_count,
returned_count, omitted_count, truncated}`, emitted in full even when nothing was
truncated.

| Read | Bytes | Accounting share |
|---|---:|---:|
| Intake, empty Run | 12,725 | **42%** (5,356 B) |
| Check, completed | 29,983 | **33%** (9,993 B, 126 wrappers) |
| Delivery, active | 34,127 | — |

Independently measured: collapsing only the wrapper keys, while keeping every piece
of information, saves 33% at Intake and 32% at Delivery. The 2-character token `-m`
costs ~90 bytes to transmit. PR-MODEL-003, PR-MODEL-005. Additive with `F-21`
(duplication between `stage_state` and the top-level keys, confirmed still present,
~29%). **Fix:** emit the accounting keys only when `truncated` is true. Do not change
the declared budgets. Note this refines `F-21`'s "do not drop the omission
accounting" — the accounting stays, it just stops being emitted when nothing was
omitted.

## G-33 — Requirement text is never checked for the identifiers PR-REQ-003 forbids

`SRC/application/project_operations.py:82-88` rejects only the reserved *keys*
`ticket`, `ticket_id`, `run`, `run_id`, `provenance`. `_requirement_findings`
(`:414-468`) performs no text inspection. Reproduced: a requirement whose `behavior`
reads "Per ticket JIRA-4711 and RUN-7877744a…, the system shall do what
REQ-0b68485c… says" was created with exit 0 and `finding_count: 0`. The one place the
rule is written for an author — `00_Planning/templates/requirement.toml:19-21` — does
not ship. PR-REQ-003, AM-REQ-001. **Fix:** an advisory finding when `title`,
`behavior` or `confirmation` matches `RUN-[0-9a-f]{32}`, `REQ-[0-9a-f]{32}` or
`[A-Z]{2,}-\d+`, plus one clause in the workflow instruction. Advisory only.

## G-34 — `trace.validate` cannot see an orphan test

`SRC/application/project_operations.py:1041-1100` iterates Requirements and
Components only; `workspace.config.test_roots` is never enumerated. Reproduced:
`tests/test_orphan.py` present and linked to nothing → `finding_count: 0`.
PR-TRACE-008 is a flat NOT MET, not a judgement call. **Fix:** enumerate the
configured test roots and report unlinked test files as an advisory finding.

## G-35 — A staged-only change to an implementation file during Check is never named

`SRC/application/workflow_operations.py:1618-1630` keys the per-path finding on
content digests, and staging does not move bytes. Reproduced: modify `src/calc.py`
before Check, `git add src/calc.py` during Check → only the generic
`check_git_state_changed`; no path named. `classifications` and `entries` are
captured (`workspace.py:239-292`) and then discarded. PR-ZONE-005 ("content **or
repository state**"), PR-ZONE-004. **Fix:** use the captured `classifications` for the
per-path verdict, not only the digest map.

## G-36 — The Delivery prefill duplicates all prior evidence as a Python repr

`SRC/application/workflow_operations.py:1405-1406`:
`stage_state["sections"]["evidence_summary"] = str(prior_evidence)`, same for
`findings_and_residual_risk`. Reproduced: 1,272 characters of `[{'stage': 'check', …
'command': ['C:\\\\Users\\\\…']}]` for a Run with one execution — Python quoting,
doubled Windows separators, unbounded in the number of entries. PR-REPORT-002,
PR-ART-002. **Fix:** render a short human summary, or leave the section empty.

## G-37 — An Adoption journal cannot be rediscovered

The registry ships `run-list`, `requirement-list`, `component-list` and
`execution-list`, but no `adoption-list` (verified against the 48-operation argparse
choice set). `adoption-show` requires `ADOPT-<32hex>`. An agent resuming in a new
session has no CLI path back to an open journal. PR-ADOPT-005, PR-COLLAB-003.
**Fix:** add `adoption-list` mirroring `run-list`. One operation.

## G-38 — A profile change records no actor and no reason

`SRC/application/workflow_operations.py:1119-1177`; the registry declares only
`--profile <name>`; the event at `:1144` hardcodes actor `"operator"` and carries no
reason. Reproduced: `run-set-profile --profile short` → exit 0; `run-show` shows no
scope change and no event, so a reader cannot tell the profile was ever changed.
Omitting Design is the only state change in the product that identifies neither who
nor why. FS-PROFILE-007, FS-SCOPECHANGE-001/002, PR-ROLE-003. **Fix:** take `actor`
and `reason` via `--input`, as every other reason-bearing operation does, and append a
Run event.

## G-39 — Component behaviours are bound to requirements by list position

`SRC/infrastructure/codecs.py:730-738` renders `behaviors[i]` next to
`requirement_ids[i]`; the two lists arrive as independent caller inputs and are never
validated against each other, so reordering `requirement_ids` in a `component-update`
silently reassigns every behaviour, and the parse round-trip preserves the new, wrong
pairing. Same function: `drift_review` accepts arbitrary unvalidated keys — passing
`{"state": "current"}` was silently dropped and all four axes rendered as
`uncertain`, with no error and no finding. PR-COMP-001, PR-COMP-004. **Fix:** carry
the behaviour on the link (`[{requirement_id, behavior}]`), and reject unknown
`drift_review` keys with a structured `invalid_input`.

## G-40 — WAEGIS startup failure escapes the protocol envelope

`WSRC/composition.py:53` prints `WAEGIS cannot start: {exc}` to stderr and returns 4
with no `aegis.machine.response`. Reproduced during this review when a concurrent
edit desynchronised the source-tree payload manifest: `WAEGIS cannot start: Payload
digest mismatch: cli/src/aegis/application/operation_registry.py`, exit 4, empty
stdout. Same class as `F-10`, different path; `F-15`'s remedy list does not cover it.
PR-PROTO-001. **Fix:** emit the failure through the envelope.

## G-41 — Plan authorisation is invalidated by ignored files

`WSRC/infrastructure/target.py:63-82` hashes every file in the target except
`.agentic/.runtime/` and `.git/`; gitignored and untracked content is included.
Reproduced: `install-plan`, create `tests/__pycache__/test_a.cpython-312.pyc`,
`install-apply` → `state_conflict: Target changed after planning; create a new plan`.
A `git add` between plan and apply is correctly tolerated; a bytecode cache, editor
swap file or log is not. Against the guide-and-companion intent this is ceremony, not
safety. Spirit of PR-WAEGIS-002. **Fix:** exclude Git-ignored paths from the target
fingerprint — the same `git ls-files` conclusion as `F-02` and `G-04`.

## G-42 — The dry-run preview is not reviewable

`WSRC/application/lifecycle.py:158-177` writes the plan as canonical JSON with
`separators=(",",":")` and full `content_base64` bodies: measured **533,398 bytes on
one line**. The operator is asked to inspect it and authorise its exact SHA-256, and
no `plan-show` operation exists (`WSRC/application/registry.py:28-64`). The machine
response does carry a usable summary (`action_count`, `warnings`,
`modified_payload_paths`). PR-WAEGIS-002 asks for a preview "of the files and
repository state it would create, replace, or otherwise modify". **Fix:** add a
render/summary operation, or record the deferral.

## G-43 — The four shipped v1 archives have no published digests

`07_Delivery/dist/SHA256SUMS` and `release-manifest.json` list only
`aegis-light-0.2.0.zip/.tar.gz`; verified by `sha256sum *.zip` against both. An
offline recipient cannot verify the v1 archives. Separately, all four shipped
archives are stale relative to the tree — the shipped
`aegis-1.0.0-windows-x86_64-external-runtime.zip` still contains the pre-`F-10`
`bin/aegis`. PR-PKG-001. **Fix:** rebuild and publish digests as a release step.

## G-44 — `CHANGELOG.md` claims implementation through IP-17

`CHANGELOG.md:19`. IP-17's stated outcome is eight self-contained archives that work
with networking denied. Four exist, four refuse, no network-denied execution has
occurred, and no Linux execution has occurred anywhere. Overlaps `F-17`'s subject but
is a different file and a different assertion (slice completion versus archive
count). **Fix:** doc correction.

## G-45 — `AEGIS_V1_IMPLEMENTATION.md` documents the wrong execution rule and a stale test claim

`06_SoftwareDocu/AEGIS_V1_IMPLEMENTATION.md:97-99` states "Check and Implementation
receive tests, Validation and Delivery receive tests/lints/audits" — that is the
resume-context *filter* (`resume_context.py:540-548`), not the execution rule, which
refuses Delivery entirely (`G-10`). `:229` states "The repository does not retain a
separate automated test package for this maintenance script"; `02_Tools/tests/` now
exists and runs 12 tests green. **Fix:** doc correction; reconcile with `G-10`.

## G-46 — No deferral report for any of the 17 `Should` requirements

The register states `Should` "must be reported as deferred until delivered", and
`AEGIS_RELEASE_SCOPE.md:73-75` requires each to be named in the release record with
its reason and follow-up. `grep -rn "deferred" 07_Delivery/ 06_SoftwareDocu/` returns
nothing; there is no AEGIS 1.0.0 release record at all. `help-show` reports all five
adoption commands as `"implemented": true` with no deferral marker. Distinct from
`F-17` (delivery matrix) and `F-18` (acceptance record). **Fix:** an AEGIS 1.0.0
release record listing the deferred `Should` set.

## G-47 — The payload ships no `templates/` or `defaults/` directory

`AEGIS_ARTIFACT_MODEL.md` §3 and §4 place `templates/` and `defaults/` inside
`.agentic/aegis/`. The manifest lists 6 adapters, 3 bin files, 8 workflows, the CLI
tree, `manifest.toml` and `README.md` — nothing else. Artifact templates exist only
in `00_Planning/`, so neither the human nor the agent in an installed repository can
read the shape they are expected to produce. Related to but distinct from `F-22`
(templates do not parse): here they are not present at all. PR-COMP-002, PR-REQ-006.
**Fix:** doc correction if templates are deliberately planning-only; otherwise
generate them from the codec per `F-22` and add them to the manifest.

---

# S4

## G-48 — Undecodable `--input` returns `path: null`

A cp1252-encoded input file returns `{"code":"invalid_input","summary":"Structured
input is not readable UTF-8 JSON.","field":"input","path":null}` although the path
was supplied on the command line. PR-ENC-004 requires a *path-specific* error. One
line.

## G-49 — A fresh install reports four findings on its first `config-validate`

`WSRC/application/lifecycle.py:245-256` creates `config.toml`, `rules.md` and
`.agentic/tests/.gitkeep` but not the `requirements`, `components`, `adoptions` or
`runs` roots. Reproduced: immediately after a real install, `config-validate` →
`finding_count: 4`, all "Configured path does not yet exist". Nothing is blocked —
the directories are created lazily — but the first-run experience opens with four
complaints about the installer's own output. The suite misses it because
`tests/test_run_stage_workflow.py:115-116` pre-creates all five directories, which
the real installer does not. **Fix:** create the four roots at install, which also
aligns the fixture with the shipped installer.

## G-50 — No validation reports a pending interrupted transaction

Artifact model §18 item 18 requires reporting temporary files left by interrupted
publication. Reproduced: after a hard kill at the `prepared` checkpoint, with
`TXN-b0893b5c…` present, `config-validate`, `trace-validate` and `payload-verify` all
returned `finding_count: 0`. Recovery is lazy and correct when it fires
(`workspace.py:74`, `:104`) — `run-list` cleaned it up — but the one command a
developer uses to ask "is my workspace sound?" answers yes while an unfinished
publication sits there. **Fix:** `config-validate` reports a pending `TXN-` directory.

## G-51 — Audits cannot scope themselves to changed files

`SRC/application/execution_operations.py:151-156` rejects `--selection` for any
category other than `tests`; the config codec (`SRC/infrastructure/codecs.py:110-138`)
has no changed-file option. PR-CONFIG-013's second sentence is unimplemented.
**Fix:** add the option, or record the deferral. Deferred — no obstruction results.

## G-52 — WAEGIS gates filesystem-only operations behind Git

`WSRC/interface/cli.py:70-76` refuses everything except `help.show` and
`version.show` when `git` is absent. Only `repository-init-apply` invokes Git —
proven by a runtime audit hook. `install-plan`, `upgrade-plan`, `remove-plan` and all
three applies are pure filesystem work. **Fix:** gate only the operation that needs
it. Low value; accepted divergence is a reasonable answer.

## G-53 — The two AEGIS archives are not platform-specific

`aegis-1.0.0-windows-x86_64-external-runtime.zip` (416,245 B) and the
`ubuntu-22.04-x86_64` archive (416,248 B) contain the same 67 members, including both
`bin/aegis` and `bin/aegis.cmd`; they differ only in the manifest `platform` string.
Separately, `02_Tools/build_aegis_release.py:407` asserts
`"architecture":"x86_64"` in `ARCHIVE_INVENTORY.json` regardless of content, and the
external-runtime archives contain zero architecture-specific bytes. PR-PKG-006 is met
nominally. **Fix:** doc correction, or drop the irrelevant wrapper per platform.

---

# Verified working — do not "fix" these

Each was attacked and held.

- **`F-01`'s strip loop is sound.** `evidence-add` carrying `red_witness`,
  `fingerprints` and `red_fingerprint_comparison` stores none of the three;
  `attachment-add` carrying the same keys is rejected and attachments never reach the
  evidence collection; `decision-add` with an empty reason is rejected; `timed_out`
  and `launch_error` executions produce no witness. The red door is shut. It is
  `G-01` that remains open.
- **`F-02`'s `git_visible_files` is sound.** `tests/__pycache__/*.pyc` and a stray
  `.pyc` are excluded; `git rm --cached` plus a `.gitignore` append plus gutting is
  still detected, because the comparison unions the red key set with vanished-path
  digests. Only the ZONE path (`G-04`) is untouched.
- **`F-03`'s `recorded_state` works as designed** — regenerated at completion,
  rejected by `stage.set_section` (exit 2), rendered in the Markdown body, and it
  correctly contradicts an author who writes "No Stage was skipped" over six skips.
- **`F-04`, `F-05`, `F-09`, `F-13` are fixed**, verified by execution, including
  `run-abandon` from an active Delivery the developer will not approve.
- **`F-07` and `F-10` are fixed for the shapes they named.** Bare-function pytest
  detection works and reports its basis; a Git-absent invocation yields a parseable
  `missing_prerequisite` envelope on stdout with empty stderr and exit 5, for both
  products, from source and from the built package.
- **Atomic publication survives a real kill.** `os._exit(137)` at all four
  checkpoints across four repositories: `prepared` rolled back, `commit_decided`
  rolled forward, both `*_applied` cases completed. Zero stray `.tmp` files. `_verify`
  digest-checks both sides.
- **Upgrade and removal preserve project data, proven by bytes.** SHA-256 of every
  non-payload file identical before and after `upgrade.apply` then `remove.apply`;
  `payload leftovers: []`. Install over pre-existing `config.toml`, `rules.md` and a
  requirement preserved all three verbatim.
- **Offline, no telemetry, no home access — proven twice.** Zero network symbols and
  zero home/env symbols in either runtime; stdlib-only imports; a runtime
  `sys.addaudithook` over nine live operations recorded network = 0 and home = 0.
  Both runtimes compile clean under 3.11, 3.12 and 3.14.
- **Read-only Git.** AEGIS uses only `symbolic-ref`, `rev-parse`, `status` and
  `ls-files`; WAEGIS's entire subprocess surface is `git init --quiet`, proven by
  audit hook.
- **The non-blocking posture is real and measured.** An entirely empty Run reaches
  `delivered` in 16 operations, exit 0 throughout, carrying 46 open findings. No hooks
  exist anywhere in the payload; `validation.toml:4` explicitly instructs against
  turning findings into blockers.
- **All six middle Stages are individually skippable**, with actor and reason enforced
  against blank and whitespace-only values, and `skipped` stays distinct from
  `omitted` everywhere including the Delivery record. `work_applied` correctly blocks
  a dishonest skip after `requirement.create`, and the Stage remains completable — no
  trap.
- **Five execution outcomes are honest.** `passed`/`failed`/`timed_out`/`cancelled`/
  `launch_error`, with `engineering_conclusion == "unknown"` for the last three; a
  timeout is never a red witness. `timeout_seconds = 0` imposes no deadline; Ctrl-C
  records a `cancelled` attempt rather than losing it.
- **Collaboration holds.** Two branches with independent Runs merge with zero
  conflicts; a clone resumes mid-Alignment with full state; `trace-validate` on a
  simulated bad merge reported `duplicate_identity`, `identity_path_mismatch`,
  `missing_requirement` and `component_membership_conflict`, naming every artifact by
  path, exit 0, modifying nothing.
- **Path relocation is real.** All five roots moved to `docs/reqs`, `docs/comps`,
  `qa/tests`, `audit/runs`, `audit/adoptions` left the workflow fully working with
  zero findings.
- **Removability is real.** Deleting `.agentic/aegis` leaves the project's own suite
  passing and preserves runs, config and artifacts.
- **Current-only knowledge cascades correctly.** Deleting a Requirement removed it,
  deleted its Specification, cleared the Component link and converted the orphaned
  behaviour to a visible `(gap)` — no tombstone, source and tests untouched.
- **Adversarial content is escaped, not mangled.** A specification body containing
  `## Purpose` and a literal `+++` block round-tripped intact.
- **Protocol conformance is solid.** All 48 AEGIS operations return exactly one
  parseable line on stdout, empty stderr, all 19 envelope fields, never more than
  three `next_actions`; exit classes verified (`invalid_input`→2, `not_found`→3,
  `state_conflict`→4); 56/56 command tokens derive exactly from their dotted
  identifier with zero aliases.
- **The build tool is honest.** It refuses bundled editions with a clear message
  rather than fabricating them, and `inspect_archive` independently re-verifies every
  member digest.
