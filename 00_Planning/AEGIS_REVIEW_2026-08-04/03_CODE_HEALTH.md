# AEGIS V2 Review — Dead Code, Duplication, and Simplification Observations

Date: 2026-08-04
Scope: `05_Software/aegis`

Per the owner's constraint, this document is split into **work** (things that are
a bug risk or a workflow problem) and **observations** (things a greenfield
review would flag, which are deliberately *not* proposed as work).

---

## Headline: there is no dead code

A whole-tree symbol-reference scan enumerated every top-level `def`, `class`, and
constant across the 21 CLI modules, 7 hooks, and `tools/run_aegis.py`, then
counted word-boundary references across the **entire** payload including `tests/`,
`documents/`, `skills/`, and every `.toml` / `.json` / `.mjs` / `.ts` / `.sh` /
`.ps1` file.

**Every production symbol resolved to at least one reference beyond its own
definition.** The 78 symbols with no external reference were all module-private
helpers used exactly once inside their own file — live, not dead.

There is also **no obsolete schema-version handling**: `models.py:331`,
`config.py:641`, and `requirement_store.py:615` all reject anything that is not
their current schema version outright rather than migrating, so there are no
branches for versions that can no longer occur.

And **no V1 leftovers on this `AEGIS_V2` branch**. Every `waegis repowise …` /
`waegis configure …` reference in `documents/` points at the separate WAEGIS
companion tool, not at a removed `aegis` subcommand — verified against
`REPOWISE_INTEGRATION.md:25-45`. This was initially flagged and then disproved;
the negative is recorded here so it is not re-investigated.

Specific plausible-looking false positives, confirmed live: `stage_forms.py:2114`
`_legacy_rehydrated_values` (despite the name it is the normal first-`prepare`
path, not V1 residue), `paths.py:76` `contained_relative_path`,
`guard_write_zone.py:163` `extract_patch_paths`, config constants `RISK_LEVELS` /
`COMPLETION_LEVELS` / `DEFAULT_QUICK_CHANGED_PATHS_MAX`,
`requirements/coverage_waivers.txt` (read at `requirements.py:607`), and
`component_template.md` (properly wired via `workflow.toml:28` → `config.py:417`).

`reports/adoption/adoption_report_template.md` is read by no code, but that is
correct by design — it is a hand-authoring template introduced by
`reports/adoption/README.md:16` with no competing CLI generator. Not a finding.

---

## Work

### H1 — `stage_forms._q` must not be "cleaned up" into the shared helper

**Severity: latent bug risk** · Files: `stage_forms.py:2204`, `_form_io.py:63-65`, `requirement_store.py:839`

Three TOML-quoting helpers exist. Two are byte-identical; the third is not:

```
_form_io.quote_toml_string(v)   -> json.dumps(v,       ensure_ascii=False)
requirement_store._toml_string(v) -> json.dumps(v,       ensure_ascii=False)   # identical
stage_forms._q(value)            -> json.dumps(str(value), ensure_ascii=False)  # DIFFERENT
```

The names have already collided: `check_execution.py:30` and
`evidence_forms.py:24` both import `quote_toml_string` **aliased to `_q`**, while
`stage_forms.py:32` imports a different helper from the same module and keeps its
own `_q`, used 24 times.

The obvious future "cleanup" — adding
`from ._form_io import quote_toml_string as _q` to `stage_forms.py` — would
silently change all 24 call sites for non-`str` inputs. `json.dumps(True)` emits
bare `true` and `json.dumps(1)` emits bare `1`, which TOML parses as a **bool or
int, not a string**. A form field would change type with no error anywhere.

**Action: add a comment, not a refactor.** ~~One line in the `_q` docstring at
`stage_forms.py:2202` stating that the `str()` coercion is load-bearing and this
function must not be replaced by `_form_io.quote_toml_string`.~~ **Superseded by
B25 (Batch 6, 2026-08-04):** `_q` itself carried B3's U+007F defect, so "leave
the function alone" was the wrong instruction — it needed the same TOML-legal
escaping the other two helpers got. The fix keeps the load-bearing part: `_q`
still coerces every scalar with `str()` before quoting, so it still never emits
a bare `true`/`1` TOML literal for a non-string field. What changed is that the
quoting step now runs through a TOML-legal escaper (`_toml_escape`, a third,
deliberately separate copy — see below) instead of `json.dumps`. The docstring
now says the `str()` coercion is load-bearing, not that the whole function must
be left unchanged. Merging the three helpers into one is still the risky move,
not the safe one.

Note **B3** in `01_BUGS.md` changes the *bodies* of the two identical helpers for
TOML-legal escaping, and **B25** applies the equivalent fix to `_q`. Apply each
fix separately; do not take any of them as licence to consolidate the three
helpers.

### H2 — Two different companion-spec scaffolds

Covered as **D3** in `02_WORKFLOW.md` — the docs point the agent at
`requirements/spec_template.md` (8 sections) while the CLI auto-generates a
different 3-heading scaffold at the `spec_ref` path. `spec_template.md` is read by
no code; grep finds exactly one reference in the whole payload, and it is the
README line that misdirects.

### H3 — Adapter skill drift

Covered as **D8** in `02_WORKFLOW.md` — `.claude` and `.qwen` copies of
`documentation-audit/SKILL.md` dropped "in changed-only mode", which the
`.agentic` source and the `.codex` copy both retain. Impact is mild (both
wrappers still cite the shared skill as authoritative), but it is the only place
an adapter restates a rule differently per host, and that is the drift pattern
worth stopping while it is still two words.

---

## Observations — **not** recommended work

Each item below is real, and each is deliberately **not** proposed. They are
recorded so the same ground is not re-covered by a future review, and so the
reasoning for leaving them alone is on file.

### Duplication that has not drifted

