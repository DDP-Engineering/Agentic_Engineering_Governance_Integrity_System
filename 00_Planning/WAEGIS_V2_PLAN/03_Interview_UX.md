Applied to WAEGIS V1 in batch 17 (2026-07-31); V2 Phase 2 inherits this catalog and the V1 wording as its starting point.

# WAEGIS V2 — Interview UX Specification

## 1. The principle

Every interview question must be answerable by a normal developer **without reading the glossary**. The template is:

```
<Plain question>? [choices / Y/n] (default: <safe default>)
  -> <one sentence: what enabling/answering this actually DOES, in consequence terms>
  e.g. <a realistic example answer>
```

Rules: one concept per question; the consequence sentence names the *behavioral effect on the agent/developer*, never the config key; defaults are the ship-open defaults (everything restrictive starts disabled/unrestricted); pressing Enter always takes the shown default; analysis proposals are shown inline as the default where available ("detected from package.json"). The machinery: `interview.py` renders these from the harvested `FieldSpec`s — the specs gain a `consequence` text field; keys, choices, validators, and answers-file compatibility are unchanged.

## 2. The question catalog (authoritative draft)

### Project basics

- **Which language is this project mainly written in?** [python/javascript/typescript/java/c/cpp/rust/go/other] (default: detected — e.g. "python, detected from 214 .py files and pyproject.toml")
  -> Selects conventions for where source and tests usually live and how test references are checked; nothing language-specific is installed.
- *(if other)* **File extension of your source files?** / **How is a single test referenced in your test runner?**
  -> Lets the traceability check resolve "this requirement is covered by that test" for a language it has no preset for. e.g. `.zig`, `test_file::test_name`
- **Where does your source code live?** (default: proposed — e.g. `src`)
  -> Folders the workflow treats as production code: coverage checks, scope advisories, and write restrictions (if you enable them below) apply here.
- **Where do your tests live?** (default: proposed — e.g. `tests`)
  -> Folders where linked tests are looked up when checking that requirements are covered.

### Quality gates (one block per gate: build, typecheck, lint, test, security)

- **Enable the <name> gate? [Y/n]** (default: n — all gates start disabled)
  -> When enabled, `aegis verify run` executes the commands below and a failure blocks validation until fixed or explicitly waived with a recorded reason. When disabled, reports honestly say "disabled" — never "passed".
- **Command(s) for the <name> gate?** (default: proposed with provenance — e.g. `npm test` — detected from package.json scripts.test)
  -> Run exactly as given, from the repo root. Multiple commands run in order; the first failure fails the gate.

### Guardrails — each starts with the same shape of question

- **Scan for secrets before validation? [Y/n]** (default: n)
  -> When enabled, changed and new files are scanned against the patterns below; a match blocks validation (waivable with a recorded reason). e.g. pattern: `AKIA[0-9A-Z]{16}` for AWS keys.
- **Protect specific paths from modification? [Y/n]** (default: n)
  -> When enabled, changes to matching paths (e.g. `migrations/**`, `LICENSE.txt`) are flagged as blocking findings in the working-tree review — useful for files an agent should never touch.
- **Block suspicious working-tree patterns? [Y/n]** (default: n)
  -> When enabled, files matching the patterns (e.g. `*.env`, `credentials*`) appearing in the diff block validation until reviewed.
- **Restrict which folders may be written during each stage? [Y/n]** (default: n — unrestricted)
  -> When enabled, the agent hooks deny writes outside the allowed folders for the current stage — e.g. during the check stage the agent may write only under `tests/`, which prevents it from editing source code just to make its own test cases pass.
- **Advise when a run touches files outside its declared scope? [Y/n]** (default: n)
  -> When enabled, changes outside the run's planned paths produce an advisory (never a block) so scope creep is visible at close time.
- **Guard outward delivery commands? [Y/n]** (default: n)
  -> When enabled, shell commands matching the patterns (e.g. `git push*`, `gh pr create*`) are blocked by the hooks until the delivery stage's preflight has passed — the agent cannot push before the workflow is complete.

### Traceability and components

- **Enforce requirement coverage for source files? [Y/n]** (default: n)
  -> When enabled, every file under the coverable roots must be touched by at least one Active requirement with a resolvable test, or be listed in the waiver file; missing coverage blocks validation. Start disabled and enable once your requirement register is populated.
- **Enforce a component baseline before behavior changes? [Y/n]** (default: n)
  -> When enabled, behavior-changing runs may only touch components whose documented completion level meets the minimum you set — protects poorly-understood legacy components from casual modification.
- **Allow adoption runs to modify source files? [allow/forbid]** (default: forbid)
  -> Adoption runs document existing behavior; forbidding source changes guarantees they cannot alter it.

### Workflow interface

- **Keep, version, or discard stage forms after import? [versioned/latest/discard]** (default: versioned)
  -> versioned keeps every revision under the run folder (full audit trail); latest keeps only the newest; discard deletes forms after import (leanest repo).
- **Who executes check commands? [external/managed]** (default: external)
  -> external: the agent runs the commands and records results (works in any environment); managed: the AEGIS CLI executes them itself (stronger evidence, requires commands runnable from the CLI's environment).
- **Advise when a quick run grows too large? [Y/n]** (default: n)
  -> When enabled, a quick (proportional) run touching more than N files gets an advisory suggesting a full run — never a block. (default N: 10)

### Adopt-specific

- **Per-file conflict decisions** — for each payload file that already exists and differs: **keep yours / take payload / write payload beside yours as `.new`** (asked per file, or supplied via the answers file as `adoption_conflicts`).
  -> Nothing you own is ever silently overwritten.
- **Commit the installed workflow now? [Y/n]** (default: Y)
  -> Creates one commit containing only the AEGIS payload and generated config, keeping the install separable from your own changes.

### RepoWise (only in Complete edition / Phase 7)

- **Install the bundled offline RepoWise index? [Y/n]** (default: n)
  -> Adds a local structural index some agents use for repository discovery; fully offline; ~<size> on disk. Can be linked to an external RepoWise instead, or skipped entirely.

## 3. Acceptance criteria for this document's implementation

- Every `FieldSpec` in the harvested set has a `consequence` line and (where meaningful) an `example`, rendered exactly in the §1 template.
- A user pressing Enter through the entire `adopt` interview on a detected-language repo gets: all gates disabled, all guardrails off, proposed roots accepted — a working install with zero restrictive policy, matching V1's ship-open defaults.
- `--answers` files created for V1 still satisfy the interview with no changes (keys and accepted values unchanged).
- The rendered question text is covered by a golden transcript test (like the V1 upgrade consent golden test).
