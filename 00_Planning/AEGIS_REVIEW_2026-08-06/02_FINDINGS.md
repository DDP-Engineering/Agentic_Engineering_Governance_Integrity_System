# Findings — AEGIS V2 Lifecycle Field Test, 2026-08-06

`W*` = WAEGIS deployment wizard. `A*` = AEGIS governance CLI and payload.
Every finding was **reproduced by execution** against `F:\2026_VoiceWeaver`
during this run. Source paths are relative to
`05_Software/waegis/` or `05_Software/aegis/template/.agentic/cli/src/aegis/`.

Severity: **blocking** = stops the workflow with no working documented way out;
**obstruction** = costs the operator real time or misleads them; **defect** =
wrong behavior with a workaround; **doc** = documentation disagrees with code.

---

## A1 — INV-7 matches AEGIS's own generated artifacts — *blocking*

`aegis verify run` writes `validation-summary.json` into the untracked run
directory. That file embeds the invariant table verbatim, including INV-7's own
name and its own *passing* message:

```json
"name": "Clean secrets",
"message": "No configured secret pattern found in diff or untracked files."
```

INV-7 then scans the diff and untracked files for the configured secret
patterns. With `(?i)secret` — the obvious pattern for anyone enabling secret
scanning — it matches its own output. `report.md` and `graph.json` match too, for
the same reason.

**Reproduction.** With `secrets_mode = "enforce"` and `(?i)secret` among
`secret_patterns`:

```text
$ aegis verify invariants
  "id": "INV-7", "holds": false, "message": "Secret pattern matched: (?i)secret"

$ mv .agentic/runs/<id>/validation-summary.json /tmp/
$ aegis verify invariants
  "id": "INV-7", "holds": true

$ aegis verify run          # regenerates the file
$ aegis verify invariants
  "id": "INV-7", "holds": false
```

No repository content matched. Confirmed by scanning every changed and untracked
file: the only hits were AEGIS's own `validation-summary.json`, `report.md`, and
`graph.json`.

**Fix.** Exclude the active run directory (`.agentic/runs/<current-run-id>/`)
from the INV-7 scan surface. It is tool output, not authored content, and the
tool is the only writer.

---

## A2 — Recording a waiver for INV-7 invalidates that waiver — *blocking*

Waivers pin a `state_digest` of the blocker they cover. `waive add INV-7` writes
the waiver's `reason` and `blocker_id` into `graph.json`. `graph.json` is one of
the files INV-7 scans (A1). So recording the waiver changes the blocker's state
digest, and the waiver — pinned to the digest as it was one instant earlier — is
immediately stale.

**Reproduction.**

```text
$ aegis waive add INV-7 --reason "..."
  status: ok   (waiver WVR-8d375c06 created, pins invariant:INV-7 = a9e5310f...)

$ aegis verify invariants
  "id": "INV-7", "waived": true

$ aegis stage close
  error: invariant INV-7 does not hold

$ aegis waive list
  active_waivers: []                       <- the waiver is gone
  eligible_blockers: INV-7 digest bf6febf3...   <- digest moved

$ aegis waive add INV-7 --reason "..."     # identical command, second time
$ aegis stage close
  complete: True
```

The blocker digest moved from `a9e5310f` to `bf6febf3` because the match set grew
from one file (`validation-summary.json`) to three (plus `graph.json` and
`report.md`) — and `graph.json` matched *because the first waiver was written
into it*.

Every INV-7 waiver therefore has to be issued twice. Nothing tells the operator
that; the second attempt looks like superstition.

**Fix.** The general rule: state an invariant reads must not be state that
recording a waiver for that invariant writes. Fixing A1 fixes this as a side
effect, since `graph.json` lives in the run directory. Independently, the stale
waiver should be reported (`waiver WVR-... went stale: blocker state changed`)
rather than silently vanishing from `active_waivers`.

---

## A3 — `non-waivable` is advertised but not enforced — *defect*

INV-7 reports itself as non-waivable, and is waivable anyway.

**Reproduction.**

```text
$ aegis verify invariants
  {"id": "INV-7", "holds": false, "policy": "non-waivable", ...}

$ aegis waive list
  eligible_blockers: [ {"id": "INV-7", ...} ]     <- listed as eligible

$ aegis waive add INV-7 --reason "probe"
  status: ok                                      <- accepted

$ aegis verify invariants
  {"id": "INV-7", "holds": false, "policy": "blocking", "waived": true}
```

