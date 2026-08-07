<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Check

**Purpose:** Write the tests that prove each requirement, and observe them fail
for the right reason before any production code exists — so that when they pass
later, the passing means something.

**Resume rule:** Run `<workflow> stage prepare` only when `<workflow> run status`
reports it as `next`. Otherwise do not prepare a new revision; resume at the
reported command using the retained current form and this reference.

**Read first:**

- `<workflow> run status`, then the `check-001.toml` form and `stage.toml` that
  `stage prepare` generates.
- Every requirement this run owns, and their companion specs.
- The existing tests for the files the design's implementation sequence names.

**Steps:**

1. If `run status` reports `stage prepare`, run `<workflow> stage prepare`. It
   generates the first check form with an ID already minted. Otherwise keep the
   current revision and resume at the reported `next` command. Never invent an
   ID.
2. For each additional check, run `<workflow> stage add`. One check per
   behaviour, following the design's implementation sequence.
3. For each check, set `cites_requirement` to the exact requirement IDs it
   proves and `cites_spec` to the companion spec path. A check that cites nothing
   fails INV-2 at delivery.
4. Set `command` to the exact command that runs this check, and `path` to the
   test file it lives in.
5. Write the tests. Cover the applicable success, rejection, error, boundary,
   stale-state cleanup, rollback, concurrency, and idempotency behaviour — not
   only the happy path the requirement sentence describes.
6. Record in `concerns` the places this change could silently regress. If the
   design named a judgement call, it belongs here with its own case rather than
   left to review.
7. Identify variants — production/mock/sandbox, feature flag, role, platform,
   persistence adapter — and add parity checks in `parity_targets` where variants
   promise the same contract.
8. Run each check's command and **watch it fail**. Confirm the failure is the one
   you expect — missing behaviour — and not a typo, an import error, or a bad
   fixture. A red that fails for the wrong reason proves nothing.
9. Record the red evidence:
   - external mode: `<workflow> check prepare`, run the commands, fill `result`,
     `exit_status`, `summary`, and `output_log` in the generated `evidence.toml`,
     then `<workflow> check record`;
   - managed mode: `<workflow> check run [<check-id>...]`.
   AEGIS mints the evidence ID. Copy what it prints; never invent or reuse one.
10. Write `control.summary` in `stage.toml`, run `<workflow> stage apply` to
    import the collection atomically, then `<workflow> stage close`, and stop for
    human approval.

**Outputs:**

- New or extended test files, and nothing under the source roots.
- One check record per behaviour, citing its requirements and spec.
- Active red evidence for every check.

**Done when:**

- [ ] every requirement this run owns is cited by at least one check
- [ ] every check names an exact `command` and `path`
- [ ] every check was run and observed red, for the intended reason
- [ ] red evidence is recorded and active for every check
- [ ] no production source file was changed during this stage
- [ ] `<workflow> stage close` was accepted — it refuses without active red
      evidence, which is the stage's real gate
- [ ] the human approved `stage close` (human)

**Skip when:** The quick path bypasses the check *collection* stage by profile,
recording it as `bypassed`. Under the current quick-run contract, INV-3 is
`not-applicable` because no check is collected; implementation instead records
durable manual evidence through `<workflow> evidence prepare add`. Never invent
check IDs or report the bypassed check stage as passed or waived.

---

## If you are stuck

**`stage close` refuses with "has no active red evidence".** That is the gate
working. Run the check's command, watch it fail, and record the result at step 9.
Do not weaken the test to make it fail, and do not record a red you did not
observe.

**The test cannot fail because the module does not exist yet.** An import or
collection failure is a weak red — it proves absence, not that your assertions
discriminate a wrong implementation from a right one. Say so in `concerns`, and
treat the first green as the moment those assertions are genuinely exercised.

**The requirement turns out to be untestable.** Route back to `requirement`
rather than writing a test that asserts something else: set `control.route_to`
and `control.route_rationale`, then apply and close.
