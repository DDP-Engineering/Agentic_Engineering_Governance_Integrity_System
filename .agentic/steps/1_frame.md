<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Stage 1 — frame

**Purpose:** Turn the ask into an agreed scope and a chosen path, and open
the task journal that every later stage reads and updates.

**Read first:**

- The prompt itself, and anything it points at.
- `.agentic/AGENTS.md` (stage table, artifact locations, interaction modes).
- `python .agentic/aegis.py status` — an open task may already cover this.
- The knowledge page for the area named in the ask, if one exists:
  `.agentic/knowledge/<component>.md`.

**Stage report (completion or pause):** At this boundary, record only durable
events allowed by the journal contract, update the header and checklist, and
refresh the single `## Stage report` section in this task journal:
At every stage transition or pause, append any new Ruling and refresh the Handoff;
also refresh the Handoff for a blocker or session end.
`stage`, `result`, `current`, `changed`, `evidence`, `issues`, `next`,
`needs_user`, `spec_compliance`, `implementation_quality`, and `review_round`
(plain one-line fields, no fences). Record the completed stage
separately from `current`, which must match the header after any transition;
use `paused` when waiting or ending a session. Other results are `in_progress`,
`completed`, `blocked`, `skipped`. Run
`python .agentic/aegis.py summary TASK-<id>` and copy its block before any
detailed explanation. Unknown values stay blank (`not recorded`); refresh
stale records and read omitted details before continuing. Preserve existing
approval stops and immediate deviation notices; this report adds no new stop.

**Resume context:** Run `brief TASK-<id>` first, then read this stage's instructions,
the journal header/checklist, dedicated durable sections, and relevant log
entries (stage outcomes, blockers, material changes and consolidated evidence);
follow links to needed records.
This stage's required full reads still apply. Use linked requirements and
source as needed, not the whole register. Do not act on missing, stale, or
shortened reporting without reviewing the full journal information.

**Steps:**

1. Restate the ask in one or two sentences, in your own words. Name what
   is in scope and, explicitly, what is not.
2. Locate the area: which components and which files this will touch.
   Skim them; do not edit anything yet.
3. Choose the path. Take the **quick path** (`frame → build → validate → deliver`)
   only when all of these hold: no new externally observable behavior, no
   new interface or data format, no new dependency, an existing
   requirement already covers the behavior you are changing, and the
   change touches no security- or data-handling behavior - those always
   take the full path. Otherwise take the full path.
   Decide here whether the work is large enough for optional children. Use
   children only for independently scoped work that can remain an ordinary
   governed task; keep small or tightly coupled work in the parent.
4. Establish the branch. If you are on the repo's default branch, create
   a task branch now (`git checkout -b task/<short-slug>`, or the repo's
   own naming convention). The journal's `branch:` header must match
   `git branch --show-current` — later sessions verify this on resume.
5. Create the journal:
   `python .agentic/aegis.py task "<title>" --type feature`
   (`--type fix` or `--type change` as appropriate).
6. Fill the journal header: `stage`, `type`, `path`, `branch`, `opened`.
   Leave `requirements:` empty until `specify` (quick path: fill it now
   with the existing requirement IDs you will touch).
7. Keep the detailed scope, exclusions, path reasoning, and proposed
   requirements in the journal's dedicated Frame content. Append one concise
   `frame` outcome line to `## Log`, naming the chosen path and whether scope
   was accepted or paused. Put durable authority or scope decisions in Rulings
   instead of repeating them in the Log.
8. Copy the "Done when" checklist below into `## Done checklist`.
9. Checkpoint mode: present the scope, the chosen path, and the proposed
    requirements, and wait for a yes before continuing. Autopilot: record the
    same concise frame outcome and continue without stopping.
10. Set `stage: specify` (full path) or `stage: build` (quick path), and
    **replace `## Done checklist`** with the next stage's "Done when" list
    (from `2_specify.md`, or `4_build.md` on the quick path). The
    checklist always shows the current stage's items — that is what
    resume relies on.

**Outputs:**

- `.agentic/tasks/TASK-<id>.md` — created, header filled, one frame outcome
  line written, checklist copied in.

**Done when:**

- [ ] scope and exclusions written in the dedicated Frame content
- [ ] path chosen (`full` or `quick`) with its reason logged
- [ ] task branch established; `branch:` header matches the checkout
- [ ] task journal created with a complete header
- [ ] expected requirements listed
- [ ] scope confirmed (checkpoint mode) or logged (autopilot)
- [ ] `stage:` advanced

**Skip when:** Never. Every task starts here, however small. If the prompt
names an existing task, do not frame it again — follow the resume
procedure in `.agentic/AGENTS.md` instead.
