# AEGIS 0.16.0 repository review - 2026-11-17 (commit 77f404a)

| | |
|---|---|
| Review date | 2026-11-17 |
| AEGIS version | 0.16.0 (`VERSION` in `05_Software/aegis/template/.agentic/aegis.py`) |
| Commit | `77f404a5753cf49a5383864aa831b33d231e78f1` on `master`, clean working tree |
| Type | Read-only review with Claude Code; no repository file was changed by it |

This is a dated snapshot. Line numbers refer to the commit above. It does not
describe current behavior once the findings are addressed.

## Summary

- **Secrets:** no real credential in the tracked tree or in any reachable
  commit. Personal and machine-local data is present in a few places, and one
  pushed branch carries session transcripts of another private project.
- **Code:** ten findings. Five are defects in `aegis.py` reproduced in a
  temporary repository; the most serious is a secret scan that silently sees
  nothing under two ordinary Git settings.
- **Documentation:** one error that makes a documented command fail, eleven
  misleading statements and about fifteen minor ones.
- **Repository and delivery records:** the 0.16.0 host packages are not
  reproducible from the commit, most of a delivery has no tracked build
  procedure, and several records contradict each other.
- **Validation:** 521 tests passed, 2 skipped.

## Scope and method

Reviewed: `05_Software/aegis/` (payload CLI, templates, five host
integrations, tests, evaluation records), `02_Tools/`, all Markdown under
`00_Planning/`, `01_Documentation/`, `06_SoftwareDocu/` and the root, the
delivery records under `07_Delivery/`, and the Git history.

- `aegis.py` (4,927 lines) and every integration source file were read in
  full. Evaluation runners in `02_Tools/` were searched for risky constructs
  and read in part.
- Candidate defects in `aegis.py` were reproduced by running a copy of the
  payload in a temporary repository outside this one.
- Documentation was compared with the argument parser, `--help` output and
  the source. Delivery and baseline hashes were recomputed.
- The secret scan covered the 361 tracked files, all 196 commits on every
  local ref, the 13 tracked `evidence.zip` archives, 16 evidence archives and
  one 7z archive that exist only in history, and PPTX, PDF and PNG metadata.

Statuses used below: **reproduced** (observed by running it), **read**
(established from the source or the file), **deduced** (follows from the code,
not run).

## Secrets and sensitive data

### Result

No credential was found. Every token-shaped match is a fixture or a
placeholder: the fake AWS-style key and password literal in
`05_Software/aegis/tests/test_check.py` (they test the secret scanner), a
sample JWT inside third-party test code in the historic 7z archive, a
placeholder local-model API key, and lists of environment variable names in
recorded CLI events.

### Personal and machine-local data

| What | Where | Severity |
|---|---|---|
| Session transcripts of another private project (its name, its remote URL, user-profile paths) and about 61 MB of third-party `node_modules` | `01_Documentation/LocalModelsTests.7z`, added in commit `180bd50` on `origin/ddp/codegraph-plugin-plan` | medium |
| Codex project configuration without sandbox or approvals: `sandbox_mode = "danger-full-access"`, `approval_policy = "never"`, network access on | `.codex/config.toml` (tracked) | medium |
| Windows user-profile paths | `manifest.json` of the seven subscription baselines; `host.json` and `cli-command.json` inside their `evidence.zip`; `D:\...` paths in `07_Delivery/aegis-0.14.0/delivery-manifest.json` | low |
| A LAN address of the local model server | `manifest.json` of the six Qwen baselines (`base_url`) | low |
| A personal e-mail address | `LICENSE.txt` and the payload copy (intended licensing contact); author and committer of every commit | informational |

Notes:

- The 7z archive contradicts its own `TEST_ENVIRONMENT.md`, which says the
  target repository is described "by its properties rather than its name" so
  the material can be used externally. The transcripts name it thousands of
  times. This matters only if the remote becomes reachable by someone else;
  the branch would then have to be rewritten or deleted.
