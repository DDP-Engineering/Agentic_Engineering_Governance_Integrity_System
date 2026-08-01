<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Maintenance, Upgrades, Transactions, and Legacy History

This guide explains how WAEGIS safely maintains an installed AEGIS payload.
Maintenance is different from an AEGIS workflow run: WAEGIS changes the
installed governance system itself, while AEGIS records work performed under
that system.

## Maintenance operations

| Operation | What it reads or changes | Performed by | Why it exists |
| --- | --- | --- | --- |
| `waegis analyze --repo <path>` | Reads a repository to propose source/test roots, technology, and available commands. | WAEGIS, read-only. | Helps configure an existing repository from observed facts instead of invented commands. |
| `waegis doctor --repo <path>` | Reads installation health: manifest validity and drift, workflow configuration, adapter/runability checks, and pending transactions. | WAEGIS, read-only. | Identifies whether AEGIS is installed and usable before a workflow relies on it. |
| `waegis configure --repo <path>` | Updates generated local configuration, such as `workflow.toml` and selected integration policy. | WAEGIS with explicit operator approval. | Lets the repository change governance configuration while preserving an auditable installation record. |
| `waegis repair --repo <path>` | Restores eligible missing or damaged payload material without treating local configuration as a generic copied file. | WAEGIS with explicit operator approval. | Repairs a known installation while protecting repository-owned data. |
| `waegis upgrade --repo <path>` | Compares the installed manifest with a selected newer payload and applies the approved upgrade plan. | WAEGIS with explicit operator approval. | Updates AEGIS code, adapters, hooks, skills, and documentation safely. |
| `waegis adopt <path>` | Installs AEGIS into an existing repository that has no valid current manifest. | WAEGIS with explicit operator approval. | Creates a valid current installation baseline; an upgrade is not allowed without one. |
| `waegis repowise status` / `sync` | Reads or refreshes optional Repowise state under explicit integration policy. | WAEGIS and optional Repowise tooling. | Maintains optional discovery evidence without making it implicit authority. |

Mutating commands show a plan and require explicit approval (`--yes` for a
non-interactive operation). `--dry-run` remains read-only: it reports proposed
work but does not create a transaction, change files, or recover a pending
transaction.

## Installation health and drift

The install manifest defines the payload baseline. WAEGIS compares managed
paths with the `files` hashes and sizes in `install-manifest.json` to determine
whether an installed payload file has changed, disappeared, or remains intact.

| State | Meaning | Appropriate response |
| --- | --- | --- |
| Clean | A managed payload file matches its recorded hash and size. | Normal operation. |
| Drifted | A managed payload file no longer matches its recorded baseline. | Inspect the change; use supported repair or upgrade only when the intended outcome is clear. |
| Generated file changed | A configuration-generated file differs from its original generated hash. | This can be an intentional local policy change; review it as local configuration, not payload drift to overwrite blindly. |
| Skipped file exists | An optional repository-owned path was deliberately not overwritten during install. | Preserve it unless the operator consciously changes ownership. |
| Missing/invalid manifest | The repository may be a legacy pre-manifest installation or be damaged. | Use `waegis doctor` and normally adopt rather than attempting an ordinary upgrade. |

The point of this distinction is safety: WAEGIS can update its own payload
without overwriting configuration or project material that the repository owns.

## Transaction records

Every mutating WAEGIS operation uses a persistent transaction. Transaction
state lives below:

```text
.agentic/.waegis-transactions/
```

This location may be absent when no operation is in progress or after a fully
cleaned successful operation. It may remain after interruption, failure, or a
recovery condition. It is operational state, not ordinary AEGIS workflow
evidence.

| Transaction data | Created by | Why it is needed |
| --- | --- | --- |
| Version and transaction ID | WAEGIS. | Identifies the transaction and allows strict schema validation. |
| Command and UTC creation time | WAEGIS. | Records which operation began and when. |
| Phase | WAEGIS. Supported phases are `staged`, `applying`, `verified`, `committed`, and `rolled-back`. | Lets recovery determine whether rollback or cleanup is safe. |
| Entries | WAEGIS. Each entry names a canonical repository-relative destination and records prior existence, backup details when applicable, byte size, and SHA-256 digest. | Allows exact recovery of only the files the transaction touched. |
| Backups | WAEGIS. Stored under transaction-controlled paths with generated names. | Preserves pre-mutation file content for verified rollback. |
| Key identifier and MAC | WAEGIS, using a secret key kept outside the repository. | Detects altered transaction state before it can direct recovery. |

