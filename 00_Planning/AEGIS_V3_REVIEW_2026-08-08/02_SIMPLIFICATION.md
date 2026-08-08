<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0.0 - Simplification And Removals

Every item here is a **deletion or a collapse**. Nothing in this document adds
a check, a layer, or a feature. Paths are relative to `05_Software/aegis/`.

## Why this document exists

The review was asked to look for over-engineering. The honest headline is that
AEGIS is **not** structurally over-engineered: the dead-symbol sweep across
every text file in the repository found **zero** unreferenced module-level
symbols among 594 package symbols and 34 hook symbols, and the module
decomposition is sensible.

The weight is elsewhere. It is concentrated in **two subsystems that no user
can reach**, **one configuration table that is validated and then ignored**,
and **a handful of checks that duplicate a sibling check**. Removing them costs
no capability.

## Ranked removals

| # | Item | Lines | Risk | Capability lost |
| --- | --- | --- | --- | --- |
| S1 | `tools/local_model_pilot.py` + its test | 1,557 | None | None - finished experiment |
| S2 | RepoWise integration | ~1,010 | Low | None reachable today |
| S3 | `[alignment]` config table | ~80 | None | None - already inert |
| S4 | Dead requirement-creation chain | ~120 | None | None - tests only |
| S5 | `spec_items` / `SpecItem` | ~15 | Low | None - always empty |
| S6 | INV-8 `missing` branch | ~5 | None | None - INV-2 covers it |
| S7 | `waiver_eligible` / `effective_policy` | ~15 | None | None - unreachable |
| S8 | Three validated-but-unread config keys | ~25 | None | None - already inert |
| S9 | `configuration_error_payload/json` | ~35 | None | None - no caller |
| S10 | `stage_forms` duplicate renderers | ~120 | Low | None - identical logic |
| S11 | Unreachable branches (12 sites) | ~60 | None | None |
| S12 | `config.py` re-reading `components.toml` | ~25 | None | Removes a self-lock (V3-23) |

**Total: roughly 3,000 lines**, of which ~2,570 is the two unreachable
subsystems.

---

## S1 - `tools/local_model_pilot.py` - a completed experiment

**1,174 lines of tool + 383 lines of test.**

A repository-wide grep for `local_model_pilot` returns exactly three hits: the
file itself, two lines of `05_Software/aegis/README.md`, and its own test.

- **Not deployed.** It sits at `aegis/tools/`, a *sibling* of `template/`. Only
  `template/` is copied into generated projects.
- **Not packaged.** `pyproject.toml` builds from `template/.agentic/cli/src`
  and the sole entry point is `aegis = "aegis.cli:main"`.
- **Not referenced by the deployer.** Zero hits across `05_Software/waegis`.
- **Its output schema names a one-off evaluation**, not a capability: line 1001
  reads `"scope": "Bonsai-only user override"` and line 1003
  `"not_equivalent_to": ["original Qwen/Codex/Claude provider matrix"]`.

The pilot answered its question. Delete the tool, its test, and the README
section. This also retires V3-58 without fixing it.

## S2 - RepoWise integration - reachable, but it cannot succeed

**718 lines of module + 250 lines of test + a shipped document + a config
file + ~40 call-site lines** in `cli.py` and `stage_forms.py`.

Unlike S1 this *is* referenced (`cli.py:1002-1003`, `stage_forms.py:444`,
`:1350`, `:2480`), so it is not dead by grep. It is unusable in practice:

- The shipped `integrations/repowise.toml` is `mode = "disabled"`, and absence
  also means disabled.
- **No AEGIS or WAEGIS command writes `repowise.toml` or the receipt.** WAEGIS 3
  *removed* the RepoWise command and pins that removal -
  `waegis/tests/test_structure_guards.py:55,76` assert the symbol stays absent.
- The evidence files are gitignored (`template/.gitignore:19-21`), so nothing
  can be committed.
- **Decisive:** with the shipped, documented `require_worktree_match = true`,
  an external provider must emit a `worktree_fingerprint` byte-identical to
  AEGIS's **private, undocumented** algorithm (`repowise.py:300-345` - a
  specific git invocation, a digest of raw porcelain bytes, then per-file
  digests in status order). `REPOWISE_INTEGRATION.md:74` says only "a worktree
  fingerprint". A third-party RepoWise cannot reproduce it, so the integration
  can effectively never report `current`. Every test monkeypatches both
  `repository_head` and `worktree_fingerprint`, so the real ones are never
  exercised - which is why V3-34 went unnoticed.

Its only live effect on a default install is the failure mode in V3-32: one
unknown key in a **disabled** optional file blocks `config validate` in a loop.

