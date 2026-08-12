# WAEGIS

WAEGIS is the separate, offline, standard-library-only operator application
for planning and applying AEGIS repository initialization, installation,
upgrade, and removal. It is not installed into target repositories.

Every mutation uses an operator-owned JSON plan written outside the target.
Apply requires the exact `sha256:` digest printed by the corresponding plan
operation and refuses a changed target. Except for an explicitly authorized
`repository-init-apply`, WAEGIS performs no Git mutation.

The ten flat operations are `help-show`, `version-show`,
`repository-init-plan/apply`, `install-plan/apply`, `upgrade-plan/apply`, and
`remove-plan/apply`. Human and JSON modes share the AEGIS version 1 response
envelope and error meanings.

Installation detects conventional test roots, uses pytest only when a pytest
configuration signal exists, otherwise configures standard-library unittest,
and records Ruff when its project configuration is present. Missing tests use
the shipped `.agentic/tests` unittest default. Existing configuration, rules,
project knowledge, tests, application files, Adoption state, and Run evidence
are preserved.

Normal repositories and linked Git worktrees are accepted as installation
targets. For a linked worktree, WAEGIS does not mutate the primary repository's
shared `.git/info/exclude`; the plan reports that omission as a warning.

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

External-runtime delivery launchers check for Python 3.12 and Git, then use
those existing tools without installing or configuring them. Bundled delivery
launchers use the private Python 3.12 and Git copies inside their archive.
