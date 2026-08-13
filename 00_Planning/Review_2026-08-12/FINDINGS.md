<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Findings and proposed implementations — 2026-08-12

Read `README.md` in this folder first. It defines the severity scale, the scope
rule, and the order of work.

Paths are relative to the repository root. `SRC` abbreviates
`05_Software/aegis/template/.agentic/aegis/cli/src/aegis`.

## Summary

| ID | Finding | Severity | Scope |
|---|---|---|---|
| F-01 | The red-before-green witness can be fabricated | S1 | Defect |
| F-02 | Test fingerprints include bytecode caches | S1 | Defect |
| F-03 | Delivery can report the opposite of what the Run records | S1 | Defect |
| F-04 | A Run cannot be abandoned between Stages | S2 | Obstruction |
| F-05 | `stage.revisit` strands a later active Stage | S2 | Obstruction |
| F-06 | ~~Skipping a Stage discards recorded evidence~~ — withdrawn, merged into F-03 | — | Not a work item |
| F-07 | The installed default test command cannot pass for a common repository shape | S2 | Obstruction |
| F-08 | `next_actions` is empty for 46 of 48 operations and every error | S2 | Defect |
| F-09 | A hand-edited artifact escapes the structured error boundary | S2 | Defect |
| F-10 | Launcher prerequisite failure breaks the machine envelope | S2 | Defect |
| F-11 | `--expected-revision` is required but appears in no help output | S2 | Defect |
| F-12 | Pagination is emitted but cannot be navigated | S3 | Defect |
| F-13 | A delivered Run can be reopened through the selection pointer | S3 | Defect |
| F-14 | Installing AEGIS delivers no host guidance | S3 | Defect |
| F-15 | WAEGIS drifts from the shared protocol | S3 | Defect |
| F-16 | Stage, Adoption and Abandonment artifacts hide their state in one line | S3 | Deferred |
| F-17 | The delivery matrix is documented as eight archives; four exist | S3 | Truthfulness |
| F-18 | The acceptance record reads `accepted` on unverified input | S3 | Truthfulness |
| F-19 | Shipped agent guidance is a fraction of the planned guidance | S3 | Defect |
| F-20 | Human output is a JSON dump | S3 | Defect |
| F-21 | `stage.show` returns its Stage state twice | S3 | Defect |
| F-22 | Rendered artifacts do not match the shipped templates | S3 | Defect |

---

## F-01 — The red-before-green witness can be fabricated

**Severity** S1 · **Scope** Defect · **Design** `DESIGN_RED_BEFORE_GREEN.md`

**Where** `SRC/application/workflow_operations.py:1603`, validator at `:191`;
`SRC/application/stage_expectations.py:139`;
`SRC/application/execution_operations.py:172-195`

**Reproduce** On a fresh install, gut a test to assert nothing, then submit one
`evidence-add` carrying `"red_witness": true` and a `fingerprints` map whose digest
is the already-gutted file. No process is launched. Check completes with no
red-witness finding; Implementation then runs the real suite, passes, and raises no
integrity finding at all.

**Why** This is the product's central promise: an agent must not be able to make
tests pass by editing them, and the defence is fingerprint at red, compare at green.
Both halves are currently supplied by the caller, so both can be chosen to agree.
`PR-RED-002`, `PR-SUCCESS-004`, `PR-INT-001`.

**Change** Strip the reserved keys from caller input. After `entry = dict(inputs)` at
`workflow_operations.py:1603`:

```python
for reserved in ("red_witness", "fingerprints", "red_fingerprint_comparison"):
    entry.pop(reserved, None)
```

That is the entire security fix. Those keys are written in exactly one place
(`execution_operations.py:194-195`), inside the branch that runs only when AEGIS
launched the process, so once they cannot arrive from a caller they can only mean a
real observed failure. `_valid_red_witness` needs no change.

Separately, and in the same Run, make the honest alternative findable: the
`check_red_witness_missing` finding text must name the exception path — the operation,
the `red_before_green` target, and the two mandatory fields. See
`DESIGN_RED_BEFORE_GREEN.md` section 4.

**Prove** `test_reported_evidence_cannot_become_a_red_witness` and
`test_executed_failure_is_a_red_witness` in
`05_Software/aegis/tests/test_execution_integrity.py`.

**Do not** Add a gate — nothing here may refuse a `stage.complete`. Do not add a
`provenance` field; an earlier draft of the design made it the centrepiece and it is
redundant. Do not write a migration; version 1 has not been accepted and there is
nothing in the field.

---

## F-02 — Test fingerprints include bytecode caches

**Severity** S1 · **Scope** Defect · **Design** `DESIGN_FINGERPRINT_SCOPE.md`

**Where** `SRC/application/execution_operations.py:82-87`

