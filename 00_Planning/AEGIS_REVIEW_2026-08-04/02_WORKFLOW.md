# AEGIS V2 Review — Workflow Obstructions

Date: 2026-08-04
Scope: `05_Software/aegis` — the process an agent follows, not the code that implements it.

Judged against the stated philosophy: **AEGIS assists the agent in developing, it
does not block him. Every gate needs an escape hatch. Ceremony must be
proportional to the change.**

The machinery mostly honors this. `next_command` is genuinely good, `close_stage`
auto-preparing the successor is good, and the three-way honesty of
`not-applicable` vs `waived` vs `disabled` is maintained throughout. The findings
below are the specific places where it does not.

Verification legend: **EXECUTED** / **READ** as in `01_BUGS.md`.

---

## W1 — A requirement can only be created as `functional`; the docs demand seven other categories

**Severity: critical (deterministic stall, hits every feature run)** · **Verification: EXECUTED**

Files: `stage_forms.py:270`, `requirement_store.py:625-626`, `requirements/README.md:48-72`, `AGENTS.md:63`

### The obstruction

`aegis stage add` on the requirement stage always mints a functional ID:

```python
if graph.stage == "requirement":
    requirement_id = _new_requirement_id("functional")   # hardcoded
```

`_apply_requirements` (`stage_forms.py:1418-1420`) then copies both `id` and
`category` verbatim from the form into the record, and
`validate_requirement_record` rejects any disagreement:

```python
if record.category != id_category:
    raise RequirementValidationError(source, "category", "does not match the category code in id")
```

Meanwhile `requirements/README.md:48-72` instructs the agent to cover
`ux`, `non_functional`, `security`, `data_privacy`, `platform`, `release`, and
`testing`. The only way to satisfy that is to hand-rewrite the ID prefix
(`REQ-FUNC-` → `REQ-SEC-`) while keeping the canonical lowercase UUIDv4
byte-identical — which `AGENTS.md:63` ("The CLI generates all durable IDs") and
`agentic-development/SKILL.md:96` ("Never invent IDs") forbid.

The agent is caught between two rules it cannot both obey. The error message
names the mismatch but never mentions that the ID also needs editing, so the
likely outcomes are a loop on `stage apply` or every requirement filed as
functional.

### Fix

Add a category option to `stage add` and pass it through to the ID minter.

- `cli.py` — add `--category` to the `stage add` subparser, choices being the
  eight keys of `CATEGORY_IDENTITIES`, default `functional`.
- `stage_forms.py:270` — `requirement_id = _new_requirement_id(args_category)`.
- `stage_forms.py` `_requirement_form` — write that same category into the form.
- `requirements/README.md:19-31` and `skills/agentic-development/reference/requirement.md:10`
  — document it.

Also improve the error text at `requirement_store.py:626` so the manual route is
discoverable when someone does edit by hand:

> `category does not match the category code in id; regenerate the form with
> \`aegis stage add --category <category>\` rather than editing either field`

---

## W2 — A run cannot be abandoned, but the stop menu offers exactly that

**Severity: critical (dead end with no exit)** · **Verification: EXECUTED**

Files: `cli.py:216-228`, `AGENTS.md:214`, `skills/agentic-development/SKILL.md:118`, `MERGE_AND_REBASE.md:125-129`

### The obstruction

`aegis run` accepts only `start`, `status`, `resume`, `select`. Confirmed at the
CLI surface:

```
usage: aegis run [-h] {start,status,resume,select} ...
```

No `abandon` / `abort` / `cancel` / `discard` verb exists anywhere in the CLI —
grepping the whole payload finds `discard` only as a *stage-form retention*
value. Yet `AGENTS.md:214` and `SKILL.md:118` both end the Stop Format with
"…or abort", and `MERGE_AND_REBASE.md:125-129` explicitly forbids deleting a run
directory to get rid of it.

So a developer who changes their mind has two options: drive the run all the way
through delivery, or leave a permanently incomplete run in `.agentic/runs/`
forever. There is also no `aegis run list`, so finding that orphan later means
listing the directory by hand.

A workflow whose own stop menu offers an action the CLI cannot perform will make
the agent hallucinate the command.

### Fix

Add `aegis run abandon --reason "<text>"`:

- New subparser beside `select` in `cli.py:227`.
- Sets `graph.complete = True` and a new `graph.outcome = "abandoned"` field.
- Appends a `run.abandoned` journal event carrying the reason.
- Clears `.agentic/.workspace/state/current_run`.