- The user-profile paths enter the evidence through
  `02_Tools/evaluate_aegis_subscription.py:69-94`, which records absolute
  paths in `host.json` and `cli-command.json`.
- Nineteen local `refs/codex/snapshots/*` refs hold the same transcripts
  unpacked, plus older trees. They are not on the remote.
- PPTX metadata names only the export tool; PDF metadata names the company
  as author; the PNG files carry no text chunks.

### Not scanned

The fourteen `refs/pull/*/head` refs on the remote are not fetched locally and
were not scanned, because fetching would have changed the repository.

## Code findings

Ranked by severity.

### C1. Secret scan sees nothing under `color.ui=always` or `diff.external` (reproduced)

`05_Software/aegis/template/.agentic/aegis.py:2758`, `collect_diff`.

The patch is read from plain `git diff`. With `git config color.ui always`, or
with `diff.external` set, the `diff --git` header is no longer recognised and
the per-file fallback finds no line starting with `+`. An added AWS-style key
in a tracked file then produces no `secret-in-diff` finding, and the file is
not reported as "added lines not scanned" either. Observed: three warnings
became two. `diff.noprefix` degrades correctly.

Direction: pass `--no-color --no-ext-diff --no-textconv` and explicit
`--src-prefix`/`--dst-prefix` to both patch calls, and report a gap when a
changed text file yields no attributable line.

### C2. `init` ends in a traceback on a non-UTF-8 pointer file or `.gitignore` (reproduced)

`aegis.py:932` (`write_pointer`), `aegis.py:997` (`write_ignore_block`),
`aegis.py:4916-4923` (`main`).

`main` catches `UserError` and `OSError`; `UnicodeDecodeError` is neither. A
`CLAUDE.md` or `.gitignore` written by `>` in Windows PowerShell 5.1 is
UTF-16, and `init` then exits 1 with a five-frame traceback after it has
already created `aegis.toml` and `AGENTS.md` but not `QWEN.md` or the ignore
block. The module docstring promises no tracebacks for expected failures.

Direction: turn the decode error into a `UserError`, and check every target
before writing any.

### C3. A multi-line task title injects header fields (reproduced)

`aegis.py:1139`, `aegis.py:1165` (`cmd_task`).

The title is only stripped. `task $'Add export\nstage: done'` writes
`stage: done` directly under the heading, followed by a blank line; the
parser closes the header there. The task is born `done`, has no `type` or
`branch`, and is hidden from `status`. The host adapters reject control
characters in a title (`integrations/shared/adapter.mjs:20-23`); the CLI
called directly does not.

Direction: collapse the title with `one_line`, or reject control characters.

### C4. An uninitialised submodule is fingerprinted with the superproject's HEAD (reproduced)

`aegis.py:648` (`fingerprint`).

For any directory the code asks `git -C <dir> rev-parse HEAD`. In an empty
submodule directory Git walks up to the parent repository and returns its
HEAD. `anchor` stores that commit as the submodule's identity, and after any
unrelated commit `evolution` reports `MODIFIED [other] <submodule>`.

Direction: read the gitlink from `git ls-files -s`, or require the directory
to have its own `.git` before asking.

### C5. `max_fix_cycles` is accepted up to 255 but rounds stop at 6 (reproduced)

`aegis.py:2199` (`cmd_verdict`), `aegis.py:1571`, `aegis.py:1769` (parsers),
`aegis.py:1359` (`MAX_FIX_CYCLES_LIMIT`), `integrations/shared/adapter.mjs:109`,
`integrations/shared/operations.mjs:32`.

With `max_fix_cycles = 10`, `check` raises no `config` warning and `brief`
prints `max_fix_cycles=10`, yet `verdict --round 7` is refused with "review
round must be 1 through 6", and a hand-written `review_round: 7` makes the
State unreadable. The documentation promises `1 + max_fix_cycles` rounds (see
D7).