**Reproduce** A Check witness on a trivial project records
`tests/__pycache__/test_calc.cpython-314.pyc` beside `tests/test_calc.py`. CPython's
default cache embeds the source mtime, so touching the mtime of an otherwise
unchanged test changes the `.pyc` digest — demonstrated on this tree, digest
`a191dc450a076120` becoming `c31b1100c5fe5309` with identical source bytes.

**Why** A fresh clone, checkout, worktree switch or CI runner will report
`test_changed_after_red` naming a file nobody touched. False accusations in the one
signal the product exists to produce teach a developer to ignore it. `PR-INT-001`,
`PR-INT-003`.

**Change** Ask Git instead of walking the filesystem. Add a `tracked_files(root)`
method to the workspace adapter that runs
`git ls-files -z --cached --others --exclude-standard -- <root>` through the existing
Git subprocess helper at `infrastructure/workspace.py:181-186`, and call it from
`_fingerprints`. The repository's own `.gitignore` then excludes the caches, with no
list to maintain and nothing to configure. Fall back to today's walk if the Git call
fails, so the change can never make a working setup worse. Do not modify `list_files`
— it has eight other callers. Full reasoning in `DESIGN_FINGERPRINT_SCOPE.md`.

**Prove** `test_fingerprints_exclude_ignored_cache_files`,
`test_tracked_test_stays_fingerprinted_when_gitignored`, and
`test_fingerprints_fall_back_without_git`.

**Do not** Add a built-in denylist or a new configuration key — an earlier draft
proposed both and they are unnecessary. Do not set `PYTHONDONTWRITEBYTECODE` in the
child environment; AEGIS does not change how a project runs.

---

## F-03 — Delivery can report the opposite of what the Run records

**Severity** S1 · **Scope** Defect

**Where** `SRC/application/workflow_operations.py:1119-1143` seeds the Delivery
sections at `stage.start`; `:1284-1295` and `SRC/application/stage_expectations.py`
check only that each section is non-empty and that `terminal_result` is one of three
enums.

**Reproduce** Skip Alignment, Requirement, Design, Check, Implementation and
Validation. Start Delivery, overwrite `skips_waivers_and_omitted_stages` with "No
Stage was skipped, waived, or omitted.", `evidence_summary` with "All automated tests
passed.", and `test_integrity` with "No test was changed between red and green." Set
`terminal_result` to `achieved` and approve. The Run delivers with **no finding**.

**Why** Delivery is the artifact a later reader trusts. Prefilled text that
`stage.set_section` can overwrite, and that completion never revisits, means the
final record can contradict every Stage beneath it. `PR-REPORT-001`,
`PR-DELIVERY-001`, `PR-ESCAPE-005`.

**Change** Do not compare prose against facts — that needs language understanding and
would be unreliable. Instead give Delivery one section AEGIS owns.

At Delivery completion, regenerate a `recorded_state` section from the Run and Stage
data that already exists: skipped and omitted Stage names with their reasons, waiver
escapes, executions with a non-passing outcome, changed tests named by any red
comparison, and whether a red witness or an approved exception exists. Write it as a
short fixed list.

Keep it out of `allowed_sections`, which is the mechanism that already prevents
`stage.set_section` from writing a section. The author's summary stays exactly as
written, and the derived facts sit beside it. A reader who sees "No Stage was skipped"
directly above a list of six skipped Stages has everything needed, and AEGIS never has
to judge the prose.

**Prove** `test_delivery_records_derived_state` in
`05_Software/aegis/tests/test_stage_completion_expectations.py`: a Run with six
skipped Stages whose author text denies them completes, and the `recorded_state`
section names all six. Plus `test_delivery_recorded_state_is_not_writable` asserting
`stage.set_section` rejects it.

**Do not** Block the completion, and do not overwrite what the author wrote. Do not
add contradiction detection.

---

## F-04 — A Run cannot be abandoned between Stages

**Severity** S2 · **Scope** Obstruction

**Where** `SRC/application/lifecycle_operations.py:112`

**Reproduce** Complete or skip any Stage, then `run-abandon`. It fails with
`invalid_transition: Current Stage mutations require an active Stage.` The developer
must first start another Stage to regain the exit.

**Why** Abandonment is the escape hatch of last resort and the only way out of a
Delivery a developer does not want to finish. Requiring the Run to be mid-Stage to
leave it is the exact shape of trap the non-blocking posture exists to avoid.
`PR-ESCAPE-001`, `PR-ESCAPE-003`.

**Change** Drop the `_require_active_stage` call from the abandonment path. Normal
abandonment already records actor, reason and time on `run.md` and the current Stage
file; neither requires the Stage to be active. Keep the existing expected-revision
comparison against `run.md`.

**Prove** `test_run_abandons_from_a_completed_stage` in
`05_Software/aegis/tests/test_delivery_adoption.py`.

**Do not** Change the exceptional abandonment path — the sibling record for
unreadable Run state is correct as it stands.

---

## F-05 — `stage.revisit` strands a later active Stage

**Severity** S2 · **Scope** Obstruction