**Recommendation:** delete the module, `integrations/repowise.toml`,
`REPOWISE_INTEGRATION.md`, the test, and the call sites. If the capability is
wanted later, it should return with a *published* fingerprint contract. Doing
this also retires V3-32, V3-33 and V3-34.

If deletion is too aggressive for this release, the minimum is to move the two
`inspect_repowise` calls in `_config_command` **inside** the action branch, so
a disabled integration cannot block `config validate`.

## S3 - The `[alignment]` table is validated and never enforced

`config.py:276-280`, `509-554`, `764-780`. Five keys, a type-and-range
validator, and a cross-field consistency rule at `config.py:774-779` enforcing
coherence of a policy **nothing implements**. The only consumer is
`effective_config_dict` - that is, `config show` echoing it back.

This is worse than dead code: `06_SoftwareDocu/04_Configuring_AEGIS.md:150-175`
tells operators `[alignment.protected_scope]` "blocks a run from touching paths
you've marked". A governance tool reporting a restriction that does not exist
is the most damaging kind of inert code.

**Two honest options.** Delete the table and its documentation, or implement
one blocker in `stage_forms`' alignment-close path. Do not leave it as-is. See
V3-17.

## S4 - The requirement-creation chain is reachable only from tests

The `requirement` CLI group is **read-only** - `cli.py:296-300` registers only
`list` and `show`. Requirements are created exclusively through
`publish_requirement_records` from `stage_forms.py:1803`. Verified against
every call site in source, tests, and `waegis`:

| Symbol | Location | Only callers |
| --- | --- | --- |
| `create_requirement` | `requirements.py:189-223` | tests |
| `create_requirement_record` | `requirement_store.py:350-410` | `create_requirement` |
| `_publish_exclusive` + retry limit | `requirement_store.py:63,876-905` | `create_requirement_record` |
| `activate_requirement` | `requirements.py:356-385` | tests |
| `load_all_requirements` | `requirements.py:129-139` | tests (pass-through wrapper) |
| `RequirementRecord.req_id` | `requirement_store.py:167-170` | **zero readers** |
| `list_requirements(category=, status=)` | `requirements.py:240-260` | `cli.py:1149` passes neither |

The `create_requirement` chain is ~120 lines including an `os.link` /
`O_CREAT|O_EXCL` cross-filesystem fallback that production never executes.

**`RequirementIndex.by_test` and `by_path` are the costly ones**
(`requirements.py:84-85`, built at `:162-169`). Both dicts are rebuilt on every
`audit_traceability`, `audit_coverage`, `impact` and `uncovered_coverable_files`
call - iterating every requirement's full `linked_tests` and `affected_paths` -
and **nothing in production reads either**. `build_requirement_index`'s only
live purpose at `:453/504/655` is a duplicate-ID side effect on a discarded
return value.

## S5 - `spec_items` is a mandatory key that is always empty

Complete list of references in the repository:

```
models.py:136   class SpecItem
models.py:290   spec_items: list[SpecItem] = field(default_factory=list)
models.py:332   "spec_items",                      <- in the *required* schema key set
models.py:414   spec_items=[SpecItem(**item) for item in data["spec_items"]]
test_cli_surface.py:1052        "spec_items": [],
06_SoftwareDocu/05_Reading_AEGIS_Metadata.md:103            | `spec_items` | Every closed requirement. |
06_SoftwareDocu/.../04_Workflow_Run_Records.md:83           | `spec_items` | Specification items … applied by AEGIS. |
```

Nothing ever appends to, reads, or queries it. No `SpecItem` is constructed
outside `from_dict`. Its fields `tag`, `status`, `examples` and `threshold` are
dead by extension - `threshold` has zero hits anywhere else. Yet a graph
missing the key is **rejected** at `models.py:353-361`, and it is serialized
into every `graph.json`.

The two documentation rows are actively wrong; they describe content the list
never carries. (`Check.cites_spec` is unrelated - it holds file paths.)

Removing the key is a persisted-schema change. Either drop it in a schema bump,
or - cheaper and honest today - **fix the two documentation rows now** and
retire the model in the next schema revision.

## S6 - INV-8's missing-row branch duplicates INV-2

`invariants.py:700` versus `invariants.py:536-544`.

INV-2 fails for **any** check citing a requirement ID absent from the register.
INV-8 computes `missing = [req_id for req_id in cited if req_id not in requirements]`
over **green** checks only - a strict subset of what INV-2 already scans,
against the identical dict.

