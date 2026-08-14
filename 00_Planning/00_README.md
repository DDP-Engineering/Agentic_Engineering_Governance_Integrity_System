<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details.
SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# AEGIS plan overview

Status: **implemented**. The product is at `05_Software/aegis/`; its user
documentation is in `06_SoftwareDocu/`. This directory retains the design
record. Where it differs from the payload, the payload is authoritative.

AEGIS provides a staged, advisory workflow. Its single standard-library CLI
scaffolds durable artifacts and reports traceability and quality findings. The
workflow is defined in `AGENTS.md` and the per-stage instructions, making it
usable by both frontier and constrained local coding agents.

## Design principles

1. Guidance over enforcement.
2. Plain files and Git history provide durable state and collaboration.
3. One artifact per file keeps parallel work merge-friendly.
4. The default check is advisory; teams may opt into `--strict` in CI.
5. The workflow is small, portable, offline-friendly, and interruptible.
