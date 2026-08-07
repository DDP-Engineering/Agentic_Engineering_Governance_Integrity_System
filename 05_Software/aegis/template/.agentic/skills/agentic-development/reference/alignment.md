<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Alignment

**Purpose:** Agree what "done" means before any contract is written, by
separating what the code does today from what the human wants it to do, and
recording the acceptance criteria both sides will be held to.

**Read first:**

- `<workflow> run status`, then the alignment form `stage prepare` generates.
- The intake form under `.agentic/runs/<run-id>/stages/intake/`.
- The source files `scope_hints` named — enough to describe current behaviour
  accurately, not to design a fix.

**Steps:**

1. Run `<workflow> stage prepare` and open the form.
2. Write `understanding`: what the code does **today**, in observable terms, and
   why that is a problem. Keep discovered current behaviour and desired future
   behaviour in separate sentences. Mixing them is the most common way a run
   ends up implementing something nobody agreed to.
3. Fill `in_scope` and `out_of_scope`. `out_of_scope` earns its keep — naming
   what you will deliberately not touch is the cheapest scope control available,
   and it is what a reviewer checks the diff against.
4. Write `assumptions`: anything you are taking as true without proving it. If an
   assumption turns out false later, this list is what tells you the run needs
   to route back rather than push on.
5. Write `acceptance_criteria`: distinct, observable, independently checkable
   statements. One behaviour per entry. "Works correctly" is not a criterion;
   "a payload that decodes to an array is rejected with a message naming the
   array type" is.
6. Record open `questions` with your `recommended_answers` beside them, so the
   human can approve a recommendation instead of composing an answer.
7. Set `planned_paths` to the files you now expect to change, refined from the
   intake hints.
8. Set `risk` to `low`, `medium`, or `high`, and `decision` to `proceed` or
   `pause`. Use `proceed` only when no configured pause rule applies — a high
   risk with open questions is a `pause`, and saying so is not a failure.
9. Write `control.summary`, run `<workflow> stage apply`, then
   `<workflow> stage close`, and stop for human approval.

**Outputs:**

- The applied alignment form: agreed scope, assumptions, acceptance criteria,
  risk, and an explicit proceed/pause decision.

**Done when:**

- [ ] `understanding` states current behaviour and desired behaviour separately
- [ ] `out_of_scope` is non-empty, or the work genuinely has no adjacent area
- [ ] every entry in `acceptance_criteria` is independently checkable
- [ ] every open question has a recommended answer beside it
- [ ] `risk` and `decision` are set, and `decision` respects the configured
      pause rules
- [ ] no solution design appears anywhere in the form (human)
- [ ] the human approved `stage close` (human)

**Skip when:** The `[alignment] enabled = false` policy switches this stage off
for the whole repository, and the quick path bypasses it by profile. Both record
it as `bypassed`, which is its own audit state — never report a bypass as passed
or waived.

---

## If you are stuck

**You want to write how it will be fixed.** That belongs in `design`, not here.
Alignment records what "done" looks like from outside; design records how the
code gets there. Putting design in alignment means the human approves a solution
before they have approved the problem.

**Current behaviour is unclear.** Read more source and say what you found. If it
is still unclear, that is an entry in `questions` with your best recommendation —
not an assumption smuggled into `understanding`.

**A pause rule blocks `proceed`.** Set `decision = "pause"` and stop. The human
either answers the questions or approves proceeding; both are their call.
