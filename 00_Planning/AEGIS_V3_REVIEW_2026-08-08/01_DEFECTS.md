<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS 3.0.0 - Defects

Verification tags: **[reproduced]** first-hand in a scratch deployment with a
control case; **[code-verified]** confirmed by executing or reading the exact
code path; **[reported]** established by a reviewing agent through execution,
not independently re-run.

Paths are relative to `05_Software/aegis/`.

## Summary

| ID | Sev | Tag | Defect |
| --- | --- | --- | --- |
| V3-01 | High | reproduced | Guard hooks fail **open** for every non-ASCII policy pattern on Windows |
| V3-02 | High | reproduced | CLI crashes with `UnicodeEncodeError` **after** mutating durable state |
| V3-03 | High | reproduced | `echo x>file` (no space) bypasses the shell write guard |
| V3-04 | High | reproduced | `>\|` clobber operator bypasses the shell write guard |
| V3-05 | High | reproduced | `cp -t DEST src` makes the guard inspect the wrong operand |
| V3-06 | High | reproduced | `*** Move to:` patch destination is never checked |
| V3-07 | High | reproduced | Unknown tool names are allowed; `NotebookEdit` writes unguarded |
| V3-08 | High | reported | Protected-**read** policy is not wired to the shell on any adapter |
| V3-09 | High | reproduced | Non-object `graph.json` escapes the error boundary as a traceback |
| V3-10 | High | reproduced | A path containing `[` or `]` crashes `verify impact` |
| V3-11 | High | code-verified | `component-adoption` form is invisible to `run context` |
| V3-12 | High | reproduced | `run context` omits `status` and `next` from the universal envelope |
| V3-13 | High | reported | Stale `control.route_to` silently re-routes and re-waives the evidence gate |
| V3-14 | High | reported | `stage prepare` is a no-op, so five error messages give impossible advice |
| V3-15 | High | reported | Working-tree audit evaluates nothing when `.agentic` is below the Git root |
| V3-16 | High | reproduced | `**/x` misses repository-root files; `*` crosses `/` in write allow-lists |
| V3-17 | High | reported | The whole `[alignment]` policy table is validated and never enforced |
| V3-18 | High | reported | `gates.test.impacted_command` rejects legal argv, bricking the workspace |
| V3-19 | High | reported | Managed-check reruns overwrite the log of the still-active red witness |
| V3-20 | High | reported | Gate/check timeout is unenforceable on Windows; `verify gates` can hang |
| V3-21 | Med | reproduced | `report.md` reports coverage **PASS** when coverage is disabled (default) |
| V3-22 | Med | reported | Disabling a failing gate leaves INV-4 blocking with no waiver target |
| V3-23 | Med | reported | A malformed `components.toml` bricks every command including recovery |
| V3-24 | Med | reported | INV-9 aborts the whole invariant pass, taking `waive list` with it |
| V3-25 | Med | reported | Abandoning an unreadable run loops the operator forever |
| V3-26 | Med | reported | A torn journal makes a readable run impossible to abandon |
| V3-27 | Med | reproduced | Release-hygiene test fails on ordinary local activity |
| V3-28 | Med | reported | `secret_scan` carve-out matches any `*/.agentic/workflow.toml` |
| V3-29 | Med | reported | `MultiEdit` that **deletes** a credential is denied |
| V3-30 | Med | reported | `delivery_preflight` substring match evaded by any inserted git flag |
| V3-31 | Med | reported | Evidence can be appended to a completed run |
| V3-32 | Med | reported | Optional, **disabled** RepoWise file blocks `config validate` in a loop |
| V3-33 | Med | reported | External RepoWise graph crashes the CLI with an uncaught `TypeError` |
| V3-34 | Med | reported | `worktree_fingerprint` degrades to a content-blind hash |
| V3-35 | Med | code-verified | Shipped docs contradict the code (INV-3, INV-7, response keys) |

Lower-severity items are tabulated in the final section.

---

## A. One root cause behind three High defects: I/O encoding is never pinned

AEGIS never fixes UTF-8 on its own standard streams or subprocess decoding. On
Windows the process therefore inherits `cp1252`. Confirmed on the review host:
`sys.stdin.encoding == 'cp1252'`, `errors == 'surrogateescape'`.

This one omission produces V3-01, V3-02 and the approver-corruption defect
below. It is the highest-value fix in the review: roughly one line per entry
point.

### V3-01 - High - [reproduced] - Guards fail **open** on non-ASCII patterns

**Where:** `template/.agentic/hooks/secret_scan.py:72`,
`guard_write_zone.py:74`, `guard_read_path.py:118`, `guard_shell_write.py:94`,
`delivery_preflight.py:35`, `post_tool_evidence.py:33` - every hook reads
`json.load(sys.stdin)`.

The adapters send UTF-8 bytes. Python decodes them as `cp1252` with
`errors="surrogateescape"`, which **cannot raise** - so the text is silently
mangled and no pattern matches it. The hook exits 0: allow.

**Reproduced** with `[guardrails.secrets] mode = "enforce"` and two patterns,
one ASCII and one accented:

