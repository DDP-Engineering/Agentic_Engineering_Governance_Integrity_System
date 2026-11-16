# Agent integrations

Host-specific packages for OpenCode, Codex, Pi, Qwen Code and Claude Code share the installed-AEGIS adapter, tracked verification worker, runtime discovery and owned-file installation logic.

- `opencode/`: primary agent, reviewers, commands, typed tools and loader installation.
- `codex/`: local marketplace, native plugin skill, review roles, command bridge and Codex CLI registration.
- `pi/`: native commands/tools, workflow skill, fresh reviewer launcher and auto-discovery installation.
- `qwen/`: native extension resources, two review agents, local MCP server and auto-discovery installation.
- `claude/`: native marketplace, commands/skill/review agents, hooks, MCP and owned installation.
- `shared/`: reusable implementation copied into each standalone build.
- `tests/`: executable Node behavior checks, included in the repository pytest suite through `test_agent_integrations.py` and `test_additional_integrations.py`.

Reviewer prompts share the same evidence procedure across hosts: read the full
named current journal and linked checkout files, include untracked scope, and
separate focused proof due at review from final full proof after approvals.
Incomplete final-stage checklists alone are not review defects. Candidate-binding
operations retain each host's existing permissions and coordinator ownership.

Build from the repository root with `node 02_Tools/build_agent_plugins.mjs`. Source directories are not complete installable distributions until the builder copies the shared implementation into each package. See [Agent plugins](../../../06_SoftwareDocu/Agent_Plugins.md) for installation, distribution, behavior and verified limits.
