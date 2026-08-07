# The AEGIS Logical Workflow — Analysis From A Full Run

What the lifecycle is supposed to do, what it actually did on
`F:\2026_VoiceWeaver`, and where the model leaks. Finding ids in parentheses
refer to [02_FINDINGS.md](02_FINDINGS.md).

## 1. The shape of the model

AEGIS is a **file-first state machine over git**. Three ideas carry the whole
design:

1. **The artifact is the interface.** Every stage generates a TOML (or Markdown)
   form; the agent edits the file; `stage apply` imports and digests it;
   `stage close` needs a human. Nothing meaningful is passed as a CLI flag, which
   is what stops an agent from asserting a decision in passing.
2. **Evidence is minted, not claimed.** Checks get CLI-minted ids, evidence gets
   ids (`E-0001`), and forms reference those ids rather than restating outcomes.
   An agent cannot write "tests pass" into a form and have it count.
3. **Two registers, different lifetimes.** `.agentic/runs/<id>/` is run-local and
   disposable; `.agentic/requirements/` is the durable repository contract. Runs
   record what was done; requirements record what the project promises.

There are three routes through it:

```text
adoption:  adoption-intake → adoption-alignment → repo-discovery → component-map
           → component-adoption → baseline-review → adoption-delivery
full:      intake → alignment → requirement → design → check → implementation
           → validation → delivery
quick:     intake → implementation → validation → delivery
```

The routes are well chosen. Adoption exists because you cannot govern a
repository you have not described; quick exists because a proportional route is
the only thing that stops people routing around the system entirely.

## 2. Stage by stage, as it actually behaved

### Deployment (WAEGIS, outside the governed repo)

`analyze → adopt → configure → doctor`. The separation is right: WAEGIS is never
copied into the governed repo, so the wizard cannot be tampered with by the
agent it configures.

What happened: `analyze` inspected 75 tracked files, correctly ranked the project
as Python, and then proposed **`04_Software` as the source root and nothing at all
as the test root**, because every root heuristic matches only at the repository
root (`W1`, `W2`). Gate extraction reads only the root `pyproject.toml`,
`Makefile`, and `package.json`, so VoiceWeaver's `[tool.pytest.ini_options]` and
`[tool.ruff]` — one directory down — produced **zero** gate candidates (`W3`).
A cascading false positive followed: because no test root was found, the
colocated-tests heuristic reported that tests sit beside sources and advised
switching write zones to file patterns, for a repository with an entirely
ordinary `tests/` directory (`W4`).

This is not an exotic layout. It is the numbered-folder convention AEGIS's own
documentation promotes, and the one this repository itself uses
(`05_Software/aegis`). The wizard does not understand its own house style.

The adoption then stopped three times, each stop needing knowledge the operator
had no way to have:

1. `--non-interactive` refused with `missing: test_roots` — and did not say what
   an answers file looks like (`W1`).
2. `deploy.gates` failed both gates with `command not found` and demanded an
   explicit `accept_failing_gates` decision (`W5`).
3. On re-run, `repo.prior-install` failed because the payload WAEGIS had just
   installed was now detected as a prior install — so the wizard's own
   remediation, "re-run the wizard; steps already green will be detected and
   skipped", is dead (`W6`).

The third is the worst of the three, because a mid-run failure is the *normal*
outcome for a first adoption and the printed recovery path does not work.

### The adoption route

This route is the strongest-designed part of the system and the most
under-served by its tooling.

`adoption-intake` correctly refused to close while `unresolved_questions` was
non-empty, and pointed at `waive list`, which produced a stable waivable blocker
id. That is exactly the escape-hatch shape the design calls for.

`repo-discovery` arrived pre-populated from `workflow.toml` with roots and gate
commands — a small thing that materially reduces the chance of the agent
inventing facts.

`component-map` is where the model shows its teeth: it forces every source file
into exactly one named component with an honest `adoption_status`, and the
reference explicitly tells the agent to "mark unknown or risky areas honestly
instead of stretching a component boundary to make the map look complete." That
instruction is worth keeping verbatim.

But the two commands the reference tells the agent to use to *review* that map —
`adoption scope-check` and `verify coverage` — returned `issues: []` for a mapped
path, an unmapped path outside the source root, and a path that does not exist at
all (`A5`). Both are governed by a policy mode that WAEGIS had left disabled, and
neither says so. Their output is indistinguishable from a genuine pass.

`component-adoption` is where the route breaks structurally. Its form has a
`requirement_links` field. Its reference says to add requirement links.
`SKILL.md` says adoption may update requirements. And `stage add` — the only
documented way to mint a requirement id — answers `stage add is valid only during
requirement or check` (`A6`). The requirement commands are read-only. So the
adoption route, whose entire purpose is to produce the durable description a
governed repository needs, **cannot produce the durable description**. A
repository that walks the full route ends with an empty register.

Hand-authoring the TOML files works, passes `verify traceability`, and is what
the earlier VoiceWeaver and AudioMancer migrations must have done. It is simply
undocumented and directly contradicted by the requirements README.

### The full change route

This route worked, and worked well.

`intake → alignment → requirement → design → check` behaved as designed: the
requirement stage minted an id and generated a companion-spec scaffold at
`spec_ref`; the design stage produced a Markdown document whose form cites the
requirement id explicitly, so the design cannot silently drift from what it
claims to implement.