**Where** `SRC/application/workflow_operations.py:1545-1556`

**Reproduce** With Alignment active, revisit Intake. Both Stages are now `active`.
Alignment is unreachable: `stage.start` requires `pending`, `stage.revisit` requires
`completed` or `skipped`. With F-04 unfixed, the Run cannot be abandoned either.

**Why** Revisit is the sanctioned way to correct earlier work. It must not cost the
Run its forward path. `PR-EVOL-004`, `PR-WORKFLOW-004`.

**Change** When revisiting an earlier Stage, demote the previously current Stage to
`pending` in the same publication, and record the demotion as an event on that Stage
so the history stays truthful. The transaction already writes both the Stage and the
Run summary, so no new publication seam is needed.

**Prove** `test_revisit_returns_the_later_stage_to_pending` in
`05_Software/aegis/tests/test_run_stage_workflow.py`, asserting the demoted Stage can
subsequently be started.

**Do not** Introduce a Stage stack or multi-active model. Exactly one Stage is
current.

---

## F-06 — Withdrawn, merged into F-03

**Severity** — · **Scope** Not a work item

The original finding claimed that skipping a Stage silently discards its recorded
evidence. That was overstated. The Stage file retains every evidence entry,
execution, decision and attachment, and the skip records its actor, reason and time.
Nothing is discarded.

The real gap was that Delivery never summarised any of it — which the `recorded_state`
section in F-03 now covers. Make sure that section notes when a skipped Stage held a
red witness, and F-06 needs no separate change.

Do not widen `work_applied` to cover evidence. That would make Check un-skippable
after any execution, converting an escape hatch into a gate. The stricter literal
reading of the functional specification is recorded under `Needs an owner decision`.

---

## F-07 — The installed default test command cannot pass for a common repository shape

**Severity** S2 · **Scope** Obstruction

**Where** `05_Software/waegis/src/waegis/infrastructure/target.py:104-108`

**Reproduce** A repository with `tests/test_calc.py` written in the common
bare-function style, and no `pytest.ini`, no `conftest.py` and no `pyproject.toml`.
Detection falls through to `python -m unittest discover -s tests`, which discovers
zero tests and exits 5. Every `execution-run` records `failed` forever, and at Check
that failure was — before F-01 — accepted as a red witness.

**Why** The product promises to be useful with no configuration on first install.
A default command that can never pass, in a repository shape that is extremely
common, breaks that on day one. `PR-DEFAULT-001`, `PR-CONFIG-007`, `PR-SUCCESS-001`.

**Change** Two small steps.

1. Widen detection with one substring check: if a file matching `test_*.py` or
   `*_test.py` under a detected test root does not contain `unittest`, it cannot be a
   `TestCase`, so choose pytest. Read a bounded prefix of a bounded number of files;
   this is a text scan, not an import.
2. Always report the basis. The install result already carries `warnings`; add one
   naming the framework chosen and the signal that chose it, so a developer who
   disagrees knows immediately which line of `config.toml` to change.

**Prove** `test_bare_function_tests_are_detected_as_pytest` and
`test_detection_basis_is_reported` in `05_Software/waegis/tests/test_lifecycle.py`.

**Do not** Execute the project's test command during install or during
`config-validate`. Installation and validation are read-only with respect to project
behavior.

---

## F-08 — `next_actions` is empty for 46 of 48 operations and every error

**Severity** S2 · **Scope** Defect

**Where** populated only in `SRC/application/workflow_operations.py:869`
(`run.create`) and `SRC/application/execution_operations.py:307` (`execution.run`);
`SRC/application/dispatcher.py:68-95` has no parameter for it

**Reproduce** `stage-show` returns `next_actions: []`. So does every error, including
`state_conflict`, where the protocol requires a proposed re-read.

**Why** Bounded next actions are the plan's central affordance for a small model.
Without them a host has to infer the workflow from prose, which is precisely what the
machine protocol exists to avoid. `PR-MODEL-003`, `PR-MODEL-004`, the protocol's
Stage and revision clauses.

**Change** Two cases carry almost all the value; do those and stop.

1. `stage.show` proposes the next atomic operation for the current Stage status. This
   is the one an agent reads on every resume.
2. Any error that requires a fresh revision token — `state_conflict`, and
   `invalid_input` on a missing `expected_revision` — proposes the read operation that
   returns one. This needs an optional `next_actions` argument on the error builder in
   `dispatcher.py` and on `_error` in `workflow_operations.py`.

Leave the other operations alone until something needs them. The three-action bound is
already enforced by the result object.

**Prove** `test_stage_show_returns_next_actions` and
`test_state_conflict_proposes_a_read` in
`05_Software/aegis/tests/test_cli_protocol.py`.

**Do not** Sweep all 48 operations. Do not invent actions the caller cannot perform.

---

## F-09 — A hand-edited artifact escapes the structured error boundary

**Severity** S2 · **Scope** Defect

