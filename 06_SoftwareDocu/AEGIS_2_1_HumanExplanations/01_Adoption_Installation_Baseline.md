<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS Adoption: Installation Baseline

This note explains the first outcome of adopting AEGIS into an existing
repository. It deliberately describes the AEGIS artifacts in general, not the
repository being adopted.

## What adoption creates first

Adoption places the AEGIS payload under a repository-local `.agentic/`
directory. The application source is not moved or rewritten. Instead, AEGIS is
installed beside it as a versioned governance layer.

The initial artifacts that establish this layer are:

| Artifact | What it contains | What it represents |
| --- | --- | --- |
| `.agentic/install-manifest.json` | The payload version, installation time, installation mode, installer version, configuration snapshot, and a SHA-256 checksum and size for each installed payload file. | The installation receipt and baseline inventory. It lets AEGIS tooling determine which files were supplied by the payload and detect later changes. |
| `.agentic/workflow.toml` | Repository-specific locations for source, tests, requirements, knowledge, reports, and components; plus selected governance policies and check commands. | The connection between the generic AEGIS payload and this particular repository. It is the main configuration contract. |
| `.agentic/LICENSE.txt` | The AEGIS payload license text. | The legal terms applying to the copied AEGIS material. |
| `.agentic/cli/` | The local Python AEGIS command-line implementation and its package metadata. | The executable engine that reads the workflow configuration, evaluates rules, and manages AEGIS records. |
| `.agentic/documents/` | User and operator reference material for the installed AEGIS version. | Local documentation that travels with the payload. |
| `.agentic/hooks/` | Optional guard and evidence scripts that integrations can invoke around tool activity. | The enforcement and observation mechanisms that can be wired into supported agent tools. |

## The important distinction

At this point, AEGIS does **not** describe the application's business purpose
or replace its source code. It describes how AEGIS should locate and govern
that source: where work occurs, which checks apply, and where governance
evidence will be stored.

The `install-manifest.json` answers, "What AEGIS payload was installed?" The
`workflow.toml` answers, "How should that payload operate in this repository?"

## What the installation manifest records

The manifest records more than the `files` mapping. Its top-level fields have
the following roles:

| Field | Meaning |
| --- | --- |
| `manifest_version` | The format version of the manifest. |
| `product` | The identity of the installed product: AEGIS. |
| `payload_version` | The exact AEGIS payload release installed. |
| `installed_at` | The installation timestamp in UTC. |
| `installed_by` | The installer name and version, normally WAEGIS. |
| `mode` | The type of installation, such as `adopt`. |
| `files` | Every payload-managed file, with its relative path, SHA-256 checksum, and size at installation time. |
| `generated` | Paths created specifically from the installation configuration rather than copied unchanged from the payload. |
| `skipped` | Optional paths deliberately not overwritten, usually because they already existed or remain repository-owned. |
| `payload_digest` | A single checksum representing the complete installed payload inventory. |
| `configuration` | The installation decisions used to generate and configure the local AEGIS deployment. |

The `configuration` object contains:

| Field | Meaning |
| --- | --- |
| `answers` | The selected repository mappings and policy settings. Its individual fields are described below. |
| `generator_version` | The WAEGIS version that generated configuration-driven files. |
| `generated_files` | Checksums for individual files generated from the recorded answers, such as the workflow configuration and optional integration configuration. |
| `repowise` | Optional Repowise integration settings: source, profile, local endpoint, models, and enforcement mode. |

### Configuration answers

