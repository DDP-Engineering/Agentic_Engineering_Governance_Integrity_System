<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Design

**Purpose:** Decide how the code will satisfy the requirements, and record the
alternatives you rejected, so implementation is transcription rather than
invention and a reviewer can check the reasoning instead of re-deriving it.

**Resume rule:** Run `<workflow> stage prepare` only when `<workflow> run status`
reports it as `next`. Otherwise do not prepare a new revision; resume at the
reported command using the retained current form and this reference.

**Read first:**

- `<workflow> run status`, then the `design.md` document and the `design.toml`
  form that `stage prepare` generates.
- Every requirement this run owns, and their companion specs.
- The existing source the change will touch, and the component pages under
  `.agentic/knowledge/components` that describe it.

**Steps:**

1. If `run status` reports `stage prepare`, run `<workflow> stage prepare`. It
   writes a `design.md` skeleton with the sections to fill and a `design.toml`
   form that cites it. Otherwise keep the current revision and resume at the
   reported `next` command.
2. Fill `design.md` section by section. The sections that carry the weight are:
   - **Relevant Existing Architecture** — what is there now, so the change is
     placed rather than bolted on.
   - **Alternatives and Trade-offs** — at least two real options with their
     costs. One option is not a design, it is a preference.
   - **Selected Design and Rationale** — the choice, and why the rejected ones
     lost.
   - **Implementation Sequence** — the order the check and implementation stages
     will follow.
   - **Validation Approach** — how you will know it worked.
3. Name the specific judgement calls. If a decision could reasonably have gone
   the other way, say which way and why, and prefer covering it with its own
   check rather than leaving it to review.
4. In `design.toml`, set `cited_requirement_ids` to the exact requirement IDs
   this design implements, and `selected_option` to a one-line statement of the
   choice.
5. Write `control.summary`, run `<workflow> stage apply`, then
   `<workflow> stage close`, and stop for human approval.

**Outputs:**

- `design.md`, the approved design document for this run.
- The applied design form, citing the requirement IDs it implements.

**Done when:**

- [ ] [machine] The design cites its requirements, alternatives, and selected option.
- [ ] [machine] The imported design form has a digest.
- [ ] [human] The human approves stage close.

**Skip when:** The quick path bypasses this stage by profile, recording it as
`bypassed`. A full run never skips design. For a small change with one obvious
implementation, keep the required design brief: cite every requirement, record
the obvious option and why alternatives add no value, and select that option.

---

## If you are stuck

**Designing reveals the requirement is wrong.** Route back rather than designing
around it: set `control.route_to = "requirement"` and `control.route_rationale`,
then apply and close. Routing takes effect at close, not at apply. Requirement
`status` and `created_on` survive the round trip.

**The design keeps growing.** That is scope feedback. Take it to the human before
implementation, not after — a design that has outgrown its alignment is cheaper
to stop here than to unwind from a diff.

**INV-10 fails later.** The approved design and its cited requirement snapshots
are digest-pinned at approval. If either changes afterwards the invariant fires;
re-approve the design rather than editing it quietly.
