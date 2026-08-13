---
name: aegis
description: Resume and guide an AEGIS-governed task through the local workflow.
---

# AEGIS for Claude Code

Resume with `.agentic/aegis/bin/aegis --format json stage-show`. Follow the
returned Stage instruction, common findings, recovery actions, and next actions.
Before any `--input` call, use `help-show` to inspect its `aegis.machine.input`
data contract.

Do not infer approvals, skips, or waivers; record them through the applicable
AEGIS operation. Keep commit, branch, push, merge, and other outward Git actions
outside AEGIS.