Direction: decide one bound and apply it in the config check, the parsers,
`verdict`, the adapters and the documents.

### C6. The release archive ships documents with dangling links (read)

`02_Tools/build_aegis_release.py:149-159` (`stage_tree`).

The builder copies the product README, the root changelog and only
`06_SoftwareDocu/*.md`, without rewriting links. In
`aegis-0.16.0-windows.zip`:

- `README.md` links to `../../06_SoftwareDocu/...`,
  `template/.agentic/CLI.md`, `evaluations/README.md`, `../../00_Planning/...`
  and `../../02_Tools/README.md`.
- `docs/00_Index.md` links to the eight `.pptx` decks and to
  `Plugin_Installation/...`; `docs/Agent_Plugins.md` and `docs/README.md` do
  the same.
- `CHANGELOG.md` links to `CHANGELOG-archive.md`.

None of the targets is in the archive: 24 dangling links in total.

### C7. OpenCode redefines the tool schemas and has fallen behind (read)

`05_Software/aegis/integrations/opencode/plugin.mjs:26-46`.

The plugin declares its own twelve tools instead of building them from
`integrations/shared/operations.mjs`. `aegis_evidence` lacks `compact` and
`aegis_run` lacks `no_fallback`, although `opencode/prompts/aegis.md:53-60`
and `05_Software/aegis/README.md:204-205` tell the agent to use both. On this
host the agent cannot refuse the full-suite fallback; on the other four it
can. Every new operation has to be added in two places.

### C8. The verification lock stays if the closing fingerprint fails (deduced)

`05_Software/aegis/integrations/shared/worker.mjs:39-52`.

If `fingerprint(job.root)` throws after the child has exited (a file removed
between `git ls-files` and its read, or a Git timeout), the job becomes
`failed` with `exit_code: null`, and because `child_pid` is set the lock is
kept. Every later run returns `duplicate: true` until the lock file is
deleted by hand, and the real result of the suite is lost.

Direction: once the child's `close` event has been observed, release the lock
and keep the exit code whatever the fingerprint does.

### C9. Comments cite check numbers that no longer match (read)

`aegis.py:2863`, `2922`, `2935`, `3109`, `3112`, `3218`, `3225`.

Checks are named by position, and the positions moved when checks were added
to `CHECKS`. "check 19" means `manual-verification`, now the 20th; "20" means
`stage-zone`, now the 22nd; "check 15 reports it" means `config`, but the
15th is `fingerprints-tracked`. Slugs would stay correct.

### C10. Two docstrings use `@raises` (read)

`aegis.py:4145` (`diagram_scope`), `aegis.py:4529` (`repo_path_arg`).

`01_Documentation/Code_Style.md`, Python section: "a longer one, in plain
sentences, only for a non-obvious contract. No `@` tags." The rest of the
file uses the prose form `Raises UserError: ...`.

### Minor observations

- `parse_stage_report` (`aegis.py:1516-1547`) repeats the fence and comment
  scanner of `live_markdown_lines` (`aegis.py:1370-1404`); the two must be
  kept in step by hand.
- Journals are written with a plain read-modify-write (`write_text`), while
  the JSON sidecars are written atomically (`write_json_file`). An
  interrupted or concurrent journal write can lose content.
- `integrations/claude/cache.mjs:19` compares paths case-sensitively on
  Windows; `shared/native-cache.mjs:28` and `claude/setup.mjs:16` normalise
  case for the same kind of check.
- The adapter accepts task ids of 4 to 32 lowercase hex characters
  (`adapter.mjs:13`, `operations.mjs:6`); the CLI accepts 4 to 12 in either
  case (`aegis.py:529`).
- `status --all` prints "N open task journal(s)" for journals that are done.
- `aegis test` returns the command's exit code, so exit 1 can mean either a
  failing suite or a usage error of `aegis` itself.