**Where** `SRC/interface/cli.py:337-338` — `_present` and `_exit_code` are called
outside the `try` that begins at `:202`

**Reproduce** Add one bare TOML date to `run.md` front matter, exactly as a human
editing a documented Markdown artifact might:

```
reviewed_on = 2026-08-12
```

Then `aegis --format json run-show` gives exit 1, empty stdout, and a raw Python
traceback on stderr. `tomllib` returns a `datetime.date`, and `json.dumps` raises
after the guard has been left.

**Why** `05_Software/aegis/README.md` states that no operator-producible input or
repository state is emitted as a traceback. `run.md` is a project-owned, hand-editable
artifact, so this is operator-producible. `PR-PROTO-003`, `PR-PROTO-004`.

**Change** Two edits, each a few lines. Do both — they fix different halves.

1. **Make the file work.** After `tomllib.loads` in `parse_markdown_document`
   (`SRC/infrastructure/codecs.py:403`), coerce any `date`, `datetime` or `time` value
   to RFC 3339 text. TOML dates are valid TOML, the templates themselves use them, and
   a developer writing one into front matter should simply get a working read. This is
   what actually unblocks the user.
2. **Make the boundary hold.** Move `_present` and `_exit_code` inside the `try`, so
   any future serialization fault becomes an `internal_error` envelope rather than a
   traceback. Pass `allow_nan=False` in `SRC/interface/json_presenter.py:36-40` — TOML
   permits `nan` and `inf`, which would otherwise emit invalid JSON.

**Prove** `test_toml_dates_in_front_matter_are_readable` and
`test_unserializable_data_returns_a_structured_error` in
`05_Software/aegis/tests/test_cli_protocol.py`.

**Do not** Broaden this into a general artifact-validation pass.

---

## F-10 — Launcher prerequisite failure breaks the machine envelope

**Severity** S2 · **Scope** Defect · **Introduced by the 2026-08-12 packaging change**

**Where** `05_Software/aegis/template/.agentic/aegis/bin/aegis` and `aegis.cmd`;
generated equivalents in `02_Tools/build_aegis_release.py:253-283`

**Reproduce** With Git absent from `PATH`:

```
aegis --format json version-show
→ exit 5, stdout empty, stderr "AEGIS requires Git on PATH."
```

**Why** A machine caller receives no `aegis.machine.response` and cannot parse the
failure. The protocol requires exactly one JSON line on stdout and an empty stderr.
The exit class 5 is right; the delivery is not. The check also gates operations that
do not need Git at all, including `version-show`, `help-show` and `config-show`.

**Change** Move the Git check out of the shell wrappers and into `launcher.py`, which
already knows the requested format. Emit a `missing_prerequisite` envelope — human
text or one JSON line as `--format` dictates — and keep exit 5. Leave the interpreter
check in the wrappers; it has to run before Python exists.

Once the check lives in Python, it costs nothing to require Git only where the
repository is actually observed, so `version-show` and `help-show` work without it.
Do that in the same edit if it falls out naturally; do not restructure to achieve it.

**Prove** `test_missing_prerequisite_is_reported_as_an_envelope` in
`02_Tools/tests/test_release_launchers.py`, asserting one parseable JSON line on
stdout and exit 5.

**Do not** Revert the prerequisite check itself. Pinning to Python 3.12 and failing
early with a clear message is an improvement; only its delivery needs fixing.

---

## F-11 — `--expected-revision` is required but appears in no help output

**Severity** S2 · **Scope** Defect

**Where** enforced in `SRC/application/dispatcher.py:119-133`; the registry declares
only per-command arguments, and global options live in `SRC/interface/cli.py:84-89`

**Reproduce** `aegis help-show --operation stage.set_section` lists only
`--input <source>` and prints the example
`aegis stage-set-section --input section.json`. That example fails in machine mode
with `invalid_input`.

**Why** Twenty-six operations require a token that no help output mentions, and the
published examples do not work. For a small model driving AEGIS from help alone this
is the single worst trap in the surface. `PR-MODEL-001`, `PR-MODEL-003`.

**Change** Extend the help payload for every operation whose machine-revision policy
is a `required:*` class: add `--expected-revision <sha256:…>` to the required
arguments, name the read operation that returns the matching token, and correct the
example to include it. The policy table already lives beside the operation
declarations in `SRC/application/operation_registry.py`, so the help can be derived
rather than hand-maintained.

**Prove** `test_revision_bearing_operations_document_the_token` in
`05_Software/aegis/tests/test_operation_registry.py`, asserting every `required:*`
operation names the option and that its example contains it.

**Do not** Relax the enforcement. The token is correct; only its discoverability is
broken.

---

## F-12 — Pagination is emitted but cannot be navigated

**Severity** S3 · **Scope** Defect

**Where** `SRC/application/workflow_operations.py:889-911`;
`SRC/application/project_operations.py:361-380` and `:821-841`