| Content written | Default env | `PYTHONUTF8=1` |
| --- | --- | --- |
| `KEY = "CLE_SECRETE_4242"` (control) | DENY | DENY |
| `KEY = "CLÉ_SECRÈTE_4242"` | **ALLOW** | DENY |

The ASCII control denies in both environments, so the harness is sound; only
the non-ASCII case leaks.

**Why it matters:** this is precisely the capability `secret_scan.py:15-18`
claims to have delivered - "so a configured pattern can match a secret that
contains non-ASCII characters". That fix (`ensure_ascii=False`) repaired the
**output** side of serialization while the **input** side was already
destroying the characters. Any team writing policy in a non-English language
has guards that silently do nothing.

**Fix:** `sys.stdin.reconfigure(encoding="utf-8")` at the top of each hook, or
set `PYTHONUTF8=1` in the spawn environment of the three transports.

### V3-02 - High - [reproduced] - CLI crashes **after** mutating state

**Where:** `template/.agentic/cli/src/aegis/cli.py:1305-1336` (`_respond`).

`_respond` writes through `sys.stdout`, which is `cp1252` whenever stdout is a
pipe (only an attached console gets UTF-8). A character outside cp1252 raises
`UnicodeEncodeError` - a `ValueError`, but not one of the seven types `main()`
catches at `cli.py:225`, so it escapes the error boundary.

**Reproduced** with stdout piped:

| `run abandon --reason ...` | rc | stdout | stderr |
| --- | --- | --- | --- |
| `blocked until CI >= 3 green runs` (control) | 0 | `status: ok` | - |
| `blocked until CI ≥ 3 green runs` | **1** | `status: ok` (truncated) | `UnicodeEncodeError` |

The graph was inspected afterwards: `complete=True, outcome='abandoned'`. **The
run really was abandoned.** The caller sees exit 1, a traceback, and a partial
body whose visible `status` says `ok`.

**Why it matters:** exit 1 must mean a typed `blocked` response
(`CLI_API_REFERENCE.md:56-66`); here it means "succeeded, then failed to print".
AEGIS's own `delivery_preflight.py` runs the CLI with `capture_output=True` and
treats non-zero as verification failure, so this surfaces as a governance block
on work that actually completed. Reachable through waiver reasons, approver
names, requirement prose, and any error string embedding them.

**Fix:** `sys.stdout.reconfigure(encoding="utf-8")` in `main()`. Note the
asymmetry proving this is unintended: `verification.py:222` writes the durable
summary with default `ensure_ascii=True`, so the file surface is already safe.

### Approver corruption - High - [reported] - same root cause

`cli.py:1235-1241` runs `git config` with `text=True` and no `encoding=`, so
Git's UTF-8 output is decoded as cp1252. With `user.name = "José Müller"`,
`_resolve_approver` returns `'JosÃ© MÃ¼ller <jose@example.com>'`, and that
string is persisted permanently into `graph.json` and `journal.jsonl` as the
`approver` - the one field whose entire purpose is attributing who accepted a
risk. For names whose UTF-8 bytes include `0x81/0x8D/0x8F/0x90/0x9D` the decode
raises and `except (OSError, ValueError)` silently degrades the approver to the
bare email. `delivery_preflight.py` already passes `encoding="utf-8"`
explicitly, so the convention exists in-repo.

---

## B. Guardrail bypasses

All six below were reproduced against a working control - the equivalent
"obvious" form of the same operation is correctly denied, so these are gaps in
the matcher, not a misconfigured harness. Configuration used:
`[guardrails.protected_paths] mode = "enforce"`, `patterns = ["secrets/**"]`,
`operations = ["read", "write"]`.

| Command / input | Verdict |
| --- | --- |
| `echo evil > secrets/prod.key` (control) | DENY |
| `echo evil >secrets/prod.key` | DENY |
| `echo evil>secrets/prod.key` | **ALLOW** (V3-03) |
| `echo evil >\| secrets/prod.key` | **ALLOW** (V3-04) |
| `cp payload.sh secrets/prod.key` (control) | DENY |
| `cp -t secrets payload.sh` | **ALLOW** (V3-05) |
| `apply_patch` with `*** Update File: secrets/prod.key` (control) | DENY |
| `apply_patch` with `*** Move to: secrets/prod.key` | **ALLOW** (V3-06) |
| `Write` to `secrets/prod.key` (control) | DENY |
| `NotebookEdit` with `notebook_path: secrets/prod.key` | **ALLOW** (V3-07) |

### V3-03 / V3-04 - High - [reproduced] - Redirect tokenizing

**Where:** `guard_shell_write.py:64` (`_SEGMENT_SPLIT_RE`), `:70`
(`_REDIRECT_TOKEN_RE`), `:195-198` (`_tokenize` with `whitespace_split=True`).

`shlex` with `whitespace_split=True` does not treat `>` as a delimiter, so
`evil>path` stays one token, and the regex requires the token to *begin* with
`>`. The module docstring files this under obfuscation - but `echo x>f` is
ordinary shell, and it is the first variation anyone types. The parametrized
test at `tests/test_hooks.py:1368-1400` only ever exercises the spaced form.