The policy label silently changes from `non-waivable` to `blocking` once waived.
Of all ten invariants, secrets is the one where an absolute rule is actually
defensible — a real leaked credential should not be waivable by the agent that
leaked it.

**Fix.** Either enforce the label (`waive add` rejects it, and it never appears
in `eligible_blockers`), or stop advertising it. Given A1/A2 make INV-7 fire
spuriously today, enforcing it *before* fixing A1 would create a true dead end —
so fix A1 first, then enforce.

---

## A4 — INV-7 names the pattern but not the file — *obstruction*

```text
error: invariant INV-7 does not hold
"message": "Secret pattern matched: (?i)secret"
```

For a blocker presented as non-waivable, that is the entire diagnostic. Which
file, which line, which of the four configured patterns' matches — none of it is
there. Finding the culprit took a manual sweep of every changed and untracked
file.

The information exists: `aegis waive list` emits working-tree blocker ids that
*do* carry the path
(`working-tree:secret-pattern:.agentic/runs/.../validation-summary.json:bec5c0f1eabe`).
It is simply not in the message the operator is shown when they are stopped.

**Fix.** Put the matching path (and line number) into the INV-7 message, as the
working-tree finding already does. Do not echo the matched text.

---

## A5 — `scope-check` and `verify coverage` report "clean" when they are switched off — *defect*

`adoption scope-check` returns `issues: []` for every input when the component
baseline guard is disabled — including paths that do not exist.

**Reproduction** (baseline guard disabled, which is the WAEGIS default):

```text
$ aegis adoption scope-check 04_Software/VoiceWeaver/src/voiceweaver/config.py
  issues: []          # mapped path
$ aegis adoption scope-check 02_Tools/package_runtime.py
  issues: []          # unmapped, outside every source root
$ aegis adoption scope-check does/not/exist.py
  issues: []          # not a file
```

Cause, in `components.py::audit_local_scope`: `resolved_minimum` is `None`
because the guard is disabled, and the function returns `[]` before it loads the
manifest at all. `verify coverage` behaves the same way when
`traceability.coverage.mode = "disabled"`.

This matters because the adoption skill's `component-map` reference explicitly
instructs the agent to use these two commands to review the map. Under WAEGIS's
default configuration they cannot distinguish a mapped path from a typo.

**Fix.** Return a distinct `not-enforced` status (or a `policy: disabled`
advisory finding) rather than an empty issue list, so "switched off" and "nothing
wrong" stop being the same output. This is the highest-leverage small fix in the
review.

---

## A6 — The adoption route cannot create requirements — *blocking (documented dead end)*

The `component-adoption` stage form ships a `requirement_links` field. Its
reference says "Add or update component documentation, **requirement links**,
known test commands, and adoption notes". `SKILL.md` says "Adoption may update
workflow configuration, maps, **requirements**". And:

```text
$ aegis stage add --category functional
  error: stage add is valid only during requirement or check
```

`aegis requirement list|show` are read-only. The requirements README states:
*"Create or revise requirements only through requirement-stage forms."* No
adoption stage is a requirement stage.

**Result.** A repository that completes the entire seven-stage adoption route
ends with an empty `.agentic/requirements/`. Verified: `aegis requirement list`
returned `[]` after `component-map` closed.

**Workaround, which works.** Hand-author the requirement TOMLs and mint the
UUIDv4 ids by hand. Three were written this way; `aegis requirement list` picked
them up and `aegis verify traceability` returned no issues. This is presumably
what the earlier AudioMancer and VoiceWeaver migrations did.

**Fix (smallest that closes the dead end).** Allow `stage add --category` during
`component-adoption`. The requirement store already accepts the resulting files;
only the stage guard rejects the command. Failing that, the requirements README
and the adoption references must document hand-authoring as the supported path,
because today they document the opposite.

---

## A7 — Adoption never seeds `coverage_waivers.txt` — *obstruction*

Switching on `coverage_mode = "enforce"` after adoption produced **19**
`REQ-COVERAGE-MISSING` findings, one per source module with no Active
test-linked requirement. None were caused by the run that hit them.