- Tree cancellation is implemented for Windows and Linux only
  (`shared/process-tree.mjs:12`). Elsewhere the cancel fails, the run
  continues, and `worker.mjs:36` then records it as `cancelled`.
- The skills say never to clear an uncertain lock blindly, but no document
  says which file the lock is or how to clear it once checked.
- `aegis-install-backups/` gains a full copy on every update and uninstall
  (`shared/install.mjs:75-81`) and is never pruned.
- `02_Tools/evaluate_aegis_prompts.py` has 1,907 lines against the "about 400
  lines" rule in `Code_Style.md`; see also R19.
- No linter configuration is tracked, although the code carries `# noqa`
  comments for specific ruff rules. Ruff with a user-level configuration
  reports 1 finding in `aegis.py`, 2 in the tests and 53 in `02_Tools`; none
  is a defect.

## Documentation errors

D1, D2, D3, D7 (by reproduction), D8, D9, D12 and D27 were checked again
individually after the audit pass; the others rest on that pass, which cites
the source line for each.

### High

**D1.** `06_SoftwareDocu/03_Example_Feature.md:63` uses
`advance TASK-8b12 --path full --reason "scope accepted"`. `advance` has no
`--path` (`aegis.py:4826-4835`); the command exits 2. Lines 53-54 and 58-59
repeat the removed "path" concept. The file shipped in the 0.16.0 archive.

### Medium

**D2. Stale `path:` header.** `06_SoftwareDocu/02_Folders_and_Files.md:148`
shows `path: full` in the sample journal and lines 208-209 list `path` among
the header lines the agent edits; `06_SoftwareDocu/07_FAQ.md:244` says `brief`
shows "stage and path". `task` writes no such line and `brief` has no such
field.

**D3. `explain` and "a finding".** `02_Folders_and_Files.md:345-346`,
`07_FAQ.md:136-139` and `08_Prompt_Cheatsheet.md:308-310` say an uncovered
path is called a finding. The command prints only
`no requirement covers this path.` and exits 0 (`aegis.py:4596-4598`).
`CLI.md:1021-1022` and `04_Example_Direct_Change.md:55-56` say the opposite.

**D4.** `integrations/claude/README.md:38` lists eleven MCP operations;
`journal` is missing. The server exposes twelve.

**D5.** `integrations/opencode/prompts/aegis.md:53-60` and
`05_Software/aegis/README.md:204-205` describe `no_fallback` and `compact` as
available on every host; OpenCode does not offer them (C7).

**D6.** `template/.agentic/CLI.md:604-606`: "Invalid values warn and fail safe
to disabled review with the default bound." An invalid `max_fix_cycles`
leaves review enabled with a bound of 0 (`aegis.py:380-389`).
`01_Install_and_Setup.md:227` is correct.

**D7. Round bound.** `1 + max_fix_cycles` with `max_fix_cycles` 0-255 is
stated in `CLI.md:330-331, 604-605, 609-610`,
`09_CLI_Reference.md:316-317, 572-575`, `templates/task.md:44`,
`steps/review.md:29-30`, `05_Software/aegis/README.md:286-287`,
`01_Install_and_Setup.md:230-231`, `02_Folders_and_Files.md:370, 376` and
`07_FAQ.md:254`. Rounds stop at 6 (C5).

**D8. Exit code.** `CLI.md:1041` and `09_CLI_Reference.md:1001` promise exit 1
for usage errors. `argparse` usage errors exit 2 with a multi-line message;
only `UserError` cases exit 1.

**D9.** `05_Software/aegis/README.md:201-202` says licenses are preserved in
new task and requirement records. They are removed (`aegis.py:1120-1134`).

**D10.** `01_Install_and_Setup.md:155-159` says its settings reference names
every setting the CLI reads. `[context] page_kb` is missing there and from
the table in `02_Folders_and_Files.md:353-372`.