The `>|` case is a second-order effect: `_SEGMENT_SPLIT_RE` strips `|` and `&`
*before* `_REDIRECT_TOKEN_RE` runs, so that regex's `\|?` group and its `&`
alternative can never match anything - they are dead branches, and the `\|?`
one is a live bypass.

**Fix:** pre-split each segment on `(?<=\S)(?=(?:[0-9]+|&)?>)` before
tokenizing, and handle `>|` in the redirect token.

### V3-05 - High - [reproduced] - `-t` target-directory flag

**Where:** `guard_shell_write.py:251-255` - `non_flags[-1]` is taken as the
destination. With `-t DEST`, the destination comes **first**, so the guard
inspects a source file. It both misses the violation and, when it does deny,
can name a path the command only reads.

### V3-06 - High - [reproduced] - `*** Move to:` unparsed

**Where:** `guard_write_zone.py:199` -
`re.match(r"\*\*\* (?:Add|Update|Delete) File: (.+)", line)`. The Codex patch
envelope also carries `*** Move to: <destination>` beneath an
`*** Update File:` header. Only the source path is extracted, so a rename is an
unguarded write to any protected or out-of-zone path.

### V3-07 - High - [reproduced] - Unknown tools default to allow

**Where:** `guard_write_zone.py:81-90` - an unrecognized `tool_name` returns 0.
`NotebookEdit` writes a repository file via `notebook_path` and is in none of
the accepted names. Note the two guards default in **opposite** directions:
`guard_read_path.py:113-116` deliberately treats an unknown tool as the strict
case. `secret_scan.py:54` already lists `notebook_path` in `PATH_KEYS`, showing
the tool was known about; `guard_write_zone.extract_target_paths` never reads
that key.

### V3-08 - High - [reported] - Read policy unenforced through the shell

**Where:** `.codex/hooks.json:34-55`, `.claude/settings.json:33-52`,
`.qwen/settings.json:39-61`, `.opencode/plugins/agentic-guard.mjs:261-272`,
`.pi/extensions/agentic-guard/bridge.ts:84-98`.

Every adapter's shell branch runs `guard_shell_write`, `secret_scan` and
`delivery_preflight` - never `guard_read_path`. With read protection enforced,
`Read credentials/x.json` is denied but `cat credentials/x.json` is allowed.

Compounding it, `tests/test_hooks.py:891-921` justifies the gap with a false
statement - that Codex "reads through `shell`, already matched by the Bash
entry". The Bash entry does not run the read guard. The liveness check in
`hooks/README.md:136-140` ("ask the agent to read a protected path") therefore
passes silently on a host with no read enforcement.

---

## C. Crash and dead-end paths

### V3-09 - High - [reproduced] - Non-object JSON escapes the error boundary

**Where:** `store.py:393` (via `models.py:349`), `store.py:511`,
`verification.py:252`.

Each calls `.get()` on whatever `json.loads` returned without checking it is a
mapping, and no `except` tuple includes `AttributeError`.

**Reproduced** - with `graph.json` replaced by each value, all three commands
produce a raw traceback and exit 1:

| `graph.json` | `run status` | `run list` | `verify run` |
| --- | --- | --- | --- |
| truncated / empty / `{"schema_version": 2}` | clean `RUN-POINTER-STALE` | clean | clean |
| `[]`, `"text"`, `123`, `null`, `true` | **traceback** | **traceback** | **traceback** |

The same applies to `validation-summary.json` and `verify status`.

**Why it matters:** `store.py:511` sits inside `_pointer_missing_remediation` -
the code that builds the operator's *recovery* message. One malformed run takes
down the guidance meant to rescue it, and hides every healthy run beside it.
Both functions' docstrings promise total absorption
(`@exception None All filesystem and decoding failures are absorbed`).

**Fix already exists in-repo:** `store.py:694-696` does
`if not isinstance(payload, dict): raise ValueError("graph JSON must be an object")`
and lists `AttributeError` in its `except`. `repowise.py:534` does the same.
Three of five loaders got the guard; two did not.

### V3-10 - High - [reproduced] - Bracketed paths crash `verify impact`

**Where:** `requirements.py:515` and `:541` and `:613`, via
`paths.py:171` (`normalize_repository_path(..., allow_glob=False)`).

The glob-rejection rule is right for operator-typed patterns and wrong for
**concrete paths discovered on disk or reported by Git**. `RepositoryPathError`
is a plain `ValueError` and is not in the CLI's handled tuple.

**Reproduced and isolated** to a minimal trigger - one *uncommitted* change to
a file whose path contains `[`:

```
git status --porcelain  ->   M app/[slug]/page.py
aegis verify impact     ->   rc=1, RepositoryPathError: must not contain glob syntax
```

Same repository, same position, a file named `normal.py`: `rc=0`, correct
output. Committing the bracketed file also makes it pass, which is what makes
this easy to miss.

**Why it matters:** `app/[slug]/page.tsx` and `pages/[...all].tsx` are the
mandatory routing convention of Next.js, Astro, SvelteKit and Remix. In such a
repository, editing a route file breaks `verify impact` with a traceback naming
no file. The fault is also unwaivable, because `waive list` walks the same
code.

