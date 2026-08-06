# AEGIS V2 Review — Field Test Report

Date: 2026-08-04
Test repository: `F:\2026_VoiceWeaver` (had AEGIS 1.4.1 installed, 110 requirements)
Branch: `aegis-v2-test` — 2 local commits, working tree clean, **nothing pushed, no remote touched**
Notes left in repo: `F:\2026_VoiceWeaver\AEGIS_V2_TEST_NOTES.md`

This document records what actually happened when the V2 payload was installed
into a real repository and driven through a real change — as opposed to the
source analysis in `01_BUGS.md` and `02_WORKFLOW.md`. Findings already covered
elsewhere are cross-referenced rather than repeated.

**The single most valuable result: the field test independently reproduced
[B11](01_BUGS.md) (gate evidence never superseded) by execution.** Three gate
evidence records — `E-0004` fail, `E-0007` fail, `E-0010` **pass** with 104 tests
green — and the gate still reported `failed` with `INV-4 holds: false`.

---

## What was exercised

Upgrade 1.4.1 → 2.1.0, then a real one-function change to
`domain/parsing.py` (`parse_model_parameters_object` now names the decoded JSON
type in its rejection message) plus a new 9-test file, driven end to end through
the `--quick fix` profile to `complete: True`.

**Not exercised** — the quick profile bypasses four stages, so the alignment,
requirement, design, and check stages were not driven; nor were
`check prepare/record/run`, managed check execution, adoption runs, RepoWise, or
the hooks. Given B10 and B18 below, a full-profile pass should come next.

---

## New findings

### B17 — Failing gate commands record no output at all

**Severity: critical** · **Verification: EXECUTED** · File: `gates.py`

`grep output_log gates.py` returns nothing. `Evidence` carries an `output_log`
field and both `check_execution.py` and `evidence_forms.py` populate it — gates
do not. A failed gate yields `exit_status: 1` and nothing else.

In the field test this meant reproducing each failure by hand to discover the
actual causes: `uv trampoline failed to canonicalize script path`, then
`ModuleNotFoundError: No module named 'numpy'`. Neither appeared anywhere in the
evidence record.

The gate's stdout/stderr *is* written to the journal as a `gate.output` event
(`gates.py:141-152`, tails capped at 4000 chars), but the journal has **no CLI
read surface** (see D7 in `02_WORKFLOW.md`), so an agent cannot reach it.

For an autonomous agent — especially a small local model — this is fatal to
recovery: it knows a gate failed and has no way to learn why.

**Fix:** populate `output_log` on the gate `Evidence` record the way
`check_execution.py:339` does — write the captured output to a file under the run
directory and store the repo-relative path. The capture already exists; only the
persistence is missing.

---

### B18 — A one-field edit to `graph.json` completes a run with zero work

**Severity: critical** · **Verification: EXECUTED**

On run `change-2026-08-04T052118Z-af3ee0b4`, editing a single field —
`"stage": "intake"` → `"stage": "delivery"` — was accepted silently. `stage prepare`
handed over a delivery form; `stage apply` + `stage close` returned
`complete: True` on a run with **zero stages done, zero evidence, and no
verification ever run**.

Two distinct defects combine here:

1. **`CLI_API_REFERENCE.md` claims this is caught** — "Hand-edited kind/profile/stage
   mismatches return a typed stage-operation block". It does not. Either the
   check is missing or the doc is wrong.
2. **Delivery `stage close` re-checks no blocking invariant.** Confirmed at
   `stage_forms.py:974-976`, the entire delivery blocker set is:

   ```python
   if graph.stage in {"delivery", "adoption-delivery"}:
       if record.payload.get("decision") != "approved":
           blockers.append("final human handoff decision is not approved")
   ```

The generated report was at least honest — `INV-6 FAIL (blocking): No evidence
recorded yet`, `Deterministic Verification: Not yet run` — which is what exposed
the hole.

**Note on scope:** per the owner's philosophy this is *not* a request for
tamper-proofing against a hostile user. A developer who hand-edits `graph.json`
is entitled to do so. The bug is that **delivery closes a run while its own
report says blocking invariants failed** — that is an internal inconsistency, not
a security gap.

**Fix (small, and the right one):** make delivery `stage close` refuse while a
blocking invariant fails un-waived. That closes the inconsistency without adding
any integrity machinery, and it is already how every other stage behaves. Drop
the `CLI_API_REFERENCE` claim about typed blocks on hand-edited graphs, or make
it true.

---

### B19 — The approver is a hardcoded literal; the audit trail cannot attribute anything

**Severity: high** · **Verification: EXECUTED** · Files: `models.py:204,220,445`, `stage_forms.py:872,879,903`

