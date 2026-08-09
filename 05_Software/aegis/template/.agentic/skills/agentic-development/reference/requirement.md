<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Requirement

**Purpose:** Turn each agreed acceptance criterion into one durable requirement
snapshot in the repository register, so the contract outlives this run and a
later change can be traced back to what it was supposed to preserve.

**Resume rule:** Run `<workflow> stage prepare` only when `<workflow> run status`
reports it as `next`. Otherwise do not prepare a new revision; resume at the
reported command using the retained current form and this reference.

**Read first:**

- `<workflow> run status`, then the `requirement-001.toml` form and the
  `stage.toml` control form that `stage prepare` generates.
- The alignment form's `acceptance_criteria`.
- `<workflow> requirement list` — search before you write. A behaviour that
  already has a requirement gets that requirement revised, keeping its ID, not a
  second one.

**Steps:**

1. If `run status` reports `stage prepare`, run `<workflow> stage prepare`. It
   generates the first requirement form with an ID already minted and a
   companion spec scaffold at `spec_ref`. Otherwise keep the current revision
   and resume at the reported `next` command. Never invent an ID.
2. For each additional requirement, run
   `<workflow> stage add --category <category>`. Categories are `functional`,
   `ux`, `non_functional`, `security`, `data_privacy`, `platform`, `release`,
   `testing`.
3. Each requirement states one independently observable contract: write one
   behaviour per requirement. If the sentence needs "and", "or", a list, or a
   semicolon to join *distinct* behaviours, split it. A shared input or component
   is not a reason to merge: each thing that can pass or fail on its own is its
   own requirement, so one failing test names exactly one broken contract.
4. Write `requirement` as a single testable sentence. EARS shapes ("When X, the
   system shall Y") are recommended because they force a trigger and a response,
   but do not contort prose to fit a pattern — a clear sentence beats a
   grammatical one.
5. Write `rationale`: why the contract exists. This is what tells a future reader
   whether the requirement may be changed or must be preserved.
6. Set `verification` to `Automated test`, or to `Manual: <method>` /
   `Inspection: <method>` when no code path can assert it.
7. Fill `affected_paths` with the source files the behaviour lives in, and
   `linked_tests` with exact selectors under a configured test root
   (`tests/test_feature.py::test_behaviour`). The tests
   need not exist yet — the check stage writes them — but the selectors must be
   the ones you will actually create.
8. Fill the companion Markdown at `spec_ref` with the concrete detail the
   sentence cannot carry: data shapes, message text, worked acceptance examples,
   and the variants that promise parity. `feature` and `change` work should have
   one; a small `fix` may leave `spec_ref` empty when the sentence is already
   complete.
9. Consider every category the change touches, not just the functional happy
   path. A category with no applicable behaviour needs no requirement; silently
   skipping one that applies is the usual source of later regressions.
10. Write `control.summary` in `stage.toml`, run `<workflow> stage apply` to
    import the whole collection atomically, review the imported state, then
    request human approval for `<workflow> stage close`.

**Outputs:**

- One TOML snapshot per requirement in `.agentic/requirements/<category>/`.
- A companion spec per requirement that has one.
- Requirements enter as `Planned`; successful validation closure activates them.

**Done when:**

- [ ] [machine] Every accepted behaviour has one independently observable requirement.
- [ ] [machine] The requirement collection imports atomically.
- [ ] [human] The human approves stage close.

**Skip when:** The quick path bypasses this stage by profile, recording it as
`bypassed`. Never report a bypass as passed or waived. If the work turns out to
need a durable contract, that is the signal to restart as a full run.

---

## If you are stuck

**The behaviour already has a requirement.** Revise it in place and keep its ID.
An ID identifies a contract, not a run; `status` and `created_on` survive
revision and a route back.

**You cannot write a testable sentence.** That usually means alignment agreed
something vaguer than it looked. Route back: set `control.route_to = "alignment"`
and `control.route_rationale`, then apply and close.

**The requirement is for behaviour you are deliberately removing.** Retire the
existing requirement rather than deleting it, and say why in its prose. A deleted
requirement leaves no trace that the contract ever existed.