**D11.** `01_Install_and_Setup.md:206-208` says `default_branch` decides what
`anchor` and `evolution` consider changed. They compare fingerprints with the
saved anchor and never resolve a branch. The same sentence is in the
generated `aegis.toml` comment (`aegis.py:126-129`).

**D12.** `integrations/codex/plugins/aegis/skills/aegis/references/operations.md:20-26`:
a paragraph at line 21 splits the table, so five rows render as raw text.

### Low

**D13.** `CLI.md:478` and `09_CLI_Reference.md:462` name the summary field
"Spec compliance"; the label is `Specification compliance`, which also
overflows the 14-column pad and prints without a space (`aegis.py:1936, 1945`).

**D14.** `templates/task.md:16-17` and `05_Software/aegis/README.md:94-95` say
each journal command prints the summary. `log` and `ruling` print one line.
README:94 also says they never refuse; `verdict` and `ruling` can.

**D15.** `05_Software/aegis/README.md:202-203` and `07_FAQ.md:331-332` say
step files refer to shared reporting instructions; none does.

**D16.** `steps/5_validate.md:53-54`, `steps/adopt.md:60-61` and
`02_Folders_and_Files.md:35-37` speak of `AEGIS:TEMPLATE` notes in the
component and spec templates; those templates contain no such marker.

**D17.** `CLI.md:96-97`, `09_CLI_Reference.md:92` and
`01_Install_and_Setup.md:44-45` say `init` names the sidecars still tracked;
it prints a count and a generic command.

**D18.** `integrations/opencode/prompts/aegis.md:14` warns against inventing a
"machine.input command"; nothing of that name exists.

**D19.** `integrations/README.md:11` names two integration test files;
`test_claude_integrations.py` is a third.

**D20.** `07_FAQ.md:43-47`: the first paragraph under "What belongs in the
task Log?" is about project context files.

**D21.** `template/.agentic/AGENTS.md:180-182` says `check` reports any edit
outside `.agentic/` in the early stages as `stage-zone`. It fires only inside
the `[layout]` source and tests globs (`aegis.py:3231-3236`).

**D22.** `diagram --component` and `--task` cannot be combined
(`aegis.py:4149-4152`); `CLI.md:875`, `09_CLI_Reference.md` and
`02_Folders_and_Files.md:332` do not say so.

**D23.** Codex `references/operations.md:12` omits the `adopt` task type;
`references/review.md:22` and `agents/aegis-quality-review.toml` name an
`aegis_candidate` tool that Codex does not have.

**D24.** The Claude, Pi and Qwen skills and the OpenCode prompt mention bridge
options (`--impacted --no-fallback`, `--compact`); only Codex has a bridge.

**D25.** `CLI.md:22` says the CLI does not access the network;
`09_CLI_Reference.md:17-18` has the accurate form (configured commands may).

**D26. Text printed by `aegis.py` that contradicts the documents.** The
generated `aegis.toml` says a stopped command is "never" a failure
(`aegis.py:114-115`), but it is an `ERROR command-timeout`; `status` ends with
"Resume one with: ... status TASK-<id>" (`aegis.py:1277`) while every document
says to resume with `brief`.

**D27.** `06_SoftwareDocu/07_FAQ.md:347`, `00_Index.md:44-45` and
`Project_Context.md:27-28` say this repository uses AEGIS and keeps populated
context in an installed `.agentic/context/`. There is no root `.agentic/`.

### CLI.md and 09_CLI_Reference.md

Apart from D6 and D25 the two do not contradict each other, but each holds
content the other lacks. Only in `CLI.md`: the refusal of a bare task id as a
title, the repeated-header and Rulings notes, the `log` stage-label reminder.
Only in `09_CLI_Reference.md`: the adoption order, the `--read` description,
legacy `deliver`, symlink and submodule fingerprinting, the `repo-evolution`
note, default-branch resolution under `test`, and the integration operations.

## Repository and delivery records

R1, R2, R3, R4 (the file count), R6 and R13 were checked again individually.

### Medium

