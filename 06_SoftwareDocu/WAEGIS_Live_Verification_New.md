<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS Live Verification — `waegis new` (task T4.4, milestone M4)

> Date: 2026-07-13.
> Scope: 00_Planning/WAEGIS_Wizard_Implementation_Plan.md §13 task T4.4 and
> §16 definition of done, items 1–4 (new-project journey only).

## What was run

`waegis new TARGET` was run for real — no `--answers` file, no fake
`CommandRunner`/asker — against a real empty target directory on this
machine, using the real console frontend (`ConsoleAsker` over real
stdin/stdout pipes) and the real repo-checkout payload at
`05_Software/aegis/template/` (auto-resolved by `locate_payload`; no
`--payload` override was needed).

Because this session has no attached human keyboard, the interactive session
was driven by a small throwaway script
(`drive_waegis_new.py`, not part of the repository) that spawns
`uv run python -m waegis new TARGET` as a real subprocess and answers each
prompt as it actually appears, reading output byte-by-byte and treating a
sustained pause as "the process is now blocked on `stdin.readline()`" — the
standard way to drive an interactive console program without a human
present. This exercises the exact same `ConsoleAsker`/`io/console.py` code
path a human would hit (prompt rendering, re-prompt-on-invalid, encoding,
launcher resolution, `run.ps1` execution) — it is not the `--answers`/
`ScriptedAsker` path. One run additionally typed a real (non-default) answer
at a specific prompt to probe the FieldSpec validators under console input,
as detailed below.

## Operating system(s)

- **Windows 11** (this machine): fully verified, four separate real runs
  (below).
- **Ubuntu 22.04 / WSL**: **not available in this session** — no WSL Ubuntu
  22 environment or VM was accessible. `run.sh`/`bash`-path verification is
  **not verified** and remains open. (§13 T4.4 calls for both OSes; this
  report closes the Windows half only.)

## Runs performed

1. **Fresh run, accept every default.** Empty target directory, no prior
   WAEGIS home. Answered every prompt with Enter (accept the detected
   default): plan preview approved, `git init -b main`, payload copy,
   `workflow.toml` interview (`source_roots=["src"]`, `test_roots=["tests"]`,
   `language="python"`, both gates empty, `alignment_enabled=True`), create
   missing `src`/`tests` roots with `.gitkeep`, accept both empty gates,
   commit, handoff. **Result: exit 0, all 16 steps green.**
2. **Re-run against the same TARGET (same WAEGIS home/journal).** Verifies
   the resume guarantee: every one of the 16 steps reported
   `resumed from prior journal (already green)` and was skipped without
   re-invoking `act`. **Result: exit 0, nothing re-executed.**
3. **Re-run against the same TARGET with a *fresh* `WAEGIS_HOME`** (no prior
   journal to resume from — forces every step's own `detect()` to run for
   real against the actual filesystem/git state, not the journal seed).
   Every step that defines a `detect()` correctly recognized the
   already-completed state and was skipped
   (`home.init`, `machine.os`/`machine.disk` info-only, `prereq.python`,
   `prereq.git`, `prereq.git-identity`, `repo.target-path`,
   `repo.init-or-clone`, `deploy.payload-copy`, `deploy.workflow-toml`,
   `verify.hooks-present`, `repo.initial-commit`). The four steps that have
   no `detect()` by design (`deploy.gates`, `verify.cli-smoke`,
   `verify.workflow-smoke`, `handoff.summary` — always-repeatable
   reporting/smoke steps) re-ran harmlessly with no side effects and no
   errors. **Result: exit 0.** This is the deeper, journal-independent half
   of the detect→skip guarantee and is the main reason this task calls for
   a *real* filesystem/git test rather than trusting the offline fakes.
4. **Targeted validator probe.** A live regression (below) was found by
   attempting to type a real, non-default `gate_test_cmds` answer at the
   console prompt.

## What was inspected on the target after run 1

- `.agentic/` copied (114 files retained under `files` in the manifest, 1
  moved to `generated`); `.claude/`, `.codex/`, `.pi/`, `.opencode/`,
  `.qwen/` adapter dirs present; `AGENTS.md`/`CLAUDE.md`/`QWEN.md`/
  `opencode.json`/`CHANGELOG.md` present.
- `.agentic/install-manifest.json`: `manifest_version=1`,
  `payload_version="0.4.0"`, `mode="new"`, `generated=[".agentic/workflow.toml"]`,
  114 files hashed.
- `.agentic/workflow.toml`: re-parsed with `tomllib` and re-checked with the
  real `verify_workflow_invariants` — holds. `write_zones.implementation`
  contains `src/**` and `.agentic/knowledge/components/**`;
  `write_zones.check`/`component-adoption` contain `tests/**`.
