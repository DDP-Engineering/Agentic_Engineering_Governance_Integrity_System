# WAEGIS

WAEGIS is the separate, offline, standard-library-only operator application
for planning and applying AEGIS repository initialization, installation,
upgrade, and removal. It is not installed into target repositories.

## Guided use

Launching WAEGIS without arguments starts the interactive human adoption
wizard. It asks for the repository, reports the active Python runtime, Git
availability, repository status, and AEGIS installation status, then selects
installation or upgrade. A non-Git directory can be initialized through its
own separately reviewed plan when Git is available.

The wizard stores plans beside, never inside, the target repository. It shows
the action count, warnings, and exact digest; offers a paged action review; and
labels every page with its exact action range. It confirms a complete review
only after displaying every numbered action without a gap, and reports the last
displayed action when review stops early. Every apply confirmation defaults to
no. An accepted apply still calls the same digest-verifying lifecycle operation
as the flat CLI. Cancellation before apply leaves the target unchanged, and
successful installation or upgrade ends with the platform-appropriate AEGIS
verification commands.

WAEGIS detects project command arrays and working directories and writes them
as execution guides. It does not add command timeouts or imply that AEGIS will
run those commands. In the installed project, use `execution-list` to inspect a
guide, run it with normal host tooling, and submit the observed outcome through
`evidence-add`.

```powershell
bin\waegis.cmd
```

```bash
./bin/waegis
```

The flat operations remain available for agents, scripts, and developers who
prefer explicit command-by-command control.

Every mutation uses an operator-owned JSON plan written outside the target.
Apply requires the exact `sha256:` digest printed by the corresponding plan
operation, verifies canonical plan bytes and action content hashes, and refuses
a meaningfully changed target. Except for an explicitly authorized
`repository-init-apply`, WAEGIS performs no Git mutation or subprocess call.

The eleven flat operations are `help-show`, `version-show`, `plan-show`,
`repository-init-plan/apply`, `install-plan/apply`, `upgrade-plan/apply`, and
`remove-plan/apply`. Human and JSON modes share the AEGIS version 1 response
envelope and error meanings.

Successful human `help-show` and `--help` output renders that registry as a
readable usage page with one command, purpose, and argument signature per
entry, followed by the plan-review-apply lifecycle reminder. Machine help keeps
the complete structured registry unchanged under `--format json`.

`plan-show --plan <path> [--offset <n>] [--limit <n>]` verifies and summarizes
one exact lifecycle plan without modifying the plan or target. It reports the
exact plan digest and byte count, target state, aggregate kind/ownership counts,
and a page of action index/path/kind/ownership/content-digest summaries. It
never returns `content_base64`; the default page is 50 actions and the maximum
is 100. Review is a companion capability, not an apply prerequisite, and it
does not require Git to be available.

Git executable availability gates only `repository-init-apply`, the sole
operation that invokes `git init --quiet`. Help, version, plan review, every
lifecycle plan, and install/upgrade/remove apply remain available without a Git
executable because they use only the filesystem protocol. Existing target
structure checks are unchanged: operations that require an initialized target
still refuse a target without repository metadata, and exact plan-digest
authorization remains mandatory.

## Machine protocol

`--format json` and `--format=json` select machine mode. Machine responses,
including argument, startup, and composition failures, are one compact UTF-8
JSON object on standard output followed by exactly one LF. Human startup and
composition failures use the same result envelope and bounded presenter rather
than ad-hoc error text. Standard error remains empty once Python starts and the
requested presentation can be determined. JSON serialization rejects
non-finite numeric values.

WAEGIS uses the shared protocol error-to-exit-code classes:

| Exit code | Error codes |
|---:|---|
| `2` | `invalid_input` |
| `3` | `not_found`, `ambiguous_run` |
| `4` | `invalid_transition`, `state_conflict`, `malformed_state`, `unsupported_schema`, `capability_unavailable` |
| `5` | `repository_error`, `missing_prerequisite` |
| `6` | `publication_failed` |
| `70` | `internal_error` and any unknown internal error code |

WAEGIS deliberately accepts only the `--format` global option. AEGIS globals
for repository selection, color, protocol negotiation, and revision tokens do
not apply to the standalone lifecycle tool. WAEGIS also retains its bounded
message-based classification of internal lifecycle plan errors; these are
accepted implementation divergences, not additions to the public protocol.

