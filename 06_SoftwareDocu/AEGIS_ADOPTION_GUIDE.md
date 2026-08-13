<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# Adopting AEGIS with WAEGIS

## Purpose

This guide explains how to install and begin using AEGIS in a software
repository on Windows or Linux. It is written for a developer who has received
a WAEGIS distribution archive.

> **Keep all WAEGIS installation artifacts outside the target repository.**
> Do not copy or extract the WAEGIS archive inside the repository that will
> receive AEGIS. Keep the archive, extracted WAEGIS directory, lifecycle JSON
> plans, installer logs, and other temporary installation files in an external
> operator-controlled directory. Otherwise those files become part of the
> target state WAEGIS must authorize and may make a plan stale or add unrelated
> files to the project's Git changes.

WAEGIS is the installer and lifecycle utility. Its archive already contains the
AEGIS payload, so a separate AEGIS archive is not required. WAEGIS remains
outside the target repository; it copies the managed AEGIS payload into the
repository and creates missing host guidance. Existing host-specific starter
files remain unchanged. A root `AGENTS.md` is handled specially: WAEGIS adds a
small marked AEGIS bridge before existing UTF-8 guidance and retains the
project's complete document as the continuation.

Running WAEGIS without a command starts its guided setup. The wizard explains
the current state and asks before every consequential step. It preserves the
same reviewable lifecycle sequence internally:

1. create a JSON plan;
2. inspect the plan and its digest;
3. apply that exact plan by confirming its digest.

The examples use placeholders such as `<WAEGIS_DIR>`, `<TARGET_REPOSITORY>`,
`<PLAN_DIR>`, and `<PLAN_DIGEST>`. Replace each placeholder, including the angle
brackets, with a real path or value. The wizard stores its lifecycle plan beside
the target repository, not inside it.

## 1. Obtain and extract WAEGIS

Choose the archive built for the operating system and runtime model in use.
An external-runtime archive relies on the prerequisites listed inside it. A
bundled-runtime archive carries its private runtime dependencies.

Extract WAEGIS into an operator-controlled tools directory that is not inside
the target repository. Do not use a project subdirectory such as `tools`,
`other`, `misc`, or `downloads` for the archive or extracted distribution.

### Windows Explorer

1. Copy the WAEGIS archive to the computer.
2. Right-click the archive.
3. Select **Extract All**.
4. Choose a tools directory and complete the extraction.

### Windows Command Prompt

Create the destination directory and extract the archive with the Windows
`tar` command:

```cmd
mkdir "<WAEGIS_DIR>"
tar -xf "<PATH_TO_WAEGIS_ARCHIVE>" -C "<WAEGIS_DIR>"
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force -Path "<WAEGIS_DIR>"
Expand-Archive -LiteralPath "<PATH_TO_WAEGIS_ARCHIVE>" -DestinationPath "<WAEGIS_DIR>"
```

### Linux shell

```bash
mkdir -p "<WAEGIS_DIR>"
unzip "<PATH_TO_WAEGIS_ARCHIVE>" -d "<WAEGIS_DIR>"
chmod +x "<WAEGIS_DIR>/bin/waegis"
```

## 2. Read and verify the prerequisites

The archive's `PREREQUISITES.md` is authoritative for that package. Read it
before running WAEGIS.

### Windows Command Prompt

```cmd
cd /d "<WAEGIS_DIR>"
type PREREQUISITES.md
```

For an external-runtime package, verify the listed Python and Git commands. For
example:

```cmd
py -3.12 --version
git --version
```

### Windows PowerShell

```powershell
Set-Location "<WAEGIS_DIR>"
Get-Content PREREQUISITES.md
py -3.12 --version
git --version
```

### Linux shell

```bash
cd "<WAEGIS_DIR>"
cat PREREQUISITES.md
python3.12 --version
git --version
```

Use the commands named by `PREREQUISITES.md` if they differ from these
examples. A bundled-runtime package may not require a system Python or Git.

## 3. Start the guided setup

Run WAEGIS from the extracted directory without a command. This starts the
interactive setup for a new installation or an upgrade.

### Windows

```cmd
cd /d "<WAEGIS_DIR>"
bin\waegis.cmd
```

### Linux

```bash
cd "<WAEGIS_DIR>"
./bin/waegis
```

The wizard begins with:

```text
Welcome to WAEGIS

This wizard installs or upgrades AEGIS in a software repository.
You can cancel safely at any prompt before applying a plan.
```

Enter the absolute path of the repository that will receive AEGIS. Do not enter
the WAEGIS tools directory.

```text
Repository path: <TARGET_REPOSITORY>
```

## 4. Let WAEGIS inspect the environment

WAEGIS asks whether it should check the active runtime and repository:

