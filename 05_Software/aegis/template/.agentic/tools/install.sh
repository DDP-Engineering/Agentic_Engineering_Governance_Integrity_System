#!/usr/bin/env bash
# Copyright (c) 2026 DDP Engineering
# This software is licensed under the PolyForm Noncommercial License 1.0.0.
# Commercial use requires a separate commercial license.
# See the LICENSE.txt in the .agentic folder for full license details. SPDX-License-Identifier: LicenseRef-PolyForm-Noncommercial-1.0.0

set -euo pipefail

# @brief Directory containing this installer after transboarding.
# @details Resolved with parameter expansion rather than `dirname`, matching
#          `run.sh`. `dirname` is an external binary, so an empty or minimal
#          `PATH` makes the substitution yield nothing and `SCRIPT_DIR` collapse
#          to the caller's working directory. `cd` and `pwd` are builtins.
_aegis_source="${BASH_SOURCE[0]}"
_aegis_dir="${_aegis_source%/*}"
[ "$_aegis_dir" = "$_aegis_source" ] && _aegis_dir="."
SCRIPT_DIR="$(cd -- "$_aegis_dir" && pwd)"
unset _aegis_source _aegis_dir
# @brief Root of the target repository after the template is transboarded.
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
# @brief Embedded CLI package installed by this helper.
CLI_ROOT="$PROJECT_ROOT/.agentic/cli"
# @brief Local virtual environment owned by AEGIS.
VENV_ROOT="$PROJECT_ROOT/.agentic/.venv"

# @brief Resolve a Python launcher available on PATH.
# @return Absolute path to a Python command, or a non-zero status when missing.
resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

# @brief Print the platform-specific Python executable inside the local venv.
venv_python() {
  if [ -x "$VENV_ROOT/Scripts/python.exe" ]; then
    printf '%s' "$VENV_ROOT/Scripts/python.exe"
  else
    printf '%s' "$VENV_ROOT/bin/python"
  fi
}

# @brief Convert an MSYS path before passing it to a native Windows executable.
native_path() {
  if [ "${OS:-}" = "Windows_NT" ] && command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s' "$1"
  fi
}

if command -v uv >/dev/null 2>&1; then
  uv venv --clear --python 3.11 "$(native_path "$VENV_ROOT")"
  uv pip install --python "$(native_path "$(venv_python)")" -e "$(native_path "$CLI_ROOT")"
  exit 0
fi

PYTHON_BIN="$(resolve_python || true)"
if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3.11+ was not found. Install Python 3.11+ or install uv, then rerun this script." >&2
  exit 2
fi

"$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Python 3.11+ is required. Install Python 3.11+ or install uv, then rerun this script." >&2
  exit 2
}

"$PYTHON_BIN" -m venv --clear "$(native_path "$VENV_ROOT")"
"$(venv_python)" -m pip install -e "$(native_path "$CLI_ROOT")"