| Field | Meaning |
| --- | --- |
| `alignment_enabled` | Enables the alignment stage, where AEGIS checks that the proposed work is understood before it proceeds. |
| `alignment_protected_scope_mode` | Sets whether alignment protects selected paths. `disabled` means no path-specific alignment protection is active. |
| `alignment_protected_scope_patterns` | The repository-relative path patterns protected by the alignment scope rule. An empty list selects no paths. |
| `baseline_guard_mode` | Sets the enforcement level for the adoption baseline guard. `disabled` means the guard is inactive. |
| `baseline_minimum_completion_level` | The minimum adoption completion state expected before the baseline is considered usable. |
| `check_execution` | Chooses who runs configured checks. `external` means AEGIS records and evaluates externally run commands rather than directly executing them. |
| `coverage_exclude` | Path patterns excluded from requirement-to-test coverage evaluation. |
| `coverage_mode` | Sets whether coverage mapping is disabled, advisory, or enforced. |
| `coverage_roots` | Source paths whose code is considered when evaluating coverage. |
| `delivery_command_patterns` | Command patterns subject to delivery control. An empty list means no commands are selected. |
| `delivery_mode` | Sets whether delivery command control is disabled, advisory, or enforced. |
| `gate_build_cmds` | Commands used for the build gate. |
| `gate_build_mode` | Sets whether the build gate is disabled, advisory, or enforced. |
| `gate_lint_cmds` | Commands used for the lint gate. |
| `gate_lint_mode` | Sets whether the lint gate is disabled, advisory, or enforced. |
| `gate_security_cmds` | Commands used for the security gate. |
| `gate_security_mode` | Sets whether the security gate is disabled, advisory, or enforced. |
| `gate_test_cmds` | Commands used for the test gate. |
| `gate_test_mode` | Sets whether the test gate is disabled, advisory, or enforced. |
| `gate_typecheck_cmds` | Commands used for the type-checking gate. |
| `gate_typecheck_mode` | Sets whether the type-checking gate is disabled, advisory, or enforced. |
| `language` | The primary implementation language used to apply language-specific traceability conventions. |
| `protected_path_operations` | The operations restricted for paths selected by the protected-path rule. |
| `protected_path_patterns` | Repository-relative path patterns selected by the protected-path rule. |
| `protected_paths_mode` | Sets whether protected-path control is disabled, advisory, or enforced. |
| `scope_allowed_roots` | Repository-relative roots in which changes are allowed when scope control is active. |
| `scope_mode` | Sets whether work scope is unrestricted, advisory, or enforced. |
| `secret_patterns` | Regular expressions used to detect likely credentials or private keys. |
| `secrets_mode` | Sets whether secret detection is disabled, advisory, or enforced. |
| `source_changes_mode` | Sets how source changes are treated during adoption. `blocked` prevents source changes as part of the adoption baseline. |
| `source_roots` | Repository-relative directories containing production source code. |
| `stage_form_retention` | Specifies how stage forms are retained. `versioned` keeps them as versioned repository records. |
| `test_roots` | Repository-relative directories containing automated tests. |
| `working_tree_blocked_patterns` | Path patterns that must not be changed when working-tree control is active. |
| `working_tree_mode` | Sets whether the working tree is unrestricted, advisory, or enforced. |
| `write_access_mode` | Sets whether stage-specific write access is unrestricted, advisory, or enforced. |
| `write_access_stages` | The allowed write locations for each workflow stage. The keys cover the normal delivery stages (`intake`, `alignment`, `requirement`, `design`, `check`, `implementation`, `validation`, and `delivery`) and adoption stages (`adoption-intake`, `adoption-alignment`, `repo-discovery`, `component-map`, `component-adoption`, `baseline-review`, and `adoption-delivery`). An empty list for a stage gives that stage no additional configured write roots. |

### Generated files

Each `generated_files` entry uses the generated file's repository-relative path
as its key and contains:

| Field | Meaning |
| --- | --- |
| `sha256` | SHA-256 checksum of the generated file immediately after installation. |

### Repowise settings

| Field | Meaning |
| --- | --- |
| `schema_version` | The format version of the Repowise configuration. |
| `source` | Selects the configured Repowise source or provider. |
| `profile` | Selects the Repowise execution/profile behavior. |
| `ollama_url` | Local Ollama service address, when the selected setup uses Ollama. |
| `model` | Optional model identifier for Repowise analysis. |
| `embedding_model` | Optional embedding-model identifier used for semantic indexing or retrieval. |
| `enforcement` | Sets whether Repowise results are advisory or enforced. |

The manifest is therefore both an installation inventory and a durable record
of the installation decisions.

The next adoption explanation should cover the working folders under
`.agentic/` (requirements, knowledge, components, reports, runs, and related
records) and the type of evidence each holds.