The escape hatch exists and is documented for precisely this case —
`.agentic/requirements/coverage_waivers.txt`, *"Use this only for pre-existing
legacy modules that do not yet have requirement coverage"* — but ships empty, so
the operator transcribes 19 paths by hand at the exact moment they are trying to
turn enforcement on.

**Fix.** Have `baseline-review` (or `adoption-delivery`) offer to write every
currently-uncovered module under the configured coverage roots into
`coverage_waivers.txt`, with the run id in a comment. The adoption route already
computes exactly this set.

---

## A8 — Unresolved-question blockers are unreadable — *obstruction*

Closing a stage with a non-empty `unresolved_questions` produces the raw question
text as the error, with a doubled full stop and no blocker id:

```text
error: The test suite cannot run in full: ... has no pip to install it..
       Run `aegis waive list` for waivable blocker IDs.
```

The blocker id is a slugified 60-character prefix of the question plus a hash:
`stage:adoption-intake:the-test-suite-cannot-run-in-full-04-software-voiceweaver-tests-691667ca`.

It is workable — `waive list` does produce the id — but the error should carry
the id it is asking you to look up.

**Fix.** Include the blocker id in the close error and strip the trailing period
before appending punctuation.

---

## W1 — The analyzer proposes no test roots for non-top-level layouts — *blocking*

`repo/analyze.py::_propose_test_roots` matches `tests`/`test`/`spec` only via
`path.startswith(name + "/")` — repository root only. VoiceWeaver's suite lives
at `04_Software/VoiceWeaver/tests`, so nothing matched:

```text
Proposed test roots:
  none proposed (operator input required)
```

`test_roots` is then the one field that makes `--non-interactive` adoption
impossible:

```text
$ waegis adopt F:\2026_VoiceWeaver --non-interactive
  waegis adopt: --non-interactive requires a complete answer set; missing: test_roots
```

The message does not say what an answers file looks like or which format it
takes.

This is the layout AEGIS's own documentation promotes and that every repository
in this estate uses, including `05_Software/aegis` itself.

**Fix.** Search for conventional test directory names at any depth, not only at
the root, ranking shallower matches higher. The `__tests__` branch of the same
function already walks arbitrary depth — apply the same treatment to
`tests`/`test`/`spec`.

---

## W2 — Source-root proposal falls back to an entire numbered folder — *obstruction*

With no conventional match, `_propose_source_roots` fell through to the coverage
fallback and proposed:

```text
04_Software [low] - fallback: top-level directory holding 30 of 32 code files
```

`04_Software` also contains `.venv/`, `models/`, `outputs/`, and `logs/`. Adopted
as-is it would mark a virtual environment and generated audio as production
source for coverage, scope, and write-zone purposes.

**Fix.** Same as W1 — depth-aware detection of `src`/`app`/`lib` would have
proposed `04_Software/VoiceWeaver/src` directly.

---

## W3 — Gate extraction reads only root build files — *blocking (in effect)*

`_pyproject_candidates`, `_makefile_candidates`, and `_package_json_candidates`
all read `repo / "<file>"` — repository root only.
`04_Software/VoiceWeaver/pyproject.toml` declares both
`[tool.pytest.ini_options]` and `[tool.ruff]`, either of which the existing
heuristics would have converted into a gate candidate. Neither was seen:

```text
Gate command candidates (test):     none found
Gate command candidates (lint):     none found
```

Combined with `commands/adopt.py`, which seeds each gate's mode as
`"enforce" if gate_proposals[name] else "disabled"`, **every gate is deployed
disabled** for any repository whose build file is not at the root. Every gate
command in this test had to be typed by hand.

**Fix.** Discover build-system marker files at the source roots the analyzer just
proposed, not only at the repository root.

---

## W4 — Colocated-tests false positive cascades from W1 — *defect*

Because no test root was detected, `_detect_colocated_tests` concluded the
`test_*.py` files sit outside every test root and advised:

```text
note: test files matching test_*.py sit beside sources outside any detected test
root; write-zone patterns must become file-pattern-based rather than
directory-based
```

VoiceWeaver has a perfectly ordinary `tests/` directory. Following this advice
would produce a materially worse configuration.