```text
Check runtime and repository prerequisites? [Y/n]
```

Press Enter or answer `Y`. WAEGIS then reports:

- whether the active Python runtime is compatible;
- whether Git is available;
- the resolved target path;
- whether the target is already a Git repository;
- whether AEGIS is already installed.

Stop and correct any reported prerequisite problem before continuing.

If the target is not a Git repository, WAEGIS can create a separate
repository-initialization plan. It does not run `git init` until the developer
reviews and explicitly applies that plan. This action is local: it does not
commit files or contact a remote repository.

If AEGIS is absent, the wizard selects installation. If AEGIS is already
present, it selects upgrade automatically.

## 5. Create and inspect the plan

The wizard proposes an external plan path beside the target repository:

```text
Create the installation plan at <EXTERNAL_PLAN_PATH>? [Y/n]
```

For an existing installation, the prompt names an AEGIS upgrade plan instead.
Press Enter or answer `Y` to create it. Planning does not change the target
repository.

WAEGIS reports the plan file, number of actions, findings, and exact digest.
Review every finding carefully. In particular, confirm that WAEGIS detected the
real project test directories and the correct test framework.

WAEGIS then asks:

```text
Review the individual planned actions now? [y/N]
```

Answer `Y` when adopting AEGIS for the first time. WAEGIS shows actions in
bounded pages whose headings state the exact displayed range and total. Review
the paths, action kinds, and ownership labels. Continue through the pages when
prompted. A complete review ends with an explicit statement that every action
number was displayed; an early stop instead names the last displayed action.

Do not edit the JSON plan. If the target, detected configuration, findings, or
actions are incorrect, answer `N`, correct the underlying situation, and start
the wizard again to create a new plan.

## 6. Explicitly authorize installation

After review, WAEGIS asks:

```text
Apply this exact plan? [y/N]
```

The safe default is `N`. Answer `Y` only after reviewing the target, findings,
actions, and digest. WAEGIS supplies that exact digest to the existing apply
operation and refuses the installation if either the plan or meaningful target
state changed after planning.

Canceling at this prompt does not install AEGIS. The external plan remains
available for inspection. WAEGIS does not commit or push an accepted
installation.

## 7. Follow the displayed verification commands

After a successful installation or upgrade, the wizard prints the exact
platform-appropriate commands for the target. Run those commands as displayed.
They verify the managed AEGIS payload and evaluate the project-owned
configuration.

The commands have this general form:

### Windows

```cmd
cd /d "<TARGET_REPOSITORY>"
.agentic\aegis\bin\aegis.cmd payload-verify
.agentic\aegis\bin\aegis.cmd config-validate
```

### Linux

```bash
cd "<TARGET_REPOSITORY>"
./.agentic/aegis/bin/aegis payload-verify
./.agentic/aegis/bin/aegis config-validate
```

`payload-verify` checks the WAEGIS-owned runtime payload. `config-validate`
evaluates project-owned configuration and reports advisory findings when
something needs attention. A finding is guidance and recorded evidence, not
permission for AEGIS to delete project work or silently rewrite the repository.

## 8. Perform additional installed checks

The following optional commands show the installed version, configuration, and
complete AEGIS operation catalog.

### Windows

```cmd
.agentic\aegis\bin\aegis.cmd version-show
.agentic\aegis\bin\aegis.cmd config-show
.agentic\aegis\bin\aegis.cmd help-show
```

### Linux

```bash
./.agentic/aegis/bin/aegis version-show
./.agentic/aegis/bin/aegis config-show
./.agentic/aegis/bin/aegis help-show
```

## 9. Review and record the installation

Inspect the repository changes before committing them.

### Windows or Linux

```text
git -C <TARGET_REPOSITORY> status --short
git -C <TARGET_REPOSITORY> diff
```

The `.agentic/aegis/` directory is the manifest-owned runtime payload. Other
`.agentic/` content is project-owned workflow state and knowledge. Host starter
files outside `.agentic/aegis/` are also project-owned: WAEGIS creates them only
when missing and does not replace existing host instructions. The root
`AGENTS.md` remains project-owned; WAEGIS creates it when missing or prefixes
one bounded AEGIS bridge while retaining existing guidance below it.

Commit the reviewed installation through the project's normal Git workflow.
Pushing remains a separate developer decision.

## 10. Begin using AEGIS

Open the repository with the supported coding agent or development host. The
installed host guidance teaches the agent how to use the canonical AEGIS
operations. Start with the installed `help-show` operation whenever command
syntax or available capabilities are unclear.

AEGIS is a development companion. Its purpose is to guide and record the work
so the developer and agent share the same understandable history. Advisory
findings should explain gaps and recovery actions; they should not be treated as
an excuse to block ordinary development.

For a new change, the normal flow is:

