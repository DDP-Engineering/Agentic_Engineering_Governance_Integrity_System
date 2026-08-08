# WAEGIS V2 — Interview UX Specification

**Baseline:** V1's `FieldSpec` already provides plain questions, descriptions,
examples, choices, defaults, and validators. V2 harvests that data model and the
useful wording, but changes the ordering and asks dependent details only when
their controlling feature is enabled. The catalog below, not V1's tuple order,
is authoritative for V2.

## 1. Interaction rules

Each question renders as:

```text
<plain question> [choices] (default: <value and proposal provenance>)
  → <one sentence describing the behavioral consequence>
  e.g. <realistic answer, when useful>
```

Rules:

- one decision per question;
- consequence wording describes what AEGIS or the operator will do, not the
  TOML key name;
- Enter selects exactly the displayed default;
- restrictive policy defaults to disabled/unrestricted;
- a proposal never masquerades as a fact: show its evidence, such as
  `npm test (package.json scripts.test)`;
- dependent rule lists, commands, thresholds, and stage maps are asked only
  when their controlling mode uses them;
- `--non-interactive` and `--json` never prompt and return code 3 with all
  missing keys in one response;
- `--yes` approves a fully resolved rendered mutation plan; it never invents
  missing answers or conflict decisions;
- answers files use a closed, versioned V2 schema and reject duplicate or
  unknown keys by default (an explicit future migration may add a warning mode);
- no question asks WAEGIS to create a branch or commit.

## 2. Project basics

- **Which language is this project mainly written in?**
  `[python/javascript/typescript/java/c/cpp/rust/go/other]`
  (default: detected with provenance, otherwise `python`)
  → Selects source extensions and linked-test conventions; it installs no
  language-specific tooling.
- **Where does your source code live?** (default: detected, otherwise `src`)
  → These roots define production code for coverage, scope, and write policy.
- **Where do your tests live?** (default: detected, otherwise `tests`)
  → AEGIS resolves linked tests beneath these roots.
- *(only for `other`)* **Which source-file extensions should AEGIS recognize?**
  → Supplies traceability extensions that the built-in presets do not know.
  e.g. `.zig, .zon`
- *(only for `other`)* **Which file-name patterns identify tests?**
  → Lets requirement links resolve tests for the custom language.
  e.g. `*_test.zig`

## 3. Alignment and workflow interface

- **Record intent alignment before requirement and design work? [Y/n]**
  (default: Y, matching the payload template)
  → When enabled, a run records approved intent before downstream engineering
  work proceeds.
- **Require protected-scope patterns in alignment? [y/N]** (default: N)
  → Records and validates protected scope for alignment. The current payload
  does not yet enforce those patterns at runtime, so the interview must state
  that limitation.
- *(only when protected scope is enabled)* **Which path globs form that scope?**
  e.g. `infra/**`
- **Keep, version, or discard stage forms after import?**
  `[versioned/latest/discard]` (default: `latest`)
  → `latest` retains the final small handoff form, `versioned` retains every
  revision, and `discard` removes imported forms.
- **Who executes check commands? [external/managed]** (default: `external`)
  → External lets an agent run and import evidence in any environment; managed
  lets AEGIS execute the command itself.

The remaining alignment settings—pause on open questions, risk threshold, and
recommended-response policy—come from the payload template and are preserved
byte-for-byte unless the operator edits them directly.

## 4. Quality gates

For each of `build`, `typecheck`, `lint`, `test`, and `security`:

- **Enable the <name> gate? [y/N]** (default: N)
  → When enforced, `aegis verify run` executes its commands and a failure blocks
  validation until fixed or explicitly waived; disabled is reported as
  disabled, never passed.
- *(only when enabled)* **Which command(s) run the <name> gate?**
  (default: evidence-backed proposal when one exists; otherwise required)
  → Commands run from the repository root in order; the first failure fails the
  gate.

Gate timeouts and `[gates.test].impacted_command` are advanced operator-owned
values. Configure preserves them byte-for-byte and the bundled AEGIS CLI
validates them.

## 5. Guardrails

