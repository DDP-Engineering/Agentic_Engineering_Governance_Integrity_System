<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Maintaining and Upgrading AEGIS 3

WAEGIS 3 maintains only installations with its valid schema-2 receipt at
`.agentic/install-manifest.json`. The receipt records exact payload identity,
baseline hashes, and one ownership disposition per path.

The shipped generated-policy default remains
`stage_form_retention = "latest"`; an upgrade preserves the current generated
workflow, and only an explicit `waegis configure` changes WAEGIS-owned fields.

## Ownership classes

| Disposition | Maintenance authority |
|---|---|
| `managed` | WAEGIS may repair or three-way-upgrade the path. |
| `generated` | Only `waegis configure` may regenerate owned policy fields. |
| `seeded` | Created only when absent, then project-owned. |
| `kept-local` | Project bytes retained by an explicit conflict decision. |
| `sidecar` | Payload review copy beside a retained local path. |

Requirements, specifications, components, knowledge, reports, runs, workspace
state, generated policy, and retained conflicts are not generic managed files.

## Health and repair

```text
waegis check --repo PATH
waegis repair --repo PATH --dry-run
waegis repair --repo PATH --yes
```

`doctor` is an alias for `check`. Check is read-only and reports manifest,
drift, wrapper, configuration, hook/adapter, Node, repository-root, version,
and runtime-pointer findings. Repair restores only approved missing/drifted
`managed` paths and publishes the updated manifest after AEGIS validation.

## AEGIS 3 upgrade

```text
waegis upgrade --repo PATH --payload NEW_PAYLOAD --dry-run
waegis upgrade --repo PATH --payload NEW_PAYLOAD --yes
```

The new payload must be strictly newer and inside `>=3.0.0,<4.0.0`. WAEGIS
compares installed baseline, current bytes, and new payload for every managed
path. Unambiguous add/replace/remove/converge outcomes are planned directly;
true conflicts require keep-local, take-payload, or sidecar. Project-owned
dispositions remain project-owned. The new manifest is written only after the
copied AEGIS wrapper passes validation and smoke.

Existing-repository mutations require a clean tree and unchanged planned HEAD.
WAEGIS prints exact path-scoped Git recovery commands before writing. Handled
failures execute them; after a hard kill, run the already printed commands and
break only the confirmed dead-owner lock. WAEGIS creates no transaction
directory, branch, stage, or commit.

## Legacy and cross-major cases

A WAEGIS 1 receipt is detected only for guidance. Use `waegis adopt`,
explicitly acknowledge migration, and resolve each differing path through the
normal conflict rules. WAEGIS never loads or trusts WAEGIS 1 ownership,
answers, transaction, or runtime data.

AEGIS 2, AEGIS 4, invalid manifests, absent manifests, and same/older payloads
cannot enter the WAEGIS 3 upgrade path. Preserve project-owned material and
establish a supported AEGIS 3 schema-2 baseline through `adopt` where
appropriate; never manufacture or hand-edit a receipt to bypass this boundary.

Historical workflow records remain audit material. A run created by an
incompatible AEGIS schema should be completed or abandoned with its original
tooling rather than rewritten to appear current.