**R1.** `README.md:176` says "the 15-file managed payload". The payload has 18
files (`build_aegis_release.py:34-53`, `02_Tools/README.md:95`, all three
`release-manifest.json`).

**R2. `AGENTS.md` names things that do not exist.** Lines 17-19 require
`template/CHANGELOG.md` to stay empty; `05_Software/aegis/template/` contains
only `.agentic/`. Lines 107-109 require updating "copied template adapters
under `.codex/`, `.claude/`, `.pi/`, and `.opencode/`"; the host sources are
under `05_Software/aegis/integrations/`, and Qwen is not in the rule.
`00_Planning/05_Implementation_Phases.md:51` repeats the changelog statement.

**R3.** `07_Delivery/aegis-0.16.0/BUILD.md:59-63` says no local-model
evaluation of the payload exists. Six Qwen baselines on the delivered payload
are now tracked. The medium and high `luna` baselines it cites ran on a
different payload, as `evaluations/README.md:15-18` itself says.

**R4. Host packages are not reproducible from the commit.** 32 tracked files
have CRLF or mixed line endings in the working tree while the index and
`.gitattributes` say LF: 30 under `integrations/`, plus
`02_Tools/build_agent_plugins.mjs` and
`07_Delivery/aegis-0.16.0/BUILD_TESTS.txt`. The `source_files` hashes in
`delivery-manifest.json` are of the working-tree bytes, and CRLF files ship
inside the Linux tarballs, including files that start with a shebang. This
contradicts "whose tree is the packaged source" (`aegis-0.16.0/BUILD.md:6`)
and "reproducible" (`02_Tools/README.md:96`). The core archive is unaffected.

**R5. Most of a delivery has no tracked build procedure.**
`01_Documentation/Releases.md:51` points to `02_Tools/README.md`, which
covers only the core builder and the plugin directory assembler. Nothing
tracked creates the ten host archives, the documentation ZIP,
`DELIVERY_SHA256SUMS`, `delivery-manifest.json`, `archive-inventories.json`,
`BUILD.md`, `BUILD_TESTS.txt` or `source-preparation.diff`. `AGENTS.md:24-25`
places delivery build scripts under `02_Tools/`.

**R6. The 0.14.0 record is inconsistent.** `aegis-0.14.0/BUILD_TESTS.txt:13-14`
records archive sizes that differ from `release-manifest.json` and
`RELEASE.md`; `BUILD.md:35-37` says the test log is from a prior build.
`BUILD_TESTS_INITIAL.txt` ends with "3 failed, 548 passed, 2 skipped", and
`BUILD.md:38-44` records that the three tests were deleted.

**R7.** There is no `aegis-0.15.0` tag, although `07_Delivery/aegis-0.15.0/`
exists. Tags present: `aegis-0.13.0`, `aegis-0.14.0`, `aegis-0.16.0`,
`waegis-0.6.0`.

### Low

**R8.** `CHANGELOG.md` `[Unreleased]` is empty although
`02_Tools/report_aegis_evaluations.py` and `report_aegis_evaluations_page.py`
were added after the 0.16.0 delivery (commit `636c606`).

**R9.** `00_Planning/00_README.md:86` calls adoption "not a seventh ordinary
stage"; there are five stages.

**R10.** `README.md:109-119`: the layout table omits `09_Others/`.

**R11.** `07_Delivery/README.md` has 17 links into the ignored `dist/`
folder; they are dead in any clone.

**R12.** `aegis-0.14.0/RELEASE.md:8` and `aegis-0.15.0/RELEASE.md:8` point to
sections of `CHANGELOG.md` that have moved to `CHANGELOG-archive.md`.
`build_aegis_release.py:227` hard-codes the wording, so it will recur.

**R13. License markers outside the payload.** The four scenario files under
`05_Software/aegis/evaluations/` carry a `"license"` field, against
`AGENTS.md:58-61`.