**Fix.** Falls out of W1.

---

## W5 — The same gate command passes under AEGIS and fails under WAEGIS — *blocking*

`workflow.toml` stores gate commands as strings, and the field description
promises they are "Run exactly as given, **from the repo root**".

- **AEGIS** (`gates.py`) executes them via `shell=True`, so a
  repository-relative interpreter path resolves against the repository root.
- **WAEGIS** (`deploy.gates`) splits to argv and runs `shell=False`, so `argv[0]`
  is resolved against **WAEGIS's own working directory** and dies.

```text
WAEGIS:  gate 'test' FAILED: 04_Software/.../python.exe -m pytest ...
         could not be launched (command not found) in 0.009s (cwd: F:\2026_VoiceWeaver)
         reproduce with: cd 'F:\2026_VoiceWeaver' && 04_Software/.../python.exe -m pytest ...

AEGIS:   "test": {"status": "passed"}
         evidence log: 95 passed in 2.40s
```

The printed reproduction command **succeeds**. Minimal confirmation of the
mechanism:

```python
subprocess.run(['04_Software/.../python.exe','-m','ruff','--version'],
               cwd=r'F:\2026_VoiceWeaver')     # FileNotFoundError (WinError 2)
subprocess.run([r'F:\2026_VoiceWeaver\04_Software\...\python.exe','-m','ruff','--version'],
               cwd=r'F:\2026_VoiceWeaver')     # exit 0
```

`deploy.gates` exists to prove the gates the operator just configured actually
run. It produced a false negative and pushed toward `accept_failing_gates` on
commands that were already correct.

**Fix.** Resolve a relative `argv[0]` against the target repository root before
launching, or match AEGIS's execution model. The two must agree — they are
running the same stored string.

---

## W6 — Adoption cannot be resumed after a mid-run failure — *blocking*

`deploy.gates` (step 13 of 18) failed, leaving the payload copied and
`workflow.toml` generated but no smoke tests, no adoption commit, and no handoff.
The wizard's own remediation:

```text
remediation: Review the run journal for details and re-run the wizard; steps
             already green will be detected and skipped.
```

Re-running dies six steps earlier, at a step that was green the first time:

```text
[FAIL] Check for a prior AEGIS install: failed
       - AEGIS payload 2.1.0 is already installed and matches the bundled payload;
         consider 'waegis doctor --repo F:\2026_VoiceWeaver'.
error: refusing to answer a default-refuse question without an explicit decision:
       ... set 'adopt_over_existing_install' in the answers file
remediation: Run 'waegis doctor --repo TARGET' to check the existing install
             instead of re-adopting.
```

WAEGIS detects the payload **it just installed** as a prior install. The
suggested alternative, `waegis doctor`, is a diagnostic — it cannot finish the
adoption, commit the branch, or emit the handoff. The only way forward is the
undocumented `adopt_over_existing_install = true`.

A first adoption failing partway is the normal case, not the exotic one.

**Fix.** `repo.prior-install` should recognize an install produced by an
*incomplete run of this same wizard* (the journal already records the run id and
the manifest is present) and resume rather than refuse. At minimum, the
remediation text must name `adopt_over_existing_install` instead of pointing at
`doctor`.

---

## W7 — The handoff reports success while both gates are broken — *defect*

With `accept_failing_gates = true`, the step prints `[OK] done` and then lists
two failures underneath:

```text
[OK]   Try the quality gates once: done
       - gate 'lint' FAILED: ... could not be launched (command not found)
       - gate 'test' FAILED: ... could not be launched (command not found)
```

The closing summary says:

```text
AEGIS payload 2.1.0 adopted into F:\2026_VoiceWeaver by WAEGIS 1.2.0.
...WAEGIS's job ends here with a verified, committed adoption branch.
```

Nothing was verified. The word "verified" is in the final sentence the operator
reads, and the accepted-failing state appears nowhere in the summary.

To WAEGIS's credit, `waegis doctor` reports it accurately and persistently
afterwards, with log paths and blunt guidance. The gap is the handoff, not the
tracking.

**Fix.** When any gate is accepted-failing, drop "verified" from the handoff and
add a line naming the accepted-failing gates and the `doctor` command.

---

## W8 — The handoff points at a documentation section that does not exist — *doc*