**Reproduce** `run-list`, `requirement-list` and `component-list` hard-slice at
twenty and return `has_more: true` with `next_cursor: "20"`. No registry entry
declares a cursor, offset or limit argument, so items past the first twenty are
unreachable.

**Why** The protocol defines bounded results that remain reachable. Announcing more
data and providing no way to ask for it is worse than a plain cap. `PR-MODEL-006`,
`PR-MODEL-007`.

**Change** Declare an optional `--cursor <token>` on the three list operations and
honour it as a slice offset. The cursor value is already computed and returned; only
the input side is missing. A project accumulates Requirements quickly, so a cap of
twenty with no way past it will be hit in normal use.

**Prove** `test_list_cursor_returns_the_next_page` in
`05_Software/aegis/tests/test_run_stage_workflow.py`.

**Do not** Add filtering or sorting arguments.

---

## F-13 — A delivered Run can be reopened through the selection pointer

**Severity** S3 · **Scope** Defect

**Where** `SRC/application/workflow_operations.py:302-331` validates only that the
pointer's Run loads, never its status

**Reproduce** Write a delivered Run identity into `.agentic/runs/context.toml` — a
file the artifact model declares non-authoritative and excludes from version control
— then `stage-revisit validation`, `stage-set-section` and `stage-complete` all
succeed against a Run whose status is `delivered`.

**Why** A terminal Run is the record of what was delivered. Corrections after
delivery are meant to be additive through a new Run. `run.set_profile` and
`run.abandon` already check Run status; the Stage path does not. `PR-RUN-008`,
`PR-RUN-009`.

**Change** Check Run status where the current Run and Stage are loaded, and return
`invalid_transition` naming the terminal state for mutating operations. Reads such as
`run.show` and `stage.show` must continue to work against terminal Runs.

**Prove** `test_delivered_run_rejects_stage_mutation` in
`05_Software/aegis/tests/test_delivery_adoption.py`.

**Do not** Make the pointer authoritative or validate it on read paths.

---

## F-14 — Installing AEGIS delivers no host guidance

**Severity** S3 · **Scope** Defect

**Where** `05_Software/aegis/template/.agentic/aegis/manifest.toml` lists only
payload paths under `.agentic/aegis/`;
`05_Software/waegis/src/waegis/application/lifecycle.py:239-241` writes only those

**Reproduce** After `waegis install-apply`, the target repository contains
`.agentic`, `.git`, `src`, `tests` — and nothing else. The five host files exist in
the AEGIS archive but not in the WAEGIS payload, so the supported install path
delivers none of them. No host is told that AEGIS exists.

**Why** The named host set is a product commitment, and WAEGIS is the operator's
install route. `PR-HOST-001`, `PR-HOST-002`.

**Change** Carry the five host files in the WAEGIS payload and write them on install
as **project-owned** files: created when absent, never overwritten, never removed on
upgrade. They sit outside `.agentic/aegis/`, so they are not manifest-owned and
`payload-verify` must continue to ignore them.

This is the option that makes the product work on first install, which is the point
of the finding. Documenting a manual wiring step instead would be defensible, but it
leaves every new user with a host that has never heard of AEGIS.

**Prove** `test_install_delivers_host_guidance` and
`test_upgrade_preserves_edited_host_guidance` in
`05_Software/waegis/tests/test_lifecycle.py`.

**Do not** Overwrite an existing host file on upgrade. These live outside the payload
ownership boundary.

---

## F-15 — WAEGIS drifts from the shared protocol

**Severity** S3 · **Scope** Defect

**Where** `05_Software/waegis/src/waegis/interface/cli.py:46-99`;
`05_Software/waegis/src/waegis/application/lifecycle.py:88-116`

**Reproduce** Four documented global options are rejected — `--repo`,
`--no-color`, `--protocol-version`, `--expected-revision` — each exiting 2. Output
format is chosen by the substring test `"json" in arguments`, so
`waegis --format=json install-plan --bogus` prints human text. Machine output uses
default `json.dumps` spacing and bare `print()`, so it is neither compact nor
newline-controlled, and startup failures write to stderr. The exit map omits
`not_found`, `ambiguous_run`, `unsupported_schema` and `capability_unavailable`, all
of which fall through to 70; and error classification matches on English substrings
of the summary, so an unreadable plan file becomes `missing_prerequisite` because its
message contains "unavailable".

**Why** Both products are required to speak one protocol. WAEGIS is a second,
drifted implementation of it. `PR-PROTO-001`, `PR-PROTO-004`, `PR-ENC-001`.

**Change** Three edits fix everything a caller can actually hit. Do these:

1. Use the parsed `--format` value on every path, including parse failures. The
   substring test is the reason `--format=json` silently yields human text.
2. Emit compact JSON with an explicit separator tuple, reconfigure stdout to UTF-8
   with `\n` newlines exactly as AEGIS does at `SRC/interface/cli.py:168-172`, and
   write the envelope to stdout rather than stderr.
3. Complete the exit map so no code falls through to 70.

