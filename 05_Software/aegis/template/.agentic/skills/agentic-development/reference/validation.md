<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Validation

**Purpose:** Prove the whole repository is still good — not only the part you
changed — by running the deterministic verification first and only then reading
the diff with your own judgement.

**Resume rule:** Run `<workflow> stage prepare` only when `<workflow> run status`
reports it as `next`. Otherwise do not prepare a new revision; resume at the
reported command using the retained current form and this reference.

**Read first:**

- `<workflow> run status`, then the validation form `stage prepare` generates.
- The implementation form's `changed_paths` and `documentation_effects`.
- Nothing else yet. The verification output below is what you read next, and
  reading the diff before it biases the review.

**Steps:**

1. If `run status` reports `stage prepare`, run `<workflow> stage prepare` and
   open the form. Otherwise keep the current revision and resume at the reported
   `next` command.
2. Run `<workflow> verify run`. This performs impact selection, the enabled
   build, typecheck, lint, test, and security gates, the invariants,
   traceability, coverage, and working-tree review, in that deterministic order,
   and writes a validation summary.
3. Read the summary before anything else. Deterministic verification always
   comes first — its job is to tell you where to look.
4. Fix what it found, or record why each remaining finding is acceptable. Never
   write "green" over a non-zero exit. A gate reported as `not-enforced` is not
   a pass; it means the policy is switched off and that check told you nothing.
5. Update any component page named in `documentation_effects`. A page that now
   describes behaviour the code no longer has is a defect this stage owns.
6. Run `$documentation-audit`, or perform the same review manually when the repo
   has no audit tooling. Run `$python-codestyle-audit` when Python changed and
   the repo has applicable style rules.
7. Now read the diff, hunk by hunk. Look specifically for scope creep beyond
   `planned_paths`, weakened or deleted assertions, missing traceability, and
   secrets.
8. Fill the form:
   - `deterministic_verification` — the validation summary path and the evidence
     IDs backing this stage. At least one entry is required to close.
   - `diff_review`, `documentation_review`, `style_review` — each is `pass` or
     `not-applicable`. `pending` refuses the close. Use `not-applicable` only
     when the review genuinely does not apply, and say why in `control.summary`.
   - `manual_evidence` and `approved_supersessions` where they apply.
9. Write `control.summary` covering what was verified and what was accepted.
10. Run `<workflow> stage apply`, then `<workflow> stage close`, and stop for
    human approval.

**Outputs:**

- The validation summary at `.agentic/runs/<run-id>/validation-summary.json`.
- Updated component pages for every documentation effect.
- The applied validation form with all three reviews resolved.

**Done when:**

- [ ] [machine] Deterministic verification and all required reviews are recorded.
- [ ] [machine] All validation blockers are resolved or waived.
- [ ] [human] The human approves stage close.

**Skip when:** Never, on either path. The quick path reaches validation with
fewer stages behind it, not with less verification in front of it.

---

## What closing this stage does

Successful closure activates the run's eligible `Planned` requirements. Until
then INV-8 reports them as not Active and coverage counts their files as
uncovered — both clear at closure. Seeing those two fail mid-stage is expected
and is not a reason to change anything.

## If you are stuck

**Evidence is stale.** Run `<workflow> evidence prepare supersede`, edit the
generated form, and run `<workflow> evidence apply`. Superseding is a recorded
act with a reason, not a deletion.

**A gate fails for a reason unrelated to your change.** Record it, waive it with
`<workflow> waive add <blocker-id> --reason "<reason>"` after explicit human
approval, and say in `control.summary` that it is pre-existing. Do not fix
unrelated breakage inside this run; that is scope creep with good intentions.

**Coverage fails on legacy files you did not touch.** Those belong in
`.agentic/requirements/coverage_waivers.txt`, one path per line, and are removed
as each module gets a real requirement. Do not add a requirement you cannot
verify just to silence the audit.

**Delivery is a separate gate.** Validation closing does not push, publish,
merge, or open a pull request. Invoke the `agentic-delivery` skill for preflight,
reports, commits, and PR/push/merge.