Final instruction of a successful adoption:

```text
See '## Adopt An Existing Project' in .agentic/documents/PROMPT_CHEATSHEET.md
for the adoption-intake prompt.
```

The headings in that file are: Start or Resume, Alignment, Requirements, Design,
Check, Implementation, Validation, Delivery, Routing and Evidence,
Configuration, **Adoption Discovery**. There is no "Adopt An Existing Project",
and "Adoption Discovery" is nine lines about RepoWise synchronization — not an
adoption-intake prompt.

**Fix.** Point at `## Adoption Discovery`, or add the section the handoff
promises. This is the last thing the wizard says; it should resolve.

---

## W9 — A default adoption enforces nothing — *obstruction (owner decision)*

Every policy in the generated `workflow.toml`:

```toml
[components.baseline_guard]   mode = "disabled"
[traceability.coverage]       mode = "disabled"
[adoption.source_changes]     mode = "unrestricted"
[alignment.protected_scope]   mode = "disabled"
[guardrails.secrets]          mode = "disabled"
[guardrails.protected_paths]  mode = "disabled"
[guardrails.working_tree]     mode = "unrestricted"
[guardrails.write_access]     mode = "unrestricted"
[guardrails.scope]            mode = "unrestricted"
[guardrails.delivery]         mode = "disabled"
```

Only `[alignment] enabled = true` is on. Gates are enabled only when the analyzer
proposed commands — which W3 makes unlikely. Combined with A5, the adopted
repository answers "no issues" to every verification question it is asked.

Shipping conservative defaults is defensible under constraint 3 (do not block the
adopter), so **no default change is proposed here**. What is proposed is
visibility.

**Fix.** Have the adoption handoff print which policies are inactive, and have
`baseline-review` list them as follow-up gaps. Turning them on remains an
explicit `waegis configure` decision.

---

## W10 — A field with a shipped default becomes a required field with no default — *obstruction*

`WORKFLOW_FIELD_SPECS` gives `test_roots` a default of `["tests"]`.
`commands/adopt.py::_seeded_workflow_specs` overrides it with `tests or None`,
and `proposals.get(spec.key, spec.default)` returns that `None` (the key is
present, so `.get` never falls back). Interactively:

```text
Where do your tests live? (e.g. tests): test_roots has no default; a value is required
Where do your tests live? (e.g. tests): test_roots has no default; a value is required
... 78 times
```

No retry cap, no documented way to abort, and no suggestion offered even though a
sensible default exists in the spec.