- **Scan for secrets before validation? [y/N]** (default: N)
  → When enabled, matching tool input is blocked live and the working tree is
  scanned again at validation.
- *(only when enabled)* **Which Python regular expressions identify secrets?**
- **Protect specific paths from reads or writes? [y/N]** (default: N)
  → Matching hook operations are denied and matching working-tree changes are
  blocking findings.
- *(only when enabled)* **Which path globs are protected?**
- *(only when enabled)* **Protect reads, writes, or both?**
- **Block suspicious working-tree patterns? [y/N]** (default: N)
  → Matching files in the working tree block validation until reviewed.
- *(only when enabled)* **Which path globs are blocked?**
- **Restrict writes by workflow stage? [y/N]** (default: N)
  → Hooks deny writes outside the selected stage's allowed folders.
- *(only when enabled)* **Which globs may each stage write?**
  → Every stage is listed; an empty list makes that stage read-only.
- **Check paths against the run's declared scope?**
  `[unrestricted/advisory/enforce]` (default: `unrestricted`)
  → Advisory reports scope creep; enforce blocks it.
- *(only for advisory/enforce)* **Which roots are allowed?**
- **Guard outward delivery commands? [y/N]** (default: N)
  → Matching commands are denied until deterministic verification and delivery
  preflight succeed.
- *(only when enabled)* **Which lowercase command fragments count as delivery?**
  e.g. `git push`, not a glob such as `git push*`

## 6. Traceability, components, adoption, and quick runs

- **Enforce requirement coverage for source files? [y/N]** (default: N)
  → Files under covered roots need an Active requirement with a resolvable test
  or an explicit coverage waiver.
- *(only when enabled)* **Which roots require coverage?**
- *(only when enabled)* **Which globs are excluded?**
- **Enforce a component baseline before behavior changes? [y/N]**
  (default: N)
  → Behavior-changing runs may touch only components documented to the selected
  minimum level.
- *(only when enabled)* **What minimum completion level is required?**
  `[unknown/discovered/characterized/baseline-usable/baseline-strict]`
  (default: `baseline-usable`)
- **Allow adoption runs to modify application source? [Y/n]**
  (default: Y / `unrestricted`, matching the payload template)
  → `blocked` guarantees adoption cannot deliver application-source changes;
  `unrestricted` adds no such restriction.
- **Advise when a quick run touches too many paths? [y/N]** (default: N)
  → When enabled, an above-threshold quick run recommends a full run but never
  blocks work.
- *(only when enabled)* **How many changed paths trigger the advice?**
  (default: 10; positive integer)

Disabled quick advice omits the active `[quick.changed_paths]` table for a new
configuration. Configure may explicitly add or remove that table while
preserving surrounding comments and advanced operator-authored fields.

## 7. Conflict and migration questions

For every existing payload destination whose bytes differ:

- **Keep local** — leave the destination untouched and record it as
  `kept-local`;
- **Take payload** — replace it after the full recovery plan is shown and record
  the resulting ownership class;
- **Write sidecar** — preserve the destination and write payload bytes to a
  collision-free review path recorded as `sidecar`.

There is no global "take all" default. Answers files may resolve paths exactly;
unknown, missing, duplicate, case-colliding, or stale path decisions return
needs-input. Sidecar naming is deterministic and never overwrites an existing
path.

When a V1 manifest is minimally detected, V2 asks one additional migration
consent after explaining that V1 ownership metadata is not trusted and every
differing destination will use the ordinary conflict rules.

## 8. Acceptance criteria

- A golden transcript covers interactive order, conditional skips, proposal
  provenance, defaults, validation retries, and the V1 warning.
- Pressing Enter through an ordinary detected-language adoption yields all
  gates and restrictive guardrails disabled, adoption source changes
  unrestricted, alignment enabled, form retention `latest`, external check
  execution, and quick advice absent.
- No disabled feature asks for its unused command/rules/threshold.
- Every accepted interview produces a complete config that the bundled
  `config validate --json` accepts.
- Non-interactive and JSON invocations write no prompt text and report every
  missing answer/conflict in one response.
- Conflict transcripts prove no existing differing file is overwritten without
  a path-specific resolution and final plan consent.