Add `aegis run list` — read `.agentic/runs/*/graph.json`, print run_id, kind,
profile, stage, complete/outcome.

Then change the `or abort` in `AGENTS.md:214` and `SKILL.md:118` to
`or abandon the run with \`aegis run abandon --reason "<text>"\``.

---

## W3 — Routing backwards is gated by the blockers of the stage you are leaving

**Severity: high (punishes the honest correction)** · **Verification: READ**

Files: `stage_forms.py:438-440`, `:921-937`, `:1017-1022`, `:991-993`, `:1026-1028`

### The obstruction

`route_to` is honored only inside `close_stage` (`_advance_stage`), and
`close_stage` refuses to close while any blocker stands:

```python
raise StageOperationError("; ".join(blockers))
```

At the implementation stage, `_evidence_stage_blockers` emits
`CHK-x is missing prior red evidence` and `CHK-x has no active green evidence`
for **every** imported check. So a developer who realizes at implementation that
the requirements were wrong must first produce red *and* green evidence for
checks they are about to delete — or file one waiver per check, each needing
separate explicit human approval.

The same trap exists at check → requirement (red evidence required first) and at
validation → anywhere (`diff_review` / `documentation_review` / `style_review`
must read `pass` or `not-applicable`).

**No document mentions this interaction.** This is the worst dead end in the
payload: the honest act (stop, the contract is wrong) costs more than the
dishonest one (fabricate evidence and close forward).

### Fix

Routing backwards is not an approval of the current stage, so gating it on that
stage's completeness is the wrong test. Add a route fast-path in `close_stage`:
when `record.route_to` is set and names an earlier stage, skip **evidence**
blockers while still enforcing structural and control validity, and journal
`stage.routed` with a `blockers_deferred` list so nothing is hidden.

Then document it — a `## Changing direction mid-run` section in `AGENTS.md`
(after line 196) and in `reference/implementation.md`, stating that routing takes
effect at `stage close`, and naming the blocker ID shapes
`red-before-green:<check-id>` and `stage:implementation:<check-id>:green-evidence`.

---

## W4 — `aegis config validate` always says to start a new feature run

**Severity: high (actively misdirects, fires on every skill bootstrap)** · **Verification: EXECUTED**

Files: `cli.py:786`; callers `AGENTS.md:22-23`, `documentation-audit/SKILL.md:18`, `python-codestyle-audit/SKILL.md:18`, `write-component-documentation/SKILL.md:19`, `agentic-delivery/SKILL.md:15`

### The obstruction

The `next` field of `config validate` and `config show` is a hardcoded string:

```python
"next": "aegis run start feature",
```

It never consults the selected run. Five documents order the agent to run
`config validate` at the start of *every* skill, and the whole protocol trains
the agent to obey `next` literally. An agent that invokes `/documentation-audit`
midway through a validation stage is told by AEGIS itself to start a second
feature run.

### Fix

In `_config_command` (`cli.py:770-798`), resolve the selected run; if one exists
and is not complete, return `next_command(graph, root)`. Fall back to
`aegis run start feature` only when no run is selected.

---

## W5 — Hook failures deny writes to the very file that would fix them

**Severity: high (unrecoverable from inside the agent)** · **Verification: READ**

Files: `guard_write_zone.py:80-81`, `guard_shell_write.py:129-130`, `secret_scan.py:49-50`, `guard_read_path.py:143-144`

### The obstruction

Every hook treats an internal exception as `deny`. A malformed
`.agentic/workflow.toml` therefore makes `load_config` raise inside the hook,
which denies `Edit` and `Write` on **every path — including
`.agentic/workflow.toml` itself**, and `guard_read_path` denies reading it too.

The agent cannot read or repair the file causing the denial. The only exit is a
human editing it outside the agent. This is a hard deadlock produced by a typo.

### Fix

In each hook's `except` branch, allow the operation when every target path is the
workflow config (or under `.agentic/`):

```python
if all(t.endswith(".agentic/workflow.toml") for t in targets):
    return 0
```

About three lines per hook, no CLI or test-suite impact.

---

## W6 — A corrupt journal line disables the escape hatch itself

**Severity: high** · **Verification: READ**

Files: `store.py:1041`, `:1097`, `:1140`

### The obstruction

`add_waiver` calls `_validate_journal_records` before minting the waiver. A
single partial or invalid journal line therefore makes **every** waiver
unmintable while all the blockers remain in force. The escape hatch is gated on
the integrity of an append-only log that a crash mid-write can truncate.

