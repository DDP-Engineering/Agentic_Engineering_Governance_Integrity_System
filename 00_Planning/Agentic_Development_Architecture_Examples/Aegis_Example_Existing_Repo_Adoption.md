<!-- Copyright (c) 2026 DDP Engineering. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0 -->

# Example: Existing Repository Adoption

1. WAEGIS 1.0 analyzes explicit scripts, tool configuration, Make targets, and
   CI commands and proposes build/typecheck/lint/test/security gates. It never
   invents a security command.
2. The operator reviews schema-3 interface policy and each gate group, then
   previews and deploys AEGIS 2.x.
3. `aegis run start adoption` prepares adoption intake.
4. The specialized adoption stages use the same prepare/apply/close lifecycle:
   alignment, repository discovery, component map, component adoption,
   baseline review, adoption delivery.
5. Delivery closure records completion without publishing.

An AEGIS 1.x install is not upgraded in place. Preserve intended project-owned
artifacts and deploy a fresh AEGIS 2.x payload.