| Location | Observation | Why leave it |
|---|---|---|
| `guard_shell_write.py:276`, `guard_write_zone.py:108` | `read_run_state()` duplicated verbatim | Consolidating needs a new shared hook module; hook files are deliberately standalone |
| `guard_shell_write.py:298` vs `guard_write_zone.py:206` | `is_protected_path` in 3-arg and 2-arg forms | Identical logic, different matcher plumbing |
| 7 sites incl. `requirement_store.py:875`, `waivers.py:71`, `store.py:681` | `sha256(path.read_bytes()).hexdigest()` open-coded | All agree; no drift |
| `_form_io.py:68` `retire_form` vs `stage_forms.py:1968` `_apply_retention` | Same retention policy at different granularity | Genuinely different scopes — merging would be worse |
| `components.py:352` `_normalize_path` | Weaker than `paths.normalize_repository_path` | Not currently a bug: all callers receive paths already normalized upstream. Recorded as a trap, not a defect |
| 35 `SKILL.md` files across 5 host directories | Intentional thin-wrapper architecture | `.agentic/` holds the neutral procedure; adapters carry host-specific frontmatter and cite it. Verified by diffing all five copies of two skills |

### Machinery a greenfield review would question

Each of these is load-bearing for something. Removing any would touch multiple
modules and the 433-test suite.

| Machinery | Why it exists | Cost to remove |
|---|---|---|
| Graph digest / stale-update rejection (`store.py:679-686`, `:882-928`) | INV-10 and every waiver depend on digest identity; `graph_transaction` performs the silent-heal reload that makes concurrent CLI calls safe | Not removable without breaking INV-10 and waiver matching |
| Cross-process `FileLock` (`persistence.py:84-205`, ~120 lines) | Real concurrency exists — `post_tool_evidence.py:64` appends a journal line on every tool use, concurrently with the CLI | Removing it would corrupt journals |
| Journal/graph rollback choreography (`store.py:711-786`, `:986-1085`, ~160 lines) | The only thing between a crash and a graph claiming a waiver the journal never recorded. Git cannot recover this — `.agentic/runs/` is typically uncommitted mid-run | ~160 lines |
| Directory fsync / `create_temporary_*` (`persistence.py:240-350`) | Durability for atomic replace; already a no-op on Windows | ~50 lines; cheap insurance |
| Run-ID calendar validation (`store.py:456-469`) | Rejects impossible dates in what is only ever a directory name | ~10 lines; purely cosmetic |
| Canonical UUIDv4 round-trip (`requirement_store.py:203-212`) | Keeps filename↔ID a bijection on case-insensitive filesystems — a legitimate concern on Windows | ~8 lines |
| Timestamp regex + `strptime` (`requirement_store.py:815-822`) | Two-layer check of one thing | ~6 lines; harmless |
| `_unquote_git_path` C-style unquoting (`working_tree.py:170-208`) | Covers quotes/backslashes in filenames; `core.quotepath=false` covers the non-ASCII case | ~40 lines. See **B7** — the bug is the `.replace()` *after* it, not the unquoting |
| `guard_shell_write.py` shell-write modelling (338 lines) | Its own docstring concedes it is best-effort, with the delivery working-tree audit as the real backstop. Only active when `write_access.mode = "stage_restricted"`, not the default | 338 lines, but deleting it is a policy decision, not a cleanup |

### Config surface that is parsed but never consumed

`[alignment]` requires seven keys plus a subtable, and **none of them has a
consumer anywhere in the package** outside `effective_config_dict`. Verified: the
only non-`config.py` references to `alignment_enabled`,
`alignment_pause_on_open_questions`, `alignment_risk_threshold`,
`alignment_allow_recommended_responses`, and `alignment_protected_scope` are
assertions in `tests/test_documentation_workflow.py:55-59,86-90`.

`config.py:773-778` even enforces a consistency rule *between two unused values*.
Same situation for `documentation.component_template` and `knowledge.roots`.

Every adopting repository must therefore author a table that does nothing, and
get it exactly right — one of the config errors hit while reproducing **B1**
during this review was `alignment.protected_scope has the wrong type`, on a
value nothing reads.

**Still not proposed as work.** Making `[alignment]` optional the way `[quick]`
already is (`config.py:598-637`) is a single-module change, but it rewrites the
template `workflow.toml` and every config test — larger than the owner's bar. It
is recorded here because if `[alignment]` is *intended* to drive future behavior,
that intent should be written down; and if it is not, this is the single largest
piece of ceremony in the config surface.

---

## Test-coverage gaps confirmed during this review

Not proposed as work on their own, but worth knowing when fixing the bugs above:

- No test asserts file modes (`chmod` / `st_mode` appear nowhere) — **B5**.
- No test feeds a rename/`previous_path` status entry — **B2**.
- No test puts a control character in requirement text — **B3**.
- `INV-1` appears in tests only in the quick-run not-applicable lists — **B10**.
- `tests/test_gates.py:36` tests only `PermissionError` for launch refusal — **B12**.

---

## Areas not covered

- `.pi/extensions/*.ts` (3 files) and `.opencode/plugins/agentic-guard.mjs` were
  included in reference counting but their internal logic was not reviewed
  against the Python hooks.
- Intra-function dead branches. The analysis was at top-level-symbol granularity;
  `config.py` (1448 lines) and `stage_forms.py` (2217 lines) are the likeliest
  homes for unreachable `if` arms.
- `repowise.py` (718 lines) was not reviewed by any pass. Its `inspect_repowise`
  return contract drives both the `repo-discovery` readiness blocker and a
  non-waivable classification (**W7**), so it is a plausible home for further
  gating bugs and deserves its own pass.
- `tests/` internal duplication — tests were used as a reference source for
  liveness, not audited as a subject.