### Fix

Either downgrade the check inside `add_waiver` to a warning recorded in the
waiver reason, or add `aegis run repair-journal` that truncates to the last
complete valid record and journals the truncation. One function in `store.py`.

---

## W7 — Two stage blockers are deliberately non-waivable

**Severity: medium** · **Verification: READ** · File: `stage_forms.py:757-771`

### The obstruction

`_is_non_waivable_stage_blocker` excludes two descriptions from waiver targets:

- `"cited requirement integrity cannot be verified: …"` — triggered by *any*
  `OSError`/`ValueError` while reading a cited requirement, including a transient
  read failure. The design stage then cannot close, with no override.
- `"required RepoWise discovery is not current: …"` — adoption runs only.

### Fix

Delete both branches so they become ordinary waivable stage blockers, and let the
waiver record carry the exception text. The human still approves each waiver, so
nothing is silently bypassed — the difference is that a transient filesystem
error stops being terminal.

---

## W8 — A malformed requirement file anywhere kills blocker enumeration

**Severity: medium** · **Verification: READ** · File: `requirement_store.py:291-308`

### The obstruction

`load_requirement_index` walks `rglob("*.toml")` and raises on the first bad
file. `evaluate()` calls it, so `waive list` and `verify run` both die — meaning
the blocker cannot even be *enumerated*, let alone waived. (This is the same
failure amplified by **B3**.)

The error does name the file and key, which is the saving grace.

### Fix

In `evaluate()` only, wrap the index load in
`try / except RequirementValidationError` and emit a failed-but-waivable
invariant result carrying the parse error. About eight lines in `invariants.py`.

---

## W9 — Generated forms carry no guidance and the accepted vocabularies are undocumented

**Severity: medium (a failed close per field, every run)** · **Verification: READ**

Files: `stage_schema.py:41-43`, `stage_forms.py:1336-1345`, `:1026-1028`, `:974-976`, `:1023-1025`

### The obstruction

`StageFieldSpec` carries `help` text that is explicitly **not rendered**, and
`_single_form_text` emits bare `key = value` lines. The agent sees
`diff_review = "pending"` with no hint that only `"pass"` and `"not-applicable"`
clear the blocker; `decision = "pending"` with no hint that delivery requires
exactly `"approved"`; `deterministic_verification = []` with no statement of what
a verification reference even is. Each costs a failed close and a guess.

### Fix

Render the help that already exists. Change `_single_form_text` to emit
`# <help> — accepted: <values>` above each key, and add
`accepted: tuple[str, ...] = ()` to `StageFieldSpec`, populated for
`diff_review` / `documentation_review` / `style_review` (`pass`,
`not-applicable`), delivery and baseline `decision` (`approved`, `rejected`,
`pending`), component-map `approval_decision`, and alignment `decision`.

Zero behavior change, removes a recurring stall.

---

## W10 — The `--quick` profile is not proportional

**Severity: medium** · **Verification: READ**

### The obstruction

A one-line fix costs **15 CLI invocations, 6 file edits, and 4 human approval
round-trips**. The quick profile removes four of eight stages but only about 55%
of the commands, because the surviving stages carry the same
prepare/apply/close/verify ceremony.

The worst part is the manual-evidence dance: `evidence prepare add` → edit form →
`evidence apply` → **copy the minted `E-NNNN` by hand into
`linked_check_evidence`**. That transcription between two files exists only to
satisfy INV-6 and is the most error-prone step in the payload.

For comparison, a medium feature run costs roughly 36 CLI invocations, 34 file
edits, and 8 human stops — about nine governance actions per productive file
edit.

### Fix

For `profile == "quick"`, have `stage prepare` at implementation auto-generate
`manual-evidence.toml` alongside `implementation.toml` and pre-fill
`linked_check_evidence` with the ID minted at `evidence apply`
(`evidence_forms.py:87`). Removes two of the fifteen commands and the only
hand-transcribed identifier in the workflow.

---

## W11 — Error messages diagnose without prescribing

**Severity: medium (cheap to fix, high cumulative value)** · **Verification: READ**

Each of these is a text-only change. The pattern to apply: **every hard-fail
message ends with the command that resolves it.**

