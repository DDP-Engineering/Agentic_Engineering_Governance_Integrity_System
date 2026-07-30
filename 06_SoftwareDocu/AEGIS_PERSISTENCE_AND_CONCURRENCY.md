<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Persistence and Concurrency

## Scope

This contract covers same-worktree AEGIS processes. Different clones and
branches retain the existing distributed model: globally unique run
directories merge additively, UUID-per-file requirement creation avoids shared
creation targets, and edits to the same requirement on separate branches
remain ordinary Git conflicts.

## Shared Atomic Publication

`persistence.py` is the single stdlib-only primitive used by graph, journal,
requirement, active-run pointer, and normalized RepoWise JSON writers. It:

- creates a unique sibling temporary file with exclusive operating-system
  creation;
- writes the complete UTF-8/byte payload, flushes it, and fsyncs it;
- publishes with `os.replace`;
- fsyncs the parent directory on supported POSIX filesystems;
- removes every unpublished temporary file on failure.

Windows has no portable stdlib parent-directory fsync interface. On Windows,
file fsync and atomic replacement are performed, while directory fsync is
explicitly unsupported.

## Locking

Persistent lock files live below `.agentic/.workspace/locks/`, which remains
worktree-local and unstaged. AEGIS locks byte zero with `msvcrt.locking` on
Windows and uses `fcntl.flock` on POSIX. A process-local reentrant mutex also
serializes threads and permits nested graph operations.

Acquisition is bounded to 15 seconds. A timeout raises the typed
`PERSISTENCE-LOCK-TIMEOUT` error with retry guidance. Lock files are not owner
claims by themselves and are intentionally retained: the operating system
releases a live lock on process exit, after which the existing file can be
locked again safely. AEGIS never deletes a lock based on age or unverifiable
process metadata.

## Graph and Evidence

Every stage, evidence, check, gate, access-mode, and direct graph mutation holds
the run lock across authoritative reload, validation, mutation, atomic graph
publication, and its journal calls. This prevents stale caller-held `Graph`
objects from discarding newer stage or evidence state.

Loaded graphs carry non-serialized source and semantic digests. A direct save
whose source was replaced returns `GRAPH-STALE-UPDATE`. A mutation operation
reloads newer authoritative state when its caller has not also changed the
old in-memory object; competing in-memory and on-disk changes fail closed.

Evidence identifiers retain the public `E-NNNN` format. Allocation uses the
highest existing numeric identifier under the run lock rather than list
length, and duplicate direct additions are refused.

## Journal

Journal publication holds a separate per-run journal lock. The new JSON line is
serialized completely, combined with the existing complete journal, fsynced to
a unique temporary sibling, and atomically replaces the prior journal. This
keeps every visible record as one complete parseable UTF-8 line after
concurrent writes or replacement failure.

Graph and journal are separate files, so no filesystem API can atomically
commit both as one transaction. AEGIS holds the run lock across their ordered
updates, preventing writer interleaving; abrupt termination between the two
publications may still leave one durable record ahead of the other without
truncating either file.

## Requirements

Reads remain lock-free. Creation retains UUID-per-file identity and exclusive
publication.

An update locks only the target requirement, then loads, modifies, validates,
checks linked resources, compares the exact source digest, and atomically
publishes. Cooperative same-requirement writers therefore serialize and apply
their patches to the latest snapshot. If an external writer changes the file
after load, publication returns the typed `REQUIREMENT-STALE-UPDATE` conflict
and preserves the external content.

Requirement-stage batch publication acquires target locks in sorted identity
order, stages every complete file, rechecks source digests, and then performs
atomic per-file replacements.

## RepoWise State

AEGIS RepoWise discovery snapshots use the same exclusive temporary-file,
fsync, replacement, cleanup, and supported directory-durability contract.
WAEGIS writers remain outside this implementation boundary.
