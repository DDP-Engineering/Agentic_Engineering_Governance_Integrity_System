# Stage Reference Authoring Guide

**Status:** implementation aid for WP1
**Canonical plan:** [00_PLAN.md](00_PLAN.md)
**Scope:** all 15 standard and adoption lifecycle stages

This file describes how to write the human-facing stage references. It is not
the source of truth for completion criteria. The canonical `Done when` data is
the declarative stage-contract mapping introduced by WP1 in `stage_schema.py`.
Tests must fail when a Markdown checklist drifts from that mapping.

## Required six-section shape

Every stage reference uses these sections in this order:

```markdown
# Stage: <name>

**Purpose:** One sentence describing what exists after this stage.

**Read first:**

- Only the artifacts named by `aegis run context --json`.
- The prepared current-stage form.
- The named final form from the preceding stage, when applicable.

**Steps:**

1. Use imperative, numbered actions.
2. Put one action in each step.
3. Include exact commands; do not require the model to recall syntax.
4. State the reason beside a rule when it changes behavior in edge cases.

**Outputs:**

- Name each repository artifact or durable state change.

**Done when:**

- [ ] Exact checked projection of the canonical stage contract.
- [ ] Human judgement is marked `(human)`.
- [ ] Machine criteria name their verification command.

**Skip when:** State the exact condition, or `Never`, with its reason.

---

## If you are stuck

Put route-back, waiver, and recovery instructions here, after the forward path.
```

## Authoring rules

1. Forward work appears before routing, waivers, and recovery.
2. A normal stage session reads only its active router/reference, not all stage
   files.
3. Every command must exist in the CLI version shipped with the reference.
4. A bypass is described as `bypassed`, never pass or waived.
5. A disabled policy is described as `not-enforced`, never pass.
6. A command request that launches no command is `nothing-ran`, never pass.
7. Quick work still requires a registered reproducing check and red then green
   evidence after WP3.
8. Use the requirement guidance `one independently observable contract` and
   retain the Light-derived clarification that clear prose is better than a
   contorted EARS sentence.
9. Keep each active reference at or below 5 KiB unless the WP1 implementation
   record contains a measured exception.
10. Keep host-specific instructions in adapters; keep workflow rules here.

## Stage-to-reference inventory

| Stage | Canonical human-facing path |
|---|---|
| `intake` | `.agentic/skills/agentic-development/reference/intake.md` |
| `alignment` | `.agentic/skills/agentic-development/reference/alignment.md` |
| `requirement` | `.agentic/skills/agentic-development/reference/requirement.md` |
| `design` | `.agentic/skills/agentic-development/reference/design.md` |
| `check` | `.agentic/skills/agentic-development/reference/check.md` |
| `implementation` | `.agentic/skills/agentic-development/reference/implementation.md` |
| `validation` | `.agentic/skills/agentic-development/reference/validation.md` |
| `delivery` | `.agentic/skills/agentic-delivery/SKILL.md` |
| `adoption-intake` | `.agentic/skills/agentic-adoption/reference/adoption-intake.md` |
| `adoption-alignment` | `.agentic/skills/agentic-adoption/reference/adoption-alignment.md` |
| `repo-discovery` | `.agentic/skills/agentic-adoption/reference/repo-discovery.md` |
| `component-map` | `.agentic/skills/agentic-adoption/reference/component-map.md` |
| `component-adoption` | `.agentic/skills/agentic-adoption/reference/component-adoption.md` |
| `baseline-review` | `.agentic/skills/agentic-adoption/reference/baseline-review.md` |
| `adoption-delivery` | `.agentic/skills/agentic-adoption/reference/adoption-delivery.md` |

## WP1 review checklist

- [ ] all 15 `ALL_STAGES` values have a stage contract
- [ ] every contract contains at least one item
- [ ] every item names a command or is marked human
- [ ] single-stage forms render the checklist once
- [ ] collection stages render it once in `stage.toml`
- [ ] TOML parsing and imported payload digests are unchanged by comments
- [ ] re-prepared forms reproduce the same checklist
- [ ] every Markdown checklist matches the canonical normalized list
- [ ] every reference uses all six sections in the required order
- [ ] every reference stays within the measured context budget
- [ ] recovery instructions come after the ordinary forward path
- [ ] the context pack does not require `graph.json` or `journal.jsonl`
