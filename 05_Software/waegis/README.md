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

## Machine protocol

`--format json` and `--format=json` select machine mode. Machine responses,
including argument and startup failures, are one compact UTF-8 JSON object on
standard output followed by exactly one LF; standard error remains empty once
the requested machine protocol can be determined. JSON serialization rejects
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

Installation detects conventional test roots and selects pytest when either a
pytest configuration signal or a bounded scan finds a bare pytest-style test
function without `unittest.TestCase` usage. Otherwise it configures
standard-library unittest. The plan warning names the selected framework and
its detection basis. Ruff is recorded when its project configuration is
present, and missing tests use the shipped `.agentic/tests` unittest default.
Existing configuration, rules, project knowledge, tests, application files,
Adoption state, and Run evidence are preserved.

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

External-runtime delivery wrappers check for Python 3.12, then the Python
launcher checks Git without installing or configuring either tool. Missing Git
uses the normal human or one-line JSON response with exit code 5; help and
version remain available. Bundled delivery launchers use the private Python
3.12 and Git copies inside their archive.