| Message | File:line | Append |
|---|---|---|
| `GraphConflictError` "Reload the run and retry" | `store.py:137` | `Retry the same command; if it repeats, run \`aegis run status\` first.` |
| `LockTimeoutError` | `persistence.py:52-71` | `A crashed process releases its lock automatically; if this persists, no other AEGIS process is running and the failure is a filesystem permission problem.` |
| "run is complete; no stage can be prepared" | `stage_forms.py:203` | `Start a follow-up run with \`aegis run start fix --quick\`; a closed run is never reopened.` |
| "refusing to overwrite existing form" | `stage_forms.py:266-268` | `Delete it, or run \`aegis stage prepare\` to regenerate the set.` |
| "evidence id is stale or was not generated by AEGIS" | `evidence_forms.py:133-136` | `Re-run \`aegis evidence prepare add\` and copy your values into the regenerated form.` |
| "unknown key X" / "revision must be N" / "missing required key" | `stage_forms.py:2025`, `:1963-1965`, `:1385-1387` | `Run \`aegis stage prepare\` to regenerate the current-revision form.` |
| `RUN-POINTER-INVALID` / `RUN-POINTER-STALE` | `store.py:478-487`, `:524-535` | Reuse `_pointer_missing_remediation(...)` — `RUN-POINTER-MISSING` at `store.py:423-453` already lists recoverable run IDs and the exact `aegis run select` command. Two lines each. |
| `RequirementConflictError` "reload it and retry" | `requirement_store.py:107` | Name the command. |
| Stage close blocker list | `stage_forms.py:440` | `Run \`aegis waive list\` for waivable blocker IDs.` |

`ConfigurationError` is already exemplary — it names the offending key, the legal
values, and the follow-up command. It is the model the others should copy.

---

## W12 — WITHDRAWN 2026-08-04. Revert if implemented.

**This finding was wrong and must be reverted.** It was implemented in Batch 2;
the revert is the first task of Batch 3.

### What W12 originally proposed

For invariants that do not set their own `state_digests` (INV-1, INV-2, INV-5,
INV-6, INV-8, INV-9), the digest is computed over `{"id", "message"}`, and the
message embeds the offender list (`"Missing checks for: A, B"`). W12 claimed that
adding an unrelated requirement stales the waiver and forces a re-approval
"that carries no new information", and proposed digesting `{"id": result.id}`
only.

### Why it was wrong

The premise is false. The message is **derived from** the offender list, so it
cannot churn unless the offender set actually changes — and when the offender set
changes, re-approval carries exactly the information that matters: a human
approved offenders A and B, and there is now also a C they never saw.

Dropping the message from the digest therefore does not remove meaningless
churn — it silently extends a human approval to offenders the human never
reviewed. In a system whose purpose is governance and integrity, that is a defect,
not a friction reduction.

The Batch 2 implementer surfaced the worst cases: W12 as written also widens
**INV-5** (in-scope paths) and **INV-9** (component baseline). For those two the
offender's *identity is the entire substance* of the approval — a waiver for
out-of-scope path X would silently cover a different out-of-scope path Y added
later. The original finding named INV-9 without noticing this and missed INV-5
entirely.

### Fix

Revert to digesting `{"id": result.id, "message": result.message}` on the
message-fallback path. INV-3, INV-4, INV-7 and INV-10 pin their own structured
state and were never affected either way.

### If waiver churn is ever genuinely observed

The fix is to make the offender list **deterministically ordered** (sort it before
`', '.join(...)`) so the message is stable whenever the set is stable — not to
remove the set from the digest. Only a message that can churn while the offender
set is unchanged is a real problem, and sorting eliminates that class.

---

## W20 — INV-3 digests an unsorted offender list

**Severity: low** · **Raised by the Batch 4 implementer, 2026-08-04** · File: `invariants.py`

Same class as W18, but outside the set W18 named: INV-3 pins its own structured
state via `state_digests({"missing": missing})` rather than falling back to the
message, so the sorting sweep did not reach it. An ordering change in `missing`
stales an INV-3 waiver even though the offender set is unchanged.

**Fix:** sort `missing` before it enters `state_digests`. One line. Audit the
other invariants that pin structured state (INV-4, INV-7, INV-10) for collections
digested in nondeterministic order while you are there.

**Assigned to Batch 5.**

---

## W21 — `next_command` does not know about `route_to`

**Severity: medium** · **Raised by the Batch 4 implementer, 2026-08-04** · File: `stage_forms.py` (`next_command`)

With W3 implemented, an agent at the implementation stage that has set
`route_to` and has only evidence blockers left is now able to close and route
backwards — but `next_command` still tells it to run `aegis check run`.

