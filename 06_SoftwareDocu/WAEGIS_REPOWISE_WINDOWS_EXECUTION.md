<!--
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt file for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
-->

# WAEGIS RepoWise Windows Execution

## Failure Boundary

WAEGIS builds RepoWise commands as argument arrays and launches them with
`shell=False`. Python's Windows subprocess serialization, the uv console
trampoline, and Python 3.12 argv handling preserve the two managed exclusion
patterns as literal `sys.argv` entries:

```text
.agentic/tools/**
.agentic/runs/**
```

RepoWise 0.37 uses Click. When a Click command starts on Windows without an
explicit argument list, Click enables `windows_expand_args` and performs
shell-style wildcard expansion before it parses options. A matching standalone
pattern therefore becomes one argument per matching file or directory. The
first expansion can still satisfy `--exclude`, but the remaining matches become
unexpected positional arguments. An unmatched pattern remains literal, which
is why an empty fixture or a help-only probe does not reproduce the defect.

## Literal Windows Options

Click accepts both `--option VALUE` and `--option=VALUE`. WAEGIS uses the latter
on Windows for exclusion patterns and other wildcard-capable dynamic Click
values:

```text
--exclude=.agentic/tools/**
--exclude=.agentic/runs/**
```

The option prefix prevents the complete token from matching a filesystem path,
while Click still returns the exact pattern value. This retains array-based
execution, avoids a shell command string, and preserves spaces, embedded
quotes, parentheses, Unicode, drive-qualified paths, and reachable UNC paths.
On POSIX, WAEGIS retains the historical two-token option form because Click
does not perform the Windows expansion there.

## Complete Sidecar Execution

The packaged Windows `repowise.cmd` forwards arguments with `%*`. Its forwarding
preserves the tested literal characters after launch, but `cmd.exe /c` cannot
reliably start the batch file from an argument array when the batch path itself
contains spaces. Managed Complete execution therefore resolves the verified
sidecar's pinned `runtime/python/python.exe` and invokes a static bootstrap with
an argument array. The bootstrap adds only the verified sidecar
`site-packages`, imports the bundled offline socket guard, and runs
`waegis_repowise_bootstrap` in the separate RepoWise process. The batch launcher
remains available as packaged material but is not on WAEGIS's managed Windows
execution path.

External commands remain the configured argument array. Executable and script
paths containing spaces are supported by Windows subprocess serialization;
WAEGIS does not parse or join them into a command string.

## Project-Local Setup Boundary

RepoWise 0.37 unconditionally writes `.mcp.json`, `.vscode/mcp.json`, and
`.vscode/extensions.json` during initialization even when global editor setup
and named agent integrations are disabled. Before launching RepoWise, WAEGIS
captures exact bytes or absence for those paths. It restores them after every
success, nonzero exit, launch error, or interrupt, and removes a newly empty
`.vscode` directory. Unsafe links or non-file collisions fail closed.

Artifact schema validation and receipt creation occur only after successful
process exit and successful restoration. Any indexing or restoration failure
keeps the valid RepoWise policy/runtime configuration, writes no successful
receipt, retains the subprocess log, and reports the exact public resume
command.

## Regression Coverage

The WAEGIS tests use a real child process that emulates Click's matching-glob
pre-parser and contains actual matches below both excluded directories. They
also cover external command/script paths with spaces, shell-free Complete
bootstrap execution, version/capability probes, graph/state validation, receipt
fingerprints and digests, project-local setup restoration, nonzero failures,
and unchanged POSIX command construction.
