@echo off
setlocal
set "BIN_DIR=%~dp0"
if exist "%BIN_DIR%..\runtime\git\cmd\git.exe" set "PATH=%BIN_DIR%..\runtime\git\cmd;%PATH%"
if exist "%BIN_DIR%..\runtime\python\python.exe" (
  "%BIN_DIR%..\runtime\python\python.exe" "%BIN_DIR%launcher.py" %*
) else (
  py -3.12 -c "import sys" >nul 2>nul
  if errorlevel 1 (
    echo AEGIS requires Python 3.12. 1>&2
    exit /b 5
  )
  py -3.12 "%BIN_DIR%launcher.py" %*
)
exit /b %ERRORLEVEL%
