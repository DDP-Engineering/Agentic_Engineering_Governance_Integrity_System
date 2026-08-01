<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS Transaction Integrity and Crash Recovery

## Purpose

WAEGIS file transactions protect a bounded set of repository-relative files
across validation, apply, verification, manifest publication, rollback, and
process termination. The design is stdlib-only and offline. It treats the
repository as potentially editable while trusting a separately protected
WAEGIS home belonging to the invoking OS account.

## Persistent Records

Repository state version 2 is stored at:

```text
.agentic/.waegis-transactions/<transaction-id>/
  state.json
  backups/
    000000.bak
    ...
```

The state document contains exactly:

```text
transaction_version, id, command, phase, created_at, entries, key_id, mac
```

Each entry contains exactly:

```text
path, existed, backup, backup_size, backup_sha256
```

`path` is canonical POSIX form and passes the same portable managed-path
validator as install-manifest paths. Duplicate and case-fold-colliding
destinations are refused. Existing destinations have a generated positional
backup basename plus original size and SHA-256; new destinations have `null`
for all backup fields.

The external WAEGIS home contains:

```text
transaction-auth.key
transaction-ownership/<repository-id>/<transaction-id>.json
transaction-locks/<repository-id>.lock
```

The ownership record authenticates the resolved repository identity and digest
of the immutable operation set. The repository state MAC authenticates its
operation fields and current phase. Editing only `state.json` therefore cannot
select another destination or backup. Recovery also refuses a missing,
mismatched, or modified ownership record. Before repository state enters a
terminal phase, that outcome is authenticated in the external record; replaying
an older valid non-terminal `state.json` therefore cannot turn a committed or
rolled-back transaction into a new rollback candidate.

## Validation Barrier

Recovery discovers only direct children of the expected repository-local
transaction root. It refuses symbolic links, junctions, other reparse points,
non-directory children, linked state/backup storage, unknown transaction
objects, unexpected backups, missing non-terminal backups, altered backup
content, malformed JSON, excessive state size, and excessive entry counts.

All discovered transaction documents and backup objects are validated before
the first repository destination changes. Immediately before rollback, every
destination is resolved again and inspected with non-following metadata.
Directories, links, junctions, devices, and other non-regular substitutions
are rejected. Original files are restored through an exclusive sibling
temporary followed by exact-path atomic replacement and digest verification.
Transaction-created files are removed only when the exact destination is a
regular file; deletion is never recursive.

Cleanup does not call recursive removal. It deletes only authenticated backup
basenames, the regular state file, the known backup directory, the known
transaction directory, and the matching external ownership record. Terminal
cleanup tolerates already removed backups so interruption during cleanup can be
retried.

## Phases and Recovery

The supported sequence is:

```text
staged -> applying -> verified -> committed
    \          \           \
     +----------+-----------+-> rolled-back
```

An uncommitted transaction rolls back. After restoration completes, WAEGIS
persists `rolled-back` before cleanup, so an interrupted cleanup never repeats
destination mutation. `committed` is also terminal and cleanup-only. A rollback
failure leaves its non-terminal state and ownership record intact and is
reported as incomplete recovery.

The repository-scoped OS lock is held from `begin` through commit or rollback.
Recovery holds the same lock while it re-discovers, validates, and processes
the transaction set. This prevents two WAEGIS processes from recovering the
same record or applying a new WAEGIS transaction concurrently. It does not
stop an unrelated process from changing files outside WAEGIS.

Dry-run discovery does not acquire or create a lock and does not change
repository or transaction state. Commands expose pending IDs in JSON plans and
human output. A later mutating invocation still requires explicit approval
before recovery.

## RepoWise Barrier

RepoWise configuration plans its complete policy/runtime/manifest result before
beginning a transaction. It then:

1. stages authenticated backups;
2. marks `applying`;
3. atomically writes and byte/TOML-verifies policy;
4. atomically writes and byte/JSON-verifies runtime metadata;
5. writes and byte-verifies the install manifest last;
6. marks `verified`;
7. marks `committed` and cleans storage.

Abrupt termination at steps 2 through 5 leaves a non-terminal record and the
next approved recovery restores the exact pre-operation bytes or absence.
Termination after the commit mark retains the applied files and retries only
cleanup. Ordinary errors attempt rollback immediately, report its actual
outcome, and preserve `KeyboardInterrupt` and `SystemExit`.

## Mutating-Command Failure Reporting

`configure`, `repair`, and `upgrade` all report the transaction's actual
terminal state rather than a single generic failure, because the three
post-write outcomes are materially different:

| Transaction state | Repository | Reported as |
|---|---|---|
| `committed`, cleanup failed | fully upgraded, durable | committed, cleanup pending; recovery retries cleanup |
| `rolled-back` | restored to its exact pre-command bytes | failed and rolled back |
| rollback raised | possibly partially applied | rollback did not complete; recovery state retained |

For `upgrade` the apply phase raises a typed `UpgradeApplyError` carrying that
state, so the reported outcome never depends on inspecting message text. All
three keep the frozen `upgrade` operational exit code; the machine-readable
distinction is in the `--json` `result` mapping, which carries `applied`,
`rolled_back`, and `cleanup_pending`. A committed-but-cleanup-pending upgrade
journals as a completed run, because the payload really was upgraded on disk
and only transaction storage remains to be removed.

Whenever files are left on disk, an `upgrade` run in `branch-commit` mode also
reports that they are uncommitted and names the branch holding them: the Git
commit step runs only for a clean apply, so a committed-but-cleanup-pending
upgrade leaves the new payload in the working tree with nothing recorded in Git.

`KeyboardInterrupt` and `SystemExit` are never converted into a reported
outcome; they propagate after the same rollback attempt, carrying any rollback
failure as an exception note.

## Legacy State and Manual Remediation

Version-1 state has no MAC, external operation ownership, or authenticated
backup metadata. Automatic migration would reintroduce trust in editable
repository paths, so it is deliberately refused.

When recovery reports untrusted state:

1. stop concurrent WAEGIS activity and copy the repository and WAEGIS-home
   transaction records;
2. inspect the named transaction directory without following links;
3. compare backup contents with the intended repository destinations;
4. restore only operator-verified files or revert by another trusted source;
5. remove the repository transaction directory and matching ownership record
   only after the repository is verified;
6. rerun the command.

WAEGIS never deletes failed validation evidence automatically.

## Threat-Model Limits

HMAC provides authentication only while `transaction-auth.key` and the
ownership directory are protected from the repository writer. A process with
the same OS-account privileges, an administrator, or an attacker that can read
and replace WAEGIS-home state can forge records. POSIX restrictive modes are
checked; Python's standard library does not provide a portable Windows ACL
owner/permission verification API. Filesystem metadata checks also cannot make
arbitrary concurrent hostile filesystem mutation impossible, though exact-path
atomic replacement and repeated non-following checks close the unsafe
directory-copy and link-following behavior.