**The check/implementation pair is the best thing in AEGIS.** `stage close` at
check refused with `CHK-... has no active red evidence`; after recording a
genuinely failing run (7 failed, 6 passed), it closed. Implementation then
refused with `CHK-... has no active green evidence` until the same check was
recorded passing. Test-first is not advice here, it is a state transition. An
agent cannot skip it, and cannot fake it, because the evidence carries a
CLI-minted id and an exit status.

Validation exposed a moment that *looks* like a deadlock and is not. A new
requirement is `Planned` while the run is in flight, so mid-run `verify
invariants` reports INV-8 failing (`not Active: REQ-...`) and `verify coverage`
reports the very file the run just covered as uncovered. Both clear the instant
validation closes, because closure activates eligible Planned requirements. The
design is right; only the intermediate reporting is alarming.

What validation *did* expose is real: enabling `coverage_mode = enforce` on a
freshly adopted legacy repository produced 19 `REQ-COVERAGE-MISSING` findings,
one per module that had no requirement — none of them caused by the run. The
escape hatch exists and is documented for exactly this case
(`.agentic/requirements/coverage_waivers.txt`, "use this only for pre-existing
legacy modules"), but adoption never seeds it, so the list must be transcribed by
hand at the moment enforcement is switched on (`A7`).

Delivery is where the secrets invariant collapsed (`A1`–`A4`). Details in the
findings; the short version is that AEGIS's own generated artifacts match the
secret patterns, the resulting blocker is labelled non-waivable but is waivable,
and the act of waiving it invalidates the waiver.

## 3. The four structural seams

Individually the findings look like a list of bugs. They are not. They cluster
into four seams where two parts of the system disagree about the same fact.

### Seam 1 — WAEGIS and AEGIS disagree about what a gate command is

`workflow.toml` stores gate commands as **strings**. AEGIS executes them through
`shell=True` (`gates.py`), so a repository-relative interpreter path resolves
against the repository root. WAEGIS executes them through `shell=False` with an
argv list, so the same string is resolved against **WAEGIS's own working
directory** and dies with `command not found` (`W5`).

The consequence is not cosmetic. `deploy.gates` — the step whose entire job is to
prove the gates the operator just configured actually run — produced a false
negative on commands that AEGIS then ran successfully, 95 tests green. WAEGIS
even printed `reproduce with: cd 'F:\2026_VoiceWeaver' && <cmd>`, and that
reproduction command succeeds. The operator is told their gates are broken,
offered `accept_failing_gates`, and pushed toward rewriting commands that were
already correct.

### Seam 2 — "disabled" and "clean" are the same output

`adoption scope-check` and `verify coverage` return `issues: []` both when
nothing is wrong and when the policy governing them is switched off (`A5`). The
root cause is visible in `components.py`: `audit_local_scope` resolves the
minimum completion level, finds `None` because the guard is disabled, and returns
`[]` before it reads the manifest at all — so even a nonexistent path reports
clean.

Combine that with `W9` (WAEGIS ships everything disabled) and the result is a
system that, out of the box, answers "no issues" to every question it is asked.
An operator following the adoption skill's own instructions to review the
component map with these commands learns nothing and is told nothing is wrong.

This is the single highest-leverage fix in the review, and it is small: report
`not-enforced` as a distinct state from `no issues`.

### Seam 3 — the tool's own artifacts are inside the surface it inspects

INV-7 scans the diff and untracked files for secret patterns. AEGIS writes
`validation-summary.json`, `report.md`, and `graph.json` into the untracked run
directory. Those files contain the invariant's own name (`"Clean secrets"`) and
its own message (`"No configured secret pattern found in diff or untracked
files."`). With `(?i)secret` configured, the scanner finds itself (`A1`).

The same seam makes the escape hatch self-defeating. `waive add INV-7` writes the
waiver's reason and blocker id into `graph.json`; `graph.json` is scanned by
INV-7; the blocker's state digest changes; the waiver pinned to the old digest
goes stale. `stage close` is refused. Issuing the identical waiver a second time
succeeds, because by then the state has stopped moving (`A2`). Reproduced
exactly, twice.

The generic statement of the seam: **any state that an invariant reads must not
be state that recording a waiver for that invariant writes.**

### Seam 4 — adoption is asked to produce what only a change run can produce

The adoption route's deliverable is a described repository: components, docs,
and requirements. It can produce the first two. The third is reachable only
through `stage add`, which is gated to the `requirement` and `check` stages of a
non-adoption run (`A6`).

There is no dead end for the agent — hand-authoring works and passes every audit
— but there is a documentation dead end, because the requirements README states
the opposite. An agent following the documents faithfully stops; an agent that
ignores them succeeds.

## 4. What this says about the workflow as a whole

The lifecycle model is sound. The stage sequence, the artifact-not-flags rule,
the minted-evidence rule, and the red-then-green transition are all doing real
work, and the run showed each of them catching something an agent would otherwise
have been able to assert its way past.

The weakness is at the **boundaries**: between the wizard and the CLI (seam 1),
between policy and reporting (seam 2), between the tool and its own output
(seam 3), and between the adoption route and the requirement register (seam 4).
None of the four needs a redesign. Each is a small correction at a place where
two components hold different assumptions.

The one judgement call worth putting to the owner is `W9`. Shipping every
guardrail off is defensible as "do not block a new adopter" — but combined with
seam 2, an adopted repository reports a clean bill of health while enforcing
nothing, and nothing in the handoff says so. At minimum the adoption handoff
should state which policies are inactive; the alternative, turning some on by
default, would violate constraint 3 and is not proposed here.
