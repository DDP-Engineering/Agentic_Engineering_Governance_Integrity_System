<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS - team setup

AEGIS has no server and no shared database: **the branch is the
workspace, git is the sync layer**. A team gets multi-user governance
from the workflow it already has.

## The model

- Each developer works on their own branch, on their own machine, with
  their own agent (different people can even use different models).
- Share committed core records through separately authorized Git operations.
  On the receiving machine, check out the recorded branch, run
  `python .agentic/aegis.py brief TASK-<id>`, then read the current step,
  Handoff paths and required full journal. `status` finds an unknown task ID.
  Uncommitted changes and local host/job caches do not travel with the branch.
- Parallel work rarely collides by construction: one task = one journal
  file; one requirement = one file with a random 8-hex id. Independent new IDs normally
  create disjoint files; this does not eliminate source or record conflicts. The genuine merge hotspots are the shared
  *content* files: two people editing the same requirement, two tasks
  touching the same component's knowledge page, or two people sharing one
  adoption journal (use one journal per person - the adopt step says
  how). All three are conflicts a human should see anyway.

## After a merge

Recheck affected project/environment context and component pages against the
merged implementation and established requirements. Each branch edits only the
facts it changes. Keep current positive statements in shared documents and
decisions/history in task records. Context is shared project data, so ordinary
review and merge apply. See [project context](Project_Context.md).

Run the reconciliation check on the target branch:

```bash
python .agentic/aegis.py check
```

It flags what merges can break: duplicate requirement ids, journal
references to requirements that moved, `affected_paths` that no longer
exist, specs that no longer resolve. Fix forward, commit. No ceremony.

## The one hard gate - CI, opt-in

Advisory-by-default ends at the merge boundary, if the team wants it to.
In your PR pipeline:

```bash
python .agentic/aegis.py check --strict --run
```

- `--strict` exits 1 on **errors** (broken artifacts) and on warnings
  the team explicitly promoted;
- `--run` also executes eligible `[commands]` entries (test, lint, ...) and
  turns failures into errors. Running *nothing* is an error too, so a
  misconfigured gate fails loudly instead of passing silently.

The gate proves exactly what your configuration covers, no more: it is
green because `[commands] test` really is your suite. If you add a
`[check] run` allowlist that omits `test`, the suite stops running and
the skip is printed - the gate will not invent a guarantee for you.

Promote the warnings your team considers non-negotiable in
`.agentic/aegis.toml`:

```toml
[check]
strict_promote = [
  "no-linked-tests",            # active requirement without tests
  "source-no-test-changes",     # code changed, no test changed
  "secret-in-diff",             # possible secret in the diff
]
```

Start with an empty list, watch the warnings for a couple of weeks, then
promote the ones nobody ever wants to override.

Only **warnings** can be promoted. `manual-verification` is a NOTE, so
listing it here does nothing: the manual-verification
note itself cannot fail the gate. Other errors in that requirement can still
fail it. That is the point -
it lets a team promote `no-linked-tests` hard without the unautomatable
requirements (UX judgements, clean-install checks) making the gate
unpassable. What it costs you is that the honesty of a `Manual:` claim is
a review question, not a CI one; the NOTE stays in every report so the
claims remain countable and visible.

One thing to know if you promote `secret-in-diff`: when part of a diff
cannot be inspected - a binary or oversized file, or a filename git
could not attribute - `check` reports it as a `secret-in-diff` warning
saying *"added lines not scanned"* rather than staying silent. So a
promoted secret scan fails the gate on an unscanned file too. That is
deliberate: a partial scan must never read as a clean one. Review that warning-promotion list alongside command selection, timeout
settings and the independent review policy; all are visible in configuration.

Any CI system works - the command is plain Python with exit codes. A
minimal Gitea/GitHub-style step:

```yaml
- name: AEGIS gate
  run: python .agentic/aegis.py check --strict --run
```

## Conventions worth agreeing on (all social, none enforced)

- **Journals are per-task, not per-person** - if you hand a task over,
  the journal goes with it; the Log shows durable stage progress and evidence,
  not every action performed by each participant.
- **Don't renumber, don't reuse ids** - retire requirements
  (`status = "retired"`) instead of deleting them; history stays
  readable.
- **The frame checkpoint is where scope arguments belong** - cheaper
  than review-time arguments. The journal retains the accepted scope and any
  material unresolved issue, not the full discussion transcript.
- **`DEVIATION` lines arrive mid-run and are not a question** - the agent
  states one and carries on; nobody is being asked to decide. Read them
  as they land, raise what bothers you, and expect all of them again at
  the delivery stop.
- **Upgrades are one person's PR**: copy the new payload over, everyone
  reviews the diff like any other change.
- **Child visibility is local**: the parent lists only child journals in its
  checkout. Push or merge a child only with explicit Git authority, then
  validate the combined candidate in the parent.
- **Commit journals with approved work**: code without its child journal,
  Rulings, and refreshed Handoff is not a transferable governed task.
- **Sidecars stay local**: `[records] commit_fingerprints` is `false`, so
  `init` keeps a managed `.gitignore` block that excludes
  `TASK-<id>.anchor.json` and `.evolution.json`. They never reach a
  teammate's checkout, and the journal's recorded evolution line is the
  shared evidence. Set it to `true` and rerun `init` if your team wants the
  sidecars in review; `check` reports a repository that disagrees.
- **Resume from durable state**: run `brief TASK-<id>`, read the current step
  and Handoff `must_read` paths, then inspect the full journal where required.
  A Handoff coordinates work; it never authorizes a push, merge, or release.

## Independent review and final proof

```toml
[review]
enabled = true
max_fix_cycles = 2
```

Each round requires two independent verdicts for the same candidate:
specification compliance and implementation quality. After a candidate fix,
clear both verdicts while retaining the consumed round and historical findings,
rerun focused proof and obtain both reviews again. Reviewers read current linked
files even when untracked and judge evidence due at their phase. A pending final
strict check is not itself a review failure; that check follows approvals. One
initial round plus two fix cycles is the default bound when review is enabled.
An unresolved final round requires a human decision; it grants no Git authority.
Review is disabled by default, while ordinary semantic review remains required.

The parent validates the combined candidate after child branches become visible.
Passing child tests are not proof of the integrated result. The final
`check --strict --run` executes the configured proof; do not duplicate a long
suite already owned by an integration job. Schedule full verification after
final edits and review, with focused native checks during build. Ensure that the
project runner honors any impacted references; `--no-fallback` prevents CLI
fallback, not a runner that ignores selection.

Agree on documented readiness checks for each checkout. Handoff and Stage report
still refresh at stage boundaries, pauses, blockers and session ends, but they
should not repeat the full journal. Reuse unchanged instructions in an intact
session; a new session or compaction requires durable re-entry. Neither an older
successful run nor an unchanged fingerprint on a cancelled job proves the final
candidate. These guidelines add no cross-machine test-result cache.

## Each user installs their own host package

Distribute complete built OpenCode, Codex, Pi, Qwen or Claude packages, then let
each developer run the installer and `doctor` on their own Windows/Linux
environment. Each keeps their own sign-in, provider, model and permissions.
Do not distribute an installed profile, authentication or `runtime.json` from
another person's machine. See [Agent_Plugins.md](Agent_Plugins.md).

Use a common local AEGIS cache across hosts on one machine for duplicate-job
detection. It is not a distributed team lock, and externally launched suites
are outside it. After interruption, inspect the reserved job and processes
before retrying. An uncertain job is not permission to start another suite.

Documentation-only maintenance in this repository is performed directly,
without an AEGIS task journal or development verification run.
