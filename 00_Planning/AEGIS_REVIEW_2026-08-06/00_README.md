# AEGIS V2 Lifecycle Field Test — 2026-08-06

An end-to-end test of the **logical workflow**, run against a real repository
rather than by reading source: `waegis adopt` into a virgin repo, the seven-stage
AEGIS adoption route, `waegis configure` to switch enforcement on, and a full
eight-stage `change` run that ships a real code change.

Branch `AEGIS_V2`, WAEGIS 1.2.0, bundled payload 2.1.0, schema_version 3.
Companion to [AEGIS_REVIEW_2026-08-04](../AEGIS_REVIEW_2026-08-04/00_README.md),
which covered the same payload by source analysis plus a partial field test.

## What was actually run

Target: `F:\2026_VoiceWeaver` — a real Python voice-runtime repository, 22 source
modules, 7009 lines, 8 test modules. Nothing was pushed and no remote was
touched.

The repository was first **stripped back to a virgin state**: AEGIS 1.4.1 and
every host adapter were deleted and committed away, leaving real application
code with no governance installed. That is the true starting condition for
`waegis adopt`, and it is the condition the 08-04 field test did not cover (it
copied a payload over an existing 1.4.1 install by hand).

| Phase | Command surface | Outcome |
|---|---|---|
| Deploy | `waegis analyze` / `adopt` / `configure` / `doctor` | Completed, after three forced stops |
| Adoption | `aegis run start adoption` → 7 stages | Completed, `complete: True` |
| Change | `aegis run start change` → 8 stages | Completed, `complete: True` |

The change delivered is real and green: `parse_model_parameters_object` now names
the decoded JSON type when a model-parameters payload is valid JSON but not an
object, plus a new 13-test module for the previously untested
`domain/parsing.py`. Full suite 108 passed.

Four commits on the scratch branch `aegis-v2-flowtest`:

```text
624c692 feat(domain): name the decoded JSON type when model parameters are not an object
bc7a2ac chore(aegis): enable coverage, baseline, scope, secrets, and write-access enforcement
cdcbda5 chore(aegis): record the VoiceWeaver adoption run, component map, and baseline
91a96ce Adopt AEGIS via WAEGIS 1.2.0
```

## Constraints this review was written under

Carried forward unchanged from the 08-04 review:

1. **Only two things justify a change**: a real software bug, or a workflow
   problem that obstructs the developer/agent.
2. **No over-engineering for hardening.** AEGIS is a developer plus an LLM on
   their own git repo, not a security boundary against a hostile user.
3. **The workflow must assist the agent, not block him.** Every gate needs an
   escape hatch; every dead end needs a documented way out.
4. **No large changes.** Nothing proposed here needs a cross-module refactor.

Anything failing those tests is in the *observations* section of
[02_FINDINGS.md](02_FINDINGS.md) rather than dropped.

## Documents

| File | Contents |
|---|---|
| [01_LIFECYCLE_ANALYSIS.md](01_LIFECYCLE_ANALYSIS.md) | The logical workflow, stage by stage: what the model gets right, and the four structural seams where it leaks |
| [02_FINDINGS.md](02_FINDINGS.md) | 21 findings (`W*` deployment, `A*` governance) with reproduction and a fix for each, plus verified-working behavior and observations |
| [03_FIX_STATUS.md](03_FIX_STATUS.md) | **All 23 findings implemented and verified** (2 more were found while fixing). Per-finding disposition, the two diagnoses that turned out to be wrong, and what was deliberately not done |

> **Status: fixed, uncommitted.** AEGIS `556 → 565 passed`, WAEGIS
> `678 → 698 passed`, 29 new regression tests, no pre-existing test broken and
> no new lint. Read `03_FIX_STATUS.md` before `02_FINDINGS.md` — it corrects
> several details of the analysis below.

Every finding below was **reproduced by execution** during this run. No finding
here rests on source reading alone; where source is cited it is to explain a
failure that was already observed.

