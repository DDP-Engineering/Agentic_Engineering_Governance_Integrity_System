<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Light — install and setup

Five minutes, three steps, no wizard, no hooks. AEGIS Light never blocks
your agent: it gives it a workflow to read and a small CLI that scaffolds
files and reports findings.

## What you need

- Python 3.11 or newer on PATH (`python` on Windows, usually `python3`
  on Linux — the examples below use `python`).
- git (recommended; without it the diff-based checks politely skip
  themselves and everything else still works).
- Any coding agent: Claude Code, Codex CLI, Qwen Code, OpenCode, or a
  local model harness. Online or offline — both are first-class.

## Step 1 — copy one folder

Copy the payload folder `template/.agentic/` from the AEGIS Light
release into the root of your repository, so you have `<repo>/.agentic/`.

## Step 2 — run init

```bash
python .agentic/aegis.py init
```

This finishes the installation, idempotently:

- creates the data folders (`requirements/`, `specs/`, `tasks/`,
  `knowledge/`),
- writes a default `.agentic/aegis.toml` — **only if absent**; an
  existing one is never touched,
- creates or appends the root pointer files `AGENTS.md`, `CLAUDE.md`,
  `QWEN.md` (a short digest under markers; your existing content in
  those files is preserved).

Commit the result. Running `init` again changes nothing.

## Step 3 — tell the config about your project

Open `.agentic/aegis.toml` and set the three keys that matter:

```toml
[commands]
test = "pytest -q"                    # how to run your test suite
test_impacted = "pytest -q {tests}"   # optional: focused regression

[layout]
source = ["src/"]                     # where your production code lives
tests  = ["tests/"]                   # where your tests live
```

If your application lives in a subfolder rather than at the repository
root, add one more line and let AEGIS Light handle the rest:

```toml
[commands]
workdir = "app"                       # run commands here, not at the root
```

Do not put a directory change inside the commands themselves. AEGIS Light
substitutes repository-relative test paths into `test_impacted`, so a
command that moves itself would resolve those paths a second time and find
nothing. With `workdir` set, the paths are rewritten to match.

Nothing limits how long a command may run. If you want a limit — a hung
linter, a CI budget — ask for one per command:

```toml
[timeouts]
test = 5400                           # seconds; this command only
lint = 120
```

A command stopped by its limit is reported as having proved nothing, which
is different from a suite that ran and failed.

Everything else in the file is optional tuning and can wait.

## First contact

Tell your agent:

```
using aegis workflow, implement feature <what you want>
```

The agent reads the workflow from `AGENTS.md`, opens a task journal, and
walks the stages. Check where things stand at any time with:

```bash
python .agentic/aegis.py status
```

`status` lists **open** tasks; delivered ones (`stage: done`) are hidden
with a count — add `--all` to see them too.

and get the advisory findings report with:

```bash
python .agentic/aegis.py check
```

`check` always exits 0 — it informs, it never blocks.

## Upgrade, undo, uninstall

- **Upgrade:** copy the newer payload-owned files over (`AGENTS.md`,
  `steps/`, `templates/`, `aegis.py`, `LICENSE.txt`), review `git diff`,
  commit. Your data folders and `aegis.toml` are never part of the
  payload, so they are never overwritten.
- **Undo anything:** `git restore` / revert the commit. Git is the
  safety net; AEGIS Light has no state outside the repo.
- **Uninstall:** delete `.agentic/` and the marked blocks in the root
  pointer files. Nothing else was touched.
