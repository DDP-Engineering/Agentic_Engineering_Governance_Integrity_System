<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Design — what the test fingerprint covers

**Answers finding:** `F-02`
**Answer in one line:** ask Git which files exist under the test roots. The
repository's own `.gitignore` is sufficient. No denylist, no new configuration.

## 1. The problem

`_fingerprints` walks the filesystem and hashes everything it finds:

```
execution_operations.py:82   def _fingerprints(context, workspace) -> dict[str, str]:
execution_operations.py:84       for root in workspace.config.test_roots:
execution_operations.py:85           for path in workspace.list_files(str(root)):
execution_operations.py:86               result[path] = context.hash_service.digest(workspace.read_bytes(path))
```

`list_files` (`infrastructure/workspace.py:108-117`) is a plain `rglob("*")`. Called
with no suffix it returns build artifacts alongside tests. A real Check produced:

```json
{
  "tests/__pycache__/test_calc.cpython-314.pyc": "sha256:af9e30…",
  "tests/test_calc.py": "sha256:425d77…"
}
```

CPython's default bytecode cache embeds the source mtime, so the digest moves when
nothing changed. Demonstrated on this tree — identical source bytes, mtime touched:

```
pyc digest before: a191dc450a076120
pyc digest after:  c31b1100c5fe5309
```

A fresh clone, a checkout, a worktree switch or a CI runner then reports
`test_changed_after_red` naming a file nobody touched. False accusations in the one
signal the product exists to produce teach a developer to ignore it.

## 2. The fix

Replace the filesystem walk with Git's view of the working tree:

```
git ls-files -z --cached --others --exclude-standard -- <test_root>
```

That is "files Git tracks, plus untracked files Git does not ignore". Every real
repository already ignores `__pycache__`, `.pytest_cache` and friends, so the caches
disappear with no list to maintain and nothing for the user to configure. The
project's existing `.gitignore` is the answer.

## 3. Why this is safe — a correction

An earlier draft of this document argued against using ignore rules, on the grounds
that an agent could append a test file to `.gitignore` and remove it from
protection. **That argument was wrong**, and the correction is the reason the simple
design is also the safe one.

Git's ignore rules do not apply to tracked files. Verified on this tree — a committed
test, then appended to `.gitignore`:

```
$ git check-ignore -v tests/test_a.py
   (no output — not ignored)

$ git ls-files --cached --others --exclude-standard tests
tests/test_a.py
```

The file stays tracked, stays listed, stays fingerprinted. The attack does not work,
against `ls-files` or even against `check-ignore`. Any test that has ever been
committed — which is every test that matters — cannot be hidden this way.

The one remaining case is a test that is **both** brand new and ignored. Git then
does not see it at all:

```
$ git status --porcelain=v2 --untracked-files=all | grep test_new
   (nothing)
```

That case needs no special handling, for three reasons. Such a file is invisible to
AEGIS's change attribution already, since attribution reads `git status`. It would
not survive a clone and would never run in CI, so it cannot carry a passing claim
anywhere but one machine. And creating it requires editing a tracked `.gitignore`,
which attribution does record as an observed change. Detection, which is the
product's model, still holds.

## 4. Implementation

**One function, one helper, one fallback.**

1. Add a `tracked_files(root)` method to the workspace adapter in
   `infrastructure/workspace.py`, using the existing Git subprocess helper at
   `:181-186`. Run `ls-files -z --cached --others --exclude-standard -- <root>`,
   split on `NUL`, return sorted repository-relative POSIX paths. Add the matching
   signature to `ports/workspace.py`.
2. In `_fingerprints` (`execution_operations.py:82-87`), call `tracked_files` instead
   of `list_files`.
3. If the Git call fails — no repository, or Git unavailable — fall back to today's
   `list_files` walk. Behavior is then exactly what ships now, so the change can
   never make a working setup worse.

Do not change `list_files` itself. It has eight other callers
(`project_operations.py` lines 355, 819, 915, 983, 1032, 1073;
`resume_context.py:791`; `workflow_operations.py:285`), every one of them enumerating
`.agentic/` material with an explicit `.md` suffix.

Both fingerprint call sites — the red capture at `execution_operations.py:194` and the
green comparison at `:208` — already route through `_fingerprints`, so one change
fixes both and they cannot drift apart.

## 5. Do not set `PYTHONDONTWRITEBYTECODE`

Tempting, since AEGIS launches the process and could suppress `.pyc` creation
entirely. Reject it. AEGIS's boundary is that it does not change how a project runs;
suppressing bytecode caching changes startup cost and makes an AEGIS-launched run
behave differently from the same command typed by the developer. It is also
Python-specific reasoning inside a language-neutral runtime. Asking Git solves the
same problem without touching the child environment.

## 6. Not a problem: change attribution

The Run baseline showed `src/__pycache__/*.pyc` under `changes_first_observed`, which
looks like the same defect. It is not, and needs no change. Attribution reads
`git status --porcelain=v2 -z --untracked-files=all` (`infrastructure/workspace.py:201-254`),
and Git omits ignored files unless `--ignored` is passed, which it is not. The caches
appeared only because the review fixture was a bare `git init` with no `.gitignore`.

That is the same insight as section 2, and it is worth stating plainly: **attribution
was already correct because it asks Git. The fingerprint walk is the only place that
bypasses Git's view of the working tree, which is exactly why it is the only place
with this defect.**

## 7. Tests to add

In `05_Software/aegis/tests/test_execution_integrity.py`:

- `test_fingerprints_exclude_ignored_cache_files` — a fixture with a normal
  `.gitignore`, `tests/test_a.py`, and `tests/__pycache__/test_a.cpython-312.pyc`;
  assert the fingerprint map holds exactly `tests/test_a.py`.
- `test_tracked_test_stays_fingerprinted_when_gitignored` — append a committed test
  to `.gitignore`, capture red, edit the test, run green; assert
  `test_changed_after_red` still names it. This is the regression test that keeps the
  design honest.
- `test_fingerprints_fall_back_without_git` — a directory that is not a repository;
  assert the walk still produces a map.