`next_command` is the single most trusted output in the protocol; the agent
follows it literally. Telling it to gather evidence for checks it is about to
delete is precisely the friction W3 was written to remove, re-introduced through
the guidance channel.

**Fix:** when `record.route_to` is set and the only remaining blockers are the
evidence blockers W3 defers, `next_command` should return `aegis stage close`.

**Assigned to Batch 5.**

---

## W18 — INV-1's offender list is unsorted, so waivers can stale on ordering alone

**Severity: low** · **Raised by the Batch 3 implementer, 2026-08-04** · File: `invariants.py` (`_coverage`)

`missing` is built from `requirements.values()` — dict insertion order, derived
from the register walk — and is not sorted before `', '.join(...)`.

With W12 reverted the message is back in the waiver digest, so a change in
*ordering alone* now stales a waiver even though the offender **set** is
unchanged. This is exactly the churn class the W12 closing note identifies as the
one real problem, and names the correct fix for.

**Fix:** sort the list. One line:

```python
missing = sorted(item.id for item in requirements.values() if ...)
```

Check the other message-fallback invariants for the same pattern while you are
there (INV-2, INV-5, INV-6, INV-8, INV-9) — any that join a collection into their
message need the same treatment, for the same reason.

**Assigned to Batch 4 as task 0** — it is one line and it closes out the W12 arc.

---

## W19 — A run with a corrupt graph cannot be abandoned

**Severity: medium** · **Raised by the Batch 3 implementer, 2026-08-04** · Files: `store.py`, `cli.py`

`run abandon` (added by W2) requires a resolvable run, so the escape hatch does
not work in the case that most needs it: a run whose `graph.json` is unreadable or
schema-invalid. The only exit is `run start`, which since W16 at least warns that
it is leaving a run behind — but the orphan stays in `.agentic/runs/` forever and
`run list` may not be able to render it either.

This is the same family as **W17** and **B20**: recovery paths must keep working
when the state they read is exactly what is broken.

**Fix:** let `run abandon` operate on a run **ID** without loading its graph —
write the abandonment to the journal and clear the current-run pointer, tolerating
an unparseable graph. If the graph cannot be loaded, say so in the output rather
than refusing the command. Make `run list` degrade the same way: render an
unreadable run as a row carrying the parse error instead of failing the whole
listing.

**Assigned to Batch 5.**

---

## W17 — `waive list` still dies on a malformed requirement file (W8 residual)

**Severity: high** · **Verification: EXECUTED during Batch 2** · Files: `requirements.py`, `waiver_targets.py`, `verification.py:115`

### The obstruction

W8's specified fix scoped the `try / except RequirementValidationError` to
`invariants.evaluate()` only. That was insufficient. `waiver_targets.collect_waiver_targets`
calls `audit_traceability` and `audit_coverage`, which load the requirement
register **independently** of `evaluate()`, and `verification.py:115` does the same.

Confirmed by execution after Batch 2:

```
waive list RAISES: RequirementValidationError
.agentic/requirements/bad.toml: category: required key is missing
```

So W8's stated obstruction — *"the blocker cannot even be enumerated, let alone
waived"* — **survives**. Batch 2 improved the failure from an uncaught raise to a
typed error inside the CLI boundary that names the file and key, which is real
progress, but the escape hatch is still unreachable.

This is the same amplification path as **B3**: one malformed requirement file
disables the mechanism for recovering from it.

### Fix

Apply the same tolerance at the other two load sites so a malformed register
degrades to a waivable finding rather than an exception:

- `waiver_targets.collect_waiver_targets` — wrap the `audit_traceability` /
  `audit_coverage` calls so a `RequirementValidationError` yields a synthetic
  waivable blocker carrying the parse error, instead of propagating.
- `verification.py:115` — same treatment.

Assign to **Batch 5** by file coupling. Verify by reproducing the command above
and asserting `waive list` returns a blocker list naming the bad file.

---

## Documentation defects

These mislead the agent but change no behavior.