Leave the rest. The rejected global options are harmless to a WAEGIS caller — WAEGIS
has no repository selection and no revision tokens, so `--repo` and
`--expected-revision` have nothing to do. The substring error classification is ugly
but produces a defensible code in every case a user reaches. Record both in the plan
as accepted divergence rather than spending a Run on them.

**Prove** Extend `05_Software/waegis/tests/test_cli_protocol.py` with an equals-form
format assertion, a compact-and-single-line assertion, and one exit-class case per
code.

**Do not** Make WAEGIS import from AEGIS. Independent runnability is deliberate; the
duplication of the small envelope contract is accepted.

---

## F-16 — Stage, Adoption and Abandonment artifacts hide their state in one line

**Severity** S3 · **Scope** Deferred — needs an owner decision before any work

**Where** `SRC/infrastructure/codecs.py:358-378` writes `state_json`; `:429` reads
state back only from it

**Reproduce** A real `05-check.md` from a one-test Run is 46,890 characters, of which
40,549 are a single escaped `state_json` line in the front matter. The Markdown body
renders the same data again as JSON fences and contains zero table rows. Editing the
body has no effect — it is never parsed.

**Why** `run`, `component` and `specification` were migrated to real Markdown
round-trips and read back from their sections; Stage, Adoption and Abandonment were
not. The result is that the artifacts which change most often are the ones that are
neither human-reviewable nor merge-friendly: every mutation rewrites one enormous
line, so any concurrent edit conflicts on the whole file. `PR-ART-002`,
`PR-COLLAB-008`.

**Change — do not start without an instruction.** The full remedy is a
`_parse_stage_body` and siblings that read the rendered sections, then removal of
`state_json`. That is the largest item in this pack by a wide margin, and it fails the
standing scope test: the software works, no workflow is blocked, and no requirement is
contradicted outright. It buys reviewable diffs and friendlier merges — real, but not
a defect.

Two things make deferring it safe:

- The single-developer-with-agent workflow this product targets rarely produces
  concurrent edits to the same Run. The merge-hostility is mostly theoretical until
  two people share a Run.
- Readers almost always reach Stage state through `stage-show`, not by opening the
  file.

**The cheap partial, if the file size becomes annoying.** The body currently renders
the same data as JSON fences that nothing ever parses, while `state_json` holds it
again. Deleting the duplicate body rendering roughly halves the file and cannot break
a reader, because the body is already write-only. That is a small, safe change
available at any time without committing to the full round-trip.

**Prove** If the full remedy is ever authorised: a round-trip test asserting
`state_json` is absent and that a parsed Stage equals the rendered one, mirroring the
existing assertions for `run.md`.

**Do not** Attempt this alongside F-01, F-02 or F-03. It touches the same files and
would make the changes that matter harder to review.

---

## F-17 — The delivery matrix is documented as eight archives; four exist

**Severity** S3 · **Scope** Truthfulness · **Introduced by the 2026-08-12 change**

**Where** `07_Delivery/README.md`; `00_Planning/AEGIS_RELEASE_SCOPE.md`

**Reproduce** Both documents assert in the present tense that version 1 is delivered
as eight archives, and the table names all eight filenames. `07_Delivery/dist/` holds
four, all external-runtime. `02_Tools/runtime_inputs.toml` is still
`required_inputs_not_supplied` with empty digests for all four entries. Running all
eight build combinations gives four archives and four refusals:
`Build refused: Locked python runtime input is not supplied`.

**Why** The project's own release rule is that a deferred capability is never
represented as delivered. These documents previously described the deferral
accurately; the packaging change moved them ahead of the software.

**Change** Return both statements to the intended-matrix form, and mark the four
bundled editions as pending supplied runtime inputs. The build tool's refusal is
correct and needs no change.

**Prove** Documentation only.

**Do not** Fabricate runtime inputs to make the sentence true.

---

## F-18 — The acceptance record reads `accepted` on unverified input

**Severity** S3 · **Scope** Truthfulness

**Where** `02_Tools/aegis_acceptance.py`, catalog totals check at `:122-125`

**Reproduce** The tool executes nothing; it validates a hand-authored JSON record.
A record whose commands were never run, whose evidence file is a single reused
29-byte artifact, and whose four environments include two claiming Ubuntu — authored
on Windows — validates and reports `verdict: accepted`. Separately, the authoritative
totals invariant applies only when `catalog_name` matches an exact string, and
`--catalog` accepts any path, so a renamed two-scenario catalog also yields
`accepted`.

**Why** The document it emits is titled "AEGIS acceptance completion record" and
carries far more apparent authority than its inputs justify. The tool's own docstring
and `06_SoftwareDocu/AEGIS_V1_IMPLEMENTATION.md` are honest about this; the artifact
is not.