**Fix:** normalize disk- and Git-sourced paths with the lenient
`contained_relative_path`, keeping `allow_glob=False` for operator input only.

### V3-14 - High - [reported] - `stage prepare` cannot do what five errors ask

**Where:** `stage_forms.py:226-227` - `prepare_stage` returns early when the
record is `prepared` and the primary file exists.

Five errors instruct the operator to run exactly this command to repair a
corrupted current-revision form: `stage_forms.py:1740`, `:1768`, `:2002`,
`:2615`, and `add_stage_item` at `:303`. Every one is raised from the state in
which `stage prepare` is a no-op.

```
form gains a typo'd key -> apply: "unknown key statemnt. Run `aegis stage prepare` to regenerate..."
aegis stage prepare     -> returns intake.toml, revision still 1, typo still present
apply again             -> identical error
```

There is no `--force` on `stage prepare` (`cli.py:281-282`), so the loop is
only escapable by editing files outside the session. The early return is
defensible; the guidance text is what is wrong.

### V3-25 / V3-26 - Medium - [reported] - The run exit can be blocked

- `store.py:1189-1218`: abandoning an **unreadable** run returns
  `complete: True` but never writes it to `graph.json`, so `_discoverable_runs`
  keeps offering the abandoned run for restore, and following that advice
  re-enters the stale-pointer error. A closed loop.
- `store.py:1336-1349`: a journal not ending in `\n` raises `PersistenceError`
  before anything is written, so a **readable** run with a torn journal cannot
  be abandoned at all. The sibling path at `store.py:1212-1216` handles exactly
  this case, with the comment "a journal that is broken too must not take the
  exit down with it". That reasoning was not applied here.

---

## D. Analysis that silently fails open

### V3-15 - High - [reported] - Working-tree audit when `.agentic` is below the Git root

**Where:** `working_tree.py:242-279` (`_git_status`).

`git status --porcelain` reports paths relative to the **Git root**;
`_git_status` treats them as `repo_root`-relative. AEGIS's own root discovery
(`store.py:183-206`) deliberately lets `.agentic` win over `.git`, so this
layout is by design reachable.

With Git root `proj/` and `repo_root = proj/sub/`, a secret in
`proj/sub/config/secrets.yaml` yields `path = 'sub/config/secrets.yaml'`, which
matches no pattern and resolves to no existing file:

```
protected match?  False      file exists at repo_root?  False      secret scan  None
```

`protected_paths`, `blocked_patterns`, the secret scan and the adoption
source-change guard all evaporate, and `verify run` passes. This contradicts
the function's own contract at lines 141-143 ("a Git that failed or is missing
has to fail closed"). WAEGIS refuses a non-root target, so the deployed path is
safe; hand adoption, monorepo subprojects, or a later `git init` at a parent
are not. Every test in `test_working_tree.py` uses one directory as both roots.

### V3-16 - High - [reproduced] - Glob semantics

**Where:** `paths.py:98-130` (`matches_pattern`, built on `fnmatchcase`).

```
matches_pattern("secrets/key.pem",       "**/*.pem")       -> True
matches_pattern("key.pem",               "**/*.pem")       -> False   <-- root files missed
matches_pattern("src/vendor/third/x.py", "src/*.py")       -> True    <-- * crossed /
matches_pattern("infra/prod/eu/main.tf", "infra/*/main.tf")-> True
```

`fnmatch` has no `**` concept, so `**/` cannot match zero directories: a
pattern only matches paths containing at least one `/`. And `*` translates to
`.*`, which spans separators.

For a **deny**-list (`protected_paths`) over-matching is fail-safe and the
root-file miss is the danger. For the **allow**-list
(`guardrails.write_access`, treated as a permit list at
`guard_write_zone.py:102`), `*` crossing `/` is fail-open:
`implementation = ["src/*.py"]`, intended as "top-level files under src",
silently authorizes `src/vendor/third_party/anything.py`. `config.py` accepts
both patterns without complaint.

### V3-17 - High - [reported] - `[alignment]` is validated and never read

**Where:** `config.py:276-280`, `509-554`, `764-780`. The only consumer is
`effective_config_dict` at `config.py:1422-1431` - i.e. `config show`.

Repo-wide grep: `alignment_enabled`, `alignment_pause_on_open_questions`,
`alignment_risk_threshold`, `alignment_allow_recommended_responses` and
`alignment_protected_scope` appear only in `config.py` and one test. No hook,
command, invariant or skill reads them.

Setting `pause_on_open_questions = true` and then closing an alignment stage
with unresolved questions **succeeds**. `06_SoftwareDocu/04_Configuring_AEGIS.md:150-175`
describes `[alignment.protected_scope]` as "blocks a run from touching paths
you've marked", and `config.py:774-779` spends a cross-field consistency check
enforcing coherence of a policy nothing implements.

This is a governance tool telling an operator a restriction is active when it
is not. Either implement it or delete it - see `02_SIMPLIFICATION.md`.

---

## E. Contract drift