Every journal event and every waiver records `approver = "human"`. It is not a
default that can be overridden — `models.py:220` types it as
`approver: Literal["human"] = "human"`, and `models.py:436` rejects anything else
on load. No `--approver` flag exists on `stage close` or `waive add`.

For a system whose name is *Governance & Integrity*, approvals that cannot be
attributed to a person are a real gap — and on a team, the waiver record becomes
unusable as evidence of who accepted the risk.

**Fix:** add `--approver` to `stage close` and `waive add`, defaulting to git
`user.name <user.email>`. Widen the `Literal["human"]` to `str` and update
`_waiver_from_dict`. Keep `"human"` as the fallback so existing graphs load
unchanged.

---

### B20 — A stale run pointer blocks read-only commands

**Severity: medium** · **Verification: EXECUTED**

The legacy schema-2 run left by 1.4.1 wedged every read command, including
`aegis requirement list` — a pure read of the durable requirement store that has
nothing to do with runs:

```
error: RUN-POINTER-STALE: This worktree selects adoption-2026-07-25T164318Z-eae9af40,
but .agentic/runs/adoption-.../graph.json is missing or invalid.
Start a new run or pass `--run <existing-run-id>` explicitly.
```

Three problems in one message: the file **exists** (it is a schema-2 graph), so
"missing or invalid" misdiagnoses; `next:` points at `aegis config validate` when
config was already valid; and the suggested remediation is a dead end, since the
stale ID *is* the existing ID.

**Fix:** do not resolve a run for commands that do not need one (`requirement
list/show`, `config *`). Make the message name the actual cause
(`schema_version 2, requires 3`) and offer a working next step. This is the same
family as **W11** — see `store.py:524-535`, which should reuse
`_pointer_missing_remediation` from `store.py:423-453`.

---

### B21 — `verify status` returns `status: ok` and exit 0 while reporting a failed verification

**Severity: medium** · **Verification: EXECUTED**

An agent polling `verify status` to decide whether it may proceed gets the wrong
signal. Related to but distinct from **B16** in `01_BUGS.md`.

**Fix:** exit non-zero when the verification being reported failed, matching
`verify run`.

---

### B22 — The non-`--json` surface prints one unwrapped ~4 KB JSON line

**Severity: medium** · **Verification: EXECUTED**

`verify run` and `verify status` without `--json` emit a single unwrapped JSON
line, unreadable in a terminal. That defeats the purpose of having a
human-facing surface distinct from `--json`.

**Fix:** indent nested JSON in the non-`--json` path, or render a summary table.

---

### B23 — Template packaging defects

**Severity: low** · **Verification: EXECUTED**

- ~~`template/.agentic/cli/src/aegis.egg-info/` is shipped in the payload.~~
  **CORRECTED 2026-08-04 — this claim was wrong.** `*.egg-info/` is ignored by
  `05_Software/aegis/.gitignore:4` and is not in the git index; it is local
  build residue from an editable install, not shipped material. The residual
  concern is narrower: `install.ps1` copies `template/` from the working tree,
  so an installer run from a dirty dev checkout would propagate both
  `aegis.egg-info/` and any `__pycache__/`. **Fix belongs in the installer's copy
  exclusions, not in the template.** Note `tests/test_release_hygiene.py:161`
  already guards `__pycache__`/`.pyc` in the template and will fail loudly if
  they appear — it caught exactly this during Batch 2 verification.
- `template/.gitignore` has **no** `.venv/` or `.agentic/.venv/` entry, but
  `install.ps1` creates `.agentic/.venv`. A fresh project that follows the docs
  commits its virtualenv. (Masked in VoiceWeaver only because that repo's own
  `.gitignore` already has `.venv/`.)
- `install.ps1` dies under Windows PowerShell 5.1 when its stderr is redirected:
  `$ErrorActionPreference = "Stop"` turns `uv`'s progress-on-stderr into a
  terminating `NativeCommandError`. Works when run bare, so this bites CI and
  wrapper scripts. Fix: `$ErrorActionPreference = "Continue"` around native
  calls, or invoke them in a way that does not promote stderr.

---

## New workflow findings

### W13 — There is no upgrade procedure

**Severity: high** · **Verification: EXECUTED**

Nothing in the payload documents a 1.x → 2.x upgrade.
`How_To_Start_A_New_Project.md` §10 says only that it is "unsupported; make a
fresh AEGIS 2.x deployment after preserving project-owned artifacts
deliberately" — **without listing which artifacts are project-owned**.

The boundary had to be derived by diffing the template against the install:

| Payload-owned (replace) | Project-owned (preserve) |
|---|---|
| `.agentic/{cli,tools,hooks,documents,skills,integrations}`, `.agentic/LICENSE.txt`, the five host-adapter directories, `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `opencode.json` | `.agentic/requirements/`, `components.toml`, `knowledge/`, `reports/`, `specs/`, `runs/` |

The schema-2 → 3 config migration is only two mechanical edits — add the
`[interface]` table, split `[gates]` into five `[gates.<group>]` tables — but it
was discovered **one error at a time across four `config validate` round-trips**.

Good news worth documenting: **the requirement store needs no migration.** All
110 legacy `schema_version = 1` requirement TOMLs read cleanly under V2 and
`requirement list` returned them unmodified.

**Fix:** write `documents/UPGRADING.md` with the ownership manifest above, the
two-edit config delta, and the statement that requirement snapshots carry over
untouched.

---

### W14 — Stage enum values are validated at `close`, not at `apply`, and the error never names the accepted tokens

**Severity: high** · **Verification: EXECUTED**

This is **W9** in `02_WORKFLOW.md` observed in the field, and it is worse than the
source reading suggested. Two full prepare/edit/apply cycles were lost to it:
`diff_review = "approved"` and `decision = "accept"` were **accepted silently by
`stage apply`** and only rejected at `stage close`:

```
error: diff review is not complete; documentation review is not complete; style review is not complete
error: final human handoff decision is not approved
```

Neither message names the real tokens. The accepted values (`pass` /
`not-applicable`, and `pending` / `approved`) were found only by reading
`stage_forms.py:1027` and `:975`. **They appear in zero shipped documents** —
grepped across all of `.agentic/documents`.

The inconsistency is internal: `baseline-review` *does* validate its decision at
import (`_validate_import_decision`, "must be pending or approved"). Delivery does
not.

**Fix:** validate stage enums at `stage apply` the way `_validate_import_decision`
already does, and name the accepted values in the message —
`diff_review must be "pass" or "not-applicable" (got "approved")`. This subsumes
part of W9 and is the higher-value half.

---

### W15 — Waiver friction observed in practice

**Severity: medium** · **Verification: EXECUTED**

`waive list` is genuinely good — it enumerates eligible blockers with
descriptions and state digests, and `waive add` worked as documented. Two
problems surfaced only under real use:

1. **One failing gate produces two independently waivable blockers** — `gate:test`
   and `INV-4` — each needing its own reason and its own human approval, for one
   underlying failure.
2. **Waivers are digest-pinned and silently invalidated by re-verification.**
   After waiving `gate:test`, fixing the gate command and re-running `verify run`
   moved the waiver to `status: "stale"` — correctly visible in `waive list`, but
   the validation summary reported `"waivers": null` and the gate simply as
   `failed`, with no trace that a waiver had existed and been invalidated.

Combined with **B11**, this produces a perverse operating rule: **waive only
after your final verify, and never verify again.**

**Fix:** collapse `gate:<name>` and its mirror invariant into one waivable
blocker; surface stale and invalidated waivers in the validation summary instead
of `"waivers": null`.

---

### W16 — `run start` silently abandons an in-flight run

**Severity: medium** · **Verification: EXECUTED**

Reinforces **W2** in `02_WORKFLOW.md`. `run start` repoints the worktree at a new
run with no warning that an incomplete run is being left behind. Nothing wedges —
`run select <id>` recovers full state — but only if you still have the run ID,
and nothing enumerates them.

**Fix:** as W2 (`run list` + `run abandon`), plus a warning on `run start` when
the current run is incomplete.

---

## What worked well in the field

- **Config error messages are the best in the product** — typed code,
  `config_path`, `key_path`, `received`, `expected`, `remediation`. They are the
  model the stage layer should copy (W11). Two complaints only: they surface
  serially rather than batched, and the `gates.mode` remediation names the group
  list instead of the new `[gates.<group>]` table shape.
- **The requirement store carried over with zero migration** — 110 files, no edits.
- **Stage-form tamper resistance is correct.** With
  `stage_form_retention = "discard"` the form is deleted at apply, and
  `stage prepare` invalidates the applied state so `stage close` demands a fresh
  apply. Out-of-band edits to stage forms cannot slip through.
- **`waive list`** as a discovery surface.
- **`install.ps1`** ran clean when invoked bare (`aegis==2.1.0`).

---

## Additions to the implementation order

Fold into the phases in [00_README.md](00_README.md):

- **Phase 1** gains **B17** (gate output capture) — without it an agent cannot
  recover from any gate failure autonomously, which compounds B11.
- **Phase 2** gains **B18** (delivery close must re-check blocking invariants) and
  **W13** (write the upgrade document — it is pure prose and unblocks every
  existing 1.x repository).
- **Phase 3** gains **B19** (`--approver`) and **W14** (validate enums at apply,
  name the tokens).
- **Phase 4** gains **B20**, **B21**, **B22**, **W15**, **W16**.
- **Phase 5** gains **B23** (packaging: drop `egg-info`, add `.venv/` to
  `.gitignore`, fix `install.ps1` stderr handling).