**Change** Two cheap steps now, one larger step later. Now: apply the totals
invariant unconditionally rather than keying it on `catalog_name`; and stamp every
emitted record and report with a prominent provenance banner stating that results are
operator-attested and that no scenario was executed by this tool. Later, when IP-18
proceeds: have the harness execute the scenarios it records, so evidence originates
from a run rather than from an author.

**Prove** `test_totals_invariant_applies_to_a_renamed_catalog` in
`02_Tools/tests/test_aegis_acceptance.py`.

**Do not** Remove the validator. Its coverage arithmetic and evidence binding are
genuinely useful; only its authority is overstated.

---

## F-19 — Shipped agent guidance is a fraction of the planned guidance

**Severity** S3 · **Scope** Defect

**Where** `05_Software/aegis/template/.agentic/aegis/workflows/*.toml`; the five host
files under `template/.claude`, `.codex`, `.opencode`, `.pi`, `.qwen`

**Reproduce** The eight Stage instructions total 1,908 bytes — one sentence each,
plus a list of section names. The eight planned Stage templates total 22,412 bytes of
structured guidance: what belongs in each section, table columns, decision semantics,
handoff expectations. The five host files are byte-identical to each other at 506
bytes and describe no Stage, no operation payload, and no input envelope.

**Why** The product is a guide for a model and a companion for a developer. What
reaches the model is roughly eight percent of what was designed, and it omits exactly
the parts that tell a model what to write. Nothing in the shipped payload documents
the `aegis.machine.input` envelope or any operation's `data` fields, and help does not
either — so an agent must read the source to drive the product.

**Change** Two things, in this order, and stop there.

1. **The input envelope, once.** Document the `aegis.machine.input` shape and each
   operation's `data` fields in the help payload. This is the single highest-value
   change in the pack for an agent driving AEGIS, because without it the agent must
   read the runtime source to send any `--input`. Do it in the same pass as F-11,
   which is already editing the same help metadata.
2. **The two missing Stage elements.** Add to each `workflows/*.toml` instruction the
   common findings for that Stage and the escape actions available in it — the two
   elements the functional specification requires and the payload omits. That is where
   most of the guidance value in the planned templates actually lives.

Do not attempt a wholesale port of all 22,412 bytes of template prose. Most of it
describes table layouts that the artifacts no longer use, so porting it would document
a shape the software does not produce. If a later Run wants richer per-section
guidance, it can add it one Stage at a time.

**Prove** An assertion per Stage that the instruction names its escape actions, and
one asserting every `--input` operation documents its `data` fields.

**Do not** Exceed the declared instruction character budgets. If content does not fit,
cut prose, not the escape actions.

---

## F-20 — Human output is a JSON dump

**Severity** S3 · **Scope** Defect

**Where** `SRC/interface/human_presenter.py:55`

**Reproduce** `run-show` prints roughly 20,000 characters of minified JSON.
`stage-show` prints about 13,700, with single lines over 5,000 characters. Every data
value is rendered with `json.dumps`. Findings appear as a bare code with no severity,
message or path; artifacts lose their action; next actions lose their reason.

**Why** Human and machine presentations are required to carry the same semantic
result, which they do — but the human presentation is required to be short, plain and
to point at durable detail rather than flood the reader. `PR-MODEL-005`.

**Change** Render the common envelope fields as labelled lines — the selected Run and
Stage, the outcome, findings as label, severity and summary, artifacts as action and
path — and for large nested payloads print a one-line summary plus the artifact path
that holds the detail. Machine mode is unchanged.

**Prove** `test_human_output_is_bounded` in
`05_Software/aegis/tests/test_cli_protocol.py`, asserting a maximum line length for
`run-show` and `stage-show` as the existing help-output assertion already does.

**Do not** Freeze wording in tests. Assert shape and bounds, not prose.

---

## F-21 — `stage.show` returns its Stage state twice

**Severity** S3 · **Scope** Defect

**Where** `SRC/application/resume_context.py`

**Reproduce** A Delivery `stage-show` on a trivial Run returns 43,429 characters.
`run_summary` is 33 percent of it and `stage_state` a further 29 percent — and
`stage_state` repeats `sections`, `findings` and `decisions`, which are already
returned as top-level keys.

**Why** The resume context is the product's main output to a model, and its budget
map exists to keep it affordable. Roughly a third of every Stage read is duplication.
`PR-MODEL-003`.

**Change** Return each collection once. Keep the top-level keys, and reduce
`stage_state` to the fields not otherwise present — status, revision, timestamps,
`work_applied`, and the event history. The budget map already declares the caps; only
the duplication needs removing.

**Prove** `test_stage_show_does_not_duplicate_collections` in
`05_Software/aegis/tests/test_stage_resume_context.py`.

**Do not** Change the declared budgets, and do not drop the omission accounting —
`total`, `returned`, `omitted` and `truncated` are correct and valuable.

---

## F-22 — Rendered artifacts do not match the shipped templates

**Severity** S3 · **Scope** Defect