- `git log --oneline`: one commit, `"Bootstrap AEGIS via WAEGIS 0.1.0"`;
  `git status --porcelain` empty.
- Handoff message: named the exact first fenced prompt from the copied
  `.agentic/documents/PROMPT_CHEATSHEET.md` ("Use the agentic development
  workflow installed in this repository. Read AGENTS.md and
  .agentic/workflow.toml. ...") — confirmed byte-identical to the shipped
  file, not a hardcoded string.

## What broke, and what was fixed

**Console encoding / launcher resolution / PowerShell execution policy:**
none of these broke. `run.ps1` was invoked exactly as
`powershell -NoProfile -ExecutionPolicy Bypass -File <path> --help` /
`... status`, both exits were correct (`--help` → 0, `status` → 1 on a
fresh install, recognized as the healthy "No active agentic run" outcome).
No mojibake or unencodable glyphs appeared: `io/console.py` only uses its
richer Unicode glyph set when a caller opts in with `use_glyphs=True`, and
`commands/new.py` never does today, so the wizard always renders the plain
`[OK]`/`[SKIP]`/`[..]` ASCII markers — this is a deliberate, already-correct
design, not a gap.

**One real defect found and fixed** — `deploy.workflow-toml`'s gate-command
prompt was practically unusable for a real console operator:

- **Symptom.** `normalize_gate_commands` (in
  `05_Software/waegis/src/waegis/repo/workflow_toml.py`) rejected *any*
  `str` value outright — but `ConsoleAsker.ask_field` (and a plain-text
  answers file) can only ever hand the validator a `str`. Typing the
  prompt's own printed example, `[["uv", "run", "pytest", "-q"]]`, at the
  `gate_test_cmds`/`gate_lint_cmds` console prompt failed validation and
  `ConsoleAsker` re-prompted — forever, since no string answer could ever
  pass. The *only* way through the prompt interactively was to press Enter
  and accept the empty `[]` default. This was confirmed live (typing the
  example text at the real prompt produced the rejection message and looped)
  and reproduced directly:
  `normalize_gate_commands('[["python", "--version"]]')` raised
  `ValueError` before the fix.
- **Fix.** `normalize_gate_commands` now parses a `str` answer as JSON
  first, then applies the existing list-of-argv-lists validation
  unchanged. A flat list (`["pytest", "-q"]`) is still rejected as
  ambiguous (same as before); malformed JSON re-prompts with a corrected,
  parseable example. Minimal, targeted change — no other behavior in the
  generator was touched.
- **Regression tests added**
  (`05_Software/waegis/tests/test_repo_workflow_toml.py`):
  `test_gate_commands_console_string_is_parsed_as_json` (direct validator
  unit test: valid JSON string accepted, malformed JSON and the
  already-covered flat-list case still rejected) and
  `test_console_asker_accepts_typed_gate_command_on_first_try` (drives a
  real `ConsoleAsker` over injected `io.StringIO` streams with the exact
  prompt example as input and asserts it is accepted with no rejection
  text) — the second test is the one that would have caught this offline,
  since it exercises the same `ConsoleAsker.ask_field` call path a live
  operator uses.

No other breakage surfaced across all four runs: git identity (already
configured globally on this machine), Python/`py -3` launcher resolution,
disk-space probe, nested-work-tree check, manifest read/write, `.gitkeep`
root creation, and the initial commit all worked on the first try.

## What remains unverified

- **Ubuntu 22 / `run.sh` path** — not tested in this session (no WSL Ubuntu
  22 or VM access). The `bash`-invocation branch of `_wrapper_invocation`
  (`commands/new.py`), the `run.sh` `set -euo pipefail`/`BASH_SOURCE`
  behavior, and any POSIX path-quoting differences remain unverified against
  a real filesystem/git state. This is the one open item against §13 T4.4's
  "Windows 11 machine and ... Ubuntu 22" requirement.
- **`clone_url` / `net.proxy` path** — every run above created a local
  repository (`git init`); the remote-clone branch (`repo.init-or-clone`
  cloning a URL, and the `net.proxy` step it gates) was not exercised live
  in this session.
- **Non-default interview answers driven fully end-to-end** — the targeted
  validator probe above proves the gate-command fix at the `ConsoleAsker`
  layer directly (offline, deterministic); a fully-driven live session that
  types a non-default answer at exactly the right prompt in a real
  subprocess turned out to be flaky in the throwaway driver script itself
  (idle-timing heuristics misaligning with which prompt is "current" when
  responses arrive close together) — this is a limitation of the ad hoc
  driver, not of the wizard, and was not worth hardening further once the
  fix was proven directly.

## Validation

`uv run --group dev python -m pytest -q tests` (in `05_Software/waegis`):
**282 passed** (280 pre-existing + 2 new regression tests), including the
two `integration`-marked real-payload/real-git end-to-end tests from T4.3.