**R14.** `README.md:205-206` says the bundled third-party modules keep their
own MIT notices; `vendor/jsonc.mjs` and `vendor/opencode-tool.mjs` contain no
license text. The notices are only in `vendor/LICENSES.txt`.

**R15.** `REUSE.toml` names two licenses but there is no `LICENSES/`
directory, so a REUSE tool cannot resolve them; its `**` annotation also
labels the vendor notice files as DDP-licensed.

**R16.** `AGENTS.md:84` gives `python template/.agentic/aegis.py --help`,
which is relative to `05_Software/aegis/`, while the two commands above it are
relative to the repository root.

**R17.** `00_Planning/05_Implementation_Phases.md:121` says raw evidence is
kept outside the repository; `02_Tools/README.md:51-52` says it is in the
ignored `.tmp-codex-eval/` inside it. The file is titled "Current
implementation" and contains no phases, so its name is stale.

**R18.** `07_Delivery/aegis-0.16.0/delivery-manifest.json` has no
`verification` block, although `07_Delivery/README.md:60-61` points to it for
verification details; the 0.14.0 and 0.15.0 manifests have one.

**R19. `Code_Style.md` rules the code does not meet.** Sixteen of twenty
Python files have a multi-line module docstring; tests and
`evaluate_aegis_subscription.py` mostly lack type hints; three files exceed
about 400 lines; `integrations/pi/index.js` is not `.mjs`.

**R20.** `integrity.json` keys in the subscription baselines use Windows
backslashes, so a POSIX verifier cannot resolve them.

### Not confirmed

- The local 0.14.0 archives fail the tracked `DELIVERY_SHA256SUMS` and match
  the first 0.14.0 build instead; the archives of the recorded rebuild are
  not on this machine.
- Whether `.codex/config.toml` takes effect depends on Codex project-trust
  semantics, which were not checked.
- `--type fix` is still presented as governed work in
  `00_Planning/03_Companion_CLI.md:27` and `CLI.md:29, 159`, while
  `00_README.md:79-83` says bug fixes get no journal. This may be intended
  for fixes that change a rule.
- `steps/review.md:31-33` has the agent return to build, fix and come back in
  one flow, while `steps/5_validate.md:42-45` and the CLI make any return
  wait for the user. Which is intended is not stated.
- `07_Delivery/agent-plugins-unreleased/`, the default output of
  `build_agent_plugins.mjs`, is covered by no ignore rule.

## Verified consistent

- `VERSION = "0.16.0"` matches `CHANGELOG.md`, the four source manifests, all
  0.16.0 delivery records and the tag.
- All 13 archives of 0.15.0 and of 0.16.0 match `DELIVERY_SHA256SUMS` and
  `SHA256SUMS`; `archive-inventories.json` matches the local archives.
- All 13 baselines verify: every `integrity.json` and `evidence.sha256.json`
  hash, and the pass counts in `evaluations/README.md`.
- All 20 subcommands are documented, the 24 check slugs and the 12 adapter
  operations match the source, and every documented flag exists except D1.
- 212 relative links across 98 tracked Markdown files resolve, apart from the
  `dist/` links (R11) and one template placeholder.
- `LICENSE.txt` is byte-identical to the payload copy.

## Validation run

- `python -m pytest -q -p no:cacheprovider 05_Software/aegis/tests`:
  521 passed, 2 skipped in 238 s, with bytecode writing disabled.
- Every Python file under the payload and `02_Tools/` parses.
- `python 05_Software/aegis/template/.agentic/aegis.py --help` and
  `--version` work.
- `git status` was clean before and after the review.

## Not verified

- PPTX and PDF bodies, and external URLs.
- The real behavior of the hosts (OpenCode, Codex, Pi, Qwen Code, Claude
  Code); integration findings rest on the source.
- C8, which is deduced from the code.
- The remote `refs/pull/*` refs (see Secrets).
- The evaluation narrative in `evaluations/README.md` beyond its counts.