**Where** `SRC/infrastructure/codecs.py:882-919` renders Stage bodies;
`00_Planning/templates/` holds the intended shapes

**Reproduce** Five of the nine shipped Markdown templates cannot be parsed by the
product that owns them — all eight Stage templates plus `adoption.md` and
`abandonment.md` fail with `malformed Markdown artifact`, because they lack the
undocumented `state_json` key. Heading text also diverges: `.title()` produces
`Test Work` for `Test work` and destroys punctuation, turning
`Red-before-green decision` into `Red Before Green Decision` and
`Skips, waivers, and omitted stages` into `Skips Waivers And Omitted Stages`. Every
planned table renders as a JSON fence. Titles read `# 5 - Check` rather than
`# 05 - Check`.

**Why** The artifact model states that the templates demonstrate the schemas. They
currently demonstrate a shape the product rejects. `PR-ART-002`, `PR-ART-003`.

**Change** With F-16 deferred, the codec is authoritative — so regenerate the
templates from it rather than rewriting the codec to match them. Emit each shipped
template by rendering an empty artifact of that type, then correct the artifact model
where it describes a shape the software does not produce.

Add the round-trip test regardless of anything else in this pack: every shipped
template must parse through `parse_markdown_document`. That single test is what stops
the templates and the codec drifting apart again, and it is cheap.

**Prove** `test_every_shipped_template_parses` in
`05_Software/aegis/tests/test_configuration_codecs.py`.

**Do not** Hand-edit the templates to match, and do not fix the heading casing in
isolation. Generate them, so they cannot drift.

---

## Needs an owner decision

Recorded so they are not rediscovered. None is a work item without an explicit
instruction.

| Topic | The question |
|---|---|
| Stage artifact format (F-16) | Stage, Adoption and Abandonment keep their state in a single escaped `state_json` line, so those files are neither reviewable as diffs nor merge-friendly. The full remedy is the largest item in this pack and fixes no defect. Worth doing only if two people start sharing a Run. See F-16 for the cheap partial. |
| Skipping Intake and Delivery | Six of eight Stages skip today; the standing requirement is that every Stage must be skippable. Intake is straightforward. Delivery is not: if it is skipped, the Run has no delivery report, and the terminal state that results is undefined. Options are a new terminal state, treating a Delivery skip as abandonment, or accepting the current exception. Fixing F-04 gives a real exit from Delivery in the meantime. |
| The literal skip rule | The functional specification says a skip must fail after work has been applied. F-06 keeps `work_applied` narrow so that recording evidence does not lock the Stage. The stricter reading would make Check un-skippable after any execution. Confirm the intended reading. |
| Linux evidence | No Ubuntu code path has ever executed — no CI exists in the repository. The new launcher tests assert launcher text, not behavior. The release gate requires demonstration on both platforms. |
| Bundled editions | Two of four delivery editions cannot be built until real Python 3.12 and Git archives with pinned versions and digests are supplied in `02_Tools/runtime_inputs.toml`. |
| Adoption | Adoption is a free-text journal: no workflow resource, no Stage instructions, no component discovery. The release scope defers it, so this is an accurately recorded shortfall rather than a defect. |
| Dead policy keys | `policy.risk_attention_threshold` and `policy.protected_scope_patterns` are parsed and echoed into the resume context but never produce a finding. Either give them an advisory effect or remove them. |
| Unwritable Run fields | `excluded_scope` and `open_questions` are initialised to `"None"` and no operation can ever set them, yet both are rendered in `run.md` and the resume context. |
| Orphan tests | `trace.validate` never enumerates the configured test roots, so a test that no Requirement links is invisible. |
| Scope revision follow-through | After a scope revision nothing identifies which completed Stages, artifacts or evidence need reconsideration; `affected_work` is caller-declared and echoed back. |

---

## Verified working — do not "fix" these

Confirmed by field test or code reading during this review. Changing them would be a
regression.

- **The non-blocking posture is real.** An empty Stage completes with findings and
  exit 0. There are no hooks anywhere in the payload. Findings never deny an action.
- **AEGIS performs no outward Git action.** The only Git verbs invoked are
  `symbolic-ref`, `rev-parse` and `status`. WAEGIS runs only `git init`, and only
  through `repository-init-apply`.
- **No network access and no home-directory access** anywhere in either runtime.
- **Atomic publication and recovery** are genuinely well built — temporary sibling,
  `fsync`, `os.replace`, a commit-decision bundle, and digest-verified roll-forward.
- **Change attribution** records observed paths without claiming authorship, and
  preserves a dirty starting state correctly.
- **The bounded resume context** accounts for every omission and never fabricates a
  missing reference.
- **Current-only project knowledge** cascades Requirement, Specification and
  Component deletion atomically without touching source or tests.
- **One runtime copy.** The test suite exercises the exact bytes delivered to a
  target repository; there is no second implementation to keep in step.
- **The five execution outcomes** and the separation of a project failure from an
  AEGIS protocol failure are correct and well tested.