The module docstring says this is deliberate ("or `None` (genuinely required)
when the analysis proposed none"), and as a design choice it is defensible — an
operator should not silently accept `tests` for a repository that has no `tests`
directory. The obstruction is entirely downstream of W1: fix the detection and
this field is proposed correctly. Listed here because the failure the operator
*sees* is this one.

**Fix.** Falls out of W1. Independently, the retry message should restate the
accepted format, and offer the spec default as a suggestion rather than claiming
none exists.

---

## W11 — Prompt rendering leaks Python repr and runs questions together — *defect*

```text
Marks these folders as production code: ...Where does your source code live?
(e.g. src, app; default: ['04_Software']): Folders where linked tests are looked
up...Where do your tests live? (e.g. tests):
```

Two problems: `['04_Software']` is a Python list repr in operator-facing text
(should be `04_Software`), and each question's description is emitted without a
line break, so the previous prompt, its answer echo, and the next description run
together on one line.

**Fix.** Format list defaults as comma-separated values; terminate the
description with a newline before the prompt.

---

## W12 — `configure` reports one validation error per invocation — *obstruction*

Building a valid policy set took three round trips, each surfacing exactly one
problem:

```text
1. workflow.toml invariant 1 violated: guardrails.secrets requires rules in enforce mode
2. expected a mapping from stage names to glob lists
3. stage mapping must be exact; missing=['adoption-alignment', ... 12 more], unknown=[]
```

Each message is good in isolation. The wizard already batches missing answers for
`--non-interactive` (`missing: test_roots` lists all of them at once), so the
convention exists — it just is not applied to policy validation.

**Fix.** Collect and report all policy validation failures in one pass, as
`require_non_interactive_answers` already does for missing answers.

---

## W13 — `write_access_stages` requires all 15 stages with no default — *obstruction*

Enabling `write_access_mode = "stage_restricted"` requires an exact mapping over
every stage in the system — all 8 standard plus all 7 adoption stages. There is
no partial form, no default, and no document listing them.

Mitigating: the error message enumerates every missing stage, which makes it
recoverable in one step. This is close to acceptable as-is.

**Fix (optional).** Treat an unlisted stage as "no write access" and warn, rather
than refusing the whole configuration; or ship a commented template in
`POLICY_CONFIGURATION.md`.

---

# Verified working

Behavior that was tested and behaved correctly, including two items open in the
08-04 review. Worth recording so the same ground is not re-covered.

| Behavior | Evidence |
|---|---|
| **Red-then-green enforcement** | `check` close refused: `CHK-... has no active red evidence`; after recording 7 failed / 6 passed it closed. `implementation` close refused: `has no active green evidence`; after 13 passed it closed. |
| **Requirement activation at validation closure** | INV-8 `not Active: REQ-...` and one `REQ-COVERAGE-MISSING` for the file the run had just covered; both cleared the instant validation closed. No deadlock. |
| **Gate evidence supersession** (08-04 `B11`) | `"supersede_reason": "superseded by a newer run of the same gate command"` observed in `graph.json`. |
| **`waive add --approver`** (08-04 open finding) | Flag exists, defaults to the git identity: `"approver": "Dan Dumitru Pasare <...>"`. |
| **`waegis doctor`** | Correctly reported both accepted-failing gates long after the adopt run, with log paths and honest guidance. The most trustworthy command in the system. |
| **`waegis configure`** | Rendered an exact 11-field before/after diff and refused invalid policy combinations before writing. |
| **Payload copy conflict handling** | Detected `.gitignore` and `CHANGELOG.md` conflicts with sizes and hashes, and kept local per the answers file. Nothing was silently overwritten. |
| **Stage form pre-population** | `repo-discovery` arrived with source roots, test roots, requirement roots, documentation roots, and both gate commands already filled from `workflow.toml`. |
| **Hand-authored requirements** | Three TOMLs written by hand were picked up by `requirement list` and passed `verify traceability` with no issues. |
| **Waiver state digests** | Waivers correctly pin and re-check blocker state — the mechanism is right; A2 is a case where the state being pinned is state the waiver itself moves. |
| **Companion spec scaffolding** | `stage add` at the requirement stage generated the `spec_ref` scaffold automatically at the recorded path. |

---

# Observations — deliberately not proposed as work

Recorded so the reasoning is on file.

**Adoption `readiness: {}` is empty at `run status`.** Cosmetic; the delivery
stage populates it. Not worth a change.

**`verify gates` prints only gate modes, not gate results.** The name suggests it
runs them; it does not — `verify run` does. Mildly surprising, but the output is
unambiguous once seen, and renaming a command is a larger change than the
confusion justifies.

**`workflow.toml` stores gate commands as strings, then re-splits them.** This is
the root enabler of W5, and a structured argv form would remove the ambiguity —
but that is a schema change across WAEGIS, AEGIS, and every deployed repository.
W5's fix is local and sufficient.

**Secret patterns are unanchored substring regexes over whole files.** Enabling
them on any repository that discusses security will produce matches on prose. A
proper secrets scanner is out of scope under constraint 2, and A1's fix removes
the case that actually broke this run.

**`fnmatch` semantics let `*` cross `/` in component paths.** Already documented
as a caveat in `COMPONENTS_CONFIGURATION.md` with the advice to verify boundaries
using `adoption scope-check` — which A5 shows is a no-op by default. Fixing A5
restores the mitigation; changing the matcher is not proposed.

**Hooks were not exercised.** Write-access and scope guardrails are enforced by
host hooks (`guard_write_zone.py`, `guard_shell_write.py`), which do not fire
when the CLI is driven from a plain shell as it was here. Nothing in this review
tests or disputes them; a separate hook-loading test would be needed.

**`test_adapters.py` cannot run in this repository** (numpy absent, and the
project venv has no pip). Pre-existing environment breakage, unrelated to AEGIS,
carried through the run as a recorded waiver and an accepted legacy risk — which
is exactly how the workflow is meant to carry it.
