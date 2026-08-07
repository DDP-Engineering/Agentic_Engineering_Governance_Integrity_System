<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Implementation

**Purpose:** Make the checks pass by changing production source only, so that
every green check has a recorded red result before it.

**Resume rule:** Run `<workflow> stage prepare` only when `<workflow> run status`
reports it as `next`. Otherwise do not prepare a new revision; resume at the
reported command using the retained current form and this reference.

**Read first:**

- `<workflow> run status`, then the implementation form `stage prepare`
  generates.
- The design document named by the design form's `document` field.
- The check forms under `.agentic/runs/<run-id>/stages/check/`, for the check IDs
  and their commands.
- The source files the design's implementation sequence names.

**Steps:**

1. If `run status` reports `stage prepare`, run `<workflow> stage prepare`. The
   form arrives with a change-unit ID already minted. Otherwise keep the current
   revision and resume at the reported `next` command. Never invent an ID.
2. Work one check at a time, in the design's implementation sequence. Do not open
   several at once.
3. Write the smallest change that makes that check pass. Add no behaviour no
   requirement asks for. If the design turns out to be wrong, stop and route back
   rather than designing in place.
4. Run the check's command and confirm it passes for the right reason. Never
   write "green" over a non-zero exit.
5. Record green evidence:
   - external mode: `<workflow> check prepare`, run the command, fill `result`,
     `exit_status`, `summary`, and `output_log` in the generated `evidence.toml`,
     then `<workflow> check record`;
   - managed mode: `<workflow> check run <check-id>`.
   Copy the evidence ID AEGIS prints; never invent or reuse one, and never cite
   a superseded or other-stage ID.
6. Repeat steps 3–5 until every check is green.
7. Run `<workflow> verify run` once before filling the form. A change that is
   shared, cross-cutting, or touches a file no requirement covers needs the full
   suite, not only its own checks.
8. Fill the form:
   - `changed_paths` — every file you changed, repo-relative, forward slashes,
     and nothing you did not change;
   - `linked_check_evidence` — the exact active evidence IDs from step 5;
   - `documentation_effects` — any component page under
     `.agentic/knowledge/components` this change makes wrong. Name the page and
     say what is now untrue; validation fixes it.
   - `control.summary` — what changed and why, in prose a reviewer reads six
     weeks from now.
9. Run `<workflow> stage apply`, then `<workflow> stage close`, and stop for
   human approval.

**Outputs:**

- Production source changes, and no test changes — tests belong to the check
  stage.
- One active green evidence record per check, each with a prior red one.

**Done when:**

- [ ] [machine] Changed paths and active green check evidence are recorded.
- [ ] [machine] Every green check has prior red evidence.
- [ ] [human] The human approves stage close.

**Skip when:** Never. Every run that changes behaviour passes through
implementation, including the quick path.

---

## If you are stuck

**`stage close` refuses with "has no active green evidence".** Run the check,
confirm it passes, and record it at step 5. Do not weaken the test to make it
pass — that is the failure the check/implementation split exists to prevent.

**The design or a check is wrong.** Do not edit check artifacts here. Set
`control.route_to` to the earlier stage and `control.route_rationale` to the
reason, then apply and close. Routing takes effect at close, not at apply. A
route defers the red/green blockers this stage would otherwise require and
records the deferred list on the `stage.routed` journal event. An empty
`changed_paths`, an unresolved question, or a `route_to` that does not name an
earlier stage all still refuse the close.

**A blocker you cannot clear.** Run `<workflow> waive list` for the exact blocker
ID, present it to the human, and only after explicit approval record
`<workflow> waive add <blocker-id> --reason "<reason>"`. A waiver is never a
pass: the failure stays `WAIVED` with its reason and timestamp.

**Requirement state.** Planned requirements activate only after successful
validation closure. Their `status` and `created_on` survive a route back, so
re-applying the requirement stage does not reset an Active requirement or lose
its creation date.