A green check citing a deleted requirement therefore produces **two**
independent blocking failures with two distinct waiver targets. The human must
approve two waivers to clear one defect, and `waive list` shows two entries for
it.

INV-8's only non-redundant contribution is the `status != "Active"` branch at
`:701-705`. Deleting lines 700 and 711-712 removes a whole duplicated blocker
with zero loss of protection. **This is the clearest example in the codebase of
the burden the owner asked to avoid.**

## S7 - The waiver-policy indirection is provably unreachable

`invariants.py:100-131` and `:290`. `InvariantResult` is constructed only
inside `invariants.py`, and **no construction anywhere uses
`policy="non-waivable"`**. Therefore:

- the `"non-waivable"` member of the set at line 290 can never match;
- `waiver_eligible` is set `True` in exactly four places, all on INV-7 results
  whose `policy` is already `"blocking"`, so the fallback
  `return self.policy == "blocking"` already yields `True`. The field never
  changes an outcome;
- `effective_policy` returns `self.policy` in every reachable case, yet is
  threaded through `to_dict` and `report.py:207`.

Four layers preserving a label that no longer exists. Collapsing them to
`policy == "blocking"` is behavior-preserving.

## S8 - Three config keys validated and never used

`config.py:264` `documentation.component_template`, `config.py:271`
`traceability.test_file_patterns`, `config.py:267` `knowledge.roots`.

Each appears only in `config.py`, `effective_config_dict`, and tests. An
operator who relocates docs and sets `component_template` sees the new value in
`config show`, while `write-component-documentation/SKILL.md:28,40` hard-codes
the original path. `test_file_patterns` is validated as globs and matched
against nothing. `knowledge.roots` is required non-empty and never enumerated.

## S9 - `configuration_error_payload` / `configuration_error_json`

`hooks/workflow_config_bootstrap.py:66-97`. No hook, transport, or adapter
calls either. Every hook uses `deny(str(exc))`, and `ConfigurationError.__str__`
(`config.py:116-121`) already returns exactly the `code: message\nremediation`
shape the README promises. The only live reference is an assertion at
`tests/test_hooks.py:91` - **a test that exists solely to cover unused code.**

## S10 - Duplicate renderers and loaders in `stage_forms.py`

At 2,864 lines this is the largest module, and a real share of it is
copy-paste:

| Pair | Lines saved | Difference between them |
| --- | --- | --- |
| `_requirement_form` / `_requirement_form_from_snapshot` (`:1565`,`:1588`) | ~35 | Only where values come from |
| `_check_form` / `_check_form_from_record` (`:1630`,`:1651`) | ~25 | Only where values come from |
| `_load_quick_check_form` / the loader inside `_apply_checks` (`:1849`,`:1996`) | ~30 | ID/filename rule, citation rule |
| `_rehydrate_requirement_forms` / `_rehydrate_adopted_requirement_forms` (`:1485`,`:1515`) | ~20 | Only the empty case |
| `_quick_check_next_command` (`:1906-1926`) | ~12 | Both branches return byte-identical expressions |

The "active implementation evidence" set comprehension also appears **verbatim
three times** (`:707-711`, `:1302-1306`, `:2201-2205`), and `:2192-2211`
duplicates checks already made by `_validate_quick_linked_check_evidence` at
`:1940-1947`.

Two more one-line wrappers with a single caller: `bypassed_stages` (`:144-151`)
over `run_stage_spec(graph).bypassed_stages` - five other modules call the
attribute directly - and `evidence_forms._next_evidence_id` (`:254-258`) over
`store.next_evidence_id`.

Treat this as opportunistic cleanup while fixing V3-11/V3-13 in the same file,
not as a standalone refactor.

## S11 - Unreachable branches

| Where | Why it cannot fire |
| --- | --- |
| `components.py:414-419` | `audit_local_scope:330` already `continue`d for every component that meets the minimum |
| `config.py:715-716` | `tomllib.loads` is typed `-> dict` and cannot return otherwise |
| `config.py:693-699` | `_path` already ran `normalize_repository_path`, which rejects absolute, `~`, drive-letter and `..` |
| `stage_schema.py:481` | `set(mapping) == set(ALL_STAGES)` already implies equal lengths |
| `stage_forms.py:2228-2231` | `_validate_stage_values:2462` rejects the same value first |
| `stage_forms.py:1510-1511`, `:1560-1561` | Guarded by an earlier early return, so `first` is always set |
| `stage_forms.py:2662-2663` | Every accepted-token tuple in `stage_schema.py` has 2 or 3 members |
| `waiver_targets.py:181-182` | `audit_working_tree` always includes `blocking_findings`; `verification.py:202` indexes it unguarded |
| `cli.py:1189-1190` | `store.list_runs` documents and implements total absorption |
| `cli.py:1004` | `--run` has `dest="run"`, so the attribute always exists |
| `cli.py:1152` | On the `show` path `records` is always length 1 |
| `store.py:209-230` | `_reject_nested_agentic_root` only fires for nonexistent-path fallbacks; production always passes `Path.cwd()` |

