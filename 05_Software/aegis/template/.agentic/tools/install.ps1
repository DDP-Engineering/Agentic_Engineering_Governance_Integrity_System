<#
Copyright (c) 2026 DDP Engineering
This software is licensed under the PolyForm Noncommercial License 1.0.0.
Commercial use requires a separate commercial license.
See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0
#>

param(
    [switch] $UseUv
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# @brief Root of the target repository after the template is transboarded.
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir "..\..")
# @brief Embedded CLI package installed by this helper.
$CliRoot = Join-Path $ProjectRoot ".agentic\cli"
# @brief Local virtual environment owned by AEGIS.
$VenvRoot = Join-Path $ProjectRoot ".agentic\.venv"

# @brief Resolve a Python launcher available on PATH.
# @return Command name for Python, or $null when no supported launcher exists.
function Resolve-Python {
    $candidates = @("python", "py")
    foreach ($candidate in $candidates) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -ne $command) {
            return $candidate
        }
    }
    return $null
}

$Uv = Get-Command "uv" -ErrorAction SilentlyContinue

# Native tools (uv, python, pip) write routine progress to stderr. Under
# Windows PowerShell 5.1, $ErrorActionPreference = "Stop" promotes any stderr
# output from a native command into a terminating NativeCommandError even when
# the process exits 0 (B23) - so relax it for the duration of each native
# call and rely on $LASTEXITCODE, which is what actually reflects success.
$ErrorActionPreference = "Continue"

if ($UseUv -or $null -ne $Uv) {
    if ($null -eq $Uv) {
        $ErrorActionPreference = "Stop"
        Write-Error "uv was requested but was not found. Install uv or run without -UseUv."
    }
    & uv venv --python 3.11 $VenvRoot
    & uv pip install --python (Join-Path $VenvRoot "Scripts\python.exe") -e $CliRoot
    $ExitCode = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    exit $ExitCode
}

$Python = Resolve-Python
if ($null -eq $Python) {
    $ErrorActionPreference = "Stop"
    Write-Error "Python 3.11+ was not found. Install Python 3.11+ or install uv, then rerun this script."
}

& $Python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    $ErrorActionPreference = "Stop"
    Write-Error "Python 3.11+ is required. Install Python 3.11+ or install uv, then rerun this script."
}

& $Python -m venv $VenvRoot
$VenvPython = Join-Path $VenvRoot "Scripts\python.exe"
& $VenvPython -m pip install -e $CliRoot
$ExitCode = $LASTEXITCODE
$ErrorActionPreference = "Stop"
exit $ExitCode