## The five that matter most

**1. A default WAEGIS adoption enforces nothing.** Every guardrail in the
generated `workflow.toml` comes out `disabled` or `unrestricted` —
`baseline_guard`, `coverage`, `protected_scope`, `secrets`, `protected_paths`,
`working_tree`, `write_access`, `scope`, `delivery`. Only `alignment` is on.
Gates are enabled only if the analyzer found commands, and finding 2 explains why
it usually will not. A repository can complete adoption, report success, and
enforce nothing. (`W9`)

**2. The repository analyzer only understands top-level layouts.** Test roots,
source roots, and gate commands are all detected at the repository root only.
VoiceWeaver keeps its project at `04_Software/VoiceWeaver/`, so the analyzer
proposed no test roots and no gates at all — and that is the layout AEGIS's own
documentation promotes and every repository in this estate uses. The single
missing proposal (`test_roots`) is also the one field that blocks
`--non-interactive` adoption outright. (`W1`, `W2`, `W3`)

**3. INV-7 fails on AEGIS's own output, and waiving it invalidates the waiver.**
`aegis verify run` writes `validation-summary.json`, which contains the
invariant's own name (`"Clean secrets"`) and its own passing message
(`"No configured secret pattern found..."`). With the obvious pattern
`(?i)secret`, INV-7 matches that file, plus `report.md` and `graph.json`.
Recording a waiver then writes the waiver's reason and blocker id into
`graph.json` — which INV-7 also scans — changing the blocker digest and making
the waiver that was just created stale. Delivery close is blocked; issuing the
**identical** waiver a second time lets it through. (`A1`, `A2`)

**4. `non-waivable` is advertised but not enforced.** INV-7 reports
`"policy": "non-waivable"`, yet it appears in `waive list` under
`eligible_blockers` and `waive add INV-7` is accepted. Afterwards the same
invariant reports `"policy": "blocking"`. The one invariant that should be
absolute — secrets — is waivable with one command. (`A3`)

**5. The adoption route cannot create requirements.** The `component-adoption`
form has a `requirement_links` field, its reference tells the agent to fill it,
and `SKILL.md` says adoption may update requirements — but `stage add` is
rejected in every adoption stage, and the requirement commands are read-only.
A repository that completes the entire adoption route ends with an **empty
requirement register**. The only way through is to hand-author requirement TOMLs
and hand-mint UUIDs, which contradicts the requirements README ("Create or revise
requirements only through requirement-stage forms") — and which does work and
does pass traceability. (`A6`)

## What is working well

This is not a failing system. The core loop is sound, and several things the
08-04 review flagged are fixed:

- **Test-first enforcement is real and correct in both directions.** The check
  stage will not close without recorded *red* evidence; the implementation stage
  will not close without *green* evidence for the same check. This caught the
  intended workflow honestly and was the most convincing part of the run.
- **Requirement activation at validation closure works.** A new requirement is
  `Planned` during the run, so INV-8 and `verify coverage` both fail mid-run,
  then both clear the moment validation closes. No deadlock, contrary to what the
  mid-run output suggests.
- **Gate evidence supersession works** (`B11` on 08-04): `supersede_reason` was
  observed on re-run.
- **`waive add --approver` exists** (open finding on 08-04) and defaults to the
  git identity.
- **`waegis doctor` is the most trustworthy command in the system.** It reported
  the two accepted-failing gates long after the fact, with log paths and blunt
  guidance ("accept that this repository's verification status is unproven").
- **`waegis configure` renders an exact field-level before/after diff** and
  refuses invalid policy combinations.
- Stage forms pre-populate from `workflow.toml`, so `repo-discovery` arrives with
  roots and gate commands already filled in.

The gap is not in the lifecycle model. It is that **the deployment wizard hands
over a repository configured to enforce almost nothing, and several verification
commands report "no issues" when they are simply switched off.**
