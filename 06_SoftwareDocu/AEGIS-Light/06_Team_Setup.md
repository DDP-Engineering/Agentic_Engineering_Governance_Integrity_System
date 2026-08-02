<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light — team setup

AEGIS Light has no server and no shared database: **the branch is the
workspace, git is the sync layer**. A team gets multi-user governance
from the workflow it already has.

## The model

- Each developer works on their own branch, on their own machine, with
  their own agent (different people can even use different models).
- Everything AEGIS Light knows is committed files, so any machine
  resumes any task with: `git fetch`, check out the task branch recorded
  in the journal, then `python .agentic/aegis.py status`. (Push the
  branch from the old machine first — uncommitted work never travels.)
- Parallel work rarely collides by construction: one task = one journal
  file; one requirement = one file with a random 8-hex id. Two branches
  create disjoint files. The genuine merge hotspots are the shared
  *content* files: two people editing the same requirement, two tasks
  touching the same component's knowledge page, or two people sharing one
  adoption journal (use one journal per person — the adopt step says
  how). All three are conflicts a human should see anyway.

## After a merge

Run the reconciliation check on the target branch:

```bash
python .agentic/aegis.py check
```

It flags what merges can break: duplicate requirement ids, journal
references to requirements that moved, `affected_paths` that no longer
exist, specs that no longer resolve. Fix forward, commit. No ceremony.

## The one hard gate — CI, opt-in

Advisory-by-default ends at the merge boundary, if the team wants it to.
In your PR pipeline:

```bash
python .agentic/aegis.py check --strict --run
```

- `--strict` exits 1 on **errors** (broken artifacts) and on warnings
  the team explicitly promoted;
- `--run` also executes every `[commands]` entry (test, lint, ...) and
  turns failures into errors. Running *nothing* is an error too, so a
  misconfigured gate fails loudly instead of passing silently.

The gate proves exactly what your configuration covers, no more: it is
green because `[commands] test` really is your suite. If you add a
`[check] run` allowlist that omits `test`, the suite stops running and
the skip is printed — the gate will not invent a guarantee for you.

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
promote the ones nobody ever wants to override. This is the whole
governance dial: one list, reviewed by the team, visible in the diff.

Any CI system works — the command is plain Python with exit codes. A
minimal Gitea/GitHub-style step:

```yaml
- name: AEGIS Light gate
  run: python .agentic/aegis.py check --strict --run
```

## Conventions worth agreeing on (all social, none enforced)

- **Journals are per-task, not per-person** — if you hand a task over,
  the journal goes with it; the log shows who did what when.
- **Don't renumber, don't reuse ids** — retire requirements
  (`status = "retired"`) instead of deleting them; history stays
  readable.
- **The frame checkpoint is where scope arguments belong** — cheaper
  than review-time arguments, and recorded in the journal either way.
- **Upgrades are one person's PR**: copy the new payload over, everyone
  reviews the diff like any other change.