Also `cli.py:122-133` `TOP_LEVEL_COMMANDS` - a parallel source of truth no
production code reads. Its only consumers are three lines of
`tests/test_cli_v2.py`, and that test asserts the constant equals a hardcoded
literal, so the constant can drift from the real parser without failing.

## S12 - Duplicated validation layers

- **`config.py:693-717` re-reads `components.toml`.** `components.py:113-114`
  already loads the same file with the same exception set. The only added
  effect of the config-layer copy is the self-lock in V3-23.
- **`requirements.py` triple-validates an update.** `activate_requirement:374`
  calls `_require_resolvable_tests`, then `update_requirement:342` calls it
  again with no cache, so every linked test file is read from disk twice.
  `update_requirement:341` calls `validate_requirement_record`, then
  `write_requirement_record:430` calls it again. The requirement lock is
  acquired at `:295` and re-acquired at `requirement_store.py:445` - safe
  because `FileLock` is reentrant, but the safety depends on an invariant
  neither site states.
- **`requirements.py:106-123` `clear_linked_tests`/`clear_affected_paths`/
  `clear_spec_ref`.** The docstring says they exist so "replace with empty is
  distinguishable from leave unchanged" - but `None` already encodes
  "unchanged" and `[]` already means "empty". Three bool fields, three
  mutual-exclusion checks, and three conditional branches for a distinction the
  types already carry. No production caller sets any of them.
- **`invariants.py:1076-1098` `_staged_changes_text`.** Its own docstring says:
  "Once a `HEAD` exists this is a subset of `git diff HEAD`, so scanning both is
  redundant but never wrong." It matters only in a repository with **no commits
  at all**, yet costs an extra `git diff` subprocess plus a full re-run of every
  secret regex on `verify invariants`, `verify run`, `waive list`, `run status`,
  `delivery report`, and every stage close.
- **`cli.py:195-196` `run select` parses the graph twice** - `resolve_run_id`
  already validated it via `_load_selected_graph`.
- **`cli.py:891` `_adoption_command` loads components before dispatching to
  `coverage-waivers`**, which never uses the manifest.

## Performance items worth folding in

These are not defects, but they are cheap wins that reduce felt weight:

- **`store.py:842-845` `append_journal` is O(n²).** Every event reads the whole
  journal, concatenates one line, and rewrites a full fsynced copy through
  `os.replace`. It matters because `gate.output` events carry two 4,000-char
  tails, so journals reach megabytes and every later event re-fsyncs all of it.
  A plain `O_APPEND` write plus fsync gives the same crash-safety at O(1) - the
  journal lock is already held.
- **Every `Bash` call spawns Node plus Python three times** (`guard_shell_write`,
  `secret_scan`, `delivery_preflight`), each re-importing `aegis.config` and
  re-parsing `workflow.toml`. Measured on the review host: **~0.55 s of pure
  overhead per shell command.** One dispatcher hook loading the config once and
  running the three checks in-process would cut this to ~0.2 s with no loss of
  coverage.
- **`gates.py:222` persists the graph once per gate command.** An eight-command
  sweep writes and fsyncs `graph.json` eight times, journals eight times, then
  writes a ninth time - and a crash mid-loop leaves gate evidence on disk with
  none of its `gate.output` events. The two sibling implementations
  (`gates.py:504`, `check_execution.py:416`) batch correctly; only the main gate
  loop diverges, contradicting the module docstring.
- **`store.py:1289-1292`** retries on a UUID4 collision (2^122). `init_graph` at
  `store.py:759` mints an ID with no such loop, so the codebase already
  disagrees with itself about whether this is warranted.

## One duplication to consolidate rather than delete

`gates._supersede_prior_gate_evidence` and `check_execution._update_check_states`
are two near-identical supersession algorithms with subtly different rules;
`gates.py:637` says one "Mirrors" the other. Likewise
`check_execution._check_stage_blocker:534` states its construction "mirrors
`stage_forms._specific_stage_blocker` exactly; any divergence would silently
stop matching approved waivers". They currently agree - but two hand-copied
digest constructions guarding the same waiver identity, with nothing enforcing
the equality, is a standing hazard. This is the same one-sided-fix pattern that
produced V3-09, V3-19 and V3-21.