Target authorization remains filesystem-based and stdlib-only. Planning and
apply hash every tracked worktree file even when it matches an ignore rule, and
every unignored file. Untracked paths matched by target-local `.gitignore` or
`.git/info/exclude` rules are omitted whether they appear before or after
planning. Therefore bytecode caches, swap files, and logs remain disposable,
while changed/deleted tracked files, changed ignore rules, non-ignored files,
and force-added ignored paths still make the plan stale. WAEGIS reads the local
Git index conservatively as data and does not invoke `git ls-files`,
`git check-ignore`, or any other new Git process; an unreadable or unsupported
index causes ignored paths to remain fingerprinted rather than silently omitted.

Installation detects conventional `tests`/`test` roots up to four levels below
the repository root. The bounded walk prunes hidden, virtual-environment,
dependency, cache, build, distribution, vendor, and linked directories. Pytest
selection recognizes configuration in the repository root or the owning
nested software project, as well as a bounded scan for pytest-style test
functions or methods without `unittest.TestCase` usage. Otherwise it configures
standard-library unittest. The plan warning names the selected framework and
its detection basis. Ruff is recorded when its repository-root configuration
is present, and missing tests use the shipped `.agentic/tests` unittest
default. Existing configuration, rules, project knowledge, tests, application
files, Adoption state, and Run evidence are preserved.

The exact install plan also adds a project-owned `.gitkeep` only for each
missing configured Requirement, Component, test, Adoption, and Run root. This
uses existing relocated paths as written, makes a fresh installation immediately
configuration-valid, and leaves existing directories and operator files
unchanged. An obstructing existing file is preserved and reported as a plan
warning. Upgrade and removal never treat these placeholders or their roots as
payload-owned, so project state remains in place.

Install also creates missing native AEGIS starter guidance for Claude Code,
Codex, OpenCode, Pi, and Qwen Code at each host's project discovery path.
Upgrade backfills any missing starter, including `.pi/skills/aegis/SKILL.md`;
install and upgrade never replace an existing host file, and removal preserves
all host files. A legacy project-owned `.pi/agents/aegis.md` is likewise left
untouched. The starter bytes come from manifest-owned canonical resources under
`.agentic/aegis/adapters/starters/`, while the external copies are
project-owned and intentionally excluded from payload verification.

Install and upgrade also make AEGIS discoverable to agents that automatically
read a repository-root `AGENTS.md`. When that file is missing, the plan creates
a minimal project-owned bridge. When it already exists as a UTF-8 regular file,
the plan prefixes one bounded WAEGIS-managed bridge and retains the complete
existing document as its continuation. The marker makes later upgrades
idempotent while allowing WAEGIS to refresh its own bounded block. The bridge
requires checkpoint-default Run creation, distinguishes ordinary requests to
implement, validate, and report from explicit continuous delegation, and tells
the host to end its turn without another tool call after presenting a required
checkpoint. It also requires checkpoint choices to appear as a vertical
Markdown list with one choice per line. Symlinks, non-regular files, unreadable
files, non-UTF-8 content, and incomplete existing bridge markers are preserved
and reported for manual review instead of being rewritten.

Installation also creates or safely extends the project-owned
`.agentic/.gitignore` with `.runtime/` and the configured Run pointer expressed
relative to that file. These exclusions are versioned and therefore reach
clones. Existing rules remain byte-preserved apart from missing appended rules;
upgrade and reinstall are idempotent, and removal leaves this project-owned
file in place. Normal repositories additionally retain the transitional
configured-pointer entries in `.git/info/exclude`; the repository-root
`.gitignore` is never changed.

Normal repositories and linked Git worktrees are accepted as installation
targets. For a linked worktree, WAEGIS does not mutate the primary repository's
shared `.git/info/exclude`; the versioned `.agentic/.gitignore` is still planned
and the shared-metadata omission remains a warning.

## Development

```powershell
uv run --group dev python -m pytest -q tests
uv run --group dev ruff check src tests
uv run --group dev python -B -m waegis --help
uv run --group dev python -B -m waegis --format json version-show
```

Source-checkout execution reads the canonical sibling AEGIS payload strictly
as data. Release archives embed that exact payload below the WAEGIS package;
WAEGIS never imports AEGIS runtime code.

External-runtime delivery wrappers prefer a bundled runtime, then probe an exact
Python 3.12 as `python3.12`, Windows `py -3.12`, `python3`, or `python`, allowing
venv, pyenv, and conda environments without widening the version pin. Missing
Python uses the normal launcher prerequisite response. Once Python is running,
missing Git returns the normal human or one-line JSON `missing_prerequisite`
response with exit code 5 and empty stderr only for `repository-init-apply`;
filesystem-only operations remain dispatchable. Bundled delivery launchers keep
using the private Python 3.12 and Git copies inside their archive.