### V3-11 - High - [code-verified] - Two tables disagree about one stage

**Where:** `stage_forms.py:90` - `COLLECTION_STAGES = ("requirement", "check")`
versus `stage_context.py:35` -
`_COLLECTION_STAGES = frozenset({"requirement", "check", "component-adoption"})`.

Both drive the identical decision
`"stage.toml" if stage in <table> else f"{stage}.toml"`:

| Stage | Writer produces | `run context` looks for | |
| --- | --- | --- | --- |
| `requirement` | `stage.toml` | `stage.toml` | ok |
| `check` | `stage.toml` | `stage.toml` | ok |
| `component-adoption` | `component-adoption.toml` | `stage.toml` | **mismatch** |
| `baseline-review` | `baseline-review.toml` | `baseline-review.toml` | ok |

`run context` therefore reports `artifact: none` and
`unavailable_current_artifact`, and omits the form from `required_reads`
entirely. Since `AGENTS.md:47-52` forbids reading anything not named in
`required_reads`, a fresh session at `component-adoption` is procedurally
barred from opening the only file that stage exists to produce. The same bug
hits `baseline-review`'s view of its predecessor.

The existing adoption test samples only `adoption-delivery`, whose predecessor
is `baseline-review`, so it steps over the one broken pair.

**Fix:** one word - make the two tables the same object.

### V3-12 - High - [reproduced] - `run context` breaks the universal envelope

**Where:** `cli.py:386-387` returns `build_stage_context(...)` verbatim.

`CLI_API_REFERENCE.md:30-42`: "Default output always begins: status / stage /
artifact / next … The four keys above are present on every response."

```
aegis run context --json  ->  'status' in payload = False,  'next' in payload = False
aegis run context         ->  prints  status: none   and   next: none
```

`_respond` falls back to `payload.get(key, 'none')`. `next: none` everywhere
else in AEGIS means the run is over, and `status: none` is not one of
`ok|blocked|failed`. This is the documented **first** command of every fresh
agent session (`AGENTS.md:47`, all three skill routers, `CLAUDE.md`), and a
JSON consumer doing `payload["status"]` gets a `KeyError`.

### V3-13 - High - [reported] - Stale `route_to` re-routes and re-waives

**Where:** `stage_forms.py:512` stores the whole `control` table in
`record.payload`; `:962` deep-copies it into the next prepared revision;
`:1699` renders it back into the regenerated form.

`route_to` is a transient directive, so it should not survive. Executed
sequence: implementation routes to design once (intended); after walking
forward, the regenerated `implementation.toml` **already contains**
`route_to = "design"`, `next_command` reports a plain `stage close` with no
warning, and the second close routes backwards again. Two `stage.routed`
events, unbounded.

The second consequence is worse than the loop: `close_stage:573-580` waives the
red/green evidence blockers *because* `route_to` is set, so implementation
closes with zero check evidence on every lap. A stale field silently re-arms an
integrity exemption a human approved once.

### V3-21 - Medium - [reproduced] - `report.md` says PASS when coverage is off

**Where:** `report.py:214-215`. `audit_coverage` returns `[]` when coverage is
disabled (`requirements.py:450-451`), so the report emits
`- PASS: live traceability and coverage audits have no findings.`

The shipped `template/.agentic/workflow.toml:47-48` sets `mode = "disabled"`,
so **this is the default for every newly scaffolded project**. On the same
repository, `aegis verify coverage` correctly answers
`audit_status: not-enforced`.