1. create or select a Run;
2. record intent and scope;
3. link or create relevant requirements and component knowledge;
4. progress through the applicable engineering Stages;
5. record tests, findings, decisions, and exceptions as they occur;
6. review the Delivery record with the developer.

Small changes may use the product's shorter profile. Stages can be skipped or
revisited with explicit reasons where the workflow permits. Use the structured
operations advertised by `help-show` rather than editing runtime-owned state by
hand.

## 11. Upgrade an existing AEGIS installation

Extract the new WAEGIS distribution into its own external operator directory.
Do not copy a new payload over the existing installation.

Launch WAEGIS without arguments and enter the target repository as described
in section 3. WAEGIS detects the existing manifest and automatically changes
the guided operation from installation to upgrade. Review and approve the new
upgrade plan using the same process described in sections 5 and 6, then run the
verification commands printed by the wizard.

## 12. Advanced manual lifecycle commands

The guided setup is the normal path for a developer adopting or upgrading
AEGIS. Flat commands remain available for explicit command-by-command control,
agents, and automation.

Every manual mutation must still use plan, review, and exact-digest apply:

### Windows installation example

```cmd
bin\waegis.cmd install-plan --target "<TARGET_REPOSITORY>" --output "<PLAN_DIR>\install.json"
bin\waegis.cmd plan-show --plan "<PLAN_DIR>\install.json"
bin\waegis.cmd install-apply --target "<TARGET_REPOSITORY>" --plan "<PLAN_DIR>\install.json" --confirm-digest "<PLAN_DIGEST>"
```

### Linux installation example

```bash
./bin/waegis install-plan --target "<TARGET_REPOSITORY>" --output "<PLAN_DIR>/install.json"
./bin/waegis plan-show --plan "<PLAN_DIR>/install.json"
./bin/waegis install-apply --target "<TARGET_REPOSITORY>" --plan "<PLAN_DIR>/install.json" --confirm-digest "<PLAN_DIGEST>"
```

Manual repository initialization uses `repository-init-plan` and
`repository-init-apply`; manual upgrades use `upgrade-plan` and
`upgrade-apply`. Use `plan-show --offset <N> --limit <N>` when a plan contains
more actions than one page.

If WAEGIS reports that a plan is stale or the target state conflicts with it,
do not force the operation. Inspect the target and generate a fresh plan.

## 13. Remove the managed AEGIS payload

Removal is currently an explicit flat-command workflow. It also uses a reviewed
plan and exact digest confirmation.

### Windows

```cmd
bin\waegis.cmd remove-plan --target "<TARGET_REPOSITORY>" --output "<PLAN_DIR>\remove.json"
bin\waegis.cmd plan-show --plan "<PLAN_DIR>\remove.json"
bin\waegis.cmd remove-apply --target "<TARGET_REPOSITORY>" --plan "<PLAN_DIR>\remove.json" --confirm-digest "<PLAN_DIGEST>"
```

### Linux

```bash
./bin/waegis remove-plan --target "<TARGET_REPOSITORY>" --output "<PLAN_DIR>/remove.json"
./bin/waegis plan-show --plan "<PLAN_DIR>/remove.json"
./bin/waegis remove-apply --target "<TARGET_REPOSITORY>" --plan "<PLAN_DIR>/remove.json" --confirm-digest "<PLAN_DIGEST>"
```

Removal deletes only the manifest-owned AEGIS payload. Project-owned workflow
state, knowledge, configuration support files, and host guidance are preserved.
Review the removal plan to confirm the exact boundary before applying it.

## 14. Troubleshooting and safe recovery

- **Missing prerequisite:** Read the packaged `PREREQUISITES.md` and make the
  required executable available to the launcher.
- **Target is not a Git repository:** Allow the wizard to create and review a
  separate local Git-initialization plan, or initialize it through the
  project's normal Git process.
- **AEGIS is already installed:** Launch the wizard normally; it automatically
  selects upgrade.
- **Plan digest mismatch:** Do not edit the plan or guess the digest. Start the
  wizard again to generate and review a new plan.
- **Target state conflict:** Something meaningful changed after planning.
  Review the repository and generate a fresh plan.
- **Incorrect test discovery:** Do not apply the plan. Correct the repository
  layout or report the unsupported layout, then generate a new plan.
- **Existing host guidance:** WAEGIS preserves host-specific starter files. For
  a UTF-8 root `AGENTS.md`, it proposes one marked AEGIS bridge and retains the
  existing instructions as the continuation. Obstructed, unreadable, or
  non-UTF-8 root guidance is preserved and reported for manual reconciliation.
- **Advisory validation findings:** Read the finding and proposed next action.
  Correct, explain, waive, or defer it according to the actual engineering
  situation; do not erase useful project state merely to make a report empty.
