<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Stage: Intake

**Purpose:** Turn the human's ask into one written statement of intent and an
agreed scope, so every later stage can be checked against something the human
approved rather than against your memory of the conversation.

**Read first:**

- `<workflow> run status` — the run id, the stage, the artifact path.
- The intake form the run generated. Its comments give each field's accepted
  values.
- Nothing else yet. Do not read source, and do not start diagnosing.

**Steps:**

1. Run `<workflow> run start <feature|fix|change>` if no run exists, or
   `<workflow> run resume` to pick up an existing one. Add `--quick` only for a
   genuinely small `fix` or `change`; when the ask looks small, offer the route
   explicitly — `small scope - suggest: <workflow> run start fix --quick` — and
   let the human choose.
2. Run `<workflow> stage prepare` and open the form it names.
3. Write `statement`: what the human asked for, in your words, as the observable
   outcome they want. Not the cause, not the fix. If you cannot state it without
   guessing, that guess belongs in `control.unresolved_questions`.
4. Write `scope_hints`: the repo-relative paths you expect to touch. Being wrong
   here is fine and expected; being silent is not, because the later scope audit
   compares what you touched against what you said.
5. Set `access_mode`. `standard` reads only the configured source and test roots.
   Ask for `repo-wide` only when the work genuinely needs to read outside them,
   and then fill `control.requested_access_mode` and `control.access_rationale`
   with the reason. An empty rationale refuses the close.
6. Write `control.summary`: two or three sentences a reviewer reads six weeks
   from now to know what this run was for.
7. List anything you could not resolve in `control.unresolved_questions`. Each
   entry blocks the close until it is answered or waived — that is the point.
   Do not empty the list to make the stage close.
8. Run `<workflow> stage apply`, then `<workflow> stage close`, and stop for
   human approval.

**Outputs:**

- The applied intake form, with intent, scope hints, and access mode recorded.
- A run id every later stage and every later session attaches to.

**Done when:**

- [ ] `statement` names an observable outcome, not a cause or a fix
- [ ] `scope_hints` lists the paths you expect to touch
- [ ] `access_mode` is set, with a rationale if it is `repo-wide`
- [ ] `control.summary` is written
- [ ] every open question is either answered or recorded in
      `control.unresolved_questions`
- [ ] `<workflow> stage apply` succeeded and reported a digest
- [ ] the human approved `stage close` (human)

**Skip when:** Never. Every run starts at intake, including the quick path. A
run with no recorded intent cannot be checked against anything later, and the
delivery invariants will fail on an empty run.

---

## If you are stuck

**A question blocks the close.** That is correct behaviour. Answer it with the
human, or run `<workflow> waive list` to get the exact blocker id, present it,
and only after explicit approval record
`<workflow> waive add <blocker-id> --reason "<reason>"`. A waiver is never a
pass — the question stays recorded with its reason and timestamp.

**The ask turns out to be two tasks.** Say so and let the human split it. Do not
widen `statement` to cover both; a run whose scope grows silently is the failure
mode intake exists to prevent.

**Scope grows after a `--quick` start.** Stop, tell the human the quick profile
no longer fits, and start a full run carrying the recorded context forward.