This contradicts `CLI_API_REFERENCE.md:388-390` ("Disabled groups are reported
`not-enforced`, never `passed`") and `cli.py:767-774`, whose docstring
documents fixing this exact defect - "could not tell 'nothing wrong' from
'switched off'". The fix landed on the CLI command but not on `report.md`,
which is the artifact a human reads to sign off delivery.

### V3-35 - Medium - [code-verified] - Shipped documents contradict the code

- `INVARIANTS.md:7-8,58` states INV-3 is always `not-applicable` on quick runs.
  `invariants.py:212-220` only collapses it when
  `red_green_policy == "legacy-not-applicable"`; new quick runs default to
  `required`, where INV-3 evaluates and can block. `CLI_API_REFERENCE.md:216`
  states it correctly, so the two shipped documents disagree with each other.
- `INVARIANTS.md:27` labels INV-7 `Non-waivable`. Every INV-7 result is built
  with `"blocking"` (`invariants.py:936,946,963,988`), and
  `CLI_API_REFERENCE.md:331-334` records the change. The JSON `policy` field an
  integrator keys off never equals the documented value.
- `CLI_API_REFERENCE.md:44-54`: three of nine "Additional response keys" rows
  are wrong. `waived_gates` is emitted by `verify gates`, not `verify run`;
  `readiness`/`waived_blockers` are not emitted on a blocked `stage close`;
  `run_profile`/`bypass_status`/`bypassed_stages` do not appear on
  `delivery report` and are nested inside `verification` on `verify run`.

### V3-27 - Medium - [reproduced] - A test that fails on ordinary local activity

**Where:** `tests/test_release_hygiene.py:153-165`
(`test_copied_template_contains_no_interpreter_cache_artifacts`) asserts the
live working tree contains no `__pycache__` under `template/`.

`conftest.py` sets `sys.dont_write_bytecode = True`, which protects the test
suite's *own* run and nothing else. Any other Python process that imports the
template - running the CLI locally, an IDE indexer, a coverage run, a different
interpreter - writes `.pyc` there and reddens the suite.

This was triggered twice **accidentally** during this review by two unrelated,
entirely ordinary actions. The `.pyc` files are gitignored, so `git status`
stays clean and they can never be committed; the risk the test guards is real
only for a verbatim directory copy, which is WAEGIS's job and which the
CHANGELOG already records WAEGIS handling. The test converts benign local state
into a red suite and points at nothing actionable.

---

## F. Remaining Medium and Low defects

| ID | Sev | Where | Defect |
| --- | --- | --- | --- |
| V3-18 | High | `config.py:1209-1221` | `impacted_command` is validated with **set** semantics, so a legal argv repeating a token (`-p no:cacheprovider -p no:randomly`) is rejected. `load_config` is the entry point for every command **and** every hook, so the workspace is unusable until the operator deletes the duplicate. Tokens are also silently `.strip()`ed. |
| V3-19 | High | `check_execution.py:383` | Managed-check log name is `{check.id}-{stage}.log` with no ordinal, so a rerun overwrites the log of the prior evidence record. In quick+`required` mode the failing record stays **active** as the red-before-green witness while its log now shows the passing output. `gates.py:204` already fixed this by folding the evidence ID into the name; `test_gates.py:640` documents the reasoning. |
| V3-20 | High | `gates.py:669-743` | On Windows, `subprocess.run(shell=True, capture_output=True, timeout=…)` kills only `cmd.exe`; surviving grandchildren hold the pipe, and CPython's post-timeout `communicate()` has **no timeout**, so `verify gates` can block forever instead of returning the documented exit-124 result. POSIX returns but leaks orphaned grandchildren (no process-group kill). |
| V3-22 | Med | `gates.py:630-666`, `invariants.py:617-627` | Disabling or editing a failing gate leaves its failure evidence active and unsupersedable. `gate_failure_blockers` skips non-`enforce` groups, so no waiver target exists, while INV-4 still sees the active failure and blocks. The summary simultaneously reports the gate `not-enforced` and its evidence blocking. Only exits are a coarse INV-4 waiver or abandoning the run. |
| V3-23 | Med | `config.py:693-717` | With `components.baseline_guard.mode = "enforce"`, the **config parser** reads and re-parses `.agentic/components.toml`. A typo there makes every command and every hook fail with a configuration error - including `run context` and `config validate`, the documented recovery route. `components.py:113-114` already loads the same file with the same exception set, so this layer's only added effect is the self-lock. |
| V3-24 | Med | `invariants.py:803` | INV-9 calls `audit_local_scope`, whose `CommandInputError` is caught nowhere (`grep "except CommandInputError"` returns zero hits). A malformed `components.toml` aborts the whole `evaluate()` pass, killing `verify invariants`, `verify run`, `delivery report`, stage close, and `waive list` - the escape hatch for that very blocker. The module docstring records this same class being fixed twice before, for INV-5 and the requirement register. |
| V3-28 | Med | `secret_scan.py:100,154` | The config-deadlock carve-out uses `endswith(".agentic/workflow.toml")`, so **any** nested path ending that way (e.g. `docs/.agentic/workflow.toml`) is an unscanned drop box. In `secret_scan` the carve-out fires on a *pattern match*, not only on a config-load failure, so it is reachable in a healthy repo. Same suffix shape in `guard_write_zone.py:63`, `guard_shell_write.py:336`, `guard_read_path.py:224`. |
| V3-29 | Med | `secret_scan.py:126-129` | Only **top-level** keys are stripped, so `MultiEdit`'s nested `edits[].old_string` is still scanned. The edit that *deletes* a hardcoded credential is denied while the file keeping it is left alone - exactly the failure the 2.1.0 fix at `secret_scan.py:19-25` was written for, still live for the batched form. `.claude/settings.json:5` keeps `MultiEdit` wired. |
| V3-30 | Med | `delivery_preflight.py:43,54` | Raw substring match on the normalized command. With `command_patterns = ["git push"]`, `git -c core.pager=cat push origin main` and `git --no-pager push` contain no `"git push"` substring, so preflight is skipped entirely - no verification, no delivery-closed check. |
| V3-31 | Med | `evidence_forms.py:93-99` | The guard is `record is None` only, but a terminal stage's record is `closed`, not absent, and there is no `graph.complete` check. Verified: `evidence prepare add` + `evidence apply` mutate and re-save the graph of a **finished** run and append to its journal after `run.completed`. `stage_forms.py:218-222` has the correct guard ("a closed run is never reopened"). |
| V3-32 | Med | `cli.py:1000-1003`, `repowise.py:146` | `_config_command` calls `effective_repowise_config` and `inspect_repowise` unconditionally, before branching on the action. One unknown key in the **optional, shipped-as-disabled** `integrations/repowise.toml` blocks `config validate` and `config show`, and the emitted `next` is the same failing command. No AEGIS or WAEGIS command can repair the file. |
| V3-33 | Med | `repowise.py:254` | `_derive_proposals` is called **outside** the `try/except RepoWiseIntegrationError`, and `_validate_knowledge_graph` checks only that `nodes`/`edges`/`layers` are lists, never element shapes. An externally produced graph with `tags = 7` raises `TypeError: argument of type 'int' is not iterable`, which `cli.py:225-233` does not catch. Also injects unvalidated `filePath` values (`['..', '/', 'C:']` observed) into the discovery record, does substring matching on a string `tags`, and iterates a string `entry_points` character by character. |
| V3-34 | Med | `repowise.py:300-345` | Same Git-root-relative bug as V3-15: `repo_root / candidate` never resolves, so **no file bytes are hashed** and the fingerprint reduces to the porcelain status text. Verified: nested layout `fp1 == fp2` is `True` after a content change (should be `False`); git-root layout correctly `False`. With `require_worktree_match = true`, stale evidence reports `current`. |
| V3-36 | Med | `_form_io.py:53-57` | `tomllib.load` decodes internally, so invalid UTF-8 raises `UnicodeDecodeError` - neither `OSError` nor `TOMLDecodeError`, so it bypasses the documented `StageOperationError` and reaches the user as a traceback. Realistic on Windows: any editor saving a hand-edited form as ANSI. Adding `UnicodeDecodeError` to the existing tuple is the whole fix. |
| V3-37 | Med | `persistence.py:155-156` | `mkdir`/`open` sit **outside** the `try` whose `except BaseException` releases `thread_lock`, so an `OSError` there leaves the process-global `RLock` held forever. A later caller burns the full timeout and is told "Another AEGIS process still holds the OS lock" while the lock file does not exist. |
| V3-38 | Med | `waiver_targets.py:66-74,121-132` | For audit-finding and working-tree blockers the state digest's first 12 chars are embedded in the blocker ID, so `"stale"` is reachable only on a 48-bit hash collision. A waiver whose target changes silently becomes `inactive` instead of `stale` - the exact regression `cli.py:588-591` says was fixed. Affects 3 of 5 blocker families. |
| V3-39 | Med | `cli.py:158` | `load_config` is hoisted above the `run list` and `run abandon` branches, though neither takes a config. An invalid `workflow.toml` disables both run-independent recovery commands, against their own docstrings ("the only exit a run has"). |
| V3-40 | Low | `working_tree.py:268-269` | Rename parsing splits on `" -> "` before unquoting, so a rename of a file whose name contains `" -> "` yields two wrong paths, and a quoted path can be split mid-string. POSIX-only (Windows forbids `>` in filenames). `repowise.py:308-317` already uses `-z`. |
| V3-41 | Low | `working_tree.py:235-249` | The only shipped Git call with **no timeout** (`repowise.py:696` and `invariants.py:1071/1096/1121` all use 30 s). A hung `git status` hangs `verify run` and the delivery preflight hook with no diagnostic. Also decodes with `errors="replace"`, so a non-UTF-8 filename becomes a path that exists nowhere and matches no pattern - the dodge its own docstring claims to have closed. |
| V3-42 | Low | `cli.py:1368-1374` | `verify impact --run <paths-file>` reinterprets the paths file as a run ID and reports `RUN-ID-NOT-FOUND` naming the wrong thing. Documented argument order works; the transposed order misleads. |
| V3-43 | Low | `report.py:277` | The only artifact writer using text-mode `write_text`: CRLF on Windows, LF on Linux, and non-atomic. `.agentic/runs/` is not gitignored and the template ships no `.gitattributes`, so a mixed-OS team gets whole-file diffs on `report.md`. |
| V3-44 | Low | `cli.py:1125` | `run abandon` emits `next: "aegis run start <kind>"` - a placeholder where the contract requires an exact command. An agent obeying `next` verbatim gets argparse exit 2. `_run_list` in the same situation emits a concrete command. |
| V3-45 | Low | `cli.py:1325-1326` | `_respond` renders Python's `None` rather than the `none` sentinel used everywhere else (e.g. `unavailable_current_artifact: None`). |
| V3-46 | Low | `cli.py:1306-1313` | `_respond`'s docstring claims one-line scalars, but `RunResolutionError.__str__` embeds newlines, so a blocked response emits unprefixed continuation lines - one of which a `": "`-splitting reader parses as a key/value pair. |
| V3-47 | Low | `components.py:270` | `adoption scope-check` passes user input straight to `audit_scope_check`; `repo_root / "C:/Windows/win.ini"` discards the left operand, so absolute paths outside the repo are stat'ed. Advisory output only, but `paths.relative_to_root` exists for this boundary. |
| V3-48 | Low | `stage_forms.py:2101` | Every `adoption-alignment` error names `alignment.toml` instead of `adoption-alignment.toml`. |
| V3-49 | Low | `stage_schema.py:239-241,295-297` | `access_mode` is a closed token set shipped with **no** `accepted` list, though every other closed field carries one and `StageFieldSpec`'s docstring says that is what `accepted` is for. An agent writing `repo_wide` loses a stage close to a guessable typo. |
| V3-50 | Low | `stage_schema.py:315-317` | The `component-map` form hard-codes `manifest = ".agentic/components.toml"`, ignoring the configurable `components.manifest`, and nothing ever reads the field back. It both misdirects the agent and is write-only. |
| V3-51 | Low | `stage_schema.py:311-312` | `repo_discovery`'s `repowise_status`/`repowise_warnings` are agent-writable but `stage_forms.py:2518-2519` unconditionally overwrites them on every apply. |
| V3-52 | Low | `config.py:1021-1028` | A **disabled** guardrail must have empty rule lists, which is documented nowhere and is the exact opposite of the gate rule ("Disabled groups may retain commands"). Flipping `mode` to `"disabled"` to unblock a run is refused until every regex is deleted. |
| V3-53 | Low | `paths.py:184-201` | `validate_glob` rejects `[[]`, fnmatch's only escape for a literal `[`, so a path containing `[` can never be protected, excluded, or zoned. Compounds V3-10. |
| V3-54 | Low | `requirements.py:631-635` | Extension matching is case-sensitive on every platform while `matches_pattern` case-folds on Windows, so `Helper.PY` is silently excluded from the coverable set and escapes coverage enforcement with no finding. |
| V3-55 | Low | `store.py:281-288`, `:767` | A colliding run ID (same UTC second **and** a 32-bit `uuid4` clash) overwrites the existing run silently, because `mkdir(exist_ok=True)` and the compare-and-swap is skipped for a freshly constructed graph. Probability is tiny; the consequence is unrecoverable loss. `exist_ok=False` converts it to a clean failure. |
| V3-56 | Low | `persistence.py:259-263` | Temp files are created as siblings inside the git-tracked `.agentic/runs/<id>/`; a `SIGKILL` between `mkstemp` and `os.replace` leaves them permanently, nothing sweeps them, and `template/.gitignore` has no rule, so they can be committed. |
| V3-57 | Low | `persistence.py:272-275` | `os.umask(0)` then restore, to *read* the umask, is not thread-safe and briefly makes the whole process create world-writable files. POSIX only. |
| V3-58 | Low | `tools/local_model_pilot.py:690-691` | `verify run` is invoked with `allow_failure=True` and then indexed unconditionally; the resulting `KeyError` is outside every handler, so the pilot loses **all** accumulated evidence and its `TemporaryDirectory` deletes the repos. Moot if the tool is deleted - see `02_SIMPLIFICATION.md`. |
| V3-59 | Low | `template/.agentic/tools/run.ps1:21-23` | `AEGIS_PYTHON` is not trimmed, though `run.sh:32-42` trims and its comment claims parity with "the Node and PowerShell launchers". A value with surrounding whitespace works under bash and fails under PowerShell. |
| V3-60 | Low | `run.ps1:8-11` | The parameter is named `$Args`, shadowing the automatic variable. Verified harmless for AEGIS's actual flags (all double-dash), but any single-dash `-a…` argument binds to the parameter and fails with "A positional parameter cannot be found". |

---

## Not defects - checked and cleared

Recorded so the same ground is not re-covered:

- **Form parsing is robust.** Seven adversarial `stage apply` inputs -
  malformed TOML, wrong scalar types, a list field given a string, a missing
  table, a duplicate key, a 20,000-element array, and unicode/emoji/tab content
  - all produced clean typed errors with exit 1 and no traceback.
- **Corrupt run state is handled** for the realistic cases: truncated, empty
  and wrong-schema `graph.json` all yield a clean `RUN-POINTER-STALE`. Only the
  non-object JSON case (V3-09) escapes.
- **Concurrency holds.** Eight concurrent `run status` and six concurrent
  `verify run` processes completed with no traceback and left a 44-line journal
  with zero corrupt records. Locking is reentrant and acquisition order is
  consistent (run lock, then journal lock) at every call site.
- **`Graph.to_dict`/`from_dict` round-trips losslessly**, including every
  optional-by-absence key (`profile`, `waivers`, `outcome`).
- **Waivers have no expiry field**, so there is no date-comparison bug class to
  find. Requirement IDs use UUID4 plus `O_EXCL`/`os.link` exclusive
  publication - no sequence numbers, no off-by-one.
- **Adapter skill files are thin ~1 KB pointers** to the canonical
  `.agentic/skills/` procedure, not copies. Correct design; no drift risk.
- **Delivery pattern normalization agrees** byte-for-byte between
  `config.py:1011` and `delivery_preflight.py:43`.
- **Symlinks are handled correctly** by the write guard - `relative_to_root`
  resolves before judging. Quoted, spaced, `>>`, `&>`, `1>`, `sed -i`, `dd of=`,
  env-var prefixes, `&&` chaining and `{ …; }` grouping all extract correctly.
- **The 39-command CLI surface matches `CLI_API_REFERENCE.md` exactly** - no
  undocumented or unimplemented command.
- **All version declarations agree at 3.0.0** across the four required files.