| # | Doc says | Code does | Fix |
|---|---|---|---|
| D1 | `AGENTS.md:117`, `INVARIANTS.md:19,21`, `SKILL.md:93` — red-before-green is a **fix** rule | `stage_forms.py:988-993` requires red evidence per check for **all** full runs, kind-independent (**EXECUTED**) | Reword the docs to "every full run", or add `if graph.intent.kind == "fix"` at `:991` if fix-only was the intent |
| D2 | `CLI_API_REFERENCE.md:138-140` — quick runs mark "INV-1, INV-2, INV-8, and INV-10" not-applicable | `invariants.py:166-192` marks **five**, including **INV-3** (**EXECUTED**). `INVARIANTS.md:7-9` is correct; the CLI reference contradicts itself at `:174` | Add INV-3 |
| D10 | `INVARIANTS.md:19` and `:30-34` — INV-1 is "Every non-retired requirement has a check" | **Stale as of Batch 2 (B10).** INV-1 is now scoped to requirements the run owns | Reword to "every non-retired requirement **this run owns**", and point at `REQ-LINK-MISSING` for repository-wide coverage. Raised by the Batch 2 implementer |
| D3 | `requirements/README.md:109` — "Use `spec_template.md` as the starting point" | `stage_forms.py:270-282` auto-creates the companion spec from `_companion_spec_template()`, a *different* 3-heading structure. `spec_template.md` is read by no code — grep finds exactly one reference, that README line | Say the CLI generates the scaffold at `spec_ref`; keep `spec_template.md` as the reference for a hand-placed spec outside a run |
| D4 | `PROMPT_CHEATSHEET.md:110-116` — run `waegis repowise status --repo "<project>"` | WAEGIS is never copied into a governed repo (`GLOSSARY.md:236-240`); command not found | Mark the block "run from the WAEGIS host, not inside the governed repo" |
| D5 | `agentic-delivery/SKILL.md:24` + delivery form field + `hooks/README.md:22` all say "preflight" | Three unrelated meanings; no `aegis delivery preflight` command exists | Rename the form field to `preflight_reference` (`stage_schema.py:164`) |
| D6 | `CLI_API_REFERENCE.md:30-37` documents four response keys | Undocumented extras: `readiness`, `waived_blockers`, `waived_gates`, `advisories`, `eligible_blockers`, `waiver_history`, `run_profile`, `bypass_status`, `bypassed_stages` | Add an "additional keys by command" table plus the exit-code contract (0 / 1 blocked / 2 argparse) |
| D7 | No doc states where run state lives | `graph.json`, `journal.jsonl`, `design.md`, `report.md`, `validation-summary.json`, `stages/<stage>/*.toml`, `.agentic/.workspace/state/current_run` | Add a "Where state lives" table to `CLI_API_REFERENCE.md` after line 126 |
| D8 | `.claude` and `.qwen` `documentation-audit/SKILL.md:28` say "run it" | `.agentic` source and `.codex` copy both say "run it **in changed-only mode**" | Restore the two dropped words |
| D9 | `How_To_Start_A_New_Project.md:99-104` includes `stage show` in the loop | `AGENTS.md:52-60` and `SKILL.md:63-69` omit it | Pick one and make all three agree |

Also undocumented, and worth stating because agents rely on it: `close_stage`
auto-prepares the successor stage (`stage_forms.py:453`), so the manual
`stage prepare` the docs imply per stage is unnecessary. And `prepare_stage` is
idempotent while a form is unimported, but **deletes every file in the stage
directory** on a genuine re-prepare (`stage_forms.py:786-789`).

---

## Suggested order

Highest value per line changed:

1. **W4** — one function, stops AEGIS from misdirecting the agent on every skill bootstrap.
2. **W1** — one flag; removes the only deterministic dead end in a feature run.
3. **W2** — one subcommand pair; gives every run an exit.
4. **W5** — three lines per hook; removes a config-typo deadlock.
5. **W11** — pure text; every message gains its remediation command.
6. **W9** — renders help that already exists in the schema.
7. **W3** — the route fast-path; the design fix matters more than the code.
8. **W6**, **W7**, **W8** — un-gate the escape hatch in its three failure modes.
9. **W10**, **W12** — proportionality and waiver churn.
10. Documentation defects D1–D9.

## What is working and should not be touched

- The invariant layer's waiver coverage: all ten invariants have a real hatch, and
  `verification.py:185` correctly excludes waived failures from the exit code, so
  the hatch reaches the delivery hook.
- `waiver_targets.collect_waiver_targets` unifying stage, invariant, gate, audit,
  and working-tree blockers into one discoverable `waive list`.
- `next_command` (`stage_forms.py:511-576`).
- The shipped template shipping everything `disabled` / `unrestricted`.
- `route_to` restricted to earlier stages (`stage_forms.py:1845-1848`) — a
  deliberate lifecycle property, not a defect.