WAEGIS also maintains authenticated ownership information and process locks in
its protected per-user WAEGIS home. The ownership record binds a transaction to
the resolved repository and immutable operation digest; locks prevent two
processes from applying or recovering the same repository concurrently.

The transaction mechanism exists to make payload/configuration changes
recoverable. It publishes the new install manifest last, after the deployment
has been applied and verified. A failed smoke verification or interruption can
therefore roll the changed destinations back rather than leaving a partly
installed payload treated as complete.

## Recovery rules

WAEGIS validates pending state before changing any destination. It requires
valid schemas, matching transaction and ownership records, the expected
external authentication key, contained real directories, regular state and
backup files, and matching backup sizes/digests.

| Situation | WAEGIS behavior | Operator responsibility |
| --- | --- | --- |
| `staged`, `applying`, or `verified` transaction | Reports/requires recovery approval; can roll back only after validation. | Review the reported plan and approve recovery only when appropriate. |
| `rolled-back` transaction | Performs cleanup only; rollback is idempotent. | Confirm cleanup completed. |
| `committed` transaction | Performs cleanup only; it is never rolled back. | Inspect the deployed result if cleanup was interrupted. |
| Malformed, altered, unowned, link-directed, incomplete, or legacy version-1 state | Fails closed and preserves state as evidence. | Make a repository copy, inspect the state/backups, restore only verified intended paths, then remove state only after the repository is known good. |

Do not edit, move, or delete transaction state to “make the error go away.” A
pending transaction is evidence needed to recover safely. `waegis doctor` and a
read-only dry run are the correct first inspections.

## Payload upgrade behavior

An upgrade requires a valid current installation manifest. WAEGIS uses it to
classify every payload path and produce an upgrade plan. The plan can update
managed payload code, adapters, hooks, skills, and payload documentation while
preserving repository-local generated configuration such as `workflow.toml`.

| Artifact class | Normal upgrade treatment | Reason |
| --- | --- | --- |
| Payload-managed file in `files` | Compared to its manifest baseline and updated through the transaction plan when eligible. | Keeps the installed AEGIS release coherent. |
| Generated file in `generated` | Preserved as local configuration unless a supported configuration operation regenerates it. | Prevents a payload upgrade from silently discarding local policy. |
| Skipped/repository-owned file | Left under repository control. | WAEGIS did not claim ownership at install time. |
| New payload-only file | Added through the approved plan. | Delivers new AEGIS capability. |
| Removed payload file | Removed only when the transaction plan and policy allow it. | Keeps the payload inventory aligned while retaining rollback capability. |

After an upgrade, run `waegis doctor` and confirm that the relevant host adapter
is still active. Some hosts require the project or changed hooks to be trusted
again before their guard layer runs.

## Legacy history

“Legacy” has two different meanings and they should not be confused.

| Legacy case | Represents | Who handles it | Why it is retained or detected |
| --- | --- | --- | --- |
| Pre-manifest AEGIS installation | `.agentic/` exists but no valid current install manifest exists. | WAEGIS detects it during doctor/adopt. | Prevents an ordinary upgrade from guessing ownership or overwriting an unknown installation. |
| Historical project records | Repository-owned archives, previous AEGIS run exports, or prior-version material, often kept under a project `legacy/` area. | Repository operator and reviewers. | Preserves audit context; current AEGIS runs do not automatically resume or rewrite these records. |
| Legacy transaction state | Earlier or unsupported transaction format. | WAEGIS detects it and fails closed. | Prevents unauthenticated or incomplete transaction data from controlling recovery. |

Historical material is read-only audit context unless a human explicitly
decides otherwise. Do not mix it with current `.agentic/runs/` records: current
run schemas and lifecycle checks apply only to the active AEGIS version.

## Ownership summary

- **WAEGIS** owns installation, manifest-aware maintenance, transactions,
  repair, upgrade, and recovery logic.
- **AEGIS** owns current workflow runs and the evidence created within them.
- **Repository operators** approve mutations, choose policy, inspect drift, and
  decide how historical project records are retained.
- **Humans** must resolve ambiguous, malformed, or legacy transaction state;
  WAEGIS intentionally refuses to guess in those cases.
